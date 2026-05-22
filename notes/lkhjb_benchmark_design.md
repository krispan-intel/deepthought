---
# LKHJB: Linux Kernel Hierarchy Judgement Benchmark
# Experiment design — commit before starting
# Purpose: prove LLM hierarchy oracle > cPCA, decide Paper 3 architecture
---

## Why this benchmark exists

BGE-M3 trained on (query, relevant_doc) pairs — no hierarchy supervision.
Hierarchy in BGE-M3 is accidental side-effect, not designed.
cPCA finds "anchor-distinctive directions" but can't guarantee those = hierarchy.

LLM pretraining saw billions of "X is-a Y", "X implements Y", "X generalizes Y" sentences.
LLM is the only tool with directional semantic knowledge.

**This benchmark answers three questions:**
1. How accurate is LLM hierarchy judgement in Linux kernel domain?
2. How much better than cPCA / cosine baselines?
3. Which model is cost-optimal?

**Expected outcome: Qwen-2.5-72B or Llama-3.3-70B ≥ 80%, gcPCA ~65%**

If outcome confirmed → Paper 3 drops all hyperbolic complexity, adopts hybrid:
  BGE-M3 (geometric substrate) + LLM (hierarchy direction)
  From: "6 geometric lifts + 3 calibration methods + 7 numerical fixes"
  To:   "2 standard components + 2 paradigm contributions"

---

## Ground truth construction

### Scale
200 pairs total, 8 subsystems × 25 pairs each

### Subsystems
- scheduler (CFS, EAS, RT, deadline, affinity)
- memory management (slab, NUMA, hugepages, KSM, OOM)
- networking (TCP, BPF, XDP, netfilter, sockets)
- filesystem (ext4, btrfs, vfs, fuse, overlayfs)
- block layer (io_uring, blk-mq, NVMe, multiqueue)
- locking (RCU, futex, mutex, spinlock, lockdep)
- security (LSM, seccomp, capabilities, audit)
- tracing (ftrace, perf, eBPF tracing, kprobes)

### Pair validity criteria
(general, specific) is valid if at least one holds:
- specific is-a general  (CFS is-a scheduler)
- specific implements general  (BBR implements congestion control)
- specific is-special-case-of general  (hugepages is-special-case-of memory mgmt)
- specific is-mechanism-for general  (RCU is-mechanism-for lockless reads)

**EXCLUDE ambiguous / sibling pairs:**
- mutex vs spinlock (siblings, not hierarchy)
- eBPF vs BPF (evolution, not hierarchy)
- ext4 vs ext3 (version, not hierarchy)

Only include pairs where a kernel engineer would immediately agree.

### Inter-annotator reliability
- Minimum: you annotate all 200, then re-annotate 50 after 1 week
  - Intra-annotator κ > 0.85 required
- Better: find 1 other kernel engineer to review 50 pairs
  - Inter-annotator κ > 0.80 required

---

## Baselines to test

| Baseline | Method | Expected accuracy |
|---|---|---|
| Random | coin flip | 50% |
| BGE-M3 cosine | cos(general, specific) > median | ~55% |
| BGE-M3 norm | not applicable (L2-normalized) | ~50% |
| gcPCA top-1 | sign of projection onto top gcPCA eigvec | ~60-65% |
| Calibration mean (30 pairs) | mean(specific - general) direction | ~70-75% |
| Llama-3-8B | pairwise judge | ~70% |
| Qwen-2.5-32B | pairwise judge | ~80% |
| Llama-3.3-70B | pairwise judge | ~85% |
| Qwen-2.5-72B | pairwise judge | ~85% |
| GPT-4o | pairwise judge | ~88% |
| Claude Sonnet | pairwise judge | ~88% |
| GPT-4 | pairwise judge | ~90% |
| Claude Opus | pairwise judge | ~92% |
| o1-mini | pairwise judge | ~93% |

---

## LLM evaluation protocol

### Why pairwise (not scalar scoring)
- Pairwise 5-10x more stable than scalar (established in RLHF / LMSys arena literature)
- Eliminates calibration drift between models
- Win-rate directly computable as accuracy

### Prompt template
```python
PROMPT = """You are an expert Linux kernel engineer.
Determine which concept is MORE SPECIFIC (less general/abstract).

A: {concept_A}
B: {concept_B}

Respond with exactly one character: A or B."""
```

### Position bias control
Each pair runs TWICE with A/B swapped.
Only count as correct if BOTH orderings answered correctly.
This eliminates position bias.

