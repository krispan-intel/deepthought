from __future__ import annotations

import numpy as np

from vectordb.store import CollectionName, Document, RetrievedDocument
from scripts.run_db_contamination_audit import detect_contamination


def _item(content: str, metadata: dict, doc_id: str = "doc-1") -> RetrievedDocument:
    return RetrievedDocument(
        document=Document(content=content, metadata=metadata, doc_id=doc_id),
        embedding=np.array([0.1, 0.2], dtype=np.float32),
        distance=0.0,
        collection=CollectionName.KERNEL_SOURCE,
    )


def test_detect_contamination_flags_metadata_header_content() -> None:
    item = _item(
        content="file_path: kernel/sched/core.c\nstatic void wake_affine(void) {}",
        metadata={"name": "wake_affine", "file_path": "kernel/sched/core.c"},
    )

    reasons = detect_contamination(item)

    assert "metadata_header_in_content" in reasons


def test_detect_contamination_flags_hash_and_missing_semantics() -> None:
    item = _item(
        content="plain technical text",
        metadata={},
        doc_id="676ccb225f0fd11bc101ebd806a36644",
    )

    reasons = detect_contamination(item)

    assert "hash_label" in reasons
    assert "missing_semantic_metadata" in reasons


def test_detect_contamination_accepts_clean_kernel_function() -> None:
    item = _item(
        content="static int wake_affine_idle(int cpu) { return cpu; }",
        metadata={"name": "wake_affine_idle", "file_path": "kernel/sched/fair.c"},
    )

    reasons = detect_contamination(item)

    assert reasons == []