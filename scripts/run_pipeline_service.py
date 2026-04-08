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
from services.io_writer import IOWriterService
from services.pipeline_service import PipelineService
from services.status_store import PipelineStatusStore
from services.target_mutation_service import DEFAULT_MUTATION_HINT, TargetMutationService
from services.tid_notification_service import TIDNotificationService


DEFAULT_TARGET = ""
AUTO_BASE_TARGET = "Derive a high-value x86/Linux kernel optimization target from sampled evidence"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run DeepThought in continuous service mode")
    parser.add_argument("--domain", default="all_domains", help="Domain label (non-restrictive by default)")
    parser.add_argument("--target", default=DEFAULT_TARGET, help="Target optimization goal (optional in auto-target mode)")
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
        "--auto-target",
        action="store_true",
        help="Auto-generate target from random sampled chunks each iteration (implies --random-walk-mutate)",
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
    parser.add_argument(
        "--verbose-review-logs",
        action="store_true",
        help="Print conference review / committee / judge traces to terminal",
    )
    parser.add_argument(
        "--no-delay-on-reject",
        action="store_true",
        help="Start next iteration immediately when run_status is REJECTED",
    )
    parser.add_argument(
        "--no-delay-on-failure",
        action="store_true",
        help="Start next iteration immediately on any failed run status (REJECTED/RETRY_PENDING) or crash",
    )
    return parser.parse_args()


def _print_review_traces(state) -> None:
    metadata = state.metadata or {}

    review_trace = metadata.get("conference_review_trace", [])
    if isinstance(review_trace, list) and review_trace:
        print("[review] conference trace")
        for event in review_trace[-3:]:
            event_type = event.get("event", "unknown")
            round_id = event.get("round", "?")
            items = event.get("items", []) if isinstance(event.get("items", []), list) else []
            print(f"  - event={event_type} round={round_id} items={len(items)}")
            for item in items[:3]:
                title = str(item.get("title") or item.get("before_title") or "").strip()
                verdict = str(item.get("verdict") or item.get("status") or "").strip()
                reason = str(item.get("reason") or item.get("summary") or "").strip()
                print(f"      title={title[:80]} | status={verdict} | note={reason[:140]}")

    committee_log = metadata.get("committee_review_log", [])
    if isinstance(committee_log, list) and committee_log:
        print("[review] committee summary")
        for reviewer in committee_log[:6]:
            print(
                "  - reviewer={} status={} score={} issue={}".format(
                    str(reviewer.get("reviewer", ""))[:32],
                    str(reviewer.get("status", ""))[:12],
                    reviewer.get("score", ""),
                    str(reviewer.get("top_issue", ""))[:140],
                )
            )

    judge_trace = metadata.get("judge_trace", {})
    if isinstance(judge_trace, dict) and judge_trace:
        print("[review] judge")
        print(
            "  - verdict={} title={} rule={} reason={}".format(
                judge_trace.get("final_verdict", ""),
                str(judge_trace.get("winning_title", ""))[:100],
                (judge_trace.get("deterministic_rule") or {}).get("rule_trigger", ""),
                str((judge_trace.get("deterministic_rule") or {}).get("synthesis", ""))[:180],
            )
        )


def run_once(
    args: argparse.Namespace,
    service: PipelineService,
    status_store: PipelineStatusStore,
    notifier: TIDNotificationService,
    mutator: TargetMutationService | None,
):
    effective_target = args.target
    mutation_info = {}

    if args.random_walk_mutate:
        active_mutator = mutator or TargetMutationService()
        base_target = args.target.strip() if args.target else AUTO_BASE_TARGET
        mutation_info = active_mutator.mutate_target(
            base_target=base_target,
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
    if args.verbose_review_logs:
        _print_review_traces(state)
    print(f"Email notified: {'yes' if notified else 'no'}")
    return state


def _compute_sleep_seconds(args: argparse.Namespace, state, crashed: bool = False) -> int:
    if args.no_delay_on_failure:
        if crashed:
            return 0
        if state is not None:
            status = getattr(state, "run_status", "")
            failed_stages = getattr(state, "failed_stages", [])
            if status in {"REJECTED", "RETRY_PENDING"} or bool(failed_stages):
                return 0

    if args.no_delay_on_reject and state is not None and getattr(state, "run_status", "") == "REJECTED":
        return 0
    return args.interval_seconds


def main() -> int:
    args = parse_args()
    if args.interval_seconds <= 0:
        raise ValueError("--interval-seconds must be positive")

    if args.auto_target:
        args.random_walk_mutate = True

    if not args.target and not args.random_walk_mutate:
        raise ValueError("Provide --target, or enable auto target search via --auto-target (or --random-walk-mutate)")

    # Start IO writer service to prevent file contention in parallel mode
    IOWriterService.start()

    print(f"Service mode start | interval={args.interval_seconds}s")
    print(f"LLM backend: {settings.llm_backend}")
    if settings.llm_backend == "copilot_cli":
        print(f"Copilot CLI command: {settings.copilot_cli_command}")
    else:
        print(f"LLM base URL: {settings.internal_llm_base_url}")
        print(f"Maverick model: {settings.maverick_model}")

    try:
        if args.once:
            service = PipelineService()
            status_store = PipelineStatusStore(file_path=args.status_file)
            notifier = TIDNotificationService()
            mutator = TargetMutationService() if args.random_walk_mutate else None
            attempt = 0
            while True:
                attempt += 1
                print(f"Once-mode attempt: {attempt}")
                try:
                    state = run_once(args, service, status_store, notifier, mutator)
                except Exception as exc:
                    logger.exception(f"Once-mode iteration crashed: {exc}")
                    state = None

                if state and state.run_status == "APPROVED" and state.output_paths:
                    print("Once-mode satisfied: APPROVED TID generated.")
                    return 0

                sleep_seconds = _compute_sleep_seconds(args, state)
                if sleep_seconds > 0:
                    print(f"Once-mode continuing: no APPROVED TID yet. Next attempt in {sleep_seconds}s")
                    time.sleep(sleep_seconds)
                else:
                    print("Once-mode continuing immediately after failed run (no delay)")

        service = PipelineService()
        status_store = PipelineStatusStore(file_path=args.status_file)
        notifier = TIDNotificationService()
        mutator = TargetMutationService() if args.random_walk_mutate else None

        while True:
            state = None
            crashed = False
            try:
                state = run_once(args, service, status_store, notifier, mutator)
            except Exception as exc:
                crashed = True
                logger.exception(f"Service iteration crashed: {exc}")
            sleep_seconds = _compute_sleep_seconds(args, state, crashed=crashed)
            if sleep_seconds > 0:
                print(f"Next service iteration in {sleep_seconds}s")
                time.sleep(sleep_seconds)
            else:
                print("Next service iteration starts immediately (failure fast-retry enabled)")
    finally:
        # Graceful shutdown: flush pending writes
        IOWriterService.shutdown(timeout=10.0)


if __name__ == "__main__":
    raise SystemExit(main())
