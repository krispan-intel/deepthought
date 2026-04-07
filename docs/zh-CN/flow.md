# DeepThought Pipeline 流程

## 端到端执行流程

1. **任务注入（输入）**
	- 用户或服务 daemon 注入目标领域（例如 `Linux Scheduler`）、优化目标（例如 `Latency Reduction`）以及先前技术边界。

2. **Phase 1：空洞检测（Forager）**
	- **动作：** 使用 BGE-M3 Triad 过滤器查询 Hybrid Data Tier。
	- **输出：** 返回 `VoidLandscape` 载荷，其中包含语义兼容但历史零重叠的 `Concept A` 和 `Concept B`。

3. **Phase 2：草稿生成（Maverick）**
	- **动作：** 使用 `VoidLandscape` 合成跨领域方案。
	- **输出：** 生成 `N` 份发散式 RFC（Request for Comments）结构化草稿。

4. **Phase 3：Patent Shield（快速失败）**
	- **动作：** 从草稿中提取关键 claim 并调用外部 API。
	- **输出：** 若检测到直接 1:1 先前技术冲突，立即中止该分支。

5. **Phase 4：Conference Review 模拟（循环）**
	- **动作：** Reality Checker 评估 RFC 的物理可行性。
	- **决策节点：**
	  - `APPROVE`：进入综合阶段。
	  - `REJECT`：发现致命缺陷，草稿淘汰。
	  - `REVISE`：生成具体诊断反馈（例如 lock contention、cache misses）。
	- **突变修订：** 若为 `REVISE`，Maverick 接收反馈并更新架构。循环直到 `APPROVE` 或命中 `MAX_RETRIES`。

6. **Phase 5：委员会综合（Debate Panel）**
	- **动作：** 聚合幸存草稿、修订历史与批评日志。
	- **输出：** 选出单个最具可辩护性的专利概念。

7. **Phase 6：产物铸造（导出）**
	- **动作：** 将最终状态格式化为 Technical Invention Disclosure（TID），并发送邮件通知。

## LangGraph 状态流转

- `[PENDING]` $\rightarrow$ `[FORAGING]`
- `[FORAGING]` $\rightarrow$ `[DRAFTING]`
- `[DRAFTING]` $\rightarrow$ `[REVIEW_EVALUATION]`
- `[REVIEW_EVALUATION]` $\rightarrow$ `[MUTATION_REVISION]`（触发循环）
- `[REVIEW_EVALUATION]` $\rightarrow$ `[REJECTED]`（终态）
- `[REVIEW_EVALUATION]` $\rightarrow$ `[COMMITTEE_CONSENSUS]`
- `[COMMITTEE_CONSENSUS]` $\rightarrow$ `[APPROVED_AND_EXPORTED]`（成功）
