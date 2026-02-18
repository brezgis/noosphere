#!/usr/bin/env python3
"""Noosphere music recommendation generator.

Spotify deprecated recommendations, related-artists, and audio-features for
dev-mode apps (Nov 2024). So we use a different approach:

1. Pull Anna's top artists + liked songs from Spotify (still available)
2. Use Last.fm's free API to find similar artists she doesn't already know
3. Search Spotify for that artist's tracks → guaranteed real, linkable song
4. Claude writes the blurb — never picks the song

No hallucinated artists. Every link is verified.
"""
import json, os, sys, random, time
from datetime import datetime
from dotenv import load_dotenv

# Load env
for p in ['~/clawd/.env', '~/.env']:
    load_dotenv(os.path.expanduser(p), override=True)

import spotipy
from spotipy.oauth2 import SpotifyOAuth
import requests

sys.path.insert(0, os.path.dirname(__file__))
from utils import write_feed, feed_exists, today, ask_claude

FEED_NAME = f"{today()}-music-rec"

LASTFM_API_KEY = os.environ.get('LASTFM_API_KEY', '')


def get_spotify():
    """Get authenticated Spotify client."""
    return spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=os.environ['SPOTIFY_CLIENT_ID'],
        client_secret=os.environ['SPOTIFY_CLIENT_SECRET'],
        redirect_uri=os.environ['SPOTIFY_REDIRECT_URI'],
        scope='user-read-recently-played user-top-read user-library-read',
        cache_path=os.path.expanduser('~/.spotify-token-cache'),
        open_browser=False,
    ))


def load_listening_profile():
    """Load the distilled taste profile from historical data."""
    profile_path = os.path.join(os.path.dirname(__file__), 'data', 'taste-profile.json')
    if os.path.exists(profile_path):
        return json.load(open(profile_path))
    return None


def get_liked_track_keys(sp):
    """Fetch all liked songs and return a set of 'artist::track' keys (lowercased)."""
    keys = set()
    offset = 0
    while True:
        try:
            results = sp.current_user_saved_tracks(limit=50, offset=offset)
            if not results['items']:
                break
            for item in results['items']:
                t = item['track']
                artist = t['artists'][0]['name'].lower().strip()
                track = t['name'].lower().strip()
                keys.add(f"{artist}::{track}")
            offset += 50
            if offset >= results['total']:
                break
        except:
            break
    return keys


def get_known_artist_names(sp, profile):
    """Build a set of artist names Anna already knows."""
    known = set()

    # From taste profile
    if profile and 'known_artists' in profile:
        for a in profile['known_artists']:
            known.add(a.lower().strip())

    # From top artists (all time ranges)
    for term in ['short_term', 'medium_term', 'long_term']:
        try:
            top = sp.current_user_top_artists(limit=50, time_range=term)
            for a in top['items']:
                known.add(a['name'].lower().strip())
        except:
            pass

    return known


def get_seed_artist_names(sp):
    """Get artist names from top artists for Last.fm similarity lookups."""
    artists = []
    for term in ['short_term', 'medium_term', 'long_term']:
        try:
            top = sp.current_user_top_artists(limit=30, time_range=term)
            for a in top['items']:
                artists.append(a['name'])
        except:
            pass
    return list(set(artists))


