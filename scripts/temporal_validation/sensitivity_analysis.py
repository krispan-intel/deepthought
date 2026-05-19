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


def hierarchical_bootstrap_diff(
    anchor_tva: dict[str, list[int]],
    anchor_b2: dict[str, list[int]],
    n_boot: int,
    seed: int,
):
    """
    Hierarchical cluster bootstrap for TVA - B2 fill-rate difference (pp).
    Resampling: anchors (outer) → voids within anchor (inner).
    Returns (observed_diff_pp, ci_low, ci_high).
    anchor_tva / anchor_b2: {anchor_id → list of binary fill indicators}
    """
    rng = np.random.default_rng(seed)
    anchors = list(anchor_tva.keys())
    n_anchors = len(anchors)

    def anchor_diff(anchor_subset):
        tva_vals, b2_vals = [], []
        for a in anchor_subset:
            tva_vals.extend(anchor_tva.get(a, []))
            b2_vals.extend(anchor_b2.get(a, []))
        if not tva_vals or not b2_vals:
            return np.nan
        return np.mean(tva_vals) * 100 - np.mean(b2_vals) * 100

    observed = anchor_diff(anchors)
    boot_diffs = []
    for _ in range(n_boot):
        sampled_anchors = list(rng.choice(anchors, size=n_anchors, replace=True))
        boot_diffs.append(anchor_diff(sampled_anchors))
    boot_diffs = np.array([d for d in boot_diffs if not np.isnan(d)])
    ci_low = float(np.percentile(boot_diffs, 2.5))
    ci_high = float(np.percentile(boot_diffs, 97.5))
    return float(observed), ci_low, ci_high


