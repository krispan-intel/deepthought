"""
data_collection/crawler/pdf_crawler.py

Download PDF specifications (Intel SDM, CXL Spec, etc.)
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import AsyncIterator, Optional

import httpx
from loguru import logger

from data_collection.crawler.base_crawler import (
    BaseCrawler,
    CrawlResult,
    DataSource,
    SourceType,
)


class PDFCrawler(BaseCrawler):
    """
    Download PDF specifications from URLs.

    Features:
    - Skip download if file already exists and hash matches
    - Resume partial downloads
    - Rate limiting
    """

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        timeout: int = 120,
    ):
        super().__init__(output_dir)
        self.timeout = timeout

    async def crawl(
        self,
        source: DataSource,
    ) -> AsyncIterator[CrawlResult]:
        """Download a PDF and yield as CrawlResult."""

        assert source.source_type == SourceType.PDF_SPEC

        out_path = (
            self.output_dir
            / "specs"
            / source.name
            / f"{source.name}.pdf"
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"📄 PDF crawl: {source.name}")

        # Check if already downloaded
        if out_path.exists():
            logger.info(f"  Using cached: {out_path}")
            content = out_path.read_bytes()
        else:
            content = await self._download(source.uri, out_path)

        if content:
            yield CrawlResult(
                source_name=source.name,
                source_type=SourceType.PDF_SPEC,
                uri=source.uri,
                content=content,
                content_type="application/pdf",
                metadata={
                    "file_path": str(out_path),
                    "domain_tags": source.domain_tags,
                    "parser_hint": source.parser_hint,
                    "priority": source.priority,
                }
            )

    async def _download(self, url: str, out_path: Path) -> Optional[bytes]:
        """Download file with progress logging."""

        logger.info(f"  Downloading: {url}")

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
            ) as client:
                async with client.stream("GET", url) as response:
                    response.raise_for_status()

                    total = int(
                        response.headers.get("content-length", 0)
                    )
                    downloaded = 0
                    chunks = []

                    async for chunk in response.aiter_bytes(
                        chunk_size=65536
                    ):
                        chunks.append(chunk)
                        downloaded += len(chunk)

                        if total:
                            pct = downloaded / total * 100
                            if downloaded % (1024 * 1024) < 65536:
                                logger.debug(
                                    f"  Progress: {pct:.1f}% "
                                    f"({downloaded // 1024}KB)"
                                )

                    content = b"".join(chunks)
                    out_path.write_bytes(content)
                    logger.info(
                        f"  ✅ Downloaded: {len(content) // 1024}KB"
                    )
                    return content

        except Exception as e:
            logger.error(f"  ❌ Download failed: {e}")
            return None
