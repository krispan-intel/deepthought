"""
agents/debate_panel.py

Virtual Patent Committee:
- 4 specialist reviewers (kernel, prior-art, strategy, security)
- optional fact-check retrieval for contested claims
- chairman synthesis with deterministic veto rules
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from loguru import logger

from configs.settings import settings

from agents.llm_client import LLMClient
from agents.state import DebateResult, PipelineState
from vectordb.store import DeepThoughtVectorStore


class DebatePanelAgent:
    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or LLMClient()
        self.store = DeepThoughtVectorStore()

    def run(self, state: PipelineState) -> PipelineState:
        if not state.drafts:
            state.metadata["judge_trace"] = {
                "final_verdict": "REJECT",
                "reason": "No drafts available for debate.",
                "rule_trigger": "empty_drafts",
            }
            state.debate_result = DebateResult(
                final_verdict="REJECT",
                synthesis="No drafts available for debate.",
                winning_title="",
                confidence=0.0,
            )
            return state

        draft_blob = self._format_drafts(state)

        reports = {
            "kernel_hardliner": self._specialist_review(
                role="Kernel Hardliner",
                model=settings.debate_code_expert_model,
                system_prompt=(
                    "You are The Kernel Hardliner. Focus on Linux kernel implementation correctness, "
                    "locking and concurrency validity. Reject unsafe ideas."
                ),
                draft_blob=draft_blob,
            ),
            "prior_art_shark": self._specialist_review(
                role="Prior-Art Shark",
                model=settings.debate_deep_thinker_model,
                system_prompt=(
                    "You are The Prior-Art Shark. Focus on novelty, non-obviousness, and overlap risk with known work."
                ),
                draft_blob=draft_blob,
            ),
            "intel_strategist": self._specialist_review(
                role="Intel Strategist",
                model=settings.debate_deep_thinker_model,
                system_prompt=(
                    "You are The Intel Strategist. Focus on x86 strategic value, Xeon competitiveness, and HW/SW co-design leverage."
                ),
                draft_blob=draft_blob,
            ),
            "security_guardian": self._specialist_review(
                role="Security Guardian",
                model=settings.debate_code_expert_model,
                system_prompt=(
                    "You are The Security and Stability Guardian. Focus on TAA/side-channel risk, crash risk, and compatibility guarantees."
                ),
                draft_blob=draft_blob,
            ),
        }

        fact_checks = self._run_fact_checks(reports)

        chairman_prompt = f"""
You are the Chairman of the Intel DeepThought Patent Committee.

Consensus rules:
- CRITICAL REJECT: if any specialist reports status REJECT or fatal flaw.
- REVISE: if no fatal flaws but any score < 4 or unresolved major issues.
- APPROVE: only if all 4 specialists score >= 4 and no fatal flaw.

Specialist reports (JSON):
{json.dumps(reports, ensure_ascii=False, indent=2)}

Fact-check notes:
{json.dumps(fact_checks, ensure_ascii=False, indent=2)}

Return strict JSON:
{{
  "final_verdict": "APPROVE|REVISE|REJECT",
  "winning_title": "string",
  "synthesis": "string",
  "confidence": 0.0
}}
""".strip()

        chairman = self.llm.chat(
            model=settings.debate_judge_model,
            system_prompt="Be strict, concise, and enforce the committee rules.",
            user_prompt=chairman_prompt,
            temperature=0.2,
        )
        chairman_result = self._parse_json(chairman)

        deterministic = self._deterministic_verdict(reports)
        final_verdict = deterministic["final_verdict"]
        synthesis = deterministic["synthesis"]
        confidence = deterministic["confidence"]
        winning_title = str(chairman_result.get("winning_title", "")).strip()
        if not winning_title and state.drafts:
            winning_title = state.drafts[0].title

        state.metadata["committee_reports"] = reports
        state.metadata["committee_fact_checks"] = fact_checks
        state.metadata["committee_review_log"] = self._build_committee_review_log(reports, fact_checks)
        state.metadata["judge_trace"] = {
            "chairman_result": chairman_result,
            "deterministic_rule": deterministic,
            "final_verdict": final_verdict,
            "winning_title": winning_title,
        }

        for reviewer in state.metadata["committee_review_log"]:
            logger.info(
                "Committee review | run_id={} | reviewer={} | status={} | score={} | issue={}",
                state.run_id,
                reviewer["reviewer"],
                reviewer["status"],
                reviewer["score"],
                reviewer["top_issue"],
            )
        logger.info(
            "Judge decision | run_id={} | verdict={} | title={} | reason={}",
            state.run_id,
            final_verdict,
            winning_title,
            synthesis[:240],
        )

        if final_verdict == "REJECT":
            state.run_status = "REJECTED"
            state.last_error = synthesis

        state.debate_result = DebateResult(
            final_verdict=final_verdict,
            winning_title=winning_title,
            synthesis=synthesis,
            confidence=confidence,
        )

        selected = 0
        for i, d in enumerate(state.drafts):
            if d.title.strip().lower() == state.debate_result.winning_title.strip().lower():
                selected = i
                break
        state.selected_draft_index = selected
        return state

    def _specialist_review(self, role: str, model: str, system_prompt: str, draft_blob: str) -> Dict[str, Any]:
        user_prompt = f"""
Role: {role}

Review all candidate drafts below and pick the strongest one for your report.

Drafts:
{draft_blob}

