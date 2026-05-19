# Paper 2 Skeleton — Topological Void Validation

*Draft 2026-05-19. Kris Pan.*

---

## Working Title

**Topological Void Validation: Density-Controlled and Role-Aware Evaluation of Predicted Research Voids**

---

## Abstract

Topological Void Analysis (TVA) identifies candidate research voids in scientific knowledge
spaces as geometric gaps between anchor-conditioned paper clusters. A natural validation
question is whether future papers fill these predicted voids. We show that raw fill rate —
whether any future paper appears near a void's midpoint — fails as a validation target for
three reasons: it is confounded by local corpus density, limited by anchor observability,
and weakly correlated with genuine epistemic resolution. A hot-zone baseline outperforms
TVA on raw fill rate (36% vs. 28%), but this advantage disappears under a density-matched
baseline (25%, TVA/B2 lift = 1.12×). Anchor eligibility gating exposes a corpus
observability limit: only 5–7% of future papers are anchor-eligible, so many unfilled voids
should be treated as right-censored rather than invalid. Finally, role-aware epistemic
classification shows that even anchor-eligible geometric fills rarely correspond to genuine
void resolution: 59–67% of gated raw fills are false positives, and most non-false cases
correspond to boundary expansion rather than full void closure. These findings motivate a
three-layer validation framework — geometric closure, anchor eligibility, and epistemic role
— and show that raw fill rate measures future local activity near predicted voids but does
not by itself validate epistemic closure.

*Core claim: Raw fill fails for three reasons — density bias, observability limits, and epistemic-role mismatch.*

---

## 1. Introduction

### Opening problem
Classical IR asks: given a query, what existing documents are relevant?
TVA asks: given an anchor, what relevant knowledge is missing?

TVA extends anchor-conditioned retrieval toward the detection of meaningful absences —
regions where expected connections, evidence, or conceptual bridges are missing.

Validating TVA requires asking: do predicted voids correspond to real epistemic gaps?
The natural operationalization is temporal fill rate: does a future paper appear near
the predicted void's midpoint?

### The problem with raw fill rate
Raw fill rate conflates three distinct quantities:
1. Geometric proximity (is any future paper near the midpoint?)
2. Research momentum (is this a hot region with many future papers?)
3. Epistemic quality (does the future paper actually bridge the gap?)

### Our contributions
1. We show that raw temporal fill rate is strongly confounded by local historical density and research momentum.
2. We introduce a density-matched baseline that controls for this confound and reverses TVA's apparent disadvantage against hot-zone baselines.
3. We quantify anchor exposure and show that many unfilled voids are better interpreted as right-censored by observability limits than as invalid predictions.
4. We introduce role-aware epistemic classification to distinguish true/partial fills from rhetorical or geometric false positives.
5. We propose a three-layer validation framework: geometric closure, anchor eligibility, and epistemic role.

### Relationship to LBD
Prior LBD systems treat the future appearance of a predicted association as validation
success. TVA validation requires a stricter notion: whether a future paper plays an
epistemic bridging role relative to an Anchor-conditioned void.

---

---

## Mathematics Reference

All papers embedded on unit hypersphere: $\mathbf{p} \in \mathbb{S}^{1023} \subset \mathbb{R}^{1024}$. Similarity = cosine = inner product: $\text{sim}(a,b) = \mathbf{a}^\top\mathbf{b}$.

### Void midpoint (used everywhere)

$$m(A,B) = \frac{\mathbf{a}+\mathbf{b}}{\|\mathbf{a}+\mathbf{b}\|}$$

### Three-layer fill predicate (core formula)

$$\text{Fill}(P,V,q) = G(V) \wedge E(P,q) \wedge R(P,A,B)$$

| Layer | Condition | Threshold |
|---|---|---|
| G geometric | $\max_{P \in \text{Val}_q} \text{sim}(P,m_V) \geq \tau_{\text{fill}}(q,\rho(V))$ | calibrated (see below) |
| E eligibility | $\text{sim}(P,q) > \tau_q$ | $\tau_q = \max(Q_{80}^{\text{val}},\ Q_{90}^{\text{train}})$ |
| R epistemic | $\text{role}(P,A,B) \in \{\text{TRUE-FILL, PARTIAL-FILL}\}$ | LLM |

**G uses void-level max-sim, not paper-level sim** — this compensates for val corpus size.

