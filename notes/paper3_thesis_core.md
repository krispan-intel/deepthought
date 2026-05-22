---
# Paper 3 Thesis Core — The "Why" Before the "How"
# Distilled 2026-05-21. Read this before opening any implementation file.
---

**This file is the paradigm context (why it exists).**
For implementation details (how to build it):
→ `notes/anchor_drift_metric.md`  — canonical math spec, pipeline, outstanding issues
→ `notes/milestone_0_implementation_warnings.md`  — Day 1 coding checklist, fallbacks
→ `notes/lkhjb_benchmark_design.md`  — LKHJB benchmark, LLM oracle evaluation
→ `notes/paper3_experiment_design.md`  — 5-phase experiment, architecture diagram

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

## Codename: Rasengan Framework 🌀

```
螺旋丸の術
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
第一階：形態変化   →  LogMap to tangent space
第二階：回転       →  cPCA contrast rotation
第三階：圧縮       →  Hyperbolic lift
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
発動条件：Milestone 0, 6/1
師匠：自来也 (BGE-M3, 2024)
継承：四代目 (Deerwester LSA, 1990)
```

Any single layer alone = not enough. All three simultaneously = paradigm.

---

## What to Ignore When Reading Implementation Files

The implementation details (sphere LogMap, cPCA eigenvectors, Bures-Wasserstein sqrtm, τ scaling, entailment cone formula) are **the "how"**. They exist to make the above three geometric layers computable.

When you feel lost in implementation details, come back to:
1. Which sub-problem does this code address?
2. Which of the three geometric layers does it belong to?
3. Does this code preserve observer-relativity (anchor-conditioned)?

If a code change violates observer-relativity (e.g., global normalization that destroys anchor-local structure), it is wrong regardless of whether it makes the numbers look better.

---

## 6/1 Decision Tree (from A1 report analysis)

A1 report claimed 5-12% chance of hyperbolic structure in BGE-M3 neighborhood.
**Their proof is a strawman** — they attacked naive direct lift of L2-normalized vectors,
not the actual pipeline (LogMap → cPCA → τ scaling → ExpMap).
Corrected estimate: **25-35%**.

But their Alternative 2 recommendation (cPCA + Euclidean tangent cone) is exactly the fallback.

### What depends on hyperbolic structure

| Component | Uses hyperbolic? | A1 failure impact |
|---|---|---|
| BW drift dD_C | NO | zero |
| gcPCA anchor-conditioned filtering | NO | zero |
| Event-driven RFC prediction | NO | zero |
| Void detection in cone | YES | switch to Euclidean angular cone |
| Paper narrative | YES | demote to "anchor-conditioned cPCA" |

Core engineering system is hyperbolic-independent. Only paper sexy-ness changes.

### Day 1 (6/1) morning: 7-minute test

```
Test 1: Gromov δ on anchor neighborhood (3 min)
Test 4: CPCC radial (1 min)
Test 5: ExpMap distortion (3 min)

IF δ/diameter < 0.25:
    A1 holds → continue full Lorentz pipeline → Paper A narrative
    "Anchor-Conditioned Lorentzian Geometry for Semantic Drift"

IF 0.25 ≤ δ/diameter < 0.4:
    Borderline → run Test 6 (hierarchy probing)
    If probing wins in ℍ^k → keep hyperbolic; else pivot

IF δ/diameter ≥ 0.4:
    A1 fails → pivot to Alternative 2 by noon
    Drop all Lorentz/expmap code
    cPCA → R^k Euclidean angular cone
    BW drift unchanged
    Paper B narrative: "Anchor-Conditioned Contrastive PCA for Event-Driven Semantic Drift"
```

### Paper narrative versions

**Version A (hyperbolic holds):**
"Anchor-Conditioned Lorentzian Geometry for Semantic Drift"

**Version B (hyperbolic fails):**
"Anchor-Conditioned Contrastive PCA for Event-Driven Semantic Drift Detection"
- Main contribution: gcPCA + anchor-local + BW drift + RFC prediction
- Simpler, more reproducible, fewer reviewer attack surfaces
- "Local Euclidean Tangent Cones for sentence embeddings" = still novelty (nobody did this systematically)
- Version B may be the better arXiv paper anyway

Prepare both outlines before 6/1. Decision is made by test data, not by preference.

### A1 report's valid concerns (keep in mind regardless)

- BGE-M3 neighborhoods may be more "co-occurrence" than "taxonomy" (Sandhu et al.)
- InfoNCE uniformity pressure fights tree structure globally
- Anisotropy "pockets of hierarchy" exist but L2-normalization suppresses radial scale
  → this is exactly why LogMap + cPCA + τ scaling are needed

