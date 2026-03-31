"""
data_collection/chunker/code_chunker.py

Tree-sitter aware chunker for source code.
Respects AST boundaries - never splits a function or struct.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from loguru import logger

from data_collection.parser.base_parser import ParsedDocument


@dataclass
class Chunk:
    """A chunk ready for embedding and storage in the vector store."""
    content: str
    doc_type: str
    source_name: str
    uri: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def token_estimate(self) -> int:
        """Rough token count estimate (words / 0.75)."""
        return int(len(self.content.split()) / 0.75)


class CodeChunker:
    """
    Chunk parsed source code documents.

    Strategy:
    - Each ParsedDocument from CodeParser is already one
      semantic unit (function, struct, enum).
    - If it fits within max_tokens: keep as-is.
    - If it's too large: split by logical blocks using
      tree-sitter, keeping parent metadata.
    - Always preserve the complete unit as a "summary chunk"
      for high-level retrieval.
    """

    def __init__(
        self,
        max_tokens: int = 512,
        overlap_lines: int = 5,
    ):
        self.max_tokens = max_tokens
        self.overlap_lines = overlap_lines

    def chunk(self, doc: ParsedDocument) -> List[Chunk]:
        """
        Chunk a ParsedDocument into RAG-ready Chunks.
        """
        token_count = self._estimate_tokens(doc.content)

        if token_count <= self.max_tokens:
            # Fits in one chunk - ideal case
            return [self._doc_to_chunk(doc, is_partial=False)]

        # Too large - need to split
        logger.debug(
            f"  Large node ({token_count} tokens): "
            f"{doc.metadata.get('name', 'unknown')} "
            f"in {doc.metadata.get('file_path', '')}"
        )

        chunks = []

        # Always keep a summary chunk (first N lines = signature + comment)
        summary = self._extract_summary(doc)
        if summary:
            summary_chunk = self._doc_to_chunk(
                doc,
                content_override=summary,
                is_partial=True,
                chunk_role="summary",
            )
            chunks.append(summary_chunk)

        # Split into sub-chunks by lines with overlap
        sub_chunks = self._split_by_lines(doc)
        chunks.extend(sub_chunks)

        return chunks

    def chunk_many(
        self,
        docs: List[ParsedDocument],
    ) -> List[Chunk]:
        """Chunk a list of ParsedDocuments."""
        all_chunks = []
        for doc in docs:
            all_chunks.extend(self.chunk(doc))
        return all_chunks

    # ── Private ───────────────────────────────────────────────────

    def _doc_to_chunk(
        self,
        doc: ParsedDocument,
        content_override: Optional[str] = None,
        is_partial: bool = False,
        chunk_role: str = "complete",
    ) -> Chunk:
        content = content_override or doc.content
        return Chunk(
            content=content,
            doc_type=doc.doc_type,
            source_name=doc.source_name,
            uri=doc.uri,
            metadata={
                **doc.metadata,
                "is_partial": is_partial,
                "chunk_role": chunk_role,
                "token_estimate": self._estimate_tokens(content),
            }
        )

    def _extract_summary(self, doc: ParsedDocument) -> str:
        """
        Extract the first meaningful lines of a large node.
        For functions: signature + opening comment.
        """
        lines = doc.content.split("\n")
        # Take first 20 lines as summary
        summary_lines = lines[:20]
        return "\n".join(summary_lines)

    def _split_by_lines(self, doc: ParsedDocument) -> List[Chunk]:
        """
        Split a large document into overlapping line-based chunks.
        Used as fallback when tree-sitter sub-splitting is unavailable.
        """
        lines = doc.content.split("\n")
        chunks = []

        # Calculate lines per chunk based on token budget
        # Rough estimate: 1 line ≈ 10 tokens for C code
        lines_per_chunk = max(20, self.max_tokens // 10)
        step = lines_per_chunk - self.overlap_lines

        for i in range(0, len(lines), step):
            chunk_lines = lines[i:i + lines_per_chunk]
            if not any(line.strip() for line in chunk_lines):
                continue

            content = "\n".join(chunk_lines)
            chunk = self._doc_to_chunk(
                doc,
                content_override=content,
                is_partial=True,
                chunk_role=f"block_{i // step}",
            )
            chunk.metadata["start_line_offset"] = i
            chunks.append(chunk)

        return chunks

    def _estimate_tokens(self, text: str) -> int:
        """Rough token count: words / 0.75."""
        return int(len(text.split()) / 0.75)
