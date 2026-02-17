#!/usr/bin/env python3
"""Noosphere music recommendation generator.

Uses Anna's Spotify listening history + the Spotify API to find
genuinely surprising music she hasn't heard. Posts as a daily card.
"""
import json, os, sys, random
from datetime import datetime
from dotenv import load_dotenv

# Load env
for p in ['~/clawd/.env', '~/.env']:
    load_dotenv(os.path.expanduser(p), override=True)

import spotipy
from spotipy.oauth2 import SpotifyOAuth

sys.path.insert(0, os.path.dirname(__file__))
from utils import write_feed, feed_exists, today, ask_claude

FEED_NAME = f"{today()}-music-rec"

def get_spotify():
    """Get authenticated Spotify client."""
    return spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=os.environ['SPOTIFY_CLIENT_ID'],
        client_secret=os.environ['SPOTIFY_CLIENT_SECRET'],
        redirect_uri=os.environ['SPOTIFY_REDIRECT_URI'],
        scope='user-read-recently-played user-top-read',
        cache_path=os.path.expanduser('~/.spotify-token-cache'),
        open_browser=False,
    ))

def load_listening_profile():
    """Load the distilled taste profile from historical data."""
    profile_path = os.path.join(os.path.dirname(__file__), 'data', 'taste-profile.json')
    if os.path.exists(profile_path):
        return json.load(open(profile_path))
    return None

def get_recent_context(sp):
    """Get recent listening for context."""
    try:
        recent = sp.current_user_recently_played(limit=50)
        artists = set()
        tracks = []
        for item in recent['items']:
            t = item['track']
            artists.add(t['artists'][0]['name'])
            tracks.append(f"{t['name']} — {t['artists'][0]['name']}")
        return {
            'recent_artists': list(artists)[:20],
            'recent_tracks': tracks[:15],
        }
    except:
        return {'recent_artists': [], 'recent_tracks': []}

def get_top_context(sp):
    """Get top artists/tracks for different time ranges."""
    context = {}
    for term in ['short_term', 'medium_term', 'long_term']:
        try:
            top = sp.current_user_top_artists(limit=20, time_range=term)
            context[term] = [a['name'] for a in top['items']]
        except:
            context[term] = []
    return context

def find_spotify_url(sp, track_name, artist_name):
    """Search Spotify for a track and return its URL."""
    try:
        q = f'track:{track_name} artist:{artist_name}'
        results = sp.search(q=q, type='track', limit=1)
        if results['tracks']['items']:
            return results['tracks']['items'][0]['external_urls'].get('spotify', '')
    except:
        pass
    try:
        # Broader search
        results = sp.search(q=f'{track_name} {artist_name}', type='track', limit=1)
        if results['tracks']['items']:
            return results['tracks']['items'][0]['external_urls'].get('spotify', '')
    except:
        pass
    return ''

def load_past_recs():
    """Load previously recommended artists to avoid repeats."""
    state_path = os.path.join(os.path.dirname(__file__), '.music-rec-state.json')
    if os.path.exists(state_path):
        return json.load(open(state_path))
    return {'recommended': []}

def save_past_recs(state):
    state_path = os.path.join(os.path.dirname(__file__), '.music-rec-state.json')
    with open(state_path, 'w') as f:
        json.dump(state, f, indent=2)

