#!/usr/bin/env python3
"""Noosphere monthly playlist generator.

On the 1st of each month, compiles a themed playlist from:
1. All daily music recs from the previous month
2. Fresh picks from Claude to fill out the vibe
Creates a real Spotify playlist and posts a card.
"""
import json, os, sys, random, glob
from datetime import datetime, date, timedelta
from calendar import month_name
from dotenv import load_dotenv

# Load env
for p in ['~/clawd/.env', '~/.env']:
    load_dotenv(os.path.expanduser(p), override=True)

import spotipy
from spotipy.oauth2 import SpotifyOAuth

sys.path.insert(0, os.path.dirname(__file__))
from utils import write_feed, feed_exists, today, ask_claude

FEED_DIR = os.path.join(os.path.dirname(__file__), '..', 'feed')


def get_spotify():
    """Get authenticated Spotify client with playlist-modify scope."""
    return spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=os.environ['SPOTIFY_CLIENT_ID'],
        client_secret=os.environ['SPOTIFY_CLIENT_SECRET'],
        redirect_uri=os.environ['SPOTIFY_REDIRECT_URI'],
        scope='user-read-recently-played user-top-read user-library-read playlist-modify-public playlist-modify-private user-read-currently-playing',
        cache_path=os.path.expanduser('~/.spotify-token-cache'),
        open_browser=False,
    ))


def get_last_month():
    """Return (year, month_num, month_name) for the previous month."""
    first_of_this_month = date.today().replace(day=1)
    last_month_date = first_of_this_month - timedelta(days=1)
    return last_month_date.year, last_month_date.month, month_name[last_month_date.month]


def collect_monthly_recs(year, month):
    """Gather all music_rec feed items from a given month."""
    recs = []
    prefix = f"{year}-{month:02d}"
    pattern = os.path.join(FEED_DIR, f"{prefix}-*-music-rec.json")
    for path in sorted(glob.glob(pattern)):
        try:
            with open(path) as f:
                data = json.load(f)
            if data.get('type') == 'music_rec' and data.get('artist') and data.get('title'):
                recs.append(data)
        except (json.JSONDecodeError, KeyError):
            continue
    return recs


def load_taste_profile():
    """Load the distilled taste profile."""
    profile_path = os.path.join(os.path.dirname(__file__), 'data', 'taste-profile.json')
    if os.path.exists(profile_path):
        return json.load(open(profile_path))
    return None


def generate_playlist_theme(month_name_str, recs):
    """Ask Claude to name and describe a playlist based on the month's recs."""
    rec_list = '\n'.join(
        f"- {r['title']} by {r['artist']}" + (f" ({r.get('year', '')})" if r.get('year') else '')
        for r in recs
    )

    prompt = f"""You're naming a monthly playlist for {month_name_str}. These songs were recommended throughout the month:

{rec_list if recs else "(No recommendations yet — this is the first month.)"}

Create a playlist name and description. The name should be evocative, specific to the vibe of this collection — NOT generic like "{month_name_str} Mix" or "Monthly Vibes." Think of it like naming a mixtape for a close friend. The description should be 2-3 sentences, poetic but not overwrought.

Also suggest 8-12 ADDITIONAL tracks that would complete this playlist — songs that fit the overall mood and fill any gaps. These should be real songs on Spotify. Mix well-known with obscure. Match the multilingual, genre-fluid taste profile (emo, folk, French indie, Russian, classic rock, Spanish — anything sincere).

Format EXACTLY:
NAME: [playlist name]
DESCRIPTION: [2-3 sentences]
ADDITIONS:
- [Artist] — [Track]
- [Artist] — [Track]
..."""

    return ask_claude(prompt, max_tokens=800, temperature=1.0)


def parse_theme_response(response):
    """Parse Claude's playlist theme response."""
    result = {'name': '', 'description': '', 'additions': []}
    lines = response.strip().split('\n')
    in_additions = False

    for line in lines:
        if line.startswith('NAME:'):
            result['name'] = line.split(':', 1)[1].strip().strip('"\'')
        elif line.startswith('DESCRIPTION:'):
            result['description'] = line.split(':', 1)[1].strip()
        elif line.startswith('ADDITIONS:'):
            in_additions = True
        elif in_additions and line.strip().startswith('-'):
            entry = line.strip().lstrip('- ').strip()
            if '—' in entry:
                artist, track = entry.split('—', 1)
            elif ' - ' in entry:
                artist, track = entry.split(' - ', 1)
            else:
                continue
            result['additions'].append({
                'artist': artist.strip(),
                'track': track.strip(),
            })

    return result


def find_track_uri(sp, track_name, artist_name):
    """Search Spotify for a track, return (uri, url) or (None, None)."""
    for query in [
        f'track:{track_name} artist:{artist_name}',
        f'{track_name} {artist_name}',
    ]:
        try:
            results = sp.search(q=query, type='track', limit=1)
            if results['tracks']['items']:
                t = results['tracks']['items'][0]
                return t['uri'], t['external_urls'].get('spotify', '')
        except Exception:
            pass
    return None, None


def create_spotify_playlist(sp, name, description, track_uris):
    """Create a Spotify playlist and add tracks.
    Uses /me/playlists endpoint directly (works with dev-mode apps)
    instead of spotipy's user_playlist_create which uses /users/{id}/playlists (403 in dev mode).
    """
    token = sp.auth_manager.get_access_token(as_dict=False)
    import requests as _req
    r = _req.post(
        'https://api.spotify.com/v1/me/playlists',
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
        json={'name': name, 'public': False, 'description': description},
    )
    r.raise_for_status()
    playlist = r.json()
    if track_uris:
        # Add tracks directly via API (spotipy's method gets 403 in dev mode)
        for i in range(0, len(track_uris), 100):
            _req.post(
                f"https://api.spotify.com/v1/playlists/{playlist['id']}/tracks",
                headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
                json={'uris': track_uris[i:i+100]},
            ).raise_for_status()
    return playlist['external_urls'].get('spotify', ''), playlist['id']


