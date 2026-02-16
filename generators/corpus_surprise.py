#!/usr/bin/env python3
"""The Corpus Surprise — real sentence from a multilingual linguistic corpus with Claude commentary.

Uses Leipzig Corpora Collection data (130K+ sentences across 13 languages):
English (news, Wikipedia), Russian, French, Spanish, German, Japanese, 
Arabic, Turkish, Portuguese, Italian, Polish, Chinese.
"""
import os, random, json
from utils import ask_claude, today, write_feed, feed_exists

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

CORPORA = [
    {"file": "corpus-eng-news.txt", "corpus": "Leipzig English News", "register": "news", "year": "2020", "language": "English", "lang_code": "en"},
    {"file": "corpus-eng-wiki.txt", "corpus": "Leipzig English Wikipedia", "register": "encyclopedia", "year": "2016", "language": "English", "lang_code": "en"},
    {"file": "corpus-rus-news.txt", "corpus": "Leipzig Russian News", "register": "news", "year": "2020", "language": "Russian", "lang_code": "ru"},
    {"file": "corpus-fra-news.txt", "corpus": "Leipzig French News", "register": "news", "year": "2020", "language": "French", "lang_code": "fr"},
    {"file": "corpus-spa-news.txt", "corpus": "Leipzig Spanish News", "register": "news", "year": "2020", "language": "Spanish", "lang_code": "es"},
    {"file": "corpus-deu-news.txt", "corpus": "Leipzig German News", "register": "news", "year": "2020", "language": "German", "lang_code": "de"},
    {"file": "corpus-jpn-news.txt", "corpus": "Leipzig Japanese News", "register": "news", "year": "2020", "language": "Japanese", "lang_code": "ja"},
    {"file": "corpus-ara-news.txt", "corpus": "Leipzig Arabic News", "register": "news", "year": "2020", "language": "Arabic", "lang_code": "ar"},
    {"file": "corpus-tur-news.txt", "corpus": "Leipzig Turkish News", "register": "news", "year": "2020", "language": "Turkish", "lang_code": "tr"},
    {"file": "corpus-por-news.txt", "corpus": "Leipzig Portuguese News", "register": "news", "year": "2020", "language": "Portuguese", "lang_code": "pt"},
    {"file": "corpus-ita-news.txt", "corpus": "Leipzig Italian News", "register": "news", "year": "2020", "language": "Italian", "lang_code": "it"},
    {"file": "corpus-pol-news.txt", "corpus": "Leipzig Polish News", "register": "news", "year": "2020", "language": "Polish", "lang_code": "pl"},
    {"file": "corpus-zho-news.txt", "corpus": "Leipzig Chinese News", "register": "news", "year": "2020", "language": "Chinese", "lang_code": "zh"},
]

def pick_interesting_sentence(filepath, language, attempts=50):
    """Pick a random sentence that's interesting enough to be worth showing."""
    with open(filepath, 'r', errors='replace') as f:
        lines = f.readlines()
    
    for _ in range(attempts):
        line = random.choice(lines).strip()
        parts = line.split('\t', 1)
        if len(parts) < 2:
            continue
        sentence = parts[1].strip()
        
        words = sentence.split()
        # Different length criteria for different scripts
        if language in ('Japanese', 'Chinese'):
            if len(sentence) < 20 or len(sentence) > 200:
                continue
        else:
            if len(words) < 8 or len(words) > 45:
                continue
        
        # Skip if mostly numbers/URLs
        alpha_ratio = sum(1 for c in sentence if c.isalpha()) / max(len(sentence), 1)
        if alpha_ratio < 0.5:
            continue
        # Skip emoji-heavy
        if any(ord(c) > 0x1F600 and ord(c) < 0x1F700 for c in sentence[:5]):
            continue
        
        return sentence
    
    return None

def generate():
    name = f"{today()}-corpus-surprise"
    if feed_exists(name):
        print(f"Already exists: {name}")
        return

    # Filter to corpora that exist on disk
    available = [c for c in CORPORA if os.path.exists(os.path.join(DATA_DIR, c['file']))]
    if not available:
        print("No corpus files found!")
        return
    
    corpus_info = random.choice(available)
    filepath = os.path.join(DATA_DIR, corpus_info['file'])
    
    sentence = pick_interesting_sentence(filepath, corpus_info['language'])
    if not sentence:
        print("Couldn't find an interesting sentence")
        return

    lang = corpus_info['language']
    
    prompt = f"""This sentence was randomly sampled from the {corpus_info['corpus']} ({corpus_info['year']}):

"{sentence}"

This is {lang} text. Write 1-2 sentences of linguistic commentary in English about what makes 
this sentence interesting from a morphological, syntactic, pragmatic, or sociolinguistic perspective. 
What would a corpus linguist or computational linguist notice? What's revealing about the 
construction, register, word order, or presuppositions?

If the sentence is not in English, briefly note what it says before your linguistic analysis.

Keep it under 80 words. Be precise and specific — focus on actual linguistic phenomena."""

    system = "You are a multilingual corpus linguist who finds patterns in naturally-occurring language across the world's languages. Your commentary is precise, insightful, and notices things most readers would miss. You can read and analyze text in any major language."

    context = ask_claude(prompt, system=system, max_tokens=250, temperature=0.8)

    genre = "news article" if corpus_info['register'] == 'news' else corpus_info['register']
    
    write_feed(name, {
        "type": "corpus_surprise",
        "timestamp": f"{today()}T14:15:00",
        "sentence": sentence,
        "corpus": corpus_info['corpus'],
        "register": corpus_info['register'],
        "year": corpus_info['year'],
        "genre": genre,
        "context": context,
    })

if __name__ == '__main__':
    generate()
