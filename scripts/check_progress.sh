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

# Auto Workers (supports multiple concurrent workers)
WORKER_COUNT=0
WORKER_PIDS=""
for pid_file in logs/auto_worker_*.pid logs/auto_worker.pid; do
    [ -f "$pid_file" ] || continue
    pid=$(cat "$pid_file")
    if ps -p "$pid" > /dev/null 2>&1; then
        WORKER_COUNT=$((WORKER_COUNT + 1))
        WORKER_PIDS="$WORKER_PIDS $pid"
    fi
done

if [ "$WORKER_COUNT" -gt 0 ]; then
    COPILOT_ACTIVE=$(ps aux | grep "[g]h copilot" | wc -l)
    CLAUDE_ACTIVE=$(ps aux | grep "[c]laude -p" | grep -v "claude_agent\|check_progress" | wc -l || true)
    # Count w* vs c* workers from active pids
    COPILOT_WORKERS=0
    CLAUDE_WORKERS=0
    for pid_file in logs/auto_worker_*.pid; do
        [ -f "$pid_file" ] || continue
        pid=$(cat "$pid_file")
        ps -p "$pid" > /dev/null 2>&1 || continue
        wname=$(basename "$pid_file" .pid | sed 's/auto_worker_//')
        case "$wname" in c*) CLAUDE_WORKERS=$((CLAUDE_WORKERS+1)) ;; *) COPILOT_WORKERS=$((COPILOT_WORKERS+1)) ;; esac
    done
    printf "│  Auto Workers:      ✅ %d RUNNING (copilot: %d workers/%d calls | claude: %d workers/%d calls)  │\n" \
        "$WORKER_COUNT" "$COPILOT_WORKERS" "$COPILOT_ACTIVE" "$CLAUDE_WORKERS" "$CLAUDE_ACTIVE"
else
    echo "│  Auto Workers:      ❌ NOT RUNNING                                 │"
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
echo "│  Auto Worker Logs (active workers only):                            │"
FOUND_LOG=0
# Only show workers with active PID files
for pid_file in logs/auto_worker_*.pid; do
    [ -f "$pid_file" ] || continue
    pid=$(cat "$pid_file")
    ps -p "$pid" > /dev/null 2>&1 || continue  # skip dead workers
    wname=$(basename "$pid_file" .pid | sed 's/auto_worker_//')
    log_file="logs/auto_worker_${wname}.log"
    [ -f "$log_file" ] || continue
    FOUND_LOG=1
    # Detect backend from worker ID: c* = claude_code_cli, w* = copilot_cli
    case "$wname" in
        c*) backend="claude_code" ;;
        *)  backend="copilot_cli" ;;
    esac
    last_line=$(tail -1 "$log_file" 2>/dev/null | cut -c 1-52)
    printf "│    [%s|%s] %-52s  │\n" "$wname" "$backend" "$last_line"
done
if [ "$FOUND_LOG" -eq 0 ]; then
    echo "│    (no active workers)                                               │"
fi

echo "│                                                                      │"
echo "└──────────────────────────────────────────────────────────────────────┘"
echo ""

# ─────────────────────────────────────────────────────────────────
# 7. Pachinko Funnel (Stage-by-Stage Conversion)
# ─────────────────────────────────────────────────────────────────
echo "┌─ 7. 🎰 PACHINKO FUNNEL ──────────────────────────────────────────────┐"
echo "│                                                                      │"

source .venv/bin/activate 2>/dev/null || true
python3 << 'FUNNEL_EOF'
import json, glob, os

# Count completions at each stage
maverick = len(glob.glob('data/completed_maverick/*.json'))
professor = len(glob.glob('data/completed_professor/*.json'))
rc = len(glob.glob('data/completed_reality_checker/*.json'))
debate = len(glob.glob('data/completed_reviews/*.json'))

