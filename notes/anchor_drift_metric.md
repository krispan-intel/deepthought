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

## Paradigm Archive: Erdős 2024 × Dynamic TVA (2026-05-21)

**One-line:** Erdős unit distance proof meta-strategy = 「2D 不夠用 → 升維高維代數對稱性 → 製造大量結構 → 投影回 2D 保留性質」，與 Dynamic TVA 結構同構。

**Connection:**
- Erdős: 2D 平面代數對稱性不足 → 升到 CM 體 K → norm-1 元素大量製造 → Minkowski 嵌入 → 投影回 2D
- Dynamic TVA: embedding 投影不足以量 void dynamics → 升到 anchor 軌跡 / fiber bundle → 找 invariant → 投影回 observable plane

**5 ideas to revisit in Paper 3 (展開時間: 6 月):**

1. **Invariant-based measurement** — 不測「void 在 t 時刻位置」，測「所有 t 都守恆的 invariant」。比 instantaneous scalar 對 noise 穩定。

2. **升維 → 構造 → 降維 三段論** — anchor C 從點升到軌跡 C(t)；void 從點升到 fiber bundle over time；在 bundle 上定義 holonomy / monodromy；投影回 observable。Void Velocity / Collapse Pulse 可能是 fiber bundle invariant 的投影，不是 vector difference。

3. **鴿籠製造結構** — 不精細定義 collapse，觀察時間窗 [t, t+Δ] 內進入 void 鄰域的 paper 數量碰撞。大數法則替代幾何 measurement，對 noisy embedding 特別 robust。

4. **Bounded discriminant 對應** — Erdős 關鍵: 升維但根判別式有界，投影時點密度不崩。Paper 3 必須找對應的有界性保證（anchor drift 速度有界？embedding norm 變化有界？），否則投影回 observable 時 noise 吞 signal。這是 Paper 3 第一個技術 milestone。

5. **Galois 對稱對應** — CM 體的複數共軛自同構保證代數元素在所有嵌入一致。embedding space 的對應對稱？rotation / paraphrase / cross-lingual invariance + anchor drift commutativity，可能是 Paper 3 的 hidden structure。

**警告:** 借 paradigm 不借具體工具。不要強行把 CM 體 / number field 搬到 embedding space（embedding 沒有自然的 number field 結構）。學 strategy，找 embedding space 本身的代數結構（manifold / group action / bundle）。

**信心來源:** 升維 paradigm 在數學史反覆 work — Wiles (Fermat, modular forms)、Tao-Green (算術級數, Gowers norm)、Erdős 2024。Dynamic TVA 是第 N 次應用，不是 first-of-its-kind。

---

## Paradigm Archive: Time-as-Dimension (2026-05-21)

**Lab notebook one-liner:**
> "Dynamic TVA: time-as-dimension, not time-as-parameter. Joint algebraic structure. Quantum-observation paradigm in IR. Milestone 1 (6月): choose joint structure type."

**Core framing shift:**
- ❌ Galileo: embedding space indexed by t → e(t) ∈ R^768, time is external parameter
- ✅ Einstein: embedding × time as joint algebraic structure, time is a dimension of the manifold

「傳播 + drift」都是 Galileo 框架——能描述 anchor 軌跡，不能描述 void cosmology 級別的現象。

**4 candidate joint structures (6月選一個):**

| Structure | Dynamics primitive | Invariant | 適合當... |
|---|---|---|---|
| Fiber Bundle | section over time | holonomy | anchor trajectory |
| Sheaf over Time | restriction map | cohomology | historical accumulation |
| Lorentzian manifold | geodesic | causal structure | citation causality |
| Time-indexed Lie Group | group orbit | orbit invariant | symmetry-driven drift |

直覺猜: Sheaf over Time + cohomology invariant + Lorentzian causal flavor。但 6 月自己決定。

