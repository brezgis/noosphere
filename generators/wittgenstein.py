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
        with open(STATE_FILE) as f:
            state = json.load(f)
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

Write 2-4 sentences connecting this to something contemporary — LLMs, computational linguistics,
memes, internet culture, programming, or the hypothesis that distributional patterns encode 
culturally-specific attentional structures. Be genuinely insightful, not forced.
If the connection is a stretch, pick a different angle — philosophy of mind, mathematics,
the nature of representation, whatever the proposition actually invites.

Use monospace/code-like language where it fits naturally. Be direct and a little wry.
No intro, no "This proposition...", just the commentary. Under 80 words."""

    system = "You are a philosophy commentator with deep knowledge of Wittgenstein, language models, and computational linguistics. Your commentary is sharp, surprising, and connects old ideas to new technology without being gimmicky."

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
