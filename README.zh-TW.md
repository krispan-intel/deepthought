# 🧠 DeepThought

語言： [English](README.md) | [繁體中文](README.zh-TW.md) | [简体中文](README.zh-CN.md)

> *"The Answer to the Great Question of Life, the Universe and Everything"*
> — Douglas Adams, The Hitchhiker's Guide to the Galaxy

一個系統化、由 AI 驅動的發明探索引擎，用來在技術知識空間中識別
**拓撲空洞（Topological Voids）**，並將其具體化為
**可直接交由律師使用的技術發明揭露文件（Technical Invention Disclosure, TID）**。

## 🎯 核心概念

傳統研發通常依賴人的直覺去發現創新缺口。
DeepThought 則將這件事變得**系統化且數學化**。

知識空間示意如下：

    ████████░░░░░░████████
    ████████░░░░░░████████   <-░░ = 拓撲空洞
    █████████████████████       （尚未探索的創新空間）
    ████████░░░░░░████████
    ████████░░░░░░████████

    █ = 既有專利 / 解法
    ░ = DeepThought 鎖定的高價值創新缺口
    ★ = V_target（你的最佳化目標）

## 📐 Hybrid DeepThought 方程式（BGE-M3 Dense-Sparse Triad）

核心數學引擎已從傳統 global MMR 演進為 **Hybrid Vector-Inverted Index Triad**。系統會在一個領域錨點（C）之下，尋找兩個語意上相容、但在歷史資料中 **完全沒有共同出現** 的概念（A 與 B），以此識別真正的 Topological Void。

**目標：** 找出滿足以下條件的 Triad (C, A, B)：

1. 領域凝聚性：`Cos(Dense(A), Dense(C)) > τ_domain` 且 `Cos(Dense(B), Dense(C)) > τ_domain`
2. 邊際新穎性校準：`τ_low ≤ Cos(Dense(A), Dense(B)) ≤ τ_high`
3. 真正的全域空洞：`Boolean_AND(Sparse_Top_Tokens(A), Sparse_Top_Tokens(B)) == 0`（透過 Elasticsearch）

| 元件 | 意義 | 執行方式 |
|------|------|----------|
| **Dense(·)** | 1024 維語意嵌入 | 透過 FAISS 做 Nearest Neighbor (KNN) 候選檢索。 |
| **Sparse(·)** | Top-5 詞彙權重 | 使用 BGE-M3 的 learned sparse layer 萃取精準的「Concept Anchors」。 |
| **τ_low, τ_high** | 邊際門檻 | 從 git history 的「首次子系統碰撞」校準而來，避免產生 Franken-IP。 |
| **True Global Void** | 歷史上的絕對真空 | 對整體倒排索引（code + docs + papers）執行精確 boolean query。 |

## 🏗️ 架構：解耦的三層式 Pipeline
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
|  |  Forager        -->  Hybrid Triad Void Detection         |  |
|  |  Maverick       -->  Divergent RFC Gen (Concept Anchors) |  |
|  |  Patent Shield  -->  Global Prior Art API Check          |  |
|  |  Reality Checker-->  Constraint Validation & Critique    |  |
|  |  Debate Panel   -->  Multi-Model Consensus & Mutation    |  |
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

## 🤖 三位一體 Agents

### 🕵️ The Forager（數學引擎）
- 執行 Hybrid DeepThought Triad Equation
- 協調雙引擎查詢（FAISS 做語意檢索 + Elasticsearch 做真實共現檢查）
- 萃取 BGE-M3 Top-5 Sparse Tokens 作為精準的「Concept Anchors」
- **模型**：`BAAI/bge-m3` + FAISS + Elasticsearch

### 💡 The Maverick（點子生成器）
- 生成發散式 RFC 草案
- 使用高溫、低約束創意模式
- 探索已識別的空洞空間
- **模型**：`DeepSeek-V3-0324-671B`（發散思考）

### 🛡️ The Reality Checker（批判者與評估器）
- 執行 **Global Prior-Art Check**（Google Patents / Semantic Scholar APIs）
- 透過 simulation 與靜態檢查驗證實體限制（x86 ISA、Linux ABI）
- 為 Conference Review Simulated Framework 產生精準錯誤日誌與 performance debt metrics
- **模型**：API Integrations + `Claude Sonnet 4`（最嚴格的技術推理）

### ⚖️ The Debate Panel（共識層）
- 多模型對抗式辯論
- **Deep Thinker**：`DeepSeek-R1-671B` — 邏輯與邊界案例
- **Code Expert**：`Qwen3-Coder-480B` — 實作可行性
- **Judge**：`Qwen3-32B` — 綜合裁決與最終判定