**Selection heuristic (6月用):**
1. corpus 演化有自然 group action? → Lie / group cohomology; 否 → bundle / sheaf
2. 需要因果方向? → Lorentzian; 否 → Riemannian / sheaf
3. 關心歷史回溯? → Sheaf; 否 → Bundle
4. invariant 要 numerical 還是 topological? → curvature vs cohomology

**Quantum observation analogy:**
觀察在量子力學裡 = 升維到 Hilbert space + operator + 投影到 eigenstate。
Dynamic TVA 是同一 paradigm 的 IR 泛化：觀察 = 升維到 joint manifold + invariant + 投影回 observable。

**Paper 4 implication:**
有了 embedding-time 聯合結構，Paper 4 從「lifting paradigm」變成：
> *Algebraic-Topological Foundations of Information Retrieval*

份量 ≈ Deerwester 1990 LSA。

**Milestone 1 is critical:** 選錯結構，後面全部 redo。休息期讓潛意識 incubate，6 月開工再決定。

---

## Paradigm Survey Archive: Lifting_Paradigms_for_Void_Observation.md (2026-05-21)

Full report: `notes/Lifting_Paradigms_for_Void_Observation.md`

**Critical finding:** Gap #2 in the report = verbatim your intuition today:
> "No existing model integrates time and semantics into a continuous pseudo-Riemannian spacetime metric ds² = dt² + g_ij dx^i dx^j... modeling semantic drift, velocity, and void collapse as geodesic trajectories on a unified spacetime manifold"

= "time-as-dimension, not time-as-parameter" = exactly Paper 3.

**Trilogy mapping:**

| Paper | Direction | Gap |
|---|---|---|
| Paper 1 (TVA) | Direction 1: Sheaf Cohomology — void = H¹(F) obstruction | Gap #1: topological-to-semantic mapping |
| Paper 2 (TVV) | negative proof of Gap #1 | Gap #1 boundary established |
| Paper 3 (D-TVA) | Direction 2: Lorentzian Spacetime Cone | Gap #2: continuous spacetime metric |
| Paper 4 (framework) | Cross-pollination #2: Weak Lensing × Sheaf | Gap #1 + #2 unified |
| Paper 5 (future) | Direction 3: Tomographic Inversion | Gap #3: generative manifold inversion |

**Top 3 directions for Paper 3:**

**Direction 1 — Sheaf Laplacian Obstruction Fields**
- void = non-zero H¹(F) (cohomology obstruction)
- k-NN graph + vector stalks + variational restriction maps
- Bayesian Sheaf Neural Networks (Bodnar/Hansen/Gebhart 2022) = direct starting point

**Direction 2 — Lorentzian Spacetime Cone** ← main candidate
- ds² = -dt² + g_ij dx^i dx^j (Minkowski spacetime metric)
- void drift / velocity = geodesic trajectory
- void collapse = reaching causal horizon boundary
- Hasan et al. 2026 WACV (Lorentz Entailment Cone) = direct build-on paper

**Direction 3 — Tomographic Density Inversion (GLIMPSE)**
- queries as background sources, documents as lensing potentials
- semantic "shear" = query neighborhood distortion
- sparse wavelet regularization → continuous density field → void map
- GLIMPSE (Leonard/Lanusse/Starck 2014-2025)

**Paper 5 candidate — Cross-pollination #2: Weak Lensing × Sheaf**
- measure "semantic shear" from query passing through document neighborhoods
- invert shear pattern → "semantic mass map" → identify underdense voids + dark matter bridging concepts
- brand new, nobody has done this

**Key papers to read in June (verified real):**
- Bodnar et al. 2022 — Sheaf Neural Networks (Direction 1 foundation)
- Hamilton et al. 2016 — Diachronic Word Embeddings (temporal alignment baseline)
- Leonard/Lanusse/Starck 2014 — GLIMPSE (Direction 3 foundation)
- Hasan et al. 2026 WACV — Lorentz Entailment Cone (Direction 2 build-on)
- Huynh et al. 2026 — TMRL arXiv 2601.05549 (paradigm 0.5 to differentiate from)

