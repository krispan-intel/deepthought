"""
scripts/run_idea_collision.py

Run single-LLM idea collision on top of DeepThought void context,
then emit Markdown + HTML TID reports.

Usage:
  python scripts/run_idea_collision.py \
    --domain linux_kernel \
    --target "scheduler latency optimization" \
    --collection kernel_source \
    --domain-filter scheduler \
    --n-ideas 3
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from output.tid_formatter import TIDDetail, TIDReport, TIDScorecard, TIDSummary
from services.idea_collision_service import IdeaCollisionService


def _slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("_") or "idea"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate invention ideas using DeepThought void context + one LLM"
    )
    parser.add_argument("--domain", required=True, help="Domain label, e.g. linux_kernel")
    parser.add_argument("--target", required=True, help="Target optimization goal")
    parser.add_argument(
        "--collection",
        action="append",
        default=[],
        help="Collection to search (repeatable), e.g. kernel_source",
    )
    parser.add_argument(
        "--existing",
        action="append",
        default=[],
        help="Existing solution text for novelty conditioning (repeatable)",
    )
    parser.add_argument("--domain-filter", default=None, help="Optional subsystem filter")
    parser.add_argument("--lambda-val", type=float, default=0.7, help="MMR lambda in [0,1]")
    parser.add_argument("--top-k-voids", type=int, default=5, help="Void candidates count")
    parser.add_argument("--n-ideas", type=int, default=3, help="Number of ideas to generate")
    parser.add_argument("--model", default=None, help="Override LLM model")
    parser.add_argument("--temperature", type=float, default=0.8, help="LLM temperature")
    parser.add_argument("--output-dir", default="output/generated", help="Output directory")
    parser.add_argument("--tid-prefix", default="TID-AUTO", help="TID ID prefix")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    service = IdeaCollisionService(model=args.model, temperature=args.temperature)
    candidates = service.generate(
        domain=args.domain,
        target=args.target,
        existing_solutions=args.existing,
        collection_names=args.collection,
        domain_filter=args.domain_filter,
        lambda_val=args.lambda_val,
        top_k_voids=args.top_k_voids,
        n_ideas=args.n_ideas,
    )

    if not candidates:
        print("No valid idea candidates generated.")
        return 1

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for i, c in enumerate(candidates, start=1):
        report = TIDReport(
            tid_id=f"{args.tid_prefix}-{i:03d}",
            title=c.title,
            domain=args.domain,
            target=args.target,
            summary=TIDSummary(
                one_liner=c.one_liner,
                novelty_thesis=c.novelty_thesis,
                feasibility_thesis=c.feasibility_thesis,
                market_thesis=c.market_thesis,
                why_now=c.why_now,
            ),
            scorecard=TIDScorecard(
                innovation=c.innovation,
                implementation_difficulty=c.implementation_difficulty,
                commercial_value=c.commercial_value,
                technical_risk=c.technical_risk,
                prior_art_conflict_risk=c.prior_art_conflict_risk,
            ),
            detail=TIDDetail(
                problem_statement=c.problem_statement,
                prior_art_gap=c.prior_art_gap,
                proposed_invention=c.proposed_invention,
                architecture_overview=c.architecture_overview,
                implementation_plan=c.implementation_plan,
                validation_plan=c.validation_plan,
                draft_claims=c.draft_claims,
                risks_and_mitigations=c.risks_and_mitigations,
                references=c.references,
            ),
        )

        base_name = f"{report.tid_id}_{_slugify(c.title)[:64]}"
        md_path, html_path = report.save(out_dir, base_name=base_name)
        print(f"[{i}] {c.title}")
        print(f"  md:   {md_path}")
        print(f"  html: {html_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
