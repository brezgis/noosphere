#!/usr/bin/env python3
"""Wittgenstein's Ladder. One Tractatus proposition a day, in order.

The card carries the proposition and the rungs above it (3.321 arrives with
3.32, 3.3 and 3), because the numbering is the book's own commentary. Nothing
else is added.
"""
import json, os
from utils import today, write_feed, feed_exists

DATA_FILE = os.path.join(os.path.dirname(__file__), 'data', 'tractatus.json')
STATE_FILE = os.path.join(os.path.dirname(__file__), '.wittgenstein-state.json')


def load_propositions():
    with open(DATA_FILE) as f:
        return json.load(f)


def get_next_index(total):
    """Walk sequentially through all the propositions."""
    state = {}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                state = json.load(f)
        except (json.JSONDecodeError, ValueError):
            state = {}  # empty/corrupt state: restart from the beginning
    idx = state.get('index', 0) % total
    with open(STATE_FILE, 'w') as f:
        json.dump({'index': (idx + 1) % total}, f)
    return idx


def ladder(number, by_number):
    """The ancestors of a proposition, nearest first: 3.321 -> 3.32, 3.3, 3."""
    rungs = []
    n = number
    while len(n) > 1:
        n = n[:-1].rstrip('.')
        if n in by_number and n != number:
            rungs.append({'number': n, 'text': by_number[n]})
    return rungs


def generate():
    name = f"{today()}-wittgenstein"
    if feed_exists(name):
        print(f"Already exists: {name}")
        return

    props = load_propositions()
    by_number = {p['number']: p['text'] for p in props}
    idx = get_next_index(len(props))
    prop = props[idx]

    write_feed(name, {
        "type": "wittgenstein",
        "v": 2,
        "timestamp": f"{today()}T08:00:00",
        "number": prop['number'],
        "proposition": prop['text'],
        "ladder": ladder(prop['number'], by_number),
        "position": idx + 1,
        "total": len(props),
    })


if __name__ == '__main__':
    generate()
