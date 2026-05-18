"""
scripts/temporal_validation/run_rolling_validation.py

Run TVV validation across multiple temporal splits (rolling windows).

Splits:
  t1: train < 2010, val 2011-2015
  t2: train < 2012, val 2013-2017
  t3: train < 2014, val 2015-2019
  t4: train < 2016, val 2017-2021
  t5: train < 2018, val 2019-2023

Fill validation — three levels:
  Level 0 (raw):          sim(midpoint, val_paper) > fill_threshold
  Level 1 (anchor-gated): Level 0 AND sim(anchor, val_paper) > anchor_threshold
  Level 2 (role-aware):   separate script (classify_void_fillers.py)

TVA and baseline use the SAME gating condition (fair comparison).

Usage:
    python scripts/temporal_validation/run_rolling_validation.py --splits t5
    python scripts/temporal_validation/run_rolling_validation.py --all --top-k 30
    python scripts/temporal_validation/run_rolling_validation.py --splits t1 t2 --top-k 30
"""

import argparse
import json
import random
from collections import defaultdict
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
ANCHOR_THRESHOLDS = [0.55, 0.60, 0.65, 0.70]  # fixed threshold sweep (diagnostic)
ANCHOR_QUANTILES = [0.80, 0.85, 0.90, 0.95]   # quantile-based (main method)
BASELINE_PER_ANCHOR = 20
C1_POOL = 300


def paper_matches(paper: dict, categories: set) -> bool:
    return any(c in paper.get("categories", "") for c in categories)


def get_year(paper: dict) -> int:
    date = paper.get("update_date", "")
    try:
        return int(date[:4]) if date and len(date) >= 4 else 0
    except ValueError:
        return 0


def split_corpus(split_name: str, categories: set):
    cfg = SPLITS[split_name]
    out_dir = OUTPUT_DIR / split_name
    out_dir.mkdir(parents=True, exist_ok=True)
    train_path = out_dir / "train.jsonl"
    val_path = out_dir / "val.jsonl"

    if train_path.exists() and val_path.exists():
        logger.info(f"[{split_name}] Using cached split files")
        return train_path, val_path

    logger.info(f"[{split_name}] Splitting: train<{cfg['train_end']}, val {cfg['val_start']}-{cfg['val_end']}")
    train_count = val_count = 0
    with open(ARXIV_JSONL) as src, open(train_path, "w") as tf, open(val_path, "w") as vf:
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
    import chromadb
    import numpy as np
    from configs.settings import settings
    from vectordb.embedder import create_embedder
    from tqdm import tqdm

    client = chromadb.PersistentClient(path=str(settings.vectordb_path))

    if not overwrite:
        try:
            col = client.get_collection(collection_name)
            logger.info(f"Collection '{collection_name}' exists ({col.count()} docs), skipping")
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
    import chromadb
    import numpy as np
    import re
    from configs.settings import settings
    from vectordb.embedder import create_embedder
    from core.deepthought_equation import DeepThoughtEquation, TechVector

    out_dir = OUTPUT_DIR / split_name
    voids_path = out_dir / "voids.jsonl"
    if voids_path.exists():
        logger.info(f"[{split_name}] Using cached voids")
        return voids_path

    client = chromadb.PersistentClient(path=str(settings.vectordb_path))
    col = client.get_collection(collection_name)
    embedder = create_embedder()

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

    train_path = out_dir / "train.jsonl"
    id_to_abstract = {}
    with open(train_path) as f:
        for line in f:
            p = json.loads(line)
            id_to_abstract[p["id"]] = p.get("abstract", "") or ""

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
        top_idx = sims.argsort()[::-1][:C1_POOL].tolist()
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
            id_a, id_b = (cid.split("::", 1) if "::" in cid else (cid, cid))
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
    logger.info(f"[{split_name}] {len(all_voids)} voids → {voids_path}")
    return voids_path


