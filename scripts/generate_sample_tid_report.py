"""
scripts/generate_sample_tid_report.py

Generate a sample TID report in both markdown and html.

Usage:
    python scripts/generate_sample_tid_report.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from output.tid_formatter import TIDDetail, TIDReport, TIDScorecard, TIDSummary


def main() -> int:
    report = TIDReport(
        tid_id="TID-DEMO-0001",
        title="Adaptive Cross-Subsystem Cache Hinting for Linux Scheduler + Memory Paths",
        domain="linux_kernel",
        target="scheduler latency optimization",
        summary=TIDSummary(
            one_liner="Use runtime-derived scheduling pressure to drive cache hint propagation in memory hot paths.",
            novelty_thesis="Bridges scheduler pressure signals with memory path hinting where prior art is sparse.",
            feasibility_thesis="Can be implemented incrementally with tracepoints, BPF validation, and guarded kernel flags.",
            market_thesis="Useful for latency-sensitive infra workloads and can be packaged as kernel optimization IP.",
            why_now="Mature observability in modern kernels enables low-risk staged rollout.",
        ),
        scorecard=TIDScorecard(
            innovation=4,
            implementation_difficulty=4,
            commercial_value=4,
            technical_risk=3,
            prior_art_conflict_risk=2,
        ),
        detail=TIDDetail(
            problem_statement=(
                "Kernel scheduling and memory behavior are often optimized in isolation, creating avoidable tail latency."
            ),
            prior_art_gap=(
                "Existing mechanisms tune scheduler or memory independently; little evidence for dynamic cross-subsystem hint coupling."
            ),
            proposed_invention=(
                "Introduce a policy layer that converts scheduler pressure vectors into cache/memory path hints at bounded cadence."
            ),
            architecture_overview=(
                "Signal extractor -> policy mapper -> hint applier -> feedback loop; each stage is separately switchable."
            ),
            implementation_plan=(
                "Phase 1 trace-only, Phase 2 shadow hints, Phase 3 guarded activation with subsystem allowlists."
            ),
            validation_plan=(
                "Measure p95/p99 latency, context-switch cost, cache miss rate, and regression under synthetic and prod-like workloads."
            ),
            draft_claims=[
                "A method for generating memory path hints from scheduler pressure vectors in kernel runtime.",
                "A bounded-frequency hint propagation mechanism with adaptive rollback based on latency regression.",
                "A cross-subsystem control policy with pluggable mapping functions and safety gates.",
            ],
            risks_and_mitigations=[
                "Risk: hint oscillation under bursty load. Mitigation: hysteresis + cooldown windows.",
                "Risk: subsystem coupling regressions. Mitigation: per-subsystem feature gates and staged rollout.",
            ],
            references=[
                "Linux scheduler docs",
                "Kernel memory management docs",
                "Internal benchmark traces",
            ],
        ),
    )

    out_dir = Path("output/generated")
    md_path, html_path = report.save(out_dir, base_name="tid_demo_report")

    print(f"Generated markdown: {md_path}")
    print(f"Generated html:     {html_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
