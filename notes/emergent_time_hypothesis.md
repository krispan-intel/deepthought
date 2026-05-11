# Emergent Time in Knowledge Space — Hypothesis Notes

*Draft. 2026-05-11. Kris Pan.*
*Not a paper. A place to hold ideas before they're ready.*

---

## Starting Intuition

> "No external input, no time. A stone has no time — but wind and rain give it time."

Time is not a background parameter. Time is an emergent quantity — it only exists when a system's state changes in response to input.

`Δtime = f(external input density, meaningful state change)`

If the stone is hard enough that wind doesn't change its shape: `ΔS = 0` → `ΔT = 0`. Time does not flow for that stone.

---

## The Emergent Time Equation (revised)

The original formulation:

$$\Delta \mathcal{T} = \int_{\text{Path}} \mathcal{C}(\mathbf{E}_{\text{ext}}, \mathbf{R}_{\text{int}}) \cdot d\mathbf{S}$$

Had three open problems: undefined coupling function C, D* circular definition, and the free-falling clock counterexample.

**All three are resolved by Anchor.**

The coupling function C is not mysterious — it is the projection of dS onto the Anchor direction:

$$\mathcal{C} = \langle d\mathbf{S},\, \hat{\mathbf{C}}_{\text{anchor}} \rangle$$

D* is not computed from corpus statistics alone — it is defined relative to Anchor C:

$$D^* = D^*(\mathbf{C})$$

The revised equation:

$$\boxed{\Delta \mathcal{T}_{\mathbf{C}} = \int_{\text{Path}} \langle d\mathbf{S}_{D^*(\mathbf{C})},\, \hat{\mathbf{C}} \rangle}$$

**Reading:** Time = accumulated projection of state displacement onto the Anchor direction, within the Anchor-defined signal subspace.

Three consequences:
1. **Time is Anchor-relative, not absolute.** No Anchor → no time. Consistent with GR proper time being observer-dependent.
2. **D* circular definition resolved.** Anchor fixes the direction; D*(C) is well-defined. If corpus changes, D*(C) changes traceably.
3. **Free-falling clock resolved.** The clock's Anchor = its own self-continuation. Internal phase evolution is its time. No contradiction with QM.

The stone has no Anchor (no self-maintenance goal, no intent) → nothing to project onto → ΔT = 0.

Where:
- **ΔT** — emergent time for this system
- **dS** — displacement in high-dimensional state space
- **E_ext** — external input tensor (new papers, commits, events)
- **R_int** — internal reorganization tensor (self-reflection, dream consolidation, quantum fluctuation)
- **C** — coupling function: how efficiently the system absorbs and transforms input

### Key properties
- If `dS = 0` (no state change despite input) → `ΔT = 0`
- If `E_ext = 0` but `R_int > 0` and internal reorganization causes `dS ≠ 0` → time still flows
- High-frequency external input + high coupling → time accelerates

---

## Connection to Existing Physics

This framework maps onto known results:

**KL Divergence (Information Theory):**
$$\Delta \mathcal{T} \propto D_{KL}(P_{\text{new}} \,||\, P_{\text{old}})$$
Time = information distance between old and new state.

**Fubini-Study Metric (Quantum Mechanics):**
$$ds^2 = 1 - |\langle \Psi(t) | \Psi(t+dt) \rangle|^2$$
Time = distance traveled in Hilbert space.

**Page-Wootters Mechanism (1983):**
The universe as a whole has no time (`Ĥ|Ψ⟩ = 0`).
Time emerges from entanglement between a clock subsystem C and the rest R:
$$|\Psi\rangle = \sum_t |t\rangle_C \otimes |\psi(t)\rangle_R$$

**Thermal Time Hypothesis (Rovelli & Connes, 1994):**
$$H_{\text{thermal}} = -\ln \rho$$
Time emerges from our incomplete information about the system's state.

---

## The Bridge: Anchor IS the Bridge

The connection between TVA and emergent time is not analogy — it is identity.

| TVA | Emergent Time |
|---|---|
| Anchor C filters 10^10 voids → meaningful ones | Anchor C filters infinite state changes → time |
| D*(C) = optimal signal subspace for Anchor | D*(C) = signal subspace where time is meaningful |
| C1: A and B must point toward Anchor | dS must project onto Anchor to count as time |
| Void = unoccupied coordinate relative to Anchor | Time = displacement relative to Anchor |