def compute_fill_rate(split_name: str, voids_path: Path, val_collection_name: str):
    import chromadb
    import numpy as np
    from configs.settings import settings
    from vectordb.embedder import create_embedder

    client = chromadb.PersistentClient(path=str(settings.vectordb_path))
    train_col = client.get_collection(f"tvv_rolling_{split_name}_train")
    val_col = client.get_collection(val_collection_name)

    FETCH = 5000
    t_ids, t_vecs = [], []
    for offset in range(0, train_col.count(), FETCH):
        b = train_col.get(limit=FETCH, offset=offset, include=["embeddings"])
        t_ids.extend(b["ids"])
        t_vecs.extend(b["embeddings"])
    train_emb = np.array(t_vecs, dtype=np.float32)
    id_to_vec = {t_ids[i]: train_emb[i] for i in range(len(t_ids))}

    v_ids, v_vecs = [], []
    for offset in range(0, val_col.count(), FETCH):
        b = val_col.get(limit=FETCH, offset=offset, include=["embeddings"])
        v_ids.extend(b["ids"])
        v_vecs.extend(b["embeddings"])
    val_emb = np.array(v_vecs, dtype=np.float32)

    def slerp(a, b):
        c = a + b; n = np.linalg.norm(c)
        return c/n if n > 0 else c

    # Embed anchors
    embedder = create_embedder()
    anchor_vecs = {
        aid: np.array(embedder.embed_query(atext), dtype=np.float32)
        for aid, atext in ANCHORS.items()
    }

    # Precompute Anchor-local quantile thresholds from train corpus
    anchor_quantile_thresholds = {}
    for aid, av in anchor_vecs.items():
        sims_train = train_emb @ av
        anchor_quantile_thresholds[aid] = {
            q: float(np.quantile(sims_train, q)) for q in ANCHOR_QUANTILES
        }
    logger.info(f"[{split_name}] Sample anchor thresholds (sched_opt): "
                + str({q: round(v, 3) for q, v in
                       anchor_quantile_thresholds.get("sched_opt", {}).items()}))

    def check_raw(mp):
        return bool((val_emb @ mp >= FILL_THRESHOLD).any())

    def check_gated_fixed(mp, av, anc_thresh):
        sims_mid = val_emb @ mp
        mask = val_emb @ av >= anc_thresh
        if not mask.any():
            return False
        return bool((sims_mid[mask] >= FILL_THRESHOLD).any())

    def check_gated_quantile(mp, aid, q):
        av = anchor_vecs[aid]
        tau = anchor_quantile_thresholds[aid][q]
        sims_mid = val_emb @ mp
        mask = val_emb @ av >= tau
        if not mask.any():
            return False
        return bool((sims_mid[mask] >= FILL_THRESHOLD).any())

    voids = []
    with open(voids_path) as f:
        for line in f:
            voids.append(json.loads(line))

    # Counters
    anchor_stats = {
        aid: {"total": 0, "raw": 0,
              **{f"g{int(t*100)}": 0 for t in ANCHOR_THRESHOLDS},
              **{f"q{int(q*100)}": 0 for q in ANCHOR_QUANTILES}}
        for aid in ANCHORS
    }

    raw_filled = 0
    gated_filled = {t: 0 for t in ANCHOR_THRESHOLDS}
    quantile_filled = {q: 0 for q in ANCHOR_QUANTILES}
    valid_voids = 0

    for v in voids:
        va = id_to_vec.get(v["paper_a"]["id"])
        vb = id_to_vec.get(v["paper_b"]["id"])
        if va is None or vb is None:
            continue
        mp = slerp(va, vb)
        av = anchor_vecs.get(v["anchor_id"])
        aid = v["anchor_id"]
        valid_voids += 1
        anchor_stats[aid]["total"] += 1

        if check_raw(mp):
            raw_filled += 1
            anchor_stats[aid]["raw"] += 1
        for t in ANCHOR_THRESHOLDS:
            if av is not None and check_gated_fixed(mp, av, t):
                gated_filled[t] += 1
                anchor_stats[aid][f"g{int(t*100)}"] += 1
        for q in ANCHOR_QUANTILES:
            if check_gated_quantile(mp, aid, q):
                quantile_filled[q] += 1
                anchor_stats[aid][f"q{int(q*100)}"] += 1

    # Baseline — same gating applied
    rng = random.Random(42)
    base_raw = 0
    base_gated = {t: 0 for t in ANCHOR_THRESHOLDS}
    base_quantile = {q: 0 for q in ANCHOR_QUANTILES}
    base_total = 0

    for anchor_id in ANCHORS:
        av = anchor_vecs[anchor_id]
        sims = train_emb @ av
        top_idx = sims.argsort()[::-1][:C1_POOL].tolist()
        for _ in range(BASELINE_PER_ANCHOR):
            i, j = rng.sample(top_idx, 2)
            mp = slerp(train_emb[i], train_emb[j])
            if check_raw(mp):
                base_raw += 1
            for t in ANCHOR_THRESHOLDS:
                if check_gated_fixed(mp, av, t):
                    base_gated[t] += 1
            for q in ANCHOR_QUANTILES:
                if check_gated_quantile(mp, anchor_id, q):
                    base_quantile[q] += 1
            base_total += 1

    def safe_lift(a, na, b, nb):
        if na == 0 or nb == 0 or b == 0:
            return None
        return round((a/na) / (b/nb), 4)

    result = {
        "split": split_name,
        "fill_threshold": FILL_THRESHOLD,
        "anchor_quantile_thresholds_sample": anchor_quantile_thresholds.get("sched_opt", {}),
        "tva": {
            "total": valid_voids,
            "raw_filled": raw_filled,
            "raw_rate": round(raw_filled/valid_voids, 4) if valid_voids else 0,
            **{f"gated_{int(t*100)}_filled": gated_filled[t] for t in ANCHOR_THRESHOLDS},
            **{f"gated_{int(t*100)}_rate": round(gated_filled[t]/valid_voids, 4) if valid_voids else 0
               for t in ANCHOR_THRESHOLDS},
            **{f"q{int(q*100)}_filled": quantile_filled[q] for q in ANCHOR_QUANTILES},
            **{f"q{int(q*100)}_rate": round(quantile_filled[q]/valid_voids, 4) if valid_voids else 0
               for q in ANCHOR_QUANTILES},
        },
        "baseline": {
            "total": base_total,
            "raw_filled": base_raw,
            "raw_rate": round(base_raw/base_total, 4) if base_total else 0,
            **{f"gated_{int(t*100)}_filled": base_gated[t] for t in ANCHOR_THRESHOLDS},
            **{f"gated_{int(t*100)}_rate": round(base_gated[t]/base_total, 4) if base_total else 0
               for t in ANCHOR_THRESHOLDS},
            **{f"q{int(q*100)}_filled": base_quantile[q] for q in ANCHOR_QUANTILES},
            **{f"q{int(q*100)}_rate": round(base_quantile[q]/base_total, 4) if base_total else 0
               for q in ANCHOR_QUANTILES},
        },
        "lifts": {
            "raw": safe_lift(raw_filled, valid_voids, base_raw, base_total),
            **{f"gated_{int(t*100)}": safe_lift(gated_filled[t], valid_voids, base_gated[t], base_total)
               for t in ANCHOR_THRESHOLDS},
            **{f"q{int(q*100)}": safe_lift(quantile_filled[q], valid_voids, base_quantile[q], base_total)
               for q in ANCHOR_QUANTILES},
        },
        "per_anchor": anchor_stats,
    }

    out = OUTPUT_DIR / split_name / "fill_rate.json"
    with open(out, "w") as f:
        json.dump(result, f, indent=2)

    # Print summary
    print(f"\n[{split_name}] fill_threshold={FILL_THRESHOLD}")
    print(f"{'Metric':<22} {'TVA':>10} {'Baseline':>10} {'Lift':>8}")
    print("-" * 55)
    tva = result["tva"]
    base = result["baseline"]
    lifts = result["lifts"]
    rows = [
        ("raw", tva["raw_filled"], tva["raw_rate"], base["raw_filled"], base["raw_rate"], lifts["raw"]),
    ]
    for t in ANCHOR_THRESHOLDS:
        k = f"gated_{int(t*100)}"
        rows.append((f"fixed≥{t}", tva[k+"_filled"], tva[k+"_rate"],
                      base[k+"_filled"], base[k+"_rate"], lifts[k]))
    for q in ANCHOR_QUANTILES:
        k = f"q{int(q*100)}"
        rows.append((f"quantile q{int(q*100)}", tva[k+"_filled"], tva[k+"_rate"],
                      base[k+"_filled"], base[k+"_rate"], lifts[k]))
    for label, tf, tr, bf, br, lift in rows:
        lift_str = f"{lift:.2f}x" if lift else "N/A"
        print(f"{label:<22} {tf}/{tva['total']}={tr:.0%}  {bf}/{base['total']}={br:.0%}  {lift_str:>8}")

    logger.info(f"[{split_name}] Results → {out}")
    return result


