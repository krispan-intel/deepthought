"""
scripts/temporal_validation/run_tvv_void_search.py

Run TVA void search on the TVV training corpus (t < 2019).
Outputs void candidates to data/processed/tvv/voids_<anchor_id>.jsonl

Usage:
    python scripts/temporal_validation/run_tvv_void_search.py
    python scripts/temporal_validation/run_tvv_void_search.py --top-k 20 --anchors 2
"""

import argparse
import json
from pathlib import Path

from loguru import logger

OUTPUT_DIR = Path("data/processed/tvv")
COLLECTION_NAME = "tvv_arxiv_train"

# Default anchors — OS/arch topics that bridge Linux corpus and arXiv
DEFAULT_ANCHORS = [
    ("sched_opt",    "kernel scheduler optimization and CPU affinity for multicore systems"),
    ("mm_vm",        "virtual memory management and page reclamation in operating systems"),
    ("ebpf_obs",     "eBPF programs for kernel tracing and system call observability"),
    ("hwsw_x86",     "hardware-software co-design for x86 processor microarchitecture features"),
    ("net_io",       "high-performance network I/O and packet processing in the kernel"),
    ("sync_lock",    "synchronization primitives and lock-free data structures in concurrent systems"),
]


def search_voids(anchor_id: str, anchor_text: str, top_k: int = 10):
    import chromadb
    import numpy as np
    from configs.settings import settings
    from vectordb.embedder import create_embedder
    from core.deepthought_equation import DeepThoughtEquation

    logger.info(f"Anchor: [{anchor_id}] {anchor_text}")

    embedder = create_embedder()
    client = chromadb.PersistentClient(path=str(settings.vectordb_path))

    try:
        col = client.get_collection(COLLECTION_NAME)
    except Exception:
        logger.error(f"Collection '{COLLECTION_NAME}' not found. Run build_tvv_corpus.py first.")
        return []

    logger.info(f"Collection: {col.count()} papers")

    # Get all embeddings in batches (ChromaDB has SQL variable limits)
    FETCH_BATCH = 5000
    total = col.count()
    ids, embeddings_list, docs, metas = [], [], [], []

    for offset in range(0, total, FETCH_BATCH):
        batch = col.get(
            limit=FETCH_BATCH,
            offset=offset,
            include=["embeddings", "documents", "metadatas"]
        )
        ids.extend(batch["ids"])
        embeddings_list.extend(batch["embeddings"])
        docs.extend(batch["documents"])
        metas.extend(batch["metadatas"])
        logger.debug(f"  fetched {len(ids)}/{total}")

    embeddings = np.array(embeddings_list, dtype=np.float32)
    logger.info(f"Loaded {len(ids)} embeddings")

    # Embed anchor
    anchor_vec = np.array(embedder.embed_query(anchor_text))

    # Build sparse tokens from title words (simple but effective for arXiv)
    import re
    STOP = {"the","a","an","of","in","on","for","and","or","with","to","from",
            "is","are","be","by","at","as","we","our","this","that","which",
            "using","based","via","new","paper","work","method","approach",
            "system","model","algorithm","results","show","propose","present"}

    def extract_tokens(text: str) -> list[str]:
        words = re.findall(r"[a-z][a-z0-9\-]{2,}", text.lower())
        return [w for w in words if w not in STOP]

    # Load abstracts for sparse tokens
    _train_jsonl = Path("data/processed/tvv/arxiv_train.jsonl")
    abstract_map: dict[str, str] = {}
    with open(_train_jsonl) as f:
        for line in f:
            p = json.loads(line)
            abstract_map[p["id"]] = p.get("abstract", "") or ""

    sparse_tokens: dict[str, list[str]] = {}
    for pid in ids:
        title = id_to_meta_temp.get(pid, {}).get("title", "") if False else ""
        abstract = abstract_map.get(pid, "")
        sparse_tokens[pid] = extract_tokens(abstract)[:20]

    # Run TVA via existing equation engine — hybrid triad (real C1-C4)
    from core.deepthought_equation import TechVector, MarginalityThresholds

    # Build id→metadata lookup early
    id_to_meta = {ids[i]: metas[i] for i in range(len(ids))}

    candidates = [
        TechVector(
            id=ids[i],
            vector=embeddings[i],
            label=(docs[i] or ids[i])[:120],
            metadata=metas[i] if metas[i] else {},
        )
        for i in range(len(ids))
    ]

    target = TechVector(
        id="anchor",
        vector=anchor_vec,
        label=anchor_text,
    )

    # C1 pre-filter: keep only top-300 most relevant candidates
    C1_POOL = 300
    sims = embeddings @ anchor_vec
    top_indices = sims.argsort()[::-1][:C1_POOL]
    filtered_candidates = [candidates[i] for i in top_indices]
    filtered_sparse = {candidates[i].id: sparse_tokens[candidates[i].id] for i in top_indices}

    logger.info(f"C1 pre-filter: {len(candidates)} → {len(filtered_candidates)} candidates")

    eq = DeepThoughtEquation()
    landscape = eq.find_hybrid_voids_iterative(
        v_target=target,
        candidates=filtered_candidates,
        existing=[],
        sparse_tokens=filtered_sparse,
        global_cooccurrence_checker=lambda a, b: False,
        n_select=top_k,
        domain=anchor_id,
    )
    voids = landscape.voids if hasattr(landscape, "voids") else []

    logger.info(f"Found {len(voids)} voids for anchor [{anchor_id}]")

    # Save results
    out_path = OUTPUT_DIR / f"voids_{anchor_id}.jsonl"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    records = []
    for v in voids:
        cand = v.candidate
        void_id = cand.id
        # VoidResult candidate id may be "A_id::B_id" (pair) or single
        if "::" in void_id:
            id_a, id_b = void_id.split("::", 1)
        else:
            id_a, id_b = void_id, void_id

        meta_a = id_to_meta.get(id_a, {})
        meta_b = id_to_meta.get(id_b, {})

        record = {
            "anchor_id": anchor_id,
            "anchor_text": anchor_text,
            "void_id": void_id,
            "label": cand.label,
            "mmr_score": float(v.mmr_score),
            "relevance_score": float(v.relevance_score),
            "domain_score": float(v.domain_score),
            "pairwise_score": float(v.pairwise_score),
            "paper_a": {
                "id": id_a,
                "title": meta_a.get("title", ""),
                "year": meta_a.get("year"),
                "categories": meta_a.get("categories", ""),
            },
            "paper_b": {
                "id": id_b,
                "title": meta_b.get("title", ""),
                "year": meta_b.get("year"),
                "categories": meta_b.get("categories", ""),
            },
        }
        records.append(record)

    with open(out_path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    logger.info(f"Saved {len(records)} voids → {out_path}")
    return records


def main():
    parser = argparse.ArgumentParser(description="TVV: find voids in t<2019 arXiv corpus")
    parser.add_argument("--top-k", type=int, default=10, help="Voids per anchor (default: 10)")
    parser.add_argument("--anchors", type=int, default=len(DEFAULT_ANCHORS),
                        help=f"Number of anchors to use (default: all {len(DEFAULT_ANCHORS)})")
    args = parser.parse_args()

    anchors = DEFAULT_ANCHORS[:args.anchors]
    all_voids = []

    for anchor_id, anchor_text in anchors:
        voids = search_voids(anchor_id, anchor_text, top_k=args.top_k)
        all_voids.extend(voids)
        logger.info(f"---")

    # Summary
    summary_path = OUTPUT_DIR / "voids_summary.jsonl"
    with open(summary_path, "w") as f:
        for v in all_voids:
            f.write(json.dumps(v) + "\n")

    logger.info(f"Total voids found: {len(all_voids)}")
    logger.info(f"Summary → {summary_path}")


if __name__ == "__main__":
    main()
