# Dynamic TVA — Definitions Inventory

*What has actually been defined. No associations, no philosophy, no future work.*
*When lost, come back here. 13 objects, 3 core, one sentence.*

---

## Layer 1 — Static TVA (Paper 1, implemented, empirically validated)

**1. Topological Void** — triad (A, B, C) satisfying:
- C1: A, B semantically cohesive with Anchor C
- C2: pairwise similarity in marginality band [τ_low, τ_high]
- C3: shared sparse lexical bridge token
- C4: SLERP geodesic midpoint unoccupied in corpus

**2. SLERP Vacancy Probe** — spherical geodesic midpoint instead of linear interpolation; symmetric w.r.t. A and B.

**3. Adaptive Marginality Calibration** — τ_domain and [τ_low, τ_high] derived from corpus statistics, not hardcoded.

**4. TVA Dimensionality Theorem**
```
D* = [γ·ln(N) / k·(1 − D_LLM^(−γ))]^(1/(γ+1))
```
Optimal embedding dimension given corpus size N, decay exponent γ, LLM dimension D_LLM.

---

## Layer 2 — Anchor-Time (Paper 2 / TVV, defined, experiment pending)

**5. Anchor-Conditioned Illumination Operator L_C**
```
L_C : (M_τ, ΔI) → ΔO_C
```
Three-layer decomposition: `L_C = P_C ∘ W_C ∘ T` (conceptual; formal construction is Issue #1).

**6. Anchor-Time dτ_C**
```
dτ_C = ‖ΔO_C‖_C ≥ 0
```
Full formula: `dτ_C = α·W_2 + β·W_p + γ·|ΔH_C| + δ·|Δrank_C|`
Weights α,β,γ,δ not yet specified — this is Issue #1 (P0).

**7. Anchor-Time vs Calendar-Time Decoupling** — empirical mapping φ: t_human → τ_C. No bijection. Sync points only.

---

## Layer 3 — Dynamic TVA (Paper 3, defined, awaits Paper 2 data)

**8. Void Velocity Vector**
```
V_void^C = dC_τ / dτ_C
```
Tracks void midpoint motion in Anchor-time: expanding / contracting / forming.

**9. Reflexivity as Jump Discontinuity** (Issue #2)
```
dτ_C^report = ‖O_C^+ − O_C^−‖_C
```
Reporting a void is a discrete τ_C jump, not a smooth limit. Observation is a topological event.

**10. Collapse Pulse** — falsification event:
- dτ_C ≥ 0 always (magnitude forward)
- σ_C = sign(ΔH_C) (direction separate)
- Signatures: Δrank_C < 0, Betti numbers drop, bar death in persistence diagram

**11. Event Taxonomy**

| Event | dτ_C | σ_C | Topology |
|---|---|---|---|
| Innovation | large | +1 | void filled |
| Discovery | moderate | +1 | new void revealed |
| Falsification | large | -1 | void death, rank drop |
| Paradigm shift | very large | ±1 | global topology surgery |
| Maintenance | small | 0 | no change |

**12. Void Taxonomy**

| Type | Description |
|---|---|
| True Void | Genuine unfilled innovation space |
| False Void | Appears empty but not viable |
| Shadow Void | Data gap or Anchor blind spot |
| Emergent Void | Forming, not yet fully visible |
| Collapsed Void | Killed by falsification |

**13. Five-Axiom System**
- A1 — Anchor defines observability
- A2 — Light is an Anchor-conditioned operation: `L_C : (M_τ, ΔI) → ΔO_C`
- A3 — Time is accumulated magnitude of observable change: `τ_C = Σ ‖ΔO_C‖_C`
- A4 — Void is illuminated absence under an Anchor
- A5 — Collapse is positive Anchor-time + contraction of hypothesis topology

---

## The Three Core Objects

Everything else derives from these three:

1. **Anchor C** — defines observability
2. **L_C** — Anchor-conditioned operator
3. **dτ_C = ‖L_C output‖** — time

---

## What Has NOT Been Defined (important boundaries)

- ❌ What light *is* — only what it *does*
- ❌ Absolute time — only Anchor-relative time metric
- ❌ Consciousness / intelligence / AGI
- ❌ Cosmology (association, not derivation)
- ❌ Unification of physical and informational light (explicitly declined)

These are the framework's **boundaries**, not defects.

---

## One sentence

> **Anchor C is the mathematical object that defines observability; void, light, and time are all derived operators of the Anchor.**

---

## Open Issues

- **Issue #1** — Define norm ‖·‖_C and weights (P0)
- **Issue #2** — Formalize reflexivity as jump discontinuity
- **Issue #3** — Linux kernel scheduler Anchor-time experiment
