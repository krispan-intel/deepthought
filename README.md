# 🧠 DeepThought

Language: [English](README.md) | [繁體中文](README.zh-TW.md) | [简体中文](README.zh-CN.md)

> *"The Answer to the Great Question of Life, the Universe and Everything"*
> — Douglas Adams, The Hitchhiker's Guide to the Galaxy

A systematic AI-driven invention discovery engine that identifies
**Topological Voids** in technical knowledge spaces and materializes
them into **Lawyer-ready Technical Invention Disclosures (TID)**.

## 🎯 The Core Idea

Traditional R&D relies on human intuition to find innovation gaps.
DeepThought makes this **systematic and mathematical**.

The knowledge space visualization:

    ████████░░░░░░████████
    ████████░░░░░░████████   <-░░ = Topological Void
    █████████████████████       (unexplored innovation space)
    ████████░░░░░░████████
    ████████░░░░░░████████

    █ = Existing patents / solutions
    ░ = DeepThought target: high-value innovation gaps
    ★ = V_target (your optimization goal)

## 📐 The Hybrid DeepThought Equation (BGE-M3 Dense-Sparse Triad)

The core mathematical engine has evolved from traditional global MMR to a **Hybrid Vector-Inverted Index Triad**. We identify Topological Voids by finding two concepts (A and B) within a domain anchor (C) that are semantically marginal but share a **sparse lexical bridge** — at least one meaningful co-occurring token.

**Hybrid Score Formula:**

```
HybridScore(A,B) = λ · Cos(Dense(A⊕B), Dense(C))
                 - (1-λ) · AvgRedundancy(A,B)
                 + w_m · MarginalityFit(A,B)
                 + bias
```

Where `MarginalityFit(A,B) = max(0, 1 - |Cos(A,B) - midpoint| / half_band)` is a Gaussian-like penalty that peaks when the pair similarity sits at the center of the marginality band and drops to zero outside it.

**Objective:** Find Triad (C, A, B) that satisfies:

1. Domain Cohesion: `Cos(Dense(A), Dense(C)) > τ_domain` AND `Cos(Dense(B), Dense(C)) > τ_domain` (τ_domain uses percentile-adaptive calibration)
2. Calibrated Marginality: `τ_low ≤ Cos(Dense(A), Dense(B)) ≤ τ_high`
3. Sparse Lexical Bridge: `|SparseTokens(A) ∩ SparseTokens(B) - StopWords| > 0` — pairs must share at least one meaningful token

| Component | Meaning | Execution |
|-----------|---------|-----------|
| **Dense(·)** | 1024D Semantic Embedding | Nearest Neighbor (KNN) via FAISS for fast O(N) candidate retrieval. |
| **Sparse(·)** | Top-5 Lexical Weights | Extracts precise "Concept Anchors" using BGE-M3's learned sparse layer. |
| **τ_domain** | Domain Cohesion Threshold | Percentile-adaptive calibration (not a static constant). |
| **τ_low, τ_high** | Marginality Threshold | Calibrated from git-history of "first-time subsystem collisions" to avoid Franken-IPs. |
| **MarginalityFit** | Gaussian-like band penalty | Peaks at midpoint of [τ_low, τ_high], zero outside the band. |
| **Sparse Lexical Bridge** | Shared token filter | Requires at least one non-stop-word token overlap between A and B sparse vocabularies. |
| **StopWords** | Noise filter | Common function words removed before sparse token intersection. |

