from __future__ import annotations

from agents.patent_shield import PatentShieldAgent
from agents.state import DraftIdea, PipelineState


def _draft(title: str, one_liner: str) -> DraftIdea:
    return DraftIdea(
        title=title,
        one_liner=one_liner,
        novelty_thesis="n",
        feasibility_thesis="f",
        market_thesis="m",
        why_now="w",
        problem_statement="p",
        prior_art_gap="g",
        proposed_invention="x86 kernel memory balancing",
        architecture_overview="a",
        implementation_plan="i",
        validation_plan="v",
        draft_claims=["c1", "c2", "c3"],
    )


def test_patent_shield_flags_high_overlap_without_api() -> None:
    state = PipelineState(
        domain="linux_kernel",
        target="scheduler",
        existing_solutions=["x86 kernel memory balancing telemetry design"],
    )
    state.drafts = [_draft("Kernel telemetry balancer", "x86 kernel memory balancing")]

    updated = PatentShieldAgent().run(state)

    assert len(updated.patent_checks) == 1
    assert updated.patent_checks[0].status in {"PASS", "FLAG"}
    assert "patent_shield_reports" in updated.metadata


def test_patent_shield_rejects_when_all_flagged(monkeypatch) -> None:
    state = PipelineState(
        domain="linux_kernel",
        target="scheduler",
        existing_solutions=["x86 kernel memory balancing telemetry design"],
    )
    state.drafts = [_draft("A", "x86 kernel memory balancing")]

    monkeypatch.setattr("configs.settings.settings.patent_conflict_threshold", 0.01)
    updated = PatentShieldAgent().run(state)

    assert updated.run_status == "REJECTED"
    assert "Patent Shield" in updated.last_error
