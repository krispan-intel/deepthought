# 針對拓撲空缺分析 (Topological Void Analysis) 的時序驗證框架：區分幾何檢索與實質知識填補的方法論研究

## 1. 緒論：認知拓撲學與時序驗證的挑戰

在當代科學計量學 (Scientometrics) 與計算知識發掘的交界處，拓撲空缺分析
(Topological Void Analysis, TVA)
代表了一次典範轉移。傳統的文獻計量方法著重於觀察已存在的引用網路，而 TVA
則致力於對潛在的科學發現進行預測性建模。透過將數十萬份文獻映射至高維度嵌入空間
(Embedding Space) 並辨識其中的「結構洞」(Structural Holes)，TVA
能夠在極早期的階段標定出具有高度潛能的知識缺口，進而生成數以千計的發明候選方案
^1^。

然而，在推動 TVA 的時序驗證 (Temporal Validation)
時，一個核心的認識論困境浮現：並非所有在幾何拓撲上被封閉的「空缺」都代表實質的科學知識生成。在知識的嵌入空間中，高被引用的「錨點文獻」(Anchor
Nodes)
會產生類似重力的空間扭曲效應；這種拓撲空間的重力扭曲，經常會導致單純基於距離的幾何檢索產生虛假的聯結
(Spurious geometric
links)，使得演算法誤判知識缺口已被填補。這些虛假填補往往源自於語義漂移
(Semantic drift)、相鄰概念的過度可觀察性
(Hyper-observability)，或僅僅是作者為了提高發表機率而進行的修辭性橋接
(Rhetorical bridging)，而非具備嚴謹證據支持的實質認知路徑。

本研究報告旨在從方法論的深層角度出發，設計一套具備高度鑑別力的時序驗證框架，以徹底區分「單純的幾何檢索」與「實質的知識填補」。為此，本報告將系統性地整合五個具體面向的文獻與實踐作法：(1)
預測性研究缺口 (Research gap) 的驗證方法；(2) 基於文獻發現
(Literature-based discovery, LBD) 的回顧性時序驗證；(3)
科學計量學中處理語料庫暴露、可觀察性與右側設限 (Right-censoring)
的機制；(4) 關於主張與證據對齊 (Claim-evidence alignment) 及過度宣稱
(Overclaiming) 檢測的研究；以及 (5) 嵌入模型如何處理偽陽性與密集區域干擾
(Dense-region confounding)。透過上述整合，本報告將建立一個包含 Raw
Fill、Anchor Gating 與 Role-Aware Classification
三階段分工的驗證框架，並提出高成本效益的抽樣策略與具體的實驗執行計畫。

## 2. 知識缺口驗證與結構洞理論的演進

研究缺口 (Research Gap)
的精準辨識與填補，是推動科學知識邊界擴張的基礎動力。在驗證 TVA
模型所預測的空缺是否具備科學價值之前，必須先釐清「缺口」在學術語境中的多維度本質，以及量化其被「填補」的標準。

### 2.1 研究缺口的分類與認知功能

文獻回顧在辨識研究缺口時，通常將其定義為現有研究中缺乏知識、未被探討的觀點或未被提出的問題
^3^。學者通常將這些缺口細分為多種類型，每一種類型在知識網絡中扮演不同的認知角色：

  ---------------------------------------------------------------------------------------------------------------------------------------------
  **缺口類型 (Gap Type)** **定義與特徵**                                                   **在拓撲空間中的幾何表現**
  ----------------------- ---------------------------------------------------------------- ----------------------------------------------------
  **知識缺口 (Knowledge   該領域幾乎沒有或完全沒有相關研究，或新興技術尚未應用於特定領域   廣泛的低密度區域，缺乏節點與邊的連結。
  Gap)**                  ^3^。                                                            

  **方法論缺口            現有研究採用的方法受限，允許使用替代方法來驗證或推翻既有結論     相同主題叢集內，代表不同方法的子叢集之間缺乏橋接。
  (Methodological Gap)**  ^3^。                                                            

  **理論缺口 (Theoretical 缺乏解釋特定現象的概念模型，或現有理論模型之間存在矛盾與斷層     兩個高度密集的理論叢集之間存在明顯的結構洞。
  Gap)**                  ^3^。                                                            

  **實證缺口 (Empirical   需要透過實證評估來驗證先前的研究發現或命題 ^6^。                 概念節點存在，但缺乏代表實驗數據的證據節點連結。
  Gap)**                                                                                   

  **實務知識衝突缺口      專業人士的實際行為與其所倡導的行為之間存在差異的範圍與原因 ^6^。 實務應用叢集與學術理論叢集之間的網絡斷裂。
  (Practical-Knowledge                                                                     
  Conflict)**                                                                              
  ---------------------------------------------------------------------------------------------------------------------------------------------

### 2.2 明確缺口與隱含缺口的驗證差異

在驗證方法論上，必須區分明確缺口 (Explicit Knowledge Gaps) 與隱含缺口
(Implicit Knowledge
Gaps)。明確缺口通常由研究者在論文的「未來研究建議」或系統性文獻回顧中直接用語句表達
^7^。自然語言處理 (NLP) 模型可利用特定領域的無知線索字典 (Ignorance-cues
dictionary) 或論述分析來提取並驗證這些明確陳述的準確性 ^9^。

然而，TVA
的核心價值在於發掘「隱含缺口」------也就是在引文網絡中以「結構洞」(Structural
Holes) 形式存在，尚未被任何單一學者明確指出的知識斷層
^2^。驗證這類隱含缺口的填補，不能僅仰賴關鍵字的出現，而必須追蹤這些結構洞的「填補率」(Fill
rate) 以及其對知識網絡造成的系統性影響
^11^。當一個結構洞連接了原本斷裂的個人、群體或概念（即所謂的 tertius
iungens 經紀行為），它會在組織或學科層面引發可衡量的創新與協調改善
^12^。

### 2.3 知識不確定性的降低作為填補標準

從科學計量學 (Knowmetrics)
的角度來看，單純縮小拓撲空間中的幾何距離並不足以宣稱缺口已被填補。實質的知識填補必須能夠「降低知識的不確定性」(Reducing
knowledge uncertainty) ^14^。若 TVA 預測了 A 與 B
之間的空缺，而後續有一篇論文在文本中同時提及 A 與
B，我們必須評估這座橋梁是具備認知承載力的（例如：解決了矛盾、驗證了假設），還是僅僅是語義上的共現。因此，驗證方案必須超越單純的共現計數，深入探討新知識單位對於減少特定科學問題不確定性的貢獻度
^14^。

## 3. 基於文獻發現 (LBD) 的回顧性時序驗證機制