**6-month open question:** Direction 1 (Sheaf) vs Direction 2 (Lorentzian) vs hybrid?
Gut: Sheaf for static void formalization + Lorentzian for dynamics. Hybrid = Paper 3.

---

## Strategic Archive: 3 Takeaways × Deep Research (2026-05-21)

### Takeaway 1 — Your intuition = Gap #2 (global open problem)

Gap #2 verbatim from report:
> "No existing model integrates time and semantics into a continuous pseudo-Riemannian spacetime metric ds² = -dt² + g_ij dx^i dx^j... modeling semantic drift, velocity, and void collapse as geodesic trajectories on a unified spacetime manifold."

You said this morning: "time-as-dimension, not time-as-parameter."
Two independent paths → same open problem.

Implications:
- Paper 3 positioning requires zero justification — cite gap directly
- window is open: zero active competitors on paradigm 1.0
- confidence upgrade: from "I believe" → "objectively open problem"

### Takeaway 2 — 6-year research program structure

| Year | Paper | Mathematical substrate | Paradigm function |
|---|---|---|---|
| 2024 | Paper 1 TVA | Sheaf cohomology (static) | void = H¹ obstruction |
| 2025 | Paper 2 TVV | Impossibility theorem | non-lifted methods fail |
| 2026 | Paper 3 D-TVA | Lorentz manifold | dynamics = geodesic |
| 2027 | Paper 4 Framework | Direction 1+2+3 unified | algebraic-topological IR |
| 2028 | Paper 5 Lensing | Tomographic inversion | semantic → generative |

Paper 2 retrospective upgrade: not "4 methods fail" but "demonstration of Gap #1 unsolvability under non-lifted paradigm" → motivating necessity proof for Papers 3-5.

Paper 1 retrospective upgrade: C1-C4 conditions = engineering operationalization of sheaf cohomology. Can be re-framed as "first sheaf-theoretic operationalization of unknown unknowns in IR."

Program title: **Algebraic-Topological Foundations of Information Retrieval**  
Outcome: 1 paradigm + 5-7 papers + 1 framework  
Comparable: Einstein 1905-1915 arc (special → general relativity)

### Takeaway 3 — Paper 5 candidate: semantic gravitational lensing

Core idea: treat queries as background sources, document corpus as foreground gravitational lenses.
Measure "semantic shear" = coordinate shift of queries passing through document neighborhoods.
Apply GLIMPSE sparse regularization inversion → reconstruct continuous semantic density field.
Identify semantic voids = underdense regions, "dark matter bridging concepts" = overdense regions.
Route sheaf messages *around* voids → reduce hallucinations.

Mathematical analog:
- astrophysics: γ(θ) ≈ ∇²ψ(θ)/2 (shear = lensing potential)
- IR: σ_sem(q) ≈ ∇²Φ_doc(q)/2 (semantic shear)

Why brand new: zero prior literature combining gravitational lensing + IR.
Why compelling: directly addresses LLM hallucination → industrial relevance.
Why Paper 5 not sooner: needs Paper 3 spacetime metric as foundation.

Red flags to watch: (1) don't jump to Paper 5 before Paper 3 ships; (2) lensing is mathematical analog, not 1:1 physical; (3) "semantic dark matter" is too sexy — maintain rigor.

### One-line summary

> "6-year paradigm program 2024-2030: Sheaf (P1) → Impossibility (P2) → Lorentzian (P3) → Framework (P4) → Semantic Lensing (P5). Not a paper collection — a paradigm build."

---

## Engineering Risk: BGE-M3 1024D → Lorentz Manifold (2026-05-21)

**Confirmed embedding dimension: 1024D** (tested in Paper 1/2; 1024 outperforms 768 for this domain).

### Why BGE-M3 is insufficient for Paper 3

BGE-M3 is trained with InfoNCE contrastive loss on (query, positive, negative) triplets.
This enforces **cosine similarity geometry** — the embedding space is optimized for:
- uniform distribution on hypersphere (Wang & Isola 2020 alignment/uniformity)
- high cosine similarity = semantically close
- low cosine similarity = semantically far

