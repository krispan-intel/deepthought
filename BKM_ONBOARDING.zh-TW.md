# 🚀 DeepThought Onboarding BKM — AI 引導式部署

將 TVA 部署到新領域最快的方式，是讓 AI agent 互動式地引導你。不需要手動讀文件——把下面的 prompt 貼進 **Claude**、**Copilot** 或任何有能力的 LLM，agent 會問你正確的問題，並一步一步幫你生成配置。

---

## 主引導 Prompt

將以下內容貼入 Claude 或 Copilot，開始引導流程：

```
你是一位 TVA Domain Deployment Advisor，正在幫我為新領域部署 DeepThought 發明探索系統。

DeepThought 使用拓撲空洞分析（TVA）在技術知識語料庫中尋找未開拓的創新缺口，並生成可交律師使用的技術發明揭露文件（TID）。部署分三個步驟：
  步驟零 — 建立領域語料庫（收集、清理、分塊、嵌入文件）
  步驟一 — 配置四個 Debate Panel Specialist 角色進行對抗審查
  步驟二 — 重新校準邊際帶 [τ_low, τ_high]（匯入後自動完成）

你的任務是互動式地引導我完成這三個步驟。

請依序問我以下問題，一次一個：
1. 我的技術領域是什麼？（例如：生醫、汽車、編譯器、材料科學）
2. 我的主要創新目標或目標領域是什麼？
3. 我有哪些類型的文件或資料來源？（程式碼庫、PDF、專利、論文、影片等）
4. 審查 Specialist 應了解哪些組織或平台背景？

根據我的回答：
- 推薦語料庫收集與分塊策略
- 生成領域專屬停用詞清單（50–100 個 token）
- 設計四個 Debate Panel Specialist 角色，附完整 system prompt
- 提供針對我領域執行 DeepThought 的確切 CLI 指令

一次問一個問題，等我回答後再繼續。
```

---

## 步驟專屬 Prompt

如果你已有語料庫，只需要某個特定部分，可使用以下聚焦 prompt。

### 生成 Debate Panel Specialist

```
我正在為以下領域部署 DeepThought TVA 系統：

領域：[你的領域]
創新目標：[你想要發明什麼]
組織背景：[你的公司 / 平台 / 法規環境]

請為這個領域的技術發明揭露文件對抗審查，設計四個 Debate Panel Specialist 角色。
參考 [相關會議，例如 NeurIPS / PLDI / SAE] 的審查規範——嚴格、領域專屬、視角不重疊。

對每個 Specialist 請提供：
1. 角色名稱與一句話說明
2. 完整 system prompt（3–5 項評估標準，verdict 格式：APPROVE / REVISE / REJECT）
3. 哪類致命缺陷應立即觸發 REJECT

確保：至少一個角色涵蓋先前技術新穎性審查。每個角色視角明確且不重疊。
```

---

### 生成語料庫計畫

```
我想為以下領域建立 TVA 知識語料庫：

領域：[你的領域]
可用來源：[列出你有的資源——PDF、git repo、論文、標準文件、影片等]
規模目標：[大約多少份文件]

請給我：
1. 優先匯入哪些來源（信噪比最高）
2. 每種來源類型的建議分塊策略
3. 領域專屬停用詞清單（50–100 個到處出現但無判別意義的 token）
4. 品質驗證計畫——健康語料庫的 cosine 相似度分佈應該長什麼樣？
```

---

### 診斷失敗的 Pipeline

```
我的 DeepThought pipeline 執行失敗或結果很差，請幫我診斷。

領域：[你的領域]
症狀：[例如：所有 void 都被 reject、找不到 void、Debate Panel 總是 reject、校準失敗]
語料庫大小：[文件數量]
錯誤或 log 片段：[貼上相關輸出]

請帶我做系統性診斷：語料庫品質 → 閾值校準 → Specialist prompt 品質 → LLM 輸出格式。
```

---

## 數學 / 實現細節問題

如果你有關於 TVA 數學的問題（SLERP 公式、邊際帶校準、vacancy probe 閾值、C1–C4 條件），請先把 [PAPER.zh-TW.md](PAPER.zh-TW.md) 的相關章節貼進 Claude/Copilot 的對話，再提問。AI 會從論文回答——不需要聯絡作者。

```
# 如何取得詳細技術解答：
# 1. 開啟 PAPER.zh-TW.md
# 2. 複製相關章節（例如「自適應閾值校準」）
# 3. 貼入 Claude/Copilot 並提問
```

## 使用建議

- **Claude Opus** 生成的 Specialist prompt 和語料庫計畫最為詳盡。
- **Copilot** 適合已在 GitHub 工作流中的快速語料庫規劃。
- 即使你覺得已經了解自己的領域，也建議先跑主引導 prompt——問題會暴露你可能忽略的假設。
- 生成的 Specialist prompt 可直接貼入 `agents/debate_panel.py` 的 specialist 定義中。
- 停用詞清單：用上方 prompt 生成候選清單後，再對照你的實際稀疏 token 頻率驗證（對 FTS5 index 跑 `Counter`）。

---

*另見：[VECTORDB_GUIDE.zh-TW.md](VECTORDB_GUIDE.zh-TW.md) 語料庫完整準備流程。*