文獻基發現 (Literature-Based Discovery, LBD)
技術的核心機制是從大量不相關的文獻中發掘隱含的關聯（例如著名的
![](media/image4.png){width="1.1007502187226597in"
height="0.24922681539807523in"} 典範），以生成新穎的科學假設
^15^。為了驗證 TVA 預測拓撲空缺的準確性，必須借鑒並升級 LBD
領域中的回顧性驗證 (Retrospective Validation) 方法。

### 3.1 傳統靜態評估指標的局限性

LBD 的傳統驗證方法通常採用時間切片 (Time-slicing) 或複製方法
(Replication method)：將時間點
![](media/image1.png){width="7.291666666666667e-2in" height="0.25in"}
之前可用的文獻輸入系統，要求系統產生潛在發現的排序列表，接著觀察時間點
![](media/image1.png){width="7.291666666666667e-2in" height="0.25in"}
之後發表的文獻是否包含了這些預測的關聯 ^17^。

在評估這些預測時，傳統資訊檢索 (Information Retrieval, IR)
指標被廣泛使用：

-   **Recall@K
    > (召回率)**：衡量在所有已知的真實未來發現中，有多少比例出現在系統預測的前
    > K 個結果中。這確保了系統能夠提取出涵蓋所有必要資訊的上下文 ^16^。

-   **Precision at K (P@K)**：衡量在固定的前 K
    > 個檢索結果中，真實發現所佔的比例，強調早期發現相關結果的重要性
    > ^16^。

-   **Average Precision (AP) 與
    > MAP**：這是一種結合精準度與召回率的閾值無關 (Threshold-agnostic)
    > 指標，透過計算不同 K
    > 值下的平均精度，全面評估系統將真實正例排在偽陽性之前的能力 ^20^。

儘管 AP 提供了比單一 K 值更全面的評估，但靜態的
![](media/image3.png){width="0.8286132983377078in"
height="0.2175109361329834in"}
時間切片方法依然存在根本性的瑕疵。它假設所有被預測的缺口都有相等的機率在該任意設定的
![](media/image6.png){width="0.24104768153980752in"
height="0.2515277777777778in"}
窗口內被填補。事實上，複雜的拓撲空缺可能需要數十年的前置技術發展才能被橋接，而微不足道的漸進式缺口則可能在幾個月內就被填補。

### 3.2 將缺口填補形式化為存活分析 (Survival Analysis) 問題

為了解決時間窗口的武斷性問題，TVA
的時序驗證必須將「預測發現」形式化為時間至事件 (Time-to-event)
的存活分析問題
^23^。透過將「拓撲空缺被填補」視為感興趣的事件，研究者可以估計動態風險預測與時間至事件的分布，而非僅僅依賴固定時間點的預測
^26^。

在具體的模型選擇上，除了常見的 Cox 比例風險模型外，Lin-Ying 附加風險模型
(Additive Hazard Model) 在此情境下展現出顯著優勢。Lin-Ying
模型作為最簡單的 AH
模型，能夠提供隨時間變化的附加效應的單一摘要統計量，避免了在不同時間區間內比較不同風險函數所帶來的複雜性
^27^。

此外，由於重大科學發現（真實的空缺填補）相對於漸進式出版物的背景噪音而言，屬於相對罕見的事件，傳統的對數秩檢定
(Log-rank test)
可能缺乏足夠的統計檢定力。因此，驗證框架應導入基於大量精確超幾何檢定
(Exact hypergeometric tests) 所取得的 p-values 之高階批評 (Higher
Criticism)
方法。此方法對於未知且相對罕見的時間區間內的風險差異具備高度敏感性，能夠在稀有度與強度參數平面上展現出優越的漸近功效
(Asymptotic power)，精準捕捉真實的缺口填補風險率 ^29^。

## 4. 科學計量學中的語料庫暴露、可觀察性與右側設限

在科學計量學中，科學社群的社會認知行為 (Socio-epistemic behavior) 是干擾
TVA
時序驗證的最大混淆變數。文獻網絡並非被動的客觀事實庫，而是一個受資金、聲望與注意力高度驅動的複雜適應系統
^30^。因此，要區分純粹的幾何檢索與實質知識填補，驗證框架必須對語料庫暴露
(Corpus Exposure)、可觀察性 (Observability) 以及右側設限
(Right-censoring) 建立嚴格的控制機制。

### 4.1 錨點暴露 (Anchor Exposure) 與可觀察性驅動的漸進式噪音

「錨點暴露」指的是某些具有極高聲望或剛發表便引發轟動的「錨點文獻」，對後續研究軌跡產生不成比例的吸引力與影響力
^32^。在 TVA
的幾何空間中，如果一個被預測的拓撲空缺恰好位於某個強大錨點文獻的附近，該空缺在時序驗證窗口內極有可能顯示為被「迅速填補」。

然而，這種填補往往不是因為科學界突破了深層的認知障礙，而是源於「可觀察性」(Observability)
的社會學效應。在創新擴散理論中，可觀察性是指一項創新被潛在採用者認為容易理解、符合現有價值觀並能進行有限度實驗的程度
^35^。在高可觀察性與高錨點暴露的次領域中，研究人員會蜂擁而至，發表大量僅具微小差異的漸進式研究
(Incremental research) 來最大化出版效益
^31^。這些漸進式論文在嵌入空間中形成了一個高密度的局部叢集，從數學幾何上輕易地橫跨了先前辨識出的空缺。

若依賴傳統 LBD
指標，這會被記錄為一個「真實的未來發現」。但實際上，這僅代表預設的認知填補
(Default epistemic filling) 或典範內的模型漂移，而非庫恩 (Thomas Kuhn)
意義上的典範轉移或結構洞的實質突破 ^31^。因此，驗證框架必須引入錨點閘門
(Anchor Gating)，透過計算特定概念周邊的引用速度 (Citation velocity)
與網絡中心性，來折現或過濾掉那些僅僅是乘著錨點文獻順風車而產生的虛假填補。

### 4.2 處理右側設限 (Right-Censoring) 與長期演化軌跡

與錨點暴露導致的過早虛假填補相反，許多深層的理論缺口或實證缺口需要極長的時間才能被克服。如果時序驗證窗口設定為
![](media/image7.png){width="0.8069663167104112in"
height="0.2515223097112861in"} 年，一個在第 6
年才被實質填補的重大拓撲空缺，在模型中會被錯誤地標記為偽陽性。這種現象在書目計量學成長模型中被稱為右側設限
(Right-censoring) ^38^。