Lorentz manifold requires **hyperbolic geometry**:
- distances are exponential not cosine
- hierarchy is encoded by distance to origin (general = near origin, specific = far)
- timelike vs spacelike dimensions have fundamentally different metric signature ds² = -dt² + g_ij dx^i dx^j

**The mismatch:**
```
BGE-M3 output:    unit sphere in R^1024 (cosine space)
Lorentz needs:    Minkowski space R^(1,1024) (indefinite metric)

cosine similarity ≠ hyperbolic distance
flat sphere      ≠ curved hyperbolic manifold
no time axis     ≠ timelike dimension required
```

Projecting BGE-M3 vectors into Lorentz space via exponential map is possible, but:
- semantic relationships learned under cosine objective may not transfer
- no guarantee that "close in cosine" = "close in hyperbolic distance"
- causal cone structure (entailment) has no correspondence in contrastive training

### Three options (choose in June)

**Option A: Post-hoc projection (low cost, high risk)**
- take frozen BGE-M3 1024D vectors
- apply exponential map to project into Lorentz model
- hope cosine neighborhoods survive projection
- risk: semantic structure may be destroyed

**Option B: Fine-tune with hyperbolic objective (medium cost, medium risk)**
- start from BGE-M3 weights
- add hyperbolic contrastive loss (Lorentz distance instead of cosine)
- fine-tune on domain corpus (arXiv CS + Linux kernel)
- risk: catastrophic forgetting of general semantic knowledge

**Option C: Train Lorentz-native embedding from scratch (high cost, low risk)**
- new model trained directly in Lorentz space
- loss function: Poincaré/Lorentz distance + entailment cone constraints
- full control over geometry
- risk: massive compute + need large training corpus

**Current guess:** Option B (fine-tune) is most practical.
BGE-M3 as initialization + hyperbolic fine-tuning on the anchor domain.

### Fallback plan

If Lorentz projection proves intractable (>3 months blocked):
- Paper 3a: Direction 1 (Sheaf Cohomology static formalization) — no embedding change needed
- Paper 3b: Lorentzian dynamics — defer until embedding model resolved

This keeps Paper 3 shipping on schedule regardless of embedding model decision.

### C1-C4 translation to Lorentz manifold

Paper 1 的 4 個 void 定位條件在 Lorentz manifold 上**完整保留邏輯，但計算公式全換**。
這是 Paper 1 → Paper 3 的升維接點 — Paper 1 不被推翻，被升維。

| 條件 | Paper 1 (cosine / R^1024) | Lorentz manifold | 難度 |
|---|---|---|---|
| C1 anchor relevance | cosine(paper, anchor) > θ_a | paper 在 anchor 的 entailment cone 內 | **更自然** — cone 就是 C1 的幾何體 |
| C2 A-B separation | cosine(A, B) < θ_sim | geodesic distance(A, B) > d_min | 換公式，有解析解 |
| C3 midpoint in gap | midpoint M = (A+B)/2 | geodesic midpoint M on arc(A,B) | 最難 — Lorentz geodesic midpoint 複雜但有解 |
| C4 neighborhood empty | no paper near M (cosine ball) | no paper in hyperbolic ball around M | 換距離定義 |

**C1 升維最明顯：** θ_a threshold → entailment cone，幾何意義從「相似度截斷」升級為「概念範疇邊界」。

**C3 是技術難點：** 線性中點 (A+B)/2 在 Lorentz space 無意義。需要 Lorentz geodesic midpoint：
```
M = expₚ(½ · logₚ(q))   where p=A, q=B
```
Geoopt 有實作，但數值穩定性需注意。

**升維時機點就在 C1-C4：** 這 4 個條件是 Paper 1 的核心貢獻，也是 Paper 3 的起點。
Lorentz 版的 C1-C4 = Paper 3 的 §3 Mathematical Formalization 的天然結構。

### Option upgrade: Mixed-curvature product space (2026-05-21)

**Key reframing from second Deep Research report:**

