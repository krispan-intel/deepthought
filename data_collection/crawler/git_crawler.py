"""
data_collection/crawler/git_crawler.py

Crawl Git repositories (Linux kernel, AOSP, etc.)
Uses GitPython for local operations and GitHub API for metadata.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator, List, Optional, Set

import git
from loguru import logger

from data_collection.crawler.base_crawler import (
    BaseCrawler,
    CrawlResult,
    DataSource,
    SourceType,
)


# File extensions we care about
TARGET_EXTENSIONS: Set[str] = {
    ".c", ".h",           # C source
    ".rs",                # Rust (kernel)
    ".cpp", ".cc", ".cxx", ".hpp",  # C++
    ".py",                # Python tools
    ".S", ".s",           # Assembly
    ".ld",                # Linker scripts
}

# Extensions to always skip
SKIP_EXTENSIONS: Set[str] = {
    ".o", ".a", ".so", ".ko",
    ".png", ".jpg", ".gif", ".svg",
    ".tar", ".gz", ".xz", ".zip",
    ".dtb", ".dts",
}


class GitCrawler(BaseCrawler):
    """
    Crawl Git repositories with smart filtering.

    Strategies:
    - Clone once, then pull incremental updates
    - Filter by directory and file extension
    - Extract commit messages as separate documents
    - Track last-processed commit for incremental updates
    """

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        github_token: Optional[str] = None,
    ):
        super().__init__(output_dir)
        self.github_token = github_token
        self._repos: dict = {}

    async def crawl(
        self,
        source: DataSource,
    ) -> AsyncIterator[CrawlResult]:
        """
        Crawl a git repository.

        Yields CrawlResult for:
        - Each source file (filtered by extension and path)
        - Each commit message (design decisions)
        """
        assert source.source_type == SourceType.GIT_REPO

        repo_path = self.output_dir / "repos" / source.name
        target_paths: List[str] = source.extra.get("target_paths", [])
        since_date: Optional[str] = source.extra.get("since_date", None)

        logger.info(f"🔄 Git crawl: {source.name} → {source.uri}")

        # Clone or update
        repo = await self._get_repo(source.uri, repo_path)

        # Crawl source files (Incremental or Full)
        async for result in self._crawl_files(
            repo, repo_path, source, target_paths
        ):
            yield result

        # Crawl commit messages
        async for result in self._crawl_commits(
            repo, source, target_paths, since_date
        ):
            yield result

    async def _get_repo(
        self,
        uri: str,
        repo_path: Path,
    ) -> git.Repo:
        """Clone repo if not exists, otherwise pull latest."""

        if repo_path.exists() and (repo_path / ".git").exists():
            logger.info(f"  Pulling latest: {repo_path.name}")
            repo = git.Repo(repo_path)
            # Run pull in thread to avoid blocking
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: repo.remotes.origin.pull()
            )
        else:
            logger.info(f"  Cloning: {uri}")
            repo_path.parent.mkdir(parents=True, exist_ok=True)

            # Shallow clone for speed (depth=1 for initial)
            # For kernel we want history, so no depth limit
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: git.Repo.clone_from(
                    uri,
                    repo_path,
                    multi_options=["--filter=blob:none"],
                )
            )
            repo = git.Repo(repo_path)

        return repo

    async def _crawl_files(
        self,
        repo: git.Repo,
        repo_path: Path,
        source: DataSource,
        target_paths: List[str],
    ) -> AsyncIterator[CrawlResult]:
        """Yield CrawlResult for each relevant source file."""

        since_date: Optional[str] = source.extra.get("since_date", None)
        count = 0
        
        # 🌟 Incremental Logic: Identify files that changed since last update
        if since_date and since_date != "2020-01-01":
            try:
                logger.info(f"  🔍 Finding files changed since {since_date}...")
                commits = list(repo.iter_commits(after=since_date))
                
                if not commits:
                    logger.info("  ✅ No new files changed since last update.")
                    return
                
                changed_files = set()
                for commit in commits:
                    if commit.parents:
                        diffs = commit.parents[0].diff(commit)
                        for diff in diffs:
                            if diff.b_path: changed_files.add(diff.b_path)
                            if diff.a_path: changed_files.add(diff.a_path)
                            
                # Filter down to specific blobs
                target_blobs = []
                for file_path in changed_files:
                    if target_paths and not any(file_path.startswith(tp) for tp in target_paths):
                        continue
                    try:
                        blob = repo.tree()[file_path]
                        if blob.type == "blob":
                            target_blobs.append(blob)
                    except KeyError:
                        # File was deleted in this commit or path is invalid
                        continue
                        
                logger.info(f"  🔍 Found {len(target_blobs)} modified files matching target paths.")
                        
            except Exception as e:
                logger.warning(f"  Failed to compute incremental diff ({e}), falling back to full scan.")
                target_blobs = [item for item in repo.tree().traverse() if item.type == "blob"]
        else:
            # Full scan logic
            target_blobs = [item for item in repo.tree().traverse() if item.type == "blob"]

        # Iterate over the determined blobs
        for item in target_blobs:
            file_path = item.path

            # Path filter (already done for incremental, but keep for full scan safety)
            if target_paths:
                if not any(
                    file_path.startswith(tp)
                    for tp in target_paths
                ):
                    continue

            # Extension filter
            suffix = Path(file_path).suffix.lower()
            if suffix in SKIP_EXTENSIONS:
                continue
            if suffix not in TARGET_EXTENSIONS:
                continue

            try:
                content = item.data_stream.read()

                # Skip binary files
                try:
                    content.decode("utf-8")
                except UnicodeDecodeError:
                    continue

                yield CrawlResult(
                    source_name=source.name,
                    source_type=SourceType.GIT_REPO,
                    uri=f"{source.uri}/blob/HEAD/{file_path}",
                    content=content,
                    content_type="text/plain",
                    metadata={
                        "file_path": file_path,
                        "file_name": Path(file_path).name,
                        "extension": suffix,
                        "domain_tags": source.domain_tags,
                        "parser_hint": source.parser_hint,
                        "repo": source.name,
                        "size_bytes": len(content),
                    }
                )
                count += 1

            except Exception as e:
                logger.warning(f"  Skipping {file_path}: {e}")
                continue

        logger.info(f"  ✅ Files crawled: {count}")

    async def _crawl_commits(
        self,
        repo: git.Repo,
        source: DataSource,
        target_paths: List[str],
        since_date: Optional[str],
    ) -> AsyncIterator[CrawlResult]:
        """
        Yield commit messages as documents.

        Commit messages are gold for DeepThought:
        - Why was this change made?
        - What problem does it solve?
        - What was rejected and why?
        """
        count = 0
        kwargs = {}

        if since_date:
            kwargs["after"] = since_date

        if target_paths:
            kwargs["paths"] = target_paths

        try:
            commits = list(repo.iter_commits(**kwargs))
        except Exception as e:
            logger.warning(f"  Could not iterate commits: {e}")
            return

        for commit in commits:
            # Skip merge commits with no message
            if not commit.message.strip():
                continue

            # Format commit as structured text
            content = (
                f"COMMIT: {commit.hexsha[:12]}\n"
                f"AUTHOR: {commit.author.name}\n"
                f"DATE: {datetime.fromtimestamp(commit.committed_date)}\n"
                f"FILES CHANGED: "
                f"{commit.stats.total.get('files', 0)}\n"
                f"\n"
                f"MESSAGE:\n{commit.message.strip()}\n"
            )

            yield CrawlResult(
                source_name=source.name,
                source_type=SourceType.GIT_REPO,
                uri=f"{source.uri}/commit/{commit.hexsha}",
                content=content.encode("utf-8"),
                content_type="text/plain",
                metadata={
                    "doc_subtype": "commit_message",
                    "commit_sha": commit.hexsha[:12],
                    "author": commit.author.name,
                    "date": str(
                        datetime.fromtimestamp(commit.committed_date)
                    ),
                    "files_changed": commit.stats.total.get("files", 0),
                    "domain_tags": source.domain_tags,
                    "repo": source.name,
                }
            )
            count += 1

        logger.info(f"  ✅ Commits crawled: {count}")