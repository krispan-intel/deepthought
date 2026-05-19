"""
scripts/temporal_validation/reverse_tva_classifier.py

Reverse TVA Classifier — paper-centered topological impact classification.

Given a new paper P_t and a historical corpus DB_{t-1}, classify P_t's
topological impact as one of:

  DENSIFICATION        — falls in already-dense region; no new structure
  BOUNDARY_EXPANSION   — extends one direction without bridging a gap
  CANDIDATE_VOID_FILL  — first occupant of a vacant bridge region
  OUT_OF_DOMAIN        — not in Anchor's problem space

This is an offline retrospective version: runs against a pre-built
ChromaDB collection. The same logic applies online (streaming).

Usage:
    # Classify val papers from a split against its train collection
    python scripts/temporal_validation/reverse_tva_classifier.py \\
      --split t5 \\
      --output data/processed/tvv/rolling/t5/reverse_tva_events.jsonl

    # Quick test on first 50 val papers
    python scripts/temporal_validation/reverse_tva_classifier.py \\
      --split t5 --max-papers 50

Algorithm per paper P_t:
  1. Retrieve k=50 local historical neighbors N_t from train collection
  2. Compute local density = mean sim(P_t, N_t[:10])
  3. Find best candidate bridge pair (A, B) in N_t by bridge_score:
       bridge_score = sim(P,A) + sim(P,B) - 1.5*sim(A,B)
  4. Compute midpoint m = slerp(A, B)
  5. Check historical vacancy: kNN(m, train, k=5).max_sim < θ_vacant
  6. Classify:
       local_density > θ_dense              → DENSIFICATION
       vacant AND sim(P,m) > θ_fill         → CANDIDATE_VOID_FILL
       otherwise                            → BOUNDARY_EXPANSION
  7. If Anchor provided: check eligibility (sim(P,anchor) > τ_anchor)
"""

import argparse
import json
from pathlib import Path

import numpy as np
from loguru import logger

OUTPUT_DIR = Path("data/processed/tvv/rolling")

SPLITS = {
    "t1": {"train_end": 2010, "val_start": 2011, "val_end": 2016},
    "t2": {"train_end": 2012, "val_start": 2013, "val_end": 2018},
    "t3": {"train_end": 2014, "val_start": 2015, "val_end": 2020},
    "t4": {"train_end": 2016, "val_start": 2017, "val_end": 2022},
    "t5": {"train_end": 2018, "val_start": 2019, "val_end": 2024},
}

ANCHORS = {
    "sched_opt":  "kernel scheduler optimization and CPU affinity for multicore systems",
    "mm_vm":      "virtual memory management and page reclamation in operating systems",
    "ebpf_obs":   "eBPF programs for kernel tracing and system call observability",
    "hwsw_x86":   "hardware-software co-design for x86 processor microarchitecture features",
    "net_io":     "high-performance network I/O and packet processing in the kernel",
    "sync_lock":  "synchronization primitives and lock-free data structures in concurrent systems",
    "mem_alloc":  "memory allocator design and heap fragmentation in systems software",
    "virt_hyp":   "virtualization and hypervisor design for cloud workloads",
    "power_mgmt": "dynamic power management and CPU frequency scaling",
    "storage_io": "storage I/O path optimization and NVMe device drivers",
}

# Thresholds — calibrate from LLM-labeled ground truth once available
#
# NOTE: In high-dimensional anisotropic corpora (BGE-M3 1024d), all cosine
# similarities are compressed into ~[0.60, 0.95]. Absolute vacancy thresholds
# (e.g., THETA_VACANT=0.75) will never trigger because the corpus is so dense
# that every midpoint has a neighbor above 0.85.
#
# We therefore use RELATIVE vacancy: a midpoint is "vacant" if its local
# density is significantly lower than the mean local density of its anchor's
# C1 pool. VACANCY_GAP is the minimum required gap (in cosine units).
#
# Similarly THETA_DENSE uses a percentile of the corpus distribution, not
# an absolute value. These are re-estimated per split/anchor at runtime if
# DYNAMIC_THRESHOLDS=True.
THETA_DENSE_PCTILE = 80  # local_density above this percentile → densification
THETA_FILL = 0.82        # sim(P, midpoint) above this → near midpoint
VACANCY_GAP = 0.03       # midpoint_max_sim must be < (local_density - VACANCY_GAP)
BRIDGE_TAU_FACTOR = 0.97 # bridge candidate must reach tau = min(sim_pa, sim_pb) * factor
THETA_ANCHOR = 0.55      # sim(P, anchor) above this → in-domain
K_NEIGHBORS = 50         # local neighborhood size
K_BRIDGE_PAIRS = 20      # top pairs to consider for bridge search
K_VACANCY = 5            # neighbors to check for midpoint vacancy
K_DENSITY = 10           # neighbors to average for local density


