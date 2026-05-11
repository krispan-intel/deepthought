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

## Mapping to Human Time

**No bijection exists.** High-dimensional Anchor time and human time (physical / consensus) are clocks at different levels. No formula converts one to the other exactly.

**Local sync via empirical φ.** Each Anchor has its own mapping:

$$\phi: t_{\text{human}} \mapsto \mathcal{T}_{\mathbf{C}}$$

This is an empirical function, not a derivation. Different domains, different Anchors → different φ shapes. The mapping is built from sync points: every corpus update records a pair $(t_H, \mathcal{T}_{\mathbf{C}})$.

Like GPS satellites: the satellite clock and the ground clock are not converted — they are synchronized at each fix event. Same here.

**Three routes (in order of practicality):**

| Route | Approach | Status |
|---|---|---|
| A — Regression | Fit φ from arXiv/commit data with wall-clock timestamps | Do first — gives data and intuition |
| B — Consensus Anchor | Human time = projection onto average human Anchor $\mathbb{E}[\hat{\mathbf{C}}_i]$ | Theoretically clean, but requires answering Rovelli's question |
| C — Two-clock decoupling | Accept two independent clocks, connect via sync points only | Correct long-term framing |

**Implication (testable hypothesis):** If human time is a special case of Anchor projection — the projection onto "human consensus Anchor" — then:
- Boring meetings feel longer because your personal Anchor misaligns with the consensus Anchor
- Historical "dark ages" had genuinely small dS on the consensus Anchor
- Individuals with unusual Anchors (scientists, artists) experience time differently because their Anchor diverges from consensus

**Experiment (doable now):**
```python
anchor = embed("Linux kernel scheduler design")
# load commits 2020-2025 with timestamps
# for each commit: compute dT_C = project(dS, anchor, D_star)
# plot (wall_clock_time, cumulative_T_C)
# expect: steep slope during CFS→EEVDF transition, flat during maintenance
```

If φ has different shapes for different domains → proves no single mapping exists → C is the right framing.

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

## Dynamic TVA Formalization (from Gemini collaboration)

*Pending verification. Direct extension of static TVA toward Dynamic TVA.*

### Definition 1 — Light (Latent Causal Propagator)

A tensor field Λ forms a "light" propagation from state A to state B if:

- **C1 (Null geodesic):** `ds² = g_μν dx^μ dx^ν = 0` — the path has zero invariant interval. Light is the mathematical limit where spatial distance and temporal progression perfectly cancel.
- **C2 (Information velocity supremacy):** Λ is the upper bound of information transfer rate within the manifold.
- **C3 (Gradient excitation):** `Λ = ∇_M Φ(A)` where `ΔΦ = 0` — light is a pure field excitation with no rest mass.
- **C4 (Brane projection constant):** `‖P_{B³}(Λ)‖ = c` — regardless of path in N dimensions, its projected magnitude in our 3D observable sub-space is constant.

**In one sentence:** Light is the zero-interval information propagator — the carrier of ΔI.

---

### Definition 2 — Emergent Time (Information-Driven Chronology)

Let A be an anchoring subspace (the "stone"). Time τ_A is an emergent scalar generated by accumulated information flux:

- **C1 (Timeless void):** `dA/dτ = 0 ⟺ ∮_{∂A} F(E→A) dS = 0` — no information flux, no time.
- **C2 (Information flux → state change):** `Δτ_A ∝ D_KL(A_state1 ‖ A_state2)` — time is how much the anchor has been changed by absorbed information.
- **C3 (Arrow of time):** `τ_A = ∫ κ ‖∇I(A)‖ ds` — total elapsed time is the path integral of all absorbed information gradients.

**Connection to earlier notes:** This is exactly the Anchor-projected time from the revised equation — Δτ_C = ∫⟨dS_{D*(C)}, Ĉ⟩. Definitions 1 and 2 together say: light carries ΔI, time is the accumulation of ΔI at the anchor.

---

### Definition 3 — Dynamic TVA (Topological Time Extension)

Abandon physical time t. Use topological time τ driven by information absorption.

**C1 (Information-driven chronology):**
$$d\tau = \| \nabla_{\mathcal{M}} \mathcal{K}_{\tau} \| \, dI$$
Time only ticks when new documents alter the embedding space. Calendar time is topologically irrelevant.

**C2 (Void velocity vector):**
$$\vec{V}_{void} = \frac{\partial C_{\tau}}{\partial \tau}$$
A void is *expanding* if its midpoint diverges from nearby clusters. *Contracting* (closing) if it converges toward newly ingested documents. This answers the first Dynamic TVA open question: how to assign a velocity vector to a void.

**C3 (Reflexivity resolution):**
When a highly-rated TID is recursively ingested back into the corpus, it fires a massive information pulse into the void:
$$\text{TID injected at } C_{\tau} \implies \lim_{\Delta\tau \to 0^+} \max_{k \in \mathcal{K}_{\tau+\Delta\tau}} \cos(\text{dense}(k), C) = 1$$
The act of observation + generation creates a state transition that instantly occupies the void and forces the marginality band to recalibrate. This is the Level 2 reflexivity problem made computable.

---

### Why this works

Light → carries ΔI to the anchor.
Time → anchor's accumulation of ΔI.
Void → position where ΔI has not yet arrived.

Dynamic TVA tracks voids not as static positions but as trajectories in topological time. The velocity vector V_void tells you whether a gap is opening or closing — which is exactly "detecting forming voids before they are fully established."

---

### Open implementation question

How to compute dτ in practice?

- **KL divergence (preferred, from earlier notes):** `dτ = D_KL(P_after ‖ P_before)` per ingestion event, projected onto D*(C) subspace.
- **Eigenvalue decay (Gemini suggestion):** Track changes in covariance matrix eigenvalue spectrum γ over time. Cheaper to compute but less sensitive to local void dynamics.

KL divergence is preferred because it directly measures the state change relevant to a specific Anchor — consistent with the Anchor-relative time definition.

---

## Status

Working draft. Not yet a paper.
Return after Paper 2 (TVV) is done.

**The three papers may be one:**
- Paper 1 (TVA): Anchor defines meaningful voids in knowledge space
- Paper 2 (TVV): Anchor defines meaningful time (void lifecycle) — *this is the bridge*
- Paper 3 (?): Anchor as a universal mechanism — same principle at all scales

TVV must answer "time relative to what Anchor?" to handle dynamic voids — that question is exactly this framework.