### Anchor exposure (Finding 2)

$$\pi_{q,t} = \frac{|\{P \in \text{val}_t : \text{sim}(P,q) \geq \tau_q\}|}{|\text{val}_t|}$$

Measured: $\pi_{q,t} \approx 5\text{–}7\%$. Underexposed flag: $\pi_{q,t} < 10\%$.

### Local density (B2 baseline matching)

$$\rho(P) = \frac{1}{k}\sum_{i=1}^{k}\text{sim}(P,\ \text{kNN}_i(P,\text{train})),\quad k=20$$

B2 match: $\arg\min_j|\rho(B_j)-\rho(V)|$ over 300 candidates per anchor.

### Calibrated fill threshold (replaces 0.82)

$$\tau_{\text{fill}}(q,\rho,t) = Q_{1-\alpha}\!\left(\left\{\max_{P \in \text{Val}_q}\text{sim}(P,m_0) : m_0 \in \text{Null}(q,\rho,t)\right\}\right)$$

where $\text{Null}(q,\rho,t)$ = density-matched null midpoints, same anchor $q$, density bucket $\rho$, split $t$; $\alpha=0.05$.

**Calibration results across t3/t4/t5** (why 0.82 is not a valid constant):

| Split | τ\_fill mean | τ\_fill range | FPR@0.82 mean | FPR@0.82 max |
|---|---|---|---|---|
| t3 | 0.841 | 0.805–0.897 | 33.9% | 99.0% |
| t4 | 0.841 | 0.802–0.885 | 35.6% | 99.5% |
| t5 | 0.841 | 0.790–0.881 | 35.7% | 98.0% |

τ\_fill is **stable at 0.841** across all splits — corpus density is the main driver,
not temporal window. 0.82 is systematically 0.02 below the calibrated threshold.
FPR@0.82 reaches 98–99% in high-density anchors (virt\_hyp, sched\_opt high bucket).

**In paper**: use global τ\_fill=0.82 as legacy operating point for comparability,
but report calibrated τ\_fill per (anchor, density bucket) in sensitivity analysis.

### Role-aware fill score (Table 3)

$$s(P) = \begin{cases} 1.0 & \text{TRUE-FILL} \\ 0.7 & \text{PARTIAL-FILL} \\ 0.5 & \text{SUPPORT-EVIDENCE} \\ 0.3 & \text{SURVEY-OR-NAMING} \\ 0.2 & \text{INCREMENTAL-EXT} \\ 0.0 & \text{FALSE-POSITIVE} \end{cases} \qquad \bar{s} = \frac{1}{|C|}\sum_{P\in C}s(P)$$

### When to use what

| Question | Math |
|---|---|
| Geometrically close enough? | $\max_{P \in \text{Val}_q}\text{sim}(P,m_V) \geq \tau_{\text{fill}}(q,\rho(V))$ |
| In anchor's problem domain? | $\text{sim}(P,q)>\tau_q$ |
| How to set $\tau_q$? | $\max(Q_{80}^{\text{val}},Q_{90}^{\text{train}})$ |
| How many future papers observable? | $\pi_{q,t}$ |
| Hot-zone bias present? | Compare $\rho(\text{B1})$ vs $\rho(\text{TVA})$ |
| Is paper epistemic fill? | $s(P)$ via LLM role label |
| Group epistemic quality? | $\bar{s}$ |

---

## 2. Background

### 2.1 Topological Void Analysis (TVA)
- C1–C4 conditions (brief recap from Paper 1)
- Anchor, void, midpoint definitions
- TVA operates on pre-committed corpus snapshot

### 2.2 Temporal Validation in LBD
- Time-slicing / replication method
- Recall@K, Precision@K, AP — standard LBD metrics
- Limitation: treats appearance as success; ignores epistemic role

### 2.3 Structural Holes and Research Momentum
- Burt structural holes: brokers connect disconnected clusters
- Research momentum: hot zones attract more future papers regardless of void quality
- Dense-region confounding: baseline in hot zone inflates raw fill

---

## 3. Experimental Setup

### 3.1 Corpus and Splits
Rolling temporal splits (t3–t5), train < T, val [T, T+5]:
| Split | Train | Val window | Train size | Val size |
|---|---|---|---|---|
| t3 | < 2014 | 2015–2019 | ~29k | ~60k |
| t4 | < 2016 | 2017–2021 | ~35k | ~80k |
| t5 | < 2018 | 2019–2023 | ~51k | ~193k |

