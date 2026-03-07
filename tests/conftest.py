"""Fixtures for Noosphere tests."""
import json
import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, date

# Add project root and generators to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'generators'))


@pytest.fixture
def sample_feed_items():
    """Sample feed items for testing."""
    return [
        {
            "type": "weather",
            "timestamp": "2026-03-01T08:00:00-05:00",
            "title": "Morning Weather",
            "body": "Sunny skies with a light breeze.",
        },
        {
            "type": "wittgenstein",
            "timestamp": "2026-03-01T07:00:00-05:00",
            "title": "Proposition 6.54",
            "number": "6.54",
            "proposition": "My propositions serve as elucidations.",
            "commentary": "The ladder must be thrown away.",
        },
        {
            "type": "russian",
            "timestamp": "2026-03-01T06:00:00-05:00",
            "title": "Word of the Day",
            "russian": "тоска",
            "transliteration": "toská",
            "body": "A deep spiritual anguish.",
        },
    ]


@pytest.fixture
def future_feed_item():
    """A feed item with a future timestamp."""
    return {
        "type": "weather",
        "timestamp": "2099-12-31T23:59:59-05:00",
        "title": "Future Weather",
        "body": "Unknown.",
    }


@pytest.fixture
def mock_llm(monkeypatch):
    """Mock the LLM API to avoid real API calls."""
    def fake_ask_claude(prompt, system=None, max_tokens=1024, temperature=0.8):
        return "Mocked LLM response for testing."
    monkeypatch.setattr('utils.ask_claude', fake_ask_claude)
    return fake_ask_claude


@pytest.fixture
def mock_requests(monkeypatch):
    """Mock requests.post/get to prevent external API calls."""
    mock_post = MagicMock()
    mock_post.return_value.status_code = 200
    mock_post.return_value.ok = True
    mock_post.return_value.json.return_value = {
        "choices": [{"message": {"content": "Mocked response"}}]
    }
    mock_get = MagicMock()
    mock_get.return_value.status_code = 200
    mock_get.return_value.ok = True
    mock_get.return_value.json.return_value = {}
    monkeypatch.setattr('requests.post', mock_post)
    monkeypatch.setattr('requests.get', mock_get)
    return mock_post, mock_get


XSS_PAYLOADS = [
    '<script>alert(1)</script>',
    '<img src=x onerror=alert(1)>',
    '" onmouseover="alert(1)',
    "javascript:alert('xss')",
    '<svg/onload=alert(1)>',
]
