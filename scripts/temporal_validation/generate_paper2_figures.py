"""
scripts/temporal_validation/generate_paper2_figures.py

Generate all Paper 2 figures. Saves to paper2/figures/.

Figures:
  Fig 1: Role decomposition stacked bar (Table 3 visualization)
  Fig 2: Threshold calibration — null distribution + τ_fill vs 0.82
  Fig 3: Raw fill rates with bootstrap CI (legacy vs calibrated)
  Fig 4: Anchor exposure heatmap (pass rate by anchor × split)
  Fig 5: Local A-B density profile for Case Study (void valley)

Usage:
    python scripts/temporal_validation/generate_paper2_figures.py --all
    python scripts/temporal_validation/generate_paper2_figures.py --fig 1 2 3
"""

import argparse
import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

FIGURES_DIR = Path("paper2/figures")
FIGURES_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR = Path("data/processed/tvv/rolling")

SPLITS = ["t3", "t4", "t5"]
COLORS = {
    "void_resolution": "#2ecc71",
    "boundary_activity": "#3498db",
    "geometric_fp": "#e74c3c",
    "tva": "#2c3e50",
    "b1": "#e67e22",
    "b2": "#27ae60",
    "near_miss": "#95a5a6",
}


# ============================================================
def fig1_role_decomposition():
    """Stacked bar: role decomposition by source group (t5)."""
    WEIGHTS = {"TRUE_FILL": 1.0, "PARTIAL_FILL": 0.7, "SUPPORT_EVIDENCE": 0.5,
               "BENCHMARK_OR_MEASUREMENT": 0.4, "SURVEY_OR_NAMING": 0.3,
               "INCREMENTAL_EXTENSION": 0.2, "FALSE_POSITIVE": 0.0}

    # Load t5 role classification
    path = OUTPUT_DIR / "t5" / "role_classification_v2.json"
    data = json.load(open(path))
    from collections import defaultdict, Counter
    by_source = defaultdict(list)
    for r in data["results"]:
        by_source[r["case"].get("source", "?")].append(r)

    groups = [
        ("TVA\n(gated)", "tva"),
        ("B1\n(hot-zone)", "baseline"),
        ("B2\n(density)", "b2_density"),
        ("Near-miss", "tva_near_miss"),
    ]
    labels = [g[0] for g in groups]
    void_res, boundary, geo_fp = [], [], []

    for _, src in groups:
        cases = by_source.get(src, [])
        n = len(cases) if cases else 1
        roles = Counter(c["classification"]["role"] for c in cases)
        void_res.append((roles.get("TRUE_FILL", 0) + roles.get("PARTIAL_FILL", 0)) / n * 100)
        boundary.append((roles.get("INCREMENTAL_EXTENSION", 0) +
                         roles.get("SUPPORT_EVIDENCE", 0) +
                         roles.get("SURVEY_OR_NAMING", 0)) / n * 100)
        geo_fp.append(roles.get("FALSE_POSITIVE", 0) / n * 100)

    x = np.arange(len(labels))
    width = 0.55

    fig, ax = plt.subplots(figsize=(6, 4))
    b1 = ax.bar(x, geo_fp, width, label="Geometric FP", color=COLORS["geometric_fp"], alpha=0.85)
    b2 = ax.bar(x, boundary, width, bottom=geo_fp, label="Boundary activity", color=COLORS["boundary_activity"], alpha=0.85)
    b3 = ax.bar(x, void_res, width,
                bottom=[a + b for a, b in zip(geo_fp, boundary)],
                label="Void resolution", color=COLORS["void_resolution"], alpha=0.85)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel("Cases (%)", fontsize=11)
    ax.set_title("Figure 1: Epistemic Role Decomposition (t5, n=200 sampled)", fontsize=11)
    ax.legend(loc="lower right", fontsize=9)
    ax.set_ylim(0, 115)
    ax.axhline(100, color="gray", lw=0.5, ls="--")

    for i, (fp, ba, vr) in enumerate(zip(geo_fp, boundary, void_res)):
        ax.text(i, fp / 2, f"{fp:.0f}%", ha="center", va="center", fontsize=8, color="white", fontweight="bold")
        if ba > 5:
            ax.text(i, fp + ba / 2, f"{ba:.0f}%", ha="center", va="center", fontsize=8, color="white")
        if vr > 1:
            ax.text(i, fp + ba + vr / 2, f"{vr:.0f}%", ha="center", va="center", fontsize=7)

    plt.tight_layout()
    out = FIGURES_DIR / "fig1_role_decomposition.pdf"
    plt.savefig(out, bbox_inches="tight")
    plt.savefig(str(out).replace(".pdf", ".png"), dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Fig 1 saved → {out}")


# ============================================================
def fig2_threshold_calibration():
    """Null distribution boxplot per density bucket + 0.82 vs τ_fill lines."""
    cal = json.load(open(OUTPUT_DIR / "t5" / "fill_threshold_calibration.json"))

    # Gather τ_fill and FPR@0.82 per (anchor, bucket)
    taus = {"low": [], "mid": [], "high": []}
    fprs = {"low": [], "mid": [], "high": []}
    null_p50 = {"low": [], "mid": [], "high": []}

    for anchor_id, ar in cal["results"].items():
        for bucket in ["low", "mid", "high"]:
            if bucket in ar["density_buckets"]:
                br = ar["density_buckets"][bucket]
                taus[bucket].append(br["tau_calibrated"])
                fprs[bucket].append(br["fpr_at_0.82"])
                null_p50[bucket].append(br["null_p50"])

    fig, axes = plt.subplots(1, 2, figsize=(9, 4))

    # Left: τ_fill distributions
    ax = axes[0]
    colors = ["#85c1e9", "#3498db", "#1a5276"]
    bplot = ax.boxplot(
        [taus["low"], taus["mid"], taus["high"]],
        labels=["Low density", "Mid density", "High density"],
        patch_artist=True,
    )
    for patch, color in zip(bplot["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    ax.axhline(0.82, color="red", lw=1.5, ls="--", label="Legacy τ=0.82")
    ax.axhline(0.841, color="green", lw=1.5, ls="--", label="Mean calibrated τ=0.841")
    ax.set_ylabel("τ_fill (calibrated 5%-FPR threshold)", fontsize=10)
    ax.set_title("Calibrated threshold by density bucket", fontsize=10)
    ax.legend(fontsize=8)
    ax.set_ylim(0.77, 0.91)

    # Right: FPR@0.82
    ax = axes[1]
    bplot2 = ax.boxplot(
        [np.array(fprs["low"])*100, np.array(fprs["mid"])*100, np.array(fprs["high"])*100],
        labels=["Low density", "Mid density", "High density"],
        patch_artist=True,
    )
    for patch, color in zip(bplot2["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    ax.axhline(5, color="green", lw=1.5, ls="--", label="Target 5% FPR")
    ax.axhline(np.mean([v for vals in fprs.values() for v in vals])*100,
               color="red", lw=1.5, ls="--", label=f"Mean FPR@0.82 = {np.mean([v for vals in fprs.values() for v in vals])*100:.0f}%")
    ax.set_ylabel("Null FPR at τ=0.82 (%)", fontsize=10)
    ax.set_title("FPR of 0.82 by density bucket (t5)", fontsize=10)
    ax.legend(fontsize=8)
    ax.set_ylim(-5, 105)

    fig.suptitle("Figure 2: Threshold Calibration — Fixed τ=0.82 is Not Portable", fontsize=11)
    plt.tight_layout()
    out = FIGURES_DIR / "fig2_threshold_calibration.pdf"
    plt.savefig(out, bbox_inches="tight")
    plt.savefig(str(out).replace(".pdf", ".png"), dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Fig 2 saved → {out}")


# ============================================================
def fig3_fill_rates_ci():
    """Fill rates: legacy vs calibrated, with CI, across splits."""
    splits_data = {}
    for split in SPLITS:
        sa_path = OUTPUT_DIR / split / "sensitivity_analysis.json"
        if not sa_path.exists():
            continue
        splits_data[split] = json.load(open(sa_path))

    if not splits_data:
        print("Fig 3: no sensitivity_analysis.json found for any split, skipping")
        return

    fig, axes = plt.subplots(1, 2, figsize=(9, 4), sharey=False)

    split_labels = list(splits_data.keys())
    x = np.arange(len(split_labels))
    width = 0.25

    # Left: legacy τ=0.82
    ax = axes[0]
    tva_rates = [splits_data[s]["tva_legacy"]["rate"]*100 for s in split_labels]
    b2_rates  = [splits_data[s]["b2_legacy"]["rate"]*100 for s in split_labels]
    lifts     = [splits_data[s]["lift_legacy_tva_b2"]["lift"] for s in split_labels]
    ci_lo     = [splits_data[s]["lift_legacy_tva_b2"]["ci_95"][0] for s in split_labels]
    ci_hi     = [splits_data[s]["lift_legacy_tva_b2"]["ci_95"][1] for s in split_labels]

    ax.bar(x - width/2, tva_rates, width, label="TVA", color=COLORS["tva"], alpha=0.8)
    ax.bar(x + width/2, b2_rates,  width, label="B2 density-matched", color=COLORS["b2"], alpha=0.8)
    ax.set_xticks(x); ax.set_xticklabels(split_labels)
    ax.set_ylabel("Fill rate (%)"); ax.set_title("Legacy τ=0.82", fontsize=10)
    ax.legend(fontsize=9)

    # Annotate lift + CI
    for i, (l, lo, hi) in enumerate(zip(lifts, ci_lo, ci_hi)):
        ax.text(x[i], max(tva_rates[i], b2_rates[i]) + 1.5,
                f"{l:.2f}×\n[{lo:.2f},{hi:.2f}]", ha="center", fontsize=7, color="gray")

    # Right: calibrated τ
    ax = axes[1]
    tva_c = [splits_data[s]["tva_calib"]["rate"]*100 for s in split_labels]
    b2_c  = [splits_data[s]["b2_calib"]["rate"]*100 for s in split_labels]

    ax.bar(x - width/2, tva_c, width, label="TVA", color=COLORS["tva"], alpha=0.8)
    ax.bar(x + width/2, b2_c,  width, label="B2 density-matched", color=COLORS["b2"], alpha=0.8)
    ax.set_xticks(x); ax.set_xticklabels(split_labels)
    ax.set_ylabel("Fill rate (%)"); ax.set_title("Calibrated τ_fill(q,ρ,t)", fontsize=10)
    ax.legend(fontsize=9)
    ax.set_ylim(-0.2, 3)

    fig.suptitle("Figure 3: Fill Rates — Legacy vs Calibrated Threshold", fontsize=11)
    plt.tight_layout()
    out = FIGURES_DIR / "fig3_fill_rates_ci.pdf"
    plt.savefig(out, bbox_inches="tight")
    plt.savefig(str(out).replace(".pdf", ".png"), dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Fig 3 saved → {out}")


# ============================================================
def fig4_anchor_exposure():
    """Anchor exposure heatmap: pass rate by anchor × split."""
    exp_path = OUTPUT_DIR / "anchor_exposure_table.json"
    if not exp_path.exists():
        print("Fig 4: anchor_exposure_table.json not found, skipping")
        return

    rows = json.load(open(exp_path))
    splits_in_data = sorted(set(r["split"] for r in rows))
    anchors = sorted(set(r["anchor_id"] for r in rows))

    matrix = np.zeros((len(anchors), len(splits_in_data)))
    for r in rows:
        ai = anchors.index(r["anchor_id"])
        si = splits_in_data.index(r["split"])
        matrix[ai, si] = r["pass_hybrid_rate"] * 100

    fig, ax = plt.subplots(figsize=(5, 5))
    im = ax.imshow(matrix, aspect="auto", cmap="Blues", vmin=0, vmax=15)
    ax.set_xticks(range(len(splits_in_data)))
    ax.set_xticklabels(splits_in_data)
    ax.set_yticks(range(len(anchors)))
    ax.set_yticklabels(anchors, fontsize=8)
    plt.colorbar(im, ax=ax, label="Anchor-eligible val papers (%)")

    for i in range(len(anchors)):
        for j in range(len(splits_in_data)):
            ax.text(j, i, f"{matrix[i,j]:.1f}%", ha="center", va="center",
                    fontsize=7, color="black" if matrix[i,j] < 10 else "white")

    ax.set_title("Figure 4: Anchor Exposure (hybrid gate pass rate)", fontsize=10)
    plt.tight_layout()
    out = FIGURES_DIR / "fig4_anchor_exposure.pdf"
    plt.savefig(out, bbox_inches="tight")
    plt.savefig(str(out).replace(".pdf", ".png"), dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Fig 4 saved → {out}")


# ============================================================
def fig5_void_valley(split="t5", anchor_id="sched_opt", case_id=None):
    """Local density profile along A→B bridge ('void valley' plot)."""
    import chromadb
    from configs.settings import settings
    from vectordb.embedder import create_embedder

    client = chromadb.PersistentClient(path=str(settings.vectordb_path))
    train_col = client.get_collection(f"tvv_rolling_{split}_train")
    FETCH = 5000
    t_vecs = []
    for offset in range(0, train_col.count(), FETCH):
        b = train_col.get(limit=FETCH, offset=offset, include=["embeddings"])
        t_vecs.extend(b["embeddings"])
    train_emb = np.array(t_vecs, dtype=np.float32)

    # Use one TVA void from voids.jsonl
    voids_path = OUTPUT_DIR / split / "voids.jsonl"
    voids = [json.loads(l) for l in open(voids_path)]
    anchor_voids = [v for v in voids if v["anchor_id"] == anchor_id]
    if not anchor_voids:
        print(f"Fig 5: no voids for anchor {anchor_id}, skipping")
        return
    # pick void with highest mmr_score
    v = max(anchor_voids, key=lambda x: x["mmr_score"])

    t_ids = []
    for offset in range(0, train_col.count(), FETCH):
        b = train_col.get(limit=FETCH, offset=offset, include=[])
        t_ids.extend(b["ids"])
    id_to_vec = {t_ids[i]: train_emb[i] for i in range(len(t_ids))}

    va = id_to_vec.get(v["paper_a"]["id"])
    vb = id_to_vec.get(v["paper_b"]["id"])
    if va is None or vb is None:
        print(f"Fig 5: missing embeddings for void {v['void_id']}, skipping")
        return

    # Interpolated points along A→B
    lambdas = np.linspace(0, 1, 21)
    densities = []
    for lam in lambdas:
        z = (1 - lam) * va + lam * vb
        z = z / np.linalg.norm(z)
        sims = train_emb @ z
        k = 20
        density = float(np.sort(sims)[::-1][:k].mean())
        densities.append(density)

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(lambdas, densities, "b-o", markersize=5, linewidth=2)
    ax.axvline(0.5, color="red", ls="--", lw=1.5, label="Midpoint m(A,B)")
    ax.fill_between(lambdas, densities,
                    min(densities) - 0.002, alpha=0.1, color="blue")

    min_idx = np.argmin(densities)
    ax.annotate("Void\n(local density valley)",
                xy=(lambdas[min_idx], densities[min_idx]),
                xytext=(lambdas[min_idx] + 0.1, densities[min_idx] - 0.003),
                arrowprops=dict(arrowstyle="->", color="red"),
                fontsize=9, color="red")

    ax.set_xlabel("Interpolation λ (0=A, 1=B)", fontsize=11)
    ax.set_ylabel("Mean k-NN cosine sim (local density)", fontsize=11)
    ax.set_title(f"Figure 5: Local Density Profile Along A–B Bridge\n"
                 f"Anchor: {anchor_id}  |  Split: {split}", fontsize=10)
    ax.legend(fontsize=9)
    plt.tight_layout()
    out = FIGURES_DIR / "fig5_void_valley.pdf"
    plt.savefig(out, bbox_inches="tight")
    plt.savefig(str(out).replace(".pdf", ".png"), dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Fig 5 saved → {out}")
    print(f"  Void used: {v['void_id']}  A='{v['paper_a']['title'][:50]}'")
    print(f"             B='{v['paper_b']['title'][:50]}'")


# ============================================================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--fig", nargs="+", type=int)
    args = parser.parse_args()

    figs = list(range(1, 6)) if args.all else (args.fig or [1, 2, 3, 4])

    for f in figs:
        if f == 1: fig1_role_decomposition()
        elif f == 2: fig2_threshold_calibration()
        elif f == 3: fig3_fill_rates_ci()
        elif f == 4: fig4_anchor_exposure()
        elif f == 5: fig5_void_valley()

    print(f"\nAll figures saved to {FIGURES_DIR}/")


if __name__ == "__main__":
    main()
