from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .topic_dedupe import script_topic_fingerprint


@dataclass(frozen=True)
class ScriptRecord:
    id: int
    user_id: str
    format: str
    status: str
    title: str
    angle: str
    hook: str
    trigger: str
    voiceover: str
    cta: str
    why_it_works: str
    source_basis: str
    raw: dict[str, Any]
    topic_fingerprint: str = ""


@dataclass(frozen=True)
class FormatJob:
    id: int
    user_id: str
    script_id: int
    format_key: str
    task_type: str
    title: str
    status: str
    output_text: str
    external_task_id: str | None
    output_url: str | None
    error: str | None
    raw: dict[str, Any]
    created_at: str
    updated_at: str


class Storage:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_settings (
                    user_id TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    PRIMARY KEY (user_id, key)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scripts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    format TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    title TEXT NOT NULL,
                    angle TEXT NOT NULL,
                    hook TEXT NOT NULL,
                    trigger TEXT NOT NULL,
                    voiceover TEXT NOT NULL,
                    cta TEXT NOT NULL,
                    why_it_works TEXT NOT NULL,
                    source_basis TEXT NOT NULL,
                    raw_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS format_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    script_id INTEGER NOT NULL,
                    format_key TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'ready',
                    output_text TEXT NOT NULL,
                    external_task_id TEXT,
                    output_url TEXT,
                    error TEXT,
                    raw_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self._add_column_if_missing(conn, "format_jobs", "external_task_id", "TEXT")
            self._add_column_if_missing(conn, "format_jobs", "output_url", "TEXT")
            self._add_column_if_missing(conn, "format_jobs", "error", "TEXT")
            self._add_column_if_missing(conn, "scripts", "topic_fingerprint", "TEXT NOT NULL DEFAULT ''")

    def _add_column_if_missing(self, conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        existing = {str(row["name"]) for row in rows}
        if column not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def get_setting(self, user_id: str, key: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM user_settings WHERE user_id = ? AND key = ?",
                (user_id, key),
            ).fetchone()
        return str(row["value"]) if row else None

    def set_setting(self, user_id: str, key: str, value: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO user_settings (user_id, key, value)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id, key) DO UPDATE SET value = excluded.value
                """,
                (user_id, key, value),
            )

    def add_script(self, user_id: str, format: str, payload: dict[str, Any]) -> ScriptRecord:
        normalized = normalize_script_payload(payload)
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO scripts (
                    user_id, format, status, title, angle, hook, trigger, voiceover,
                    cta, why_it_works, source_basis, raw_json, topic_fingerprint
                )
                VALUES (?, ?, 'pending', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    format,
                    normalized["title"],
                    normalized["angle"],
                    normalized["hook"],
                    normalized["trigger"],
                    normalized["voiceover"],
                    normalized["cta"],
                    normalized["why_it_works"],
                    normalized["source_basis"],
                    json.dumps(payload, ensure_ascii=False),
                    normalized["topic_fingerprint"],
                ),
            )
            script_id = int(cursor.lastrowid)
        record = self.get_script(user_id, script_id)
        if not record:
            raise RuntimeError("failed to load inserted script")
        return record

    def get_script(self, user_id: str, script_id: int) -> ScriptRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM scripts WHERE user_id = ? AND id = ?",
                (user_id, script_id),
            ).fetchone()
        return row_to_script(row) if row else None

    def update_script_status(self, user_id: str, script_id: int, status: str) -> ScriptRecord | None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE scripts SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ? AND id = ?",
                (status, user_id, script_id),
            )
        return self.get_script(user_id, script_id)

    def count_scripts(self, user_id: str, *, format: str = "short", status: str | None = None) -> int:
        query = "SELECT COUNT(*) AS count FROM scripts WHERE user_id = ? AND format = ?"
        params: list[Any] = [user_id, format]
        if status:
            query += " AND status = ?"
            params.append(status)
        with self._connect() as conn:
            row = conn.execute(query, params).fetchone()
        return int(row["count"] or 0)

    def count_by_status(self, user_id: str, *, format: str = "short") -> dict[str, int]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT status, COUNT(*) AS count
                FROM scripts
                WHERE user_id = ? AND format = ?
                GROUP BY status
                """,
                (user_id, format),
            ).fetchall()
        return {str(row["status"]): int(row["count"] or 0) for row in rows}

    def list_scripts(
        self,
        user_id: str,
        *,
        format: str = "short",
        status: str | None = None,
        limit: int = 10,
    ) -> list[ScriptRecord]:
        query = "SELECT * FROM scripts WHERE user_id = ? AND format = ?"
        params: list[Any] = [user_id, format]
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY id ASC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [row_to_script(row) for row in rows]

    def list_recent_scripts(
        self,
        user_id: str,
        *,
        format: str = "short",
        limit: int = 50,
    ) -> list[ScriptRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM scripts
                WHERE user_id = ? AND format = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (user_id, format, limit),
            ).fetchall()
        return [row_to_script(row) for row in rows]

    def list_approved_scripts(self, user_id: str, *, limit: int = 50) -> list[ScriptRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM scripts
                WHERE user_id = ? AND format = 'short' AND status = 'approved'
                ORDER BY id DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        return [row_to_script(row) for row in rows]

    def count_approved_today(self, user_id: str, format: str = "short") -> int:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM scripts
                WHERE user_id = ? AND format = ? AND status = 'approved'
                AND date(created_at) = date('now')
                """,
                (user_id, format),
            ).fetchone()
        return int(row["count"] or 0)

    def add_format_job(
        self,
        user_id: str,
        *,
        script_id: int,
        format_key: str,
        task_type: str,
        title: str,
        output_text: str,
        raw: dict[str, Any] | None = None,
    ) -> FormatJob:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO format_jobs (
                    user_id, script_id, format_key, task_type, title, status, output_text, raw_json
                )
                VALUES (?, ?, ?, ?, ?, 'ready', ?, ?)
                """,
                (
                    user_id,
                    script_id,
                    format_key,
                    task_type,
                    title,
                    output_text,
                    json.dumps(raw or {}, ensure_ascii=False),
                ),
            )
            job_id = int(cursor.lastrowid)
        job = self.get_format_job(user_id, job_id)
        if not job:
            raise RuntimeError("failed to load inserted format job")
        return job

    def update_format_job_delivery(
        self,
        user_id: str,
        job_id: int,
        *,
        status: str,
        external_task_id: str | None = None,
        output_url: str | None = None,
        output_text: str | None = None,
        error: str | None = None,
        raw: dict[str, Any] | None = None,
    ) -> FormatJob:
        fields = [
            "status = ?",
            "external_task_id = ?",
            "output_url = ?",
            "error = ?",
            "updated_at = CURRENT_TIMESTAMP",
        ]
        values: list[Any] = [status, external_task_id, output_url, error]
        if output_text is not None:
            fields.append("output_text = ?")
            values.append(output_text)
        if raw is not None:
            fields.append("raw_json = ?")
            values.append(json.dumps(raw, ensure_ascii=False))
        values.extend([user_id, job_id])
        with self._connect() as conn:
            conn.execute(
                f"""
                UPDATE format_jobs
                SET {", ".join(fields)}
                WHERE user_id = ? AND id = ?
                """,
                values,
            )
        job = self.get_format_job(user_id, job_id)
        if not job:
            raise RuntimeError("failed to load updated format job")
        return job

    def claim_queued_format_job(self, user_id: str, job_id: int, *, output_text: str) -> FormatJob | None:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE format_jobs
                SET status = 'processing', output_text = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND id = ? AND status = 'queued'
                """,
                (output_text, user_id, job_id),
            )
        return self.get_format_job(user_id, job_id) if cursor.rowcount else None

    def get_format_job(self, user_id: str, job_id: int) -> FormatJob | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM format_jobs WHERE user_id = ? AND id = ?",
                (user_id, job_id),
            ).fetchone()
        return row_to_format_job(row) if row else None

    def list_format_jobs(self, user_id: str, *, limit: int = 50) -> list[FormatJob]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM format_jobs
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        return [row_to_format_job(row) for row in rows]


def normalize_script_payload(payload: dict[str, Any]) -> dict[str, str]:
    def pick(*keys: str) -> str:
        for key in keys:
            value = payload.get(key)
            if value is not None and str(value).strip():
                return str(value).strip()
        return ""

    return {
        "title": pick("title", "topic", "тема"),
        "angle": pick("angle", "угол"),
        "hook": pick("hook", "хук"),
        "trigger": pick("trigger", "триггер"),
        "voiceover": pick("voiceover", "voice_over", "text", "озвучка", "текст_озвучки"),
        "cta": pick("cta", "призыв"),
        "cta_type": pick("cta_type"),
        "cta_reason": pick("cta_reason"),
        "why_it_works": pick("why_it_works", "why", "почему_сработает"),
        "source_basis": pick("source_basis", "sources", "опора_из_базы"),
        "topic_fingerprint": pick("topic_fingerprint") or script_topic_fingerprint(payload),
    }


def row_to_script(row: sqlite3.Row) -> ScriptRecord:
    return ScriptRecord(
        id=int(row["id"]),
        user_id=str(row["user_id"]),
        format=str(row["format"]),
        status=str(row["status"]),
        title=str(row["title"]),
        angle=str(row["angle"]),
        hook=str(row["hook"]),
        trigger=str(row["trigger"]),
        voiceover=str(row["voiceover"]),
        cta=str(row["cta"]),
        why_it_works=str(row["why_it_works"]),
        source_basis=str(row["source_basis"]),
        raw=json.loads(row["raw_json"] or "{}"),
        topic_fingerprint=str(row["topic_fingerprint"] or ""),
    )


def row_to_format_job(row: sqlite3.Row) -> FormatJob:
    return FormatJob(
        id=int(row["id"]),
        user_id=str(row["user_id"]),
        script_id=int(row["script_id"]),
        format_key=str(row["format_key"]),
        task_type=str(row["task_type"]),
        title=str(row["title"]),
        status=str(row["status"]),
        output_text=str(row["output_text"]),
        external_task_id=str(row["external_task_id"]) if row["external_task_id"] else None,
        output_url=str(row["output_url"]) if row["output_url"] else None,
        error=str(row["error"]) if row["error"] else None,
        raw=json.loads(row["raw_json"] or "{}"),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )
