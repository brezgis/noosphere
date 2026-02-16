"""Shared utilities for Noosphere content generators."""
import json, os, sys, datetime, requests

FEED_DIR = os.path.join(os.path.dirname(__file__), '..', 'feed')
GATEWAY_URL = 'http://localhost:18789/v1/chat/completions'

def get_gateway_token():
    config_path = os.path.expanduser('~/.openclaw/openclaw.json')
    with open(config_path) as f:
        config = json.load(f)
    return config.get('gateway', {}).get('auth', {}).get('token', '')

def ask_claude(prompt, system=None, max_tokens=1024, temperature=0.8):
    """Generate text via the OpenClaw gateway chat completions endpoint."""
    token = get_gateway_token()
    messages = [{"role": "user", "content": prompt}]
    body = {
        "model": "anthropic/claude-sonnet-4-20250514",
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if system:
        body["messages"] = [{"role": "system", "content": system}] + messages
    
    resp = requests.post(
        GATEWAY_URL,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=body,
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    return data['choices'][0]['message']['content']

def today():
    """Return today's date string YYYY-MM-DD."""
    return datetime.date.today().isoformat()

def now_iso():
    """Return current time as ISO string."""
    return datetime.datetime.now().isoformat(timespec='seconds')

def write_feed(name, data):
    """Write a feed item JSON file. name like '2026-02-16-weather'."""
    os.makedirs(FEED_DIR, exist_ok=True)
    path = os.path.join(FEED_DIR, f"{name}.json")
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Wrote {path}")
    return path

def feed_exists(name):
    """Check if a feed item already exists for today."""
    path = os.path.join(FEED_DIR, f"{name}.json")
    return os.path.exists(path)
