# 🗄️ 为 TVA 建立高质量向量数据库

本指南说明如何建立一个 DeepThought 可用于搜索拓扑空洞的知识语料库。同样的方法适用于**任何技术领域**——不只是 Linux kernel。

---

## 目标

TVA 需要一个满足以下条件的语料库：
1. **每份文件都有有意义的 embedding** — 无噪音、无样板、无重复
2. **稀疏 token 具备领域专属性** — 过滤停用词，保留技术术语
3. **覆盖广泛但聚焦** — 你要的是知识空间的**边界**，而非只是中心

把它想成建一张地图。好地图有清晰的边缘，那里才是未探索领域的起点。

---

## 第 1 步：确定你的领域

在收集任何东西之前，先回答这些问题：

| 问题 | 范例（Linux/x86） | 你的领域 |
|---|---|---|
| 核心产物是什么？ | kernel 源代码 | 你的代码库、规格文档 |
| 先前技术在哪里？ | 论文、专利 | 学术论文、标准文档 |
| 目标硬件/平台是什么？ | x86 ISA、Intel SDM | 你的平台规格 |
| "新颖性"的定义是什么？ | kernel 子系统边界 | 你的领域子系统地图 |

**领域边界比完整性更重要。** 5 万份高质量的领域专属文件，胜过 50 万份噪音文件。

---

## 第 2 步：输入格式 → 工具选择

| 输入格式 | 内容类型 | 推荐工具 | 备注 |
|---|---|---|---|
| **Git repository** | 源代码、commit 历史 | `GitPython`、`PyDriller` | 使用 tree-sitter 做 AST 解析 |
| **PDF** | 论文、规格、手册 | `PyMuPDF`（`fitz`）、`pdfplumber` | 提取文字并处理数学符号 |
| **HTML / Web** | 文档、wiki、博客 | `BeautifulSoup`、`Playwright` | 遵守 robots.txt |
| **arXiv / Semantic Scholar** | 学术论文 | arXiv API、S2 API | 免费、有结构化 metadata |
| **USPTO / EPO** | 专利 | USPTO bulk data、EPO OPS API | 只使用 claim 文字 |
| **邮件列表 / 论坛** | LKML、GitHub Issues | 自定义爬虫 | 积极过滤噪音 |
| **Markdown / RST** | 文档、README | `mistune`、`docutils` | 信噪比高 |
| **Jupyter Notebooks** | 研究代码 | `nbformat` | 提取 markdown cells + 代码 |
| **CSV / JSON / JSONL** | 结构化数据 | pandas / 原生 | 展平成文字字段 |
| **视频** | 讲座、会议演讲、教程 | `yt-dlp` + Whisper（OpenAI）| 先转录为文字，再走文字 pipeline；章节时间戳可作为分块边界 |
| **音频** | Podcast、访谈、录音 | `openai-whisper`、`faster-whisper` | 说话人分离（`pyannote-audio`）可提升分块质量 |

---

## 第 3 步：分块策略

**错误的分块会毁掉 embedding。** 错误的 chunk 大小意味着你的向量代表的是噪音，而非概念。

| 文件类型 | 分块策略 | 建议大小 |
|---|---|---|
| 源代码 | 函数/类边界（tree-sitter AST） | 1 个函数 = 1 个 chunk |
| 学术论文 | 章节层级 | ~500–1000 tokens |
| 硬件规格（PDF） | 表格 + 周围段落 | ~300–500 tokens |
| Commit messages | 完整信息 | 原样 |
| 专利 | Claim 1 + 摘要 | ~200–400 tokens |
| 邮件列表讨论串 | 单封邮件，去除引用 | ~200–500 tokens |
| 视频/音频转录 | 按说话停顿或章节标记分割 | ~300–600 tokens |

**原则：** 一个 chunk = 一个概念。如果一个 chunk 涵盖 3 个不相关的主题，请拆分它。

---

## 第 4 步：Embedding 模型选择

