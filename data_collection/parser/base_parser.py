"""
data_collection/parser/base_parser.py

Abstract base class for all parsers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List

from data_collection.crawler.base_crawler import CrawlResult


@dataclass
class ParsedDocument:
    """
    A parsed document ready for chunking.
    """
    content: str
    doc_type: str              # "kernel_source" | "spec" | "paper" | ...
    source_name: str
    uri: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        preview = self.content[:60].replace("\n", " ")
        return (
            f"ParsedDocument("
            f"type={self.doc_type}, "
            f"source={self.source_name}, "
            f"preview='{preview}...')"
        )


class BaseParser(ABC):
    """Abstract base for all parsers."""

    @abstractmethod
    def parse(self, result: CrawlResult) -> List[ParsedDocument]:
        """Parse a CrawlResult into a list of ParsedDocuments."""
        ...

    def can_parse(self, result: CrawlResult) -> bool:
        """Check if this parser can handle the given CrawlResult."""
        return True
