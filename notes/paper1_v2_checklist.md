# Paper 1 v2 Submission Checklist

*Prepared 2026-05-13. To be executed after arXiv v1 passes moderation.*

---

## Category Change

- [ ] Change primary category: `cs.AI` → `cs.IR`
- [ ] Keep secondary: `cs.AI`, `cs.SE`
- [ ] Update submission metadata accordingly

---

## Introduction

- [ ] Add framing sentence near the top:
  > *Classical IR asks: given a query, what existing documents are relevant? TVA asks: given an anchor, what relevant knowledge is missing?*

- [ ] Add IR lineage paragraph connecting to Belkin ASK, Swanson ABC, exploratory search:
  > *TVA extends anchor-conditioned retrieval toward the detection of meaningful absences: regions where expected connections, evidence, or conceptual bridges are missing.*

- [ ] Replace any "TVA is revolutionary" language with "TVA extends IR tradition"

---

## Background / PRH Section

- [ ] Add bridge after PRH paragraph:
  > *PRH provides a qualitative convergence claim. However, TVA requires a finite-dimensional operational question: how much of that geometry must be preserved for void detection to remain reliable? The TVA Dimensionality Theorem (Appendix A) supplies this missing operational layer.*

- [ ] Clarify that PRH supports proxy alignment, but proxy alignment alone is insufficient — Dimensionality Theorem provides the criterion

---

## Discussion — Broader Implications

- [ ] Add guard sentence at top of broader implications section:
  > *The following discussion illustrates how anchor-conditioned absence detection may extend beyond document retrieval. These are implications, not formal claims of this paper.*

- [ ] Compress multi-agent / DMN / monolithic AI limit paragraphs — keep 1-2 sentences each, not full paragraphs
- [ ] Every paragraph should end with a pull-back to IR language: absence, void, anchor, knowledge space, retrieval

---

## Appendix A — Dimensionality Theorem

- [ ] Add at top of A.1:
  > *PRH provides a qualitative convergence claim; this appendix turns it into a finite-dimensional retrieval question. We ask how much of the shared representation geometry a D-dimensional vector database can preserve, and at what point additional dimensions create more spurious voids than useful resolution.*

- [ ] Fix the "Applying SVD to the LLM's embedding space" claim — add bridge:
  > *In practice, we estimate the task-relevant spectral decay γ from the embedded corpus rather than from the inaccessible frontier LLM representation. Under PRH, the corpus-induced geometry of a sufficiently aligned embedding model is treated as an operational proxy for the task-relevant subgeometry of the frontier model.*

- [ ] Add theorem guard clause:
  > *Under a power-law spectral decay model and a linear sparsity-noise penalty, the optimal embedding dimension is...*

- [ ] Add to k=0.001 section:
  > *We do not claim k=0.001 is universal; it is an implementation-level noise tolerance estimated for this corpus and pipeline. Future work should estimate k from null-model void occupancy and human-labeled false-void rates.*

- [ ] Consider renaming Theorem subtitle:
  `TVA Dimensionality Theorem (Optimal Proxy Dimension under PRH and Sparsity Noise)`

- [ ] Define "topological resolution" more carefully:
  > *We use the term topological resolution operationally: the fraction of spectral structure retained by the embedding proxy that is available for downstream void detection. It is not a homology invariant.*

---

## Math / Notation Fixes (already done in current draft, verify)

- [x] JL Lemma replaced with curse of dimensionality argument
- [x] C2 lower bound present in .tex
- [x] Sensitivity table A.5 added
- [x] Upstream/downstream slogan updated

---

## Zenodo / arXiv Links

- [ ] Replace `*(pending)*` with actual arXiv URL in PAPER.md, README.md (all 3 languages)
- [ ] Update Zenodo record if needed

---

## Push to public repo

- [ ] `git push public deepthought:main`
- [ ] Verify GitHub shows updated paper

---

## Notes

- D-TVA in Future Work: keep as-is, no change needed
- Meta-evaluation section: keep as-is, it's a distinctive strength
- Multi-agent / DMN paragraphs: compress but do not delete
- "TVA is not for Level 2 systems" scope boundary: keep as-is
- Collapse Pulse / Safety-Creativity tension: keep as-is
