#!/usr/bin/env python3
"""Русский Час. One sentence of Russian literature a day.

The sentence and its source come from the curated list. The transliteration is
a fixed table. The local model supplies a plain English translation and nothing
else, and the card is written without one if the model is down.
"""
import json, os
from utils import today, write_feed, feed_exists, translate

DATA_FILE = os.path.join(os.path.dirname(__file__), 'data', 'russian-sentences.json')
STATE_FILE = os.path.join(os.path.dirname(__file__), '.russian-state.json')

TRANSLIT = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
    'ъ': '', 'ы': 'y', 'ь': "'", 'э': 'e', 'ю': 'yu', 'я': 'ya',
}


def transliterate(text):
    out = []
    for ch in text:
        low = ch.lower()
        if low in TRANSLIT:
            t = TRANSLIT[low]
            out.append(t.capitalize() if ch != low else t)
        elif ch not in '«»':
            out.append(ch)
    return ''.join(out).strip()


def load_sentences():
    with open(DATA_FILE) as f:
        return json.load(f)


def get_next_sentence():
    sentences = load_sentences()
    state = {}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                state = json.load(f)
        except (json.JSONDecodeError, ValueError):
            state = {}  # empty/corrupt state: restart from the beginning
    idx = state.get('index', 0)
    if idx >= len(sentences):
        idx = 0
    with open(STATE_FILE, 'w') as f:
        json.dump({'index': idx + 1}, f)
    return sentences[idx]


def generate():
    name = f"{today()}-russian"
    if feed_exists(name):
        print(f"Already exists: {name}")
        return

    sentence = get_next_sentence()
    text = sentence['text']

    card = {
        "type": "russian",
        "v": 2,
        "timestamp": f"{today()}T08:30:00",
        "text": text,
        "transliteration": transliterate(text),
        "source": sentence['source'],
    }
    translation = translate(text.strip('«»'), 'Russian')
    if translation:
        card["translation"] = translation
    write_feed(name, card)


if __name__ == '__main__':
    generate()
