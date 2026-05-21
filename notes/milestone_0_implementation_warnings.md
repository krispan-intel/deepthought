---
# Milestone 0 Implementation Warnings
# DO NOT START CODING UNTIL THIS FILE IS READ
# Last updated: 2026-05-21
---

## Day 1 checklist (write these before running anything)

- [ ] Sign canonicalization for cPCA eigenvectors
- [ ] Taylor fallback for sphere LogMap
- [ ] Maclaurin fallback for Lorentz ExpMap
- [ ] Filter antipodal points (cos < -0.99)
- [ ] Use float64 throughout
- [ ] Residual in coordinate form, not ambient
- [ ] BW in 1023D ambient tangent space, not k-dim subspace
- [ ] LKML thread packing (before first RFC event, June end)

---

## P0: Silent failures (code runs, results are garbage)

### P0-A: BW subspace mismatch across time (SILENT FAILURE)

D*(C,t) changes with t. Σ_C(t₁) and Σ_C(t₂) live in different k-dim subspaces.
BW on k-dim subspace matrices from different bases = garbage (looks like valid numbers).

**Symptom:** dD_C curve has large spikes that move when you rerun. Hard to diagnose.
**When it fires:** First RFC event dD_C computation (June end). NOT in Milestone 0 (single-t tests).

**Fix: compute BW in shared 1023D ambient tangent space.**

```python
# WRONG (current spec):
# Sigma_C_t1 = np.cov(z_i_t1.T)   # k×k, in D*(C,t1) basis
# Sigma_C_t2 = np.cov(z_i_t2.T)   # k×k, in D*(C,t2) basis — DIFFERENT BASIS!
# BW(Sigma_t1, Sigma_t2)           # GARBAGE

# CORRECT: keep everything in 1023D ambient tangent space
# mu_1023_t = mean of v_i_projected_ambient (1023D, rank ≤ k)
# Sigma_1023_t = (1/n) * V_ambient.T @ V_ambient  (1023×1023, rank-k)

def mat_sqrt_psd(S, tol=1e-10):
    """Matrix sqrt for rank-deficient symmetric PSD matrix.
    Uses tolerance-based rank selection (more robust than fixed rank_k).
    """
    S = 0.5 * (S + S.T)                    # symmetrize
    vals, vecs = np.linalg.eigh(S)          # ascending order
    vals = np.clip(vals, 0, None)           # clamp numerical negatives
    max_val = vals.max()
    keep = vals > tol * max_val if max_val > 0 else np.zeros(len(vals), dtype=bool)
    vals_sqrt = np.zeros_like(vals)
    vals_sqrt[keep] = np.sqrt(vals[keep])
    return vecs @ np.diag(vals_sqrt) @ vecs.T

def bw_distance_sq(mu1, Sigma1, mu2, Sigma2):
    """Squared BW distance on rank-deficient Gaussians in shared ambient space.
    Works on UNSCALED z_i (or ambient 1023D projected coords).
    τ scaling is NOT applied here — τ only affects hyperbolic lift and cone shape.
    BW drift and hyperbolic curvature are decoupled by design.
    """
    mean_term = np.sum((mu2 - mu1) ** 2)
    S1_half = mat_sqrt_psd(Sigma1)
    M = S1_half @ Sigma2 @ S1_half
    M_half = mat_sqrt_psd(M)         # mat_sqrt_psd already symmetrizes internally
    cov_term = max(np.trace(Sigma1) + np.trace(Sigma2) - 2 * np.trace(M_half), 0.0)
    return mean_term + cov_term

def bw_distance(mu1, Sigma1, mu2, Sigma2):
    return np.sqrt(bw_distance_sq(mu1, Sigma1, mu2, Sigma2))
```

### P0-B: cPCA sign flipping (SILENT FAILURE, cross-run inconsistent)

np.linalg.eigh returns eigenvectors with arbitrary sign (±u both valid).
At different time points t1, t2, the same eigenvector may flip sign.
Result: μ_C(t2) - μ_C(t1) includes spurious contribution from sign change, not real drift.

**Symptom:** dD_C spikes at random locations, changes position on re-run.

**Fix: sign canonicalization after every cPCA computation.**