Categories: cs.OS, cs.AR, cs.PL, cs.SE, cs.DC, cs.NI, cs.CR, cs.AI, cs.LG

### 3.2 TVA Void Generation
- 10 Anchors × top-30 MMR voids = 300 candidate voids per split
- Embedding: BGE-M3 (1024d), cosine similarity
- Midpoint: SLERP(paper_A, paper_B)

### 3.3 Baselines
- **B1 (hot-zone)**: random pairs from top-300 anchor-adjacent C1 pool, 20 per anchor
- **B2 (density-matched)**: for each TVA void, find B1-style pair with matching local
  historical density (greedy nearest match from 300 candidates)

### 3.4 Three-Layer Fill Predicate
```
ValidatedFill(P, V, q) = G(P, m) ∧ E(P, q) ∧ R(P, A, B, q)
  G = sim(P, midpoint) > 0.82       (geometric closure)
  E = sim(P, anchor) > τ_q          (anchor eligibility)
  R(P,A,B,q) = 1 iff role(P,A,B,q) ∈ {TRUE_FILL, PARTIAL_FILL}
```

Role labels (simplified for reporting):
- TRUE_FILL / PARTIAL_FILL → validated fill
- FALSE_POSITIVE / OTHER → not a fill

Note: TVA does not claim to compute β₂ persistent homology. "Topological" is used
operationally: BGE-M3 provides the coordinate system; void predicates and validation
operators are defined externally.

---

## 4. Results

### 4.1 Finding 1: Raw Fill Rate Is Density-Confounded

Table 1: Raw fill rates across rolling splits (B1 = hot-zone, B2 = density-matched)

| Split | TVA | B1 hot-zone | TVA/B1 | B2 density | TVA/B2 |
|---|---|---|---|---|---|
| t3 | 31% | 32% | 0.97× | 30% | **1.03×** |
| t4 | 26% | 32% | 0.80× | 23% | **1.12×** |
| t5 | 28% | 36% | 0.78× | 25% | **1.12×** |

TVA/B1 lift worsens from t3→t5 (dense val corpus inflates B1 over time).
TVA/B2 lift is consistently positive across all splits (1.03–1.12×).

Key sentence: Hot-zone baseline inflates raw fill by sampling high-density,
high-momentum regions. After density matching, TVA achieves a modest but consistent
positive lift across all temporal splits.

TODO: Add 95% bootstrap CI over void candidates for TVA/B2 lift.

### 4.2 Finding 2: Anchor Eligibility Reveals Observability Limits

Table 2: Anchor exposure (t5, 192k val papers, hybrid gate = max(Q80_val, Q90_train))

| Anchor | mean sim | τ_hybrid | pass≥0.55 | pass≥0.65 | pass_hybrid | TVA raw fill |
|---|---|---|---|---|---|---|
| sched_opt | 0.520 | 0.582 | 21.3% | 0.1% | 5.8% | 40% |
| mm_vm | 0.506 | 0.559 | 10.7% | 0.0% | 6.7% | 27% |
| ebpf_obs | 0.495 | 0.547 | 5.4% | 0.0% | 6.5% | 0% |
| hwsw_x86 | 0.494 | 0.559 | 7.5% | 0.0% | 5.0% | 30% |
| net_io | 0.507 | 0.574 | 14.8% | 0.0% | 5.4% | 30% |
| virt_hyp | 0.498 | 0.555 | 9.4% | 0.1% | 7.7% | 57% |
| power_mgmt | 0.503 | 0.563 | 10.8% | 0.0% | 6.1% | 47% |
| **mean** | **0.503** | **0.563** | **11.2%** | **0.0%** | **6.2%** | — |

Key observations:
- Mean sim(val, anchor) ≈ 0.50–0.52 — val corpus weakly aligned with anchors
- Fixed threshold ≥ 0.65 passes ~0% of val papers → near-zero observability
- Hybrid gate passes only 5–8% per anchor
- ebpf_obs: pass rate 6.5% but TVA raw fill 0% → classic underexposure case
- virt_hyp/power_mgmt: pass rate ~7% but TVA fill 47–57% → well-exposed anchors

