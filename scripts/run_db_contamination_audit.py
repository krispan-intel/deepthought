"""
Small-sample contamination audit for existing vector DB contents.

Checks whether sampled documents from selected collections still contain
metadata bleed, noisy concept labels, or other obvious semantic pollution.
"""

from __future__ import annotations

import argparse
import json
import numpy as np
import random
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence

sys.path.insert(0, str(Path(__file__).parent.parent))

from vectordb.store import CollectionName, DeepThoughtVectorStore, Document, RetrievedDocument


CONTENT_HEADER_RE = re.compile(
    r"^(?:file_path|filepath|path|url|uri|author|md5|hash|source_name|page_num)\s*:\s*.*$",
    re.IGNORECASE,
)
RAW_PATH_RE = re.compile(r"(?:[A-Za-z]:\\|/|\\).*(?:\.c|\.h|\.pdf|\.md|\.json|\.txt|\.rst)", re.IGNORECASE)
AUTHOR_HEADER_RE = re.compile(r"^authors?\s*:\s*", re.IGNORECASE)
HASH_RE = re.compile(r"^[0-9a-f]{16,64}$", re.IGNORECASE)
GENERIC_LABELS = {
    "resource",
    "data",
    "value",
    "values",
    "result",
    "results",
    "item",
    "items",
    "entry",
    "entries",
    "unknown",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit existing vector DB collections for contamination")
    parser.add_argument(
        "--collection",
        action="append",
        choices=[c.value for c in CollectionName],
        help="Collection(s) to audit. Default: kernel_source, hardware_specs, papers",
    )
    parser.add_argument("--samples", type=int, default=20, help="Random samples per collection")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducible sampling")
    parser.add_argument("--preview-chars", type=int, default=180, help="Preview length for suspicious samples")
    parser.add_argument("--json-output", default=None, help="Optional JSON output path")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if any contamination is detected")
    return parser.parse_args()


def default_collections(values: Sequence[str] | None) -> List[CollectionName]:
    if values:
        return [CollectionName(value) for value in values]
    return [
        CollectionName.KERNEL_SOURCE,
        CollectionName.HARDWARE_SPECS,
        CollectionName.PAPERS,
    ]


def compact_preview(text: str, limit: int) -> str:
    compact = " ".join((text or "").split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def detect_contamination(item: RetrievedDocument) -> List[str]:
    reasons: List[str] = []
    content = str(item.document.content or "")
    metadata = item.document.metadata or {}
    label = item.to_tech_vector().label

    first_non_empty_line = ""
    for line in content.splitlines():
        stripped = line.strip()
        if stripped:
            first_non_empty_line = stripped
            break

    if first_non_empty_line and CONTENT_HEADER_RE.match(first_non_empty_line):
        reasons.append("metadata_header_in_content")
    if AUTHOR_HEADER_RE.match(first_non_empty_line):
        reasons.append("author_header_in_content")
    if RAW_PATH_RE.search(first_non_empty_line):
        reasons.append("path_like_content_prefix")

    lowered_label = str(label).strip().lower()
    if HASH_RE.fullmatch(str(label).strip()):
        reasons.append("hash_label")
    if lowered_label in GENERIC_LABELS:
        reasons.append("generic_label")
    if "/" in str(label) or "\\" in str(label):
        reasons.append("path_label")

    if not metadata.get("function_name") and not metadata.get("name") and not metadata.get("title"):
        reasons.append("missing_semantic_metadata")

    return reasons


def sample_collection(
    store: DeepThoughtVectorStore,
    collection: CollectionName,
    sample_count: int,
    seed: int,
) -> List[RetrievedDocument]:
    random.seed(seed)
    col = store._collections[collection]
    count = col.count()
    if count <= 0:
        return []

    take = min(sample_count, count)
    offsets = random.sample(range(count), k=take)
    samples: List[RetrievedDocument] = []
    for offset in offsets:
        result = col.get(limit=1, offset=offset, include=["documents", "metadatas", "embeddings"])
        ids = result.get("ids")
        documents = result.get("documents")
        metadatas = result.get("metadatas")
        embeddings = result.get("embeddings")

        if ids is None or len(ids) == 0:
            continue
        if documents is None or len(documents) == 0:
            continue

        metadata = metadatas[0] if metadatas is not None and len(metadatas) > 0 else {}
        embedding_data = embeddings[0] if embeddings is not None and len(embeddings) > 0 else None
        if embedding_data is None:
            embedding = store.embedder.embed_one(str(documents[0]))
        else:
            embedding = np.array(embedding_data, dtype=np.float32)

        samples.append(
            RetrievedDocument(
                document=Document(
                    content=str(documents[0]),
                    metadata=metadata or {},
                    doc_id=str(ids[0]),
                ),
                embedding=embedding,
                distance=0.0,
                collection=collection,
            )
        )
    return samples


def print_collection_report(collection: CollectionName, samples: List[RetrievedDocument], preview_chars: int) -> Dict[str, Any]:
    suspicious = []
    for item in samples:
        reasons = detect_contamination(item)
        if reasons:
            suspicious.append(
                {
                    "doc_id": item.document.doc_id,
                    "label": item.to_tech_vector().label,
                    "reasons": reasons,
                    "preview": compact_preview(item.document.content, preview_chars),
                    "metadata": {
                        key: item.document.metadata.get(key)
                        for key in ("file_path", "name", "title", "function_name", "source", "page_num")
                        if key in item.document.metadata
                    },
                }
            )

    print(f"\n=== {collection.value} ===")
    print(f"samples={len(samples)} suspicious={len(suspicious)} clean={len(samples) - len(suspicious)}")
    for index, item in enumerate(suspicious[:5], start=1):
        print(f"[{index}] label={item['label']} reasons={','.join(item['reasons'])}")
        print(f"    preview={item['preview']}")

    return {
        "collection": collection.value,
        "samples": len(samples),
        "suspicious": len(suspicious),
        "clean": len(samples) - len(suspicious),
        "items": suspicious,
    }


def main() -> int:
    args = parse_args()
    if args.samples <= 0:
        raise ValueError("--samples must be positive")

    store = DeepThoughtVectorStore()
    collections = default_collections(args.collection)
    summaries = []

    for index, collection in enumerate(collections):
        samples = sample_collection(store, collection, sample_count=args.samples, seed=args.seed + index)
        summaries.append(print_collection_report(collection, samples, args.preview_chars))

    if args.json_output:
        output_path = Path(args.json_output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(summaries, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nSaved JSON summary to {output_path}")

    suspicious_total = sum(item["suspicious"] for item in summaries)
    sample_total = sum(item["samples"] for item in summaries)
    print(f"\nAudit summary: suspicious={suspicious_total} / samples={sample_total}")
    if args.strict and suspicious_total:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())