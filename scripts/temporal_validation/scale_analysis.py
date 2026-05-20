"""
scripts/temporal_validation/scale_analysis.py

Runtime and scale table for Paper 2 Discussion.

Reports per-anchor:
- C1 pool size
- pairs enumerated (C1 choose 2)
- pairs after C2 (marginality filter)
- pairs after C3 (sparse bridge filter)
- pairs after C4 (vacancy filter)
- final top-K voids
- wall-clock runtime

Usage:
    python scripts/temporal_validation/scale_analysis.py --split t5
"""

import argparse
import json
import re
import time
from pathlib import Path

import numpy as np
from loguru import logger

OUTPUT_DIR = Path("data/processed/tvv/rolling")

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

C1_POOL = 300
TAU_DOMAIN = 0.50     # C1 lower bound (domain cohesion)
TAU_HIGH = 0.85       # C2 upper bound (too similar = not marginal)
TAU_LOW = 0.30        # C2 lower bound (too dissimilar = noise)
TOP_K = 30

STOP = {"the","a","an","of","in","on","for","and","or","with","to","from",
        "is","are","be","by","at","as","we","our","this","that","which",
        "using","based","via","new","paper","work","method","approach",
        "system","model","algorithm","results","show","propose","present"}


def tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z][a-z0-9\-]{2,}", text.lower())
    return {w for w in words if w not in STOP}


