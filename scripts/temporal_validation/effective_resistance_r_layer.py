"""
scripts/temporal_validation/effective_resistance_r_layer.py

Effective Resistance as a mathematical surrogate for the R layer of TVV.

For each classified case (P, A, B, q, role_label):
  1. Build local k-NN graph from train papers near A and B
  2. Compute effective resistance R_eff(A_community, B_community) BEFORE adding P
  3. Add P to the graph
  4. Compute R_eff AFTER adding P
  5. ΔR = R_eff_before - R_eff_after
  6. ΔR/R_eff_before = relative drop in effective resistance

True bridging papers should cause large ΔR/R_eff (A and B become closer in the graph).
Boundary expansion / false positives should cause small ΔR/R_eff.

Calibrate δ: R_graph(V) = 1 iff ΔR/R_eff_before >= δ
Compare R_graph labels vs LLM role labels using Cohen's κ.

If κ > 0.5 → effective resistance can replace or validate LLM R layer.

Implementation uses scipy.sparse CG solver (Spielman-Srivastava style, but simple).
For N_local ~ 100-300 papers, direct solve is fast enough.

Usage:
    python scripts/temporal_validation/effective_resistance_r_layer.py --split t5
"""

import argparse
import json
from pathlib import Path

import numpy as np
from loguru import logger

OUTPUT_DIR = Path("data/processed/tvv/rolling")
K_LOCAL = 30   # local graph size per community
K_GRAPH = 10   # k-NN edges per paper in graph
DELTA_GRID = np.linspace(0.01, 0.50, 50)  # δ search grid


def build_knn_graph(vecs: np.ndarray, k: int):
    """
    Build k-NN graph adjacency from embedding vectors.
    Returns: (N, N) sparse-friendly list of (i, j, weight) edges.
    Weight = cosine similarity.
    """
    N = len(vecs)
    sims = vecs @ vecs.T  # (N, N)
    np.fill_diagonal(sims, -1)
    edges = []
    for i in range(N):
        top_k = np.argsort(sims[i])[::-1][:k]
        for j in top_k:
            if sims[i, j] > 0:
                edges.append((i, j, float(sims[i, j])))
    return edges, N


def effective_resistance(edges, N: int, src_nodes: list[int], tgt_nodes: list[int]) -> float:
    """
    Approximate effective resistance between source community and target community
    using the Laplacian and a sparse CG solve.

    For communities S and T, we use the star approximation:
    - Add a super-source s connected to all nodes in S with weight 1
    - Add a super-sink t connected to all nodes in T with weight 1
    - Compute R_eff(s, t)

    Returns approximate effective resistance.
    """
    from scipy.sparse import csr_matrix, lil_matrix
    from scipy.sparse.linalg import spsolve, cg

    total_nodes = N + 2  # N + super_source + super_sink
    s_idx = N      # super source
    t_idx = N + 1  # super sink

    L = lil_matrix((total_nodes, total_nodes), dtype=np.float64)

    # Add original edges
    for i, j, w in edges:
        L[i, i] += w
        L[j, j] += w
        L[i, j] -= w
        L[j, i] -= w

    # Connect super-source to S community
    for node in src_nodes:
        w = 1.0
        L[s_idx, s_idx] += w
        L[node, node] += w
        L[s_idx, node] -= w
        L[node, s_idx] -= w

    # Connect super-sink to T community
    for node in tgt_nodes:
        w = 1.0
        L[t_idx, t_idx] += w
        L[node, node] += w
        L[t_idx, node] -= w
        L[node, t_idx] -= w

    L = L.tocsr()

    # Solve (L + epsilon*I) x = b, b[s_idx]=1, b[t_idx]=-1
    b = np.zeros(total_nodes)
    b[s_idx] = 1.0
    b[t_idx] = -1.0

    # Add small regularization (grounded Laplacian)
    eps = 1e-8
    from scipy.sparse import eye as speye
    L_reg = L + eps * speye(total_nodes, format="csr")

    try:
        x, info = cg(L_reg, b, maxiter=1000, atol=1e-8)
        if info != 0:
            x = spsolve(L_reg, b)
    except Exception:
        x = np.zeros(total_nodes)

    r_eff = float(x[s_idx] - x[t_idx])
    return max(r_eff, 0.0)


