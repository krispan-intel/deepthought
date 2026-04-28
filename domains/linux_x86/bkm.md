# BKM — linux_x86 Domain

This file is the accumulated institutional knowledge for the linux_x86 domain.
It is read by the Curator agent and by human operators.
**Do not hardcode domain knowledge into Python — write it here.**

---

## k Calibration

**2026-04-21**: k=0.001 chosen. D*=1063, nearest standard dim 1024D.
BGE-M3 1024D lies within 4% of theoretical optimum.
See calibration.json for full sensitivity table.

To recalibrate after corpus growth:
```bash
python scripts/run_dimension_analysis.py --collection kernel_source --sample 10000
```
Update calibration.json with new values.

---

## Specialist Lessons

See `specialists/*.md` — each file has a "What I have learned" section
that accumulates run-by-run lessons.

---

## Known Domain Patterns

- **TSX proposals**: valid if X86_FEATURE_RTM gating is explicit and
  fail-closed. Security Guardian frequently raises TAA policy as concern —
  require explicit admissibility check in implementation plan.

- **RCU patterns**: Kernel Hardliner is strict. Proposals must specify
  which RCU flavor (rcu_read_lock vs srcu) and quiescent state strategy.

- **APIC / IPI batching**: Prior-Art Shark will check against existing
  x2apic_cluster.c work. Claims must be narrowed to the specific
  optimization trigger (density threshold, epoch-versioning).

---

## PR #2–4 (Future Work for Next AI)

The following improvements are scoped out but not yet implemented.
A Curator agent or future contributor should pick these up:

### PR #2 — Move remaining hardcoded domain strings
- `core/deepthought_equation.py`: `KERNEL_STOP_WORDS` → move to
  `domains/linux_x86/stopwords.txt`, load dynamically
- `scripts/ingest_kernel.py`: hardcoded paths/subsystems → move to
  `domain.yaml` under `ingest.default_subsystems`
- `agents/maverick.py`: Linux/x86 terminology in system prompt →
  make domain-aware via `domain.yaml`

### PR #3 — domain_bootstrapper agent
Convert `BKM_ONBOARDING.md` conversation flow into an executable agent:
```bash
python -m curator.domain_bootstrapper --interactive
# Generates domains/<new_domain>/ from scratch via AI conversation
# No more "paste into debate_panel.py"
```

### PR #4 — bkm_updater (Curator meta-loop)
```bash
python -m curator.bkm_updater --domain linux_x86 --since "7 days ago" --propose-pr
```
Reads recent verdict logs, identifies specialist prompt weaknesses,
proposes PRs to update `specialists/*.md` "What I have learned" sections.
