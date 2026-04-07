# DeepThought Pipeline 流程

## 端到端執行流程

1. **任務注入（輸入）**
	- 使用者或服務 daemon 注入目標領域（例如 `Linux Scheduler`）、最佳化目標（例如 `Latency Reduction`）與先前技術邊界。

2. **Phase 1：空洞偵測（Forager）**
	- **動作：** 使用 BGE-M3 Triad 過濾器查詢 Hybrid Data Tier。
	- **輸出：** 回傳 `VoidLandscape`，其中包含語意相容但歷史零重疊的 `Concept A` 與 `Concept B`。

3. **Phase 2：草稿生成（Maverick）**
	- **動作：** 使用 `VoidLandscape` 合成跨領域解法。
	- **輸出：** 生成 `N` 份具結構的 RFC（Request for Comments）發散草稿。

4. **Phase 3：Patent Shield（快速失敗）**
	- **動作：** 從草稿擷取關鍵 claim 並呼叫外部 API。
	- **輸出：** 若偵測到直接 1:1 先前技術衝突，立即中止該分支。

5. **Phase 4：Conference Review 模擬（迴圈）**
	- **動作：** Reality Checker 評估 RFC 的物理可行性。
	- **決策節點：**
	  - `APPROVE`：進入綜合階段。
	  - `REJECT`：發現致命缺陷，草稿淘汰。
	  - `REVISE`：產生具體診斷回饋（例如 lock contention、cache misses）。
	- **突變修訂：** 若為 `REVISE`，Maverick 接收回饋並更新架構，迴圈直到 `APPROVE` 或達到 `MAX_RETRIES`。

6. **Phase 5：委員會綜合（Debate Panel）**
	- **動作：** 聚合存活草稿、修訂歷史與批判日誌。
	- **輸出：** 選出單一最具防禦性的專利概念。

7. **Phase 6：成品鑄造（匯出）**
	- **動作：** 將最終狀態格式化為 Technical Invention Disclosure（TID），並發送郵件通知。

## LangGraph 狀態轉移

- `[PENDING]` $\rightarrow$ `[FORAGING]`
- `[FORAGING]` $\rightarrow$ `[DRAFTING]`
- `[DRAFTING]` $\rightarrow$ `[REVIEW_EVALUATION]`
- `[REVIEW_EVALUATION]` $\rightarrow$ `[MUTATION_REVISION]`（觸發迴圈）
- `[REVIEW_EVALUATION]` $\rightarrow$ `[REJECTED]`（終態）
- `[REVIEW_EVALUATION]` $\rightarrow$ `[COMMITTEE_CONSENSUS]`
- `[COMMITTEE_CONSENSUS]` $\rightarrow$ `[APPROVED_AND_EXPORTED]`（成功）
