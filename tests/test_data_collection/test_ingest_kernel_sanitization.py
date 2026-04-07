from __future__ import annotations

from scripts.ingest_kernel import sanitize_chunk_for_embedding


def test_sanitize_chunk_for_embedding_removes_metadata_headers() -> None:
    content = """file_path: kernel/sched/core.c
author: someone@example.com
static void wake_affine(void) {
    return;
}
"""
    metadata = {
        "file_path": "kernel/sched/core.c",
        "author": "someone@example.com",
    }

    cleaned = sanitize_chunk_for_embedding(content, metadata)

    assert cleaned.startswith("static void wake_affine")
    assert "file_path:" not in cleaned
    assert "author:" not in cleaned


def test_sanitize_chunk_for_embedding_keeps_plain_code_unchanged() -> None:
    content = "static int sched_balance(void) { return 0; }"
    metadata = {"file_path": "kernel/sched/fair.c"}

    cleaned = sanitize_chunk_for_embedding(content, metadata)

    assert cleaned == content