```python
def canonicalize_eigvecs(V):
    """Force sign: max absolute value component of each eigenvector is positive."""
    signs = np.sign(V[np.argmax(np.abs(V), axis=0), np.arange(V.shape[1])])
    signs[signs == 0] = 1
    return V * signs  # (1023, k)

# Usage:
vals, vecs = np.linalg.eigh(Sfg - alpha * Sbg)
vecs_canonical = canonicalize_eigvecs(vecs)
D_star = vecs_canonical[:, np.argsort(vals)[::-1][:k]].T  # (k, 1023)
```

Note: sign canonicalization fixes ± ambiguity (single-time internal consistency).
It does NOT fix cross-time subspace rotation or eigenvector ordering swaps.
For cross-time BW: use fixed D*(C, t_ref) — do NOT recompute D* at each t in Milestone 0.

---

## Numerical stability fallbacks (write first, run second)

### Sphere LogMap: unstable when e_i ≈ C

```python
def sphere_logmap(C, e, eps=1e-6):
    """Log map on S^1023 at base point C (norm-1 vector).
    C and e must both be on S^1023 (unit norm). Do NOT pass np.zeros(1023).
    """
    diff = e - C
    if np.linalg.norm(diff) < eps:
        # Taylor fallback: project onto tangent plane at C for exact orthogonality
        v = diff - (diff @ C) * C
        return v
    cos_theta = np.clip(C @ e, -(1-eps), 1-eps)
    theta = np.arccos(cos_theta)
    sin_theta = np.sin(theta)
    return (theta / sin_theta) * (e - cos_theta * C)
```

### Lorentz ExpMap: unstable when ||v|| → 0

```python
def lorentz_expmap0(v, eps=1e-8):
    """ExpMap at origin of H^k. v is k-dim tangent vector."""
    n = np.linalg.norm(v)
    if n < eps:
        return np.concatenate([[1.0], v])  # Maclaurin O(1) fallback
    return np.concatenate([[np.cosh(n)], np.sinh(n) * v / n])
```

### Other Day 1 fixes

```python
# Filter antipodal points (cos(C, e_i) < -0.99 → LogMap undefined)
def filter_antipodal(corpus, anchor, threshold=-0.99):
    cos_sims = corpus @ anchor
    return corpus[cos_sims > threshold]

# float64 everywhere
corpus = corpus.astype(np.float64)
anchor = anchor.astype(np.float64)

# PCA sample deficiency: n=500 neighbors × 1024 dims → k_max = 250
# Never sweep k > n_neighbors // 2
k_max = len(foreground) // 2  # hard cap
```

---

## Residual: coordinate form, not ambient form

```python
# WRONG (will produce incorrect shape or redundant dims):
# r_i_ambient = v_i - D_star.T @ D_star @ v_i  # still 1023D, has redundancy

# CORRECT: project residual into orthogonal complement basis
def compute_residual_coords(v_i, D_star):
    """
    D_star: (k, 1023) — top-k cPCA eigenvectors (rows orthonormal)
    Returns: z_coords (k,), r_coords (1023-k,)
    """
    z_coords = D_star @ v_i                          # (k,)
    z_ambient = D_star.T @ z_coords                  # (1023,) reconstruction
    r_ambient = v_i - z_ambient                      # (1023,) residual

    # Orthogonal complement basis via scipy null_space (deterministic, no random)
    from scipy.linalg import null_space
    D_perp_T = null_space(D_star)                    # (1023, 1023-k)
    D_perp = D_perp_T.T                              # (1023-k, 1023)
    # Sign canonicalize rows of D_perp for cross-call consistency
    for i in range(D_perp.shape[0]):
        idx = np.argmax(np.abs(D_perp[i]))
        if D_perp[i, idx] < 0:
            D_perp[i] *= -1
    assert D_perp.shape == (1023 - D_star.shape[0], 1023)
    r_coords = D_perp @ r_ambient                    # (1023-k,)

    return z_coords, r_coords

# IMPORTANT: for cross-time product distances, cache D_perp once at t_ref.
# D_perp recomputed at each t will give different bases → r_coords not comparable.

# Final product space vector: (k+1 Lorentz) + (1023-k Euclidean)
h_i = lorentz_expmap0(z_coords * tau)               # (k+1,)
product_i = np.concatenate([h_i, r_coords])         # (k+1 + 1023-k,) = (1024,)
```

Cache D_perp once per (anchor, t) — QR is expensive inside loops.

---

## Sign canonicalization (call immediately after every cPCA)

```python
def canonicalize_signs(D_star):
    """
    Force each eigenvector's largest-magnitude entry to be positive.
    Eliminates cross-run and cross-time sign flipping from np.linalg.eigh.
    Must call after every cPCA computation.
    """
    for i in range(D_star.shape[0]):
        idx = np.argmax(np.abs(D_star[i]))
        if D_star[i, idx] < 0:
            D_star[i] *= -1
    return D_star

def assert_D_star_orthonormal(D_star, atol=1e-8):
    """Verify cPCA eigenvectors are orthonormal before QR-based D_perp."""
    product = D_star @ D_star.T
    assert np.allclose(product, np.eye(D_star.shape[0]), atol=atol), \
        f"cPCA eigenvectors not orthonormal (max err={np.max(np.abs(product - np.eye(D_star.shape[0]))):.2e}). " \
        "QR-based D_perp will be invalid if this fails."

# Usage order (MANDATORY):
# vals, vecs = np.linalg.eigh(Sfg - alpha * Sbg)
# idx = np.argsort(vals)[::-1][:k]
# D_star = vecs[:, idx].T           # (k, 1023)
# D_star = canonicalize_signs(D_star)
# assert_D_star_orthonormal(D_star)
# D_perp = ...QR...
```

## cPCA hyperparameter sweeps

```python
# α sweep: [0.1, 0.5, 1.0, 2.0, 5.0]
# Check: top eigenvector of (Sfg - α*Sbg) should align with foreground centroid
# If projection_sign < 0 for all corpus points → α too large, flipped direction
alphas = [0.1, 0.5, 1.0, 2.0, 5.0]

# τ sweep: [1, 2, 3, 5, 7, 10]
# Criterion: τ* = argmin Gromov_δ / diameter  (elbow point)
# τ affects ONLY hyperbolic lift and cone. NOT BW drift (BW uses unscaled z_i).
taus = [1, 2, 3, 5, 7, 10]

# k sweep: [32, 64, 128, 256]
# Hard cap: k ≤ n_foreground // 2  (sample deficiency: n=500 → k_max=250)
# DO NOT sweep k=512 or k=1024 with n=500 foreground points.
ks = [32, 64, 128, 256]  # 512/1024 removed — invalid with n=500
```

---

## Cone direction: τ is signed scalar projection onto radial direction

**DO NOT tie τ axis to cPCA eigenvector.**
**DO NOT use τ_q = ||v_q|| (norm is always ≥ 0, cone degenerates to entire space).**

τ must be a **signed scalar projection** so that τ_q > 0 (outward, more specific) vs τ_q < 0 (inward) is meaningful.

```python
def get_tau_direction_milestone0(foreground_v, D_star):
    """
    τ axis = foreground centroid direction in cPCA subspace.
    PROVISIONAL for Milestone 0. Semantically: "the mean direction of anchor's
    neighborhood" — a proxy for abstraction axis, not the abstraction axis itself.

    WHY NOT anchor radial:
      In anchor-centered tangent chart, anchor C = origin = log_C(C) = 0.
      Origin has no direction. "Anchor's radial" does not exist in this chart.
      np.zeros(1023) is NOT a sphere point — sphere_logmap would fail.

    For paper-grade experiments (Phase 2+): replace with Option C —
      labeled general-specific pairs:
        tau_hat = mean(z_specific - z_general) for known hierarchy pairs
        e.g., "BPF verifier" - "BPF subsystem" for Linux RFC
    """
    z_fg = foreground_v @ D_star.T    # (n_fg, k) — project foreground into cPCA coords
    centroid = z_fg.mean(axis=0)      # (k,)
    norm_c = np.linalg.norm(centroid)
    if norm_c < 1e-8:
        return D_star[0]              # degenerate fallback: first eigenvector
    return centroid / norm_c          # unit vector in R^k

def in_entailment_cone(z_q, tau_hat, angle_threshold=1.0):
    """
    z_q: (k,) projected point in cPCA coordinate space
    tau_hat: (k,) unit radial direction (from get_tau_direction)

    Split: τ_q = <z_q, tau_hat>  (signed scalar — CAN be negative)
            x_q = z_q - τ_q * tau_hat  (k-1 dimensional perpendicular component)

    Future cone: τ_q > 0  AND  ||x_q|| ≤ τ_q * angle_threshold
    """
    tau_q = z_q @ tau_hat                          # signed scalar
    x_q = z_q - tau_q * tau_hat                    # perpendicular component
    return (tau_q > 0) and (np.linalg.norm(x_q) <= tau_q * angle_threshold)
```

**Why signed projection, not norm:**
- τ_q = ||z_q|| ≥ 0 always → "future cone τ_q > 0" = every point except anchor → cone = entire space (degenerate, useless)
- τ_q = <z_q, τ̂> is signed → τ_q > 0 means "in the direction of anchor's radial" → proper cone with boundary

**No calibration oracle needed.** Anchor C's own radial direction is the natural τ axis (more specific concepts appear further from ℍ^k origin than C).

---

## LKML thread packing (implement before first RFC event, June end)

Stage 1 recall unit = thread, not single email.

```python
def pack_lkml_thread(msg_id, messages, max_tokens=2048):
    """
    Reconstruct RFC thread from message-id and In-Reply-To headers.
    Returns concatenated text for embedding.
    """
    thread = get_thread_by_root(msg_id, messages)  # follow In-Reply-To tree
    # Sort chronologically, concat subject + body
    thread_text = ' '.join([
        f"{m['subject']} {m['body'][:200]}"
        for m in sorted(thread, key=lambda x: x['timestamp'])
    ])[:max_tokens]
    return thread_text

# Stage 1: embed thread (not single email)
# Stage 2: Lorentz lift on thread embedding
```

---

## Σ_C(t) definition: SAMPLE covariance of projected points (not cPCA matrix)

```python
# WRONG: using cPCA contrastive matrix directly as Sigma_C
# Sfg - alpha * Sbg  ← this is indefinite, NOT a valid covariance

# CORRECT: project points, then compute sample covariance
def compute_state(foreground_v, D_star):
    """
    foreground_v: (n_fg, 1023) tangent vectors of anchor k-NN
    D_star: (k, 1023) cPCA eigenvectors
    Returns: (mu_1023, Sigma_1023) for BW computation
    """
    # Project to k-dim coords, then reconstruct in ambient 1023D
    z_coords = foreground_v @ D_star.T   # (n_fg, k)
    z_ambient = z_coords @ D_star        # (n_fg, 1023) — rank-k reconstruction
    mu = z_ambient.mean(axis=0)          # (1023,)
    centered = z_ambient - mu
    Sigma = (centered.T @ centered) / len(foreground_v)  # (1023, 1023) — rank-k, PSD
    return mu, Sigma
```

---

## Milestone 0 execution order

Day 0: `pip install geoopt geomstats contrastive GraphRicciCurvature POT manify`

Day 1 (write code):
1. Write all fallbacks above (sphere_logmap, lorentz_expmap0, filter_antipodal)
2. Write canonicalize_eigvecs
3. Write compute_residual_coords (with D_perp)
4. Write compute_state (sample covariance in ambient 1023D)
5. Write bw_distance_ambient (rank-deficient)
6. Write in_entailment_cone (radial τ direction)
7. Sweep α, τ, k — set up experiment grid

Day 2 (run):
8. Run 7-test battery on anchor k-NN (single t, no cross-time BW yet)
9. Record: Gromov δ vs τ curve, pick τ*
10. Record: foreground/background separation quality vs α, pick α*
11. Record: hyperbolicity score vs k, pick k*

Day 3 (commit):
12. Commit (τ*, α*, k*) as Milestone 0 result
13. Run 5-ablation table (cosine / BM25+dense / tangent-cPCA / hyperbolic / full)
14. If "tangent-cPCA only" beats "cosine" but "full" ≠ "tangent-cPCA": Paper 3 = cPCA contribution, hyperbolic = interpretability. Adjust claims.
15. Commit final decision on Paper 3 scope

**June end (before first RFC event EAS 2013-08):**
16. Implement LKML thread packing
17. Finalize P0-A fix (BW in 1023D ambient, with sign canonicalization)
18. Run EAS 2013-08 event as smoke test
