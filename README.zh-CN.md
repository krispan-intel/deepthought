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

## 📐 DeepThought 方程

核心数学引擎结合了
**最大边际相关性（Maximum Marginal Relevance, MMR）** 与 **潜在空间算术（Latent Space Arithmetic）**。

MMR_Patent = λ · Sim(V_new, V_target) - (1-λ) · max[Sim(V_new, V_existing)]

| 符号 | 含义 |
|------|------|
| V_new | 潜在空间中的候选创新向量 |
| V_target | 目标领域 / 优化目标向量 |
| V_existing | 现有专利 / 解决方案向量 |
| λ (lambda) | 相关性与新颖性的平衡参数（默认 0.7） |
| Sim(·) | 嵌入空间中的 cosine similarity |

### 解读
高 MMR_Patent 分数 = 与目标高度相似（相关）
且与现有方案相似度低（新颖）
= 拓扑空洞 = 创新机会

### Lambda 策略
| λ 值 | 策略 | 使用场景 |
|------|------|----------|
| 0.9 | 激进型 | 尽量贴近目标，较少考虑现有技术 |
| 0.7 | 平衡型 ✅ | 默认：兼顾相关性与新颖性 |
| 0.5 | 保守型 | 最大化与现有方案的距离 |
| 0.3 | 颠覆型 | 蓝海探索、范式转移 |

## 🏗️ 架构：解耦的三层 Pipeline
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

## 🤖 三位一体 Agents

### 🕵️ The Forager（数学引擎）
- 执行 DeepThought 方程
- 查询本地 RAG 知识库
- 在潜在空间中定位拓扑空洞
- **模型**：纯数学 + `IKT-Qwen3-Embedding-8B`

### 💡 The Maverick（创意生成器）
- 生成发散式 RFC 草案
- 使用高温、低约束创意模式
- 探索已识别的空洞空间
- **模型**：`DeepSeek-V3-0324-671B`（发散思考）

### 🛡️ The Reality Checker（批判者）
- 基于物理系统与 kernel 约束进行严格审查
- 校验 x86 ISA、Linux ABI、现有技术
- 输出 APPROVE / REVISE / REJECT 结论
- **模型**：`Claude Sonnet 4`（最严格的技术推理）

### ⚖️ The Debate Panel（共识层）
- 多模型对抗式辩论
- **Deep Thinker**：`DeepSeek-R1-671B` — 逻辑与边界案例
- **Code Expert**：`Qwen3-Coder-480B` — 实现可行性
- **Judge**：`Qwen3-32B` — 综合判断与最终裁决

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
│   └── embedder.py               # 本地/API embedding backend
│
├── output/
│   ├── tid_formatter.py          # TID 报告格式器（md + html）
│   ├── templates/
│   └── generated/                # 已生成报告
│
├── services/
│   ├── ingestion_service.py      # 摄取流程编排
│   ├── idea_collision_service.py # 单模型 idea collision
│   ├── pipeline_service.py       # Multi-agent 运行服务
│   ├── status_store.py           # run status 持久化与重试检索
│   └── tid_notification_service.py # 新 TID email 通知服务
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

规划中（尚未完整实现）：
- `core/void_detector.py`
- `vectordb/retriever.py` 与 `vectordb/collections.py`
- `services/query_service.py`
- `output/tid_formatter.py` 的 DOCX/PDF 导出扩展

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

## 📌 当前实现进度（2026-04-02）

已完成：
- 本地数据摄取主流程（crawler -> parser -> chunker -> Chroma store）
- DeepThought Equation、iterative MMR、concept arithmetic
- Topological Void 检索 API 与 probe 脚本
- Multi-agent 主干与可执行 CLI（`forager`、`maverick`、`reality_checker`、`debate_panel`）
- TID 报告格式器（Markdown + HTML 双格式输出）
- 运行状态持久化与重试流程（`RETRY_PENDING` + `--retry-failed`）
- Pipeline 实跑已验证可到 `APPROVED` 并产出报告
- 常驻 service 模式（`scripts/run_pipeline_service.py`）
- 新 TID email 通知服务（`services/tid_notification_service.py`）

