"""Shared utilities for Noosphere content generators."""
import json, os, sys, time, datetime, requests, subprocess

FEED_DIR = os.path.join(os.path.dirname(__file__), '..', 'feed')

def _read_openclaw_config_value(key_path):
    """Read a value from ~/.openclaw/openclaw.json using node.js.

    openclaw.json uses JSONC format (JS-style comments + trailing commas),
    which stdlib json.load() cannot parse. node.js eval handles it cleanly.
    key_path: dot-separated, e.g. 'gateway.auth.token'
    """
    config_path = os.path.expanduser('~/.openclaw/openclaw.json')
    if not os.path.exists(config_path):
        return None
    js_access = 'obj'
    for part in key_path.split('.'):
        js_access += f'?.[{json.dumps(part)}]'
    script = (
        f"const fs=require('fs');"
        f"const txt=fs.readFileSync({json.dumps(config_path)},'utf8');"
        f"const obj=eval('('+txt+')');"
        f"const val={js_access};"
        f"if(val)process.stdout.write(String(val));"
    )
    try:
        result = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=5)
        val = result.stdout.strip()
        return val if val else None
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None

def _get_llm_config():
    """Get LLM API configuration. Checks environment variables first, then OpenClaw config."""
    # Environment variables (for standalone/generic use)
    url = os.environ.get('LLM_API_URL')
    key = os.environ.get('LLM_API_KEY')
    model = os.environ.get('LLM_MODEL', 'claude-sonnet-4-20250514')
    
    if url and key:
        return url, key, model
    
    # Fall back to OpenClaw gateway config.
    # openclaw.json is JSONC — must use node.js to parse it.
    token = _read_openclaw_config_value('gateway.auth.token')
    if token:
        return 'http://localhost:18789/v1/chat/completions', token, model

    raise RuntimeError(
        "No LLM API configured. Set LLM_API_URL and LLM_API_KEY environment variables, "
        "or run with an OpenClaw gateway."
    )

_llm_ready = False

def _ensure_llm(url):
    """Make sure the local model server is up, starting it on demand.

    If LLM_FLEET_ID is set (a ~/.config/llm-fleet/<id>.conf entry), a dead
    endpoint is started via `systemctl --user start llm@<id>` and we wait for
    /health. The fleet's idle timer stops it again afterwards, so the GPU is
    only held while cards are actually being written. Without LLM_FLEET_ID
    this is a no-op and the request just fails as before.
    """
    global _llm_ready
    fleet_id = os.environ.get('LLM_FLEET_ID')
    if _llm_ready or not fleet_id:
        return
    base = url.split('/v1/')[0]
    def healthy():
        try:
            return requests.get(f"{base}/health", timeout=3).ok
        except requests.RequestException:
            return False
    if not healthy():
        # cron has no user-session env; systemctl --user needs the runtime dir.
        env = dict(os.environ)
        env.setdefault('XDG_RUNTIME_DIR', f"/run/user/{os.getuid()}")
        print(f"  LLM: starting llm@{fleet_id} ...")
        subprocess.run(['systemctl', '--user', 'start', f'llm@{fleet_id}'], env=env, check=False)
        for _ in range(60):  # ~3 min budget for a cold load
            if healthy():
                break
            time.sleep(3)
        else:
            raise RuntimeError(f"llm@{fleet_id} did not become healthy at {base}")
    _llm_ready = True

def ask_claude(prompt, system=None, max_tokens=1024, temperature=0.8):
    """Generate text via an OpenAI-compatible chat completions endpoint."""
    url, token, model = _get_llm_config()
    _ensure_llm(url)

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            # Disable "thinking" on reasoning models (e.g. gemma4) so the whole
            # token budget goes to the answer, not chain-of-thought. Harmless /
            # ignored by non-reasoning models and other OpenAI-compatible APIs.
            "reasoning_effort": "none",
        },
        timeout=180,  # a 12B cold-load into VRAM can exceed 60s
    )
    resp.raise_for_status()
    data = resp.json()
    return data['choices'][0]['message']['content']

def today():
    """Return today's date string YYYY-MM-DD.

    NOOSPHERE_DATE=YYYY-MM-DD overrides it, which is only meant for
    backfilling a preview feed by hand.
    """
    return os.environ.get('NOOSPHERE_DATE') or datetime.date.today().isoformat()

def today_date():
    """today() as a datetime.date (honours NOOSPHERE_DATE)."""
    return datetime.date.fromisoformat(today())

def now_iso():
    """Return current time as ISO string."""
    return datetime.datetime.now().isoformat(timespec='seconds')

NOOSPHERE_DISCORD_CHANNEL = os.environ.get('NOOSPHERE_DISCORD_CHANNEL', '')

