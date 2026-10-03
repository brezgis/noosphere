#!/usr/bin/env python3
"""Midday Museum — a public-domain painting from the Art Institute of Chicago.

(Internal card type stays "painting"; "Midday Museum" is the display name —
a midday counterpart to the Midnight Postcard.)

A deliberately visual card, placed midday to break up the text-heavy streams.
No LLM commentary — just the image and a museum placard (title, artist, date,
medium, origin). All facts come straight from the museum's own metadata, so
there is nothing to hallucinate.

Source: Art Institute of Chicago public API (no key required). Metadata is CC0;
images shown are public domain, served on the fly via IIIF.
"""
import requests, random
from utils import today, write_feed, feed_exists

AIC_SEARCH = "https://api.artic.edu/api/v1/artworks/search"
UA = {"AIC-User-Agent": "Noosphere (personal feed; annabrezgis@gmail.com)"}

# Evocative subjects — rotated for day-to-day variety across the collection.
SUBJECTS = [
    "landscape", "portrait", "still life", "the sea", "night", "garden",
    "river", "mountains", "storm", "snow", "harbor", "forest", "flowers",
    "street", "interior", "moonlight", "dancers", "horses", "city", "rain",
    "twilight", "figures", "boats", "autumn", "window", "bridge", "clouds",
    "coast", "meadow", "market", "cathedral", "sunset",
]

FIELDS = ",".join([
    "id", "title", "artist_display", "artist_title", "date_display",
    "medium_display", "place_of_origin", "image_id", "classification_titles",
    "credit_line", "thumbnail",
])


# IIIF refuses to upscale (403), so never ask for more pixels than the scan
# has; and skip scans too small to look good on a card at all.
MAX_WIDTH = 1200
MIN_WIDTH = 800


def source_width(art):
    return (art.get("thumbnail") or {}).get("width") or 0


def is_painting(art):
    """Keep only actual paintings (drop prints, sculpture, photos, etc.)."""
    cls = art.get("classification_titles") or []
    return any("painting" in (c or "").lower() for c in cls)


def fetch_candidates(subject, page):
    resp = requests.get(
        AIC_SEARCH,
        params={
            "q": subject,
            "query[term][is_public_domain]": "true",
            "fields": FIELDS,
            "limit": 100,
            "page": page,
        },
        headers=UA,
        timeout=20,
    )
    resp.raise_for_status()
    payload = resp.json()
    iiif = payload.get("config", {}).get("iiif_url", "https://www.artic.edu/iiif/2")
    return iiif, payload.get("data", [])


def pick_painting():
    """Try several random subjects/pages until a public-domain painting turns up."""
    for subject in random.sample(SUBJECTS, k=min(6, len(SUBJECTS))):
        # AIC forbids a result offset >= 1000 (403). With limit 100 that means
        # pages 1..9 (offset <= 800) — still ~900 works per subject for variety.
        page = random.randint(1, 9)
        try:
            iiif, data = fetch_candidates(subject, page)
        except Exception as e:
            print(f"  search failed for {subject!r} p{page}: {e}")
            continue
        paintings = [a for a in data if a.get("image_id") and is_painting(a)
                     and source_width(a) >= MIN_WIDTH]
        if paintings:
            return iiif, random.choice(paintings), subject
    return None, None, None


def generate():
    name = f"{today()}-painting"
    if feed_exists(name):
        print(f"Already exists: {name}")
        return

    iiif, art, subject = pick_painting()
    if not art:
        print("Couldn't find a painting")
        return

    thumb = art.get("thumbnail") or {}
    write_feed(name, {
        "type": "painting",
        # Midday slot: sits between git_log (12:00) and the afternoon cluster,
        # a visual break in the middle of the day's text feeds.
        "timestamp": f"{today()}T13:00:00",
        # IIIF resizes on request; up to 1200px wide is crisp on retina, light to load.
        "image": f"{iiif}/{art['image_id']}/full/{min(MAX_WIDTH, source_width(art))},/0/default.jpg",
        "title": art.get("title") or "Untitled",
        "artist": art.get("artist_title") or art.get("artist_display") or "Unknown artist",
        "date": art.get("date_display") or "",
        "medium": art.get("medium_display") or "",
        "origin": art.get("place_of_origin") or "",
        "museum": "The Art Institute of Chicago",
        "credit": art.get("credit_line") or "",
        "source_url": f"https://www.artic.edu/artworks/{art['id']}",
        "alt": thumb.get("alt_text") or art.get("title") or "",
    })


if __name__ == "__main__":
    generate()
