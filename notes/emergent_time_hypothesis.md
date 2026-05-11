# Emergent Time in Knowledge Space — Hypothesis Notes

*Draft. 2026-05-11. Kris Pan.*
*Not a paper. A place to hold ideas before they're ready.*

---

## Starting Intuition

> "No external input, no time. A stone has no time — but wind and rain give it time."

Time is not a background parameter. Time is an emergent quantity — it only exists when a system's state changes meaningfully.

`Δtime = f(external input density, meaningful state change)`

If the stone is hard enough that wind doesn't change its shape: `ΔS = 0` → `ΔT = 0`. Time does not flow for that stone.

---

## Scope: What This Framework Applies To

**(a) Autopoietic systems only.**
Emergent time applies to systems with a self-maintenance goal: life, knowledge systems, AI, any system that maintains its own existence. Anchor = the direction of self-continuation. Electrons don't need this framework; QFT handles them fine.

**(b) Future hook.**
Anchor may emerge from autopoiesis naturally. Any self-sustaining system has an implicit Anchor = its survival direction. Connects to Friston's Free Energy Principle (organisms minimize surprise = implicit Anchor). Leave for future work.

**Early universe (pre-life):** Outside scope (a). Framework does not claim to explain pre-autopoietic time. That is GR/QFT's problem.

---

## The Revised Equation

**Anchor C** is the key. It is the observer's intent, goal, or self-continuation direction — the same concept as Anchor C in TVA.

Notation: **C** = Anchor vector, `Ĉ` = unit direction, `D*(C)` = optimal signal subspace defined by Anchor.

$$\boxed{\Delta \mathcal{T}_{\mathbf{C}} = \int_{\text{Path}} \langle d\mathbf{S}_{D^*(\mathbf{C})},\, \hat{\mathbf{C}} \rangle}$$

**Reading:** Time = accumulated projection of state displacement onto the Anchor direction, within the Anchor-defined signal subspace.

### Symbol definitions
- **ΔT_C** — emergent time relative to Anchor C
- **dS** — displacement in high-dimensional state space
- **D*(C)** — optimal signal subspace defined by Anchor (see TVA Dimensionality Theorem)
- **Ĉ** — unit vector in Anchor direction
- *(No separate coupling function needed — the projection ⟨dS, Ĉ⟩ IS the coupling)*

### Key properties
- `dS = 0` → `ΔT = 0` (no state change → no time)
- No Anchor → no projection → no time
- Internal reorganization alone (`E_ext = 0`, `R_int > 0`) can produce `dS ≠ 0` → time still flows
- High external input + high alignment with Anchor → time accelerates

### Three open problems resolved by Anchor

| Problem | Resolution |
|---|---|
| Coupling function undefined | C = projection ⟨dS, Ĉ⟩ — not mysterious, just inner product |
| D* circular (corpus-defined but corpus changes) | D*(C) is defined relative to Anchor; if corpus changes, D*(C) changes traceably |
| Free-falling clock has no input but has time | Clock's Anchor = self-continuation; internal phase evolution is its time |

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

D* is a consequence of Anchor, not the cause:
1. Anchor defines the direction of meaning
2. D*(C) is the optimal subspace for that direction
3. Time = projection of state change onto that subspace

---

## Connection to Existing Physics

**KL Divergence (Information Theory):**
$$\Delta \mathcal{T} \propto D_{KL}(P_{\text{new}} \,||\, P_{\text{old}})$$
Time = information distance between old and new state.

**Fubini-Study Metric (Quantum Mechanics):**
$$ds^2 = 1 - |\langle \Psi(t) | \Psi(t+dt) \rangle|^2$$
Time = distance traveled in Hilbert space.

**Note:** Fisher information metric is the symmetrized KL on statistical manifolds, and is the classical limit of the Fubini-Study metric. These three may be the same measure in different contexts — a free theoretical unification worth exploring.

**Page-Wootters Mechanism (1983):**
Universe has no absolute time (`Ĥ|Ψ⟩ = 0`). Time emerges from entanglement between clock subsystem and the rest:
$$|\Psi\rangle = \sum_t |t\rangle_{\text{clock}} \otimes |\psi(t)\rangle_{\text{rest}}$$
*Each subsystem is the other's Anchor.*

**Thermal Time Hypothesis (Rovelli & Connes, 1994):**
$$H_{\text{thermal}} = -\ln \rho$$
Time emerges from incomplete information about the system's state.

---

## Connection to Dynamic TVA

Dynamic TVA needs a time axis. Physical time is too crude. Event time (commit count) is too crude.

**Proposed: KL-divergence event time, projected onto D*(C).**