None of these are fatal to Version B. They explain why Version A is uncertain.

---

## A2: Hierarchy Direction Problem (the real bottleneck)

A1 failure = fallback to Euclidean cone. Still works.
A2 failure = cone has no direction, drift has no polarity. dD_C still computes, but "drifting toward what" is unanswerable.

**Root cause:** BGE-M3 trained on (query, relevant_doc) pairs — topic relevance only.
"Abstract ↔ specific" dimension was never in the supervision signal.
Hierarchy in BGE-M3 is an accidental side-effect, not a designed feature.
You are not "extracting" hierarchy — you are **defining** an operational hierarchy direction and injecting it.

### Three routes by engineering cost

| Route | Method | Cost | Est. success |
|---|---|---|---|
| 1 | Pure gcPCA (hope it works) | 0 | 20-30% |
| **2** | **30 calibration pairs (human expert)** | **1 hour** | **60-70% ← best ROI** |
| 3b | LLM oracle (500 neighbors, Ridge fit) | half day | 70-80% |
| 3c | Structural proxy (citation count, term density) | 1 day | medium |

### Route 2: 30 calibration pairs (do this first)

```python
calibration_pairs = [
    ("scheduler", "CFS bandwidth control"),
    ("memory management", "slab allocator NUMA balancing"),
    ("networking", "TCP BBR congestion control"),
    # ... 30 pairs, kernel engineer lists in 1 hour
]

# Compute hierarchy direction in BGE-M3 tangent space
directions = []
for general, specific in calibration_pairs:
    v_g = sphere_logmap(anchor_C, bge_embed(general))
    v_s = sphere_logmap(anchor_C, bge_embed(specific))
    d = (v_s - v_g); directions.append(d / np.linalg.norm(d))

hierarchy_axis = np.mean(directions, axis=0)
hierarchy_axis /= np.linalg.norm(hierarchy_axis)

# Find which gcPCA eigenvector aligns best
alignment = D_star @ hierarchy_axis
best_idx = np.argmax(np.abs(alignment))
tau_hat = np.sign(alignment[best_idx]) * D_star[best_idx]
```

### Test 8: hierarchy direction validation (add to Milestone 0, 30 min)

```
1. List 30 (general, specific) pairs (done before 6/1)
2. Compute three candidate directions:
   v_cPCA  = top gcPCA eigenvector (route 1)
   v_calib = mean(specific - general) from 30 pairs (route 2)
   v_LLM   = Ridge fit on LLM hierarchy scores of 500 neighbors (route 3b)
3. Hold out 10 pairs
4. Ranking accuracy on hold-out: <specific - general, v> > 0
5. Pick best v as τ̂

Decision:
  any v > 70% accuracy → use it
  all v < 70%           → hierarchy is not recoverable from BGE-M3
                          → drop polarity σ_C from paper
                          → cone becomes directionless (detect voids but not "future" vs "past")
```

### Correct paper framing (honest)

```
WRONG: "BGE-M3 contains latent hierarchical structure that our method extracts"

RIGHT: "We define an operational hierarchy direction by combining BGE-M3's local geometry
        with calibration pairs as weak supervision. This direction constructs
        anchor-conditioned entailment cones."
```

Second framing is stronger — reviewer cannot attack "unverified assumption" because there is no assumption. You use weak supervision to define, not discover.

### Key reframe: "upgrading" not "failing"

Your paradigm already accepts that pure embedding is insufficient (anchor = external grounding).
Hierarchy calibration = same kind of move: BGE-M3 + external grounding.
This is the direction the paradigm points, not a retreat from it.

"Upgraded from closed system (embedding only) to open system (embedding + domain expert grounding)"
= consistent with observer-relative design throughout.

### Start today (before 6/1)

List the 30 calibration pairs for Linux kernel. Takes 30 minutes.
Gives you Test 8 data on 6/1, and fallback τ̂ if gcPCA fails.

---

## Strategic Pivot: LLM as Hierarchy Oracle (2026-05-22)

### The decision

gcPCA hierarchy extraction: **systematically fails** (not noisily).
Rayleigh quotient proof: sibling axes always dominate hierarchy axes.
LLM-as-oracle: **only affordable high-density directional semantic source**.

Paper 3 pivots from "mathematical paper with 2 silent failure risks"
to "engineering paper with 1 verifiable experiment."

### What changes

