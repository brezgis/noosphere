"""Integration tests for Noosphere export pipeline and feed JSON."""
import json
import os
import tempfile
import pytest
from datetime import datetime
from zoneinfo import ZoneInfo


class TestFeedExport:
    """Test the feed JSON export logic (inline Python from export.sh)."""

    def _build_feed(self, items, feed_dir, output_file):
        """Replicate the inline Python from export.sh."""
        all_items = []
        for i, item in enumerate(items):
            fname = os.path.join(feed_dir, f"item-{i:03d}.json")
            with open(fname, 'w') as f:
                json.dump(item, f)

        # Read back (same logic as export.sh)
        for fname in sorted(os.listdir(feed_dir), reverse=True):
            if not fname.endswith('.json'):
                continue
            with open(os.path.join(feed_dir, fname)) as fh:
                data = json.load(fh)
                entries = data if isinstance(data, list) else [data]
                all_items.extend(entries)

        all_items.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        now = datetime.now(ZoneInfo('America/New_York'))
        def parse_ts(ts):
            ts = ts.replace('Z', '+00:00')
            dt = datetime.fromisoformat(ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=ZoneInfo('America/New_York'))
            return dt

        all_items = [i for i in all_items if parse_ts(i['timestamp']) <= now]
        all_items = all_items[:500]

        with open(output_file, 'w') as f:
            json.dump({"items": all_items, "count": len(all_items)}, f)

        return all_items

    def test_feed_json_structure(self, sample_feed_items):
        """Exported feed JSON has correct structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            feed_dir = os.path.join(tmpdir, 'feed')
            os.makedirs(feed_dir)
            output = os.path.join(tmpdir, 'feed.json')
            self._build_feed(sample_feed_items, feed_dir, output)

            with open(output) as f:
                feed = json.load(f)

            assert 'items' in feed
            assert 'count' in feed
            assert feed['count'] == len(feed['items'])
            assert feed['count'] == len(sample_feed_items)

    def test_feed_sorted_newest_first(self, sample_feed_items):
        """Feed items are sorted newest-first by timestamp."""
        with tempfile.TemporaryDirectory() as tmpdir:
            feed_dir = os.path.join(tmpdir, 'feed')
            os.makedirs(feed_dir)
            output = os.path.join(tmpdir, 'feed.json')
            self._build_feed(sample_feed_items, feed_dir, output)

            with open(output) as f:
                feed = json.load(f)

            timestamps = [i['timestamp'] for i in feed['items']]
            assert timestamps == sorted(timestamps, reverse=True)

    def test_future_items_filtered(self, sample_feed_items, future_feed_item):
        """Items with future timestamps are excluded."""
        items = sample_feed_items + [future_feed_item]
        with tempfile.TemporaryDirectory() as tmpdir:
            feed_dir = os.path.join(tmpdir, 'feed')
            os.makedirs(feed_dir)
            output = os.path.join(tmpdir, 'feed.json')
            self._build_feed(items, feed_dir, output)

            with open(output) as f:
                feed = json.load(f)

            # Future item should be filtered out
            assert feed['count'] == len(sample_feed_items)
            types = [i['type'] for i in feed['items']]
            assert future_feed_item['title'] not in [i.get('title') for i in feed['items']]

    def test_feed_snapshot(self, sample_feed_items, snapshot):
        """Snapshot test for feed JSON structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            feed_dir = os.path.join(tmpdir, 'feed')
            os.makedirs(feed_dir)
            output = os.path.join(tmpdir, 'feed.json')
            self._build_feed(sample_feed_items, feed_dir, output)

            with open(output) as f:
                feed = json.load(f)

            summary = {
                'count': feed['count'],
                'types': sorted(set(i['type'] for i in feed['items'])),
                'all_have_timestamp': all('timestamp' in i for i in feed['items']),
                'all_have_type': all('type' in i for i in feed['items']),
            }
            assert summary == snapshot

    def test_empty_feed_dir(self):
        """Empty feed directory produces empty feed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            feed_dir = os.path.join(tmpdir, 'feed')
            os.makedirs(feed_dir)
            output = os.path.join(tmpdir, 'feed.json')
            self._build_feed([], feed_dir, output)

            with open(output) as f:
                feed = json.load(f)

            assert feed['count'] == 0
            assert feed['items'] == []


class TestEscapeHtml:
    """Test the frontend escapeHtml function logic.

    The actual function uses DOM (document.createElement), so we test
    the equivalent Python-side: ensure any user content going into
    the feed is safe, and verify the JS escapeHtml contract.
    """

    @pytest.mark.parametrize("payload", [
        '<script>alert(1)</script>',
        '<img src=x onerror=alert(1)>',
        '" onmouseover="alert(1)',
        '<svg/onload=alert(1)>',
    ])
    def test_xss_payloads_escaped(self, payload):
        """XSS payloads must be escaped by the equivalent of escapeHtml.

        The JS function uses textContent→innerHTML which escapes < > & ".
        html.escape neutralizes these by escaping angle brackets and quotes,
        making event handler attributes inert (they're text, not HTML).
        """
        from html import escape
        escaped = escape(payload, quote=True)
        # The raw payload must not appear unescaped
        assert payload not in escaped
        # Angle brackets must be escaped
        assert '<script>' not in escaped
        assert '<img ' not in escaped
        assert '<svg' not in escaped
        # Quotes must be escaped
        assert '"' not in escaped