def _post_to_discord(data):
    """Post a feed item to the Noosphere Discord channel via OpenClaw gateway."""
    try:
        # No channel configured → cross-posting disabled (don't spam the API).
        if not NOOSPHERE_DISCORD_CHANNEL:
            return
        # Find discord bot token. openclaw.json is JSONC — use node.js helper.
        discord_token = _read_openclaw_config_value('channels.discord.token')
        if not discord_token:
            print("  Discord: no bot token found, skipping")
            return

        # Format the card for Discord
        card_type = data.get('type', 'unknown')
        title = data.get('title', '')
        body = data.get('body', data.get('text', data.get('content', '')))

        # Strip HTML tags from any text content
        import re
        def strip_html(text):
            return re.sub(r'<[^>]+>', '', text) if text else text

        # Type-specific formatting
        type_labels = {
            'weather': '🌤 Lyrical Weather',
            'wittgenstein': '🪜 Wittgenstein\'s Ladder',
            'russian': '🇷🇺 Русский Час',
            'untranslatable': '🌍 The Untranslatable',
            'penny_red': '📮 The Penny Red',
            'git_log': '📟 git log --oneline',
            'apophenia': '🔮 Apophenia Machine',
            'midnight_postcard': '🌙 Midnight Postcard',
            'painting': '🖼 Midday Museum',
            'dead_medium': '📼 The Dead Medium',
            'the_diff': '📝 The Diff',
            'typeface': '🔤 Typeface of the Week',
            'recipe': '🍳 Recipe',
            'entropy_garden': '🌿 Entropy Garden',
            'annotation': '📖 Annotation Layer',
            'corpus_surprise': '🗣 Corpus Surprise',
            'music_rec': '🎵 You Should Hear This',
            'monthly_playlist': '📻 Monthly Playlist',
            'language': '🗺 A Language a Day',
            'poem': '🕯 The Night Poem',
            'link': '🔗 Open Tabs',
        }
        label = type_labels.get(card_type, card_type)

        # Build message
        parts = [f"**{label}**"]
        if title:
            parts.append(f"### {title}")
        
        # Handle type-specific body content
        if card_type == 'wittgenstein':
            num = data.get('number', '')
            prop = data.get('proposition', '')
            commentary = data.get('commentary', '')
            if num and prop:
                parts.append(f"**{num}** — {prop}")
            if commentary:
                parts.append(commentary)
        elif card_type == 'russian' and data.get('russian'):
            parts.append(f"*{data['russian']}*")
            if data.get('transliteration'):
                parts.append(f"`{data['transliteration']}`")
            if body:
                parts.append(strip_html(body))
        elif card_type == 'postcard':
            if data.get('image'):
                parts.append(data['image'])
            if data.get('photographer'):
                parts.append(f"-# Photo: {data['photographer']}")
        elif card_type == 'painting':
            if data.get('title') or data.get('artist'):
                parts.append(f"*{data.get('title', '')}* — **{data.get('artist', '')}**")
            bits = [b for b in (data.get('date'), data.get('medium'), data.get('origin')) if b]
            if bits:
                parts.append(' · '.join(bits))
            if data.get('image'):
                parts.append(data['image'])
            if data.get('museum'):
                parts.append(f"-# {data['museum']}")
        elif card_type == 'music_rec':
            if data.get('artist'):
                parts.append(f"**{data.get('track', '')}** by **{data['artist']}**")
            if data.get('album') and data.get('year'):
                parts.append(f"*{data['album']}* ({data['year']})")
            if body:
                parts.append(body)
            if data.get('spotify_url'):
                parts.append(data['spotify_url'])
        elif card_type == 'monthly_playlist':
            if data.get('description'):
                parts.append(f"*{data['description']}*")
            parts.append(f"{data.get('track_count', 0)} tracks · {data.get('daily_rec_count', 0)} from daily recs · {data.get('curated_count', 0)} curated")
            if data.get('tracks'):
                track_lines = [f"  {t['track']} — {t['artist']}" for t in data['tracks'][:10]]
                parts.append('\n'.join(track_lines))
                if len(data['tracks']) > 10:
                    parts.append(f"  *+ {len(data['tracks']) - 10} more*")
            if data.get('spotify_url'):
                parts.append(data['spotify_url'])
        elif card_type == 'recipe' and data.get('ingredients'):
            if body:
                parts.append(strip_html(body))
            parts.append("**Ingredients:** " + ', '.join(data['ingredients'][:8]))
            if data.get('source_url'):
                parts.append(f"[Full recipe](<{data['source_url']}>)")
        elif card_type == 'git_log' and data.get('commits'):
            parts.append('```')
            for c in data['commits'][:8]:
                parts.append(c if isinstance(c, str) else f"{c.get('hash','')} {c.get('message','')}")
            parts.append('```')
        elif card_type == 'entropy_garden':
            if data.get('algorithm'):
                parts.append(f"*{data['algorithm']}*")
            if body:
                parts.append(strip_html(body))
        else:
            if body:
                body = strip_html(body)
                if len(body) > 1500:
                    body = body[:1500] + '…'
                parts.append(body)

        # Add source/attribution if present
        if data.get('source'):
            parts.append(f"-# {data['source']}")
        elif data.get('attribution'):
            parts.append(f"-# {data['attribution']}")

        msg = '\n'.join(parts)

        # Post via Discord API directly
        resp = requests.post(
            f'https://discord.com/api/v10/channels/{NOOSPHERE_DISCORD_CHANNEL}/messages',
            headers={"Authorization": f"Bot {discord_token}", "Content-Type": "application/json"},
            json={"content": msg},
            timeout=15,
        )
        if resp.ok:
            print(f"  Discord: posted to #{NOOSPHERE_DISCORD_CHANNEL}")
        else:
            print(f"  Discord: failed ({resp.status_code}): {resp.text[:200]}")
    except Exception as e:
        print(f"  Discord: error posting — {e}")

