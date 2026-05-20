# Anchor Drift Metric — Working Draft

*2026-05-11. Kris Pan.*

---

## Ontological Clarification

This framework does not posit the existence of light or time inside latent space.

The terms "light" and "time" are used only as source-domain analogies:
- physical light contributes the idea of a propagation/probing operation
- physical time contributes the idea of accumulated state change

In the formal model, these are replaced by:
- an **Anchor-conditioned response operator** `R_C`
- an **Anchor-relative drift coordinate** `D_C`

Dynamic TVA contains no high-dimensional photons, no latent clock, and no physical temporal dimension. It only contains event-ordered transformations of knowledge states under an Anchor.

---

## Starting Intuition

> "No external input, no time. A stone has no time — but wind and rain give it time."

Anchor Drift is a knowledge-state metric — it only exists when a system's state changes meaningfully relative to an Anchor.

---

## Core Equations

$$\Delta O_C^{(n)} = R_C(K_n,\, \Delta I_n)$$

$$dD_C^{(n)} = \|\Delta O_C^{(n)}\|_C$$

$$D_C(N) = \sum_{n=1}^{N} dD_C^{(n)}$$

Where:
- `K_n` = corpus state after event n
- `ΔI_n` = information injected at event n
- `R_C` = Anchor-conditioned response operator
- `D_C` = Anchor-relative drift coordinate (non-negative, event-ordered)

The response operator decomposes as `R_C = P_C ∘ W_C ∘ T`:
- `T` = transition/propagation through knowledge state
- `W_C` = Anchor weighting
- `P_C` = Anchor projection

---

## Working Definition (Implementable)

$$\Delta D_C(S_1 \to S_2) = \big\| \Pi_{D^*(\mathbf{C})}(S_2 - S_1) \big\| \cdot \cos\theta_{\mathbf{C}}$$

Three metric choices for `‖·‖_C`:

| Layer | Formula | Use |
|---|---|---|
| **Fisher / Fubini-Study** | $ds^2 = 1 - \|\langle\Psi_t\|\Psi_{t+dt}\rangle\|^2$ | Base metric |
| **KL divergence** | $D_{KL}(P_{\text{after}} \| P_{\text{before}})$ | Event-level distance |
| **Anchor projection** | $\|\Pi_{D^*(\mathbf{C})}(S_2-S_1)\| \cdot \cos\theta$ | Observer-relative drift |

Related formal frameworks: Page-Wootters (1983), thermal time (Rovelli-Connes 1994), Fubini-Study quantum metrics. No claim of physical identity — structural analogy only.

---

## Three Open Problems Resolved by Anchor

| Problem | Resolution |
|---|---|
| Coupling function undefined | `R_C` projection ⟨dS, Ĉ⟩ IS the coupling |
| D* circular definition | D*(C) defined relative to Anchor; changes traceably |
| Reflexivity | Reporting is a discrete D_C jump (see below) |

---

## The Bridge: Anchor IS the Bridge

| S-TVA | Anchor Drift Metric |
|---|---|
| Anchor C filters 10^10 voids → meaningful ones | Anchor C filters infinite state changes → drift |
| D*(C) = optimal signal subspace | D*(C) = signal subspace where drift is meaningful |
| Void = unoccupied coordinate relative to Anchor | Drift = displacement relative to Anchor |

Anchor is the same mechanism at two scales.

---

## Connection to D-TVA

$$D_C^{\text{knowledge}}(N) = \sum_{n=1}^{N} D_{KL}(P_n \,||\, P_{n-1})\big|_{D^*(\mathbf{C})}$$

- 1000 trivial commits → small D_KL → little drift
- 1 paradigm-shifting paper → large D_KL → large drift step

---

## Applications (Concrete)

**1. D-TVA event ordering** — replace commit timestamp with cumulative `D_C`.

**2. LLM staleness** — LLM is stale when `D_C > θ_stale`. Measured in Anchor-relative drift, not months.

**3. LLM response quality** — filler tokens have `dD_C ≈ 0`; key reasoning steps have large `dD_C`. True response depth ≠ token count.

---

## D-TVA Formalization

### Void velocity

Not physical velocity — drift-normalized void displacement:

$$\vec{V}_{v}^{C} = \frac{dM_v}{dD_C}$$

Where `M_v` = void midpoint / void representative.

### Reflexivity as jump discontinuity

$$K^-,\, R_C^- \xrightarrow{\text{Report } Q} K^+,\, R_C^+$$

$$dD_C^{\text{report}} = \|O_C^+ - O_C^-\|_C$$

$$D_C^+ = D_C^- + dD_C^{\text{report}}$$

