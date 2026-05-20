# Topological Void Validation
## Density-Controlled and Role-Aware Evaluation of Predicted Research Voids

**Kris Pan** · Intel Corporation · kris.pan@intel.com

📄 [Full PDF](paper2/tvv_paper.pdf) | [TVA Paper 1](PAPER.md) | [Zenodo (Paper 1)](https://zenodo.org/records/19836730) | [Code](https://github.com/krispan-intel/deepthought/tree/dynamic_tva)

---

## Abstract

Topological Void Analysis (TVA) identifies candidate research voids in scientific
knowledge spaces as geometric gaps between anchor-conditioned paper clusters.
A natural validation question is whether future papers fill these predicted voids.
We show that raw fill rate — whether any future paper appears near a void's midpoint —
fails as a validation target for three compounding reasons.

First, it is confounded by local corpus density: a hot-zone baseline outperforms TVA on
raw fill rate, but this advantage disappears under a density-matched baseline. TVA shows
a small directional difference (+1.3 to +3.0 pp across three temporal splits), but all
hierarchical cluster-bootstrap confidence intervals include zero and paired anchor-level
permutation tests are not significant (p > 0.35). Under null-calibrated thresholds,
fill rates collapse from ~27% to ~0.7%, revealing that most raw fills are null-zone noise.

Second, anchor eligibility gating reveals a corpus observability limit: only 5–7% of
future papers are anchor-eligible per split. Fill rates increase monotonically with
anchor exposure (23.3% → 32.2%), confirming that many unfilled voids are right-censored
by observability rather than invalid predictions.

Third, role-aware epistemic classification shows that even anchor-eligible geometric
fills rarely represent genuine void resolution: 59–76% are false positives across all
groups and splits (1,076 sampled cases, t3+t4+t5), with most non-false cases
representing boundary expansion rather than void closure.

A landmark diagnostic confirms the three-layer structure: five pre-specified bridge-type
papers all pass geometric (G) and eligibility (E) screening, but none pass role-aware
bridge interpretation (R) — illustrating that geometry and anchor alignment are necessary
but not sufficient for epistemic closure.

These findings motivate a three-layer validation framework — calibrated geometric
closure, anchor eligibility, and epistemic role — and establish that raw fill rate
measures future local activity near predicted voids but does not validate epistemic
closure. TVA is best understood as a rapid triage instrument: it compresses an
otherwise intractable search space (~45,000 candidate pairs per anchor) into a
human-auditable set of inspectable hypotheses. TVV is the downstream adjudication
protocol.

---

## Key Results

| Finding | Result |
|---|---|
| TVA vs B2 (density-matched) | +1.3 to +3.0 pp across splits, hierarchical CI all contain 0, p > 0.35 |
| Under calibrated threshold | TVA and B2 both collapse to ~0.7%, near-perfect parity |
| FPR of τ=0.82 | 35.7% average null FPR, range 1–99% across anchor-density cells |
| Anchor exposure | 5–7% of val papers eligible; fill rises 23% → 32% with exposure |
| Role audit (1,076 cases) | 59–76% FP across all groups; void resolution < 5% |
| Landmark diagnostic | 5/5 G+E pass, 0/5 R pass (geometry ≠ bridge interpretability) |

---

## 1. Introduction

Classical IR asks: given a query, what existing documents are relevant?
TVA asks: given an anchor, what relevant knowledge is *absent*?

**Validating predicted voids is not the same as validating a predicted link.**
A predicted link has a direct future target: it appears or it does not.
A predicted void has a richer failure mode: future literature may occupy the region
geometrically while failing to bridge the source concepts epistemically.

Unlike document retrieval or link prediction, predicted research voids have no
established gold-standard benchmark. Exhaustive human annotation is infeasible at
corpus scale. TVV addresses this by turning void validation into a staged, auditable
protocol.

**Contributions:**
1. Raw temporal fill rate is strongly confounded by local historical density.
2. Density-matched baseline shows TVA–B2 difference is not statistically significant.
3. Fixed cosine thresholds (τ=0.82) are not portable: 35.7% average null FPR.
4. Anchor eligibility limits observability; unfilled voids are right-censored.
5. LLM-assisted role audit suggests geometric fill substantially overestimates epistemic resolution.

**Scope:** Static retrospective validation against pre-committed future corpus windows.
This is a *validation stress test*, not a confirmatory demonstration of TVA superiority.

---

## 2. Background

### 2.1 Topological Void Analysis

TVA~[1] operates on a corpus embedded with BGE-M3 (d=1024, cosine similarity).
For anchor q and source papers A, B, a candidate void satisfies four conditions:
- **C1** domain cohesion — both near anchor q
- **C2** calibrated marginality — neither too central nor too marginal
- **C3** sparse lexical bridge — shared discriminative tokens, no generic overlap
- **C4** midpoint vacancy — m(A,B) = normalize(a+b) is unoccupied in corpus

### 2.2 Temporal Validation in LBD

Literature-Based Discovery validates predictions by checking whether future publications
confirm predicted connections~[2,3,4]. TVV extends this by requiring epistemic bridging
role, not merely geometric proximity.

### 2.3 Validation Gap

Prior work validates predicted connections or missing edges under fixed relation schemas.
TVA voids are anchor-conditioned geometric vacancies whose future occupancy may represent
true bridging, boundary expansion, or false-positive proximity. To our knowledge,
no prior work evaluates embedding-space voids under density-controlled,
observability-aware, and role-aware temporal validation.

---

## 3. Experimental Setup

### Corpus and Temporal Splits

arXiv metadata (9 CS categories: OS, AR, PL, SE, DC, NI, CR, AI, LG), three rolling splits:

| Split | Train cutoff | Val window | Train | Val |
|---|---|---|---|---|
| t3 | 2014 | 2015–2019 | ~29k | ~101k |
| t4 | 2016 | 2017–2021 | ~35k | ~171k |
| t5 | 2018 | 2019–2023 | ~51k | ~193k |

### Baselines

- **B1 (hot-zone):** 20 random pairs from top-300 anchor C1 pool. Biased toward high-density regions.
- **B2 (density-matched):** For each TVA void, the B1-style pair with closest midpoint density (ρ(m) = mean sim to 20 nearest train neighbors).

### Three-Layer Fill Predicate

$$Val_q = \{P \in Val_t : \text{sim}(P,q) \geq \tau_q\}, \quad \tau_q = \max(Q_{80}^{val}, Q_{90}^{train})$$

$$P_V^* = \arg\max_{P \in Val_q} \text{sim}(P, m_V)$$

$$G(V) = \mathbf{1}[\text{sim}(P_V^*, m_V) \geq \tau_{fill}(q, \rho(V), t)]$$

$$\text{Fill}(V) = G(V) \wedge R(P_V^*, A, B, q)$$

**Calibrated threshold:** τ_fill uses a finite-sample conformal quantile from density-matched null midpoints (n=1000, 50/50 cal/test, α=0.05). Held-out null FPR: 6.3% vs nominal 5%.

**Statistical tests:** Hierarchical cluster bootstrap (outer: anchors, inner: voids) + anchor-level sign-flip paired permutation test. All results report paired Δpp, not ratio.

---

## 4. Results

### Finding 1: Raw Fill Rate Is Density-Confounded

TVA–B2 paired fill-rate differences under legacy τ=0.82:

| Split | TVA | B2 | Δpp | Hierarch. CI | p |
|---|---|---|---|---|---|
| t3 | 31% | 29% | +1.3 | [−5.0, +9.0] | 0.787 |
| t4 | 26% | 23% | +2.4 | [−1.4, +7.1] | 0.352 |
| t5 | 27% | 24% | +3.0 | [−2.0, +8.3] | 0.360 |

All CIs contain zero; all p > 0.35. Under calibrated τ: Δ = −0.7 to +0.7 pp (near-perfect parity).

**Fixed thresholds are not portable.** τ=0.82 has 35.7% average null FPR (range 1–99% across anchor-density cells). Calibrated τ averages 0.841.

### Finding 2: Anchor Eligibility Reveals Observability Limits

Only 5–7% of val papers are anchor-eligible per split. Fill increases with exposure:

| Exposure | Anchors | Mean |Val_q| | Fill rate |
|---|---|---|---|
| Low | 3 | 10,178 | 23.3% |
| Mid | 4 | 11,794 | 26.7% |
| High | 3 | 14,206 | 32.2% |

Non-fill is partly right-censored by observability, not a clean negative label.

### Finding 3: Geometric Fill Rarely Equals Epistemic Fill

Role audit (1,076 cases, t3+t4+t5, collapsed 3-class):

| Source | n | FP | FP CI | VR CI |
|---|---|---|---|---|
| TVA (gated) | 204 | 71% | [65,77] | [1,6] |
| B1 (gated) | 158 | 75% | [67,81] | [0,2] |
| B2 density | 202 | 67% | [60,73] | [1,6] |
| Near-miss | 512 | 84% | [81,87] | [1,4] |

59–76% FP across all groups. Void resolution (TRUE/PARTIAL-FILL) is rare even among gated fills.

### Landmark Three-Layer Diagnostic

Five pre-specified bridge-type landmark papers:

| Landmark | Year | G (>null p95) | E (anchor-eligible) | R (bridge audit) |
|---|---|---|---|---|
| vLLM / PagedAttention | 2023 | Yes | Yes | No |
| MLIR | 2020 | Yes | Yes | No |
| Devign | 2019 | Yes | Yes | No |
| Ansor | 2020 | Yes | Yes | Weak |
| FlashAttention | 2022 | Yes | Yes | No |

5/5 G+E pass, 0/5 R pass. Anchor alignment is recoverable; bridge interpretation is not geometric.

---

## 5. Discussion

### TVA as a Rapid Triage Instrument

TVA compresses ~45,000 candidate pairs per anchor into 300 inspectable void hypotheses
in minutes. Human experts cannot enumerate at this scale but are well-suited to
adjudicating a compact ranked list. TVA is a **detector**, not an oracle:
it prioritizes candidate locations for inspection but does not certify epistemic closure.

Parity with B2 is the **expected outcome** under a strong density-matched control.
B2 is not a competing discovery workflow; it estimates background arrival rates.
TVA reaches the same low calibrated fill rate while producing interpretable (q,A,B,m)
hypotheses. The relevant question is not raw superiority but enrichment.

### Three-Layer Protocol Necessity

The landmark diagnostic illustrates why three layers are not redundant:
all five landmarks pass G and E but fail R. Geometric proximity and anchor alignment
are necessary screens, not sufficient evidence of bridge interpretability.

### No Established Standard

There is no prior gold-standard benchmark for predicted research voids. TVV provides
a first operational protocol — density-controlled, observability-aware, and role-audited —
designed to be reproducible and auditable. The protocol is a contribution, not a side effect.

---

## 6. Reproducibility

All parameters are pre-specified in [`paper2/configs/tvv_config.yaml`](paper2/configs/tvv_config.yaml).
Role annotation prompt and rubric: [`paper2/prompts/role_classifier_prompt.txt`](paper2/prompts/role_classifier_prompt.txt).
Code, scripts, and derived labels: [github.com/krispan-intel/deepthought](https://github.com/krispan-intel/deepthought) (branch: `dynamic_tva`).

---

## 7. Conclusion

Temporal validation of predicted research voids requires separating geometric occupancy,
density bias, anchor observability, and epistemic role. Raw fill rate conflates all four.

After density matching, TVA's apparent disadvantage disappears but the difference is not
statistically significant. Under null-calibrated thresholds, fill rates collapse to ~0.7%,
revealing that most raw fills were null-zone noise. Role-aware classification confirms
that genuine epistemic bridging is rare even among geometrically close, anchor-eligible papers.

**TVA is a detector, not an oracle. TVV is the adjudication protocol.**

> A TVA void is a hypothesis to inspect, not a claim already validated.

---

## References

[1] Pan, K. (2026). Topological Void Analysis: A Mathematical Framework for Systematic Technical Innovation Discovery in Knowledge Spaces. Preprint. [Zenodo](https://zenodo.org/records/19836730)

[2] Swanson, D.R. (1986). Fish Oil, Raynaud's Syndrome, and Undiscovered Public Knowledge. *Perspectives in Biology and Medicine*, 30(1), 7–18.

[3] Gordon, M.D. & Lindsay, R.K. (1996). Toward Discovery Support Systems. *JASIS*, 47(2), 116–128.

[4] Weeber, M. et al. (2001). Using Concepts in Literature-Based Discovery. *JASIST*, 52(7), 548–557.

[5] Burt, R.S. (2004). Structural Holes and Good Ideas. *American Journal of Sociology*, 110(2), 349–399.

[6] Chen, J. et al. (2024). BGE M3-Embedding. arXiv:2402.03216.

---

*Draft — 2026-05-20. See [paper2/tvv_paper.pdf](paper2/tvv_paper.pdf) for LaTeX version.*
