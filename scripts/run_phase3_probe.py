"""
scripts/run_phase3_probe.py

Phase 3 validation probe for DeepThought.

This script exercises the currently implemented Phase 3 path:
1. Read collection stats from ChromaDB
2. Run a raw similarity query
3. Run MMR reranking via the DeepThought Equation
4. Run topological void discovery

Usage:
    python scripts/run_phase3_probe.py
    python scripts/run_phase3_probe.py --query "scheduler latency optimization"
    python scripts/run_phase3_probe.py --collection kernel_source --top-k 5
    python scripts/run_phase3_probe.py --existing "CFS wakeup balancing"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

from core.deepthought_equation import VoidLandscape
from vectordb.store import CollectionName, DeepThoughtVectorStore, RetrievedDocument


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate DeepThought Phase 3 retrieval and void detection"
    )
    parser.add_argument(
        "--query",
        type=str,
        default="scheduler latency optimization",
        help="Natural language target/query to probe against the vector store",
    )
    parser.add_argument(
        "--collection",
        action="append",
        choices=[c.value for c in CollectionName],
        help="Limit search to one or more collections (repeatable)",
    )
    parser.add_argument(
        "--existing",
        action="append",
        default=[],
        help="Known existing solution text used for novelty/MMR (repeatable)",
    )
    parser.add_argument(
        "--domain-filter",
        type=str,
        default=None,
        help="Optional subsystem filter (for example: sched, mm, x86)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of top results/voids to display",
    )
    parser.add_argument(
        "--lambda-val",
        type=float,
        default=0.7,
        help="MMR lambda value in [0.0, 1.0]",
    )
    parser.add_argument(
        "--preview-chars",
        type=int,
        default=180,
        help="How many content characters to print per result preview",
    )
    return parser.parse_args()


def resolve_collections(values: Optional[List[str]]) -> Optional[List[CollectionName]]:
    if not values:
        return None
    return [CollectionName(value) for value in values]


def build_where(domain_filter: Optional[str]) -> Optional[dict]:
    if not domain_filter:
        return None
    return {"subsystem": {"$eq": domain_filter}}


def format_metadata(doc: RetrievedDocument) -> str:
    metadata = doc.document.metadata
    interesting_keys = [
        "function_name",
        "title",
        "subsystem",
        "file_path",
        "doc_type",
        "source_name",
    ]
    pairs = [
        f"{key}={metadata[key]}"
        for key in interesting_keys
        if key in metadata and metadata[key]
    ]
    return " | ".join(pairs) if pairs else "(no metadata)"


def preview_text(text: str, limit: int) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def print_stats(store: DeepThoughtVectorStore) -> int:
    stats = store.get_stats()
    print("\n=== Vector DB Stats ===")
    for name, count in stats.items():
        print(f"{name:>20}: {count}")
    return int(stats.get("total", 0))


def print_results(title: str, results: Iterable[RetrievedDocument], preview_chars: int) -> None:
    print(f"\n=== {title} ===")
    result_list = list(results)
    if not result_list:
        print("(no results)")
        return

    for idx, item in enumerate(result_list, start=1):
        print(f"[{idx}] collection={item.collection.value} similarity={item.similarity:.4f}")
        print(f"    id={item.document.doc_id}")
        print(f"    meta={format_metadata(item)}")
        print(f"    preview={preview_text(item.document.content, preview_chars)}")


def print_landscape(landscape: VoidLandscape) -> None:
    print("\n=== Topological Voids ===")
    print(landscape.summary())

    if not landscape.voids:
        print("(no voids found)")
        return

    for idx, void in enumerate(landscape.voids, start=1):
        print(
            f"[{idx}] label={void.candidate.label} "
            f"mmr={void.mmr_score:.4f} "
            f"relevance={void.relevance_score:.4f} "
            f"novelty={void.novelty_score:.4f}"
        )
        if void.void_description:
            print(f"    description={void.void_description}")

        file_path = void.candidate.metadata.get("file_path")
        subsystem = void.candidate.metadata.get("subsystem")
        if file_path or subsystem:
            parts = []
            if subsystem:
                parts.append(f"subsystem={subsystem}")
            if file_path:
                parts.append(f"file={file_path}")
            print(f"    {' | '.join(parts)}")


def main() -> int:
    args = parse_args()

    if not 0.0 <= args.lambda_val <= 1.0:
        raise ValueError("--lambda-val must be between 0.0 and 1.0")
    if args.top_k <= 0:
        raise ValueError("--top-k must be positive")
    if args.preview_chars <= 0:
        raise ValueError("--preview-chars must be positive")

    collections = resolve_collections(args.collection)
    where = build_where(args.domain_filter)

    logger.info("Starting Phase 3 validation probe")
    logger.info(f"Query: {args.query}")
    logger.info(f"Collections: {args.collection or 'all'}")
    logger.info(f"Existing solutions: {len(args.existing)}")

    store = DeepThoughtVectorStore()
    total_docs = print_stats(store)
    if total_docs == 0:
        print("\nVector DB is empty. Run ingestion before Phase 3 probing.")
        return 1

    raw_results = store.query(
        query_text=args.query,
        collections=collections,
        n_results=args.top_k,
        where=where,
    )
    print_results("Raw Similarity Query", raw_results[: args.top_k], args.preview_chars)

    mmr_results = store.query_with_mmr(
        query_text=args.query,
        existing_texts=args.existing,
        collections=collections,
        n_results=args.top_k,
        lambda_val=args.lambda_val,
        where=where,
    )
    print_results("MMR Re-ranked Results", mmr_results[: args.top_k], args.preview_chars)

    landscape = store.find_topological_voids(
        target_description=args.query,
        existing_solutions=args.existing,
        collections=collections,
        domain_filter=args.domain_filter,
        lambda_val=args.lambda_val,
        top_k=args.top_k,
    )
    print_landscape(landscape)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
