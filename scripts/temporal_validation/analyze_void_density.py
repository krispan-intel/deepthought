"""
scripts/temporal_validation/analyze_void_density.py

Check if TVA voids are in lower-density regions than anchor-nearby random midpoints.
This tests the "hard void" hypothesis: TVA finds sparse, less-touched regions.

Usage:
    python scripts/temporal_validation/analyze_void_density.py
    python scripts/temporal_validation/analyze_void_density.py --k 20
"""

import argparse
import json
import random
from pathlib import Path
from scipy import stats

import numpy as np
from loguru import logger

VOIDS_DIR = Path("data/processed/tvv")
COLLECTION_NAME = "tvv_arxiv_train"
C1_POOL = 300
K_NEIGHBORS = 10  # k for local density estimation


def slerp_midpoint(a, b):
    c = a + b
    n = np.linalg.norm(c)
    return c / n if n > 0 else c


def local_density(point: np.ndarray, all_embeddings: np.ndarray, k: int) -> float:
    """Local density = mean cosine similarity to k nearest neighbors."""
    sims = all_embeddings @ point
    top_k = np.sort(sims)[::-1][1:k+1]  # skip self (index 0)
    return float(top_k.mean())


def load_train_embeddings():
    import chromadb
    from configs.settings import settings
    client = chromadb.PersistentClient(path=str(settings.vectordb_path))
    col = client.get_collection(COLLECTION_NAME)
    FETCH = 5000
    total = col.count()
    ids, vecs = [], []
    for offset in range(0, total, FETCH):
        b = col.get(limit=FETCH, offset=offset, include=["embeddings"])
        ids.extend(b["ids"])
        vecs.extend(b["embeddings"])
    return ids, np.array(vecs, dtype=np.float32)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, default=K_NEIGHBORS)
    args = parser.parse_args()

    train_ids, train_embeddings = load_train_embeddings()
    id_to_vec = {train_ids[i]: train_embeddings[i] for i in range(len(train_ids))}
    id_to_idx = {train_ids[i]: i for i in range(len(train_ids))}

    # Load anchor vectors
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

    # Load TVA voids
    voids = []
    for path in sorted(VOIDS_DIR.glob("voids_*.jsonl")):
        if "summary" in path.name:
            continue
        with open(path) as f:
            for line in f:
                voids.append(json.loads(line))
    logger.info(f"Loaded {len(voids)} TVA voids")

    # Compute density for TVA void midpoints
    logger.info(f"Computing density for TVA void midpoints (k={args.k})...")
    tva_densities = []
    tva_pair_distances = []
    for v in voids:
        id_a = v["paper_a"]["id"]
        id_b = v["paper_b"]["id"]
        vec_a = id_to_vec.get(id_a)
        vec_b = id_to_vec.get(id_b)
        if vec_a is None or vec_b is None:
            continue
        midpoint = slerp_midpoint(vec_a, vec_b)
        density = local_density(midpoint, train_embeddings, args.k)
        pair_dist = float(1 - np.dot(vec_a, vec_b))  # cosine distance
        tva_densities.append(density)
        tva_pair_distances.append(pair_dist)

    # Compute density for anchor-nearby random midpoints
    logger.info("Computing density for anchor-nearby random midpoints...")
    rng = random.Random(42)
    baseline_densities = []
    baseline_pair_distances = []
    n_baseline = len(tva_densities) * 3  # 3x more for stable estimate

    for anchor_id, anchor_vec in anchor_vecs.items():
        sims = train_embeddings @ anchor_vec
        top_idx = sims.argsort()[::-1][:C1_POOL].tolist()
        n_per_anchor = n_baseline // len(anchor_vecs)
        for _ in range(n_per_anchor):
            i, j = rng.sample(top_idx, 2)
            vec_a = train_embeddings[i]
            vec_b = train_embeddings[j]
            midpoint = slerp_midpoint(vec_a, vec_b)
            density = local_density(midpoint, train_embeddings, args.k)
            pair_dist = float(1 - np.dot(vec_a, vec_b))
            baseline_densities.append(density)
            baseline_pair_distances.append(pair_dist)

    tva_d = np.array(tva_densities)
    base_d = np.array(baseline_densities)
    tva_pd = np.array(tva_pair_distances)
    base_pd = np.array(baseline_pair_distances)

    # Statistics
    t_stat, p_density = stats.ttest_ind(tva_d, base_d, alternative='less')
    t_stat2, p_dist = stats.ttest_ind(tva_pd, base_pd, alternative='greater')

    print(f"\n{'='*55}")
    print(f"LOCAL DENSITY (k={args.k} nearest neighbors)")
    print(f"TVA void midpoints:        {tva_d.mean():.4f} ± {tva_d.std():.4f} (n={len(tva_d)})")
    print(f"Anchor-nearby random:      {base_d.mean():.4f} ± {base_d.std():.4f} (n={len(base_d)})")
    print(f"TVA < baseline? p = {p_density:.4f}  {'✅ YES' if p_density < 0.05 else '❌ NO'}")
    print()
    print(f"PAIR DISTANCE (source A ↔ source B)")
    print(f"TVA pair distance:         {tva_pd.mean():.4f} ± {tva_pd.std():.4f}")
    print(f"Anchor-nearby pair dist:   {base_pd.mean():.4f} ± {base_pd.std():.4f}")
    print(f"TVA > baseline? p = {p_dist:.4f}  {'✅ YES (TVA pairs more distant)' if p_dist < 0.05 else '❌ NO'}")
    print(f"{'='*55}\n")

    if p_density < 0.05:
        print("✅ HARD VOID HYPOTHESIS SUPPORTED:")
        print("   TVA midpoints are in significantly lower-density regions.")
        print("   Lower fill rate is expected — TVA finds sparse, less-touched voids.")
    else:
        print("❌ Hard void hypothesis not supported by density alone.")
        print("   TVA and baseline midpoints have similar local density.")

    if p_dist < 0.05:
        print("✅ TVA selects more distant source pairs (synthesis voids).")
    else:
        print("   TVA and baseline have similar source pair distances.")

    # Save
    results = {
        "k": args.k,
        "tva": {"density_mean": float(tva_d.mean()), "density_std": float(tva_d.std()),
                "pair_dist_mean": float(tva_pd.mean()), "n": len(tva_d)},
        "baseline": {"density_mean": float(base_d.mean()), "density_std": float(base_d.std()),
                     "pair_dist_mean": float(base_pd.mean()), "n": len(base_d)},
        "p_density_tva_lower": float(p_density),
        "p_dist_tva_greater": float(p_dist),
    }
    out = VOIDS_DIR / "void_density_analysis.json"
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"Results → {out}")


if __name__ == "__main__":
    main()
