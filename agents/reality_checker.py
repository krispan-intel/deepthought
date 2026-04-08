"""
agents/reality_checker.py

Reality Checker agent: critique each draft and produce APPROVE/REVISE/REJECT.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from loguru import logger

from configs.settings import settings
from agents.llm_client import LLMClient
from agents.state import CritiqueResult, PipelineState


class RealityCheckerAgent:
    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or LLMClient()

    def run(self, state: PipelineState) -> PipelineState:
        critiques: List[CritiqueResult] = []
        round_trace: List[Dict[str, Any]] = []

        for draft in state.drafts:
            convergence_rule = ""
            if state.revisions >= 2:
                convergence_rule = (
                    " CRITICAL CONVERGENCE RULE: This is revision round "
                    f"{state.revisions + 1}. If the major architectural flaws from "
                    "previous rounds have been addressed, you MUST output APPROVED. "
                    "Do NOT invent new minor nitpicks or move the goalposts. "
                    "If the core concept is physically implementable and the author has "
                    "complied with your previous constraints, output APPROVED and leave "
                    "minor implementation details for the engineer to resolve."
                )
            system_prompt = (
                "You are a senior Intel patent reviewer and Linux kernel architect. "
                "Your goal is to identify technically sound ideas worth patenting and help them improve. "
                "Be rigorous but constructive: prefer REVISE over REJECT whenever the core idea is salvageable. "
                "Reserve REJECT strictly for ideas that are physically impossible, rely on fictional kernel APIs, "
                "or have an unfixable ABI breakage. "
                "Output valid JSON only."
                + convergence_rule
            )
            user_prompt = f"""
OUTPUT FORMAT (respond with ONLY this JSON, no prose before or after):
{{
    "status": "APPROVED|REVISE|REJECT",
    "fatal_flaw": "string or empty — only populate for true showstoppers",
    "scorecard": {{
        "innovation": 1,
        "feasibility": 1,
        "prior_art_risk": 1
    }},
    "hallucinations_found": ["only list fictional kernel symbols or impossible x86 ops"],
    "actionable_feedback": "string — specific, fixable instructions if REVISE",
    "approved": false
}}

Critique this TID draft:

Title: {draft.title}
One-liner: {draft.one_liner}
Novelty thesis: {draft.novelty_thesis}
Feasibility thesis: {draft.feasibility_thesis}
Problem statement: {draft.problem_statement}
Prior-art gap: {draft.prior_art_gap}
Proposed invention: {draft.proposed_invention}
Architecture: {draft.architecture_overview}
Implementation plan: {draft.implementation_plan}
Validation plan: {draft.validation_plan}
Claims: {draft.draft_claims}

Evaluation criteria:
1. Hallucination check: only flag functions or instructions that do not exist (not merely obscure).
2. Domain compliance: x86 plus Linux kernel internals.
3. Patentability: is the core idea non-obvious? Minor prior-art overlap alone is not fatal.
4. Concurrency validity: flag only clear ABBA deadlocks or races, not speculative ones.
5. Hardware reality: TSX/TAA mitigations need acknowledgment but do not need to be fully designed.

