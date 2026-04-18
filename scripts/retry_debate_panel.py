#!/usr/bin/env python3
"""
Manually trigger additional Debate Panel revision rounds for a specific TID.

Usage:
    python scripts/retry_debate_panel.py run-1cf1b8a3
    python scripts/retry_debate_panel.py tid_3.0avg_2approve_run-1cf1b8a3.html
    python scripts/retry_debate_panel.py run-1cf1b8a3 --rounds 2  # queue 2 retries

The script reads the final_drafts from completed_reviews, creates a new
pending_reviews entry, and lets the Auto Worker process it.
"""

import json
import sys
import glob
import shutil
import argparse
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent.parent


def find_run_id(input_str: str) -> str:
    """Accept full run_id, short prefix, or HTML filename."""
    # Strip HTML filename to extract run_id prefix
    if input_str.endswith(".html"):
        name = Path(input_str).stem
        parts = name.split("_")
        # filename: tid_3.0avg_2approve_run-1cf1b8a3
        for p in parts:
            if p.startswith("run-"):
                input_str = p
                break

    # Find full run_id from completed_reviews
    for f in glob.glob(str(BASE / "data/completed_reviews/*.json")):
        rid = Path(f).stem
        if rid.startswith(input_str):
            return rid

    raise ValueError(f"run_id not found: {input_str}")


def retry(run_id: str, rounds: int = 1):
    review_file = BASE / "data/completed_reviews" / f"{run_id}.json"
    mav_file = BASE / "data/completed_maverick" / f"{run_id}.json"

    if not review_file.exists():
        raise FileNotFoundError(f"No completed review: {review_file}")
    if not mav_file.exists():
        raise FileNotFoundError(f"No maverick data: {mav_file}")

    review = json.loads(review_file.read_text())
    mav = json.loads(mav_file.read_text())

    # Use final_drafts if available, otherwise fall back to original maverick drafts
    final_drafts = review.get("final_drafts")
    if not final_drafts:
        final_drafts = mav.get("drafts", [])
        print("  ⚠  No final_drafts in review, using original Maverick drafts")
    else:
        print(f"  Using final_drafts ({len(final_drafts)} drafts from last DP round)")

    target = mav.get("target", "")
    void_context = mav.get("void_context", "")
    domain = mav.get("domain", "")

    # Show current state
    cr = review.get("chairman_result", {})
    reviews = review.get("reviews", {})
    approves = sum(1 for r in reviews.values() if r.get("status") == "APPROVE")
    scores = [float(r.get("score", 0)) for r in reviews.values()]
    avg = sum(scores) / len(scores) if scores else 0
    prev_rounds = review.get("debate_rounds", 1)

    print(f"\n  Run ID: {run_id}")
    print(f"  Target: {target[:70]}")
    print(f"  Previous result: {cr.get('final_verdict')} | {approves}/4 APPROVE | avg={avg:.1f} | {prev_rounds} rounds")
    print(f"  Queueing {rounds} new retry round(s)...")

    pending_dir = BASE / "data/pending_reviews"
    pending_dir.mkdir(parents=True, exist_ok=True)

    queued = []
    for i in range(rounds):
        # Create a new run_id for each retry to avoid collision
        retry_run_id = f"{run_id}-retry{i+1}"
        pending_file = pending_dir / f"{retry_run_id}.json"

        if pending_file.exists():
            print(f"  ⚠  {pending_file.name} already exists, skipping")
            continue

        request = {
            "run_id": retry_run_id,
            "original_run_id": run_id,
            "timestamp": datetime.now().isoformat(),
            "domain": domain,
            "target": target,
            "void_context": void_context,
            "drafts": final_drafts,
            "retry_round": i + 1,
            "previous_verdict": cr.get("final_verdict", "REVISE"),
            "previous_approves": approves,
            "previous_avg_score": avg,
        }

        pending_file.write_text(json.dumps(request, indent=2, ensure_ascii=False))
        queued.append(pending_file.name)
        print(f"  ✅ Queued: {pending_file.name}")

    if queued:
        print(f"\n  {len(queued)} retry task(s) queued in data/pending_reviews/")
        print(f"  Auto Worker will pick them up automatically (DP priority).")
        print(f"  Results will appear in: output/generated/human_review/")
    return queued


def main():
    parser = argparse.ArgumentParser(description="Retry Debate Panel for a specific TID")
    parser.add_argument("run_id", help="run_id prefix, full run_id, or HTML filename from human_review/")
    parser.add_argument("--rounds", type=int, default=1, help="Number of additional retry rounds (default: 1)")
    args = parser.parse_args()

    import os
    os.chdir(BASE)

    try:
        full_rid = find_run_id(args.run_id)
        retry(full_rid, args.rounds)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
