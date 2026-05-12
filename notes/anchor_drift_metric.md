# Anchor Drift Metric in Knowledge Space — Working Draft

*2026-05-11. Kris Pan.*

---

## Naming Note

> *We deliberately avoid the term "time" for `dD_C`. While it shares formal properties with temporal measures (monotonicity, accumulation, event ordering), it is defined purely on knowledge state space and makes no claim of physical or relativistic interpretation. Readers familiar with thermal time hypotheses or Page-Wootters formulations will recognize structural analogies; we intend none.*

`dD_C` = **Anchor-relative drift** — the accumulated observable response of Anchor C to information changes.

---

## Starting Intuition

> "No external input, no time. A stone has no time — but wind and rain give it time."

Anchor Drift is a knowledge-state metric — it only exists when a system's state changes meaningfully relative to an Anchor.

---

## The Revised Equation

**Anchor C** is the key — the observer's intent or goal direction.

Notation: **C** = Anchor vector, `Ĉ` = unit direction, `D*(C)` = optimal signal subspace.

$$\boxed{\Delta \mathcal{D}_{\mathbf{C}} = \int_{\text{Path}} \langle d\mathbf{S}_{D^*(\mathbf{C})},\, \hat{\mathbf{C}} \rangle}$$

**Reading:** Drift = accumulated projection of state displacement onto the Anchor direction, within the Anchor-defined signal subspace.

| Problem | Resolution via Anchor |
|---|---|
| Coupling function undefined | Projection ⟨dS, Ĉ⟩ IS the coupling |
| D* circular definition | D*(C) defined relative to Anchor; changes traceably |
| Free-falling clock | Clock's Anchor = self-continuation; internal phase evolution is its drift |

---

## Working Definition (Implementable)

$$\Delta \mathcal{D}_{\mathbf{C}}(S_1 \to S_2) = \big\| \Pi_{D^*(\mathbf{C})}(S_2 - S_1) \big\| \cdot \cos\theta_{\mathbf{C}}$$

Three metric choices (not competitors — three levels):

| Layer | Formula | Use |
|---|---|---|
| **Fisher / Fubini-Study** | $ds^2 = 1 - \|\langle\Psi_t\|\Psi_{t+dt}\rangle\|^2$ | Base metric |
| **KL divergence** | $D_{KL}(P_{\text{after}} \| P_{\text{before}})$ | Event-level distance |
| **Anchor projection** | $\|\Pi_{D^*(\mathbf{C})}(S_2-S_1)\| \cdot \cos\theta$ | Observer-relative drift |

Related formal frameworks: Page-Wootters (1983), thermal time (Rovelli-Connes 1994), Fubini-Study quantum metrics. No claim of physical identity — structural analogy at the operator level only.

---

## Connection to Dynamic TVA

$$t_{\text{knowledge}} = \sum_{\text{events}} D_{KL}(P_{\text{after}} \,||\, P_{\text{before}})\big|_{D^*(\mathbf{C})}$$

Properties:
- 1000 trivial commits → small D_KL → little Anchor-drift
- 1 paradigm-shifting paper → large D_KL → large Anchor-drift step

---

## Applications (Concrete)

**1. Dynamic TVA event ordering** — replace commit timestamp with cumulative ΔD_C.

**2. LLM staleness** — LLM is stale when `Σ ΔD_C > θ_stale`. Measured in Anchor-relative drift, not months.

**3. LLM thinking drift** — filler tokens have ΔD ≈ 0; key reasoning steps have large ΔD. True thinking drift ≠ token count.

---

## The Bridge: Anchor IS the Bridge

| TVA | Anchor Drift Metric |
|---|---|
| Anchor C filters 10^10 voids → meaningful ones | Anchor C filters infinite state changes → drift |
| D*(C) = optimal signal subspace | D*(C) = signal subspace where drift is meaningful |
| Void = unoccupied coordinate relative to Anchor | Drift = displacement relative to Anchor |

Anchor is not a bridge between TVA and anchor drift. **Anchor IS the same mechanism at two scales.**

---

## Dynamic TVA Formalization

### Core equations

$$\Delta O_C = L_C(\mathcal{M}_\tau,\, \Delta I)$$
$$dD_C = \|\Delta O_C\|_C$$

Where `L_C = P_C ∘ W_C ∘ T` is the **Anchor-conditioned illumination operator** (formally; "light" is metaphor only).

### Void velocity (answers Paper 1 open question #1)

$$\vec{V}_{void}^C = \frac{dC_\tau}{dD_C}$$

### Reflexivity (answers Paper 1 open question #3)

Reporting a void is a discrete jump event, not a smooth limit:

```
K_{τ-}, L_C^-  →  Report R injected  →  K_{τ+} = U_R(K_{τ-}), L_C^+ = U_R(L_C^-)
dD_C^{report} = ‖O_C^+ - O_C^-‖_C
```

Observation/reporting is a topological event that advances Anchor-drift. (See Issue #2.)

---

## Collapse Pulse

Entropy decrease ≠ time reversal. Falsification = compressive phase transition.

```
Magnitude drift:  dD_C = ‖ΔO_C‖_C ≥ 0   (always forward)
Entropy arrow:   σ_C = sign(ΔH_C)         (direction only)
```

**Full drift formula:**

$$dD_C = \alpha\, W_2(\mu^{\tau+}, \mu^\tau) + \beta\, W_p(PD^{\tau+}, PD^\tau) + \gamma\, |\Delta H_C| + \delta\, |\Delta \text{rank}_C|$$

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
2. **Illumination operator L_C** — Anchor-conditioned operation: `L_C : (M_τ, ΔI) → ΔO_C`
3. **Drift** — `D_C = Σ ‖ΔO_C‖_C ≥ 0`
4. **Void** — illuminated absence under an Anchor
5. **Collapse** — positive Anchor-drift + contraction of hypothesis topology

---

## Void Taxonomy

| Type | Description |
|---|---|
| **True Void** | Genuine unfilled innovation space |
| **False Void** | Appears empty but not viable — eliminated by compressive L_C (falsification) |
| **Shadow Void** | Caused by data gap or Anchor blind spot |
| **Emergent Void** | Forming — not yet fully visible |
| **Collapsed Void** | Killed by falsification evidence |

LLM hallucination = model fills **False Void** without compressive L_C (no falsification signal).

---

## Paper-ready sentence

> **Dynamic TVA treats drift not as calendar duration, but as the accumulated deformation of an anchor-conditioned knowledge topology. The illumination operator is the operation that makes such deformation observable.**

---

## Status

Working draft. Not a paper yet.
Return after TVV (Paper 2) is done.

**Three papers:**
- Paper 1 (TVA): Anchor defines meaningful voids
- Paper 2 (TVV): Validates voids are real — *the bridge*
- Paper 3 (DTVA): Voids move, collapse, form in Anchor-drift

Open issues: #1 (norm), #2 (reflexivity jump), #3 (Linux experiment).
