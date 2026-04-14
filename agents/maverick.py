"""
agents/maverick.py

Maverick agent: generate multiple invention drafts from void context.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from loguru import logger

from configs.settings import settings

from agents.json_parser import robust_json_parse
from agents.llm_client import LLMClient
from agents.state import DraftIdea, PipelineState


class MaverickAgent:
    def __init__(self, llm: LLMClient | None = None, model: str | None = None):
        self.llm = llm or LLMClient()
        self.model = model or settings.maverick_model

    def _should_use_claude_proxy(self) -> bool:
        """Check if Claude Agent proxy mode should be used."""
        return self.model.startswith("claude-")

    def _delegate_to_claude_agent(self, state: PipelineState, n_drafts: int, system_prompt: str, user_prompt: str) -> PipelineState:
        """Save draft generation request for Claude Agent and wait for completion."""
        import time

        pending_dir = Path("data/pending_maverick")
        completed_dir = Path("data/completed_maverick")
        pending_dir.mkdir(parents=True, exist_ok=True)
        completed_dir.mkdir(parents=True, exist_ok=True)

        request = {
            "run_id": state.run_id,
            "timestamp": datetime.now().isoformat(),
            "domain": state.domain,
            "target": state.target,
            "n_drafts": n_drafts,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "void_context": state.topological_void_context,
            "model": self.model,
        }

        request_file = pending_dir / f"{state.run_id}.json"
        completed_file = completed_dir / f"{state.run_id}.json"

        request_file.write_text(json.dumps(request, indent=2, ensure_ascii=False))

        logger.info(
            "Delegated to Claude Agent (Maverick) | run_id={} | file={} | waiting for completion...",
            state.run_id,
            request_file,
            n_drafts,
        )

        # Wait for completed file (Phase 2 auto-recovery)
        max_wait_seconds = 1800  # 30 minutes
        check_interval = 5  # Check every 5 seconds
        elapsed = 0

        while elapsed < max_wait_seconds:
            if completed_file.exists():
                logger.info(
                    "Claude Agent (Maverick) completed | run_id={} | elapsed={}s",
                    state.run_id,
                    elapsed,
                )
                # Load completed result
                try:
                    result = json.loads(completed_file.read_text())
                    drafts = result.get("drafts", [])

                    # Parse drafts into DraftIdea objects
                    from agents.state import DraftIdea
                    parsed_drafts = []
                    for item in drafts:
                        scores = item.get("scores", {})
                        detail = item.get("tid_detail", {})
                        parsed_drafts.append(
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

                    state.drafts = parsed_drafts
                    state.metadata["draft_count"] = len(parsed_drafts)
                    state.metadata["claude_agent_maverick_status"] = "COMPLETED"

                    # Clean up
                    request_file.unlink(missing_ok=True)

                    logger.info(
                        "Maverick generated drafts via Claude Agent | run_id={} | produced={}",
                        state.run_id,
                        len(parsed_drafts),
                    )

                    return state

                except Exception as exc:
                    logger.error(
                        "Failed to parse Claude Agent result | run_id={} | error={}",
                        state.run_id,
                        exc,
                    )
                    raise ValueError(f"Failed to parse Claude Agent Maverick result: {exc}")

            time.sleep(check_interval)
            elapsed += check_interval

        # Timeout
        state.metadata["claude_agent_maverick_status"] = "TIMEOUT"
        state.run_status = "PENDING_CLAUDE_MAVERICK"
        state.last_error = f"Claude Agent (Maverick) timeout after {max_wait_seconds}s"

        logger.error(
            "Claude Agent (Maverick) timeout | run_id={} | max_wait={}s",
            state.run_id,
            max_wait_seconds,
        )

        return state

    def run(self, state: PipelineState, n_drafts: int = 3) -> PipelineState:
        system_prompt = (
            "You are an Elite System Architect specializing in cross-domain innovation. "
            "Draft deep system-level Technical Invention Disclosure ideas that fill topological voids. "
            "Use precise Linux kernel and x86 hardware terminology only. "
            "\n\n"
            "CRITICAL BRIDGE RULE:\n"
            "You have been provided with a Topological Void containing two highly divergent concepts (Concept A and Concept B). "
            "Do NOT simply force them together or pretend they natively interact. "
            "Your invention MUST define a NEW INTERFACE, ABSTRACTION LAYER, OR STATE MACHINE (The Bridge) "
            "that successfully translates between these two domains without violating their individual "
            "physical or asynchronous constraints. The bridge is the invention.\n"
            "\n"
            "Output valid JSON only."
        )

        compact_context = self._compact_void_context(state.topological_void_context)
        review_feedback = state.metadata.get("conference_review_feedback", {})
        feedback_text = self._format_conference_feedback(review_feedback)

        user_prompt = f"""
