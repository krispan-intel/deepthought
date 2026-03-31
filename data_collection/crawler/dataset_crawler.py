"""
data_collection/crawler/dataset_crawler.py

Crawl large local datasets (e.g., Kaggle ArXiv JSONL).
Uses streaming to prevent memory overload.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import AsyncIterator

from loguru import logger

from data_collection.crawler.base_crawler import (
    BaseCrawler,
    CrawlResult,
    DataSource,
    SourceType,
)

class KaggleArXivCrawler(BaseCrawler):
    """
    Reads the massive arxiv-metadata-oai-snapshot.json file line by line.
    Filters out papers that don't match our target categories.
    """

    async def crawl(
        self,
        source: DataSource,
    ) -> AsyncIterator[CrawlResult]:
        assert source.source_type == SourceType.LOCAL_DATASET

        filepath = Path(source.uri)
        if not filepath.exists():
            logger.error(f"❌ Dataset not found at: {filepath}")
            logger.error("Please download it from Kaggle and place it there.")
            return

        target_categories = source.extra.get("target_categories", [])
        max_records = source.extra.get("max_records", 0)

        logger.info(f"📂 Reading Kaggle dataset: {filepath.name}")
        count = 0

        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    paper = json.loads(line)
                    categories = paper.get("categories", "")

                    if not any(cat in categories for cat in target_categories):
                        continue

                    yield CrawlResult(
                        source_name=source.name,
                        source_type=SourceType.LOCAL_DATASET,
                        uri=f"arxiv:{paper.get('id')}",
                        content=json.dumps(paper).encode("utf-8"),
                        content_type="application/json",
                        metadata={
                            "doc_subtype": "arxiv_paper",
                            "arxiv_id": paper.get("id"),
                            "title": paper.get("title", "").replace("\n", " "),
                            "authors": paper.get("submitter", "Unknown"),
                            "category": categories,
                            "update_date": paper.get("update_date", ""),
                            "domain_tags": source.domain_tags + [categories.split()[0]],
                            "parser_hint": source.parser_hint,
                        }
                    )
                    count += 1

                    if count % 5000 == 0:
                        logger.info(f"  ... Extracted {count} relevant papers")
                        await asyncio.sleep(0) 

                    if max_records and count >= max_records:
                        logger.info(f"🛑 Reached max_records limit ({max_records})")
                        break

                except json.JSONDecodeError:
                    continue

        logger.info(f"✅ Finished Kaggle dataset. Total extracted: {count}")
