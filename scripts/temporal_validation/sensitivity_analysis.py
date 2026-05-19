"""
scripts/temporal_validation/sensitivity_analysis.py

Paper 2 sensitivity analysis:
  1. Table 1b — fill rates under calibrated τ_fill(q,ρ,t)
  2. Bootstrap CI for TVA/B2 lift under τ=0.82 and calibrated τ

Usage:
    python scripts/temporal_validation/sensitivity_analysis.py --splits t5
    python scripts/temporal_validation/sensitivity_analysis.py --splits t3 t4 t5
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

LEGACY_TAU = 0.82
TAU_ANCHOR = 0.55
C1_POOL = 300
BASELINE_PER_ANCHOR = 20
DENSITY_K = 20
N_BOOTSTRAP = 1000
BOOTSTRAP_SEED = 42


def slerp(a, b):
    c = a + b; n = np.linalg.norm(c)
    return c / n if n > 0 else c


def local_density(vec, train_emb, k=DENSITY_K):
    sims = train_emb @ vec
    return float(np.sort(sims)[::-1][:k].mean())


def load_calibration(split_name: str) -> dict:
    """Load pre-computed τ_fill per (anchor, density_bucket) from calibration file."""
    cal_path = OUTPUT_DIR / split_name / "fill_threshold_calibration.json"
    if not cal_path.exists():
        raise FileNotFoundError(f"Run calibrate_fill_threshold.py first: {cal_path}")
    with open(cal_path) as f:
        cal = json.load(f)
    # Build lookup: anchor_id → {bucket → tau_calibrated}
    lookup = {}
    for anchor_id, ar in cal["results"].items():
        lookup[anchor_id] = {
            bucket: br["tau_calibrated"]
            for bucket, br in ar["density_buckets"].items()
        }
    return lookup


def get_density_bucket(density: float, buckets: dict) -> str:
    """Map local density to bucket key matching calibration (low/mid/high)."""
    vals = sorted(buckets.keys())
    # Use the bucket thresholds embedded in the calibration file indirectly
    # We re-use the simple tertile scheme: lowest third=low, middle=mid, top=high
    # (same scheme as calibrate_fill_threshold.py)
    # Without knowing corpus tertiles here, default to 'mid' as safe fallback
    return "mid"  # overridden in run_split with proper bucket assignment


def bootstrap_lift(filled_a: list[int], filled_b: list[int], n_boot: int, seed: int):
    """
    Bootstrap CI for lift = (mean_a / mean_b).
    filled_a, filled_b: per-void binary fill indicator (0/1).
    Returns (lift, ci_low, ci_high).
    """
    rng = np.random.default_rng(seed)
    n_a, n_b = len(filled_a), len(filled_b)
    arr_a = np.array(filled_a, dtype=float)
    arr_b = np.array(filled_b, dtype=float)
    observed_lift = arr_a.mean() / arr_b.mean() if arr_b.mean() > 0 else np.nan
    boot_lifts = []
    for _ in range(n_boot):
        ba = arr_a[rng.integers(0, n_a, size=n_a)]
        bb = arr_b[rng.integers(0, n_b, size=n_b)]
        if bb.mean() > 0:
            boot_lifts.append(ba.mean() / bb.mean())
    boot_lifts = np.array(boot_lifts)
    ci_low = float(np.percentile(boot_lifts, 2.5))
    ci_high = float(np.percentile(boot_lifts, 97.5))
    return float(observed_lift), ci_low, ci_high


def run_split(split_name: str, n_bootstrap: int):
    import chromadb
    from configs.settings import settings
    from vectordb.embedder import create_embedder

    # Load calibration
    cal_lookup = load_calibration(split_name)

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

    # Per-anchor calibrated τ_q (same as run_rolling_validation)
    anchor_tau_q = {}
    for aid, av in anchor_vecs.items():
        train_sims = train_emb @ av
        val_sims = val_emb @ av
        tau_min = float(np.quantile(val_sims, 0.80))
        tau_q90 = float(np.quantile(train_sims, 0.90))
        anchor_tau_q[aid] = max(tau_min, tau_q90)

    # Per-anchor C1 density tertile thresholds (reproduce calibrate_fill_threshold scheme)
    anchor_density_thresholds = {}
    for aid, av in anchor_vecs.items():
        c1_sims = train_emb @ av
        c1_idx = c1_sims.argsort()[::-1][:C1_POOL].tolist()
        c1_dens = [local_density(train_emb[i], train_emb) for i in c1_idx]
        anchor_density_thresholds[aid] = (
            float(np.percentile(c1_dens, 33)),
            float(np.percentile(c1_dens, 67)),
        )

    def get_bucket(aid, density):
        lo, hi = anchor_density_thresholds[aid]
        if density < lo: return "low"
        if density < hi: return "mid"
        return "high"

    def get_calib_tau(aid, density):
        bucket = get_bucket(aid, density)
        return cal_lookup.get(aid, {}).get(bucket, 0.841)  # fallback to global mean

    # Load TVA voids
    voids_path = OUTPUT_DIR / split_name / "voids.jsonl"
    voids = [json.loads(l) for l in open(voids_path)]

    id_to_vec = {t_ids[i]: train_emb[i] for i in range(len(t_ids))}

    # --- TVA fill indicators ---
    tva_legacy = []   # 1 if max_val_sim >= 0.82
    tva_calib  = []   # 1 if max_val_sim >= τ_fill(q,ρ,t)

    for v in voids:
        va = id_to_vec.get(v["paper_a"]["id"])
        vb = id_to_vec.get(v["paper_b"]["id"])
        if va is None or vb is None:
            continue
        mp = slerp(va, vb)
        aid = v["anchor_id"]
        av = anchor_vecs[aid]
        tau_q = anchor_tau_q[aid]

        # Val_q: anchor-eligible val papers
        val_anchor_sims = val_emb @ av
        eligible_mask = val_anchor_sims >= tau_q
        if not eligible_mask.any():
            tva_legacy.append(0)
            tva_calib.append(0)
            continue

        eligible_val = val_emb[eligible_mask]
        max_sim = float((eligible_val @ mp).max())

        mid_density = local_density(mp, train_emb)
        tau_c = get_calib_tau(aid, mid_density)

        tva_legacy.append(1 if max_sim >= LEGACY_TAU else 0)
        tva_calib.append(1 if max_sim >= tau_c else 0)

    # --- B2 density-matched fill indicators ---
    rng_b2 = random.Random(99)
    b2_legacy = []
    b2_calib  = []

    valid_void_data = []  # (aid, mp, density) for B2 matching
    for v in voids:
        va = id_to_vec.get(v["paper_a"]["id"])
        vb = id_to_vec.get(v["paper_b"]["id"])
        if va is None or vb is None:
            continue
        mp = slerp(va, vb)
        valid_void_data.append((v["anchor_id"], mp, local_density(mp, train_emb)))

    anchor_c1_idx = {}
    for aid, av in anchor_vecs.items():
        sims = train_emb @ av
        anchor_c1_idx[aid] = sims.argsort()[::-1][:C1_POOL].tolist()

    for (aid, tva_mp, tva_dens) in valid_void_data:
        c1_idx = anchor_c1_idx[aid]
        pairs = [rng_b2.sample(c1_idx, 2) for _ in range(300)]
        best_diff = float("inf")
        best_mp = None
        for i, j in pairs:
            mp_b2 = slerp(train_emb[i], train_emb[j])
            d = local_density(mp_b2, train_emb)
            if abs(d - tva_dens) < best_diff:
                best_diff = abs(d - tva_dens)
                best_mp = (mp_b2, d)

        if best_mp is None:
            continue
        mp, mid_d = best_mp
        av = anchor_vecs[aid]
        tau_q = anchor_tau_q[aid]
        val_anchor_sims = val_emb @ av
        eligible_mask = val_anchor_sims >= tau_q
        if not eligible_mask.any():
            b2_legacy.append(0)
            b2_calib.append(0)
            continue

        eligible_val = val_emb[eligible_mask]
        max_sim = float((eligible_val @ mp).max())
        tau_c = get_calib_tau(aid, mid_d)

        b2_legacy.append(1 if max_sim >= LEGACY_TAU else 0)
        b2_calib.append(1 if max_sim >= tau_c else 0)

    # Results
    tva_rate_legacy = np.mean(tva_legacy)
    tva_rate_calib  = np.mean(tva_calib)
    b2_rate_legacy  = np.mean(b2_legacy)
    b2_rate_calib   = np.mean(b2_calib)

    lift_legacy, ci_l_lo, ci_l_hi = bootstrap_lift(tva_legacy, b2_legacy, n_bootstrap, BOOTSTRAP_SEED)
    lift_calib,  ci_c_lo, ci_c_hi = bootstrap_lift(tva_calib,  b2_calib,  n_bootstrap, BOOTSTRAP_SEED + 1)

    result = {
        "split": split_name,
        "n_tva": len(tva_legacy),
        "n_b2": len(b2_legacy),
        "legacy_tau": LEGACY_TAU,
        "tva_legacy": {"rate": round(float(tva_rate_legacy), 4), "n_filled": int(sum(tva_legacy))},
        "b2_legacy":  {"rate": round(float(b2_rate_legacy),  4), "n_filled": int(sum(b2_legacy))},
        "tva_calib":  {"rate": round(float(tva_rate_calib),  4), "n_filled": int(sum(tva_calib))},
        "b2_calib":   {"rate": round(float(b2_rate_calib),   4), "n_filled": int(sum(b2_calib))},
        "lift_legacy_tva_b2": {
            "lift": round(lift_legacy, 4),
            "ci_95": [round(ci_l_lo, 4), round(ci_l_hi, 4)],
        },
        "lift_calib_tva_b2": {
            "lift": round(lift_calib, 4),
            "ci_95": [round(ci_c_lo, 4), round(ci_c_hi, 4)],
        },
    }

    out_path = OUTPUT_DIR / split_name / "sensitivity_analysis.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    logger.info(f"Saved → {out_path}")

    print(f"\n[{split_name}] SENSITIVITY ANALYSIS")
    print(f"{'':20} {'τ=0.82 (legacy)':>18} {'calibrated τ':>18}")
    print("-" * 60)
    print(f"{'TVA fill rate':20} {tva_rate_legacy:>17.1%} {tva_rate_calib:>17.1%}")
    print(f"{'B2 fill rate':20} {b2_rate_legacy:>17.1%} {b2_rate_calib:>17.1%}")
    print(f"{'TVA/B2 lift':20} {lift_legacy:>17.2f}x {lift_calib:>17.2f}x")
    print(f"{'95% CI':20} [{ci_l_lo:.2f}, {ci_l_hi:.2f}]x     [{ci_c_lo:.2f}, {ci_c_hi:.2f}]x")
    print()

    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--splits", nargs="+", choices=list(SPLITS.keys()), default=["t5"])
    parser.add_argument("--n-bootstrap", type=int, default=1000)
    args = parser.parse_args()

    all_results = []
    for s in args.splits:
        r = run_split(s, args.n_bootstrap)
        all_results.append(r)

    print(f"\n{'='*75}")
    print(f"{'Split':<6} {'TVA@0.82':>9} {'B2@0.82':>8} {'L(0.82)':>9} {'CI':>16}  "
          f"{'TVA@cal':>8} {'B2@cal':>7} {'L(cal)':>8} {'CI':>16}")
    print("-" * 105)
    for r in all_results:
        print(f"{r['split']:<6} "
              f"{r['tva_legacy']['rate']:>8.1%} {r['b2_legacy']['rate']:>7.1%} "
              f"{r['lift_legacy_tva_b2']['lift']:>8.2f}x "
              f"[{r['lift_legacy_tva_b2']['ci_95'][0]:.2f},{r['lift_legacy_tva_b2']['ci_95'][1]:.2f}]  "
              f"{r['tva_calib']['rate']:>7.1%} {r['b2_calib']['rate']:>6.1%} "
              f"{r['lift_calib_tva_b2']['lift']:>7.2f}x "
              f"[{r['lift_calib_tva_b2']['ci_95'][0]:.2f},{r['lift_calib_tva_b2']['ci_95'][1]:.2f}]")
    print(f"{'='*75}")


if __name__ == "__main__":
    main()
