"""
scripts/temporal_validation/classify_void_fillers.py

Epistemic role classification for void fillers.

For each filled void, uses LLM to classify what the filler paper did:
  TRUE_FILL, PARTIAL_FILL, INCREMENTAL_EXTENSION, SUPPORT_EVIDENCE,
  BENCHMARK_OR_MEASUREMENT, SURVEY_OR_NAMING, REFUTATION_OR_COLLAPSE,
  FALSE_POSITIVE, UNCLEAR

Blind classification: LLM does not know if case is TVA or baseline.

Usage:
    python scripts/temporal_validation/classify_void_fillers.py
    python scripts/temporal_validation/classify_void_fillers.py --max-cases 20  # quick test
    python scripts/temporal_validation/classify_void_fillers.py --results-file data/processed/tvv/fill_rate_results_v2.json
"""

import argparse
import json
import random
from pathlib import Path

import numpy as np
from loguru import logger

VOIDS_DIR = Path("data/processed/tvv")
VAL_JSONL = Path("data/processed/tvv/arxiv_val.jsonl")
VAL_EMBEDDINGS_NPZ = Path("data/processed/tvv/val_embeddings.npz")
COLLECTION_NAME = "tvv_arxiv_train"
OUTPUT_PATH = Path("data/processed/tvv/role_classification.json")

ROLE_WEIGHTS = {
    "TRUE_FILL": 1.0,
    "PARTIAL_FILL": 0.7,
    "SUPPORT_EVIDENCE": 0.5,
    "BENCHMARK_OR_MEASUREMENT": 0.4,
    "SURVEY_OR_NAMING": 0.3,
    "INCREMENTAL_EXTENSION": 0.2,
    "REFUTATION_OR_COLLAPSE": None,  # separate event, not fill
    "FALSE_POSITIVE": 0.0,
    "UNCLEAR": None,  # exclude from scoring
}

CLASSIFICATION_PROMPT = """You are classifying the epistemic role of a candidate future paper relative to a proposed research void.

Do not judge whether the paper is generally good. Judge only what the candidate paper does with respect to the void implied by the anchor and the two source papers.

Anchor (the research direction defining this void):
{anchor}

Source paper A (year: {year_a}):
Title: {title_a}
Abstract: {abstract_a}

Source paper B (year: {year_b}):
Title: {title_b}
Abstract: {abstract_b}

Candidate future paper (year: {year_f}):
Title: {title_f}
Abstract: {abstract_f}

Classify the candidate paper into exactly one role:

- TRUE_FILL: proposes a new method, theory, mechanism, or synthesis that substantively fills the gap between the source papers under the anchor.
- PARTIAL_FILL: addresses part of the gap but does not fully resolve it.
- INCREMENTAL_EXTENSION: mainly extends one source direction without bridging the gap.
- SUPPORT_EVIDENCE: provides empirical evidence relevant to the gap but does not propose a new solution.
- BENCHMARK_OR_MEASUREMENT: introduces dataset, benchmark, metric, or evaluation method relevant to the gap.
- SURVEY_OR_NAMING: names, reviews, or frames the gap without filling it.
- REFUTATION_OR_COLLAPSE: provides evidence or argument that undermines the gap or makes the proposed direction invalid.
- FALSE_POSITIVE: semantically close but not actually relevant to the void.
- UNCLEAR: abstract is insufficient to determine.

Return strict JSON only (no markdown, no explanation outside JSON):
{{
  "role": "ONE_OF_THE_ROLES_ABOVE",
  "confidence": 0.0,
  "anchor_relevance": 0,
  "void_relevance": 0,
  "novelty_relative_to_sources": 0,
  "evidence_strength": 0,
  "reason": "one concise paragraph",
  "needs_full_text": false
}}

anchor_relevance, void_relevance, novelty_relative_to_sources, evidence_strength are integers 0-3."""


def slerp_midpoint(a, b):
    c = a + b
    n = np.linalg.norm(c)
    return c / n if n > 0 else c