Decision policy:
- APPROVED: technically plausible, non-obvious core idea, no showstopper flaw.
- REVISE: promising idea with fixable issues — provide specific actionable_feedback.
- REJECT: only for physically impossible designs, pure fiction, or unfixable ABI breaks.
""".strip()

            raw = self.llm.chat_reality_checker(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.2,
            )
            data = self._parse_json(raw)
            scorecard = data.get("scorecard", {}) if isinstance(data, dict) else {}
            feasibility = self._clamp_star(scorecard.get("feasibility", 2))
            innovation = self._clamp_star(scorecard.get("innovation", 2))
            prior_art_risk = self._clamp_star(scorecard.get("prior_art_risk", 3))
            hallucinations = [str(x) for x in data.get("hallucinations_found", [])]
            status = str(data.get("status", "")).upper().strip()
            fatal_flaw = str(data.get("fatal_flaw", "")).strip()

            if status not in {"APPROVED", "REVISE", "REJECT"}:
                approved = bool(data.get("approved", False)) and feasibility >= 4 and not hallucinations and not fatal_flaw
                status = "APPROVED" if approved else ("REJECT" if feasibility <= 2 or fatal_flaw else "REVISE")

            verdict = "APPROVE" if status == "APPROVED" else status
            feedback = str(data.get("actionable_feedback", "")).strip()
            confidence = min(0.99, max(0.1, (innovation + feasibility + (6 - prior_art_risk)) / 15.0))

            critiques.append(
                CritiqueResult(
                    verdict=verdict,
                    rationale=feedback or "No actionable feedback provided",
                    required_revisions=[feedback] + hallucinations if (feedback or hallucinations) else ["Tighten feasibility and remove hallucinations"],
                    confidence=confidence,
                    fatal_flaw=fatal_flaw,
                )
            )
            round_trace.append(
                {
                    "title": draft.title,
                    "verdict": verdict,
                    "pass": verdict == "APPROVE",
                    "reason": feedback or fatal_flaw or "No actionable feedback provided",
                    "fatal_flaw": fatal_flaw,
                    "hallucinations_found": hallucinations,
                    "required_revisions": [feedback] + hallucinations if (feedback or hallucinations) else ["Tighten feasibility and remove hallucinations"],
                    "confidence": round(confidence, 4),
                }
            )
            logger.info(
                "Reality Checker verdict | run_id={} | title={} | verdict={} | reason={}",
                state.run_id,
                draft.title,
                verdict,
                (feedback or fatal_flaw or "No actionable feedback provided")[:220],
            )

        state.critiques = critiques
        state.metadata["reality_checker_reports"] = round_trace
        state.metadata["conference_review_feedback"] = self._build_conference_feedback(critiques)
        state.metadata.setdefault("conference_review_trace", []).append(
            {
                "event": "review_round",
                "round": state.revisions + 1,
                "items": round_trace,
            }
        )
        return state

    def revise_drafts(self, state: PipelineState) -> PipelineState:
        revised = []
        revision_trace: List[Dict[str, Any]] = []
        for draft, critique in zip(state.drafts, state.critiques):
            if critique.verdict != "REVISE":
                revised.append(draft)
                revision_trace.append(
                    {
                        "before_title": draft.title,
                        "after_title": draft.title,
                        "status": "SKIPPED",
                        "feedback_used": list(critique.required_revisions),
                        "summary": draft.one_liner[:240],
                    }
                )
                continue

            system_prompt = (
                "You are a senior kernel and x86 IP architect acting as both the Inventor and their "
                "Senior IP Advisor. Your previous draft was critiqued. Your advisor has given you a "
                "strict convergence strategy to get this approved:\n"
                "1. CUT THE DEAD WEIGHT: Immediately drop any component the reviewer flagged as "
                "physically impossible, ABI-breaking, or fictional. Do not defend them.\n"
                "2. NARROW THE BOUNDARY: Reframe the invention strictly around the surviving mechanism. "
                "If the reviewer said only one sub-component is interesting, make the ENTIRE draft "
                "focus on that sub-component.\n"
                "3. FORMAT AS AN IP CLAIM: Write a defensible System Architecture specification, "
                "not a software patch. Be precise about data structures, lock ordering, and kernel paths.\n"
                "Output valid JSON only."
            )
            user_prompt = f"""
OUTPUT FORMAT (respond with ONLY this JSON, no prose before or after):
{{
  "strategic_rebuttal": "bullet-point summary of exactly what you dropped and what you narrowed",
  "title": "string",
  "one_liner": "string",
  "novelty_thesis": "string",
  "feasibility_thesis": "string",
  "market_thesis": "string",
  "why_now": "string",
  "scores": {{
    "innovation": 1,
    "implementation_difficulty": 1,
    "commercial_value": 1,
    "technical_risk": 1,
    "prior_art_conflict_risk": 1
  }},
  "tid_detail": {{
    "problem_statement": "string",
    "prior_art_gap": "string",
    "proposed_invention": "string",
    "architecture_overview": "string",
    "implementation_plan": "string",
    "validation_plan": "string",
    "draft_claims": ["string"],
    "risks_and_mitigations": ["string"],
    "references": ["string"]
  }}
}}

Revision round: {state.revisions + 1}

Current draft title: {draft.title}
Current one-liner: {draft.one_liner}
Current novelty thesis: {draft.novelty_thesis}
Current feasibility thesis: {draft.feasibility_thesis}
Current problem statement: {draft.problem_statement}
Current prior-art gap: {draft.prior_art_gap}
Current proposed invention: {draft.proposed_invention}
Current architecture: {draft.architecture_overview}
Current implementation plan: {draft.implementation_plan}
Current validation plan: {draft.validation_plan}
Current claims: {draft.draft_claims}