## 🏗️ Architecture: Decoupled 3-Tier Pipeline
```
+================================================================+
|                      DeepThought System                        |
+================================================================+
|                                                                |
|  TIER 1: Hybrid Data Tier (Secure Ingestion)                   |
|  +----------------------------------------------------------+  |
|  |  100% Local RAG on Intel Hardware                        |  |
|  |  Tree-sitter AST Parsing                                 |  |
|  |   ├──> FAISS (1024D Dense Vectors)                       |  |
|  |   └──> Elasticsearch (Inverted Index / Sparse Tokens)    |  |
|  |  Sources: Linux Kernel, x86 Specs, Papers, Patents       |  |
|  +----------------------------------------------------------+  |
|                              |                                 |
|                              v                                 |
|  TIER 2: Logic Tier (Evolutionary State Machine)               |
|  +----------------------------------------------------------+  |
|  |  LangGraph orchestrates the Conference Review Simulated Framework |  |
|  |                                                          |  |
|  |  Forager        -->  Hybrid Triad Void Detection                            |  |
|  |  Maverick       -->  Divergent RFC Gen (gpt-5.4)                            |  |
|  |  Professor      -->  Pre-Flight Draft Triage (gpt-5.2)                      |  |
|  |  Patent Shield  -->  Global Prior Art API Check                             |  |
|  |  Reality Checker-->  Constraint Validation & Critique (gpt-5.2)             |  |
|  |  Debate Panel   -->  4-Specialist Parallel Review + Deterministic Verdict (gpt-5.4) |  |
|  +----------------------------------------------------------+  |
|                              |                                 |
|                              v                                 |
|  TIER 3: Execution Tier (Output)                               |
|  +----------------------------------------------------------+  |
|  |  Automated Technical Invention Disclosures               |  |
|  |  Lawyer-ready TID Templates                              |  |
|  +----------------------------------------------------------+  |
|                                                                |
+================================================================+
```


## 🤖 The Triad Agents

### 🕵️ The Forager (Math Engine)
- Executes the Hybrid DeepThought Triad Equation
- Orchestrates Dual-Engine queries (FAISS for semantics + Elasticsearch for true co-occurrence)
- Extracts BGE-M3 Top-5 Sparse Tokens as precision "Concept Anchors"
- **Model**: `BAAI/bge-m3` + FAISS + Elasticsearch

### 💡 The Maverick (Idea Generator)
- Generates divergent RFC drafts
- High temperature, unconstrained creativity
- Explores the identified Void space
- **Model**: `copilot_cli` -> `gpt-5.4` via `--model --effort high`

### 📚 The Professor (Pre-Flight Reviewer)
- Fast triage gate after Maverick, before expensive stages
- Validates draft structure, technical coherence, and claim quality
- Rejects weak drafts early to save downstream compute
- **Model**: `copilot_cli` -> `gpt-5.2` via `--model`

### 🛡️ The Patent Shield (Fast-Fail Gate)
- Pre-screens drafts against global APIs (Semantic Scholar / Google Patents) before expensive LLM processing
- Extracts key claims and checks for direct 1:1 prior-art conflicts
- Immediately halts a branch on exact match, saving downstream compute
- **Model**: API integrations (`patent_shield.py`)

### 🛡️ The Reality Checker (Critic & Evaluator)
- Executes **Global Prior-Art Check** (Google Patents / Semantic Scholar APIs)
- Validates against physical constraints (x86 ISA, Linux ABI) via simulation and static checks
- Generates precise error logs and performance debt metrics for the Conference Review Simulated Framework
- **Model**: API Integrations + `copilot_cli` -> `gpt-5.2` via `--model --effort high`

### ⚖️ The Debate Panel (4-Specialist Consensus)
- Conference-style adversarial committee with 4 named specialists:
  - **Kernel Hardliner**: Linux kernel correctness, locking, concurrency
  - **Prior-Art Shark**: Novelty, non-obviousness, overlap risk
  - **Intel Strategist**: x86 strategic value, Xeon competitiveness, HW/SW co-design
  - **Security Guardian**: TAA/side-channel risk, crash risk, compatibility
- **Deterministic Verdict Rules**: Fatal flaw reject, majority reject (>=2), yellow card reject (>=3), full approval (all APPROVE + avg>=4), majority approval (>=3 + avg>=3.5)
- Parallel execution via bash-level fleet (4 specialists run simultaneously)
- **Model**: `copilot_cli` -> `gpt-5.4` via `--model --effort high`

## 🔄 Pipeline Flow

