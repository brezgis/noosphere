#!/bin/bash
# Noosphere export wrapper with log rotation.
# Path-robust: resolves its own directory instead of hardcoding one.
NOOSPHERE_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$NOOSPHERE_DIR/export.log"
MAX_LINES=1000

# Rotate if too big
if [ -f "$LOG" ] && [ "$(wc -l < "$LOG")" -gt "$MAX_LINES" ]; then
    tail -$MAX_LINES "$LOG" > "${LOG}.tmp" && mv "${LOG}.tmp" "$LOG"
fi

# Run the actual export, appending to the log
bash "$NOOSPHERE_DIR/export.sh" >> "$LOG" 2>&1
