# Code Review — Noosphere (2026-02-16)

Reviewer: Bea | Focus: New music recommendation + monthly playlist generators, feed ordering, entropy garden scroll-back

---

## 🔴 Critical

### 1. `schedule.py` — Syntax error breaks all generators
The `monthly_playlist` entry is outside the `SCHEDULE` dict (dict is closed with `}` on line 44, then the entry appears on line 46). This causes an `IndentationError` on import, which crashes `run_all.sh` since every generator imports from `schedule.py` via `utils.py` or directly.

```python
    # Line 44: dict closes
    'music_rec': 'daily',
}
    # Line 46: orphaned entry
    'monthly_playlist': 'monthly_1st',
}
```

**Impact**: No generators can run until this is fixed.

### 2. CSS `--flamingo` variable undefined
`card-music-rec` styles reference `var(--flamingo)` but this color is never defined in `:root`. Results in invisible/unstyled text for the music rec card's artist name, link, and border.

**Impact**: Music rec cards render with missing colors (browser falls back to inherited or transparent).

---

## 🟡 Important

### 3. `music_rec.py` — Spotify OAuth scope missing `user-library-read`
`get_liked_track_keys()` calls `sp.current_user_saved_tracks()` which requires `user-library-read` scope. The OAuth setup only requests `user-read-recently-played user-top-read`. This will 403 at runtime.

Note: `monthly_playlist.py` has the same issue — it also fetches liked songs but its scope list doesn't include `user-library-read` either.

### 4. Hardcoded Discord channel ID in `utils.py`
`NOOSPHERE_DISCORD_CHANNEL` defaults to `'1473064914074734793'` when the env var isn't set. This is a personal channel ID that shouldn't be in source.

### 5. Duplicate HTML meta tags in `index.html`
`theme-color`, `apple-mobile-web-app-capable`, `apple-mobile-web-app-status-bar-style`, and `manifest.json` link are each declared twice.

### 6. `monthly_playlist.py` — Direct `requests` import inside function
Uses `import requests as _req` inside `create_spotify_playlist()` to work around spotipy's 403 on dev-mode apps. This is fine functionally but `requests` isn't guaranteed to be available (it's not in the function's module-level imports). Should be a top-level import.

---

## 🔵 Minor

### 7. `music_rec.py` taste profile prompt contains real personal data
The prompt includes detailed listening stats ("played Such Small Hands 31 times", "Bailamos 37 times"). Not a secret per se, but worth noting — this goes to the LLM API on every call.

### 8. Feed ordering: today newest-first is good UX, but `groupByTimeOfDay` thresholds are hardcoded
Morning < 11, midday < 14, afternoon < 18, evening >= 18. Not configurable but probably fine.

### 9. Entropy garden `IntersectionObserver` creates two observers per canvas
`initEntropyGarden` creates a re-entry observer, and each algorithm (dla, flow_field, game_of_life) creates its own visibility observer. Could consolidate but works fine.

### 10. `README.md` still says "15 streams" — now 17 with music_rec and monthly_playlist
Stream count and table need updating.

### 11. `server.js` — PORT is hardcoded to 7701
Could read from `process.env.PORT` for flexibility.

---

## ✅ What's Good

- Music rec generator is well-designed: taste profile, liked-songs filter, retry loop, past-rec tracking
- Monthly playlist gracefully handles Spotify dev-mode 403s (falls back to individual track links)
- Feed ordering (today newest-first, older days grouped by time-of-day) is clean
- Entropy garden scroll-back replay via IntersectionObserver is elegant
- All generators remain idempotent
- State tracking patterns are consistent
