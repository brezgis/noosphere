#!/usr/bin/env python3
"""The Apophenia Machine. Two unrelated real things, side by side.

Pulls from Wikipedia's random article API, arXiv, PoetryDB and Wikipedia's On
This Day feed. The card asks what connects them and leaves the answer to the
reader. (The model used to answer, and its answers were filler.)
"""
import requests, random, json, re
from utils import UA
from datetime import date
from utils import today, today_date, write_feed, feed_exists

def truncate_sentence(text, max_chars=350):
    """Truncate text at the last complete sentence within max_chars."""
    if len(text) <= max_chars:
        return text
    # Find last sentence-ending punctuation before the limit
    truncated = text[:max_chars]
    for end in ['. ', '! ', '? ']:
        idx = truncated.rfind(end)
        if idx > 0:
            return truncated[:idx + 1]
    # Fallback: cut at last space and add ellipsis
    idx = truncated.rfind(' ')
    return truncated[:idx] + '…' if idx > 0 else truncated + '…'

def get_wikipedia_random():
    """Get a random Wikipedia article summary."""
    resp = requests.get(
        'https://en.wikipedia.org/api/rest_v1/page/random/summary',
        headers=UA,
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    return {
        'type': 'wikipedia',
        'title': data.get('title', ''),
        'content': truncate_sentence(data.get('extract', ''), 250),
        'url': data.get('content_urls', {}).get('desktop', {}).get('page', ''),
    }

def get_arxiv_random():
    """Get a random recent arxiv paper."""
    # Search for recent papers in interesting categories
    categories = ['cs.CL', 'cs.AI', 'physics.soc-ph', 'q-bio.NC', 'math.HO', 
                  'cs.CY', 'stat.ML', 'physics.hist-ph', 'cond-mat.stat-mech',
                  'nlin.AO', 'cs.SI', 'econ.GN']
    cat = random.choice(categories)
    resp = requests.get(
        f'https://export.arxiv.org/api/query?search_query=cat:{cat}&sortBy=submittedDate&sortOrder=descending&start={random.randint(0,50)}&max_results=1',
        headers=UA, timeout=20,
    )
    resp.raise_for_status()
    # Parse XML (simple extraction)
    text = resp.text
    title_match = re.search(r'<title>([^<]+)</title>', text[text.find('<entry>'):] if '<entry>' in text else '')
    if not title_match:
        raise ValueError('arXiv returned no entry')
    summary_match = re.search(r'<summary>([^<]+)</summary>', text)
    
    title = ' '.join(title_match.group(1).split())
    summary = summary_match.group(1).strip()[:300] if summary_match else ''
    summary = ' '.join(summary.split())  # normalize whitespace
    
    # Extract arxiv URL from <id> tag inside <entry>
    entry_text = text[text.find('<entry>'):] if '<entry>' in text else ''
    id_match = re.search(r'<id>(https?://[^<]+)</id>', entry_text)
    url = id_match.group(1).strip() if id_match else ''
    url = re.sub(r'v\d+$', '', url.replace('http://', 'https://'))
    
    return {
        'type': 'arxiv',
        'title': title,
        'content': truncate_sentence(summary, 250),
        'url': url,
    }

def get_poem_fragment():
    """A real fragment of a real public-domain poem, via PoetryDB.

    Previously this asked the LLM to quote "a lesser-known poem" from memory,
    which a small local model answers by inventing verse and pinning it on a
    real poet. PoetryDB serves actual texts, so the quote is always genuine.
    """
    for _ in range(5):
        resp = requests.get('https://poetrydb.org/random/1', headers=UA, timeout=15)
        resp.raise_for_status()
        poem = resp.json()[0]
        # split into stanzas, pick one, take 2-4 consecutive lines from it
        stanzas, cur = [], []
        for line in poem.get('lines', []):
            if line.strip():
                cur.append(line.strip())
            elif cur:
                stanzas.append(cur); cur = []
        if cur:
            stanzas.append(cur)
        stanzas = [s for s in stanzas if len(s) >= 2]
        if not stanzas:
            continue
        stanza = random.choice(stanzas)
        n = min(len(stanza), random.randint(2, 4))
        start = random.randint(0, len(stanza) - n)
        lines = stanza[start:start + n]
        if sum(len(l) for l in lines) > 320:
            continue
        return {
            'type': 'poem',
            'title': f"{poem['author']}, “{poem['title']}”",
            'content': '\n'.join(lines),
        }
    raise RuntimeError('PoetryDB returned nothing usable')

def get_historical_fact():
    """A real event that happened on today's date, via Wikipedia's On This Day API.

    Previously this asked Claude for "an obscure historical fact," which happily
    invented plausible-sounding but fictional events. On This Day returns real,
    sourced events with a Wikipedia link — no fabrication.
    """
    d = today_date()
    resp = requests.get(
        f'https://en.wikipedia.org/api/rest_v1/feed/onthisday/events/{d.month:02d}/{d.day:02d}',
        headers=UA,
        timeout=10,
    )
    resp.raise_for_status()
    events = resp.json().get('events', [])
    if not events:
        raise ValueError('no On This Day events returned')

    ev = random.choice(events)
    pages = ev.get('pages') or []
    page = pages[0] if pages else {}
    url = page.get('content_urls', {}).get('desktop', {}).get('page', '')
    year = ev.get('year', '')
    when = f"{d:%B} {d.day}"
    title = f"{when}, {year}" if year else when

    return {
        'type': 'history',
        'title': title,
        'content': truncate_sentence(ev.get('text', '').strip(), 250),
        'url': url,
    }

SOURCES = [
    ('wikipedia', get_wikipedia_random),
    ('arxiv', get_arxiv_random),
    ('poem', get_poem_fragment),
    ('history', get_historical_fact),
]

def generate():
    name = f"{today()}-apophenia"
    if feed_exists(name):
        print(f"Already exists: {name}")
        return

    # Pick two different source types
    source_types = random.sample(SOURCES, 2)
    
    items = []
    for stype, fn in source_types:
        try:
            item = fn()
            items.append(item)
        except Exception as e:
            print(f"Failed to get {stype}: {e}")
            # Fallback
            try:
                item = get_wikipedia_random()
                items.append(item)
            except:
                pass
    
    if len(items) < 2:
        print("Couldn't get two items")
        return

    write_feed(name, {
        "type": "apophenia",
        "v": 2,
        "timestamp": f"{today()}T14:00:00",
        "items": [{
            "kind": it['type'],
            "title": it['title'],
            "text": it['content'],
            "url": it.get('url', ''),
        } for it in items],
        "prompt": "What connects these?",
    })

if __name__ == '__main__':
    generate()
