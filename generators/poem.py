#!/usr/bin/env python3
"""The Night Poem. A short public-domain poem, three evenings a week.

The text comes from PoetryDB (https://poetrydb.org) and is printed whole.
Poems longer than a screen are skipped rather than excerpted.
"""
import json, os, re
import requests
from utils import today, write_feed, feed_exists, UA

STATE_FILE = os.path.join(os.path.dirname(__file__), '.poem-state.json')
MAX_LINES = 24
MIN_LINES = 4
MAX_LINE_CHARS = 80


def fits(poem):
    lines = poem.get('lines') or []
    body = [l for l in lines if l.strip()]
    if not (MIN_LINES <= len(body) <= MAX_LINES):
        return False
    if any(len(l) > MAX_LINE_CHARS for l in lines):
        return False
    return bool(poem.get('title') and poem.get('author'))


def generate():
    name = f"{today()}-poem"
    if feed_exists(name):
        print(f"Already exists: {name}")
        return

    seen = []
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                seen = json.load(f).get('seen', [])
        except (json.JSONDecodeError, ValueError):
            seen = []

    poem = None
    for _ in range(6):
        try:
            resp = requests.get('https://poetrydb.org/random/8', headers=UA, timeout=20)
            resp.raise_for_status()
            batch = resp.json()
        except Exception as e:
            print(f"  PoetryDB request failed: {e}")
            continue
        for p in batch:
            key = f"{p.get('author')}::{p.get('title')}"
            if fits(p) and key not in seen:
                poem = p
                break
        if poem:
            break
    if not poem:
        print("No short poem turned up")
        return

    lines = [l.rstrip() for l in poem['lines']]
    # Sonnet sequences arrive with their roman numeral as a first line.
    while lines and (not lines[0].strip() or re.fullmatch(r'[IVXLC]+\.?', lines[0].strip())):
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    write_feed(name, {
        "type": "poem",
        "v": 2,
        "timestamp": f"{today()}T21:00:00",
        "title": poem['title'].strip(),
        "author": poem['author'].strip(),
        "lines": lines,
        "source": "PoetryDB",
    })

    seen.append(f"{poem['author']}::{poem['title']}")
    with open(STATE_FILE, 'w') as f:
        json.dump({'seen': seen[-400:]}, f, ensure_ascii=False)


if __name__ == '__main__':
    generate()
