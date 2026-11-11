#!/usr/bin/env python3
"""Monthly Mixtape. On the 1st, last month's daily picks become one tracklist.

The tracklist is read straight from the month's music cards in feed/, which
already carry verified Spotify links, so nothing is searched for again and no
model names the playlist or adds songs to it. (The old version asked the model
for a title and extra tracks, then re-searched every song, and since February
it had been posting playlists with zero tracks.)

If Spotify allows it, the tracks are also saved as a private playlist on the
account. Set NOOSPHERE_SKIP_SPOTIFY_WRITE=1 to skip that step. The card is
written either way.
"""
import json, os, sys, glob, re
from datetime import date, timedelta
from calendar import month_name

sys.path.insert(0, os.path.dirname(__file__))
from utils import write_feed, feed_exists, today, today_date

FEED_DIR = os.path.join(os.path.dirname(__file__), '..', 'feed')
STATE_FILE = os.path.join(os.path.dirname(__file__), '.monthly-playlist-state.json')


def get_last_month():
    """Return (year, month_num, month_name) for the previous month."""
    last = today_date().replace(day=1) - timedelta(days=1)
    return last.year, last.month, month_name[last.month]


def collect_monthly_recs(year, month):
    """All music_rec cards from one month, oldest first, without repeats."""
    tracks, seen = [], set()
    pattern = os.path.join(FEED_DIR, f"{year}-{month:02d}-*-music-rec.json")
    for path in sorted(glob.glob(pattern)):
        try:
            with open(path) as f:
                d = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        if d.get('type') != 'music_rec' or not d.get('artist') or not d.get('title'):
            continue
        url = d.get('spotify_url', '')
        m = re.search(r'/track/([A-Za-z0-9]+)', url)
        track_id = d.get('track_id') or (m.group(1) if m else '')
        key = track_id or f"{d['artist']}::{d['title']}".lower()
        if key in seen:
            continue
        seen.add(key)
        tracks.append({
            'track': d['title'],
            'artist': d['artist'],
            'album': d.get('album', ''),
            'spotify_url': url,
            'track_id': track_id,
            'day': os.path.basename(path)[:10],
        })
    return tracks


def create_spotify_playlist(name, description, track_ids):
    """Save the tracks as a private playlist. Returns (url, id) or raises."""
    import requests
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
    from dotenv import load_dotenv
    for p in ['~/.env', os.path.join(os.path.dirname(__file__), '..', '.env')]:
        load_dotenv(os.path.expanduser(p), override=True)
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=os.environ['SPOTIFY_CLIENT_ID'],
        client_secret=os.environ['SPOTIFY_CLIENT_SECRET'],
        redirect_uri=os.environ['SPOTIFY_REDIRECT_URI'],
        scope='user-read-recently-played user-top-read user-library-read playlist-modify-public playlist-modify-private user-read-currently-playing',
        cache_path=os.path.expanduser('~/.spotify-token-cache'),
        open_browser=False,
    ))
    token = sp.auth_manager.get_access_token(as_dict=False)
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    r = requests.post('https://api.spotify.com/v1/me/playlists', headers=headers, timeout=20,
                      json={'name': name, 'public': False, 'description': description})
    r.raise_for_status()
    playlist = r.json()
    uris = [f"spotify:track:{t}" for t in track_ids]
    for i in range(0, len(uris), 100):
        requests.post(f"https://api.spotify.com/v1/playlists/{playlist['id']}/tracks",
                      headers=headers, timeout=20, json={'uris': uris[i:i + 100]}).raise_for_status()
    return playlist['external_urls'].get('spotify', ''), playlist['id']


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {'playlists': []}


def generate_playlist():
    year, month, month_str = get_last_month()
    feed_name = f"{today()}-monthly-playlist"
    if feed_exists(feed_name):
        print(f"Already exists: {feed_name}")
        return

    state = load_state()
    month_key = f"{year}-{month:02d}"
    # A month whose earlier attempt produced no tracks is allowed to run again.
    if any(p.get('month') == month_key and p.get('track_count') for p in state.get('playlists', [])):
        print(f"Already generated playlist for {month_key}")
        return

    tracks = collect_monthly_recs(year, month)
    print(f"  Found {len(tracks)} daily picks from {month_str}")
    if not tracks:
        print("  Nothing to compile, so no card is written.")
        return

    title = f"{month_str} {year} mixtape"
    spotify_url, playlist_id = '', ''
    ids = [t['track_id'] for t in tracks if t['track_id']]
    if ids and not os.environ.get('NOOSPHERE_SKIP_SPOTIFY_WRITE'):
        try:
            spotify_url, playlist_id = create_spotify_playlist(
                title, f"Every daily pick from {month_str} {year}, in the order it was posted.", ids)
            print(f"  Created playlist: {spotify_url}")
        except Exception as e:
            print(f"  Spotify playlist was not created ({e}). The card links each track instead.")

    write_feed(feed_name, {
        'type': 'monthly_playlist',
        'v': 2,
        'timestamp': f"{today()}T06:00:30",
        'title': title,
        'month': month_str,
        'year': year,
        'track_count': len(tracks),
        'tracks': tracks,
        'spotify_url': spotify_url,
        'playlist_id': playlist_id,
    })

    state['playlists'] = [p for p in state.get('playlists', []) if p.get('month') != month_key]
    state['playlists'].append({
        'month': month_key, 'name': title, 'spotify_url': spotify_url,
        'track_count': len(tracks), 'created': today(),
    })
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)
    print(f"Done. {title}: {len(tracks)} tracks")


if __name__ == '__main__':
    generate_playlist()
