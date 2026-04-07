# DeepThought 架構

## 總覽
DeepThought 採用解耦的三層架構。此設計可確保資料匯入（高 I/O 負載）、代理推理（高 LLM 推論負載）與輸出格式化彼此隔離，支援各層獨立擴展與非同步執行。

## Tier 1：Hybrid Data Tier（基礎層）

### 職責
- **絕對知識邊界：** 透過本地化處理，建立先前技術的「已知宇宙」。
- **雙引擎索引：** 對每個程式碼 chunk 同時建立 Dense（語意）與 Sparse（詞彙）表示。

### 核心機制
- **Tree-sitter 解析流程：** 產生 AST 感知的 chunk，而非單純文字切割。可理解函式邊界、struct 定義與 Kconfig 相依。
- **BGE-M3 雙編碼器：**
	- 產生 `1024D Dense Vectors` 用於概念相似度（儲存於 ChromaDB/FAISS）。
	- 擷取 `Top-N Sparse Tokens` 進行精確關鍵詞追蹤（儲存於 SQLite FTS5 / Elasticsearch）。
- **絕對空洞過濾器：** 以數學方式保證被檢索的概念 `A` 與 `B` 在 sparse 索引中的歷史共現滿足 `Boolean_AND == 0`。

## Tier 2：Logic Tier（演化大腦）

### 職責
- 透過 LangGraph 狀態機協調多代理發明合成流程。
- 落實 **Conference Review Simulated Framework**（Generate $\rightarrow$ Critique $\rightarrow$ Mutate）。

### Agent 委員會
1. **Forager：** 數學引擎。執行 Dense-Sparse Triad 方程，定位拓樸空洞。
2. **Maverick（作者）：** 發散式創造者。根據 Forager 發現的空洞撰寫 TID 草稿。
3. **Patent Shield：** 快速失敗閘門。先用全域 API（例如 Semantic Scholar）預篩草稿，避免浪費昂貴 reviewer token。
4. **Reality Checker（Reviewer 2）：** 嚴格評估者。驗證物理約束（x86 ISA、Memory Ordering、Kernel ABI）。不是只做二元拒絕，而是輸出*診斷指標*（例如「第 42 行可能有競態條件」）。
5. **Debate Panel（程序委員會）：** 綜合 Maverick 修訂與 Reality Checker 批判，形成最終共識。

### 狀態機保證
- **演化迴圈：** Maverick 必須依據 Reality Checker 指標修稿，最多到 `MAX_RETRIES`（通常 3-5 次）。
- **致命缺陷拒絕：** 違反不可變物理法則的概念會被永久剪枝。

## Tier 3：Execution Tier（產出工廠）

### 職責
- 將通過審查、非結構化的代理思考轉為結構化、可交給法務的文件。
- 管理持續性「Nightly Mining」服務的生命週期。

### 元件
- **TID Formatter：** 將代理輸出映射到標準化 IP 法務模板（Markdown、HTML、DOCX、PDF）。
- **Audit Logger：** 記錄完整代理辯論逐字軌跡（「反駁歷史」），作為非顯而易見性的佐證。
- **Notification Hook：** 當 `APPROVED` 專利草稿成功產生時，非同步發送 SMTP 通知。
