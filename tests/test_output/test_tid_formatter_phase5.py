from __future__ import annotations

from output.tid_formatter import TIDDetail, TIDReport, TIDScorecard, TIDSummary


def _sample_report() -> TIDReport:
    return TIDReport(
        tid_id="TID-TEST-001",
        title="Phase5 Test",
        domain="linux_kernel",
        target="scheduler",
        summary=TIDSummary(
            one_liner="one",
            novelty_thesis="novel",
            feasibility_thesis="feasible",
            market_thesis="market",
            why_now="now",
        ),
        scorecard=TIDScorecard(
            innovation=4,
            implementation_difficulty=3,
            commercial_value=4,
            technical_risk=3,
            prior_art_conflict_risk=2,
        ),
        detail=TIDDetail(
            problem_statement="p",
            prior_art_gap="g",
            proposed_invention="i",
            architecture_overview="a",
            implementation_plan="impl",
            validation_plan="val",
            draft_claims=["claim one"],
            claim_confidence=["Claim 1: confidence=0.81, conflict_score=0.20"],
            prior_art_conflicts=["Claim 1 conflicts with: ref A"],
            risks_and_mitigations=["r"],
            references=["ref"],
        ),
    )


def test_markdown_contains_phase5_sections() -> None:
    report = _sample_report()
    markdown = report.to_markdown()

    assert "3.10 Claim Confidence Scores" in markdown
    assert "3.11 Prior-Art Conflict Detector" in markdown


def test_save_extended_always_writes_md_html(tmp_path) -> None:
    report = _sample_report()
    outputs = report.save_extended(tmp_path, base_name="phase5")

    assert outputs["markdown"].endswith("phase5.md")
    assert outputs["html"].endswith("phase5.html")
