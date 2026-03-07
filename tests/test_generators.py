"""Unit tests for Noosphere generators and schedule."""
import json
import os
import sys
import pytest
from datetime import date
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'generators'))

import schedule


class TestSchedule:
    """Test schedule.py day-of-week logic."""

    def test_daily_generators_always_run(self):
        """Generators marked 'daily' should always return True."""
        for name, sched in schedule.SCHEDULE.items():
            if sched == 'daily':
                assert schedule.should_run(name) is True

    def test_weekly_monday_generator(self):
        """the_diff runs on Monday (weekday 0) only."""
        assert schedule.SCHEDULE['the_diff'] == [0]
        with patch('schedule.date') as mock_date:
            mock_date.today.return_value = date(2026, 3, 2)  # Monday
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            assert schedule.should_run('the_diff') is True

    def test_weekly_generator_wrong_day(self):
        """the_diff should NOT run on Tuesday."""
        with patch('schedule.date') as mock_date:
            mock_date.today.return_value = date(2026, 3, 3)  # Tuesday
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            assert schedule.should_run('the_diff') is False

    def test_monthly_1st(self):
        """monthly_playlist runs on 1st of month only."""
        assert schedule.SCHEDULE['monthly_playlist'] == 'monthly_1st'
        with patch('schedule.date') as mock_date:
            mock_date.today.return_value = date(2026, 3, 1)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            assert schedule.should_run('monthly_playlist') is True

    def test_monthly_not_1st(self):
        with patch('schedule.date') as mock_date:
            mock_date.today.return_value = date(2026, 3, 15)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            assert schedule.should_run('monthly_playlist') is False

    def test_mwf_schedule(self):
        """untranslatable runs Mon/Wed/Fri."""
        assert schedule.SCHEDULE['untranslatable'] == [0, 2, 4]

    def test_unknown_generator_defaults_daily(self):
        """Unknown generator name defaults to 'daily' (always runs)."""
        assert schedule.should_run('nonexistent_generator') is True


class TestGeneratorOutputSchema:
    """Each generator should produce feed items with required fields."""

    REQUIRED_FIELDS = {'type', 'timestamp'}
    REQUIRED_CONTENT = {'title', 'body', 'content', 'text', 'proposition',
                        'russian', 'description', 'commits', 'tracks', 'track'}

    def _validate_item(self, item):
        """Validate a feed item has required structure."""
        assert isinstance(item, dict), f"Feed item must be dict, got {type(item)}"
        assert 'type' in item, "Feed item missing 'type'"
        assert 'timestamp' in item, "Feed item missing 'timestamp'"
        # Must have at least one content field
        has_content = any(k in item for k in self.REQUIRED_CONTENT)
        assert has_content, f"Feed item has no content field. Keys: {list(item.keys())}"

    def test_sample_items_valid(self, sample_feed_items):
        """Sample fixture items pass validation."""
        for item in sample_feed_items:
            self._validate_item(item)
