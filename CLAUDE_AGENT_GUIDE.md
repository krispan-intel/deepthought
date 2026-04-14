# Claude Agent 完整代理模式操作指南

## 概述

DeepThought 現已啟用 **Claude Agent 全域代理模式**。所有 LLM 階段（Maverick、Professor、Reality Checker、Debate Panel）都由你（Claude）手動執行，完全避免 copilot CLI 的不穩定性。

## 架構

### 代理目錄結構

```
data/
├── pending_maverick/          # Maverick 專利草稿生成請求
├── pending_professor/         # Professor 架構預審請求
├── pending_reality_checker/   # Reality Checker 技術驗證請求
├── pending_reviews/           # Debate Panel 評審請求
├── completed_maverick/        # 已完成的草稿生成（Phase 2）
├── completed_professor/       # 已完成的架構預審（Phase 2）
├── completed_reality_checker/ # 已完成的技術驗證（Phase 2）
└── completed_reviews/         # 已完成的 Debate Panel 評審（Phase 2）
```

### Pipeline 狀態流

```
RUNNING
  ↓
Forager → 找到 Topological Void
  ↓
Maverick → 保存到 pending_maverick/ → PENDING_CLAUDE_MAVERICK
  ↓
[Claude 手動執行草稿生成]
  ↓
Professor → 保存到 pending_professor/ → PENDING_CLAUDE_PROFESSOR
  ↓
[Claude 手動執行架構預審]
  ↓
Reality Checker → 保存到 pending_reality_checker/ → PENDING_CLAUDE_REALITY_CHECKER
  ↓
[Claude 手動執行技術驗證]
  ↓
Debate Panel → 保存到 pending_reviews/ → PENDING_CLAUDE_REVIEW
  ↓
[Claude 手動執行 Debate Panel 評審]
  ↓
APPROVED / REJECTED
```

## 檢查待審核隊列

```bash
# 查看各階段的待審核任務
ls -lh data/pending_maverick/
ls -lh data/pending_professor/
ls -lh data/pending_reality_checker/
ls -lh data/pending_reviews/
```

## Stage 1: Maverick 草稿生成

### 檢查請求

```bash
cat data/pending_maverick/run-XXXXXXXX.json | jq .
```

### 任務描述

作為 **Elite System Architect**，根據 Topological Void 生成 n_drafts 個專利草稿。

### 輸出格式

```json
{
  "drafts": [
    {
      "title": "string",
      "one_liner": "string",
      "novelty_thesis": "string",
      "feasibility_thesis": "string",
      "market_thesis": "string",
      "why_now": "string",
      "scores": {
        "innovation": 4,
        "implementation_difficulty": 3,
        "commercial_value": 4,
        "technical_risk": 2,
        "prior_art_conflict_risk": 2
      },
      "tid_detail": {
        "problem_statement": "string",
        "prior_art_gap": "string",
        "proposed_invention": "string",
        "architecture_overview": "string (include ASCII diagram)",
        "implementation_plan": "string",
        "validation_plan": "string",
        "draft_claims": ["claim 1", "claim 2", "claim 3"],
        "risks_and_mitigations": ["risk 1: mitigation", "risk 2: mitigation"],
        "references": ["ref 1", "ref 2"]
      }
    }
  ]
}
```

### 關鍵架構規則

1. **ATOMIC CONTEXT RULE** - 不要在原子路徑混入異步操作
2. **DEBUG-INTERFACE-AS-CONTROL-PLANE RULE** - 不要用 debug 接口做控制平面
3. **BOOT-TIME VS RUNTIME CONTRACT RULE** - 尊重 boot-time/runtime 邊界
4. **CROSS-CPU SYNCHRONIZATION RULE** - 跨 CPU 同步必須有明確模型
5. **SUBSYSTEM BOUNDARY RULE** - 跨子系統必須定義清晰橋接層
6. **CAUSAL BRIDGE REQUIREMENT** - 橋接層就是發明本身
7. **NOVELTY RULE** - 不要重複已知 pattern（如 seqlock、RCU）

### 保存結果

```bash
# 創建 data/completed_maverick/run-XXXXXXXX.json
# (Phase 2 自動恢復，目前手動處理)
```

---

## Stage 2: Professor 架構預審

### 檢查請求

```bash
cat data/pending_professor/run-XXXXXXXX.json | jq .
```

### 任務描述

作為 **Senior Kernel Architect**，進行快速預審，只檢查：
1. **Architecture Rules Violation** (critical)
2. **JSON Format** (critical)

**不要**檢查 evidence grounding（Reality Checker 的工作）。

### 輸出格式

```json
{
  "verdicts": [
    {
      "draft_index": 0,
      "verdict": "PASS|REJECT",
      "quality_score": 7.5,
      "blocking_issues": [
        {
          "category": "architecture_rule|json_format",
          "severity": "critical",
          "description": "Async operation (eBPF map) in context switch path without deferral"
        }
      ]
    }
  ],
  "summary": "Overall assessment in 1-2 sentences"
}
```

