from __future__ import annotations

from pathlib import Path

from agents.state import PipelineState, VoidStatus
from services.void_tracker import IncrementalVoidTracker


def _state(run_id: str, void_id: str, label: str) -> PipelineState:
    state = PipelineState(domain="linux_kernel", target="sched")
    state.run_id = run_id
    state.void_statuses = [
        VoidStatus(
            void_id=void_id,
            label=label,
            mmr_score=0.8,
            relevance_score=0.7,
            novelty_score=0.6,
        )
    ]
    return state


def test_void_tracker_counts_new_and_recurring(tmp_path: Path) -> None:
    path = tmp_path / "voids.jsonl"
    tracker = IncrementalVoidTracker(file_path=path)

    first = tracker.record_run(_state("run-1", "v1", "foo"))
    second = tracker.record_run(_state("run-2", "v1", "foo"))

    assert first["new_voids"] == 1
    assert first["recurring_voids"] == 0
    assert second["new_voids"] == 0
    assert second["recurring_voids"] == 1
