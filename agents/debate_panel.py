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
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List

from loguru import logger

from configs.settings import settings

from agents.json_parser import robust_json_parse
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

        # Check if Claude Agent proxy mode is enabled
        if self._should_use_claude_proxy():
            return self._delegate_to_claude_agent(state)

        draft_blob = self._format_drafts(state)

        _specialist_defs = [
            (
                "kernel_hardliner",
                "Kernel Hardliner",
                settings.debate_code_expert_model,
                (
                    "You are The Kernel Hardliner. Focus on Linux kernel implementation correctness, "
                    "locking and concurrency validity. Reject unsafe ideas."
                ),
            ),
            (
                "prior_art_shark",
                "Prior-Art Shark",
                settings.debate_deep_thinker_model,
                "You are The Prior-Art Shark. Focus on novelty, non-obviousness, and overlap risk with known work.",
            ),
            (
                "intel_strategist",
                "Intel Strategist",
                settings.debate_deep_thinker_model,
                "You are The Intel Strategist. Focus on x86 strategic value, Xeon competitiveness, and HW/SW co-design leverage.",
            ),
            (
                "security_guardian",
                "Security Guardian",
                settings.debate_code_expert_model,
                "You are The Security and Stability Guardian. Focus on TAA/side-channel risk, crash risk, and compatibility guarantees.",
            ),
        ]

        # Enforce queue depth limit for debate panel parallelism
        if len(_specialist_defs) > settings.max_debate_queue_depth:
            raise RuntimeError(
                f"Debate panel specialist count ({len(_specialist_defs)}) exceeds "
                f"max_debate_queue_depth ({settings.max_debate_queue_depth})"
            )

        with ThreadPoolExecutor(max_workers=len(_specialist_defs)) as executor:
            futures = {
                name: executor.submit(
                    self._specialist_review,
                    role=role,
                    model=model,
                    system_prompt=prompt,
                    draft_blob=draft_blob,
                )
                for name, role, model, prompt in _specialist_defs
            }
            reports = {name: fut.result() for name, fut in futures.items()}

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

    def extract_revision_feedback(self, state: PipelineState) -> Dict[str, Any]:
        """
        Extract actionable revision feedback from debate panel specialist reviews.

        Returns structured feedback that Maverick can use to improve drafts.
        """
        if not state.debate_result:
            return {}

        committee_reports = state.metadata.get("committee_reports", {})
        if not committee_reports:
            return {}

        feedback = {
            "final_verdict": state.debate_result.final_verdict,
            "chairman_synthesis": state.debate_result.synthesis,
            "confidence": state.debate_result.confidence,
            "reviewer_feedback": []
        }

        # Extract key concerns from each specialist
        for reviewer_name, review in committee_reports.items():
            status = review.get("status", "REVISE")
            if status in ["REVISE", "REJECT"]:
                issues = review.get("issues", [])
                fatal_flaw = review.get("fatal_flaw", "")

                # Truncate long comments
                key_concerns = "; ".join(issues[:3]) if issues else ""
                if len(key_concerns) > 500:
                    key_concerns = key_concerns[:500] + "..."

                # Extract actionable suggestions if present
                actionable = ""
                for issue in issues:
                    if "suggest" in issue.lower() or "should" in issue.lower() or "must" in issue.lower():
                        actionable = issue[:300]
                        break

                feedback["reviewer_feedback"].append({
                    "role": reviewer_name,
                    "status": status,
                    "score": review.get("score", 2),
                    "fatal_flaw": fatal_flaw[:200] if fatal_flaw else "",
                    "key_concerns": key_concerns,
                    "actionable_suggestions": actionable
                })

        return feedback

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

CRITICAL JSON SCHEMA REQUIREMENTS:
If you assign status 'REVISE' or 'REJECT', you ABSOLUTELY MUST provide at least 3 specific, actionable technical critiques in the "issues" array.
DO NOT return an empty array []. An empty issues array will cause the revision feedback loop to fail.

Example of VALID issues array:
"issues": [
  "The proposed use of RCU read lock is invalid here because function X can sleep",
  "You must define a concrete data structure for the abstraction layer between eBPF and CXL",
  "The synchronization model violates scheduler correctness under concurrent wakeups"
]

