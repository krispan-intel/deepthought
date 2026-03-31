"""
data_collection/crawler/base_crawler.py

Abstract base class for all crawlers.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import AsyncIterator, List, Optional

from loguru import logger

class SourceType(str, Enum):
    GIT_REPO     = "git_repo"
    PDF_SPEC     = "pdf_spec"
    WEB_PAGE     = "web_page"
    MAILING_LIST = "mailing_list"
    API          = "api"
    LOCAL_DATASET = "local_dataset"

@dataclass
class CrawlResult:
    """Raw result from a crawler before parsing."""
    source_name: str
    source_type: SourceType
    uri: str
    content: bytes
    content_type: str          # "text/plain", "application/pdf", etc.
    metadata: dict = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def is_ok(self) -> bool:
        return self.error is None


@dataclass
class DataSource:
    """Definition of a data source to crawl."""
    name: str
    source_type: SourceType
    uri: str
    priority: int              # 1=highest
    update_frequency: str      # "daily" | "weekly" | "on_release"
    domain_tags: List[str]
    parser_hint: str
    extra: dict = field(default_factory=dict)


class BaseCrawler(ABC):
    """Abstract base for all crawlers."""

    def __init__(self, output_dir: Optional[Path] = None):
        from configs.settings import settings
        self.output_dir = output_dir or settings.data_raw_path
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    async def crawl(self, source: DataSource) -> AsyncIterator[CrawlResult]:
        """Crawl a source and yield CrawlResult objects."""
        ...

    def _save_raw(self, result: CrawlResult, filename: str) -> Path:
        """Save raw content to disk."""
        out_path = self.output_dir / result.source_name / filename
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(result.content)
        return out_path

    async def _retry(self, coro, retries: int = 3, delay: float = 2.0):
        """Retry a coroutine with exponential backoff."""
        for attempt in range(retries):
            try:
                return await coro
            except Exception as e:
                if attempt == retries - 1:
                    raise
                wait = delay * (2 ** attempt)
                logger.warning(
                    f"Attempt {attempt + 1} failed: {e}. "
                    f"Retrying in {wait}s..."
                )
                await asyncio.sleep(wait)