## 🔄 Pipeline 流程

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
   |          |  DeepSeek-V3-671B            |
   |          |  RFC Draft Generation        |
   |          +------------+
   |                  |
   |                  v
   |          +------------------+
   |          | PATENT SHIELD    |
   |          | Global Prior Art |
   |          +------------------+
   |                  | (Pass)
   |                  v
   |          +------------------+
   |          | REALITY CHECKER  |
        |          | Constraint Eval  |
   |          +------------------+
   |                  |
   +------------------+ (REVISE: 回饋 metrics 做 Mutation，最多 3-5 次)
                      |
                   APPROVE
                      |
                      v
              +--------------+
              | DEBATE PANEL |
              | R1-671B      |
              | Qwen3-32B    |
              +--------------+
                      |
                      v
              +----------------+
              | CONSENSUS JUDGE|
              +----------------+
                      |
                      v
              +--------------+
              | TID FORMATTER|
              +--------------+
```

## 🧭 實務說明：空洞定義與規模

- DeepThought 的 Topological Void 是相對於**本地語料邊界**定義（也就是你的 prior art 範圍），不是整個網際網路的絕對空洞。
- 目前工作規模（快照）：**1024 維 embedding**、約 **14 萬筆索引資料**。
- 本地 RAG 用來建立新穎性與證據邊界；LLM 推理負責提出跨領域假設。
- 生成點子不會直接採納：必須通過檢索 grounding、技術約束檢查，以及多 agent 評審/辯論，才會成為 TID 候選。
- 因此系統目標是產出**有證據支撐的發明假設**，而非直接保證可核准專利。

## 📊 資料來源

| 類別 | 來源 |
|------|------|
| 硬體規格 | Intel SDM Vol 1-4、Optimization Manual、CXL Spec、JEDEC DDR5 |
| Linux Kernel | torvalds/linux、LKML archives、kernel Documentation |
| Userspace | glibc、LLVM/Clang、jemalloc、DPDK、io_uring |
| Android | AOSP、Android Kernel、Bionic libc、ART Runtime、Binder |
| 學術論文 | ArXiv cs.AR / cs.OS、ISCA、MICRO、OSDI、ASPLOS |
| 專利 | USPTO full text、EPO Open Patent Services、WIPO |

## 📁 專案結構

目前倉庫結構（已實作）：

```
deepthought/
├── core/
│   └── deepthought_equation.py   # DeepThought Equation + MMR + arithmetic
│
├── agents/
│   ├── state.py                  # 共用 pipeline state + status
│   ├── llm_client.py             # 統一 LLM 呼叫器
│   ├── forager.py                # 空洞檢索 agent
│   ├── maverick.py               # 點子生成 agent
│   ├── reality_checker.py        # 批判與修訂 agent
│   ├── debate_panel.py           # 多模型綜合評審 agent
│   └── pipeline.py               # Multi-agent 協調器
│
├── data_collection/
│   ├── crawler/                  # Git/PDF/API/dataset crawlers
│   ├── parser/                   # Tree-sitter + Kconfig parsers
│   └── chunker/                  # 供 embedding 的 chunkers
│
├── vectordb/
│   ├── store.py                  # Chroma 介面 + void API
│   └── embedder.py               # 本地/API embedding backend
│
├── output/
│   ├── tid_formatter.py          # TID 報告格式器（md + html）
│   ├── templates/
│   └── generated/                # 已產生報告
│
├── services/
│   ├── ingestion_service.py      # 匯入流程協調
│   ├── idea_collision_service.py # 單模型 idea collision
│   ├── pipeline_service.py       # Multi-agent 執行服務
│   ├── status_store.py           # run status 持久化與重試查找
│   └── tid_notification_service.py # 新 TID email 通知服務
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

規劃中（尚未完整實作）：
- `core/void_detector.py`
- `vectordb/retriever.py` 與 `vectordb/collections.py`
- `services/query_service.py`
- `output/tid_formatter.py` 的 DOCX/PDF 匯出延伸

## 🚀 快速開始

### 前置需求

- Python 3.11+
- 建議使用 Intel 硬體（Xeon + Gaudi）
- 本地 LLM 推論建議至少 32GB RAM

### 設定流程

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

## 📌 目前實作進度（2026-04-02）

