"""
services/void_tracker.py

Phase 6 incremental void tracking:
- Records discovered voids for each run.
- Computes new vs recurring void counts over time.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Set

from agents.state import PipelineState, VoidStatus
from configs.settings import settings


class IncrementalVoidTracker:
    def __init__(self, file_path: Path | None = None):
        self.file_path = file_path or settings.void_tracking_path
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def record_run(self, state: PipelineState) -> Dict[str, int]:
        seen = self._load_seen_signatures()
        current_signatures = {self._signature(v) for v in state.void_statuses}
        new_voids = current_signatures - seen
        recurring_voids = current_signatures.intersection(seen)

        timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self.file_path.open("a", encoding="utf-8") as fp:
            for void in state.void_statuses:
                fp.write(
                    json.dumps(
                        {
                            "timestamp": timestamp,
                            "run_id": state.run_id,
                            "domain": state.domain,
                            "target": state.target,
                            "void_signature": self._signature(void),
                            "void_id": void.void_id,
                            "label": void.label,
                            "mmr_score": void.mmr_score,
                            "relevance_score": void.relevance_score,
                            "novelty_score": void.novelty_score,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )

        return {
            "tracked_voids": len(current_signatures),
            "new_voids": len(new_voids),
            "recurring_voids": len(recurring_voids),
            "historical_voids": len(seen.union(current_signatures)),
        }

    def _load_seen_signatures(self) -> Set[str]:
        if not self.file_path.exists():
            return set()

        seen: Set[str] = set()
        for line in self.file_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            signature = str(row.get("void_signature", "")).strip()
            if signature:
                seen.add(signature)
        return seen

    @staticmethod
    def _signature(void: VoidStatus) -> str:
        base = f"{void.void_id}|{void.label}".strip().lower()
        return base
