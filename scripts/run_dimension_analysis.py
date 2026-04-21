"""
scripts/run_dimension_analysis.py

TVA Dimensionality Analysis — find the optimal vector DB dimension for your corpus.

Based on the TVA Dimensionality Theorem:
    D* = [γ · ln(N) / (k · (1 - D_LLM^(-γ)))]^(1/(γ+1))

where:
    γ   = power-law decay exponent of your corpus (measured from SVD)
    N   = number of documents in your corpus
    k   = noise tolerance constant (calibrated from adversarial review reject rates)
    D_LLM = assumed frontier LLM dimensionality (default 12288)

Usage:
    python scripts/run_dimension_analysis.py
    python scripts/run_dimension_analysis.py --collection papers --sample 5000
    python scripts/run_dimension_analysis.py --D-llm 16384 --k 0.002
"""

import argparse
import numpy as np
from scipy.stats import linregress

def load_embeddings(collection_name: str, sample_size: int) -> np.ndarray:
    import chromadb
    from configs.settings import settings

    client = chromadb.PersistentClient(path=str(settings.vectordb_path))
    col = client.get_collection(collection_name)
    total = col.count()
    actual_sample = min(sample_size, total)
    print(f"Collection '{collection_name}': {total} docs, sampling {actual_sample}")
    result = col.get(limit=actual_sample, include=["embeddings"])
    return np.array(result["embeddings"])


def fit_power_law(eigenvalues: np.ndarray, fit_range=(2, 400)) -> tuple[float, float]:
    """Fit λ_i ∝ i^(-α) on log-log scale. Returns (α, R²)."""
    lo, hi = fit_range
    hi = min(hi, len(eigenvalues))
    idx = np.arange(lo, hi)
    log_i = np.log(idx)
    log_lam = np.log(eigenvalues[idx - 1] + 1e-12)
    slope, _, r, _, _ = linregress(log_i, log_lam)
    return -slope, r ** 2


def resolution(D: int, gamma: float, D_llm: int) -> float:
    """R(D) = (1 - D^(-γ)) / (1 - D_LLM^(-γ))"""
    denom = 1 - D_llm ** (-gamma)
    if denom <= 0:
        return 1.0
    return (1 - D ** (-gamma)) / denom


def d_star(gamma: float, N: int, k: float, D_llm: int) -> float:
    """Optimal dimension D* from TVA Dimensionality Theorem."""
    denom = 1 - D_llm ** (-gamma)
    return (gamma * np.log(N) / (k * denom)) ** (1 / (gamma + 1))


def run_analysis(collection: str, sample: int, D_llm: int, k: float):
    # ── 1. Load embeddings ────────────────────────────────────────
    embeddings = load_embeddings(collection, sample)
    N_sample, D = embeddings.shape
    print(f"Embedding matrix: {N_sample} × {D}\n")

    # ── 2. SVD ────────────────────────────────────────────────────
    print("Running SVD (this may take 30–60 seconds for large samples)...")
    X = embeddings - embeddings.mean(axis=0)
    _, S, _ = np.linalg.svd(X, full_matrices=False)
    eigenvalues = S ** 2 / N_sample

    # ── 3. Fit power law ──────────────────────────────────────────
    alpha, r2 = fit_power_law(eigenvalues)
    gamma = alpha - 1
    print(f"Power-law fit:  λ_i ∝ i^(-α)")
    print(f"  α = {alpha:.4f}   γ = α−1 = {gamma:.4f}   R² = {r2:.4f}")
    if gamma <= 0:
        print("  ⚠️  γ ≤ 0: corpus may be too small or too homogeneous for reliable fit.")
    print()

    # ── 4. Resolution table ───────────────────────────────────────
    total_var = eigenvalues.sum()
    checkpoints = [64, 128, 256, 384, 512, 640, 768, 896, 1024, 1536, 2048, 3072]
    checkpoints = [d for d in checkpoints if d <= D]

    print(f"{'D':>6} | {'R(D) theory':>12} | {'Empirical var':>13} | {'Marginal gain':>13}")
    print("-" * 52)
    prev_R = 0.0
    for d in checkpoints:
        R = resolution(d, gamma, D_llm) * 100 if gamma > 0 else float('nan')
        emp = eigenvalues[:d].sum() / total_var * 100
        marginal = R - prev_R if gamma > 0 else float('nan')
        print(f"{d:>6} | {R:>11.2f}% | {emp:>12.2f}% | {marginal:>12.2f}%")
        prev_R = R
    print()

    # ── 5. D* recommendation ──────────────────────────────────────
    # Get total N from all collections for D* calc
    try:
        import chromadb
        from configs.settings import settings
        client = chromadb.PersistentClient(path=str(settings.vectordb_path))
        N_total = sum(c.count() for c in client.list_collections())
    except Exception:
        N_total = N_sample

    if gamma > 0:
        D_opt = d_star(gamma, N_total, k, D_llm)
        print(f"Corpus total N  = {N_total:,}")
        print(f"ln(N)           = {np.log(N_total):.3f}")
        print(f"D_LLM           = {D_llm:,}")
        print(f"(1−D_LLM^(−γ)) = {1 - D_llm**(-gamma):.4f}")
        print(f"k (noise const) = {k}")
        print()
        print(f"  ➜  Theoretical optimal D* = {D_opt:.0f}")

        # Find closest standard embedding dimension
        standard_dims = [256, 384, 512, 768, 1024, 1536, 2048, 3072]
        closest = min(standard_dims, key=lambda d: abs(d - D_opt))
        print(f"  ➜  Nearest standard dimension: {closest}D")
        print()

        # Marginal cost warning
        if D_opt < 768:
            print("  ℹ️  D* < 768: your corpus may be too small for high-dim embeddings.")
            print("      Consider ingesting more documents before upgrading embedding model.")
        elif D_opt > 1024:
            print("  ℹ️  D* > 1024: consider upgrading to a higher-dim embedding model")
            print("      when corpus grows significantly.")
        else:
            print("  ✅  Current BGE-M3 1024D is near-optimal for this corpus.")
    else:
        print("  ⚠️  Cannot compute D*: γ ≤ 0. Increase sample size or corpus diversity.")

    print()
    print("─" * 52)
    print("Interpretation guide:")
    print("  γ < 0.1  → broad corpus (mixed domains), slow decay, higher D needed")
    print("  γ 0.1–0.4 → focused technical domain, moderate decay")
    print("  γ > 0.4  → highly specialized, fast decay, lower D sufficient")


def main():
    parser = argparse.ArgumentParser(description="TVA Dimensionality Analysis")
    parser.add_argument("--collection", default="kernel_source",
                        help="ChromaDB collection name (default: kernel_source)")
    parser.add_argument("--sample", type=int, default=10000,
                        help="Number of embeddings to sample (default: 10000)")
    parser.add_argument("--D-llm", type=int, default=12288,
                        help="Assumed frontier LLM dimensionality (default: 12288)")
    parser.add_argument("--k", type=float, default=0.001,
                        help="Noise tolerance constant k (default: 0.001, calibrate from reject rates)")
    args = parser.parse_args()

    run_analysis(
        collection=args.collection,
        sample=args.sample,
        D_llm=args.D_llm,
        k=args.k,
    )


if __name__ == "__main__":
    main()
