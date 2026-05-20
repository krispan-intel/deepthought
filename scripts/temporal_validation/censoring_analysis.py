"""
scripts/temporal_validation/censoring_analysis.py

Censoring-aware fill analysis for Paper 2.

1. Exposure-conditioned fill: bucket anchors by Val_q size (low/mid/high),
   show fill rate rises with exposure → unfilled voids are observability-limited.

2. Time-to-first-geometric-fill (Kaplan-Meier style):
   For each void, find the YEAR of the first anchor-eligible paper with sim > legacy tau.
   Voids with no fill are right-censored at end of validation window.
   Compare TVA vs B2 KM curves.

Usage:
    python scripts/temporal_validation/censoring_analysis.py --split t5
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from loguru import logger

OUTPUT_DIR = Path("data/processed/tvv/rolling")
LEGACY_TAU = 0.82

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


def slerp(a, b):
    c = a + b; n = np.linalg.norm(c)
    return c / n if n > 0 else c


def run_split(split_name: str):
    import chromadb
    from configs.settings import settings
    from vectordb.embedder import create_embedder

    client = chromadb.PersistentClient(path=str(settings.vectordb_path))
    train_col = client.get_collection(f"tvv_rolling_{split_name}_train")
    val_col   = client.get_collection(f"tvv_rolling_{split_name}_val")

    FETCH = 5000
    t_ids, t_vecs = [], []
    for offset in range(0, train_col.count(), FETCH):
        b = train_col.get(limit=FETCH, offset=offset, include=["embeddings"])
        t_ids.extend(b["ids"]); t_vecs.extend(b["embeddings"])
    train_emb = np.array(t_vecs, dtype=np.float32)

    v_ids, v_vecs, v_metas = [], [], []
    for offset in range(0, val_col.count(), FETCH):
        b = val_col.get(limit=FETCH, offset=offset, include=["embeddings","metadatas"])
        v_ids.extend(b["ids"]); v_vecs.extend(b["embeddings"]); v_metas.extend(b["metadatas"])
    val_emb = np.array(v_vecs, dtype=np.float32)
    val_years = {v_ids[i]: (v_metas[i] or {}).get("year", 9999) for i in range(len(v_ids))}
    logger.info(f"[{split_name}] Train={len(t_ids):,}  Val={len(v_ids):,}")

    embedder = create_embedder()
    anchor_vecs = {
        aid: np.array(embedder.embed_query(atext), dtype=np.float32)
        for aid, atext in ANCHORS.items()
    }

    # Per-anchor τ_q
    anchor_tau_q = {}
    for aid, av in anchor_vecs.items():
        train_sims = train_emb @ av
        val_sims   = val_emb @ av
        tau_min = float(np.quantile(val_sims, 0.80))
        tau_q90 = float(np.quantile(train_sims, 0.90))
        anchor_tau_q[aid] = max(tau_min, tau_q90)

    # Compute Val_q sizes for each anchor
    val_q_sizes = {}
    for aid, av in anchor_vecs.items():
        tau_q = anchor_tau_q[aid]
        val_anchor_sims = val_emb @ av
        val_q_sizes[aid] = int((val_anchor_sims >= tau_q).sum())

    # Load TVA voids
    voids_path = OUTPUT_DIR / split_name / "voids.jsonl"
    voids = [json.loads(l) for l in open(voids_path)]
    id_to_vec = {t_ids[i]: train_emb[i] for i in range(len(t_ids))}

    # --- Exposure-conditioned fill analysis ---
    # Bucket anchors by Val_q size
    anchor_sizes = list(val_q_sizes.values())
    p33 = np.percentile(anchor_sizes, 33)
    p67 = np.percentile(anchor_sizes, 67)

    def exposure_bucket(size):
        if size < p33: return "low"
        if size < p67: return "mid"
        return "high"

    anchor_bucket = {aid: exposure_bucket(val_q_sizes[aid]) for aid in ANCHORS}

    # Per-void fill + time-to-fill
    void_records = []
    for v in voids:
        va = id_to_vec.get(v["paper_a"]["id"])
        vb = id_to_vec.get(v["paper_b"]["id"])
        if va is None or vb is None:
            continue
        mp = slerp(va, vb)
        aid = v["anchor_id"]
        av = anchor_vecs[aid]
        tau_q = anchor_tau_q[aid]

        val_anchor_sims = val_emb @ av
        eligible_mask = val_anchor_sims >= tau_q
        eligible_idx = np.where(eligible_mask)[0]

        if len(eligible_idx) == 0:
            # No eligible papers — censored at start
            void_records.append({
                "void_id": v["void_id"], "anchor_id": aid,
                "exposure_bucket": anchor_bucket[aid],
                "val_q_size": val_q_sizes[aid],
                "filled_legacy": False, "fill_year": None, "censored": True,
            })
            continue

        eligible_val = val_emb[eligible_idx]
        sims = eligible_val @ mp
        filled = bool((sims >= LEGACY_TAU).any())

        fill_year = None
        if filled:
            best_idx = eligible_idx[int(sims.argmax())]
            fill_year = val_years.get(v_ids[best_idx])

        void_records.append({
            "void_id": v["void_id"], "anchor_id": aid,
            "exposure_bucket": anchor_bucket[aid],
            "val_q_size": val_q_sizes[aid],
            "filled_legacy": filled, "fill_year": fill_year,
            "censored": not filled,
            "max_sim": round(float(sims.max()), 4),
        })

    # --- Table: exposure-conditioned fill ---
    by_bucket = defaultdict(list)
    for r in void_records:
        by_bucket[r["exposure_bucket"]].append(r)

    print(f"\n[{split_name}] EXPOSURE-CONDITIONED FILL RATE (legacy τ=0.82)")
    print(f"{'Bucket':<8} {'n_anchors':>10} {'mean_Valq':>10} {'n_voids':>8} {'fill%':>7} {'censored%':>10}")
    print("-" * 60)
    bucket_rows = []
    for bucket in ["low", "mid", "high"]:
        recs = by_bucket.get(bucket, [])
        n_anchors = len({r["anchor_id"] for r in recs})
        mean_vq = np.mean([r["val_q_size"] for r in recs]) if recs else 0
        n_voids = len(recs)
        fill_rate = np.mean([r["filled_legacy"] for r in recs]) if recs else 0
        cens_rate = np.mean([r["censored"] for r in recs]) if recs else 0
        print(f"{bucket:<8} {n_anchors:>10} {mean_vq:>10.0f} {n_voids:>8} {fill_rate:>7.1%} {cens_rate:>10.1%}")
        bucket_rows.append({
            "bucket": bucket, "n_anchors": n_anchors,
            "mean_val_q": round(mean_vq, 1), "n_voids": n_voids,
            "fill_rate": round(fill_rate, 4), "censored_rate": round(cens_rate, 4),
        })
    print()

    # --- Simple time-to-fill summary ---
    filled_records = [r for r in void_records if r["filled_legacy"] and r["fill_year"]]
    if filled_records:
        years = sorted(set(r["fill_year"] for r in filled_records if r["fill_year"]))
        print(f"  Fill year distribution: {dict({y: sum(1 for r in filled_records if r['fill_year']==y) for y in years})}")

    result = {
        "split": split_name,
        "n_voids": len(void_records),
        "val_q_sizes": {aid: int(s) for aid, s in val_q_sizes.items()},
        "anchor_buckets": anchor_bucket,
        "exposure_table": bucket_rows,
        "void_records_sample": void_records[:20],  # sample only
    }
    out_path = OUTPUT_DIR / split_name / "censoring_analysis.json"
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
