#!/usr/bin/env python3
"""
Auto Worker Statistics
Analyzes auto_worker_continuous.log to show processing stats
"""

import re
from datetime import datetime, timedelta
from pathlib import Path

def parse_log():
    log_file = Path("logs/auto_worker_continuous.log")
    if not log_file.exists():
        print("No log file found")
        return

    stats_30min = {"maverick": {"success": 0, "failed": 0},
                   "professor": {"success": 0, "failed": 0},
                   "reality_checker": {"success": 0, "failed": 0},
                   "debate_panel": {"success": 0, "failed": 0}}

    stats_total = {"maverick": {"success": 0, "failed": 0},
                   "professor": {"success": 0, "failed": 0},
                   "reality_checker": {"success": 0, "failed": 0},
                   "debate_panel": {"success": 0, "failed": 0}}

    cutoff_30min = datetime.now() - timedelta(minutes=30)

    with open(log_file, 'r') as f:
        for line in f:
            # Parse timestamp
            match_time = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
            if not match_time:
                continue

            try:
                timestamp = datetime.strptime(match_time.group(1), '%Y-%m-%d %H:%M:%S')
            except:
                continue

            # Parse completion messages
            if "task completed:" in line:
                if "Maverick" in line:
                    agent = "maverick"
                elif "Professor" in line:
                    agent = "professor"
                elif "Reality Checker" in line:
                    agent = "reality_checker"
                elif "Debate Panel" in line:
                    agent = "debate_panel"
                else:
                    continue

                stats_total[agent]["success"] += 1
                if timestamp >= cutoff_30min:
                    stats_30min[agent]["success"] += 1

            elif "task failed:" in line or "Unexpected error processing" in line:
                if "maverick" in line:
                    agent = "maverick"
                elif "professor" in line:
                    agent = "professor"
                elif "reality_checker" in line:
                    agent = "reality_checker"
                elif "debate_panel" in line:
                    agent = "debate_panel"
                else:
                    continue

                stats_total[agent]["failed"] += 1
                if timestamp >= cutoff_30min:
                    stats_30min[agent]["failed"] += 1

    print("="*70)
    print("AUTO WORKER STATISTICS")
    print("="*70)
    print()
    print("LAST 30 MINUTES:")
    print("-"*70)
    for agent, data in stats_30min.items():
        total = data["success"] + data["failed"]
        if total > 0:
            success_rate = (data["success"] / total * 100) if total > 0 else 0
            print(f"  {agent.upper():20s} {data['success']:3d} succeeded, {data['failed']:3d} failed  ({success_rate:.1f}% success)")

    print()
    print("TOTAL (Since worker started):")
    print("-"*70)
    for agent, data in stats_total.items():
        total = data["success"] + data["failed"]
        if total > 0:
            success_rate = (data["success"] / total * 100) if total > 0 else 0
            print(f"  {agent.upper():20s} {data['success']:3d} succeeded, {data['failed']:3d} failed  ({success_rate:.1f}% success)")
    print("="*70)

if __name__ == "__main__":
    parse_log()