| Dimension | Before (math-heavy) | After (LLM-hybrid) |
|---|---|---|
| Risk type | 2 silent assumptions | 1 measurable experiment |
| Engineering complexity | High (Lorentz + 7 fixes) | Low (LLM call + Ridge) |
| Time to ship | 6 months | 3-4 months |
| Reviewer attack surface | Large (every fix = attack) | Focused (LLM choice + benchmark) |
| Reproducibility | cPCA sensitive to k-NN choice | Open-weights + frozen + public benchmark |

### What gets dropped from anchor_drift_metric.md (~60% of content)

- All Lorentz ExpMap / hyperbolic lifting complexity
- τ scaling sweep and Gromov δ calibration
- Mixed-curvature ℍ^k × R^(1023-k) geometry
- All τ̂ / cone direction debate (3 conflicting versions)
- Entailment cone hyperbolic formula (Ganea 2018)
- Cartan formalism / HypLoRA / fine-tuning fallbacks
- Fix 2 (Minkowski cone), Fix 11 (3-layer Lorentz separation)

### What the paper still says about hyperbolic (framing)

> "Entailment cone structure is most naturally expressed in hyperbolic geometry
> (Ganea 2018). However, contrastive embedders (BGE-M3) trained with InfoNCE
> enforce spherical uniformity, incompatible with hyperbolic structure
> (Wang & Isola 2020). We circumvent this by using a large language model
> to provide hierarchical supervision directly in tangent space.
> This preserves directional semantics without hyperbolic implementation debt."

You keep the depth, drop the debt.

### The architecture that emerges

```
BGE-M3 (geometric substrate):  fast, cheap, indexable, 95% of compute
LLM (semantic operator):        slow, expensive, but provides direction
Anchor (scope control):         LLM calls only on k-NN neighborhood
Event-driven (cost amortization): LLM triggered only when needed
```

Each component does what it's designed for. Clean separation of concerns.
LLM = directional semantic operator. NOT: retrieval, distance metric, anchor selection.

### Revised Milestone 0 (6/1-6/3)

```
Day 1 AM:  List 200 (general, specific) pairs — you alone, 3 hours
Day 1 PM:  Run open-source LLM benchmark (Copilot CLI)
Day 2 AM:  Run commercial LLM models
Day 2 PM:  gcPCA + density + Procrustes baselines
Day 3 AM:  Analysis, Pareto curve, pick production model
Day 3 PM:  Commit + LKHJB v1 to Zenodo
```

Output by 6/3:
- LKHJB benchmark (standalone arXiv candidate)
- Production model confirmed
- Paper 3 narrative locked
- Zero hyperbolic math debt

### Do not let LLM become a maximalist solution

```
LLM is correct for:
  - hierarchy direction (paradigm justification: only source of directional semantics)
  - (general, specific) pair annotation
  - void candidate final ranking
  - RFC outcome explanation

LLM is wrong for:
  - dense corpus retrieval (too expensive)
  - drift distance metric (LLM doesn't produce metrics)
  - anchor selection (anchor = human expert grounding)
  - event detection (time-axis structure, not LLM domain)
```

LLM = "directional semantic operator." Keep this boundary or contribution blurs.

### Why this is the right time (2026)

```
2017-2022: encoder is everything
2023-2024: encoder + LLM rerank (RAG era)
2025-2026: encoder as substrate + LLM as semantic operator  ← you are here
2026-2027: LLM-native retrieval
```

Paper 3 sits exactly at the inflection point.
BGE-M3 + LLM hybrid is not behind the curve — it is the curve.

---

## Paradigm Lock-In: Lifted Retrieval (2026-05-22)

**Codename for the 6-year program.**

All papers share one architecture:
- BGE-M3: continuous geometric substrate (cheap, indexable, fast)
- LLM: directional semantic operator (expensive, but anchor-constrained)
- Anchor: limits LLM cost to semantically hot regions
- Event-driven: amortizes LLM cost over time

This is one paradigm — **Lifted Retrieval** — with multiple operator instantiations.

### Operator algebra

```
AnchorConditionedLLMOperator(anchor C, neighborhood N_C, operator_type T) → signal

Paper 1 TVA:  T = void_judge      (is this void semantically meaningful?)
Paper 2 TVV:  T = void_validate   (does this void actually exist?)
Paper 3 DTVA: T = hierarchy_score (what is the abstraction depth?)
Paper 4:      formalize {T_1, T_2, T_3, ...} as operator algebra
Paper 5:      T = semantic_density_estimate (gravitational lensing)
```

