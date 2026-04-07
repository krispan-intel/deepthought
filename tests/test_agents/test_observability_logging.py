from __future__ import annotations

import json
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Dict, List

from agents.debate_panel import DebatePanelAgent
from agents.forager import ForagerAgent
from agents.maverick import MaverickAgent
from agents.reality_checker import RealityCheckerAgent
from agents.state import DraftIdea, PipelineState


@dataclass
class _FakeCandidate:
    id: str
    label: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class _FakeVoid:
    candidate: _FakeCandidate
    mmr_score: float
    relevance_score: float
    novelty_score: float
    domain_score: float
    pairwise_score: float
    marginality_low: float
    marginality_high: float
    sparse_overlap_count: int
    sparse_anchor_tokens: tuple[str, ...]


class _FakeLandscape:
    def __init__(self) -> None:
        self.target = SimpleNamespace(label="linux_kernel/scheduler")
        self.domain = "linux_kernel"
        self.lambda_used = 0.7
        self.voids = [
            _FakeVoid(
                candidate=_FakeCandidate(
                    id="void-1",
                    label="per-cpu scheduler telemetry <> lock-aware wakeup routing",
                    metadata={
                        "anchor_a_label": "per-cpu scheduler telemetry",
                        "anchor_b_label": "lock-aware wakeup routing",
                    },
                ),
                mmr_score=0.82,
                relevance_score=0.77,
                novelty_score=0.69,
                domain_score=0.77,
                pairwise_score=0.52,
                marginality_low=0.31,
                marginality_high=0.63,
                sparse_overlap_count=0,
                sparse_anchor_tokens=("sched", "wakeup", "telemetry"),
            )
        ]

    def to_maverick_context(self) -> str:
        return "Void #1: scheduler telemetry + wakeup routing"


class _FakeStore:
    def find_topological_voids(self, **kwargs) -> _FakeLandscape:
        return _FakeLandscape()


class _FakeLLM:
    def __init__(self, responses: List[str]) -> None:
        self.responses = list(responses)

    def chat(self, **kwargs) -> str:
        if not self.responses:
            raise AssertionError("No fake LLM responses remaining")
        return self.responses.pop(0)

    def chat_reality_checker(self, **kwargs) -> str:
        return self.chat(**kwargs)


class _FakeDebateStore:
    def query(self, query_text: str, n_results: int = 2):
        return [
            SimpleNamespace(
                similarity=0.91,
                collection=SimpleNamespace(value="kernel_source"),
                document=SimpleNamespace(
                    metadata={"file_path": "kernel/sched/core.c"},
                    to_tech_vector=lambda: SimpleNamespace(label="sched/core.c::wake_affine"),
                ),
            )
        ]


def _draft(title: str = "Telemetry-guided wake routing") -> DraftIdea:
    return DraftIdea(
        title=title,
        one_liner="Adapt scheduler wakeup routing with per-cpu telemetry.",
        novelty_thesis="Novel cross between telemetry and wake routing.",
        feasibility_thesis="Feasible with sched domain hooks.",
        market_thesis="Improves Xeon latency stability.",
        why_now="Modern socket contention makes this timely.",
        problem_statement="Wakeups ignore transient telemetry.",
        prior_art_gap="Current approaches do not fuse these signals.",
        proposed_invention="Telemetry-aware wake target selection.",
        architecture_overview="producer -> telemetry -> scheduler",
        implementation_plan="Patch kernel/sched/core.c and tracepoints.",
        validation_plan="Measure wakeup latency under load.",
        draft_claims=["Claim 1", "Claim 2", "Claim 3"],
    )


def test_forager_records_triad_observations() -> None:
    state = PipelineState(domain="linux_kernel", target="sched latency")

    updated = ForagerAgent(store=_FakeStore()).run(state, top_k=1)

    report = updated.metadata["forager_observations"]
    assert report["void_count"] == 1
    assert report["top_voids"][0]["anchor_a"] == "per-cpu scheduler telemetry"
    assert report["top_voids"][0]["anchor_b"] == "lock-aware wakeup routing"
    assert report["top_voids"][0]["domain_score"] == 0.77
    assert report["top_voids"][0]["pairwise_score"] == 0.52


def test_maverick_records_empty_generation_reason() -> None:
    llm = _FakeLLM([json.dumps({"drafts": []})])
    state = PipelineState(domain="linux_kernel", target="sched latency")
    state.topological_void_context = "Void #1"

    updated = MaverickAgent(llm=llm).run(state, n_drafts=2)

    report = updated.metadata["maverick_generation"]
    assert report["status"] == "EMPTY"
    assert report["produced_drafts"] == 0
    assert "zero valid drafts" in report["reason"].lower()


