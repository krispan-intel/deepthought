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

## Dynamic TVA Formalization

*Working draft. Reviewed and corrected from initial Gemini formulation.*

### What "light" means in Dynamic TVA

Light in Dynamic TVA is **not a physical entity**. Do not use `ds²=0`, null geodesics, or `c`.
Those belong to Lorentzian spacetime, not latent space.

> **Light = Anchor-conditioned illumination/propagation operator.**
> It determines which latent distinctions become visible to an Anchor.

Formally: `L_A : ΔK → δ_A M`

- `ΔK` = new information entering the corpus
- `δ_A M` = Anchor-observable deformation of the latent manifold

In practice: new papers arrive → filtered through Anchor relevance → those that shift the Anchor's relevant subspace constitute the "light" that changes that Anchor's world.

The full conceptual chain:

```
Anchor     = the flashlight / reference frame
Light      = L_A, the illumination operator emitted by the Anchor
Latent M   = the knowledge manifold being illuminated
Void       = a position that is illuminated but absent
Time       = accumulated state change under L_A
Dynamic TVA = tracking how voids move in Anchor-time
```

In formal writing: call it **"Illumination Operator"** (safe for reviewers).
Informally: "light" as metaphor, clearly labelled as such.

---

### Definition 1 — Anchor-Light (Illumination Operator)

> **Light is not a state. Light is the operation by which state change becomes observable.**

Light is not information. Information can sit static in a structure.
Light is the *operation* that makes latent distinctions manifest — the propagation, illumination, and detection of difference.

Formally, Anchor-light `L_C` is an operator:

$$L_C : (\mathcal{M}_\tau,\, \Delta I) \mapsto \Delta O_C$$

where:
- `M_τ` = current latent manifold (corpus state at topological time τ)
- `ΔI` = incoming information (new documents, commits, discoveries)
- `ΔO_C` = Anchor-observable change produced by this operation

The operator decomposes as:

$$L_C = P_C \circ W_C \circ T$$

- `T` = propagation: how information spreads through latent space
- `W_C` = Anchor weighting: how the Anchor weighs different distinctions
- `P_C` = projection: collapse to Anchor-observable result

**Rank of light:** `rank(L_C)` = number of independent observable directions this Anchor-light can reveal. Low-rank light has blind spots; full-rank light illuminates everything the Anchor cares about.

**In one sentence:** Anchor-light converts latent distinction into observable distinction, for a specific Anchor.

---

### Definition 2 — Anchor-Time

The two core equations of Dynamic TVA:

$$\Delta O_C = L_C(\mathcal{M}_\tau,\, \Delta I)$$

$$d\tau_C = \|\Delta O_C\|_C$$

Time is the norm of the Anchor-observable change produced by the illumination operation. Nothing else.

**Integrated form:**

$$\tau_C(K_0 \to K_n) = \sum_{i} \|L_C(\mathcal{M}_i, \Delta I_i)\|_C$$

**Properties:**
- 100 trivial papers → small `‖ΔO_C‖` → `dτ_C ≈ 0`
- 1 paradigm-shifting paper → large `‖ΔO_C‖` → large `dτ_C`
- Stone (no Anchor, no `L_C`) → `ΔO_C` undefined → no time

---

### Definition 3 — Dynamic TVA

**Void velocity vector** (answers Paper 1 open question #1):

$$\vec{V}_{void}^C = \frac{dC_\tau}{d\tau_C}$$

- Expanding void: midpoint `C_τ` diverges from nearby clusters → gap is widening
- Contracting void: `C_τ` converges toward newly ingested documents → gap is closing
- Forming void: `‖V_void‖` increasing → not yet visible but detectable early

**Reflexivity resolution** (answers Paper 1 open question #3 — Level 2 dynamics):

When a TID is recursively ingested at void position `C_τ`:

$$\lim_{\Delta\tau \to 0^+} \max_{k \in \mathcal{K}_{\tau+\Delta\tau}} \cos(\text{dense}(k), C_\tau) \to 1$$

The act of reporting fires a "light pulse" (large `L_C(ΔK)`) at the void location, instantly advancing `τ_C` and forcing the marginality band `[τ_low, τ_high]` to recalibrate. Level 2 reflexivity is now computable as a state transition event.

---

### Connection to earlier Anchor-time equation

The revised equation from earlier in this document:

$$\Delta \mathcal{T}_{\mathbf{C}} = \int_{\text{Path}} \langle d\mathbf{S}_{D^*(\mathbf{C})},\, \hat{\mathbf{C}} \rangle$$

is a special case of `D_C(K_{i+1}, K_i)` where the distance is measured as projection onto the Anchor direction within `D*(C)`.

Three definitions, one language:
- Light carries `ΔI` to the Anchor
- Time is the Anchor's accumulation of `D_C`
- Void is where `ΔI` has not yet arrived

---

## Collapse Pulse — Falsification as Topological Event

Entropy decrease ≠ time reversal. A falsification event is a **compressive phase transition** in Anchor-time.

**Key distinction:**

```
Magnitude time:  dT_A = D(ρ_A', ρ_A) ≥ 0    (always forward)
Entropy arrow:   σ_A = sign(H_A' - H_A)       (direction, ±1)
```

A collapse pulse occurs when:
- `dT_A` is large (major state change)
- `σ_A = -1` (entropy decreasing — possibilities pruned)
- `Δrank_A < 0` (fewer observable directions)
- `Δβ_k < 0` (Betti numbers drop — topological voids die)

**Geometric signatures:**

1. **Void death by falsification** — a void `V(τ-)` exists, then `V(τ+)` is invalidated. Not filled by innovation; *cancelled* by evidence.
2. **Volume collapse** — a region of latent space loses Anchor-relevance; its effective volume under `L_C` shrinks.
3. **Rank collapse** — `rank(L_C)` drops; the Anchor's observable dimensions decrease.
4. **Bar death in persistence diagram** — long-lived bars abruptly terminate; `W_p(PD(τ-), PD(τ+))` is large.

**Two kinds of light:**

```
Expansive light = reveals new reachable structure  (σ_A = +1)
Compressive light = eliminates false structure      (σ_A = -1)
```

Both advance time. Falsification is also light.

**Full Anchor-time formula (accounting for collapse):**

$$d\tau_C = \alpha\, W_2(\mu^{\tau+}, \mu^\tau) + \beta\, W_p(PD^{\tau+}, PD^\tau) + \gamma\, |\Delta H_C| + \delta\, |\Delta \text{rank}_C|$$

Record direction separately: `arrow_C = sign(ΔH_C)`

**Dynamic TVA event taxonomy:**

| Event | dτ_C | σ_C | Topology |
|---|---|---|---|
| Innovation | large | +1 | void filled |
| Discovery | moderate | +1 | new void revealed |
| Falsification | large | -1 | void death, rank drop |
| Paradigm shift | very large | ±1 | global topology surgery |
| Maintenance | small | 0 | no change |

---

## Status

Working draft. Not yet a paper.
Return after Paper 2 (TVV) is done.

**The three papers may be one:**
- Paper 1 (TVA): Anchor defines meaningful voids in knowledge space
- Paper 2 (TVV): Anchor defines meaningful time (void lifecycle) — *this is the bridge*
- Paper 3 (?): Anchor as a universal mechanism — same principle at all scales

TVV must answer "time relative to what Anchor?" to handle dynamic voids — that question is exactly this framework.
