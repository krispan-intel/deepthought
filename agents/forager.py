"""
agents/forager.py

Forager agent: retrieves topological voids from vector store.
"""

from __future__ import annotations

from typing import Any, Dict, List

from loguru import logger

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
        forager_observations = {
            "target": landscape.target.label,
            "domain": landscape.domain,
            "lambda": landscape.lambda_used,
            "void_count": len(landscape.voids),
            "top_voids": self._summarize_voids(landscape.voids),
            "domain_threshold": {
                "strategy": landscape.target.metadata.get("domain_threshold_strategy", "unknown"),
                "static_fallback": landscape.target.metadata.get("domain_threshold_static_fallback", 0.0),
                "dynamic_computed": landscape.target.metadata.get("domain_threshold_dynamic_computed", 0.0),
                "score_distribution": landscape.target.metadata.get("candidate_score_distribution", {}),
            },
        }
        has_hybrid_triads = any(
            bool(item.get("anchor_a")) and bool(item.get("anchor_b"))
            for item in forager_observations["top_voids"]
        )
        forager_observations["search_mode"] = "hybrid_triad" if has_hybrid_triads else "iterative_mmr_fallback"
        forager_observations["hybrid_triad_found"] = has_hybrid_triads
        state.metadata["forager_observations"] = forager_observations
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

        if forager_observations["top_voids"]:
            top_void = forager_observations["top_voids"][0]
            logger.info(
                "Forager result | run_id={} | mode={} | voids={} | anchor_c={} | anchor_a={} | anchor_b={} | domain_score={:.4f} | pairwise_score={:.4f} | mmr={:.4f}",
                state.run_id,
                forager_observations["search_mode"],
                forager_observations["void_count"],
                top_void["anchor_c"],
                top_void["anchor_a"],
                top_void["anchor_b"],
                top_void["domain_score"],
                top_void["pairwise_score"],
                top_void["mmr_score"],
            )
        else:
            logger.warning("Forager produced no voids | run_id={} | target={}", state.run_id, state.target)

        return state

    @staticmethod
    def _summarize_voids(voids: List[Any], max_items: int = 5) -> List[Dict[str, Any]]:
        observations: List[Dict[str, Any]] = []
        for rank, void in enumerate(voids[:max_items], start=1):
            metadata = getattr(void.candidate, "metadata", {}) or {}
            observations.append(
                {
                    "rank": rank,
                    "anchor_c": str(getattr(void.candidate, "label", "")).strip(),
                    "anchor_a": str(metadata.get("anchor_a_label", "")).strip(),
                    "anchor_b": str(metadata.get("anchor_b_label", "")).strip(),
                    "domain_score": round(float(getattr(void, "domain_score", 0.0)), 4),
                    "pairwise_score": round(float(getattr(void, "pairwise_score", 0.0)), 4),
                    "mmr_score": round(float(getattr(void, "mmr_score", 0.0)), 4),
                    "relevance_score": round(float(getattr(void, "relevance_score", 0.0)), 4),
                    "novelty_score": round(float(getattr(void, "novelty_score", 0.0)), 4),
                    "marginality_low": round(float(getattr(void, "marginality_low", 0.0)), 4),
                    "marginality_high": round(float(getattr(void, "marginality_high", 0.0)), 4),
                    "sparse_overlap_count": int(getattr(void, "sparse_overlap_count", 0) or 0),
                    "sparse_anchor_tokens": [str(token) for token in getattr(void, "sparse_anchor_tokens", ())],
                }
            )
        return observations
