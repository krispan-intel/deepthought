"""
scripts/temporal_validation/landmark_recovery_v2.py

IMPROVED retrospective landmark recovery test.

Four improvements over v1:
  1. Per-landmark cutoff: use the split whose train_end is closest to but before
     the landmark paper's year (not just t5 for everyone).
  2. Anchor-restricted void search: only consider TVA voids for anchors where
     sim(landmark, anchor) > anchor_p90 (anchor-eligible).
  3. Same-anchor null midpoint percentile: compare sim(P, best_void_midpoint)
     against the null midpoint distribution for THAT anchor, not all train papers.
  4. A/B interpretability audit: LLM judges whether the top void's A/B/q
     forms a plausible pre-publication bridge hypothesis for the landmark.

Selection criteria (pre-specified, independent):
  - Published 2019-2023
  - arXiv CS categories used by TVA
  - Widely cited, bridge-type, cross-community
  - NOT cherry-picked after running TVA

Usage:
    python scripts/temporal_validation/landmark_recovery_v2.py
    python scripts/temporal_validation/landmark_recovery_v2.py --output notes/landmark_v2.json
"""

import argparse
import json
import random
from pathlib import Path

import numpy as np
from loguru import logger

OUTPUT_DIR = Path("data/processed/tvv/rolling")

