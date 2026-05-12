"""
scripts/temporal_validation/analyze_fill_quality.py

Novelty and fill quality analysis for TVV experiment.

Runs four analyses:
1. TVA void novelty vs anchor-nearby baseline novelty
2. Logistic regression: filled ~ novelty + density + pair_dist + anchor_sim
3. Fill quality: sim(filler, midpoint) - max(sim(filler, source_A), sim(filler, source_B))
4. Bin analysis: fill rate / fill quality by novelty quartile

Usage:
    python scripts/temporal_validation/analyze_fill_quality.py
    python scripts/temporal_validation/analyze_fill_quality.py --skip-embed
"""

import argparse
import json
import random
from pathlib import Path

import numpy as np
from loguru import logger
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

VOIDS_DIR = Path("data/processed/tvv")
VAL_EMBEDDINGS_NPZ = Path("data/processed/tvv/val_embeddings.npz")
COLLECTION_NAME = "tvv_arxiv_train"
C1_POOL = 300
BASELINE_PER_ANCHOR = 30


def slerp_midpoint(a, b):
    c = a + b
    n = np.linalg.norm(c)
    return c / n if n > 0 else c


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


def void_novelty(midpoint, corpus_matrix):
    """1 - max cosine similarity to any corpus document (C4 vacancy)."""
    sims = corpus_matrix @ midpoint
    return float(1 - sims.max())


