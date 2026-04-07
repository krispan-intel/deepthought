# DeepThought Pipeline Flow

## End-to-End Execution Flow

1. **Mission Injection (Input)**
	- The user or service daemon injects a Target Domain (e.g., `Linux Scheduler`), Optimization Goal (e.g., `Latency Reduction`), and any prior-art limits.

2. **Phase 1: Void Detection (Forager)**
	- **Action:** Queries the Hybrid Data Tier using the BGE-M3 Triad filter.
	- **Output:** Returns a `VoidLandscape` payload containing `Concept A` and `Concept B` that are semantically compatible but have zero historical overlap.

3. **Phase 2: Draft Generation (Maverick)**
	- **Action:** Uses the `VoidLandscape` to synthesize a cross-domain solution.
	- **Output:** Generates `N` divergent RFC (Request for Comments) structured drafts.

4. **Phase 3: The Patent Shield (Fast-Fail)**
	- **Action:** Extracts key claims from the drafts and pings external APIs.
	- **Output:** Immediately halts the branch if a direct 1:1 prior-art conflict is detected.

5. **Phase 4: Conference Review Simulation (The Loop)**
	- **Action:** The Reality Checker evaluates the physical feasibility of the RFC.
	- **Decision Node:**
	  - `APPROVE`: Proceeds to Synthesis.
	  - `REJECT`: Fatal flaw detected, draft dropped.
	  - `REVISE`: Generates specific diagnostic feedback (e.g., lock contention, cache misses).
	- **Mutation:** If `REVISE`, the Maverick receives the feedback and updates the architecture. This loops until `APPROVE` or `MAX_RETRIES` is hit.

6. **Phase 5: Committee Synthesis (Debate Panel)**
	- **Action:** Aggregates the surviving drafts, the revision history, and the critique logs.
	- **Output:** Selects the single most defensible patent concept.

7. **Phase 6: Artifact Minting (Export)**
	- **Action:** Formats the final state into a Technical Invention Disclosure (TID) and fires email notifications.

## LangGraph State Transitions

- `[PENDING]` $\rightarrow$ `[FORAGING]`
- `[FORAGING]` $\rightarrow$ `[DRAFTING]`
- `[DRAFTING]` $\rightarrow$ `[REVIEW_EVALUATION]`
- `[REVIEW_EVALUATION]` $\rightarrow$ `[MUTATION_REVISION]` (Loop trigger)
- `[REVIEW_EVALUATION]` $\rightarrow$ `[REJECTED]` (Terminal)
- `[REVIEW_EVALUATION]` $\rightarrow$ `[COMMITTEE_CONSENSUS]`
- `[COMMITTEE_CONSENSUS]` $\rightarrow$ `[APPROVED_AND_EXPORTED]` (Success)
