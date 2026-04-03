"""
scripts/run_pipeline.py

Run DeepThought multi-agent pipeline end-to-end.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from configs.settings import settings
from services.pipeline_service import PipelineService
from services.status_store import PipelineStatusStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run DeepThought multi-agent pipeline")
    parser.add_argument("--domain", default="", help="Domain label")
    parser.add_argument("--target", default="", help="Target optimization goal")
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
        help="Existing solutions for novelty conditioning (repeatable)",
    )
    parser.add_argument("--domain-filter", default=None, help="Optional subsystem filter")
    parser.add_argument("--lambda-val", type=float, default=0.7, help="MMR lambda")
    parser.add_argument("--n-drafts", type=int, default=3, help="Maverick draft count")
    parser.add_argument("--top-k-voids", type=int, default=5, help="Forager top-k voids")
    parser.add_argument("--output-dir", default="output/generated", help="Report output directory")
    parser.add_argument("--tid-prefix", default="TID-MA", help="TID ID prefix")
    parser.add_argument("--status-file", default=None, help="Optional pipeline status jsonl path")
    parser.add_argument("--retry-failed", action="store_true", help="Retry the latest failed run from status store")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    service = PipelineService()
    status_store = PipelineStatusStore(file_path=args.status_file)

    print(f"LLM base URL: {settings.internal_llm_base_url}")
    print(f"Maverick model: {settings.maverick_model}")
    print(f"Reality checker model: {settings.reality_checker_model}")
    print(f"OPENAI_API_BASE set: {'yes' if os.environ.get('OPENAI_API_BASE') else 'no'}")
    print(f"INTERNAL_LLM_BASE_URL set: {'yes' if os.environ.get('INTERNAL_LLM_BASE_URL') else 'no'}")

    if args.retry_failed:
        retry_input = status_store.latest_retry_input()
        if not retry_input:
            print("No RETRY_PENDING run found in status store.")
            return 1

        args.domain = retry_input.get("domain", args.domain)
        args.target = retry_input.get("target", args.target)
        args.existing = retry_input.get("existing_solutions", args.existing)
        args.collection = retry_input.get("collection_names", args.collection)
        args.domain_filter = retry_input.get("domain_filter", args.domain_filter)
        args.lambda_val = float(retry_input.get("lambda_val", args.lambda_val))
        args.n_drafts = int(retry_input.get("n_drafts", args.n_drafts))
        args.top_k_voids = int(retry_input.get("top_k_voids", args.top_k_voids))
        args.output_dir = retry_input.get("output_dir", args.output_dir)
        args.tid_prefix = retry_input.get("tid_prefix", args.tid_prefix)
    else:
        if not args.domain or not args.target:
            print("--domain and --target are required unless --retry-failed is used")
            return 2

    state = service.run(
        domain=args.domain,
        target=args.target,
        existing_solutions=args.existing,
        collection_names=args.collection,
        domain_filter=args.domain_filter,
        lambda_val=args.lambda_val,
        n_drafts=args.n_drafts,
        top_k_voids=args.top_k_voids,
        output_dir=args.output_dir,
        tid_prefix=args.tid_prefix,
    )

    status_path = status_store.append(state)

    print("Pipeline completed")
    print(f"Run ID: {state.run_id}")
    print(f"Run status: {state.run_status}")
    print(f"Drafts: {len(state.drafts)}")
    print(f"Void statuses: {len(state.void_statuses)}")
    print(f"TID statuses: {len(state.tid_statuses)}")
    if state.failed_stages:
        print(f"Failed stages: {', '.join(state.failed_stages)}")
        print(f"Last error: {state.last_error}")
    if state.debate_result:
        print(f"Debate verdict: {state.debate_result.final_verdict}")
        print(f"Winning title: {state.debate_result.winning_title}")
        print(f"Confidence: {state.debate_result.confidence:.2f}")
    if state.output_paths:
        print(f"Markdown: {state.output_paths.get('markdown', '')}")
        print(f"HTML: {state.output_paths.get('html', '')}")
    print(f"Status file: {status_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
