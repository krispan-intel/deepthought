# DeepThought 架构

## 总览
DeepThought 采用解耦的三层架构。该设计保证数据摄取（高 I/O 负载）、代理推理（高 LLM 推理负载）与输出格式化彼此隔离，从而支持独立扩展与异步执行。

## Tier 1：Hybrid Data Tier（基础层）

### 职责
- **绝对知识边界：** 通过本地处理建立先前技术的“已知宇宙”。
- **双引擎索引：** 为每个代码 chunk 同时生成 Dense（语义）与 Sparse（词汇）表示。

### 核心机制
- **Tree-sitter 解析流水线：** 生成 AST 感知的 chunk，而不是朴素文本切分。可理解函数边界、struct 定义和 Kconfig 依赖。
- **BGE-M3 双编码器：**
	- 生成 `1024D Dense Vectors` 用于概念相似性（存储于 ChromaDB/FAISS）。
	- 提取 `Top-N Sparse Tokens` 用于绝对关键词追踪（存储于 SQLite FTS5 / Elasticsearch）。
- **绝对空洞过滤器：** 通过数学约束确保检索到的概念 `A` 与 `B` 在 sparse 索引中的历史共现满足 `Boolean_AND == 0`。

## Tier 2：Logic Tier（演化大脑）

### 职责
- 通过 LangGraph 状态机编排多代理发明合成流程。
- 强制执行 **Conference Review Simulated Framework**（Generate $\rightarrow$ Critique $\rightarrow$ Mutate）。

### Agent 委员会
1. **Forager：** 数学引擎。执行 Dense-Sparse Triad 方程以定位拓扑空洞。
2. **Maverick（作者）：** 发散思考者。围绕 Forager 发现的空洞起草 TID。
3. **Patent Shield：** 快速失败守门人。在消耗昂贵 reviewer token 前，先用全局 API（如 Semantic Scholar）预筛草稿。
4. **Reality Checker（Reviewer 2）：** 严格评估者。验证物理约束（x86 ISA、Memory Ordering、Kernel ABI）。不是二元拒绝，而是输出*诊断指标*（例如“第 42 行可能存在竞态条件”）。
5. **Debate Panel（程序委员会）：** 综合 Maverick 的修订与 Reality Checker 的批评，形成最终共识。

### 状态机保障
- **演化循环：** Maverick 必须基于 Reality Checker 指标反复修订，直到达到 `MAX_RETRIES` 上限（通常 3-5 次）。
- **致命缺陷拒绝：** 违反不可变物理规律的概念将被永久剪枝。

## Tier 3：Execution Tier（产出工厂）

### 职责
- 将已批准、非结构化的代理思考转换为结构化、可交付法务的产物。
- 管理持续“Nightly Mining”服务的生命周期。

### 组件
- **TID Formatter：** 将代理输出映射到标准化 IP 法务模板（Markdown、HTML、DOCX、PDF）。
- **Audit Logger：** 记录完整代理辩论记录（“反驳历史”），作为非显而易见性的证明。
- **Notification Hook：** 当 `APPROVED` 专利草稿成功产出时，异步发送 SMTP 告警。
