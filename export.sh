#!/bin/bash
# Noosphere static export: generate feed JSON + bundle static site → SCP to the deploy host
set -e

NOOSPHERE_DIR="$(cd "$(dirname "$0")" && pwd)"
FEED_DIR="$NOOSPHERE_DIR/feed"
PUBLIC_DIR="$NOOSPHERE_DIR/public"
EXPORT_DIR="/tmp/noosphere-export"

# Local config (.env) names the deploy host, so no machine name lives in the repo.
if [ -f "$NOOSPHERE_DIR/.env" ]; then set -a; . "$NOOSPHERE_DIR/.env"; set +a; fi
DEPLOY_HOST="${DEPLOY_HOST:?Set DEPLOY_HOST (an ssh host or alias) in .env or the environment}"
REMOTE_DIR="${REMOTE_DIR:-/home/projects/noosphere/public}"
REMOTE_PARENT="$(dirname "$REMOTE_DIR")"

echo "[$(date)] Starting Noosphere export..."

# 1. Run generators (skip if not scheduled today)
bash "$NOOSPHERE_DIR/generators/run_all.sh" 2>&1 || echo "Warning: some generators failed"

# 2. Build static export (frontend + /api/feed as one static JSON file)
bash "$NOOSPHERE_DIR/build.sh" "$EXPORT_DIR"

# 3. Upload to VPS via SCP (uses SSH alias from ~/.ssh/config)
echo "[$(date)] Uploading to VPS..."
ssh "$DEPLOY_HOST" "mkdir -p $REMOTE_DIR/api"
scp -r "$EXPORT_DIR"/* "$DEPLOY_HOST":"$REMOTE_DIR/"
# chown to the projects user; a+rX gives nginx (www-data) read on files and
# traverse (+x) on directories — plain o+r would not let it enter subdirs.
ssh "$DEPLOY_HOST" "chown -R projects:projects $REMOTE_DIR/ && chmod -R a+rX $REMOTE_DIR/ && chmod a+rx $REMOTE_PARENT $(dirname "$REMOTE_PARENT")"

# 4. Cleanup
rm -rf "$EXPORT_DIR"

echo "[$(date)] Export complete."
