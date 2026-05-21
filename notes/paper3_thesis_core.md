---
# Paper 3 Thesis Core — The "Why" Before the "How"
# Distilled 2026-05-21. Read this before opening any implementation file.
---

## The Big Question

Knowledge evolves. How do we *measure* this evolution?

Not counting (papers/year), not citation graphs, not topic models.
Measuring: **how much the state changed, in which direction, and whether it was meaningful.**

---

## Three Sub-Problems (and why existing tools fail all three)

### Sub-problem 1: What counts as "change"?

1000 trivial papers vs 1 paradigm-shifting paper — which is a bigger change?

Intuition: the latter. Every existing metric (L2, cosine, KL on topic distribution, citation count) says the former.

→ Need a metric sensitive to **information content**, not data volume.

### Sub-problem 2: "Meaningful" relative to whom?

The same paper is a major event for the scheduler maintainer, noise for the filesystem maintainer.

Change magnitude is not an intrinsic property of the corpus — it is **observer-relative**.

→ Need to explicitly put the observer (Anchor) inside the metric definition.

### Sub-problem 3: How do you measure something that doesn't exist?

Void = knowledge that should exist but hasn't been filled yet.
(e.g., "mobile-aware CPU scheduler" in 2010 — the concept wasn't named, but retrospectively it "should have been there.")

A void is not a paper, not a cluster, not any existing embedding. It is **absence**.

→ Need a geometry that can define "absence", not just "presence".

---

## The Framework: Three Geometric Layers

### Layer 1: Anchor-conditioned tangent chart ("relative to whom")

Cut the BGE-M3 sphere at anchor C. Get tangent space T_C.

Meaning: "What does everything look like from the anchor's perspective?"
Points near C = things the anchor cares about. Far points = outside anchor's view.

### Layer 2: cPCA contrast filtering ("what is meaningful change")

In tangent space: contrast foreground (anchor k-NN) vs background (random corpus).
Find anchor-distinctive directions D*.

Meaning: filter out "things moving globally" (language drift, buzzword churn).
Keep only "change along dimensions the anchor cares about."

### Layer 3: Hyperbolic lift ("how to measure absence")

Lift D* subspace to hyperbolic geometry ℍ^k.

Euclidean space has no natural way to define "absence" — a low-density ball is just a low-density ball.
Hyperbolic space has **entailment cones**: given anchor C, can define "what C should conceptually extend to" (inside cone) vs "what couldn't arise from C" (outside cone).

Void = inside cone, but density ≈ 0.

This is why lift is *necessary*, not merely convenient. Euclidean doesn't have entailment structure.

---

## Two Observables

### Observable 1: Drift dD_C ("how much changed")

Corpus distribution in anchor's view = Gaussian in cPCA subspace.
Two time points → two Gaussians → **Bures-Wasserstein distance** = drift.

Property:
- 1000 trivial papers → Gaussian barely moves → dD_C ≈ 0
- 1 paradigm shift → mean shifts + covariance deforms → dD_C large
- Automatically solves sub-problem 1 (information vs data volume)

### Observable 2: Polarity σ_C ("which direction")

Sign of drift direction projected onto anchor's expected evolution direction.

- σ = +1: along expected direction (innovation)
- σ = -1: opposite (falsification — hypothesis disproved)
- σ = 0: orthogonal (maintenance)

Drift magnitude and polarity are **kept separate** (not collapsed into one scalar — avoids cancellation between large positive and large negative changes).

---

## Ground Truth: Linux Kernel RFC

Void detection problem: how do you know a predicted void is real?

LKML provides **human-expert-labeled void ground truth**:
- RFC = "we need X but don't have it" = explicit void declaration
- merge/reject/stall = whether the void was filled
- 25+ years = massive event sequence

Run framework on RFC: can it **predict the void before the RFC appears**?

This converts "define a framework" into **a falsifiable scientific claim**.

---

## One-Sentence Summary

> Anchor-conditioned dynamic measurement of knowledge state evolution:
> contrast against background to isolate observer-relevant signal,
> lift to hyperbolic geometry to define absence,
> measure distributional shift via Bures-Wasserstein.

Short version:

> "In the observer's reference frame, use contrastive filtering to find meaningful dimensions, use negative-curvature geometry to define absence, use distributional distance to measure evolution."

---

## Why This Is Paradigm-Level, Not Method-Level

| Traditional IR | This framework |
|---|---|
| Absolute corpus properties | Observer-relative properties |
| Measures relations between existing things | Measures absent things |
| Same metric for all queries | Each anchor has its own metric |
| Static snapshot | Event-driven evolution |
| Euclidean / cosine | Mixed-curvature geometry |
| Point vs point | Distribution vs distribution |

All 5 dimensions replaced simultaneously → not improving a method, **changing the paradigm**.

Physics analogy:
- Newton → Einstein: absolute → observer-relative
- Classical → Quantum: definite value → distribution
- Euclidean → Riemannian: flat → curved

IR paradigm shift = doing all three at once.

---

## Logical Necessity of the Three Papers

- **Paper 1 (TVA)**: Proves voids exist → "absence" is genuinely definable
- **Paper 2 (TVV)**: Proves non-lifted methods cannot find voids → "need deeper geometry" is *necessary*, not nice-to-have
- **Paper 3 (D-TVA)**: Gives the lifted geometry + dynamic measurement → completes the paradigm

P1 establishes the claim. P2 proves P1's own methods are *insufficient* (self-refutation gives the argument its force). P3 gives the *only* sufficient method.

Structure: Einstein 1905 (special relativity, establishes claim) → Michelson-Morley interpretation (impossibility, proves ether doesn't exist) → 1915 (general relativity, complete framework).

P2 is not a companion paper to P1. It is P1 refuting itself, which is what makes P3 *forced*.

---

## What to Ignore When Reading Implementation Files

The implementation details (sphere LogMap, cPCA eigenvectors, Bures-Wasserstein sqrtm, τ scaling, entailment cone formula) are **the "how"**. They exist to make the above three geometric layers computable.

When you feel lost in implementation details, come back to:
1. Which sub-problem does this code address?
2. Which of the three geometric layers does it belong to?
3. Does this code preserve observer-relativity (anchor-conditioned)?

If a code change violates observer-relativity (e.g., global normalization that destroys anchor-local structure), it is wrong regardless of whether it makes the numbers look better.
