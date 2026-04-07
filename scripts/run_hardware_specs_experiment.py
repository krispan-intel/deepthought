"""
One-command hardware_specs experiment runner.

What it does:
1) Rebuild an isolated experiment vector DB path (optional reset).
2) Ingest only intel_opt_manual (or another named source).
3) Check title metadata coverage in sampled records.
4) Run contamination audit on hardware_specs and print summary.

Usage:
    python scripts/run_hardware_specs_experiment.py
    python scripts/run_hardware_specs_experiment.py --no-reset --skip-ingest
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run isolated hardware_specs ingestion + contamination audit experiment"
    )
    parser.add_argument(
        "--exp-path",
        default="data/vectorstore_exp",
        help="Isolated vector DB path for the experiment",
    )
    parser.add_argument(
        "--source-name",
        default="intel_opt_manual",
        help="Data source name in DATA_SOURCES to ingest",
    )
    parser.add_argument(
        "--collection",
        default="hardware_specs",
        help="Collection to audit",
    )
    parser.add_argument("--samples", type=int, default=15, help="Audit sample size")
    parser.add_argument("--seed", type=int, default=42, help="Audit random seed")
    parser.add_argument("--preview-chars", type=int, default=180, help="Preview chars for suspicious items")
    parser.add_argument("--title-samples", type=int, default=20, help="How many records to check for title coverage")
    parser.add_argument("--json-output", default="", help="Optional output JSON path for audit summary")
    parser.add_argument("--no-reset", action="store_true", help="Do not delete experiment DB before running")
    parser.add_argument("--skip-ingest", action="store_true", help="Skip ingestion step and only inspect/audit")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when suspicious items are found")
    return parser.parse_args()


def configure_isolated_paths(exp_path: Path) -> None:
    sparse_path = exp_path / "sparse_sidecar.sqlite3"
    os.environ["VECTORDB_PATH"] = str(exp_path)
    os.environ["SPARSE_INDEX_PATH"] = str(sparse_path)
    print(f"[env] VECTORDB_PATH={exp_path}")
    print(f"[env] SPARSE_INDEX_PATH={sparse_path}")


async def run_ingestion(source_name: str) -> None:
    from data_collection.scheduler import DATA_SOURCES
    from services.ingestion_service import IngestionService

    source = next((s for s in DATA_SOURCES if s.name == source_name), None)
    if source is None:
        available = ", ".join(sorted(s.name for s in DATA_SOURCES))
        raise ValueError(f"Unknown source_name={source_name}. Available: {available}")

    print(f"[ingest] source={source.name} uri={source.uri}")
    await IngestionService().ingest_source(source)


def inspect_title_coverage(collection_name: str, title_samples: int) -> dict:
    from vectordb.store import CollectionName, DeepThoughtVectorStore

    store = DeepThoughtVectorStore()
    collection = CollectionName(collection_name)
    col = store._collections[collection]
    total = col.count()
    print(f"[db] {collection.value} total_docs={total}")

    if total <= 0:
        return {
            "total_docs": 0,
            "checked": 0,
            "title_present": 0,
            "title_missing": 0,
            "title_examples": [],
        }

    check_n = min(title_samples, total)
    result = col.get(limit=check_n, include=["metadatas"])
    metadatas = result.get("metadatas") or []

    title_present = 0
    title_examples = []
    for metadata in metadatas:
        title = (metadata or {}).get("title")
        if title:
            title_present += 1
            if len(title_examples) < 5:
                title_examples.append(str(title))

    title_missing = len(metadatas) - title_present
    print(
        "[title] checked={} present={} missing={}".format(
            len(metadatas),
            title_present,
            title_missing,
        )
    )
    for index, title in enumerate(title_examples, start=1):
        print(f"  [title-example-{index}] {title}")

    return {
        "total_docs": total,
        "checked": len(metadatas),
        "title_present": title_present,
        "title_missing": title_missing,
        "title_examples": title_examples,
    }


def run_contamination_audit(
    collection_name: str,
    samples: int,
    seed: int,
    preview_chars: int,
) -> dict:
    from scripts.run_db_contamination_audit import print_collection_report, sample_collection
    from vectordb.store import CollectionName, DeepThoughtVectorStore

    store = DeepThoughtVectorStore()
    collection = CollectionName(collection_name)
    sampled = sample_collection(store, collection, sample_count=samples, seed=seed)
    return print_collection_report(collection, sampled, preview_chars)


def main() -> int:
    args = parse_args()
    exp_path = Path(args.exp_path)

    print("[step] configure isolated experiment DB")
    configure_isolated_paths(exp_path)

    if not args.no_reset:
        print("[step] reset experiment DB path")
        shutil.rmtree(exp_path, ignore_errors=True)
    exp_path.mkdir(parents=True, exist_ok=True)

    if not args.skip_ingest:
        print("[step] ingest selected source into isolated DB")
        asyncio.run(run_ingestion(args.source_name))
    else:
        print("[step] skip ingestion (requested)")

    print("[step] inspect title coverage")
    title_summary = inspect_title_coverage(args.collection, args.title_samples)

    print("[step] run contamination audit")
    audit_summary = run_contamination_audit(
        collection_name=args.collection,
        samples=args.samples,
        seed=args.seed,
        preview_chars=args.preview_chars,
    )

    merged = {
        "exp_path": str(exp_path),
        "source_name": args.source_name,
        "collection": args.collection,
        "title_summary": title_summary,
        "audit_summary": audit_summary,
    }

    if args.json_output:
        output_path = Path(args.json_output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[json] wrote summary: {output_path}")

    suspicious = int(audit_summary.get("suspicious", 0))
    sampled = int(audit_summary.get("samples", 0))
    print(f"\n[summary] suspicious={suspicious} / samples={sampled}")
    if args.strict and suspicious > 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
