# DeepThought Architecture

## Overview
DeepThought implements a decoupled 3-tier architecture. This design guarantees that data ingestion (heavy I/O), agent reasoning (heavy LLM inference), and output formatting remain isolated, allowing for independent scaling and asynchronous execution.

## Tier 1: Hybrid Data Tier (The Foundation)

### Responsibilities
- **Absolute Knowledge Boundary:** Establishes the "known universe" of prior art via local processing.
- **Dual-Engine Indexing:** Generates both Dense (Semantic) and Sparse (Lexical) representations for every code chunk.

### Core Mechanisms
- **Tree-sitter Parsing Pipeline:** Generates AST-aware chunks instead of naive text-splitting. It understands function boundaries, struct definitions, and Kconfig dependencies.
- **BGE-M3 Dual Encoder:**
	- Generates `1024D Dense Vectors` for conceptual similarity (stored in ChromaDB/FAISS).
	- Extracts `Top-N Sparse Tokens` for absolute keyword tracking (stored in SQLite FTS5 / Elasticsearch).
- **The Absolute Void Filter:** Mathematically ensures that retrieved concepts `A` and `B` have `Boolean_AND == 0` historical co-occurrence in the sparse index.

## Tier 2: Logic Tier (The Evolutionary Brain)

### Responsibilities
- Orchestrates the multi-agent invention synthesis via a LangGraph state machine.
- Enforces the **Conference Review Simulated Framework** (Generate $\rightarrow$ Critique $\rightarrow$ Mutate).

### The Agentic Committee
1. **Forager:** The math engine. Executes the Dense-Sparse Triad equation to pinpoint topological voids.
2. **Maverick (The Author):** The divergent thinker. Drafts TIDs targeting the voids discovered by the Forager.
3. **Patent Shield:** The fast-fail gatekeeper. Pre-screens drafts against global APIs (e.g., Semantic Scholar) before wasting expensive reviewer tokens.
4. **Reality Checker (Reviewer 2):** The strict evaluator. Validates against physical constraints (x86 ISA, Memory Ordering, Kernel ABI). Instead of binary rejection, it outputs *diagnostic metrics* (e.g., "Potential Race Condition in line 42").
5. **Debate Panel (The Program Committee):** Synthesizes the Maverick's revisions and the Reality Checker's critiques to reach a final consensus.

### State Machine Guarantees
- **Evolutionary Loop:** Maverick is forced to revise drafts based on Reality Checker metrics up to a `MAX_RETRIES` limit (typically 3-5).
- **Fatal Flaw Rejection:** Concepts violating immutable physical laws are permanently pruned.

## Tier 3: Execution Tier (The Factory Output)

### Responsibilities
- Transforms approved, unstructured agent thoughts into structured, lawyer-ready artifacts.
- Manages the lifecycle of continuous "Nightly Mining" services.

### Components
- **TID Formatter:** Maps agent outputs to standardized IP legal templates (Markdown, HTML, DOCX, PDF).
- **Audit Logger:** Captures the entire agent debate transcript (the "Rebuttal history") as proof of non-obviousness.
- **Notification Hook:** Asynchronous SMTP alerting when a `APPROVED` patent draft is successfully minted.
