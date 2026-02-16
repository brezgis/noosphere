#!/usr/bin/env python3
"""git log --oneline — curated interesting commits from watched repos.

Uses GitHub API (no auth needed for public repos, 60 req/hr rate limit).
"""
import requests, random, json, os
from datetime import datetime, timedelta
from utils import today, write_feed, feed_exists

# Repos to watch — a mix of NLP tools, terminal utilities, creative coding, language models
REPOS = [
    # NLP / Linguistics
    "huggingface/transformers",
    "explosion/spaCy",
    "stanfordnlp/stanza",
    "nltk/nltk",
    "facebookresearch/fastText",
    "flairNLP/flair",
    
    # Language Models / AI
    "ggerganov/llama.cpp",
    "ollama/ollama",
    "vllm-project/vllm",
    "Mozilla-Ocho/llamafile",
    "openai/whisper",
    "SYSTRAN/faster-whisper",
    
    # Terminal / CLI
    "starship/starship",
    "sharkdp/bat",
    "eza-community/eza",
    "tmux/tmux",
    "helix-editor/helix",
    "jesseduffield/lazygit",
    "charmbracelet/glow",
    "charmbracelet/bubbletea",
    
    # Creative Coding / Generative
    "processing/p5.js",
    "mrdoob/three.js",
    "tonsky/FiraCode",
    "be5invis/Iosevka",
    
    # Languages / Compilers
    "rust-lang/rust",
    "python/cpython",
    "ziglang/zig",
    
    # Interesting / Misc
    "jgm/pandoc",
    "typst/typst",
    "obsidianmd/obsidian-releases",
]

HEADERS = {
    'Accept': 'application/vnd.github.v3+json',
    'User-Agent': 'Noosphere/1.0',
}

def get_recent_commits(repo, since_hours=48, max_commits=3):
    """Get recent commits from a GitHub repo."""
    since = (datetime.utcnow() - timedelta(hours=since_hours)).isoformat() + 'Z'
    url = f"https://api.github.com/repos/{repo}/commits?since={since}&per_page={max_commits}"
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return []
        
        commits = []
        for c in resp.json()[:max_commits]:
            msg = c['commit']['message'].split('\n')[0][:80]  # first line, truncated
            sha = c['sha'][:7]
            commits.append({
                'hash': sha,
                'message': msg,
                'repo': repo.split('/')[-1],
            })
        return commits
    except Exception as e:
        return []

def generate():
    name = f"{today()}-git-log"
    if feed_exists(name):
        print(f"Already exists: {name}")
        return

    all_commits = []
    
    # Sample ~15 repos to avoid hitting rate limits
    sample = random.sample(REPOS, min(15, len(REPOS)))
    
    for repo in sample:
        commits = get_recent_commits(repo)
        all_commits.extend(commits)
    
    if not all_commits:
        # Fallback: try with longer window
        for repo in random.sample(REPOS, 5):
            commits = get_recent_commits(repo, since_hours=168)  # past week
            all_commits.extend(commits)
    
    if not all_commits:
        print("No commits found")
        return
    
    # Pick the most interesting ~5 commits (diverse repos)
    seen_repos = set()
    selected = []
    random.shuffle(all_commits)
    for c in all_commits:
        if c['repo'] not in seen_repos and len(selected) < 6:
            selected.append(c)
            seen_repos.add(c['repo'])
    
    write_feed(name, {
        "type": "git_log",
        "timestamp": f"{today()}T12:00:00",
        "commits": selected,
    })

if __name__ == '__main__':
    generate()
