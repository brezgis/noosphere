#!/bin/bash
# Noosphere static export: generate feed JSON + bundle static site → SCP to samovar
set -e

NOOSPHERE_DIR="$(cd "$(dirname "$0")" && pwd)"
FEED_DIR="$NOOSPHERE_DIR/feed"
PUBLIC_DIR="$NOOSPHERE_DIR/public"
EXPORT_DIR="/tmp/noosphere-export"
REMOTE_DIR="/home/projects/noosphere/public"

echo "[$(date)] Starting Noosphere export..."

# 1. Run generators (skip if not scheduled today)
bash "$NOOSPHERE_DIR/generators/run_all.sh" 2>&1 || echo "Warning: some generators failed"

# 2. Build static export
rm -rf "$EXPORT_DIR"
mkdir -p "$EXPORT_DIR/api"

# Copy static frontend
cp -r "$PUBLIC_DIR"/* "$EXPORT_DIR/"

# Stamp service worker with deploy version (content hash of index.html)
SW_VERSION=$(md5sum "$EXPORT_DIR/index.html" | cut -c1-8)
sed -i "s/AUTO_VERSION/$SW_VERSION/g" "$EXPORT_DIR/sw.js"
echo "  SW cache version: $SW_VERSION"

# Generate /api/feed as static JSON
python3 - "$FEED_DIR" "$EXPORT_DIR/api/feed" << 'PYEOF'
import json, os, sys
from datetime import datetime
from zoneinfo import ZoneInfo

feed_dir = sys.argv[1]
output_file = sys.argv[2]
items = []
for f in sorted(os.listdir(feed_dir), reverse=True):
    if not f.endswith('.json'): continue
    try:
        with open(os.path.join(feed_dir, f)) as fh:
            data = json.load(fh)
            entries = data if isinstance(data, list) else [data]
            items.extend(entries)
    except Exception as e:
        print(f"  Warning: malformed {f}: {e}")
items.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
now = datetime.now(ZoneInfo('America/New_York'))
def parse_ts(ts):
    ts = ts.replace('Z', '+00:00')
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo('America/New_York'))
    return dt
items = [i for i in items if parse_ts(i['timestamp']) <= now]
items = items[:500]
with open(output_file, 'w') as f:
    json.dump({"items": items, "count": len(items)}, f)
print(f"  Exported {len(items)} feed items")
PYEOF

# 3. Upload to samovar via SCP (uses SSH alias from ~/.ssh/config)
echo "[$(date)] Uploading to samovar..."
scp -r "$EXPORT_DIR"/* samovar:"$REMOTE_DIR/"
ssh samovar "chown -R projects:projects $REMOTE_DIR/ && chmod -R o+r $REMOTE_DIR/"

# 4. Cleanup
rm -rf "$EXPORT_DIR"

echo "[$(date)] Export complete."