| 模型 | 维度 | 使用时机 | 备注 |
|---|---|---|---|
| **BGE-M3**（我们使用的） | 1024D dense + sparse | 技术多语言 | 最适合代码 + 散文混合 |
| `text-embedding-3-large`（OpenAI） | 3072D | 通用文字、高质量 | API 费用，无稀疏向量 |
| `nomic-embed-text` | 768D | 轻量本地 | 适合纯散文 |
| `codet5p-110m-embedding` | 256D | 纯代码 | 对 TVA 而言太窄 |
| `multilingual-e5-large` | 1024D | 多语言 | BGE-M3 的替代方案 |

**TVA 专用：** 使用 BGE-M3。稀疏权重对于 Sparse Lexical Bridge 条件（C3）至关重要。

---

## 第 5 步：清理 Pipeline

```
原始文件
    │
    ▼
① 语言过滤     （保留英文 + 你的目标语言）
    │
    ▼
② 去重复       （内容的 minhash LSH 或精确哈希）
    │
    ▼
③ 长度过滤     （丢弃 < 50 tokens、> 2000 tokens）
    │
    ▼
④ 噪音过滤     （丢弃自动生成、样板、测试 fixture）
    │
    ▼
⑤ 领域相关性  （可选：与种子文件的 embedding 相似度）
    │
    ▼
⑥ 分块         （依文件类型，见上表）
    │
    ▼
⑦ Embedding    （BGE-M3 本地，batch size 32–64）
    │
    ▼
⑧ 建索引       （< 100 万文件用 FAISS flat，> 100 万用 HNSW）
    │
    ▼
高质量向量数据库 ✓
```

---

## 第 6 步：领域停用词清单

TVA 在计算 Sparse Lexical Bridge 之前会过滤掉通用 token。你需要一份领域专属的停用词清单。

**Linux kernel（内置）：**
```python
KERNEL_STOP_WORDS = {
    "define", "include", "struct", "int", "void", "static", "return",
    "linux", "kernel", "core", "sys", "device", "driver", "memory", ...
}
```

**你的领域：** 新增 50–100 个出现在所有地方但没有判别意义的最高频 token。对所有稀疏 token 跑 `Counter`，取前 200 个，手动移除那些确实具有领域专属意义的。

---

## 第 7 步：质量检查

执行 TVA 之前，验证你的语料库：

```python
# 检查 embedding 质量
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# 抽样 1000 个随机配对 — 分布应以 ~0.3-0.6 为中心
# 如果太多配对 > 0.9：语料库太同质（不好）
# 如果太多配对 < 0.1：语料库太噪杂（不好）
sample = np.random.choice(embeddings, 1000)
sims = cosine_similarity(sample)
print(f"Mean similarity: {sims.mean():.3f}")  # 目标：0.3-0.5
print(f"Std: {sims.std():.3f}")              # 目标：> 0.15
```

---

## 第 7b 步：选择正确的嵌入维度

不要靠猜测选择嵌入维度。执行 TVA 维度分析，找出你语料库的数学最优维度 `D*`。

### TVA 维度定律

基于语料库特征值频谱的幂次衰减与 Johnson-Lindenstrauss 噪音惩罚：

$$D^* = \left[\frac{\gamma \cdot \ln N}{k \cdot (1 - D_{LLM}^{-\gamma})}\right]^{\frac{1}{\gamma+1}}$$

其中：
- `γ` = 语料库的幂次衰减指数（由 SVD 测量，γ = α − 1）
- `N` = 语料库文件总数
- `k` = 噪音容忍常数（默认 0.001，可从对抗审查 reject 率校准）
- `D_LLM` = 前沿 LLM 维度假设（默认 12288）

### 执行分析

```bash
# 默认：kernel_source collection，1 万条样本
python scripts/run_dimension_analysis.py

# 指定不同 collection 或更大样本
python scripts/run_dimension_analysis.py --collection papers --sample 20000

# 若对抗审查 reject 太多（调高 k）或太少（调低 k）
python scripts/run_dimension_analysis.py --k 0.002
```

### 解读结果

| γ 值 | 语料库类型 | 典型 D* |
|---|---|---|
| γ < 0.1 | 广泛混合领域语料库 | 768–1024+ |
| γ 0.1–0.4 | 聚焦技术领域 | 512–768 |
| γ > 0.4 | 高度专精（单一子领域） | 256–512 |

**真实范例（Linux kernel + 硬件 + 论文，N=149k）：**
```
α = 1.069,  γ = 0.069,  R² = 0.929

  D    | R(D) 理论  | 实际方差   | 边际增益
  768  |    77.0%  |   99.7%   |  +1.7%
  1024 |    79.6%  |  100.0%   |  +1.2%
  3072 |    89.1%  |    —      |  +9.5%  (3 倍成本，不划算)

  D* = 1063  →  最近标准维度：1024D  ✅
```

**关键洞察：** D* 确定后，继续增加维度收益递减。在此语料库中，从 1024D 升级到 3072D（`text-embedding-3-large`）计算成本增加 3 倍，理论解析度增益仅 +9.5%。

---

## 领域范例

| 领域 | 核心来源 | 需额外新增的停用词 |
|---|---|---|
| **Linux kernel**（我们的使用案例） | torvalds/linux、LKML、Intel SDM | `mutex`、`spinlock`、`cpu`、`irq` |
| **生医** | PubMed、PDB、UniProt | `patient`、`study`、`method`、`result` |
| **材料科学** | Materials Project、ICSD、论文 | `material`、`sample`、`measured`、`Fig` |
| **汽车** | AUTOSAR 规格、ISO 26262、MISRA | `shall`、`system`、`function`、`module` |
| **金融** | SEC 文件、财报电话、论文 | `company`、`period`、`million`、`percent` |
| **编译器/PL** | LLVM、GCC 源代码、PLDI 论文 | `pass`、`node`、`type`、`value` |

---

## 实用资源

### Embedding 与向量数据库
| 资源 | URL | 你将学到什么 |
|---|---|---|
| BGE-M3 论文 | https://arxiv.org/abs/2309.07597 | Dense-sparse 双重 embedding |
| FAISS 文档 | https://faiss.ai | 十亿规模相似度搜索 |
| ChromaDB | https://docs.trychroma.com | 简单的本地向量数据库 |
| Qdrant | https://qdrant.tech/documentation | 生产就绪，支持过滤 |
| Weaviate | https://weaviate.io/developers/weaviate | 图 + 向量混合 |

### 数据收集
| 资源 | URL | 你将学到什么 |
|---|---|---|
| arXiv API | https://arxiv.org/help/api | 免费论文访问 |
| Semantic Scholar | https://api.semanticscholar.org | 引用图 + 摘要 |
| USPTO 批量数据 | https://bulkdata.uspto.gov | 专利全文 |
| PyDriller | https://github.com/ishepard/pydriller | Git 历史挖掘 |
| tree-sitter | https://tree-sitter.github.io | 语言无关的 AST 解析 |

### 分块与处理
| 资源 | URL | 你将学到什么 |
|---|---|---|
| LangChain text splitters | https://python.langchain.com/docs/modules/data_connection/document_transformers | 分块策略 |
| LlamaIndex ingestion | https://docs.llamaindex.ai | 端到端 RAG pipeline |
| PyMuPDF | https://pymupdf.readthedocs.io | PDF 提取 |

### 视频 / 音频转录
| 资源 | URL | 你将学到什么 |
|---|---|---|
| OpenAI Whisper | https://github.com/openai/whisper | 本地语音转文字（多语言） |
| faster-whisper | https://github.com/SYSTRAN/faster-whisper | Whisper 的 CTranslate2 加速版本 |
| yt-dlp | https://github.com/yt-dlp/yt-dlp | 下载 YouTube / 会议视频 |
| pyannote-audio | https://github.com/pyannote/pyannote-audio | 说话人分离（diarization） |
| WhisperX | https://github.com/m-bain/whisperX | Whisper + 对齐 + diarization 一体化 |

---

## 第 7.5 步：写你的 Anchor C（意图向量）

执行 TVA 之前，你需要一件事：一个**目标短语**。这就是你的 Anchor C——发明者的意图向量。

**它是什么：** 一句描述你想在哪里创新的句子。TVA 将这句话嵌入与语料库相同的向量空间，然后找到指向那个方向的空洞。

**它不是什么：** 关键词、搜索查询，或某份具体文件。你不是在搜索已存在的东西——你在知识空间中声明一个方向。

> TVA 论文中列举的 96 个 target 只是为了可重现性。实际上，你只需要一句话。

### 什么是好的 Anchor C

| | 太窄 | 太宽 | 刚刚好 |
|---|---|---|---|
| **Linux kernel** | `"优化调度器 runqueue 的 spinlock 竞争"` | `"改善 Linux 性能"` | `"在高核心数 x86 系统中降低调度器延迟"` |
| **生医** | `"降低 NLRP3 通路中的 IL-6 细胞因子"` | `"治愈炎症"` | `"能穿越血脑屏障的神经炎症新型小分子靶点"` |
| **材料科学** | `"提高 Al₂O₃ 在 1200°C 的断裂韧性"` | `"更好的电池材料"` | `"低阻抗、高热稳定性的固态电池固态电解质界面"` |
| **汽车** | `"SOME/IP 中 AUTOSAR SWC 的超时处理"` | `"更安全的汽车"` | `"ASIL-D 汽车 ECU 无线更新验证的功能安全机制"` |
| **编译器** | `"内联后消除冗余 store 指令"` | `"更快的编译"` | `"降低短生命周期服务器工作负载 JIT 预热延迟的技术"` |
| **云端/基础设施** | `"降低丢包情况下 gRPC keepalive 的尾延迟"` | `"更快的云端"` | `"部分网络分区下地理分散有状态微服务的低延迟共识协议"` |

**太窄：** TVA 几乎找不到空洞——你已经定义了解法，而非方向。  
**太宽：** TVA 找到太多不相关的空洞——向量没有判别力。  
**刚刚好：** 具体到足以有意义地嵌入，又足够开放以发现非显而易见的连接。

### TVA 论文中的真实范例

这些是产生两个案例研究的 target：

**案例研究 1 — TSX-Advisory MGLRU 旋转胶囊：**
> `"memory reclamation latency optimisation for high-core-count x86 systems"`

TVA 发现了空洞 #2：一篇乐观内存回收论文（概念 A）× 一份存储技术比率研究（概念 B）。稀疏桥接 token `reclamation` 将它们连接。没有人会搜索这个配对——TVA 发现它，是因为两者都指向意图向量的方向。

**案例研究 2 — 验证器衍生的同步契约：**
> `"eBPF JIT correctness and synchronisation on x86"`

TVA 发现了空洞 #5：`ELF_MACHINE_NAME`（ELF 可移植性宏）× `addend_may_be_ifunc`（链接器重定位谓词）。余弦相似度 0.64——相关但非显而易见。由此产生的想法（每位点同步契约向量）与两个来源概念都没有表面联系。

### 关键洞察

> Anchor C 是方向，不是目的地。TVA 不是找*关于*你意图的文件——它找的是**附近未探索的空间**。一个较弱、较间接的 target，往往比精确的目标发现更有趣的空洞。

---

## 第 8 步：配置你的 Debate Panel

语料库准备好之后，唯一需要手动配置的是对抗审查委员会的**四个 Specialist 角色**。就像为一个领域会议挑选程序委员会一样：你需要能从不同角度挑战想法的审查者——技术正确性、新颖性、策略价值，以及风险。

目前 Linux/x86 的阵容是：

| 角色 | 审查焦点 |
|---|---|
| Kernel Hardliner | 实现正确性、ABI 约束、锁机制 |
| Prior-Art Shark | 新颖性、非显而易见性、与已知技术的重叠 |
| Intel Strategist | 平台策略契合度、HW/SW 协同设计价值 |
| Security Guardian | 安全性与隐私风险 |

**Prior-Art Shark** 与**安全/安全性**角色具有普遍适用性——每个领域都保留它们。其他两个应反映你领域的技术与组织现实。

