"""
agents/maverick.py

Maverick agent: generate multiple invention drafts from void context.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from configs.settings import settings

from agents.llm_client import LLMClient
from agents.state import DraftIdea, PipelineState


class MaverickAgent:
    def __init__(self, llm: LLMClient | None = None, model: str | None = None):
        self.llm = llm or LLMClient()
        self.model = model or settings.maverick_model

    def run(self, state: PipelineState, n_drafts: int = 3) -> PipelineState:
        system_prompt = (
            "You are an ambitious Kernel and Hardware Architect. "
            "Draft deep system-level Technical Invention Disclosure ideas that fill topological voids. "
            "Use precise Linux kernel and x86 hardware terminology only. "
            "Output valid JSON only."
        )

        compact_context = self._compact_void_context(state.topological_void_context)

        user_prompt = f"""
Domain: {state.domain}
Target: {state.target}
Requested drafts: {n_drafts}

Constraints:
- Focus strictly on Linux kernel internals plus x86 architecture coupling.
- Avoid generic AI buzzwords.
- Include specific kernel subsystems, data structures, or locking implications where appropriate.
- Each draft must include at least 3 patent claims.
- HARD CONSTRAINT: Evidence grounding is mandatory.
- Do NOT invent Linux kernel functions, structs, or x86 instructions.
- In Implementation Plan, explicitly cite concrete file paths and symbols from Void context.
- If the idea cannot be grounded in provided context, declare it unfeasible in feasibility_thesis and validation_plan.
- In Architecture Overview, include a simple ASCII control-flow diagram.

Void context:
{compact_context}

Return JSON:
{{
  "drafts": [
    {{
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
  ]
}}
""".strip()

        raw = self.llm.chat(
            model=self.model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.85,
        )
        payload = self._parse_json(raw)

        drafts: List[DraftIdea] = []
        for item in payload.get("drafts", []):
            scores = item.get("scores", {})
            detail = item.get("tid_detail", {})
            drafts.append(
                DraftIdea(
                    title=str(item.get("title", "Untitled")),
                    one_liner=str(item.get("one_liner", "")),
                    novelty_thesis=str(item.get("novelty_thesis", "")),
                    feasibility_thesis=str(item.get("feasibility_thesis", "")),
                    market_thesis=str(item.get("market_thesis", "")),
                    why_now=str(item.get("why_now", "")),
                    innovation=self._clamp_star(scores.get("innovation", 3)),
                    implementation_difficulty=self._clamp_star(scores.get("implementation_difficulty", 3)),
                    commercial_value=self._clamp_star(scores.get("commercial_value", 3)),
                    technical_risk=self._clamp_star(scores.get("technical_risk", 3)),
                    prior_art_conflict_risk=self._clamp_star(scores.get("prior_art_conflict_risk", 3)),
                    problem_statement=str(detail.get("problem_statement", "")),
                    prior_art_gap=str(detail.get("prior_art_gap", "")),
                    proposed_invention=str(detail.get("proposed_invention", "")),
                    architecture_overview=str(detail.get("architecture_overview", "")),
                    implementation_plan=str(detail.get("implementation_plan", "")),
                    validation_plan=str(detail.get("validation_plan", "")),
                    draft_claims=[str(x) for x in detail.get("draft_claims", [])],
                    risks_and_mitigations=[str(x) for x in detail.get("risks_and_mitigations", [])],
                    references=[str(x) for x in detail.get("references", [])],
                )
            )

        state.drafts = drafts
        state.metadata["draft_count"] = len(drafts)
        return state

    @staticmethod
    def _compact_void_context(context: str, max_chars: int = 3800) -> str:
        text = (context or "").strip()
        if len(text) <= max_chars:
            return text

        lines = [ln for ln in text.splitlines() if ln.strip()]
        head = []
        for ln in lines:
            if ln.startswith("Void #") or ln.startswith("Target:") or ln.startswith("Domain:") or ln.startswith("Lambda"):
                head.append(ln)
            if len("\n".join(head)) > max_chars:
                break

        compact = "\n".join(head).strip()
        if not compact:
            compact = text[:max_chars]
        if len(compact) > max_chars:
            compact = compact[:max_chars]
        return compact

    def _parse_json(self, text: str) -> Dict[str, Any]:
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

        raise ValueError("Maverick output is not valid JSON")

    @staticmethod
    def _clamp_star(value: Any) -> int:
        try:
            score = int(value)
        except (TypeError, ValueError):
            score = 3
        return max(1, min(5, score))
