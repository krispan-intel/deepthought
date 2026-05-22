# Lifted Retrieval

**Lifted Retrieval** is a paradigm for retrieval and semantic measurement
in which a dense encoder's geometric substrate is augmented by an
anchor-conditioned large language model operator, supplying asymmetric
semantic structure that symmetric contrastive training cannot represent.

## Formal Definition

A retrieval system instantiates **Lifted Retrieval (LR)** if it composes:

1. A **dense geometric substrate** — a contrastive sentence encoder
   (e.g., BGE-M3) providing continuous topical proximity in R^d.
2. An **anchor** C ∈ R^d — a human-grounded reference point defining
   a local neighborhood N_C (typically k-nearest neighbors of C).
3. A **directional semantic operator** T: N_C → S — realized by a
   large language model, supplying asymmetric semantic structure S
   that the encoder cannot represent by construction.

The system is *lifted* because T provides capabilities beyond what
the encoder's symmetric InfoNCE objective admits
(Wang & Isola 2020, alignment-uniformity theorem).

## Why LLM Is Architecturally Necessary

InfoNCE enforces cos(a,b) = cos(b,a) — symmetric by design.
Hierarchy, entailment, and causality are asymmetric.
No amount of scale or fine-tuning within InfoNCE resolves this.
The LLM operator is not a convenience — it is a structural necessity.

## Canonical Instantiations

| Paper | Operator type T | What LLM judges |
|---|---|---|
| TVA (Paper 1) | void-judge | Is this gap semantically meaningful? |
| TVV (Paper 2) | void-validator | Does this void actually exist? |
| D-TVA (Paper 3) | hierarchy-oracle | What is the abstraction depth? |
| Framework (Paper 4) | operator algebra | Formalization of the full class |

## Stable Terminology

| Term | Definition |
|---|---|
| **Lifted Retrieval (LR)** | The paradigm: encoder + anchor + LLM operator |
| **Anchor** | Human-grounded semantic reference point |
| **LLM operator T** | Anchor-conditioned directional semantic judgment function |
| **Anchor Drift Metric (D_C)** | Bures-Wasserstein distance between anchor-local corpus states |
| **Void** | Anchor-relevant absence in semantic space |
| **Drift polarity σ_C** | Direction of drift: toward specific (+1) or general (−1) |
| **LKHJB** | Linux Kernel Hierarchy Judgement Benchmark |
| **D-TVA** | Dynamic Topological Void Analysis, the LR instantiation for drift |

## Priority Record

The name "Lifted Retrieval" was assigned on **2026-05-22** by Kris Pan
(Intel Corporation) during the design of D-TVA, upon recognizing the
recurrent architectural pattern across three prior systems (TVA, TVV, D-TVA).

Zenodo record: https://zenodo.org/records/20337446

## Related Work

- TVA: https://zenodo.org/records/19836730
- TVV: https://zenodo.org/records/20303369
- D-TVA / Lifted Retrieval: https://zenodo.org/records/20337446

## Repository Structure

```
paper1/     TVA — void taxonomy
paper2/     TVV — void validation
paper3/     D-TVA — Lifted Retrieval instantiation for semantic drift
notes/      design documents, benchmarks, implementation specs
docs/       this file + terminology reference
```
