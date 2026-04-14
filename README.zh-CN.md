# 🧠 DeepThought

语言： [English](README.md) | [繁體中文](README.zh-TW.md) | [简体中文](README.zh-CN.md)

> *"The Answer to the Great Question of Life, the Universe and Everything"*
> — Douglas Adams, The Hitchhiker's Guide to the Galaxy

一个系统化、由 AI 驱动的发明探索引擎，用于在技术知识空间中识别
**拓扑空洞（Topological Voids）**，并将其具体化为
**可直接交由律师使用的技术发明披露文件（Technical Invention Disclosure, TID）**。

## 🎯 核心理念

传统研发通常依赖人的直觉去发现创新空白。
DeepThought 则把这件事变成**系统化且数学化**的过程。

知识空间可视化如下：

    ████████░░░░░░████████
    ████████░░░░░░████████   <-░░ = 拓扑空洞
    █████████████████████       （尚未探索的创新空间）
    ████████░░░░░░████████
    ████████░░░░░░████████

    █ = 现有专利 / 解决方案
    ░ = DeepThought 的目标：高价值创新缺口
    ★ = V_target（你的优化目标）

## 📐 Hybrid DeepThought 方程（BGE-M3 Dense-Sparse Triad）

核心数学引擎已经从传统 global MMR 演进为 **Hybrid Vector-Inverted Index Triad**。系统会在一个领域锚点（C）下寻找两个语义上兼容、但在历史资料中 **完全没有共同出现** 的概念（A 与 B），以此识别真正的 Topological Void。

**实际公式：**

```
HybridScore(A,B) = λ · Cos(Dense(A⊕B), Dense(C))
                 - (1-λ) · AvgRedundancy(A,B)
                 + w_m · MarginalityFit(A,B)
                 + bias
```

**目标：** 找到满足以下条件的 Triad (C, A, B)：

1. 领域凝聚性：`Cos(Dense(A), Dense(C)) > τ_domain` 且 `Cos(Dense(B), Dense(C)) > τ_domain`（τ_domain 使用百分位自适应校准）
2. 边际新颖性校准：`τ_low ≤ Cos(Dense(A), Dense(B)) ≤ τ_high`
3. 稀疏词汇桥接：配对必须在去停用词过滤后至少共享一个有意义的 token（共现检查器通过 Elasticsearch 已**禁用**）

| 组件 | 含义 | 执行方式 |
|------|------|----------|
| **Dense(·)** | 1024 维语义嵌入 | 通过 FAISS 做 Nearest Neighbor (KNN) 候选检索。 |
| **Sparse(·)** | Top-5 词汇权重 | 使用 BGE-M3 的 learned sparse layer 提取精准的「Concept Anchors」。 |
| **τ_low, τ_high** | 边际阈值 | 从 git history 的「首次子系统碰撞」校准而来，避免产生 Franken-IP。 |
| **τ_domain** | 领域凝聚阈值 | 百分位自适应校准（percentile-adaptive calibration）。 |
| **Sparse Lexical Bridge** | 稀疏词汇桥接 | 去停用词后至少共享一个有意义 token；Elasticsearch 共现检查器已禁用。 |

## 🏗️ 架构：解耦的三层 Pipeline
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
|  |  Professor      -->  Pre-Flight Structure Review         |  |
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

## 🤖 Agents

### 🕵️ The Forager（数学引擎）
- 执行 Hybrid DeepThought Triad Equation
- 协调双引擎查询（FAISS 做语义检索 + Elasticsearch 做真实共现检查）
- 提取 BGE-M3 Top-5 Sparse Tokens 作为精准的「Concept Anchors」
- **模型**：`BAAI/bge-m3` + FAISS + Elasticsearch

### 💡 The Maverick（创意生成器）
- 生成发散式 RFC 草案
- 使用高温、低约束创意模式
- 探索已识别的空洞空间
- **模型**：`gpt-5.4`（通过 `--model` 指定，`--effort high`）

