# 🗄️ 為 TVA 建立高品質向量資料庫

本指南說明如何建立一個 DeepThought 可用來搜尋拓撲空洞的知識語料庫。同樣的方法適用於**任何技術領域**——不只是 Linux kernel。

---

## 目標

TVA 需要一個滿足以下條件的語料庫：
1. **每份文件都有有意義的 embedding** — 無噪音、無樣板、無重複
2. **稀疏 token 具備領域專屬性** — 過濾停用詞，保留技術術語
3. **覆蓋廣泛但聚焦** — 你要的是知識空間的**邊界**，而非只是中心

把它想成建一張地圖。好地圖有清晰的邊緣，那裡才是未探索領域的起點。

---

## 第 1 步：確定你的領域

在收集任何東西之前，先回答這些問題：

| 問題 | 範例（Linux/x86） | 你的領域 |
|---|---|---|
| 核心產物是什麼？ | kernel 原始碼 | 你的程式碼庫、規格文件 |
| 先前技術在哪裡？ | 論文、專利 | 學術論文、標準文件 |
| 目標硬體/平台是什麼？ | x86 ISA、Intel SDM | 你的平台規格 |
| 「新穎性」的定義是什麼？ | kernel 子系統邊界 | 你的領域子系統地圖 |

**領域邊界比完整性更重要。** 5 萬份高品質的領域專屬文件，勝過 50 萬份噪音文件。

---

## 第 2 步：輸入格式 → 工具選擇

| 輸入格式 | 內容類型 | 推薦工具 | 備註 |
|---|---|---|---|
| **Git repository** | 原始碼、commit 歷史 | `GitPython`、`PyDriller` | 使用 tree-sitter 做 AST 解析 |
| **PDF** | 論文、規格、手冊 | `PyMuPDF`（`fitz`）、`pdfplumber` | 提取文字並處理數學符號 |
| **HTML / Web** | 文件、wiki、部落格 | `BeautifulSoup`、`Playwright` | 遵守 robots.txt |
| **arXiv / Semantic Scholar** | 學術論文 | arXiv API、S2 API | 免費、有結構化 metadata |
| **USPTO / EPO** | 專利 | USPTO bulk data、EPO OPS API | 只使用 claim 文字 |
| **郵件列表 / 論壇** | LKML、GitHub Issues | 客製爬蟲 | 積極過濾噪音 |
| **Markdown / RST** | 文件、README | `mistune`、`docutils` | 信噪比高 |
| **Jupyter Notebooks** | 研究程式碼 | `nbformat` | 提取 markdown cells + 程式碼 |
| **CSV / JSON / JSONL** | 結構化資料 | pandas / 原生 | 攤平成文字欄位 |
| **視頻** | 講座、會議演講、教學影片 | `yt-dlp` + Whisper（OpenAI） | 先轉錄為文字，再走文字 pipeline；章節時間戳可作為分塊邊界 |
| **音頻** | Podcast、訪談、錄音 | `openai-whisper`、`faster-whisper` | 說話者分離（`pyannote-audio`）可提升分塊品質 |

---

## 第 3 步：分塊策略

**錯誤的分塊會毀掉 embedding。** 錯誤的 chunk 大小意味著你的向量代表的是噪音，而非概念。

| 文件類型 | 分塊策略 | 建議大小 |
|---|---|---|
| 原始碼 | 函數/類別邊界（tree-sitter AST） | 1 個函數 = 1 個 chunk |
| 學術論文 | 章節層級 | ~500–1000 tokens |
| 硬體規格（PDF） | 表格 + 周圍段落 | ~300–500 tokens |
| Commit messages | 完整訊息 | 原樣 |
| 專利 | Claim 1 + 摘要 | ~200–400 tokens |
| 郵件列表討論串 | 單封郵件，去除引用 | ~200–500 tokens |
| 視頻/音頻轉錄 | 按說話停頓或章節標記分割 | ~300–600 tokens |

**原則：** 一個 chunk = 一個概念。如果一個 chunk 涵蓋 3 個不相關的主題，請拆分它。

---

## 第 4 步：Embedding 模型選擇

| 模型 | 維度 | 使用時機 | 備註 |
|---|---|---|---|
| **BGE-M3**（我們使用的） | 1024D dense + sparse | 技術多語言 | 最適合程式碼 + 散文混合 |
| `text-embedding-3-large`（OpenAI） | 3072D | 通用文字、高品質 | API 費用，無稀疏向量 |
| `nomic-embed-text` | 768D | 輕量本地 | 適合純散文 |
| `codet5p-110m-embedding` | 256D | 純程式碼 | 對 TVA 而言太窄 |
| `multilingual-e5-large` | 1024D | 多語言 | BGE-M3 的替代方案 |

**TVA 專用：** 使用 BGE-M3。稀疏權重對於 Sparse Lexical Bridge 條件（C3）至關重要。

---

## 第 5 步：清理 Pipeline

