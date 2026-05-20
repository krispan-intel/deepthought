"""
scripts/temporal_validation/er_stage2_orc.py

Stage 2: Ollivier-Ricci Curvature on localized subgraph.

For each void V = (A, B, P, G_local):
  1. Build G_local (N~328) same as Stage 1
  2. Compute ORC on G_local WITHOUT P
  3. Find shortest path A→B in G_local
  4. Record mean ORC along that path (κ_path_before)
  5. Add P with k-NN edges
  6. Recompute ORC
  7. Record κ_path_after and Δκ_path

True bridging should create new edges that increase curvature on A-B path
(negative ORC = structural hole; bridge paper should reduce bridge edge negativity).

Decision gate:
  κ (Δκ_path vs LLM fill) ≥ 0.4 → ORC is viable R surrogate
  κ < 0.2 → Stage 2 also fails → impossibility is complete for ΔR + ORC family

Usage:
    python scripts/temporal_validation/er_stage2_orc.py --split t5 --max-cases 100
"""

import argparse
import json
from pathlib import Path

import numpy as np
from loguru import logger

OUTPUT_DIR = Path("data/processed/tvv/rolling")
C1_POOL = 300
K_LOCAL = 20
K_INNER = 10
DELTA_GRID = np.linspace(-0.5, 0.5, 101)

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


def slerp(a, b):
    c = a + b; n = np.linalg.norm(c)
    return c / n if n > 0 else c


def build_nx_graph(vecs: np.ndarray, k: int):
    """Build NetworkX graph from cosine k-NN."""
    import networkx as nx
    N = len(vecs)
    sims = vecs @ vecs.T
    np.fill_diagonal(sims, -1)
    G = nx.Graph()
    G.add_nodes_from(range(N))
    for i in range(N):
        top = np.argsort(sims[i])[::-1][:k]
        for j in top:
            if sims[i, j] > 0 and j != i:
                G.add_edge(i, j, weight=float(sims[i, j]))
    return G


def compute_orc_path_curvature(G, src: int, tgt: int) -> float:
    """
    Compute mean ORC along shortest path src→tgt.
    Returns mean edge ORC on the path (or 0 if no path).
    """
    import networkx as nx
    try:
        path = nx.shortest_path(G, src, tgt, weight=None)
    except nx.NetworkXNoPath:
        return 0.0
    if len(path) < 2:
        return 0.0

    edge_orcs = []
    for u, v in zip(path[:-1], path[1:]):
        orc = G[u][v].get("ricciCurvature", 0.0)
        edge_orcs.append(orc)
    return float(np.mean(edge_orcs)) if edge_orcs else 0.0


def compute_orc_and_path(vecs: np.ndarray, src: int, tgt: int, k: int):
    """Build graph, compute ORC, return path curvature."""
    try:
        from GraphRicciCurvature.OllivierRicci import OllivierRicci
    except ImportError:
        logger.error("GraphRicciCurvature not installed. pip install GraphRicciCurvature")
        return 0.0

    G = build_nx_graph(vecs, k)
    if not G.has_node(src) or not G.has_node(tgt):
        return 0.0

    orc = OllivierRicci(G, alpha=0.5, verbose="ERROR")
    orc.compute_ricci_curvature()
    G_orc = orc.G
    return compute_orc_path_curvature(G_orc, src, tgt)