尚缺或部分完成：
- 完整 prior-art 覆盖（USPTO/EPO/WIPO 正式摄取）
- UMAP 空洞景观可视化
- Human-in-the-loop 审核界面/流程
- claim 级置信度评分与 DOCX/PDF 导出
- Production hardening（安全集成、完整审计、性能基准）

## ✅ TODO

### 立即执行路线（P0-P3）
- [ ] P0：先确定本周运行模式（`run_pipeline.py` 单次 vs `run_pipeline_service.py` 常驻）
- [ ] P0：固定一条 baseline 命令，作为 smoke test 参考
- [ ] P0：在当前超大模型配置下连续验证 2-3 次成功 run
- [ ] P1：持续运行 service 模式，确认 `pipeline_runs.jsonl` 稳定增长
- [ ] P1：在稳定阶段保持通知关闭（`tid_email_notifications_enabled=false`）
- [ ] P2：补齐 process supervision（systemd/supervisor）与自动重启策略
- [ ] P2：补齐 log rotation 与保留策略（长期服务）
- [ ] P3：补齐 hallucination guard（RAG 验证）、prior-art conflict detector、claim confidence scoring

### Phase 1: Foundation
- [x] 环境搭建与验证
- [x] Vector DB 初始化（ChromaDB）
- [x] C / Rust Tree-sitter 集成
- [ ] 基础 RAG pipeline（LlamaIndex）

### Phase 2: Data Ingestion
- [x] Linux Kernel crawler（arch/x86、sched、mm、bpf）
- [x] Intel SDM PDF parser
- [x] LKML 邮件列表 parser
- [x] Kconfig 依赖图构建器
- [x] ArXiv 论文摄取（cs.AR、cs.OS、cs.PF）
- [ ] USPTO 专利摄取
- [x] 增量更新调度器

### Phase 3: Core Engine
- [x] DeepThought Equation 实现
- [x] 拓扑空洞检测器
- [x] 基于 MMR 的 retriever
- [x] 概念算术（Latent Space Arithmetic）
- [ ] 空洞景观可视化（UMAP 2D projection）

### Phase 4: Agent Pipeline
- [x] LangGraph State Machine 骨架
- [x] Forager Agent
- [x] Maverick Agent（DeepSeek-V3）
- [x] Reality Checker Agent（Claude Sonnet 4）
- [x] Debate Panel（DeepSeek-R1 + Qwen3-Coder + Qwen3）
- [ ] 基于 RAG 验证的幻觉防护
- [ ] Human-in-the-loop 人工审查节点

### Phase 5: Output
- [x] TID 模板引擎
- [x] 专利 claim 自动生成
- [ ] 现有技术冲突检测
- [ ] 每条 claim 的置信度评分
- [ ] 导出 DOCX / PDF

### Phase 6: Production Hardening
- [ ] Intel TDX / SGX 安全集成
- [ ] 完整审计日志
- [ ] 性能基准测试
- [ ] 多领域支持（Android、RISC-V）
- [ ] 随时间追踪拓扑空洞变化
- [x] 常驻 service 执行模式
- [x] 新 TID email 通知挂钩（SMTP）

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
| 外部 API 调用 | 仅 Claude API（Reality Checker） |
| 内存保护 | Intel TME roadmap |
| 执行隔离 | Intel TDX / SGX roadmap |

唯一的外部网络调用是为 Reality Checker agent 使用的 Anthropic API。
其他所有 LLM 都运行在内部 Intel Gaudi2 endpoint 上。

## 📜 许可

专有许可 — All Rights Reserved

---

## 🙏 致谢

- [LangGraph](https://github.com/langchain-ai/langgraph) — Agent orchestration
- [LlamaIndex](https://github.com/run-llama/llama_index) — RAG framework
- [Tree-sitter](https://tree-sitter.github.io/) — AST parsing
- [ChromaDB](https://www.trychroma.com/) — 本地向量数据库
- [DeepSeek](https://www.deepseek.com/) — Maverick 与 Debate 模型
- Douglas Adams — 命名灵感来源