SPLITS = {
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

LANDMARKS = [
    {
        "arxiv_id": "2006.06762",
        "title": "Ansor: Generating High-Performance Tensor Programs for Deep Learning",
        "year": 2020,
        "a_side": "ML framework / tensor computation and DNN operator optimization",
        "b_side": "compiler optimization / loop tiling / automated code generation",
        "bridge_rationale": "Redefines tensor code generation as ML-guided search over a compiler search space",
        "expected_anchors": ["hwsw_x86", "sched_opt"],
    },
    {
        "arxiv_id": "2205.14135",
        "title": "FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness",
        "year": 2022,
        "a_side": "ML algorithm design / Transformer attention computation",
        "b_side": "hardware memory hierarchy / IO complexity / SRAM vs HBM bandwidth",
        "bridge_rationale": "Reframes attention as an IO-complexity optimization problem, bridging ML and hardware memory analysis",
        "expected_anchors": ["hwsw_x86", "mem_alloc"],
    },
    {
        "arxiv_id": "2309.06180",
        "title": "Efficient Memory Management for Large Language Model Serving with PagedAttention",
        "year": 2023,
        "a_side": "LLM inference serving / KV cache management",
        "b_side": "OS virtual memory management / demand paging / memory fragmentation",
        "bridge_rationale": "Ports OS demand paging concept directly to LLM KV cache, bridging OS and ML serving communities",
        "expected_anchors": ["mm_vm", "virt_hyp"],
    },
    {
        "arxiv_id": "2002.11054",
        "title": "MLIR: Scaling Compiler Infrastructure for Domain Specific Computation",
        "year": 2020,
        "a_side": "compiler infrastructure / LLVM ecosystem / code optimization",
        "b_side": "ML hardware accelerators / domain-specific languages (XLA, TPU, custom ASIC)",
        "bridge_rationale": "Unified multi-level IR hierarchy allowing compiler and ML hardware designers to share infrastructure",
        "expected_anchors": ["hwsw_x86", "sched_opt"],
    },
    {
        "arxiv_id": "1909.03496",
        "title": "Devign: Effective Vulnerability Identification by Learning Comprehensive Program Semantics via Graph Neural Networks",
        "year": 2019,
        "a_side": "software vulnerability detection / static analysis / code review",
        "b_side": "graph neural networks / program representation learning",
        "bridge_rationale": "First large-scale benchmark combining CFG+DFG+AST with GNN for C/C++ vulnerability detection",
        "expected_anchors": ["ebpf_obs", "sync_lock"],
    },
]

C1_POOL = 300
NULL_SAMPLES = 500


def slerp(a, b):
    c = a + b; n = np.linalg.norm(c)
    return c / n if n > 0 else c


def pick_split(year: int) -> str:
    """Pick the split whose train_end is closest to but before the landmark year."""
    best = None
    for sname, cfg in SPLITS.items():
        if cfg["train_end"] < year:
            if best is None or cfg["train_end"] > SPLITS[best]["train_end"]:
                best = sname
    return best or "t5"


def run_landmark(lm: dict, top_k: int = 10):
    import chromadb
    from configs.settings import settings
    from vectordb.embedder import create_embedder
    from agents.llm_client import LLMClient
    from agents.json_parser import robust_json_parse

    embedder = create_embedder()
    client = chromadb.PersistentClient(path=str(settings.vectordb_path))
    llm = LLMClient()

    # Improvement 1: per-landmark cutoff
    split_name = pick_split(lm["year"])
    logger.info(f"  Using split {split_name} (train_end={SPLITS[split_name]['train_end']}) for {lm['year']} landmark")

    try:
        train_col = client.get_collection(f"tvv_rolling_{split_name}_train")
    except Exception as e:
        logger.error(f"  Collection not found: {e}")
        return None

    FETCH = 5000
    t_ids, t_vecs, t_metas = [], [], []
    for offset in range(0, train_col.count(), FETCH):
        b = train_col.get(limit=FETCH, offset=offset, include=["embeddings", "metadatas"])
        t_ids.extend(b["ids"])
        t_vecs.extend(b["embeddings"])
        t_metas.extend(b["metadatas"])
    train_emb = np.array(t_vecs, dtype=np.float32)

    # Embed landmark
    lm_vec = np.array(embedder.embed_query(lm["title"]), dtype=np.float32)

    # Embed all anchors
    anchor_vecs = {
        aid: np.array(embedder.embed_query(atext), dtype=np.float32)
        for aid, atext in ANCHORS.items()
    }

    # Improvement 2: anchor-restricted — only anchors where sim(P, q) > p90
    anchor_sims = {aid: float(lm_vec @ av) for aid, av in anchor_vecs.items()}
    train_anchor_sims = {
        aid: train_emb @ anchor_vecs[aid]
        for aid in ANCHORS
    }
    anchor_p90 = {aid: float(np.percentile(sims, 90)) for aid, sims in train_anchor_sims.items()}
    eligible_anchors = [
        aid for aid in ANCHORS
        if anchor_sims[aid] >= anchor_p90[aid]
    ]
    logger.info(f"  Anchor-eligible: {eligible_anchors} (of {len(ANCHORS)})")

    if not eligible_anchors:
        # Fallback: use top-2 by sim
        eligible_anchors = sorted(ANCHORS, key=lambda a: anchor_sims[a], reverse=True)[:2]
        logger.info(f"  No eligible anchors; fallback to top-2: {eligible_anchors}")

    # Load TVA voids
    voids_path = OUTPUT_DIR / split_name / "voids.jsonl"
    if not voids_path.exists():
        logger.error(f"  Voids not found: {voids_path}")
        return None
    all_voids = [json.loads(l) for l in open(voids_path)]

    id_to_idx = {t_ids[i]: i for i in range(len(t_ids))}
    id_to_meta = {t_ids[i]: t_metas[i] for i in range(len(t_ids))}
    id_to_title = {t_ids[i]: (t_metas[i] or {}).get("title", "") for i in range(len(t_ids))}

    best_void = None
    best_sim = -1
    best_anchor = None
    anchor_results = {}

    rng = random.Random(42)

    for anchor_id in eligible_anchors:
        av = anchor_vecs[anchor_id]
        voids_for_anchor = [v for v in all_voids if v["anchor_id"] == anchor_id]

        # Compute sim(landmark, void_midpoint) for each void
        void_sims = []
        for v in voids_for_anchor:
            ai = id_to_idx.get(v["paper_a"]["id"])
            bi = id_to_idx.get(v["paper_b"]["id"])
            if ai is None or bi is None:
                continue
            mp = slerp(train_emb[ai], train_emb[bi])
            s = float(lm_vec @ mp)
            void_sims.append((s, v, ai, bi, mp))
        void_sims.sort(key=lambda x: x[0], reverse=True)

        # Improvement 3: same-anchor null midpoint percentile
        c1_sims = train_emb @ av
        c1_idx = c1_sims.argsort()[::-1][:C1_POOL].tolist()
        null_sims = []
        for _ in range(NULL_SAMPLES):
            i, j = rng.sample(c1_idx, 2)
            mp_null = slerp(train_emb[i], train_emb[j])
            null_sims.append(float(lm_vec @ mp_null))
        null_sims = np.array(null_sims)
        null_p90 = float(np.percentile(null_sims, 90))
        null_p95 = float(np.percentile(null_sims, 95))

        top_voids = void_sims[:top_k]
        top_result = top_voids[0] if top_voids else None

        if top_result and top_result[0] > best_sim:
            best_sim = top_result[0]
            best_void = top_result
            best_anchor = anchor_id

        anchor_results[anchor_id] = {
            "anchor_sim": round(anchor_sims[anchor_id], 4),
            "anchor_p90": round(anchor_p90[anchor_id], 4),
            "eligible": True,
            "n_voids": len(voids_for_anchor),
            "null_p90": round(null_p90, 4),
            "null_p95": round(null_p95, 4),
            "best_void_sim": round(top_result[0], 4) if top_result else None,
            "above_null_p90": (top_result[0] > null_p90) if top_result else False,
            "above_null_p95": (top_result[0] > null_p95) if top_result else False,
            "top3_voids": [
                {
                    "sim": round(s, 4),
                    "void_id": v["void_id"],
                    "paper_a_title": id_to_title.get(v["paper_a"]["id"], "")[:80],
                    "paper_b_title": id_to_title.get(v["paper_b"]["id"], "")[:80],
                }
                for s, v, _, _, _ in void_sims[:3]
            ],
        }

    # Improvement 4: LLM interpretability audit for best void
    interpretability = None
    if best_void:
        sim, v, ai, bi, mp = best_void
        a_title = id_to_title.get(v["paper_a"]["id"], "Unknown")
        b_title = id_to_title.get(v["paper_b"]["id"], "Unknown")
        a_abstract = (id_to_meta.get(v["paper_a"]["id"]) or {}).get("abstract", "")[:300]
        b_abstract = (id_to_meta.get(v["paper_b"]["id"]) or {}).get("abstract", "")[:300]

        prompt = f"""You are evaluating whether a TVA void forms a plausible pre-publication bridge hypothesis for a landmark paper.

Landmark paper: "{lm['title']}" ({lm['year']})
Known bridge: {lm['a_side']} ↔ {lm['b_side']}
Bridge rationale: {lm['bridge_rationale']}

TVA void source papers (published before {lm['year']}):
Source A: "{a_title}"
Abstract A: {a_abstract}

Source B: "{b_title}"
Abstract B: {b_abstract}

Question: Does this A/B pair form a plausible pre-publication bridge hypothesis for the landmark paper?
Specifically: Could A and B represent the two communities that the landmark paper later bridged?

Return strict JSON:
{{
  "plausible_bridge": true or false,
  "confidence": 0.0 to 1.0,
  "a_represents": "what A-side community does paper A represent?",
  "b_represents": "what B-side community does paper B represent?",
  "match_to_landmark_a": "does A match the landmark's A-side? (yes/partial/no)",
  "match_to_landmark_b": "does B match the landmark's B-side? (yes/partial/no)",
  "overall_verdict": "strong/partial/weak/no",
  "reason": "one paragraph"
}}"""

        try:
            raw = llm.chat(
                model="claude-sonnet-4-5",
                system_prompt="You are evaluating landmark paper bridge hypotheses. Return only valid JSON.",
                user_prompt=prompt,
                temperature=0.1,
            )
            interpretability = robust_json_parse(raw)
        except Exception as e:
            logger.warning(f"  LLM audit failed: {e}")
            interpretability = {"error": str(e)}

    result = {
        "landmark": {
            "arxiv_id": lm["arxiv_id"],
            "title": lm["title"],
            "year": lm["year"],
            "a_side": lm["a_side"],
            "b_side": lm["b_side"],
            "bridge_rationale": lm["bridge_rationale"],
            "expected_anchors": lm["expected_anchors"],
        },
        "split_used": split_name,
        "eligible_anchors": eligible_anchors,
        "anchor_results": anchor_results,
        "best_anchor": best_anchor,
        "best_void_sim": round(best_sim, 4) if best_sim >= 0 else None,
        "best_void": {
            "void_id": best_void[1]["void_id"],
            "paper_a_title": id_to_title.get(best_void[1]["paper_a"]["id"], "")[:80],
            "paper_b_title": id_to_title.get(best_void[1]["paper_b"]["id"], "")[:80],
        } if best_void else None,
        "interpretability_audit": interpretability,
    }

    # Summary log
    above_null = anchor_results.get(best_anchor, {}).get("above_null_p95", False) if best_anchor else False
    verdict = (interpretability or {}).get("overall_verdict", "?")
    logger.info(f"  Best anchor: {best_anchor}  sim={round(best_sim,4)}  above_null_p95={above_null}  audit={verdict}")

    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--output", default="notes/landmark_v2_results.json")
    args = parser.parse_args()

    results = []
    for lm in LANDMARKS:
        logger.info(f"\n{'='*60}")
        logger.info(f"Landmark: {lm['arxiv_id']} ({lm['year']}) {lm['title'][:50]}")
        r = run_landmark(lm, args.top_k)
        if r:
            results.append(r)

    # Print summary
    print(f"\n{'='*80}")
    print("LANDMARK RECOVERY v2 — SUMMARY")
    print(f"{'Paper':<40} {'Eligible':>8} {'BestSim':>8} {'>p95':>6} {'Audit':>8}")
    print("-" * 80)
    for r in results:
        lm = r["landmark"]
        n_elig = len(r["eligible_anchors"])
        bsim = r["best_void_sim"] or 0
        ar = r["anchor_results"].get(r["best_anchor"], {})
        above = "✓" if ar.get("above_null_p95") else "✗"
        audit = (r.get("interpretability_audit") or {}).get("overall_verdict", "?")
        print(f"{lm['title'][:39]:<40} {n_elig:>8} {bsim:>8.4f} {above:>6} {audit:>8}")
    print(f"{'='*80}")

    out_path = Path(args.output)
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"\nSaved → {out_path}")


if __name__ == "__main__":
    main()
