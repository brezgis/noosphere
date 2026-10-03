#!/usr/bin/env python3
"""Wittgenstein's Ladder — daily Tractatus proposition with commentary.
Uses the full 513 propositions parsed from Project Gutenberg."""
import json, os
from utils import ask_claude, today, write_feed, feed_exists

DATA_FILE = os.path.join(os.path.dirname(__file__), 'data', 'tractatus.json')
STATE_FILE = os.path.join(os.path.dirname(__file__), '.wittgenstein-state.json')

def load_propositions():
    with open(DATA_FILE) as f:
        return json.load(f)

def get_next_index():
    """Walk sequentially through all 513 propositions."""
    state = {}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                state = json.load(f)
        except (json.JSONDecodeError, ValueError):
            state = {}  # empty/corrupt state — restart from the beginning
    idx = state.get('index', 0)
    props = load_propositions()
    next_idx = (idx + 1) % len(props)
    with open(STATE_FILE, 'w') as f:
        json.dump({'index': next_idx}, f)
    return idx

def generate():
    name = f"{today()}-wittgenstein"
    if feed_exists(name):
        print(f"Already exists: {name}")
        return

    props = load_propositions()
    idx = get_next_index()
    prop = props[idx]
    number = prop['number']
    text = prop['text']

    prompt = f"""You're writing a brief commentary on Tractatus Logico-Philosophicus proposition {number}:

"{text}"

Write 2-4 sentences on what this proposition actually says and why it is strange or
interesting. Most days, stay with the idea itself — logic, pictures, representation,
mathematics, the limits of language, ordinary life. Only occasionally (and only if it is
genuinely illuminating) reach for something contemporary like programming or language
models; never force it, and never use tech metaphors as a punchline.

Be direct, concrete, and a little wry.
No intro, no "This proposition...", just the commentary. Under 80 words."""

    system = "You are a philosophy commentator with deep knowledge of Wittgenstein, language models, and computational linguistics. Your commentary is sharp, plainspoken, and surprising; you explain hard ideas without jargon and without gimmicks."

    commentary = ask_claude(prompt, system=system, max_tokens=300, temperature=0.85)

    write_feed(name, {
        "type": "wittgenstein",
        "timestamp": f"{today()}T08:00:00",
        "number": number,
        "proposition": text,
        "commentary": commentary,
    })

if __name__ == '__main__':
    generate()
