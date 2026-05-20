"""
scripts/temporal_validation/er_stage1_localized.py

Stage 1: Localized subgraph effective resistance.

Instead of full 51k train corpus, restrict to:
  N_local = top-300 C1 anchor pool + k-NN of A, B, midpoint
  (typically N ~ 500–1000 papers)

If κ ≥ 0.5 → R_eff on localized subgraph is a viable R surrogate
If κ < 0.3 → impossibility extends to localized regime

Usage:
    python scripts/temporal_validation/er_stage1_localized.py --split t5 --max-cases 100
"""

import argparse
import json
from pathlib import Path

import numpy as np
from loguru import logger

OUTPUT_DIR = Path("data/processed/tvv/rolling")
C1_POOL = 300
K_LOCAL = 20   # k-NN to add around A, B, midpoint
K_GRAPH = 10   # edges in local graph
DELTA_GRID = np.linspace(0.0, 0.5, 51)

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


def er_localized(local_vecs: np.ndarray, a_local_idx: int, b_local_idx: int,
                  p_local_idx: int, k: int, weighted: bool = True) -> tuple[float, float]:
    """
    Compute effective resistance between A and B in local subgraph,
    before and after adding P.
    Returns (r_before, r_after).
    """
    from scipy.sparse import lil_matrix, eye as speye
    from scipy.sparse.linalg import cg

    def build_er(vecs, src, tgt):
        N = len(vecs)
        sims = vecs @ vecs.T
        np.fill_diagonal(sims, -1)
        total = N + 2
        s, t = N, N + 1
        L = lil_matrix((total, total))

        for i in range(N):
            top_k = np.argsort(sims[i])[::-1][:k]
            for j in top_k:
                w = float(sims[i, j]) if weighted and sims[i, j] > 0 else (1.0 if sims[i, j] > 0 else 0)
                if w <= 0: continue
                L[i,i]+=w; L[j,j]+=w; L[i,j]-=w; L[j,i]-=w

        for n in [src]: L[s,s]+=1; L[n,n]+=1; L[s,n]-=1; L[n,s]-=1
        for n in [tgt]: L[t,t]+=1; L[n,n]+=1; L[t,n]-=1; L[n,t]-=1

        L = L.tocsr()
        b = np.zeros(total); b[s]=1; b[t]=-1
        L_reg = L + 1e-8 * speye(total, format="csr")
        x, _ = cg(L_reg, b, maxiter=2000, atol=1e-10)
        return max(float(x[s] - x[t]), 0)

    # Before: vecs without P
    vecs_before = local_vecs
    r_before = build_er(vecs_before, a_local_idx, b_local_idx)

    # After: vecs with P already included at p_local_idx
    r_after = build_er(local_vecs, a_local_idx, b_local_idx)
    # Note: P is already in local_vecs at p_local_idx — we compute R_eff
    # The "before" state needs P removed
    # Actually: compute before on local_vecs[all except p_local_idx], after on all

    # Recompute properly
    mask = [i for i in range(len(local_vecs)) if i != p_local_idx]
    vecs_excl_p = local_vecs[mask]
    # remap indices
    a_new = mask.index(a_local_idx) if a_local_idx in mask else None
    b_new = mask.index(b_local_idx) if b_local_idx in mask else None
    if a_new is None or b_new is None:
        return 0.0, 0.0
    r_before = build_er(vecs_excl_p, a_new, b_new)
    r_after  = build_er(local_vecs, a_local_idx, b_local_idx)

    return r_before, r_after


