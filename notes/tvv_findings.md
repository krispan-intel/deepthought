# TVV Experiment Findings

*2026-05-13. Kris Pan.*

## Summary

Raw fill rate is the wrong metric for TVA validation.
Role-aware epistemic classification reveals TVA's true advantage.

---

## Anchor-Gating Diagnostics (t5)

Val papers' mean cosine similarity to Anchors = **0.52** (std=0.047).
At threshold 0.65, only 1% of val papers pass → gate too strict, almost nothing fills.

Corpus-aware hybrid gate: `τ_C = max(Q80_val, Q_q_train)`

| Gate | TVA | Baseline | Lift | Val pass rate |
|---|---|---|---|---|
| Raw | 28% | 36% | 0.78x | 100% |
| Fixed 0.55 | 27% | 35% | 0.78x | ~25% |
| Fixed 0.65 | 13% | 20% | 0.65x | ~1% |
| Hybrid Q90 (floor≈0.58) | 27% | 35% | 0.78x | 5-7% |

**Key finding:** Domain-filtered val corpus (cs.OS/AR/PL/SE) already limits semantic diversity. Further Anchor-gating (hybrid Q90) passes only 5-7% of val papers but converges to same lift as raw because the gate is still too narrow to discriminate TVA from baseline.

Fixed 0.65 shows discriminative effect (0.65x lift) but at the cost of near-zero pass rate — the gate is filtering out real fills alongside noise.

**Implication — Anchor Exposure Problem:**

Anchor-gating reveals a deeper issue: **fill rate is exposure-limited** when the Anchor-gated validation set is small.

When hybrid q90 gate passes only 5-7% of val papers, an unfilled void has three possible explanations:
1. The void is genuinely not filled
2. The void is filled but not in this validation corpus/window
3. The Anchor-relevant future papers are too few to observe fill (*underexposure*)

These cannot be distinguished from fill rate alone.

**Raw fill rate conflates three factors: geometric proximity, research momentum, and Anchor exposure.**

Anchor-gating separates Anchor exposure from midpoint proximity.
Role-aware classification separates epistemic fill from geometric false positive.

**Three-layer validation framework:**

| Layer | Metric | What it measures |
|---|---|---|
| Geometric | Raw fill rate | Is any future paper near the midpoint? |
| Eligibility | Anchor val pass rate | Does the validation window have enough Anchor-relevant evidence? |
| Epistemic | Role-aware fill score | Is the nearby paper actually doing epistemic work? |

**Minimum exposure threshold:** If Anchor-gated val papers < N_min or pass_rate < 10%, fill result should be marked as *underexposed*, not as evidence of void invalidity.

---

## Fill Rate: Final Conclusion (2026-05-19)

Raw fill rate is a diagnostic metric only, not a validation target.

### t5 with B2 density-matched baseline

| Method | Raw fill | vs TVA |
|---|---:|---|
| TVA | 28% | — |
| B1 hot-zone baseline | 36% | TVA 0.78x |
| **B2 density-matched** | **25%** | **TVA 1.12x** |

**B1 shows the confound. B2 shows the corrected comparison.**

B1 is biased toward high-density / high-momentum regions. When controlled for local historical density (B2), TVA achieves a modest positive lift. The apparent 0.78x raw underperformance is entirely explained by density bias.

**Paper 2 claim:**
> Raw fill rate is strongly confounded by local density and research momentum. After density matching, TVA no longer underperforms the baseline. This motivates a shift from raw occupancy metrics to role-aware epistemic validation.

### Paper 2 Three Findings

**Finding 1: Raw fill is density-confounded**
- TVA 28%, B1 hot-zone 36%, B2 density-matched 25%
- Hot-zone baseline inflates raw fill; density matching reverses apparent disadvantage

**Finding 2: Anchor-gating reveals observability limits**
- Hybrid gate pass rate 5–7%; mean sim_to_anchor ~0.52
- Anchor eligibility is sparse; corpus exposure is limiting
- Unfilled voids = right-censored, not invalid

