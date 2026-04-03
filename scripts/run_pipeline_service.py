"""
scripts/run_pipeline_service.py

Run DeepThought pipeline in service mode (continuous loop) and optionally
send email notifications when new TID outputs are generated.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

from configs.settings import settings
from services.pipeline_service import PipelineService
from services.status_store import PipelineStatusStore
from services.target_mutation_service import DEFAULT_MUTATION_HINT, TargetMutationService
from services.tid_notification_service import TIDNotificationService


DEFAULT_TARGET = "Generate new x86 IP or any improvement to any part of the Linux kernel on x86"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run DeepThought in continuous service mode")
    parser.add_argument("--domain", default="all_domains", help="Domain label (non-restrictive by default)")
    parser.add_argument("--target", default=DEFAULT_TARGET, help="Target optimization goal")
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
    parser.add_argument("--top-k-voids", type=int, default=10, help="Forager top-k voids")
    parser.add_argument("--output-dir", default="output/generated", help="Report output directory")
    parser.add_argument("--tid-prefix", default="TID-SVC", help="TID ID prefix")
    parser.add_argument("--status-file", default=None, help="Optional pipeline status jsonl path")
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=settings.service_loop_interval_seconds,
        help="Interval between service iterations",
    )
    parser.add_argument(
        "--random-walk-mutate",
        action="store_true",
        help="Sample random chunk from VectorDB and mutate it into a new target before retrieval",
    )
    parser.add_argument(
        "--mutation-seed-hint",
        default=DEFAULT_MUTATION_HINT,
        help="Instruction used by LLM when mutating random seed chunk",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run until one APPROVED TID is produced (non-approved iterations do not count)",
    )
    parser.add_argument(
        "--skip-duplicate-input",
        action="store_true",
        help="Skip iteration when the same input already has APPROVED/COMPLETED status",
    )
    return parser.parse_args()


def run_once(args: argparse.Namespace):
    service = PipelineService()
    status_store = PipelineStatusStore(file_path=args.status_file)
    notifier = TIDNotificationService()
    effective_target = args.target
    mutation_info = {}

    if args.random_walk_mutate:
        mutator = TargetMutationService()
        mutation_info = mutator.mutate_target(
            base_target=args.target,
            collection_names=args.collection,
            mutation_hint=args.mutation_seed_hint,
        )
        effective_target = mutation_info.get("mutated_target", args.target)
        print("Random walk mutation applied")
        print(f"Seed collection: {mutation_info.get('seed_collection', '')}")
        print(f"Seed label: {mutation_info.get('seed_label', '')}")
        print(f"Mutated target: {effective_target}")

    input_payload = {
        "domain": args.domain,
        "target": effective_target,
        "existing_solutions": args.existing,
        "collection_names": args.collection,
        "domain_filter": args.domain_filter,
        "lambda_val": args.lambda_val,
        "n_drafts": args.n_drafts,
        "top_k_voids": args.top_k_voids,
        "output_dir": args.output_dir,
        "tid_prefix": args.tid_prefix,
        "random_walk_mutate": bool(args.random_walk_mutate),
        "mutation_seed_hint": args.mutation_seed_hint if args.random_walk_mutate else "",
        "mutation_seed_doc_id": mutation_info.get("seed_doc_id", ""),
        "mutation_seed_collection": mutation_info.get("seed_collection", ""),
        "mutation_seed_label": mutation_info.get("seed_label", ""),
    }

    if args.skip_duplicate_input and status_store.has_completed_input(input_payload):
        status_path = status_store.append_skipped(input_payload=input_payload)
        print("Service iteration skipped (duplicate input already completed)")
        print(f"Status file: {status_path}")
        return None

    state = service.run(
        domain=args.domain,
        target=effective_target,
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
    notified = False
    try:
        notified = notifier.notify_new_tid(state)
    except Exception as exc:
        logger.warning(f"Email notification failed: {exc}")

    print("Service iteration completed")
    print(f"Run ID: {state.run_id}")
    print(f"Run status: {state.run_status}")
    print(f"Status file: {status_path}")
    if state.failed_stages:
        print(f"Failed stages: {', '.join(state.failed_stages)}")
    if state.last_error:
        print(f"Last error: {state.last_error}")
    if state.output_paths:
        print(f"Markdown: {state.output_paths.get('markdown', '')}")
        print(f"HTML: {state.output_paths.get('html', '')}")
    print(f"Email notified: {'yes' if notified else 'no'}")
    return state


def main() -> int:
    args = parse_args()
    if args.interval_seconds <= 0:
        raise ValueError("--interval-seconds must be positive")

    print(f"Service mode start | interval={args.interval_seconds}s")
    print(f"LLM backend: {settings.llm_backend}")
    if settings.llm_backend == "copilot_cli":
        print(f"Copilot CLI command: {settings.copilot_cli_command}")
    else:
        print(f"LLM base URL: {settings.internal_llm_base_url}")
        print(f"Maverick model: {settings.maverick_model}")

    if args.once:
        attempt = 0
        while True:
            attempt += 1
            print(f"Once-mode attempt: {attempt}")
            try:
                state = run_once(args)
            except Exception as exc:
                logger.exception(f"Once-mode iteration crashed: {exc}")
                state = None

            if state and state.run_status == "APPROVED" and state.output_paths:
                print("Once-mode satisfied: APPROVED TID generated.")
                return 0

            print("Once-mode continuing: no APPROVED TID yet.")
            time.sleep(args.interval_seconds)

    while True:
        try:
            run_once(args)
        except Exception as exc:
            logger.exception(f"Service iteration crashed: {exc}")
        time.sleep(args.interval_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
