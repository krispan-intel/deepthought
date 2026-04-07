"""
vectordb/store.py

DeepThought Vector Store
Manages all knowledge collections for the RAG pipeline.
Integrates with the DeepThought Equation for MMR retrieval.
"""

from __future__ import annotations

import hashlib
import random
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any

import chromadb
import numpy as np
from chromadb.config import Settings as ChromaSettings
from loguru import logger

from vectordb.embedder import create_embedder, LocalEmbedder
from configs.settings import settings
from core.deepthought_equation import (
    DeepThoughtEquation,
    TechVector,
    VoidLandscape,
)
from vectordb.sparse_index import SparseCooccurrenceIndex


# ─────────────────────────────────────────────────────────────────
# Collection Definitions
# ─────────────────────────────────────────────────────────────────

class CollectionName(str, Enum):
    """
    All knowledge collections in DeepThought.
    Each collection holds a different type of technical knowledge.
    """
    HARDWARE_SPECS    = "hardware_specs"
    KERNEL_SOURCE     = "kernel_source"
    KERNEL_DISCUSSION = "kernel_discussion"
    USERSPACE_LIBS    = "userspace_libs"
    ANDROID           = "android"
    PAPERS            = "papers"
    PATENTS           = "patents"


COLLECTION_METADATA = {
    CollectionName.HARDWARE_SPECS: {
        "description": "x86 ISA, Intel SDM, CXL, JEDEC specs",
        "priority": 1,
        "update_freq": "on_release",
    },
    CollectionName.KERNEL_SOURCE: {
        "description": "Linux kernel C/Rust source code",
        "priority": 1,
        "update_freq": "daily",
    },
    CollectionName.KERNEL_DISCUSSION: {
        "description": "LKML threads, commit messages, patch reviews",
        "priority": 2,
        "update_freq": "daily",
    },
    CollectionName.USERSPACE_LIBS: {
        "description": "glibc, LLVM, jemalloc, DPDK, io_uring",
        "priority": 2,
        "update_freq": "weekly",
    },
    CollectionName.ANDROID: {
        "description": "AOSP, Android kernel, Bionic, ART, Binder",
        "priority": 2,
        "update_freq": "weekly",
    },
    CollectionName.PAPERS: {
        "description": "ArXiv, ISCA, OSDI, ASPLOS papers",
        "priority": 2,
        "update_freq": "daily",
    },
    CollectionName.PATENTS: {
        "description": "USPTO, EPO, WIPO patents",
        "priority": 3,
        "update_freq": "weekly",
    },
}


# ─────────────────────────────────────────────────────────────────
# Document Model
# ─────────────────────────────────────────────────────────────────

class Document:
    """A document stored in the vector store."""

    def __init__(
        self,
        content: str,
        metadata: Dict[str, Any],
        doc_id: Optional[str] = None,
    ):
        self.content = content
        self.metadata = metadata
        self.doc_id = doc_id or self._generate_id()

    def _generate_id(self) -> str:
        """Generate stable ID from content hash."""
        return hashlib.sha256(
            self.content.encode()
        ).hexdigest()[:16]

    def __repr__(self) -> str:
        source = self.metadata.get("source", "unknown")
        return f"Document(id={self.doc_id}, source={source})"


