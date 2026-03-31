"""
scripts/ingest_all.py

Master script to ingest all configured data sources into the Vector DB.
It uses the scheduler logic to only ingest what's necessary (incremental).
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from data_collection.scheduler import DataScheduler

async def main():
    logger.info("🚀 Starting DeepThought Master Ingestion Pipeline")

    scheduler = DataScheduler()

    await scheduler.run_once(force=True)
    
    logger.info("🏁 Master Ingestion Pipeline Completed!")

if __name__ == "__main__":
    asyncio.run(main())
