# Paper 2 Revision Notes / Cover Letter Draft

*TVV: Topological Void Validation — Density-Controlled and Role-Aware Evaluation of Predicted Research Voids*
*Kris Pan, Intel Corporation. 2026-05-19.*

---

## 1. What We No Longer Claim

- **No TVA superiority over B2**: All TVA–B2 paired differences have hierarchical CIs spanning zero; all permutation p > 0.35. The paper does not claim TVA outperforms the density-matched baseline.
- **No guaranteed 5% FPR**: The null-calibrated threshold is reported as a *nominal operating point*. Held-out null FPR = 6.3% vs nominal 5% (slightly liberal; reported explicitly).
- **No human gold standard**: LLM role labels are primary; human audit is an external plausibility check. We do not claim ground-truth role classification.
- **No necessary-and-sufficient conditions**: The three validation layers are operational screens, not necessary/sufficient conditions for scientific discovery.
- **No landmark bridge recovery**: Landmark anchor eligibility is recoverable (3/5 papers), but geometric midpoint retrieval alone does not identify interpretable bridge pairs.

---

## 2. What We Fixed (v1 → v4)

### Statistical fixes
| Issue | Fix |
|---|---|
| Void-level bootstrap (violates IID) | Hierarchical cluster bootstrap: outer=anchors, inner=voids |
| Ratio CI on low base-rate data | Paired Δpp + hierarchical CI (all contain zero) |
| Interpolated Q0.95 from n=200 | Finite-sample conformal quantile k=⌈(n+1)(1−α)⌉ |
| No held-out calibration check | 50/50 cal/test split; held-out FPR=6.3% reported explicitly |
| No dependence-aware test | Anchor-level sign-flip paired permutation test |

### Framing fixes
- Confirmatory narrative → validation stress-test / methodology paper
- "confirms" → "suggests" for LLM role audit
- "necessary and sufficient" → "operational screens"
- Added: "validating a void ≠ validating a link" (novelty clarification)
- Added: Related Work gap paragraph on void validation vs link prediction

### Content additions (v5)
- 3-class collapsed role taxonomy with operational definitions
- Role classification pipeline section (blind protocol, model, reliability checks)
- Landmark anchor-eligibility diagnostic (3/5 pass; honest failure mode noted)
- Reproducibility Protocol appendix (anchors, algorithm, stats, prompt URL)
- Code/data availability statement (GitHub dynamic_tva branch)

---

## 3. What Remains Limited

1. **Pilot-scale role annotation** (n=1076 total, single LLM). Fine-grained nine-class labels not validated at inter-rater level; quantitative claims use collapsed three-class only.

2. **Small anchor set** (10 anchors, 300 voids per split). Hierarchical bootstrap with 10 anchors yields wide CIs (±5–9 pp). This is honest, not a bug — it reflects the true uncertainty.

3. **BGE-M3 embedding dependence**. All metrics use a single embedding model. Per-cell null calibration controls threshold, not embedding anisotropy/hubness.

4. **arXiv CS corpus only**. Results may not generalize to other domains or citation-graph-based representations.

5. **No full LBD baseline comparison**. B1/B2 are density/momentum controls, not full A–B–C LBD competitors. Future work should add citation-based predictors.

6. **Landmark bridge recovery incomplete**. Full per-paper-cutoff, anchor-restricted, role-audited landmark recovery remains future work.

---

## 4. Rebuttal Template (for reviewers)

### To statistical calibration reviewer (v3 REJECT → v4 MR):
> We replaced interpolated Q0.95 with the finite-sample conformal quantile and replaced void-level bootstrap with hierarchical cluster bootstrap and anchor-level paired sign-flip permutation. The observed held-out null FPR of 6.3% vs nominal 5% is now reported explicitly as a slightly liberal operating point, not as a guarantee.

### To LLM annotation reviewer:
> We added a dedicated role classification pipeline section with the blind protocol, model/version, and reliability checks (90%+ self-consistency, 80%+ human FP/non-FP agreement). All quantitative claims now use the collapsed three-class taxonomy; fine-grained nine-class labels are qualitative only.

### To reproducibility reviewer:
> We added Appendix A (Reproducible TVV Protocol) with exact anchor list, algorithm pseudocode, density/null/calibration specifications, and statistical test details. Code and prompts are available at github.com/krispan-intel/deepthought (branch: dynamic_tva).

### To effectiveness claims reviewer:
> TVA does not significantly outperform B2 on temporal occupancy — this is the expected result under a strong density-matched control. The paper's contribution is methodological: showing that raw fill rate is unstable, density-confounded, and not sensitive to TVA's added value as an ex-ante void hypothesis generator. Parity with B2 confirms, not contradicts, this claim.

---

## 5. Positioning Statement

This paper is a **validation methodology contribution**, not a TVA effectiveness proof.

Core claim:
> *Temporal validation of predicted research voids requires separating geometric occupancy, density bias, anchor observability, and epistemic role. Raw fill rate conflates all four.*

The three-layer protocol (G → E → R) is the deliverable:
- G: null-calibrated geometric closure with density bucket controls
- E: anchor eligibility / corpus observability
- R: LLM-assisted role audit with collapsed three-class taxonomy

TVA's value — providing interpretable ex-ante void hypotheses — cannot be measured by raw temporal occupancy at pilot scale. This paper establishes the measurement framework; large-scale deployment is future work.

---

## 6. Next Steps Before Submission

- [ ] Run per-paper-cutoff landmark recovery (improved design)
- [ ] Confirm `claude-sonnet-4-5` model version in paper
- [ ] Replace `eprint=TODO` in pan2026tva when arXiv ID assigned
- [ ] Final pass: delete any remaining "confirms" / "validates" language
- [ ] Compile main.tex (ACM sigconf) once acmart.cls available
