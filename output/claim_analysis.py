"""
output/claim_analysis.py

Phase 5 helpers:
- Prior-art conflict detection per claim.
- Confidence scoring per claim.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence


@dataclass
class ClaimAssessment:
    claim: str
    confidence: float
    conflict_score: float
    conflict_hits: List[str]


HEDGE_TOKENS = {
    "maybe", "possibly", "could", "might", "approximately", "roughly", "optionally"
}


def assess_claims(
    claims: Sequence[str],
    prior_art_corpus: Iterable[str],
    conflict_threshold: float = 0.42,
) -> List[ClaimAssessment]:
    corpus = [str(item).strip() for item in prior_art_corpus if str(item).strip()]
    assessments: List[ClaimAssessment] = []

    for claim in claims:
        text = str(claim).strip()
        claim_tokens = _tokenize(text)
        best_score = 0.0
        hits: List[str] = []

        for item in corpus:
            score = _jaccard(claim_tokens, _tokenize(item))
            if score > best_score:
                best_score = score
            if score >= conflict_threshold:
                hits.append(item)

        confidence = _claim_confidence(text=text, conflict_score=best_score)
        assessments.append(
            ClaimAssessment(
                claim=text,
                confidence=round(confidence, 3),
                conflict_score=round(best_score, 3),
                conflict_hits=hits[:3],
            )
        )

    return assessments


def _claim_confidence(text: str, conflict_score: float) -> float:
    tokens = _tokenize(text)
    if not tokens:
        return 0.1

    len_factor = min(1.0, 0.35 + len(tokens) / 28.0)
    hedge_penalty = 0.0
    if any(tok in HEDGE_TOKENS for tok in tokens):
        hedge_penalty += 0.12

    structural_bonus = 0.1 if ("wherein" in tokens or "comprising" in tokens) else 0.0
    conflict_penalty = min(0.5, conflict_score * 0.75)
    score = len_factor + structural_bonus - hedge_penalty - conflict_penalty
    return max(0.05, min(0.98, score))


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    union = a.union(b)
    if not union:
        return 0.0
    return len(a.intersection(b)) / len(union)


def _tokenize(text: str) -> set[str]:
    normalized = (
        (text or "")
        .lower()
        .replace("/", " ")
        .replace("-", " ")
        .replace(",", " ")
        .replace(".", " ")
        .replace(":", " ")
        .replace(";", " ")
    )
    return {tok for tok in normalized.split() if len(tok) >= 3}
