from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from services.query_service import QueryService


@dataclass
class _FakeDocument:
    doc_id: str
    content: str
    metadata: Dict[str, Any]


@dataclass
class _FakeCollection:
    value: str


@dataclass
class _FakeRetrieved:
    document: _FakeDocument
    collection: _FakeCollection
    similarity: float


class _FakeStore:
    def query(self, query_text: str, collections=None, n_results: int = 5, where=None) -> List[_FakeRetrieved]:
        return [
            _FakeRetrieved(
                document=_FakeDocument(
                    doc_id="doc-1",
                    content="Linux scheduler balancing with x86 telemetry and cache pressure.",
                    metadata={"source": "kernel"},
                ),
                collection=_FakeCollection("kernel_source"),
                similarity=0.88,
            ),
            _FakeRetrieved(
                document=_FakeDocument(
                    doc_id="doc-2",
                    content="NUMA allocator feedback and lock contention mitigation.",
                    metadata={"source": "paper"},
                ),
                collection=_FakeCollection("papers"),
                similarity=0.74,
            ),
        ][:n_results]


def test_query_service_retrieve_returns_store_items() -> None:
    service = QueryService(store=_FakeStore())
    items = service.retrieve(query="scheduler", top_k=2)

    assert len(items) == 2
    assert items[0].document.doc_id == "doc-1"


def test_query_service_answer_contains_sources_and_context() -> None:
    service = QueryService(store=_FakeStore())
    result = service.answer(query="x86 scheduler telemetry", top_k=2)

    assert result.query == "x86 scheduler telemetry"
    assert result.sources
    assert result.context_chunks
    assert "RAG summary" in result.answer