### 领域范例

**生医 / 药物发现**
参考 NeurIPS / Nature Medicine 审查规范：科学严谨性 + 安全性优先。

| 角色 | 审查焦点 |
|---|---|
| Clinical Researcher | 临床可行性、患者安全、FDA/EMA 申请路径 |
| Drug-Safety Expert | 毒理学、脱靶效应、禁忌症 |
| Prior-Art Shark | 专利格局、已发表先前技术 |
| Regulatory Specialist | GxP 法规合规、标示、试验设计要求 |

---

**材料科学**
参考 Nature Materials / ICMSE 审查：可重现性 + 可制造性。

| 角色 | 审查焦点 |
|---|---|
| Materials Physicist | 热力学可行性、DFT/实验一致性 |
| Manufacturing Engineer | 可扩展性、工艺集成、良率问题 |
| Prior-Art Shark | 专利与文献重叠 |
| IP Counsel | 自由实施、权利要求范围 |

---

**汽车软件（AUTOSAR / ISO 26262）**
参考 SAE / AUTOSAR 技术审查：安全完整性 + 标准合规。

| 角色 | 审查焦点 |
|---|---|
| Functional Safety Engineer | ASIL 分解、FMEA、安全目标可追溯性 |
| AUTOSAR Architect | BSW/RTE 集成、ARXML 合规、时序 |
| Prior-Art Shark | 相对于现有 AUTOSAR 扩展、SAE 论文的新颖性 |
| Cybersecurity Expert | EVITA/TARA 威胁建模、ISO 21434 |

---

**编译器 / 编程语言**
参考 PLDI / POPL 程序委员会：形式正确性 + 性能。

| 角色 | 审查焦点 |
|---|---|
| Compiler Engineer | IR 正确性、别名分析、未定义行为 |
| Language Theorist | 类型系统健全性、形式语义 |
| Prior-Art Shark | 与 LLVM/GCC patch、学术发表的重叠 |
| Performance Architect | 性能基准退化风险、codegen 质量 |

---

**企业 / 云基础设施**
参考 SOSP / OSDI 审查：故障下的正确性 + 运维成本。

| 角色 | 审查焦点 |
|---|---|
| Distributed Systems Engineer | 一致性模型、故障模式、CAP 权衡 |
| SRE / Operations | 运维复杂性、爆炸半径、回滚策略 |
| Prior-Art Shark | AWS/GCP/Azure 专利格局、开源先前技术 |
| Security Guardian | 供应链风险、零信任、数据驻留 |

---

### Prompt 模板

为每个 Specialist 提供如下形式的一段 system prompt：

```
你是 [角色名称]。你的关注点是 [领域 + 视角]。
在审查技术发明披露文件时，你评估：
- [此角色专属的评估标准 1]
- [此角色专属的评估标准 2]
- [此角色专属的评估标准 3]
回应格式：verdict（APPROVE / REVISE / REJECT）、一句话理由，
若为 REVISE 则附上一项具体必要修改。
```

Claude 或任何有能力的 LLM 都能帮你起草这些 prompt，只要你描述你的领域即可。关键是每个 Specialist 应有**明确且不重叠的审查视角**——如果两个审查者会说同样的话，合并它们或替换其中一个。

---

## 快速开始（任何领域）

```bash
# 1. Clone DeepThought
git clone <this repo>
cd deepthought

# 2. 将你的文件加入 data/raw/your_domain/

# 3. 撰写简单的导入脚本（参考 scripts/ingest_kernel.py 作为模板）
python scripts/ingest_kernel.py --subsystem your_domain

# 4. 验证语料库质量
python scripts/run_forager_probe.py --target "your intent here"

# 5. 执行 TVA
python scripts/run_pipeline_service.py \
    --target "your innovation intent" \
    --collection your_domain \
    --auto-target
```

---

*开 issue 之前，请先试试 [AI 引导式 Onboarding →](BKM_ONBOARDING.zh-CN.md) — Claude 或 Copilot 能互动式地回答大多数领域适应问题。自己动手，丰衣足食。*
