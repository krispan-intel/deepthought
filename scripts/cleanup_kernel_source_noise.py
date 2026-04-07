"""
Targeted cleanup tool for noisy kernel_source records.

Default mode is dry-run. Use --apply to actually delete records.
The cleaner is intentionally conservative and only targets commit-message
blob records with hash-like labels.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from vectordb.store import CollectionName, DeepThoughtVectorStore, RetrievedDocument
from scripts.run_db_contamination_audit import compact_preview


HASH_RE = re.compile(r"^[0-9a-f]{16,64}$", re.IGNORECASE)
COMMIT_BLOB_RE = re.compile(
    r"COMMIT:\s+[0-9a-f]{7,40}\b.*AUTHOR:\s+.*(?:DATE:\s+.*)?MESSAGE:\s+",
    re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clean noisy kernel_source commit-message blobs")
    parser.add_argument(
        "--collection",
        default=CollectionName.KERNEL_SOURCE.value,
        choices=[c.value for c in CollectionName],
        help="Collection to clean (default: kernel_source)",
    )
    parser.add_argument("--batch-size", type=int, default=256, help="Scan batch size")
    parser.add_argument("--max-scan", type=int, default=0, help="Max docs to scan (0 means all)")
    parser.add_argument("--delete-batch-size", type=int, default=200, help="Delete batch size when --apply")
    parser.add_argument("--preview-chars", type=int, default=180, help="Preview length in report")
    parser.add_argument("--json-output", default=None, help="Optional JSON output path")
    parser.add_argument("--apply", action="store_true", help="Actually delete matched records")
    parser.add_argument("--strict", action="store_true", help="Return non-zero if any matches are found")
    return parser.parse_args()


def derive_label(doc_id: str, metadata: Dict[str, Any]) -> str:
    label = (
        RetrievedDocument._sanitize_label(metadata.get("function_name"))
        or RetrievedDocument._sanitize_label(metadata.get("name"))
        or RetrievedDocument._sanitize_label(metadata.get("title"))
    )
    if label:
        return label

    file_path = RetrievedDocument._sanitize_label(metadata.get("file_path"))
    start_line = metadata.get("start_line")
    if file_path and start_line:
        return f"{file_path}:{start_line}"
    if file_path:
        return str(file_path)
    return str(doc_id)


def classify_noise(doc_id: str, content: str, metadata: Dict[str, Any]) -> Tuple[bool, List[str], str]:
    label = derive_label(doc_id, metadata)
    reasons: List[str] = []

    # Some legacy records may have path-like fallback labels but hash-like doc IDs.
    if HASH_RE.fullmatch(label.strip()) or HASH_RE.fullmatch(str(doc_id).strip()):
        reasons.append("hash_label")

    if not metadata.get("function_name") and not metadata.get("name") and not metadata.get("title"):
        reasons.append("missing_semantic_metadata")

    first_non_empty_line = ""
    raw_content = str(content or "")
    for line in raw_content.splitlines():
        stripped = line.strip()
        if stripped:
            first_non_empty_line = stripped
            break

    normalized_head = " ".join(raw_content.split())[:2000]
    commit_markers = (
        "COMMIT:" in normalized_head.upper()
        and "AUTHOR:" in normalized_head.upper()
        and "MESSAGE:" in normalized_head.upper()
    )
    commit_blob = bool(
        (first_non_empty_line and COMMIT_BLOB_RE.search(first_non_empty_line))
        or COMMIT_BLOB_RE.search(normalized_head)
        or commit_markers
    )
    if commit_blob:
        reasons.append("commit_message_blob")

    # Conservative delete policy: confirmed commit blob plus either
    # hash-like identity or no semantic metadata.
    should_delete = commit_blob and (
        "hash_label" in reasons or "missing_semantic_metadata" in reasons
    )
    return should_delete, reasons, label


def scan_candidates(
    store: DeepThoughtVectorStore,
    collection: CollectionName,
    batch_size: int,
    max_scan: int,
    preview_chars: int,
) -> Dict[str, Any]:
    col = store._collections[collection]
    total_count = col.count()
    target_count = total_count if max_scan <= 0 else min(max_scan, total_count)

    scanned = 0
    candidates: List[Dict[str, Any]] = []

    while scanned < target_count:
        take = min(batch_size, target_count - scanned)
        result = col.get(limit=take, offset=scanned, include=["documents", "metadatas"])

        ids = result.get("ids") or []
        documents = result.get("documents") or []
        metadatas = result.get("metadatas") or []

        for index, doc_id in enumerate(ids):
            content = str(documents[index]) if index < len(documents) else ""
            metadata = metadatas[index] if index < len(metadatas) and metadatas[index] is not None else {}
            matched, reasons, label = classify_noise(str(doc_id), content, metadata)
            if matched:
                candidates.append(
                    {
                        "doc_id": str(doc_id),
                        "label": label,
                        "reasons": reasons,
                        "preview": compact_preview(content, preview_chars),
                        "metadata": {
                            key: metadata.get(key)
                            for key in ("file_path", "name", "title", "function_name", "source", "commit")
                            if key in metadata
                        },
                    }
                )

        scanned += take

    return {
        "collection": collection.value,
        "total_docs": total_count,
        "scanned": scanned,
        "candidates": candidates,
    }


def delete_candidates(
    store: DeepThoughtVectorStore,
    collection: CollectionName,
    candidates: List[Dict[str, Any]],
    delete_batch_size: int,
) -> int:
    if not candidates:
        return 0
    col = store._collections[collection]
    ids = [item["doc_id"] for item in candidates]

    deleted = 0
    for start in range(0, len(ids), delete_batch_size):
        batch = ids[start : start + delete_batch_size]
        col.delete(ids=batch)
        deleted += len(batch)
    return deleted


def main() -> int:
    args = parse_args()
    if args.batch_size <= 0:
        raise ValueError("--batch-size must be positive")
    if args.delete_batch_size <= 0:
        raise ValueError("--delete-batch-size must be positive")

    collection = CollectionName(args.collection)
    store = DeepThoughtVectorStore()

    summary = scan_candidates(
        store=store,
        collection=collection,
        batch_size=args.batch_size,
        max_scan=args.max_scan,
        preview_chars=args.preview_chars,
    )

    candidates = summary["candidates"]
    print(f"\n=== cleanup target: {collection.value} ===")
    print(f"total_docs={summary['total_docs']} scanned={summary['scanned']} matches={len(candidates)}")
    for idx, item in enumerate(candidates[:10], start=1):
        print(f"[{idx}] label={item['label']} reasons={','.join(item['reasons'])}")
        print(f"    preview={item['preview']}")

    deleted = 0
    if args.apply and candidates:
        deleted = delete_candidates(
            store=store,
            collection=collection,
            candidates=candidates,
            delete_batch_size=args.delete_batch_size,
        )
        print(f"\nDeleted {deleted} records from {collection.value}")
    elif args.apply:
        print("\nNo matching records to delete")
    else:
        print("\nDry-run mode: no records were deleted (pass --apply to delete)")

    output = {
        "collection": collection.value,
        "total_docs": summary["total_docs"],
        "scanned": summary["scanned"],
        "matches": len(candidates),
        "deleted": deleted,
        "apply": bool(args.apply),
        "items": candidates,
    }

    if args.json_output:
        out_path = Path(args.json_output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Saved JSON summary to {out_path}")

    if args.strict and len(candidates) > 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
