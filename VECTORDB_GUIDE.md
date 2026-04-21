# 🗄️ Building a Clean Vector DB for TVA

This guide explains how to build a knowledge corpus that DeepThought can search for Topological Voids. The same approach works for **any technical domain** — not just Linux kernel.

---

## The Goal

TVA needs a corpus where:
1. **Every document has a meaningful embedding** — not noise, boilerplate, or duplicates
2. **Sparse tokens are domain-specific** — stop-words filtered, technical terms preserved
3. **Coverage is broad but focused** — you want the *boundary* of the knowledge space, not just the center

Think of it like building a map. A good map has clear edges where unexplored territory begins.

---

## Step 1: Decide Your Domain

Before collecting anything, answer these questions:

| Question | Example (Linux/x86) | Your Domain |
|---|---|---|
| What is the core artifact? | kernel source code | your codebase, spec docs |
| What is the prior art? | papers, patents | academic papers, standards |
| What is the target hardware/platform? | x86 ISA, Intel SDM | your platform spec |
| What defines "novelty" here? | kernel subsystem boundaries | your domain's subsystem map |

**The domain boundary is more important than completeness.** 50k high-quality domain-specific documents beat 500k noisy ones.

---

## Step 2: Input Format → Tool Selection

| Input Format | Content Type | Recommended Tool | Notes |
|---|---|---|---|
| **Git repository** | Source code, commit history | `GitPython`, `PyDriller` | Use tree-sitter for AST parsing |
| **PDF** | Papers, specs, manuals | `PyMuPDF` (`fitz`), `pdfplumber` | Extract text + handle math symbols |
| **HTML / Web** | Documentation, wikis, blogs | `BeautifulSoup`, `Playwright` | Respect robots.txt |
| **arXiv / Semantic Scholar** | Academic papers | arXiv API, S2 API | Free, structured metadata |
| **USPTO / EPO** | Patents | USPTO bulk data, EPO OPS API | Use claim text only |
| **Mailing lists / Forums** | LKML, GitHub Issues | Custom scrapers | Filter noise aggressively |
| **Markdown / RST** | Docs, READMEs | `mistune`, `docutils` | Good signal-to-noise ratio |
| **Jupyter Notebooks** | Research code | `nbformat` | Extract markdown cells + code |
| **CSV / JSON / JSONL** | Structured data | pandas / native | Flatten to text fields |
| **Video** | Lectures, conference talks, tutorials | `yt-dlp` + Whisper (OpenAI) | Transcribe to text first, then use text pipeline; chapter timestamps work as chunk boundaries |
| **Audio** | Podcasts, interviews, recordings | `openai-whisper`, `faster-whisper` | Speaker diarization (`pyannote-audio`) improves chunking quality |

---

## Step 3: Chunking Strategy

**Bad chunking kills embeddings.** The wrong chunk size means your vectors represent noise, not concepts.

| Document Type | Chunk Strategy | Recommended Size |
|---|---|---|
| Source code | Function/class boundary (tree-sitter AST) | 1 function = 1 chunk |
| Academic papers | Section-level | ~500–1000 tokens |
| Hardware specs (PDF) | Table + surrounding paragraph | ~300–500 tokens |
| Commit messages | Whole message | As-is |
| Patents | Claim 1 + abstract | ~200–400 tokens |
| Mailing list threads | Single email, trim quoting | ~200–500 tokens |
| Video / audio transcripts | Split on speech pauses or chapter markers | ~300–600 tokens |

**Rule:** One chunk = one concept. If a chunk covers 3 unrelated topics, split it.

---

## Step 4: Embedding Model Choice

| Model | Dimensions | Use When | Notes |
|---|---|---|---|
| **BGE-M3** (what we use) | 1024D dense + sparse | Technical multi-lingual | Best for code + prose mix |
| `text-embedding-3-large` (OpenAI) | 3072D | General text, high quality | API cost, no sparse |
| `nomic-embed-text` | 768D | Lightweight local | Good for pure prose |
| `codet5p-110m-embedding` | 256D | Code-only | Too narrow for TVA |
| `multilingual-e5-large` | 1024D | Multi-language | Alternative to BGE-M3 |

