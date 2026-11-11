#!/usr/bin/env python3
"""Echoes — the recycled-content stream.

Reblogs a past *evergreen* card so the feed always has something fresh at the
top, even on days when little else is scheduled or generation stalls. The card
keeps its original type (so the frontend renders it natively) and is shown as
a reblog of the stream it came from.

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
    'penny_red', 'annotation', 'poem', 'language', 'painting',
}

# Cards written before the v2 streams carry model-written commentary. When one
# of those is reblogged, the commentary stays behind and the sourced part
# travels. Types whose whole body was model text are only reblogged from v2 on.
LEGACY_STRIP = {
    'wittgenstein': ['commentary'],
    'russian': ['breakdown', 'transliteration'],
    'corpus_surprise': ['context'],
    'the_diff': ['commentary'],
    'diff': ['commentary'],
    'apophenia': ['connection'],
    'annotation': ['annotations'],
}
# A card has to be at least this old before it can come round again.
MIN_AGE_DAYS = 21

LEGACY_SKIP = {'untranslatable', 'dead_medium', 'typeface', 'penny_red'}

# The tag a reblog gets, tumblr style.
ECHO_NOTES = [
    "from the archive",
    "worth seeing again",
    "reblogging my own feed",
    "still thinking about this one",
    "a rerun, lovingly",
    "queue",
]


def reblogable(card):
    """The card as it should travel, or None if it should stay in the archive."""
    kind = card.get('type')
    if kind not in EVERGREEN:
        return None
    if (card.get('v') or 1) >= 2:
        return dict(card)
    if kind in LEGACY_SKIP:
        return None
    out = dict(card)
    for field in LEGACY_STRIP.get(kind, []):
        out.pop(field, None)
    if kind == 'annotation':
        # v1 passages have footnote markers spliced into the text.
        import re
        out['text'] = re.sub(r'<sup[^>]*>.*?</sup>', '', out.get('text', ''))
    return out


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
    # Types that already have a fresh card today — an echo of the same stream
    # right next to it reads as a duplicate, so prefer other streams.
    today_types = set()
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
        if fn.startswith(today()):
            today_types.add(card.get('type'))
            continue
        if card.get('echo'):
            continue  # never echo an echo
        try:
            age = (date.fromisoformat(today()) - date.fromisoformat(fn[:10])).days
        except ValueError:
            age = MIN_AGE_DAYS
        if age < MIN_AGE_DAYS:
            continue  # too recent to count as a rerun
        card = reblogable(card)
        if card is None:
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

    fn, card = random.choice([c for c in fresh if c[1].get('type') not in today_types] or fresh)

    orig_ts = card.get('timestamp', '')
    echo = dict(card)
    echo['echo'] = True
    echo['echo_from'] = date_label(orig_ts)
    echo['echo_source'] = fn
    echo['echo_note'] = random.choice(ECHO_NOTES)
    echo['echo_date'] = orig_ts[:10]
    # Surface near the top of today's feed (morning slot, so it's visible most
    # of the day), but don't re-ping Discord.
    echo['timestamp'] = f"{today()}T08:00:00"

    write_feed(name, echo, post_discord=False)

    used.add(fn)
    save_state({"used": sorted(used)})
    print(f"Echoes: resurfaced {card.get('type')} from {echo['echo_from']} ({fn})")


if __name__ == '__main__':
    generate()
