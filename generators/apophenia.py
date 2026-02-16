#!/usr/bin/env python3
"""The Apophenia Machine — juxtapose two unrelated things and ask 'what connects these?'

Pulls from Wikipedia random article API + arxiv API + Poetry Foundation + misc sources.
"""
import requests, random, json, re
from utils import ask_claude, today, write_feed, feed_exists

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
        headers={'User-Agent': 'Noosphere/1.0 (personal feed)'},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    return {
        'type': 'wikipedia',
        'title': data.get('title', ''),
        'content': truncate_sentence(data.get('extract', ''), 350),
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
        f'http://export.arxiv.org/api/query?search_query=cat:{cat}&sortBy=submittedDate&sortOrder=descending&start={random.randint(0,50)}&max_results=1',
        timeout=10,
    )
    resp.raise_for_status()
    # Parse XML (simple extraction)
    text = resp.text
    title_match = re.search(r'<title>([^<]+)</title>', text[text.find('<entry>'):] if '<entry>' in text else '')
    summary_match = re.search(r'<summary>([^<]+)</summary>', text)
    
    title = title_match.group(1).strip() if title_match else 'Untitled'
    summary = summary_match.group(1).strip()[:300] if summary_match else ''
    summary = ' '.join(summary.split())  # normalize whitespace
    
    return {
        'type': 'arxiv',
        'title': title,
        'content': summary,
    }

def get_poem_fragment():
    """Generate a poem fragment via Claude (more reliable than scraping)."""
    prompt = """Give me a real 2-4 line fragment from a published poem — something vivid and strange. 
Include the poet's name and poem title. Pick something lesser-known, not the usual anthology pieces.
Format: the lines, then "— Poet Name, 'Title'" on the last line.
Just the poem and attribution, nothing else."""
    
    result = ask_claude(prompt, max_tokens=150, temperature=0.95)
    return {
        'type': 'poem',
        'title': 'Poetry Fragment',
        'content': result.strip(),
    }

def get_historical_fact():
    """Get an interesting historical fact via Claude."""
    prompt = """Give me one obscure, specific historical fact — something that happened on a particular 
date involving a particular person or event. Not well-known. Make it genuinely surprising.
2-3 sentences max. Include the year. Just the fact, no preamble, no meta-commentary, no "let me try again." 
One fact, stated cleanly."""
    
    result = ask_claude(prompt, max_tokens=150, temperature=0.95)
    return {
        'type': 'history',
        'title': 'Historical Fact',
        'content': result.strip(),
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
        "timestamp": f"{today()}T14:00:00",
        "item_a": {
            "type": items[0]['type'],
            "content": f"<strong>{items[0]['title']}</strong><br><br>{items[0]['content']}",
        },
        "item_b": {
            "type": items[1]['type'],
            "content": f"<strong>{items[1]['title']}</strong><br><br>{items[1]['content']}",
        },
    })

if __name__ == '__main__':
    generate()
