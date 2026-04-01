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

## 📐 DeepThought 方程式

核心數學引擎結合了
**最大邊際相關性（Maximum Marginal Relevance, MMR）** 與 **潛在空間算術（Latent Space Arithmetic）**。

MMR_Patent = λ · Sim(V_new, V_target) - (1-λ) · max[Sim(V_new, V_existing)]

| 符號 | 意義 |
|------|------|
| V_new | 潛在空間中的候選創新向量 |
| V_target | 目標領域 / 最佳化目標向量 |
| V_existing | 既有專利 / 解法向量 |
| λ (lambda) | 相關性與新穎性的平衡參數（預設 0.7） |
| Sim(·) | 嵌入空間中的 cosine similarity |

### 解讀
MMR_Patent 分數高 = 與目標高度相似（具相關性）
且與既有解法相似度低（具新穎性）
= 拓撲空洞 = 創新機會

### Lambda 策略
| λ 值 | 策略 | 使用情境 |
|------|------|----------|
| 0.9 | 積極型 | 極度貼近目標，較少考慮先前技術 |
| 0.7 | 平衡型 ✅ | 預設：兼顧相關性與新穎性 |
| 0.5 | 保守型 | 最大化與既有解法的距離 |
| 0.3 | 顛覆型 | 藍海探索、典範轉移 |

## 🏗️ 架構：解耦的三層式 Pipeline
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

## 🤖 三位一體 Agents

### 🕵️ The Forager（數學引擎）
- 執行 DeepThought 方程式
- 查詢本地 RAG 知識庫
- 在潛在空間中定位拓撲空洞
- **模型**：純數學 + `IKT-Qwen3-Embedding-8B`

### 💡 The Maverick（點子生成器）
- 生成發散式 RFC 草案
- 使用高溫、低約束創意模式
- 探索已識別的空洞空間
- **模型**：`DeepSeek-V3-0324-671B`（發散思考）

### 🛡️ The Reality Checker（批判者）
- 以實體系統與 kernel 限制做無情審查
- 驗證 x86 ISA、Linux ABI、先前技術
- 輸出 APPROVE / REVISE / REJECT 判定
- **模型**：`Claude Sonnet 4`（最嚴格的技術推理）

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
│   └── status_store.py           # run status 持久化與重試查找
│
├── scripts/
│   ├── setup_vectordb.py
│   ├── ingest_kernel.py
│   ├── ingest_all.py
│   ├── run_phase3_probe.py
│   ├── run_idea_collision.py
│   ├── run_pipeline.py
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

## 📌 目前實作進度（2026-04-01）

已完成：
- 本地端資料匯入主流程（crawler -> parser -> chunker -> Chroma store）
- DeepThought Equation、iterative MMR、concept arithmetic
- Topological Void 檢索 API 與 probe 腳本
- Multi-agent 主幹與可執行 CLI（`forager`、`maverick`、`reality_checker`、`debate_panel`）
- TID 報告格式器（Markdown + HTML 雙格式輸出）
- 執行狀態持久化與重試流程（`RETRY_PENDING` + `--retry-failed`）

尚缺或部分完成：
- 完整 prior-art 覆蓋（USPTO/EPO/WIPO 正式匯入）
- UMAP 空洞地景視覺化
- Human-in-the-loop 審核介面/流程
- claim 級別信心分數與 DOCX/PDF 輸出
- Production hardening（安全整合、完整稽核、效能基準）

## ✅ TODO

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
- [x] 基於 MMR 的 retriever
- [x] 概念算術（Latent Space Arithmetic）
- [ ] 空洞地景視覺化（UMAP 2D projection）

### Phase 4: Agent Pipeline
- [x] LangGraph State Machine 骨架
- [x] Forager Agent
- [x] Maverick Agent（DeepSeek-V3）
- [x] Reality Checker Agent（Claude Sonnet 4）
- [x] Debate Panel（DeepSeek-R1 + Qwen3-Coder + Qwen3）
- [ ] 透過 RAG 驗證的幻覺防護
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