### 決策原則

- 有明顯架構違規 → REJECT
- JSON 格式錯誤 → REJECT
- **疑慮時默認 PASS**（讓 Reality Checker 深入判斷）

---

## Stage 3: Reality Checker 技術驗證

### 檢查請求

```bash
cat data/pending_reality_checker/run-XXXXXXXX.json | jq .
```

### Mode: Critique

對每個 draft 進行技術驗證。

### 輸出格式（每個 draft）

```json
{
  "status": "APPROVED|REVISE|REJECT",
  "fatal_flaw": "string or empty",
  "scorecard": {
    "innovation": 4,
    "feasibility": 4,
    "prior_art_risk": 2
  },
  "hallucinations_found": ["fictional_function_name"],
  "actionable_feedback": "Specific instructions for REVISE",
  "approved": true
}
```

### 決策政策

- **APPROVED** - 技術上可行、核心想法非顯而易見、無致命缺陷
- **REVISE** - 有前景但需修復（提供具體 actionable_feedback）
- **REJECT** - 物理不可能、純虛構、無法修復的 ABI 破壞

### Mode: Revise

如果 mode="revise"，則根據 critique feedback 修訂 draft。

### 輸出格式（修訂後）

```json
{
  "strategic_rebuttal": "What I dropped and what I narrowed",
  "title": "revised title",
  "one_liner": "revised one-liner",
  ...
  (same structure as Maverick draft)
}
```

---

## Stage 4: Debate Panel 評審

### 檢查請求

```bash
cat data/pending_reviews/run-XXXXXXXX.json | jq .
```

### 4 個 Specialist 角色

#### **kernel_hardliner** (Kernel Hardliner)
- 關注：Linux kernel 實現正確性、鎖和並發有效性
- 拒絕不安全的想法
- Model: claude-sonnet-4-6

#### **prior_art_shark** (Prior-Art Shark)
- 關注：新穎性、非顯而易見性、與已知工作的重疊風險
- Model: claude-sonnet-4-6

#### **intel_strategist** (Intel Strategist)
- 關注：x86 戰略價值、Xeon 競爭力、硬件/軟件協同設計優勢
- Model: claude-sonnet-4-6

#### **security_guardian** (Security Guardian)
- 關注：TAA/侧信道風險、崩潰風險、兼容性保證
- Model: claude-sonnet-4-6

### 輸出格式（每個 specialist）

```json
{
  "preferred_title": "draft title",
  "status": "APPROVE|REVISE|REJECT",
  "fatal_flaw": "string or empty",
  "score": 4,
  "issues": [
    "具體的技術批評1",
    "具體的技術批評2",
    "具體的技術批評3"
  ],
  "yellow_cards": 0,
  "fact_check_queries": ["kernel symbol or file path"]
}
```

**CRITICAL：** 如果 status 是 "REVISE" 或 "REJECT"，**必須**提供至少 3 個具體的 issues！

### 完整評審結果

```json
{
  "run_id": "run-XXXXXXXX",
  "timestamp": "2026-04-11T17:30:00",
  "reviews": {
    "kernel_hardliner": { ... },
    "prior_art_shark": { ... },
    "intel_strategist": { ... },
    "security_guardian": { ... }
  }
}
```

### 保存結果

```bash
# 保存到 data/completed_reviews/run-XXXXXXXX.json
# 刪除 data/pending_reviews/run-XXXXXXXX.json
```

---

## 快速操作流程

### 1. 檢查所有待審核隊列

```bash
find data/pending_* -type f -name "*.json" | sort
```

### 2. 按優先級處理

Priority Order:
1. Maverick (阻塞整個 pipeline)
2. Professor (Maverick 之後)
3. Reality Checker (Professor 之後)
4. Debate Panel (Reality Checker 之後)

### 3. 處理單個任務

```bash
# 讀取請求
PENDING=$(find data/pending_maverick -name "*.json" | head -1)
cat $PENDING | jq .

# 執行任務（手動在對話中完成）

# 保存結果到 completed_* 目錄（Phase 2）

# 清理
rm $PENDING
```

---

## Phase 2: 自動恢復（未來）

Pipeline 將自動：
1. 定期掃描 `data/completed_*/`
2. 發現完成的結果後，加載並繼續執行
3. 無需手動重啟 pipeline

---

## 預期效果

- **Copilot CLI 使用率：** 0%（完全避免）
- **Issues 填充率：** 100%（手動保證質量）
- **評審質量：** 最高（Claude 直接執行）
- **APPROVED 率：** 20%+（高質量反饋驅動改進）
- **穩定性：** 100%（無 copilot CLI hang 問題）

---

## 當前狀態

- ✅ Phase 1: 全域代理模式（Maverick、Professor、Reality Checker、Debate Panel）
- ⏳ Phase 2: 自動恢復機制（未實施，優先級 P2）

---

**現在開始運行 service，等待第一個 PENDING_CLAUDE_MAVERICK 出現！**