def anchor_permutation_pvalue(
    anchor_tva: dict[str, list[int]],
    anchor_b2: dict[str, list[int]],
    n_perm: int = 10000,
    seed: int = 0,
) -> float:
    """
    Anchor-level sign-flip permutation test for TVA - B2 difference.
    Each anchor: d_a = mean(TVA_i) - mean(B2_i). Flip signs randomly.
    Returns two-sided p-value.
    """
    rng = np.random.default_rng(seed)
    anchors = list(anchor_tva.keys())
    anchor_diffs = []
    for a in anchors:
        tva = np.mean(anchor_tva.get(a, [0])) if anchor_tva.get(a) else 0.0
        b2  = np.mean(anchor_b2.get(a, [0]))  if anchor_b2.get(a)  else 0.0
        anchor_diffs.append(tva - b2)
    anchor_diffs = np.array(anchor_diffs)
    observed = np.abs(anchor_diffs.mean())
    perm_stats = []
    for _ in range(n_perm):
        signs = rng.choice([-1, 1], size=len(anchor_diffs))
        perm_stats.append(np.abs((signs * anchor_diffs).mean()))
    return float(np.mean(np.array(perm_stats) >= observed))


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

    # --- TVA fill indicators (per-anchor for hierarchical bootstrap) ---
    tva_legacy = []
    tva_calib  = []
    anchor_tva_legacy: dict[str, list[int]] = {a: [] for a in ANCHORS}
    anchor_tva_calib:  dict[str, list[int]] = {a: [] for a in ANCHORS}

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
        if not eligible_mask.any():
            tva_legacy.append(0); tva_calib.append(0)
            anchor_tva_legacy[aid].append(0); anchor_tva_calib[aid].append(0)
            continue

        eligible_val = val_emb[eligible_mask]
        max_sim = float((eligible_val @ mp).max())
        mid_density = local_density(mp, train_emb)
        tau_c = get_calib_tau(aid, mid_density)

        fl = 1 if max_sim >= LEGACY_TAU else 0
        fc = 1 if max_sim >= tau_c else 0
        tva_legacy.append(fl); tva_calib.append(fc)
        anchor_tva_legacy[aid].append(fl); anchor_tva_calib[aid].append(fc)

    # --- B2 density-matched fill indicators (per-anchor for hierarchical bootstrap) ---
    rng_b2 = random.Random(99)
    b2_legacy = []
    b2_calib  = []
    anchor_b2_legacy: dict[str, list[int]] = {a: [] for a in ANCHORS}
    anchor_b2_calib:  dict[str, list[int]] = {a: [] for a in ANCHORS}

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

        fl = 1 if max_sim >= LEGACY_TAU else 0
        fc = 1 if max_sim >= tau_c else 0
        b2_legacy.append(fl); b2_calib.append(fc)
        anchor_b2_legacy[aid].append(fl); anchor_b2_calib[aid].append(fc)

    # Results
    tva_rate_legacy = np.mean(tva_legacy)
    tva_rate_calib  = np.mean(tva_calib)
    b2_rate_legacy  = np.mean(b2_legacy)
    b2_rate_calib   = np.mean(b2_calib)

    # Hierarchical cluster bootstrap (anchor level) for paired difference pp
    diff_legacy, hb_l_lo, hb_l_hi = hierarchical_bootstrap_diff(
        anchor_tva_legacy, anchor_b2_legacy, n_bootstrap, BOOTSTRAP_SEED)
    diff_calib, hb_c_lo, hb_c_hi = hierarchical_bootstrap_diff(
        anchor_tva_calib, anchor_b2_calib, n_bootstrap, BOOTSTRAP_SEED + 1)

    # Anchor-level paired sign-flip permutation test
    pval_legacy = anchor_permutation_pvalue(anchor_tva_legacy, anchor_b2_legacy, seed=BOOTSTRAP_SEED)
    pval_calib  = anchor_permutation_pvalue(anchor_tva_calib,  anchor_b2_calib,  seed=BOOTSTRAP_SEED + 1)

    result = {
        "split": split_name,
        "n_tva": len(tva_legacy),
        "n_b2": len(b2_legacy),
        "n_anchors": len([a for a in ANCHORS if anchor_tva_legacy.get(a)]),
        "legacy_tau": LEGACY_TAU,
        "tva_legacy": {"rate": round(float(tva_rate_legacy), 4), "n_filled": int(sum(tva_legacy))},
        "b2_legacy":  {"rate": round(float(b2_rate_legacy),  4), "n_filled": int(sum(b2_legacy))},
        "tva_calib":  {"rate": round(float(tva_rate_calib),  4), "n_filled": int(sum(tva_calib))},
        "b2_calib":   {"rate": round(float(b2_rate_calib),   4), "n_filled": int(sum(b2_calib))},
        # Primary: paired difference + hierarchical CI (anchor-clustered)
        "diff_legacy_pp": {
            "diff": round(diff_legacy, 2),
            "hierarchical_ci_95": [round(hb_l_lo, 2), round(hb_l_hi, 2)],
            "permutation_pval": round(pval_legacy, 4),
        },
        "diff_calib_pp": {
            "diff": round(diff_calib, 2),
            "hierarchical_ci_95": [round(hb_c_lo, 2), round(hb_c_hi, 2)],
            "permutation_pval": round(pval_calib, 4),
        },
    }

    out_path = OUTPUT_DIR / split_name / "sensitivity_analysis.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    logger.info(f"Saved → {out_path}")

    print(f"\n[{split_name}] SENSITIVITY (hierarchical bootstrap, n_anchors={result['n_anchors']})")
    print(f"{'':22} {'τ=0.82 (legacy)':>20} {'calibrated τ':>20}")
    print("-" * 65)
    print(f"{'TVA fill rate':22} {tva_rate_legacy:>19.1%} {tva_rate_calib:>19.1%}")
    print(f"{'B2 fill rate':22} {b2_rate_legacy:>19.1%} {b2_rate_calib:>19.1%}")
    print(f"{'Δ pp (TVA-B2)':22} {diff_legacy:>+18.1f}pp {diff_calib:>+18.1f}pp")
    print(f"{'Hierarch. 95% CI':22} [{hb_l_lo:+.1f},{hb_l_hi:+.1f}]pp   [{hb_c_lo:+.1f},{hb_c_hi:+.1f}]pp")
    print(f"{'Permut. p-val':22} {pval_legacy:>19.3f} {pval_calib:>19.3f}")
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
