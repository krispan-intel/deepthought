#!/bin/bash
#
# Stop all Claude Agent Auto Worker instances
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PID_DIR="$PROJECT_ROOT/logs"

STOPPED=0

for pid_file in "$PID_DIR"/auto_worker_*.pid "$PID_DIR"/auto_worker.pid; do
    [ -f "$pid_file" ] || continue
    pid=$(cat "$pid_file")
    if ps -p "$pid" > /dev/null 2>&1; then
        echo "Stopping worker (PID: $pid)..."
        kill "$pid" 2>/dev/null
        STOPPED=$((STOPPED + 1))
    fi
    rm -f "$pid_file"
done

if [ "$STOPPED" -gt 0 ]; then
    echo "$STOPPED worker(s) stopped."
else
    echo "No workers running."
fi
