#!/usr/bin/env python3
"""Open Tabs. One link a day from a short list of blogs and journals.

The card is the feed item as its publisher wrote it: title, site, author, date
and the opening of the summary. Feeds take turns so that one busy site cannot
fill the stream. No model summarises anything.
"""
import json, os, random, re, time
import requests
from utils import today, today_date, write_feed, feed_exists, UA, strip_tags, clip

STATE_FILE = os.path.join(os.path.dirname(__file__), '.link-state.json')
MAX_AGE_DAYS = 21

FEEDS = [
    ("Language Log", "https://languagelog.ldc.upenn.edu/nll/?feed=rss2"),
    ("Languagehat", "https://languagehat.com/feed/"),
    ("All Things Linguistic", "https://allthingslinguistic.com/rss"),
    ("The Public Domain Review", "https://publicdomainreview.org/rss.xml"),
    ("Quanta Magazine", "https://www.quantamagazine.org/feed/"),
    ("JSTOR Daily", "https://daily.jstor.org/feed/"),
    ("Aeon", "https://aeon.co/feed.rss"),
    ("Atlas Obscura", "https://www.atlasobscura.com/feeds/latest"),
    ("Low-tech Magazine", "https://solar.lowtechmagazine.com/posts/index.xml"),
    ("Strong Language", "https://stronglang.wordpress.com/feed/"),
    ("arXiv cs.CL", "https://rss.arxiv.org/rss/cs.CL"),
]


def clean_url(url):
    """Drop tracking parameters that feeds append."""
    url = re.sub(r'([?&])utm_[a-z]+=[^&#]*', r'\1', url)
    return re.sub(r'[?&]+$', '', url.replace('?&', '?').replace('&&', '&'))


def entries(site, feed_url):
    import feedparser
    resp = requests.get(feed_url, headers=UA, timeout=25)
    resp.raise_for_status()
    parsed = feedparser.parse(resp.content)
    out = []
    for e in parsed.entries[:40]:
        when = e.get('published_parsed') or e.get('updated_parsed')
        if not e.get('link') or not e.get('title') or not when:
            continue
        summary = strip_tags(e.get('summary', ''))
        # arXiv prefixes its abstracts with an announcement line.
        summary = re.sub(r'^arXiv:\S+\s+Announce Type:\s*\S+\s*Abstract:\s*', '', summary)
        # WordPress feeds end summaries with "The post X appeared first on Y."
        summary = re.sub(r'\s*The post .{0,200} appeared first on .{0,80}\.?$', '', summary)
        summary = re.sub(r'\s*\[(…|\.\.\.|&#8230;)\]\s*$', '…', summary)
        out.append({
            'site': site,
            'title': ' '.join(strip_tags(e['title']).split()),
            'url': clean_url(e['link']),
            'author': (e.get('author') or '').strip(),
            'published': time.strftime('%Y-%m-%d', when),
            'summary': clip(summary, 420),
        })
    return out


def generate():
    name = f"{today()}-link"
    if feed_exists(name):
        print(f"Already exists: {name}")
        return

    state = {'seen': [], 'last_sites': []}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                state.update(json.load(f))
        except (json.JSONDecodeError, ValueError):
            pass
    seen = set(state['seen'])
    recent_sites = state['last_sites'][-5:]

    # Sites not used lately go first, in random order.
    order = [f for f in FEEDS if f[0] not in recent_sites]
    random.shuffle(order)
    order += [f for f in FEEDS if f[0] in recent_sites]

    today_d = today_date()
    pick = None
    for site, url in order:
        try:
            items = entries(site, url)
        except Exception as e:
            print(f"  {site}: feed unavailable ({e})")
            continue
        fresh = []
        for it in items:
            age = (today_d - today_d.fromisoformat(it['published'])).days
            if it['url'] not in seen and -1 <= age <= MAX_AGE_DAYS and len(it['title']) > 3:
                fresh.append(it)
        if fresh:
            # arXiv lists hundreds of papers a day, so any of them will do.
            pick = random.choice(fresh) if site.startswith('arXiv') else fresh[0]
            break
    if not pick:
        print("No fresh link found in any feed")
        return

    write_feed(name, {
        "type": "link",
        "v": 2,
        "timestamp": f"{today()}T16:00:00",
        **pick,
    })
    state['seen'] = (state['seen'] + [pick['url']])[-600:]
    state['last_sites'] = (state['last_sites'] + [pick['site']])[-8:]
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=1)


if __name__ == '__main__':
    generate()
