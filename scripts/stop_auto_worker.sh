#!/bin/bash
#
# Stop Claude Agent Auto Worker V2
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PID_FILE="$PROJECT_ROOT/logs/auto_worker.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "No PID file found. Worker may not be running."
    exit 0
fi

WORKER_PID=$(cat "$PID_FILE")

if ps -p "$WORKER_PID" > /dev/null 2>&1; then
    echo "Stopping auto worker (PID: $WORKER_PID)..."
    kill "$WORKER_PID"

    # Wait for graceful shutdown
    sleep 2

    if ps -p "$WORKER_PID" > /dev/null 2>&1; then
        echo "Worker didn't stop gracefully, forcing..."
        kill -9 "$WORKER_PID" 2>/dev/null || true
    fi

    rm -f "$PID_FILE"
    echo "Worker stopped."
else
    echo "Worker process $WORKER_PID not found (already stopped?)"
    rm -f "$PID_FILE"
fi
