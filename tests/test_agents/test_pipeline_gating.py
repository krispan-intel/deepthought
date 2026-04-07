from __future__ import annotations

from agents.pipeline import DeepThoughtPipeline
from agents.state import PipelineState


class _ForagerNoVoids:
    def run(self, state: PipelineState, top_k: int = 5) -> PipelineState:
        state.void_statuses = []
        state.topological_void_context = ""
        return state


class _MaverickMustNotRun:
    def run(self, state: PipelineState, n_drafts: int = 3) -> PipelineState:
        raise AssertionError("Maverick should be skipped when Forager has no void evidence")


def test_pipeline_skips_maverick_when_forager_returns_no_voids() -> None:
    pipeline = DeepThoughtPipeline()
    pipeline.forager = _ForagerNoVoids()
    pipeline.maverick = _MaverickMustNotRun()

    state = PipelineState(domain="all_domains", target="auto")
    updated = pipeline.run(state, n_drafts=2, top_k_voids=8)

    assert updated.run_status == "REJECTED"
    assert "no topological voids" in updated.last_error.lower()
    assert updated.metadata["stage_status"]["forager"] == "OK"
    assert updated.metadata["stage_status"]["maverick"] == "SKIPPED_NO_VOIDS"
    assert updated.metadata["stage_status"]["patent_shield"] == "SKIPPED_NO_VOIDS"
    assert updated.metadata["stage_status"]["reality_checker"] == "SKIPPED_NO_VOIDS"
    assert updated.metadata["stage_status"]["debate_panel"] == "SKIPPED_NO_VOIDS"
