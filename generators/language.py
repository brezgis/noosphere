#!/usr/bin/env python3
"""A Language a Day. One language from the World Atlas of Language Structures.

Each card is a small typological profile: family, genus, where it is spoken,
and a handful of WALS feature values (word order, tone, whether "hand" and
"arm" are one word, where the word for tea came from). Every value is copied
from WALS as coded by its authors. data/wals.json is built by build_wals.py.

Source: Dryer & Haspelmath (eds.) 2013, WALS Online, https://wals.info (CC BY 4.0).
"""
import json, os, random
from utils import today, write_feed, feed_exists

DATA_FILE = os.path.join(os.path.dirname(__file__), 'data', 'wals.json')
STATE_FILE = os.path.join(os.path.dirname(__file__), '.language-state.json')
MAX_FEATURES = 8


def generate():
    name = f"{today()}-language"
    if feed_exists(name):
        print(f"Already exists: {name}")
        return

    with open(DATA_FILE, encoding='utf-8') as f:
        data = json.load(f)
    languages = data['languages']

    used = set()
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                used = set(json.load(f).get('used', []))
        except (json.JSONDecodeError, ValueError):
            used = set()
    available = [l for l in languages if l['id'] not in used]
    if not available:
        used, available = set(), languages

    lang = random.choice(available)
    used.add(lang['id'])
    with open(STATE_FILE, 'w') as f:
        json.dump({'used': sorted(used)}, f)

    # data['features'] is already in the order a card should prefer.
    features = [{'id': fid, 'name': data['features'][fid], 'value': lang['features'][fid]}
                for fid in data['features'] if fid in lang['features']][:MAX_FEATURES]

    write_feed(name, {
        "type": "language",
        "v": 2,
        "timestamp": f"{today()}T10:30:00",
        "name": lang['name'],
        "family": lang['family'],
        "genus": lang['genus'],
        "macroarea": lang['macroarea'],
        "countries": lang['countries'],
        "iso": lang['iso'],
        "glottocode": lang['glottocode'],
        "lat": lang['lat'],
        "lon": lang['lon'],
        "features": features,
        "url": f"https://wals.info/languoid/lect/wals_code_{lang['id']}",
        "source": "WALS Online (CC BY 4.0)",
    })


if __name__ == '__main__':
    generate()
