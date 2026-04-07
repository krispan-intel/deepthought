"""
services/audit_logger.py

Phase 6 audit logger:
- Emits one immutable JSONL record per pipeline run.
- Captures inputs, stage outcomes, outputs, and key metadata.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

from agents.state import PipelineState
from configs.settings import settings


class PipelineAuditLogger:
    def __init__(self, file_path: Path | None = None):
        self.file_path = file_path or settings.audit_log_path
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def append_run_audit(self, state: PipelineState) -> Path:
        record = self._build_record(state)
        with self.file_path.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(record, ensure_ascii=False) + "\n")
        return self.file_path

    @staticmethod
    def _build_record(state: PipelineState) -> Dict:
        return {
            "audit_timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "run_id": state.run_id,
            "started_at": state.started_at.isoformat(timespec="seconds"),
            "run_status": state.run_status,
            "domain": state.domain,
            "target": state.target,
            "failed_stages": list(state.failed_stages),
            "last_error": state.last_error,
            "input": state.metadata.get("input", {}),
            "stage_status": state.metadata.get("stage_status", {}),
            "void_statuses": [asdict(v) for v in state.void_statuses],
            "tid_statuses": [asdict(t) for t in state.tid_statuses],
            "output_paths": dict(state.output_paths),
            "debate_result": asdict(state.debate_result) if state.debate_result else None,
            "metadata": state.metadata,
        }
