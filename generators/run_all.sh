#!/bin/bash
# Run all Noosphere content generators for today.
# Called by cron at 6am ET. Each generator skips if already generated for today.
# Schedule checks are handled by each generator via schedule.py.
set -e
cd "$(dirname "$0")"

echo "[$(date)] Running Noosphere generators..."

# Helper: run generator with schedule check
run() {
    local name="$1"
    local script="$2"
    if python3 -c "from schedule import should_run; exit(0 if should_run('$name') else 1)" 2>/dev/null; then
        python3 "$script" 2>&1 || echo "$name failed"
    else
        echo "  $name: skipped (not scheduled today)"
    fi
}

# Daily
run weather weather.py
run wittgenstein wittgenstein.py
run russian russian.py
run corpus_surprise corpus_surprise.py
run entropy_garden entropy_garden.py
run git_log git_log.py
run midnight_postcard midnight_postcard.py
run music_rec music_rec.py

# 3x/week (Mon, Wed, Fri)
run untranslatable untranslatable.py

# 2x/week
run apophenia apophenia.py
run penny_red penny_red.py

# Weekly
run the_diff the_diff.py
run typeface typeface.py
run recipe recipe.py
run dead_medium dead_medium.py
run annotation annotation.py

# Monthly (1st of month)
run monthly_playlist monthly_playlist.py

# === Low-stock monitor ===
python3 - <<'PYEOF'
import json, os, sys

DIR = os.path.dirname(os.path.realpath(sys.argv[0] if sys.argv[0] else "."))
DATA_DIR = os.path.join(DIR, "data")
warnings = []

def check_state(label, state_file, total, rate_desc, threshold=15):
    if os.path.exists(state_file):
        state = json.load(open(state_file))
        if 'used' in state:
            remaining = total - len(state['used'])
        elif 'index' in state:
            idx = state['index']
            remaining = total - idx if idx < total else total
        else:
            return
        if remaining < threshold:
            warnings.append(f"⚠️ {label}: {remaining}/{total} remaining ({rate_desc})")

# Check pools
check_state("Untranslatable", os.path.join(DIR, ".untranslatable-state.json"), 50, "~17 weeks at 3/wk")
check_state("Penny Red", os.path.join(DIR, ".penny-red-state.json"), 46, "~23 weeks at 2/wk")
check_state("Dead Medium", os.path.join(DIR, ".dead-medium-state.json"), 61, "~61 weeks at 1/wk")
check_state("The Diff", os.path.join(DIR, ".diff-state.json"), 20, "~20 weeks at 1/wk")
check_state("Typeface", os.path.join(DIR, ".typeface-state.json"), 32, "~32 weeks at 1/wk")

# JSON data files
for label, state_f, data_f, threshold in [
    ("Russian", ".russian-state.json", "data/russian-sentences.json", 20),
    ("Annotation", ".annotation-state.json", "data/literary-passages.json", 30),
    ("Wittgenstein", ".wittgenstein-state.json", "data/tractatus.json", 30),
]:
    sf = os.path.join(DIR, state_f)
    df = os.path.join(DIR, data_f)
    if os.path.exists(sf) and os.path.exists(df):
        state = json.load(open(sf))
        total = len(json.load(open(df)))
        idx = state.get('index', 0)
        remaining = total - idx if idx < total else total
        if remaining < threshold:
            warnings.append(f"⚠️ {label}: {remaining}/{total} remaining")

if warnings:
    print("\n🔔 NOOSPHERE LOW STOCK ALERTS:")
    for w in warnings:
        print(f"  {w}")
    alert_path = os.path.join(DIR, "..", "feed", ".low-stock-alert.txt")
    with open(alert_path, "w") as f:
        f.write("\n".join(warnings))
else:
    # Remove old alert if pools recovered
    alert_path = os.path.join(DIR, "..", "feed", ".low-stock-alert.txt")
    if os.path.exists(alert_path):
        os.remove(alert_path)
    print("✅ All content pools healthy.")
PYEOF

echo "[$(date)] Done."
