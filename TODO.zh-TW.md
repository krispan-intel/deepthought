# DeepThought TODO 清單

最後更新：2026-04-07

## 目前優先事項
- [ ] 先將目前所有待提交變更（tests/scripts/docs/observability）整理成乾淨 commit 批次。
- [ ] 在本次 commit 完成後，針對 `kernel_source` 的可疑歷史資料（commit-message / hash-like 標籤）做定向清理。

## 立即執行路線（P0-P3）
- [ ] P0：先選定本週執行模式（`run_pipeline.py` 單次 vs `run_pipeline_service.py` 常駐）
- [ ] P0：固定一條 baseline 指令，作為 smoke test 參考
- [ ] P0：完成 Copilot backend 長跑驗證，直到第一份 `APPROVED` TID（`--once` 語義）
- [ ] P1：持續跑 service 模式，確認 `pipeline_runs.jsonl` 穩定成長
- [ ] P1：在穩定化期間維持通知關閉（`tid_email_notifications_enabled=false`）
- [ ] P2：補上 process supervision（systemd/supervisor）與自動重啟策略
- [ ] P2：補上 log rotation 與保留策略（長期服務）
- [ ] P3：將 prior-art conflict detector 與 claim confidence scoring 做到 production-ready
- [x] P0：啟用 Linux 主機 Copilot CLI backend（`LLM_BACKEND=copilot_cli`）
- [x] P0：啟用嚴格輸出閘門（僅 `APPROVED` 才輸出 TID）
- [x] P1：加入殘酷淘汰機制（`fatal_flaw`、三振出局、stage 失敗紅牌）
- [x] P1：加入虛擬專利委員會共識審查（四專家 + 主席 + 一票否決）

## Phase 1: Foundation
- [x] 環境建立與驗證
- [x] Vector DB 初始化（ChromaDB）
- [x] C / Rust Tree-sitter 整合
- [x] 使用 LlamaIndex 的基礎 RAG pipeline

## Phase 2: Data Ingestion
- [x] Linux Kernel crawler（arch/x86、sched、mm、bpf）
- [x] Intel SDM PDF parser
- [x] LKML 郵件列表 parser
- [x] Kconfig 相依圖建構器
- [x] ArXiv 論文匯入（cs.AR、cs.OS、cs.PF）
- [ ] USPTO 專利匯入
- [x] 增量更新排程器

## Phase 3: Core Engine
- [x] DeepThought Equation 實作
- [x] 拓樸空洞偵測器
- [x] **將 MMR 重構為 Hybrid BGE-M3 Triad Equation**（Dense + Sparse）
- [x] **部署 Elasticsearch / SQLite FTS5** sidecar，做真正的全域共現檢查
- [x] **實作 Historical First-Collision Calibration**，動態設定邊際門檻（`tau_low`, `tau_high`）
- [x] 概念算術（Latent Space Arithmetic）
- [ ] 空洞地景視覺化（UMAP 2D projection）

## Phase 4: Agent Pipeline
- [x] LangGraph State Machine 骨架
- [x] Forager Agent
- [x] Maverick Agent（`copilot_cli`）
- [x] Reality Checker Agent（`copilot_cli`）
- [x] **整合 Global Patent API**（Google Patents / Semantic Scholar）做 prior-art fast-screening
- [x] **實作 Conference Review Simulated Framework**（將 reviewer metrics 回饋給 Maverick，進行多代 mutation）
- [x] Debate Panel（`copilot_cli` 角色化委員會）
- [x] 透過委員會 fact-check 檢索與 fatal-flaw 規則的幻覺防護
- [x] Human-in-the-loop 人工審查節點

## Phase 5: Output
- [x] TID 模板引擎
- [x] 專利 claim 自動生成
- [x] 先前技術衝突檢測
- [x] 每條 claim 的信心分數
- [x] 匯出 DOCX / PDF

## Phase 6: Production Hardening
- [x] 完整 audit logging
- [x] 隨時間追蹤拓樸空洞變化
- [x] 常駐 service 執行模式
- [x] 新 TID email 通知掛鉤（SMTP）
