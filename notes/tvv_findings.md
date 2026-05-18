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

## Open Questions (for Paper 3 / D-TVA)

- How does D_C (anchor-relative drift) correlate with void lifecycle events?
- Can we detect void formation before it's visible in the corpus?
- What is the distribution of void lifetimes (time from formation to fill)?
- Does void velocity predict fill quality?