class RetrievedDocument:
    """A document retrieved from the vector store with scores."""

    INVALID_LABELS = {"unknown", "unnamed", "none", "null", "n/a"}

    def __init__(
        self,
        document: Document,
        embedding: np.ndarray,
        distance: float,
        collection: CollectionName,
    ):
        self.document = document
        self.embedding = embedding
        self.distance = distance
        self.similarity = 1.0 - distance  # Convert distance to similarity
        self.collection = collection

    def to_tech_vector(self) -> TechVector:
        """Convert to TechVector for DeepThought Equation."""
        metadata = self.document.metadata
        label = (
            self._sanitize_label(metadata.get("function_name"))
            or self._sanitize_label(metadata.get("name"))
            or self._sanitize_label(metadata.get("title"))
        )

        if not label:
            file_path = self._sanitize_label(metadata.get("file_path"))
            start_line = metadata.get("start_line")
            if file_path and start_line:
                label = f"{file_path}:{start_line}"
            elif file_path:
                label = str(file_path)
            else:
                label = self.document.doc_id

        return TechVector(
            id=self.document.doc_id,
            vector=self.embedding,
            label=label,
            metadata={
                **metadata,
                "content_excerpt": self.document.content[:400],
                "collection": self.collection.value,
            },
        )

    @classmethod
    def _sanitize_label(cls, value: Any) -> str:
        if value is None:
            return ""

        text = str(value).strip()
        if not text:
            return ""
        if text.lower() in cls.INVALID_LABELS:
            return ""
        return text


# ─────────────────────────────────────────────────────────────────
# Embedder
# ─────────────────────────────────────────────────────────────────

class DeepThoughtEmbedder:
    """
    Embedding engine for DeepThought.

    Primary:  IKT-Qwen3-Embedding-8B (via internal endpoint)
    Fallback: text-embedding-3-large  (via internal endpoint)
    """

    def __init__(self):
        self._client = None
        self._model = settings.embedding_model
        self._init_client()

    def _init_client(self):
        try:
            from openai import OpenAI
            self._client = OpenAI(
                base_url=settings.internal_llm_base_url,
                api_key=settings.internal_llm_api_key,
            )
            logger.info(f"✅ Embedder initialized | model={self._model}")
        except Exception as e:
            logger.error(f"❌ Embedder init failed: {e}")
            raise

    def embed(self, texts: List[str]) -> List[np.ndarray]:
        """
        Embed a list of texts.

        Returns:
            List of normalized numpy arrays
        """
        if not texts:
            return []

        try:
            response = self._client.embeddings.create(
                model=self._model,
                input=texts,
            )

            embeddings = []
            for item in response.data:
                vec = np.array(item.embedding, dtype=np.float32)
                # L2 normalize
                norm = np.linalg.norm(vec)
                if norm > 0:
                    vec = vec / norm
                embeddings.append(vec)

            return embeddings

        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            raise

    def embed_one(self, text: str) -> np.ndarray:
        """Embed a single text."""
        return self.embed([text])[0]

    def embed_query(self, query: str) -> np.ndarray:
        """
        Embed a query.
        Some models use different instructions for queries vs documents.
        """
        # Qwen3-Embedding supports task instructions
        query_with_instruction = f"Instruct: Retrieve relevant technical documents\nQuery: {query}"
        return self.embed_one(query_with_instruction)


# ─────────────────────────────────────────────────────────────────
# Main Vector Store
# ─────────────────────────────────────────────────────────────────