def test_maverick_parser_handles_wrapped_json_with_footer() -> None:
    agent = MaverickAgent(llm=_FakeLLM([]))
    wrapped = (
        "Sure, here is the output:\n"
        "```json\n"
        "{\"drafts\": [{\"title\": \"A\", \"one_liner\": \"B\", \"scores\": {}, \"tid_detail\": {}}]}\n"
        "```\n"
        "Total usage est: 123 tokens"
    )

    payload = agent._parse_json(wrapped)

    assert isinstance(payload, dict)
    assert payload.get("drafts", [{}])[0].get("title") == "A"


def test_maverick_parser_accepts_list_payload_with_drafts_dict() -> None:
    agent = MaverickAgent(llm=_FakeLLM([]))
    text = '[{"meta":"x"}, {"drafts": []}]'

    payload = agent._parse_json(text)

    assert isinstance(payload, dict)
    assert "drafts" in payload


def test_reality_checker_records_review_and_revision_trace() -> None:
    critique_response = json.dumps(
        {
            "status": "REVISE",
            "fatal_flaw": "",
            "scorecard": {"innovation": 4, "feasibility": 3, "prior_art_risk": 2},
            "hallucinations_found": ["symbol foo_bar_sched() is not real"],
            "actionable_feedback": "Cite real scheduler symbols and add fallback path.",
            "approved": False,
        }
    )
    revision_response = json.dumps(
        {
            "title": "Telemetry-guided wake routing v2",
            "one_liner": "Use real scheduler telemetry hooks to route wakeups safely.",
            "novelty_thesis": "Novel but grounded revision.",
            "feasibility_thesis": "Uses real hooks and fallback logic.",
            "market_thesis": "Improves datacenter latency.",
            "why_now": "Pressure from mixed workloads.",
            "scores": {
                "innovation": 4,
                "implementation_difficulty": 3,
                "commercial_value": 4,
                "technical_risk": 2,
                "prior_art_conflict_risk": 2
            },
            "tid_detail": {
                "problem_statement": "Wakeups miss telemetry windows.",
                "prior_art_gap": "No telemetry-locked wake routing.",
                "proposed_invention": "Grounded wake routing revision.",
                "architecture_overview": "tracepoint -> policy -> wake target",
                "implementation_plan": "Use kernel/sched/core.c and trace hooks.",
                "validation_plan": "Test with wake storms.",
                "draft_claims": ["Claim 1", "Claim 2", "Claim 3"],
                "risks_and_mitigations": ["Fallback to default wake path"],
                "references": ["kernel/sched/core.c"]
            }
        }
    )
    agent = RealityCheckerAgent(llm=_FakeLLM([critique_response, revision_response]))
    state = PipelineState(domain="linux_kernel", target="sched latency")
    state.drafts = [_draft()]

    updated = agent.run(state)
    updated = agent.revise_drafts(updated)

    trace = updated.metadata["conference_review_trace"]
    assert trace[0]["event"] == "review_round"
    assert trace[0]["items"][0]["verdict"] == "REVISE"
    assert "fallback path" in trace[0]["items"][0]["reason"]
    assert trace[1]["event"] == "maverick_revision"
    assert trace[1]["items"][0]["status"] == "REVISED"
    assert trace[1]["items"][0]["after_title"] == "Telemetry-guided wake routing v2"


def test_debate_panel_records_committee_and_judge_trace() -> None:
    specialist = json.dumps(
        {
            "preferred_title": "Telemetry-guided wake routing",
            "status": "APPROVE",
            "fatal_flaw": "",
            "score": 4,
            "issues": ["Clarify tracepoint overhead"],
            "yellow_cards": 0,
            "fact_check_queries": ["wake_affine"],
        }
    )
    chairman = json.dumps(
        {
            "final_verdict": "APPROVE",
            "winning_title": "Telemetry-guided wake routing",
            "synthesis": "All reviewers aligned after overhead clarification.",
            "confidence": 0.93,
        }
    )
    agent = DebatePanelAgent(llm=_FakeLLM([specialist, specialist, specialist, specialist, chairman]))
    agent.store = _FakeDebateStore()
    state = PipelineState(domain="linux_kernel", target="sched latency")
    state.drafts = [_draft()]

    updated = agent.run(state)

    assert len(updated.metadata["committee_review_log"]) == 4
    assert updated.metadata["committee_review_log"][0]["top_issue"] == "Clarify tracepoint overhead"
    assert updated.metadata["judge_trace"]["final_verdict"] == "APPROVE"
    assert updated.metadata["judge_trace"]["deterministic_rule"]["rule_trigger"] == "full_committee_approval"