def lastfm_similar_artists(artist_name, limit=30):
    """Use Last.fm API to find artists similar to the given artist."""
    if not LASTFM_API_KEY:
        return []
    try:
        resp = requests.get('http://ws.audioscrobbler.com/2.0/', params={
            'method': 'artist.getsimilar',
            'artist': artist_name,
            'api_key': LASTFM_API_KEY,
            'format': 'json',
            'limit': limit,
        }, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        similar = data.get('similarartists', {}).get('artist', [])
        return [{'name': a['name'], 'match': float(a.get('match', 0))} for a in similar]
    except Exception as e:
        print(f"    Last.fm similar failed for {artist_name}: {e}")
        return []


def lastfm_top_tracks(artist_name, limit=10):
    """Get an artist's top tracks from Last.fm (for context, not for linking)."""
    if not LASTFM_API_KEY:
        return []
    try:
        resp = requests.get('http://ws.audioscrobbler.com/2.0/', params={
            'method': 'artist.gettoptracks',
            'artist': artist_name,
            'api_key': LASTFM_API_KEY,
            'format': 'json',
            'limit': limit,
        }, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        tracks = data.get('toptracks', {}).get('track', [])
        return [t['name'] for t in tracks]
    except:
        return []


def spotify_search_artist_track(sp, artist_name, track_name=None):
    """Search Spotify for a specific track by an artist. Returns track dict or None."""
    try:
        if track_name:
            q = f'artist:{artist_name} track:{track_name}'
        else:
            q = f'artist:{artist_name}'
        results = sp.search(q=q, type='track', limit=10)
        items = results['tracks']['items']
        if not items:
            return None

        # If we searched for a specific track, verify the artist matches
        for item in items:
            sp_artist = item['artists'][0]['name'].lower().strip()
            if artist_name.lower().strip() in sp_artist or sp_artist in artist_name.lower().strip():
                return {
                    'id': item['id'],
                    'name': item['name'],
                    'artist': item['artists'][0]['name'],
                    'album': item.get('album', {}).get('name', ''),
                    'year': item.get('album', {}).get('release_date', '')[:4],
                    'popularity': item.get('popularity', 0),
                    'spotify_url': item.get('external_urls', {}).get('spotify', ''),
                }
        return None
    except Exception as e:
        print(f"    Spotify search failed for {artist_name}: {e}")
        return None


def load_past_recs():
    """Load previously recommended tracks to avoid repeats."""
    state_path = os.path.join(os.path.dirname(__file__), '.music-rec-state.json')
    if os.path.exists(state_path):
        return json.load(open(state_path))
    return {'recommended_tracks': [], 'recommended_artists': []}


def save_past_recs(state):
    state_path = os.path.join(os.path.dirname(__file__), '.music-rec-state.json')
    state['recommended_tracks'] = state.get('recommended_tracks', [])[-100:]
    state['recommended_artists'] = state.get('recommended_artists', [])[-100:]
    with open(state_path, 'w') as f:
        json.dump(state, f, indent=2)


def generate_recommendation():
    """Generate today's music recommendation from real data."""
    if feed_exists(FEED_NAME):
        print(f"Already exists: {FEED_NAME}")
        return

    sp = get_spotify()
    profile = load_listening_profile()
    past = load_past_recs()

    print("  Loading known artists...")
    known_artists = get_known_artist_names(sp, profile)
    print(f"  {len(known_artists)} known artists")

    print("  Loading liked songs...")
    liked_keys = get_liked_track_keys(sp)
    print(f"  {len(liked_keys)} liked songs")

    print("  Getting seed artists...")
    seeds = get_seed_artist_names(sp)
    print(f"  {len(seeds)} seed artists")

    past_artist_names = set(a.lower() for a in past.get('recommended_artists', []))
    # Also include old format
    past_artist_names.update(a.lower() for a in past.get('recommended', []))
    past_track_ids = set(past.get('recommended_tracks', []))

    if not seeds:
        print("No seed artists available")
        return

    # Shuffle seeds and try to find a good recommendation
    random.shuffle(seeds)
    chosen = None

    for seed in seeds[:10]:  # Try up to 10 seed artists
        print(f"  Trying seed: {seed}")
        similar = lastfm_similar_artists(seed)
        if not similar:
            continue

        # Filter: unknown to Anna, not recently recommended
        candidates = [
            a for a in similar
            if a['name'].lower().strip() not in known_artists
            and a['name'].lower().strip() not in past_artist_names
        ]

        if not candidates:
            continue

        # Bias toward medium similarity (not too close, not too far)
        # Sort by match score, pick from the middle third
        candidates.sort(key=lambda a: a['match'], reverse=True)
        mid_start = len(candidates) // 3
        mid_end = 2 * len(candidates) // 3
        pool = candidates[mid_start:mid_end] if mid_end > mid_start else candidates
        if not pool:
            pool = candidates

        random.shuffle(pool)

        for candidate in pool[:5]:  # Try up to 5 candidates per seed
            artist_name = candidate['name']

            # Get their top tracks from Last.fm
            top_tracks = lastfm_top_tracks(artist_name)

            # Try to find them on Spotify
            track = None
            if top_tracks:
                # Try a few top tracks
                for track_name in random.sample(top_tracks, min(3, len(top_tracks))):
                    track = spotify_search_artist_track(sp, artist_name, track_name)
                    if track:
                        break

            if not track:
                # Generic artist search
                track = spotify_search_artist_track(sp, artist_name)

            if not track:
                continue

            # Check if already liked or recommended
            key = f"{track['artist'].lower().strip()}::{track['name'].lower().strip()}"
            if key in liked_keys:
                continue
            if track['id'] in past_track_ids:
                continue

            track['_seed'] = seed
            track['_match'] = candidate['match']
            chosen = track
            break

        if chosen:
            break

    if not chosen:
        print("No suitable recommendation found")
        return

    print(f"  Found: {chosen['name']} by {chosen['artist']} (via {chosen['_seed']}, match: {chosen['_match']:.2f})")

    # Claude writes the blurb about a REAL, VERIFIED song
    taste_summary = ''
    if profile:
        taste_summary = f"Taste: {profile.get('summary', '')}. Traits: {', '.join(profile.get('traits', []))}"

    prompt = f"""Write a 2-3 sentence music recommendation blurb. You're a music-obsessed friend texting someone.

SONG: "{chosen['name']}" by {chosen['artist']}
ALBUM: {chosen['album']} ({chosen['year']})
DISCOVERED VIA: Similar to {chosen['_seed']}

LISTENER: {taste_summary}

Write like you're texting a friend "okay STOP and listen to this." Be specific about the sound/vibe. No preamble, just the blurb. If you aren't sure about the specific song, write about why the artist is worth discovering and connect to the listener's taste."""

    blurb = ask_claude(prompt, max_tokens=200, temperature=0.9)

    card = {
        'type': 'music_rec',
        'timestamp': datetime.now().isoformat(timespec='seconds'),
        'title': chosen['name'],
        'artist': chosen['artist'],
        'album': chosen['album'],
        'year': chosen['year'],
        'body': blurb.strip(),
        'spotify_url': chosen['spotify_url'],
    }

    write_feed(FEED_NAME, card)

    # Track recommendations
    past.setdefault('recommended_tracks', []).append(chosen['id'])
    past.setdefault('recommended_artists', []).append(chosen['artist'])
    if 'recommended' in past:
        past['recommended_artists'].extend(past.pop('recommended'))
    save_past_recs(past)

    print(f"  ✓ Recommended: {card['title']} by {card['artist']}")
    print(f"    Spotify: {card['spotify_url']}")


if __name__ == '__main__':
    generate_recommendation()