def load_train_data():
    import chromadb
    from configs.settings import settings
    client = chromadb.PersistentClient(path=str(settings.vectordb_path))
    col = client.get_collection(COLLECTION_NAME)
    FETCH = 5000
    total = col.count()
    ids, vecs, docs, metas = [], [], [], []
    for offset in range(0, total, FETCH):
        b = col.get(limit=FETCH, offset=offset, include=["embeddings", "documents", "metadatas"])
        ids.extend(b["ids"])
        vecs.extend(b["embeddings"])
        docs.extend(b["documents"])
        metas.extend(b["metadatas"])
    return ids, np.array(vecs, dtype=np.float32), docs, metas


def load_val_data():
    data = np.load(VAL_EMBEDDINGS_NPZ, allow_pickle=True)
    val_ids = list(data["ids"])
    val_matrix = data["embeddings"]
    val_papers = {}
    with open(VAL_JSONL) as f:
        for line in f:
            p = json.loads(line)
            val_papers[p["id"]] = p
    return val_ids, val_matrix, val_papers


def build_cases(voids, id_to_vec, id_to_meta, id_to_abstract,
                val_ids, val_matrix, val_papers,
                fill_threshold: float = 0.82,
                n_baseline_per_anchor: int = 5,
                anchor_vecs: dict = None):
    """Build blind classification cases from TVA voids + baseline."""
    cases = []

    # TVA filled voids
    for v in voids:
        id_a = v["paper_a"]["id"]
        id_b = v["paper_b"]["id"]
        vec_a = id_to_vec.get(id_a)
        vec_b = id_to_vec.get(id_b)
        if vec_a is None or vec_b is None:
            continue
        midpoint = slerp_midpoint(vec_a, vec_b)
        val_sims = val_matrix @ midpoint
        max_sim = float(val_sims.max())
        if max_sim < fill_threshold:
            continue
        best_filler_idx = int(val_sims.argmax())
        filler_id = val_ids[best_filler_idx]
        filler = val_papers.get(filler_id, {})
        cases.append({
            "case_id": f"tva_{v['void_id'][:16]}",
            "source": "tva",
            "anchor_id": v["anchor_id"],
            "anchor": next((d for k, d in anchor_vecs.items() if k == v["anchor_id"]), ""),
            "source_a": {
                "id": id_a,
                "title": v["paper_a"]["title"],
                "abstract": id_to_abstract.get(id_a, ""),
                "year": v["paper_a"].get("year"),
            },
            "source_b": {
                "id": id_b,
                "title": v["paper_b"]["title"],
                "abstract": id_to_abstract.get(id_b, ""),
                "year": v["paper_b"].get("year"),
            },
            "filler": {
                "id": filler_id,
                "title": filler.get("title", ""),
                "abstract": filler.get("abstract", ""),
                "year": filler.get("year"),
                "sim_to_midpoint": max_sim,
            },
        })

    # Baseline cases (anchor-nearby random, matched count per anchor)
    from collections import defaultdict
    tva_by_anchor = defaultdict(int)
    for c in cases:
        tva_by_anchor[c["anchor_id"]] += 1

    rng = random.Random(99)
    all_train_ids = list(id_to_vec.keys())
    from vectordb.embedder import create_embedder
    embedder = create_embedder()

    anchor_defs = {k: v for k, v in [
        ("sched_opt", "kernel scheduler optimization and CPU affinity for multicore systems"),
        ("mm_vm", "virtual memory management and page reclamation in operating systems"),
        ("ebpf_obs", "eBPF programs for kernel tracing and system call observability"),
        ("hwsw_x86", "hardware-software co-design for x86 processor microarchitecture features"),
        ("net_io", "high-performance network I/O and packet processing in the kernel"),
        ("sync_lock", "synchronization primitives and lock-free data structures in concurrent systems"),
    ]}

    train_embeddings = np.array(list(id_to_vec.values()), dtype=np.float32)
    train_id_list = list(id_to_vec.keys())

    for anchor_id, anchor_text in anchor_defs.items():
        n_needed = max(tva_by_anchor.get(anchor_id, 0) * 2, n_baseline_per_anchor)
        anchor_vec = np.array(embedder.embed_query(anchor_text), dtype=np.float32)
        sims = train_embeddings @ anchor_vec
        top_idx = sims.argsort()[::-1][:300].tolist()
        attempts = 0
        added = 0
        while added < n_needed and attempts < n_needed * 10:
            attempts += 1
            i, j = rng.sample(top_idx, 2)
            id_a = train_id_list[i]
            id_b = train_id_list[j]
            vec_a = id_to_vec[id_a]
            vec_b = id_to_vec[id_b]
            midpoint = slerp_midpoint(vec_a, vec_b)
            val_sims = val_matrix @ midpoint
            max_sim = float(val_sims.max())
            if max_sim < fill_threshold:
                continue
            best_filler_idx = int(val_sims.argmax())
            filler_id = val_ids[best_filler_idx]
            filler = val_papers.get(filler_id, {})
            meta_a = id_to_meta.get(id_a, {})
            meta_b = id_to_meta.get(id_b, {})
            cases.append({
                "case_id": f"base_{anchor_id}_{added:03d}",
                "source": "baseline",
                "anchor_id": anchor_id,
                "anchor": anchor_text,
                "source_a": {
                    "id": id_a,
                    "title": meta_a.get("title", id_a),
                    "abstract": id_to_abstract.get(id_a, ""),
                    "year": meta_a.get("year"),
                },
                "source_b": {
                    "id": id_b,
                    "title": meta_b.get("title", id_b),
                    "abstract": id_to_abstract.get(id_b, ""),
                    "year": meta_b.get("year"),
                },
                "filler": {
                    "id": filler_id,
                    "title": filler.get("title", ""),
                    "abstract": filler.get("abstract", ""),
                    "year": filler.get("year"),
                    "sim_to_midpoint": max_sim,
                },
            })
            added += 1

    # Shuffle for blind evaluation
    rng.shuffle(cases)
    return cases


