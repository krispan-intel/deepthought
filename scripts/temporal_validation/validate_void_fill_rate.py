"""
scripts/temporal_validation/validate_void_fill_rate.py

Phase 3: Check how many TVA voids (t < 2019) were filled in (t >= 2019).

Fill definition:
  A void (A, B, midpoint C) is "filled" if any post-2019 paper's embedding
  is within cosine distance θ of the SLERP midpoint C.

Also computes a random baseline: same fill check on random non-void pairs.

Usage:
    python scripts/temporal_validation/validate_void_fill_rate.py
    python scripts/temporal_validation/validate_void_fill_rate.py --fill-threshold 0.85
"""

import argparse
import json
import random
from pathlib import Path

import numpy as np
from loguru import logger
from tqdm import tqdm

VOIDS_DIR = Path("data/processed/tvv")
VAL_JSONL = Path("data/processed/tvv/arxiv_val.jsonl")
COLLECTION_NAME = "tvv_arxiv_train"
RESULTS_PATH = Path("data/processed/tvv/fill_rate_results.json")

DEFAULT_FILL_THRESHOLD = 0.82  # cosine similarity to midpoint = "filled"
BASELINE_SAMPLES = 60          # same count as TVA voids


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
    logger.info(f"Loaded {len(voids)} voids from {VOIDS_DIR}")
    return voids


def load_val_embeddings():
    """Load post-2019 paper embeddings."""
    from vectordb.embedder import create_embedder
    embedder = create_embedder()

    logger.info("Loading val papers and embedding...")
    val_papers = []
    with open(VAL_JSONL) as f:
        for line in f:
            val_papers.append(json.loads(line))

    logger.info(f"Embedding {len(val_papers):,} val papers...")
    val_embeddings = []
    BATCH = 64
    for i in tqdm(range(0, len(val_papers), BATCH), desc="Embedding val"):
        batch = val_papers[i:i+BATCH]
        texts = [f"{p['title']} {p['abstract']}" for p in batch]
        embs = [embedder.embed_query(t) for t in texts]
        val_embeddings.extend(embs)

    val_matrix = np.array(val_embeddings, dtype=np.float32)
    logger.info(f"Val matrix: {val_matrix.shape}")
    return val_papers, val_matrix


def load_train_embeddings():
    """Load train embeddings from ChromaDB for baseline."""
    import chromadb
    from configs.settings import settings

    client = chromadb.PersistentClient(path=str(settings.vectordb_path))
    col = client.get_collection(COLLECTION_NAME)

    FETCH_BATCH = 5000
    total = col.count()
    ids, embeddings_list = [], []
    for offset in range(0, total, FETCH_BATCH):
        batch = col.get(limit=FETCH_BATCH, offset=offset, include=["embeddings"])
        ids.extend(batch["ids"])
        embeddings_list.extend(batch["embeddings"])

    return ids, np.array(embeddings_list, dtype=np.float32)


def check_fill(midpoint: np.ndarray, val_matrix: np.ndarray, threshold: float) -> tuple[bool, float]:
    """Check if any val paper is within threshold of midpoint."""
    sims = val_matrix @ midpoint
    max_sim = float(sims.max())
    return max_sim >= threshold, max_sim


def run_validation(fill_threshold: float):
    voids = load_voids()
    val_papers, val_matrix = load_val_embeddings()
    train_ids, train_embeddings = load_train_embeddings()

    id_to_vec = {train_ids[i]: train_embeddings[i] for i in range(len(train_ids))}

    # ── TVA void fill check ────────────────────────────────────────────────
    logger.info(f"\n=== TVA Void Fill Rate (threshold={fill_threshold}) ===")
    tva_results = []
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

    tva_filled = sum(1 for r in tva_results if r["filled"])
    tva_fill_rate = tva_filled / len(tva_results) if tva_results else 0

    # ── Random baseline ────────────────────────────────────────────────────
    logger.info(f"\n=== Random Baseline Fill Rate ===")
    random.seed(42)
    all_ids = list(id_to_vec.keys())
    baseline_results = []
    for _ in tqdm(range(BASELINE_SAMPLES), desc="Checking random pairs"):
        id_a, id_b = random.sample(all_ids, 2)
        vec_a = id_to_vec[id_a]
        vec_b = id_to_vec[id_b]
        midpoint = slerp_midpoint(vec_a, vec_b)
        filled, max_sim = check_fill(midpoint, val_matrix, fill_threshold)
        baseline_results.append({"filled": filled, "max_sim": max_sim})

    base_filled = sum(1 for r in baseline_results if r["filled"])
    base_fill_rate = base_filled / len(baseline_results) if baseline_results else 0

    # ── Results ────────────────────────────────────────────────────────────
    print(f"\n{'='*50}")
    print(f"TVA void fill rate:    {tva_filled}/{len(tva_results)} = {tva_fill_rate:.1%}")
    print(f"Random baseline rate:  {base_filled}/{len(baseline_results)} = {base_fill_rate:.1%}")
    if base_fill_rate > 0:
        lift = tva_fill_rate / base_fill_rate
        print(f"Lift (TVA / random):   {lift:.2f}x")
    print(f"{'='*50}\n")

    # Per-anchor breakdown
    from collections import defaultdict
    by_anchor = defaultdict(list)
    for r in tva_results:
        by_anchor[r["anchor_id"]].append(r)

    print("Per-anchor fill rate:")
    for anchor_id, results in sorted(by_anchor.items()):
        n_filled = sum(1 for r in results if r["filled"])
        print(f"  {anchor_id:<15}: {n_filled}/{len(results)} = {n_filled/len(results):.1%}")

    print("\nFilled voids (TVA):")
    for r in tva_results:
        if r["filled"]:
            print(f"  [{r['anchor_id']}] sim={r['max_sim_to_midpoint']:.3f}")
            print(f"    A: {r['paper_a']['title'][:60]}")
            print(f"    B: {r['paper_b']['title'][:60]}")

    # Save results
    output = {
        "fill_threshold": fill_threshold,
        "tva": {
            "total": len(tva_results),
            "filled": tva_filled,
            "fill_rate": tva_fill_rate,
            "results": tva_results,
        },
        "baseline": {
            "total": len(baseline_results),
            "filled": base_filled,
            "fill_rate": base_fill_rate,
        },
        "lift": tva_fill_rate / base_fill_rate if base_fill_rate > 0 else None,
    }
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_PATH, "w") as f:
        json.dump(output, f, indent=2)
    logger.info(f"Results saved → {RESULTS_PATH}")


def main():
    parser = argparse.ArgumentParser(description="TVV Phase 3: validate void fill rate")
    parser.add_argument("--fill-threshold", type=float, default=DEFAULT_FILL_THRESHOLD,
                        help=f"Cosine similarity threshold for 'filled' (default: {DEFAULT_FILL_THRESHOLD})")
    args = parser.parse_args()
    run_validation(args.fill_threshold)


if __name__ == "__main__":
    main()