| Option | Description | Est. success rate |
|---|---|---|
| A.1 | Pure exponential map → Lorentz | 35% |
| A.2 | MLP-learned projector (new) | 60% |
| **A.3** | **Mixed-curvature product space ℍ × 𝕊** | **70% ← recommended** |
| B | HypLoRA adapter fine-tune | 85% |
| C | From scratch Lorentz | 95% |

**Option A.3 rationale:**
- Lorentz factor ℍ: handles hierarchy, entailment cone, causal structure
- Spherical factor 𝕊: preserves BGE-M3 original cosine structure
- Two factors decouple — no need to destroy cosine geometry
- Reference: ProCLIP 2026 (just published, build-on opportunity)
- Extra cost vs A.1: +1 month. Cost-benefit ratio: best.

**Option A.2 (new, not in previous commit):**
- Train small MLP to learn cosine → Lorentz mapping
- Supervised by WordNet hierarchy (small dataset, no BGE-M3 retraining)
- Engineering cost: 1-2 months (cheaper than Option B)
- Risk: learned mapping may not generalize

**Risk mitigations (all have solutions):**

| Risk | Mitigation |
|---|---|
| R1 Bourgain distortion | mixed-curvature product space ℍ × 𝕊 |
| R2 Numerical instability | Maclaurin expansion + float64 + retraction |
| R3 Temporal incoherence | Dynamic Fusion Distance (Euclidean + Lorentz blend) |
| R4 Anchor instability | Riemannian Karcher Mean |
| R5 Causal-cone misalign | asymmetric Lorentz entailment loss calibration |
| R6 Geodesic tractability | Klein-Lorentz hybrid (HNSW upper Klein, ground Lorentz) |

### Milestone 0: 7-test battery (6/1, ~46 min total)

Full protocol from second Deep Research report (`Latent_Hyperbolic_Structure_in_Embeddings.md`).

**Day 1 quick tests (9 min, go/no-go):**
- Test 1: Gromov δ-hyperbolicity (3 min)
- Test 2: Sarich-Boomsma tree-additivity (2 min)
- Test 4: Radial cophenetic correlation CPCC (1 min)
- Test 5: Exponential map distortion (3 min)

**Day 2 deep tests (37 min, if quick tests pass):**
- Test 3: Ollivier-Ricci curvature (12 min) ← same metric as Paper 2 §4.5, different task
- Test 6: Probing classifier on WordNet (15 min)
- Test 7: Spectral Laplacian (10 min)

**Day 3:** write Milestone 0 commit based on results → decide A.1 / A.2 / A.3 / B.

**Reference verification (Day 1 first, 1 hour):**
- 🟢 Hasan 2026 WACV, Atigh 2022 CVPR, Khrulkov 2020, Sala 2018 ICML — verified real
- 🟡 HypLoRA 2025/2026 NeurIPS — verify before citing
- 🟡 Madan et al. 2026, HypCBM 2026 — check arXiv IDs
- 🔴 HyperspaceDB (Reddit citation) — academic red flag, discard

---

## Critical Reframing: Anchor-Conditioned Lift (2026-05-21)

**Lab notebook one-liner:**
> "Paper 3 = anchor-conditioned lift, not global. Milestone 0 scope = anchor neighborhood. Cartan frame hint (defer)."

### Why anchor-conditioned > global lifting

Global Lorentz violated the paradigm's own anchor-centric nature.
Paper 1 is anchor-conditioned. Paper 2 proves non-anchor methods fail. Paper 3 should complete the paradigm, not contradict it.

```
Global lift:  distortion O(diameter) — affects entire corpus
Anchor lift:  distortion O(r²)       — only at C neighborhood, r = distance to C
              → r small near C → distortion negligible
              → far from C you don't care → distortion irrelevant
```

Mathematical basis: Riemannian normal coordinates — any smooth manifold is locally Euclidean (or locally Lorentzian). Einstein's GR uses exactly this: local Lorentz frame at each point, not global Lorentz manifold.