```
Input: Legacy Code + Modern Specs
              |
              v
        +------------+
        |  FORAGER   |
        |  Dense + Sparse Void Triad Filter  |
        +------------+
              | (Concept Anchors A & B)
              v
   +--------> +------------+
   |          |  MAVERICK  |
   |          |  gpt-5.4                     |
   |          |  RFC Draft Generation        |
   |          +------------+
   |                  |
   |                  v
   |          +------------------+
   |          | PROFESSOR        |
   |          | gpt-5.2          |
   |          | Pre-Flight Triage|
   |          +------------------+
   |                  | (Pass)
   |                  v
   |          +------------------+
   |          | PATENT SHIELD    |
   |          | Global Prior Art |
   |          +------------------+
   |                  | (Pass)
   |                  v
   |          +------------------+
   |          | REALITY CHECKER  |
   |          | gpt-5.2          |
   |          | Constraint Eval  |
   |          +------------------+
   |                  |
   +------------------+ (REVISE: Feed metrics back for Mutation - Max 3-5x)
                      |
                   APPROVE
                      |
                      v
   +--------> +-------------------------------+
   |          | DEBATE PANEL (4 Specialists)  |
   |          | gpt-5.4 x4 parallel           |
   |          +-------------------------------+
   |          | Kernel Hardliner              |
   |          | Prior-Art Shark               |
   |          | Intel Strategist              |
   |          | Security Guardian             |
   |          +-------------------------------+
   |                      |
   |                      v
   |          +-------------------------------+
   |          | DETERMINISTIC VERDICT         |
   |          | (rule-based, no LLM call)     |
   |          +-------------------------------+
   |                      |
   +----------------------+ (REVISE: Debate revision loop)
                          |
                       APPROVE
                          |
                          v
                  +--------------+
                  | TID FORMATTER|
                  +--------------+
```

## 🧭 Practical Notes: Void Semantics and Scale

- A Topological Void in DeepThought is defined relative to the **local corpus** (your prior-art boundary), not the entire internet.
- Current working scale (snapshot): **1024-dimensional embeddings** with around **140k indexed documents**.
- Local RAG is used to establish novelty and evidence boundaries; LLM reasoning is used to propose cross-domain hypotheses.
- A generated idea is not accepted directly: it must pass retrieval grounding, technical constraint checks, and multi-agent critique/debate before becoming a TID candidate.
- This means the system optimizes for **evidence-backed invention hypotheses**, not guaranteed patentability claims.

## 📊 Data Sources

| Category | Sources |
|----------|---------|
| Hardware Specs | Intel SDM Vol 1-4, Optimization Manual, CXL Spec, JEDEC DDR5 |
| Linux Kernel | torvalds/linux, LKML archives, kernel Documentation |
| Userspace | glibc, LLVM/Clang, jemalloc, DPDK, io_uring |
| Android | AOSP, Android Kernel, Bionic libc, ART Runtime, Binder |
| Academic | ArXiv cs.AR / cs.OS, ISCA, MICRO, OSDI, ASPLOS |
| Patents | USPTO full text, EPO Open Patent Services, WIPO |

## 📁 Project Structure

Current repo layout (implemented):

```
deepthought/
├── core/
│   └── deepthought_equation.py   # DeepThought Equation + MMR + arithmetic
│
├── agents/
│   ├── state.py                  # Shared pipeline state + statuses
│   ├── llm_client.py             # Unified LLM caller
│   ├── forager.py                # Void retrieval agent
│   ├── maverick.py               # Idea generation agent
│   ├── patent_shield.py          # Prior-art fast-fail gate
│   ├── reality_checker.py        # Critique/revision agent
│   ├── debate_panel.py           # Multi-model synthesis agent
│   └── pipeline.py               # Multi-agent orchestrator
│
├── data_collection/
│   ├── crawler/                  # Git/PDF/API/dataset crawlers
│   ├── parser/                   # Tree-sitter + Kconfig parsers
│   └── chunker/                  # Chunkers for embedding
│
├── vectordb/
│   ├── store.py                  # Chroma interface + void APIs
│   ├── sparse_index.py           # SQLite FTS5 / ES inverted index
│   └── embedder.py               # Local/API embedding backends
│
├── output/
│   ├── tid_formatter.py          # TID report formatter (md + html + docx + pdf)
│   ├── claim_analysis.py         # Patent claim auto-generator + confidence scoring
│   ├── templates/
│   └── generated/                # Generated TID reports
│
├── services/
│   ├── ingestion_service.py      # Ingestion orchestration
│   ├── idea_collision_service.py # Single-LLM idea collision
│   ├── query_service.py          # Basic RAG query service (LlamaIndex)
│   ├── pipeline_service.py       # Multi-agent run service
│   ├── status_store.py           # Run status persistence + retry lookup
│   ├── audit_logger.py           # Append-only JSONL audit trail
│   ├── human_review.py           # Human-in-the-loop review checkpoint
│   ├── target_mutation_service.py # Random-walk target mutation
│   ├── void_tracker.py           # Incremental void tracking over time
│   └── tid_notification_service.py # Email notification for new TIDs
│
├── scripts/
│   ├── verify_env.py
│   ├── setup_vectordb.py
│   ├── setup_treesitter.py
│   ├── ingest_kernel.py
│   ├── ingest_all.py
│   ├── run_phase3_probe.py
│   ├── run_forager_probe.py
│   ├── run_retrieval_audit.py
│   ├── run_idea_collision.py
│   ├── run_pipeline.py
│   ├── run_pipeline_service.py
│   ├── run_db_contamination_audit.py
│   ├── run_hardware_specs_experiment.py
│   ├── run_kernel_source_cleanup_pipeline.py
│   ├── cleanup_kernel_source_noise.py
│   └── generate_sample_tid_report.py
│
├── tests/
│   ├── test_core/
│   ├── test_agents/
│   ├── test_data_collection/
│   ├── test_output/
│   ├── test_services/
│   └── test_vectordb/
│
├── configs/
│   └── settings.py
│
├── logs/
├── data/
│   ├── raw/
│   ├── processed/
│   ├── models/
│   └── vectorstore/
│
├── requirements.txt
├── setup.sh
├── .env.example
└── README.md
```

