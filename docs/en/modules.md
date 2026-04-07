# DeepThought Module Reference

This document details the internal responsibilities, key functions, and data contracts of the DeepThought engine's core modules.

## ⚙️ 1. Core Mathematical Engine (`core/`)

### `core/deepthought_equation.py`
The mathematical heart of the system. Implements the **BGE-M3 Dense-Sparse Triad** algorithm, permanently replacing legacy global MMR.
- **`find_hybrid_voids()`**: Executes the primary mathematical filter.
	- Step 1: Evaluates Domain Cohesion via FAISS `Cosine(A, C)` and `Cosine(B, C)`.
	- Step 2: Enforces Cross-Domain Marginality (`τ_low <= Cosine(A, B) <= τ_high`).
	- Step 3: Pings the `SparseIndex` for `Boolean_AND == 0` validation.
- **`calibrate_thresholds()`**: Analyzes historical Git commits across subsystems to dynamically set the `τ_low` and `τ_high` parameters, preventing "Franken-IP" generation.

## 🧠 2. Agentic State Machine (`agents/`)

### `agents/pipeline.py`
The LangGraph orchestrator. Defines the StateGraph, conditional edges, and handles the `MAX_RETRIES` loop for the Conference Review simulation. Manages the shared `PipelineState` dataclass.

### `agents/forager.py`
- **Role:** Retrieval orchestrator.
- **Action:** Wraps `deepthought_equation.py`, passes the domain targets, and formats the returned `VoidLandscape` into prompt-injectable context blocks for the Maverick.

### `agents/maverick.py` (The Author)
- **Role:** Divergent generation and revision processing.
- **Action:** Submits the initial `RFC Draft` based on Forager's concept anchors. If triggered by a `REVISE` state, it ingests diagnostic metrics from the Reality Checker to mutate and patch the architectural design.

### `agents/patent_shield.py` (The Fast-Fail Gate)
- **Role:** API-driven global prior-art screening.
- **Action:** Extracts keywords from the draft and queries Semantic Scholar / Google Patents APIs. Flags exact matches to bypass expensive downstream LLM processing.

### `agents/reality_checker.py` (Reviewer 2)
- **Role:** Technical constraint validator.
- **Action:** Evaluates drafts against physical constraints (e.g., Memory Ordering, x86 ISA limits, Kernel ABI). 
- **Output:** Returns structured diagnostic payloads (e.g., `{ "status": "REVISE", "metric": "Cache line bounce detected in struct X", "severity": "HIGH" }`) instead of raw text.

### `agents/debate_panel.py`
- **Role:** Multi-model consensus and synthesis.
- **Action:** Acts as the Program Committee. Reviews the original draft, the Reality Checker's critique logs, and the Maverick's rebuttal/mutations. Outputs the final `APPROVED` or `REJECTED` verdict with a detailed technical rationale.

## 🗄️ 3. Hybrid Vector Database (`vectordb/`)

### `vectordb/store.py`
The unified data access layer.
- Manages the local `ChromaDB` collections (or raw FAISS indices) for 1024D Dense Vector storage.
- Routes semantic similarity queries (KNN) to the Dense backend.

### `vectordb/sparse_index.py`
The exact-match sidecar index (implemented via SQLite FTS5 or Elasticsearch backend).
- **Responsibility:** Maintains the inverted index of the Top-N BGE-M3 sparse lexical tokens.
- **Function:** Provides the `check_absolute_vacuum(concept_a, concept_b)` method that guarantees zero historical co-occurrence.

### `vectordb/embedder.py`
- Local embedding factory. Instantiates and caches the `BAAI/bge-m3` model via HuggingFace / ONNX. Forces 100% offline execution.

## 📥 4. Data Collection & Ingestion (`data_collection/`)

### `data_collection/crawler/`
- `kernel_crawler.py`: Clones specific kernel subsystems, parses Git history for collision calibration.
- `pdf_parser.py`: Extracts text and tables from Intel SDM and optimization manuals.

### `data_collection/parser/tree_sitter_parser.py`
- **AST-Aware Parsing:** Replaces naive text-splitting. Uses Tree-sitter `C` and `Rust` grammars to extract logically complete functions, structs, and macro definitions. Ensures that embeddings represent full code semantics, not broken text fragments.

## 🏭 5. System Services (`services/`)

### `services/pipeline_service.py`
- The continuous execution daemon. Wraps the LangGraph pipeline for 24/7 "Nightly Mining". Handles loop intervals, configuration overriding, and crash recovery.

### `services/audit_logger.py`
- **Responsibility:** Append-only JSONL logging. Records the entire state machine trace (Prompts, Outputs, Revision Metrics, and Final Verdicts) to prove the "non-obviousness" history for patent filing.

### `services/tid_notification_service.py`
- SMTP webhook. Fires asynchronous alerts containing a summary of the IP when the state machine hits `APPROVED_AND_EXPORTED`.

## 📤 6. Execution & Output (`output/`)

### `output/tid_formatter.py`
- Template engine (Jinja2). Maps the unstructured JSON consensus output from the Debate Panel into strict, lawyer-ready Technical Invention Disclosure (TID) markdown/HTML files.

### `output/claim_analysis.py`
- Auto-generates independent and dependent patent claims based on the final approved architecture. Assigns confidence scores to each claim based on prior-art distance.
