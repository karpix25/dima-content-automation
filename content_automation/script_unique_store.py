from __future__ import annotations

import json
import sqlite3
from typing import Any, Callable

from .script_uniqueness import unique_script_keys


class DuplicateScriptError(RuntimeError):
    def __init__(self, kind: str):
        super().__init__(f"duplicate script {kind}")
        self.kind = kind


def create_script_unique_keys_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS script_unique_keys (
            user_id TEXT NOT NULL,
            format TEXT NOT NULL,
            kind TEXT NOT NULL,
            key TEXT NOT NULL,
            script_id INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, format, kind, key)
        )
        """
    )


def backfill_script_unique_keys(conn: sqlite3.Connection, normalize_payload: Callable[[dict[str, Any]], dict[str, str]]) -> None:
    rows = conn.execute("SELECT * FROM scripts ORDER BY id ASC").fetchall()
    for row in rows:
        raw = json.loads(row["raw_json"] or "{}")
        normalized = normalize_payload(raw)
        for kind, key in unique_script_keys(raw, normalized):
            conn.execute(
                """
                INSERT OR IGNORE INTO script_unique_keys (user_id, format, kind, key, script_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (str(row["user_id"]), str(row["format"]), kind, key, int(row["id"])),
            )


def claim_script_unique_keys(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    format: str,
    keys: list[tuple[str, str]],
) -> None:
    for kind, key in keys:
        try:
            conn.execute(
                """
                INSERT INTO script_unique_keys (user_id, format, kind, key, script_id)
                VALUES (?, ?, ?, ?, 0)
                """,
                (user_id, format, kind, key),
            )
        except sqlite3.IntegrityError as exc:
            raise DuplicateScriptError(kind) from exc


def attach_script_unique_keys(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    format: str,
    keys: list[tuple[str, str]],
    script_id: int,
) -> None:
    for kind, key in keys:
        conn.execute(
            """
            UPDATE script_unique_keys
            SET script_id = ?
            WHERE user_id = ? AND format = ? AND kind = ? AND key = ?
            """,
            (script_id, user_id, format, kind, key),
        )
