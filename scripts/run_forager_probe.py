"""
scripts/run_forager_probe.py

Standalone Forager probe for inspecting hybrid triad scores.

Example:
    python scripts/run_forager_probe.py --domain-term ctags --domain-term tree-sitter --anchor RAG
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.forager import ForagerAgent
from agents.state import PipelineState
from vectordb.store import CollectionName


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe Forager triad scores for a custom anchor/domain combination")
    parser.add_argument(
        "--domain-term",
        action="append",
        default=[],
        help="Domain concept to blend into the target query. Repeatable.",
    )
    parser.add_argument(
        "--anchor",
        required=True,
        help="Primary anchor concept, for example: RAG",
    )
    parser.add_argument(
        "--domain",
        default="custom_probe",
        help="Pipeline domain label recorded in state metadata.",
    )
    parser.add_argument(
        "--collection",
        action="append",
        choices=[c.value for c in CollectionName],
        help="Optional collection filter. Repeatable.",
    )
    parser.add_argument(
        "--existing",
        action="append",
        default=[],
        help="Known existing solution text used as novelty baseline. Repeatable.",
    )
    parser.add_argument(
        "--domain-filter",
        default=None,
        help="Optional metadata subsystem filter passed into vector retrieval.",
    )
    parser.add_argument(
        "--lambda-val",
        type=float,
        default=0.7,
        help="MMR / hybrid triad lambda in [0, 1].",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="How many voids to print.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the structured Forager observation payload as JSON.",
    )
    return parser.parse_args()


def build_target(anchor: str, domain_terms: List[str]) -> str:
    pieces = [anchor.strip()]
    cleaned_terms = [term.strip() for term in domain_terms if term.strip()]
    if cleaned_terms:
        pieces.append(" ".join(cleaned_terms))
    return " ".join(piece for piece in pieces if piece).strip()


def print_summary(state: PipelineState) -> None:
    report = state.metadata.get("forager_observations", {})
    top_voids = report.get("top_voids", [])

    print("\n=== Forager Probe ===")
    print(f"run_id:      {state.run_id}")
    print(f"domain:      {state.domain}")
    print(f"target:      {state.target}")
    print(f"void_count:  {report.get('void_count', 0)}")
    print(f"lambda:      {report.get('lambda', state.lambda_val)}")
    print(f"mode:        {report.get('search_mode', 'unknown')}")

    if not top_voids:
        print("\n(no triads found)")
        return

    print("\n=== Triad Scores ===")
    for item in top_voids:
        print(f"\n[{item['rank']}] Anchor C: {item['anchor_c']}")
        print(f"    Anchor A: {item['anchor_a']}")
        print(f"    Anchor B: {item['anchor_b']}")
        print(f"    domain_score:      {item['domain_score']:.4f}")
        print(f"    pairwise_score:    {item['pairwise_score']:.4f}")
        print(f"    mmr_score:         {item['mmr_score']:.4f}")
        print(f"    relevance_score:   {item['relevance_score']:.4f}")
        print(f"    novelty_score:     {item['novelty_score']:.4f}")
        print(
            f"    marginality_band:  [{item['marginality_low']:.4f}, {item['marginality_high']:.4f}]"
        )
        print(f"    sparse_overlap:    {item['sparse_overlap_count']}")
        print(f"    sparse_tokens:     {', '.join(item['sparse_anchor_tokens']) or '(none)'}")


def main() -> int:
    args = parse_args()
    if not 0.0 <= args.lambda_val <= 1.0:
        raise ValueError("--lambda-val must be between 0.0 and 1.0")
    if args.top_k <= 0:
        raise ValueError("--top-k must be positive")

    target = build_target(args.anchor, args.domain_term)
    state = PipelineState(
        domain=args.domain,
        target=target,
        existing_solutions=args.existing,
        collection_names=args.collection or [],
        domain_filter=args.domain_filter,
        lambda_val=args.lambda_val,
    )

    state = ForagerAgent().run(state, top_k=args.top_k)

    if args.json:
        print(json.dumps(state.metadata.get("forager_observations", {}), indent=2, ensure_ascii=False))
    else:
        print_summary(state)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())