"""
scripts/temporal_validation/er_stage3a_crossencoder.py

Stage 3a: Cross-Encoder Reranking as R-layer surrogate.

Uses BAAI/bge-reranker-v2-m3 (BGE-M3's own cross-encoder sibling).

Score function: rerank_score(P_text, query)
Query formats tested:
  (1) A_text + " " + B_text (concat) — measures P's relevance to joint A∪B
  (2) anchor_query — measures P's relevance to anchor (G proxy)
  (3) asymmetry: |score(P|A) - score(P|B)| — tests one-sidedness

24h falsification gate:
  Run on 5 landmark papers first.
  If ≥4/5 score > random_baseline_mean + 1.5σ → proceed to 100 cases.

Decision gate:
  κ ≥ 0.5 → found R surrogate
  κ < 0.1 → architectural impossibility confirmed

Usage:
    # Quick landmark gate first
    python er_stage3a_crossencoder.py --mode landmarks --split t5

    # Full 100 cases
    python er_stage3a_crossencoder.py --mode full --split t5 --max-cases 100
"""

import argparse
import json
import time
from pathlib import Path

import numpy as np
from loguru import logger

OUTPUT_DIR = Path("data/processed/tvv/rolling")

LANDMARKS = [
    {"arxiv_id": "2309.06180", "title": "Efficient Memory Management for Large Language Model Serving with PagedAttention", "year": 2023},
    {"arxiv_id": "2002.11054", "title": "MLIR: Scaling Compiler Infrastructure for Domain Specific Computation", "year": 2020},
    {"arxiv_id": "1909.03496", "title": "Devign: Effective Vulnerability Identification by Learning Comprehensive Program Semantics via Graph Neural Networks", "year": 2019},
    {"arxiv_id": "2006.06762", "title": "Ansor: Generating High-Performance Tensor Programs for Deep Learning", "year": 2020},
    {"arxiv_id": "2205.14135", "title": "FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness", "year": 2022},
]

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


def load_reranker(model_name="data/models/bge-reranker-v2-m3"):
    from sentence_transformers import CrossEncoder
    logger.info(f"Loading cross-encoder: {model_name}")
    model = CrossEncoder(model_name, max_length=512)
    return model


def rerank_score(model, query: str, doc: str) -> float:
    """Score (query, doc) pair. Returns logit (before sigmoid)."""
    score = model.predict([[query, doc]])
    return float(score[0])


def run_landmarks(model, split_name: str):
    """24h falsification: run 5 landmarks against their expected anchors."""
    data = json.load(open(OUTPUT_DIR / split_name / "role_classification_v2.json"))
    cases = data["results"]

    # Build random baseline from 50 random cases (non-fill)
    random_scores = []
    for r in cases[:50]:
        case = r["case"]
        p_text = case.get("filler", {}).get("title", "") + " " + case.get("filler", {}).get("abstract", "")[:200]
        a_text = case.get("source_a", {}).get("title", "") + " " + case.get("source_a", {}).get("abstract", "")[:200]
        b_text = case.get("source_b", {}).get("title", "") + " " + case.get("source_b", {}).get("abstract", "")[:200]
        if not p_text.strip() or not a_text.strip():
            continue
        score = rerank_score(model, a_text + " " + b_text, p_text)
        random_scores.append(score)

    baseline_mean = np.mean(random_scores)
    baseline_std  = np.std(random_scores)
    logger.info(f"Random baseline: mean={baseline_mean:.3f} std={baseline_std:.3f} n={len(random_scores)}")

    # Landmark scores
    results = []
    for lm in LANDMARKS:
        lm_text = lm["title"]
        # Use virt_hyp for vLLM, hwsw for MLIR/Ansor/FlashAttention, ebpf for Devign
        anchor_map = {
            "2309.06180": "mm_vm",
            "2002.11054": "hwsw_x86",
            "1909.03496": "ebpf_obs",
            "2006.06762": "hwsw_x86",
            "2205.14135": "hwsw_x86",
        }
        anchor_id = anchor_map.get(lm["arxiv_id"], "sched_opt")

        # Find a matching void (same anchor) to get A, B
        best_case = None
        for r in cases:
            if r["case"].get("anchor_id") == anchor_id:
                best_case = r["case"]
                break

        if best_case is None:
            logger.warning(f"  No case found for anchor {anchor_id}")
            continue

        a_text = best_case.get("source_a", {}).get("title", "") + " " + best_case.get("source_a", {}).get("abstract", "")[:200]
        b_text = best_case.get("source_b", {}).get("title", "") + " " + best_case.get("source_b", {}).get("abstract", "")[:200]

        score_ab = rerank_score(model, a_text + " " + b_text, lm_text)
        z_score = (score_ab - baseline_mean) / max(baseline_std, 0.001)
        pass_gate = z_score > 1.5

        results.append({
            "landmark": lm["title"][:50],
            "score": round(score_ab, 4),
            "z_score": round(z_score, 3),
            "pass": pass_gate,
        })
        logger.info(f"  {lm['arxiv_id']}: score={score_ab:.3f}  z={z_score:.2f}  {'✓' if pass_gate else '✗'}")

    n_pass = sum(1 for r in results if r["pass"])
    print(f"\n=== LANDMARK GATE: {n_pass}/{len(results)} pass ===")
    print(f"Criterion: z-score > 1.5 (baseline mean={baseline_mean:.3f} std={baseline_std:.3f})")
    for r in results:
        print(f"  {'✓' if r['pass'] else '✗'}  {r['landmark']:<50}  z={r['z_score']:+.2f}")

    gate_pass = n_pass >= 4
    if gate_pass:
        print(f"\n→ GATE PASSED: proceed to full 100 cases")
    else:
        print(f"\n→ GATE FAILED: cross-encoder has no landmark signal — impossibility extends to CE")

    return gate_pass, results, baseline_mean, baseline_std


