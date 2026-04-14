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
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from loguru import logger

from configs.settings import settings
from agents.json_parser import robust_json_parse
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

    def _should_use_claude_proxy(self) -> bool:
        """Check if Claude Agent proxy mode should be used."""
        return self.model.startswith("claude-")

    def _delegate_to_claude_agent(self, state: PipelineState, system_prompt: str, user_prompt: str) -> PipelineState:
        """Save professor review request for Claude Agent and wait for completion."""
        import time

        pending_dir = Path("data/pending_professor")
        completed_dir = Path("data/completed_professor")
        pending_dir.mkdir(parents=True, exist_ok=True)
        completed_dir.mkdir(parents=True, exist_ok=True)

        request = {
            "run_id": state.run_id,
            "timestamp": datetime.now().isoformat(),
            "domain": state.domain,
            "target": state.target,
            "drafts": [asdict(draft) for draft in state.drafts],
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "model": self.model,
        }

        request_file = pending_dir / f"{state.run_id}.json"
        completed_file = completed_dir / f"{state.run_id}.json"

        request_file.write_text(json.dumps(request, indent=2, ensure_ascii=False))

        logger.info(
            "Delegated to Claude Agent (Professor) | run_id={} | file={} | waiting...",
            state.run_id,
            request_file,
        )

        # Wait for completion
        max_wait_seconds = 300
        check_interval = 5
        elapsed = 0

        while elapsed < max_wait_seconds:
            if completed_file.exists():
                logger.info(f"Claude Agent (Professor) completed | run_id={state.run_id} | elapsed={elapsed}s")
                try:
                    result = json.loads(completed_file.read_text())
                    verdicts = result.get("verdicts", [])

                    # Filter drafts based on verdicts
                    filtered_drafts = []
                    for i, draft in enumerate(state.drafts):
                        if i < len(verdicts) and verdicts[i].get("verdict", "PASS").upper() == "PASS":
                            filtered_drafts.append(draft)

                    state.drafts = filtered_drafts
                    state.metadata["claude_agent_professor_status"] = "COMPLETED"

                    request_file.unlink(missing_ok=True)

                    logger.info(f"Professor completed via Claude Agent | run_id={state.run_id} | passed={len(filtered_drafts)}")

                    return state

                except Exception as exc:
                    logger.error(f"Failed to parse Professor result | run_id={state.run_id} | error={exc}")
                    raise ValueError(f"Failed to parse Claude Agent Professor result: {exc}")

            time.sleep(check_interval)
            elapsed += check_interval

        # Timeout
        state.metadata["claude_agent_professor_status"] = "TIMEOUT"
        state.run_status = "PENDING_CLAUDE_PROFESSOR"
        state.last_error = f"Claude Agent (Professor) timeout after {max_wait_seconds}s"
        logger.error(f"Claude Agent (Professor) timeout | run_id={state.run_id}")

        return state

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

Check these 2 BLOCKING issues:

1. ARCHITECTURE RULES VIOLATION (CRITICAL - always check)
   - Async operations (eBPF maps, RCU callbacks, deferred work) in strictly synchronous paths (context switch, rq locking, NMI/IRQ handlers)
   - Debug/reporting interfaces (procfs, debugfs, seq_file, arch_show_interrupts, print_bpf_insn) used as primary control plane
   - Boot-time vs runtime contract violation (dynamic CPUID renegotiation, modifying immutable hardware state)
   - Cross-CPU wakeup suppression or reschedule-IPI filtering without grounded synchronization model
   - Jumping across unrelated subsystems without credible causal bridge
   - EXCEPTION-AS-CONTROL-FLOW: Using hardware exceptions (#NM, #UD, page faults) as routine control flow in hot kernel paths (scheduler, context switch, network datapath). This includes CR0.TS + #NM for lazy FPU/SIMD state switching (removed in Linux 4.6 due to CVE-2018-3665)
   - STATE ISOLATION: Proposing lazy context switching or deferred state saving for CPU architectural state (FPU, SIMD, Matrix engines). Linux mandates eager state switching for security (Meltdown/Spectre/CVE-2018-3665)
   - HARDWARE DELEGATION: Reinventing functionality the hardware already provides (e.g., XSAVE's XINUSE bitmap for tracking unmodified state). Do NOT wrap hardware-level state tracking in software

2. JSON FORMAT (CRITICAL - always check)
   - Malformed JSON structure
   - Missing required fields (title, claims, implementation_plan, etc.)

IMPORTANT: Do NOT check evidence grounding (kernel functions/paths cited).
- It is ACCEPTABLE for drafts to cite standard kernel functions not literally in void context
- Example: void context mentions "scheduler" → draft can cite try_to_wake_up(), select_idle_sibling()
- Only reject if draft invents COMPLETELY FICTIONAL subsystems (not real Linux code)

Decision rules:
- If draft has critical architecture rule violation → REJECT
- If draft has malformed JSON → REJECT
- Otherwise → PASS (even if you have concerns about evidence, let Reality Checker judge)
- Be lenient: when in doubt, PASS

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

        # Check if Claude Agent proxy mode is enabled
        if self._should_use_claude_proxy():
            return self._delegate_to_claude_agent(state, system_prompt, user_prompt)

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
        """Parse JSON from Professor output."""
        return robust_json_parse(
            text,
            llm_repair_callback=None,
            agent_name="Professor",
        )
