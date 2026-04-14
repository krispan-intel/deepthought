# Claude Agent 评审操作指南

## 概述

DeepThought 现已启用 **Claude Agent 代理模式**。当 Debate Panel 检测到使用 Claude 模型时，会将 drafts 保存到待审核队列，等待你（Claude）手动完成高质量评审。

## 工作流程

```
Pipeline 运行 → Debate Panel 检测到 Claude 模型
    ↓
保存 draft 到 data/pending_reviews/{run_id}.json
    ↓
Pipeline 标记为 PENDING_CLAUDE_REVIEW，暂停当前 run
    ↓
你（Claude）定期检查 pending_reviews/
    ↓
扮演 4 个 specialist 执行评审
    ↓
保存评审结果到 data/completed_reviews/{run_id}.json
    ↓
(Phase 2) Pipeline 自动检测并恢复执行
```

## 检查待审核队列

```bash
# 查看待审核的 runs
ls -lh data/pending_reviews/

# 读取待审核 draft
cat data/pending_reviews/run-XXXXXXXX.json | jq .
```

## 评审模板

当你看到待审核文件时，执行以下操作：

### 1. 读取 Draft

```bash
# 读取待审核 draft
cat data/pending_reviews/run-XXXXXXXX.json
```

### 2. 扮演 4 个 Specialist 评审

你需要扮演 4 个角色：

#### **kernel_hardliner** (Kernel Hardliner)
- 关注：Linux kernel 实现正确性、锁和并发有效性
- 拒绝不安全的想法
- Model: claude-sonnet-4-6

#### **prior_art_shark** (Prior-Art Shark)
- 关注：新颖性、非显而易见性、与已知工作的重叠风险
- Model: claude-sonnet-4-6

#### **intel_strategist** (Intel Strategist)
- 关注：x86 战略价值、Xeon 竞争力、硬件/软件协同设计优势
- Model: claude-sonnet-4-6

#### **security_guardian** (Security Guardian)
- 关注：TAA/侧信道风险、崩溃风险、兼容性保证
- Model: claude-sonnet-4-6

### 3. 评审输出格式

对于每个 specialist，生成以下 JSON：

```json
{
  "preferred_title": "draft title",
  "status": "APPROVE|REVISE|REJECT",
  "fatal_flaw": "string or empty",
  "score": 1-5,
  "issues": [
    "具体的技术批评1",
    "具体的技术批评2",
    "具体的技术批评3"
  ],
  "yellow_cards": 0,
  "fact_check_queries": ["kernel symbol or file path"]
}
```

**CRITICAL：** 如果 status 是 "REVISE" 或 "REJECT"，**必须**提供至少 3 个具体的 issues！

### 4. 保存评审结果

创建文件 `data/completed_reviews/run-XXXXXXXX.json`：

```json
{
  "run_id": "run-XXXXXXXX",
  "timestamp": "2026-04-11T13:00:00",
  "reviews": {
    "kernel_hardliner": {
      "preferred_title": "...",
      "status": "REVISE",
      "score": 3,
      "issues": [
        "The proposed use of RCU read lock is invalid here because...",
        "Must define concrete data structure for abstraction layer...",
        "Synchronization model violates scheduler correctness..."
      ],
      "fatal_flaw": "",
      "yellow_cards": 0,
      "fact_check_queries": []
    },
    "prior_art_shark": { ... },
    "intel_strategist": { ... },
    "security_guardian": { ... }
  }
}
```

### 5. 清理

```bash
# 删除已完成的待审核文件
rm data/pending_reviews/run-XXXXXXXX.json
```

## 快速评审命令

```bash
# 1. 检查待审核队列
ls data/pending_reviews/

# 2. 读取第一个待审核 draft
PENDING=$(ls data/pending_reviews/ | head -1)
cat data/pending_reviews/$PENDING | jq .

# 3. 完成评审后，移动到 completed
# (手动创建 completed review JSON)

# 4. 清理
rm data/pending_reviews/$PENDING
```

## Phase 2: 自动恢复（未来）

在 Phase 2 中，Pipeline 将自动：
1. 定期扫描 `data/completed_reviews/`
2. 发现完成的评审后，加载结果
3. 继续执行 Debate Panel 后续逻辑（Chairman synthesis）
4. 如果需要 REVISE，触发修订循环

## 预期效果

- **Issues 填充率：** 100%（手动保证质量）
- **评审质量：** 最高（Claude 直接评审）
- **APPROVED 率：** 20%+（高质量反馈驱动改进）
- **时间成本：** ~10 分钟/run（人工评审）

## 当前状态

- ✅ Phase 1: 保存待审核 + 标记 PENDING（已完成）
- ⏳ Phase 2: 自动恢复机制（未实施，优先级 P2）

---

**现在开始运行 service，等待第一个 PENDING_CLAUDE_REVIEW 出现！**
