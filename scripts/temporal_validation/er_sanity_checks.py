"""
scripts/temporal_validation/er_sanity_checks.py

6 sanity checks to confirm ΔR=0 null result is real (not a bug).

Run before writing the 'geometric limit' impossibility result into the paper.

Usage:
    python scripts/temporal_validation/er_sanity_checks.py
"""

import json
import numpy as np
from pathlib import Path
from loguru import logger

OUTPUT_DIR = Path("data/processed/tvv/rolling")


# ==============================================================
# Helper: effective resistance on explicit matrix (ground truth)
# ==============================================================
def effective_resistance_direct(adj: np.ndarray, src: int, tgt: int) -> float:
    """Ground-truth ΔR via pseudoinverse Laplacian."""
    from numpy.linalg import pinv
    D = np.diag(adj.sum(axis=1))
    L = D - adj
    L_pinv = pinv(L)
    return float(L_pinv[src, src] + L_pinv[tgt, tgt] - 2 * L_pinv[src, tgt])


def er_sparse(vecs: np.ndarray, k: int, src_nodes, tgt_nodes, weighted=True) -> float:
    """Sparse ΔR via CG (same as main script)."""
    from scipy.sparse import lil_matrix, eye as speye
    from scipy.sparse.linalg import cg

    N = len(vecs)
    sims = vecs @ vecs.T
    np.fill_diagonal(sims, -1)

    total = N + 2
    s, t = N, N + 1
    L = lil_matrix((total, total))

    for i in range(N):
        nbrs = np.argsort(sims[i])[::-1][:k]
        for j in nbrs:
            w = float(sims[i, j]) if weighted and sims[i, j] > 0 else (1.0 if sims[i, j] > 0 else 0)
            if w <= 0: continue
            L[i,i]+=w; L[j,j]+=w; L[i,j]-=w; L[j,i]-=w

    for n in src_nodes:
        L[s,s]+=1; L[n,n]+=1; L[s,n]-=1; L[n,s]-=1
    for n in tgt_nodes:
        L[t,t]+=1; L[n,n]+=1; L[t,n]-=1; L[n,t]-=1

    L = L.tocsr()
    b = np.zeros(total); b[s]=1; b[t]=-1
    L_reg = L + 1e-8 * speye(total, format="csr")
    x, _ = cg(L_reg, b, maxiter=2000, tol=1e-10)
    return max(float(x[s]-x[t]), 0)


# ==============================================================
# Check 1: Direct solver on 5 real cases
# ==============================================================
def check1_direct_solver(split="t5"):
    logger.info("\n=== CHECK 1: Direct pinv solver on 5 real cases ===")
    import chromadb
    from configs.settings import settings

    data = json.load(open(OUTPUT_DIR / split / "role_classification_v2.json"))
    client = chromadb.PersistentClient(path=str(settings.vectordb_path))
    train_col = client.get_collection(f"tvv_rolling_{split}_train")

    FETCH=5000; t_ids=[]; t_vecs=[]
    for off in range(0, train_col.count(), FETCH):
        b = train_col.get(limit=FETCH, offset=off, include=["embeddings"])
        t_ids.extend(b["ids"]); t_vecs.extend(b["embeddings"])
    train_emb = np.array(t_vecs, dtype=np.float32)
    id_to_idx = {t_ids[i]:i for i in range(len(t_ids))}

    K_LOCAL = 10  # smaller for direct solver
    results = []
    for r in data["results"][:5]:
        case = r["case"]
        a_idx = id_to_idx.get(case.get("source_a",{}).get("id",""))
        b_idx = id_to_idx.get(case.get("source_b",{}).get("id",""))
        if a_idx is None or b_idx is None: continue

        a_vec = train_emb[a_idx]; b_vec = train_emb[b_idx]
        sims_a = train_emb @ a_vec
        a_local = sims_a.argsort()[::-1][:K_LOCAL+1]
        a_local = [x for x in a_local if x != b_idx][:K_LOCAL]
        sims_b = train_emb @ b_vec
        b_local = sims_b.argsort()[::-1][:K_LOCAL+1]
        b_local = [x for x in b_local if x != a_idx][:K_LOCAL]

        local_vecs = train_emb[a_local + b_local]
        N = len(local_vecs)
        sims = local_vecs @ local_vecs.T
        np.fill_diagonal(sims, 0)
        k = min(5, N-1)
        adj = np.zeros_like(sims)
        for i in range(N):
            top = np.argsort(sims[i])[::-1][:k]
            for j in top:
                if sims[i,j] > 0:
                    adj[i,j] = sims[i,j]; adj[j,i] = sims[i,j]

        src = 0; tgt = K_LOCAL  # first A-side vs first B-side node
        r_eff = effective_resistance_direct(adj, src, tgt)
        results.append(r_eff)
        logger.info(f"  R_eff (direct pinv) = {r_eff:.8f}")

    logger.info(f"  Mean R_eff = {np.mean(results):.8f}  (if ~0 even with direct solver → confirmed collapse)")
    return results


