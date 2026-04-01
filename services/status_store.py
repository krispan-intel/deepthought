"""
services/status_store.py

Persist pipeline run statuses and enable retry of failed runs.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from configs.settings import settings
from agents.state import PipelineState


class PipelineStatusStore:
    def __init__(self, file_path: str | None = None):
        self.file_path = Path(file_path) if file_path else settings.data_processed_path / "pipeline_runs.jsonl"
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, state: PipelineState) -> Path:
        record = self._to_record(state)
        with self.file_path.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(record, ensure_ascii=False) + "\n")
        return self.file_path

    def latest_retry_input(self) -> Optional[Dict[str, Any]]:
        if not self.file_path.exists():
            return None

        lines = self.file_path.read_text(encoding="utf-8").splitlines()
        for line in reversed(lines):
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("run_status") == "RETRY_PENDING":
                return row.get("input")
        return None

    def _to_record(self, state: PipelineState) -> Dict[str, Any]:
        return {
            "run_id": state.run_id,
            "timestamp": datetime.utcnow().isoformat(timespec="seconds"),
            "run_status": state.run_status,
            "failed_stages": state.failed_stages,
            "last_error": state.last_error,
            "input": state.metadata.get("input", {}),
            "void_statuses": [asdict(v) for v in state.void_statuses],
            "tid_statuses": [asdict(t) for t in state.tid_statuses],
            "output_paths": state.output_paths,
            "debate_result": asdict(state.debate_result) if state.debate_result else None,
        }
