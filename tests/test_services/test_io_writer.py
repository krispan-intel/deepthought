"""
Tests for IOWriterService
"""

from __future__ import annotations

import json
from pathlib import Path

from services.io_writer import IOWriterService


def test_write_jsonl_basic(tmp_path: Path) -> None:
    """Test basic JSONL write operation."""
    IOWriterService.start()

    try:
        file_path = tmp_path / "test.jsonl"
        record = {"test": "data", "value": 123}

        IOWriterService.write_jsonl(file_path, record)
        IOWriterService.flush(timeout=5.0)

        assert file_path.exists()
        lines = file_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["test"] == "data"
        assert parsed["value"] == 123
    finally:
        IOWriterService.shutdown(timeout=5.0)


def test_write_multiple_jsonl(tmp_path: Path) -> None:
    """Test multiple JSONL writes to the same file."""
    IOWriterService.start()

    try:
        file_path = tmp_path / "test.jsonl"

        IOWriterService.write_jsonl(file_path, {"id": 1})
        IOWriterService.write_jsonl(file_path, {"id": 2})
        IOWriterService.write_jsonl(file_path, {"id": 3})
        IOWriterService.flush(timeout=5.0)

        lines = file_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 3
        assert json.loads(lines[0])["id"] == 1
        assert json.loads(lines[1])["id"] == 2
        assert json.loads(lines[2])["id"] == 3
    finally:
        IOWriterService.shutdown(timeout=5.0)


def test_write_text_basic(tmp_path: Path) -> None:
    """Test basic text write operation."""
    IOWriterService.start()

    try:
        file_path = tmp_path / "test.txt"
        content = "Hello, World!\n"

        IOWriterService.write_text(file_path, content, mode="w")
        IOWriterService.flush(timeout=5.0)

        assert file_path.exists()
        assert file_path.read_text(encoding="utf-8") == content
    finally:
        IOWriterService.shutdown(timeout=5.0)


def test_fallback_when_not_started(tmp_path: Path) -> None:
    """Test that writes fall back to direct I/O when service not started."""
    # Ensure service is not running
    IOWriterService.shutdown(timeout=1.0)

    file_path = tmp_path / "fallback.jsonl"
    record = {"fallback": "test"}

    # Should not raise, should write directly
    IOWriterService.write_jsonl(file_path, record)

    assert file_path.exists()
    lines = file_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["fallback"] == "test"
