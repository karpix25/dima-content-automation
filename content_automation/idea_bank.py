from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .topic_dedupe import normalize_for_similarity, token_overlap


@dataclass(frozen=True)
class ContentIdea:
    id: int
    user_id: str
    source: str
    source_url: str
    status: str
    title: str
    pain: str
    angle: str
    summary: str
    source_meta: dict[str, Any]
    fingerprint: str
    created_at: str
    updated_at: str


class IdeaBank:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS content_ideas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'new',
                    title TEXT NOT NULL,
                    pain TEXT NOT NULL,
                    angle TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    source_meta_json TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, source_url)
                )
                """
            )

    def add_many(self, user_id: str, ideas: list[dict[str, Any]]) -> list[ContentIdea]:
        inserted: list[ContentIdea] = []
        for idea in ideas:
            record = self.add_if_new(user_id, idea)
            if record:
                inserted.append(record)
        return inserted

    def add_if_new(self, user_id: str, idea: dict[str, Any]) -> ContentIdea | None:
        source = str(idea.get("source") or "reddit")
        fingerprint = idea_fingerprint(idea)
        if source != "notebooklm_plan" and self._has_similar(user_id, fingerprint):
            return None
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO content_ideas (
                    user_id, source, source_url, title, pain, angle, summary, source_meta_json, fingerprint
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    source,
                    str(idea.get("source_url") or ""),
                    str(idea.get("title") or ""),
                    str(idea.get("pain") or ""),
                    str(idea.get("angle") or ""),
                    str(idea.get("summary") or ""),
                    json.dumps(idea.get("source_meta") or {}, ensure_ascii=False),
                    fingerprint,
                ),
            )
            if cursor.rowcount == 0:
                return None
            idea_id = int(cursor.lastrowid)
        return self.get(user_id, idea_id)

    def get(self, user_id: str, idea_id: int) -> ContentIdea | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM content_ideas WHERE user_id = ? AND id = ?",
                (user_id, idea_id),
            ).fetchone()
        return row_to_idea(row) if row else None

    def list_new(self, user_id: str, *, limit: int = 10) -> list[ContentIdea]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM content_ideas
                WHERE user_id = ? AND status = 'new'
                ORDER BY id DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        return [row_to_idea(row) for row in rows]

    def update_status(self, user_id: str, idea_id: int, status: str) -> ContentIdea | None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE content_ideas
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND id = ?
                """,
                (status, user_id, idea_id),
            )
        return self.get(user_id, idea_id)

    def _has_similar(self, user_id: str, fingerprint: str) -> bool:
        if not fingerprint:
            return False
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT fingerprint
                FROM content_ideas
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT 200
                """,
                (user_id,),
            ).fetchall()
        return any(token_overlap(fingerprint, str(row["fingerprint"] or "")) >= 0.68 for row in rows)


def idea_fingerprint(idea: dict[str, Any]) -> str:
    source_meta = idea.get("source_meta") if isinstance(idea.get("source_meta"), dict) else {}
    return normalize_for_similarity(
        " ".join(
            [
                *(str(idea.get(field) or "") for field in ("title", "pain", "angle", "summary")),
                *(str(source_meta.get(field) or "") for field in ("pillar", "format", "visual_note", "source_basis")),
            ]
        )
    )


def row_to_idea(row: sqlite3.Row) -> ContentIdea:
    try:
        source_meta = json.loads(str(row["source_meta_json"] or "{}"))
    except json.JSONDecodeError:
        source_meta = {}
    return ContentIdea(
        id=int(row["id"]),
        user_id=str(row["user_id"]),
        source=str(row["source"]),
        source_url=str(row["source_url"]),
        status=str(row["status"]),
        title=str(row["title"]),
        pain=str(row["pain"]),
        angle=str(row["angle"]),
        summary=str(row["summary"]),
        source_meta=source_meta if isinstance(source_meta, dict) else {},
        fingerprint=str(row["fingerprint"] or ""),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )
