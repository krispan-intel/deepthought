# 🚀 DeepThought Onboarding BKM — AI 引导式部署

将 TVA 部署到新领域最快的方式，是让 AI agent 互动式地引导你。不需要手动读文档——把下面的 prompt 贴进 **Claude**、**Copilot** 或任何有能力的 LLM，agent 会问你正确的问题，并一步一步帮你生成配置。

---

## 主引导 Prompt

将以下内容贴入 Claude 或 Copilot，开始引导流程：

```
你是一位 TVA Domain Deployment Advisor，正在帮我为新领域部署 DeepThought 发明探索系统。

DeepThought 使用拓扑空洞分析（TVA）在技术知识语料库中寻找未开拓的创新缺口，并生成可交律师使用的技术发明披露文件（TID）。部署分三个步骤：
  步骤零 — 建立领域语料库（收集、清理、分块、嵌入文件）
  步骤一 — 配置四个 Debate Panel Specialist 角色进行对抗审查
  步骤二 — 重新校准边际带 [τ_low, τ_high]（导入后自动完成）

你的任务是互动式地引导我完成这三个步骤。

请依次问我以下问题，一次一个：
1. 我的技术领域是什么？（例如：生医、汽车、编译器、材料科学）
2. 我的主要创新目标或目标领域是什么？
3. 我有哪些类型的文件或数据来源？（代码库、PDF、专利、论文、视频等）
4. 审查 Specialist 应了解哪些组织或平台背景？

根据我的回答：
- 推荐语料库收集与分块策略
- 生成领域专属停用词清单（50–100 个 token）
- 设计四个 Debate Panel Specialist 角色，附完整 system prompt
- 提供针对我领域执行 DeepThought 的确切 CLI 指令

一次问一个问题，等我回答后再继续。
```

---

## 步骤专属 Prompt

如果你已有语料库，只需要某个特定部分，可使用以下聚焦 prompt。

### 生成 Debate Panel Specialist

```
我正在为以下领域部署 DeepThought TVA 系统：

领域：[你的领域]
创新目标：[你想要发明什么]
组织背景：[你的公司 / 平台 / 法规环境]

请为这个领域的技术发明披露文件对抗审查，设计四个 Debate Panel Specialist 角色。
参考 [相关会议，例如 NeurIPS / PLDI / SAE] 的审查规范——严格、领域专属、视角不重叠。

对每个 Specialist 请提供：
1. 角色名称与一句话说明
2. 完整 system prompt（3–5 项评估标准，verdict 格式：APPROVE / REVISE / REJECT）
3. 哪类致命缺陷应立即触发 REJECT

确保：至少一个角色涵盖先前技术新颖性审查。每个角色视角明确且不重叠。
```

---

### 生成语料库计划

```
我想为以下领域建立 TVA 知识语料库：

领域：[你的领域]
可用来源：[列出你有的资源——PDF、git repo、论文、标准文档、视频等]
规模目标：[大约多少份文件]

请给我：
1. 优先导入哪些来源（信噪比最高）
2. 每种来源类型的建议分块策略
3. 领域专属停用词清单（50–100 个到处出现但无判别意义的 token）
4. 质量验证计划——健康语料库的 cosine 相似度分布应该长什么样？
```

---

### 诊断失败的 Pipeline

```
我的 DeepThought pipeline 运行失败或结果很差，请帮我诊断。

领域：[你的领域]
症状：[例如：所有 void 都被 reject、找不到 void、Debate Panel 总是 reject、校准失败]
语料库大小：[文件数量]
错误或 log 片段：[粘贴相关输出]

请带我做系统性诊断：语料库质量 → 阈值校准 → Specialist prompt 质量 → LLM 输出格式。
```

---

## 使用建议

- **Claude Opus** 生成的 Specialist prompt 和语料库计划最为详尽。
- **Copilot** 适合已在 GitHub 工作流中的快速语料库规划。
- 即使你觉得已经了解自己的领域，也建议先跑主引导 prompt——问题会暴露你可能忽略的假设。
- 生成的 Specialist prompt 可直接贴入 `agents/debate_panel.py` 的 specialist 定义中。
- 停用词清单：用上方 prompt 生成候选清单后，再对照你的实际稀疏 token 频率验证（对 FTS5 index 跑 `Counter`）。

---

*另见：[VECTORDB_GUIDE.zh-CN.md](VECTORDB_GUIDE.zh-CN.md) 语料库完整准备流程。*
