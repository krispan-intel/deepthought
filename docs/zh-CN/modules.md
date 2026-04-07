# DeepThought 模块参考

本文档说明 DeepThought 核心模块的内部职责、关键函数与数据契约。

## ⚙️ 1. 核心数学引擎（`core/`）

### `core/deepthought_equation.py`
系统的数学核心。实现 **BGE-M3 Dense-Sparse Triad** 算法，永久替代旧版全局 MMR。
- **`find_hybrid_voids()`：** 执行主数学过滤流程。
	- 步骤 1：通过 FAISS 的 `Cosine(A, C)` 与 `Cosine(B, C)` 评估领域凝聚度。
	- 步骤 2：强制跨领域边际性约束（`τ_low <= Cosine(A, B) <= τ_high`）。
	- 步骤 3：调用 `SparseIndex` 验证 `Boolean_AND == 0`。
- **`calibrate_thresholds()`：** 分析跨子系统历史 Git 提交，动态设定 `τ_low` 与 `τ_high`，避免生成“Franken-IP”。

## 🧠 2. Agent 状态机（`agents/`）

### `agents/pipeline.py`
LangGraph 编排器。定义 StateGraph、条件边，并处理 Conference Review 模拟中的 `MAX_RETRIES` 循环。管理共享 `PipelineState` dataclass。

### `agents/forager.py`
- **角色：** 检索编排器。
- **动作：** 封装 `deepthought_equation.py`，传入领域目标，并将返回的 `VoidLandscape` 格式化为可注入 Maverick 提示的上下文块。

### `agents/maverick.py`（作者）
- **角色：** 发散生成与修订处理。
- **动作：** 基于 Forager 的概念锚点提交初始 `RFC Draft`。若进入 `REVISE` 状态，则吸收 Reality Checker 的诊断指标进行架构突变与修补。

### `agents/patent_shield.py`（快速失败闸门）
- **角色：** API 驱动的全局先前技术筛查。
- **动作：** 提取草稿关键词并查询 Semantic Scholar / Google Patents API。命中高相似结果时可跳过后续昂贵 LLM 处理。

### `agents/reality_checker.py`（Reviewer 2）
- **角色：** 技术约束验证器。
- **动作：** 评估草稿是否满足物理约束（如 Memory Ordering、x86 ISA 限制、Kernel ABI）。
- **输出：** 返回结构化诊断载荷（例如 `{ "status": "REVISE", "metric": "Cache line bounce detected in struct X", "severity": "HIGH" }`），而非原始文本。

### `agents/debate_panel.py`
- **角色：** 多模型共识与综合。
- **动作：** 作为程序委员会审阅原始草稿、Reality Checker 批评日志以及 Maverick 反驳/修订，输出最终 `APPROVED` 或 `REJECTED` 结论，并附详细技术依据。

## 🗄️ 3. 混合向量数据库（`vectordb/`）

### `vectordb/store.py`
统一数据访问层。
- 管理本地 `ChromaDB` 集合（或原生 FAISS 索引）用于 1024D Dense Vector 存储。
- 将语义相似度查询（KNN）路由到 Dense 后端。

### `vectordb/sparse_index.py`
精确匹配 sidecar 索引（可由 SQLite FTS5 或 Elasticsearch 后端实现）。
- **职责：** 维护 Top-N BGE-M3 sparse 词汇的倒排索引。
- **函数：** 提供 `check_absolute_vacuum(concept_a, concept_b)`，保证历史零共现。

### `vectordb/embedder.py`
- 本地 embedding 工厂。通过 HuggingFace / ONNX 实例化并缓存 `BAAI/bge-m3`，强制 100% 离线执行。

## 📥 4. 数据采集与摄取（`data_collection/`）

### `data_collection/crawler/`
- `kernel_crawler.py`：克隆特定 kernel 子系统，并解析 Git 历史用于碰撞校准。
- `pdf_parser.py`：提取 Intel SDM 与优化手册中的文本和表格。

### `data_collection/parser/tree_sitter_parser.py`
- **AST 感知解析：** 替代朴素文本切分。使用 Tree-sitter 的 `C` 与 `Rust` grammar 提取语义完整的函数、struct 与宏定义，确保 embedding 表示完整代码语义而非碎片文本。

## 🏭 5. 系统服务（`services/`）

### `services/pipeline_service.py`
- 持续执行守护进程。封装 LangGraph pipeline，用于 24/7 “Nightly Mining”，并处理循环间隔、配置覆盖和崩溃恢复。

### `services/audit_logger.py`
- **职责：** 追加写入 JSONL 日志。记录完整状态机轨迹（Prompts、Outputs、Revision Metrics、Final Verdicts），用于专利申请时证明“非显而易见性”历史。

### `services/tid_notification_service.py`
- SMTP webhook。当状态机达到 `APPROVED_AND_EXPORTED` 时，异步发送包含 IP 摘要的告警。

## 📤 6. 执行与输出（`output/`）

### `output/tid_formatter.py`
- 模板引擎（Jinja2）。将 Debate Panel 的非结构化 JSON 共识输出映射为严格、可用于法务的 TID markdown/HTML 文件。

### `output/claim_analysis.py`
- 基于最终批准架构自动生成独立与从属专利 claim，并依据先前技术距离为每条 claim 分配置信度分数。