def run_split(split_name: str, top_k: int, overwrite: bool):
    logger.info(f"\n{'='*50}\nSPLIT: {split_name}  ({SPLITS[split_name]})\n{'='*50}")
    train_path, val_path = split_corpus(split_name, TARGET_CATEGORIES)
    train_col_name = f"tvv_rolling_{split_name}_train"
    val_col_name = f"tvv_rolling_{split_name}_val"
    embed_corpus(train_path, train_col_name, overwrite=overwrite)
    embed_corpus(val_path, val_col_name, overwrite=overwrite)
    voids_path = find_voids(split_name, train_col_name, top_k=top_k)
    return compute_fill_rate(split_name, voids_path, val_col_name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--splits", nargs="+", choices=list(SPLITS.keys()), default=["t5"])
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

    # Summary table
    print(f"\n{'='*75}")
    print(f"{'Split':<6} {'raw TVA':>9} {'raw Base':>9} {'raw Lift':>8} "
          f"{'g65 TVA':>9} {'g65 Base':>9} {'g65 Lift':>8}")
    print("-" * 75)
    for r in all_results:
        t = r["tva"]
        b = r["baseline"]
        l = r["lifts"]
        print(f"{r['split']:<6} "
              f"{t['raw_filled']}/{t['total']}={t['raw_rate']:.0%}  "
              f"{b['raw_filled']}/{b['total']}={b['raw_rate']:.0%}  "
              f"{str(l['raw'])+'x':>8}  "
              f"{t['gated_65_filled']}/{t['total']}={t['gated_65_rate']:.0%}  "
              f"{b['gated_65_filled']}/{b['total']}={b['gated_65_rate']:.0%}  "
              f"{str(l['gated_65'])+'x':>8}")
    print(f"{'='*75}")

    summary_path = OUTPUT_DIR / "rolling_summary.json"
    with open(summary_path, "w") as f:
        json.dump(all_results, f, indent=2)
    logger.info(f"Summary → {summary_path}")


if __name__ == "__main__":
    main()
