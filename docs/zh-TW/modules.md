# DeepThought 模組參考

本文件說明 DeepThought 核心模組的內部職責、關鍵函式與資料契約。

## ⚙️ 1. 核心數學引擎（`core/`）

### `core/deepthought_equation.py`
系統的數學核心。實作 **BGE-M3 Dense-Sparse Triad** 演算法，永久取代舊版全域 MMR。
- **`find_hybrid_voids()`：** 執行主要數學過濾流程。
	- 步驟 1：透過 FAISS 的 `Cosine(A, C)` 與 `Cosine(B, C)` 評估領域凝聚度。
	- 步驟 2：套用跨領域邊際性約束（`τ_low <= Cosine(A, B) <= τ_high`）。
	- 步驟 3：呼叫 `SparseIndex` 驗證 `Boolean_AND == 0`。
- **`calibrate_thresholds()`：** 分析跨子系統歷史 Git commit，動態設定 `τ_low` 與 `τ_high`，避免產生「Franken-IP」。

## 🧠 2. Agent 狀態機（`agents/`）

### `agents/pipeline.py`
LangGraph 編排器。定義 StateGraph、條件邊與 Conference Review 的 `MAX_RETRIES` 迴圈，並管理共享的 `PipelineState` dataclass。

### `agents/forager.py`
- **角色：** 檢索編排器。
- **動作：** 封裝 `deepthought_equation.py`，傳入領域目標，並把 `VoidLandscape` 格式化為可注入 Maverick 提示的上下文區塊。

### `agents/maverick.py`（作者）
- **角色：** 發散生成與修訂處理。
- **動作：** 依 Forager 的概念錨點提交初始 `RFC Draft`。若進入 `REVISE` 狀態，則吸收 Reality Checker 的診斷指標進行架構突變與修補。

### `agents/patent_shield.py`（快速失敗閘門）
- **角色：** API 驅動的全域先前技術篩查。
- **動作：** 擷取草稿關鍵詞並查詢 Semantic Scholar / Google Patents API。若命中高相似結果，可提前阻斷下游昂貴 LLM 流程。

### `agents/reality_checker.py`（Reviewer 2）
- **角色：** 技術約束驗證者。
- **動作：** 檢查草稿是否符合物理約束（如 Memory Ordering、x86 ISA 限制、Kernel ABI）。
- **輸出：** 回傳結構化診斷（例如 `{ "status": "REVISE", "metric": "Cache line bounce detected in struct X", "severity": "HIGH" }`），而非純文字。

### `agents/debate_panel.py`
- **角色：** 多模型共識與綜合判定。
- **動作：** 扮演程序委員會，審閱原始草稿、Reality Checker 批判日誌與 Maverick 反駁/修訂，最終輸出 `APPROVED` 或 `REJECTED`，並附技術理由。

## 🗄️ 3. 混合向量資料庫（`vectordb/`）

### `vectordb/store.py`
統一資料存取層。
- 管理本地 `ChromaDB` 集合（或原生 FAISS 索引）以儲存 1024D Dense Vector。
- 將語意相似度查詢（KNN）路由到 Dense 後端。

### `vectordb/sparse_index.py`
精確比對 sidecar 索引（可由 SQLite FTS5 或 Elasticsearch 後端實作）。
- **職責：** 維護 BGE-M3 Top-N Sparse 詞彙倒排索引。
- **函式：** 提供 `check_absolute_vacuum(concept_a, concept_b)`，保證歷史零共現。

### `vectordb/embedder.py`
- 本地 embedding 工廠。透過 HuggingFace / ONNX 建立並快取 `BAAI/bge-m3`，強制離線執行。

## 📥 4. 資料收集與匯入（`data_collection/`）

### `data_collection/crawler/`
- `kernel_crawler.py`：克隆特定 kernel 子系統，解析 Git 歷史供碰撞校準。
- `pdf_parser.py`：抽取 Intel SDM 與最佳化手冊中的文字與表格。

### `data_collection/parser/tree_sitter_parser.py`
- **AST 感知解析：** 取代天真式文字切割。使用 Tree-sitter 的 `C` 與 `Rust` grammar 萃取語義完整的函式、struct 與 macro 定義，避免 embedding 片段化。

## 🏭 5. 系統服務（`services/`）

### `services/pipeline_service.py`
- 常駐執行 daemon。封裝 LangGraph pipeline 以支援 24/7「Nightly Mining」，包含迴圈間隔、設定覆寫與崩潰復原。

### `services/audit_logger.py`
- **職責：** Append-only JSONL 日誌。記錄完整狀態機軌跡（Prompts、Outputs、Revision Metrics、Final Verdicts），作為專利申請時的「非顯而易見性」證據鏈。

### `services/tid_notification_service.py`
- SMTP webhook。當狀態機達到 `APPROVED_AND_EXPORTED` 時，非同步發送包含 IP 摘要的通知。

## 📤 6. 執行與輸出（`output/`）

### `output/tid_formatter.py`
- 模板引擎（Jinja2）。將 Debate Panel 的非結構化 JSON 共識輸出，映射為嚴格、可供法務使用的 TID Markdown/HTML 文件。

### `output/claim_analysis.py`
- 依最終核准架構自動生成獨立與附屬專利 claim，並依先前技術距離為每條 claim 指派信心分數。
