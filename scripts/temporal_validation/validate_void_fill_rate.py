"""
scripts/temporal_validation/validate_void_fill_rate.py

Phase 3: Check how many TVA voids (t < 2019) were filled in (t >= 2019).

Fill definition:
  A void (A, B, midpoint C) is "filled" if any post-2019 paper's embedding
  is within cosine similarity θ of the SLERP midpoint C.

Baselines:
  - Anchor-nearby random: random pairs from top-300 C1-relevant candidates
    (same pool TVA uses — fair comparison)
  - Anchor-distant random: random pairs from full corpus (weak baseline)

Statistics:
  - Fisher's exact test for significance
  - Shuffle test (1000 permutations) for empirical p-value

Usage:
    python scripts/temporal_validation/validate_void_fill_rate.py
    python scripts/temporal_validation/validate_void_fill_rate.py --fill-threshold 0.82
    python scripts/temporal_validation/validate_void_fill_rate.py --skip-embed  # reuse saved val embeddings
"""

import argparse
import json
import random
from pathlib import Path
from scipy import stats

import numpy as np
from loguru import logger
from tqdm import tqdm

VOIDS_DIR = Path("data/processed/tvv")
VAL_JSONL = Path("data/processed/tvv/arxiv_val.jsonl")
VAL_EMBEDDINGS_NPZ = Path("data/processed/tvv/val_embeddings.npz")
COLLECTION_NAME = "tvv_arxiv_train"
RESULTS_PATH = Path("data/processed/tvv/fill_rate_results_v2.json")

DEFAULT_FILL_THRESHOLD = 0.82
BASELINE_SAMPLES = 200   # more samples for stable baseline
SHUFFLE_ROUNDS = 1000
C1_POOL = 300            # same as void search