OUTPUT FORMAT (respond with ONLY this JSON, no prose before or after):
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

Domain: {state.domain}
Target: {state.target}
Requested drafts: {n_drafts}

Constraints:
- Focus strictly on Linux kernel internals plus x86 architecture coupling.
- Avoid generic AI buzzwords.
- Include specific kernel subsystems, data structures, or locking implications where appropriate.
- Each draft must include at least 3 patent claims.
- PREFERENCE: Ground proposals in provided void context when possible.
- You MAY cite well-known kernel subsystems (e.g., sched, mm, bpf, fs) even if not literally in void context.
- If void concepts are too divergent to bridge credibly, focus your invention on ONE concept (either A or B) that has stronger technical merit.
- Do NOT invent fictional functions, but referencing standard kernel APIs (kmalloc, schedule, etc.) is acceptable.
- In Architecture Overview, include a simple ASCII control-flow diagram.

CRITICAL ARCHITECTURE RULES (violation = immediate rejection):

1. ATOMIC CONTEXT RULE
   Do NOT mix async operations (eBPF maps, deferred work, RCU callbacks, copy_from_user,
   kmalloc(GFP_KERNEL)) into strictly synchronous or atomic kernel paths (spinlock regions,
   context switches, hardware interrupt handlers, NMI handlers, rq/runqueue locking).

   ❌ FORBIDDEN EXAMPLE (from real rejection):
   "Scheduler context-switch path → IRQ affinity routing changes"
   (Places interrupt-routing on strictly synchronous path without explicit deferral)

2. DEBUG-INTERFACE-AS-CONTROL-PLANE RULE
   Do NOT use debug/reporting interfaces (procfs, debugfs, seq_file, arch_show_interrupts,
   print_bpf_insn, tracepoints) as primary control plane routing or real-time decision points.
   These are inspection tools, not hot-path logic.

3. BOOT-TIME VS RUNTIME CONTRACT RULE
   Respect the boot-time vs runtime contract: CPUID, MSRs, and hardware topology are
   typically fixed at boot or during initialization. Do NOT propose dynamic per-request
   renegotiation of immutable hardware state (CPUID feature flags do not change after boot).

4. CROSS-CPU SYNCHRONIZATION RULE
   Do NOT propose cross-CPU wakeup suppression or reschedule-IPI filtering without a
   grounded synchronization model that preserves scheduler correctness under concurrent
   wakeups and CPU migration (IPI suppression requires proving memory-ordering correctness).

5. SUBSYSTEM BOUNDARY RULE
   Stay within the natural boundaries of the seed subsystem. If void context is from
   scheduler code, do NOT jump into unrelated domains (Wi-Fi MAC, PCIe ASPM, USB stack)
   without a credible causal bridge. Cross-domain proposals must define explicit abstraction layers.

   ❌ FORBIDDEN EXAMPLES (from real rejections):
   a) "TDX host lifecycle state ↔ MT6357 backlight MMIO control"
      (Virtualization + off-chip backlight = no causal bridge)
   b) "VMX/EPT capability ↔ vm86 interrupt-shadow state"
      (Modern virtualization + legacy vm86 = unrelated subsystems)
   c) "AMX xstate ↔ VMX MMIO buffer-clear flags"
      (Instruction-set extension + virtualization buffer = no causal connection)
   d) "GPIO expander pins → x86 CR4.PVI + LAPIC delivery"
      (Off-chip GPIO + on-chip CPU semantics = architectural mismatch)

