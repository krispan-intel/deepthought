from __future__ import annotations

from pathlib import Path

from agents.state import PipelineState, TIDStatus
from services.human_review import HumanReviewCheckpoint


def _approved_state(run_id: str = "run-1") -> PipelineState:
    state = PipelineState(domain="linux_kernel", target="sched")
    state.run_id = run_id
    state.run_status = "APPROVED"
    state.tid_statuses = [TIDStatus(draft_index=0, title="x", status="DRAFTED")]
    return state


def test_human_review_pending_without_decision(tmp_path: Path) -> None:
    checker = HumanReviewCheckpoint(file_path=tmp_path / "decisions.jsonl")
    state = checker.apply(_approved_state())

    assert state.run_status == "HUMAN_REVIEW_REQUIRED"
    assert state.metadata["human_review"]["decision"] == "PENDING"
    assert state.tid_statuses[0].status == "WAITING_HUMAN_REVIEW"


def test_human_review_approved_when_decision_exists(tmp_path: Path) -> None:
    path = tmp_path / "decisions.jsonl"
    checker = HumanReviewCheckpoint(file_path=path)
    checker.append_decision("run-2", "APPROVED", reviewer="alice")

    state = checker.apply(_approved_state(run_id="run-2"))

    assert state.run_status == "APPROVED"
    assert state.metadata["human_review"]["decision"] == "APPROVED"