def slerp_midpoint(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    combined = a + b
    norm = np.linalg.norm(combined)
    return combined / norm if norm > 0 else combined


def load_voids() -> list[dict]:
    voids = []
    for path in sorted(VOIDS_DIR.glob("voids_*.jsonl")):
        if "summary" in path.name:
            continue
        with open(path) as f:
            for line in f:
                voids.append(json.loads(line))
    logger.info(f"Loaded {len(voids)} voids")
    return voids


def load_or_embed_val(skip_embed: bool = False):
    """Load all val paper embeddings. Cache to NPZ to avoid re-running."""
    if skip_embed and VAL_EMBEDDINGS_NPZ.exists():
        logger.info(f"Loading cached val embeddings from {VAL_EMBEDDINGS_NPZ}")
        data = np.load(VAL_EMBEDDINGS_NPZ, allow_pickle=True)
        val_ids = list(data["ids"])
        val_matrix = data["embeddings"]
        logger.info(f"Loaded {len(val_ids):,} cached embeddings")
        return val_ids, val_matrix

    from vectordb.embedder import create_embedder
    embedder = create_embedder()

    val_papers = []
    with open(VAL_JSONL) as f:
        for line in f:
            val_papers.append(json.loads(line))

    logger.info(f"Embedding {len(val_papers):,} val papers (full set)...")
    val_embeddings = []
    BATCH = 64
    for i in tqdm(range(0, len(val_papers), BATCH), desc="Embedding val"):
        batch = val_papers[i:i+BATCH]
        texts = [f"{p['title']} {p['abstract']}" for p in batch]
        embs = [embedder.embed_query(t) for t in texts]
        val_embeddings.extend(embs)

    val_ids = [p["id"] for p in val_papers]
    val_matrix = np.array(val_embeddings, dtype=np.float32)

    VAL_EMBEDDINGS_NPZ.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(VAL_EMBEDDINGS_NPZ, ids=np.array(val_ids), embeddings=val_matrix)
    logger.info(f"Saved val embeddings → {VAL_EMBEDDINGS_NPZ}")
    return val_ids, val_matrix


def load_train_embeddings():
    import chromadb
    from configs.settings import settings
    client = chromadb.PersistentClient(path=str(settings.vectordb_path))
    col = client.get_collection(COLLECTION_NAME)
    FETCH_BATCH = 5000
    total = col.count()
    ids, vecs = [], []
    for offset in range(0, total, FETCH_BATCH):
        b = col.get(limit=FETCH_BATCH, offset=offset, include=["embeddings"])
        ids.extend(b["ids"])
        vecs.extend(b["embeddings"])
    return ids, np.array(vecs, dtype=np.float32)


def check_fill(
    midpoint: np.ndarray,
    val_matrix: np.ndarray,
    threshold: float,
    anchor_vec=None,
    anchor_threshold: float = 0.55,
    src_a=None,
    src_b=None,
    nontrivial_threshold: float = 0.0,
) -> tuple[bool, float]:
    """Check fill. Three versions:
    v1 raw:     anchor_vec=None
    v2 gated:   anchor_vec + anchor_threshold
    v3 quality: also src_a, src_b, nontrivial_threshold > 0
    """
    sims_mid = val_matrix @ midpoint
    if anchor_vec is not None:
        sims_anc = val_matrix @ anchor_vec
        mask = sims_anc >= anchor_threshold
        if not mask.any():
            return False, 0.0
        sims_mid = np.where(mask, sims_mid, -1.0)
    if src_a is not None and src_b is not None and nontrivial_threshold > 0:
        sims_a = val_matrix @ src_a
        sims_b = val_matrix @ src_b
        synthesis = sims_mid - np.maximum(sims_a, sims_b)
        sims_mid = np.where(synthesis >= nontrivial_threshold, sims_mid, -1.0)
    max_sim = float(sims_mid.max())
    return max_sim >= threshold, max_sim


def anchor_nearby_baseline(
    anchor_vec: np.ndarray,
    train_embeddings: np.ndarray,
    train_ids: list,
    val_matrix: np.ndarray,
    threshold: float,
    n_samples: int,
    rng: random.Random,
) -> list[dict]:
    """Random pairs from top-C1_POOL anchor-relevant candidates — fair baseline."""
    sims = train_embeddings @ anchor_vec
    top_idx = sims.argsort()[::-1][:C1_POOL].tolist()

    results = []
    for _ in range(n_samples):
        i, j = rng.sample(top_idx, 2)
        midpoint = slerp_midpoint(train_embeddings[i], train_embeddings[j])
        filled, max_sim = check_fill(midpoint, val_matrix, threshold)
        results.append({"filled": filled, "max_sim": max_sim})
    return results


def fisher_pvalue(tva_filled, tva_total, base_filled, base_total):
    """Fisher's exact test: is TVA fill rate significantly higher than baseline?"""
    table = [
        [tva_filled, tva_total - tva_filled],
        [base_filled, base_total - base_filled],
    ]
    _, p = stats.fisher_exact(table, alternative="greater")
    return p


def shuffle_test(tva_filled_rate, all_midpoints, val_matrix, threshold, rounds=1000):
    """Shuffle test: randomly reassign midpoints to check if lift is by chance."""
    n = len(all_midpoints)
    null_rates = []
    for _ in range(rounds):
        perm = np.random.permutation(n)
        filled = sum(
            1 for i in perm[:n//2]
            if check_fill(all_midpoints[i], val_matrix, threshold)[0]
        )
        null_rates.append(filled / (n // 2))
    empirical_p = np.mean(np.array(null_rates) >= tva_filled_rate)
    return empirical_p, null_rates


def run_validation(fill_threshold: float, skip_embed: bool = False):
    voids = load_voids()
    val_ids, val_matrix = load_or_embed_val(skip_embed)
    train_ids, train_embeddings = load_train_embeddings()
    id_to_vec = {train_ids[i]: train_embeddings[i] for i in range(len(train_ids))}
    id_to_idx = {train_ids[i]: i for i in range(len(train_ids))}

    # Load anchor vectors for baseline
    from vectordb.embedder import create_embedder
    embedder = create_embedder()
    anchor_defs = {
        "sched_opt": "kernel scheduler optimization and CPU affinity for multicore systems",
        "mm_vm":     "virtual memory management and page reclamation in operating systems",
        "ebpf_obs":  "eBPF programs for kernel tracing and system call observability",
        "hwsw_x86":  "hardware-software co-design for x86 processor microarchitecture features",
        "net_io":    "high-performance network I/O and packet processing in the kernel",
        "sync_lock": "synchronization primitives and lock-free data structures in concurrent systems",
    }
    anchor_vecs = {k: np.array(embedder.embed_query(v), dtype=np.float32)
                   for k, v in anchor_defs.items()}

    ANCHOR_THRESHOLD = 0.55   # val paper must be relevant to anchor
    NONTRIVIAL_THRESHOLD = 0.0  # fill_quality > 0 = filler closer to midpoint than sources

    # ── TVA void fill check — three versions ────────────────────────────
    logger.info(f"=== TVA Void Fill Rate (threshold={fill_threshold}) ===")
    tva_results = []
    tva_midpoints = []
    for v in tqdm(voids, desc="Checking TVA voids"):
        id_a = v["paper_a"]["id"]
        id_b = v["paper_b"]["id"]
        vec_a = id_to_vec.get(id_a)
        vec_b = id_to_vec.get(id_b)
        if vec_a is None or vec_b is None:
            continue
        midpoint = slerp_midpoint(vec_a, vec_b)
        anchor_vec = anchor_vecs[v["anchor_id"]]

        # v1: raw
        filled_v1, sim_v1 = check_fill(midpoint, val_matrix, fill_threshold)
        # v2: anchor-gated
        filled_v2, sim_v2 = check_fill(midpoint, val_matrix, fill_threshold,
                                        anchor_vec=anchor_vec,
                                        anchor_threshold=ANCHOR_THRESHOLD)
        # v3: anchor-gated + nontrivial
        filled_v3, sim_v3 = check_fill(midpoint, val_matrix, fill_threshold,
                                        anchor_vec=anchor_vec,
                                        anchor_threshold=ANCHOR_THRESHOLD,
                                        src_a=vec_a, src_b=vec_b,
                                        nontrivial_threshold=NONTRIVIAL_THRESHOLD)
        tva_results.append({
            "void_id": v["void_id"],
            "anchor_id": v["anchor_id"],
            "label": v["label"],
            "filled": filled_v1,
            "filled_v2": filled_v2,
            "filled_v3": filled_v3,
            "max_sim_to_midpoint": sim_v1,
            "paper_a": v["paper_a"],
            "paper_b": v["paper_b"],
        })
        tva_midpoints.append(midpoint)

    from collections import defaultdict
    by_anchor = defaultdict(list)
    for r in tva_results:
        by_anchor[r["anchor_id"]].append(r)

    def rate(results, key="filled"):
        n = sum(1 for r in results if r.get(key))
        return n, len(results), n/len(results) if results else 0

    tva_v1 = rate(tva_results, "filled")
    tva_v2 = rate(tva_results, "filled_v2")
    tva_v3 = rate(tva_results, "filled_v3")
    tva_fill_rate = tva_v1[2]

    # ── Anchor-nearby baseline — also three versions ────────────────────
    logger.info("=== Anchor-nearby Baseline (3 versions) ===")
    rng = random.Random(42)

    nearby_v1, nearby_v2, nearby_v3 = [], [], []
    for anchor_id, anchor_vec_item in anchor_vecs.items():
        n_for_anchor = len(by_anchor[anchor_id])
        if n_for_anchor == 0:
            continue
        sims = train_embeddings @ anchor_vec_item
        top_idx = sims.argsort()[::-1][:C1_POOL].tolist()
        n_samp = max(n_for_anchor * 3, BASELINE_SAMPLES // len(anchor_defs))
        for _ in range(n_samp):
            i, j = rng.sample(top_idx, 2)
            va = train_embeddings[i]
            vb = train_embeddings[j]
            mp = slerp_midpoint(va, vb)
            f1, s1 = check_fill(mp, val_matrix, fill_threshold)
            f2, s2 = check_fill(mp, val_matrix, fill_threshold,
                                 anchor_vec=anchor_vec_item,
                                 anchor_threshold=ANCHOR_THRESHOLD)
            f3, s3 = check_fill(mp, val_matrix, fill_threshold,
                                 anchor_vec=anchor_vec_item,
                                 anchor_threshold=ANCHOR_THRESHOLD,
                                 src_a=va, src_b=vb,
                                 nontrivial_threshold=NONTRIVIAL_THRESHOLD)
            nearby_v1.append({"filled": f1})
            nearby_v2.append({"filled": f2})
            nearby_v3.append({"filled": f3})

    base_v1 = rate(nearby_v1)
    base_v2 = rate(nearby_v2)
    base_v3 = rate(nearby_v3)
    base_fill_rate = base_v1[2]

    # ── Statistics ───────────────────────────────────────────────────────
    lift_v1 = tva_v1[2] / base_v1[2] if base_v1[2] > 0 else float("inf")
    lift_v2 = tva_v2[2] / base_v2[2] if base_v2[2] > 0 else float("inf")
    lift_v3 = tva_v3[2] / base_v3[2] if base_v3[2] > 0 else float("inf")
    lift = lift_v1

    p_fisher = fisher_pvalue(tva_v1[0], tva_v1[1], base_v1[0], base_v1[1])

    logger.info("Running shuffle test...")
    p_shuffle, null_dist = shuffle_test(
        tva_fill_rate, tva_midpoints, val_matrix, fill_threshold, SHUFFLE_ROUNDS
    )

    # ── Print results ────────────────────────────────────────────────────
    print(f"\n{'='*62}")
    print(f"{'Version':<25} {'TVA':>12} {'Baseline':>12} {'Lift':>8}")
    print(f"{'-'*62}")
    print(f"{'v1 raw fill':<25} {tva_v1[0]}/{tva_v1[1]}={tva_v1[2]:.0%}  {base_v1[0]}/{base_v1[1]}={base_v1[2]:.0%}  {lift_v1:.2f}x")
    print(f"{'v2 anchor-gated':<25} {tva_v2[0]}/{tva_v2[1]}={tva_v2[2]:.0%}  {base_v2[0]}/{base_v2[1]}={base_v2[2]:.0%}  {lift_v2:.2f}x")
    print(f"{'v3 nontrivial':<25} {tva_v3[0]}/{tva_v3[1]}={tva_v3[2]:.0%}  {base_v3[0]}/{base_v3[1]}={base_v3[2]:.0%}  {lift_v3:.2f}x")
    print(f"{'='*62}")
    print(f"Fisher p (v1): {p_fisher:.4f}  |  Shuffle p: {p_shuffle:.4f}")
    print(f"{'='*62}\n")

    print("Per-anchor fill rate (v1 / v2 / v3):")
    for anchor_id, results in sorted(by_anchor.items()):
        n1 = sum(1 for r in results if r["filled"])
        n2 = sum(1 for r in results if r["filled_v2"])
        n3 = sum(1 for r in results if r["filled_v3"])
        n = len(results)
        print(f"  {anchor_id:<15}: {n1}/{n}={n1/n:.0%}  {n2}/{n}={n2/n:.0%}  {n3}/{n}={n3/n:.0%}")

    # ── Save ─────────────────────────────────────────────────────────────
    output = {
        "fill_threshold": fill_threshold,
        "tva": {"total": tva_total, "filled": tva_filled, "fill_rate": tva_fill_rate, "results": tva_results},
        "baseline_nearby": {"total": base_total, "filled": base_filled, "fill_rate": base_fill_rate},
        "lift": lift,
        "p_fisher": p_fisher,
        "p_shuffle": p_shuffle,
        "shuffle_null_mean": float(np.mean(null_dist)),
        "shuffle_null_std": float(np.std(null_dist)),
    }
    with open(RESULTS_PATH, "w") as f:
        json.dump(output, f, indent=2)
    logger.info(f"Results → {RESULTS_PATH}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fill-threshold", type=float, default=DEFAULT_FILL_THRESHOLD)
    parser.add_argument("--skip-embed", action="store_true", help="Reuse cached val embeddings")
    args = parser.parse_args()
    run_validation(args.fill_threshold, args.skip_embed)


if __name__ == "__main__":
    main()