class DeepThoughtVectorStore:
    """
    Central vector store for all DeepThought knowledge.

    Manages multiple ChromaDB collections, each for a different
    type of technical knowledge. Integrates with the DeepThought
    Equation for MMR-based void detection.
    """

    def __init__(
        self,
        persist_path: Optional[Path] = None,
        embedder: Optional[DeepThoughtEmbedder] = None,
    ):
        self.persist_path = persist_path or settings.vectordb_path
        self.persist_path.mkdir(parents=True, exist_ok=True)

        # ChromaDB client (local, persistent)
        self._client = chromadb.PersistentClient(
            path=str(self.persist_path),
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True,
            )
        )

        # Embedder
        self.embedder = embedder or create_embedder()
        # Collections cache
        self._collections: Dict[CollectionName, Any] = {}
        self.sparse_index = SparseCooccurrenceIndex(settings.sparse_index_path)

        # Initialize all collections
        self._init_collections()

        logger.info(
            f"✅ DeepThought VectorStore ready | "
            f"path={self.persist_path}"
        )

    def _init_collections(self):
        """Initialize all knowledge collections."""
        for col_name, meta in COLLECTION_METADATA.items():
            collection = self._client.get_or_create_collection(
                name=col_name.value,
                metadata=meta,
            )
            self._collections[col_name] = collection
            logger.debug(f"  Collection ready: {col_name.value}")

    # ── Write Operations ──────────────────────────────────────────

    def add_documents(
        self,
        documents: List[Document],
        collection_name: CollectionName,
    ) -> int:
        """Add documents to a collection."""
        if not documents:
            return 0

        col = self._collections[collection_name]

        texts = [doc.content for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        embeddings = self.embedder.embed(texts)

        import hashlib
        ids = []
        for i, doc in enumerate(documents):
            filepath = doc.metadata.get("file_path", "unknown_path")
            node_name = doc.metadata.get("name", f"chunk_{i}")
            chunk_role = doc.metadata.get("chunk_role", "complete")

            unique_string = f"{filepath}_{node_name}_{chunk_role}_{doc.content}"
            doc_id = hashlib.md5(unique_string.encode("utf-8")).hexdigest()
            ids.append(doc_id)

        try:
            col.add(
                embeddings=[e.tolist() for e in embeddings],
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            self._sync_sparse_collection(collection_name)
            logger.debug(f"  Added {len(documents)} docs to {collection_name.value}")
            return len(documents)
            
        except Exception as e:
            logger.error(f"Failed to add documents to ChromaDB: {e}")
            raise

    def upsert_documents(
        self,
        documents: List[Document],
        collection: CollectionName,
    ) -> int:
        """Upsert documents (add or update if exists)."""
        if not documents:
            return 0

        col = self._collections[collection]
        texts = [doc.content for doc in documents]
        embeddings = self.embedder.embed_documents(texts)

        col.upsert(
            ids=[doc.doc_id for doc in documents],
            embeddings=[e.tolist() for e in embeddings],
            documents=[doc.content for doc in documents],
            metadatas=[doc.metadata for doc in documents],
        )

        return len(documents)

    def delete_by_source(
        self,
        source_path: str,
        collection: CollectionName,
    ):
        """Delete all documents from a specific source file."""
        col = self._collections[collection]
        col.delete(where={"file_path": source_path})
        logger.debug(f"Deleted docs from {source_path}")

    # ── Read Operations ───────────────────────────────────────────

    def query(
        self,
        query_text: str,
        collections: Optional[List[CollectionName]] = None,
        n_results: int = 20,
        where: Optional[Dict] = None,
    ) -> List[RetrievedDocument]:
        """
        Query across one or more collections.

        Args:
            query_text:  Natural language query
            collections: Which collections to search (None = all)
            n_results:   Results per collection
            where:       Metadata filter

        Returns:
            List of RetrievedDocument sorted by similarity
        """
        target_collections = collections or list(CollectionName)
        query_embedding = self.embedder.embed_query(query_text)
        all_results: List[RetrievedDocument] = []

        for col_name in target_collections:
            col = self._collections[col_name]

            if col.count() == 0:
                continue

            try:
                results = col.query(
                    query_embeddings=[query_embedding.tolist()],
                    n_results=min(n_results, col.count()),
                    where=where,
                    include=["documents", "metadatas",
                             "distances", "embeddings"],
                )

                # Parse results
                for j in range(len(results["ids"][0])):
                    doc = Document(
                        content=results["documents"][0][j],
                        metadata=results["metadatas"][0][j],
                        doc_id=results["ids"][0][j],
                    )
                    retrieved = RetrievedDocument(
                        document=doc,
                        embedding=np.array(
                            results["embeddings"][0][j],
                            dtype=np.float32
                        ),
                        distance=results["distances"][0][j],
                        collection=col_name,
                    )
                    all_results.append(retrieved)

            except Exception as e:
                logger.warning(
                    f"Query failed for {col_name.value}: {e}"
                )
                continue

        # Sort by similarity (highest first)
        all_results.sort(key=lambda x: x.similarity, reverse=True)

        return all_results

    def query_with_mmr(
        self,
        query_text: str,
        existing_texts: Optional[List[str]] = None,
        collections: Optional[List[CollectionName]] = None,
        n_results: int = 10,
        lambda_val: float = 0.7,
        where: Optional[Dict] = None,
    ) -> List[RetrievedDocument]:
        """
        Query with MMR re-ranking using the DeepThought Equation.

        This is the primary retrieval method for the Forager agent.
        Returns diverse, relevant results that avoid redundancy.

        Args:
            query_text:     The search query / target
            existing_texts: Known existing solutions (for novelty calc)
            collections:    Which collections to search
            n_results:      Final number of results
            lambda_val:     MMR lambda parameter
            where:          Metadata filter

        Returns:
            MMR-reranked list of RetrievedDocument
        """
        # Step 1: Get initial candidates (fetch more than needed)
        fetch_k = n_results * 4
        candidates = self.query(
            query_text=query_text,
            collections=collections,
            n_results=fetch_k,
            where=where,
        )

        if not candidates:
            return []

        # Step 2: Embed the target query
        query_embedding = self.embedder.embed_query(query_text)
        v_target = TechVector(
            id="query_target",
            vector=query_embedding,
            label=query_text[:50],
        )

        # Step 3: Embed existing solutions (if provided)
        existing_vectors: List[TechVector] = []
        if existing_texts:
            existing_embeddings = self.embedder.embed(existing_texts)
            existing_vectors = [
                TechVector(
                    id=f"existing_{i}",
                    vector=emb,
                    label=text[:50],
                )
                for i, (text, emb) in enumerate(
                    zip(existing_texts, existing_embeddings)
                )
            ]

        # Step 4: Convert candidates to TechVectors
        candidate_vectors = [r.to_tech_vector() for r in candidates]

        # Step 5: Run DeepThought Equation
        engine = DeepThoughtEquation(lambda_val=lambda_val)
        landscape = engine.find_voids_iterative(
            v_target=v_target,
            candidates=candidate_vectors,
            existing=existing_vectors,
            n_select=n_results,
        )

        # Step 6: Map back to RetrievedDocument
        void_id_to_rank = {
            void.candidate.id: rank
            for rank, void in enumerate(landscape.voids)
        }

        reranked = sorted(
            [r for r in candidates if r.document.doc_id in void_id_to_rank],
            key=lambda r: void_id_to_rank.get(r.document.doc_id, 999)
        )

        return reranked[:n_results]

    def _collection_records(self, collection_name: CollectionName) -> List[Dict[str, str]]:
        col = self._collections[collection_name]
        count = col.count()
        if count <= 0:
            return []

        result = col.get(
            limit=count,
            offset=0,
            include=["documents", "metadatas"],
        )
        ids = result.get("ids")
        documents = result.get("documents")
        metadatas = result.get("metadatas")

        if ids is None or documents is None or metadatas is None:
            return []

        records: List[Dict[str, str]] = []
        for idx, doc_id in enumerate(ids):
            metadata = metadatas[idx] or {}
            label = (
                RetrievedDocument._sanitize_label(metadata.get("function_name"))
                or RetrievedDocument._sanitize_label(metadata.get("name"))
                or RetrievedDocument._sanitize_label(metadata.get("title"))
                or str(doc_id)
            )
            records.append(
                {
                    "doc_id": str(doc_id),
                    "label": label,
                    "content": str(documents[idx] or ""),
                }
            )
        return records

    def _sync_sparse_collection(self, collection_name: CollectionName) -> None:
        records = self._collection_records(collection_name)
        self.sparse_index.upsert_records(records=records, collection=collection_name.value)

    def _ensure_sparse_index(self, collections: Optional[List[CollectionName]]) -> List[str]:
        target_collections = collections or list(CollectionName)
        collection_names: List[str] = []
        for collection_name in target_collections:
            self._sync_sparse_collection(collection_name)
            collection_names.append(collection_name.value)
        return collection_names

    def _build_sparse_tokens(self, retrieved: List[RetrievedDocument]) -> Dict[str, List[str]]:
        token_map: Dict[str, List[str]] = {}
        for item in retrieved:
            vector = item.to_tech_vector()
            token_map[item.document.doc_id] = self.sparse_index.extract_top_tokens(
                f"{vector.label} {item.document.content[:600]}",
                max_tokens=5,
            )
        return token_map

    def sample_random_document(
        self,
        collections: Optional[List[CollectionName]] = None,
    ) -> Optional[RetrievedDocument]:
        """
        Sample one random document from the vector store.

        Args:
            collections: Optional subset of collections. None means all collections.

        Returns:
            RetrievedDocument without distance semantics (distance=0.0), or None if DB is empty.
        """
        target_collections = collections or list(CollectionName)
        weighted_pool: List[tuple[CollectionName, int]] = []
        total_count = 0

        for col_name in target_collections:
            col = self._collections[col_name]
            count = col.count()
            if count <= 0:
                continue
            weighted_pool.append((col_name, count))
            total_count += count

        if total_count <= 0:
            return None

        pick = random.randint(0, total_count - 1)
        running = 0
        selected_col_name = weighted_pool[0][0]
        selected_col_count = weighted_pool[0][1]
        for col_name, count in weighted_pool:
            if running + count > pick:
                selected_col_name = col_name
                selected_col_count = count
                break
            running += count

        selected_col = self._collections[selected_col_name]
        offset = random.randint(0, selected_col_count - 1)
        result = selected_col.get(
            limit=1,
            offset=offset,
            include=["documents", "metadatas", "embeddings"],
        )

        ids = result.get("ids")
        if ids is None:
            return None

        if isinstance(ids, np.ndarray):
            if ids.size == 0:
                return None
            doc_id = str(ids[0])
        else:
            if len(ids) == 0:
                return None
            doc_id = str(ids[0])

        documents = result.get("documents")
        if documents is None:
            content = ""
        elif isinstance(documents, np.ndarray):
            content = str(documents[0]) if documents.size > 0 else ""
        else:
            content = str(documents[0]) if len(documents) > 0 else ""

        metadatas = result.get("metadatas")
        if metadatas is None:
            metadata = {}
        elif isinstance(metadatas, np.ndarray):
            metadata = metadatas[0] if metadatas.size > 0 else {}
        else:
            metadata = metadatas[0] if len(metadatas) > 0 else {}

        doc = Document(
            content=content,
            metadata=metadata or {},
            doc_id=doc_id,
        )

        embeddings = result.get("embeddings")
        if embeddings is None:
            embedding_data = None
        elif isinstance(embeddings, np.ndarray):
            embedding_data = embeddings[0] if embeddings.size > 0 else None
        else:
            embedding_data = embeddings[0] if len(embeddings) > 0 else None

        if embedding_data is None:
            embedding = self.embedder.embed_one(doc.content)
        else:
            embedding = np.array(embedding_data, dtype=np.float32)

        return RetrievedDocument(
            document=doc,
            embedding=embedding,
            distance=0.0,
            collection=selected_col_name,
        )

    def find_topological_voids(
        self,
        target_description: str,
        existing_solutions: Optional[List[str]] = None,
        collections: Optional[List[CollectionName]] = None,
        domain_filter: Optional[str] = None,
        lambda_val: float = 0.7,
        top_k: int = 5,
    ) -> VoidLandscape:
        """
        High-level API: Find Topological Voids for the Forager.

        This is what the Forager agent calls directly.

        Args:
            target_description: What we want to achieve/optimize
            existing_solutions: Known existing approaches
            collections:        Which collections to search
            domain_filter:      e.g., "x86", "scheduler", "mm"
            lambda_val:         Innovation strategy
            top_k:              Number of voids to find

        Returns:
            VoidLandscape ready for the Maverick agent
        """
        logger.info(
            f"🕵️ Finding Topological Voids | "
            f"target='{target_description[:50]}...'"
        )

        # Build metadata filter
        where = None
        if domain_filter:
            where = {"subsystem": {"$eq": domain_filter}}

        # Get dense candidates first; hybrid triad selection happens after retrieval.
        retrieved = self.query(
            query_text=target_description,
            collections=collections,
            n_results=top_k * 4,
            where=where,
        )

        if not retrieved:
            logger.warning("No candidates found for void detection")
            return VoidLandscape(
                target=TechVector(
                    id="target",
                    vector=self.embedder.embed_query(target_description),
                    label=target_description[:50],
                ),
                voids=[],
                lambda_used=lambda_val,
                domain=domain_filter or "unknown",
            )

        # Embed target
        target_embedding = self.embedder.embed_query(target_description)
        v_target = TechVector(
            id="target",
            vector=target_embedding,
            label=target_description[:50],
        )

        # Embed existing solutions
        existing_vectors: List[TechVector] = []
        if existing_solutions:
            existing_embeddings = self.embedder.embed(existing_solutions)
            existing_vectors = [
                TechVector(
                    id=f"existing_{i}",
                    vector=emb,
                    label=sol[:50],
                )
                for i, (sol, emb) in enumerate(
                    zip(existing_solutions, existing_embeddings)
                )
            ]

        # Convert to TechVectors
        candidate_vectors = [r.to_tech_vector() for r in retrieved]
        collection_names = self._ensure_sparse_index(collections)
        sparse_tokens = self._build_sparse_tokens(retrieved)

        # Run Hybrid DeepThought Equation
        engine = DeepThoughtEquation(lambda_val=lambda_val)
        thresholds = engine.calibrate_marginality_thresholds(
            candidates=candidate_vectors,
            v_target=v_target,
        )
        landscape = engine.find_hybrid_voids_iterative(
            v_target=v_target,
            candidates=candidate_vectors,
            existing=existing_vectors,
            sparse_tokens=sparse_tokens,
            global_cooccurrence_checker=lambda left, right: self.sparse_index.has_cooccurrence(
                left,
                right,
                collections=collection_names,
            ),
            n_select=top_k,
            domain=domain_filter or "unknown",
            domain_threshold=settings.triad_domain_threshold,
            thresholds=thresholds,
        )
        landscape.target.metadata["triad_threshold_low"] = thresholds.low
        landscape.target.metadata["triad_threshold_high"] = thresholds.high
        landscape.target.metadata["triad_threshold_source"] = thresholds.source

        logger.info(f"✅ {landscape.summary()}")
        return landscape

    # ── Stats & Maintenance ───────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for all collections."""
        stats = {}
        total = 0

        for col_name, col in self._collections.items():
            count = col.count()
            stats[col_name.value] = count
            total += count

        stats["total"] = total
        return stats

    def print_stats(self):
        """Pretty print collection statistics."""
        stats = self.get_stats()
        logger.info("📊 VectorStore Statistics:")
        logger.info(f"{'─' * 40}")
        for name, count in stats.items():
            if name != "total":
                logger.info(f"  {name:<25} {count:>8,} docs")
        logger.info(f"{'─' * 40}")
        logger.info(f"  {'TOTAL':<25} {stats['total']:>8,} docs")

    def reset_collection(self, collection: CollectionName):
        """Reset (clear) a specific collection."""
        logger.warning(f"⚠️  Resetting collection: {collection.value}")
        self._client.delete_collection(collection.value)
        new_col = self._client.get_or_create_collection(
            name=collection.value,
            metadata=COLLECTION_METADATA[collection],
        )
        self._collections[collection] = new_col
        logger.info(f"✅ Collection reset: {collection.value}")

    # ── Private Helpers ───────────────────────────────────────────

    def _filter_duplicates(
        self,
        documents: List[Document],
        collection: Any,
    ) -> List[Document]:
        """Filter out documents that already exist in the collection."""
        if collection.count() == 0:
            return documents

        existing_ids = set(
            collection.get(
                ids=[doc.doc_id for doc in documents]
            )["ids"]
        )

        return [
            doc for doc in documents
            if doc.doc_id not in existing_ids
        ]