```python
def evaluate_pair(model, general, specific):
    # Forward order
    resp1 = model.generate(PROMPT.format(concept_A=general, concept_B=specific),
                            max_tokens=1, temperature=0)
    correct1 = resp1.strip().upper() == "B"  # specific is B

    # Reverse order
    resp2 = model.generate(PROMPT.format(concept_A=specific, concept_B=general),
                            max_tokens=1, temperature=0)
    correct2 = resp2.strip().upper() == "A"  # specific is A

    return correct1 and correct2  # both must be correct
```

### Metric
Accuracy = fraction of pairs where both orderings answered correctly.

---

## gcPCA baseline (strongest possible, no strawman)

```python
# Use gcPCA (not cPCA) — eliminates α hyperparameter
# Use Sphere LogMap before gcPCA — correct sphere geometry
# Anchor-local (not global corpus PCA) — consistent with Paper 3 pipeline

def gcpca_hierarchy_direction(anchor_embedding, corpus_embeddings, k_fg=500, n_bg=5000, n_comp=1):
    # Sphere LogMap
    tangent_vecs = np.array([sphere_logmap(anchor_embedding, e) for e in corpus_embeddings])
    anchor_tangent = np.zeros(tangent_vecs.shape[1])  # anchor is origin

    # gcPCA
    dists = np.linalg.norm(tangent_vecs, axis=1)
    fg = tangent_vecs[np.argsort(dists)[:k_fg]]
    bg = tangent_vecs[np.random.choice(len(tangent_vecs), n_bg, replace=False)]

    from scipy.linalg import eigh
    Sfg = (fg - fg.mean(0)).T @ (fg - fg.mean(0)) / k_fg
    Sbg = (bg - bg.mean(0)).T @ (bg - bg.mean(0)) / n_bg + 1e-6 * np.eye(fg.shape[1])
    vals, vecs = eigh(Sfg, Sbg)
    D_star = vecs[:, -n_comp:][:, ::-1].T  # top eigenvector

    # Predict: sign of projection onto top eigenvector
    def predict_specific(general_emb, specific_emb):
        v_g = sphere_logmap(anchor_embedding, general_emb)
        v_s = sphere_logmap(anchor_embedding, specific_emb)
        score_g = D_star @ v_g
        score_s = D_star @ v_s
        return "specific_higher" if score_s > score_g else "general_higher"

    return predict_specific, D_star

# Sweep k in {32, 64, 128} (BW constraint: k ≤ n/4, n=500 → k_max=125)
# Report best k's accuracy
```

---

## Cost budget

### Open-source (Together AI / Fireworks / Groq)
```
200 pairs × 2 (position swap) = 400 calls per model

Llama-3-8B:       $0.0002/call × 400 = $0.08
Qwen-2.5-32B:     $0.0004/call × 400 = $0.16
Llama-3.3-70B:    $0.0009/call × 400 = $0.36
Qwen-2.5-72B:     $0.0009/call × 400 = $0.36
DeepSeek-V3:      $0.0014/call × 400 = $0.56

Open-source total: < $5
```

### Commercial API
```
GPT-4o:        400 × $0.005 = $2
Claude Sonnet: 400 × $0.003 = $1.20
GPT-4:         400 × $0.03  = $12
Claude Opus:   400 × $0.015 = $6
o1-mini:       400 × $0.03  = $12

Commercial total: < $35
```

### Tooling: GitHub Copilot CLI
Use Copilot CLI to run multi-model experiments.
- Multiple models available in single interface, no separate API setup needed
- Model selection decided at experiment time based on CLI availability
- Copilot subscription already paid — marginal cost ≈ $0
- Write batch eval script that loops pairs through `gh copilot` or Copilot API

### Extended (5 anchors instead of 1)
All above × 5 = < $200 total

**Budget: $200-500 covers full experiment including multiple anchors.**

---

## 2-day execution plan

### Day 1
```
09:00-12:00  List 200 (general, specific) pairs
             8 subsystems × 25 pairs
             Mark uncertain pairs for exclusion
             Save as CSV with columns: general, specific, subsystem, notes

12:00-13:00  Shuffle order, strip metadata, save eval format

13:00-15:00  Run open-source LLMs (Together AI)
             Llama-3-8B, Qwen-2.5-32B, Llama-3.3-70B, Qwen-2.5-72B, DeepSeek-V3
             Cost < $5

15:00-17:00  Run gcPCA / calibration mean baselines
             Use existing BGE-M3 embedded corpus from deepthought
             Sweep k ∈ {32, 64, 128}

17:00-18:00  Collect Day 1 results table
```

