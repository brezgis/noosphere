#!/usr/bin/env python3
"""The Commonplace Book. One paragraph from a public-domain novel each week.

(Internal card type stays "annotation". The stream used to ask the model for
margin notes, and the notes were confident and wrong, so now the passage
stands by itself with its source.)

Uses 566 passages extracted from 20 Project Gutenberg texts.
"""
import json, os, random
from utils import today, write_feed, feed_exists

DATA_FILE = os.path.join(os.path.dirname(__file__), 'data', 'literary-passages.json')
STATE_FILE = os.path.join(os.path.dirname(__file__), '.annotation-state.json')


def get_next_passage():
    with open(DATA_FILE) as f:
        passages = json.load(f)

    state = {}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                state = json.load(f)
        except (json.JSONDecodeError, ValueError):
            state = {}

    used = set(state.get('used', []))
    available = [i for i in range(len(passages)) if i not in used]
    if not available:
        used = set()
        available = list(range(len(passages)))

    idx = random.choice(available)
    used.add(idx)
    with open(STATE_FILE, 'w') as f:
        json.dump({'used': sorted(used)}, f)
    return passages[idx]


def generate():
    name = f"{today()}-annotation"
    if feed_exists(name):
        print(f"Already exists: {name}")
        return

    passage = get_next_passage()
    write_feed(name, {
        "type": "annotation",
        "v": 2,
        "timestamp": f"{today()}T15:00:00",
        "text": passage['text'],
        "source": passage['source'],
        "author": passage.get('author', ''),
        "title": passage.get('title', ''),
        "year": passage.get('year', ''),
    })


if __name__ == '__main__':
    generate()
