#!/bin/bash
#
# Check status of all DeepThought services
#

echo "=== DeepThought Services Status ==="
echo ""

# Pipeline Service
echo "1. Pipeline Service:"
PIPELINE_PID=$(ps aux | grep "run_pipeline_service.py" | grep -v grep | awk '{print $2}')
if [ -n "$PIPELINE_PID" ]; then
    echo "   ✅ Running (PID: $PIPELINE_PID)"
else
    echo "   ❌ Not running"
fi

# Auto Worker
echo ""
echo "2. Auto Worker:"
PID_FILE="logs/auto_worker.pid"
if [ -f "$PID_FILE" ]; then
    WORKER_PID=$(cat "$PID_FILE")
    if ps -p "$WORKER_PID" > /dev/null 2>&1; then
        echo "   ✅ Running (PID: $WORKER_PID)"
    else
        echo "   ❌ Not running (stale PID file)"
    fi
else
    echo "   ❌ Not running"
fi

# Pending tasks
echo ""
echo "3. Pending Tasks:"
echo "   Maverick: $(ls data/pending_maverick/*.json 2>/dev/null | wc -l)"
echo "   Professor: $(ls data/pending_professor/*.json 2>/dev/null | wc -l)"
echo "   Reality Checker: $(ls data/pending_reality_checker/*.json 2>/dev/null | wc -l)"
echo "   Debate Panel: $(ls data/pending_reviews/*.json 2>/dev/null | wc -l)"

echo ""
echo "=== Recent Activity ==="
echo "Pipeline log (last 5 lines):"
tail -5 logs/pipeline_service.log 2>/dev/null || echo "  (no log)"
echo ""
echo "Auto worker log (last 5 lines):"
tail -5 logs/auto_worker_continuous.log 2>/dev/null || echo "  (no log)"
