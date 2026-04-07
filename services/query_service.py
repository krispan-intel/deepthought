"""
services/query_service.py

Basic RAG pipeline with LlamaIndex (Phase 1):
- Retrieve from local vector store.
- Build node chunks via LlamaIndex SentenceSplitter.
- Rank chunks with lightweight lexical overlap.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from vectordb.store import CollectionName, DeepThoughtVectorStore


@dataclass
class QueryAnswer:
    query: str
    answer: str
    context_chunks: List[str]
    sources: List[Dict[str, Any]]


class QueryService:
    def __init__(self, store: DeepThoughtVectorStore | None = None):
        self.store = store or DeepThoughtVectorStore()

    def retrieve(
        self,
        query: str,
        collection_names: Optional[List[str]] = None,
        top_k: int = 5,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[Any]:
        collections = None
        if collection_names:
            collections = [CollectionName(name) for name in collection_names]

        return self.store.query(
            query_text=query,
            collections=collections,
            n_results=max(1, int(top_k)),
            where=where,
        )

    def answer(
        self,
        query: str,
        collection_names: Optional[List[str]] = None,
        top_k: int = 5,
    ) -> QueryAnswer:
        retrieved = self.retrieve(
            query=query,
            collection_names=collection_names,
            top_k=top_k,
        )
        chunks = self._build_ranked_chunks(query=query, retrieved=retrieved)

        if chunks:
            answer = "\n".join(
                [
                    "RAG summary (LlamaIndex chunks):",
                    f"- Query: {query}",
                    f"- Top context: {chunks[0][:220]}",
                    "- Recommendation: validate against kernel/x86 constraints before draft promotion.",
                ]
            )
        else:
            answer = (
                "No relevant context found in local corpus for this query. "
                "Expand collection coverage or ingest more domain data first."
            )

        sources = [
            {
                "doc_id": item.document.doc_id,
                "collection": item.collection.value,
                "similarity": round(float(item.similarity), 4),
                "metadata": item.document.metadata,
            }
            for item in retrieved
        ]

        return QueryAnswer(
            query=query,
            answer=answer,
            context_chunks=chunks,
            sources=sources,
        )

    def _build_ranked_chunks(self, query: str, retrieved: List[Any]) -> List[str]:
        if not retrieved:
            return []

        try:
            from llama_index.core import Document as LlamaDocument
            from llama_index.core.node_parser import SentenceSplitter
        except Exception:
            # Fallback if LlamaIndex is not available at runtime.
            return [item.document.content[:500] for item in retrieved]

        docs = [
            LlamaDocument(
                text=item.document.content,
                metadata=item.document.metadata,
                doc_id=item.document.doc_id,
            )
            for item in retrieved
        ]

        splitter = SentenceSplitter(chunk_size=380, chunk_overlap=40)
        nodes = splitter.get_nodes_from_documents(docs)

        q_tokens = self._tokenize(query)
        scored: List[tuple[float, str]] = []
        for node in nodes:
            text = (node.text or "").strip()
            if not text:
                continue
            score = self._overlap_score(q_tokens, self._tokenize(text))
            scored.append((score, text))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [text for _, text in scored[: max(1, min(5, len(scored)))]]

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        cleaned = (
            (text or "")
            .lower()
            .replace("/", " ")
            .replace("-", " ")
            .replace(",", " ")
            .replace(".", " ")
        )
        return {tok for tok in cleaned.split() if len(tok) >= 3}

    @staticmethod
    def _overlap_score(a: set[str], b: set[str]) -> float:
        if not a or not b:
            return 0.0
        union = a.union(b)
        if not union:
            return 0.0
        return len(a.intersection(b)) / len(union)
