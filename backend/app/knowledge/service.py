from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class KnowledgeHit:
    document_id: str
    title: str
    snippet: str
    review_status: str
    trust_label: str = "UNTRUSTED_DATA"


class FTSKnowledgeBase:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING "
                "fts5(document_id UNINDEXED, title, content, review_status UNINDEXED)"
            )

    def add(
        self, document_id: str, title: str, content: str, review_status: str = "PENDING"
    ) -> None:
        if review_status not in {"PENDING", "APPROVED", "REJECTED"}:
            raise ValueError("invalid review status")
        with sqlite3.connect(self.path) as db:
            db.execute(
                "INSERT INTO knowledge_fts(document_id,title,content,review_status) VALUES(?,?,?,?)",
                (document_id, title, content, review_status),
            )

    def search(self, query: str, limit: int = 10) -> list[KnowledgeHit]:
        if not query.strip() or not 1 <= limit <= 50:
            raise ValueError("invalid search")
        with sqlite3.connect(self.path) as db:
            rows = db.execute(
                "SELECT document_id,title,snippet(knowledge_fts,2,'[',']','…',12),"
                "review_status FROM knowledge_fts WHERE knowledge_fts MATCH ? "
                "ORDER BY bm25(knowledge_fts), rowid DESC LIMIT ?",
                (query, limit),
            ).fetchall()
        return [KnowledgeHit(*row) for row in rows]

    def search_approved(self, query: str, limit: int = 5) -> list[KnowledgeHit]:
        tokens = re.findall(r"[A-Za-z0-9_\u4e00-\u9fff-]+", query)[:12]
        if not tokens or not 1 <= limit <= 20:
            return []
        expression = " OR ".join(f'"{token}"' for token in tokens)
        try:
            with sqlite3.connect(self.path) as db:
                rows = db.execute(
                    "SELECT document_id,title,snippet(knowledge_fts,2,'[',']','…',12),"
                    "review_status FROM knowledge_fts WHERE knowledge_fts MATCH ? "
                    "AND review_status='APPROVED' ORDER BY bm25(knowledge_fts), rowid DESC LIMIT ?",
                    (expression, limit),
                ).fetchall()
        except sqlite3.OperationalError:
            return []
        return [KnowledgeHit(*row) for row in rows]

    def review(self, document_id: str, status: str) -> None:
        if status not in {"APPROVED", "REJECTED"}:
            raise ValueError("invalid review status")
        with sqlite3.connect(self.path) as db:
            cursor = db.execute(
                "UPDATE knowledge_fts SET review_status=? WHERE document_id=?",
                (status, document_id),
            )
            if cursor.rowcount == 0:
                raise ValueError("document not found")
