#!/bin/bash
#
# Start Claude Agent Auto Worker V2 in continuous mode
#
# Usage:
#   ./start_auto_worker.sh [N]              # N workers, all copilot_cli
#   ./start_auto_worker.sh [N] [M]          # N copilot_cli + M claude_code_cli
#
# Examples:
#   ./start_auto_worker.sh 4                # 4 copilot_cli workers
#   ./start_auto_worker.sh 4 4             # 4 copilot_cli + 4 claude_code_cli
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PID_DIR="$PROJECT_ROOT/logs"
NUM_COPILOT="${1:-1}"
NUM_CLAUDE="${2:-0}"
TOTAL=$((NUM_COPILOT + NUM_CLAUDE))

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
        echo "To stop all: $SCRIPT_DIR/stop_auto_worker.sh"
        exit 1
    fi
fi

echo "Starting $TOTAL Auto Worker(s): $NUM_COPILOT copilot_cli + $NUM_CLAUDE claude_code_cli"
echo ""

# Start copilot_cli workers
for i in $(seq 1 "$NUM_COPILOT"); do
    WORKER_ID="w${i}"
    LOG_FILE="$PID_DIR/auto_worker_${WORKER_ID}.log"
    PID_FILE="$PID_DIR/auto_worker_${WORKER_ID}.pid"

    nohup python "$SCRIPT_DIR/claude_agent_auto_worker_v2.py" \
        --worker-id "$WORKER_ID" \
        --backend copilot_cli \
        > "$LOG_FILE" 2>&1 &
    WORKER_PID=$!
    echo "$WORKER_PID" > "$PID_FILE"
    echo "  Worker $WORKER_ID [copilot_cli] started (PID: $WORKER_PID)"
done

# Start claude_code_cli workers (numbered after copilot workers)
for i in $(seq 1 "$NUM_CLAUDE"); do
    IDX=$((NUM_COPILOT + i))
    WORKER_ID="c${i}"
    LOG_FILE="$PID_DIR/auto_worker_${WORKER_ID}.log"
    PID_FILE="$PID_DIR/auto_worker_${WORKER_ID}.pid"

    nohup python "$SCRIPT_DIR/claude_agent_auto_worker_v2.py" \
        --worker-id "$WORKER_ID" \
        --backend claude_code_cli \
        > "$LOG_FILE" 2>&1 &
    WORKER_PID=$!
    echo "$WORKER_PID" > "$PID_FILE"
    echo "  Worker $WORKER_ID [claude_code_cli] started (PID: $WORKER_PID)"
done

echo ""
echo "Commands:"
echo "  View logs:  tail -f $PID_DIR/auto_worker_*.log"
echo "  Stop all:   $SCRIPT_DIR/stop_auto_worker.sh"
echo "  Status:     ps aux | grep auto_worker | grep -v grep"