```
原始文件
    │
    ▼
① 語言過濾     （保留英文 + 你的目標語言）
    │
    ▼
② 去重複       （內容的 minhash LSH 或精確雜湊）
    │
    ▼
③ 長度過濾     （丟棄 < 50 tokens、> 2000 tokens）
    │
    ▼
④ 噪音過濾     （丟棄自動生成、樣板、測試 fixture）
    │
    ▼
⑤ 領域相關性  （可選：與種子文件的 embedding 相似度）
    │
    ▼
⑥ 分塊         （依文件類型，見上表）
    │
    ▼
⑦ Embedding    （BGE-M3 本地，batch size 32–64）
    │
    ▼
⑧ 建索引       （< 100 萬文件用 FAISS flat，> 100 萬用 HNSW）
    │
    ▼
高品質向量資料庫 ✓
```

---

## 第 6 步：領域停用詞清單

TVA 在計算 Sparse Lexical Bridge 之前會過濾掉通用 token。你需要一份領域專屬的停用詞清單。

**Linux kernel（內建）：**
```python
KERNEL_STOP_WORDS = {
    "define", "include", "struct", "int", "void", "static", "return",
    "linux", "kernel", "core", "sys", "device", "driver", "memory", ...
}
```

**你的領域：** 新增 50–100 個出現在所有地方但沒有判別意義的最高頻 token。對所有稀疏 token 跑 `Counter`，取前 200 個，手動移除那些確實具有領域專屬意義的。

---

## 第 7 步：品質檢查

執行 TVA 之前，驗證你的語料庫：

```python
# 檢查 embedding 品質
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# 抽樣 1000 個隨機配對 — 分佈應以 ~0.3-0.6 為中心
# 如果太多配對 > 0.9：語料庫太同質（不好）
# 如果太多配對 < 0.1：語料庫太噪雜（不好）
sample = np.random.choice(embeddings, 1000)
sims = cosine_similarity(sample)
print(f"Mean similarity: {sims.mean():.3f}")  # 目標：0.3-0.5
print(f"Std: {sims.std():.3f}")              # 目標：> 0.15
```

---

## 領域範例

| 領域 | 核心來源 | 需額外新增的停用詞 |
|---|---|---|
| **Linux kernel**（我們的使用案例） | torvalds/linux、LKML、Intel SDM | `mutex`、`spinlock`、`cpu`、`irq` |
| **生醫** | PubMed、PDB、UniProt | `patient`、`study`、`method`、`result` |
| **材料科學** | Materials Project、ICSD、論文 | `material`、`sample`、`measured`、`Fig` |
| **汽車** | AUTOSAR 規格、ISO 26262、MISRA | `shall`、`system`、`function`、`module` |
| **金融** | SEC 文件、財報電話、論文 | `company`、`period`、`million`、`percent` |
| **編譯器/PL** | LLVM、GCC 原始碼、PLDI 論文 | `pass`、`node`、`type`、`value` |

---

## 實用資源

### Embedding 與向量資料庫
| 資源 | URL | 你將學到什麼 |
|---|---|---|
| BGE-M3 論文 | https://arxiv.org/abs/2309.07597 | Dense-sparse 雙重 embedding |
| FAISS 文件 | https://faiss.ai | 十億規模相似度搜尋 |
| ChromaDB | https://docs.trychroma.com | 簡單的本地向量資料庫 |
| Qdrant | https://qdrant.tech/documentation | 生產就緒，支援過濾 |
| Weaviate | https://weaviate.io/developers/weaviate | 圖 + 向量混合 |

### 資料收集
| 資源 | URL | 你將學到什麼 |
|---|---|---|
| arXiv API | https://arxiv.org/help/api | 免費論文存取 |
| Semantic Scholar | https://api.semanticscholar.org | 引用圖 + 摘要 |
| USPTO 批量資料 | https://bulkdata.uspto.gov | 專利全文 |
| PyDriller | https://github.com/ishepard/pydriller | Git 歷史挖掘 |
| tree-sitter | https://tree-sitter.github.io | 語言無關的 AST 解析 |

### 分塊與處理
| 資源 | URL | 你將學到什麼 |
|---|---|---|
| LangChain text splitters | https://python.langchain.com/docs/modules/data_connection/document_transformers | 分塊策略 |
| LlamaIndex ingestion | https://docs.llamaindex.ai | 端到端 RAG pipeline |
| PyMuPDF | https://pymupdf.readthedocs.io | PDF 提取 |

### 視頻 / 音頻轉錄
| 資源 | URL | 你將學到什麼 |
|---|---|---|
| OpenAI Whisper | https://github.com/openai/whisper | 本地語音轉文字（多語言） |
| faster-whisper | https://github.com/SYSTRAN/faster-whisper | Whisper 的 CTranslate2 加速版本 |
| yt-dlp | https://github.com/yt-dlp/yt-dlp | 下載 YouTube / 會議視頻 |
| pyannote-audio | https://github.com/pyannote/pyannote-audio | 說話者分離（diarization） |
| WhisperX | https://github.com/m-bain/whisperX | Whisper + 對齊 + diarization 一體化 |

