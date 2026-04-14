#!/bin/bash
#
# DeepThought Progress Report
# Shows current system status, pending tasks, and recent activity
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║                    DeepThought Progress Report                         ║"
echo "║                    $(date '+%Y-%m-%d %H:%M:%S')                                   ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""

# ─────────────────────────────────────────────────────────────────
# 1. Services Status
# ─────────────────────────────────────────────────────────────────
echo "┌─ 1. SERVICES STATUS ────────────────────────────────────────────────┐"
echo "│                                                                      │"

# Pipeline Service
PIPELINE_PID=$(ps aux | grep "[r]un_pipeline_service.py" | awk '{print $2}' | head -1)
if [ -n "$PIPELINE_PID" ]; then
    PIPELINE_CPU=$(ps -p "$PIPELINE_PID" -o %cpu= | xargs)
    PIPELINE_MEM=$(ps -p "$PIPELINE_PID" -o %mem= | xargs)
    echo "│  Pipeline Service:  ✅ RUNNING (PID: $PIPELINE_PID, CPU: ${PIPELINE_CPU}%, MEM: ${PIPELINE_MEM}%)  │"
else
    echo "│  Pipeline Service:  ❌ NOT RUNNING                                  │"
fi

# Auto Worker
PID_FILE="logs/auto_worker.pid"
if [ -f "$PID_FILE" ]; then
    WORKER_PID=$(cat "$PID_FILE")
    if ps -p "$WORKER_PID" > /dev/null 2>&1; then
        WORKER_CPU=$(ps -p "$WORKER_PID" -o %cpu= | xargs)
        WORKER_MEM=$(ps -p "$WORKER_PID" -o %mem= | xargs)
        echo "│  Auto Worker:       ✅ RUNNING (PID: $WORKER_PID, CPU: ${WORKER_CPU}%, MEM: ${WORKER_MEM}%)  │"
    else
        echo "│  Auto Worker:       ❌ NOT RUNNING (stale PID)                      │"
    fi
else
    echo "│  Auto Worker:       ❌ NOT RUNNING                                  │"
fi

echo "│                                                                      │"
echo "└──────────────────────────────────────────────────────────────────────┘"
echo ""

# ─────────────────────────────────────────────────────────────────
# 2. Pending Tasks Queue
# ─────────────────────────────────────────────────────────────────
echo "┌─ 2. PENDING TASKS QUEUE ────────────────────────────────────────────┐"
echo "│                                                                      │"

PENDING_MAVERICK=$(find data/pending_maverick -name "*.json" 2>/dev/null | wc -l || echo 0)
PENDING_PROFESSOR=$(find data/pending_professor -name "*.json" 2>/dev/null | wc -l || echo 0)
PENDING_REALITY=$(find data/pending_reality_checker -name "*.json" 2>/dev/null | wc -l || echo 0)
PENDING_DEBATE=$(find data/pending_reviews -name "*.json" 2>/dev/null | wc -l || echo 0)
TOTAL_PENDING=$((PENDING_MAVERICK + PENDING_PROFESSOR + PENDING_REALITY + PENDING_DEBATE))

printf "│  %-30s %4d tasks                        │\n" "Maverick (Draft Gen):" "$PENDING_MAVERICK"
printf "│  %-30s %4d tasks                        │\n" "Professor (Review):" "$PENDING_PROFESSOR"
printf "│  %-30s %4d tasks                        │\n" "Reality Checker:" "$PENDING_REALITY"
printf "│  %-30s %4d tasks                        │\n" "Debate Panel:" "$PENDING_DEBATE"
echo "│  ────────────────────────────────────────────────────────────────    │"
printf "│  %-30s %4d tasks                        │\n" "TOTAL PENDING:" "$TOTAL_PENDING"

echo "│                                                                      │"
echo "└──────────────────────────────────────────────────────────────────────┘"
echo ""

# ─────────────────────────────────────────────────────────────────
# 3. Recently Completed (Last 30 minutes)
# ─────────────────────────────────────────────────────────────────
echo "┌─ 3. RECENTLY COMPLETED (Last 30 min) ───────────────────────────────┐"
echo "│                                                                      │"

COMPLETED_MAVERICK=$(find data/completed_maverick -name "*.json" -mmin -30 2>/dev/null | wc -l)
COMPLETED_PROFESSOR=$(find data/completed_professor -name "*.json" -mmin -30 2>/dev/null | wc -l)
COMPLETED_REALITY=$(find data/completed_reality_checker -name "*.json" -mmin -30 2>/dev/null | wc -l)
COMPLETED_DEBATE=$(find data/completed_reviews -name "*.json" -mmin -30 2>/dev/null | wc -l)

printf "│  %-30s %4d completed                     │\n" "Maverick:" "$COMPLETED_MAVERICK"
printf "│  %-30s %4d completed                     │\n" "Professor:" "$COMPLETED_PROFESSOR"
printf "│  %-30s %4d completed                     │\n" "Reality Checker:" "$COMPLETED_REALITY"
printf "│  %-30s %4d completed                     │\n" "Debate Panel:" "$COMPLETED_DEBATE"

