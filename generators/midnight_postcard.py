#!/usr/bin/env python3
"""Midnight Postcard — a single image with no caption, delivered late at night.

Uses Unsplash API with proper authentication.
"""
import requests, random, os
from dotenv import load_dotenv
from utils import today, write_feed, feed_exists

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env'), override=True)

UNSPLASH_KEY = os.environ.get('UNSPLASH_ACCESS_KEY', '')

# Curated search terms — evocative, atmospheric, surprising
SEARCH_TERMS = [
    "fog city night", "abandoned architecture", "bioluminescence",
    "northern lights", "empty train station", "underwater cathedral",
    "desert night sky", "neon rain", "brutalist architecture",
    "japanese garden autumn", "volcanic lightning", "frozen lake",
    "moroccan doorway", "lighthouse storm", "abandoned library",
    "crystal cave", "misty mountain forest", "old bookshop",
    "cherry blossom night", "iceland moss", "stained glass shadow",
    "typewriter closeup", "crumbling fresco", "tide pool",
    "rooftop sunset city", "snow covered bench", "old map detail",
    "film noir shadow", "origami crane", "rust pattern",
    "cobblestone rain", "greenhouse plants", "moonrise ocean",
    "empty theater", "spiral staircase above", "paper lanterns",
    "frost on window", "radio telescope", "coral reef macro",
    "cathedral ceiling", "foggy bridge", "wildflower meadow dusk",
    "chess piece shadow", "astronomy observatory", "vintage train",
    "ink in water", "sand dune ripples", "candlelit manuscript",
    "stone labyrinth", "clock mechanism", "autumn leaves water",
]

def get_unsplash_image(query):
    """Get a random image from Unsplash using the proper API."""
    resp = requests.get(
        'https://api.unsplash.com/photos/random',
        params={
            'query': query,
            'orientation': 'landscape',
        },
        headers={
            'Authorization': f'Client-ID {UNSPLASH_KEY}',
            'Accept-Version': 'v1',
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    
    return {
        'url': data['urls']['regular'],
        'photographer': data.get('user', {}).get('name', ''),
        'photographer_url': data.get('user', {}).get('links', {}).get('html', ''),
        'description': data.get('alt_description') or data.get('description') or '',
        'unsplash_url': data.get('links', {}).get('html', ''),
        'color': data.get('color', ''),
    }

def generate():
    name = f"{today()}-midnight-postcard"
    if feed_exists(name):
        print(f"Already exists: {name}")
        return

    if not UNSPLASH_KEY:
        print("No UNSPLASH_ACCESS_KEY set")
        return

    query = random.choice(SEARCH_TERMS)
    
    try:
        img = get_unsplash_image(query)
    except Exception as e:
        print(f"Failed to get image: {e}")
        # Try one more time with a different query
        try:
            query = random.choice(SEARCH_TERMS)
            img = get_unsplash_image(query)
        except Exception as e2:
            print(f"Failed again: {e2}")
            return

    write_feed(name, {
        "type": "postcard",
        "timestamp": f"{today()}T23:30:00",
        "image": img['url'],
        # Unsplash requires attribution
        "photographer": img['photographer'],
        "photographer_url": img['photographer_url'],
        "unsplash_url": img['unsplash_url'],
    })

if __name__ == '__main__':
    generate()
