"""
services/pipeline_service.py

Service wrapper for running the DeepThought multi-agent pipeline.
"""

from __future__ import annotations

from typing import List, Optional

from agents.pipeline import DeepThoughtPipeline
from agents.state import PipelineState
from configs.settings import settings
from services.audit_logger import PipelineAuditLogger
from services.void_tracker import IncrementalVoidTracker


class PipelineService:
    def __init__(self):
        self.pipeline = DeepThoughtPipeline()
        self.audit_logger = PipelineAuditLogger() if settings.audit_log_enabled else None
        self.void_tracker = IncrementalVoidTracker() if settings.void_tracking_enabled else None

    def run(
        self,
        domain: str,
        target: str,
        existing_solutions: Optional[List[str]] = None,
        collection_names: Optional[List[str]] = None,
        domain_filter: str | None = None,
        lambda_val: float = 0.7,
        n_drafts: int = 3,
        top_k_voids: int = 5,
        output_dir: str = "output/generated",
        tid_prefix: str = "TID-MA",
    ) -> PipelineState:
        state = PipelineState(
            domain=domain,
            target=target,
            existing_solutions=existing_solutions or [],
            collection_names=collection_names or [],
            domain_filter=domain_filter,
            lambda_val=lambda_val,
        )
        state.metadata["input"] = {
            "domain": domain,
            "target": target,
            "existing_solutions": existing_solutions or [],
            "collection_names": collection_names or [],
            "domain_filter": domain_filter,
            "lambda_val": lambda_val,
            "n_drafts": n_drafts,
            "top_k_voids": top_k_voids,
            "output_dir": output_dir,
            "tid_prefix": tid_prefix,
        }

        state = self.pipeline.run(
            state=state,
            n_drafts=n_drafts,
            top_k_voids=top_k_voids,
        )
        state = self.pipeline.export_reports(
            state=state,
            output_dir=output_dir,
            tid_prefix=tid_prefix,
        )

        if self.void_tracker:
            state.metadata["void_tracking"] = self.void_tracker.record_run(state)

        if self.audit_logger:
            audit_path = self.audit_logger.append_run_audit(state)
            state.metadata["audit_log_path"] = str(audit_path)

        return state
