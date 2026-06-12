#!/usr/bin/env python3
"""Echoes — the recycled-content stream.

Resurfaces a past *evergreen* card so the feed always has something fresh at the
top, even on days when little else is scheduled or generation stalls. The card
keeps its original type (so the frontend re-renders it natively) and gains an
"echo" ribbon.

Deliberately dependency-light: no LLM, no network. This is the safety net that
keeps the noosphere from ever looking dead, so it must work even when the local
model and every API are unreachable.
"""
import json
import os
import random
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import FEED_DIR, today, write_feed, feed_exists  # noqa: E402

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.echoes-state.json')

# Timeless card types that are safe to resurface (no stale "today" references).
EVERGREEN = {
    'untranslatable', 'wittgenstein', 'russian', 'corpus_surprise',
    'apophenia', 'dead_medium', 'typeface', 'the_diff', 'diff',
    'penny_red', 'annotation',
}

ECHO_NOTES = [
    "resurfaced from the archive",
    "worth seeing again",
    "an echo from {date}",
    "the noosphere remembers",
    "pulled back up from {date}",
    "still thinking about this one",
    "a rerun, lovingly",
]


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"used": []}


def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)


def date_label(ts):
    """'2026-02-18T15:00:00' -> 'February 18'."""
    try:
        return date.fromisoformat(ts[:10]).strftime('%B %-d')
    except Exception:
        return ts[:10] if ts else ''


def generate():
    name = f"{today()}-echo"
    if feed_exists(name):
        return

    today_file = f"{name}.json"
    candidates = []
    for fn in os.listdir(FEED_DIR):
        if not fn.endswith('.json') or fn.startswith('.') or fn == today_file:
            continue
        try:
            with open(os.path.join(FEED_DIR, fn)) as f:
                card = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(card, dict):
            continue
        if card.get('echo'):
            continue  # never echo an echo
        if card.get('type') not in EVERGREEN:
            continue
        candidates.append((fn, card))

    if not candidates:
        print("Echoes: no evergreen cards to resurface yet.")
        return

    state = load_state()
    used = set(state.get('used', []))
    fresh = [c for c in candidates if c[0] not in used]
    if not fresh:
        # Exhausted the archive — reset and cycle through again.
        used = set()
        fresh = candidates

    fn, card = random.choice(fresh)

    orig_ts = card.get('timestamp', '')
    echo = dict(card)
    echo['echo'] = True
    echo['echo_from'] = date_label(orig_ts)
    echo['echo_source'] = fn
    note = random.choice(ECHO_NOTES)
    echo['echo_note'] = note.format(date=echo['echo_from']) if '{date}' in note else note
    # Surface near the top of today's feed (morning slot, so it's visible most
    # of the day), but don't re-ping Discord.
    echo['timestamp'] = f"{today()}T08:00:00"

    write_feed(name, echo, post_discord=False)

    used.add(fn)
    save_state({"used": sorted(used)})
    print(f"Echoes: resurfaced {card.get('type')} from {echo['echo_from']} ({fn})")


if __name__ == '__main__':
    generate()
