"""
agents/pipeline.py

DeepThought multi-agent pipeline orchestrator.
"""

from __future__ import annotations

from pathlib import Path
from loguru import logger

from configs.settings import settings
from output.tid_formatter import TIDDetail, TIDReport, TIDScorecard, TIDSummary

from agents.debate_panel import DebatePanelAgent
from agents.forager import ForagerAgent
from agents.maverick import MaverickAgent
from agents.patent_shield import PatentShieldAgent
from agents.reality_checker import RealityCheckerAgent
from agents.state import PipelineState, TIDStatus


class DeepThoughtPipeline:
    def __init__(self):
        self.forager = ForagerAgent()
        self.maverick = MaverickAgent()
        self.patent_shield = PatentShieldAgent()
        self.reality_checker = RealityCheckerAgent()
        self.debate_panel = DebatePanelAgent()

    def run(self, state: PipelineState, n_drafts: int = 3, top_k_voids: int = 5) -> PipelineState:
        state.run_status = "RUNNING"
        state.metadata.setdefault("stage_status", {})

        try:
            state = self.forager.run(state, top_k=top_k_voids)
            state.metadata["stage_status"]["forager"] = "OK"
        except Exception as exc:
            return self._mark_failure(state, "forager", exc)

        try:
            state = self.maverick.run(state, n_drafts=n_drafts)
            state.metadata["stage_status"]["maverick"] = "OK"
        except Exception as exc:
            return self._mark_failure(state, "maverick", exc)

        state.tid_statuses = [
            TIDStatus(draft_index=i, title=d.title, status="DRAFTED")
            for i, d in enumerate(state.drafts)
        ]

        try:
            state = self.patent_shield.run(state)
            state.metadata["stage_status"]["patent_shield"] = "OK"
        except Exception as exc:
            return self._mark_failure(state, "patent_shield", exc)

        if state.run_status == "REJECTED":
            for t in state.tid_statuses:
                t.status = "REJECTED"
                t.last_error = state.last_error
            return state

        # Revision loop driven by reality checker
        try:
            revision_attempts = 0
            while revision_attempts < settings.max_revision_iterations:
                state = self.reality_checker.run(state)
                revision_attempts += 1
                has_revise = any(c.verdict == "REVISE" for c in state.critiques)
                has_approve = any(c.verdict == "APPROVE" for c in state.critiques)
                hard_reject = all(c.verdict == "REJECT" for c in state.critiques)
                fatal_flaws = [c.fatal_flaw for c in state.critiques if c.fatal_flaw]

                if hard_reject:
                    state.run_status = "REJECTED"
                    state.last_error = "; ".join(fatal_flaws) if fatal_flaws else "All drafts rejected by reality checker"
                    state.metadata["rejected_reason"] = state.last_error
                    for t in state.tid_statuses:
                        t.status = "REJECTED"
                    break

                if not has_revise:
                    break

                if revision_attempts >= settings.max_revision_iterations:
                    # Three-strikes rule: unresolved revisions are aborted.
                    state.run_status = "REJECTED"
                    state.last_error = "Failed to satisfy reality checker after maximum revisions"
                    state.metadata["rejected_reason"] = state.last_error
                    for t in state.tid_statuses:
                        if t.status not in {"REJECTED"}:
                            t.status = "REJECTED"
                    break

                if has_revise and not has_approve:
                    state = self.reality_checker.revise_drafts(state)
                    continue

                # Mixed APPROVE/REVISE case: revise unresolved drafts and continue.
                state = self.reality_checker.revise_drafts(state)

            state.metadata["stage_status"]["reality_checker"] = "OK"
        except Exception as exc:
            state = self._mark_failure(state, "reality_checker", exc)

        if state.run_status == "REJECTED":
            return state

        try:
            state = self.debate_panel.run(state)
            state.metadata["stage_status"]["debate_panel"] = "OK"
        except Exception as exc:
            state = self._mark_failure(state, "debate_panel", exc)
            # Keep pipeline moving even if debate fails.

        if state.debate_result and state.debate_result.final_verdict == "REJECT":
            for t in state.tid_statuses:
                t.status = "REJECTED"

        if state.failed_stages:
            if settings.reject_on_stage_failure:
                state.run_status = "REJECTED"
                if not state.last_error:
                    state.last_error = f"Stage failure: {', '.join(state.failed_stages)}"
                for t in state.tid_statuses:
                    if t.status not in {"APPROVED_AND_EXPORTED", "REJECTED"}:
                        t.status = "REJECTED"
                        t.last_error = state.last_error
            else:
                state.run_status = "RETRY_PENDING"
        elif state.debate_result and state.debate_result.final_verdict == "APPROVE":
            state.run_status = "APPROVED"
        elif state.debate_result and state.debate_result.final_verdict == "REJECT":
            state.run_status = "REJECTED"
            if not state.last_error:
                state.last_error = state.debate_result.synthesis
        else:
            state.run_status = "RETRY_PENDING"
            if state.debate_result and not state.last_error:
                state.last_error = state.debate_result.synthesis
        return state

    def export_reports(
        self,
        state: PipelineState,
        output_dir: str = "output/generated",
        tid_prefix: str = "TID-MA",
    ) -> PipelineState:
        if not state.drafts:
            return state

        if settings.export_only_approved_tid and state.run_status != "APPROVED":
            logger.info(
                "Skip TID export due to strict gate | run_status={} | export_only_approved_tid=true",
                state.run_status,
            )
            if state.tid_statuses:
                for t in state.tid_statuses:
                    if t.status not in {"REJECTED"}:
                        t.status = "NOT_EXPORTED"
            return state

        idx = max(0, min(state.selected_draft_index, len(state.drafts) - 1))
        draft = state.drafts[idx]

        report = TIDReport(
            tid_id=f"{tid_prefix}-001",
            title=draft.title,
            domain=state.domain,
            target=state.target,
            summary=TIDSummary(
                one_liner=draft.one_liner,
                novelty_thesis=draft.novelty_thesis,
                feasibility_thesis=draft.feasibility_thesis,
                market_thesis=draft.market_thesis,
                why_now=draft.why_now,
            ),
            scorecard=TIDScorecard(
                innovation=self._clamp_star(draft.innovation),
                implementation_difficulty=self._clamp_star(draft.implementation_difficulty),
                commercial_value=self._clamp_star(draft.commercial_value),
                technical_risk=self._clamp_star(draft.technical_risk),
                prior_art_conflict_risk=self._clamp_star(draft.prior_art_conflict_risk),
            ),
            detail=TIDDetail(
                problem_statement=draft.problem_statement,
                prior_art_gap=draft.prior_art_gap,
                proposed_invention=draft.proposed_invention,
                architecture_overview=draft.architecture_overview,
                implementation_plan=draft.implementation_plan,
                validation_plan=draft.validation_plan,
                draft_claims=draft.draft_claims,
                risks_and_mitigations=draft.risks_and_mitigations,
                references=draft.references,
            ),
        )

        out_dir = Path(output_dir)
        md_path, html_path = report.save(out_dir)
        state.output_paths = {
            "markdown": str(md_path),
            "html": str(html_path),
        }

        idx = max(0, min(state.selected_draft_index, len(state.tid_statuses) - 1))
        if state.tid_statuses:
            for t in state.tid_statuses:
                if t.status not in {"REJECTED"}:
                    t.status = "NOT_SELECTED"
            chosen = state.tid_statuses[idx]
            chosen.output_markdown = str(md_path)
            chosen.output_html = str(html_path)
            if state.run_status == "APPROVED":
                chosen.status = "APPROVED_AND_EXPORTED"
            elif state.run_status == "RETRY_PENDING":
                chosen.status = "EXPORTED_WITH_MODEL_FAILURE"
            else:
                chosen.status = "EXPORTED"

        return state

    @staticmethod
    def _clamp_star(value: int) -> int:
        return max(1, min(5, int(value)))

    def _mark_failure(self, state: PipelineState, stage: str, exc: Exception) -> PipelineState:
        state.failed_stages.append(stage)
        state.last_error = f"{stage}: {exc}"
        state.metadata.setdefault("stage_status", {})
        state.metadata["stage_status"][stage] = "FAILED"
        lowered = str(exc).lower()
        if "timed out" in lowered or "timeout" in lowered:
            state.metadata["fatal_flaw"] = "Model timeout under committee SLA"
        state.run_status = "REJECTED" if settings.reject_on_stage_failure else "RETRY_PENDING"
        for t in state.tid_statuses:
            if t.status not in {"APPROVED_AND_EXPORTED", "REJECTED"}:
                t.status = "REJECTED" if settings.reject_on_stage_failure else "RETRY_PENDING"
                t.last_error = state.last_error
        return state
