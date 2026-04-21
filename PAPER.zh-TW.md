# 拓樸空洞分析（TVA）
## 一個用於技術知識空間中系統性創新發現的數學框架

**潘凱瑞（Kris Pan）** · 英特爾公司 · kris.pan@intel.com

📄 [完整 PDF](output/generated/deepthought_paper.pdf) | [arXiv 預印本](https://arxiv.org) *(待發布)*

---

## Abstract

**Abstract.**
  Identifying where to innovate in a dense technical domain—such as
  operating systems or hardware/software co-design—is fundamentally a
  search problem in a high-dimensional knowledge space.  Existing
  approaches rely on keyword search, citation proximity, or human
  intuition, none of which formalise the notion of an  that is simultaneously relevant to a target goal and absent
  from prior art.

  We present *Topological Void Analysis* (TVA), a mathematical
  framework that defines *topological voids* as triads $(A, B, C)$
  in a dense-sparse hybrid embedding space.  A void requires three
  conditions: (i) both concepts $A$ and $B$ are semantically cohesive
  with domain anchor $C$; (ii) their pairwise similarity falls within a
  calibrated marginality band—avoiding both obvious combinations and
  unrelated noise; and (iii) they share a sparse lexical bridge while
  the geodesic midpoint on the embedding hypersphere is unoccupied.

  Applied to $$140k indexed documents, TVA generates 2,128
  invention candidates across 96 targets; 90\
  quality filtering, yielding 191 REVISE and 1 APPROVE verdict from
  four-specialist adversarial review (0.05\
  studies demonstrate the framework surfaces non-obvious connective
  tissue rather than merely obvious related pairs.

---

## Introduction

Modern software systems, especially at the systems-software layer,
evolve through incremental invention: a developer notices a gap
between two subsystems, proposes an abstraction to bridge them, and
the community iterates toward a patch or patent.  The *noticing*
step is bottlenecked by human attention and domain breadth.  A single
engineer cannot simultaneously hold in mind the locking semantics of
the Linux scheduler, the memory-ordering guarantees of eBPF JIT
output, the ELF relocation model, and the BPF verifier's type system
well enough to recognise that an IFUNC-style dispatch contract could
unify the latter three.

This paper asks: *can we formalise and automate the discovery of unexplored technical gaps?*

We answer yes, and make the following contributions:

- A formal definition of a *topological void*
  (Section ): a triad $(A, B, C)$ satisfying
  domain cohesion, calibrated marginality, and sparse lexical bridge
  conditions in a hybrid dense-sparse embedding space.

- A *vacancy probing* mechanism
  (Section ) based on spherical linear interpolation
  (SLERP) that rejects pseudo-voids whose midpoint is occupied by
  existing documents.

- An *adaptive threshold calibration* procedure
  (Section ) that derives domain-specific
  marginality bounds from corpus statistics, removing manual tuning.

- A large-scale empirical evaluation
  (Section ) with two detailed case studies demonstrating
  that TVA surfaces non-obvious yet technically grounded innovation
  candidates.

## Background and Motivation

### Technical Knowledge as an Embedding Space

Pre-trained embedding models map technical documents into a
high-dimensional unit sphere .  Points
close in cosine distance share semantic content; distant points are
unrelated.  A *knowledge corpus* $$ is a finite set of
such points.

Innovation in this view is the act of bridging two concepts $A$, $B$
that are not yet co-located in $$, provided their
combination is relevant to a target goal $C$.

### Geometric Convergence Across Model Scales

A key theoretical underpinning of TVA is the
*Platonic Representation Hypothesis* :
sufficiently trained models—regardless of architecture, modality, or
scale—converge toward a common statistical geometry of their shared
training world.  Concretely, the pairwise distance structure of a
compact embedding model (BGE-M3, 1024D) and a frontier LLM are
approximately isometric: if $((A),
(B))  0$ in BGE-M3 space, the same pair tends
to be distant in the LLM's implicit representation space.

This convergence provides the theoretical basis for TVA's design.
A topological void identified in BGE-M3 space—a pair $(A,B)$ whose
geodesic midpoint is unoccupied—serves as a  for an underexplored region in the frontier LLM's
reasoning space.  The compact model acts as an efficient navigator;
the LLM supplies the high-resolution generative capability to fill
the identified gap.  Geometric alignment across scales, formalised via
CKA , supports this proxy relationship
empirically.

### Limitations of Prior Art Search

Conventional patent and prior-art search is keyword-driven or
citation-driven .  These
methods retrieve *known* content; they do not identify
*missing* content.  Knowledge-graph completion
approaches  predict missing edges but require a
pre-defined relation schema and do not model the continuous
``marginality'' notion central to patentable non-obviousness.

### The Marginality Principle

Patent law requires that an invention be *non-obvious*: too
similar to existing work fails the novelty bar; too dissimilar yields
an incoherent or non-enabling disclosure.  High-value inventions live
in a band of *moderate dissimilarity*—far enough from prior art
to be novel, close enough to the domain to be useful.  This is the
informal basis for our formal marginality condition.

## Why Standard Approaches Fail

Three retrieval baselines were evaluated before arriving at TVA, each
failing in a characteristic way.
**Cosine top-$k$** retrieves relevant but redundant results—all
from the same well-covered subsystem, with no notion of a gap.
**MMR**  improves diversity but provides
no occupancy guarantee: $$30\
neighbour within cosine distance 0.08 of their linear midpoint,
making them false voids.
**Latent vector arithmetic** 
($v_ =  + (v_A - v_B)$) fails in
1024-dimensional contextualised space: anisotropy 
makes difference vectors nearly orthogonal to semantic axes, and the
curse of dimensionality  strips them of
directional meaning—67\
manifold entirely.
All three lack an explicit *occupancy check*: they rank or
construct candidate points without verifying the region is genuinely
unoccupied.  This motivates the vacancy probe in TVA.

## The Topological Void Framework

### Notation

Let $ = \k_1, , k_n\$ be a corpus of technical
documents.  Each document $k  $ is mapped by BGE-M3
($d=1024$)  to a dense unit vector
$(k)  S^d-1$ and a sparse token set
$(k)  ^*$ (top-5 lexical weights).

Let $(u,v) = u^ v$ for unit vectors.  Let
$(k) = \t  (k) : t 
\$ where $$ is a domain stop-word list
(high-frequency, low-specificity tokens such as `int`,
`define`, `linux`).

### Formal Definition

> **Definition:** [Topological Void]

Let $A, B  $ be two corpus documents and let
$C = m((A),\,(B))  S^d-1$
(Definition ) be their synthetic
*void midpoint*—the geodesic bridge concept.
The pair $(A, B)$ forms a *topological void*
with respect to a domain query vector $  S^d-1$ if
all of the following hold:

**C1

Intuitively: $A$ and $B$ both point toward the target domain (C1);
are neither trivially similar nor unrelated (C2); share at least one
meaningful technical token as a conceptual bridge (C3); and the
synthetic void midpoint $C$ is unoccupied by any existing
document (C4).  The idea to be invented lives in the neighbourhood
of $C$—the gap between two related but unexplored concepts.

### Ranking Voids

Valid pairs $(A, B)$ are ranked by a multi-objective scoring
functional $(A, B; )$ that integrates
(i) relevance of the synthetic void midpoint $C = m(A,B)$ to the
target domain, (ii) a redundancy penalty against already-selected
solutions, and (iii) a non-linear marginality reward centred at
the band $[, ]$.  The precise functional form and
weights are omitted per commercial confidentiality requirements,
consistent with industry-track submission guidelines.

## Vacancy Probing via SLERP

A key failure mode of purely similarity-based approaches is the
*false void*: two documents that appear to span an empty region
but whose midpoint is, in fact, close to an existing document.
Condition C4 addresses this.

> **Definition:** [Geodesic Midpoint]

For unit vectors $u, v  S^d-1$ with $ = (u^ v)$,
the geodesic midpoint on $S^d-1$ is given by SLERP :

> *(see formula in PDF)*

with fallback to $u$ for antipodal vectors ($ = $).

We use the geodesic midpoint rather than an arbitrary interpolation
because it is *equidistant* from $u$ and $v$ on the hypersphere:
$(m(u,v), u) = (m(u,v), v)$, guaranteeing
that the vacancy test is symmetric with respect to both anchors.
For non-antipodal unit vectors this simplifies to
normalised linear interpolation; the SLERP formulation handles
the degenerate case and connects to the broader literature on
geodesic midpoints in curved spaces .

Vacancy check (C4) is an $O(n)$ dot-product scan of the corpus matrix
against $m(A,B)$, requiring no index rebuild.

## Adaptive Threshold Calibration

Static thresholds fail across corpora with different density profiles.
TVA employs a density-aware calibration layer that derives both
$$ and $[, ]$ on-the-fly from the empirical
distribution of the current query's candidate pool.

### Domain Threshold $$

The domain cohesion threshold combines a data-driven percentile
statistic over the cosine-score distribution of all candidates with
a corpus-specific floor.  The key property is that $$
rises in dense regions and falls in sparse ones, preventing both
over-permissive selection and empty-result failures.
Specific parameterisation is omitted per confidentiality requirements.

### Marginality Band $[, ]$

The marginality band is centred at the empirical mode of the
pairwise-similarity distribution among domain-cohesive candidates,
with width derived from the spread of that distribution.  This
operationalises non-obviousness: the band excludes the
high-similarity tail (obvious combinations) and the low-similarity
tail (unrelated noise) without hard-coded constants.
Notably, the calibrated band is itself a *domain characterisation*:
it quantifies the pairwise semantic distance at which innovation
typically occurs in the target technical space and will differ across
domains.  Cross-domain comparison of these bands is left as future work.
Scale parameters are omitted per confidentiality requirements.

## System Implementation

We implement TVA in a prototype that ingests a heterogeneous corpus of
Linux kernel source (parsed via tree-sitter into
function/struct/symbol chunks), hardware architecture manuals, academic
papers (PDF-extracted), and patent texts.  The corpus contains
approximately 140,000 indexed documents after deduplication.

**Embedding.**  We use BGE-M3  in local
offline mode for both dense ($d=1024$) and sparse (top-$p$ lexical
weights) representations.  All computation runs on CPU.

**Index.**  Dense vectors are stored in a FAISS flat
index  for $O(n)$ exact similarity search.
Sparse tokens are stored in an SQLite FTS5 inverted index for
boolean co-occurrence queries.

**Candidate generation.**  For a given target phrase, we embed
the target, retrieve the top-$K$ domain-cohesive candidates (C1),
enumerate all $$ pairs, and filter by C2, C3, and C4 in
sequence.  Surviving pairs are ranked and the top-$k$ returned as voids.

**Idea generation.**  Each void is passed to a frontier LLM with
a structured prompt instructing it to propose a technical invention
disclosure (TID) that bridges the two void concepts toward the target
domain.  The LLM is not told the scoring details; it receives only the
void description and the target.

## Evaluation

### Setup

We run TVA over a Cartesian matrix of 12 target domains (Linux
scheduler, memory management, file systems, eBPF, virtualisation,
networking, power management, device drivers, IRQ handling, CXL
memory, PCIe, and security) crossed with 8 x86-hardware
feature areas (PEBS, AMX, TDX, CXL, APIC, RAPL, EPT, AVX-512),
yielding 96 target specifications.  For each target, TVA produces up
to 10 void triads, each triggering one LLM call for idea generation.

**Quality evaluation.**  We use a four-stage automated filtering
pipeline as a proxy for expert review:

  
- *Structural check*: validates JSON completeness and
    absence of fictional kernel APIs.
  
- *Reality check*: iterative critique-and-revise with up
    to 3 rounds; rejects physically impossible ideas.
  
- *Adversarial review*: a four-specialist committee
    (kernel correctness, novelty/prior-art, strategic value,
    security/stability) each independently assigns APPROVE / REVISE /
    REJECT with an integer score.
  
- *Deterministic verdict*: fatal-flaw, yellow-card, and
    majority rules aggregate the four specialist votes.

### Quantitative Results

Table  summarises the filtering funnel over 2,128
candidate ideas generated across all 96 targets.

> *(see table in PDF)*

The 191 candidates reaching a REVISE verdict received substantive
technical feedback from all four specialists (avg.\ 5.1 issues per
specialist per candidate, avg.\ specialist score 4.0–5.0/5).
Under our deterministic rules, REVISE indicates that the committee
found genuine technical merit and requested elaboration—it is a
*qualified positive result*, not a rejection.
The two case studies below are drawn from this REVISE cohort.

One candidate reached the `majority\_approval` threshold
(3/4 APPROVE, avg.\ score 4.0/5, zero fatal flaws, two Debate Panel
rounds): , which proposes per-cluster density-adaptive
IPI mode selection in `native\_flush\_tlb\_multi()`.
We present REVISE candidates as case studies rather than this APPROVE
candidate, because ideas receiving near-unanimous expert agreement
are, by construction, less likely to exhibit the non-obvious
``connective tissue'' that defines the topological void—a point
we discuss further in Section .

### Rejection Taxonomy

To understand *why* ideas fail, we categorise the fatal flaws
in the 888 REJECT verdicts by keyword analysis of specialist feedback.
Table  shows the distribution.

> *(see table in PDF)*

> *(see table in PDF)*

Table  shows the adversarial approval distribution.
The 75.5\
are filtered from the human-review queue—unanimous rejection signals
that no specialist found the core concept defensible.  The remaining
24.5\
the system's effective human-review yield: ideas where at least one
domain expert identified genuine technical merit despite identifying
issues requiring elaboration.  This stringent end-to-end conversion
rate reflects the *Driving-AI* philosophy: the value lies not
in volume but in surfacing a small set of technically grounded
candidates for expert follow-up.

Three observations stand out.  First, 90.2\
by `fatal\_flaw\_reject` (at least one specialist identifies a
blocking technical error), confirming that the committee is performing
genuine domain-specific reasoning rather than surface-level critique.
Second, locking and concurrency errors (35.5\
with the difficulty of safe kernel synchronisation—exactly the class
of error that a Linux maintainer would cite when rejecting a patch.
Third, prior-art overlap (19.8\
of void-derived ideas, while geometrically novel in embedding space,
overlap with existing techniques when viewed through a deep-domain lens.
This motivates future work on tighter prior-art integration in the
vacancy probe.

### Case Study 1: TSX-Advisory MGLRU Rotation Capsules

**Target and void.**  Target:   TVA surfaced
void \#2 from 8 candidate voids: concept $A$ is a paper on
*optimistic memory reclamation in lock-free programs*, concept $B$
is a storage-technology selection study (TRaCaR Ratio).  Sparse bridge
tokens: `memory`, `optimistic`, `reclamation`,
`access`.  The geodesic midpoint $C = m(A,B)$ had no corpus
neighbour within cosine distance 0.09—confirming vacancy.

**Idea.**  The LLM proposed : a fail-closed mechanism that
wraps the Linux MGLRU folio rotation fast-path in an RTM (Restricted
Transactional Memory) speculation region.  If the transaction aborts,
the fallback acquires the `lru\_lock` normally.  The proposal
introduces per-folio mutation cookies (seqcount-like odd/even) and a
fail-closed locked revalidation step to preserve lruvec consistency.

**Expert verdict (REVISE — 
This is the highest-approval result in our new-format cohort.
[noitemsep,topsep=2pt]
  
- *Kernel Hardliner* (APPROVE): ``TSX advisory path
    is architecturally sound; RTM abort falls back correctly.''
  
- *Prior-Art Shark* (APPROVE): ``No direct prior art on
    TSX-advisory MGLRU rotation; non-obviousness defensible.''
  
- *Intel Strategist* (APPROVE): ``Strong x86 TSX
    differentiation story on Xeon platforms with hardware TSX support.''
  
- *Security Guardian* (REVISE, fatal flaw): ``TSX/TAA
    policy gating not specified concretely enough to guarantee
    fail-closed behavior under incomplete writer-coverage.''

After Round 3 revision: mutation-cookie semantics were formalised
(monotonic counter, never odd during active optimistic phase), and
the TSX admissibility check was made explicit: RTM is enabled only
when `X86\_FEATURE\_RTM` is present *and* the current
kernel TAA mitigation policy permits transactional use.
Three of four specialists approved the final draft, making this
the strongest positive result in the evaluation cohort.

### Case Study 2: Verifier-Derived Synchronization Contracts

**Void.**  Void \#5 in the same run: concept $A$ is
`ELF\_MACHINE\_NAME` (an ELF portability macro), concept $B$ is
`addend\_may\_be\_ifunc` (a linker IFUNC relocation predicate).
Sparse bridge tokens: `addend\_may\_be\_ifunc`,
`elf\_machine\_name`, `x86\_64`.  The pairwise cosine
similarity (0.64) is at the high end of the calibrated band, indicating
the pair is related but non-obvious in the target context.

**Idea.**  Despite the weak, oblique signal, the LLM proposed
*Verifier-Derived Synchronization Contract Vectors (SCVs)* for the
x86 eBPF JIT: an immutable per-program sidecar table in which the eBPF
verifier records each synchronisation site's primitive family, memory
order, address class, context mask, and admissibility class; the JIT
resolves each site exactly once at load time to an inline template or
call-equivalent thunk.  The idea ran through three rounds of
adversarial revision, refining the SCV schema and clarifying
LKMM-equivalence requirements.

**Expert verdict (REVISE after 3 rounds — qualified positive).**
The idea underwent three rounds of adversarial revision (all REVISE,
no REJECT; avg.\ specialist score 5.0/5).  Representative feedback
and responses:
[noitemsep,topsep=2pt]
  
- *Round 1 — Kernel Hardliner*: ``Define the stable-feature
    admissibility rule in terms of existing `x86\_cpufeature` APIs.''
    $$ Added explicit stable-feature whitelist (TSO baseline, CX8,
    optional CX16); excluded RTM/HLE and revocable features.
  
- *Round 2 — Kernel Hardliner*: ``The SCV ABI requires
    precise versioning and endianness specification.''
    $$ SCV entry schema extended with `linux\_primitive\_id`,
    `width\_code`, `memory\_order`, `admissibility\_class`.
  
- *Round 3 — Prior-Art Shark*: ``Claims overlap with
    generic verifier fact propagation.''
    $$ Claims narrowed to the normative primitive-family identifier
    and the one-time admissibility resolution rule.

**Significance.**  This case demonstrates a key property of TVA:
the void pair (`ELF\_MACHINE\_NAME`, `addend\_may\_be\_ifunc`)
has no surface-level connection to BPF synchronisation semantics.  A
human engineer would not naturally connect these concepts; the LLM
used the IFUNC dispatch mechanism as a structural analogy for per-site
JIT resolution.  The 3-round revision trace confirms that the idea was
technically grounded enough to survive sustained adversarial critique
and emerge with a stronger, more narrowly-claimed design.
This is the ``non-obvious connective tissue'' that TVA is designed to surface.

## Discussion

**Engineering time savings.**
A 140,000-document corpus yields approximately $
 10$ billion candidate concept pairs.
The practical difficulty is not merely combinatorial: a human engineer
has no principled way to decide *which* pairs to evaluate without
first examining them, making exhaustive manual exploration effectively
intractable regardless of expertise or time.
TVA converts this intractable search into a tractable shortlist:
25,536 automated LLM expert-review calls screen 2,128 candidates and
deliver **49 human-review candidates** ($$1/4 specialist
approval) requiring approximately **49 person-hours** of focused
domain expert review.
The authors consider the resulting time saving beyond meaningful
quantification—the baseline is not ``slower,'' it is ``not
systematically possible.''

**Independent expert evaluation.**
The 8 candidates achieving $$2/4 adversarial approval (7 REVISE + 1 APPROVE) were subjected to independent domain expert
review evaluating technical feasibility, kernel correctness, novelty,
and claim quality on a 1–5 scale.
Of these, 6/8 (75\
with a mean expert score of 3.5/5.
The two remaining candidates require significant additional work: one
has incomplete `tid\_detail` fields due to revision data loss,
and one requires a narrower claim rewrite to address prior-art
proximity.
This 75\
the adversarial committee's discriminative power and supports TVA's
end-to-end effectiveness.

**Why does a weak void signal still yield a strong idea?**
The void conditions define the *search region*, not the idea
itself.  The LLM fills the region with its own parametric knowledge.
A sparse but valid bridge token (here, `addend\_may\_be\_ifunc`)
acts as a semantic trigger—analogous to how a human expert reading an
unrelated paper suddenly connects it to their domain expertise.  TVA
formalises the triggering mechanism; the LLM supplies the reasoning.

**Calibration sensitivity.**  The adaptive $$
calibration reduces manual tuning but introduces dependence on corpus
density.  For very sparse domains, the percentile-based calibration may
set $$ too low, admitting noisy candidates.  The vacancy
probe (C4) partially compensates by rejecting occupied midpoints.

**On the choice of REVISE as positive evidence.**
We deliberately present REVISE rather than APPROVE verdicts as case
studies.  Under our deterministic rules, APPROVE requires at least 3/4
specialist approval with zero fatal flaws from any specialist—a
bar calibrated for patent-ready enabling disclosures.
REVISE with 3/4 specialist approval and substantive technical feedback
represents the system's *intended* output: technically grounded
innovation candidates that require domain-expert completion, not
autonomous patent generation.  A system that routinely produces APPROVE
verdicts from LLM specialists alone would be under-calibrated rather
than superior—it would fail to catch the locking, prior-art, and
security issues that Table  shows are pervasive in
this domain.  The 191 REVISE candidates are the value; the single APPROVE (0.05\
rate is evidence of calibration rigour, not system failure.

Paradoxically, near-unanimous (4/4) APPROVE may indicate an idea
that is *too* straightforward: an invention obvious enough that
all four independent domain experts agree without reservation is, by
definition, unlikely to survive a non-obviousness challenge.
This mirrors peer review in top-tier venues, where a paper receiving
perfect scores from all reviewers on the first round is either a
once-in-a-decade breakthrough or a sign that reviewers did not look
closely enough.  The most patentable candidates in our cohort—those
surviving adversarial review with 2–3/4 approval and substantive
specialist feedback—sit precisely in the calibrated marginality band
that TVA is designed to surface: not so similar to prior art as to be
obvious, not so dissimilar as to be incoherent.  Expert disagreement is
not a failure mode; it is the geometric signature of a genuine
topological void.

**Evaluation limitations.**  Our automated adversarial review
pipeline is a proxy for formal human expert evaluation.
The 49 shortlisted candidates ($$1/4 approval) are ready for
domain-expert review; structured evaluation with a pre-defined rubric,
inter-rater reliability measurement, and blinded expert scoring is
left for future work.

The revision loop issues a single LLM call per round that addresses
all four specialists' feedback simultaneously; this ``attend-to-all''
strategy can lead to trade-offs where addressing one specialist's
concerns inadvertently weakens another's approval.
A specialist-decomposed approach—one focused revision per specialist,
followed by a merge pass—would likely improve approval rates at the
cost of 4–5$$ more inference per revision round, a
compute-efficiency trade-off we leave for future work.

**Reproducibility note.**  Specific hyperparameter values and
functional forms for $$ and the calibration layer are
omitted per proprietary constraints.  The four conditions C1–C4,
the vacancy probe, and the calibration strategy are described
with sufficient precision to reproduce the qualitative behaviour;
practitioners can derive corpus-specific values from the
described procedures.  Guidance on calibration ranges is
available upon request from the authors.

**適用範疇：僅限靜態知識空間。**
TVA 假設知識空間具有*穩定的幾何結構*——語料庫是一組固定的先前技術，空洞相對於它定義，且識別空洞的行為不會改變這個空間。這個假設在 Level 1 系統中成立：技術領域的事實是客觀的，文件是持久的，發現創新缺口的行為不會導致競爭者立即填補它。

這個假設在 Level 2 動態系統中會失效——市場、社會協作、競爭策略——這些領域的知識空間具有反身性：識別空洞並採取行動，會改變其他 agent 的位置，進而重塑拓撲結構。在這類領域中，今天識別的空洞，可能因為揭露本身而被競爭者明天填補；「市場機會」的 embedding 也可能隨著閱讀過這份分析的人的行動而移動。

TVA 並非為 Level 2 系統設計，對這些領域不做任何有效性聲明。在不考慮反身性的情況下，將 TVA 應用於商業策略、金融市場或社會動態，將產生在測量當下是真實的、但在結構上不穩定的空洞座標。形式化 TVA 的反身性延伸——其中語料庫本身是一個被曾閱讀過先前空洞報告的 agent 行動所塑造的動態對象——留作開放問題。

**Meta-evaluation.**
This manuscript was iteratively revised through five rounds of the
Debate Panel itself—the same adversarial review pipeline described
in Section .  Round 1 triggered a Writing Reviewer
REVISE citing ``narrative cherry-picking,'' directly prompting the
inclusion of Table  and the deterministic verdict
formalisation.  The Math Reviewer issued REJECT (score 3/10) in
Round 3 over a type error in Condition C4 (`cos`$(k, C)$
vs.\ `cos`(`dense`$(k), C)$), which was corrected in
Round 4.  By Round 5, the Math Reviewer upgraded to **ACCEPT**
(score 8/10) and average specialist score reached 6.2.

This trajectory mirrors exactly the design rationale for
`PENDING\_HUMAN\_REVIEW`: the system did not produce a final
APPROVE verdict autonomously—the human author intervened at each
round to address specialist feedback.  Ideas (and papers) that
survive multiple adversarial rounds without full approval are not
failures; they are candidates for the ``last-mile'' refinement that
only human expertise can provide.  The system identified and corrected
weaknesses in its own originating paper across five rounds of
substantive, sycophancy-resistant critique.
Notably, the committee also penalised this manuscript for withholding
implementation details—the same system that identifies innovation
gaps was unwilling to fill one about itself.  We regard this as
evidence of consistent calibration rather than irony.

## Future Work

**Recursive Topological Expansion.**
Currently, TVA interpolates strictly within the empirical boundaries
of human-authored prior art.  A profound avenue for future research is
*recursive innovation bootstrapping*.  By vectorising and
re-ingesting highly-rated, APPROVE-verdict Technical Invention
Disclosures back into the active corpus as synthetic prior art, the
system can dynamically alter the topology of the knowledge space.  In
this autoregressive loop, a synthesised TID acts as a newly
established structural anchor in the embedding space, creating
secondary topological voids between itself and historically distant
concepts.  This feedback mechanism would transition TVA from a
single-step gap-discovery engine into an autonomous ``technology tree''
generator—iteratively mapping multi-generational frontiers of systems
architecture beyond the immediate human horizon.

**Downstream implementation.**
The structured TID format produced by TVA—comprising problem
statement, architecture overview, implementation plan, and draft
claims—is designed to be directly actionable.  A validated TID
can serve as a specification prompt for LLM-based coding
agents , enabling a seamless path from
knowledge-gap discovery to prototype implementation.  Future work
will evaluate end-to-end pipelines from void discovery through
automated patch generation and CI-validated compilation.

**Human-architect integration.**
Ideas that exhaust the automated revision budget without reaching
APPROVE are routed to a `PENDING\_HUMAN\_REVIEW` queue.
These candidates represent the frontier where LLM reasoning reaches
its current limit—precisely the cases most worthy of expert
human attention.  A structured human-in-the-loop interface that
presents the accumulated specialist critique alongside the draft
is a natural next step.

**Cross-domain generalisation.**
While this paper instantiates TVA on a Linux kernel and x86
hardware corpus, the framework is domain-agnostic.  Any
organisation that maintains a large, embeddable technical knowledge
base—hardware design documentation, biomedical literature,
materials-science patents, automotive software standards, or
enterprise architecture repositories—admits the same void
formalization.  A unified *organisational knowledge graph*
that spans multiple engineering disciplines would allow TVA to
surface cross-domain voids: ideas at the boundary between, say,
a firmware subsystem and a compiler backend that neither team would
discover in isolation.  Domain adaptation involves two steps: (i) reconfiguring the four
specialist roles in the adversarial review committee with
domain-appropriate reviewers (e.g., Clinical Researcher and
Drug-Safety Expert for biomedical, Materials Physicist and
Manufacturing Engineer for materials science), and
(ii) re-calibrating the marginality band $[, ]$
from a domain corpus, as the geometric distance at which innovation
occurs varies across fields.  Both steps are data-driven and require
no manual threshold tuning.  The rest of the pipeline—void
discovery, LLM generation, and revision loop—transfers unchanged.
At scale, this positions TVA as an
*enterprise-wide innovation radar*—systematically mapping
the unexplored territory across an entire organisation's collective
technical knowledge, one topological void at a time.

## Related Work

**Patent and technology forecasting.**
 propose keyword-based patent maps for technology
opportunity identification.   apply
BERT to prior-art search.  Neither formalises the notion of an
unexplored region or provides a mathematical criterion for
non-obviousness.

**Knowledge graph completion.**
TransE  and its successors predict missing
triples in knowledge graphs.  These methods require a pre-defined
relation schema and binary (present/absent) labels; TVA operates on
continuous similarity and does not require a schema.

**Diversity-based retrieval.**
Maximum Marginal Relevance  selects a diverse
set of documents relevant to a query by penalising redundancy.  TVA
uses a similar relevance-novelty trade-off but applies it to the
*generation* of new concepts rather than the retrieval of existing
ones.

**LLMs for code and creativity.**
Large language models have demonstrated strong performance on code
generation  and
instruction-following .  We treat LLMs as
black-box reasoners invoked after void discovery; the novelty is the
void identification mechanism, not the generation step.

**Topological data analysis.**
Persistent homology  identifies topological
features (connected components, loops, voids) in point clouds.  Our
use of ``topological void'' is inspired by but distinct from TDA:
we define voids in semantic embedding space by algebraic conditions on
pairwise similarities, not by simplicial complex homology.

**Embedding geometry.**
 show that contextualised
representations are anisotropic—concentrated in a narrow cone.  Our
adaptive threshold calibration is designed to be robust to this
property; SLERP avoids the geometric distortion that linear
interpolation introduces in anisotropic spaces.

## Conclusion

We have presented Topological Void Analysis, a mathematical framework
for systematic technical innovation discovery.  By defining topological
voids as triads satisfying domain cohesion, calibrated marginality,
sparse lexical bridge, and vacancy conditions in a hybrid
dense-sparse embedding space, TVA converts the informal notion of
``unexplored region'' into a decidable predicate.

Applied to a 140k-document corpus of Linux kernel and hardware
specifications, TVA generated 2,128 invention candidates, 90\
which survived automated quality filtering and 191 of which engaged
four adversarial expert reviewers with substantive technical critique.
Two case studies illustrate that TVA surfaces both obvious-gap ideas
and non-obvious connective-tissue ideas that neither keyword search nor
human browsing would naturally find.

We release the mathematical framework and threshold calibration
procedure for reproducibility; implementation details are available
upon request.

Ultimately, TVA embodies a design philosophy we term
*Driving-AI, not AI-driven*: the system surfaces the map;
human experts navigate it.

---

*完整數學公式、表格與參考文獻，請見 [PDF 版本](output/generated/deepthought_paper.pdf)。*