def write_feed(name, data, post_discord=True):
    """Write a feed item JSON file. name should be like '2026-02-16-weather'.

    post_discord=False suppresses the Discord cross-post (used by the echoes
    generator so reruns don't spam the channel).
    """
    os.makedirs(FEED_DIR, exist_ok=True)
    path = os.path.join(FEED_DIR, f"{name}.json")
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Wrote {path}")
    if post_discord:
        _post_to_discord(data)
    return path

def feed_exists(name):
    """Check if a feed item already exists for today."""
    path = os.path.join(FEED_DIR, f"{name}.json")
    return os.path.exists(path)


# ---------------------------------------------------------------------------
# Source helpers (v2 streams)
#
# The streams quote real sources and never ask the model for facts. These
# helpers fetch the sources. Every request uses a generic client name with no
# personal details in it.
# ---------------------------------------------------------------------------

UA = {'User-Agent': 'NoosphereFeed/2.0 (personal reading feed)'}


def clip(text, max_chars=420):
    """Cut text at the last full sentence that fits in max_chars."""
    text = ' '.join((text or '').split())
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    best = max(cut.rfind('. '), cut.rfind('! '), cut.rfind('? '), cut.rfind('." '))
    if best > max_chars * 0.4:
        return cut[:best + 1]
    space = cut.rfind(' ')
    return (cut[:space] if space > 0 else cut).rstrip(',;:') + '…'


