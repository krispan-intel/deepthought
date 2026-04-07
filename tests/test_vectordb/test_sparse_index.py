from __future__ import annotations

from pathlib import Path

from vectordb.sparse_index import SparseCooccurrenceIndex


def test_extract_top_tokens_filters_noise() -> None:
    tokens = SparseCooccurrenceIndex.extract_top_tokens(
        "Linux scheduler feedback loop for cache pressure rebalance and scheduler tuning"
    )
    assert "scheduler" in tokens
    assert "feedback" in tokens
    assert "linux" not in tokens


def test_sparse_sidecar_detects_global_cooccurrence(tmp_path: Path) -> None:
    index = SparseCooccurrenceIndex(tmp_path / "sidecar.sqlite3")
    index.upsert_records(
        [
            {
                "doc_id": "1",
                "label": "doc1",
                "content": "scheduler feedback uses cache pressure hints",
            },
            {
                "doc_id": "2",
                "label": "doc2",
                "content": "allocator telemetry coordinates numa balancing",
            },
        ],
        collection="kernel_source",
    )

    assert index.has_cooccurrence(["scheduler"], ["cache"], ["kernel_source"]) is True
    assert index.has_cooccurrence(["scheduler"], ["numa"], ["kernel_source"]) is False