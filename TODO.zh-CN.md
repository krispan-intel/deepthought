# DeepThought TODO 清单

最后更新：2026-04-07

## 当前优先事项
- [ ] 先将当前所有待提交变更（tests/scripts/docs/observability）整理为干净 commit 批次。
- [ ] 在本次 commit 完成后，针对 `kernel_source` 的可疑历史数据（commit-message / hash-like 标签）进行定向清理。

## 立即执行路线（P0-P3）
- [ ] P0：先确定本周运行模式（`run_pipeline.py` 单次 vs `run_pipeline_service.py` 常驻）
- [ ] P0：固定一条 baseline 命令，作为 smoke test 参考
- [ ] P0：完成 Copilot backend 长跑验证，直到第一份 `APPROVED` TID（`--once` 语义）
- [ ] P1：持续运行 service 模式，确认 `pipeline_runs.jsonl` 稳定增长
- [ ] P1：在稳定阶段保持通知关闭（`tid_email_notifications_enabled=false`）
- [ ] P2：补齐 process supervision（systemd/supervisor）与自动重启策略
- [ ] P2：补齐 log rotation 与保留策略（长期服务）
- [ ] P3：将 prior-art conflict detector 与 claim confidence scoring 做到 production-ready
- [x] P0：启用 Linux 主机 Copilot CLI backend（`LLM_BACKEND=copilot_cli`）
- [x] P0：启用严格输出闸门（仅 `APPROVED` 才输出 TID）
- [x] P1：加入残酷淘汰机制（`fatal_flaw`、三振出局、stage 失败红牌）
- [x] P1：加入虚拟专利委员会共识审查（四专家 + 主席 + 一票否决）

## Phase 1: Foundation
- [x] 环境搭建与验证
- [x] Vector DB 初始化（ChromaDB）
- [x] C / Rust Tree-sitter 集成
- [x] 基础 RAG pipeline（LlamaIndex）

## Phase 2: Data Ingestion
- [x] Linux Kernel crawler（arch/x86、sched、mm、bpf）
- [x] Intel SDM PDF parser
- [x] LKML 邮件列表 parser
- [x] Kconfig 依赖图构建器
- [x] ArXiv 论文摄取（cs.AR、cs.OS、cs.PF）
- [ ] USPTO 专利摄取
- [x] 增量更新调度器

## Phase 3: Core Engine
- [x] DeepThought Equation 实现
- [x] 拓扑空洞检测器
- [x] **将 MMR 重构为 Hybrid BGE-M3 Triad Equation**（Dense + Sparse）
- [x] **部署 Elasticsearch / SQLite FTS5** sidecar，进行真正的全局共现检查
- [x] **实现 Historical First-Collision Calibration**，动态设置边际阈值（`tau_low`, `tau_high`）
- [x] 概念算术（Latent Space Arithmetic）
- [ ] 空洞景观可视化（UMAP 2D projection）

## Phase 4: Agent Pipeline
- [x] LangGraph State Machine 骨架
- [x] Forager Agent
- [x] Maverick Agent（`copilot_cli`）
- [x] Reality Checker Agent（`copilot_cli`）
- [x] **集成 Global Patent API**（Google Patents / Semantic Scholar）进行 prior-art fast-screening
- [x] **实现 Conference Review Simulated Framework**（将 reviewer metrics 回馈给 Maverick，进行多代 mutation）
- [x] Debate Panel（`copilot_cli` 角色化委员会）
- [x] 基于委员会 fact-check 检索与 fatal-flaw 规则的幻觉防护
- [x] Human-in-the-loop 人工审查节点

## Phase 5: Output
- [x] TID 模板引擎
- [x] 专利 claim 自动生成
- [x] 现有技术冲突检测
- [x] 每条 claim 的置信度评分
- [x] 导出 DOCX / PDF

## Phase 6: Production Hardening
- [x] 完整审计日志
- [x] 随时间追踪拓扑空洞变化
- [x] 常驻 service 执行模式
- [x] 新 TID email 通知挂钩（SMTP）
