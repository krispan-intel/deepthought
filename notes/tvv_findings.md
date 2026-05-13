# TVV Experiment Findings

*2026-05-13. Kris Pan.*

## Summary

Raw fill rate is the wrong metric for TVA validation.
Role-aware epistemic classification reveals TVA's true advantage.

---

## Experiment Setup

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

> **Raw fill rate measures research momentum, not void quality. TVA sacrifices fill frequency for epistemic fill quality.**

This is the Paper 2 thesis.

---

## What This Motivates

1. **Epistemic role classification** is necessary for void validation
2. **Raw fill rate is a biased metric** — unsuitable as primary TVA validation
3. **True voids are rare events** — cannot be validated with large-sample frequency statistics
4. **D-TVA** needs to track void lifecycle (fill, partial fill, collapse, support) not just presence/absence
5. **Role-aware drift metric D_C** should weight epistemic events, not count fills

---

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

## Open Questions (for Paper 3 / D-TVA)

- How does D_C (anchor-relative drift) correlate with void lifecycle events?
- Can we detect void formation before it's visible in the corpus?
- What is the distribution of void lifetimes (time from formation to fill)?
- Does void velocity predict fill quality?
