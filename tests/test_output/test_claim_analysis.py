from __future__ import annotations

from output.claim_analysis import assess_claims


def test_assess_claims_detects_conflict_hits() -> None:
    claims = [
        "A kernel scheduler method comprising cache pressure feedback balancing",
        "A lock-free ring buffer for trace transport",
    ]
    prior = [
        "cache pressure feedback balancing in linux scheduler",
        "userspace lock free queue design",
    ]

    results = assess_claims(claims=claims, prior_art_corpus=prior, conflict_threshold=0.3)

    assert len(results) == 2
    assert results[0].conflict_score > 0
    assert results[0].conflict_hits
    assert 0.0 < results[0].confidence <= 0.98


def test_assess_claims_penalizes_hedged_text() -> None:
    claims = ["A method that could possibly improve scheduling maybe"]
    prior = []
    results = assess_claims(claims=claims, prior_art_corpus=prior)

    assert len(results) == 1
    assert results[0].confidence < 0.7
