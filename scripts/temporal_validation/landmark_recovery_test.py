"""
scripts/temporal_validation/landmark_recovery_test.py

Retrospective landmark recovery test for TVV Paper 2.

For each landmark bridge paper P published in year Y:
1. Build pre-Y corpus from TVA temporal splits (train corpus)
2. Run TVA to find candidate voids
3. Check if any void V=(A,B,q,m) aligns with P:
   - sim(P, m) — geometric proximity
   - anchor eligibility of P
   - interpretability of A/B as bridge hypothesis
4. Compare with B2 density-matched pairs on same metrics

Selection criteria (independent, pre-specified):
  - Published 2019-2023 (within TVA t3-t5 val windows)
  - arXiv paper in CS categories used by TVA
  - Recognized as bridging two separate CS communities
  - Landmark: widely cited or award paper

Selected landmarks:
  2006.06762  Ansor (2020)             ML framework ↔ compiler optimization
  2205.14135  FlashAttention (2022)    ML algorithm ↔ hardware memory hierarchy
  2309.06180  vLLM/PagedAttention (2023)  LLM serving ↔ OS virtual memory
  2002.11054  MLIR (2020)             compiler infra ↔ ML accelerators
  1909.03496  Devign (2019)           SW vulnerability detection ↔ GNN

This is a POSITIVE CONTROL / SANITY CHECK, not confirmatory evidence of TVA superiority.
It asks: Can TVA recover plausible pre-publication void hypotheses for known bridge papers?

Usage:
    python scripts/temporal_validation/landmark_recovery_test.py
    python scripts/temporal_validation/landmark_recovery_test.py --top-k 50 --output notes/landmark_results.json
"""

import argparse
import json
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

# Landmark papers: selected BEFORE running TVA, using independent bridge criteria
LANDMARKS = [
    {
        "arxiv_id": "2006.06762",
        "title": "Ansor: Generating High-Performance Tensor Programs for Deep Learning",
        "year": 2020,
        "split": "t5",    # train < 2018 → 2020 paper is in val
        "a_side": "ML framework / tensor computation",
        "b_side": "compiler optimization / loop tiling / code generation",
        "bridge_rationale": "Re-defines tensor program generation as ML-guided compiler search space exploration",
        "best_anchor": "hwsw_x86",  # hardware-software co-design
    },
    {
        "arxiv_id": "2205.14135",
        "title": "FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness",
        "year": 2022,
        "split": "t5",
        "a_side": "ML algorithm design / Transformer attention",
        "b_side": "hardware memory hierarchy / IO complexity (HBM vs SRAM)",
        "bridge_rationale": "Re-interprets attention as IO-complexity problem, bridging GPU memory analysis to ML algorithm design",
        "best_anchor": "hwsw_x86",
    },
    {
        "arxiv_id": "2309.06180",
        "title": "Efficient Memory Management for Large Language Model Serving with PagedAttention",
        "year": 2023,
        "split": "t5",
        "a_side": "LLM inference / ML serving",
        "b_side": "OS virtual memory management / paging",
        "bridge_rationale": "Ports OS paging concept to KV cache management, bridging OS and LLM serving communities",
        "best_anchor": "mm_vm",  # virtual memory management
    },
    {
        "arxiv_id": "2002.11054",
        "title": "MLIR: Scaling Compiler Infrastructure for Domain Specific Computation",
        "year": 2020,
        "split": "t5",
        "a_side": "traditional compiler infrastructure (LLVM ecosystem)",
        "b_side": "ML hardware accelerators / domain-specific languages (XLA, TPU)",
        "bridge_rationale": "Unified IR hierarchy allowing compiler and ML hardware designers to share infrastructure",
        "best_anchor": "hwsw_x86",
    },
    {
        "arxiv_id": "1909.03496",
        "title": "Devign: Effective Vulnerability Identification by Learning Comprehensive Program Semantics via Graph Neural Networks",
        "year": 2019,
        "split": "t3",  # train < 2014? No — 2019 is in t3 val (2015-2019)? Check: t3 val=2015-2019 ✓
        "a_side": "software vulnerability detection / static analysis",
        "b_side": "graph neural networks / program representation learning",
        "bridge_rationale": "First large-scale benchmark combining CFG+DFG+AST graph representation with GNN for vulnerability detection",
        "best_anchor": "ebpf_obs",  # kernel tracing / observability closest
    },
]


def slerp(a, b):
    c = a + b; n = np.linalg.norm(c)
    return c / n if n > 0 else c


