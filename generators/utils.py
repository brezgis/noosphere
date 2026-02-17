"""Shared utilities for Noosphere content generators."""
import json, os, sys, datetime, requests

FEED_DIR = os.path.join(os.path.dirname(__file__), '..', 'feed')

def _get_llm_config():
    """Get LLM API configuration. Checks environment variables first, then OpenClaw config."""
    # Environment variables (for standalone/generic use)
    url = os.environ.get('LLM_API_URL')
    key = os.environ.get('LLM_API_KEY')
    model = os.environ.get('LLM_MODEL', 'claude-sonnet-4-20250514')
    
    if url and key:
        return url, key, model
    
    # Fall back to OpenClaw gateway config
    for config_name in ['openclaw.json', 'config.json']:
        for config_dir in ['~/.openclaw', '~/.clawdbot']:
            config_path = os.path.expanduser(os.path.join(config_dir, config_name))
            if os.path.exists(config_path):
                try:
                    with open(config_path) as f:
                        config = json.load(f)
                    token = config.get('gateway', {}).get('auth', {}).get('token', '')
                    if token:
                        return 'http://localhost:18789/v1/chat/completions', token, model
                except (json.JSONDecodeError, KeyError):
                    continue
    
    raise RuntimeError(
        "No LLM API configured. Set LLM_API_URL and LLM_API_KEY environment variables, "
        "or run with an OpenClaw gateway."
    )

def ask_claude(prompt, system=None, max_tokens=1024, temperature=0.8):
    """Generate text via an OpenAI-compatible chat completions endpoint."""
    url, token, model = _get_llm_config()
    
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
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    return data['choices'][0]['message']['content']

def today():
    """Return today's date string YYYY-MM-DD."""
    return datetime.date.today().isoformat()

def now_iso():
    """Return current time as ISO string."""
    return datetime.datetime.now().isoformat(timespec='seconds')

NOOSPHERE_DISCORD_CHANNEL = os.environ.get('NOOSPHERE_DISCORD_CHANNEL', '')

def _post_to_discord(data):
    """Post a feed item to the Noosphere Discord channel via OpenClaw gateway."""
    try:
        # Find gateway token
        token = None
        for config_name in ['openclaw.json', 'config.json']:
            for config_dir in ['~/.openclaw', '~/.clawdbot']:
                config_path = os.path.expanduser(os.path.join(config_dir, config_name))
                if os.path.exists(config_path):
                    try:
                        with open(config_path) as f:
                            config = json.load(f)
                        token = config.get('gateway', {}).get('auth', {}).get('token', '')
                        if token:
                            break
                    except (json.JSONDecodeError, KeyError):
                        continue
            if token:
                break
        if not token:
            print("  Discord: no gateway token found, skipping")
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
            'dead_medium': '📼 The Dead Medium',
            'the_diff': '📝 The Diff',
            'typeface': '🔤 Typeface of the Week',
            'recipe': '🍳 Recipe',
            'entropy_garden': '🌿 Entropy Garden',
            'annotation': '📖 Annotation Layer',
            'corpus_surprise': '🗣 Corpus Surprise',
            'music_rec': '🎵 You Should Hear This',
            'monthly_playlist': '📻 Monthly Playlist',
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
        discord_token = config.get('channels', {}).get('discord', {}).get('token', '')
        if not discord_token:
            print("  Discord: no bot token found, skipping")
            return
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

def write_feed(name, data):
    """Write a feed item JSON file. name should be like '2026-02-16-weather'."""
    os.makedirs(FEED_DIR, exist_ok=True)
    path = os.path.join(FEED_DIR, f"{name}.json")
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Wrote {path}")
    _post_to_discord(data)
    return path

def feed_exists(name):
    """Check if a feed item already exists for today."""
    path = os.path.join(FEED_DIR, f"{name}.json")
    return os.path.exists(path)
