"""
data_collection/crawler/api_crawler.py

Crawl APIs: ArXiv papers, USPTO patents, LKML archives.
"""

from __future__ import annotations

import asyncio
import json
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path
from typing import AsyncIterator, List, Optional

import httpx
from loguru import logger

from data_collection.crawler.base_crawler import (
    BaseCrawler,
    CrawlResult,
    DataSource,
    SourceType,
)


# 🌟 新增：偽裝成正常瀏覽器，避免被 LKML 和 ArXiv 的防火牆擋下
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/atom+xml,application/xml,text/xml,application/json,*/*",
}


class ArXivCrawler(BaseCrawler):
    """
    Crawl ArXiv papers via the ArXiv API.

    Target categories:
    - cs.AR  (Hardware Architecture)
    - cs.OS  (Operating Systems)
    - cs.PF  (Performance)
    - cs.DC  (Distributed Computing)
    """

    BASE_URL = "http://export.arxiv.org/api/query"

    CATEGORIES = [
        "cs.AR",   # Hardware Architecture
        "cs.OS",   # Operating Systems
        "cs.PF",   # Performance
        "cs.DC",   # Distributed Computing
        "cs.SY",   # Systems and Control
    ]

    # 🌟 優化：將 Keywords 縮減，避免 ArXiv 伺服器 504 Timeout
    KEYWORDS = [
        "linux kernel",
        "x86 architecture",
        "cpu scheduler",
        "memory management",
    ]

    async def crawl(
        self,
        source: DataSource,
    ) -> AsyncIterator[CrawlResult]:
        """Fetch recent papers from ArXiv."""

        max_results = source.extra.get("max_results", 100)
        days_back = source.extra.get("days_back", 30)
        since = datetime.now() - timedelta(days=days_back)

        logger.info(
            f"📚 ArXiv crawl | "
            f"categories={self.CATEGORIES} | "
            f"since={since.date()}"
        )

        for category in self.CATEGORIES:
            async for result in self._fetch_category(
                category=category,
                since=since,
                max_results=max_results,
            ):
                yield result

            # 🌟 新增：溫柔對待免費 API，避免連續請求被封鎖
            await asyncio.sleep(3)

    async def _fetch_category(
        self,
        category: str,
        since: datetime,
        max_results: int,
    ) -> AsyncIterator[CrawlResult]:
        """Fetch papers for a single ArXiv category."""

        # 🌟 優化：簡化查詢字串，並確保 URL Encoding 正確
        keyword_query = "+OR+".join(f'all:"{urllib.parse.quote(kw)}"' for kw in self.KEYWORDS)
        query = f"cat:{category}+AND+({keyword_query})"

        # 注意：ArXiv API 不喜歡標準的 urllib.parse.urlencode，我們手動拼接 URL
        url = f"{self.BASE_URL}?search_query={query}&start=0&max_results={max_results}&sortBy=submittedDate&sortOrder=descending"

        try:
            # 🌟 新增：拉長 Timeout 並加入 User-Agent
            async with httpx.AsyncClient(timeout=60.0, headers=HEADERS) as client:
                response = await client.get(url)
                response.raise_for_status()

                # Parse Atom XML
                papers = self._parse_arxiv_response(response.text)
                count = 0

                for paper in papers:
                    yield CrawlResult(
                        source_name="arxiv",
                        source_type=SourceType.API,
                        uri=paper["url"],
                        content=json.dumps(paper).encode("utf-8"),
                        content_type="application/json",
                        metadata={
                            "doc_subtype": "arxiv_paper",
                            "arxiv_id": paper["id"],
                            "title": paper["title"],
                            "authors": paper["authors"],
                            "category": category,
                            "submitted": paper["submitted"],
                            "domain_tags": ["research", "paper", category],
                            "parser_hint": "academic_paper",
                        }
                    )
                    count += 1

                logger.info(
                    f"  ✅ ArXiv {category}: {count} papers"
                )

        except Exception as e:
            logger.error(f"  ❌ ArXiv {category} failed: {e}")

    def _parse_arxiv_response(self, xml_text: str) -> List[dict]:
        """Parse ArXiv Atom XML response."""
        import xml.etree.ElementTree as ET

        papers = []
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom",
        }

        try:
            root = ET.fromstring(xml_text)
            entries = root.findall("atom:entry", ns)

            for entry in entries:
                paper = {
                    "id": entry.findtext(
                        "atom:id", "", ns
                    ).split("/")[-1],
                    "title": entry.findtext(
                        "atom:title", "", ns
                    ).strip().replace("\n", " "),
                    "summary": entry.findtext(
                        "atom:summary", "", ns
                    ).strip(),
                    "url": entry.findtext("atom:id", "", ns),
                    "submitted": entry.findtext(
                        "atom:published", "", ns
                    ),
                    "authors": [
                        a.findtext("atom:name", "", ns)
                        for a in entry.findall("atom:author", ns)
                    ],
                }
                papers.append(paper)

        except ET.ParseError as e:
            logger.error(f"XML parse error: {e}")

        return papers


class LKMLCrawler(BaseCrawler):
    """
    Crawl Linux Kernel Mailing List archives via lore.kernel.org.
    """

    BASE_URL = "https://lore.kernel.org"

    LISTS = [
        "linux-kernel",
        "linux-mm",
        "linux-arch",
        "linux-perf-users",
        "bpf",
        "linux-scheduler",
    ]

    async def crawl(
        self,
        source: DataSource,
    ) -> AsyncIterator[CrawlResult]:
        """Crawl recent LKML threads."""

        days_back = source.extra.get("days_back", 30)
        max_threads = source.extra.get("max_threads", 200)

        logger.info(
            f"📧 LKML crawl | "
            f"lists={self.LISTS} | "
            f"days_back={days_back}"
        )

        for mailing_list in self.LISTS:
            async for result in self._fetch_list(
                mailing_list=mailing_list,
                days_back=days_back,
                max_threads=max_threads,
            ):
                yield result
            
            # 🌟 新增：避免短時間高頻連線被 lore.kernel.org 封鎖
            await asyncio.sleep(2)

    async def _fetch_list(
        self,
        mailing_list: str,
        days_back: int,
        max_threads: int,
    ) -> AsyncIterator[CrawlResult]:
        """Fetch threads from a single mailing list."""

        url = f"{self.BASE_URL}/{mailing_list}/"
        count = 0

        lkml_headers = {
            "User-Agent": "Mozilla/5.0 (compatible; Linux Kernel Feed Reader/1.0)",
            "Accept": "application/atom+xml,application/xml,text/xml",
        }

        try:
            # 🌟 新增：加入 User-Agent 破解 403 Forbidden
            async with httpx.AsyncClient(
                timeout=45.0, 
                headers=lkml_headers, 
                follow_redirects=True
            ) as client:
                # Fetch the list index (Atom feed)
                response = await client.get(
                    f"{url}?x=A&q=d:{days_back}d",
                )

                if response.status_code != 200:
                    logger.warning(
                        f"  LKML {mailing_list}: "
                        f"HTTP {response.status_code}"
                    )
                    return

                threads = self._parse_lkml_feed(response.text)

                for thread in threads[:max_threads]:
                    content = json.dumps(thread).encode("utf-8")

                    yield CrawlResult(
                        source_name="lkml",
                        source_type=SourceType.MAILING_LIST,
                        uri=thread.get("url", ""),
                        content=content,
                        content_type="application/json",
                        metadata={
                            "doc_subtype": "lkml_thread",
                            "list": mailing_list,
                            "subject": thread.get("subject", ""),
                            "date": thread.get("date", ""),
                            "domain_tags": [
                                "linux", "kernel", "discussion",
                                mailing_list,
                            ],
                            "parser_hint": "email_thread",
                        }
                    )
                    count += 1

            logger.info(
                f"  ✅ LKML {mailing_list}: {count} threads"
            )

        except Exception as e:
            logger.error(f"  ❌ LKML {mailing_list} failed: {e}")

    def _parse_lkml_feed(self, xml_text: str) -> List[dict]:
        """Parse lore.kernel.org Atom feed."""
        import xml.etree.ElementTree as ET

        threads = []
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        try:
            root = ET.fromstring(xml_text)
            for entry in root.findall("atom:entry", ns):
                threads.append({
                    "subject": entry.findtext(
                        "atom:title", "", ns
                    ).strip(),
                    "url": entry.findtext("atom:id", "", ns),
                    "date": entry.findtext(
                        "atom:updated", "", ns
                    ),
                    "summary": entry.findtext(
                        "atom:summary", "", ns
                    ),
                })
        except ET.ParseError as e:
            logger.error(f"LKML XML parse error: {e}")

        return threads