**Success rate revision:** Global A.3 mixed-curvature 70% → Anchor-conditioned 85%+

### Three framework candidates

**Framework A — Tangent Space Lift (recommended for math)**
1. Take anchor C ∈ BGE-M3 1024D sphere
2. Compute tangent space T_C ≅ R^1023 via log map: v_P = log_C(P)
3. Attach Lorentz metric on T_C: ds² = -dt² + g_ij dv^i dv^j
4. All dynamic primitives (drift, velocity, collapse) computed on T_C
- Pro: simplest, distortion minimal, no fine-tuning needed
- Con: per-anchor chart, multi-anchor needs coordination

**Framework B — Cartan G-structure / Moving Frames (mathematically deep)**
- attach Lorentz frame bundle at each anchor C
- connect frames via connection (parallel transport)
- anchor drift = holonomy of connection
- void dynamic = connection curvature
- corresponds exactly to Cartan's method of moving frames (1920s)
- Pro: multi-anchor natural, holonomy = cumulative drift effect
- Con: uncommon in ML, needs differential geometry depth
- NOTE: defer decision until Milestone 0

**Framework C — Conditional Hyperbolic Embedding (recommended for implementation)**
- keep BGE-M3 frozen globally
- at query time: find anchor C(Q), dynamically project (C + candidate docs) to local Lorentz
- compute dynamic primitives in local Lorentz
- project results back for cosine ranking
- Pro: no pre-compute needed, GPU parallelizable
- Con: higher query-time latency (acceptable for research)

**Recommended: Framework A math + Framework C implementation.**

### Milestone 0 scope revision

7-test battery unchanged, but **scope = anchor k-NN neighborhood, not full corpus**.

| Test | Original scope | Revised scope |
|---|---|---|
| Test 1 Gromov δ | sample 100K quadruplets from full corpus | sample 100K from anchor neighborhood |
| Test 3 Ollivier-Ricci | full corpus k-NN graph | anchor-centered k-NN (k=500) |
| Test 4 CPCC | full WordNet hierarchy | anchor C as root, sub-hierarchy only |
| Others | full corpus | anchor neighborhood |

Expected result improvement: local hyperbolicity > global hyperbolicity.
Why Paper 1 BGE-M3 worked: likely because local structure near anchors is already hyperbolic.

### Dual-local framework: the final reframing

**Lab notebook two-liners:**
> "升維 = 雙重 local (space × dimension)"
> "Milestone 0: add PCA + k sweep, find sweet spot k*"

Two orthogonal constraints, both reducing distortion:
- Anchor-conditioned (space-local): only lift at anchor C neighborhood, distortion O(r²)
- Mixed-curvature (dimension-local): only hyperbolic on relevant subspace, distortion O(diameter × k), k << 1024

Combined: **O(r² × k)** — estimated success rate 90%+

### Mixed-curvature product space mechanics

"升維" = upgrade metric structure complexity, NOT increase dimension count.

```
BGE-M3 original:  R^1024, cosine metric on sphere
Mixed-curvature:  ℍ^k × 𝕊^(1024-k), product metric
                  same 1024 numbers, different geometry
Full Lorentz:     R^1025, Lorentz metric (+1 timelike axis)
```

**Split operation (PCA-based, recommended):**
1. Take anchor C's k-NN neighborhood (1000 papers)
2. Run PCA on neighborhood
3. Top-k components → hyperbolic subspace e_hyp ∈ R^k
4. Remaining 1024-k components → spherical subspace e_sph ∈ R^(1024-k)

**Project each subspace:**
```python
# Hyperbolic: exponential map to Lorentz model
# input: v ∈ R^k (tangent vector at origin)
P_time  = cosh(||v||)
P_space = sinh(||v||) * v / ||v||
P = (P_time, P_space) ∈ R^(k+1)   # Lorentz model, +1 timelike

# Spherical: L2 normalize (same as BGE-M3 does already)
Q = e_sph / ||e_sph||  ∈ S^(1024-k-1)
```

