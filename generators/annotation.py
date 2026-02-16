#!/usr/bin/env python3
"""The Annotation Layer — real paragraph from classic literature with dense annotations.

Uses 566 passages extracted from 20 Project Gutenberg texts (Austen, Melville, Tolstoy, 
Joyce, Woolf, Kafka, Dostoevsky, Dickens, Brontë, etc.)
"""
import json, os, random
from utils import ask_claude, today, write_feed, feed_exists

DATA_FILE = os.path.join(os.path.dirname(__file__), 'data', 'literary-passages.json')
STATE_FILE = os.path.join(os.path.dirname(__file__), '.annotation-state.json')

def get_next_passage():
    with open(DATA_FILE) as f:
        passages = json.load(f)
    
    state = {}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            state = json.load(f)
    
    used = set(state.get('used', []))
    available = [i for i in range(len(passages)) if i not in used]
    if not available:
        used = set()
        available = list(range(len(passages)))
    
    idx = random.choice(available)
    used.add(idx)
    with open(STATE_FILE, 'w') as f:
        json.dump({'used': list(used)}, f)
    
    return passages[idx]

def generate():
    name = f"{today()}-annotation"
    if feed_exists(name):
        print(f"Already exists: {name}")
        return

    passage = get_next_passage()

    prompt = f"""Annotate this literary passage with 3 dense, playful, insightful annotations:

"{passage['text']}"
— {passage['source']}

For each annotation, pick a specific phrase or word and explain something non-obvious about it:
- Linguistic observations (syntax, pragmatics, register, free indirect discourse, deixis)
- Historical context that changes how you read it
- Translation choices (if translated)
- Connections to other works, ideas, or fields (philosophy, computational linguistics, etc.)

Be like a brilliant professor scribbling in the margins — opinionated, precise, occasionally funny.

Respond in this exact JSON format:
{{
  "annotated_text": "The passage with <sup class=\\"ann-marker\\">1</sup>, <sup class=\\"ann-marker\\">2</sup>, <sup class=\\"ann-marker\\">3</sup> inserted after the annotated phrases",
  "annotations": [
    "First annotation (2-3 sentences, use <em> and <strong> for emphasis)",
    "Second annotation (2-3 sentences)",  
    "Third annotation (2-3 sentences)"
  ]
}}

Keep each annotation under 50 words. Insert the <sup> markers INTO the passage text at natural breakpoints near each annotated phrase."""

    system = "You are a literary critic and linguist who writes marginalia. Your annotations are dense with insight, never obvious, sometimes funny, always precise. You notice things other readers miss."

    result = ask_claude(prompt, system=system, max_tokens=800, temperature=0.8)
    
    # Parse JSON
    try:
        if '```' in result:
            result = result.split('```')[1]
            if result.startswith('json'):
                result = result[4:]
        data = json.loads(result.strip())
    except (json.JSONDecodeError, IndexError):
        import re
        match = re.search(r'\{.*\}', result, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError:
                print(f"Failed to parse JSON: {result[:200]}")
                return
        else:
            print(f"No JSON found: {result[:200]}")
            return

    write_feed(name, {
        "type": "annotation",
        "timestamp": f"{today()}T15:00:00",
        "text": data.get("annotated_text", passage['text']),
        "annotations": data.get("annotations", []),
        "source": passage['source'],
    })

if __name__ == '__main__':
    generate()