Return strict JSON:
{{
  "preferred_title": "string",
  "status": "APPROVE|REVISE|REJECT",
  "fatal_flaw": "string or empty",
  "score": 1,
  "issues": ["string"],
  "yellow_cards": 0,
  "fact_check_queries": ["kernel symbol or file path to verify"]
}}
""".strip()

        raw = self.llm.chat(
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
        )
        data = self._parse_json(raw)
        status = str(data.get("status", "REVISE")).upper().strip()
        if status not in {"APPROVE", "REVISE", "REJECT"}:
            status = "REVISE"

        return {
            "preferred_title": str(data.get("preferred_title", "")).strip(),
            "status": status,
            "fatal_flaw": str(data.get("fatal_flaw", "")).strip(),
            "score": self._clamp_score(data.get("score", 2)),
            "issues": [str(x) for x in data.get("issues", [])][:10],
            "yellow_cards": max(0, int(data.get("yellow_cards", 0) or 0)),
            "fact_check_queries": [str(x) for x in data.get("fact_check_queries", [])][:6],
        }

    @staticmethod
    def _build_committee_review_log(
        reports: Dict[str, Dict[str, Any]],
        fact_checks: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        review_log: List[Dict[str, Any]] = []
        for reviewer, report in reports.items():
            issues = [str(item) for item in report.get("issues", []) if str(item).strip()]
            review_log.append(
                {
                    "reviewer": reviewer,
                    "preferred_title": str(report.get("preferred_title", "")).strip(),
                    "status": str(report.get("status", "REVISE")).strip(),
                    "score": int(report.get("score", 2) or 2),
                    "fatal_flaw": str(report.get("fatal_flaw", "")).strip(),
                    "issues": issues,
                    "top_issue": issues[0] if issues else "",
                    "yellow_cards": int(report.get("yellow_cards", 0) or 0),
                    "fact_check_queries": [str(item) for item in report.get("fact_check_queries", [])],
                    "fact_checks": fact_checks.get(reviewer, {}),
                }
            )
        return review_log

    def _run_fact_checks(self, reports: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        checks: Dict[str, Any] = {}
        for name, report in reports.items():
            queries = report.get("fact_check_queries", [])
            if not queries:
                continue

            query_results: Dict[str, List[Dict[str, Any]]] = {}
            for q in queries[:3]:
                try:
                    hits = self.store.query(query_text=q, n_results=2)
                    query_results[q] = [
                        {
                            "label": h.to_tech_vector().label,
                            "similarity": round(float(h.similarity), 4),
                            "source": str(h.document.metadata.get("file_path", "")),
                        }
                        for h in hits
                    ]
                except Exception as exc:
                    query_results[q] = [{"error": str(exc)}]

            checks[name] = query_results
        return checks

    @staticmethod
    def _clamp_score(value: Any) -> int:
        try:
            score = int(value)
        except (TypeError, ValueError):
            score = 2
        return max(1, min(5, score))

    @staticmethod
    def _deterministic_verdict(reports: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        statuses = [r.get("status", "REVISE") for r in reports.values()]
        fatal = [r.get("fatal_flaw", "").strip() for r in reports.values() if r.get("fatal_flaw", "").strip()]
        scores = [int(r.get("score", 2) or 2) for r in reports.values()]
        yellow_cards = sum(int(r.get("yellow_cards", 0) or 0) for r in reports.values())

        if any(s == "REJECT" for s in statuses) or fatal:
            reason = "; ".join(fatal) if fatal else "Committee fatal rejection"
            return {
                "final_verdict": "REJECT",
                "synthesis": reason,
                "confidence": 0.95,
                "rule_trigger": "fatal_reject",
                "reviewer_statuses": statuses,
            }

        if yellow_cards >= 2:
            return {
                "final_verdict": "REJECT",
                "synthesis": f"Rejected by yellow-card rule (yellow_cards={yellow_cards})",
                "confidence": 0.9,
                "rule_trigger": "yellow_card_reject",
                "reviewer_statuses": statuses,
            }

        if all(score >= 4 for score in scores) and all(s == "APPROVE" for s in statuses):
            return {
                "final_verdict": "APPROVE",
                "synthesis": "All specialists approved with score >= 4.",
                "confidence": 0.9,
                "rule_trigger": "full_committee_approval",
                "reviewer_statuses": statuses,
            }

        return {
            "final_verdict": "REVISE",
            "synthesis": "Committee requested revision due to unresolved issues.",
            "confidence": 0.7,
            "rule_trigger": "revision_required",
            "reviewer_statuses": statuses,
        }

    def _format_drafts(self, state: PipelineState) -> str:
        lines: List[str] = []
        for i, d in enumerate(state.drafts, start=1):
            lines.extend(
                [
                    f"Draft #{i}",
                    f"Title: {d.title}",
                    f"One-liner: {d.one_liner}",
                    f"Novelty: {d.novelty_thesis}",
                    f"Feasibility: {d.feasibility_thesis}",
                    f"Market: {d.market_thesis}",
                    f"Problem: {d.problem_statement}",
                    f"Proposed Invention: {d.proposed_invention}",
                    f"Architecture: {d.architecture_overview}",
                    f"Implementation Plan: {d.implementation_plan}",
                    f"Claims: {d.draft_claims}",
                    "",
                ]
            )
        return "\n".join(lines)

    def _parse_json(self, text: str) -> Dict:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        fenced = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", text)
        if fenced:
            return json.loads(fenced.group(1))

        braces = re.search(r"(\{[\s\S]*\})", text)
        if braces:
            return json.loads(braces.group(1))

        return {
            "final_verdict": "REVISE",
            "winning_title": "",
            "synthesis": text[:1000],
            "confidence": 0.4,
        }
