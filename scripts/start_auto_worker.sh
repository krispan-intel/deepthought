#!/bin/bash
#
# Start Claude Agent Auto Worker V2 in continuous mode
# This worker will continuously process pending tasks asynchronously
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_ROOT/logs/auto_worker_continuous.log"
PID_FILE="$PROJECT_ROOT/logs/auto_worker.pid"

cd "$PROJECT_ROOT"

# Check if worker is already running
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "Auto worker is already running (PID: $OLD_PID)"
        echo "To stop it: kill $OLD_PID"
        exit 1
    else
        # Stale PID file
        rm -f "$PID_FILE"
    fi
fi

# Activate virtual environment
source "$PROJECT_ROOT/.venv/bin/activate"

echo "Starting Claude Agent Auto Worker V2 (continuous mode)..."
echo "Log file: $LOG_FILE"

# Start worker in background
nohup python "$SCRIPT_DIR/claude_agent_auto_worker_v2.py" > "$LOG_FILE" 2>&1 &
WORKER_PID=$!

# Save PID
echo "$WORKER_PID" > "$PID_FILE"

echo "Worker started with PID: $WORKER_PID"
echo ""
echo "Commands:"
echo "  View logs:  tail -f $LOG_FILE"
echo "  Stop:       kill $WORKER_PID  (or: $SCRIPT_DIR/stop_auto_worker.sh)"
echo "  Status:     ps aux | grep $WORKER_PID | grep -v grep"