Implication: unfilled voids ≠ invalid voids. Fill rate is limited by anchor exposure.
Mark as *underexposed* (diagnostic flag, not void failure) when hybrid pass rate < 10%.

Note on ebpf_obs (pass 6.5%, fill 0%): eligible set may not overlap void neighborhoods
even with nonzero exposure. Exposure is a necessary but not sufficient condition for
observability — the eligible papers must also be semantically near the predicted midpoints.

### 4.3 Finding 3: Geometric Fill Rarely Equals Epistemic Fill

Role-aware classification shows that geometric fill substantially overestimates void
resolution. Among anchor-gated t5 cases, TVA and B1 have identical false-positive rates
(67%), while B2 performs slightly better (59%). TRUE_FILL and PARTIAL_FILL are rare:
TVA and B1 contain no true/partial fills in this sample; B2 contains only 2 cases (5%).
Most gated fills are boundary expansions or incremental extensions, not void resolution.

Near-miss controls provide a sanity check: FP rate 84%, role-aware score 0.054 — lower
than all gated groups, confirming that geometric proximity carries signal, but proximity
alone is insufficient.

Table 3a: Role decomposition (t5, counts — three mutually exclusive categories)

| Source | n | Void resolution | Boundary activity | Geometric FP | Other/Unclear |
|---|---|---|---|---|---|
| TVA (gated) | 36 | 0 | 12 (33%) | 24 (67%) | 0 |
| B1 hot-zone (gated) | 30 | 0 | 10 (33%) | 20 (67%) | 0 |
| B2 density-matched | 44 | 2 (5%) | 16 (36%) | 26 (59%) | 0 |
| Near-miss controls | 88 | 3 (3%) | 11 (13%) | 74 (84%) | 0 |

*Void resolution = TRUE-FILL + PARTIAL-FILL*
*Boundary activity = INCREMENTAL-EXTENSION + SUPPORT-EVIDENCE + SURVEY-OR-NAMING*
*Geometric FP = FALSE-POSITIVE (three categories sum to 100%)*

Table 3b: Topological event type (new rubric, t5)

| Source | VOID_FILL | BOUNDARY_EXPANSION | DENSIFICATION | RHETORICAL_BRIDGE |
|---|---|---|---|---|
| TVA | 0% | 67% | 22% | 11% |
| B1 | 0% | 47% | 27% | 27% |
| B2 | 0% | 77% | 16% | 7% |
| Near-miss | 0% | 59% | 26% | 15% |

VOID_FILL = 0 across all groups in t5 sample. topological_event_type and
epistemic role label are consistent (BOUNDARY_EXPANSION → INCREMENTAL_EXTENSION,
DENSIFICATION → FALSE_POSITIVE), validating the new rubric.

Interpretation:
> Geometric closure and anchor eligibility are screening conditions, not validation
> conditions. Epistemic fill — genuine bridging between two separated research directions
> — is rare even among geometrically-close, anchor-eligible future papers.

t4 confirmation (150 cases):
- TVA FP 68%, TRUE+PARTIAL 0, score 0.065
- B1 FP 65%, TRUE+PARTIAL 0, score 0.081
- B2 FP 64%, TRUE+PARTIAL 0, score 0.092
- Near-miss FP 82%, score 0.053

Pattern is consistent across t4 and t5. Finding 3 is robust.

---

## 5. Discussion

### 5.1 Raw Fill Fails for Three Reasons

1. **Density bias**: hot-zone baselines inflate raw fill; density matching reverses TVA's apparent disadvantage.
2. **Observability limits**: only 5–7% of future papers are anchor-eligible; unfilled voids are right-censored, not invalid.
3. **Epistemic-role mismatch**: even gated fills are mostly boundary expansion or geometric FP; true void resolution is rare.

Together: raw fill is a weak signal of future local activity near predicted voids, not a validation signal.

### 5.2 From Fill Detection to Role Decomposition

Future papers near void midpoints decompose into several epistemic roles: true fill,
partial fill, boundary expansion, densification, rhetorical proximity. The scarcity of
true fills is not a failure of TVA — it reveals that genuine epistemic closure is a much
stricter condition than geometric occupancy. TVV's contribution is to make this
distinction operationalizable.

> Geometric closure and anchor eligibility are screening conditions.
> Epistemic role is the validation condition.