**Finding 3: Role-aware classification estimates epistemic precision**
- TVA vs B2 on TRUE_FILL / PARTIAL_FILL / FALSE_POSITIVE distribution
- (to be completed after role classification runs)

### Closing sentence for fill rate section

> We therefore do not use raw fill rate as the final validation target. Its main role is diagnostic: it reveals how much of apparent future occupancy is explained by local density and research momentum. After density matching, TVA no longer underperforms the baseline, motivating a shift from raw occupancy metrics to role-aware epistemic validation.

### Reverse TVA / D-TVA (Future Work only)

Do NOT expand Reverse TVA into Paper 2 main contribution. One paragraph in Discussion/Future Work:

> The results suggest a natural dynamic extension: instead of asking whether a predicted void is eventually filled, one can classify each newly arriving paper by its pre-insertion topological effect on the knowledge space. This dynamic formulation, which treats vacancy as a temporal lock, is left to future work.

---

## Rolling Temporal Validation Results

Three temporal splits, 10 anchors × 30 voids = 300 TVA candidates per split.

| Split | Train corpus | Val window | TVA fill rate | Baseline fill rate | Lift |
|---|---|---|---|---|---|
| t3 | < 2014 | 2015–2020 | 30.7% | 31.5% | **0.97x** |
| t4 | < 2016 | 2017–2022 | 26.0% | 32.5% | 0.80x |
| t5 | < 2018 | 2019–2024 | 27.7% | 35.5% | 0.78x |

**Key observation:** Baseline fill rate increases over time (31.5% → 35.5%) as recent corpora are denser and anchor-nearby regions are more frequently covered by new papers. TVA fill rate remains lower and more stable.

**Interpretation:** The widening gap from t3 to t5 is not evidence of TVA failure. It reflects that baseline samples increasingly capture high-momentum research continuations, while TVA candidates remain in lower-momentum but potentially more novel regions.

t3 is nearly tied (0.97x lift) — in the 2015-2020 window, the research landscape was less densely covered, so the hot-region advantage of baseline was smaller.

**This confirms:** raw fill rate is a proxy for research momentum, not void quality. The trend across splits strengthens this interpretation.

t1 and t2 not yet run. All three splits above use raw fill metric (no anchor-gating). See Anchor-Gating Diagnostics section for gated results on t5.

---

## Pilot Experiment Setup (original 6-anchor run)

- **Train corpus:** arXiv cs.OS/AR/PL/SE/DC/NI/CR, t < 2019 (~28 years, 34,591 papers)
- **Val corpus:** same categories, t ≥ 2019 (~5 years, 51,492 papers)
- **TVA voids:** 6 anchors × 10 voids = 60 candidates
- **Baseline:** anchor-nearby random pairs (top-300 C1 pool)

---

## Result 1: Raw fill rate — TVA loses

| | TVA | Baseline | Lift |
|---|---|---|---|
| Fill rate (threshold 0.82) | 13/60 = 21.7% | 65/198 = 32.8% | 0.66x |
| Fisher p | 0.97 | | not significant |

**Interpretation:** Raw fill rate rewards research momentum (proximity to ongoing work). Baseline wins because it samples from hot regions near the anchor.

---

## Result 2: Novelty vs fill probability — strong negative correlation

| Novelty quartile | Fill rate |
|---|---|
| Q1 (lowest) | 60% |
| Q2 | 13% |
| Q3 | 13% |
| Q4 (highest) | 0% |

**Interpretation:** Higher novelty → lower near-term fill probability. True voids are rare events that persist over time.

---

## Result 3: Epistemic role classification — TVA wins

| Role | TVA (n=13) | Baseline (n=34) |
|---|---|---|
| FALSE_POSITIVE | 6 (46%) | 25 (74%) |
| INCREMENTAL_EXTENSION | 4 (31%) | 2 (6%) |
| PARTIAL_FILL | 2 (15%) | 1 (3%) |
| SURVEY_OR_NAMING | 1 (8%) | 6 (18%) |

