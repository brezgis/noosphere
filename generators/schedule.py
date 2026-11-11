"""Cadence schedule for Noosphere generators.

Each generator checks should_run() before generating.
Days: 0=Monday ... 6=Sunday
"""
import os
from datetime import datetime, date

# Schedule: which days each generator runs
SCHEDULE = {
    # Daily
    'weather': 'daily',
    'wittgenstein': 'daily',
    'russian': 'daily',
    'corpus_surprise': 'daily',
    'entropy_garden': 'daily',
    'git_log': 'daily',
    'painting': 'daily',
    'midnight_postcard': 'daily',
    'language': 'daily',
    'link': 'daily',

    # 3x/week (Tue, Thu, Sun), an evening poem
    'poem': [1, 3, 6],

    # 3x/week (Mon, Wed, Fri)
    'untranslatable': [0, 2, 4],

    # 2x/week (Tue, Thu)
    'apophenia': [1, 3],

    # 2x/week (Tue, Sat) — formerly daily
    'penny_red': [1, 5],

    # Weekly Monday
    'the_diff': [0],

    # Weekly Wednesday
    'typeface': [2],
    'recipe': [2],

    # Weekly Friday
    'dead_medium': [4],

    # Weekly Sunday
    'annotation': [6],

    # Daily music recommendation
    'music_rec': 'daily',

    # Daily recycled card — resurfaces an evergreen past card so the feed
    # always has something fresh on top (the "never looks dead" safety net).
    'echoes': 'daily',

    # Monthly (1st of month)
    'monthly_playlist': 'monthly_1st',
}

def should_run(generator_name):
    """Check if a generator should run today based on its schedule."""
    sched = SCHEDULE.get(generator_name, 'daily')
    if sched == 'daily':
        return True
    # NOOSPHERE_DATE backfills a preview feed by hand (see utils.today).
    override = os.environ.get('NOOSPHERE_DATE')
    day = date.fromisoformat(override) if override else date.today()
    if sched == 'monthly_1st':
        return day.day == 1
    today_dow = day.weekday()  # 0=Monday
    return today_dow in sched
