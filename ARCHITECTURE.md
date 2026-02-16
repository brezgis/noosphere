# Noosphere — Architecture & Internal Docs

## Overview

Noosphere is a personal content feed: 15 independent Python generators write JSON cards to `feed/`, an Express server serves them via API, and a vanilla JS frontend renders them as a scrollable timeline.

## Directory Structure

```
noosphere/
├── server.js              # Express server, port 7701
├── package.json           # Node dependencies (express only)
├── .env.example           # Template for LLM + Unsplash config
├── .gitignore             # Excludes feed/, corpus data, state files
├── public/
│   ├── index.html         # Full frontend (~960 lines, single file)
│   ├── sw.js              # Service worker (cache-first static, network-first API)
│   ├── manifest.json      # PWA manifest
│   ├── favicon.png/ico    # Concentric circles icon
│   ├── icon-192.png       # PWA icon
│   ├── icon-512.png       # PWA icon
│   └── apple-touch-icon.png
├── generators/
│   ├── utils.py           # Shared: ask_claude(), write_feed(), feed_exists(), today()
│   ├── schedule.py        # Day-of-week cadence for each generator
│   ├── run_all.sh         # Runner script (checks schedule, runs generators, low-stock monitor)
│   ├── weather.py         # ☁ Lyrical Weather
│   ├── wittgenstein.py    # ◇ Wittgenstein's Ladder
│   ├── russian.py         # 🇷🇺 Русский Час
│   ├── untranslatable.py  # ✦ The Untranslatable
│   ├── corpus_surprise.py # ⟐ Corpus Surprise
│   ├── annotation.py      # ✎ Annotation Layer
│   ├── entropy_garden.py  # ⌬ Entropy Garden (no LLM needed)
│   ├── apophenia.py       # ⟁ Apophenia Machine
│   ├── dead_medium.py     # ✝ The Dead Medium
│   ├── midnight_postcard.py # 🌙 Midnight Postcard
│   ├── git_log.py         # $ git log --oneline
│   ├── penny_red.py       # 📍 The Penny Red
│   ├── the_diff.py        # ⟺ The Diff
│   ├── typeface.py        # ◈ Typeface of the Week
│   ├── recipe.py          # 🍳 Recipe
│   └── data/
│       ├── tractatus.json          # 513 propositions
│       ├── russian-sentences.json  # 122 literary sentences
│       ├── literary-passages.json  # 566 paragraphs from 20 novels
│       └── corpus-*.txt            # Leipzig corpora (not in git, ~130K lines)
└── feed/                  # Generated JSON cards (not in git)
```

## Discord Integration

`utils.py` includes a `_post_to_discord()` function called automatically by `write_feed()`. When a new card is written, it's formatted into a Discord message (with type-specific labels, markdown formatting, and HTML stripping) and posted to a configured channel via the Discord Bot API. Failures are caught and logged without blocking feed generation.

Configuration: `NOOSPHERE_DISCORD_CHANNEL` env var for the channel ID, Discord bot token from OpenClaw config or environment.

## Generator Pattern

Every generator follows the same structure:

```python
def generate():
    name = f"{today()}-stream-name"
    if feed_exists(name):       # Idempotent: skip if already generated
        return
    
    data = get_source_data()    # From curated list, API, or random selection
    commentary = ask_claude(prompt, system=system)  # LLM commentary
    
    write_feed(name, {
        "type": "stream_type",
        "timestamp": f"{today()}T08:00:00",
        # ... stream-specific fields
    })
```

## State Tracking

Generators with curated content use two patterns:

### Sequential (index-based)
Used by: `wittgenstein.py`, `russian.py`
```json
// .wittgenstein-state.json
{"index": 42}
```
Cycles back to 0 when exhausted.

### Used-set (random without repeat)
Used by: `untranslatable.py`, `annotation.py`, `dead_medium.py`, `penny_red.py`, `the_diff.py`, `typeface.py`
```json
// .untranslatable-state.json
{"used": [3, 7, 12, 28]}
```
Resets to empty when all items used.

State files are `.gitignored` (they're runtime state, not source).

## Schedule

Defined in `schedule.py`. Days are 0=Monday through 6=Sunday:

- **Daily**: weather, wittgenstein, russian, corpus_surprise, entropy_garden, git_log, midnight_postcard
- **MWF**: untranslatable
- **Tue/Thu**: apophenia
- **Tue/Sat**: penny_red
- **Monday**: the_diff
- **Wednesday**: typeface, recipe
- **Friday**: dead_medium
- **Sunday**: annotation

## Feed JSON Format

Each card is a single JSON file: `feed/YYYY-MM-DD-stream-name.json`

The `type` field determines which card renderer the frontend uses. Required fields vary by type — see `CARD_RENDERERS` in `index.html`.

## API

### GET /api/feed
Returns all feed items, newest first.

Query params:
- `limit` (default 200) — max items to return
- `before` — ISO date, only items before this timestamp
- `type` — filter by card type

### GET /api/types
Returns list of all card types present in the feed.

## Frontend

Single HTML file with embedded CSS and JS. No build step, no framework.

Key components:
- `CARD_RENDERERS` object — one template function per card type
- `md2html()` — converts stray markdown to HTML (safety net for LLM output)
- `formatTime()` — formats ISO timestamps for display
- `initEntropyGarden()` — renders live canvas animations (DLA, flow fields, cellular automata, Game of Life)
- `filterFeed()` / `searchFeed()` — sidebar filtering
- Service worker registration for PWA install

## Low-Stock Monitor

`run_all.sh` includes an inline Python script that checks remaining items in all curated pools after generation. If any pool is below threshold, it writes `.low-stock-alert.txt` to `feed/`. A separate cron job can check this file and alert.

## Deployment

Currently deployed as:
- systemd user service on the server
- nginx reverse proxy with TLS (Let's Encrypt)
- Basic auth for access control
- Reverse SSH tunnel from server to public-facing VPS

The PWA can be installed to home screen on iOS/Android/desktop.
