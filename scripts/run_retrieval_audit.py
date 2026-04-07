"""
Batch retrieval audit for DeepThought.

Runs multiple curated probe cases to sanity-check vector-space behavior,
domain filtering, and obvious garbage candidates before enabling the LLM
pipeline on top of retrieval.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from vectordb.store import CollectionName, DeepThoughtVectorStore, RetrievedDocument


INVALID_LABELS = {"unknown", "unnamed", "none", "null", "n/a"}


@dataclass
class ProbeCase:
    name: str
    query: str
    collections: List[str]
    domain_filter: Optional[str] = None
    existing: List[str] = field(default_factory=list)
    expected_subsystem: Optional[str] = None
    expected_prefixes: List[str] = field(default_factory=list)
    notes: str = ""


DEFAULT_CASES = [
    ProbeCase(
        name="scheduler_eevdf",
        query="linux kernel EEVDF latency optimization under wakeup contention",
        collections=["kernel_source"],
        domain_filter="scheduler",
        existing=["CFS wakeup balancing", "NUMA load balancing"],
        expected_subsystem="scheduler",
        expected_prefixes=["kernel/sched", "include/linux/sched"],
        notes="Core scheduler/EEVDF sanity check.",
    ),
    ProbeCase(
        name="memory_numa",
        query="linux kernel NUMA page migration latency reduction under memory pressure",
        collections=["kernel_source"],
        domain_filter="memory_management",
        existing=["automatic NUMA balancing", "page reclaim watermark boosting"],
        expected_subsystem="memory_management",
        expected_prefixes=["mm/", "include/linux/mm"],
        notes="Checks NUMA and reclaim-related retrieval isolation.",
    ),
    ProbeCase(
        name="networking_tcp",
        query="linux kernel TCP receive path latency reduction under small packet bursts",
        collections=["kernel_source"],
        domain_filter="networking",
        existing=["NAPI polling", "generic receive offload"],
        expected_subsystem="networking",
        expected_prefixes=["net/"],
        notes="Checks networking retrieval isolation.",
    ),
    ProbeCase(
        name="x86_tlb",
        query="linux kernel x86 TLB shootdown overhead reduction on multi-socket systems",
        collections=["kernel_source"],
        domain_filter="x86",
        existing=["batched TLB flush", "PCID-based TLB preservation"],
        expected_subsystem="x86",
        expected_prefixes=["arch/x86/"],
        notes="Checks architecture-specific retrieval isolation.",
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run batch retrieval audits across multiple domains")
    parser.add_argument(
        "--case",
        action="append",
        default=[],
        help="Run only selected built-in case names (repeatable)",
    )
    parser.add_argument(
        "--cases-file",
        default=None,
        help="Optional JSON file containing a list of probe cases",
    )
    parser.add_argument("--top-k", type=int, default=8, help="Top-K results to inspect per case")
    parser.add_argument("--lambda-val", type=float, default=0.7, help="MMR lambda")
    parser.add_argument(
        "--preview-chars",
        type=int,
        default=120,
        help="Preview character count for console output",
    )
    parser.add_argument(
        "--json-output",
        default=None,
        help="Optional path to save audit summary as JSON",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if any case is flagged with WARN",
    )
    return parser.parse_args()


def load_cases(args: argparse.Namespace) -> List[ProbeCase]:
    if args.cases_file:
        payload = json.loads(Path(args.cases_file).read_text(encoding="utf-8"))
        return [ProbeCase(**item) for item in payload]

    if not args.case:
        return DEFAULT_CASES

    selected = {name.lower() for name in args.case}
    return [case for case in DEFAULT_CASES if case.name.lower() in selected]


def resolve_collections(values: List[str]) -> List[CollectionName]:
    return [CollectionName(value) for value in values]


def build_where(domain_filter: Optional[str]) -> Optional[dict]:
    if not domain_filter:
        return None
    return {"subsystem": {"$eq": domain_filter}}


def compact_preview(text: str, limit: int) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def summarize_results(case: ProbeCase, docs: Iterable[RetrievedDocument]) -> dict:
    docs = list(docs)
    collection_noise = 0
    subsystem_noise = 0
    path_noise = 0

    for doc in docs:
        if doc.collection.value not in case.collections:
            collection_noise += 1

        subsystem = str(doc.document.metadata.get("subsystem", "")).strip()
        if case.expected_subsystem and subsystem != case.expected_subsystem:
            subsystem_noise += 1

        file_path = str(doc.document.metadata.get("file_path", "")).strip().lower()
        if case.expected_prefixes and file_path:
            if not any(file_path.startswith(prefix.lower()) for prefix in case.expected_prefixes):
                path_noise += 1

    return {
        "count": len(docs),
        "collection_noise": collection_noise,
        "subsystem_noise": subsystem_noise,
        "path_noise": path_noise,
    }


def summarize_voids(landscape) -> dict:
    labels = [str(void.candidate.label).strip() for void in landscape.voids]
    invalid_labels = sum(1 for label in labels if label.lower() in INVALID_LABELS or not label)
    duplicate_labels = len(labels) - len(set(labels))
    return {
        "count": len(labels),
        "invalid_labels": invalid_labels,
        "duplicate_labels": duplicate_labels,
        "top_labels": labels[:5],
    }


def case_status(raw_summary: dict, mmr_summary: dict, void_summary: dict) -> str:
    total_noise = (
        raw_summary["collection_noise"]
        + raw_summary["subsystem_noise"]
        + mmr_summary["collection_noise"]
        + mmr_summary["subsystem_noise"]
        + mmr_summary["path_noise"]
        + void_summary["invalid_labels"]
    )
    if total_noise == 0 and void_summary["duplicate_labels"] <= 1:
        return "PASS"
    return "WARN"


def print_case_report(case: ProbeCase, raw_results, mmr_results, landscape, args: argparse.Namespace) -> dict:
    raw_summary = summarize_results(case, raw_results)
    mmr_summary = summarize_results(case, mmr_results)
    void_summary = summarize_voids(landscape)
    status = case_status(raw_summary, mmr_summary, void_summary)

    print(f"\n=== {case.name} [{status}] ===")
    print(f"query={case.query}")
    if case.notes:
        print(f"notes={case.notes}")
    print(
        "raw_noise="
        f"collections:{raw_summary['collection_noise']} "
        f"subsystems:{raw_summary['subsystem_noise']}"
    )
    print(
        "mmr_noise="
        f"collections:{mmr_summary['collection_noise']} "
        f"subsystems:{mmr_summary['subsystem_noise']} "
        f"paths:{mmr_summary['path_noise']}"
    )
    print(
        "void_quality="
        f"invalid_labels:{void_summary['invalid_labels']} "
        f"duplicate_labels:{void_summary['duplicate_labels']}"
    )
    print(f"top_void_labels={', '.join(void_summary['top_labels']) or '(none)'}")

    for idx, doc in enumerate(mmr_results[: min(3, len(mmr_results))], start=1):
        meta = doc.document.metadata
        print(
            f"  mmr[{idx}] sim={doc.similarity:.4f} "
            f"subsystem={meta.get('subsystem', '')} file={meta.get('file_path', '')}"
        )
        print(f"         preview={compact_preview(doc.document.content, args.preview_chars)}")

    return {
        "case": case.name,
        "status": status,
        "query": case.query,
        "raw_summary": raw_summary,
        "mmr_summary": mmr_summary,
        "void_summary": void_summary,
        "domain_filter": case.domain_filter,
        "collections": case.collections,
    }


def main() -> int:
    args = parse_args()
    if args.top_k <= 0:
        raise ValueError("--top-k must be positive")
    if not 0.0 <= args.lambda_val <= 1.0:
        raise ValueError("--lambda-val must be between 0.0 and 1.0")

    cases = load_cases(args)
    if not cases:
        print("No audit cases selected.")
        return 1

    store = DeepThoughtVectorStore()
    summaries = []

    for case in cases:
        collections = resolve_collections(case.collections)
        where = build_where(case.domain_filter)
        raw_results = store.query(
            query_text=case.query,
            collections=collections,
            n_results=args.top_k,
            where=where,
        )
        mmr_results = store.query_with_mmr(
            query_text=case.query,
            existing_texts=case.existing,
            collections=collections,
            n_results=args.top_k,
            lambda_val=args.lambda_val,
            where=where,
        )
        landscape = store.find_topological_voids(
            target_description=case.query,
            existing_solutions=case.existing,
            collections=collections,
            domain_filter=case.domain_filter,
            lambda_val=args.lambda_val,
            top_k=args.top_k,
        )
        summaries.append(print_case_report(case, raw_results, mmr_results, landscape, args))

    if args.json_output:
        output_path = Path(args.json_output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(summaries, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nSaved JSON summary to {output_path}")

    warn_count = sum(1 for item in summaries if item["status"] == "WARN")
    pass_count = len(summaries) - warn_count
    print(f"\nAudit summary: PASS={pass_count} WARN={warn_count}")

    if args.strict and warn_count:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())