隨著近期世代出版物呈指數級增長，右側設限的問題日益嚴重 ^39^。為了避免
TVA
模型因預測了需要長期探索的深層科學缺口而受到不公平的懲罰，時序驗證必須揚棄線性回歸，轉而採用廣義加性模型
(Generalized Additive Models, GAMs) 或上述的存活分析風險模型 ^38^。GAMs
透過平滑函數 (Smooth functions)
取代線性預測變數，能夠靈活處理研究人員尚未達到生產力巔峰或長期缺口尚未閉合的非線性軌跡，保留並利用那些存活到觀察視窗邊緣的設限數據，確保驗證框架的統計無偏性
^38^。

## 5. 處理偽陽性與密集區域干擾 (Dense-Region Confounding)

嵌入式科學發現 (Embedding-based scientific discovery)
的核心依賴於將高維度的自然語言數據映射至連續的拓撲流形 (Topological
manifolds)
中。雖然高維度文本嵌入能夠捕捉結構化數據所缺失的關鍵潛在混淆變數代理
^42^，但這種連續拓撲性質也帶來了獨特的挑戰，特別是模型降維時所引發的偏差-變異權衡
(Bias-variance tradeoff) 與高偽陽性率 ^43^。

### 5.1 密集區域干擾的幾何陷阱

在 TVA 的驗證中，最難以處理的技術誤差之一是「密集區域干擾」(Dense-region
confounding)。在嵌入空間中，兩個截然不同但皆擁有龐大文獻基數（高密度）的子領域，可能在幾何地理上彼此相鄰。它們之間的邊界在演算法眼中會呈現為一個顯著的拓撲空缺。

由於這兩個子領域極為密集，若有一篇隨機的、低品質的論文在寫作時不經意地混合了兩邊的常見詞彙，該論文的嵌入向量就會精準地落在這個空缺的正中央。這種純粹的語彙重疊
(Lexical overlap)
創造了一座虛假的語義橋梁。傳統的基於樹狀結構的雙重機器學習 (Tree-based
Double Machine Learning, DML)
估計器難以調整這種偏差，因為它們無法建立嵌入流形的連續拓撲模型，從而保留了高達
+24% 的實質偏差 ^42^。

### 5.2 神經網絡增強的雙重機器學習與局部混淆測試

為了滿足高維度自然語言數據的無干擾假設 (Unconfoundedness
assumption)，時序驗證框架必須部署神經網絡增強的雙重機器學習 (Neural
Network-Enhanced DML)
架構。深度學習架構能夠針對優化網絡，將因果參數估計的偏差顯著降低至
-0.86%，有效恢復真實的因果效應 ^42^。

更進一步，必須實施無母數的局部混淆測試 (Partial confounder
test)，以探測模型不受干擾的虛無假設 ^44^。在 TVA
的具體應用中，這意味著必須建立「隨機拓撲虛無模型」(Random-topology null
model)。

在基因體學的 LBD
中，研究人員發現傳統的「隨機基因」虛無模型會產生大量偽陽性，必須改用「隨機表型」(Random-phenotype)
虛無模型來消除生理上不適當的虛假 GO 類別關聯 ^45^。同理，當 TVA
宣稱一篇論文填補了某個空缺時，驗證系統必須計算：這篇論文橋接兩個斷裂概念的相關性，是否顯著高於從該特定「密集區域」中隨機抽樣的論文所產生的預期相關性？

為了確保檢測結果的統計可靠性，系統應採用原則性閾值選擇 (Principled
threshold selection) 策略。透過 GammaGMM
混合模型直接從無標籤數據中推斷污染率，或利用超越質量 (Excess-mass)
方法在無標籤的情況下提供異常分數的概率估計，TVA
驗證可以摒棄武斷的距離閾值，提供具備嚴格統計保證的拓撲異常檢測 ^46^。

## 6. 認知角色驗證與主張-證據對齊 (Claim-Evidence Alignment)

即使一個拓撲空缺在幾何上被完美封閉，且神經網路 DML
與局部混淆測試也證實該填補並非由密集區域干擾或錨點暴露所引起，我們仍面臨最終的考驗：這篇論文在知識論層面上，真的證明了嵌入模型認為它所證明的內容嗎？

### 6.1 科學實踐的認知角色與過度宣稱現象

科學實踐並非單一維度的活動，不同文獻在生態系中扮演著不同的認知角色
(Epistemic roles)
^50^。某些模型作為啟發性設備，用於生成具體的類比；另一些則將學科知識與嚴謹的實驗數據相結合，以生成具有解釋力的因果推論
^53^。

在目前的學術出版生態中，研究者時常在摘要或結論中進行「修辭性橋接」。例如，一篇論文的方法學可能僅證明了
X 對 Y 具有輕微的體外影響，但作者卻在摘要中宣稱「本研究填補了 X
與系統性疾病 Z 之間的關鍵缺口」 ^55^。這種科學誇大 (Scientific
exaggeration)、主張範圍超出證據所能支持的現象，被稱為過度宣稱
(Overclaiming) 或學術自旋 (Spin) ^57^。

如果 TVA 驗證框架僅依賴語義相似度或傳統的謂詞-論元提取工具
(Predicate-argument extraction, 例如 TextRunner 或 Syncha
提取主-動-賓結構)
^58^，將不可避免地淪為修辭性橋接的受害者。幾何檢索會判定空缺已填補，但實質的科學認知卻依然停滯。

### 6.2 RIGOURATE 框架與 LLM 證據驗證

為了徹底區分修辭與實質，時序驗證管線必須強制執行主張與證據的對齊
(Claim-evidence
alignment)。這要求模型不僅要提取科學主張，還要識別用於驗證該主張的具體證據（例如表格數據、實驗數據），並解釋其對齊邏輯
^57^。

在此，整合 RIGOURATE 框架的評估準則至關重要 ^57^。RIGOURATE
提供了一套嚴謹的方法來量化科學論文中的「證據比例性」(Evidential
proportionality)------即評估一項主張的強度與範圍是否合理地奠基於論文的實際方法與結果之上。框架將論文的主張分配
0 到 1 的過度陳述分數 (Overstatement score)，並分類為：

1.  **陳述良好
    > (Well-stated)**：主張完全植基於論文的方法、結果與推理，無修辭誇大。

2.  **部分過度陳述 (Partially
    > Overstated)**：主張的某些組成部分有證據支持，但其他部分超出了證據保證的範圍。

3.  **過度陳述
    > (Overstated)**：主張做出了未經證據證實的斷言，通常是由於證據不足（數據有限）、不合理的普遍化
    > (Unjustified generalization) 或缺乏實質的方法學細節 ^57^。

透過部署大型語言模型 (LLM)
代理群，並將同儕審查的評論作為校準上下文輸入，系統能夠在長距離依賴
(Long-range dependencies)
構成挑戰的完整學術文本中，精準檢測出表面用詞華麗但缺乏實證深度的論文
^57^。這種深入到資料格 (Cell-level rationales)
等級的表格-文本對齊驗證，確保了 TVA
所辨識出的填補事件是經得起嚴格科學檢驗的知識生成 ^59^。

