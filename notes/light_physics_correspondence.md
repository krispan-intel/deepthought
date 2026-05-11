# Light as Operation — Physical World Correspondence

*Appendix to emergent_time_hypothesis.md. Speculative. Private.*
*2026-05-11. Kris Pan.*

---

## The Core Claim

The Dynamic TVA framework and physical electromagnetism share the same skeleton:

| Dynamic TVA | Physical World |
|---|---|
| Latent space | Physical state space / Hilbert space |
| Anchor C | Detector / observer / apparatus |
| Illumination operator L_C | EM propagation + interaction + measurement |
| Void | Unobserved / absent state response |
| Information absorption | Interaction causing state update |
| Anchor-time dτ_C | Internal entropy / state-change clock |
| Rank(L_C) | Channel capacity / accessible modes |

**Same equations, different underlying space:**

```
Dynamic TVA:         ΔO_C = L_C(M_τ, ΔI)      dτ_C = ‖ΔO_C‖_C
Physical world:      Δρ_D = M_D ∘ L_EM(Δρ_S)  dT_D = D(ρ_D', ρ_D)
```

---

## What "light as operation" means physically

Physical light is not just "a thing that flies."
It is the operation:

```
source state difference → field propagation → detector state change
```

Formally:

```
L_EM : ΔS_source → ΔS_detector
```

### Maxwell version (classical)

The retarded Green's function:

$$A^\mu(x) = \int G_{\text{ret}}(x, x')\, J^\mu(x')\, d^4x'$$

This is the explicit light-operation: source current J changes → electromagnetic field A propagates → observer at x sees the effect. The *retarded* nature enforces causal direction (only past → future).

### Quantum version (channel)

$$\rho_{\text{out}} = \mathcal{M}_D \circ \mathcal{L}_{EM} \circ \mathcal{P}_S(\rho_{\text{in}})$$

- P_S: source encodes state difference into photon modes
- L_EM: electromagnetic field propagates
- M_D: detector measures / projects

### Relativistic version (causal boundary)

Light cones define *which* events can causally influence which others:

```
C+(A) = {B | B reachable from A by causal propagation}
```

The light cone boundary is `ds² = 0` — not a definition of light, but a consequence of light being the fastest causal propagator.

---

## Two kinds of time in physical world

The stone example requires a careful distinction:

**(a) Relativistic proper time:** `dτ² = -ds²/c²`
The stone has this regardless of wind and rain. It exists along a worldline.

**(b) Informational / internal time:** `dT_A = D(ρ_A(t+dt), ρ_A(t))`
The stone's *internal state change clock*. If nothing changes its internal state, this is zero even though proper time flows.

The emergent_time_hypothesis.md framework describes **(b)**, not (a).

> The stone doesn't lack proper time. It lacks *informational time* — the ability to read out elapsed time from its own state changes.

---

## Why this doesn't conflict with standard physics

Photon = field excitation (quantum electrodynamics).
Light-operation = source difference → propagated field → detector update.

These are complementary descriptions, not competing ones.
The operation view adds: "what does light *do* functionally?" on top of "what is light made of?"

---

## Status

This is philosophical confirmation, not new math.
The Dynamic TVA framework is consistent with physical intuitions about light and time.
No new predictions. No action required.

Return here if Dynamic TVA (Paper 3) needs physical grounding arguments.
