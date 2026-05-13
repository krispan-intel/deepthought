# Paper 1 v2 提交清單

*準備於 2026-05-13。在 arXiv v1 通過審核後執行。*

---

## 分類更改

- [ ] 主分類改為：`cs.AI` → `cs.IR`
- [ ] 副分類保留：`cs.AI`、`cs.SE`
- [ ] 更新投稿 metadata

---

## Introduction（引言）

- [ ] 在開頭附近加上 framing 句：
  > *古典 IR 問的是：給定一個 query，哪些現有文件是相關的？TVA 問的是：給定一個 Anchor，哪些相關知識是缺席的？*

- [ ] 加上 IR 傳承段落，連接到 Belkin ASK、Swanson ABC、exploratory search：
  > *TVA 將 anchor-conditioned retrieval 延伸到偵測有意義的缺席：那些預期中的連結、證據或概念橋樑缺失的區域。*

- [ ] 把「TVA 是革命性的」語氣換成「TVA 延伸 IR 傳統」

---

## Background / PRH 章節

- [ ] 在 PRH 段落後加上橋接句：
  > *PRH 提供了一個定性的收斂聲明。然而 TVA 需要一個有限維度的操作性問題：需要保留多少幾何結構，void detection 才能可靠？TVA 維度定理（附錄 A）補上了這個缺失的操作層。*

- [ ] 說明 PRH 支持 proxy 對齊，但 proxy 對齊本身不夠——維度定理提供了判斷標準

---

## Discussion — Broader Implications（更廣泛的意涵）

- [ ] 在 broader implications 開頭加上護欄句：
  > *以下討論說明 anchor-conditioned absence detection 如何延伸到文件檢索之外。這些是本文的意涵，不是正式聲明。*

- [ ] 壓縮 multi-agent / DMN / 單體 AI 極限段落——每個保留 1-2 句，不是完整段落
- [ ] 每一段結尾都要拉回 IR 語言：缺席、void、anchor、知識空間、retrieval

---

## 附錄 A — 維度定理

- [ ] 在 A.1 開頭加上：
  > *PRH 提供了一個定性的收斂聲明；本附錄將它轉化成一個有限維度的 retrieval 問題。我們問的是：一個 D 維向量資料庫能保留多少共享表示幾何，以及在哪個點增加維度會製造比有用解析度更多的虛假 void。*

- [ ] 修正「對 LLM 的 embedding space 做 SVD」的說法——加上橋接句：
  > *在實踐中，我們從嵌入後的語料庫估計任務相關的頻譜衰減 γ，而非從不可取得的前沿 LLM representation。在 PRH 下，充分對齊的 embedding model 的語料庫誘導幾何，被視為前沿模型任務相關子幾何的操作代理。*

- [ ] 加上定理前提條件：
  > *在冪次頻譜衰減模型和線性稀疏噪音懲罰的假設下，最佳 embedding 維度為...*

- [ ] 在 k=0.001 那節加上：
  > *我們不主張 k=0.001 是通用值；它是針對本語料庫和 pipeline 估計的實作層級噪音容忍度。未來工作應從 null-model void 佔用率和人工標注的 false-void 率來估計 k。*

- [ ] 考慮重新命名 Theorem 副標題：
  `TVA 維度定理（PRH 與稀疏噪音下的最佳代理維度）`

- [ ] 更精確地定義「topological resolution（拓撲解析度）」：
  > *我們以操作性方式使用「拓撲解析度」這個詞：embedding 代理保留的可用於下游 void detection 的頻譜結構比例。它不是同調不變量。*

---

## 數學/符號修正（已在目前草稿中完成，請核實）

- [x] JL 引理已替換為維度詛咒論證
- [x] .tex 中 C2 下界存在
- [x] Sensitivity table A.5 已加入
- [x] Upstream/downstream slogan 已更新

---

## Zenodo / arXiv 連結

- [ ] 將 PAPER.md、README.md（三語言版本）中的 `*(pending)*` 替換為實際的 arXiv URL
- [ ] 如需要則更新 Zenodo 記錄

---

## Push 到 public repo

- [ ] `git push public deepthought:main`
- [ ] 確認 GitHub 顯示更新後的論文

---

## 備註

- D-TVA 在 Future Work 中：保持不變，無需更動
- Meta-evaluation 章節：保持不變，這是獨特的強項
- Multi-agent / DMN 段落：壓縮但不刪除
- 「TVA 不適用於 Level 2 系統」的範疇邊界：保持不變
- Collapse Pulse / 安全與創造力張力：保持不變