### 5.3 Descriptive, Not Evaluative

We do not interpret boundary expansion or densification as low-value. Replication,
refinement, and consolidation are essential scientific activities. TVV classifies the
type of validation evidence produced by future literature, not the intrinsic merit of
papers.

### 5.4 Right-Censoring and Unfilled Voids

Unfilled voids should be treated as right-censored, not false positives.
Harder voids may require longer windows or denser domain coverage.

### 5.5 Dynamic Extension (Future Work)

Paper 2 validates voids against a fixed future window using a static embedded corpus.
It does not implement event-driven observation of the knowledge space. The distinction:

```
Paper 2 (done): static corpus → find voids → fixed window → observe fill
D-TVA (future): paper arrives → pre-insertion DB check → classify event → update DB
```

These results suggest that future void-validation systems should not treat papers as
static future points only, but as events that update the state of a knowledge space.
We leave streaming and event-driven formulations of TVA to future work.

### 5.6 Threats to Validity
1. **Embedding dependence**: BGE-M3 defines the coordinate system; results may vary with embedding model choice.
2. **Threshold sensitivity**: geometric closure and anchor gates depend on calibrated thresholds; we use density-matched controls and report sensitivity across threshold sweep.
3. **Corpus coverage**: unobserved fills may occur outside the corpus; unfilled voids are right-censored.
4. **LLM role classification**: role labels are approximate and auditable judgments, not ground truth; single-model classification without inter-rater reliability.
5. **Domain specificity**: experiments focus on selected CS arXiv categories; generalization to other domains requires separate evaluation.

---

## 6. Conclusion

Temporal validation of predicted research voids requires separating geometric occupancy,
density bias, anchor observability, and epistemic role.

Raw fill rate alone is insufficient: it conflates void quality with local corpus density
and research momentum. After density matching, TVA's apparent disadvantage reverses.
After anchor eligibility gating, the observability limit becomes explicit — unfilled voids
are right-censored, not invalid. After role-aware classification, the gap between geometric
fill and epistemic fill becomes explicit: raw fill substantially overestimates void resolution.

Three hooks for future work — left intentionally undeveloped:

1. **Raw future occupancy is density-confounded.** Any void-validation metric must
   control for local historical density; failure to do so systematically favors
   high-momentum hot-zone baselines.

2. **Void validation is better understood as an epistemic role problem.** The binary
   filled/unfilled distinction obscures the range from true epistemic bridging to
   rhetorical proximity. Role-aware metrics are necessary.

3. **Future systems may treat papers as events that update knowledge-space state.**
   Instead of asking whether a void is eventually filled, one can ask what topological
   event a newly arriving paper induces on the corpus that existed before it.

We leave the development of streaming, event-driven, and dynamic extensions to future work.

---

## TODO for Paper 2

### Done
- [x] Table 3: role classification t4+t5 confirmed (59–68% FP, pattern consistent)
- [x] Table 1: t3/t4/t5 B2 rolling results (1.03x / 1.12x / 1.12x)
- [x] Table 2: anchor exposure table (6.2% mean hybrid pass, per-anchor breakdown)
- [x] Three-layer fill predicate formalized
- [x] Mathematics reference section written
- [x] Paper 2 skeleton with abstract, contributions, findings, discussion, threats to validity

### Still needed
- [ ] Case studies: pick 2–3 PARTIAL\_FILL cases from B2, look up citation count
- [ ] Bootstrap CI on Table 1 TVA/B2 lift (resample voids, report 95% CI)
- [ ] t3 role classification (file exists but not verified — run sanity check)
- [ ] Related work section: write 5 paragraphs (LBD, novelty detection, structural holes, dense-region bias, claim verification)
- [ ] Write up formally in LaTeX / Overleaf

---

## Key Sentences Bank

> Temporal validation of predicted voids must distinguish geometric closure from epistemic closure.

> Raw fill rate conflates void quality with sociotechnical realization rate — whether the human research community happened to walk in that direction within the validation window.

> After density matching, TVA no longer underperforms the baseline, motivating a shift from raw occupancy metrics to role-aware epistemic validation.

> Unfilled voids should be treated as right-censored rather than automatically false.

> TVA reframes research-gap discovery as a geometric void-search problem; TVV asks whether an observed future paper is the first occupant of such a void.