### Why LLM is architecturally necessary (not just convenient)

InfoNCE (contrastive loss used by BGE-M3) is symmetric: cos(a,b) = cos(b,a).
Symmetric training cannot encode asymmetric relations (hierarchy, entailment, causality).
This is fundamental impossibility, not implementation failure. (Wang & Isola 2020)

LLMs trained autoregressively see "X is-a Y", "X implements Y", "X causes Y".
They naturally encode asymmetric directional semantics.

**Reviewer response to "why not fine-tune encoder":
"No encoder trained with symmetric contrastive loss can encode asymmetric
semantic relations, by Wang-Isola theorem. LLM-as-operator is architectural
necessity, not engineering choice."**

### Paradigm name: Lifted Retrieval

"Lifted" has precise mathematical meaning: mapping from base space to total space.
BGE-M3 = base space (topical proximity, continuous)
LLM operator = lifting to total space (directional semantics, discrete)

Proposed Paper 4 subtitle:
"Lifted Retrieval: A Paradigm for LLM-Conditioned Geometric Information Retrieval"

LKHJB benchmark rename:
"LKHJB: A Benchmark for LLM-as-Hierarchy-Oracle in Specialized Technical Domains"

### 6-year program re-positioned

| Year | Paper | Lifted Retrieval role |
|---|---|---|
| 2024 | TVA | First LLM-as-void-judge application |
| 2025 | TVV | Proves LLM-lift necessary for void validation |
| 2026 | D-TVA | LLM-as-hierarchy-oracle for drift |
| 2026 Q4 | Framework | Lifted Retrieval: unify the paradigm |
| 2028 | Lensing | LLM-as-semantic-lens for density inversion |

### Window

LLM-augmented IR: people are fine-tuning encoders, building rerankers, doing RAG.
Nobody is using LLM as anchor-conditioned directional semantic operator.
A2 deep research report didn't even list it as a primary alternative.
Window: ~12-18 months before someone else defines this paradigm.

### What to retrofit into Paper 1/2 if still in revision

Add one sentence to abstract:
> "Following the Lifted Retrieval paradigm, we use a large language model as
> an anchor-conditioned void judgement operator over BGE-M3 neighborhoods."

Creates paradigm consistency across all three papers when Paper 3 cites them.

---

## Paradigm Recognition Moment (2026-05-22)

Three papers in, the pattern is undeniable:
- Paper 1 (TVA, 2024): LLM judges void semantic meaningfulness
- Paper 2 (TVV, 2025): LLM validates void real-world existence
- Paper 3 (D-TVA, 2026): LLM provides hierarchy direction

**Not planned. Discovered.** Each paper, I reached for LLM at the exact
point where BGE-M3 hit its symmetric-contrastive ceiling.
Three independent reaches → same architectural solution → not coincidence.

Paper 1+2 not retrofitted — they remain as discovered.
Paper 3 is the conscious naming moment.
Paper 4 will formalize the operator algebra.

### How to write this in Paper 3 (exact language)

> "Across three independent systems developed over 2025-2026, we found ourselves
> repeatedly reaching for the same architectural solution: a large language model
> as an anchor-conditioned operator over a dense embedding neighborhood. In each
> system, we arrived at this pattern empirically, driven by the specific problem
> at hand. Only in retrospect did we recognize that these are not three solutions
> but one paradigm, which we name **Lifted Retrieval**."

"Found ourselves repeatedly reaching for" — passive, honest, not marketing.
"Only in retrospect" — marks the naming moment explicitly.
Readers who know paradigm history will recognize the pattern immediately.

### Why not retrofitting Paper 1+2 is stronger

Retrofitting would look like post-hoc branding.
Letting Paper 1+2 stand as organic exploration means:
- Paper 3 "in retrospect" has historical weight
- Paper 4 is "formalizing what was discovered organically" — maximum credibility
- Narrative arc: exploration → recognition → naming → formalization
  This is the standard paradigm formation arc (Shannon, LSA, Transformer attention)

### Draft Paper 3 abstract paragraph

> "We propose Lifted Retrieval, a paradigm in which a dense encoder provides
> a continuous geometric substrate, an anchor restricts attention to a local
> neighborhood, and a large language model acts as a directional semantic
> operator. Anchor conditioning is essential: it constrains LLM inference to
> semantically hot regions, making the architecture deployable at corpus scale.
>
> In retrospect, our prior work on void taxonomy [1] and void validation [2]
> also instantiate this paradigm under different operator choices; we formalize
> the full operator algebra in forthcoming work [4]."