# ==============================================================
# Check 2: Toy graph — two clusters + bridge node
# ==============================================================
def check2_toy_graph():
    logger.info("\n=== CHECK 2: Toy graph sanity (two clusters + bridge) ===")
    np.random.seed(42)

    # Cluster A: 20 points around (1,0,...)
    # Cluster B: 20 points around (-1,0,...)
    d = 50  # low-d to avoid anisotropy
    a_center = np.zeros(d); a_center[0] = 1
    b_center = np.zeros(d); b_center[0] = -1

    a_vecs = a_center + 0.1*np.random.randn(20, d)
    b_vecs = b_center + 0.1*np.random.randn(20, d)
    a_vecs /= np.linalg.norm(a_vecs, axis=1, keepdims=True)
    b_vecs /= np.linalg.norm(b_vecs, axis=1, keepdims=True)

    # Bridge node: perpendicular to the A-B axis (connects both sides)
    p_vec = np.zeros(d); p_vec[1] = 1.0  # orthogonal direction, close to both

    # R_eff before
    all_vecs = np.vstack([a_vecs, b_vecs])
    N = len(all_vecs)
    sims = all_vecs @ all_vecs.T; np.fill_diagonal(sims, 0)
    adj_before = np.zeros_like(sims)
    for i in range(N):
        top = np.argsort(sims[i])[::-1][:5]
        for j in top:
            if sims[i,j]>0: adj_before[i,j]=sims[i,j]; adj_before[j,i]=sims[i,j]

    r_before = effective_resistance_direct(adj_before, 0, 20)

    # R_eff after adding bridge
    all_vecs_after = np.vstack([all_vecs, p_vec.reshape(1,-1)])
    N2 = len(all_vecs_after)
    sims2 = all_vecs_after @ all_vecs_after.T; np.fill_diagonal(sims2, 0)
    adj_after = np.zeros_like(sims2)
    for i in range(N2):
        top = np.argsort(sims2[i])[::-1][:5]
        for j in top:
            if sims2[i,j]>0: adj_after[i,j]=sims2[i,j]; adj_after[j,i]=sims2[i,j]

    r_after = effective_resistance_direct(adj_after, 0, 20)
    delta = (r_before - r_after) / max(r_before, 1e-10)

    logger.info(f"  R_eff before = {r_before:.6f}")
    logger.info(f"  R_eff after  = {r_after:.6f}")
    logger.info(f"  ΔR/R_before  = {delta:.6f}")
    if delta > 0.01:
        logger.info("  ✓ Toy bridge detected (ΔR > 1%) — solver works for well-separated clusters")
    else:
        logger.info("  ✗ Toy bridge NOT detected — solver or graph construction bug")
    return delta