# Professor pass rate (from completed professor files)
prof_passed = 0
prof_rejected = 0
for f in glob.glob('data/completed_professor/*.json'):
    try:
        data = json.load(open(f))
        verdicts = data.get("verdicts", [])
        if any(v.get("verdict") == "PASS" for v in verdicts):
            prof_passed += 1
        else:
            prof_rejected += 1
    except:
        pass

# RC verdict breakdown
rc_approve = rc_revise = rc_reject = 0
for f in glob.glob('data/completed_reality_checker/*.json'):
    try:
        data = json.load(open(f))
        s = data.get('status', data.get('verdict', ''))
        if s in ('APPROVE', 'APPROVED'): rc_approve += 1
        elif s == 'REVISE': rc_revise += 1
        elif s == 'REJECT': rc_reject += 1
    except:
        pass

# Debate verdict breakdown
db_approve = db_revise = db_reject = 0
for f in glob.glob('data/completed_reviews/*.json'):
    try:
        data = json.load(open(f))
        cr = data.get('chairman_result', data)
        v = cr.get('final_verdict', '')
        if v == 'APPROVE': db_approve += 1
        elif v == 'REVISE': db_revise += 1
        elif v == 'REJECT': db_reject += 1
    except:
        pass

# Final approved from pipeline_runs
approved = 0
total_runs = 0
if os.path.exists('data/processed/pipeline_runs.jsonl'):
    with open('data/processed/pipeline_runs.jsonl') as f:
        for line in f:
            if not line.strip(): continue
            total_runs += 1
            r = json.loads(line)
            if r.get('run_status') == 'APPROVED':
                approved += 1

# Print funnel
def pct(n, base):
    return f"{100*n/base:.0f}%" if base > 0 else "-%"

def bar(n, base, width=20):
    ratio = n / base if base > 0 else 0
    filled = int(ratio * width)
    return "█" * filled + "░" * (width - filled)

base = maverick if maverick > 0 else 1

print(f"│  Forager → Maverick    {bar(maverick, base)} {maverick:4d}  (100%)       │")
print(f"│  → Professor           {bar(professor, base)} {professor:4d}  ({pct(professor, maverick):>4s})       │")
if professor > 0:
    print(f"│    ├─ PASS: {prof_passed}   REJECT: {prof_rejected}                                   │")
print(f"│  → Reality Checker     {bar(rc, base)} {rc:4d}  ({pct(rc, maverick):>4s})       │")
if rc > 0:
    print(f"│    ├─ APPROVE: {rc_approve}  REVISE: {rc_revise}  REJECT: {rc_reject}                          │")
print(f"│  → Debate Panel        {bar(debate, base)} {debate:4d}  ({pct(debate, maverick):>4s})       │")
if debate > 0:
    print(f"│    ├─ APPROVE: {db_approve}  REVISE: {db_revise}  REJECT: {db_reject}                          │")
print(f"│  → APPROVED TID        {bar(approved, base)} {approved:4d}  ({pct(approved, maverick):>4s})       │")
print(f"│                                                                      │")
print(f"│  Jackpot Rate: {pct(approved, maverick):>4s}  ({approved}/{maverick})                                │")

# Pending queue depth (shows backlog)
pending_m = len(glob.glob('data/pending_maverick/*.json'))
pending_p = len(glob.glob('data/pending_professor/*.json'))
pending_r = len(glob.glob('data/pending_reality_checker/*.json'))
pending_d = len(glob.glob('data/pending_reviews/*.json'))
total_pending = pending_m + pending_p + pending_r + pending_d
if total_pending > 0:
    print(f"│  Backlog: M={pending_m} P={pending_p} RC={pending_r} DP={pending_d} (total={total_pending})              │")

FUNNEL_EOF

echo "│                                                                      │"
echo "└──────────────────────────────────────────────────────────────────────┘"
echo ""

# ─────────────────────────────────────────────────────────────────
# 8. Quick Actions
# ─────────────────────────────────────────────────────────────────
echo "┌─ 8. QUICK ACTIONS ───────────────────────────────────────────────────┐"
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
