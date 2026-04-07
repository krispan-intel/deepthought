"""
core/deepthought_equation.py

The DeepThought Equation - Core IP
MMR_Patent = λ · Sim(V_new, V_target) - (1-λ) · max[Sim(V_new, V_existing)]

Combines:
- Maximum Marginal Relevance (MMR)
- Latent Space Arithmetic

to identify Topological Voids in technical knowledge spaces.
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple, Dict, Any
from loguru import logger


# ─────────────────────────────────────────────────────────────────
# Data Classes
# ─────────────────────────────────────────────────────────────────

@dataclass
class TechVector:
    """
    A technology concept represented as a vector in latent space.
    """
    id: str
    vector: np.ndarray
    label: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Always store as float32
        self.vector = np.array(self.vector, dtype=np.float32)
        # L2 normalize on creation
        norm = np.linalg.norm(self.vector)
        if norm > 0:
            self.vector = self.vector / norm

    def __repr__(self) -> str:
        return (
            f"TechVector("
            f"id='{self.id}', "
            f"label='{self.label}', "
            f"dim={len(self.vector)})"
        )


@dataclass
class VoidResult:
    """
    Result of the DeepThought Equation for a single candidate.
    Represents a Topological Void - a potential innovation opportunity.
    """
    candidate: TechVector

    # Core scores from the DeepThought Equation
    mmr_score: float            # Final score: the higher, the better void
    relevance_score: float      # Sim(V_new, V_target)
    max_redundancy_score: float # max[Sim(V_new, V_existing)]

    # Context
    nearest_existing: List[Tuple[TechVector, float]] = field(
        default_factory=list
    )
    void_description: str = ""
    lambda_used: float = 0.7
    domain_score: float = 0.0
    pairwise_score: float = 0.0
    sparse_overlap_count: int = 0
    sparse_anchor_tokens: Tuple[str, ...] = field(default_factory=tuple)
    marginality_low: float = 0.0
    marginality_high: float = 0.0

    @property
    def novelty_score(self) -> float:
        """
        1.0 - max_redundancy = how novel this candidate is.
        1.0 = completely novel, 0.0 = identical to existing.
        """
        return 1.0 - self.max_redundancy_score

    @property
    def is_significant_void(self) -> bool:
        """
        A void is significant when:
          - Relevance to target  > 0.5  (it matters)
          - Similarity to existing < 0.4 (it's new)
        """
        return (
            self.relevance_score > 0.5
            and self.max_redundancy_score < 0.4
        )

    def __repr__(self) -> str:
        return (
            f"VoidResult("
            f"label='{self.candidate.label}', "
            f"mmr={self.mmr_score:.4f}, "
            f"relevance={self.relevance_score:.4f}, "
            f"novelty={self.novelty_score:.4f}, "
            f"significant={self.is_significant_void})"
        )


@dataclass
class VoidLandscape:
    """
    The full landscape of Topological Voids found in one search pass.
    This is the primary output handed to the Maverick agent.
    """
    target: TechVector
    voids: List[VoidResult]
    lambda_used: float
    domain: str

    @property
    def top_void(self) -> Optional[VoidResult]:
        """The single best void by MMR score."""
        if not self.voids:
            return None
        return max(self.voids, key=lambda v: v.mmr_score)

    @property
    def significant_voids(self) -> List[VoidResult]:
        """All voids that pass the significance threshold."""
        return [v for v in self.voids if v.is_significant_void]

    def summary(self) -> str:
        top_score = self.top_void.mmr_score if self.top_void else 0.0
        return (
            f"VoidLandscape("
            f"domain='{self.domain}', "
            f"total_voids={len(self.voids)}, "
            f"significant={len(self.significant_voids)}, "
            f"top_mmr={top_score:.4f}, "
            f"lambda={self.lambda_used})"
        )

    def to_maverick_context(self) -> str:
        """
        Serialize the landscape into a prompt-ready string
        for the Maverick agent.
        """
        if not self.voids:
            return "No topological voids found."

        lines = [
            f"Target: {self.target.label}",
            f"Domain: {self.domain}",
            f"Lambda (innovation strategy): {self.lambda_used}",
            f"Significant voids found: {len(self.significant_voids)}",
            "",
            "=== TOP TOPOLOGICAL VOIDS ===",
        ]

        for i, void in enumerate(self.voids[:5], 1):
            nearest_str = ", ".join(
                f"'{e.label}' ({s:.2f})"
                for e, s in void.nearest_existing[:2]
            )
            lines += [
                f"",
                f"Void #{i}: {void.candidate.label}",
                f"  MMR Score:    {void.mmr_score:.4f}",
                f"  Relevance:    {void.relevance_score:.4f}",
                f"  Novelty:      {void.novelty_score:.4f}",
                f"  Significant:  {void.is_significant_void}",
                f"  Nearest existing: {nearest_str or 'none'}",
                f"  Description:  {void.void_description}",
            ]

        return "\n".join(lines)


@dataclass
class MarginalityThresholds:
    low: float
    high: float
    sample_size: int = 0
    source: str = "static"


# ─────────────────────────────────────────────────────────────────
# Core Engine
# ─────────────────────────────────────────────────────────────────

class DeepThoughtEquation:
    """
    The DeepThought Equation Engine.

    MMR_Patent = λ · Sim(V_new, V_target)
               - (1-λ) · max[Sim(V_new, V_existing)]

    Identifies Topological Voids: regions in the technical latent
    space that are simultaneously:
      1. Relevant to the target optimization goal  (high Sim to target)
      2. Not yet covered by existing solutions     (low Sim to existing)

    The higher the MMR_Patent score, the more valuable the void.
    """

    def __init__(self, lambda_val: float = 0.7):
        """
        Args:
            lambda_val: Controls the relevance vs. novelty trade-off.

                        λ = 1.0  pure relevance   (ignore existing)
                        λ = 0.7  balanced          (default)
                        λ = 0.5  conservative
                        λ = 0.3  disruptive        (maximize novelty)
                        λ = 0.0  pure novelty      (ignore target)
        """
        if not 0.0 <= lambda_val <= 1.0:
            raise ValueError(
                f"lambda_val must be in [0.0, 1.0], got {lambda_val}"
            )
        self.lambda_val = lambda_val
        logger.info(
            f"DeepThought Equation initialized | λ={self.lambda_val}"
        )

    # ── Core Math ────────────────────────────────────────────────

    @staticmethod
    def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """
        Cosine similarity between two L2-normalized vectors.
        Clipped to [-1.0, 1.0] to guard against floating point drift.
        """
        return float(np.clip(np.dot(a, b), -1.0, 1.0))

    def compute_mmr_score(
        self,
        v_new: np.ndarray,
        v_target: np.ndarray,
        v_existing_list: List[np.ndarray],
    ) -> Tuple[float, float, float]:
        """
        Compute the DeepThought Equation for a single candidate vector.

        Args:
            v_new:           Candidate vector (L2-normalized)
            v_target:        Target goal vector (L2-normalized)
            v_existing_list: List of existing solution vectors

        Returns:
            Tuple of:
              mmr_score          - the final DeepThought score
              relevance_score    - Sim(V_new, V_target)
              max_redundancy     - max[Sim(V_new, V_existing)]
        """
        # Term 1: How relevant is this candidate to our goal?
        relevance = self.cosine_similarity(v_new, v_target)

        # Term 2: How similar is this to the best existing solution?
        if v_existing_list:
            max_redundancy = max(
                self.cosine_similarity(v_new, v_exist)
                for v_exist in v_existing_list
            )
        else:
            # No existing solutions means pure blue ocean territory
            max_redundancy = 0.0

        # The DeepThought Equation
        mmr_score = (
            self.lambda_val * relevance
            - (1.0 - self.lambda_val) * max_redundancy
        )

        return mmr_score, relevance, max_redundancy

    def calibrate_marginality_thresholds(
        self,
        candidates: List[TechVector],
        v_target: Optional[TechVector] = None,
        min_low: float = 0.18,
        max_high: float = 0.82,
        top_n: int = 12,
    ) -> MarginalityThresholds:
        if len(candidates) < 2:
            return MarginalityThresholds(
                low=min_low,
                high=max(min_low + 0.1, min(max_high, 0.55)),
                sample_size=0,
                source="fallback",
            )

        ranked = list(candidates)
        if v_target is not None:
            ranked.sort(
                key=lambda candidate: self.cosine_similarity(candidate.vector, v_target.vector),
                reverse=True,
            )
        ranked = ranked[: max(2, min(top_n, len(ranked)))]

        similarities: List[float] = []
        for index, left in enumerate(ranked):
            for right in ranked[index + 1 :]:
                similarities.append(self.cosine_similarity(left.vector, right.vector))

        if not similarities:
            return MarginalityThresholds(
                low=min_low,
                high=max(min_low + 0.1, min(max_high, 0.55)),
                sample_size=0,
                source="fallback",
            )

        values = np.array(similarities, dtype=np.float32)
        low = float(np.quantile(values, 0.35))
        high = float(np.quantile(values, 0.75))
        low = max(min_low, min(low, max_high - 0.08))
        high = min(max_high, max(high, low + 0.08))

        return MarginalityThresholds(
            low=low,
            high=high,
            sample_size=len(similarities),
            source="dense_neighborhood_quantiles",
        )

    def find_hybrid_voids_iterative(
        self,
        v_target: TechVector,
        candidates: List[TechVector],
        existing: List[TechVector],
        sparse_tokens: Dict[str, List[str]],
        global_cooccurrence_checker: Callable[[List[str], List[str]], bool],
        n_select: int = 5,
        domain: str = "unknown",
        domain_threshold: float = 0.45,
        thresholds: Optional[MarginalityThresholds] = None,
    ) -> VoidLandscape:
        logger.info(
            f"🕵️  DeepThought Equation (hybrid triad) | "
            f"candidates={len(candidates)} | existing={len(existing)} | "
            f"n_select={n_select} | λ={self.lambda_val}"
        )

        if len(candidates) < 2:
            return self.find_voids_iterative(
                v_target=v_target,
                candidates=candidates,
                existing=existing,
                n_select=n_select,
                domain=domain,
            )

        thresholds = thresholds or self.calibrate_marginality_thresholds(
            candidates=candidates,
            v_target=v_target,
        )

        relevance_map = {
            candidate.id: self.cosine_similarity(candidate.vector, v_target.vector)
            for candidate in candidates
        }
        existing_vectors = [item.vector for item in existing]
        redundancy_map = {
            candidate.id: (
                max(self.cosine_similarity(candidate.vector, other) for other in existing_vectors)
                if existing_vectors
                else 0.0
            )
            for candidate in candidates
        }

        pair_candidates: List[VoidResult] = []
        for index, left in enumerate(candidates):
            left_relevance = relevance_map[left.id]
            if left_relevance < domain_threshold:
                continue

            left_tokens = sparse_tokens.get(left.id, [])
            if not left_tokens:
                continue

            for right in candidates[index + 1 :]:
                right_relevance = relevance_map[right.id]
                if right_relevance < domain_threshold:
                    continue

                pair_similarity = self.cosine_similarity(left.vector, right.vector)
                if pair_similarity < thresholds.low or pair_similarity > thresholds.high:
                    continue

                right_tokens = sparse_tokens.get(right.id, [])
                if not right_tokens:
                    continue

                if global_cooccurrence_checker(left_tokens, right_tokens):
                    continue

                combined_vector = left.vector + right.vector
                norm = np.linalg.norm(combined_vector)
                if norm > 0:
                    combined_vector = combined_vector / norm

                anchor_tokens = tuple(sorted(set(left_tokens[:3] + right_tokens[:3])))
                synthetic = TechVector(
                    id=f"{left.id}::{right.id}",
                    vector=combined_vector,
                    label=f"{left.label} <> {right.label}",
                    metadata={
                        "anchor_a_id": left.id,
                        "anchor_a_label": left.label,
                        "anchor_b_id": right.id,
                        "anchor_b_label": right.label,
                        "anchor_a_tokens": left_tokens,
                        "anchor_b_tokens": right_tokens,
                    },
                )

                relevance = (left_relevance + right_relevance) / 2.0
                max_redundancy = max(redundancy_map[left.id], redundancy_map[right.id])
                midpoint = (thresholds.low + thresholds.high) / 2.0
                half_band = max((thresholds.high - thresholds.low) / 2.0, 1e-6)
                marginality_fit = max(0.0, 1.0 - abs(pair_similarity - midpoint) / half_band)
                hybrid_score = (
                    self.lambda_val * relevance
                    - (1.0 - self.lambda_val) * max_redundancy
                    + 0.25 * marginality_fit
                    + 0.10
                )

                pair_candidates.append(
                    VoidResult(
                        candidate=synthetic,
                        mmr_score=hybrid_score,
                        relevance_score=relevance,
                        max_redundancy_score=max_redundancy,
                        nearest_existing=self._find_nearest_existing(synthetic, existing, top_n=3),
                        lambda_used=self.lambda_val,
                        domain_score=relevance,
                        pairwise_score=pair_similarity,
                        sparse_overlap_count=0,
                        sparse_anchor_tokens=anchor_tokens,
                        marginality_low=thresholds.low,
                        marginality_high=thresholds.high,
                    )
                )

        if not pair_candidates:
            logger.warning("Hybrid triad produced no valid pairs; falling back to iterative MMR")
            return self.find_voids_iterative(
                v_target=v_target,
                candidates=candidates,
                existing=existing,
                n_select=n_select,
                domain=domain,
            )

        pair_candidates.sort(key=lambda item: item.mmr_score, reverse=True)

        selected: List[VoidResult] = []
        used_anchor_ids: set[str] = set()
        for candidate in pair_candidates:
            metadata = candidate.candidate.metadata
            left_id = str(metadata.get("anchor_a_id", ""))
            right_id = str(metadata.get("anchor_b_id", ""))
            if left_id in used_anchor_ids or right_id in used_anchor_ids:
                continue

            if any(
                self.cosine_similarity(candidate.candidate.vector, prior.candidate.vector) > thresholds.high
                for prior in selected
            ):
                continue

            candidate.void_description = self._describe_void(candidate, v_target)
            selected.append(candidate)
            used_anchor_ids.update({left_id, right_id})

            if len(selected) >= n_select:
                break

        landscape = VoidLandscape(
            target=v_target,
            voids=selected,
            lambda_used=self.lambda_val,
            domain=domain,
        )

        logger.info(f"✅ {landscape.summary()}")
        return landscape

    # ── Void Detection: Batch Mode ────────────────────────────────

    def find_voids(
        self,
        v_target: TechVector,
        candidates: List[TechVector],
        existing: List[TechVector],
        top_k: int = 10,
        domain: str = "unknown",
    ) -> VoidLandscape:
        """
        Score all candidates independently and return the top-k voids.

        Use this when you want a broad survey of the void landscape.
        Each candidate is scored independently against the full
        existing set - no interaction between candidates.

        Args:
            v_target:   What we want to achieve / optimize
            candidates: The search space (retrieved from RAG)
            existing:   Known existing solutions / patents
            top_k:      How many top voids to return
            domain:     Technical domain label (for metadata)

        Returns:
            VoidLandscape sorted by MMR score descending
        """
        logger.info(
            f"🕵️  DeepThought Equation (batch) | "
            f"candidates={len(candidates)} | "
            f"existing={len(existing)} | "
            f"λ={self.lambda_val}"
        )

        if not candidates:
            logger.warning("No candidates provided to find_voids()")
            return VoidLandscape(
                target=v_target,
                voids=[],
                lambda_used=self.lambda_val,
                domain=domain,
            )

        existing_vectors = [e.vector for e in existing]
        void_results: List[VoidResult] = []

        for candidate in candidates:
            mmr_score, relevance, max_redundancy = self.compute_mmr_score(
                v_new=candidate.vector,
                v_target=v_target.vector,
                v_existing_list=existing_vectors,
            )

            nearest = self._find_nearest_existing(
                candidate=candidate,
                existing=existing,
                top_n=3,
            )

            void_results.append(VoidResult(
                candidate=candidate,
                mmr_score=mmr_score,
                relevance_score=relevance,
                max_redundancy_score=max_redundancy,
                nearest_existing=nearest,
                lambda_used=self.lambda_val,
            ))

        # Sort descending by MMR score
        void_results.sort(key=lambda x: x.mmr_score, reverse=True)
        top_voids = void_results[:top_k]

        # Enrich with human-readable descriptions
        for void in top_voids:
            void.void_description = self._describe_void(void, v_target)

        landscape = VoidLandscape(
            target=v_target,
            voids=top_voids,
            lambda_used=self.lambda_val,
            domain=domain,
        )

        logger.info(f"✅ {landscape.summary()}")
        return landscape

    # ── Void Detection: Iterative / Greedy Mode ───────────────────

    def find_voids_iterative(
        self,
        v_target: TechVector,
        candidates: List[TechVector],
        existing: List[TechVector],
        n_select: int = 5,
        domain: str = "unknown",
    ) -> VoidLandscape:
        """
        Greedy iterative MMR: select a DIVERSE set of voids.

        Unlike find_voids() which scores each candidate independently,
        this method updates the redundancy set after each selection.
        This ensures the final set of voids covers different parts
        of the innovation space - no two selected voids are too similar.

        This is the preferred method for feeding the Maverick agent,
        because it produces 3-5 distinct RFC directions rather than
        5 variations of the same idea.

        Args:
            v_target:   Target goal vector
            candidates: Search space
            existing:   Known existing solutions
            n_select:   Number of diverse voids to select
            domain:     Domain label

        Returns:
            VoidLandscape with n_select diverse voids
        """
        logger.info(
            f"🕵️  DeepThought Equation (iterative) | "
            f"candidates={len(candidates)} | "
            f"existing={len(existing)} | "
            f"n_select={n_select} | "
            f"λ={self.lambda_val}"
        )

        if not candidates:
            logger.warning(
                "No candidates provided to find_voids_iterative()"
            )
            return VoidLandscape(
                target=v_target,
                voids=[],
                lambda_used=self.lambda_val,
                domain=domain,
            )

        remaining = list(candidates)
        selected: List[VoidResult] = []

        # Start with the base existing vectors
        existing_vectors = [e.vector for e in existing]

        for i in range(min(n_select, len(remaining))):

            best_void: Optional[VoidResult] = None
            best_score = float("-inf")

            for candidate in remaining:

                # Key difference from batch mode:
                # already-selected voids are added to the existing set
                # so the next selection is pushed away from them
                all_existing = existing_vectors + [
                    s.candidate.vector for s in selected
                ]

                mmr_score, relevance, max_redundancy = \
                    self.compute_mmr_score(
                        v_new=candidate.vector,
                        v_target=v_target.vector,
                        v_existing_list=all_existing,
                    )

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_void = VoidResult(
                        candidate=candidate,
                        mmr_score=mmr_score,
                        relevance_score=relevance,
                        max_redundancy_score=max_redundancy,
                        lambda_used=self.lambda_val,
                    )

            if best_void is None:
                break

            # Enrich nearest existing context
            best_void.nearest_existing = self._find_nearest_existing(
                candidate=best_void.candidate,
                existing=existing,
                top_n=3,
            )
            best_void.void_description = self._describe_void(
                best_void, v_target
            )

            selected.append(best_void)
            remaining.remove(best_void.candidate)

            logger.debug(
                f"  Selected void {i + 1}/{n_select}: "
                f"'{best_void.candidate.label}' "
                f"(mmr={best_void.mmr_score:.4f})"
            )

        landscape = VoidLandscape(
            target=v_target,
            voids=selected,
            lambda_used=self.lambda_val,
            domain=domain,
        )

        logger.info(f"✅ {landscape.summary()}")
        return landscape

    # ── Latent Space Arithmetic ───────────────────────────────────

    def interpolate(
        self,
        v_a: TechVector,
        v_b: TechVector,
        steps: int = 10,
    ) -> List[np.ndarray]:
        """
        Latent Space Arithmetic: linear interpolation between two concepts.

        Explores the space BETWEEN two existing technologies.
        The midpoints often correspond to unexplored Voids.

        Example:
            interpolate(prefetch_vec, branch_predictor_vec, steps=10)
            produces 10 vectors tracing the path from one concept
            to the other - useful for finding what lives in between.

        Args:
            v_a:   Start concept
            v_b:   End concept
            steps: Number of interpolation steps

        Returns:
            List of normalized numpy arrays (the interpolated path)
        """
        interpolations = []

        for t in np.linspace(0.0, 1.0, steps):
            z = (1.0 - t) * v_a.vector + t * v_b.vector
            norm = np.linalg.norm(z)
            if norm > 0:
                z = z / norm
            interpolations.append(z)

        return interpolations

    def concept_arithmetic(
        self,
        positive: List[TechVector],
        negative: List[TechVector],
    ) -> np.ndarray:
        """
        Latent Space Arithmetic: vector addition and subtraction.

        Analogous to the classic Word2Vec example:
            king - man + woman ≈ queen

        Technical example:
            prefetch + runtime_feedback - static_hints
            → points toward adaptive prefetch strategies

        Args:
            positive: Vectors to add
            negative: Vectors to subtract

        Returns:
            Resulting normalized vector
        """
        if not positive:
            raise ValueError("At least one positive vector required")

        result = np.zeros_like(positive[0].vector, dtype=np.float32)

        for v in positive:
            result = result + v.vector

        for v in negative:
            result = result - v.vector

        norm = np.linalg.norm(result)
        if norm > 0:
            result = result / norm

        return result

    def find_void_by_arithmetic(
        self,
        positive: List[TechVector],
        negative: List[TechVector],
        candidates: List[TechVector],
        existing: List[TechVector],
        n_select: int = 5,
        domain: str = "unknown",
    ) -> VoidLandscape:
        """
        Combine concept arithmetic with iterative void detection.

        Use case:
            "Find voids in the space of
             (dynamic_prefetch + branch_state - static_prefetch)
             that don't exist yet."

        This is a power-user API for the Forager agent when
        the user provides explicit concept directions.

        Args:
            positive:   Concepts to move toward
            negative:   Concepts to move away from
            candidates: Search space
            existing:   Known existing solutions
            n_select:   Number of voids to find
            domain:     Domain label

        Returns:
            VoidLandscape anchored at the arithmetic target
        """
        arithmetic_vector = self.concept_arithmetic(positive, negative)

        # Build a descriptive label for the synthetic target
        pos_labels = [f"+{v.label}" for v in positive]
        neg_labels = [f"-{v.label}" for v in negative]
        label = " ".join(pos_labels + neg_labels)

        v_target = TechVector(
            id="arithmetic_target",
            vector=arithmetic_vector,
            label=label,
        )

        logger.info(f"🧮 Concept arithmetic target: {label}")

        return self.find_voids_iterative(
            v_target=v_target,
            candidates=candidates,
            existing=existing,
            n_select=n_select,
            domain=domain,
        )

    # ── Lambda Strategy Presets ───────────────────────────────────

    def with_lambda(self, lambda_val: float) -> "DeepThoughtEquation":
        """Return a new instance with a different lambda value."""
        return DeepThoughtEquation(lambda_val=lambda_val)

    @classmethod
    def balanced(cls) -> "DeepThoughtEquation":
        """λ=0.7 — Default balanced mode."""
        return cls(lambda_val=0.7)

    @classmethod
    def aggressive(cls) -> "DeepThoughtEquation":
        """λ=0.9 — Prioritize relevance, less concerned with novelty."""
        return cls(lambda_val=0.9)

    @classmethod
    def conservative(cls) -> "DeepThoughtEquation":
        """λ=0.5 — Equal weight on relevance and novelty."""
        return cls(lambda_val=0.5)

    @classmethod
    def disruptive(cls) -> "DeepThoughtEquation":
        """λ=0.3 — Maximize distance from existing solutions."""
        return cls(lambda_val=0.3)

    # ── Private Helpers ───────────────────────────────────────────

    def _find_nearest_existing(
        self,
        candidate: TechVector,
        existing: List[TechVector],
        top_n: int = 3,
    ) -> List[Tuple[TechVector, float]]:
        """
        Find the top_n most similar existing solutions to a candidate.
        Used to provide context in the void description.
        """
        if not existing:
            return []

        similarities = [
            (e, self.cosine_similarity(candidate.vector, e.vector))
            for e in existing
        ]
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_n]

    def _describe_void(
        self,
        void: VoidResult,
        target: TechVector,
    ) -> str:
        """
        Generate a human-readable description of a void.
        This text is injected directly into the Maverick's prompt.
        """
        nearest_labels = [
            f"'{e.label}' (similarity={s:.2f})"
            for e, s in void.nearest_existing[:3]
        ]
        nearest_str = (
            ", ".join(nearest_labels)
            if nearest_labels
            else "no close existing solutions found"
        )

        if void.is_significant_void:
            significance = "HIGH-VALUE void"
        elif void.mmr_score > 0:
            significance = "moderate void"
        else:
            significance = "weak void"

        metadata = void.candidate.metadata
        anchor_a = str(metadata.get("anchor_a_label", "")).strip()
        anchor_b = str(metadata.get("anchor_b_label", "")).strip()
        sparse_tokens = ", ".join(void.sparse_anchor_tokens)
        hybrid_context = ""
        if anchor_a and anchor_b:
            hybrid_context = (
                f" Hybrid concept anchors: '{anchor_a}' + '{anchor_b}'."
                f" Pairwise dense similarity: {void.pairwise_score:.2f}"
                f" within calibrated band [{void.marginality_low:.2f}, {void.marginality_high:.2f}]."
            )
            if sparse_tokens:
                hybrid_context += f" Sparse anchors: {sparse_tokens}."

        return (
            f"[{significance}] "
            f"Concept '{void.candidate.label}' sits in an unexplored "
            f"region pointing toward '{target.label}'. "
            f"Relevance to target: {void.relevance_score:.2f}. "
            f"Novelty (distance from existing): {void.novelty_score:.2f}. "
            f"Nearest existing solutions: {nearest_str}."
            f"{hybrid_context}"
        )