Planned (not fully implemented yet):
- `core/void_detector.py`
- `vectordb/retriever.py` and `vectordb/collections.py`

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Intel Hardware recommended (Xeon + Gaudi)
- 32GB+ RAM for local LLM inference

### Setup

```bash
# 1. Clone
git clone https://github.com/yourorg/deepthought.git
cd deepthought

# 2. Setup environment
chmod +x setup.sh
./setup.sh

# 3. Activate venv
source .venv/bin/activate

# 4. Configure API keys
cp .env.example .env
vim .env

# 5. Verify environment
python scripts/verify_env.py

# 6. Initialize Vector DB
python scripts/setup_vectordb.py

# 7. Ingest data (start small)
python scripts/ingest_kernel.py --subsystem arch/x86 --limit 100

# 8. Run pipeline
python scripts/run_pipeline.py \
    --domain linux_kernel \
    --target "scheduler latency optimization"
```

## 📌 Current Implementation Status (2026-04-14)

Implemented now:
- End-to-end local ingestion pipeline (crawler -> parser -> chunker -> Chroma store)
- DeepThought Equation + iterative MMR + concept arithmetic
- Topological Void retrieval API and probe script
- Multi-agent pipeline skeleton and runnable CLI (`forager`, `maverick`, `professor`, `reality_checker`, `debate_panel`)
- Professor pre-flight review gate (fast triage before expensive stages)
- Debate Panel 4-specialist parallel review with deterministic verdict rules
- Auto Worker V2 with gh copilot CLI model routing (`--model`, `--effort`)
- Schema-protected prompt engineering (XML tags, smart truncation)
- Percentile-adaptive domain threshold calibration
- Cartesian Matrix target generation
- Auto Worker statistics and monitoring
- TID report formatter with dual outputs (Markdown + HTML)
- Run status persistence and retry flow (`RETRY_PENDING` -> `--retry-failed`)
- Pipeline execution validated with `APPROVED` verdict and report export
- Service-mode continuous runner (`scripts/run_pipeline_service.py`)
- New TID email notification service (`services/tid_notification_service.py`)

Still missing / partial:
- Full prior-art coverage (USPTO/EPO/WIPO production ingestion)
- UMAP void landscape visualization
- Human-in-the-loop approval UI/workflow
- Production hardening (security integration, full audit, benchmark suite)

## ✅ TODO

The active task list is maintained in standalone files:

- English: [TODO.md](TODO.md)
- Traditional Chinese: [TODO.zh-TW.md](TODO.zh-TW.md)
- Simplified Chinese: [TODO.zh-CN.md](TODO.zh-CN.md)

## 🔁 Service Mode (Always On)

DeepThought now supports a Dockerized always-on service runner.

### Start / stop service

```bash
bash scripts/start_service.sh
bash scripts/stop_service.sh
```