已完成：
- 本地端資料匯入主流程（crawler -> parser -> chunker -> Chroma store）
- DeepThought Equation、iterative MMR、concept arithmetic
- Topological Void 檢索 API 與 probe 腳本
- Multi-agent 主幹與可執行 CLI（`forager`、`maverick`、`reality_checker`、`debate_panel`）
- TID 報告格式器（Markdown + HTML 雙格式輸出）
- 執行狀態持久化與重試流程（`RETRY_PENDING` + `--retry-failed`）
- Pipeline 實跑已驗證可到 `APPROVED` 並輸出報告
- 常駐 service 模式（`scripts/run_pipeline_service.py`）
- 新 TID email 通知服務（`services/tid_notification_service.py`）

尚缺或部分完成：
- 完整 prior-art 覆蓋（USPTO/EPO/WIPO 正式匯入）
- UMAP 空洞地景視覺化
- Human-in-the-loop 審核介面/流程
- claim 級別信心分數與 DOCX/PDF 輸出
- Production hardening（安全整合、完整稽核、效能基準）

## ✅ TODO

### 立即執行路線（P0-P3）
- [ ] P0：先選定本週執行模式（`run_pipeline.py` 單次 vs `run_pipeline_service.py` 常駐）
- [ ] P0：固定一條 baseline 指令，作為 smoke test 參考
- [ ] P0：完成 Copilot backend 長跑驗證，直到第一份 `APPROVED` TID（`--once` 語義）
- [ ] P1：持續跑 service 模式，確認 `pipeline_runs.jsonl` 穩定成長
- [ ] P1：在穩定化期間維持通知關閉（`tid_email_notifications_enabled=false`）
- [ ] P2：補上 process supervision（systemd/supervisor）與自動重啟策略
- [ ] P2：補上 log rotation 與保留策略（長期服務）
- [ ] P3：補上 prior-art conflict detector 與 claim confidence scoring
- [x] P0：啟用 Linux 主機 Copilot CLI backend（`LLM_BACKEND=copilot_cli`）
- [x] P0：啟用嚴格輸出閘門（僅 `APPROVED` 才輸出 TID）
- [x] P1：加入殘酷淘汰機制（`fatal_flaw`、三振出局、stage 失敗紅牌）
- [x] P1：加入虛擬專利委員會共識審查（四專家 + 主席 + 一票否決）

### Phase 1: Foundation
- [x] 環境建立與驗證
- [x] Vector DB 初始化（ChromaDB）
- [x] C / Rust Tree-sitter 整合
- [ ] 使用 LlamaIndex 的基礎 RAG pipeline

### Phase 2: Data Ingestion
- [x] Linux Kernel crawler（arch/x86、sched、mm、bpf）
- [x] Intel SDM PDF parser
- [x] LKML 郵件列表 parser
- [x] Kconfig 相依圖建構器
- [x] ArXiv 論文匯入（cs.AR、cs.OS、cs.PF）
- [ ] USPTO 專利匯入
- [x] 增量更新排程器

### Phase 3: Core Engine
- [x] DeepThought Equation 實作
- [x] 拓撲空洞偵測器
- [x] **將 MMR 重構為 Hybrid BGE-M3 Triad Equation**（Dense + Sparse）
- [x] **部署 Elasticsearch / SQLite FTS5** sidecar，做真正的全域共現檢查
- [x] **實作 Historical First-Collision Calibration**，動態設定邊際門檻（`τ_low`, `τ_high`）
- [x] 概念算術（Latent Space Arithmetic）
- [ ] 空洞地景視覺化（UMAP 2D projection）

### Phase 4: Agent Pipeline
- [x] LangGraph State Machine 骨架
- [x] Forager Agent
- [x] Maverick Agent（DeepSeek-V3）
- [x] Reality Checker Agent（Claude Sonnet 4）
- [ ] **整合 Global Patent API**（Google Patents / Semantic Scholar）做 prior-art fast-screening
- [ ] **實作 Conference Review Simulated Framework**（將 reviewer metrics 回饋給 Maverick，進行多代 mutation）
- [x] Debate Panel（DeepSeek-R1 + Qwen3-Coder + Qwen3）
- [x] 透過委員會 fact-check 檢索與 fatal-flaw 規則的幻覺防護
- [ ] Human-in-the-loop 人工審查節點

### Phase 5: Output
- [x] TID 模板引擎
- [x] 專利 claim 自動生成
- [ ] 先前技術衝突檢測
- [ ] 每條 claim 的信心分數
- [ ] 匯出 DOCX / PDF