---

## 第 8 步：配置你的 Debate Panel

語料庫準備好之後，唯一需要手動配置的是對抗審查委員會的**四個 Specialist 角色**。就像為一個領域會議挑選程序委員會一樣：你需要能從不同角度挑戰想法的審查者——技術正確性、新穎性、策略價值，以及風險。

目前 Linux/x86 的陣容是：

| 角色 | 審查焦點 |
|---|---|
| Kernel Hardliner | 實作正確性、ABI 約束、鎖定機制 |
| Prior-Art Shark | 新穎性、非顯而易見性、與已知技術的重疊 |
| Intel Strategist | 平台策略契合度、HW/SW 協同設計價值 |
| Security Guardian | 安全性與隱私風險 |

**Prior-Art Shark** 與**安全/安全性**角色具有普遍適用性——每個領域都保留它們。其他兩個應反映你領域的技術與組織現實。

### 領域範例

**生醫 / 藥物發現**
參考 NeurIPS / Nature Medicine 審查規範：科學嚴謹性 + 安全性優先。

| 角色 | 審查焦點 |
|---|---|
| Clinical Researcher | 臨床可行性、患者安全、FDA/EMA 申請路徑 |
| Drug-Safety Expert | 毒理學、脫靶效應、禁忌症 |
| Prior-Art Shark | 專利格局、已發表先前技術 |
| Regulatory Specialist | GxP 法規合規、標示、試驗設計要求 |

---

**材料科學**
參考 Nature Materials / ICMSE 審查：可重現性 + 可製造性。

| 角色 | 審查焦點 |
|---|---|
| Materials Physicist | 熱力學可行性、DFT/實驗一致性 |
| Manufacturing Engineer | 可擴展性、製程整合、良率問題 |
| Prior-Art Shark | 專利與文獻重疊 |
| IP Counsel | 自由實施、請求項範圍 |

---

**汽車軟體（AUTOSAR / ISO 26262）**
參考 SAE / AUTOSAR 技術審查：安全完整性 + 標準合規。

| 角色 | 審查焦點 |
|---|---|
| Functional Safety Engineer | ASIL 分解、FMEA、安全目標可追溯性 |
| AUTOSAR Architect | BSW/RTE 整合、ARXML 合規、時序 |
| Prior-Art Shark | 相對於現有 AUTOSAR 擴展、SAE 論文的新穎性 |
| Cybersecurity Expert | EVITA/TARA 威脅建模、ISO 21434 |

---

**編譯器 / 程式語言**
參考 PLDI / POPL 程序委員會：形式正確性 + 效能。

| 角色 | 審查焦點 |
|---|---|
| Compiler Engineer | IR 正確性、別名分析、未定義行為 |
| Language Theorist | 型別系統健全性、形式語義 |
| Prior-Art Shark | 與 LLVM/GCC patch、學術發表的重疊 |
| Performance Architect | 效能基準退化風險、codegen 品質 |

---

**企業 / 雲端基礎設施**
參考 SOSP / OSDI 審查：故障下的正確性 + 運維成本。

| 角色 | 審查焦點 |
|---|---|
| Distributed Systems Engineer | 一致性模型、故障模式、CAP 權衡 |
| SRE / Operations | 運維複雜性、爆炸半徑、回滾策略 |
| Prior-Art Shark | AWS/GCP/Azure 專利格局、開源先前技術 |
| Security Guardian | 供應鏈風險、零信任、資料駐留 |

---

### Prompt 模板

為每個 Specialist 提供如下形式的一段 system prompt：

```
你是 [角色名稱]。你的關注點是 [領域 + 視角]。
在審查技術發明揭露文件時，你評估：
- [此角色專屬的評估標準 1]
- [此角色專屬的評估標準 2]
- [此角色專屬的評估標準 3]
回應格式：verdict（APPROVE / REVISE / REJECT）、一句話理由，
若為 REVISE 則附上一項具體必要修改。
```

Claude 或任何有能力的 LLM 都能幫你起草這些 prompt，只要你描述你的領域即可。關鍵是每個 Specialist 應有**明確且不重疊的審查視角**——如果兩個審查者會說同樣的話，合併它們或替換其中一個。

---

## 快速開始（任何領域）

```bash
# 1. Clone DeepThought
git clone <this repo>
cd deepthought

# 2. 將你的文件加入 data/raw/your_domain/

# 3. 撰寫簡單的匯入腳本（參考 scripts/ingest_kernel.py 作為範本）
python scripts/ingest_kernel.py --subsystem your_domain

# 4. 驗證語料庫品質
python scripts/run_forager_probe.py --target "your intent here"

# 5. 執行 TVA
python scripts/run_pipeline_service.py \
    --target "your innovation intent" \
    --collection your_domain \
    --auto-target
```

---

*如有任何關於將 TVA 應用於你的領域的問題，請開 issue 或聯絡 kris.pan@intel.com。*
