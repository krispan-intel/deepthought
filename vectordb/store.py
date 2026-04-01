"""
vectordb/store.py

DeepThought Vector Store
Manages all knowledge collections for the RAG pipeline.
Integrates with the DeepThought Equation for MMR retrieval.
"""

from __future__ import annotations

import hashlib
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
        return TechVector(
            id=self.document.doc_id,
            vector=self.embedding,
            label=self.document.metadata.get(
                "function_name",
                self.document.metadata.get("title", self.document.doc_id)
            ),
            metadata=self.document.metadata,
        )


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

        # Get candidates via MMR query
        retrieved = self.query_with_mmr(
            query_text=target_description,
            existing_texts=existing_solutions,
            collections=collections,
            n_results=top_k * 4,
            lambda_val=lambda_val,
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

        # Run DeepThought Equation
        engine = DeepThoughtEquation(lambda_val=lambda_val)
        landscape = engine.find_voids_iterative(
            v_target=v_target,
            candidates=candidate_vectors,
            existing=existing_vectors,
            n_select=top_k,
            domain=domain_filter or "unknown",
        )

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