### Phase 6: Production Hardening
- [ ] Intel TDX / SGX 安全整合
- [ ] 完整 audit logging
- [ ] 效能基準測試
- [ ] 多領域支援（Android、RISC-V）
- [ ] 隨時間追蹤拓撲空洞變化
- [x] 常駐 service 執行模式
- [x] 新 TID email 通知掛鉤（SMTP）

## 🔁 Service 模式（常駐執行）

DeepThought 目前支援 Docker 化的常駐服務執行。

### 啟動 / 停止服務

```bash
bash scripts/start_service.sh
bash scripts/stop_service.sh
```

### 追蹤服務日誌

```bash
docker compose logs -f deepthought-service
```

### 資料持久化與不重建 DB 行為

容器使用以下 bind mount：

- `./data:/app/data`
- `./logs:/app/logs`
- `./output:/app/output`

因此既有 `data/raw` 與 `data/vectorstore` 會在重啟後直接沿用。
啟停服務不會重建向量資料庫。

### 執行參數（docker-compose environment）

- `TARGET`：每輪迭代的基礎任務目標。
- `N_DRAFTS`：每輪 Innovator 產生草案數（預設 `8`）。
- `TOP_K_VOIDS`：每輪挑選的 void 數量（預設 `30`）。
- `INTERVAL_SECONDS`：迴圈間隔秒數（預設 `300`）。
- `RANDOM_WALK_MUTATE_ENABLED`：`true` 時，檢索前先做 Random Walk and Mutate。
- `MUTATION_SEED_HINT`：Mutator Agent 的突變提示語。
- `SKIP_DUPLICATE_INPUT`：`true` 時，已完成的相同輸入指紋會略過。
- `TID_EMAIL_NOTIFICATIONS_ENABLED`：啟用/停用 SMTP 通知。

### 在 Linux 主機上用 GitHub Copilot CLI 試跑 GPT-5.4

如果你的 Linux 主機已完成 `gh auth login`，且 `gh copilot -p "..."` 可以正常回應，
就可以把 pipeline backend 切成 Copilot CLI，而不是內部 OpenAI-compatible endpoint。

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

注意：

- 這個模式適合 Linux 主機上的實驗，不建議直接當成無人值守 Docker production backend。
- 執行前請確認 `GH_TOKEN` / `GITHUB_TOKEN` 已 unset，讓 `gh copilot` 會回退讀取 `~/.config/gh/hosts.yml`。
- 成功互動時 Copilot CLI 目前會顯示使用 `gpt-5.4`，但實際模型選擇權仍在 GitHub Copilot 端，不是由本 repo 控制。

### Random Walk and Mutate 流程

當 `RANDOM_WALK_MUTATE_ENABLED=true`，每輪會執行：

1. 從 VectorDB 隨機抽一個 chunk。
2. 經由 LLM 突變成新的 x86/Linux 目標語句。
3. 以突變後 target 進入 MMR void discovery。

## 📧 新 TID Email 通知

啟動 service 前設定 SMTP 參數：

```bash
export SMTP_HOST=smtp.your-company.com
export SMTP_PORT=587
export SMTP_USE_TLS=true
export SMTP_USERNAME=your_account
export SMTP_PASSWORD=your_password
export SMTP_FROM=deepthought@your-company.com
export TID_NOTIFY_TO=your.name@your-company.com
```

當 run 到 `APPROVED`/`COMPLETED` 且有報告輸出時，系統會針對每個新 `run_id` 發送一次通知信。

## 🔒 安全模型

所有計算皆**100% 在 Intel 硬體本地執行**。

| 風險 | 緩解方式 |
|------|----------|
| IP 洩漏 | 無資料離開本地環境 |
| Void 座標 | 永不外傳 |
| 外部 API 呼叫 | 僅 Claude API（Reality Checker） |
| 記憶體保護 | Intel TME roadmap |
| 執行隔離 | Intel TDX / SGX roadmap |

唯一的外部網路呼叫是給 Reality Checker agent 使用的 Anthropic API。
其他所有 LLM 都在內部 Intel Gaudi2 endpoint 上執行。

## 📜 授權

專有授權 — All Rights Reserved

---

## 🙏 致謝

- [LangGraph](https://github.com/langchain-ai/langgraph) — Agent orchestration
- [LlamaIndex](https://github.com/run-llama/llama_index) — RAG framework
- [Tree-sitter](https://tree-sitter.github.io/) — AST parsing
- [ChromaDB](https://www.trychroma.com/) — 本地向量資料庫
- [DeepSeek](https://www.deepseek.com/) — Maverick 與 Debate 模型
- Douglas Adams — 命名靈感來源