**Role-aware fill score: TVA 0.192 vs Baseline 0.085 = 2.25x lift**

Baseline's high fill rate is 74% false positive — geometrically close but epistemically irrelevant.

---

## Core Finding

> **Raw fill rate measures research momentum, not void quality.**

More precisely: raw fill rate is a property of the interaction between TVA candidates and the human research ecosystem within a time window. It is not a direct measure of void validity.

TVA does not "sacrifice" fill rate — it selects different regions of knowledge space. Those regions exhibit lower observed near-term fill frequency because they are less aligned with current research momentum. Whether that is good or bad depends on what you want: if you want to predict the next incremental paper, baseline wins. If you want to find non-obvious gaps, TVA's lower fill rate may indicate it is looking in the right places.

**The correct framing:**
Raw fill rate conflates void quality with sociotechnical realization rate — whether the human research community happened to walk in that direction within the validation window. These are distinct quantities.

This is Paper 2's core finding, not a claim that TVA is better.

---

## What This Motivates

1. **Epistemic role classification** is necessary for void validation
2. **Raw fill rate is a biased metric** — unsuitable as primary TVA validation
3. **True voids are rare events** — cannot be validated with large-sample frequency statistics
4. **D-TVA** needs to track void lifecycle (fill, partial fill, collapse, support) not just presence/absence
5. **Role-aware drift metric D_C** should weight epistemic events, not count fills

---

## Scale Required for Strong Claims

Current experiment is pilot-scale only. For publishable results:

| Parameter | Current | Target |
|---|---|---|
| Anchors | 6 | 50–100 |
| Voids per anchor | 10 | 50–100 |
| Total voids | 60 | 2,500–5,000 |
| Val horizon | 5 years | rolling windows (5×) |
| Domains | cs.OS/AR/PL/SE | + cs.AI/LG/CL/CV, materials, bio |

Rolling temporal windows needed:
- train < 2010, val 2011–2015
- train < 2012, val 2013–2017
- train < 2014, val 2015–2019
- train < 2016, val 2017–2021
- train < 2018, val 2019–2023

Baseline variants needed (reviewer will ask):
- B1: anchor-nearby random (current)
- B2: density-matched
- B3: pair-distance-matched
- B4: novelty-matched
- B5: hot-zone continuation

## Limitations

- Small sample: 13 TVA filled cases
- Single domain (cs.OS/AR/PL family)
- 5-year validation window may be too short for hard voids
- LLM role classification based on abstracts only (no full text)
- Role classification by single LLM (no inter-rater reliability)

---

## Paper 2 Framing

**Title candidate:** *Validating Topological Void Analysis: Why Raw Fill Rate Fails and What Role-Aware Metrics Reveal*

**Core argument:**
1. We attempted temporal fill rate validation
2. Raw fill rate favors research momentum, not void novelty
3. Epistemic role classification reveals TVA's true advantage (2.25x role-aware lift)
4. True voids are rare events requiring longitudinal, role-aware validation
5. This motivates Dynamic TVA (D-TVA) as the proper framework

---

## Deeper Observation (not yet in paper)

*2026-05-13. Kris Pan.*

Fill rate contains an unexamined assumption:

> **Fill velocity is assumed to be human research velocity.**

When TVA is both the void-finder and the void-filler, this assumption collapses.

| | Find speed | Fill measurement speed |
|---|---|---|
| Human | slow | slow (wait for papers) |
| TVA | orders of magnitude faster | forced to wait for human papers |

The 21.7% vs 32.8% comparison may not be a quality trade-off.
It may be a **temporal-scale mismatch** — TVA's fill metric is measured on a human timescale that doesn't apply to machine-speed discovery.

More precisely:
- Human fill rate: 0.46 true fills / year across 28 years
- TVA find rate: 60 void candidates in seconds
- TVA-as-filler: would close voids in seconds, not years

