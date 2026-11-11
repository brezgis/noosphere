#!/usr/bin/env python3
"""Typeface of the Week. A real typeface from Wikipedia's typeface categories.

The card shows the specimen image and the lead of the article. No model
writes anything.
"""
import json, os, random, requests
from utils import today, write_feed, feed_exists, clip

HEADERS = {"User-Agent": "NoosphereFeed/2.0 (personal reading feed)"}

# Wikipedia categories to sample from
CATEGORIES = [
    "Category:Sans-serif typefaces",
    "Category:Serif typefaces",
    "Category:Monospaced typefaces",
    "Category:Script typefaces",
    "Category:Display typefaces",
    "Category:Blackletter typefaces",
    "Category:Slab serif typefaces",
    "Category:Humanist sans-serif typefaces",
    "Category:Geometric sans-serif typefaces",
    "Category:Grotesque sans-serif typefaces",
    "Category:Transitional serif typefaces",
    "Category:Old-style serif typefaces",
]

STATE_FILE = os.path.join(os.path.dirname(__file__), '.typeface-state.json')

def get_category_members(category, limit=50):
    """Get page titles from a Wikipedia category."""
    try:
        resp = requests.get("https://en.wikipedia.org/w/api.php", params={
            "action": "query",
            "list": "categorymembers",
            "cmtitle": category,
            "cmlimit": str(limit),
            "cmtype": "page",
            "format": "json",
        }, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        return [p["title"] for p in resp.json()["query"]["categorymembers"]
                if not p["title"].startswith("List of")]
    except Exception:
        return []

def get_article_summary(title):
    """Get a Wikipedia article summary via the REST API."""
    try:
        safe_title = title.replace(" ", "_")
        resp = requests.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{safe_title}",
            headers=HEADERS, timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            "title": data.get("title", title),
            "extract": data.get("extract", ""),
            "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
            "description": data.get("description", ""),
            "thumbnail": data.get("thumbnail", {}).get("source", ""),
        }
    except Exception:
        return None

def get_used():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return set(json.load(f).get("used", []))
    return set()

def save_used(used):
    with open(STATE_FILE, "w") as f:
        json.dump({"used": list(used)}, f)

def generate():
    name = f"{today()}-typeface"
    if feed_exists(name):
        print(f"Already exists: {name}")
        return

    used = get_used()

    # Gather typeface pages from random categories
    all_typefaces = []
    cats = random.sample(CATEGORIES, min(4, len(CATEGORIES)))
    for cat in cats:
        all_typefaces.extend(get_category_members(cat))

    # Filter out already-used, list pages, and category pages
    available = [t for t in all_typefaces
                 if t not in used
                 and not t.startswith("List of")
                 and not t.startswith("Category:")
                 and "typefaces" not in t.lower()]

    if not available:
        # Reset if exhausted
        used = set()
        available = all_typefaces

    if not available:
        print("No typefaces found from Wikipedia")
        return

    # Pick one and get its article
    title = random.choice(available)
    article = get_article_summary(title)

    if not article or len(article["extract"]) < 50:
        # Try another
        for backup in random.sample(available, min(5, len(available))):
            article = get_article_summary(backup)
            if article and len(article["extract"]) > 50:
                title = backup
                break

    if not article or len(article["extract"]) < 50:
        print(f"Couldn't get a good article for any typeface")
        return

    used.add(title)
    save_used(used)

    # Clean the title (remove "(typeface)" suffix for display)
    display_name = title.replace(" (typeface)", "").replace(" (font)", "")

    write_feed(name, {
        "type": "typeface",
        "v": 2,
        "timestamp": f"{today()}T09:30:00",
        "font_name": display_name,
        "description": article["description"],
        "extract": clip(article["extract"], 560),
        "wikipedia_url": article["url"],
        "thumbnail": article.get("thumbnail", ""),
    })

if __name__ == '__main__':
    generate()
