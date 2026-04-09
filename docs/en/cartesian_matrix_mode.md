# Cartesian Matrix Target Generation Mode

## Problem Statement

Previous random-walk mutation generated targets that were too wild, causing:
- **53% RETRY_PENDING** due to "No topological voids found"
- **93.7% REJECTED** due to architecturally unsound proposals
- Maverick proposing unrealistic cross-subsystem bridges (e.g., Wi-Fi + clockevent)

Root cause: LLM-generated targets drifted into "outer space" — combinations with no historical evidence in the corpus.

## Solution: Cartesian Matrix Mode

Replace unbounded random mutation with a **deterministic 100-target grid**:

```
10 Intel Keywords × 10 Linux Subsystems = 100 stable targets
```

### Intel Keywords (High-Value Patent Technologies)
- TDX, eBPF, CXL, AMX, PEBS, TSX, APIC, EPT, AVX-512, RAPL

### Linux Subsystems (Major Architectural Domains)
- scheduler, memory management, networking, file system, block I/O
- interrupt handling, virtualization, device driver, synchronization, power management

### Target Format
```
Optimize Linux {subsystem} using x86 {keyword} microarchitecture features
```

Example targets:
- `Optimize Linux scheduler using x86 TDX microarchitecture features`
- `Optimize Linux memory management using x86 CXL microarchitecture features`
- `Optimize Linux virtualization using x86 EPT microarchitecture features`

## Configuration

**Enable Cartesian Mode (default):**
```bash
# In .env or configs/settings.py
TARGET_GENERATION_MODE=cartesian
```

**Revert to Random Walk:**
```bash
TARGET_GENERATION_MODE=random_walk
```

## Behavior

**Cartesian Mode:**
- Sequentially iterates through all 100 targets
- Wraps around after completing the matrix
- Guarantees physically plausible, corpus-grounded targets
- Each target is stable and repeatable

**Random Walk Mode:**
- Samples random chunk from VectorDB
- LLM mutates it into a new target
- Higher creativity, higher risk of "void drift"

## Expected Outcomes

With Cartesian mode + architecture rules + relaxed domain threshold:

**Before (Random Walk):**
- APPROVED: 0.06% (1/1556)
- RETRY_PENDING (No voids): 53/97 (55%)
- REJECTED: 93.7%

**Target (Cartesian):**
- APPROVED: 2-5% (validate system at baseline before re-enabling mutation)
- RETRY_PENDING (No voids): <10%
- REJECTED: <70% (quality filter working, but less noise)

## Implementation Details

**Files:**
- `services/target_cartesian_matrix.py` — Matrix generator
- `configs/settings.py` — `target_generation_mode` switch
- `scripts/run_pipeline_service.py` — Mode selection logic

**Changes:**
1. **Cartesian Matrix** replaces wild mutation with 100 stable anchors
2. **Maverick Architecture Rules** prevent async/sync mixing, debug-interface abuse, boot/runtime confusion
3. **Forager τ Relaxation** (0.45 → 0.42) expands candidate pool by ~7% to reduce "No voids found"

## Running the Service

```bash
# Cartesian mode (default)
python scripts/run_pipeline_service.py \
  --auto-target \
  --collection kernel_source \
  --collection hardware_specs \
  --n-drafts 2 \
  --top-k-voids 8 \
  --interval-seconds 180 \
  --skip-duplicate-input \
  --no-delay-on-failure

# The service will iterate through all 100 targets sequentially
# Monitor: data/processed/pipeline_runs.jsonl for APPROVED rate
```

## Validation Plan

**Phase 1 (Current):** Run 100 iterations with Cartesian mode
- Target: 2-5 APPROVED TIDs
- Validate system baseline quality

**Phase 2 (If successful):** Re-enable intelligent mutation
- Use successful targets as seed templates
- Add corpus-grounded mutation constraints
- Maintain 2-5% APPROVED floor

**Phase 3 (Production):** Hybrid mode
- 70% Cartesian (stable baseline)
- 30% Mutation (creative exploration)