### 📚 The Professor（Pre-Flight 审查员）
- Maverick 后的快速筛选关卡，验证草稿结构和技术一致性
- 检查 RFC 格式完整性、术语一致性、claim 是否与 void 对应
- 不合格草稿直接退回 Maverick 重新生成，节省下游算力
- **模型**：`gpt-5.2`（通过 `--model` 指定，`--effort high`）

### 🛡️ The Patent Shield（快速失败关卡）
- 在昂贵的 LLM 处理之前，预先筛查草稿是否与全局 API（Semantic Scholar / Google Patents）冲突
- 提取关键 claims 并检查是否存在直接 1:1 前案冲突
- 精确匹配时立即终止该分支，节省下游算力
- **模型**：API 集成（`patent_shield.py`）

### 🛡️ The Reality Checker（批判者与评估器）
- 执行 **Global Prior-Art Check**（Google Patents / Semantic Scholar APIs）
- 通过 simulation 与静态检查验证物理约束（x86 ISA、Linux ABI）
- 为 Conference Review Simulated Framework 生成精确错误日志与 performance debt metrics
- **模型**：API Integrations + `gpt-5.2`（通过 `--model` 指定，`--effort high`）

### ⚖️ The Debate Panel（共识层）
- 模拟 conference review 的对抗式委员会
- **4 位具名 Specialist（并行执行）**：
  - Kernel Hardliner（内核强硬派）
  - Prior-Art Shark（前案鲨鱼）
  - Intel Strategist（Intel 策略师）
  - Security Guardian（安全守护者）
- **确定性裁决规则**：fatal flaw 拒绝、多数拒绝（≥2）、黄牌拒绝（≥3）、全体批准、多数批准
- **模型**：`gpt-5.2`（通过 `--model` 指定，`--effort high`）

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
   |          |  gpt-5.4 --effort high       |
   |          |  RFC Draft Generation        |
   |          +------------+
   |                  |
   |                  v
   |          +------------------+
   |          |  PROFESSOR       |
   |          |  gpt-5.2         |
   |          |  Pre-Flight 审查  |
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
   |          | Constraint Eval  |
   |          +------------------+
   |                  |
   +------------------+ (REVISE: 回馈 metrics 做 Mutation，最多 3-5 次)
                      |
                   APPROVE
                      |
                      v
              +--------------+
              | DEBATE PANEL |
              | gpt-5.2      |
              | 4 Specialists|
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

## 🧭 实务说明：空洞定义与规模

- DeepThought 的 Topological Void 是相对于**本地语料边界**定义的（即你的 prior art 范围），不是整个互联网的绝对空洞。
- 当前工作规模（快照）：**1024 维 embedding**、约 **14 万条索引数据**。
- 本地 RAG 用于建立新颖性与证据边界；LLM 推理用于提出跨领域假设。
- 生成想法不会被直接采纳：必须通过检索 grounding、技术约束检查，以及多 agent 评审/辩论，才会成为 TID 候选。
- 因此系统目标是输出**有证据支撑的发明假设**，而不是直接保证专利可授权。

## 📊 数据来源

| 类别 | 来源 |
|------|------|
| 硬件规格 | Intel SDM Vol 1-4、Optimization Manual、CXL Spec、JEDEC DDR5 |
| Linux Kernel | torvalds/linux、LKML archives、kernel Documentation |
| Userspace | glibc、LLVM/Clang、jemalloc、DPDK、io_uring |
| Android | AOSP、Android Kernel、Bionic libc、ART Runtime、Binder |
| 学术论文 | ArXiv cs.AR / cs.OS、ISCA、MICRO、OSDI、ASPLOS |
| 专利 | USPTO full text、EPO Open Patent Services、WIPO |

## 📁 项目结构

当前仓库结构（已实现）：

