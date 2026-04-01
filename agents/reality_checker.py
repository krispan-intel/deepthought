"""
agents/reality_checker.py

Reality Checker agent: critique each draft and produce APPROVE/REVISE/REJECT.
"""

from __future__ import annotations

import json
import re
from typing import Dict, List

from agents.llm_client import LLMClient
from agents.state import CritiqueResult, PipelineState


class RealityCheckerAgent:
    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or LLMClient()

    def run(self, state: PipelineState) -> PipelineState:
        critiques: List[CritiqueResult] = []

        for draft in state.drafts:
            system_prompt = (
                "You are Reality Checker, a strict technical critic. "
                "Assess feasibility, consistency, and prior-art collision risk. "
                "Output valid JSON only."
            )
            user_prompt = f"""
Draft title: {draft.title}
One-liner: {draft.one_liner}
Novelty thesis: {draft.novelty_thesis}
Feasibility thesis: {draft.feasibility_thesis}
Problem statement: {draft.problem_statement}
Proposed invention: {draft.proposed_invention}
Architecture: {draft.architecture_overview}
Implementation plan: {draft.implementation_plan}
Validation plan: {draft.validation_plan}

Return JSON:
{{
  "verdict": "APPROVE|REVISE|REJECT",
  "rationale": "string",
  "required_revisions": ["string"],
  "confidence": 0.0
}}
""".strip()

            raw = self.llm.chat_reality_checker(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.2,
            )
            data = self._parse_json(raw)

            critiques.append(
                CritiqueResult(
                    verdict=str(data.get("verdict", "REVISE")).upper(),
                    rationale=str(data.get("rationale", "")),
                    required_revisions=[str(x) for x in data.get("required_revisions", [])],
                    confidence=float(data.get("confidence", 0.5)),
                )
            )

        state.critiques = critiques
        return state

    def revise_drafts(self, state: PipelineState) -> PipelineState:
        revised = []
        for draft, critique in zip(state.drafts, state.critiques):
            if critique.verdict != "REVISE":
                revised.append(draft)
                continue

            patch = "\n".join(f"- {x}" for x in critique.required_revisions)
            draft.proposed_invention = (
                draft.proposed_invention.strip() +
                "\n\nRevision constraints applied:\n" + patch
            )
            revised.append(draft)

        state.drafts = revised
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
            "verdict": "REVISE",
            "rationale": "Could not parse critique JSON",
            "required_revisions": ["Return strict JSON output"],
            "confidence": 0.2,
        }
