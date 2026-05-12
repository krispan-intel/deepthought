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


def check_fill(midpoint: np.ndarray, val_matrix: np.ndarray, threshold: float) -> tuple[bool, float]:
    sims = val_matrix @ midpoint
    max_sim = float(sims.max())
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

    # ── TVA void fill check ─────────────────────────────────────────────
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
        filled, max_sim = check_fill(midpoint, val_matrix, fill_threshold)
        tva_results.append({
            "void_id": v["void_id"],
            "anchor_id": v["anchor_id"],
            "label": v["label"],
            "filled": filled,
            "max_sim_to_midpoint": max_sim,
            "paper_a": v["paper_a"],
            "paper_b": v["paper_b"],
        })
        tva_midpoints.append(midpoint)

    tva_filled = sum(1 for r in tva_results if r["filled"])
    tva_total = len(tva_results)
    tva_fill_rate = tva_filled / tva_total if tva_total else 0

    # ── Anchor-nearby baseline (fair) ───────────────────────────────────
    logger.info("=== Anchor-nearby Baseline ===")
    rng = random.Random(42)
    from collections import defaultdict
    by_anchor = defaultdict(list)
    for r in tva_results:
        by_anchor[r["anchor_id"]].append(r)

    nearby_results = []
    for anchor_id, anchor_vecs_item in anchor_vecs.items():
        n_for_anchor = len(by_anchor[anchor_id])
        if n_for_anchor == 0:
            continue
        res = anchor_nearby_baseline(
            anchor_vecs_item, train_embeddings, train_ids,
            val_matrix, fill_threshold,
            n_samples=max(n_for_anchor * 3, BASELINE_SAMPLES // len(anchor_defs)),
            rng=rng,
        )
        nearby_results.extend(res)

    base_filled = sum(1 for r in nearby_results if r["filled"])
    base_total = len(nearby_results)
    base_fill_rate = base_filled / base_total if base_total else 0

    # ── Statistics ───────────────────────────────────────────────────────
    lift = tva_fill_rate / base_fill_rate if base_fill_rate > 0 else float("inf")
    p_fisher = fisher_pvalue(tva_filled, tva_total, base_filled, base_total)

    logger.info("Running shuffle test...")
    p_shuffle, null_dist = shuffle_test(
        tva_fill_rate, tva_midpoints, val_matrix, fill_threshold, SHUFFLE_ROUNDS
    )

    # ── Print results ────────────────────────────────────────────────────
    print(f"\n{'='*55}")
    print(f"TVA fill rate:         {tva_filled}/{tva_total} = {tva_fill_rate:.1%}")
    print(f"Anchor-nearby baseline:{base_filled}/{base_total} = {base_fill_rate:.1%}")
    print(f"Lift:                  {lift:.2f}x")
    print(f"Fisher p-value:        {p_fisher:.4f}")
    print(f"Shuffle p-value:       {p_shuffle:.4f} ({SHUFFLE_ROUNDS} rounds)")
    print(f"{'='*55}\n")

    print("Per-anchor fill rate:")
    for anchor_id, results in sorted(by_anchor.items()):
        n_f = sum(1 for r in results if r["filled"])
        print(f"  {anchor_id:<15}: {n_f}/{len(results)} = {n_f/len(results):.0%}")

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