If finder and filler are both TVA, fill rate loses its meaning as a comparative metric.

The correct question becomes: **from void discovery to void fill, how long does it take?** For TVA, this could be seconds. The 21.7% reflects human-speed fill measurement applied to machine-speed discovery.

**Implication:** Fill rate is a human-centric metric. It measures research momentum at human velocity. TVA operates outside this timescale.

**Decision pending:** whether and how to include this in Paper 2 framing.

---

---

## Paper 2 Architecture (from deep research synthesis — 2026-05-19)

### Core claim
> Temporal validation of predicted voids must distinguish geometric closure from epistemic closure.

### Three-layer fill predicate (formal)

```
ValidatedFill(P_t, V, q) = G(P_t, m) ∧ E(P_t, q) ∧ R(P_t, A, B, q)
```

| Layer | Predicate | Measures |
|---|---|---|
| G — Geometric | sim(P_t, midpoint) > τ_fill | Is any future paper near the midpoint? |
| E — Eligibility | sim(P_t, anchor) > τ_anchor | Is P_t in the anchor's problem domain? |
| R — Epistemic | role-aware classification | Does P_t actually fill the gap? |

### Three topological event types (for role classification)

| Event type | Definition | Role mapping |
|---|---|---|
| VOID_FILL | P_t lands in previously vacant midpoint region (C4 was satisfied before P_t) | TRUE_FILL, PARTIAL_FILL |
| BOUNDARY_EXPANSION | P_t extends frontier without bridging the gap | INCREMENTAL_EXTENSION, SUPPORT_EVIDENCE |
| DENSIFICATION | P_t falls in already occupied region, no new structure | FALSE_POSITIVE, SURVEY_OR_NAMING |

### C4 Vacancy Lock / First-Filler Principle

TVV exploits C4 as a temporal mutex:

> The vacancy condition is evaluated against DB_{t-1} (corpus *before* P_t is inserted).
> The first paper to satisfy midpoint vacancy for a given void receives the Void-Filler label.
> Later papers entering the same region fail the C4 check and are downgraded to Boundary Expansion or Densification.

This solves the reflexivity problem: after a breakthrough paper, follow-on papers cluster near the filled region but C4 is already broken, so they are automatically classified as non-fills.

Formal statement:
```
VoidFiller(P_t, V) iff:
  G(P_t, m) ∧ C4_pre(m, DB_{t-1})  [midpoint was vacant before P_t]
```

Where `C4_pre(m, DB_{t-1})` = no paper in DB_{t-1} within radius θ_v of midpoint m.

### Limitations to state explicitly

1. **Midpoint ≠ void center**: SLERP(A,B) is a geometric midpoint, not the topological center of the void. This is a known approximation.
2. **Operational vacancy, not β₂ homology**: TVA defines an operational local-vacancy predicate, not persistent homology. "Topological" is used operationally.
3. **BGE-M3 as coordinate system only**: BGE-M3 provides the embedding space; all void predicates and validation operators are external.
4. **ANN approximate radius search**: C4 vacancy check via approximate NN is probabilistic, not exact.

### Key sentence for Paper 2 intro

> Prior LBD systems treat the future appearance of a predicted association as validation success. TVA validation requires a stricter notion: whether a future paper plays an epistemic bridging role relative to an Anchor-conditioned void.

### Useful references from topological_research.md

- [46] "From Topology to Retrieval: Decoding Embedding Spaces with Unified Signatures" (arxiv 2511.22150) — supports Anchor-local geometry predicts fill quality
- [5] TDA Applications in NLP Survey (arxiv 2411.10298) — related work starting point
- [17] TDA Engine v1.0 for Structural Voids — DTM filtration in practice

---

---

## Reverse TVA Framing (2026-05-19)

### The key insight

Original framing (void-centered, hard):
```
TVA predicts voids.
TVV checks whether future papers fill them.
```

