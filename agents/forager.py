"""
agents/forager.py

Forager agent: retrieves topological voids from vector store.
"""

from __future__ import annotations

from typing import List

from vectordb.store import CollectionName, DeepThoughtVectorStore

from agents.state import PipelineState, VoidStatus


class ForagerAgent:
    def __init__(self, store: DeepThoughtVectorStore | None = None):
        self.store = store or DeepThoughtVectorStore()

    def run(self, state: PipelineState, top_k: int = 5) -> PipelineState:
        collections = None
        if state.collection_names:
            collections = [CollectionName(c) for c in state.collection_names]

        landscape = self.store.find_topological_voids(
            target_description=state.target,
            existing_solutions=state.existing_solutions,
            collections=collections,
            domain_filter=state.domain_filter,
            lambda_val=state.lambda_val,
            top_k=top_k,
        )
        state.topological_void_context = landscape.to_maverick_context()
        state.metadata["void_count"] = len(landscape.voids)
        state.void_statuses = [
            VoidStatus(
                void_id=v.candidate.id,
                label=v.candidate.label,
                mmr_score=float(v.mmr_score),
                relevance_score=float(v.relevance_score),
                novelty_score=float(v.novelty_score),
                status="DISCOVERED",
            )
            for v in landscape.voids
        ]
        return state
