---
# Paper 3: Experiment Design in Plain Language
# Distilled 2026-05-22
---

## One sentence

Track how the "knowledge center" of each Linux kernel subsystem moves over
25 years, and verify whether this movement predicts RFC outcomes.

## Three-layer analogy

**Anchor** = pick a shelf in a library ("scheduler").
  The shelf's 500 closest books = current state of that topic.

**Drift** = 5 years later, those 500 books have changed.
  How much they changed = drift magnitude.
  Which direction (more abstract vs more specific) = drift polarity.

**Why LLM** = BGE-M3 sees position but not direction (symmetric = can't encode
  hierarchy). LLM sees direction. BGE-M3 = eyes. LLM = inner ear.
  Anchor = where you stand. Event = time step.

## Three experiment purposes

**Purpose 1 (minimum):** Can we compute a number dD_C(t1,t2) that is small
for noise and large for paradigm shifts?

**Purpose 2 (core):** Does the drift trajectory before RFC event E predict
whether E gets merged / rejected / stalled?

**Purpose 3 (paradigm):** Does LLM >> cPCA >> cosine on prediction accuracy,
and is the LLM advantage explained by the Wang-Isola symmetric-contrastive
ceiling (not just "LLM is smarter")?

## Phase by phase

### Phase 0: LLM benchmark (6/1-6/3, 2 days, ~$500)
- List 200 (general, specific) pairs across 8 kernel subsystems
- Run 12 LLMs via Copilot CLI, pairwise hierarchy judge
- Compare: gcPCA ~65%, LLM ≥ 80% (expected)
- Pick production model (expected: Qwen-2.5-72B)
- Release LKHJB v1 to Zenodo (standalone mini contribution)

### Phase 1: Corpus prep (2 weeks)
- Scrape lore.kernel.org (1995-2026, ~1M emails)
- Filter [RFC] threads (~5-10K events)
- Label 6-class outcomes (cross-ref git log)
- BGE-M3 embed → vector DB

### Phase 2: Anchor + hierarchy (1 week)
- Select anchor per subsystem (maintainer mean embedding)
- LLM-score 500 neighbors → Ridge regression → hierarchy axis û_h
- gcPCA → D* subspace (for BW drift computation)

### Phase 3: Drift computation (1 week)
- S_C(t) = Gaussian(μ_C(t), Σ_C(t)) over anchor k-NN in K_{<t}
- dD_C = Bures-Wasserstein distance (closed form, Euclidean)
- σ_C = sign(<Δμ, û_h>) (polarity: toward specific or toward general)

### Phase 4: Event-driven prediction (ongoing)
For each RFC event E at time t (chronological):
  - Build everything from K_{<t} only (strict temporal cut)
  - Predict outcome using drift trajectory
  - Record (prediction, actual, hit, timestamp)
  Milestones: n=50 → workshop, n=200 → arXiv, n=500 → full paper

### Phase 5: Write paper (1 month)
- Figure 1: LKHJB benchmark table + cost-accuracy Pareto
- Figure 2: Cross-method axis cosine similarity heatmap (proves LLM finds different thing)
- Figure 3: Classic RFC drift trajectories (e.g., EAS 2013→2018)
- Table 1: Ablation (cosine / cPCA / full LR)
- Lifted Retrieval naming paragraph + Paper 1+2 retrospective

## Architecture diagram (Paper 3 Figure 1)

```
Linux Kernel Corpus (LKML 1995-2026, ~1M emails)
  │ BGE-M3 embed
  ▼
Dense Geometric Substrate (1024D)   ← continuous, cheap, indexable
  │ + Anchor (maintainer embedding)
  ▼
Local Neighborhood (k=500 around C)  ← constrains LLM cost
  │ + LLM Operator (Qwen-2.5-72B)
  ▼
Hierarchy Axis û_h                   ← directional semantics
                                       mathematically unavailable to BGE-M3
  │ + Sphere LogMap + gcPCA + BW
  ▼
Drift Metric dD_C(t1,t2)
  │ + Event-driven evaluation
  ▼
RFC Outcome Prediction
```

## Story arc

Problem: can dense embeddings track knowledge movement?
→ Cosine: sees position but not direction.
→ cPCA: mathematical proof it always finds sibling axis not hierarchy.
→ Hyperbolic lift: BGE-M3 globally spherical (InfoNCE), naive lift degenerates.

Key insight: hierarchy is asymmetric. InfoNCE is symmetric.
Fundamental impossibility (Wang-Isola 2020): no InfoNCE encoder can encode
asymmetric relations. Not a quality problem — structural impossibility.
→ Only path: outsource directional semantics to LLM.

Paradigm surfaces: third time writing LLM + anchor + dense encoder.
Not planned. Recognized. Named: **Lifted Retrieval**.

Validation: Linux RFC archive, event-driven, falsifiable.

## Narrative upgrade summary

Before: "We invented anchor-conditioned Lorentzian drift metric"
After: "We recognized the Lifted Retrieval paradigm; drift detection is its 3rd instance"

Complex math → established components + paradigm contribution.
Method paper → paradigm naming moment.
6 months ship → 3-4 months ship.