Problem: unknown observability — if void is not filled, you cannot distinguish:
- void is invalid
- corpus has no coverage
- window too short
- anchor too narrow
- embedding missed it

Reverse TVA (paper-centered, tractable):
```
TVA defines what a void is.
Reverse TVV asks: given a new paper P_t, is it the first occupant of a previously vacant bridge region?
```

You go from "searching for fillers" to "classifying incoming papers". This is a **streaming local impact classifier**, not a global future-search problem.

### Three topological events (Reverse TVA)

```
1. DENSIFICATION       — P_t falls in already-dense region; no new structure
2. BOUNDARY_EXPANSION  — P_t extends one direction but does not bridge gap
3. VOID_FILL           — P_t is first to occupy vacant midpoint between A, B
4. OUT_OF_DOMAIN       — P_t not in Anchor's problem space
```

### C4 becomes the core, not a side condition

For a new paper P_t:
1. Retrieve local historical neighborhood N_t from DB_{t-1}
2. Find candidate bridge pair (A, B): both near P_t, but A-B dissimilar
3. Compute midpoint m(A, B) via SLERP
4. Check vacancy: was m(A,B) empty in DB_{t-1}? (C4 pre-insertion check)
5. If vacant AND P_t near m(A,B) → CANDIDATE_VOID_FILL
6. Insert P_t into DB → C4 broken for all future papers near same region

Complexity: O(k²) local pair search, not O(|voids| × |future corpus|).

### Reverse TVA online algorithm

```
Input:  DB_{t-1}, new paper P_t, optional Anchor q
Output: event_label ∈ {DENSIFICATION, BOUNDARY_EXPANSION, CANDIDATE_VOID_FILL, OUT_OF_DOMAIN}

1. embed(P_t)
2. N_t = kNN(P_t, DB_{t-1}, k=50)
3. local_density = mean sim of P_t to N_t
4. for (A,B) in candidate_pairs(N_t):
     bridge_score = sim(P,A) + sim(P,B) - 1.5*sim(A,B)
5. best (A,B) = argmax bridge_score
6. m = slerp(A, B)
7. vacancy = (kNN(m, DB_{t-1}, k=5).max_sim < θ_vacant)
8. classify:
   if local_density > θ_dense → DENSIFICATION
   elif not vacancy → BOUNDARY_EXPANSION
   elif sim(P_t, m) > θ_fill → CANDIDATE_VOID_FILL
   else → BOUNDARY_EXPANSION
9. [optional] role-aware LLM verification for CANDIDATE_VOID_FILL
10. insert P_t into DB
```

### Pipeline: still 3 stages, but cheaper

```
Stage 1 (geometric): Reverse TVA classifier → event_label
Stage 2 (eligibility): Anchor gate on P_t
Stage 3 (epistemic): LLM role-aware only on CANDIDATE_VOID_FILL cases
```

LLM cost drops dramatically because Stage 3 only runs on candidates, not all papers.

### Paper 2 title candidate (revised)

> Topological Void Validation: A Reverse TVA Framework for Classifying Scientific Papers as Void-Filling, Boundary-Expanding, or Densifying Events

### Relationship to current temporal validation experiments

The current t1-t5 rolling validation is still valid as **retrospective ground truth generation**:
- Run Reverse TVA offline on historical splits
- Use LLM role classification to label the results
- Use these labels to calibrate θ_vacant, θ_fill, θ_dense thresholds
- Then evaluate how well Reverse TVA predicts the LLM labels (precision/recall)

The temporal split work is not wasted — it becomes the **calibration and evaluation corpus** for the Reverse TVA classifier.

---

---

## Problem Redefinition (2026-05-19)

### Why the original formulation was stuck

Original question:
> Does the void TVA found get filled by a future paper?

Hidden dependencies that couldn't be controlled:
- Does anyone research this direction?
- Does the corpus cover it?
- Is the window long enough?
- Is the paper in the same Anchor domain?
- Does the embedding capture it?
- Is the baseline sitting in a hot zone?