echo "│                                                                      │"
echo "└──────────────────────────────────────────────────────────────────────┘"
echo ""

# ─────────────────────────────────────────────────────────────────
# 4. Pipeline Runs Statistics
# ─────────────────────────────────────────────────────────────────
echo "┌─ 4. PIPELINE RUNS (from pipeline_runs.jsonl) ───────────────────────┐"
echo "│                                                                      │"

if [ -f "data/processed/pipeline_runs.jsonl" ]; then
    source .venv/bin/activate 2>/dev/null || true
    python3 << 'PYEOF'
import json
from datetime import datetime, timedelta
from collections import Counter

with open('data/processed/pipeline_runs.jsonl', 'r') as f:
    all_runs = [json.loads(line) for line in f if line.strip()]

# Total stats
total = len(all_runs)
statuses = Counter(r['run_status'] for r in all_runs)

print(f"│  Total Runs: {total:4d}                                                  │")
print("│                                                                      │")

# Top statuses
for status in ['COMPLETED_EXPORT', 'APPROVED', 'REJECTED', 'PENDING_CLAUDE_MAVERICK',
               'PENDING_CLAUDE_PROFESSOR', 'PENDING_CLAUDE_REALITY_CHECKER', 'PENDING_CLAUDE_DEBATE_PANEL']:
    count = statuses.get(status, 0)
    if count > 0:
        print(f"│  {status:35s} {count:4d}                      │")

# Last 1 hour
cutoff = datetime.now() - timedelta(hours=1)
recent = [r for r in all_runs
          if datetime.fromisoformat(r['timestamp'].replace('Z', '+00:00')).replace(tzinfo=None) > cutoff]
print("│                                                                      │")
print(f"│  Last 1 Hour: {len(recent):4d} new runs                                       │")

PYEOF
else
    echo "│  ⚠️  pipeline_runs.jsonl not found                                  │"
fi

echo "│                                                                      │"
echo "└──────────────────────────────────────────────────────────────────────┘"
echo ""

# ─────────────────────────────────────────────────────────────────
# 5. Active gh copilot Processes
# ─────────────────────────────────────────────────────────────────
echo "┌─ 5. ACTIVE LLM PROCESSES ───────────────────────────────────────────┐"
echo "│                                                                      │"

COPILOT_COUNT=$(ps aux | grep "[g]h copilot" | grep -v grep | wc -l)
if [ "$COPILOT_COUNT" -gt 0 ]; then
    echo "│  🔄 $COPILOT_COUNT gh copilot processes currently running                   │"
else
    echo "│  ⏸️  No active gh copilot processes                                 │"
fi

echo "│                                                                      │"
echo "└──────────────────────────────────────────────────────────────────────┘"
echo ""

# ─────────────────────────────────────────────────────────────────
# 6. Recent Logs (Last 10 lines)
# ─────────────────────────────────────────────────────────────────
echo "┌─ 6. RECENT ACTIVITY ─────────────────────────────────────────────────┐"
echo "│                                                                      │"
echo "│  Pipeline Service Log (last 3 lines):                               │"
if [ -f "logs/pipeline_service.log" ]; then
    tail -3 logs/pipeline_service.log | while IFS= read -r line; do
        # Truncate long lines to fit
        truncated=$(echo "$line" | cut -c 1-66)
        printf "│    %-66s  │\n" "$truncated"
    done
else
    echo "│    (no log)                                                          │"
fi

echo "│                                                                      │"
echo "│  Auto Worker Log (last 3 lines):                                    │"
if [ -f "logs/auto_worker_continuous.log" ]; then
    tail -3 logs/auto_worker_continuous.log | while IFS= read -r line; do
        truncated=$(echo "$line" | cut -c 1-66)
        printf "│    %-66s  │\n" "$truncated"
    done
else
    echo "│    (no log)                                                          │"
fi

echo "│                                                                      │"
echo "└──────────────────────────────────────────────────────────────────────┘"
echo ""

# ─────────────────────────────────────────────────────────────────
# 7. Quick Actions
# ─────────────────────────────────────────────────────────────────
echo "┌─ 7. QUICK ACTIONS ───────────────────────────────────────────────────┐"
echo "│                                                                      │"
echo "│  View full logs:                                                     │"
echo "│    tail -f logs/pipeline_service.log                                │"
echo "│    tail -f logs/auto_worker_continuous.log                          │"
echo "│                                                                      │"
echo "│  Auto Worker statistics:                                             │"
echo "│    python scripts/auto_worker_stats.py                              │"
echo "│                                                                      │"
echo "│  Restart services:                                                   │"
echo "│    ./scripts/stop_auto_worker.sh && ./scripts/start_auto_worker.sh  │"
echo "│                                                                      │"
echo "│  Check detailed status:                                              │"
echo "│    ./scripts/check_workers_status.sh                                │"
echo "│                                                                      │"
echo "└──────────────────────────────────────────────────────────────────────┘"
echo ""
