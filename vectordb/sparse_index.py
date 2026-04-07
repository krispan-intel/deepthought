from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]{2,}")
STOPWORDS = {
    "and", "are", "but", "for", "from", "into", "not", "that", "the",
    "their", "then", "this", "was", "will", "with", "using", "use", "via",
    "linux", "kernel", "intel", "system", "code", "data", "docs", "paper",
}


class SparseCooccurrenceIndex:
    """SQLite FTS5 sidecar for lexical co-occurrence checks."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS sparse_docs USING fts5(
                doc_id UNINDEXED,
                collection,
                label,
                content,
                tokenize='unicode61 remove_diacritics 2'
            )
            """
        )
        self.conn.commit()

    def reset_collection(self, collection: str) -> None:
        self.conn.execute("DELETE FROM sparse_docs WHERE collection = ?", (collection,))
        self.conn.commit()

    def upsert_records(self, records: Iterable[Dict[str, str]], collection: str) -> int:
        self.reset_collection(collection)
        rows = [
            (
                item.get("doc_id", ""),
                collection,
                item.get("label", ""),
                item.get("content", ""),
            )
            for item in records
        ]
        if not rows:
            return 0

        self.conn.executemany(
            "INSERT INTO sparse_docs(doc_id, collection, label, content) VALUES (?, ?, ?, ?)",
            rows,
        )
        self.conn.commit()
        return len(rows)

    def count_for_collection(self, collection: str) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) FROM sparse_docs WHERE collection = ?",
            (collection,),
        ).fetchone()
        return int(row[0]) if row else 0

    def has_cooccurrence(
        self,
        tokens_a: List[str],
        tokens_b: List[str],
        collections: Optional[List[str]] = None,
    ) -> bool:
        left = self._build_or_clause(tokens_a)
        right = self._build_or_clause(tokens_b)
        if not left or not right:
            return False

        match_query = f"({left}) AND ({right})"
        sql = "SELECT 1 FROM sparse_docs WHERE sparse_docs MATCH ?"
        params: List[Any] = [match_query]
        if collections:
            placeholders = ", ".join("?" for _ in collections)
            sql += f" AND collection IN ({placeholders})"
            params.extend(collections)
        sql += " LIMIT 1"

        row = self.conn.execute(sql, params).fetchone()
        return row is not None

    @staticmethod
    def extract_top_tokens(text: str, max_tokens: int = 5) -> List[str]:
        counts: Dict[str, int] = {}
        first_seen: Dict[str, int] = {}

        for idx, match in enumerate(TOKEN_RE.findall((text or "").lower())):
            if match in STOPWORDS:
                continue
            counts[match] = counts.get(match, 0) + 1
            first_seen.setdefault(match, idx)

        ranked = sorted(
            counts,
            key=lambda token: (-counts[token], first_seen[token]),
        )
        return ranked[:max_tokens]

    @staticmethod
    def _build_or_clause(tokens: List[str]) -> str:
        cleaned = [token.strip().lower() for token in tokens if token and token.strip()]
        if not cleaned:
            return ""
        quoted = [f'"{token.replace(chr(34), "")}"' for token in cleaned]
        return " OR ".join(quoted)