def generate_recommendation():
    """Generate today's music recommendation using Claude as discovery engine."""
    if feed_exists(FEED_NAME):
        print(f"Already exists: {FEED_NAME}")
        return

    sp = get_spotify()
    profile = load_listening_profile()
    recent = get_recent_context(sp)
    top = get_top_context(sp)
    past = load_past_recs()

    # Build taste context
    taste_context = f"""Recent listening: {', '.join(recent.get('recent_artists', [])[:10])}
Current top artists (last 4 weeks): {', '.join(top.get('short_term', [])[:10])}
Longer-term favorites: {', '.join(top.get('medium_term', [])[:10])}"""

    if profile:
        taste_context += f"""
Taste profile: {profile.get('summary', '')}
Key traits: {', '.join(profile.get('traits', []))}
Languages: {', '.join(profile.get('languages', []))}"""

    # Sample some known artists to exclude
    known = profile.get('known_artists', []) if profile else []
    known_sample = ', '.join(random.sample(known, min(50, len(known))))
    past_recs = ', '.join(past.get('recommended', [])[-30:])

    # Random theme to keep recs diverse
    themes = [
        'Find something from a language she listens to (Spanish, French, or Russian) that she hasn\'t heard.',
        'Find an obscure indie/emo band she\'d obsess over.',
        'Find something from a country or musical tradition she\'d never expect to love.',
        'Find a deep folk or Americana cut that would hit her like Pinegrove or The Lumineers.',
        'Find something brand new (released in the last year) that fits her taste.',
        'Find a classic she somehow missed — something from the 60s-90s with that earnest quality she loves.',
        'Find something with stunning vocals — a voice that would stop her in her tracks.',
        'Find something from Eastern Europe, the Balkans, or the post-Soviet world.',
        'Find a song that would be perfect at 3AM — intimate, honest, slightly melancholy.',
        'Find something chaotic and fun — the musical equivalent of "Bailamos" meets "Girls" by The Dare.',
    ]
    theme = random.choice(themes)

    prompt = f"""You are a music-obsessed friend with encyclopedic, global taste. Recommend ONE specific song.

LISTENER PROFILE:
{taste_context}

KEY TRAITS:
- Values sincerity over coolness. Earnest > ironic.
- Multilingual listener: English, Spanish, French, Russian. Non-English recs welcome.
- Range: emo (Front Bottoms, MCR) + folk (Lumineers, Pinegrove) + classic rock (Eagles, Fleetwood Mac) + French indie (Therapie TAXI) + Russian rap (Oxxxymiron) + pop deep cuts + literally anything sincere.
- Played "Such Small Hands" by La Dispute 31 times AND "Bailamos" by Enrique Iglesias 37 times. That range.
- Loves discovering artists nobody she knows has heard of.

TODAY'S DIRECTION: {theme}

DO NOT recommend any of these known artists: {known_sample}
DO NOT recommend these (already recommended recently): {past_recs}

Recommend something she has GENUINELY never heard. Go obscure. Go global. Go deep. The song must actually exist on Spotify.

Format EXACTLY like this (no extra text):
ARTIST: [artist name]
TRACK: [track name]
ALBUM: [album name]
YEAR: [release year]
WHY: [2-3 sentences. Be specific about why SHE would love this. Connect to her taste. Write like a friend texting "okay STOP and listen to this."]"""

    response = ask_claude(prompt, max_tokens=300, temperature=1.0)

    # Parse response
    rec = {}
    for line in response.strip().split('\n'):
        for key in ['ARTIST', 'TRACK', 'ALBUM', 'YEAR', 'WHY']:
            if line.startswith(f'{key}:'):
                rec[key.lower()] = line.split(':', 1)[1].strip()

    if not rec.get('track') or not rec.get('artist'):
        print(f"Failed to parse recommendation: {response[:200]}")
        return

    # Find Spotify URL
    spotify_url = find_spotify_url(sp, rec['track'], rec['artist'])

    card = {
        'type': 'music_rec',
        'timestamp': datetime.now().isoformat(timespec='seconds'),
        'title': rec.get('track', 'Unknown'),
        'artist': rec.get('artist', 'Unknown'),
        'album': rec.get('album', ''),
        'year': rec.get('year', ''),
        'body': rec.get('why', ''),
        'spotify_url': spotify_url,
    }

    write_feed(FEED_NAME, card)

    # Track what we've recommended
    past['recommended'].append(rec['artist'])
    save_past_recs(past)

    print(f"Recommended: {card['title']} by {card['artist']}")
    if spotify_url:
        print(f"  Spotify: {spotify_url}")
    else:
        print("  (not found on Spotify)")

if __name__ == '__main__':
    generate_recommendation()
