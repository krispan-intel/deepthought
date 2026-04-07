import numpy as np

from vectordb.store import CollectionName, DeepThoughtVectorStore, Document, RetrievedDocument, SPARSE_SYNC_BATCH_SIZE


def make_doc(metadata, doc_id="doc-1"):
    return RetrievedDocument(
        document=Document(content="int foo(void) { return 0; }", metadata=metadata, doc_id=doc_id),
        embedding=np.array([0.1, 0.2], dtype=np.float32),
        distance=0.1,
        collection=CollectionName.KERNEL_SOURCE,
    )


def test_to_tech_vector_prefers_metadata_name():
    doc = make_doc({"name": "preempt_wakeup_action", "file_path": "kernel/sched/fair.c", "start_line": 100})
    tech = doc.to_tech_vector()
    assert tech.label == "preempt_wakeup_action"


def test_to_tech_vector_skips_unknown_and_falls_back_to_path():
    doc = make_doc({"name": "unknown", "file_path": "kernel/sched/fair.c", "start_line": 777})
    tech = doc.to_tech_vector()
    assert tech.label == "kernel/sched/fair.c:777"


def test_to_tech_vector_uses_doc_id_when_no_better_label_exists():
    doc = make_doc({}, doc_id="abc123")
    tech = doc.to_tech_vector()
    assert tech.label == "abc123"


class _FakeCollection:
    def __init__(self, total: int):
        self.total = total
        self.calls = []

    def count(self):
        return self.total

    def get(self, limit, offset, include):
        self.calls.append({"limit": limit, "offset": offset, "include": include})
        end = min(offset + limit, self.total)
        ids = [f"doc-{index}" for index in range(offset, end)]
        return {
            "ids": ids,
            "documents": [f"content-{doc_id}" for doc_id in ids],
            "metadatas": [{"title": f"title-{doc_id}"} for doc_id in ids],
        }


def test_collection_records_batches_large_sparse_sync_reads():
    store = DeepThoughtVectorStore.__new__(DeepThoughtVectorStore)
    fake = _FakeCollection(total=SPARSE_SYNC_BATCH_SIZE * 2 + 17)
    store._collections = {CollectionName.KERNEL_SOURCE: fake}

    records = store._collection_records(CollectionName.KERNEL_SOURCE)

    assert len(records) == fake.total
    assert len(fake.calls) == 3
    assert fake.calls[0]["limit"] == SPARSE_SYNC_BATCH_SIZE
    assert fake.calls[1]["offset"] == SPARSE_SYNC_BATCH_SIZE
    assert fake.calls[2]["limit"] == 17


def test_prepare_hybrid_candidates_filters_missing_and_noisy_labels():
    store = DeepThoughtVectorStore.__new__(DeepThoughtVectorStore)
    candidates = [
        make_doc({"name": "do_sched_yield"}, doc_id="good-1"),
        make_doc({"title": "resource"}, doc_id="bad-1"),
        make_doc({"file_path": "kernel/sched/core.c"}, doc_id="bad-2"),
        make_doc({"name": "676ccb225f0fd11bc101ebd806a36644"}, doc_id="bad-3"),
    ]

    filtered, rejected = store._prepare_hybrid_candidates(candidates)

    assert len(filtered) == 1
    assert filtered[0].document.doc_id == "good-1"
    assert rejected["missing_semantic_label"] == 1
    assert rejected["noisy_label"] == 2