6. CAUSAL BRIDGE REQUIREMENT
   If bridging two divergent subsystems (A and B), you MUST define:
   - The NEW ABSTRACTION LAYER that translates between them
   - The STATE MACHINE that coordinates their interaction
   - The SYNCHRONIZATION MODEL that ensures correctness

   Simply stating "use A to control B" without the bridge architecture is a critical violation.
   The bridge IS the invention. Without it, you're just forcing unrelated systems together.

7. NOVELTY RULE
   Do NOT claim standard patterns as novel inventions:
   - Optimistic concurrency (snapshot → compute → revalidate) = well-known since seqlock (2002)
   - Double-checked locking, RCU read-side deferral, per-CPU counters = established techniques

   Your invention must be a NEW APPLICATION or HARDWARE BRIDGE, not rediscovery.

8. EXCEPTION-AS-CONTROL-FLOW BAN
   Never use hardware exceptions (e.g., #NM, #UD, Page Faults) as a routine control-flow
   mechanism for performance optimization in hot kernel paths (scheduler, network datapath,
   context switch). Traps and exception handling incur massive pipeline flushes and CPU cycle
   overhead. Exceptions are for error handling, not for lazy state tracking.

   ❌ FORBIDDEN EXAMPLE (from real rejection):
   "Use CR0.TS + #NM exception to defer AVX-512 state save on context switch"
   (This was abandoned by Linux in 2016 due to CVE-2018-3665 and performance degradation)

9. STATE ISOLATION MANDATE
   Never propose 'Lazy Context Switching' or deferred state saving for any CPU architectural
   state (Registers, SIMD, Matrix engines, FPU). Linux mandates EAGER state switching to
   guarantee strict cross-process isolation and mitigate side-channel data leaks (e.g.,
   Meltdown/Spectre variants, CVE-2018-3665 Lazy FP state restore vulnerability).
   Security trumps lazy performance optimizations.

   The kernel removed lazy FPU switching in 2016 (Kernel 4.6) for security reasons.
   Do NOT reinvent it.

10. HARDWARE DELEGATION PRINCIPLE
    If the modern CPU Instruction Set Architecture (ISA) provides native hardware-level
    state tracking (e.g., XSAVE's XINUSE bitmap for tracking unmodified state), software
    must NOT invent coarse-grained software algorithms to replicate it. Trust the hardware
    state machine. XSAVEOPT/XSAVES already skip unmodified state - do NOT build software
    wrappers around functionality the hardware provides more efficiently.

FALLBACK RULE:
If you cannot credibly bridge both Concept A and Concept B, generate drafts focusing on Concept A OR Concept B only.
Returning zero drafts is UNACCEPTABLE. You MUST always generate exactly {n_drafts} drafts.
Even if a concept seems peripheral, find the technical innovation angle within Linux kernel context.

Void context:
{compact_context}

Conference review feedback (if available):
{feedback_text}
""".strip()

        # Check if Claude Agent proxy mode is enabled
        if self._should_use_claude_proxy():
            return self._delegate_to_claude_agent(state, n_drafts, system_prompt, user_prompt)

        raw = self.llm.chat(
            model=self.model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.85,
        )
        state.metadata["_maverick_raw_output"] = raw
        try:
            payload = self._parse_json(raw, with_llm_repair=True)
        except ValueError as exc:
            preview = self._build_output_preview(raw)
            state.metadata["maverick_generation"] = {
                "requested_drafts": n_drafts,
                "produced_drafts": 0,
                "status": "PARSE_ERROR",
                "reason": str(exc),
                "raw_preview": preview,
                "raw_output_length": len(raw),
            }
            logger.error(
                "Maverick parse failed | run_id={} | preview={}",
                state.run_id,
                preview,
            )
            raise ValueError(f"Maverick output is not valid JSON | preview={preview}") from exc

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
        summary = self._build_generation_summary(state=state, n_drafts=n_drafts, drafts=drafts)
        state.metadata["maverick_generation"] = summary

        if drafts:
            top = summary["drafts"][0]
            logger.info(
                "Maverick generated drafts | run_id={} | requested={} | produced={} | subject={} | summary={}",
                state.run_id,
                n_drafts,
                len(drafts),
                top["subject"],
                top["summary"],
            )
        else:
            logger.warning(
                "Maverick produced no RFC drafts | run_id={} | requested={} | reason={}",
                state.run_id,
                n_drafts,
                summary["reason"],
            )

        return state

    @staticmethod
    def _build_generation_summary(state: PipelineState, n_drafts: int, drafts: List[DraftIdea]) -> Dict[str, Any]:
        if not drafts:
            raw_output = state.metadata.get("_maverick_raw_output", "")
            return {
                "requested_drafts": n_drafts,
                "produced_drafts": 0,
                "status": "EMPTY",
                "reason": "Model returned zero valid drafts",
                "drafts": [],
                "raw_output_length": len(raw_output),
            }

        return {
            "requested_drafts": n_drafts,
            "produced_drafts": len(drafts),
            "status": "OK",
            "reason": "",
            "drafts": [
                {
                    "index": index,
                    "subject": draft.title.strip(),
                    "summary": draft.one_liner.strip()[:240],
                }
                for index, draft in enumerate(drafts)
            ],
        }

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

    def _parse_json(self, text: str, with_llm_repair: bool = False) -> Dict[str, Any]:
        """Parse JSON from Maverick output with 3-pass repair strategy."""
        llm_repair_callback = None
        if with_llm_repair and self.llm is not None:

            def repair_callback(malformed_json: str) -> str:
                fix_prompt = (
                    "The following text is malformed JSON. "
                    "Return ONLY the corrected JSON with no explanation:\n\n" + malformed_json
                )
                return self.llm.chat(
                    model=self.model,
                    system_prompt="You are a JSON repair tool. Output only valid JSON.",
                    user_prompt=fix_prompt,
                    temperature=0.0,
                )

            llm_repair_callback = repair_callback

        return robust_json_parse(
            text,
            llm_repair_callback=llm_repair_callback,
            agent_name="Maverick",
        )

    @staticmethod
    def _build_output_preview(text: str, limit: int = 280) -> str:
        # Remove ANSI escape sequences and collapse whitespace
        cleaned = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text or "").strip()
        compact = " ".join(cleaned.split())
        if len(compact) <= limit:
            return compact
        return compact[: limit - 3] + "..."

    @staticmethod
    def _format_conference_feedback(feedback: Any) -> str:
        if not isinstance(feedback, dict) or not feedback:
            return "No prior conference-review metrics available in this round."

        top_points = feedback.get("top_revision_points", [])
        if not isinstance(top_points, list):
            top_points = []
        bullets = "\n".join(f"- {str(item)}" for item in top_points[:8])
        if not bullets:
            bullets = "- No concrete revision points recorded."

        return (
            f"approve={feedback.get('approve_count', 0)}, "
            f"revise={feedback.get('revise_count', 0)}, "
            f"reject={feedback.get('reject_count', 0)}, "
            f"fatal={feedback.get('fatal_count', 0)}\n"
            f"Top revision points:\n{bullets}"
        )

    @staticmethod
    def _clamp_star(value: Any) -> int:
        try:
            score = int(value)
        except (TypeError, ValueError):
            score = 3
        return max(1, min(5, score))
