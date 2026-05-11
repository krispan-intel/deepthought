"""
scripts/temporal_validation/build_tvv_corpus.py

Build a separate ChromaDB collection from arxiv_train.jsonl (t < 2019).
This is the TVV training corpus — TVA will find voids in this snapshot.

Usage:
    python scripts/temporal_validation/build_tvv_corpus.py
    python scripts/temporal_validation/build_tvv_corpus.py --limit 5000  # quick test
"""

import argparse
import json
from pathlib import Path

from loguru import logger
from tqdm import tqdm

TRAIN_JSONL = Path("data/processed/tvv/arxiv_train.jsonl")
COLLECTION_NAME = "tvv_arxiv_train"
DEFAULT_BATCH = 64


def build(limit: int | None = None):
    import chromadb
    from configs.settings import settings
    from vectordb.embedder import create_embedder

    logger.info("Loading BGE-M3 via existing embedder...")
    embedder = create_embedder()

    logger.info(f"Opening ChromaDB at {settings.vectordb_path}")
    client = chromadb.PersistentClient(path=str(settings.vectordb_path))

    # Drop and recreate collection for clean state
    try:
        client.delete_collection(COLLECTION_NAME)
        logger.info(f"Dropped existing collection: {COLLECTION_NAME}")
    except Exception:
        pass
    col = client.create_collection(COLLECTION_NAME)

    # Load papers
    papers = []
    with open(TRAIN_JSONL) as f:
        for line in f:
            papers.append(json.loads(line))
            if limit and len(papers) >= limit:
                break

    logger.info(f"Loaded {len(papers):,} papers from train set")

    # Embed in batches
    total = 0
    for i in tqdm(range(0, len(papers), DEFAULT_BATCH), desc="Embedding"):
        batch = papers[i : i + DEFAULT_BATCH]
        texts = [f"{p['title']} {p['abstract']}" for p in batch]

        embeddings = [embedder.embed_query(t) for t in texts]

        col.add(
            ids=[p["id"] for p in batch],
            embeddings=embeddings,
            documents=[p["title"] for p in batch],
            metadatas=[
                {
                    "title": p["title"][:200],
                    "categories": p.get("categories", ""),
                    "year": p.get("year", 0),
                    "update_date": p.get("update_date", ""),
                }
                for p in batch
            ],
        )
        total += len(batch)

    logger.info(f"Done. {total:,} papers embedded into collection '{COLLECTION_NAME}'")
    logger.info(f"Collection count: {col.count()}")


def main():
    parser = argparse.ArgumentParser(description="Build TVV training corpus")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of papers (for testing)")
    args = parser.parse_args()
    build(limit=args.limit)


if __name__ == "__main__":
    main()
