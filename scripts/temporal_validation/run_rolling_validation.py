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
ANCHOR_QUANTILES = [0.80, 0.85, 0.90, 0.95]   # pure quantile (diagnostic)
TAU_MIN_QUANTILE = 0.80  # hybrid floor = Q80 of val-anchor sims (corpus-aware, ~top 20%)
HYBRID_QUANTILES = [0.85, 0.90, 0.95]          # hybrid = max(TAU_MIN, Q_q) — main method
BASELINE_PER_ANCHOR = 20
C1_POOL = 300
DENSITY_K = 20           # k-NN neighbours for local density estimation
DENSITY_POOL_SIZE = 300  # candidate pairs precomputed per anchor for B2


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

    # Precompute Anchor-local thresholds
    # hybrid floor = Q{TAU_MIN_QUANTILE} of val-anchor sims (corpus-aware top-20% of val)
    anchor_thresholds_computed = {}
    for aid, av in anchor_vecs.items():
        sims_train = train_emb @ av
        sims_val = val_emb @ av
        # floor = Q80 of actual val similarities (top 20% of val for this anchor)
        tau_min_corpus = float(np.quantile(sims_val, TAU_MIN_QUANTILE))
        pure_q = {q: float(np.quantile(sims_train, q)) for q in ANCHOR_QUANTILES}
        # hybrid: max(corpus-aware floor, train-based quantile)
        hybrid_q = {q: float(max(tau_min_corpus, np.quantile(sims_train, q))) for q in HYBRID_QUANTILES}
        val_pass = {q: float((sims_val >= hybrid_q[q]).mean()) for q in HYBRID_QUANTILES}
        anchor_thresholds_computed[aid] = {
            "tau_min_corpus": tau_min_corpus,
            "pure_q": pure_q, "hybrid_q": hybrid_q, "val_pass_rate": val_pass
        }
    sample = anchor_thresholds_computed.get("sched_opt", {})
    logger.info(f"[{split_name}] sched_opt hybrid thresholds: "
                + str({q: round(sample.get("hybrid_q",{}).get(q,0), 3) for q in HYBRID_QUANTILES})
                + "  val pass: "
                + str({q: f"{sample.get('val_pass_rate',{}).get(q,0):.0%}" for q in HYBRID_QUANTILES}))

    def check_raw(mp):
        return bool((val_emb @ mp >= FILL_THRESHOLD).any())

    def check_gated_fixed(mp, av, anc_thresh):
        sims_mid = val_emb @ mp
        mask = val_emb @ av >= anc_thresh
        if not mask.any():
            return False
        return bool((sims_mid[mask] >= FILL_THRESHOLD).any())

    def check_gated_pure_quantile(mp, aid, q):
        av = anchor_vecs[aid]
        tau = anchor_thresholds_computed[aid]["pure_q"][q]
        sims_mid = val_emb @ mp
        mask = val_emb @ av >= tau
        if not mask.any():
            return False
        return bool((sims_mid[mask] >= FILL_THRESHOLD).any())

    def check_gated_hybrid(mp, aid, q):
        """Hybrid: max(TAU_MIN, Q_q) — main method."""
        av = anchor_vecs[aid]
        tau = anchor_thresholds_computed[aid]["hybrid_q"][q]
        sims_mid = val_emb @ mp
        mask = val_emb @ av >= tau
        if not mask.any():
            return False
        return bool((sims_mid[mask] >= FILL_THRESHOLD).any())

    def local_density(mp: "np.ndarray") -> float:
        """Mean cosine sim of mp to its DENSITY_K nearest train neighbours."""
        sims = train_emb @ mp
        k = min(DENSITY_K, len(sims))
        return float(np.sort(sims)[::-1][:k].mean())

    voids = []
    with open(voids_path) as f:
        for line in f:
            voids.append(json.loads(line))

    # Counters
    anchor_stats = {
        aid: {"total": 0, "raw": 0,
              **{f"g{int(t*100)}": 0 for t in ANCHOR_THRESHOLDS},
              **{f"pq{int(q*100)}": 0 for q in ANCHOR_QUANTILES},
              **{f"h{int(q*100)}": 0 for q in HYBRID_QUANTILES}}
        for aid in ANCHORS
    }

    # Collect (anchor_id, midpoint, density) for each valid TVA void — used later to density-match B2
    valid_void_data: list[tuple[str, "np.ndarray", float]] = []

    raw_filled = 0
    gated_filled = {t: 0 for t in ANCHOR_THRESHOLDS}
    pure_q_filled = {q: 0 for q in ANCHOR_QUANTILES}
    hybrid_filled = {q: 0 for q in HYBRID_QUANTILES}
    valid_voids = 0

    # Load train abstracts for case output
    train_path = OUTPUT_DIR / split_name / "train.jsonl"
    val_path_jsonl = OUTPUT_DIR / split_name / "val.jsonl"
    id_to_abstract_train = {}
    if train_path.exists():
        with open(train_path) as f:
            for line in f:
                p = json.loads(line)
                id_to_abstract_train[p["id"]] = p.get("abstract", "")
    id_to_abstract_val = {}
    val_papers_meta = {}
    if val_path_jsonl.exists():
        with open(val_path_jsonl) as f:
            for line in f:
                p = json.loads(line)
                id_to_abstract_val[p["id"]] = p.get("abstract", "")
                val_papers_meta[p["id"]] = p

    # Filled cases for role-aware classification
    raw_filled_cases = []        # group 1: TVA raw-filled + passed hybrid gate
    raw_only_tva_cases = []      # group 3: TVA raw-filled but FAILED hybrid gate
    near_miss_tva_cases = []     # group 5: TVA not raw-filled, sim in [0.75, FILL_THRESHOLD)

    NEAR_MISS_LOW = 0.75

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
        valid_void_data.append((aid, mp, local_density(mp)))

        val_sims = val_emb @ mp
        max_sim = float(val_sims.max())
        best_idx = int(val_sims.argmax())
        filler_id = v_ids[best_idx] if best_idx < len(v_ids) else None
        filler_meta = val_papers_meta.get(filler_id, {}) if filler_id else {}
        anchor_sim = float((val_emb[best_idx] @ av)) if av is not None and filler_id else None

        def _make_tva_case(case_source: str, gate_type: str, passed_gate):
            return {
                "case_id": f"{split_name}_{gate_type}_tva_{v['void_id'][:20]}",
                "split": split_name, "metric": gate_type, "source": case_source,
                "anchor_id": aid, "anchor": ANCHORS.get(aid, ""),
                "void_id": v["void_id"],
                "source_a": {
                    "id": v["paper_a"]["id"], "title": v["paper_a"]["title"],
                    "abstract": id_to_abstract_train.get(v["paper_a"]["id"], ""),
                    "year": v["paper_a"].get("year"),
                },
                "source_b": {
                    "id": v["paper_b"]["id"], "title": v["paper_b"]["title"],
                    "abstract": id_to_abstract_train.get(v["paper_b"]["id"], ""),
                    "year": v["paper_b"].get("year"),
                },
                "filler": {
                    "id": filler_id, "title": filler_meta.get("title", ""),
                    "abstract": id_to_abstract_val.get(filler_id, "") if filler_id else "",
                    "year": filler_meta.get("year"),
                    "sim_to_midpoint": max_sim, "sim_to_anchor": anchor_sim,
                },
                "gate": {"type": gate_type, "fill_threshold": FILL_THRESHOLD,
                         "anchor_threshold": None, "passed_anchor_gate": passed_gate},
            }

        is_raw = max_sim >= FILL_THRESHOLD
        if is_raw:
            raw_filled += 1
            anchor_stats[aid]["raw"] += 1
            # Determine whether hybrid-q90 gate also passes
            passed_hybrid = check_gated_hybrid(mp, aid, 0.90)
            if passed_hybrid:
                raw_filled_cases.append(_make_tva_case("tva", "raw", True))
            else:
                raw_only_tva_cases.append(_make_tva_case("tva_raw_only_failed_gate", "raw_failed_gate", False))
        elif NEAR_MISS_LOW <= max_sim < FILL_THRESHOLD:
            near_miss_tva_cases.append(_make_tva_case("tva_near_miss", "near_miss", None))

        for t in ANCHOR_THRESHOLDS:
            if av is not None and check_gated_fixed(mp, av, t):
                gated_filled[t] += 1
                anchor_stats[aid][f"g{int(t*100)}"] += 1
        for q in ANCHOR_QUANTILES:
            if check_gated_pure_quantile(mp, aid, q):
                pure_q_filled[q] += 1
                anchor_stats[aid][f"pq{int(q*100)}"] += 1
        for q in HYBRID_QUANTILES:
            if check_gated_hybrid(mp, aid, q):
                hybrid_filled[q] += 1
                anchor_stats[aid][f"h{int(q*100)}"] += 1

    # Baseline — same gating
    rng = random.Random(42)
    base_raw = 0
    base_gated = {t: 0 for t in ANCHOR_THRESHOLDS}
    base_pure_q = {q: 0 for q in ANCHOR_QUANTILES}
    base_hybrid = {q: 0 for q in HYBRID_QUANTILES}
    base_total = 0
    base_filled_cases = []      # group 2: baseline (B1) raw-filled + passed hybrid gate
    base_raw_only_cases = []    # group 4: baseline (B1) raw-filled but FAILED hybrid gate
    base_case_counter = 0
    base_raw_only_counter = 0

    for anchor_id in ANCHORS:
        av = anchor_vecs[anchor_id]
        sims = train_emb @ av
        top_idx = sims.argsort()[::-1][:C1_POOL].tolist()
        for _ in range(BASELINE_PER_ANCHOR):
            i, j = rng.sample(top_idx, 2)
            mp = slerp(train_emb[i], train_emb[j])
            val_sims = val_emb @ mp
            max_sim = float(val_sims.max())
            if check_raw(mp):
                base_raw += 1
                best_idx = int(val_sims.argmax())
                filler_id = v_ids[best_idx] if best_idx < len(v_ids) else None
                filler_meta = val_papers_meta.get(filler_id, {}) if filler_id else {}
                anchor_sim_f = float(val_emb[best_idx] @ av) if filler_id else None
                passed_hybrid_b1 = check_gated_hybrid(mp, anchor_id, 0.90)
                _base_case = {
                    "split": split_name, "metric": "raw",
                    "anchor_id": anchor_id, "anchor": ANCHORS.get(anchor_id, ""),
                    "void_id": f"base_{anchor_id}_{i}_{j}",
                    "source_a": {
                        "id": t_ids[i] if i < len(t_ids) else "",
                        "title": "", "abstract": id_to_abstract_train.get(t_ids[i] if i < len(t_ids) else "", ""),
                        "year": None,
                    },
                    "source_b": {
                        "id": t_ids[j] if j < len(t_ids) else "",
                        "title": "", "abstract": id_to_abstract_train.get(t_ids[j] if j < len(t_ids) else "", ""),
                        "year": None,
                    },
                    "filler": {
                        "id": filler_id,
                        "title": filler_meta.get("title", ""),
                        "abstract": id_to_abstract_val.get(filler_id, "") if filler_id else "",
                        "year": filler_meta.get("year"),
                        "sim_to_midpoint": max_sim,
                        "sim_to_anchor": anchor_sim_f,
                    },
                    "gate": {"type": "raw", "fill_threshold": FILL_THRESHOLD,
                             "anchor_threshold": None, "passed_anchor_gate": passed_hybrid_b1},
                }
                if passed_hybrid_b1:
                    _base_case["case_id"] = f"{split_name}_raw_base_{anchor_id}_{base_case_counter:03d}"
                    _base_case["source"] = "baseline"
                    base_filled_cases.append(_base_case)
                    base_case_counter += 1
                else:
                    _base_case["case_id"] = f"{split_name}_raw_base_fo_{anchor_id}_{base_raw_only_counter:03d}"
                    _base_case["source"] = "baseline_raw_only_failed_gate"
                    base_raw_only_cases.append(_base_case)
                    base_raw_only_counter += 1
            for t in ANCHOR_THRESHOLDS:
                if check_gated_fixed(mp, av, t):
                    base_gated[t] += 1
            for q in ANCHOR_QUANTILES:
                if check_gated_pure_quantile(mp, anchor_id, q):
                    base_pure_q[q] += 1
            for q in HYBRID_QUANTILES:
                if check_gated_hybrid(mp, anchor_id, q):
                    base_hybrid[q] += 1
            base_total += 1

    # Baseline B2 — density-matched (one pair per TVA void, matched on local train density)
    # For each TVA void, precompute DENSITY_POOL_SIZE candidate pairs from C1 pool of its anchor,
    # score each by |density(pair) - density(void)|, pick the closest.
    b2_raw = 0
    b2_gated = {t: 0 for t in ANCHOR_THRESHOLDS}
    b2_pure_q = {q: 0 for q in ANCHOR_QUANTILES}
    b2_hybrid = {q: 0 for q in HYBRID_QUANTILES}
    b2_total = 0
    b2_filled_cases = []
    b2_case_counter = 0

    # Precompute per-anchor C1 pool indices (same as B1)
    anchor_c1_idx = {}
    for anchor_id in ANCHORS:
        av = anchor_vecs[anchor_id]
        sims = train_emb @ av
        anchor_c1_idx[anchor_id] = sims.argsort()[::-1][:C1_POOL].tolist()

    rng_b2 = random.Random(99)
    for (aid, tva_mp, tva_density) in valid_void_data:
        c1_idx = anchor_c1_idx[aid]
        # Generate DENSITY_POOL_SIZE candidate pair midpoints and their densities
        sample_size = min(DENSITY_POOL_SIZE, len(c1_idx) * (len(c1_idx) - 1) // 2)
        pairs = [rng_b2.sample(c1_idx, 2) for _ in range(sample_size)]
        best_pair = None
        best_diff = float("inf")
        for i, j in pairs:
            mp_b2 = slerp(train_emb[i], train_emb[j])
            d = local_density(mp_b2)
            diff = abs(d - tva_density)
            if diff < best_diff:
                best_diff = diff
                best_pair = (i, j, mp_b2)

        if best_pair is None:
            continue
        bi, bj, mp = best_pair
        av = anchor_vecs[aid]
        b2_total += 1
        val_sims = val_emb @ mp
        max_sim = float(val_sims.max())

        if check_raw(mp):
            b2_raw += 1
            best_idx = int(val_sims.argmax())
            filler_id = v_ids[best_idx] if best_idx < len(v_ids) else None
            filler_meta = val_papers_meta.get(filler_id, {}) if filler_id else {}
            anchor_sim_f = float(val_emb[best_idx] @ av) if filler_id else None
            b2_filled_cases.append({
                "case_id": f"{split_name}_raw_b2_{aid}_{b2_case_counter:03d}",
                "split": split_name, "metric": "raw", "source": "b2_density",
                "anchor_id": aid, "anchor": ANCHORS.get(aid, ""),
                "void_id": f"b2_{aid}_{bi}_{bj}",
                "density_match": {"tva_density": round(tva_density, 4), "b2_density": round(local_density(mp), 4), "delta": round(best_diff, 4)},
                "source_a": {
                    "id": t_ids[bi] if bi < len(t_ids) else "",
                    "title": "", "abstract": id_to_abstract_train.get(t_ids[bi] if bi < len(t_ids) else "", ""),
                    "year": None,
                },
                "source_b": {
                    "id": t_ids[bj] if bj < len(t_ids) else "",
                    "title": "", "abstract": id_to_abstract_train.get(t_ids[bj] if bj < len(t_ids) else "", ""),
                    "year": None,
                },
                "filler": {
                    "id": filler_id,
                    "title": filler_meta.get("title", ""),
                    "abstract": id_to_abstract_val.get(filler_id, "") if filler_id else "",
                    "year": filler_meta.get("year"),
                    "sim_to_midpoint": max_sim,
                    "sim_to_anchor": anchor_sim_f,
                },
                "gate": {"type": "raw", "fill_threshold": FILL_THRESHOLD,
                         "anchor_threshold": None, "passed_anchor_gate": None},
            })
            b2_case_counter += 1
        for t in ANCHOR_THRESHOLDS:
            if check_gated_fixed(mp, av, t):
                b2_gated[t] += 1
        for q in ANCHOR_QUANTILES:
            if check_gated_pure_quantile(mp, aid, q):
                b2_pure_q[q] += 1
        for q in HYBRID_QUANTILES:
            if check_gated_hybrid(mp, aid, q):
                b2_hybrid[q] += 1

    # Save filled cases for role-aware classification (5-group sampling)
    # Group 1: tva                         — TVA raw-filled + passed hybrid gate
    # Group 2: baseline                    — B1 raw-filled + passed hybrid gate
    # Group 3: tva_raw_only_failed_gate    — TVA raw-filled but failed hybrid gate
    # Group 4: baseline_raw_only_failed_gate — B1 raw-filled but failed hybrid gate
    # Group 5: tva_near_miss               — TVA not filled, sim in [0.75, threshold)
    all_cases = (raw_filled_cases + base_filled_cases + b2_filled_cases
                 + raw_only_tva_cases + base_raw_only_cases + near_miss_tva_cases)
    random.Random(42).shuffle(all_cases)  # blind shuffle
    cases_path = OUTPUT_DIR / split_name / "filled_cases_raw.jsonl"
    with open(cases_path, "w") as f:
        for c in all_cases:
            f.write(json.dumps(c) + "\n")
    logger.info(
        f"[{split_name}] Cases saved → {cases_path}\n"
        f"  G1 tva(gated)={len(raw_filled_cases)}  G2 b1(gated)={len(base_filled_cases)}"
        f"  G3 tva(raw_only)={len(raw_only_tva_cases)}  G4 b1(raw_only)={len(base_raw_only_cases)}"
        f"  G5 near_miss={len(near_miss_tva_cases)}  B2={len(b2_filled_cases)}"
    )

    def safe_lift(a, na, b, nb):
        if na == 0 or nb == 0 or b == 0:
            return None
        return round((a/na) / (b/nb), 4)

    def rates(d, n):
        return {k: round(v/n, 4) if n else 0 for k, v in d.items()}

    result = {
        "split": split_name,
        "fill_threshold": FILL_THRESHOLD,
        "tau_min_quantile": TAU_MIN_QUANTILE,
        "anchor_thresholds_sample": {
            aid: anchor_thresholds_computed[aid]["hybrid_q"]
            for aid in list(ANCHORS.keys())[:3]
        },
        "anchor_val_pass_rate_sample": {
            aid: anchor_thresholds_computed[aid]["val_pass_rate"]
            for aid in list(ANCHORS.keys())[:3]
        },
        "tva": {
            "total": valid_voids,
            "raw": {"filled": raw_filled, "rate": round(raw_filled/valid_voids,4) if valid_voids else 0},
            "fixed": {int(t*100): {"filled": gated_filled[t],
                       "rate": round(gated_filled[t]/valid_voids,4) if valid_voids else 0}
                      for t in ANCHOR_THRESHOLDS},
            "pure_q": {int(q*100): {"filled": pure_q_filled[q],
                        "rate": round(pure_q_filled[q]/valid_voids,4) if valid_voids else 0}
                       for q in ANCHOR_QUANTILES},
            "hybrid": {int(q*100): {"filled": hybrid_filled[q],
                        "rate": round(hybrid_filled[q]/valid_voids,4) if valid_voids else 0}
                       for q in HYBRID_QUANTILES},
        },
        "baseline_b1": {
            "total": base_total,
            "raw": {"filled": base_raw, "rate": round(base_raw/base_total,4) if base_total else 0},
            "fixed": {int(t*100): {"filled": base_gated[t],
                       "rate": round(base_gated[t]/base_total,4) if base_total else 0}
                      for t in ANCHOR_THRESHOLDS},
            "pure_q": {int(q*100): {"filled": base_pure_q[q],
                        "rate": round(base_pure_q[q]/base_total,4) if base_total else 0}
                       for q in ANCHOR_QUANTILES},
            "hybrid": {int(q*100): {"filled": base_hybrid[q],
                        "rate": round(base_hybrid[q]/base_total,4) if base_total else 0}
                       for q in HYBRID_QUANTILES},
        },
        "baseline_b2_density": {
            "total": b2_total,
            "raw": {"filled": b2_raw, "rate": round(b2_raw/b2_total,4) if b2_total else 0},
            "fixed": {int(t*100): {"filled": b2_gated[t],
                       "rate": round(b2_gated[t]/b2_total,4) if b2_total else 0}
                      for t in ANCHOR_THRESHOLDS},
            "pure_q": {int(q*100): {"filled": b2_pure_q[q],
                        "rate": round(b2_pure_q[q]/b2_total,4) if b2_total else 0}
                       for q in ANCHOR_QUANTILES},
            "hybrid": {int(q*100): {"filled": b2_hybrid[q],
                        "rate": round(b2_hybrid[q]/b2_total,4) if b2_total else 0}
                       for q in HYBRID_QUANTILES},
        },
        "lifts_b1": {
            "raw": safe_lift(raw_filled, valid_voids, base_raw, base_total),
            **{f"fixed_{int(t*100)}": safe_lift(gated_filled[t], valid_voids, base_gated[t], base_total)
               for t in ANCHOR_THRESHOLDS},
            **{f"pq{int(q*100)}": safe_lift(pure_q_filled[q], valid_voids, base_pure_q[q], base_total)
               for q in ANCHOR_QUANTILES},
            **{f"h{int(q*100)}": safe_lift(hybrid_filled[q], valid_voids, base_hybrid[q], base_total)
               for q in HYBRID_QUANTILES},
        },
        "lifts_b2": {
            "raw": safe_lift(raw_filled, valid_voids, b2_raw, b2_total),
            **{f"fixed_{int(t*100)}": safe_lift(gated_filled[t], valid_voids, b2_gated[t], b2_total)
               for t in ANCHOR_THRESHOLDS},
            **{f"pq{int(q*100)}": safe_lift(pure_q_filled[q], valid_voids, b2_pure_q[q], b2_total)
               for q in ANCHOR_QUANTILES},
            **{f"h{int(q*100)}": safe_lift(hybrid_filled[q], valid_voids, b2_hybrid[q], b2_total)
               for q in HYBRID_QUANTILES},
        },
        "per_anchor": anchor_stats,
    }

    out = OUTPUT_DIR / split_name / "fill_rate.json"
    with open(out, "w") as f:
        json.dump(result, f, indent=2)

    # Print summary
    tva = result["tva"]
    b1 = result["baseline_b1"]
    b2 = result["baseline_b2_density"]
    l1 = result["lifts_b1"]
    l2 = result["lifts_b2"]
    nt, nb1, nb2 = tva["total"], b1["total"], b2["total"]
    print(f"\n[{split_name}] fill_threshold={FILL_THRESHOLD}  tau_min_q={TAU_MIN_QUANTILE}")
    print(f"{'Gate':<24} {'TVA':>8} {'B1(hot)':>9} {'L1':>6} {'B2(dens)':>9} {'L2':>6}")
    print("-" * 67)
    def row(label, tf, tr, b1f, b1r, l1v, b2f, b2r, l2v):
        l1s = f"{l1v:.2f}x" if l1v else "N/A"
        l2s = f"{l2v:.2f}x" if l2v else "N/A"
        print(f"{label:<24} {tf}/{nt}={tr:.0%}  {b1f}/{nb1}={b1r:.0%} {l1s:>6}  {b2f}/{nb2}={b2r:.0%} {l2s:>6}")
    row("raw",
        tva["raw"]["filled"], tva["raw"]["rate"],
        b1["raw"]["filled"], b1["raw"]["rate"], l1["raw"],
        b2["raw"]["filled"], b2["raw"]["rate"], l2["raw"])
    for t in ANCHOR_THRESHOLDS:
        k = int(t*100)
        row(f"fixed≥{t}",
            tva["fixed"][k]["filled"], tva["fixed"][k]["rate"],
            b1["fixed"][k]["filled"], b1["fixed"][k]["rate"], l1[f"fixed_{k}"],
            b2["fixed"][k]["filled"], b2["fixed"][k]["rate"], l2[f"fixed_{k}"])
    for q in HYBRID_QUANTILES:
        k = int(q*100)
        row(f"hybrid(Q{k})",
            tva["hybrid"][k]["filled"], tva["hybrid"][k]["rate"],
            b1["hybrid"][k]["filled"], b1["hybrid"][k]["rate"], l1[f"h{k}"],
            b2["hybrid"][k]["filled"], b2["hybrid"][k]["rate"], l2[f"h{k}"])
    # val pass rate for main hybrid
    print(f"\n  Val pass rates (hybrid q90):")
    for aid in list(ANCHORS.keys())[:5]:
        vpr = anchor_thresholds_computed[aid]["val_pass_rate"].get(0.90, 0)
        tau = anchor_thresholds_computed[aid]["hybrid_q"].get(0.90, 0)
        print(f"    {aid:<15} τ={tau:.3f}  pass={vpr:.0%}")

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
    print(f"\n{'='*90}")
    print(f"{'Split':<6} {'TVA raw':>8} {'B1 raw':>7} {'L1raw':>6} {'B2 raw':>7} {'L2raw':>6} "
          f"{'TVA h90':>8} {'B1 h90':>7} {'L1h90':>6} {'B2 h90':>7} {'L2h90':>6}")
    print("-" * 90)
    for r in all_results:
        t = r["tva"]
        b1 = r["baseline_b1"]
        b2 = r["baseline_b2_density"]
        l1 = r["lifts_b1"]
        l2 = r["lifts_b2"]
        nt = t["total"]; nb1 = b1["total"]; nb2 = b2["total"]
        th90 = t["hybrid"].get(90, {})
        b1h90 = b1["hybrid"].get(90, {})
        b2h90 = b2["hybrid"].get(90, {})
        l1r = l1.get("raw"); l2r = l2.get("raw")
        l1h = l1.get("h90"); l2h = l2.get("h90")
        fmt = lambda v: f"{v:.2f}x" if v else "N/A"
        print(f"{r['split']:<6} "
              f"{t['raw']['filled']}/{nt}={t['raw']['rate']:.0%}  "
              f"{b1['raw']['filled']}/{nb1}={b1['raw']['rate']:.0%} {fmt(l1r):>6}  "
              f"{b2['raw']['filled']}/{nb2}={b2['raw']['rate']:.0%} {fmt(l2r):>6}  "
              f"{th90.get('filled',0)}/{nt}={th90.get('rate',0):.0%}  "
              f"{b1h90.get('filled',0)}/{nb1}={b1h90.get('rate',0):.0%} {fmt(l1h):>6}  "
              f"{b2h90.get('filled',0)}/{nb2}={b2h90.get('rate',0):.0%} {fmt(l2h):>6}")
    print(f"{'='*90}")

    summary_path = OUTPUT_DIR / "rolling_summary.json"
    with open(summary_path, "w") as f:
        json.dump(all_results, f, indent=2)
    logger.info(f"Summary → {summary_path}")


if __name__ == "__main__":
    main()
