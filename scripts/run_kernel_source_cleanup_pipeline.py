"""
End-to-end kernel_source cleanup pipeline.

Default behavior is safe:
- backup vectorstore
- scan and export candidate IDs
- dry-run only (no delete)

Use --apply to execute deletion and run after-cleanup audit.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from configs.settings import settings
from scripts.cleanup_kernel_source_noise import delete_candidates, scan_candidates
from scripts.run_db_contamination_audit import print_collection_report, sample_collection
from vectordb.store import CollectionName, DeepThoughtVectorStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run kernel_source cleanup pipeline")
    parser.add_argument(
        "--collection",
        default=CollectionName.KERNEL_SOURCE.value,
        choices=[c.value for c in CollectionName],
        help="Collection to clean",
    )
    parser.add_argument("--batch-size", type=int, default=256, help="Scan batch size")
    parser.add_argument("--max-scan", type=int, default=0, help="Max docs to scan (0 means all)")
    parser.add_argument("--delete-batch-size", type=int, default=200, help="Delete batch size")
    parser.add_argument("--preview-chars", type=int, default=180, help="Preview size for summary")
    parser.add_argument("--samples-after", type=int, default=200, help="Post-cleanup audit sample size")
    parser.add_argument("--seed-after", type=int, default=42, help="Post-cleanup audit random seed")
    parser.add_argument("--apply", action="store_true", help="Apply deletion after dry-run scan")
    parser.add_argument("--skip-backup", action="store_true", help="Skip vectorstore backup")
    parser.add_argument(
        "--output-prefix",
        default="output/generated/kernel_source_cleanup",
        help="Output file prefix (without extension)",
    )
    return parser.parse_args()


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def backup_vectorstore() -> Path:
    src = Path(settings.vectordb_path)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dst = src.parent / f"{src.name}_backup_before_kernel_cleanup_{ts}"
    shutil.copytree(src, dst)
    return dst


def export_ids(path: Path, items: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [str(item["doc_id"]) for item in items]
    text = "\n".join(lines)
    if text:
        text += "\n"
    path.write_text(text, encoding="utf-8")


def main() -> int:
    args = parse_args()
    collection = CollectionName(args.collection)

    backup_path = None
    if not args.skip_backup:
        print("[step] backing up vectorstore")
        backup_path = backup_vectorstore()
        print(f"[backup] {backup_path}")
    else:
        print("[step] backup skipped by flag")

    print("[step] scanning cleanup candidates")
    store = DeepThoughtVectorStore()
    dry_summary = scan_candidates(
        store=store,
        collection=collection,
        batch_size=args.batch_size,
        max_scan=args.max_scan,
        preview_chars=args.preview_chars,
    )
    candidates = dry_summary["candidates"]
    print(
        f"[dry-run] collection={collection.value} total={dry_summary['total_docs']} "
        f"scanned={dry_summary['scanned']} matches={len(candidates)}"
    )

    prefix = Path(args.output_prefix)
    dry_json = prefix.with_suffix(".dryrun.json")
    ids_txt = prefix.with_suffix(".ids.txt")
    write_json(
        dry_json,
        {
            "collection": collection.value,
            "total_docs": dry_summary["total_docs"],
            "scanned": dry_summary["scanned"],
            "matches": len(candidates),
            "apply": False,
            "backup_path": str(backup_path) if backup_path else None,
            "items": candidates,
        },
    )
    export_ids(ids_txt, candidates)
    print(f"[output] dry-run json: {dry_json}")
    print(f"[output] ids list: {ids_txt}")

    if not args.apply:
        print("[done] dry-run only. Re-run with --apply to delete matches.")
        return 0

    print("[step] applying deletion")
    deleted = delete_candidates(
        store=store,
        collection=collection,
        candidates=candidates,
        delete_batch_size=args.delete_batch_size,
    )
    apply_json = prefix.with_suffix(".apply.json")
    write_json(
        apply_json,
        {
            "collection": collection.value,
            "total_docs_before": dry_summary["total_docs"],
            "scanned": dry_summary["scanned"],
            "matches": len(candidates),
            "deleted": deleted,
            "apply": True,
            "backup_path": str(backup_path) if backup_path else None,
        },
    )
    print(f"[output] apply json: {apply_json}")

    print("[step] running post-cleanup audit sample")
    after_store = DeepThoughtVectorStore()
    after_samples = sample_collection(
        after_store,
        collection,
        sample_count=args.samples_after,
        seed=args.seed_after,
    )
    after_report = print_collection_report(collection, after_samples, args.preview_chars)
    after_json = prefix.with_suffix(".after_audit.json")
    write_json(after_json, after_report)
    print(f"[output] after-audit json: {after_json}")

    print(
        f"[summary] deleted={deleted} after_suspicious={after_report['suspicious']} "
        f"after_samples={after_report['samples']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