def run_full(model, split_name: str, max_cases: int = 100):
    """Full cross-encoder evaluation on role-classified cases."""
    from sklearn.metrics import cohen_kappa_score, roc_auc_score

    data = json.load(open(OUTPUT_DIR / split_name / "role_classification_v2.json"))
    cases = data["results"][:max_cases]

    t0 = time.time()
    results = []

    for idx, r in enumerate(cases):
        case = r["case"]
        clf  = r["classification"]
        role = clf.get("role", "UNCLEAR")
        is_fill = int(role in {"TRUE_FILL", "PARTIAL_FILL"})

        p_title = case.get("filler", {}).get("title", "")
        p_abs   = case.get("filler", {}).get("abstract", "")[:300]
        a_title = case.get("source_a", {}).get("title", "")
        a_abs   = case.get("source_a", {}).get("abstract", "")[:300]
        b_title = case.get("source_b", {}).get("title", "")
        b_abs   = case.get("source_b", {}).get("abstract", "")[:300]
        anchor  = case.get("anchor", "")

        p_text = (p_title + " " + p_abs).strip()
        a_text = (a_title + " " + a_abs).strip()
        b_text = (b_title + " " + b_abs).strip()

        if not p_text or not a_text:
            continue

        # Q1: anchor only (G proxy baseline)
        score_q1 = rerank_score(model, anchor[:400], p_text[:400])
        # Q2: A+B concat (joint bridging)
        score_q2 = rerank_score(model, a_text[:300] + " [SEP] " + b_text[:300], p_text[:400])
        # Q3: prompt-based
        q3_prompt = f"How does this paper bridge '{a_title[:60]}' and '{b_title[:60]}'?"
        score_q3 = rerank_score(model, q3_prompt, p_text[:400])
        # Q4: asymmetry — score each side separately
        score_a_only = rerank_score(model, a_text[:400], p_text[:400])
        score_b_only = rerank_score(model, b_text[:400], p_text[:400])
        asymmetry = abs(score_a_only - score_b_only)
        score_q4 = min(score_a_only, score_b_only)  # bridging requires BOTH sides

        results.append({
            "case_id": case.get("case_id", ""),
            "role_llm": role,
            "is_fill_llm": is_fill,
            "score_q1_anchor": round(score_q1, 4),
            "score_q2_joint":  round(score_q2, 4),
            "score_q3_prompt": round(score_q3, 4),
            "score_q4_min":    round(score_q4, 4),
            "score_a_only":    round(score_a_only, 4),
            "score_b_only":    round(score_b_only, 4),
            "asymmetry":       round(asymmetry, 4),
        })

        if (idx + 1) % 10 == 0:
            logger.info(f"  {idx+1}/{len(cases)}  {(time.time()-t0)/len(results):.1f}s/case")

    total_time = time.time() - t0
    if not results:
        return

    scores_q1 = np.array([r["score_q1_anchor"] for r in results])
    scores_q2 = np.array([r["score_q2_joint"]  for r in results])
    scores_q3 = np.array([r["score_q3_prompt"] for r in results])
    scores_q4 = np.array([r["score_q4_min"]    for r in results])
    llm_fill  = np.array([r["is_fill_llm"] for r in results], dtype=int)

    def eval_metric(scores, llm_fill, label):
        from scipy.stats import pearsonr
        r_c, p_c = pearsonr(scores, llm_fill)

        best_kappa = -1
        best_thr   = 0
        for thr in np.linspace(scores.min(), scores.max(), 100):
            pred = (scores >= thr).astype(int)
            if pred.sum() == 0 or pred.sum() == len(pred):
                continue
            try:
                k = cohen_kappa_score(llm_fill, pred)
                if k > best_kappa:
                    best_kappa = k; best_thr = thr
            except Exception:
                pass

        try:
            auc = roc_auc_score(llm_fill, scores)
        except Exception:
            auc = 0.5

        fill_scores = scores[llm_fill == 1]
        nfill_scores = scores[llm_fill == 0]

        print(f"\n  [{label}]")
        print(f"  Fill (n={fill_scores.shape[0]}): mean={fill_scores.mean() if len(fill_scores) else 0:.3f}  p50={np.median(fill_scores) if len(fill_scores) else 0:.3f}")
        print(f"  Non-fill (n={nfill_scores.shape[0]}): mean={nfill_scores.mean():.3f}  p50={np.median(nfill_scores):.3f}")
        print(f"  Pearson r={r_c:.4f} (p={p_c:.4f})")
        print(f"  Best κ={best_kappa:.4f} at threshold={best_thr:.3f}")
        print(f"  AUC-ROC={auc:.4f}")

        if best_kappa >= 0.5:
            print(f"  ✓✓ κ ≥ 0.5 — VIABLE R SURROGATE")
        elif best_kappa >= 0.3:
            print(f"  ~ κ ∈ [0.3,0.5) — weak but present signal")
        elif best_kappa >= 0.1:
            print(f"  ~ κ ∈ [0.1,0.3) — very weak signal")
        else:
            print(f"  ✗ κ < 0.1 — no discriminative signal")

        return {"label": label, "kappa": round(best_kappa, 4), "auc": round(auc, 4), "pearson_r": round(r_c, 4)}

    print(f"\n{'='*60}")
    print(f"STAGE 3a: CROSS-ENCODER RERANKING (n={len(results)}, {total_time:.0f}s, {total_time/len(results):.1f}s/case)")
    print(f"Query formats: Q1=anchor  Q2=A+B joint  Q3=prompt  Q4=min(A,B)")
    res1 = eval_metric(scores_q1, llm_fill, "Q1 anchor")
    res2 = eval_metric(scores_q2, llm_fill, "Q2 A+B joint")
    res3 = eval_metric(scores_q3, llm_fill, "Q3 prompt")
    res4 = eval_metric(scores_q4, llm_fill, "Q4 min(A,B)")

    # Asymmetry analysis
    asym = np.array([r["asymmetry"] for r in results])
    print(f"\n  [Asymmetry |score(A)-score(B)|]")
    print(f"  mean={asym.mean():.4f}  p50={np.median(asym):.4f}  p90={np.percentile(asym,90):.4f}")

    # 4-class breakdown for best format
    best_scores = scores_q2  # typically best candidate
    roles = [r["role_llm"] for r in results]
    for cls in ["TRUE_FILL", "PARTIAL_FILL", "INCREMENTAL_EXTENSION", "FALSE_POSITIVE"]:
        cls_scores = [best_scores[i] for i, r in enumerate(results) if r["role_llm"] == cls]
        if cls_scores:
            print(f"  {cls}: n={len(cls_scores)} mean={np.mean(cls_scores):.3f} p50={np.median(cls_scores):.3f}")

    out = {
        "split": split_name, "stage": "3a", "n_cases": len(results),
        "total_time_sec": round(total_time, 1),
        "sec_per_case": round(total_time/len(results), 2),
        "formats": [res1, res2, res3, res4],
        "asymmetry_mean": round(float(asym.mean()), 4),
        "cases": results,
    }
    out_path = OUTPUT_DIR / split_name / "er_stage3a_crossencoder.json"
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    logger.info(f"Saved → {out_path}")
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["landmarks", "full"], default="landmarks")
    parser.add_argument("--split", default="t5")
    parser.add_argument("--max-cases", type=int, default=100)
    parser.add_argument("--model", default="BAAI/bge-reranker-v2-m3")
    args = parser.parse_args()

    model = load_reranker(args.model)

    if args.mode == "landmarks":
        gate, results, bmean, bstd = run_landmarks(model, args.split)
        if gate:
            print("\nProceeding to full evaluation...")
            run_full(model, args.split, args.max_cases)
    else:
        run_full(model, args.split, args.max_cases)


if __name__ == "__main__":
    main()
