#!/usr/bin/env python3
"""Русский Час — daily Russian literary sentence with morphological breakdown."""
import json, os
from utils import ask_claude, today, write_feed, feed_exists

DATA_FILE = os.path.join(os.path.dirname(__file__), 'data', 'russian-sentences.json')
STATE_FILE = os.path.join(os.path.dirname(__file__), '.russian-state.json')

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
            state = {}  # empty/corrupt state — restart from the beginning
    idx = state.get('index', 0)
    if idx >= len(sentences):
        idx = 0
    sentence = sentences[idx]
    with open(STATE_FILE, 'w') as f:
        json.dump({'index': idx + 1}, f)
    return sentence

def generate():
    name = f"{today()}-russian"
    if feed_exists(name):
        print(f"Already exists: {name}")
        return

    sentence = get_next_sentence()

    prompt = f"""Analyze this Russian literary sentence:

"{sentence['text']}"
— {sentence['source']}

Format your response as two sections separated by a blank line:
- First line: the transliteration (no markup, plain text)
- Then a blank line
- Then the breakdown (2-4 sentences). Use HTML tags for emphasis: <strong> for Russian words, <em> for English translations/emphasis. Do NOT use markdown (*asterisks* or **double asterisks**) — only HTML tags.

Keep it under 100 words total. Be linguistically precise but conversational."""

    system = "You are a Russian philologist who makes the beauty and mechanics of Russian grammar visible to learners. You notice the poetic devices, the morphological surprises, the syntactic inversions."

    result = ask_claude(prompt, system=system, max_tokens=400, temperature=0.7)

    parts = result.strip().split('\n\n', 1)
    transliteration = parts[0].strip() if len(parts) > 0 else ''
    breakdown = parts[1].strip() if len(parts) > 1 else result.strip()

    write_feed(name, {
        "type": "russian",
        "timestamp": f"{today()}T08:30:00",
        "text": sentence['text'],
        "transliteration": transliteration,
        "breakdown": breakdown,
        "source": sentence['source'],
    })

if __name__ == '__main__':
    generate()