### Tail service logs

```bash
docker compose logs -f deepthought-service
```

### Data persistence and no-DB-rebuild behavior

The container uses bind mounts:

- `./data:/app/data`
- `./logs:/app/logs`
- `./output:/app/output`

This means existing `data/raw` and `data/vectorstore` are reused across restarts.
Starting/stopping the service does not rebuild the vector database.

### Runtime controls (docker-compose environment)

- `TARGET`: base mission for each loop iteration.
- `N_DRAFTS`: number of Innovator drafts per run (default `8`).
- `TOP_K_VOIDS`: number of voids selected for drafting (default `30`).
- `INTERVAL_SECONDS`: service loop interval (default `300`).
- `RANDOM_WALK_MUTATE_ENABLED`: if `true`, run Random Walk and Mutate before retrieval.
- `MUTATION_SEED_HINT`: mutation instruction used by the Mutator Agent.
- `SKIP_DUPLICATE_INPUT`: if `true`, skip runs whose input fingerprint already completed.
- `TID_EMAIL_NOTIFICATIONS_ENABLED`: enable/disable SMTP notifications.

### Copilot CLI Backend (Current Default)

If your Linux host already has `gh auth login` completed and `gh copilot -p "..."` works,
the pipeline runs with the Copilot CLI backend as the default model interface.

```bash
export LLM_BACKEND=copilot_cli
export COPILOT_CLI_COMMAND="gh copilot"
python scripts/run_pipeline_service.py \
      --target "Generate new x86 IP or any improvement to any part of the Linux kernel on x86" \
      --random-walk-mutate \
      --n-drafts 8 \
      --top-k-voids 30 \
      --interval-seconds 300
```

Notes:

- This mode is intended for host-side experimentation, not unattended Docker production use.
- Before running, ensure `GH_TOKEN` / `GITHUB_TOKEN` are unset so `gh copilot` falls back to `~/.config/gh/hosts.yml`.
- Model selection is now controlled by this repo via `--model` flag: Maverick uses `gpt-5.4`, review stages use `gpt-5.2`.
- Reasoning effort is set via `--effort high` for all stages.
- Prompts use XML-tagged structure (`<system_instructions>` / `<user_request>`) for reliable schema compliance.
- JSON schema is automatically extracted to `<system_instructions>` to survive prompt truncation.

### Random Walk and Mutate flow

When `RANDOM_WALK_MUTATE_ENABLED=true`, each iteration does:

1. Randomly sample one chunk from VectorDB.
2. Mutate it via LLM into a new x86/Linux target phrase.
3. Use the mutated target as retrieval query for MMR void discovery.

## 📧 New TID Email Alerts

Set SMTP variables before running service mode:

```bash
export SMTP_HOST=smtp.your-company.com
export SMTP_PORT=587
export SMTP_USE_TLS=true
export SMTP_USERNAME=your_account
export SMTP_PASSWORD=your_password
export SMTP_FROM=deepthought@your-company.com
export TID_NOTIFY_TO=your.name@your-company.com
```

The service sends one email per new `run_id` when a run reaches `APPROVED`/`COMPLETED` and has report outputs.

## 🔒 Security Model

All computation runs **100% locally** on Intel Hardware.

| Concern | Mitigation |
|---------|-----------|
| IP leakage | No data leaves local environment |
| Void coordinates | Never transmitted externally |
| External API calls | Semantic Scholar (optional) + Copilot CLI gateway |
| Memory protection | Intel TME roadmap |
| Execution isolation | Intel TDX / SGX roadmap |

External network calls can include Semantic Scholar API and
GitHub Copilot CLI gateway, depending on runtime configuration.

## 📜 License

Proprietary — All Rights Reserved

---

## 🙏 Acknowledgements

- [LangGraph](https://github.com/langchain-ai/langgraph) — Agent orchestration
- [LlamaIndex](https://github.com/run-llama/llama_index) — RAG framework
- [Tree-sitter](https://tree-sitter.github.io/) — AST parsing
- [ChromaDB](https://www.trychroma.com/) — Local vector database
- [GitHub Copilot CLI](https://docs.github.com/en/copilot) — Unified model backend via `copilot_cli`
- Douglas Adams — For naming inspiration