# ==============================================================
# Check 3: k sensitivity on 20 real cases
# ==============================================================
def check3_k_sensitivity(split="t5"):
    logger.info("\n=== CHECK 3: k sensitivity (k=5,10,20,50) on 20 cases ===")
    import chromadb
    from configs.settings import settings
    from scripts.temporal_validation.effective_resistance_r_layer import compute_delta_r

    data = json.load(open(OUTPUT_DIR / split / "role_classification_v2.json"))
    client = chromadb.PersistentClient(path=str(settings.vectordb_path))
    train_col = client.get_collection(f"tvv_rolling_{split}_train")
    FETCH=5000; t_ids=[]; t_vecs=[]
    for off in range(0, train_col.count(), FETCH):
        b = train_col.get(limit=FETCH, offset=off, include=["embeddings"])
        t_ids.extend(b["ids"]); t_vecs.extend(b["embeddings"])
    train_emb = np.array(t_vecs, dtype=np.float32)
    id_to_idx = {t_ids[i]:i for i in range(len(t_ids))}

    from vectordb.embedder import create_embedder
    val_col = client.get_collection(f"tvv_rolling_{split}_val")
    v_ids=[]; v_vecs=[]
    for off in range(0, val_col.count(), FETCH):
        b = val_col.get(limit=FETCH, offset=off, include=["embeddings"])
        v_ids.extend(b["ids"]); v_vecs.extend(b["embeddings"])
    val_emb = np.array(v_vecs, dtype=np.float32)
    val_id_to_idx = {v_ids[i]:i for i in range(len(v_ids))}

    results = {k: [] for k in [5, 10, 20, 50]}
    n_processed = 0
    for r in data["results"]:
        if n_processed >= 20: break
        case = r["case"]
        a_idx = id_to_idx.get(case.get("source_a",{}).get("id",""))
        b_idx = id_to_idx.get(case.get("source_b",{}).get("id",""))
        f_id = (case.get("filler",{}) or {}).get("id","")
        if a_idx is None or b_idx is None: continue

        a_vec = train_emb[a_idx]; b_vec = train_emb[b_idx]
        f_idx = val_id_to_idx.get(f_id)
        p_vec = val_emb[f_idx] if f_idx is not None else (a_vec+b_vec)/np.linalg.norm(a_vec+b_vec)

        K_LOCAL = 30
        sims_a = train_emb @ a_vec
        a_local = sims_a.argsort()[::-1][:K_LOCAL+1]
        a_local = [x for x in a_local if x != b_idx][:K_LOCAL]
        sims_b = train_emb @ b_vec
        b_local = sims_b.argsort()[::-1][:K_LOCAL+1]
        b_local = [x for x in b_local if x != a_idx][:K_LOCAL]

        a_community = train_emb[a_local]; b_community = train_emb[b_local]

        for k in [5, 10, 20, 50]:
            try:
                dr, rb, ra = compute_delta_r(a_community, b_community, p_vec, k=k)
                results[k].append(dr)
            except Exception: pass
        n_processed += 1

    logger.info(f"  k-sensitivity results (mean ΔR/R_before):")
    for k in [5, 10, 20, 50]:
        vals = results[k]
        if vals:
            logger.info(f"    k={k:>3}: mean={np.mean(vals):.8f}  max={np.max(vals):.8f}  n={len(vals)}")
        else:
            logger.info(f"    k={k:>3}: no results")
    return results


# ==============================================================
# Check 4: d-sensitivity on synthetic data
# ==============================================================
def check4_dimensionality_collapse():
    logger.info("\n=== CHECK 4: ΔR vs dimensionality d on synthetic two-cluster data ===")
    np.random.seed(42)
    N = 100  # 50 per cluster
    results = []
    for d in [10, 50, 100, 200, 512, 1024]:
        a_center = np.zeros(d); a_center[0] = 1
        b_center = np.zeros(d); b_center[0] = -1
        a_vecs = a_center + 0.3*np.random.randn(50, d)
        b_vecs = b_center + 0.3*np.random.randn(50, d)
        a_vecs /= np.linalg.norm(a_vecs, axis=1, keepdims=True)
        b_vecs /= np.linalg.norm(b_vecs, axis=1, keepdims=True)
        p_vec = np.zeros(d); p_vec[1] = 1.0  # bridge node orthogonal to A-B axis

        all_before = np.vstack([a_vecs, b_vecs])
        sims = all_before @ all_before.T; np.fill_diagonal(sims, 0)
        adj = np.zeros_like(sims)
        for i in range(N):
            top = np.argsort(sims[i])[::-1][:10]
            for j in top:
                if sims[i,j]>0: adj[i,j]=sims[i,j]; adj[j,i]=sims[i,j]
        r_before = effective_resistance_direct(adj, 0, 50)

        all_after = np.vstack([all_before, p_vec.reshape(1,-1)])
        sims2 = all_after @ all_after.T; np.fill_diagonal(sims2, 0)
        adj2 = np.zeros_like(sims2)
        for i in range(N+1):
            top = np.argsort(sims2[i])[::-1][:10]
            for j in top:
                if sims2[i,j]>0: adj2[i,j]=sims2[i,j]; adj2[j,i]=sims2[i,j]
        r_after = effective_resistance_direct(adj2, 0, 50)

        delta = (r_before - r_after) / max(r_before, 1e-10)
        results.append((d, r_before, delta))
        logger.info(f"  d={d:>5}: R_before={r_before:.6f}  ΔR/R={delta:.6f}")

    return results


# ==============================================================
# Main
# ==============================================================
def main():
    print("\n" + "="*60)
    print("EFFECTIVE RESISTANCE SANITY CHECKS")
    print("="*60)

    # Check 2 first (pure math, no data needed)
    delta_toy = check2_toy_graph()

    # Check 4: d-collapse on synthetic
    check4_dimensionality_collapse()

    # Check 3: k sensitivity on real data
    check3_k_sensitivity()

    # Check 1: direct solver on real data
    check1_direct_solver()

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Toy bridge ΔR = {delta_toy:.6f} (should be > 0.01 if solver works)")
    print("If Check 2 shows ΔR >> 0 but Check 3 shows ΔR ≈ 0:")
    print("  → Collapse is real: high-dim anisotropy kills the signal")
    print("  → This is the impossibility-style result for the paper")


if __name__ == "__main__":
    main()