**For TVA specifically:** Use BGE-M3. The sparse weights are essential for the Sparse Lexical Bridge condition (C3).

---

## Step 5: Cleaning Pipeline

```
Raw document
    │
    ▼
① Language filter     (keep English + your target language)
    │
    ▼
② Deduplication       (minhash LSH or exact hash on content)
    │
    ▼
③ Length filter       (drop < 50 tokens, > 2000 tokens)
    │
    ▼
④ Noise filter        (drop auto-generated, boilerplate, test fixtures)
    │
    ▼
⑤ Domain relevance   (optional: embedding similarity to seed docs)
    │
    ▼
⑥ Chunking           (by document type, see table above)
    │
    ▼
⑦ Embedding          (BGE-M3 local, batch size 32–64)
    │
    ▼
⑧ Index              (FAISS flat for <1M docs, HNSW for >1M)
    │
    ▼
Clean Vector DB ✓
```

---

## Step 6: Domain Stop-Word List

TVA filters out generic tokens before computing the Sparse Lexical Bridge. You need a domain-specific stop-word list.

**For Linux kernel (built-in):**
```python
KERNEL_STOP_WORDS = {
    "define", "include", "struct", "int", "void", "static", "return",
    "linux", "kernel", "core", "sys", "device", "driver", "memory", ...
}
```

**For your domain:** Add the 50–100 most frequent tokens that appear everywhere but carry no discriminative meaning. Run `Counter` on all your sparse tokens, take the top 200, manually remove the ones that ARE domain-specific.

---

## Step 7: Quality Check

Before running TVA, verify your corpus:

```python
# Check embedding quality
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Sample 1000 random pairs - should have distribution centered ~0.3-0.6
# If too many pairs > 0.9: corpus is too homogeneous (bad)
# If too many pairs < 0.1: corpus is too noisy (bad)
sample = np.random.choice(embeddings, 1000)
sims = cosine_similarity(sample)
print(f"Mean similarity: {sims.mean():.3f}")  # target: 0.3-0.5
print(f"Std: {sims.std():.3f}")              # target: > 0.15
```

---

## Domain Examples

| Domain | Core Sources | Key Stop-Words to Add |
|---|---|---|
| **Linux kernel** (our use case) | torvalds/linux, LKML, Intel SDM | `mutex`, `spinlock`, `cpu`, `irq` |
| **Biomedical** | PubMed, PDB, UniProt | `patient`, `study`, `method`, `result` |
| **Materials science** | Materials Project, ICSD, papers | `material`, `sample`, `measured`, `Fig` |
| **Automotive** | AUTOSAR specs, ISO 26262, MISRA | `shall`, `system`, `function`, `module` |
| **Financial** | SEC filings, earnings calls, papers | `company`, `period`, `million`, `percent` |
| **Compiler/PL** | LLVM, GCC source, PLDI papers | `pass`, `node`, `type`, `value` |

---

## Useful Resources

### Embedding & Vector DB
| Resource | URL | What you'll learn |
|---|---|---|
| BGE-M3 paper | https://arxiv.org/abs/2309.07597 | Dense-sparse dual embedding |
| FAISS docs | https://faiss.ai | Billion-scale similarity search |
| ChromaDB | https://docs.trychroma.com | Simple local vector DB |
| Qdrant | https://qdrant.tech/documentation | Production-ready, filtering support |
| Weaviate | https://weaviate.io/developers/weaviate | Graph + vector hybrid |

### Data Collection
| Resource | URL | What you'll learn |
|---|---|---|
| arXiv API | https://arxiv.org/help/api | Free paper access |
| Semantic Scholar | https://api.semanticscholar.org | Citation graph + abstracts |
| USPTO Bulk Data | https://bulkdata.uspto.gov | Patent full text |
| PyDriller | https://github.com/ishepard/pydriller | Git history mining |
| tree-sitter | https://tree-sitter.github.io | Language-agnostic AST parsing |

### Chunking & Processing
| Resource | URL | What you'll learn |
|---|---|---|
| LangChain text splitters | https://python.langchain.com/docs/modules/data_connection/document_transformers | Chunking strategies |
| LlamaIndex ingestion | https://docs.llamaindex.ai | End-to-end RAG pipeline |
| PyMuPDF | https://pymupdf.readthedocs.io | PDF extraction |