def compute_delta_r(a_vecs, b_vecs, p_vec, k=K_GRAPH):
    """
    Compute ΔR/R_before for a void (A community, B community) + candidate paper P.

    Returns: (delta_r_ratio, r_before, r_after)
    """
    # Build combined local graph (A community + B community)
    na = len(a_vecs)
    nb = len(b_vecs)
    all_vecs = np.vstack([a_vecs, b_vecs])  # indices 0..na-1 = A, na..na+nb-1 = B
    N = len(all_vecs)

    src_nodes = list(range(na))           # A community nodes
    tgt_nodes = list(range(na, na + nb))  # B community nodes

    edges_before, _ = build_knn_graph(all_vecs, k)
    r_before = effective_resistance(edges_before, N, src_nodes, tgt_nodes)

    # Add P to the graph
    all_vecs_after = np.vstack([all_vecs, p_vec.reshape(1, -1)])
    N_after = N + 1
    p_idx = N  # P is the last node

    # Update src/tgt (unchanged)
    edges_after, _ = build_knn_graph(all_vecs_after, k)
    r_after = effective_resistance(edges_after, N_after, src_nodes, tgt_nodes)

    if r_before < 1e-10:
        return 0.0, r_before, r_after

    delta_r_ratio = (r_before - r_after) / r_before
    return delta_r_ratio, r_before, r_after