**Product distance:**
```
d²(e1, e2) = w_H · d_H(P1,P2)² + w_S · d_S(Q1,Q2)²
d_H = arccosh(-<P1,P2>_Lorentz)   # hyperbolic distance
d_S = arccos(<Q1,Q2>)              # spherical = cosine
```

**Why split works:**
- Hyperbolic factor: captures paper abstraction level (general survey ↔ specific technique)
- Spherical factor: preserves BGE-M3 topical similarity (cosine structure intact)
- Two geometries decouple — each optimizes own structure, no interference

**Distortion comparison:**
- Pure Lorentz: O(diameter × 1024) → 35% success
- Mixed-curvature: O(diameter × k), k << 1024 → 70% success
- Dual-local combined: O(r² × k) → 90%+ success

### Milestone 0 revised experiment

Original: project 100 vectors, check neighborhood survives
Revised: PCA sweep to find optimal k*

```
For each k in [32, 64, 128, 256, 512, 1024]:
  1. Take anchor C, get 1000-NN
  2. PCA → top-k subspace
  3. Run 4 quick tests (Test 1,2,4,5) on k-dim subspace
  4. Record hyperbolicity score
  
Find k* = sweet spot (high hyperbolicity, sufficient info preserved)
Expected: k* ≈ 64-256

Additional time vs original: +30 min
Value: directly determines ℍ^k* × 𝕊^(1024-k*) for Paper 3
```

### Cartan formalism hint (do not expand now)

Anchor-conditioned local Lorentz ↔ Cartan's method of moving frames:
- not global symmetry, local frame at each point
- connection links frames
- curvature = frame inconsistency measure

If Milestone 0 confirms local hyperbolicity, seriously consider Cartan formalism for Paper 3 §3.
Defer until 6/3 commit.

---

## Paradigm Archive: MRL = 0.5, Dynamic TVA = 1.0 (2026-05-21)

**Lab notebook two-liners:**
> "MRL = paradigm 0.5, ours = paradigm 1.0"
> "Verify TMRL existence in June. Differentiate clearly."

**What MRL/TMRL is:**
- Matryoshka Representation Learning (Kusupati 2022): train embedding s.t. truncated sub-vectors e[:64], e[:128], e[:256] are each valid embeddings → nested dimension hierarchy
- OpenAI text-embedding-3 (2024): MRL built-in, commercially deployed
- TMRL (rumored/2026?): adds time-aware sub-vector nesting → **verify existence before citing**

**Why this validates your direction:**
MRL = "flat embedding not enough, internal structure needed"
Dynamic TVA = "flat embedding not enough, external algebraic structure needed"
共同立場: ✅ flat embedding insufficient ✅ structure is the real substrate

**Critical difference:**
- MRL: nested **dimension truncation** (intra-embedding hierarchy)
- Dynamic TVA: nested **algebraic lifting** (external fiber bundle / sheaf)

MRL optimizes retrieval performance. You define measurement physics. Different problems, different layers.

**MRL existence = good news for you:**
1. Paradigm pathway already opened — no need to convince reviewer "structure matters"
2. Reader intuition for "nested embedding" already primed
3. Industry acceptance high (OpenAI commercialized)
4. Clear differentiation: external algebraic (MRL doesn't have) + invariant theory + dynamic measurement

**Related work positioning (Paper 3 draft):**
> "MRL [Kusupati 2022] and its temporal extensions nest structure *within* embedding dimensions for retrieval optimization. Our work lifts the embedding space into an *external* algebraic-topological joint structure over time, defining dynamic invariants (void velocity, collapse pulse) for corpus-level measurement. The two approaches are complementary: intra-embedding hierarchy for retrieval vs. inter-embedding invariants for measurement."

**Red flag:** If you find yourself "optimizing a retrieval metric" → you've drifted. If you're "defining invariants on joint structure" → correct path.

**Paradigm convergence signal:** ColBERT, SPLADE, BGE-M3, MRL, (TMRL?) — whole IR industry moving toward structured embedding. All still at intra-embedding level. You are next level.

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