Reviewer required revisions:
{chr(10).join(f'- {x}' for x in critique.required_revisions)}
""".strip()

            try:
                raw = self.llm.chat(
                    model=settings.maverick_model,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=0.5,
                )
                payload = self._parse_json(raw)
                rebuttal = str(payload.get("strategic_rebuttal", "")).strip()
                revised_draft = self._merge_revised_draft(draft, payload)
                revised.append(revised_draft)
                revision_trace.append(
                    {
                        "before_title": draft.title,
                        "after_title": revised_draft.title,
                        "status": "REVISED",
                        "feedback_used": list(critique.required_revisions),
                        "summary": revised_draft.one_liner[:240],
                        "strategic_rebuttal": rebuttal[:400] if rebuttal else "",
                    }
                )
                logger.info(
                    "Maverick revision applied | run_id={} | before={} | after={} | rebuttal={}",
                    state.run_id,
                    draft.title,
                    revised_draft.title,
                    rebuttal[:120] if rebuttal else "none",
                )
            except Exception as exc:
                # Fallback: keep draft but annotate constraints to avoid losing progress.
                patch = "\n".join(f"- {x}" for x in critique.required_revisions)
                draft.proposed_invention = (
                    draft.proposed_invention.strip() +
                    "\n\nRevision constraints applied:\n" + patch
                )
                revised.append(draft)
                revision_trace.append(
                    {
                        "before_title": draft.title,
                        "after_title": draft.title,
                        "status": "FALLBACK_PATCH",
                        "feedback_used": list(critique.required_revisions),
                        "summary": f"Fallback patch applied: {str(exc)[:200]}",
                    }
                )
                logger.warning(
                    "Maverick revision fallback | run_id={} | title={} | reason={}",
                    state.run_id,
                    draft.title,
                    str(exc)[:220],
                )

        state.drafts = revised
        state.metadata.setdefault("conference_review_trace", []).append(
            {
                "event": "maverick_revision",
                "round": state.revisions + 1,
                "items": revision_trace,
            }
        )
        state.revisions += 1
        return state

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
            "status": "REVISE",
            "fatal_flaw": "",
            "scorecard": {
                "innovation": 2,
                "feasibility": 2,
                "prior_art_risk": 3,
            },
            "hallucinations_found": ["Could not parse critique JSON"],
            "actionable_feedback": "Return strict JSON output and fix factual kernel and x86 references",
            "approved": False,
        }

    @staticmethod
    def _clamp_star(value) -> int:
        try:
            score = int(value)
        except (TypeError, ValueError):
            score = 3
        return max(1, min(5, score))

    def _merge_revised_draft(self, original, payload: Dict) -> "DraftIdea":
        from agents.state import DraftIdea

        scores = payload.get("scores", {}) if isinstance(payload, dict) else {}
        detail = payload.get("tid_detail", {}) if isinstance(payload, dict) else {}
        return DraftIdea(
            title=str(payload.get("title", original.title)),
            one_liner=str(payload.get("one_liner", original.one_liner)),
            novelty_thesis=str(payload.get("novelty_thesis", original.novelty_thesis)),
            feasibility_thesis=str(payload.get("feasibility_thesis", original.feasibility_thesis)),
            market_thesis=str(payload.get("market_thesis", original.market_thesis)),
            why_now=str(payload.get("why_now", original.why_now)),
            innovation=self._clamp_star(scores.get("innovation", original.innovation)),
            implementation_difficulty=self._clamp_star(
                scores.get("implementation_difficulty", original.implementation_difficulty)
            ),
            commercial_value=self._clamp_star(scores.get("commercial_value", original.commercial_value)),
            technical_risk=self._clamp_star(scores.get("technical_risk", original.technical_risk)),
            prior_art_conflict_risk=self._clamp_star(
                scores.get("prior_art_conflict_risk", original.prior_art_conflict_risk)
            ),
            problem_statement=str(detail.get("problem_statement", original.problem_statement)),
            prior_art_gap=str(detail.get("prior_art_gap", original.prior_art_gap)),
            proposed_invention=str(detail.get("proposed_invention", original.proposed_invention)),
            architecture_overview=str(detail.get("architecture_overview", original.architecture_overview)),
            implementation_plan=str(detail.get("implementation_plan", original.implementation_plan)),
            validation_plan=str(detail.get("validation_plan", original.validation_plan)),
            draft_claims=[str(x) for x in detail.get("draft_claims", original.draft_claims)],
            risks_and_mitigations=[str(x) for x in detail.get("risks_and_mitigations", original.risks_and_mitigations)],
            references=[str(x) for x in detail.get("references", original.references)],
        )

    @staticmethod
    def _build_conference_feedback(critiques: List[CritiqueResult]) -> Dict:
        if not critiques:
            return {
                "round_size": 0,
                "approve_count": 0,
                "revise_count": 0,
                "reject_count": 0,
                "fatal_count": 0,
                "top_revision_points": [],
            }

        revision_points: List[str] = []
        approve_count = 0
        revise_count = 0
        reject_count = 0
        fatal_count = 0

        for critique in critiques:
            if critique.verdict == "APPROVE":
                approve_count += 1
            elif critique.verdict == "REVISE":
                revise_count += 1
            else:
                reject_count += 1

            if critique.fatal_flaw:
                fatal_count += 1

            for point in critique.required_revisions:
                text = str(point).strip()
                if text:
                    revision_points.append(text)

        deduped: List[str] = []
        seen = set()
        for point in revision_points:
            key = point.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(point)
            if len(deduped) >= 8:
                break

        return {
            "round_size": len(critiques),
            "approve_count": approve_count,
            "revise_count": revise_count,
            "reject_count": reject_count,
            "fatal_count": fatal_count,
            "top_revision_points": deduped,
        }