## 7. 綜合驗證框架：Raw Fill、Anchor Gating 與 Role-Aware Classification

基於上述五個面向的深度整合，本研究提出一套專為 Topological Void Analysis
設計的三階段時序驗證框架。該框架系統性地剝離幾何假象與社會計量學干擾，最終確立實質的科學發現。

+-----------------+-----------------+-----------------+-----------------+
| **驗證階段      | **核心目標      | **部            | **欲解決之偏差  |
| (Stage)**       | (Core           | 署機制與演算法  | (Addressed      |
|                 | Objective)**    | (Mechanisms &   | Bias)**         |
|                 |                 | Algorithms)**   |                 |
+=================+=================+=================+=================+
| **1. Raw Fill** | 測量時間切片    | 計算 Average    | 作為基          |
|                 | ![](m           | Precision (AP)  | 準線，捕捉包含  |
| (原始幾何填補)  | edia/image3.png | 與              | 大量偽陽性的最  |
|                 | ){width="0.8286 | Recall@K；動態  | 大可能填補池。  |
|                 | 132983377078in" | 網絡圖論映射。  |                 |
|                 | height="0.21751 |                 |                 |
|                 | 09361329834in"} |                 |                 |
|                 | 間的            |                 |                 |
|                 | 純粹拓撲閉合。  |                 |                 |
+-----------------+-----------------+-----------------+-----------------+
| **2. Anchor     | 辨識因社會暴露  | 計              | 消除語料庫暴露  |
| Gating**        | 或鄰近密度而產  | 算錨點引用速度  | (Corpus         |
|                 | 生的虛假填補。  | (Citation       | Exposure)、     |
| (錨點閘門過濾)  |                 | Velocity)；應用 | 可觀察性驅動的  |
|                 |                 | Neural          | 漸進式噪音，以  |
|                 |                 | N               | 及密集區域干擾  |
|                 |                 | etwork-Enhanced | (Dense-region   |
|                 |                 | DML             | confounding)。  |
|                 |                 | 提取因          |                 |
|                 |                 | 果效應；執行局  |                 |
|                 |                 | 部混淆測試與隨  |                 |
|                 |                 | 機拓撲虛無模型  |                 |
|                 |                 | ^42^。          |                 |
+-----------------+-----------------+-----------------+-----------------+
| **3. Role-Aware | 確              | 多重角色 LLM    | 排除修辭性橋接  |
| C               | 認填補文獻的認  | 代理評估        | (Rhetorical     |
| lassification** | 知角色，並驗證  | (Replicator/E   | brid            |
|                 | 其證據比例性。  | valuator)；執行 | ging)、過度宣稱 |
| (角色感知分類)  |                 | RIGOURATE       | (Overclaiming)  |
|                 |                 | 框架進          | 與缺乏實驗證    |
|                 |                 | 行過度陳述評分  | 據的空泛假設。  |
|                 |                 | (Overstatement  |                 |
|                 |                 | score           |                 |
|                 |                 | 0-1)；實施表    |                 |
|                 |                 | 格-文本對齊驗證 |                 |
|                 |                 | ^57^。          |                 |
+-----------------+-----------------+-----------------+-----------------+

![](media/image8.png){width="6.458333333333333in" height="6.09375in"}

### 7.1 第一階段：Raw Fill (原始幾何填補)

此階段提供純粹拓撲變化的測量基準。系統在時間
![](media/image1.png){width="7.291666666666667e-2in" height="0.25in"}
標定所有的結構洞。在時間
![](media/image2.png){width="0.5603838582677165in"
height="0.24905949256342957in"}（或隨時間連續推進），若有新發表的論文其嵌入向量成功插值
(Interpolate)
並縮短了原本斷裂概念間的幾何距離至特定閾值內，該空缺即被標記為「Raw
Fill」。此階段容忍高偽陽性，旨在捕捉最大的潛在發現池。

### 7.2 第二階段：Anchor Gating (錨點閘門)

為了阻擋可觀察性與暴露偏差模擬的科學進步，Raw Fill 的候選者必須通過
Anchor Gate。系統會計算空缺周邊節點在時間
![](media/image1.png){width="7.291666666666667e-2in" height="0.25in"}
的網絡密度與引用速度。透過前述的神經網絡 DML
模型，系統對空缺閉合與潛在連續變數進行迴歸分析。接著實施局部混淆測試，將閉合機率與「隨機拓撲虛無模型」進行比對
^44^。若該空缺的閉合機率與該密集區域的背景噪音無法區分，即被視為密集區域干擾而予以剔除。只有那些「克服了拓撲阻力」而閉合的空缺，才能進入下一階段。

### 7.3 第三階段：Role-Aware Classification (角色感知分類)

最後的防線是確保橋接空缺的論文在認知論上具備承載力。系統部署多角色 LLM
代理 (包含模擬同儕審查員與發現科學家)
^61^，提取目標論文的明確主張與實驗方法 ^57^。LLM 代理依據 RIGOURATE
準則評估其證據比例性
^57^。若論文展現出過高的過度陳述分數（如數據薄弱卻做出廣泛結論），將被歸類為「修辭性橋接」並淘汰。唯有主張與證據嚴密對齊的論文，才被認可為達成了「實質知識填補」。

## 8. 高成本效益抽樣策略 (High Cost-Efficiency Sampling Strategy)

在處理數十萬篇科學文獻的語料庫時，若對每一個潛在的空缺閉合事件都執行複雜的
DML 因果推論以及昂貴的 LLM 多代理提示鏈 (Prompt chains)
審查，將導致運算成本與時間預算徹底失控
^60^。為了實現可擴展的時序驗證，必須建立一套高成本效益的分層抽樣策略
(Hierarchical Sampling Strategy)。

首先，為了避免樣本過度集中於高密度的「主流」研究主題，系統不應採用簡單隨機抽樣，而應部署
K-Medoids 演算法。透過將 Raw Fills 的嵌入空間進行分群，並選擇例如 50
個具有高度代表性的群集中心 (Medoids/Centers)
作為原型，可以確保抽樣樣本在科學領域的多樣性與代表性之間取得完美平衡
^62^。

其次，在進行 RIGOURATE 分數的 LLM
校準時，需要「人類在迴路」(Human-in-the-loop)
的專家標註來確保大型語言模型作為評判者 (LLM as a judge)
的可靠性。為了最小化昂貴的專家標註成本，框架應導入 Chernoff 邊界
(Chernoff bounds) 定理。透過推導估計誤差的 Chernoff
邊界，系統能在理論上保證所需的樣本數量上限。結合主動學習 (Active
Learning) 與資料選擇方法，系統能精準挑選最具資訊量 (Most informative)
的邊緣案例交由人類標註，從而在減少平均 18% 樣本需求量的情況下，仍能使
LLM 與人類之間的組內相關係數 (Intraclass Correlation Coefficient, ICC)
精準度提升高達 31% ^49^。

## 9. 具體的實驗計畫與執行路徑

為了將上述理論框架落地並進行實證驗證，本報告提出以下包含三個核心階段的具體實驗計畫：

**Phase 1: 語料庫建置與基準結構洞提取 (Corpus Preparation and Baseline
Extraction)**

1.  **資料集獲取與前處理**：匯入大規模、具備完整引用網路與元數據的結構化語料庫（例如
    > PubMed、Web of Science 或 Semantic Scholar），時間跨度設定為 2000
    > 年至 2025 年 ^65^。

2.  **時序切片與特徵工程**：以
    > ![](media/image5.png){width="0.7452799650043744in"
    > height="0.24842629046369205in"} 作為基準時間點。使用 2000-2020
    > 年的數據建立基礎知識圖譜與高維度嵌入流形。

3.  **TVA 模型執行**：在
    > ![](media/image5.png){width="0.7452799650043744in"
    > height="0.24842629046369205in"}
    > 的快照上運行拓撲空缺分析演算法，提取出排名前 10,000
    > 個高潛力的結構洞，並嚴格記錄其邊界概念、局部流形密度以及錨點暴露指標。

**Phase 2: 驗證管線執行與存活分析建模 (Pipeline Execution and Survival
Modeling)**

1.  **Raw Fill 偵測
    > (2021-2025)**：將驗證窗口內的新發表文獻映射入基準嵌入空間中。篩選出在幾何上成功橋接了上述
    > 10,000 個結構洞的子集，並精確記錄其發表日期
    > (Time-to-event)。對於在 2025 年底前仍未閉合的空缺，設定為右側設限
    > (Right-censored) 數據 ^25^。

2.  **Anchor Gating 執行**：針對所有的 Raw Fills，運行神經網路 DML
    > 與隨機拓撲虛無模型測試。排除那些 P-value
    > 無法顯著超越局部混淆背景噪音的事件。

3.  **分層抽樣與 Role-Aware Classification**：利用 K-Medoids
    > 演算法從通過 Anchor Gating 的候選名單中，抽取出 500
    > 篇具備領域代表性的論文。啟動 LLM 多代理系統，依據 RIGOURATE
    > 框架對這 500
    > 篇論文進行「主張-證據對齊」的過度陳述評分，剔除修辭性橋接的偽陽性
    > ^57^。

**Phase 3: 認知指標計算與基準測試發布 (Metric Computation and Benchmark
Finalization)**

1.  **動態風險指標對比**：繪製 Kaplan-Meier 存活曲線，並計算 Lin-Ying
    > 附加風險率 ^25^。對比「Raw Fill 全集」、「通過 Anchor Gating
    > 的集合」與「最終確認為實質填補的集合」三者之間的風險分布差異。

2.  **效能評估校準**：使用經過驗證的實質填補數據，重新計算 TVA 模型的
    > Average Precision (AP)
    > 等指標。展示引入嚴格方法論驗證後，指標如何過濾掉虛假的漸進式膨脹，回歸真實的預測準確率。

3.  **開源基準測試 (Open Benchmark)**：將這 500 篇經過深層分析與
    > Chernoff 邊界統計保證的論文資料集，發布為針對 LLM
    > 與科學文獻代理人的標準評估基準
    > (Benchmark)，為未來的計算科學發現提供具備高度認知確信度的訓練目標
    > ^63^。

## 10. 結論

拓撲空缺分析 (TVA)
展現了預測科學發展軌跡的龐大潛力，但要確保其預測的科學有效性，時序驗證框架必須進行典範層級的革新。科學文獻網路並非純粹中立的數據庫，它深受聲望吸引、錨點效應、修辭誇大與幾何維度偏差的影響。單純依賴距離運算的幾何檢索，無可避免地會將這些社會計量學干擾誤認為是科學革命。

透過整合因果計量經濟學 (DML)、存活分析 (Lin-Ying AH
模型)、隨機拓撲虛無測試，以及基於大型語言模型的 RIGOURATE
主張-證據對齊評估，本報告所設計的 Raw Fill、Anchor Gating 與 Role-Aware
Classification 三階段框架，提供了一個堅實且嚴謹的方法論屏障。輔以
K-Medoids 與 Chernoff
邊界驅動的高成本效益抽樣策略，此驗證方案不僅能在龐大的運算規模中保持財務可行性，更確保了最終辨識出的每一個「缺口填補」，都是實打實、經得起證據考驗的科學知識結晶，為計算機輔助科學發現
(Computational Scientific Discovery) 奠定了不可或缺的認識論基礎。

#### 引用的著作

1.  Topological Void Analysis: A Mathematical Framework for Systematic
    > Technical Innovation Discovery in Knowledge Spaces - Zenodo,
    > 檢索日期：5月 18, 2026，
    > [[https://zenodo.org/records/19836730]{.underline}](https://zenodo.org/records/19836730)

2.  Associations between structural holes in personal networks and
    > health behaviors among young and middle-aged adults in Japan -
    > PMC, 檢索日期：5月 18, 2026，
    > [[https://pmc.ncbi.nlm.nih.gov/articles/PMC12440896/]{.underline}](https://pmc.ncbi.nlm.nih.gov/articles/PMC12440896/)

3.  How to Identify Research Gap Based on Literature Review - Ondezx,
    > 檢索日期：5月 18, 2026，
    > [[https://ondezx.com/blog/how-to-identify-research-gap-based-on-literature-review]{.underline}](https://ondezx.com/blog/how-to-identify-research-gap-based-on-literature-review)

4.  What Is A Research Gap (With Examples) - Grad Coach, 檢索日期：5月
    > 18, 2026，
    > [[https://gradcoach.com/research-gap/]{.underline}](https://gradcoach.com/research-gap/)

5.  Types of Research Gaps - AnswerThis, 檢索日期：5月 18, 2026，
    > [[https://answerthis.io/blog/types-of-research-gaps]{.underline}](https://answerthis.io/blog/types-of-research-gaps)

6.  Machine Learning--Based Approach for Identifying Research Gaps:
    > COVID-19 as a Case Study - PMC, 檢索日期：5月 18, 2026，
    > [[https://pmc.ncbi.nlm.nih.gov/articles/PMC10916961/]{.underline}](https://pmc.ncbi.nlm.nih.gov/articles/PMC10916961/)

7.  What are the most effective and professional methods to identify a
    > research gap? How do experienced researchers uncover gaps in
    > existing literature? \| ResearchGate, 檢索日期：5月 18, 2026，
    > [[https://www.researchgate.net/post/What_are_the_most_effective_and_professional_methods_to_identify_a_research_gap_How_do_experienced_researchers_uncover_gaps_in_existing_literature]{.underline}](https://www.researchgate.net/post/What_are_the_most_effective_and_professional_methods_to_identify_a_research_gap_How_do_experienced_researchers_uncover_gaps_in_existing_literature)

8.  What\'s your actual workflow for finding a research gap (without
    > going insane)? - Reddit, 檢索日期：5月 18, 2026，
    > [[https://www.reddit.com/r/AskAcademia/comments/1on9ier/whats_your_actual_workflow_for_finding_a_research/]{.underline}](https://www.reddit.com/r/AskAcademia/comments/1on9ier/whats_your_actual_workflow_for_finding_a_research/)

9.  GAPMAP: Mapping Scientific Knowledge Gaps in Biomedical Literature
    > Using Large Language Models - arXiv, 檢索日期：5月 18, 2026，
    > [[https://arxiv.org/html/2510.25055v1]{.underline}](https://arxiv.org/html/2510.25055v1)

10. Collaboration Networks, Structural Holes, and Innovation: A
    > Longitudinal Study, 檢索日期：5月 18, 2026，
    > [[https://repositories.lib.utexas.edu/server/api/core/bitstreams/015f184d-b97d-438a-bd14-c1a171e97134/content]{.underline}](https://repositories.lib.utexas.edu/server/api/core/bitstreams/015f184d-b97d-438a-bd14-c1a171e97134/content)

11. Integrating Knowledge from Network: How Explorative/Exploitative
    > Innovations are Balanced - Science and Education Publishing,
    > 檢索日期：5月 18, 2026，
    > [[https://pubs.sciepub.com/jbms/6/4/1/]{.underline}](https://pubs.sciepub.com/jbms/6/4/1/)

12. The Strain of Spanning Structural Holes: How Brokering Leads to
    > Burnout and Abusive Behavior \| Organization Science - PubsOnLine,
    > 檢索日期：5月 18, 2026，
    > [[https://pubsonline.informs.org/doi/10.1287/orsc.2023.1664]{.underline}](https://pubsonline.informs.org/doi/10.1287/orsc.2023.1664)

13. Constructing transactive memory systems for crisis resilience from
    > an intellectual capital lens: a multi-sector study of Chinese
    > manufacturing firms - Emerald Publishing, 檢索日期：5月 18, 2026，
    > [[https://www.emerald.com/jic/article/doi/10.1108/JIC-07-2025-0278/1325351/Constructing-transactive-memory-systems-for-crisis]{.underline}](https://www.emerald.com/jic/article/doi/10.1108/JIC-07-2025-0278/1325351/Constructing-transactive-memory-systems-for-crisis)

14. Towards medical knowmetrics: representing and computing medical
    > knowledge using semantic predications as the knowledge unit and
    > the uncertainty as the knowledge context - PMC, 檢索日期：5月 18,
    > 2026，
    > [[https://pmc.ncbi.nlm.nih.gov/articles/PMC7882417/]{.underline}](https://pmc.ncbi.nlm.nih.gov/articles/PMC7882417/)

15. Literature-based discovery approaches for evidence-based healthcare:
    > a systematic review, 檢索日期：5月 18, 2026，
    > [[https://pmc.ncbi.nlm.nih.gov/articles/PMC8542914/]{.underline}](https://pmc.ncbi.nlm.nih.gov/articles/PMC8542914/)

16. Identifying plausible adverse drug reactions using knowledge
    > extracted from the literature - PMC, 檢索日期：5月 18, 2026，
    > [[https://pmc.ncbi.nlm.nih.gov/articles/PMC4261011/]{.underline}](https://pmc.ncbi.nlm.nih.gov/articles/PMC4261011/)

17. Literature-based discovery: addressing the issue of the subpar \...,
    > 檢索日期：5月 18, 2026，
    > [[https://pmc.ncbi.nlm.nih.gov/articles/PMC9945845/]{.underline}](https://pmc.ncbi.nlm.nih.gov/articles/PMC9945845/)

18. RAG metrics: how to measure & optimize your retrieval pipeline -
    > Redis, 檢索日期：5月 18, 2026，
    > [[https://redis.io/blog/rag-metrics/]{.underline}](https://redis.io/blog/rag-metrics/)

19. How to Evaluate RAG Systems: Metrics, Methods, and What to Measure
    > First - Comet, 檢索日期：5月 18, 2026，
    > [[https://www.comet.com/site/blog/rag-evaluation/]{.underline}](https://www.comet.com/site/blog/rag-evaluation/)

20. Combing signals from spontaneous reports and electronic health
    > records for detection of adverse drug reactions - PMC,
    > 檢索日期：5月 18, 2026，
    > [[https://pmc.ncbi.nlm.nih.gov/articles/PMC3628045/]{.underline}](https://pmc.ncbi.nlm.nih.gov/articles/PMC3628045/)

21. Leveraging Ensemble Machine Learning Models for the Detection of
    > Primary Myelofibrosis in Electronic Health Records - MDPI,
    > 檢索日期：5月 18, 2026，
    > [[https://www.mdpi.com/2072-6694/18/10/1618]{.underline}](https://www.mdpi.com/2072-6694/18/10/1618)

22. Information Retrieval Metrics \| by Zilliz - Medium, 檢索日期：5月
    > 18, 2026，
    > [[https://medium.com/@zilliz_learn/information-retrieval-metrics-0b50ffc5873b]{.underline}](https://medium.com/@zilliz_learn/information-retrieval-metrics-0b50ffc5873b)

23. Visual analytics framework for survival analysis and biomarker
    > discovery from gene expression data \| PLOS One, 檢索日期：5月 18,
    > 2026，
    > [[https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0325399]{.underline}](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0325399)

24. Mistakes to Avoid for Accurate and Transparent Reporting of Survival
    > Analysis in Imaging Research - PMC, 檢索日期：5月 18, 2026，
    > [[https://pmc.ncbi.nlm.nih.gov/articles/PMC8484160/]{.underline}](https://pmc.ncbi.nlm.nih.gov/articles/PMC8484160/)

25. Global Trends and Evidence Gaps in Medical Errors Research: A
    > Mixed-Methods Scientometrics Study - PMC, 檢索日期：5月 18, 2026，
    > [[https://pmc.ncbi.nlm.nih.gov/articles/PMC12057632/]{.underline}](https://pmc.ncbi.nlm.nih.gov/articles/PMC12057632/)

26. DySurv: dynamic deep learning model for survival analysis with
    > conditional variational inference \| Journal of the American
    > Medical Informatics Association \| Oxford Academic, 檢索日期：5月
    > 18, 2026，
    > [[https://academic.oup.com/jamia/article/33/1/112/7906103]{.underline}](https://academic.oup.com/jamia/article/33/1/112/7906103)

27. Estimating the hazard rate difference from case-cohort studies -
    > PMC, 檢索日期：5月 18, 2026，
    > [[https://pmc.ncbi.nlm.nih.gov/articles/PMC12001820/]{.underline}](https://pmc.ncbi.nlm.nih.gov/articles/PMC12001820/)

28. Flexible modeling of the hazard rate and treatment effects in
    > long-term survival studies, 檢索日期：5月 18, 2026，
    > [[https://pmc.ncbi.nlm.nih.gov/articles/PMC5651995/]{.underline}](https://pmc.ncbi.nlm.nih.gov/articles/PMC5651995/)

29. Higher criticism for rare and weak non-proportional hazard
    > deviations in survival analysis - Oxford Academic, 檢索日期：5月
    > 18, 2026，
    > [[https://academic.oup.com/biomet/article/113/1/asaf075/8307530]{.underline}](https://academic.oup.com/biomet/article/113/1/asaf075/8307530)

30. Connecting Scientometrics: Dimensions as a Route to Broadening
    > Context for Analyses, 檢索日期：5月 18, 2026，
    > [[https://pmc.ncbi.nlm.nih.gov/articles/PMC9087033/]{.underline}](https://pmc.ncbi.nlm.nih.gov/articles/PMC9087033/)

31. A Novel Kuhnian Ontology for Epistemic Classification of STM
    > Scholarly Articles - arXiv, 檢索日期：5月 18, 2026，
    > [[https://arxiv.org/html/2002.03531v2]{.underline}](https://arxiv.org/html/2002.03531v2)

32. 2022 Abstract Book - International Society of Exposure Science,
    > 檢索日期：5月 18, 2026，
    > [[https://inses.memberclicks.net/assets/images/Abstracts.Programs/2022%20Abstract.Program%20Book.pdf]{.underline}](https://inses.memberclicks.net/assets/images/Abstracts.Programs/2022%20Abstract.Program%20Book.pdf)

33. Silymarin as a Redox-Signalling and Proteostasis Modulator - MDPI,
    > 檢索日期：5月 18, 2026，
    > [[https://www.mdpi.com/1661-3821/6/2/25]{.underline}](https://www.mdpi.com/1661-3821/6/2/25)

34. Strategic Framing in Communication to Promote Sustainable Consumer
    > Choices Jorge Mario Cáceres Rincón - Pure, 檢索日期：5月 18,
    > 2026，
    > [[https://pure.au.dk/ws/files/421729133/Thesis_Jorge_print.pdf]{.underline}](https://pure.au.dk/ws/files/421729133/Thesis_Jorge_print.pdf)

35. Building information modelling in developing countries: a
    > scientometric, thematic, and research gap analysis - Frontiers,
    > 檢索日期：5月 18, 2026，
    > [[https://www.frontiersin.org/journals/built-environment/articles/10.3389/fbuil.2026.1795619/full]{.underline}](https://www.frontiersin.org/journals/built-environment/articles/10.3389/fbuil.2026.1795619/full)

36. Structural Equation Modeling in Technology Adoption and Use in the
    > Construction Industry: A Scientometric Analysis and Qualitative
    > Review - MDPI, 檢索日期：5月 18, 2026，
    > [[https://www.mdpi.com/2071-1050/16/9/3824]{.underline}](https://www.mdpi.com/2071-1050/16/9/3824)

37. Post 365: The Noospheric AFEI Manifold \... - Answer Overflow,
    > 檢索日期：5月 18, 2026，
    > [[https://cdn.answeroverflow.com/1502768856740135043/Post_365\_\_The_Noospheric_AFEI_Manifold_Foundational_Axiomatic_Lexicon_The_Pathologization_Ladder_558_Pages.pdf]{.underline}](https://cdn.answeroverflow.com/1502768856740135043/Post_365__The_Noospheric_AFEI_Manifold_Foundational_Axiomatic_Lexicon_The_Pathologization_Ladder_558_Pages.pdf)

38. Inflection Points in Academic Career Trajectories: Statistical
    > Modeling and Interactive Visualization - RIT Digital Institutional
    > Repository, 檢索日期：5月 18, 2026，
    > [[https://repository.rit.edu/cgi/viewcontent.cgi?article=13692&context=theses]{.underline}](https://repository.rit.edu/cgi/viewcontent.cgi?article=13692&context=theses)

39. Homecoming After Brexit: Evidence on Academic Migration from
    > Bibliometric Data - Max Planck Institute for Demographic Research,
    > 檢索日期：5月 18, 2026，
    > [[https://www.demogr.mpg.de/papers/working/wp-2022-019.pdf]{.underline}](https://www.demogr.mpg.de/papers/working/wp-2022-019.pdf)

40. The Retraction Epidemic in Science Across Publishers, Fields, and
    > Countries - arXiv, 檢索日期：5月 18, 2026，
    > [[https://arxiv.org/html/2604.02302v1]{.underline}](https://arxiv.org/html/2604.02302v1)

41. Global subnational estimates of migration of scientists reveal large
    > disparities in internal and international flows \| PNAS,
    > 檢索日期：5月 18, 2026，
    > [[https://www.pnas.org/doi/10.1073/pnas.2424521122]{.underline}](https://www.pnas.org/doi/10.1073/pnas.2424521122)

42. Reading Between the Lines: Deconfounding Causal Estimates using Text
    > Embeddings and Deep Learning - arXiv, 檢索日期：5月 18, 2026，
    > [[https://arxiv.org/html/2601.01511v1]{.underline}](https://arxiv.org/html/2601.01511v1)

43. On the Theoretical Limitations of Embedding-Based Retrieval - arXiv,
    > 檢索日期：5月 18, 2026，
    > [[https://arxiv.org/html/2508.21038v1]{.underline}](https://arxiv.org/html/2508.21038v1)

44. Statistical quantification of confounding bias in machine learning
    > models - PMC, 檢索日期：5月 18, 2026，
    > [[https://pmc.ncbi.nlm.nih.gov/articles/PMC9412867/]{.underline}](https://pmc.ncbi.nlm.nih.gov/articles/PMC9412867/)

45. Overcoming false-positive gene-category enrichment in the analysis
    > of spatially resolved transcriptomic brain atlas data - PMC,
    > 檢索日期：5月 18, 2026，
    > [[https://pmc.ncbi.nlm.nih.gov/articles/PMC8113439/]{.underline}](https://pmc.ncbi.nlm.nih.gov/articles/PMC8113439/)

46. IMPACT: Influence Modeling for Open-Set Time Series Anomaly
    > Detection - arXiv, 檢索日期：5月 18, 2026，
    > [[https://arxiv.org/html/2603.29183v1]{.underline}](https://arxiv.org/html/2603.29183v1)

47. Geometric Calibration and Neutral Zones for Uncertainty-Aware
    > Multi-Class Classification, 檢索日期：5月 18, 2026，
    > [[https://arxiv.org/html/2511.20960v1]{.underline}](https://arxiv.org/html/2511.20960v1)

48. Label-Free Calibration of Fraud Rule-Based Detection: Addressing
    > Behavior Heterogeneity, 檢索日期：5月 18, 2026，
    > [[https://www.mdpi.com/2076-3417/16/8/3783]{.underline}](https://www.mdpi.com/2076-3417/16/8/3783)

49. Computer Science - arXiv, 檢索日期：5月 18, 2026，
    > [[https://www.arxiv.org/list/cs/new?skip=200&show=2000]{.underline}](https://www.arxiv.org/list/cs/new?skip=200&show=2000)

50. Replication, Uncertainty and Progress in Comparative Cognition,
    > 檢索日期：5月 18, 2026，
    > [[https://www.animalbehaviorandcognition.org/uploads/journals/33/AB_C_2021_Vol8(2)\_Boyle.pdf]{.underline}](https://www.animalbehaviorandcognition.org/uploads/journals/33/AB_C_2021_Vol8(2)_Boyle.pdf)

51. Epistemic and ethical limits of large language models in
    > evidence-based medicine: from knowledge to judgment - PMC,
    > 檢索日期：5月 18, 2026，
    > [[https://pmc.ncbi.nlm.nih.gov/articles/PMC12864482/]{.underline}](https://pmc.ncbi.nlm.nih.gov/articles/PMC12864482/)

52. Epistemology - Stanford Encyclopedia of Philosophy, 檢索日期：5月
    > 18, 2026，
    > [[https://plato.stanford.edu/entries/epistemology/]{.underline}](https://plato.stanford.edu/entries/epistemology/)

53. Models as Epistemic Artifacts for Scientific Reasoning in Science
    > Education Research, 檢索日期：5月 18, 2026，
    > [[https://www.mdpi.com/2227-7102/12/4/276]{.underline}](https://www.mdpi.com/2227-7102/12/4/276)

54. Conceptualising research environments using biological niche
    > concepts - PMC, 檢索日期：5月 18, 2026，
    > [[https://pmc.ncbi.nlm.nih.gov/articles/PMC11870986/]{.underline}](https://pmc.ncbi.nlm.nih.gov/articles/PMC11870986/)

55. Respond in Style: Personalising Review Response Generation by
    > Optimising Continuous Prefixes - zora.uzh.ch, 檢索日期：5月 18,
    > 2026，
    > [[https://www.zora.uzh.ch/server/api/core/bitstreams/b153bded-f52a-4ff4-b77d-7eed1bdafd33/content]{.underline}](https://www.zora.uzh.ch/server/api/core/bitstreams/b153bded-f52a-4ff4-b77d-7eed1bdafd33/content)

56. Categorizing Strategic Issues: Links to Organizational Action - AOM
    > Journals, 檢索日期：5月 18, 2026，
    > [[https://journals.aom.org/doi/10.5465/AMR.1987.4306483]{.underline}](https://journals.aom.org/doi/10.5465/AMR.1987.4306483)

57. RIGOURATE: Quantifying Scientific Exaggeration with \... - arXiv,
    > 檢索日期：5月 18, 2026，
    > [[https://arxiv.org/pdf/2601.04350]{.underline}](https://arxiv.org/pdf/2601.04350)

58. The Detection of Contradictory Claims in Biomedical Abstracts -
    > White Rose eTheses Online, 檢索日期：5月 18, 2026，
    > [[https://etheses.whiterose.ac.uk/id/eprint/15893/1/FinalThesis-Alamri.pdf]{.underline}](https://etheses.whiterose.ac.uk/id/eprint/15893/1/FinalThesis-Alamri.pdf)

59. Table-Text Alignment: Explaining Claim Verification Against Tables
    > in Scientific Papers, 檢索日期：5月 18, 2026，
    > [[https://aclanthology.org/2025.findings-emnlp.135/]{.underline}](https://aclanthology.org/2025.findings-emnlp.135/)

60. Can AI Validate Science ? Benchmarking LLMs on Claim → Evidence
    > Reasoning in AI Papers - ACL Anthology, 檢索日期：5月 18, 2026，
    > [[https://aclanthology.org/2025.ijcnlp-long.127.pdf]{.underline}](https://aclanthology.org/2025.ijcnlp-long.127.pdf)

61. Benchmarking LLM Agents on Scientific Tasks - Center for Open
    > Science (COS), 檢索日期：5月 18, 2026，
    > [[https://www.cos.io/benchmarking-llm-agents-on-scientific-tasks]{.underline}](https://www.cos.io/benchmarking-llm-agents-on-scientific-tasks)

62. PaperArena: An Evaluation Benchmark for Tool-Augmented Agentic
    > Reasoning on Scientific Literature - arXiv, 檢索日期：5月 18,
    > 2026，
    > [[https://arxiv.org/html/2510.10909v4]{.underline}](https://arxiv.org/html/2510.10909v4)

63. PaperArena: An Evaluation Benchmark for Tool-Augmented Agentic
    > Reasoning on Scientific Literature - arXiv, 檢索日期：5月 18,
    > 2026，
    > [[https://arxiv.org/html/2510.10909v2]{.underline}](https://arxiv.org/html/2510.10909v2)

64. Smarter Sampling for LLM Judges: Reliable Evaluation on a Budget \|
    > OpenReview, 檢索日期：5月 18, 2026，
    > [[https://openreview.net/forum?id=2aBTwSOL0e&referrer=%5Bthe%20profile%20of%20Sanmi%20Koyejo%5D(%2Fprofile%3Fid%3D\~Sanmi_Koyejo1)]{.underline}](https://openreview.net/forum?id=2aBTwSOL0e&referrer=%5Bthe+profile+of+Sanmi+Koyejo%5D(/profile?id%3D~Sanmi_Koyejo1))

65. Knowledge domain and emerging trends in medication literacy research
    > from 2003 to 2024: a scientometric and bibliometric analysis using
    > CiteSpace and VOSviewer - PMC, 檢索日期：5月 18, 2026，
    > [[https://pmc.ncbi.nlm.nih.gov/articles/PMC12234531/]{.underline}](https://pmc.ncbi.nlm.nih.gov/articles/PMC12234531/)
