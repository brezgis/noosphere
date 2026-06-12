#!/usr/bin/env python3
"""One-time Spotify OAuth helper for the music generators.

Loads ~/projects/noosphere/.env, then:
  python3 spotify_auth.py            -> use cached token if valid, else print the authorize URL
  python3 spotify_auth.py "<url>"    -> exchange the redirected URL's code and cache a token

The cached token (with a refresh token) lives at ~/.spotify-token-cache and lets
the daily cron run headlessly afterward.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# Load .env (last value wins; never printed)
for line in open(os.path.join(HERE, '.env')):
    s = line.strip()
    if s and not s.startswith('#') and '=' in s:
        k, v = s.split('=', 1)
        os.environ[k] = v

import spotipy
from spotipy.oauth2 import SpotifyOAuth

SCOPE = ('user-read-recently-played user-top-read user-library-read '
         'playlist-modify-public playlist-modify-private user-read-currently-playing')

oauth = SpotifyOAuth(
    client_id=os.environ['SPOTIFY_CLIENT_ID'],
    client_secret=os.environ['SPOTIFY_CLIENT_SECRET'],
    redirect_uri=os.environ['SPOTIFY_REDIRECT_URI'],
    scope=SCOPE,
    cache_path=os.path.expanduser('~/.spotify-token-cache'),
    open_browser=False,
)


def whoami(token):
    sp = spotipy.Spotify(auth=token['access_token'])
    me = sp.current_user()
    print(f"OK — authorized as {me.get('display_name')} ({me.get('id')})")
    print("token scopes:", token.get('scope', '(none)'))


if len(sys.argv) > 1:
    # Step 2: exchange the pasted redirect URL.
    code = oauth.parse_response_code(sys.argv[1])
    oauth.get_access_token(code, as_dict=False, check_cache=False)
    tok = oauth.cache_handler.get_cached_token()
    print("Token cached at ~/.spotify-token-cache")
    whoami(tok)
else:
    # Step 1: try the existing cache, else print the authorize URL.
    cached = oauth.cache_handler.get_cached_token()
    tok = None
    if cached:
        try:
            tok = oauth.validate_token(cached)  # refreshes if expired
        except Exception as e:
            print("CACHED TOKEN UNUSABLE:", type(e).__name__, str(e)[:160])
    if tok:
        print("ALREADY AUTHORIZED (cached token is valid).")
        whoami(tok)
    else:
        print("NEED_AUTH — open this URL, approve, then paste the redirected URL back:")
        print(oauth.get_authorize_url())