Result: any null finding could be void invalid, corpus gap, window too short, threshold wrong, or baseline unfair. Can't distinguish.

### Correct problem definition

New question:
> Given a new paper P_t and the corpus that existed before it (DB_{t-1}), what kind of topological event did P_t induce?

This is **local impact classification**, not global future search.

Inputs are controlled: DB_{t-1} is fixed, P_t is observed, time ordering is clear.

### Formal definition of Reverse TVA

> Reverse TVA classifies a newly observed paper by the topological event it induces on the pre-existing knowledge space: densifying an occupied region, expanding a frontier, or occupying a previously vacant bridge between historically separated concepts.

### Forward vs Reverse

```
Forward TVA:
  Given DB_t and Anchor q → find candidate voids

Reverse TVA:
  Given DB_{t-1} and new paper P_t → classify event(P_t | DB_{t-1})
```

Forward TVA asks: **Where might innovation occur?**
Reverse TVA asks: **What kind of innovation did this paper represent when it appeared?**

### Research Questions for Paper 2

**RQ1:**
> Given a time-ordered stream of scientific papers and a fixed embedding-based knowledge space, can we classify each newly arriving paper as a densification, boundary expansion, or candidate void-filling event relative to the corpus that existed before it?

**RQ2:**
> Among geometrically detected candidate void-filling events, how many survive role-aware epistemic validation?

### Two-layer output (stable taxonomy)

```
Geometric event layer:
  DENSIFICATION          — P_t falls in already-dense region
  BOUNDARY_EXPANSION     — P_t extends one direction, no bridge
  CANDIDATE_VOID_FILL    — P_t first to occupy vacant bridge region

Epistemic role layer (LLM validation, sampled):
  TRUE_FILL / PARTIAL_FILL / INCREMENTAL / BENCHMARK / FALSE_POSITIVE
```

Do NOT call CANDIDATE_VOID_FILL a "breakthrough" — it is a geometric event pending epistemic confirmation.

---

## Implementation Roadmap (Paper 2 experiments — 2026-05-19)

### DONE
- [x] Rolling t1-t5 splits with raw, fixed-gate, hybrid-gate fill rates
- [x] Anchor exposure diagnostics (val pass rates per anchor per split)
- [x] Density-matched baseline (B2) added to run_rolling_validation.py
- [x] 5-group case sampling: G1 tva(gated), G2 b1(gated), G3 tva(raw_only), G4 b1(raw_only), G5 tva(near_miss)
- [x] Role classification prompt with overclaiming rubric: problem_conclusion_alignment, claim_evidence_strength, overclaiming_risk
- [x] t5 role classification (old cases, 154 total)

### TODO — NEXT
- [ ] **t5 rerun** with new 5-group cases (running now)
- [ ] **Role classification on new t5 cases** — include G3/G4/G5 groups
- [ ] **Add `topological_event_type` field** to role classification prompt: VOID_FILL / BOUNDARY_EXPANSION / DENSIFICATION
- [ ] **Anchor exposure table** — per anchor per split: n_future, mean_sim, q90_sim, pass_rate, tva_raw_fill, b1_raw_fill
- [ ] **t3/t4 role classification** — run on existing filled_cases_raw.jsonl
- [ ] **Case studies** — pick 3-5 strong TRUE_FILL from TVA, compare with FALSE_POSITIVE from baseline, include citation count

### TODO — LATER (Paper 2 writing)
- [ ] Formalize C4 vacancy lock as Definition 1
- [ ] Write LBD retrospective validation as related work frame
- [ ] Add right-censoring framing to unfilled voids: "unfilled within window ≠ invalid void"
- [ ] Survival analysis as future work (not main claim)

---

## Open Questions (for Paper 3 / D-TVA)

- How does D_C (anchor-relative drift) correlate with void lifecycle events?
- Can we detect void formation before it's visible in the corpus?
- What is the distribution of void lifetimes (time from formation to fill)?
- Does void velocity predict fill quality?
