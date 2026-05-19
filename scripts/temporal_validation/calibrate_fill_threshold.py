"""
scripts/temporal_validation/calibrate_fill_threshold.py

Calibrate the geometric fill threshold τ_fill from density-matched null midpoints.

Instead of a global constant (0.82), τ_fill is defined as:

    τ_fill(q, ρ, t) = Q_{1-α}({ max_{P ∈ Val_q} sim(P, m_0) : m_0 ∈ Null(q, ρ, t) })

where:
    Val_q   = anchor-eligible val papers (sim(P, anchor_q) ≥ τ_anchor)
    Null    = density-matched B2-style null midpoints for anchor q
    ρ       = local density bucket of the void
    α       = target geometric false occupancy rate (default 0.05)

This gives a calibrated threshold per (anchor, density_bucket, split)
instead of a magic number.

Also reports:
- For each split: where does 0.82 sit in the null distribution?
- Empirical FPR at 0.82 vs at calibrated threshold
- How τ_fill varies by anchor and density

Usage:
    python scripts/temporal_validation/calibrate_fill_threshold.py --split t5
    python scripts/temporal_validation/calibrate_fill_threshold.py --all --alpha 0.05
"""

import argparse
import json
import random
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

TAU_ANCHOR = 0.55
TAU_MIN_QUANTILE = 0.80
C1_POOL = 300
NULL_SAMPLES = 200   # null midpoints per (anchor, density_bucket)
DENSITY_K = 20
DENSITY_BUCKETS = 3  # low / mid / high density


def slerp(a, b):
    c = a + b
    n = np.linalg.norm(c)
    return c / n if n > 0 else c


def local_density(vec, train_emb, k=DENSITY_K):
    sims = train_emb @ vec
    return float(np.sort(sims)[::-1][:k].mean())


