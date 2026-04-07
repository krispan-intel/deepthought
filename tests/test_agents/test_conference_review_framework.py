from __future__ import annotations

from agents.maverick import MaverickAgent
from agents.reality_checker import RealityCheckerAgent
from agents.state import CritiqueResult


def test_conference_feedback_aggregation_counts_and_points() -> None:
    critiques = [
        CritiqueResult(verdict="APPROVE", rationale="ok", required_revisions=["none"]),
        CritiqueResult(verdict="REVISE", rationale="fix", required_revisions=["tighten locking"]),
        CritiqueResult(verdict="REJECT", rationale="bad", required_revisions=["remove fictional ABI"], fatal_flaw="fictional ABI"),
    ]

    feedback = RealityCheckerAgent._build_conference_feedback(critiques)

    assert feedback["round_size"] == 3
    assert feedback["approve_count"] == 1
    assert feedback["revise_count"] == 1
    assert feedback["reject_count"] == 1
    assert feedback["fatal_count"] == 1
    assert "tighten locking" in "\n".join(feedback["top_revision_points"])


def test_maverick_formats_conference_feedback() -> None:
    text = MaverickAgent._format_conference_feedback(
        {
            "approve_count": 1,
            "revise_count": 2,
            "reject_count": 0,
            "fatal_count": 1,
            "top_revision_points": ["tighten locking", "clarify fallback"],
        }
    )

    assert "approve=1" in text
    assert "revise=2" in text
    assert "tighten locking" in text