### Video / Audio Transcription
| Resource | URL | What you'll learn |
|---|---|---|
| OpenAI Whisper | https://github.com/openai/whisper | Local speech-to-text (multilingual) |
| faster-whisper | https://github.com/SYSTRAN/faster-whisper | CTranslate2-accelerated Whisper |
| yt-dlp | https://github.com/yt-dlp/yt-dlp | Download YouTube / conference videos |
| pyannote-audio | https://github.com/pyannote/pyannote-audio | Speaker diarization |
| WhisperX | https://github.com/m-bain/whisperX | Whisper + alignment + diarization in one |

---

## Step 7.5: Write Your Anchor C (Intent Vector)

Before running TVA, you need one thing: a **target phrase**. This is your Anchor C — the inventor's intent vector.

**What it is:** A single sentence describing *where* you want to innovate. TVA embeds this sentence into the same vector space as your corpus, then finds voids that point in that direction.

**What it is NOT:** A keyword, a search query, or a specific document. You are not searching for something that exists — you are declaring a direction in knowledge space.

> The 96 targets used in the TVA paper are listed only for reproducibility. In practice, you need exactly one sentence.

### What makes a good Anchor C

| | Too narrow | Too broad | Just right |
|---|---|---|---|
| **Linux kernel** | `"optimize spinlock contention in scheduler runqueue"` | `"improve Linux performance"` | `"reduce scheduler latency in high-core-count x86 systems"` |
| **Biomedical** | `"reduce IL-6 cytokine in NLRP3 pathway"` | `"cure inflammation"` | `"novel small-molecule targets for neuroinflammation with blood-brain barrier penetration"` |
| **Materials** | `"increase fracture toughness of Al₂O₃ at 1200°C"` | `"better battery materials"` | `"solid electrolyte interfaces with low impedance and high thermal stability for next-gen solid-state batteries"` |
| **Automotive** | `"AUTOSAR SWC timeout handling in SOME/IP"` | `"safer cars"` | `"functional safety mechanisms for over-the-air update validation in ASIL-D automotive ECUs"` |
| **Compiler** | `"eliminate redundant store instructions after inlining"` | `"faster compilation"` | `"JIT compilation techniques that reduce warm-up latency for short-lived server workloads"` |
| **Cloud/Infra** | `"reduce tail latency in gRPC keepalive under packet loss"` | `"faster cloud"` | `"low-latency consensus protocols for geo-distributed stateful microservices under partial network partition"` |

**Too narrow:** TVA finds almost no voids — you've already defined the solution, not the direction.  
**Too broad:** TVA finds too many unrelated voids — the vector has no discriminative power.  
**Just right:** Specific enough to embed meaningfully, open enough to surface non-obvious connections.

### Real examples from the TVA paper

These are the targets that produced the two case studies:

**Case Study 1 — TSX-Advisory MGLRU Rotation:**
> `"memory reclamation latency optimisation for high-core-count x86 systems"`

TVA surfaced void #2: an optimistic memory reclamation paper (concept A) × a storage-technology ratio study (concept B). The sparse bridge token `reclamation` connected them. Nobody would have searched for this pair — TVA found it because both pointed toward the intent vector.

**Case Study 2 — Verifier-Derived Synchronisation Contracts:**
> `"eBPF JIT correctness and synchronisation on x86"`

TVA surfaced void #5: `ELF_MACHINE_NAME` (an ELF portability macro) × `addend_may_be_ifunc` (a linker relocation predicate). Cosine similarity 0.64 — related but non-obvious. The idea that emerged (per-site synchronisation contract vectors) had no surface connection to either source concept.

### The key insight

> Anchor C is the direction, not the destination. TVA does not find documents *about* your intent — it finds the **unexplored space nearby**. A weaker, more oblique target often surfaces more interesting voids than a precise one.

---

## Step 8: Configure Your Debate Panel

Once your corpus is ready, the only thing you need to configure manually is the **four specialist roles** in the adversarial review committee. Think of it like choosing a programme committee for a domain conference: you want reviewers who can challenge the idea from different angles — technical correctness, novelty, strategic value, and risk.

The current Linux/x86 roster is:

