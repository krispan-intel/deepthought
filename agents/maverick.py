"""
agents/maverick.py

Maverick agent: generate multiple invention drafts from void context.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from loguru import logger

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
- HARD CONSTRAINT: Evidence grounding is mandatory.
- Do NOT invent Linux kernel functions, structs, or x86 instructions.
- In Implementation Plan, explicitly cite concrete file paths and symbols from Void context.
- If the idea cannot be grounded in provided context, declare it unfeasible in feasibility_thesis and validation_plan.
- In Architecture Overview, include a simple ASCII control-flow diagram.

CRITICAL ARCHITECTURE RULES (violation = immediate rejection):
1. Do NOT mix async operations (like eBPF maps, deferred work, or RCU callbacks) into strictly synchronous
   or atomic kernel paths (like context switches, hardware interrupt handlers, or rq/runqueue locking).
2. Do NOT use debug/reporting interfaces (procfs, debugfs, seq_file, arch_show_interrupts, print_bpf_insn)
   as primary control plane routing or real-time decision points.
3. Respect the boot-time vs runtime contract: CPUID, MSRs, and hardware topology are typically fixed at boot
   or during initialization. Do not propose dynamic per-request renegotiation of immutable hardware state.
4. Do NOT propose cross-CPU wakeup suppression or reschedule-IPI filtering without a grounded synchronization
   model that preserves scheduler correctness under concurrent wakeups and CPU migration.
5. Stay within the natural boundaries of the seed subsystem: if the void context is from scheduler code,
   do not jump into unrelated domains like Wi-Fi MAC layer or PCIe ASPM without a credible causal bridge.

Void context:
{compact_context}

Conference review feedback (if available):
{feedback_text}
""".strip()

        raw = self.llm.chat(
            model=self.model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.85,
        )
        try:
            payload = self._parse_json(raw)
        except ValueError as exc:
            preview = self._build_output_preview(raw)
            state.metadata["maverick_generation"] = {
                "requested_drafts": n_drafts,
                "produced_drafts": 0,
                "status": "PARSE_ERROR",
                "reason": str(exc),
                "raw_preview": preview,
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
            return {
                "requested_drafts": n_drafts,
                "produced_drafts": 0,
                "status": "EMPTY",
                "reason": "Model returned zero valid drafts",
                "drafts": [],
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

    def _parse_json(self, text: str) -> Dict[str, Any]:
        cleaned = self._normalize_output(text)
        decoder = json.JSONDecoder()

        # Pass 1: standard parse across all candidate substrings
        for candidate in self._iter_json_candidates(cleaned):
            snippet = candidate.lstrip()
            if not snippet:
                continue
            try:
                parsed = json.loads(snippet)
            except json.JSONDecodeError:
                try:
                    parsed, _ = decoder.raw_decode(snippet)
                except json.JSONDecodeError:
                    continue
            payload = self._coerce_payload(parsed)
            if payload is not None:
                return payload

        # Pass 2: json-repair handles trailing commas, missing brackets, truncated output
        try:
            from json_repair import repair_json
            repaired = repair_json(cleaned, return_objects=True)
            payload = self._coerce_payload(repaired)
            if payload is not None:
                logger.warning("Maverick JSON recovered via json-repair | run preview truncated")
                return payload
        except Exception:
            pass

        # Pass 3: ask the LLM to fix its own output (one extra call, last resort)
        if self.llm is not None:
            try:
                fix_prompt = (
                    "The following text is malformed JSON. "
                    "Return ONLY the corrected JSON with no explanation:\n\n"
                    + cleaned[:6000]
                )
                fixed_raw = self.llm.chat(
                    model=self.model,
                    system_prompt="You are a JSON repair tool. Output only valid JSON.",
                    user_prompt=fix_prompt,
                    temperature=0.0,
                )
                fixed_cleaned = self._normalize_output(fixed_raw)
                for candidate in self._iter_json_candidates(fixed_cleaned):
                    snippet = candidate.lstrip()
                    if not snippet:
                        continue
                    try:
                        parsed = json.loads(snippet)
                    except json.JSONDecodeError:
                        continue
                    payload = self._coerce_payload(parsed)
                    if payload is not None:
                        logger.warning("Maverick JSON recovered via self-repair LLM call")
                        return payload
            except Exception as repair_exc:
                logger.warning("Maverick self-repair LLM call failed | error={}", repair_exc)

        raise ValueError("Maverick output is not valid JSON")

    @staticmethod
    def _coerce_payload(parsed: Any) -> Dict[str, Any] | None:
        if isinstance(parsed, dict):
            return parsed
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict) and "drafts" in item:
                    return item
        return None

    @staticmethod
    def _normalize_output(text: str) -> str:
        # Remove common ANSI escape sequences from terminal-rendered CLI output.
        return re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text or "").strip()

    def _iter_json_candidates(self, text: str) -> List[str]:
        candidates: List[str] = [text]

        for fenced in re.finditer(r"```(?:json)?\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE):
            candidates.append(fenced.group(1))

        for token in ("{", "["):
            idx = text.find(token)
            while idx != -1:
                candidates.append(text[idx:])
                idx = text.find(token, idx + 1)

        seen = set()
        deduped: List[str] = []
        for item in candidates:
            key = item.strip()
            if key and key not in seen:
                seen.add(key)
                deduped.append(item)
        return deduped

    @staticmethod
    def _build_output_preview(text: str, limit: int = 280) -> str:
        compact = " ".join(MaverickAgent._normalize_output(text).split())
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
