"""
agents/pipeline.py

DeepThought multi-agent pipeline orchestrator.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from typing import List

from loguru import logger

from configs.settings import settings
from output.tid_formatter import TIDDetail, TIDReport, TIDScorecard, TIDSummary
from output.claim_analysis import assess_claims

from agents.debate_panel import DebatePanelAgent
from agents.forager import ForagerAgent
from agents.maverick import MaverickAgent
from agents.patent_shield import PatentShieldAgent
from agents.professor import ProfessorAgent
from agents.reality_checker import RealityCheckerAgent
from agents.state import DraftIdea, PipelineState, TIDStatus
from services.human_review import HumanReviewCheckpoint


class DeepThoughtPipeline:
    def __init__(self):
        self.forager = ForagerAgent()
        self.maverick = MaverickAgent()
        self.professor = ProfessorAgent()
        self.patent_shield = PatentShieldAgent()
        self.reality_checker = RealityCheckerAgent()
        self.debate_panel = DebatePanelAgent()
        self.human_review = HumanReviewCheckpoint() if settings.human_review_checkpoint_enabled else None

    def run(self, state: PipelineState, n_drafts: int = 3, top_k_voids: int = 5) -> PipelineState:
        state.run_status = "RUNNING"
        state.metadata.setdefault("stage_status", {})
        logger.info(
            "Pipeline run started | run_id={} | domain={} | target={} | n_drafts={} | top_k_voids={}",
            state.run_id,
            state.domain,
            state.target,
            n_drafts,
            top_k_voids,
        )

        try:
            state = self.forager.run(state, top_k=top_k_voids)
            state.metadata["stage_status"]["forager"] = "OK"
        except Exception as exc:
            return self._mark_failure(state, "forager", exc)

        if not self._has_forager_evidence(state):
            state.run_status = "RETRY_PENDING"
            state.last_error = "No topological voids found; skipped draft generation"
            state.metadata["rejected_reason"] = state.last_error
            state.metadata["stage_status"]["maverick"] = "SKIPPED_NO_VOIDS"
            state.metadata["stage_status"]["patent_shield"] = "SKIPPED_NO_VOIDS"
            state.metadata["stage_status"]["reality_checker"] = "SKIPPED_NO_VOIDS"
            state.metadata["stage_status"]["debate_panel"] = "SKIPPED_NO_VOIDS"
            logger.warning(
                "Pipeline short-circuited after Forager | run_id={} | reason={}",
                state.run_id,
                state.last_error,
            )
            return state

        try:
            if settings.pipeline_parallel_mode and n_drafts > 1:
                # Apply backpressure: cap n_drafts to prevent resource exhaustion
                effective_drafts = n_drafts
                if n_drafts > settings.max_maverick_queue_depth:
                    effective_drafts = settings.max_maverick_queue_depth
                    logger.warning(
                        "Maverick queue backpressure applied | run_id={} | requested={} | capped={}",
                        state.run_id,
                        n_drafts,
                        effective_drafts,
                    )
                state = self._run_maverick_parallel(state, n_drafts=effective_drafts)
            else:
                state = self.maverick.run(state, n_drafts=n_drafts)
            state.metadata["stage_status"]["maverick"] = "OK"
        except Exception as exc:
            return self._mark_failure(state, "maverick", exc)

        state.tid_statuses = [
            TIDStatus(draft_index=i, title=d.title, status="DRAFTED")
            for i, d in enumerate(state.drafts)
        ]

        # Professor pre-flight review: fast triage before expensive stages
        try:
            state = self.professor.run(state)
            state.metadata["stage_status"]["professor"] = "OK"
        except Exception as exc:
            return self._mark_failure(state, "professor", exc)

        # Short-circuit if Professor rejected all drafts
        if not state.drafts:
            state.run_status = "REJECTED"
            state.last_error = "All drafts rejected by professor pre-flight review"
            state.metadata["rejected_reason"] = state.last_error
            for t in state.tid_statuses:
                t.status = "REJECTED"
                t.last_error = state.last_error
            logger.warning(
                "Pipeline short-circuited after Professor | run_id={} | reason={}",
                state.run_id,
                state.last_error,
            )
            return state

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

        # Handle debate panel verdict with revision loop
        if state.debate_result:
            if state.debate_result.final_verdict == "APPROVE":
                state.run_status = "APPROVED"
                logger.info(
                    "Pipeline completed successfully | run_id={} | verdict=APPROVED",
                    state.run_id
                )

            elif state.debate_result.final_verdict == "REJECT":
                state.run_status = "REJECTED"
                state.last_error = "Debate Panel rejected the drafts"
                for t in state.tid_statuses:
                    t.status = "REJECTED"
                logger.warning(
                    "Pipeline rejected by debate panel | run_id={}",
                    state.run_id
                )

            elif state.debate_result.final_verdict == "REVISE":
                # NEW: Automated revision loop
                debate_revision_round = 0
                max_rounds = settings.max_debate_revision_rounds

                logger.info(
                    "Debate Panel requested revisions | run_id={} | max_rounds={}",
                    state.run_id, max_rounds
                )

                while (
                    state.debate_result.final_verdict == "REVISE"
                    and debate_revision_round < max_rounds
                ):
                    debate_revision_round += 1
                    logger.info(
                        "Starting debate revision round | run_id={} | round={}/{}",
                        state.run_id, debate_revision_round, max_rounds
                    )

                    # Extract actionable feedback from specialist reviews
                    revision_feedback = self.debate_panel.extract_revision_feedback(state)

                    # Store feedback in metadata for Maverick to use
                    if "debate_revision_feedback" not in state.metadata:
                        state.metadata["debate_revision_feedback"] = []
                    state.metadata["debate_revision_feedback"].append({
                        "round": debate_revision_round,
                        "feedback": revision_feedback
                    })

                    # Aggregate feedback for Maverick (most recent round)
                    state.metadata["conference_review_feedback"] = revision_feedback

                    # Re-run Maverick with feedback (single targeted revision)
                    logger.info(
                        "Re-running Maverick with debate feedback | run_id={} | round={}",
                        state.run_id, debate_revision_round
                    )
                    try:
                        state = self.maverick.run(state, n_drafts=n_drafts)
                    except Exception as exc:
                        logger.warning(
                            "Maverick failed during debate revision | run_id={} | round={} | error={}",
                            state.run_id, debate_revision_round, exc
                        )
                        state.run_status = "REJECTED"
                        state.last_error = f"Maverick failed during debate revision: {exc}"
                        break

                    if not state.drafts:
                        logger.warning(
                            "Maverick produced no drafts after revision | run_id={} | round={}",
                            state.run_id, debate_revision_round
                        )
                        state.run_status = "REJECTED"
                        state.last_error = "Maverick failed to produce drafts after debate revision"
                        break

                    # Re-run Professor (fast-fail gate)
                    try:
                        state = self.professor.run(state)
                    except Exception as exc:
                        logger.warning(
                            "Professor failed during debate revision | run_id={} | round={} | error={}",
                            state.run_id, debate_revision_round, exc
                        )
                        state.run_status = "REJECTED"
                        state.last_error = f"Professor failed during debate revision: {exc}"
                        break

                    if not state.drafts:  # Professor rejected all
                        logger.warning(
                            "Professor rejected all revised drafts | run_id={} | round={}",
                            state.run_id, debate_revision_round
                        )
                        state.run_status = "REJECTED"
                        state.last_error = "All revised drafts rejected by professor"
                        break

                    # Re-run Patent Shield
                    try:
                        state = self.patent_shield.run(state)
                    except Exception as exc:
                        logger.warning(
                            "Patent Shield failed during debate revision | run_id={} | round={} | error={}",
                            state.run_id, debate_revision_round, exc
                        )
                        # Continue - Patent Shield failure is not fatal

                    # Re-run Reality Checker
                    logger.info(
                        "Re-running Reality Checker | run_id={} | round={}",
                        state.run_id, debate_revision_round
                    )
                    try:
                        state = self.reality_checker.run(state)
                    except Exception as exc:
                        logger.warning(
                            "Reality Checker failed during debate revision | run_id={} | round={} | error={}",
                            state.run_id, debate_revision_round, exc
                        )
                        state.run_status = "REJECTED"
                        state.last_error = f"Reality Checker failed during debate revision: {exc}"
                        break

                    if state.run_status == "REJECTED":
                        logger.warning(
                            "Reality Checker rejected revised drafts | run_id={} | round={}",
                            state.run_id, debate_revision_round
                        )
                        break

                    # Re-run Debate Panel
                    logger.info(
                        "Re-running Debate Panel | run_id={} | round={}",
                        state.run_id, debate_revision_round
                    )
                    try:
                        state = self.debate_panel.run(state)
                    except Exception as exc:
                        logger.warning(
                            "Debate Panel failed during revision | run_id={} | round={} | error={}",
                            state.run_id, debate_revision_round, exc
                        )
                        state.run_status = "REJECTED"
                        state.last_error = f"Debate Panel failed during revision: {exc}"
                        break

                    # Check new verdict
                    if state.debate_result.final_verdict == "APPROVE":
                        state.run_status = "APPROVED"
                        logger.info(
                            "Drafts approved after revision | run_id={} | round={}",
                            state.run_id, debate_revision_round
                        )
                        break
                    elif state.debate_result.final_verdict == "REJECT":
                        state.run_status = "REJECTED"
                        state.last_error = "Debate Panel rejected revised drafts"
                        for t in state.tid_statuses:
                            t.status = "REJECTED"
                        logger.warning(
                            "Debate Panel rejected after revision | run_id={} | round={}",
                            state.run_id, debate_revision_round
                        )
                        break
                    # else: continue loop (still REVISE)

                # After max rounds, if still REVISE
                if state.debate_result.final_verdict == "REVISE" and debate_revision_round >= max_rounds:
                    state.run_status = "REJECTED"
                    state.last_error = f"Failed to satisfy debate panel after {max_rounds} revision rounds"
                    for t in state.tid_statuses:
                        t.status = "REJECTED"
                    logger.warning(
                        "Debate revision exhausted | run_id={} | rounds={}",
                        state.run_id, max_rounds
                    )

            else:
                # Fallback for unexpected verdict
                state.run_status = "RETRY_PENDING"

        # Handle stage failures
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

        if self.human_review:
            state = self.human_review.apply(state)

        logger.info(
            "Pipeline run finished | run_id={} | status={} | failed_stages={} | selected_draft_index={}",
            state.run_id,
            state.run_status,
            ",".join(state.failed_stages) if state.failed_stages else "none",
            state.selected_draft_index,
        )

        return state

    @staticmethod
    def _has_forager_evidence(state: PipelineState) -> bool:
        has_voids = bool(state.void_statuses)
        has_context = bool((state.topological_void_context or "").strip())
        return has_voids and has_context

    def _run_maverick_parallel(self, state: PipelineState, n_drafts: int) -> PipelineState:
        """Run Maverick workers in parallel, each generating 1 draft, then merge results."""
        workers = min(n_drafts, max(1, settings.maverick_workers))

        def _worker(_idx: int) -> List[DraftIdea]:
            worker_state = replace(
                state,
                drafts=[],
                failed_stages=[],
                metadata=dict(state.metadata),
            )
            worker_state = self.maverick.run(worker_state, n_drafts=1)
            return worker_state.drafts

        all_drafts: List[DraftIdea] = []
        errors: List[str] = []
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(_worker, i) for i in range(n_drafts)]
            for f in futures:
                try:
                    all_drafts.extend(f.result())
                except Exception as exc:
                    errors.append(str(exc))
                    logger.warning(
                        "Parallel Maverick worker failed | run_id={} | error={}",
                        state.run_id,
                        exc,
                    )

        if not all_drafts:
            raise RuntimeError(
                f"All {n_drafts} parallel Maverick workers produced no drafts. "
                + (f"Errors: {'; '.join(errors)}" if errors else "")
            )

        state.drafts = all_drafts
        state.metadata["draft_count"] = len(all_drafts)
        state.metadata["maverick_generation"] = {
            "requested_drafts": n_drafts,
            "produced_drafts": len(all_drafts),
            "status": "OK",
            "parallel_workers": workers,
        }
        logger.info(
            "Parallel Maverick finished | run_id={} | workers={} | produced={} | failed_workers={}",
            state.run_id,
            workers,
            len(all_drafts),
            len(errors),
        )
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
        claim_assessments = self._assess_draft_claims(state=state, draft_index=idx)
        claim_confidence_lines = [
            f"Claim {i}: confidence={item.confidence:.2f}, conflict_score={item.conflict_score:.2f}"
            for i, item in enumerate(claim_assessments, start=1)
        ]
        prior_art_conflict_lines = [
            f"Claim {i} conflicts with: {', '.join(item.conflict_hits)}"
            for i, item in enumerate(claim_assessments, start=1)
            if item.conflict_hits
        ]

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
                claim_confidence=claim_confidence_lines,
                prior_art_conflicts=prior_art_conflict_lines,
                risks_and_mitigations=draft.risks_and_mitigations,
                references=draft.references,
            ),
        )

        out_dir = Path(output_dir)
        state.output_paths = report.save_extended(out_dir)

        idx = max(0, min(state.selected_draft_index, len(state.tid_statuses) - 1))
        if state.tid_statuses:
            for t in state.tid_statuses:
                if t.status not in {"REJECTED"}:
                    t.status = "NOT_SELECTED"
            chosen = state.tid_statuses[idx]
            chosen.output_markdown = state.output_paths.get("markdown", "")
            chosen.output_html = state.output_paths.get("html", "")
            chosen.output_docx = state.output_paths.get("docx", "")
            chosen.output_pdf = state.output_paths.get("pdf", "")
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

    def _assess_draft_claims(self, state: PipelineState, draft_index: int):
        draft = state.drafts[draft_index]
        prior_art_corpus = list(state.existing_solutions)

        if 0 <= draft_index < len(state.patent_checks):
            prior_art_corpus.extend(state.patent_checks[draft_index].prior_art_hits)

        prior_art_corpus.extend(draft.references)

        return assess_claims(
            claims=draft.draft_claims,
            prior_art_corpus=prior_art_corpus,
            conflict_threshold=settings.patent_conflict_threshold,
        )

    def _mark_failure(self, state: PipelineState, stage: str, exc: Exception) -> PipelineState:
        state.failed_stages.append(stage)
        state.last_error = f"{stage}: {exc}"
        state.metadata.setdefault("stage_status", {})
        state.metadata.setdefault("stage_errors", {})
        state.metadata["stage_status"][stage] = "FAILED"
        state.metadata["stage_errors"][stage] = str(exc)
        logger.error(
            "Pipeline stage failed | run_id={} | stage={} | reason={}",
            state.run_id,
            stage,
            str(exc),
        )
        lowered = str(exc).lower()
        if "timed out" in lowered or "timeout" in lowered:
            state.metadata["fatal_flaw"] = "Model timeout under committee SLA"
        state.run_status = "REJECTED" if settings.reject_on_stage_failure else "RETRY_PENDING"
        for t in state.tid_statuses:
            if t.status not in {"APPROVED_AND_EXPORTED", "REJECTED"}:
                t.status = "REJECTED" if settings.reject_on_stage_failure else "RETRY_PENDING"
                t.last_error = state.last_error
        return state
