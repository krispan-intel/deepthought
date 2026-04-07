"""
services/human_review.py

Human-in-the-loop review checkpoint.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from agents.state import PipelineState
from configs.settings import settings


class HumanReviewCheckpoint:
    def __init__(self, file_path: Path | None = None):
        self.file_path = file_path or settings.human_review_decisions_path
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def apply(self, state: PipelineState) -> PipelineState:
        if state.run_status != "APPROVED":
            return state

        decision = self._get_decision(state.run_id)
        if not decision and settings.human_review_auto_approve:
            decision = "APPROVED"
            self.append_decision(
                run_id=state.run_id,
                decision=decision,
                reviewer="auto-approve",
                rationale="human_review_auto_approve enabled",
            )

        if decision == "APPROVED":
            state.metadata["human_review"] = {"decision": "APPROVED"}
            return state

        if decision == "REJECTED":
            state.run_status = "REJECTED"
            state.last_error = "Rejected by human review checkpoint"
            state.metadata["human_review"] = {"decision": "REJECTED"}
            return state

        state.run_status = "HUMAN_REVIEW_REQUIRED"
        state.metadata["human_review"] = {
            "decision": "PENDING",
            "decision_file": str(self.file_path),
        }
        for tid in state.tid_statuses:
            if tid.status not in {"REJECTED"}:
                tid.status = "WAITING_HUMAN_REVIEW"
        return state

    def append_decision(self, run_id: str, decision: str, reviewer: str, rationale: str = "") -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "run_id": run_id,
            "decision": decision,
            "reviewer": reviewer,
            "rationale": rationale,
        }
        with self.file_path.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _get_decision(self, run_id: str) -> Optional[str]:
        if not self.file_path.exists():
            return None

        decision: Optional[str] = None
        for line in self.file_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row: Dict = json.loads(line)
            except json.JSONDecodeError:
                continue
            if str(row.get("run_id", "")).strip() != run_id:
                continue
            value = str(row.get("decision", "")).upper().strip()
            if value in {"APPROVED", "REJECTED"}:
                decision = value
        return decision
