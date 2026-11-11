#!/bin/bash
# Build the static site into a directory: the frontend from public/ plus
# /api/feed as one static JSON file. Uploads nothing and runs no generators.
#
#   bash build.sh /some/dir
#
# export.sh calls this before it uploads. To look at the site locally, build
# into a scratch directory and serve that with any static file server.
set -e

NOOSPHERE_DIR="$(cd "$(dirname "$0")" && pwd)"
FEED_DIR="$NOOSPHERE_DIR/feed"
PUBLIC_DIR="$NOOSPHERE_DIR/public"
EXPORT_DIR="${1:?usage: build.sh <output-dir>}"

rm -rf "$EXPORT_DIR"
mkdir -p "$EXPORT_DIR/api"

# Copy static frontend
cp -r "$PUBLIC_DIR"/* "$EXPORT_DIR/"

# Stamp service worker with deploy version (content hash of every frontend
# file, so a change to the stylesheet or the scripts also retires old caches)
SW_VERSION=$(cd "$PUBLIC_DIR" && find . -type f | LC_ALL=C sort | xargs cat | md5sum | cut -c1-8)
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
def published(i):
    ts = i.get('timestamp')
    if not ts:
        return False
    try:
        return parse_ts(ts) <= now
    except Exception as e:
        print(f"  Warning: bad timestamp {ts!r}: {e}")
        return False
# INCLUDE_SCHEDULED=1 keeps cards whose time has not come yet. It exists for
# local previews and must stay off in the real export.
if not os.environ.get('INCLUDE_SCHEDULED'):
    items = [i for i in items if published(i)]
items = items[:500]
with open(output_file, 'w') as f:
    json.dump({"items": items, "count": len(items)}, f)
print(f"  Exported {len(items)} feed items")
PYEOF
