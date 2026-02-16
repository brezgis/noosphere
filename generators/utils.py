"""Shared utilities for Noosphere content generators."""
import json, os, sys, datetime, requests

FEED_DIR = os.path.join(os.path.dirname(__file__), '..', 'feed')

def _get_llm_config():
    """Get LLM API configuration. Checks environment variables first, then OpenClaw config."""
    # Environment variables (for standalone/generic use)
    url = os.environ.get('LLM_API_URL')
    key = os.environ.get('LLM_API_KEY')
    model = os.environ.get('LLM_MODEL', 'claude-sonnet-4-20250514')
    
    if url and key:
        return url, key, model
    
    # Fall back to OpenClaw gateway config
    for config_name in ['openclaw.json', 'config.json']:
        for config_dir in ['~/.openclaw', '~/.clawdbot']:
            config_path = os.path.expanduser(os.path.join(config_dir, config_name))
            if os.path.exists(config_path):
                try:
                    with open(config_path) as f:
                        config = json.load(f)
                    token = config.get('gateway', {}).get('auth', {}).get('token', '')
                    if token:
                        return 'http://localhost:18789/v1/chat/completions', token, model
                except (json.JSONDecodeError, KeyError):
                    continue
    
    raise RuntimeError(
        "No LLM API configured. Set LLM_API_URL and LLM_API_KEY environment variables, "
        "or run with an OpenClaw gateway."
    )

def ask_claude(prompt, system=None, max_tokens=1024, temperature=0.8):
    """Generate text via an OpenAI-compatible chat completions endpoint."""
    url, token, model = _get_llm_config()
    
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    
    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        },
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
    """Write a feed item JSON file. name should be like '2026-02-16-weather'."""
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