def run_stage2(split_name: str, max_cases: int = None):
    import chromadb
    from configs.settings import settings
    import time

    data = json.load(open(OUTPUT_DIR / split_name / "role_classification_v2.json"))
    cases = data["results"]
    if max_cases:
        cases = cases[:max_cases]
    logger.info(f"[{split_name}] Stage 2 ORC: {len(cases)} cases")

    client = chromadb.PersistentClient(path=str(settings.vectordb_path))
    train_col = client.get_collection(f"tvv_rolling_{split_name}_train")
    val_col   = client.get_collection(f"tvv_rolling_{split_name}_val")

    FETCH = 5000
    t_ids, t_vecs = [], []
    for offset in range(0, train_col.count(), FETCH):
        b = train_col.get(limit=FETCH, offset=offset, include=["embeddings"])
        t_ids.extend(b["ids"]); t_vecs.extend(b["embeddings"])
    train_emb = np.array(t_vecs, dtype=np.float32)
    id_to_idx = {t_ids[i]: i for i in range(len(t_ids))}

    v_ids, v_vecs = [], []
    for offset in range(0, val_col.count(), FETCH):
        b = val_col.get(limit=FETCH, offset=offset, include=["embeddings"])
        v_ids.extend(b["ids"]); v_vecs.extend(b["embeddings"])
    val_emb = np.array(v_vecs, dtype=np.float32)
    val_id_to_idx = {v_ids[i]: i for i in range(len(v_ids))}

    from vectordb.embedder import create_embedder
    embedder = create_embedder()
    anchor_vecs_all = {
        aid: np.array(embedder.embed_query(atext), dtype=np.float32)
        for aid, atext in ANCHORS.items()
    }

    results = []
    t0 = time.time()
    for idx_case, r in enumerate(cases):
        case = r["case"]
        clf  = r["classification"]
        role = clf.get("role", "UNCLEAR")
        is_fill = int(role in {"TRUE_FILL", "PARTIAL_FILL"})

        a_id = case.get("source_a", {}).get("id", "")
        b_id = case.get("source_b", {}).get("id", "")
        f_id = (case.get("filler", {}) or {}).get("id", "")
        anchor_id = case.get("anchor_id", "sched_opt")

        a_idx = id_to_idx.get(a_id)
        b_idx = id_to_idx.get(b_id)
        if a_idx is None or b_idx is None:
            continue

        a_vec = train_emb[a_idx]; b_vec = train_emb[b_idx]
        mp = slerp(a_vec, b_vec)
        av = anchor_vecs_all.get(anchor_id, anchor_vecs_all["sched_opt"])

        anchor_sims = train_emb @ av
        c1_idx = set(anchor_sims.argsort()[::-1][:C1_POOL].tolist())
        a_nbrs = set(np.argsort(train_emb @ a_vec)[::-1][:K_LOCAL].tolist())
        b_nbrs = set(np.argsort(train_emb @ b_vec)[::-1][:K_LOCAL].tolist())
        m_nbrs = set(np.argsort(train_emb @ mp)[::-1][:K_LOCAL].tolist())

        local_idx = sorted(c1_idx | a_nbrs | b_nbrs | m_nbrs)
        if a_idx not in local_idx: local_idx.append(a_idx)
        if b_idx not in local_idx: local_idx.append(b_idx)

        local_vecs = train_emb[local_idx]
        local_id_map = {orig: new for new, orig in enumerate(local_idx)}
        a_local = local_id_map[a_idx]
        b_local = local_id_map[b_idx]

        f_val_idx = val_id_to_idx.get(f_id)
        p_vec = val_emb[f_val_idx] if f_val_idx is not None else mp

        try:
            # ORC before P
            kappa_before = compute_orc_and_path(local_vecs, a_local, b_local, K_INNER)

            # ORC after P
            local_vecs_with_p = np.vstack([local_vecs, p_vec.reshape(1, -1)])
            kappa_after = compute_orc_and_path(local_vecs_with_p, a_local, b_local, K_INNER)

            delta_kappa = kappa_after - kappa_before
        except Exception as e:
            logger.debug(f"  ORC failed: {e}")
            continue

        results.append({
            "case_id": case.get("case_id", ""),
            "source": case.get("source", ""),
            "role_llm": role,
            "is_fill_llm": is_fill,
            "n_local": len(local_idx),
            "kappa_path_before": round(kappa_before, 6),
            "kappa_path_after": round(kappa_after, 6),
            "delta_kappa_path": round(delta_kappa, 6),
        })

        if (idx_case + 1) % 10 == 0:
            elapsed = time.time() - t0
            logger.info(f"  {idx_case+1}/{len(cases)}  {elapsed/len(results):.1f}s/case")

    logger.info(f"  Processed {len(results)} cases")
    if not results:
        return

    from sklearn.metrics import cohen_kappa_score
    dkappa = np.array([r["delta_kappa_path"] for r in results])
    llm_fill = np.array([r["is_fill_llm"] for r in results], dtype=int)

    best_kappa = -1
    best_delta = 0
    for delta in DELTA_GRID:
        r_orc = (dkappa >= delta).astype(int)
        if r_orc.sum() == 0 or r_orc.sum() == len(r_orc):
            continue
        try:
            k = cohen_kappa_score(llm_fill, r_orc)
            if k > best_kappa:
                best_kappa = k; best_delta = delta
        except Exception:
            pass

    non_mono = float((dkappa > 0).mean())
    from scipy.stats import pearsonr
    r_corr, p_corr = pearsonr(dkappa, llm_fill) if llm_fill.sum() > 0 else (0, 1)

    print(f"\n[{split_name}] STAGE 2: ORC PATH CURVATURE")
    print(f"  n_cases={len(results)}  n_local~{np.mean([r['n_local'] for r in results]):.0f}")
    print(f"  Δκ_path: mean={dkappa.mean():.6f}  p50={np.median(dkappa):.6f}  p90={np.percentile(dkappa,90):.6f}")
    print(f"  Δκ > 0 (bridge increased curvature): {non_mono:.1%}")
    print(f"  Pearson r(Δκ, fill): {r_corr:.4f}  p={p_corr:.4f}")
    print(f"  Best δ={best_delta:.3f}  Best κ={best_kappa:.3f}")

    if best_kappa >= 0.4:
        print(f"  ✓✓ ORC STAGE 2 SUCCESS — viable R surrogate")
    elif best_kappa >= 0.2:
        print(f"  ~ Weak ORC signal — borderline")
    else:
        print(f"  ✗ ORC also fails — impossibility result now covers ΔR + ORC")

    total_time = time.time() - t0
    print(f"  Wall clock: {total_time:.0f}s total, {total_time/len(results):.1f}s/case")

    result = {
        "split": split_name, "stage": 2, "n_cases": len(results),
        "best_delta": round(float(best_delta), 4),
        "best_kappa": round(float(best_kappa), 4),
        "non_monotone_rate": round(non_mono, 4),
        "pearson_r": round(float(r_corr), 4),
        "delta_kappa_stats": {
            "mean": round(float(dkappa.mean()), 6),
            "p50":  round(float(np.median(dkappa)), 6),
            "p90":  round(float(np.percentile(dkappa, 90)), 6),
        },
        "total_time_sec": round(total_time, 1),
        "cases": results,
    }
    out_path = OUTPUT_DIR / split_name / "er_stage2_orc.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    logger.info(f"Saved → {out_path}")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", default="t5")
    parser.add_argument("--max-cases", type=int, default=50)
    args = parser.parse_args()
    run_stage2(args.split, args.max_cases)


if __name__ == "__main__":
    main()
