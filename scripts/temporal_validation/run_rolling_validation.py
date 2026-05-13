"""
scripts/temporal_validation/run_rolling_validation.py

Run TVV validation across multiple temporal splits (rolling windows).

Splits:
  t1: train < 2010, val 2011-2015
  t2: train < 2012, val 2013-2017
  t3: train < 2014, val 2015-2019
  t4: train < 2016, val 2017-2021
  t5: train < 2018, val 2019-2023

For each split:
  1. Build train corpus embedding
  2. Find TVA voids (top-K per anchor)
  3. Build val corpus embedding
  4. Compute fill rate + role classification

Usage:
    python scripts/temporal_validation/run_rolling_validation.py --splits t5
    python scripts/temporal_validation/run_rolling_validation.py --splits t3 t4 t5
    python scripts/temporal_validation/run_rolling_validation.py --all --top-k 30
"""

import argparse
import json
from pathlib import Path

from loguru import logger

ARXIV_JSONL = Path("data/raw/arxiv/arxiv-metadata-oai-snapshot.json")
OUTPUT_DIR = Path("data/processed/tvv/rolling")

SPLITS = {
    "t1": {"train_end": 2010, "val_start": 2011, "val_end": 2016},
    "t2": {"train_end": 2012, "val_start": 2013, "val_end": 2018},
    "t3": {"train_end": 2014, "val_start": 2015, "val_end": 2020},
    "t4": {"train_end": 2016, "val_start": 2017, "val_end": 2022},
    "t5": {"train_end": 2018, "val_start": 2019, "val_end": 2024},
}