def slerp(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    c = a + b
    n = np.linalg.norm(c)
    return c / n if n > 0 else c


def bridge_score(sim_pa: float, sim_pb: float, sim_ab: float) -> float:
    """Higher when P bridges two dissimilar regions."""
    return sim_pa + sim_pb - 1.5 * sim_ab


def classify_paper(
    pt_vec: np.ndarray,
    train_emb: np.ndarray,
    train_ids: list[str],
    anchor_vecs: dict[str, np.ndarray],
    anchor_id: str | None = None,
    theta_dense: float = 0.80,  # corpus-calibrated; passed in from run_split
) -> dict:
    """
    Classify a single val paper against the train corpus.

    Returns a dict with event_label, scores, and diagnostics.

    Vacancy is relative: midpoint_max_sim < (local_density - VACANCY_GAP).
    This handles the anisotropy of high-dimensional embedding corpora where
    absolute sim values are compressed into a narrow range.
    """
    # Step 1: local neighborhood
    sims_to_train = train_emb @ pt_vec
    top_idx = sims_to_train.argsort()[::-1][:K_NEIGHBORS].tolist()
    top_sims = sims_to_train[top_idx]

    # Step 2: local density (mean of top-K_DENSITY neighbors)
    local_density = float(top_sims[:K_DENSITY].mean())

    # Step 3: anchor eligibility
    anchor_sim = None
    anchor_eligible = True
    if anchor_id and anchor_id in anchor_vecs:
        anchor_sim = float(anchor_vecs[anchor_id] @ pt_vec)
        anchor_eligible = anchor_sim >= THETA_ANCHOR

    # Step 4: find best bridge pair among top K_BRIDGE_PAIRS
    k = min(K_BRIDGE_PAIRS, len(top_idx))
    neighbor_vecs = train_emb[top_idx[:k]]
    local_sim_matrix = neighbor_vecs @ neighbor_vecs.T

    best_score = -np.inf
    best_pair = (0, 1)
    for i in range(k):
        for j in range(i + 1, k):
            score = bridge_score(
                float(top_sims[i]),
                float(top_sims[j]),
                float(local_sim_matrix[i, j]),
            )
            if score > best_score:
                best_score = score
                best_pair = (i, j)

    idx_a, idx_b = best_pair
    vec_a = neighbor_vecs[idx_a]
    vec_b = neighbor_vecs[idx_b]
    sim_ab = float(local_sim_matrix[idx_a, idx_b])

    # Step 5: BRIDGE VACANCY check
    # Vacancy = no existing train paper simultaneously bridges A and B.
    # We look for papers with sim(X, A) >= tau AND sim(X, B) >= tau.
    # tau = min(sim_pa, sim_pb) * BRIDGE_TAU_FACTOR — "must be as close to
    # the source as P_t is, proportionally".
    # Exclude A and B themselves (indices idx_a, idx_b in neighbor list;
    # we use the actual train indices to exclude them).
    train_idx_a = top_idx[idx_a]
    train_idx_b = top_idx[idx_b]
    tau_bridge = min(float(top_sims[idx_a]), float(top_sims[idx_b])) * BRIDGE_TAU_FACTOR
    sims_to_a = train_emb @ vec_a
    sims_to_b = train_emb @ vec_b
    # Count bridging papers (exclude A, B themselves)
    mask = np.ones(len(train_emb), dtype=bool)
    mask[train_idx_a] = False
    mask[train_idx_b] = False
    n_bridges = int(((sims_to_a >= tau_bridge) & (sims_to_b >= tau_bridge) & mask).sum())
    vacant = n_bridges == 0

    midpoint = slerp(vec_a, vec_b)
    midpoint_max_sim = float((train_emb @ midpoint).max())
    vacancy_threshold = tau_bridge
    sim_pt_to_mid = float(midpoint @ pt_vec)
    # Also check: does P_t itself bridge A and B?
    pt_bridges = (float(train_emb[train_idx_a] @ pt_vec) >= tau_bridge and
                  float(train_emb[train_idx_b] @ pt_vec) >= tau_bridge)

    # Step 6: classify
    if not anchor_eligible:
        event_label = "OUT_OF_DOMAIN"
    elif local_density >= theta_dense:
        event_label = "DENSIFICATION"
    elif vacant and sim_pt_to_mid >= THETA_FILL:
        event_label = "CANDIDATE_VOID_FILL"
    else:
        event_label = "BOUNDARY_EXPANSION"

    return {
        "event_label": event_label,
        "local_density": round(local_density, 4),
        "bridge_score": round(float(best_score), 4),
        "sim_a": round(float(top_sims[idx_a]), 4),
        "sim_b": round(float(top_sims[idx_b]), 4),
        "sim_ab": round(sim_ab, 4),
        "midpoint_max_sim": round(midpoint_max_sim, 4),
        "vacancy_threshold": round(vacancy_threshold, 4),
        "vacant": vacant,
        "n_existing_bridges": n_bridges,
        "pt_bridges": pt_bridges,
        "sim_pt_to_midpoint": round(sim_pt_to_mid, 4),
        "anchor_sim": round(anchor_sim, 4) if anchor_sim is not None else None,
        "anchor_eligible": anchor_eligible,
        "neighbor_a_id": train_ids[top_idx[idx_a]],
        "neighbor_b_id": train_ids[top_idx[idx_b]],
        "thresholds": {
            "theta_dense_pctile": THETA_DENSE_PCTILE,
            "theta_dense_value": round(theta_dense, 4),
            "theta_fill": THETA_FILL,
            "bridge_tau_factor": BRIDGE_TAU_FACTOR,
            "vacancy_gap": VACANCY_GAP,
            "theta_anchor": THETA_ANCHOR,
        },
    }


def run_split(split_name: str, max_papers: int | None, anchor_filter: str | None):
    import chromadb
    from configs.settings import settings
    from vectordb.embedder import create_embedder

    out_dir = OUTPUT_DIR / split_name
    out_path = out_dir / "reverse_tva_events.jsonl"

    client = chromadb.PersistentClient(path=str(settings.vectordb_path))
    train_col = client.get_collection(f"tvv_rolling_{split_name}_train")
    val_col = client.get_collection(f"tvv_rolling_{split_name}_val")

    # Load train embeddings
    FETCH = 5000
    t_ids, t_vecs = [], []
    for offset in range(0, train_col.count(), FETCH):
        b = train_col.get(limit=FETCH, offset=offset, include=["embeddings"])
        t_ids.extend(b["ids"])
        t_vecs.extend(b["embeddings"])
    train_emb = np.array(t_vecs, dtype=np.float32)
    logger.info(f"[{split_name}] Train: {len(t_ids):,} papers loaded")

    # Load val embeddings + metadata
    v_ids, v_vecs, v_metas = [], [], []
    for offset in range(0, val_col.count(), FETCH):
        b = val_col.get(limit=FETCH, offset=offset, include=["embeddings", "metadatas"])
        v_ids.extend(b["ids"])
        v_vecs.extend(b["embeddings"])
        v_metas.extend(b["metadatas"])
    val_emb = np.array(v_vecs, dtype=np.float32)
    logger.info(f"[{split_name}] Val: {len(v_ids):,} papers loaded")

    if max_papers:
        v_ids = v_ids[:max_papers]
        val_emb = val_emb[:max_papers]
        v_metas = v_metas[:max_papers]

    # Embed anchors
    embedder = create_embedder()
    anchor_vecs = {
        aid: np.array(embedder.embed_query(atext), dtype=np.float32)
        for aid, atext in ANCHORS.items()
    }

    # Corpus-calibrated density threshold: THETA_DENSE_PCTILE of all val papers' local density
    # We sample 500 val papers to estimate the distribution quickly
    rng = np.random.default_rng(42)
    sample_idx = rng.choice(len(v_ids), size=min(500, len(v_ids)), replace=False)
    sample_densities = []
    for idx in sample_idx:
        sims = train_emb @ val_emb[idx]
        sample_densities.append(float(np.sort(sims)[::-1][:K_DENSITY].mean()))
    theta_dense = float(np.percentile(sample_densities, THETA_DENSE_PCTILE))
    logger.info(f"[{split_name}] theta_dense (p{THETA_DENSE_PCTILE} of sample) = {theta_dense:.4f}  "
                f"(distribution: p10={np.percentile(sample_densities,10):.3f}  "
                f"median={np.median(sample_densities):.3f}  "
                f"p90={np.percentile(sample_densities,90):.3f})")

    # Classify each val paper (against each applicable anchor)
    anchors_to_run = [anchor_filter] if anchor_filter else list(ANCHORS.keys())

    results = []
    for anchor_id in anchors_to_run:
        logger.info(f"[{split_name}] Anchor: {anchor_id}")
        av = anchor_vecs[anchor_id]
        # Pre-filter: only val papers with sim to anchor > 0.4 (broad pre-filter)
        anchor_sims = val_emb @ av
        eligible_idx = np.where(anchor_sims >= 0.40)[0]
        logger.info(f"  Pre-filtered val papers: {len(eligible_idx)} / {len(v_ids)}")

        for rank, idx in enumerate(eligible_idx):
            pt_vec = val_emb[idx]
            result = classify_paper(
                pt_vec=pt_vec,
                train_emb=train_emb,
                train_ids=t_ids,
                anchor_vecs=anchor_vecs,
                anchor_id=anchor_id,
                theta_dense=theta_dense,
            )
            result["paper_id"] = v_ids[idx]
            result["paper_title"] = (v_metas[idx] or {}).get("title", "")
            result["paper_year"] = (v_metas[idx] or {}).get("year")
            result["split"] = split_name
            result["anchor_id"] = anchor_id
            result["anchor_sim_prefilter"] = round(float(anchor_sims[idx]), 4)
            results.append(result)

    with open(out_path, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")
    logger.info(f"[{split_name}] {len(results)} classifications → {out_path}")

    # Summary
    from collections import Counter
    by_anchor: dict[str, Counter] = {}
    for r in results:
        aid = r["anchor_id"]
        if aid not in by_anchor:
            by_anchor[aid] = Counter()
        by_anchor[aid][r["event_label"]] += 1

    print(f"\n[{split_name}] REVERSE TVA EVENT DISTRIBUTION")
    print(f"{'Anchor':<15} {'DENS':>6} {'BOUND':>6} {'VOID':>6} {'OOD':>6} {'total':>7}")
    print("-" * 50)
    for anchor_id in anchors_to_run:
        c = by_anchor.get(anchor_id, Counter())
        total = sum(c.values())
        print(f"{anchor_id:<15} "
              f"{c['DENSIFICATION']:>6} "
              f"{c['BOUNDARY_EXPANSION']:>6} "
              f"{c['CANDIDATE_VOID_FILL']:>6} "
              f"{c['OUT_OF_DOMAIN']:>6} "
              f"{total:>7}")

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=list(SPLITS.keys()), default="t5")
    parser.add_argument("--max-papers", type=int, default=None,
                        help="Limit val papers per anchor (for quick test)")
    parser.add_argument("--anchor", choices=list(ANCHORS.keys()), default=None,
                        help="Run on a single anchor only")
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    run_split(args.split, args.max_papers, args.anchor)


if __name__ == "__main__":
    main()