def run_stage1(split_name: str, max_cases: int = None):
    import chromadb
    from configs.settings import settings

    data = json.load(open(OUTPUT_DIR / split_name / "role_classification_v2.json"))
    cases = data["results"]
    if max_cases:
        cases = cases[:max_cases]
    logger.info(f"[{split_name}] Stage 1 localized ER: {len(cases)} cases")

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

        a_vec = train_emb[a_idx]
        b_vec = train_emb[b_idx]
        mp    = slerp(a_vec, b_vec)

        # Build localized subgraph: C1 pool + kNN(A) + kNN(B) + kNN(mp)
        av = anchor_vecs_all.get(anchor_id, anchor_vecs_all["sched_opt"])
        anchor_sims = train_emb @ av
        c1_idx = set(anchor_sims.argsort()[::-1][:C1_POOL].tolist())

        a_nbrs = set(np.argsort(train_emb @ a_vec)[::-1][:K_LOCAL].tolist())
        b_nbrs = set(np.argsort(train_emb @ b_vec)[::-1][:K_LOCAL].tolist())
        m_nbrs = set(np.argsort(train_emb @ mp)[::-1][:K_LOCAL].tolist())

        local_idx = sorted(c1_idx | a_nbrs | b_nbrs | m_nbrs)
        # Ensure A and B are in local set
        if a_idx not in local_idx: local_idx.append(a_idx)
        if b_idx not in local_idx: local_idx.append(b_idx)

        local_vecs = train_emb[local_idx]
        local_id_map = {orig: new for new, orig in enumerate(local_idx)}
        a_local = local_id_map[a_idx]
        b_local = local_id_map[b_idx]

        # Get P (filler)
        f_val_idx = val_id_to_idx.get(f_id)
        if f_val_idx is not None:
            p_vec = val_emb[f_val_idx]
        else:
            p_vec = mp  # fallback: use midpoint

        # Add P to local vecs
        local_vecs_with_p = np.vstack([local_vecs, p_vec.reshape(1, -1)])
        p_local = len(local_vecs)  # P is last

        try:
            r_before, r_after = er_localized(
                local_vecs_with_p, a_local, b_local, p_local, k=K_GRAPH
            )
            delta_r = (r_before - r_after) / max(r_before, 1e-10)
        except Exception as e:
            logger.debug(f"  ER failed: {e}")
            continue

        results.append({
            "case_id": case.get("case_id", ""),
            "source": case.get("source", ""),
            "role_llm": role,
            "is_fill_llm": is_fill,
            "n_local": len(local_idx),
            "delta_r_ratio": round(delta_r, 6),
            "r_before": round(r_before, 6),
            "r_after": round(r_after, 6),
        })

        if (idx_case + 1) % 20 == 0:
            logger.info(f"  {idx_case+1}/{len(cases)}  n_local={len(local_idx)}")

    logger.info(f"  Processed {len(results)} cases")
    if not results:
        return

    from sklearn.metrics import cohen_kappa_score
    delta_r_vals = np.array([r["delta_r_ratio"] for r in results])
    llm_fill     = np.array([r["is_fill_llm"] for r in results], dtype=int)
    n_local_mean = np.mean([r["n_local"] for r in results])

    best_kappa = -1
    best_delta = 0
    for delta in DELTA_GRID:
        r_graph = (delta_r_vals >= delta).astype(int)
        if r_graph.sum() == 0 or r_graph.sum() == len(r_graph):
            continue
        try:
            k = cohen_kappa_score(llm_fill, r_graph)
            if k > best_kappa:
                best_kappa = k; best_delta = delta
        except Exception:
            pass

    print(f"\n[{split_name}] STAGE 1: LOCALIZED SUBGRAPH ER")
    print(f"  n_cases={len(results)}  mean_n_local={n_local_mean:.0f}")
    print(f"  ΔR/R: mean={delta_r_vals.mean():.6f}  p50={np.percentile(delta_r_vals,50):.6f}  p90={np.percentile(delta_r_vals,90):.6f}")
    print(f"  LLM fill rate: {llm_fill.mean():.1%}")
    print(f"  Best δ={best_delta:.3f}  Best κ={best_kappa:.3f}")

    if best_kappa >= 0.5:
        print(f"  ✓✓ κ ≥ 0.5 — localized ER is viable R surrogate — STAGE 1 SUCCESS")
    elif best_kappa >= 0.3:
        print(f"  ~ κ ∈ [0.3,0.5) — partial signal — proceed to Stage 2 (ERC)")
    else:
        print(f"  ✗ κ < 0.3 — localized ER also fails — impossibility extends to local regime")
        print(f"  → Proceed to Stage 2 (ERC) to complete impossibility coverage")

    result = {
        "split": split_name, "stage": 1, "n_cases": len(results),
        "mean_n_local": round(n_local_mean, 1),
        "best_delta": round(float(best_delta), 4),
        "best_kappa": round(float(best_kappa), 4),
        "delta_r_stats": {
            "mean": round(float(delta_r_vals.mean()), 6),
            "p50":  round(float(np.percentile(delta_r_vals, 50)), 6),
            "p90":  round(float(np.percentile(delta_r_vals, 90)), 6),
        },
        "cases": results,
    }
    out_path = OUTPUT_DIR / split_name / "er_stage1_localized.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    logger.info(f"Saved → {out_path}")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", default="t5")
    parser.add_argument("--max-cases", type=int, default=100)
    args = parser.parse_args()
    run_stage1(args.split, args.max_cases)


if __name__ == "__main__":
    main()