Reporting a void is a discrete D_C jump. Observation is a topological event that advances drift. (See Issue #2.)

---

## Collapse Pulse

Entropy decrease does not imply negative drift.

`D_C` is accumulated response magnitude — non-negative by construction. A falsification event may reduce entropy, rank, or hypothesis volume, but still contributes positive `dD_C` because Anchor-observable structure has changed.

```
Magnitude:  dD_C = ‖ΔO_C‖_C ≥ 0   (always positive)
Direction:  σ_C = sign(ΔH_C)         (separate scalar)
```

**Full drift formula:**

$$dD_C = \alpha\, W_2 + \beta\, W_p(PD) + \gamma\, |\Delta H_C| + \delta\, |\Delta \text{rank}_C|$$

**Event taxonomy:**

| Event | dD_C | σ_C | Topology |
|---|---|---|---|
| Innovation | large | +1 | void filled |
| Discovery | moderate | +1 | new void revealed |
| Falsification | large | -1 | void death, rank drop |
| Paradigm shift | very large | ±1 | global topology surgery |
| Maintenance | small | 0 | no change |

---

## Axiom System

1. **Anchor** — defines what differences are observable
2. **R_C** — Anchor-conditioned response operator: `R_C : (K_n, ΔI_n) → ΔO_C`
3. **Drift D_C** — `D_C = Σ ‖ΔO_C‖_C ≥ 0`
4. **Void** — position that is Anchor-responsive but absent
5. **Collapse** — positive drift + contraction of hypothesis topology

---

## Void Taxonomy

| Type | Description |
|---|---|
| **True Void** | Genuine unfilled innovation space |
| **False Void** | Appears empty but not viable — eliminated by compressive R_C |
| **Shadow Void** | Caused by data gap or Anchor blind spot |
| **Emergent Void** | Forming — not yet fully visible |
| **Collapsed Void** | Killed by falsification |

LLM hallucination = model fills **False Void** without compressive R_C (no falsification signal).

---

## Ontology Table

| Borrowed physical term | Formal replacement in D-TVA | Exists in latent space? |
|---|---|---|
| Light | Anchor-conditioned response operator `R_C` | No |
| Time | Anchor-relative drift coordinate `D_C` | No physical time |
| Velocity | Drift-normalized displacement `dM_v / dD_C` | Not physical velocity |
| Collapse | Contraction of Anchor-visible hypothesis topology | Yes, as topology update |
| Observation | Anchor-conditioned projection/update | Yes, as operation |

---

## Paper-ready sentence

> **Dynamic TVA does not introduce light or time into latent space. It replaces them with their operational analogues: an Anchor-conditioned response operator R_C that makes latent differences observable, and an Anchor-relative drift coordinate D_C that accumulates the magnitude of such observable changes.**

---

## Status

Working draft. Not a paper yet.
Return after TVV (Paper 2) is done.

**Three papers:**
- Paper 1 (S-TVA): Anchor defines meaningful voids
- Paper 2 (TVV): Validates voids are real — *the bridge*
- Paper 3 (D-TVA): Voids move, collapse, form in Anchor-drift

Open issues: #1 (norm), #2 (reflexivity jump), #3 (Linux experiment).

---

## External Peer Suggestions (2026-05-20)

### Issue #1 — Metric mismatch in Collapse Pulse formula

The four terms in:

$$dD_C = \alpha\, W_2 + \beta\, W_p(PD) + \gamma\, |\Delta H_C| + \delta\, |\Delta \text{rank}_C|$$

come from fundamentally different mathematical worlds (optimal transport, TDA, information theory, linear algebra) with incompatible scales. Cross-corpus scaling (10k → 1M documents) will break the linear weighting.

**Suggested directions:**
- Use $W_2$ as the base metric; treat the other three as perturbation terms on the manifold rather than co-equal summands.
- Normalize via Fisher Information Metric / information geometry — project all four terms into the tangent space of the same Riemannian manifold before combining.
- Or: treat $\alpha, \beta, \gamma, \delta$ as attention-style dynamic weights learned per anchor, rather than global hyperparameters.

### Issue #2 — Reflexivity damping (anti-snowball)

The discrete reflexivity jump:

$$D_C^+ = D_C^- + dD_C^{\text{report}}$$

risks positive-feedback explosion in a closed-loop AI system (AI finds void → AI fills void → AI re-evaluates → more shadow voids from the reporting act itself → runaway drift).

**Suggested fix:** Introduce a damping factor or gauge-theory-style cancellation term in $R_C$ to absorb observation-induced false topology deformation. Distinguish "epistemic drift from new knowledge" vs "drift from the act of reporting."

### Issue #3 — Linux experiment as calibration oracle

Linux kernel commit history is the natural ground-truth test:
- 1000 routine driver fixes → $D_{KL} \approx 0$, no meaningful drift
- Linus merging a core memory architecture rewrite → large $dD_C$ spike

**Key prediction:** Under Euclidean L2, large-diff maintenance commits (10k lines of boilerplate) will dominate over a 10-line paradigm-shifting change. Under Anchor-projection + $\cos\theta_{\mathbf{C}}$, the 10-line core change should produce higher drift. This comparison *validates the observer-relative drift formulation* — it's a falsifiable test.

Use this to reverse-engineer Issue #1: whichever norm choice makes the Linux ground-truth ranking correct IS the right norm.

**Why Linux kernel is an unfairly good testbed (intentional choice):**

RFC introduces a new mechanism = explicit void acknowledgment by domain experts,
structured as: Problem statement ("no mechanism for X") → proposed fill → community review.
This gives:
- Human-expert-labeled void ground truth (no annotation needed)
- Clean temporal cut (train < T_RFC, RFC is held-out validator)
- Falsifiable dD_C prediction: RFC commit >> maintenance patch
- Multi-scale signal: RFC > feature commit > bugfix > style cleanup

Compared to other domains (biology, economics, social science), Linux kernel has:
- Git history with exact timestamps and diff sizes
- RFC/patch review threads as explicit epistemic debate records
- Linus's merge decisions as community consensus labels
- 30+ years of continuous, structured knowledge accumulation

This is not "cheating" — it is choosing the domain with the cleanest measurement
instrument to validate the framework first. Standard scientific practice.
Generalization to noisier domains (arXiv, clinical trials, patent filings) is Paper 3 §6.

### LLM hallucination definition — keep in abstract

The sentence:

> **"LLM hallucination = model fills False Void without compressive $R_C$"**

is paper-abstract quality. The topological explanation (model follows geodesic into empty region, lacks reality-world compressive validation) is the cleanest formal definition of hallucination in the literature. Do not bury it.