def load_state():
    """Load past playlist state."""
    state_path = os.path.join(os.path.dirname(__file__), '.monthly-playlist-state.json')
    if os.path.exists(state_path):
        return json.load(open(state_path))
    return {'playlists': []}


def save_state(state):
    state_path = os.path.join(os.path.dirname(__file__), '.monthly-playlist-state.json')
    with open(state_path, 'w') as f:
        json.dump(state, f, indent=2)


def generate_playlist():
    """Generate this month's playlist from last month's recs."""
    year, month, month_name_str = get_last_month()
    feed_name = f"{date.today().isoformat()}-monthly-playlist"

    if feed_exists(feed_name):
        print(f"Already exists: {feed_name}")
        return

    # Check if we already made a playlist for this month
    state = load_state()
    month_key = f"{year}-{month:02d}"
    if any(p.get('month') == month_key for p in state.get('playlists', [])):
        print(f"Already generated playlist for {month_key}")
        return

    print(f"Generating playlist for {month_name_str} {year}...")

    # Collect the month's daily recs
    recs = collect_monthly_recs(year, month)
    print(f"  Found {len(recs)} daily recommendations from {month_name_str}")

    # Get theme + additional tracks from Claude
    theme_response = generate_playlist_theme(month_name_str, recs)
    theme = parse_theme_response(theme_response)

    if not theme['name']:
        theme['name'] = f"Noosphere — {month_name_str} {year}"
    if not theme['description']:
        theme['description'] = f"A month of discoveries. {month_name_str} {year}."

    print(f"  Playlist: {theme['name']}")
    print(f"  {theme['description']}")
    print(f"  {len(theme['additions'])} additional tracks suggested")

    # Resolve all tracks on Spotify, filtering out liked songs
    sp = get_spotify()

    print("  Loading liked songs...")
    liked_keys = set()
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
                liked_keys.add(f"{artist}::{track}")
            offset += 50
            if offset >= results['total']:
                break
        except:
            break
    print(f"  {len(liked_keys)} liked songs loaded")

    track_uris = []
    track_list = []  # For the card
    skipped = 0

    # First: the month's daily recs (already filtered at generation time)
    for rec in recs:
        uri, url = find_track_uri(sp, rec['title'], rec['artist'])
        if uri:
            track_uris.append(uri)
            track_list.append({
                'artist': rec['artist'],
                'track': rec['title'],
                'spotify_url': url,
                'source': 'daily_rec',
            })
        else:
            print(f"  ⚠ Not found: {rec['title']} by {rec['artist']}")

    # Then: Claude's additions (skip if already liked)
    for add in theme['additions']:
        key = f"{add['artist'].lower().strip()}::{add['track'].lower().strip()}"
        if key in liked_keys:
            print(f"  ⏭ Already liked: {add['track']} by {add['artist']}")
            skipped += 1
            continue
        uri, url = find_track_uri(sp, add['track'], add['artist'])
        if uri:
            track_uris.append(uri)
            track_list.append({
                'artist': add['artist'],
                'track': add['track'],
                'spotify_url': url,
                'source': 'curated',
            })
        else:
            print(f"  ⚠ Not found: {add['track']} by {add['artist']}")

    if skipped:
        print(f"  Skipped {skipped} tracks already in liked songs")

    # Deduplicate by URI
    seen = set()
    unique_uris = []
    unique_tracks = []
    for uri, track in zip(track_uris, track_list):
        if uri not in seen:
            seen.add(uri)
            unique_uris.append(uri)
            unique_tracks.append(track)

    print(f"  {len(unique_uris)} tracks resolved on Spotify")

    # Try to create a real Spotify playlist
    # Note: Spotify dev-mode apps may block write operations (403).
    # If so, card still works with individual track links.
    spotify_url = ''
    playlist_id = ''
    if unique_uris:
        try:
            spotify_url, playlist_id = create_spotify_playlist(
                sp,
                theme['name'],
                theme['description'],
                unique_uris,
            )
            print(f"  Created playlist: {spotify_url}")
        except Exception as e:
            print(f"  ⚠ Spotify playlist creation failed: {e}")
            print("  (Card will use individual track links instead)")

    # Write feed card
    card = {
        'type': 'monthly_playlist',
        'timestamp': datetime.now().isoformat(timespec='seconds'),
        'title': theme['name'],
        'month': month_name_str,
        'year': year,
        'description': theme['description'],
        'track_count': len(unique_tracks),
        'tracks': unique_tracks[:20],  # Cap at 20 for the card display
        'daily_rec_count': sum(1 for t in unique_tracks if t['source'] == 'daily_rec'),
        'curated_count': sum(1 for t in unique_tracks if t['source'] == 'curated'),
        'spotify_url': spotify_url,
        'playlist_id': playlist_id,
    }

    write_feed(feed_name, card)

    # Update state
    state['playlists'].append({
        'month': month_key,
        'name': theme['name'],
        'spotify_url': spotify_url,
        'track_count': len(unique_tracks),
        'created': date.today().isoformat(),
    })
    save_state(state)

    print(f"Done! {theme['name']} — {len(unique_tracks)} tracks")


if __name__ == '__main__':
    generate_playlist()
