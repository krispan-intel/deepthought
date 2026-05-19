"""
scripts/temporal_validation/anchor_exposure_table.py

Generate per-split × per-anchor exposure table for Paper 2 Finding 2.

For each split × anchor, reports:
  n_future         — total val papers
  mean_sim         — mean sim(val_paper, anchor)
  median_sim       — median sim(val_paper, anchor)
  q80_sim          — Q80 (hybrid floor)
  q90_sim          — Q90 (main hybrid threshold)
  q95_sim          — Q95
  pass_q90         — fraction of val papers passing hybrid-q90 gate
  pass_q90_count   — count
  tva_raw_fill     — TVA raw fill count/rate (from fill_rate.json)
  b1_raw_fill      — B1 baseline raw fill count/rate
  b2_raw_fill      — B2 density-matched fill count/rate
  tva_b2_lift      — TVA/B2 lift

Usage:
    python scripts/temporal_validation/anchor_exposure_table.py --splits t3 t4 t5
    python scripts/temporal_validation/anchor_exposure_table.py --all
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


def compute_split_anchor_exposure(split_name: str):
    import chromadb
    from configs.settings import settings
    from vectordb.embedder import create_embedder

    client = chromadb.PersistentClient(path=str(settings.vectordb_path))
    val_col = client.get_collection(f"tvv_rolling_{split_name}_val")

    FETCH = 5000
    v_ids, v_vecs = [], []
    for offset in range(0, val_col.count(), FETCH):
        b = val_col.get(limit=FETCH, offset=offset, include=["embeddings"])
        v_ids.extend(b["ids"])
        v_vecs.extend(b["embeddings"])
    val_emb = np.array(v_vecs, dtype=np.float32)
    logger.info(f"[{split_name}] Val: {len(v_ids):,} papers")

    embedder = create_embedder()
    anchor_vecs = {
        aid: np.array(embedder.embed_query(atext), dtype=np.float32)
        for aid, atext in ANCHORS.items()
    }

    # Load per-anchor fill stats from fill_rate.json
    fill_path = OUTPUT_DIR / split_name / "fill_rate.json"
    per_anchor_stats = {}
    if fill_path.exists():
        with open(fill_path) as f:
            fr = json.load(f)
        per_anchor_stats = fr.get("per_anchor", {})

    rows = []
    for anchor_id, av in anchor_vecs.items():
        sims = val_emb @ av
        # Fixed thresholds — what fraction of future papers exceed these?
        FIXED_THRESHOLDS = [0.55, 0.60, 0.65]
        pass_fixed = {t: int((sims >= t).sum()) for t in FIXED_THRESHOLDS}

        # Hybrid: max(Q80_val, Q90_train) — mirrors run_rolling_validation logic
        # Load train col for this anchor
        train_col_name = f"tvv_rolling_{split_name}_train"
        try:
            t_col = client.get_collection(train_col_name)
            t_vecs_raw = []
            for offset in range(0, t_col.count(), FETCH):
                b = t_col.get(limit=FETCH, offset=offset, include=["embeddings"])
                t_vecs_raw.extend(b["embeddings"])
            train_sims = np.array(t_vecs_raw, dtype=np.float32) @ av
            q90_train = float(np.quantile(train_sims, 0.90))
            q80_val = float(np.quantile(sims, 0.80))
            tau_hybrid = max(q80_val, q90_train)
        except Exception:
            tau_hybrid = float(np.quantile(sims, 0.90))
        pass_hybrid = int((sims >= tau_hybrid).sum())

        pa = per_anchor_stats.get(anchor_id, {})
        n_total = pa.get("total", 0)
        raw_filled = pa.get("raw", 0)

        row = {
            "split": split_name,
            "anchor_id": anchor_id,
            "n_future": len(v_ids),
            "mean_sim": round(float(sims.mean()), 4),
            "median_sim": round(float(np.median(sims)), 4),
            "q80_val": round(float(np.quantile(sims, 0.80)), 4),
            "q90_train": round(q90_train, 4),
            "tau_hybrid": round(tau_hybrid, 4),
            "pass_055_count": pass_fixed[0.55],
            "pass_055_rate": round(pass_fixed[0.55] / len(v_ids), 4),
            "pass_060_count": pass_fixed[0.60],
            "pass_060_rate": round(pass_fixed[0.60] / len(v_ids), 4),
            "pass_065_count": pass_fixed[0.65],
            "pass_065_rate": round(pass_fixed[0.65] / len(v_ids), 4),
            "pass_hybrid_count": pass_hybrid,
            "pass_hybrid_rate": round(pass_hybrid / len(v_ids), 4),
            "tva_total": n_total,
            "tva_raw_filled": raw_filled,
            "tva_raw_rate": round(raw_filled / n_total, 4) if n_total else None,
        }
        rows.append(row)

    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--splits", nargs="+", choices=list(SPLITS.keys()))
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    splits = list(SPLITS.keys()) if args.all else (args.splits or ["t5"])

    all_rows = []
    for split_name in splits:
        logger.info(f"Computing exposure for {split_name}...")
        rows = compute_split_anchor_exposure(split_name)
        all_rows.extend(rows)

    # Save JSON
    out_path = OUTPUT_DIR / "anchor_exposure_table.json"
    with open(out_path, "w") as f:
        json.dump(all_rows, f, indent=2)
    logger.info(f"Saved → {out_path}")

    # Print table
    print(f"\n{'='*105}")
    print(f"ANCHOR EXPOSURE TABLE")
    print(f"{'Split':<5} {'Anchor':<13} {'n_future':>8} {'mean':>6} {'τ_hyb':>6} "
          f"{'pass≥0.55':>9} {'pass≥0.60':>9} {'pass≥0.65':>9} {'pass_hyb':>9} {'tva_raw':>8}")
    print("-" * 105)
    for r in all_rows:
        print(f"{r['split']:<5} {r['anchor_id']:<13} {r['n_future']:>8,} "
              f"{r['mean_sim']:>6.3f} {r['tau_hybrid']:>6.3f} "
              f"{r['pass_055_rate']:>8.1%} "
              f"{r['pass_060_rate']:>8.1%} "
              f"{r['pass_065_rate']:>8.1%} "
              f"{r['pass_hybrid_rate']:>8.1%} "
              f"{r['tva_raw_filled']:>4}/{r['tva_total']:>3}={r['tva_raw_rate'] or 0:.0%}")
    print(f"{'='*105}")

    print(f"\nMEAN ACROSS ANCHORS PER SPLIT:")
    for split_name in splits:
        rows = [r for r in all_rows if r["split"] == split_name]
        mean_sim = np.mean([r["mean_sim"] for r in rows])
        mean_hyb = np.mean([r["pass_hybrid_rate"] for r in rows])
        mean_065 = np.mean([r["pass_065_rate"] for r in rows])
        print(f"  {split_name}: mean_sim={mean_sim:.3f}  pass≥0.65={mean_065:.1%}  pass_hybrid={mean_hyb:.1%}")


if __name__ == "__main__":
    main()