# cs.* categories most relevant to Linux/x86 TVA corpus
TARGET_CATEGORIES = {
    "cs.OS", "cs.AR", "cs.PL", "cs.SE", "cs.DC",
    "cs.NI", "cs.CR", "cs.AI", "cs.LG",
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

FILL_THRESHOLD = 0.82
BASELINE_PER_ANCHOR = 20


def paper_matches(paper: dict, categories: set) -> bool:
    return any(c in paper.get("categories", "") for c in categories)


def get_year(paper: dict) -> int:
    date = paper.get("update_date", "")
    try:
        return int(date[:4]) if date and len(date) >= 4 else 0
    except ValueError:
        return 0


def split_corpus(split_name: str, categories: set):
    """Split arXiv into train and val JSONL for a given temporal split."""
    cfg = SPLITS[split_name]
    out_dir = OUTPUT_DIR / split_name
    out_dir.mkdir(parents=True, exist_ok=True)
    train_path = out_dir / "train.jsonl"
    val_path = out_dir / "val.jsonl"

    if train_path.exists() and val_path.exists():
        logger.info(f"[{split_name}] Using cached split files")
        return train_path, val_path

    logger.info(f"[{split_name}] Splitting corpus: train<{cfg['train_end']}, val {cfg['val_start']}-{cfg['val_end']}")
    train_count = val_count = 0
    with open(ARXIV_JSONL) as src, \
         open(train_path, "w") as tf, \
         open(val_path, "w") as vf:
        for line in src:
            try:
                paper = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not paper_matches(paper, categories):
                continue
            year = get_year(paper)
            if year == 0:
                continue
            record = {
                "id": paper.get("id"),
                "title": paper.get("title", "").replace("\n", " ").strip(),
                "abstract": paper.get("abstract", "").replace("\n", " ").strip(),
                "categories": paper.get("categories"),
                "update_date": paper.get("update_date"),
                "year": year,
            }
            if year < cfg["train_end"]:
                tf.write(json.dumps(record) + "\n")
                train_count += 1
            elif cfg["val_start"] <= year <= cfg["val_end"]:
                vf.write(json.dumps(record) + "\n")
                val_count += 1

    logger.info(f"[{split_name}] Train: {train_count:,}  Val: {val_count:,}")
    return train_path, val_path


def embed_corpus(jsonl_path: Path, collection_name: str, overwrite: bool = False):
    """Embed a JSONL corpus into ChromaDB collection."""
    import chromadb
    import numpy as np
    from configs.settings import settings
    from vectordb.embedder import create_embedder
    from tqdm import tqdm

    client = chromadb.PersistentClient(path=str(settings.vectordb_path))

    if not overwrite:
        try:
            col = client.get_collection(collection_name)
            logger.info(f"Collection '{collection_name}' exists ({col.count()} docs), skipping embed")
            return col
        except Exception:
            pass

    try:
        client.delete_collection(collection_name)
    except Exception:
        pass
    col = client.create_collection(collection_name)

    embedder = create_embedder()
    papers = []
    with open(jsonl_path) as f:
        for line in f:
            papers.append(json.loads(line))

    logger.info(f"Embedding {len(papers):,} papers into '{collection_name}'...")
    BATCH = 64
    for i in tqdm(range(0, len(papers), BATCH), desc=f"Embed {collection_name}"):
        batch = papers[i:i+BATCH]
        texts = [f"{p['title']} {p['abstract']}" for p in batch]
        embs = [embedder.embed_query(t) for t in texts]
        col.add(
            ids=[p["id"] for p in batch],
            embeddings=embs,
            documents=[p["title"] for p in batch],
            metadatas=[{"title": p["title"][:200], "year": p.get("year", 0),
                        "categories": p.get("categories", "")} for p in batch],
        )
    logger.info(f"Done: {col.count()} docs in '{collection_name}'")
    return col


def find_voids(split_name: str, collection_name: str, top_k: int = 30):
    """Run TVA void search on the train collection."""
    import chromadb
    import numpy as np
    from configs.settings import settings
    from vectordb.embedder import create_embedder
    from core.deepthought_equation import DeepThoughtEquation, TechVector
    from tqdm import tqdm

    out_dir = OUTPUT_DIR / split_name
    voids_path = out_dir / "voids.jsonl"
    if voids_path.exists():
        logger.info(f"[{split_name}] Using cached voids")
        return voids_path

    client = chromadb.PersistentClient(path=str(settings.vectordb_path))
    col = client.get_collection(collection_name)
    embedder = create_embedder()

    # Fetch all embeddings
    FETCH = 5000
    total = col.count()
    ids, vecs, docs, metas = [], [], [], []
    for offset in range(0, total, FETCH):
        b = col.get(limit=FETCH, offset=offset, include=["embeddings", "documents", "metadatas"])
        ids.extend(b["ids"])
        vecs.extend(b["embeddings"])
        docs.extend(b["documents"])
        metas.extend(b["metadatas"])
    embeddings = np.array(vecs, dtype=np.float32)
    id_to_meta = {ids[i]: metas[i] for i in range(len(ids))}

    # Load train abstracts for sparse tokens
    train_path = out_dir / "train.jsonl"
    id_to_abstract = {}
    with open(train_path) as f:
        for line in f:
            p = json.loads(line)
            id_to_abstract[p["id"]] = p.get("abstract", "") or ""

    import re
    STOP = {"the","a","an","of","in","on","for","and","or","with","to","from",
            "is","are","be","by","at","as","we","our","this","that","which",
            "using","based","via","new","paper","work","method","approach",
            "system","model","algorithm","results","show","propose","present"}

    def tokens(text):
        words = re.findall(r"[a-z][a-z0-9\-]{2,}", text.lower())
        return [w for w in words if w not in STOP][:20]

    all_voids = []
    for anchor_id, anchor_text in ANCHORS.items():
        anchor_vec = np.array(embedder.embed_query(anchor_text), dtype=np.float32)
        sims = embeddings @ anchor_vec
        top_idx = sims.argsort()[::-1][:300].tolist()
        candidates = [
            TechVector(id=ids[i], vector=embeddings[i],
                       label=(docs[i] or ids[i])[:120],
                       metadata=metas[i] or {})
            for i in top_idx
        ]
        sparse = {ids[i]: tokens(id_to_abstract.get(ids[i], "")) for i in top_idx}
        target = TechVector(id="anchor", vector=anchor_vec, label=anchor_text)
        eq = DeepThoughtEquation()
        landscape = eq.find_hybrid_voids_iterative(
            v_target=target, candidates=candidates, existing=[],
            sparse_tokens=sparse,
            global_cooccurrence_checker=lambda a, b: False,
            n_select=top_k, domain=anchor_id,
        )
        for v in landscape.voids:
            cid = v.candidate.id
            if "::" in cid:
                id_a, id_b = cid.split("::", 1)
            else:
                id_a = id_b = cid
            meta_a = id_to_meta.get(id_a, {})
            meta_b = id_to_meta.get(id_b, {})
            all_voids.append({
                "split": split_name,
                "anchor_id": anchor_id,
                "void_id": cid,
                "label": v.candidate.label,
                "mmr_score": float(v.mmr_score),
                "paper_a": {"id": id_a, "title": meta_a.get("title",""), "year": meta_a.get("year")},
                "paper_b": {"id": id_b, "title": meta_b.get("title",""), "year": meta_b.get("year")},
            })

    with open(voids_path, "w") as f:
        for v in all_voids:
            f.write(json.dumps(v) + "\n")
    logger.info(f"[{split_name}] Found {len(all_voids)} voids → {voids_path}")
    return voids_path


def compute_fill_rate(split_name: str, voids_path: Path, val_collection_name: str):
    """Compute fill rate for a split."""
    import chromadb
    import numpy as np
    import random
    from configs.settings import settings
    from vectordb.embedder import create_embedder

    client = chromadb.PersistentClient(path=str(settings.vectordb_path))
    train_col = client.get_collection(f"tvv_rolling_{split_name}_train")
    val_col = client.get_collection(val_collection_name)

    # Fetch train embeddings
    FETCH = 5000
    t_ids, t_vecs = [], []
    for offset in range(0, train_col.count(), FETCH):
        b = train_col.get(limit=FETCH, offset=offset, include=["embeddings"])
        t_ids.extend(b["ids"])
        t_vecs.extend(b["embeddings"])
    train_emb = np.array(t_vecs, dtype=np.float32)
    id_to_vec = {t_ids[i]: train_emb[i] for i in range(len(t_ids))}

    # Fetch val embeddings
    v_ids, v_vecs = [], []
    for offset in range(0, val_col.count(), FETCH):
        b = val_col.get(limit=FETCH, offset=offset, include=["embeddings"])
        v_ids.extend(b["ids"])
        v_vecs.extend(b["embeddings"])
    val_emb = np.array(v_vecs, dtype=np.float32)

    def slerp(a, b):
        c = a + b; n = np.linalg.norm(c)
        return c/n if n > 0 else c

    def check(mp):
        sims = val_emb @ mp
        return sims.max() >= FILL_THRESHOLD

    voids = []
    with open(voids_path) as f:
        for line in f:
            voids.append(json.loads(line))

    filled = 0
    for v in voids:
        va = id_to_vec.get(v["paper_a"]["id"])
        vb = id_to_vec.get(v["paper_b"]["id"])
        if va is None or vb is None:
            continue
        if check(slerp(va, vb)):
            filled += 1

    # Baseline
    embedder = create_embedder()
    rng = random.Random(42)
    base_filled = base_total = 0
    for anchor_id, anchor_text in ANCHORS.items():
        av = np.array(embedder.embed_query(anchor_text), dtype=np.float32)
        sims = train_emb @ av
        top_idx = sims.argsort()[::-1][:300].tolist()
        for _ in range(BASELINE_PER_ANCHOR):
            i, j = rng.sample(top_idx, 2)
            if check(slerp(train_emb[i], train_emb[j])):
                base_filled += 1
            base_total += 1

    result = {
        "split": split_name,
        "tva": {"total": len(voids), "filled": filled,
                "fill_rate": filled/len(voids) if voids else 0},
        "baseline": {"total": base_total, "filled": base_filled,
                     "fill_rate": base_filled/base_total if base_total else 0},
        "lift": (filled/len(voids)) / (base_filled/base_total)
               if base_filled > 0 and voids else None,
    }
    out = OUTPUT_DIR / split_name / "fill_rate.json"
    with open(out, "w") as f:
        json.dump(result, f, indent=2)
    logger.info(f"[{split_name}] TVA {filled}/{len(voids)}={filled/len(voids):.1%}  "
                f"Base {base_filled}/{base_total}={base_filled/base_total:.1%}  "
                f"Lift {result['lift']:.2f}x" if result['lift'] else "")
    return result


def run_split(split_name: str, top_k: int, overwrite: bool):
    logger.info(f"\n{'='*50}")
    logger.info(f"SPLIT: {split_name}  ({SPLITS[split_name]})")
    logger.info(f"{'='*50}")

    train_path, val_path = split_corpus(split_name, TARGET_CATEGORIES)
    train_col_name = f"tvv_rolling_{split_name}_train"
    val_col_name = f"tvv_rolling_{split_name}_val"

    embed_corpus(train_path, train_col_name, overwrite=overwrite)
    embed_corpus(val_path, val_col_name, overwrite=overwrite)

    voids_path = find_voids(split_name, train_col_name, top_k=top_k)
    result = compute_fill_rate(split_name, voids_path, val_col_name)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--splits", nargs="+", choices=list(SPLITS.keys()),
                        default=["t5"])
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--top-k", type=int, default=30)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    splits = list(SPLITS.keys()) if args.all else args.splits
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    all_results = []
    for split_name in splits:
        result = run_split(split_name, args.top_k, args.overwrite)
        all_results.append(result)

    print(f"\n{'='*55}")
    print(f"{'Split':<8} {'TVA':>12} {'Baseline':>12} {'Lift':>8}")
    print("-" * 55)
    for r in all_results:
        tva = r["tva"]
        base = r["baseline"]
        lift = f"{r['lift']:.2f}x" if r["lift"] else "N/A"
        print(f"{r['split']:<8} {tva['filled']}/{tva['total']}={tva['fill_rate']:.0%}  "
              f"{base['filled']}/{base['total']}={base['fill_rate']:.0%}  {lift:>8}")
    print(f"{'='*55}")

    summary_path = OUTPUT_DIR / "rolling_summary.json"
    with open(summary_path, "w") as f:
        json.dump(all_results, f, indent=2)
    logger.info(f"Summary → {summary_path}")


if __name__ == "__main__":
    main()
