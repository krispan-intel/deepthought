"""
scripts/ingest_kernel.py

Ingest Linux Kernel source code into the DeepThought Vector Store.

Usage:
    python scripts/ingest_kernel.py
    python scripts/ingest_kernel.py --subsystem arch/x86
    python scripts/ingest_kernel.py --subsystem kernel/sched --limit 500
    python scripts/ingest_kernel.py --force-refresh
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from configs.settings import settings
from data_collection.crawler.base_crawler import DataSource, SourceType
from data_collection.crawler.git_crawler import GitCrawler
from data_collection.parser.code_parser import CodeParser
from data_collection.parser.kconfig_parser import KconfigParser
from data_collection.chunker.code_chunker import CodeChunker
from vectordb.store import DeepThoughtVectorStore, CollectionName
from data_collection.scheduler import UpdateTracker

SUBSYSTEM_PATHS = {
    "arch/x86":     ["arch/x86/"],
    "sched":        ["kernel/sched/"],
    "mm":           ["mm/"],
    "bpf":          ["kernel/bpf/", "tools/bpf/"],
    "perf":         ["tools/perf/"],
    "headers":      ["include/linux/"],
    "docs":         ["Documentation/"],
    "all":          [
        "arch/x86/",
        "kernel/sched/",
        "kernel/bpf/",
        "mm/",
        "include/linux/",
        "tools/perf/",
        "Documentation/",
    ],
}

def clean_metadata(metadata: dict) -> dict:
    """
    Clean metadata dictionary to be ChromaDB compatible.
    ChromaDB does not accept empty lists, None values, or complex objects.
    """
    cleaned = {}
    for key, value in metadata.items():
        if value is None:
            continue  # 捨棄 None
            
        if isinstance(value, list):
            if not value:
                continue
            cleaned[key] = [str(v) if not isinstance(v, (str, int, float)) else v for v in value]
            
        elif isinstance(value, (str, int, float, bool)):
            cleaned[key] = value
        else:
            cleaned[key] = str(value)
            
    return cleaned

async def ingest_kernel(
    subsystem: str = "all",
    limit: int = 0,
    force_refresh: bool = False,
):
    logger.info(f"🐧 Ingesting Linux Kernel | subsystem={subsystem}")

    tracker = UpdateTracker()
    last_update = tracker.get_last_update(f"linux_kernel_{subsystem}")

    if last_update and not force_refresh:
        since_date_str = last_update.strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"🔄 Incremental Update: Fetching commits since {since_date_str}")
    else:
        since_date_str = "2020-01-01"
        logger.info("🚀 Full Ingestion or Force Refresh")

    target_paths = SUBSYSTEM_PATHS.get(subsystem)
    if not target_paths:
        logger.error(
            f"Unknown subsystem: {subsystem}\n"
            f"Valid: {list(SUBSYSTEM_PATHS.keys())}"
        )
        sys.exit(1)

    # Build source definition
    source = DataSource(
        name="linux_kernel",
        source_type=SourceType.GIT_REPO,
        uri="https://github.com/torvalds/linux",
        priority=1,
        update_frequency="daily",
        domain_tags=["linux", "kernel", "source"],
        parser_hint="c_source_with_comments",
        extra={
            "target_paths": target_paths,
            "since_date": since_date_str
        },
    )

    # Initialize components
    crawler  = GitCrawler(github_token=settings.github_token)
    code_parser    = CodeParser()
    kconfig_parser = KconfigParser()
    chunker  = CodeChunker(max_tokens=512)
    store    = DeepThoughtVectorStore()

    total_chunks = 0
    file_count   = 0

    async for crawl_result in crawler.crawl(source):
        if limit and file_count >= limit:
            logger.info(f"Reached limit of {limit} files")
            break

        if not crawl_result.is_ok:
            continue

        file_path = crawl_result.metadata.get("file_path", "")

        # Choose parser
        if Path(file_path).name == "Kconfig":
            docs = kconfig_parser.parse(crawl_result)
            collection = CollectionName.KERNEL_SOURCE
        elif crawl_result.metadata.get("doc_subtype") == "commit_message":
            from data_collection.parser.base_parser import ParsedDocument
            docs = [ParsedDocument(
                content=crawl_result.content.decode("utf-8"),
                doc_type="commit_message",
                source_name=crawl_result.source_name,
                uri=crawl_result.uri,
                metadata=crawl_result.metadata,
            )]
            collection = CollectionName.KERNEL_DISCUSSION
        else:
            docs = code_parser.parse(crawl_result)
            collection = CollectionName.KERNEL_SOURCE

        if not docs:
            continue

        # Chunk
        chunks = chunker.chunk_many(docs)

        if not chunks:
            continue

        # Convert to store Documents
        from vectordb.store import Document
        store_docs = [
            Document(
                content=chunk.content,
                metadata=clean_metadata(chunk.metadata),
            )
            for chunk in chunks
        ]

        # Add to vector store
        added = store.add_documents(store_docs, collection)
        total_chunks += added
        file_count += 1

        if file_count % 100 == 0:
            logger.info(
                f"  Progress: {file_count} files | "
                f"{total_chunks} chunks"
            )

    logger.info(
        f"✅ Kernel ingestion complete | "
        f"files={file_count} | "
        f"chunks={total_chunks}"
    )
    store.print_stats()

    tracker.mark_updated(f"linux_kernel_{subsystem}")


def main():
    parser = argparse.ArgumentParser(
        description="Ingest Linux Kernel into DeepThought"
    )
    parser.add_argument(
        "--subsystem",
        default="all",
        help=f"Subsystem to ingest: {list(SUBSYSTEM_PATHS.keys())}",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Max files to process (0 = no limit)",
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Re-ingest even if already in vector store",
    )
    args = parser.parse_args()

    asyncio.run(ingest_kernel(
        subsystem=args.subsystem,
        limit=args.limit,
        force_refresh=args.force_refresh,
    ))


if __name__ == "__main__":
    main()