def fill_quality(filler_vec, midpoint, src_a, src_b):
    """sim(filler, midpoint) - max(sim(filler, source_A), sim(filler, source_B))."""
    sim_mid = float(np.dot(filler_vec, midpoint))
    sim_a = float(np.dot(filler_vec, src_a))
    sim_b = float(np.dot(filler_vec, src_b))
    return sim_mid - max(sim_a, sim_b)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-embed", action="store_true")
    parser.add_argument("--fill-threshold", type=float, default=0.82)
    args = parser.parse_args()

    train_ids, train_embeddings = load_train_embeddings()
    id_to_vec = {train_ids[i]: train_embeddings[i] for i in range(len(train_ids))}

    # Load val embeddings
    if VAL_EMBEDDINGS_NPZ.exists():
        logger.info("Loading cached val embeddings...")
        data = np.load(VAL_EMBEDDINGS_NPZ, allow_pickle=True)
        val_ids = list(data["ids"])
        val_matrix = data["embeddings"]
    else:
        logger.error("Val embeddings not found. Run validate_void_fill_rate.py first.")
        return

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

    # ── Build TVA void records ──────────────────────────────────────────
    logger.info("Computing TVA void features...")
    tva_records = []
    for v in voids:
        id_a = v["paper_a"]["id"]
        id_b = v["paper_b"]["id"]
        vec_a = id_to_vec.get(id_a)
        vec_b = id_to_vec.get(id_b)
        if vec_a is None or vec_b is None:
            continue
        midpoint = slerp_midpoint(vec_a, vec_b)
        anchor_vec = anchor_vecs[v["anchor_id"]]

        novelty = void_novelty(midpoint, train_embeddings)
        anchor_sim = float(np.dot(midpoint, anchor_vec))
        pair_dist = float(1 - np.dot(vec_a, vec_b))
        local_dens = float((train_embeddings @ midpoint).mean())

        # Check fill
        val_sims = val_matrix @ midpoint
        max_val_sim = float(val_sims.max())
        filled = max_val_sim >= args.fill_threshold

        # Fill quality if filled
        fq = None
        if filled:
            best_filler_idx = int(val_sims.argmax())
            filler_vec = val_matrix[best_filler_idx]
            fq = fill_quality(filler_vec, midpoint, vec_a, vec_b)

        tva_records.append({
            "anchor_id": v["anchor_id"],
            "novelty": novelty,
            "anchor_sim": anchor_sim,
            "pair_dist": pair_dist,
            "local_density": local_dens,
            "filled": int(filled),
            "max_val_sim": max_val_sim,
            "fill_quality": fq,
        })

    # ── Build baseline records ──────────────────────────────────────────
    logger.info("Computing anchor-nearby baseline features...")
    rng = random.Random(42)
    base_records = []
    for anchor_id, anchor_vec in anchor_vecs.items():
        sims = train_embeddings @ anchor_vec
        top_idx = sims.argsort()[::-1][:C1_POOL].tolist()
        for _ in range(BASELINE_PER_ANCHOR):
            i, j = rng.sample(top_idx, 2)
            vec_a = train_embeddings[i]
            vec_b = train_embeddings[j]
            midpoint = slerp_midpoint(vec_a, vec_b)
            novelty = void_novelty(midpoint, train_embeddings)
            anchor_sim = float(np.dot(midpoint, anchor_vec))
            pair_dist = float(1 - np.dot(vec_a, vec_b))
            local_dens = float((train_embeddings @ midpoint).mean())
            val_sims = val_matrix @ midpoint
            max_val_sim = float(val_sims.max())
            filled = max_val_sim >= args.fill_threshold
            fq = None
            if filled:
                best_filler_idx = int(val_sims.argmax())
                filler_vec = val_matrix[best_filler_idx]
                fq = fill_quality(filler_vec, midpoint, vec_a, vec_b)
            base_records.append({
                "novelty": novelty, "anchor_sim": anchor_sim,
                "pair_dist": pair_dist, "local_density": local_dens,
                "filled": int(filled), "fill_quality": fq,
            })

    # ── Analysis 1: Novelty comparison ─────────────────────────────────
    tva_nov = np.array([r["novelty"] for r in tva_records])
    base_nov = np.array([r["novelty"] for r in base_records])
    _, p_nov = stats.ttest_ind(tva_nov, base_nov)

    print(f"\n{'='*55}")
    print("ANALYSIS 1: Void Novelty (1 - max_sim_to_corpus)")
    print(f"TVA:      {tva_nov.mean():.4f} ± {tva_nov.std():.4f}")
    print(f"Baseline: {base_nov.mean():.4f} ± {base_nov.std():.4f}")
    print(f"Difference p = {p_nov:.4f}  {'(significant)' if p_nov < 0.05 else '(not significant)'}")

    # ── Analysis 2: Logistic regression ────────────────────────────────
    X = np.array([[r["novelty"], r["local_density"], r["pair_dist"], r["anchor_sim"]]
                  for r in tva_records])
    y = np.array([r["filled"] for r in tva_records])
    if y.sum() > 0 and y.sum() < len(y):
        scaler = StandardScaler()
        X_s = scaler.fit_transform(X)
        try:
            lr = LogisticRegression(max_iter=500)
            lr.fit(X_s, y)
            features = ["novelty", "local_density", "pair_dist", "anchor_sim"]
            print(f"\n{'='*55}")
            print("ANALYSIS 2: Logistic regression (filled ~ features)")
            for feat, coef in zip(features, lr.coef_[0]):
                print(f"  {feat:<15}: coef = {coef:+.3f}")
        except Exception as e:
            print(f"Logistic regression failed: {e}")

    # ── Analysis 3: Fill quality ────────────────────────────────────────
    tva_fq = [r["fill_quality"] for r in tva_records if r["fill_quality"] is not None]
    base_fq = [r["fill_quality"] for r in base_records if r["fill_quality"] is not None]

    print(f"\n{'='*55}")
    print("ANALYSIS 3: Fill Quality (sim_midpoint - max_sim_sources)")
    if tva_fq and base_fq:
        tva_fq_arr = np.array(tva_fq)
        base_fq_arr = np.array(base_fq)
        _, p_fq = stats.ttest_ind(tva_fq_arr, base_fq_arr)
        print(f"TVA filled voids:   n={len(tva_fq)} mean={tva_fq_arr.mean():.4f} ± {tva_fq_arr.std():.4f}")
        print(f"Baseline filled:    n={len(base_fq)} mean={base_fq_arr.mean():.4f} ± {base_fq_arr.std():.4f}")
        print(f"TVA > baseline? p = {p_fq:.4f}  {'✅' if p_fq < 0.05 and tva_fq_arr.mean() > base_fq_arr.mean() else '❌'}")
    else:
        print("Not enough filled voids for quality comparison.")

    # ── Analysis 4: Bin analysis ────────────────────────────────────────
    print(f"\n{'='*55}")
    print("ANALYSIS 4: Fill rate by novelty quartile (TVA)")
    quartiles = np.percentile(tva_nov, [25, 50, 75])
    bins = [
        ("Q1 (lowest novelty)", tva_nov <= quartiles[0]),
        ("Q2",                  (tva_nov > quartiles[0]) & (tva_nov <= quartiles[1])),
        ("Q3",                  (tva_nov > quartiles[1]) & (tva_nov <= quartiles[2])),
        ("Q4 (highest novelty)",tva_nov > quartiles[2]),
    ]
    y_tva = np.array([r["filled"] for r in tva_records])
    for label, mask in bins:
        n = mask.sum()
        if n > 0:
            rate = y_tva[mask].mean()
            print(f"  {label:<25}: {y_tva[mask].sum()}/{n} = {rate:.0%}")

    print(f"{'='*55}\n")

    # Save
    out = {"tva": tva_records, "baseline": base_records[:50]}  # sample baseline for size
    with open(VOIDS_DIR / "fill_quality_analysis.json", "w") as f:
        json.dump(out, f, indent=2)
    logger.info(f"Saved → {VOIDS_DIR}/fill_quality_analysis.json")


if __name__ == "__main__":
    main()