If you assign status 'APPROVE', you may provide an empty issues array or constructive suggestions for future improvement.
""".strip()

        raw = self.llm.chat(
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.5,
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
        def _check_one(name: str, report: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
            queries = report.get("fact_check_queries", [])
            if not queries:
                return name, {}
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
            return name, query_results

        checks: Dict[str, Any] = {}
        # Cap fact-check parallelism to queue depth limit
        max_workers = min(len(reports) or 1, settings.max_debate_queue_depth)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                name: executor.submit(_check_one, name, report)
                for name, report in reports.items()
            }
            for name, fut in futures.items():
                _, result = fut.result()
                checks[name] = result
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

        if fatal:
            reason = "; ".join(fatal)
            return {
                "final_verdict": "REJECT",
                "synthesis": reason,
                "confidence": 0.95,
                "rule_trigger": "fatal_flaw_reject",
                "reviewer_statuses": statuses,
            }

        reject_count = sum(1 for s in statuses if s == "REJECT")
        if reject_count >= 2:
            return {
                "final_verdict": "REJECT",
                "synthesis": f"Majority committee rejection ({reject_count}/{len(statuses)} REJECT, no fatal flaw stated)",
                "confidence": 0.9,
                "rule_trigger": "majority_reject",
                "reviewer_statuses": statuses,
            }

        if yellow_cards >= 3:
            return {
                "final_verdict": "REJECT",
                "synthesis": f"Rejected by yellow-card rule (yellow_cards={yellow_cards})",
                "confidence": 0.9,
                "rule_trigger": "yellow_card_reject",
                "reviewer_statuses": statuses,
            }

        avg_score = sum(scores) / len(scores) if scores else 0.0
        approve_count = sum(1 for s in statuses if s == "APPROVE")

        # Full approval: all APPROVE and avg score >= 4
        if approve_count == len(statuses) and avg_score >= 4.0:
            return {
                "final_verdict": "APPROVE",
                "synthesis": f"Full committee approval (avg_score={avg_score:.1f}).",
                "confidence": 0.92,
                "rule_trigger": "full_committee_approval",
                "reviewer_statuses": statuses,
            }

        # Majority approval: >=3 of 4 APPROVE, avg score >= 3.5, no REJECT
        if approve_count >= 3 and avg_score >= 3.5 and reject_count == 0:
            return {
                "final_verdict": "APPROVE",
                "synthesis": f"Majority committee approval ({approve_count}/{len(statuses)} APPROVE, avg_score={avg_score:.1f}).",
                "confidence": 0.80,
                "rule_trigger": "majority_approval",
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
        """Parse JSON from Debate Panel output with fallback to default verdict."""
        try:
            return robust_json_parse(
                text,
                llm_repair_callback=None,
                agent_name="DebatePanel",
            )
        except ValueError:
            # Fallback to REVISE verdict if parse fails
            return {
                "final_verdict": "REVISE",
                "winning_title": "",
                "synthesis": text[:1000],
                "confidence": 0.4,
            }

    def _should_use_claude_proxy(self) -> bool:
        """Check if Claude Agent proxy mode should be used."""
        # Enable proxy mode if any debate model starts with "claude-"
        models = [
            settings.debate_code_expert_model,
            settings.debate_deep_thinker_model,
            settings.debate_judge_model,
        ]
        return any(m.startswith("claude-") for m in models)

    def _delegate_to_claude_agent(self, state: PipelineState) -> PipelineState:
        """Save drafts for Claude Agent review and mark as pending."""
        import json
        from pathlib import Path
        from datetime import datetime

        pending_dir = Path("data/pending_reviews")
        pending_dir.mkdir(parents=True, exist_ok=True)

        # Create review request
        request = {
            "run_id": state.run_id,
            "timestamp": datetime.now().isoformat(),
            "domain": state.domain,
            "target": state.target,
            "drafts": [
                {
                    "index": i,
                    "title": d.title,
                    "one_liner": d.one_liner,
                    "novelty_thesis": d.novelty_thesis,
                    "feasibility_thesis": d.feasibility_thesis,
                    "market_thesis": d.market_thesis,
                    "why_now": d.why_now,
                    "problem_statement": d.problem_statement,
                    "prior_art_gap": d.prior_art_gap,
                    "proposed_invention": d.proposed_invention,
                    "architecture_overview": d.architecture_overview,
                    "implementation_plan": d.implementation_plan,
                    "validation_plan": d.validation_plan,
                    "draft_claims": d.draft_claims,
                    "risks_and_mitigations": d.risks_and_mitigations,
                    "references": d.references,
                }
                for i, d in enumerate(state.drafts)
            ],
        }

        # Save to pending directory
        review_file = pending_dir / f"{state.run_id}.json"
        with open(review_file, "w", encoding="utf-8") as f:
            json.dump(request, f, indent=2, ensure_ascii=False)

        logger.info(
            "Debate Panel delegated to Claude Agent | run_id={} | file={}",
            state.run_id,
            review_file,
        )

        # Mark as pending Claude review
        state.metadata["claude_agent_review_pending"] = True
        state.metadata["claude_agent_review_file"] = str(review_file)
        state.debate_result = DebateResult(
            final_verdict="PENDING_CLAUDE_REVIEW",
            synthesis="Waiting for Claude Agent manual review",
            winning_title="",
            confidence=0.0,
        )

        return state