**Anchor is not a bridge between TVA and emergent time. Anchor IS the same mechanism operating at two scales.**

D* is a consequence of Anchor, not the cause. The right order:
1. Anchor defines the direction of meaning
2. D*(C) is the optimal subspace for that direction
3. Time = projection of state change onto that subspace

## The Missing Piece: TVA Dimensionality Theorem

**New hypothesis:** Not all dimensions contribute equally to meaningful state change.

The TVA Dimensionality Theorem defines D* — the optimal dimension where signal dominates noise. Dimensions beyond D* are spurious; state changes in those dimensions are noise, not real information.

**Proposed refinement:**

$$\Delta \mathcal{T} = \int_{\text{Path}} \mathcal{C}(\mathbf{E}_{\text{ext}}, \mathbf{R}_{\text{int}}) \cdot d\mathbf{S}_{D^*}$$

Where `dS_{D*}` is the state displacement projected onto the D*-dimensional signal subspace only.

**Implications:**
- Time computed in full high-dimensional space includes spurious noise
- True emergent time should only count state changes in the meaningful subspace
- D* is determined by corpus statistics (γ, N) — so time is domain-specific

---

## Connection to Dynamic TVA

If time in knowledge space = KL divergence of state changes, then:

**Event time** for a knowledge domain = cumulative KL divergence of its embedding state.

This replaces commit frequency (too crude) with something more principled:
- A domain with 1000 trivial commits may have small `D_KL` → little time has passed
- A domain with 1 paradigm-shifting paper may have large `D_KL` → large time step

**Dynamic TVA time axis:**
$$t_{\text{knowledge}} = \sum_{\text{events}} D_{KL}(P_{\text{after}} \,||\, P_{\text{before}})$$

Projected onto D* subspace to filter noise.

---

## Broader Connections (speculative)

- Universe as mother corpus: each black hole singularity is a void in mother spacetime; a child universe fills it — recursive topological expansion at cosmic scale
- Quantum entanglement as shared pointer: two entangled particles share a memory address set at the Big Bang; measurement is a read, not a write — no faster-than-light signaling needed
- Minimum unit of universe = bit; matter/energy/spacetime are different read patterns of the same underlying information
- Mother universe dimensionality: if D* ~ 1063 for a mixed technical corpus of 150k documents, what is D* for the universe's corpus? Possibly 2^11 = 2048 (humor: matches M-theory's 11 dimensions at a different scale)

---

## Where Does Anchor Come From?

In TVA: clean. The inventor gives it. Human intent = Anchor C.

In physics: harder.

**(a) Scope restriction (recommended first):**
Emergent time applies only to systems with a self-maintenance goal (autopoietic systems: life, knowledge systems, AI, any system that maintains its own existence). Anchor = the direction of self-continuation. Electrons don't need this framework; QFT handles them fine.

**(b) Future hook:**
Anchor emerges from autopoiesis naturally. Any self-sustaining system has an implicit Anchor = its survival direction. This connects to Friston's Free Energy Principle (organisms minimize surprise to maintain existence = implicit Anchor).

Recommended: state (a) to fix scope, leave (b) as future work.

## What Is Not Settled

- Whether KL divergence or Fisher information metric is the right dS measure
- Whether the projection ⟨dS, Ĉ⟩ correctly captures all meaningful time (may miss orthogonal but important changes)
- The reflexivity problem: reporting a void changes D*(C) for that domain — needs formal treatment
- Early universe: no observer, no Anchor — how did the first time emerge?

---

## Status

Sketch only. Not ready for a paper.
Return to this after Paper 2 (TVV) is done.

**The three papers may be one:**
- Paper 1 (TVA): Anchor defines meaningful voids in knowledge space
- Paper 2 (TVV): Anchor defines meaningful time (void lifecycle)
- Paper 3 (?): Anchor as a universal mechanism — same principle at all scales

TVV is the bridge. If dynamic TVA must track how voids evolve over time, it must answer "time relative to what Anchor?" — and that question is exactly emergent time.
