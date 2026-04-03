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

## 📐 The DeepThought Equation

The core mathematical engine combining
**Maximum Marginal Relevance (MMR)** with **Latent Space Arithmetic**.

MMR_Patent = λ · Sim(V_new, V_target) - (1-λ) · max[Sim(V_new, V_existing)]
| Symbol | Meaning | 
|--------|---------| 
| V_new | Candidate innovation vector in latent space | 
| V_target | Target domain / optimization goal vector | 
| V_existing | Existing patents / solutions vectors | 
| λ (lambda) | Balance: relevance vs. novelty (default: 0.7) | 
| Sim(·) | Cosine similarity in embedding space | 

### Interpretation
High MMR_Patent score = High similarity to target goal (relevant)
Low similarity to existing solutions (novel) = Topological Void = Innovation Opportunity

### Lambda Strategy 
| λ Value | Strategy | Use Case | 
|---------|----------|----------| 
| 0.9 | Aggressive | Closest to target, ignore prior art | 
| 0.7 | Balanced ✅ | Default: relevant AND novel | 
| 0.5 | Conservative | Maximize distance from existing | 
| 0.3 | Disruptive | Blue ocean, paradigm shift |

## 🏗️ Architecture: Decoupled 3-Tier Pipeline
```
+================================================================+
|                      DeepThought System                        |
+================================================================+
|                                                                |
|  TIER 1: Data Tier (Secure Ingestion)                         |
|  +----------------------------------------------------------+  |
|  |  100% Local RAG on Intel Hardware                        |  |
|  |  Tree-sitter AST Parsing  -->  ChromaDB                  |  |
|  |  Sources: Linux Kernel, x86 Specs, Papers, Patents       |  |
|  +----------------------------------------------------------+  |
|                              |                                 |
|                              v                                 |
|  TIER 2: Logic Tier (LangGraph State Machine)                 |
|  +----------------------------------------------------------+  |
|  |  LangGraph orchestrates The Triad Agents                 |  |
|  |                                                          |  |
|  |  Forager         -->  DeepThought Equation               |  |
|  |  Maverick        -->  Divergent RFC Generation           |  |
|  |  Reality Checker -->  Ruthless Critique                  |  |
|  |  Debate Panel    -->  Multi-Model Consensus              |  |
|  +----------------------------------------------------------+  |
|                              |                                 |
|                              v                                 |
|  TIER 3: Execution Tier (Output)                              |
|  +----------------------------------------------------------+  |
|  |  Automated Technical Invention Disclosures               |  |
|  |  Lawyer-ready TID Templates                              |  |
|  +----------------------------------------------------------+  |
|                                                                |
+================================================================+
```


## 🤖 The Triad Agents

### 🕵️ The Forager (Math Engine)
- Executes the DeepThought Equation
- Queries local RAG knowledge base
- Locates Topological Voids in latent space
- **Model**: Pure math + `IKT-Qwen3-Embedding-8B`

### 💡 The Maverick (Idea Generator)
- Generates divergent RFC drafts
- High temperature, unconstrained creativity
- Explores the identified Void space
- **Model**: `DeepSeek-V3-0324-671B` (divergent thinking)

### 🛡️ The Reality Checker (Critic)
- Ruthlessly critiques based on physical kernel constraints
- Validates against x86 ISA, Linux ABI, prior art
- Issues APPROVE / REVISE / REJECT verdicts
- **Model**: `Claude Sonnet 4` (strictest technical reasoning)

### ⚖️ The Debate Panel (Consensus)
- Multi-model adversarial debate
- **Deep Thinker**: `DeepSeek-R1-671B` — logic and edge cases
- **Code Expert**: `Qwen3-Coder-480B` — implementation feasibility
- **Judge**: `Qwen3-32B` — synthesis and final verdict

## 🔄 Pipeline Flow

