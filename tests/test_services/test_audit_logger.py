from __future__ import annotations

import json
from pathlib import Path

from agents.state import PipelineState
from services.audit_logger import PipelineAuditLogger
from services.io_writer import IOWriterService


def test_append_run_audit_writes_jsonl(tmp_path: Path) -> None:
    # Start IO writer service for this test
    IOWriterService.start()

    try:
        path = tmp_path / "audit.jsonl"
        logger = PipelineAuditLogger(file_path=path)
        state = PipelineState(domain="linux_kernel", target="sched latency")
        state.run_status = "APPROVED"
        state.metadata["stage_status"] = {"forager": "OK"}

        out = logger.append_run_audit(state)

        # Flush to ensure write completes before reading
        IOWriterService.flush(timeout=5.0)

        assert out == path
        rows = path.read_text(encoding="utf-8").splitlines()
        assert len(rows) == 1
        record = json.loads(rows[0])
        assert record["run_id"] == state.run_id
        assert record["run_status"] == "APPROVED"
        assert record["stage_status"]["forager"] == "OK"
    finally:
        IOWriterService.shutdown(timeout=5.0)
