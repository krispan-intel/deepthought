import numpy as np

from vectordb.store import CollectionName, Document, RetrievedDocument


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