def get_json(url, params=None, headers=None, timeout=20):
    h = dict(UA)
    if headers:
        h.update(headers)
    resp = requests.get(url, params=params, headers=h, timeout=timeout)
    for wait in (10, 30):
        if resp.status_code != 429:
            break
        # Wikimedia throttles bursts. A daily job can afford to be patient.
        try:
            wait = min(60, max(wait, int(resp.headers.get('Retry-After', wait))))
        except ValueError:
            pass
        time.sleep(wait)
        resp = requests.get(url, params=params, headers=h, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


class SourceUnavailable(RuntimeError):
    """A source could not be reached. The generator should write nothing and
    leave its state alone, so the next cron run tries the same item again."""


def wiki_summary(title, site='en.wikipedia.org'):
    """Lead summary of a Wikipedia article, or None if there is no article.

    Uses the action API, which is throttled far less than the REST summary
    endpoint.
    """
    try:
        d = get_json(f"https://{site}/w/api.php", params={
            'action': 'query', 'format': 'json', 'redirects': 1, 'titles': title,
            'prop': 'extracts|pageimages|description|info|pageprops',
            'exintro': 1, 'explaintext': 1, 'inprop': 'url',
            'pithumbsize': 640, 'ppprop': 'disambiguation',
        })
        page = next(iter(d['query']['pages'].values()))
    except Exception as e:
        raise SourceUnavailable(f"wiki summary for {title!r}: {e}")
    if 'missing' in page or 'disambiguation' in (page.get('pageprops') or {}):
        return None
    extract = ' '.join((page.get('extract') or '').split())
    if not extract:
        return None
    return {
        'title': page.get('title', title),
        'description': page.get('description', ''),
        'extract': extract,
        'url': page.get('fullurl', ''),
        'thumbnail': (page.get('thumbnail') or {}).get('source', ''),
    }


def wiki_plaintext(title, site='en.wikipedia.org'):
    """Whole article as plain text with == Heading == lines, or ''."""
    try:
        d = get_json(f"https://{site}/w/api.php", params={
            'action': 'query', 'prop': 'extracts', 'explaintext': 1,
            'exsectionformat': 'wiki', 'titles': title, 'redirects': 1,
            'format': 'json',
        })
        page = next(iter(d['query']['pages'].values()))
        return page.get('extract', '') or ''
    except Exception as e:
        raise SourceUnavailable(f"wiki text for {title!r}: {e}")


def split_sections(text):
    """[(level, heading, body)] from wiki plain text. The lead has heading ''."""
    import re
    out, level, heading, buf = [], 0, '', []
    for line in text.split('\n'):
        m = re.match(r'^(={2,6})\s*(.*?)\s*=+\s*$', line)
        if m:
            out.append((level, heading, '\n'.join(buf).strip()))
            level, heading, buf = len(m.group(1)), m.group(2), []
        else:
            buf.append(line)
    out.append((level, heading, '\n'.join(buf).strip()))
    return out


def wiki_section(title, wanted, site='en.wikipedia.org'):
    """Text of the first section whose heading starts with one of `wanted`.

    Returns (heading, text) or (None, '').
    """
    sections = split_sections(wiki_plaintext(title, site))
    for want in wanted:
        for i, (level, heading, body) in enumerate(sections):
            if not heading.lower().startswith(want.lower()):
                continue
            if len(body) < 80:
                # A bare heading whose text lives in its subsections.
                for lv2, _h2, b2 in sections[i + 1:]:
                    if lv2 <= level:
                        break
                    body = (body + ' ' + b2).strip()
                    if len(body) >= 80:
                        break
            if len(body) >= 80:
                return heading, body
    return None, ''


def wiktionary_etymology(word):
    """English etymology text from en.wiktionary, or ''."""
    sections = split_sections(wiki_plaintext(word, site='en.wiktionary.org'))
    in_english = False
    for level, heading, body in sections:
        if level == 2:
            in_english = heading.strip().lower() == 'english'
        elif in_english and heading.lower().startswith('etymology') and body:
            return ' '.join(body.split())
    return ''


def strip_tags(html):
    import re, html as _html
    return _html.unescape(re.sub(r'<[^>]+>', '', html or '')).strip()


def wiktionary_definitions(word, language_name, limit=3):
    """[(part of speech, definition)] for `word` in one language, from
    en.wiktionary. Empty list if the entry or the language is missing."""
    import urllib.parse
    try:
        d = get_json("https://en.wiktionary.org/api/rest_v1/page/definition/"
                     + urllib.parse.quote(word, safe=''))
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            return []  # no such entry
        raise SourceUnavailable(f"wiktionary entry for {word!r}: {e}")
    except Exception as e:
        raise SourceUnavailable(f"wiktionary entry for {word!r}: {e}")
    want = language_name.lower()
    out = []
    for entries in d.values():
        for entry in entries:
            lang = (entry.get('language') or '').lower()
            if lang != want:
                continue
            for df in entry.get('definitions', []):
                text = strip_tags(df.get('definition', ''))
                low = text.lower()
                # Skip footnotes and bare inflection notes ("plural of ...").
                if text.startswith('↑') or ' of ' in low[:60] and any(
                        k in low[:60] for k in ('singular', 'plural', 'participle',
                                                'inflection', 'form of', 'tense')):
                    continue
                if text and len(text) > 3:
                    out.append((entry.get('partOfSpeech', ''), text))
                if len(out) >= limit:
                    return out
    return out


def try_llm(prompt, system=None, max_tokens=300, temperature=0.2):
    """ask_claude that returns None instead of raising. A card never waits on
    the model, so the caller writes the card with or without the answer.

    NOOSPHERE_NO_LLM=1 skips the model entirely (for tests and previews, or
    for a day when the GPU is spoken for)."""
    if os.environ.get('NOOSPHERE_NO_LLM'):
        return None
    try:
        out = ask_claude(prompt, system=system, max_tokens=max_tokens, temperature=temperature)
        return (out or '').strip() or None
    except Exception as e:
        print(f"  LLM unavailable, continuing without it: {e}")
        return None


def translate(text, language):
    """Plain English translation of one sentence by the local model.

    This is the only job the model still has in the text streams. The prompt
    asks for a translation and nothing else, and the result is thrown away if
    it does not look like one.
    """
    out = try_llm(
        f"Translate this {language} sentence into plain, literal English.\n\n"
        f"{text}\n\n"
        "Reply with the English translation only. Do not add notes, "
        "alternatives, explanations or quotation marks.",
        system="You are a careful translator. You output only the translation.",
        max_tokens=400, temperature=0.1,
    )
    if not out:
        return None
    out = out.strip().strip('"“”«»').strip()
    out = out.split('\n')[0].strip()
    if not out or len(out) > max(200, len(text) * 6) or len(out) < 3:
        return None
    return out
