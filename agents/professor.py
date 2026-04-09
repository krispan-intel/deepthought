"""
agents/professor.py

Professor Agent: Lightweight pre-flight technical reviewer.
Catches obvious errors before expensive Reality Checker / Patent Shield stages.

Checks:
1. JSON format validation
2. Architecture Rules compliance (5 critical rules)
3. Evidence grounding (cited symbols exist in void context)

Philosophy: Fast triage, not deep analysis. PASS/REJECT only (no REVISE in v1).
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from loguru import logger

from configs.settings import settings
from agents.llm_client import LLMClient
from agents.state import DraftIdea, PipelineState


class ProfessorAgent:
    """
    Pre-flight technical reviewer for draft quality assurance.

    Filters out drafts with obvious blocking issues before they reach
    expensive downstream stages (Patent Shield, Reality Checker, Debate Panel).
    """

    def __init__(self, llm: LLMClient | None = None, model: str | None = None):
        self.llm = llm or LLMClient()
        self.model = model or settings.professor_model

    def run(self, state: PipelineState) -> PipelineState:
        """
        Pre-flight review of Maverick drafts.

        Returns:
            Updated state with filtered drafts (REJECT drafts removed)
        """
        if not state.drafts:
            state.metadata["professor_review"] = {
                "verdict": "SKIP",
                "reason": "No drafts to review",
            }
            return state

        if not settings.professor_enabled:
            state.metadata["professor_review"] = {
                "verdict": "SKIP",
                "reason": "Professor disabled in settings",
            }
            return state

        original_count = len(state.drafts)
        logger.info(
            "Professor pre-flight review started | run_id={} | drafts={}",
            state.run_id,
            original_count,
        )

        # Prepare review context
        draft_summaries = self._format_drafts(state.drafts)
        void_context_excerpt = (state.topological_void_context or "")[:2000]

        system_prompt = """You are a Senior Kernel Architect conducting pre-flight technical review.

Your job: catch OBVIOUS blocking errors only. Do NOT do deep feasibility analysis (that's Reality Checker's job).

Check these 3 BLOCKING issues:

1. ARCHITECTURE RULES VIOLATION
   - Async operations (eBPF maps, RCU callbacks, deferred work) in strictly synchronous paths (context switch, rq locking, NMI/IRQ handlers)
   - Debug/reporting interfaces (procfs, debugfs, seq_file, arch_show_interrupts, print_bpf_insn) used as primary control plane
   - Boot-time vs runtime contract violation (dynamic CPUID renegotiation, modifying immutable hardware state)
   - Cross-CPU wakeup suppression or reschedule-IPI filtering without grounded synchronization model
   - Jumping across unrelated subsystems without credible causal bridge

2. EVIDENCE GROUNDING
   - Citing kernel functions, structs, macros, or file paths that do NOT appear in void context
   - Inventing non-existent symbols or subsystem interfaces

3. JSON FORMAT
   - Malformed JSON structure
   - Missing required fields (title, claims, implementation_plan, etc.)

Decision rules:
- If draft has ANY blocking issue → REJECT
- If draft passes all 3 checks → PASS (even if you have minor concerns)
- Be lenient: when in doubt, PASS and let Reality Checker do deep analysis

Output strict JSON only."""

        user_prompt = f"""
Void context evidence (kernel symbols and paths available):
{void_context_excerpt}

Drafts to review:
{draft_summaries}

Output format (strict JSON):
{{
  "verdicts": [
    {{
      "draft_index": 0,
      "verdict": "PASS|REJECT",
      "quality_score": 7.5,
      "blocking_issues": [
        {{
          "category": "architecture_rule|evidence_grounding|json_format",
          "severity": "critical",
          "description": "string"
        }}
      ]
    }}
  ],
  "summary": "Overall assessment in 1-2 sentences"
}}

Output now:
""".strip()

        raw = self.llm.chat(
            model=self.model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
        )

        try:
            review_result = self._parse_json(raw)
        except ValueError as exc:
            logger.warning(
                "Professor review parse failed, defaulting to PASS all | run_id={} | error={}",
                state.run_id,
                exc,
            )
            # Fallback: pass all drafts if parse fails (fail-open to avoid blocking pipeline)
            state.metadata["professor_review"] = {
                "verdict": "PARSE_ERROR_PASS_ALL",
                "parse_error": str(exc),
                "raw_preview": raw[:200],
            }
            return state

        # Filter drafts based on professor verdicts
        verdicts = review_result.get("verdicts", [])
        filtered_drafts: List[DraftIdea] = []
        reject_reasons: List[str] = []

        for i, draft in enumerate(state.drafts):
            if i < len(verdicts):
                verdict_data = verdicts[i]
                verdict = verdict_data.get("verdict", "PASS").upper()
                if verdict == "PASS":
                    filtered_drafts.append(draft)
                else:
                    issues = verdict_data.get("blocking_issues", [])
                    issue_desc = "; ".join([issue.get("description", "") for issue in issues])
                    reject_reasons.append(f"Draft {i}: {issue_desc}")
                    logger.info(
                        "Professor rejected draft | run_id={} | draft_index={} | title={} | issues={}",
                        state.run_id,
                        i,
                        draft.title[:60],
                        issue_desc[:100],
                    )
            else:
                # No verdict for this draft, default to PASS
                filtered_drafts.append(draft)

        state.drafts = filtered_drafts
        state.metadata["professor_review"] = {
            "original_count": original_count,
            "passed_count": len(filtered_drafts),
            "rejected_count": original_count - len(filtered_drafts),
            "verdicts": verdicts,
            "summary": review_result.get("summary", ""),
            "reject_reasons": reject_reasons,
        }

        logger.info(
            "Professor pre-flight review completed | run_id={} | submitted={} | passed={} | rejected={}",
            state.run_id,
            original_count,
            len(filtered_drafts),
            original_count - len(filtered_drafts),
        )

        return state

    @staticmethod
    def _format_drafts(drafts: List[DraftIdea]) -> str:
        """Format drafts for review (compact summary)."""
        lines = []
        for i, draft in enumerate(drafts):
            lines.append(f"=== Draft {i} ===")
            lines.append(f"Title: {draft.title}")
            lines.append(f"Novelty: {draft.novelty_thesis}")
            lines.append(f"Architecture: {draft.architecture_overview[:300]}")
            lines.append(f"Implementation: {draft.implementation_plan[:300]}")
            lines.append(f"Claims: {len(draft.draft_claims)} claims")
            if draft.draft_claims:
                lines.append(f"  - {draft.draft_claims[0][:150]}")
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _parse_json(text: str) -> Dict[str, Any]:
        """Parse JSON from LLM response."""
        text = text.strip()

        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try fenced code block
        fenced = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text, re.DOTALL)
        if fenced:
            try:
                return json.loads(fenced.group(1))
            except json.JSONDecodeError:
                pass

        # Try extracting first {...}
        braces = re.search(r"(\{[\s\S]*\})", text, re.DOTALL)
        if braces:
            try:
                return json.loads(braces.group(1))
            except json.JSONDecodeError:
                pass

        raise ValueError(f"Could not parse JSON from professor output: {text[:200]}")