```
Input: Legacy Code + Modern Specs
              |
              v
        +------------+
        |  FORAGER   |
        |  MMR_Patent Equation          |
        |  Topological Void Detection   |
        +------------+
              |
              v
        +------------+
        |  MAVERICK  |
        |  DeepSeek-V3-671B             |
        |  3x RFC Drafts  temp=0.8      |
        +------------+
              |
              v
        +------------------+
        |  REALITY CHECKER |
        |  Claude Sonnet 4 |
        |  APPROVE / REVISE / REJECT    |
        +------------------+
              |
        +-----+-----+
        |           |
      REVISE      APPROVE
        |           |
        |           v
        |     +--------------+
        |     | DEBATE PANEL |
        |     | R1-671B      |
        |     | Coder-480B   |
        |     | Qwen3-32B    |
        |     +--------------+
        |           |
        +-----+     v
      max 3x  +----------------+
              | CONSENSUS JUDGE|
              +----------------+
                     |
                     v
              +--------------+
              | TID FORMATTER|
              | Lawyer-ready |
              | Output       |
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
│   └── embedder.py               # Local/API embedding backends
│
├── output/
│   ├── tid_formatter.py          # TID report formatter (md + html)
│   ├── templates/
│   └── generated/                # Generated TID reports
│
├── services/
│   ├── ingestion_service.py      # Ingestion orchestration
│   ├── idea_collision_service.py # Single-LLM idea collision
│   ├── pipeline_service.py       # Multi-agent run service
│   ├── status_store.py           # Run status persistence + retry lookup
│   └── tid_notification_service.py # Email notification for new TIDs
│
├── scripts/
│   ├── setup_vectordb.py
│   ├── ingest_kernel.py
│   ├── ingest_all.py
│   ├── run_phase3_probe.py
│   ├── run_retrieval_audit.py
│   ├── run_idea_collision.py
│   ├── run_pipeline.py
│   ├── run_pipeline_service.py
│   └── generate_sample_tid_report.py
│
├── tests/
│   ├── test_core/
│   ├── test_agents/
│   ├── test_data_collection/
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
- `services/query_service.py`
- `output/tid_formatter.py` extensions for DOCX/PDF export

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

## 📌 Current Implementation Status (2026-04-02)

Implemented now:
- End-to-end local ingestion pipeline (crawler -> parser -> chunker -> Chroma store)
- DeepThought Equation + iterative MMR + concept arithmetic
- Topological Void retrieval API and probe script
- Multi-agent pipeline skeleton and runnable CLI (`forager`, `maverick`, `reality_checker`, `debate_panel`)
- TID report formatter with dual outputs (Markdown + HTML)
- Run status persistence and retry flow (`RETRY_PENDING` -> `--retry-failed`)
- Pipeline execution validated with `APPROVED` verdict and report export
- Service-mode continuous runner (`scripts/run_pipeline_service.py`)
- New TID email notification service (`services/tid_notification_service.py`)

Still missing / partial:
- Full prior-art coverage (USPTO/EPO/WIPO production ingestion)
- UMAP void landscape visualization
- Human-in-the-loop approval UI/workflow
- Claim-level confidence scoring and DOCX/PDF export
- Production hardening (security integration, full audit, benchmark suite)

## ✅ TODO 

### Immediate Roadmap (P0-P3)
- [ ] P0: Choose operating mode for this week (`run_pipeline.py` single-run vs `run_pipeline_service.py` always-on)
- [ ] P0: Lock one baseline command and keep it as smoke-test reference
- [ ] P0: Complete long-run soak test until first `APPROVED` TID with Copilot backend (`--once` semantics)
- [ ] P1: Keep service mode running and confirm stable `pipeline_runs.jsonl` growth
- [ ] P1: Keep email notifications disabled during stabilization (`tid_email_notifications_enabled=false`)
- [ ] P2: Add process supervision (systemd/supervisor) and auto-restart policy
- [ ] P2: Add log rotation and retention policy for long-running service
- [ ] P3: Add prior-art conflict detector and claim confidence scoring
- [x] P0: Enable host-side Copilot CLI backend (`LLM_BACKEND=copilot_cli`)
- [x] P0: Enforce strict export gate (`APPROVED` only)
- [x] P1: Add ruthless culling (`fatal_flaw`, three-strikes, stage-failure red card)
- [x] P1: Add virtual patent committee consensus (4 specialists + chairman + veto rules)

### Phase 1: Foundation 
- [x] Environment setup and verification 
- [x] Vector DB initialization (ChromaDB) 
- [x] Tree-sitter integration for C / Rust parsing 
- [ ] Basic RAG pipeline with LlamaIndex 

### Phase 2: Data Ingestion 
- [x] Linux Kernel crawler (arch/x86, sched, mm, bpf) 
- [x] Intel SDM PDF parser 
- [x] LKML mailing list parser 
- [x] Kconfig dependency graph builder 
- [x] ArXiv paper ingestion (cs.AR, cs.OS, cs.PF) 
- [ ] USPTO patent ingestion 
- [x] Incremental update scheduler 

### Phase 3: Core Engine 
- [x] DeepThought Equation implementation 
- [x] Topological Void detector 
- [x] MMR-based retriever 
- [x] Concept arithmetic (Latent Space Arithmetic) 
- [ ] Void landscape visualization (UMAP 2D projection) 

### Phase 4: Agent Pipeline 
- [x] LangGraph State Machine skeleton 
- [x] Forager Agent 
- [x] Maverick Agent (DeepSeek-V3) 
- [x] Reality Checker Agent (Claude Sonnet 4) 
- [x] Debate Panel (DeepSeek-R1 + Qwen3-Coder + Qwen3) 
- [x] Hallucination guard via committee fact-check retrieval and fatal-flaw rejection 
- [ ] Human-in-the-loop review checkpoint 

### Phase 5: Output 
- [x] TID template engine 
- [x] Patent claim auto-generator 
- [ ] Prior art conflict detector 
- [ ] Confidence scoring per claim 
- [ ] Export to DOCX / PDF 

### Phase 6: Production Hardening 
- [ ] Intel TDX / SGX security integration 
- [ ] Full audit logging 
- [ ] Performance benchmarking 
- [ ] Multi-domain support (Android, RISC-V) 
- [ ] Incremental void tracking over time
- [x] Service mode for continuous execution
- [x] New TID email notification hook (SMTP)

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

### Host-side GPT-5.4 experiment via GitHub Copilot CLI

If your Linux host already has `gh auth login` completed and `gh copilot -p "..."` works,
you can run the pipeline against the Copilot CLI backend instead of the internal OpenAI-compatible endpoint.

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
- The Copilot CLI currently reports `gpt-5.4` in successful interactive runs, but model selection is controlled by GitHub Copilot rather than this repo.

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
| External API calls | Claude API only (Reality Checker) |
| Memory protection | Intel TME roadmap |
| Execution isolation | Intel TDX / SGX roadmap |

The only external network call is to the Anthropic API
for the Reality Checker agent. All other LLMs run on
the internal Intel Gaudi2 endpoint.

## 📜 License

Proprietary — All Rights Reserved

---

## 🙏 Acknowledgements

- [LangGraph](https://github.com/langchain-ai/langgraph) — Agent orchestration
- [LlamaIndex](https://github.com/run-llama/llama_index) — RAG framework
- [Tree-sitter](https://tree-sitter.github.io/) — AST parsing
- [ChromaDB](https://www.trychroma.com/) — Local vector database
- [DeepSeek](https://www.deepseek.com/) — Maverick and Debate models
- Douglas Adams — For naming inspiration