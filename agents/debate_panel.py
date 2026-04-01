"""
agents/debate_panel.py

Debate Panel agent: multi-model synthesis over approved/revised drafts.
"""

from __future__ import annotations

import json
import re
from typing import Dict, List

from configs.settings import settings

from agents.llm_client import LLMClient
from agents.state import DebateResult, PipelineState


class DebatePanelAgent:
    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or LLMClient()

    def run(self, state: PipelineState) -> PipelineState:
        if not state.drafts:
            state.debate_result = DebateResult(
                final_verdict="REJECT",
                synthesis="No drafts available for debate.",
                winning_title="",
                confidence=0.0,
            )
            return state

        draft_blob = self._format_drafts(state)

        thinker = self.llm.chat(
            model=settings.debate_deep_thinker_model,
            system_prompt="You are Deep Thinker. Find edge cases, hidden assumptions, and long-term constraints.",
            user_prompt=draft_blob,
            temperature=0.5,
        )
        coder = self.llm.chat(
            model=settings.debate_code_expert_model,
            system_prompt="You are Code Expert. Evaluate implementation realism, integration cost, and verification strategy.",
            user_prompt=draft_blob,
            temperature=0.4,
        )

        judge_prompt = f"""
Drafts:
{draft_blob}

Deep Thinker view:
{thinker}

Code Expert view:
{coder}

Return strict JSON:
{{
  "final_verdict": "APPROVE|REVISE|REJECT",
  "winning_title": "string",
  "synthesis": "string",
  "confidence": 0.0
}}
""".strip()

        judge = self.llm.chat(
            model=settings.debate_judge_model,
            system_prompt="You are final judge. Select the best candidate and produce concise final synthesis.",
            user_prompt=judge_prompt,
            temperature=0.3,
        )
        result = self._parse_json(judge)

        state.debate_result = DebateResult(
            final_verdict=str(result.get("final_verdict", "REVISE")).upper(),
            winning_title=str(result.get("winning_title", "")),
            synthesis=str(result.get("synthesis", "")),
            confidence=float(result.get("confidence", 0.5)),
        )

        selected = 0
        for i, d in enumerate(state.drafts):
            if d.title.strip().lower() == state.debate_result.winning_title.strip().lower():
                selected = i
                break
        state.selected_draft_index = selected
        return state

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
