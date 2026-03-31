"""
scripts/setup_vectordb.py

Initialize and verify the DeepThought Vector Store.
Run this once before any data ingestion.

Usage:
    python scripts/setup_vectordb.py
    python scripts/setup_vectordb.py --reset
    python scripts/setup_vectordb.py --reset --collection kernel_source
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from configs.settings import settings
from vectordb.store import DeepThoughtVectorStore, CollectionName


# ─────────────────────────────────────────────────────────────────
# Setup
# ─────────────────────────────────────────────────────────────────

def setup_vectordb(reset: bool = False, collection: str = None):

    logger.info("🗄️  Initializing DeepThought Vector Store...")
    logger.info(f"    Path: {settings.vectordb_path}")

    # Ensure directories exist
    settings.vectordb_path.mkdir(parents=True, exist_ok=True)
    settings.data_raw_path.mkdir(parents=True, exist_ok=True)
    settings.data_processed_path.mkdir(parents=True, exist_ok=True)

    # Initialize store
    store = DeepThoughtVectorStore()

    if reset:
        if collection:
            # Reset specific collection
            try:
                col_enum = CollectionName(collection)
                logger.warning(
                    f"⚠️  Resetting collection: {collection}"
                )
                store.reset_collection(col_enum)
                logger.info(f"✅ Collection reset: {collection}")
            except ValueError:
                valid = [c.value for c in CollectionName]
                logger.error(
                    f"Unknown collection: {collection}\n"
                    f"Valid options: {valid}"
                )
                sys.exit(1)
        else:
            # Reset all collections
            logger.warning("⚠️  Resetting ALL collections...")
            confirm = input(
                "Type 'yes' to confirm full reset: "
            ).strip()
            if confirm != "yes":
                logger.info("Aborted.")
                sys.exit(0)
            for col in CollectionName:
                store.reset_collection(col)
            logger.info("✅ All collections reset")

    # Print stats
    store.print_stats()

    # Verify each collection is accessible
    logger.info("🔍 Verifying collections...")
    all_ok = True

    for col in CollectionName:
        try:
            count = store._collections[col].count()
            logger.info(f"  ✅ {col.value:<25} ({count} docs)")
        except Exception as e:
            logger.error(f"  ❌ {col.value:<25} ERROR: {e}")
            all_ok = False

    if all_ok:
        logger.info("✅ Vector Store ready for ingestion")
    else:
        logger.error("❌ Some collections failed verification")
        sys.exit(1)

    return store


# ─────────────────────────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Initialize DeepThought Vector Store"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset collections before setup"
    )
    parser.add_argument(
        "--collection",
        type=str,
        default=None,
        help="Reset specific collection only"
    )
    args = parser.parse_args()

    setup_vectordb(reset=args.reset, collection=args.collection)


if __name__ == "__main__":
    main()
