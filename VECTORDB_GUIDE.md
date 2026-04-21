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

*For questions about adapting TVA to your domain, open an issue or contact kris.pan@intel.com.*
