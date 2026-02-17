"""Cadence schedule for Noosphere generators.

Each generator checks should_run() before generating.
Days: 0=Monday ... 6=Sunday
"""
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
    'midnight_postcard': 'daily',

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
}

    # Monthly (1st of month)
    'monthly_playlist': 'monthly_1st',
}

def should_run(generator_name):
    """Check if a generator should run today based on its schedule."""
    sched = SCHEDULE.get(generator_name, 'daily')
    if sched == 'daily':
        return True
    if sched == 'monthly_1st':
        return date.today().day == 1
    today_dow = date.today().weekday()  # 0=Monday
    return today_dow in sched