```
deepthought/
├── core/
│   └── deepthought_equation.py   # DeepThought Equation + MMR + arithmetic
│
├── agents/
│   ├── state.py                  # 共享 pipeline state + status
│   ├── llm_client.py             # 统一 LLM 调用器
│   ├── forager.py                # 空洞检索 agent
│   ├── maverick.py               # 创意生成 agent
│   ├── professor.py              # Pre-Flight 结构审查 agent
│   ├── patent_shield.py          # 前案快速失败关卡
│   ├── reality_checker.py        # 批判与修订 agent
│   ├── debate_panel.py           # 多模型综合评审 agent
│   └── pipeline.py               # Multi-agent 编排器
│
├── data_collection/
│   ├── crawler/                  # Git/PDF/API/dataset crawlers
│   ├── parser/                   # Tree-sitter + Kconfig parsers
│   └── chunker/                  # 用于 embedding 的 chunkers
│
├── vectordb/
│   ├── store.py                  # Chroma 接口 + void API
│   ├── sparse_index.py           # SQLite FTS5 / ES 倒排索引
│   └── embedder.py               # 本地/API embedding backend
│
├── output/
│   ├── tid_formatter.py          # TID 报告格式器（md + html + docx + pdf）
│   ├── claim_analysis.py         # 专利 claim 自动生成 + 置信度评分
│   ├── templates/
│   └── generated/                # 已生成报告
│
├── services/
│   ├── ingestion_service.py      # 摄取流程编排
│   ├── idea_collision_service.py # 单模型 idea collision
│   ├── query_service.py          # 基础 RAG 查询服务（LlamaIndex）
│   ├── pipeline_service.py       # Multi-agent 运行服务
│   ├── status_store.py           # run status 持久化与重试检索
│   ├── audit_logger.py           # 仅追加 JSONL 审计日志
│   ├── human_review.py           # Human-in-the-loop 审核检查点
│   ├── target_mutation_service.py # 随机游走目标突变
│   ├── void_tracker.py           # 增量空洞追踪
│   └── tid_notification_service.py # 新 TID email 通知服务
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

规划中（尚未完整实现）：
- `core/void_detector.py`
- `vectordb/retriever.py` 与 `vectordb/collections.py`

## 🚀 快速开始

### 前置要求

- Python 3.11+
- 建议使用 Intel 硬件（Xeon + Gaudi）
- 本地 LLM 推理建议至少 32GB RAM

### 配置流程

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

## 📌 当前实现进度（2026-04-14）

已完成：
- 本地数据摄取主流程（crawler -> parser -> chunker -> Chroma store）
- DeepThought Equation、iterative MMR、concept arithmetic
- Topological Void 检索 API 与 probe 脚本
- Multi-agent 主干与可执行 CLI（`forager`、`maverick`、`professor`、`reality_checker`、`debate_panel`）
- TID 报告格式器（Markdown + HTML 双格式输出）
- 运行状态持久化与重试流程（`RETRY_PENDING` + `--retry-failed`）
- Pipeline 实跑已验证可到 `APPROVED` 并产出报告
- 常驻 service 模式（`scripts/run_pipeline_service.py`）
- 新 TID email 通知服务（`services/tid_notification_service.py`）
- Professor agent：Maverick 后的 Pre-Flight 结构审查关卡
- Debate Panel 4 具名 specialist 并行评审 + 确定性裁决规则
- 全部 agent 迁移至 Claude API，消除 Copilot CLI 依赖
- 模型配置：Maverick 使用 gpt-5.4，审查阶段使用 gpt-5.2，均 `--effort high`

尚缺或部分完成：
- 完整 prior-art 覆盖（USPTO/EPO/WIPO 正式摄取）
- UMAP 空洞景观可视化
- Human-in-the-loop 审核界面/流程
- Production hardening（安全集成、完整审计、性能基准）

## ✅ TODO

当前维护于独立清单文件：

- English: [TODO.md](TODO.md)
- 繁体中文: [TODO.zh-TW.md](TODO.zh-TW.md)
- 简体中文: [TODO.zh-CN.md](TODO.zh-CN.md)

## 🔁 Service 模式（常驻运行）

DeepThought 现在支持 Docker 化的常驻服务运行。

### 启动 / 停止服务

```bash
bash scripts/start_service.sh
bash scripts/stop_service.sh
```

### 查看服务日志

```bash
docker compose logs -f deepthought-service
```

### 数据持久化与不重建 DB 行为

容器使用以下 bind mount：

- `./data:/app/data`
- `./logs:/app/logs`
- `./output:/app/output`

因此现有 `data/raw` 与 `data/vectorstore` 会在重启后继续复用。
启动/停止服务不会重建向量数据库。

### 运行参数（docker-compose environment）

- `TARGET`：每轮迭代的基础任务目标。
- `N_DRAFTS`：每轮 Innovator 生成草案数（默认 `8`）。
- `TOP_K_VOIDS`：每轮选取的 void 数量（默认 `30`）。
- `INTERVAL_SECONDS`：循环间隔秒数（默认 `300`）。
- `RANDOM_WALK_MUTATE_ENABLED`：为 `true` 时，检索前先执行 Random Walk and Mutate。
- `MUTATION_SEED_HINT`：Mutator Agent 的突变提示语。
- `SKIP_DUPLICATE_INPUT`：为 `true` 时，已完成的相同输入指纹将被跳过。
- `TID_EMAIL_NOTIFICATIONS_ENABLED`：启用/禁用 SMTP 通知。

### Copilot CLI Backend（当前默认）

如果你的 Linux 主机已经完成 `gh auth login`，且 `gh copilot -p "..."` 可以正常返回，
即可使用 Copilot CLI 作为 pipeline 默认模型接口。

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

- 这个模式适合 Linux 主机上的实验，不建议直接作为无人值守 Docker production backend。
- 运行前请确认 `GH_TOKEN` / `GITHUB_TOKEN` 已 unset，让 `gh copilot` 回退读取 `~/.config/gh/hosts.yml`。
- Copilot CLI 在成功交互时目前会显示使用 `gpt-5.4`，模型选择现在由本 repo 通过 `--model` 参数控制。

### Random Walk and Mutate 流程

当 `RANDOM_WALK_MUTATE_ENABLED=true`，每轮会执行：

1. 从 VectorDB 随机抽取一个 chunk。
2. 通过 LLM 突变成新的 x86/Linux 目标短语。
3. 使用突变后的 target 进入 MMR void discovery。

## 📧 新 TID Email 通知

启动 service 前设置 SMTP 参数：

```bash
export SMTP_HOST=smtp.your-company.com
export SMTP_PORT=587
export SMTP_USE_TLS=true
export SMTP_USERNAME=your_account
export SMTP_PASSWORD=your_password
export SMTP_FROM=deepthought@your-company.com
export TID_NOTIFY_TO=your.name@your-company.com
```

当 run 到 `APPROVED`/`COMPLETED` 且有报告输出时，系统会对每个新 `run_id` 发送一次通知邮件。

## 🔒 安全模型

所有计算均**100% 在 Intel 硬件本地执行**。

| 风险 | 缓解方式 |
|------|----------|
| IP 泄漏 | 数据不会离开本地环境 |
| Void 坐标 | 永不外传 |
| 外部 API 调用 | Semantic Scholar（可选）+ Copilot CLI gateway |
| 内存保护 | Intel TME roadmap |
| 执行隔离 | Intel TDX / SGX roadmap |

外部网络调用可能包含 Semantic Scholar API 与
GitHub Copilot CLI gateway，会根据运行配置启用。

## 📜 许可

专有许可 — All Rights Reserved

---

## 🙏 致谢

- [LangGraph](https://github.com/langchain-ai/langgraph) — Agent orchestration
- [LlamaIndex](https://github.com/run-llama/llama_index) — RAG framework
- [Tree-sitter](https://tree-sitter.github.io/) — AST parsing
- [ChromaDB](https://www.trychroma.com/) — 本地向量数据库
- [GitHub Copilot CLI](https://docs.github.com/en/copilot) — 通过 `copilot_cli` 统一模型后端
- Douglas Adams — 命名灵感来源