def classify_case(case: dict, llm_client) -> dict:
    prompt = CLASSIFICATION_PROMPT.format(
        anchor=case["anchor"],
        year_a=case["source_a"].get("year", "?"),
        title_a=case["source_a"]["title"][:200],
        abstract_a=(case["source_a"]["abstract"] or "")[:500],
        year_b=case["source_b"].get("year", "?"),
        title_b=case["source_b"]["title"][:200],
        abstract_b=(case["source_b"]["abstract"] or "")[:500],
        year_f=case["filler"].get("year", "?"),
        title_f=case["filler"]["title"][:200],
        abstract_f=(case["filler"]["abstract"] or "")[:500],
    )
    try:
        from configs.settings import settings
        response = llm_client.chat(
            model=settings.debate_deep_thinker_model,
            system_prompt="You are a research assistant classifying epistemic roles. Return only valid JSON.",
            user_prompt=prompt,
            temperature=0.1,
        )
        from agents.json_parser import robust_json_parse
        result = robust_json_parse(response)
        if not result or "role" not in result:
            return {"role": "UNCLEAR", "confidence": 0, "reason": "parse_failed", "raw": response[:200]}
        result["role"] = result["role"].upper().replace(" ", "_")
        if result["role"] not in ROLE_WEIGHTS and result["role"] not in {"REFUTATION_OR_COLLAPSE", "UNCLEAR"}:
            result["role"] = "UNCLEAR"
        return result
    except Exception as e:
        return {"role": "UNCLEAR", "confidence": 0, "reason": str(e)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-cases", type=int, default=None)
    parser.add_argument("--fill-threshold", type=float, default=0.82)
    parser.add_argument("--results-file", type=str, default=None)
    args = parser.parse_args()

    # Load data
    train_ids, train_embeddings, train_docs, train_metas = load_train_data()
    id_to_vec = {train_ids[i]: train_embeddings[i] for i in range(len(train_ids))}
    id_to_meta = {train_ids[i]: train_metas[i] for i in range(len(train_ids))}

    # Load train abstracts from JSONL
    train_abstracts_path = Path("data/processed/tvv/arxiv_train.jsonl")
    id_to_abstract = {}
    with open(train_abstracts_path) as f:
        for line in f:
            p = json.loads(line)
            id_to_abstract[p["id"]] = p.get("abstract", "")

    val_ids, val_matrix, val_papers = load_val_data()

    # Load TVA voids
    voids = []
    for path in sorted(VOIDS_DIR.glob("voids_*.jsonl")):
        if "summary" in path.name:
            continue
        with open(path) as f:
            for line in f:
                voids.append(json.loads(line))

    anchor_defs = {
        "sched_opt": "kernel scheduler optimization and CPU affinity for multicore systems",
        "mm_vm": "virtual memory management and page reclamation in operating systems",
        "ebpf_obs": "eBPF programs for kernel tracing and system call observability",
        "hwsw_x86": "hardware-software co-design for x86 processor microarchitecture features",
        "net_io": "high-performance network I/O and packet processing in the kernel",
        "sync_lock": "synchronization primitives and lock-free data structures in concurrent systems",
    }

    logger.info("Building blind classification cases...")
    cases = build_cases(
        voids, id_to_vec, id_to_meta, id_to_abstract,
        val_ids, val_matrix, val_papers,
        fill_threshold=args.fill_threshold,
        n_baseline_per_anchor=5,
        anchor_vecs=anchor_defs,
    )

    tva_count = sum(1 for c in cases if c["source"] == "tva")
    base_count = sum(1 for c in cases if c["source"] == "baseline")
    logger.info(f"Cases: {tva_count} TVA + {base_count} baseline = {len(cases)} total")

    if args.max_cases:
        cases = cases[:args.max_cases]
        logger.info(f"Limited to {args.max_cases} cases")

    # Run LLM classification
    from agents.llm_client import LLMClient
    llm = LLMClient()

    results = []
    for i, case in enumerate(cases):
        logger.info(f"[{i+1}/{len(cases)}] {case['case_id']} ({case['source']})")
        classification = classify_case(case, llm)
        result = {**case, "classification": classification}
        results.append(result)

    # Summary
    from collections import defaultdict, Counter
    tva_roles = Counter(r["classification"]["role"] for r in results if r["source"] == "tva")
    base_roles = Counter(r["classification"]["role"] for r in results if r["source"] == "baseline")

    print(f"\n{'='*55}")
    print("EPISTEMIC ROLE DISTRIBUTION")
    print(f"{'Role':<35} {'TVA':>6} {'Base':>6}")
    print("-" * 55)
    all_roles = sorted(set(list(tva_roles.keys()) + list(base_roles.keys())))
    for role in all_roles:
        print(f"{role:<35} {tva_roles.get(role,0):>6} {base_roles.get(role,0):>6}")

    # Role-aware scores
    tva_scores = [ROLE_WEIGHTS.get(r["classification"]["role"], 0) or 0
                  for r in results if r["source"] == "tva"
                  and r["classification"]["role"] not in {"UNCLEAR", "REFUTATION_OR_COLLAPSE"}]
    base_scores = [ROLE_WEIGHTS.get(r["classification"]["role"], 0) or 0
                   for r in results if r["source"] == "baseline"
                   and r["classification"]["role"] not in {"UNCLEAR", "REFUTATION_OR_COLLAPSE"}]

    print(f"\n{'='*55}")
    print("ROLE-AWARE FILL SCORE")
    if tva_scores:
        print(f"TVA:      mean={sum(tva_scores)/len(tva_scores):.3f}  n={len(tva_scores)}")
    if base_scores:
        print(f"Baseline: mean={sum(base_scores)/len(base_scores):.3f}  n={len(base_scores)}")
    print(f"{'='*55}\n")

    # Save
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump({"cases": results, "tva_roles": dict(tva_roles), "base_roles": dict(base_roles)}, f, indent=2)
    logger.info(f"Saved → {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
