"""
scripts/test_crawlers.py

Dry run test for all data sources.
Verifies network connectivity, API access, and crawler logic
without passing data to the Parser or VectorDB.
"""

import asyncio
import sys
from pathlib import Path

# 確保能讀取根目錄的 module
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from data_collection.scheduler import DATA_SOURCES
from data_collection.crawler.base_crawler import SourceType
from data_collection.crawler.git_crawler import GitCrawler
from data_collection.crawler.api_crawler import ArXivCrawler, LKMLCrawler
from data_collection.crawler.pdf_crawler import PDFCrawler
from data_collection.crawler.dataset_crawler import KaggleArXivCrawler


async def test_all_crawlers(limit_per_source: int = 2):
    logger.info("🧪 Starting Crawler Dry Run Test (No VectorDB)")
    logger.info(f"🎯 Test limit set to {limit_per_source} items per source.\n")

    for source in DATA_SOURCES:
        logger.info(f"========== Testing Source: {source.name} ==========")
        
        # 根據 SourceType 動態指派 Crawler
        if source.source_type == SourceType.GIT_REPO:
            crawler = GitCrawler()
        elif source.source_type == SourceType.API:
            crawler = ArXivCrawler()
        elif source.source_type == SourceType.MAILING_LIST:
            crawler = LKMLCrawler()
        elif source.source_type == SourceType.PDF_SPEC:
            crawler = PDFCrawler()
        elif source.source_type == SourceType.LOCAL_DATASET:
            crawler = KaggleArXivCrawler()
        else:
            logger.warning(f"Unknown source type: {source.source_type}")
            continue

        count = 0
        try:
            # 啟動爬蟲
            async for result in crawler.crawl(source):
                if not result.is_ok:
                    logger.error(f"  ❌ Fetch error: {result.error}")
                    continue
                    
                logger.success(
                    f"  📥 Fetched: {result.uri}\n"
                    f"     Type: {result.content_type} | Size: {len(result.content)} bytes\n"
                    f"     Metadata: {result.metadata}"
                )
                
                count += 1
                if count >= limit_per_source:
                    logger.info(f"  🛑 Reached test limit ({limit_per_source}) for {source.name}.\n")
                    break
                    
        except Exception as e:
            logger.error(f"  💥 Failed to crawl {source.name}: {e}\n")

    logger.info("🎉 All crawler tests completed.")


if __name__ == "__main__":
    asyncio.run(test_all_crawlers())