| Role | Focus |
|---|---|
| Kernel Hardliner | Implementation correctness, ABI constraints, locking |
| Prior-Art Shark | Novelty, non-obviousness, overlap with known work |
| Intel Strategist | Platform strategic fit, HW/SW co-design value |
| Security Guardian | Security and privacy risk |

**Prior-Art Shark** and a **safety/security** role are universally useful — keep them in every domain. The other two should reflect your domain's technical and organisational reality.

### Domain Examples

**Biomedical / Drug Discovery**
Modelled after NeurIPS / Nature Medicine review norms: scientific rigor + safety above all.

| Role | Focus |
|---|---|
| Clinical Researcher | Clinical feasibility, patient safety, FDA/EMA pathway |
| Drug-Safety Expert | Toxicology, off-target effects, contraindications |
| Prior-Art Shark | Patent landscape, published prior art |
| Regulatory Specialist | GxP compliance, labelling, trial design requirements |

---

**Materials Science**
Modelled after Nature Materials / ICMSE review: reproducibility + manufacturability.

| Role | Focus |
|---|---|
| Materials Physicist | Thermodynamic feasibility, DFT/experiment consistency |
| Manufacturing Engineer | Scalability, process integration, yield concerns |
| Prior-Art Shark | Patent and literature overlap |
| IP Counsel | Freedom-to-operate, claim scope |

---

**Automotive Software (AUTOSAR / ISO 26262)**
Modelled after SAE / AUTOSAR technical review: safety integrity + standards compliance.

| Role | Focus |
|---|---|
| Functional Safety Engineer | ASIL decomposition, FMEA, safety goal traceability |
| AUTOSAR Architect | BSW/RTE integration, ARXML compliance, timing |
| Prior-Art Shark | Novelty over existing AUTOSAR extensions, SAE papers |
| Cybersecurity Expert | EVITA/TARA threat modelling, ISO 21434 |

---

**Compiler / Programming Languages**
Modelled after PLDI / POPL programme committee: formal correctness + performance.

| Role | Focus |
|---|---|
| Compiler Engineer | IR correctness, aliasing, undefined behaviour |
| Language Theorist | Type system soundness, formal semantics |
| Prior-Art Shark | Overlap with LLVM/GCC patches, academic publications |
| Performance Architect | Benchmark regression risk, codegen quality |

---

**Enterprise / Cloud Infrastructure**
Modelled after SOSP / OSDI review: correctness under failure + operational cost.

| Role | Focus |
|---|---|
| Distributed Systems Engineer | Consistency model, failure modes, CAP tradeoffs |
| SRE / Operations | Operational complexity, blast radius, rollback |
| Prior-Art Shark | AWS/GCP/Azure patent landscape, open-source prior art |
| Security Guardian | Supply chain risk, zero-trust, data residency |

---

### Prompt Template

For each specialist, provide a one-paragraph system prompt of this shape:

```
You are [Role Name]. Your focus is [domain + angle].
When reviewing a Technical Invention Disclosure, you evaluate:
- [Criterion 1 specific to this role]
- [Criterion 2 specific to this role]
- [Criterion 3 specific to this role]
Respond with: verdict (APPROVE / REVISE / REJECT), a one-sentence rationale,
and — if REVISE — one concrete required change.
```

Claude or any capable LLM can help you draft these prompts once you describe your domain. The key is that each specialist should have a **distinct, non-overlapping lens** — if two reviewers would say the same thing, merge them or replace one.

---

## Quick Start (Any Domain)

```bash
# 1. Clone DeepThought
git clone <this repo>
cd deepthought

# 2. Add your documents to data/raw/your_domain/

# 3. Write a simple ingest script (see scripts/ingest_kernel.py as template)
python scripts/ingest_kernel.py --subsystem your_domain

# 4. Verify corpus quality
python scripts/run_forager_probe.py --target "your intent here"

# 5. Run TVA
python scripts/run_pipeline_service.py \
    --target "your innovation intent" \
    --collection your_domain \
    --auto-target
```

---

*Before opening an issue, try the [AI-Guided Onboarding →](BKM_ONBOARDING.md) first — Claude or Copilot can answer most domain adaptation questions interactively.*
