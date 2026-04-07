"""
agents/state.py

Shared state for DeepThought multi-agent pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4


@dataclass
class DraftIdea:
    title: str
    one_liner: str
    novelty_thesis: str
    feasibility_thesis: str
    market_thesis: str
    why_now: str
    problem_statement: str
    prior_art_gap: str
    proposed_invention: str
    architecture_overview: str
    implementation_plan: str
    validation_plan: str
    draft_claims: List[str] = field(default_factory=list)
    risks_and_mitigations: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)

    innovation: int = 3
    implementation_difficulty: int = 3
    commercial_value: int = 3
    technical_risk: int = 3
    prior_art_conflict_risk: int = 3


@dataclass
class CritiqueResult:
    verdict: str
    rationale: str
    required_revisions: List[str] = field(default_factory=list)
    confidence: float = 0.5
    fatal_flaw: str = ""


@dataclass
class DebateResult:
    final_verdict: str
    synthesis: str
    winning_title: str
    confidence: float


@dataclass
class VoidStatus:
    void_id: str
    label: str
    mmr_score: float
    relevance_score: float
    novelty_score: float
    status: str = "DISCOVERED"


@dataclass
class TIDStatus:
    draft_index: int
    title: str
    status: str = "DRAFTED"
    last_error: str = ""
    output_markdown: str = ""
    output_html: str = ""
    output_docx: str = ""
    output_pdf: str = ""


@dataclass
class PatentCheckResult:
    draft_index: int
    status: str
    conflict_score: float
    rationale: str
    prior_art_hits: List[str] = field(default_factory=list)


@dataclass
class PipelineState:
    domain: str
    target: str
    run_id: str = field(default_factory=lambda: f"run-{uuid4().hex[:12]}")
    existing_solutions: List[str] = field(default_factory=list)
    collection_names: List[str] = field(default_factory=list)
    domain_filter: Optional[str] = None
    lambda_val: float = 0.7

    topological_void_context: str = ""
    drafts: List[DraftIdea] = field(default_factory=list)
    critiques: List[CritiqueResult] = field(default_factory=list)
    revisions: int = 0
    debate_result: Optional[DebateResult] = None
    selected_draft_index: int = 0
    patent_checks: List[PatentCheckResult] = field(default_factory=list)
    void_statuses: List[VoidStatus] = field(default_factory=list)
    tid_statuses: List[TIDStatus] = field(default_factory=list)
    run_status: str = "PENDING"
    failed_stages: List[str] = field(default_factory=list)
    last_error: str = ""

    output_paths: Dict[str, str] = field(default_factory=dict)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
