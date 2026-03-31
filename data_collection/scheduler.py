"""
data_collection/scheduler.py

Incremental update scheduler for all data sources.
Monitors sources for changes and triggers re-ingestion.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from loguru import logger

from configs.settings import settings
from data_collection.crawler.base_crawler import DataSource


# ─────────────────────────────────────────────────────────────────
# Source Registry
# ─────────────────────────────────────────────────────────────────

from data_collection.crawler.base_crawler import SourceType

DATA_SOURCES = [

    # ── Linux Kernel ─────────────────────────────────────────────
    DataSource(
        name="linux_kernel",
        source_type=SourceType.GIT_REPO,
        uri="https://github.com/torvalds/linux",
        priority=1,
        update_frequency="daily",
        domain_tags=["linux", "kernel", "source"],
        parser_hint="c_source_with_comments",
        extra={
            "target_paths": [
                "arch/x86/",
                "kernel/sched/",
                "kernel/bpf/",
                "mm/",
                "include/linux/",
                "tools/perf/",
                "Documentation/",
            ],
            "since_date": "2020-01-01",
        }
    ),

    # ── Intel SDM ────────────────────────────────────────────────
    DataSource(
        name="intel_sdm",
        source_type=SourceType.PDF_SPEC,
        uri="https://cdrdv2.intel.com/v1/dl/getContent/671200",
        priority=1,
        update_frequency="on_release",
        domain_tags=["x86", "isa", "hardware", "intel"],
        parser_hint="technical_manual",
    ),

    # ── Intel Optimization Manual ─────────────────────────────────
    DataSource(
        name="intel_opt_manual",
        source_type=SourceType.PDF_SPEC,
        uri="https://cdrdv2.intel.com/v1/dl/getContent/671488",
        priority=1,
        update_frequency="on_release",
        domain_tags=["x86", "performance", "optimization", "intel"],
        parser_hint="technical_manual",
    ),

    # ── Kaggle ArXiv Dataset (Local) ─────────────────────────────
    DataSource(
        name="arxiv_kaggle",
        source_type=SourceType.LOCAL_DATASET,
        uri="data/raw/arxiv/arxiv-metadata-oai-snapshot.json",
        priority=2,
        update_frequency="on_release",
        domain_tags=["research", "paper"],
        parser_hint="academic_paper",
        extra={
            "target_categories": ["cs.AR", "cs.OS", "cs.PF", "cs.DC"],
            "max_records": 0, 
        }
    ),

    # ── LKML ─────────────────────────────────────────────────────
    # DataSource(
    #     name="lkml",
    #     source_type=SourceType.MAILING_LIST,
    #     uri="https://lore.kernel.org",
    #     priority=2,
    #     update_frequency="daily",
    #     domain_tags=["linux", "kernel", "discussion"],
    #     parser_hint="email_thread",
    #     extra={
    #         "days_back": 30,
    #         "max_threads": 200,
    #     }
    # ),

    # ── AOSP (Android Open Source Project) ───────────────────────
    # DataSource(
    #     name="aosp",
    #     source_type=SourceType.GIT_REPO,
    #     uri="https://android.googlesource.com/platform/bionic",
    #     priority=2,
    #     update_frequency="weekly",
    #     domain_tags=["android", "aosp", "bionic", "libc", "allocator"],
    #     parser_hint="c_source_with_comments",
    #     extra={
    #         "target_paths": [
    #             "libc/",                # Android's custom C library
    #             "libm/",                # Math library optimizations
    #             "linker/",              # Dynamic linker (crucial for perf)
    #             "benchmarks/",          # Performance test cases (goldmine)
    #         ],
    #         "since_date": "2023-01-01",
    #     }
    # ),
]


# ─────────────────────────────────────────────────────────────────
# Update Tracker
# ─────────────────────────────────────────────────────────────────

class UpdateTracker:
    """Track last update times for each data source."""

    def __init__(self):
        self.state_file = settings.data_processed_path / "update_state.json"
        self._state: Dict[str, str] = self._load()

    def _load(self) -> Dict[str, str]:
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text())
            except Exception:
                return {}
        return {}

    def _save(self):
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(self._state, indent=2))

    def get_last_update(self, source_name: str) -> Optional[datetime]:
        ts = self._state.get(source_name)
        if ts:
            return datetime.fromisoformat(ts)
        return None

    def mark_updated(self, source_name: str):
        self._state[source_name] = datetime.now().isoformat()
        self._save()

    def needs_update(self, source: DataSource) -> bool:
        last = self.get_last_update(source.name)
        if last is None:
            return True

        now = datetime.now()
        delta = now - last

        if source.update_frequency == "daily":
            return delta.days >= 1
        elif source.update_frequency == "weekly":
            return delta.days >= 7
        elif source.update_frequency == "on_release":
            # Manual trigger only
            return False

        return False


# ─────────────────────────────────────────────────────────────────
# Scheduler
# ─────────────────────────────────────────────────────────────────

class DataScheduler:
    """
    Monitors data sources and triggers incremental updates.
    """

    def __init__(self):
        self.tracker = UpdateTracker()
        self.sources = DATA_SOURCES

    async def run_once(self, force: bool = False):
        """
        Check all sources and update those that need it.
        """
        logger.info("🔄 Data Scheduler: checking sources...")

        for source in self.sources:
            if force or self.tracker.needs_update(source):
                logger.info(f"  Updating: {source.name}")
                try:
                    await self._update_source(source)
                    self.tracker.mark_updated(source.name)
                    logger.info(f"  ✅ Updated: {source.name}")
                except Exception as e:
                    logger.error(
                        f"  ❌ Failed: {source.name}: {e}"
                    )
            else:
                last = self.tracker.get_last_update(source.name)
                logger.debug(
                    f"  Skipping {source.name} "
                    f"(last updated: {last})"
                )

    async def run_forever(self, check_interval: int = 3600):
        """
        Run scheduler loop indefinitely.
        Checks for updates every check_interval seconds.
        """
        logger.info(
            f"🔄 Data Scheduler started | "
            f"interval={check_interval}s"
        )
        while True:
            await self.run_once()
            logger.info(
                f"💤 Scheduler sleeping {check_interval}s..."
            )
            await asyncio.sleep(check_interval)

    async def _update_source(self, source: DataSource):
        """
        Trigger ingestion for a single source.
        Imports here to avoid circular imports.
        """
        from services.ingestion_service import IngestionService
        service = IngestionService()
        await service.ingest_source(source)
