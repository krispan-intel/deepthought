#!/bin/bash
#
# Start Claude Agent Auto Worker V2 in continuous mode
# Supports multiple concurrent workers: ./start_auto_worker.sh [N]
#   N = number of workers (default: 1)
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PID_DIR="$PROJECT_ROOT/logs"
NUM_WORKERS="${1:-1}"

cd "$PROJECT_ROOT"

# Activate virtual environment
source "$PROJECT_ROOT/.venv/bin/activate"

# Count existing workers
EXISTING=$(find "$PID_DIR" -name "auto_worker_*.pid" 2>/dev/null | wc -l)
if [ "$EXISTING" -gt 0 ]; then
    RUNNING=0
    for pid_file in "$PID_DIR"/auto_worker_*.pid; do
        pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            RUNNING=$((RUNNING + 1))
        else
            rm -f "$pid_file"
        fi
    done
    if [ "$RUNNING" -gt 0 ]; then
        echo "$RUNNING worker(s) already running."
        echo "To add more: stop first, then start with desired count."
        echo "To stop all: $SCRIPT_DIR/stop_auto_worker.sh"
        exit 1
    fi
fi

echo "Starting $NUM_WORKERS Auto Worker(s)..."
echo ""

for i in $(seq 1 "$NUM_WORKERS"); do
    WORKER_ID="w${i}"
    LOG_FILE="$PID_DIR/auto_worker_${WORKER_ID}.log"
    PID_FILE="$PID_DIR/auto_worker_${WORKER_ID}.pid"

    nohup python "$SCRIPT_DIR/claude_agent_auto_worker_v2.py" --worker-id "$WORKER_ID" > "$LOG_FILE" 2>&1 &
    WORKER_PID=$!
    echo "$WORKER_PID" > "$PID_FILE"

    echo "  Worker $WORKER_ID started (PID: $WORKER_PID) → $LOG_FILE"
done

echo ""
echo "Commands:"
echo "  View logs:  tail -f $PID_DIR/auto_worker_w*.log"
echo "  Stop all:   $SCRIPT_DIR/stop_auto_worker.sh"
echo "  Status:     ps aux | grep auto_worker | grep -v grep"