def run_landmark_recovery(top_k: int = 50):
    import chromadb
    from configs.settings import settings
    from vectordb.embedder import create_embedder

    embedder = create_embedder()
    client = chromadb.PersistentClient(path=str(settings.vectordb_path))

    results = []

    for lm in LANDMARKS:
        split_name = lm["split"]
        anchor_id = lm["best_anchor"]
        logger.info(f"\nLandmark: {lm['arxiv_id']} ({lm['year']}) — {lm['title'][:60]}")
        logger.info(f"  Split: {split_name}  Anchor: {anchor_id}")

        try:
            train_col = client.get_collection(f"tvv_rolling_{split_name}_train")
        except Exception as e:
            logger.warning(f"  Collection not found: {e}")
            continue

        FETCH = 5000
        t_ids, t_vecs, t_metas = [], [], []
        for offset in range(0, train_col.count(), FETCH):
            b = train_col.get(limit=FETCH, offset=offset, include=["embeddings", "metadatas"])
            t_ids.extend(b["ids"])
            t_vecs.extend(b["embeddings"])
            t_metas.extend(b["metadatas"])
        train_emb = np.array(t_vecs, dtype=np.float32)
        logger.info(f"  Train corpus: {len(t_ids):,} papers")

        # Embed landmark paper (title only — abstract may not be in snapshot)
        lm_vec = np.array(embedder.embed_query(lm["title"]), dtype=np.float32)
        anchor_text = ANCHORS[anchor_id]
        anchor_vec = np.array(embedder.embed_query(anchor_text), dtype=np.float32)

        # Load TVA voids for this split
        voids_path = OUTPUT_DIR / split_name / "voids.jsonl"
        if not voids_path.exists():
            logger.warning(f"  Voids file not found: {voids_path}")
            continue
        voids = [json.loads(l) for l in open(voids_path) if json.loads(l)["anchor_id"] == anchor_id]
        logger.info(f"  TVA voids for anchor {anchor_id}: {len(voids)}")

        id_to_idx = {t_ids[i]: i for i in range(len(t_ids))}
        id_to_meta = {t_ids[i]: t_metas[i] for i in range(len(t_ids))}

        # Compute sim(landmark, midpoint) for each void
        void_results = []
        for v in voids:
            va_idx = id_to_idx.get(v["paper_a"]["id"])
            vb_idx = id_to_idx.get(v["paper_b"]["id"])
            if va_idx is None or vb_idx is None:
                continue
            va = train_emb[va_idx]
            vb = train_emb[vb_idx]
            mp = slerp(va, vb)
            sim_lm_mp = float(lm_vec @ mp)
            sim_lm_anchor = float(lm_vec @ anchor_vec)
            void_results.append({
                "void_id": v["void_id"],
                "sim_landmark_to_midpoint": round(sim_lm_mp, 4),
                "sim_landmark_to_anchor": round(sim_lm_anchor, 4),
                "paper_a": {"id": v["paper_a"]["id"], "title": v["paper_a"].get("title","")},
                "paper_b": {"id": v["paper_b"]["id"], "title": v["paper_b"].get("title","")},
                "mmr_score": v.get("mmr_score", 0),
            })

        if not void_results:
            logger.warning("  No voids found for this anchor/split")
            continue

        # Sort by sim_landmark_to_midpoint
        void_results.sort(key=lambda x: x["sim_landmark_to_midpoint"], reverse=True)
        top = void_results[:5]

        logger.info(f"  Top voids by sim(landmark, midpoint):")
        for i, r in enumerate(top):
            logger.info(f"    [{i+1}] sim={r['sim_landmark_to_midpoint']:.4f}  "
                        f"anchor_sim={r['sim_landmark_to_anchor']:.4f}")
            logger.info(f"         A: {r['paper_a']['title'][:60]}")
            logger.info(f"         B: {r['paper_b']['title'][:60]}")

        # Sim of landmark to anchor
        sim_to_anchor = float(lm_vec @ anchor_vec)
        # Sim of landmark to random train papers (background)
        all_sims = train_emb @ lm_vec
        bg_p90 = float(np.percentile(all_sims, 90))
        bg_p95 = float(np.percentile(all_sims, 95))
        bg_p99 = float(np.percentile(all_sims, 99))

        result = {
            "landmark": {
                "arxiv_id": lm["arxiv_id"],
                "title": lm["title"],
                "year": lm["year"],
                "split": split_name,
                "anchor": anchor_id,
                "a_side": lm["a_side"],
                "b_side": lm["b_side"],
                "bridge_rationale": lm["bridge_rationale"],
            },
            "sim_to_anchor": round(sim_to_anchor, 4),
            "sim_to_train_background": {
                "p90": round(bg_p90, 4),
                "p95": round(bg_p95, 4),
                "p99": round(bg_p99, 4),
            },
            "n_voids_checked": len(void_results),
            "top5_voids": top,
            "best_void_sim": top[0]["sim_landmark_to_midpoint"] if top else None,
            "best_void_rank_in_corpus": None,  # rank of best sim vs all train papers
        }

        # Compute percentile rank: how often does a random train paper beat the best void?
        if top:
            best_sim = top[0]["sim_landmark_to_midpoint"]
            rank_pctile = float((all_sims < best_sim).mean())
            result["best_void_percentile_vs_train"] = round(rank_pctile, 4)
            logger.info(f"  Best void sim={best_sim:.4f} is at {rank_pctile:.0%} percentile vs train")

        results.append(result)

    return results


def print_summary(results):
    print(f"\n{'='*80}")
    print("LANDMARK RECOVERY TEST — SUMMARY")
    print(f"{'='*80}")
    print(f"{'Paper':<45} {'AncSim':>7} {'BestVoid':>9} {'Pctile':>7}")
    print("-" * 80)
    for r in results:
        lm = r["landmark"]
        best = r.get("best_void_sim", 0) or 0
        pctile = r.get("best_void_percentile_vs_train", 0) or 0
        anc_sim = r["sim_to_anchor"]
        print(f"{lm['title'][:44]:<45} {anc_sim:>7.4f} {best:>9.4f} {pctile:>6.0%}")
    print(f"{'='*80}")
    print("""
Interpretation:
- AncSim: sim(landmark, anchor vector) — is the landmark in the anchor's domain?
- BestVoid: highest sim(landmark, void_midpoint) among TVA voids for that anchor
- Pctile: fraction of train papers with sim < BestVoid (how high is the void match?)

A landmark paper with BestVoid > background p90 and interpretable A/B sides
supports the sanity check: TVA can generate plausible pre-publication void hypotheses
for known bridge-type papers.
""")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-k", type=int, default=50)
    parser.add_argument("--output", default="notes/landmark_recovery_results.json")
    args = parser.parse_args()

    results = run_landmark_recovery(args.top_k)
    print_summary(results)

    out_path = Path(args.output)
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"Saved → {out_path}")


if __name__ == "__main__":
    main()