### Day 2
```
09:00-11:00  Run commercial LLMs
             GPT-4o, Claude Sonnet, GPT-4, Claude Opus, o1-mini
             Cost < $35

11:00-13:00  Apply position bias correction (both orderings must be correct)
             Recompute accuracy for all models

14:00-16:00  Analysis:
             - Accuracy vs cost scatter plot (Pareto curve)
             - Per-subsystem breakdown
             - LLM vs gcPCA confusion matrix

16:00-18:00  Decision:
             IF best LLM ≥ 80% AND gcPCA ≤ 70%:
               → adopt hybrid LLM + BGE-M3 architecture
               → drop all hyperbolic complexity from Paper 3
               → cost-optimal model = first model hitting 80% on Pareto curve
             IF all LLMs < 75%:
               → hierarchy not recoverable from kernel concepts via LLM
               → drop σ_C polarity from paper (dD_C still works)
               → fallback to Version B (pure gcPCA + Euclidean cone)
             ELSE:
               → intermediate, evaluate per-subsystem breakdown
```

---

## Expected output (Paper 3 Figure 1)

```
Model              | Accuracy | Cost per 200 pairs
-------------------|----------|--------------------
Random             | 50%      | $0
BGE-M3 cosine      | 55%      | $0
gcPCA (k=128)      | 65%      | $0
Calibration 30prs  | 72%      | ~$0 (human time)
Llama-3-8B         | 70%      | $0.08
Qwen-2.5-32B       | 80%      | $0.16
Qwen-2.5-72B       | 85%      | $0.36  ← cost-optimal
Llama-3.3-70B      | 85%      | $0.36
GPT-4o             | 88%      | $2.00
Claude Sonnet      | 88%      | $1.20
GPT-4              | 90%      | $12.00
o1-mini            | 93%      | $12.00
```

This table alone justifies the hybrid architecture and eliminates A2 risk.

---

## If results look good: paper narrative upgrade

**Paper 3 title (hybrid version):**
"Anchor-Conditioned Semantic Drift Detection via LLM-Calibrated Geometric Embeddings"

**Abstract one-liner:**
"Dense contrastive embeddings provide a continuous geometric substrate; large language models provide discrete hierarchical structure as weak supervision. The combination enables anchor-conditioned entailment cones, void detection, and event-driven drift quantification on Linux kernel RFC archive (1995-2026)."

**What gets dropped from anchor_drift_metric.md:**
- Lorentz ExpMap / LogMap (keep sphere LogMap)
- τ scaling sweep and hyperbolic curvature activation
- Mixed-curvature ℍ^k × R^(1023-k) geometry
- Hyperbolic entailment cone (Ganea 2018)
- Gromov δ / Sarich-Boomsma / Ollivier-Ricci tests
- τ̂ / û_radial cone direction debate
- All HypLoRA / fine-tuning fallback paths

**What remains:**
- Sphere LogMap (standard, 10 lines)
- gcPCA (standard, 20 lines)
- Bures-Wasserstein drift (standard, 30 lines)
- LLM hierarchy oracle (paradigm contribution, 50 lines)
- Anchor-conditioned k-NN + RFC event-driven loop (paradigm contribution)

Estimated reduction: anchor_drift_metric.md from ~2000 lines to ~400 lines.

---

## Pitfalls to avoid

1. **Your annotations only**: get at least 1 other kernel engineer to review 50 pairs.
   Intra-annotator κ > 0.85, inter-annotator κ > 0.80 required.

2. **Only include unambiguous pairs**: remove siblings, version evolutions, mutual dependencies.

3. **Fair gcPCA baseline**: use gcPCA not cPCA, anchor-local not global, with LogMap.
   Don't beat a strawman.

4. **LLM pretraining leakage concern**: include 1 less-known domain to check generalization.
   If accuracy drops dramatically in unknown domain, add limitation to paper.

5. **Don't let benchmark become the paper**: 2 days hard stop.
   Minimum useful output = 3 sentences confirming cost-optimal model.

---

## LKHJB as standalone preprint (optional, low priority)

If benchmark quality is high (inter-annotator κ > 0.80, 12 models tested):
→ Can publish as 4-page short paper: "LKHJB: Benchmarking Hierarchical Judgement in Specialized Technical Domains"
→ Gives Paper 3 a self-citation, builds credibility
→ Only pursue after Paper 3 is submitted