def run_split(split_name: str):
    import chromadb
    from configs.settings import settings
    from vectordb.embedder import create_embedder

    t0_total = time.time()

    client = chromadb.PersistentClient(path=str(settings.vectordb_path))
    train_col = client.get_collection(f"tvv_rolling_{split_name}_train")
    embedder = create_embedder()

    FETCH = 5000
    t_ids, t_vecs, t_metas = [], [], []
    for offset in range(0, train_col.count(), FETCH):
        b = train_col.get(limit=FETCH, offset=offset, include=["embeddings", "metadatas"])
        t_ids.extend(b["ids"])
        t_vecs.extend(b["embeddings"])
        t_metas.extend(b["metadatas"])
    train_emb = np.array(t_vecs, dtype=np.float32)
    logger.info(f"[{split_name}] Train: {len(t_ids):,} papers")

    # Load abstracts for C3 token bridge
    train_path = OUTPUT_DIR / split_name / "train.jsonl"
    id_to_abstract = {}
    if train_path.exists():
        with open(train_path) as f:
            for line in f:
                p = json.loads(line)
                id_to_abstract[p["id"]] = p.get("abstract", "")

    anchor_rows = []

    for anchor_id, anchor_text in ANCHORS.items():
        t0 = time.time()
        av = np.array(embedder.embed_query(anchor_text), dtype=np.float32)
        sims = train_emb @ av

        # C1: domain cohesion (top 300 by cosine to anchor)
        c1_idx = sims.argsort()[::-1][:C1_POOL].tolist()
        n_c1 = len(c1_idx)
        n_pairs = n_c1 * (n_c1 - 1) // 2

        # Enumerate pairs and apply C2, C3, C4
        n_after_c2 = 0
        n_after_c3 = 0
        n_after_c4 = 0
        c4_voids = []  # (sim_ab, i, j) for top-K

        # Build sparse tokens
        sparse = {t_ids[i]: tokens(id_to_abstract.get(t_ids[i], "")) for i in c1_idx}
        c1_vecs = train_emb[c1_idx]
        c1_sims_matrix = c1_vecs @ c1_vecs.T  # (C1, C1)

        for ii, i in enumerate(c1_idx):
            for jj, j in enumerate(c1_idx):
                if jj <= ii:
                    continue
                sim_ab = float(c1_sims_matrix[ii, jj])

                # C2: calibrated marginality (not too similar, not too dissimilar)
                if sim_ab >= TAU_HIGH or sim_ab <= TAU_LOW:
                    continue
                n_after_c2 += 1

                # C3: sparse lexical bridge (shared tokens from both sides)
                tok_a = sparse.get(t_ids[i], set())
                tok_b = sparse.get(t_ids[j], set())
                bridge = tok_a & tok_b
                if not bridge:
                    continue
                n_after_c3 += 1

                # C4: midpoint vacancy (checked via void search — approximate here
                # by checking if no single train paper is too close to midpoint)
                va = train_emb[i]; vb = train_emb[j]
                mp = va + vb; mp /= np.linalg.norm(mp)
                mid_sims = train_emb @ mp
                # C4: top-1 nearest neighbor similarity to midpoint
                max_neighbor_sim = float(mid_sims.max())
                if max_neighbor_sim > 0.95:  # already occupied
                    continue
                n_after_c4 += 1
                c4_voids.append((sim_ab, i, j))

        runtime = time.time() - t0

        # MMR-style top-K (approximate: sort by mid-range sim_ab)
        c4_voids.sort(key=lambda x: abs(x[0] - 0.55))
        n_topk = min(TOP_K, len(c4_voids))

        row = {
            "anchor": anchor_id,
            "n_c1_pool": n_c1,
            "n_pairs_enumerated": n_pairs,
            "n_after_c2": n_after_c2,
            "n_after_c3": n_after_c3,
            "n_after_c4": n_after_c4,
            "n_top_k": n_topk,
            "pct_c2": round(n_after_c2 / n_pairs * 100, 1) if n_pairs else 0,
            "pct_c3": round(n_after_c3 / n_after_c2 * 100, 1) if n_after_c2 else 0,
            "pct_c4": round(n_after_c4 / n_after_c3 * 100, 1) if n_after_c3 else 0,
            "runtime_sec": round(runtime, 1),
        }
        anchor_rows.append(row)
        logger.info(f"  {anchor_id}: pairs={n_pairs:,} → C2={n_after_c2} → C3={n_after_c3} → C4={n_after_c4} → top-{n_topk}  ({runtime:.1f}s)")

    total_time = time.time() - t0_total

    # Print summary table
    print(f"\n[{split_name}] SCALE ANALYSIS — TVA Filter Pipeline")
    print(f"{'Anchor':<13} {'C1 pairs':>9} {'→C2':>7} {'→C3':>7} {'→C4':>7} {'top-K':>7} {'sec':>5}")
    print("-" * 65)
    total_pairs = 0
    for r in anchor_rows:
        print(f"{r['anchor']:<13} {r['n_pairs_enumerated']:>9,} "
              f"{r['n_after_c2']:>7} {r['n_after_c3']:>7} {r['n_after_c4']:>7} "
              f"{r['n_top_k']:>7} {r['runtime_sec']:>5.1f}")
        total_pairs += r["n_pairs_enumerated"]
    print("-" * 65)
    total_k = sum(r["n_top_k"] for r in anchor_rows)
    total_rt = sum(r["runtime_sec"] for r in anchor_rows)
    print(f"{'TOTAL':<13} {total_pairs:>9,} {'':>7} {'':>7} {'':>7} {total_k:>7} {total_rt:>5.1f}")
    print(f"\n  Total wall-clock (incl. embed): {total_time:.1f}s = {total_time/60:.1f}min")
    print(f"  Search space reduction: {total_pairs:,} pairs → {total_k} top-K hypotheses")
    print(f"  Reduction factor: {total_pairs/total_k:.0f}×")

    result = {
        "split": split_name,
        "n_train": len(t_ids),
        "anchor_rows": anchor_rows,
        "totals": {
            "pairs_enumerated": total_pairs,
            "top_k": total_k,
            "reduction_factor": round(total_pairs / total_k, 0),
            "total_runtime_sec": round(total_rt, 1),
            "wall_clock_sec": round(total_time, 1),
        }
    }
    out_path = OUTPUT_DIR / split_name / "scale_analysis.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    logger.info(f"Saved → {out_path}")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", default="t5")
    args = parser.parse_args()
    run_split(args.split)


if __name__ == "__main__":
    main()