def run_split(split_name: str, max_cases: int = None):
    import chromadb
    from configs.settings import settings

    # Load LLM-classified cases
    role_path = OUTPUT_DIR / split_name / "role_classification_v2.json"
    if not role_path.exists():
        logger.error(f"Role classification file not found: {role_path}")
        return

    data = json.load(open(role_path))
    cases = data["results"]
    if max_cases:
        cases = cases[:max_cases]
    logger.info(f"[{split_name}] Processing {len(cases)} cases")

    # Load embeddings
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

    # For each case: get A/B/P embeddings, compute ΔR
    results = []
    for i, r in enumerate(cases):
        case = r["case"]
        clf = r["classification"]

        # LLM label (collapsed)
        role = clf.get("role", "UNCLEAR")
        is_fill = role in {"TRUE_FILL", "PARTIAL_FILL"}
        is_fp   = role == "FALSE_POSITIVE"

        # Get A, B embeddings from train
        a_id = case.get("source_a", {}).get("id", "")
        b_id = case.get("source_b", {}).get("id", "")
        f_id = (case.get("filler", {}) or {}).get("id", "")

        a_idx = id_to_idx.get(a_id)
        b_idx = id_to_idx.get(b_id)

        if a_idx is None or b_idx is None:
            continue

        # Build local communities: k-NN around A and B in train
        a_vec = train_emb[a_idx]
        b_vec = train_emb[b_idx]

        # A community = K_LOCAL nearest train papers to A (excluding B)
        sims_a = train_emb @ a_vec
        a_local = sims_a.argsort()[::-1][:K_LOCAL + 1].tolist()
        a_local = [x for x in a_local if x != b_idx][:K_LOCAL]

        sims_b = train_emb @ b_vec
        b_local = sims_b.argsort()[::-1][:K_LOCAL + 1].tolist()
        b_local = [x for x in b_local if x != a_idx][:K_LOCAL]

        a_community = train_emb[a_local]
        b_community = train_emb[b_local]

        # Get P (filler) embedding
        p_vec = None
        if f_id:
            f_val_idx = val_id_to_idx.get(f_id)
            if f_val_idx is not None:
                p_vec = val_emb[f_val_idx]

        if p_vec is None:
            # Fallback: use midpoint as P proxy
            mp = a_vec + b_vec; mp /= np.linalg.norm(mp)
            p_vec = mp

        try:
            delta_r_ratio, r_before, r_after = compute_delta_r(
                a_community, b_community, p_vec
            )
        except Exception as e:
            logger.debug(f"  ER failed for case {i}: {e}")
            continue

        results.append({
            "case_id": case.get("case_id", ""),
            "source": case.get("source", ""),
            "role_llm": role,
            "is_fill_llm": is_fill,
            "is_fp_llm": is_fp,
            "delta_r_ratio": round(delta_r_ratio, 6),
            "r_before": round(r_before, 6),
            "r_after": round(r_after, 6),
        })

        if (i + 1) % 50 == 0:
            logger.info(f"  Processed {i+1}/{len(cases)}")

    logger.info(f"  Computed ΔR for {len(results)} cases")

    if not results:
        return

    # Calibrate δ: find threshold maximizing Cohen's κ
    from sklearn.metrics import cohen_kappa_score

    delta_r_vals = np.array([r["delta_r_ratio"] for r in results])
    llm_fill    = np.array([r["is_fill_llm"] for r in results], dtype=int)

    best_kappa = -1
    best_delta = 0
    kappa_curve = []
    for delta in DELTA_GRID:
        r_graph = (delta_r_vals >= delta).astype(int)
        if r_graph.sum() == 0 or r_graph.sum() == len(r_graph):
            kappa_curve.append((delta, -1))
            continue
        try:
            k = cohen_kappa_score(llm_fill, r_graph)
            kappa_curve.append((delta, k))
            if k > best_kappa:
                best_kappa = k
                best_delta = delta
        except Exception:
            kappa_curve.append((delta, -1))

    # Summary stats at best δ
    r_graph_best = (delta_r_vals >= best_delta).astype(int)
    precision = float(np.sum((r_graph_best == 1) & (llm_fill == 1))) / max(1, r_graph_best.sum())
    recall    = float(np.sum((r_graph_best == 1) & (llm_fill == 1))) / max(1, llm_fill.sum())

    print(f"\n[{split_name}] EFFECTIVE RESISTANCE R-LAYER SURROGATE")
    print(f"  n_cases = {len(results)}")
    print(f"  ΔR/R_before: mean={delta_r_vals.mean():.4f}  "
          f"p50={np.percentile(delta_r_vals,50):.4f}  "
          f"p90={np.percentile(delta_r_vals,90):.4f}")
    print(f"  LLM fill rate: {llm_fill.mean():.1%}")
    print(f"  Best δ = {best_delta:.3f}  Cohen's κ = {best_kappa:.3f}")
    print(f"  At best δ: precision={precision:.2f}  recall={recall:.2f}")

    if best_kappa >= 0.5:
        print(f"  ✓ κ ≥ 0.5 — R_graph can serve as non-LLM R surrogate")
    elif best_kappa >= 0.3:
        print(f"  ~ κ ∈ [0.3, 0.5) — moderate agreement, useful as corroborating signal")
    else:
        print(f"  ✗ κ < 0.3 — weak agreement, ΔR alone insufficient for R layer")

    result = {
        "split": split_name,
        "n_cases": len(results),
        "best_delta": round(float(best_delta), 4),
        "best_kappa": round(float(best_kappa), 4),
        "precision_at_best": round(precision, 4),
        "recall_at_best": round(recall, 4),
        "delta_r_stats": {
            "mean": round(float(delta_r_vals.mean()), 6),
            "p50": round(float(np.percentile(delta_r_vals, 50)), 6),
            "p90": round(float(np.percentile(delta_r_vals, 90)), 6),
            "p95": round(float(np.percentile(delta_r_vals, 95)), 6),
        },
        "kappa_curve": [(round(d, 3), round(k, 4)) for d, k in kappa_curve if k >= -0.1],
        "cases": results,
    }
    out_path = OUTPUT_DIR / split_name / "effective_resistance_r.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    logger.info(f"Saved → {out_path}")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", default="t5")
    parser.add_argument("--max-cases", type=int, default=None)
    args = parser.parse_args()
    run_split(args.split, args.max_cases)


if __name__ == "__main__":
    main()