def run_split(split_name: str, alpha: float):
    import chromadb
    from configs.settings import settings
    from vectordb.embedder import create_embedder

    client = chromadb.PersistentClient(path=str(settings.vectordb_path))
    train_col = client.get_collection(f"tvv_rolling_{split_name}_train")
    val_col = client.get_collection(f"tvv_rolling_{split_name}_val")

    FETCH = 5000
    t_ids, t_vecs = [], []
    for offset in range(0, train_col.count(), FETCH):
        b = train_col.get(limit=FETCH, offset=offset, include=["embeddings"])
        t_ids.extend(b["ids"])
        t_vecs.extend(b["embeddings"])
    train_emb = np.array(t_vecs, dtype=np.float32)

    v_ids, v_vecs = [], []
    for offset in range(0, val_col.count(), FETCH):
        b = val_col.get(limit=FETCH, offset=offset, include=["embeddings"])
        v_ids.extend(b["ids"])
        v_vecs.extend(b["embeddings"])
    val_emb = np.array(v_vecs, dtype=np.float32)
    logger.info(f"[{split_name}] Train={len(t_ids):,}  Val={len(v_ids):,}")

    embedder = create_embedder()
    anchor_vecs = {
        aid: np.array(embedder.embed_query(atext), dtype=np.float32)
        for aid, atext in ANCHORS.items()
    }

    # Corpus-adaptive anchor threshold (same as run_rolling_validation)
    anchor_thresholds = {}
    for aid, av in anchor_vecs.items():
        train_sims = train_emb @ av
        val_sims = val_emb @ av
        tau_min = float(np.quantile(val_sims, TAU_MIN_QUANTILE))
        tau_q90 = float(np.quantile(train_sims, 0.90))
        anchor_thresholds[aid] = max(tau_min, tau_q90)

    rng = random.Random(42)
    results = {}

    for anchor_id, av in anchor_vecs.items():
        tau_q = anchor_thresholds[anchor_id]

        # Val_q: anchor-eligible val papers
        val_anchor_sims = val_emb @ av
        eligible_mask = val_anchor_sims >= tau_q
        eligible_idx = np.where(eligible_mask)[0]
        if len(eligible_idx) == 0:
            logger.warning(f"[{split_name}] {anchor_id}: no eligible val papers")
            continue
        eligible_val = val_emb[eligible_idx]  # (n_elig, d)
        logger.info(f"[{split_name}] {anchor_id}: {len(eligible_idx)} eligible val papers (τ={tau_q:.3f})")

        # C1 pool for null midpoint generation
        train_anchor_sims = train_emb @ av
        c1_idx = train_anchor_sims.argsort()[::-1][:C1_POOL].tolist()

        # Compute local density of each C1 paper (for bucketing)
        c1_densities = [local_density(train_emb[i], train_emb) for i in c1_idx]
        d_low  = np.percentile(c1_densities, 33)
        d_high = np.percentile(c1_densities, 67)

        def density_bucket(d):
            if d < d_low:   return "low"
            if d < d_high:  return "mid"
            return "high"

        # For each density bucket: generate NULL_SAMPLES null midpoints split 80/20.
        # Calibrate τ on first 80%, verify held-out FPR on remaining 20%.
        # Expected held-out FPR ≈ α if calibration is valid.
        rng_heldout = random.Random(77)
        bucket_results = {}
        for bucket in ["low", "mid", "high"]:
            bucket_idx = [i for i, d in zip(c1_idx, c1_densities)
                          if density_bucket(d) == bucket]
            if len(bucket_idx) < 2:
                continue

            all_null = []
            for _ in range(NULL_SAMPLES):
                i, j = rng.sample(bucket_idx, 2)
                m = slerp(train_emb[i], train_emb[j])
                sims_to_m = eligible_val @ m
                all_null.append(float(sims_to_m.max()))

            # 80/20 split: calibrate on first 80%, evaluate on held-out 20%
            n_cal = int(len(all_null) * 0.80)
            cal_sims = np.array(all_null[:n_cal])
            heldout_sims = np.array(all_null[n_cal:])

            null_max_sims = np.array(all_null)
            tau_calibrated = float(np.quantile(cal_sims, 1 - alpha))
            fpr_at_082 = float((null_max_sims >= 0.82).mean())
            heldout_fpr = float((heldout_sims >= tau_calibrated).mean()) if len(heldout_sims) > 0 else None

            bucket_results[bucket] = {
                "n_null": len(null_max_sims),
                "n_cal": n_cal,
                "n_heldout": len(heldout_sims),
                "null_mean": round(float(null_max_sims.mean()), 4),
                "null_p50": round(float(np.percentile(null_max_sims, 50)), 4),
                "null_p90": round(float(np.percentile(null_max_sims, 90)), 4),
                "null_p95": round(float(np.percentile(null_max_sims, 95)), 4),
                "heldout_fpr": round(heldout_fpr, 4) if heldout_fpr is not None else None,
                "null_p99": round(float(np.percentile(null_max_sims, 99)), 4),
                "tau_calibrated": round(tau_calibrated, 4),
                "fpr_at_0.82": round(fpr_at_082, 4),
                "alpha": alpha,
            }

        results[anchor_id] = {
            "tau_anchor": round(tau_q, 4),
            "n_eligible_val": int(len(eligible_idx)),
            "density_buckets": bucket_results,
        }

    # Save
    out_path = OUTPUT_DIR / split_name / "fill_threshold_calibration.json"
    with open(out_path, "w") as f:
        json.dump({"split": split_name, "alpha": alpha, "results": results}, f, indent=2)
    logger.info(f"Saved → {out_path}")

    # Print table
    print(f"\n{'='*105}")
    print(f"[{split_name}] FILL THRESHOLD CALIBRATION  (α={alpha}, target FPR={alpha:.0%})")
    print(f"{'Anchor':<13} {'Bucket':<6} {'null_p50':>9} {'τ_calib':>9} {'FPR@0.82':>10} {'HeldoutFPR':>12} {'ΔExpected':>10}")
    print("-" * 90)
    for anchor_id, ar in results.items():
        for bucket, br in ar["density_buckets"].items():
            print(f"{anchor_id:<13} {bucket:<6} "
                  f"{br['null_p50']:>9.4f} "
                  f"{br['tau_calibrated']:>9.4f} "
                  f"{br['fpr_at_0.82']:>9.1%} "
                  f"{br.get('heldout_fpr', 0) or 0:>11.1%} "
                  f"{(br.get('heldout_fpr',0) or 0) - alpha:>+9.3f}")

    # Summary
    all_taus = [br["tau_calibrated"]
                for ar in results.values()
                for br in ar["density_buckets"].values()]
    all_fprs = [br["fpr_at_0.82"]
                for ar in results.values()
                for br in ar["density_buckets"].values()]
    all_hfprs = [br["heldout_fpr"] for ar in results.values()
                 for br in ar["density_buckets"].values()
                 if br.get("heldout_fpr") is not None]
    print(f"\n  Global τ_calibrated: mean={np.mean(all_taus):.4f}  "
          f"min={np.min(all_taus):.4f}  max={np.max(all_taus):.4f}")
    print(f"  FPR at 0.82:         mean={np.mean(all_fprs):.1%}")
    if all_hfprs:
        print(f"  Held-out FPR at τ:   mean={np.mean(all_hfprs):.1%}  "
              f"(target={alpha:.0%}, Δ={np.mean(all_hfprs)-alpha:+.3f})")

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=list(SPLITS.keys()), default="t5")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--alpha", type=float, default=0.05,
                        help="Target geometric false occupancy rate (default 0.05)")
    args = parser.parse_args()

    splits = list(SPLITS.keys()) if args.all else [args.split]
    for s in splits:
        run_split(s, args.alpha)


if __name__ == "__main__":
    main()