$$t_{\text{knowledge}} = \sum_{\text{events}} D_{KL}(P_{\text{after}} \,||\, P_{\text{before}})\big|_{D^*(\mathbf{C})}$$

Properties:
- 1000 trivial commits with small D_KL → little time has passed
- 1 paradigm-shifting paper with large D_KL → large time step
- Projection onto D*(C) filters spurious dimensions — noise doesn't count as time

---

## Working Definition (Implementable)

For practical use in Dynamic TVA and LLM systems:

$$\Delta \mathcal{T}_{\mathbf{C}}(S_1 \to S_2) = \big\| \Pi_{D^*(\mathbf{C})}(S_2 - S_1) \big\| \cdot \cos\theta_{\mathbf{C}}$$

Where:
- $\Pi_{D^*(\mathbf{C})}$ = projection onto Anchor-defined D* signal subspace
- $\theta_{\mathbf{C}}$ = angle between projected vector and Anchor direction Ĉ
- $\cos\theta_{\mathbf{C}}$ = how much this change points toward the Anchor

Special cases:
- Change orthogonal to Anchor → $\cos\theta = 0$ → ΔT = 0 (changed, but not toward me → no time for me)
- Change along Anchor → ΔT maximum
- No Anchor → formula undefined → no time (the stone)

### Three layers, not three competitors

| Layer | Formula | What it measures |
|---|---|---|
| **Fisher / Fubini-Study** | $ds^2 = 1 - \|\langle\Psi_t\|\Psi_{t+dt}\rangle\|^2$ | Base metric — distance in state space |
| **KL (event layer)** | $D_{KL}(P_{\text{after}} \|\| P_{\text{before}})$ | How far one update moved the distribution |
| **Anchor projection** | $\|\Pi_{D^*(\mathbf{C})}(S_2-S_1)\| \cdot \cos\theta_{\mathbf{C}}$ | How far this moved *for this observer* |

---

## Applications (Concrete)

### 1. Dynamic TVA event ordering
Replace commit timestamp with cumulative $\Delta \mathcal{T}_{\mathbf{C}}$ to sort events.
Gives domain-intrinsic event order — not wall-clock order.

### 2. LLM staleness / aging
LLM is trained at time $t_0$. Corpus keeps changing.
**LLM is stale when:** $\sum \Delta \mathcal{T}_{\mathbf{C}} > \theta_{\text{stale}}$

Not measured in months. Measured in Anchor-relative accumulated change:
- Classical math corpus: LLM never stales
- Frontier AI corpus: LLM stales in weeks

### 3. LLM thinking time (session-level)
Each token changes internal state. But not all tokens are equal.
$\Delta \mathcal{T}_{\mathbf{C}}$ per token = how much that token moved the state toward the Anchor.

**True thinking time ≠ token count.** Filler tokens ("sure", "ok") have ΔT ≈ 0. Key reasoning steps have large ΔT. This gives a metric for "LLM is actually thinking vs. generating noise."

---

## Broader Connections

*Private notes. Speculative. Do not include in any external document without review.*

- Universe as mother corpus: each black hole singularity is a void in mother spacetime; a child universe fills it — recursive topological expansion at cosmic scale
- Quantum entanglement as shared pointer: two entangled particles share a memory address set at the Big Bang; measurement is a read, not a write — no faster-than-light signaling needed
- Minimum unit of universe = bit; matter/energy/spacetime are different read patterns of the same underlying information
- Mother universe dimensionality: if D* ~ 1063 for a mixed technical corpus of 150k documents, what is D* for the universe's corpus? Possibly 2^11 = 2048 (humor: matches M-theory's 11 dimensions at a different scale)

---

## What Is Not Settled

- Whether KL divergence or Fisher information metric is the right dS measure (Fisher is symmetric; KL is not — time direction may require asymmetry)
- Whether projection ⟨dS, Ĉ⟩ correctly captures all meaningful time (may miss orthogonal but important changes)
- The reflexivity problem: reporting a void changes D*(C) for that domain — needs formal treatment
- ~~Early universe: no observer, no Anchor~~ → outside scope (a), not our problem

---

## Status

Working draft. Not yet a paper.
Return after Paper 2 (TVV) is done.

**The three papers may be one:**
- Paper 1 (TVA): Anchor defines meaningful voids in knowledge space
- Paper 2 (TVV): Anchor defines meaningful time (void lifecycle) — *this is the bridge*
- Paper 3 (?): Anchor as a universal mechanism — same principle at all scales

TVV must answer "time relative to what Anchor?" to handle dynamic voids — that question is exactly this framework.
