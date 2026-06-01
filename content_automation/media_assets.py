from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import Settings


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".m4v"}
AUDIO_EXTENSIONS = {".mp3", ".m4a", ".aac", ".wav", ".ogg", ".opus", ".flac", ".mp4", ".mov", ".m4v"}
REFERENCE_TARGETS = {"horizontal", "vertical", "both"}


@dataclass(frozen=True)
class MediaAsset:
    id: int
    user_id: str
    kind: str
    file_path: str
    file_name: str
    target: str
    meta: dict[str, Any]
    created_at: str


class MediaAssetStore:
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
                CREATE TABLE IF NOT EXISTS media_assets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    target TEXT NOT NULL DEFAULT 'both',
                    meta_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_media_assets_user_kind ON media_assets(user_id, kind)")

    def add_asset(
        self,
        user_id: str,
        *,
        kind: str,
        file_path: Path,
        file_name: str,
        target: str = "both",
        meta: dict[str, Any] | None = None,
    ) -> MediaAsset:
        normalized_target = normalize_reference_target(target)
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO media_assets (user_id, kind, file_path, file_name, target, meta_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, kind, str(file_path), file_name, normalized_target, json.dumps(meta or {}, ensure_ascii=False)),
            )
            asset_id = int(cursor.lastrowid)
        asset = self.get_asset(user_id, asset_id)
        if not asset:
            raise RuntimeError("failed to load inserted media asset")
        return asset

    def get_asset(self, user_id: str, asset_id: int) -> MediaAsset | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM media_assets WHERE user_id = ? AND id = ?",
                (user_id, asset_id),
            ).fetchone()
        return row_to_asset(row) if row else None

    def list_assets(self, user_id: str, kind: str, *, limit: int = 200) -> list[MediaAsset]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM media_assets
                WHERE user_id = ? AND kind = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (user_id, kind, limit),
            ).fetchall()
        return [row_to_asset(row) for row in rows]

    def update_target(self, user_id: str, asset_id: int, target: str) -> MediaAsset:
        normalized_target = normalize_reference_target(target)
        with self._connect() as conn:
            conn.execute(
                "UPDATE media_assets SET target = ? WHERE user_id = ? AND id = ?",
                (normalized_target, user_id, asset_id),
            )
        asset = self.get_asset(user_id, asset_id)
        if not asset:
            raise ValueError("Asset not found")
        return asset

    def delete_asset(self, user_id: str, asset_id: int) -> MediaAsset:
        asset = self.get_asset(user_id, asset_id)
        if not asset:
            raise ValueError("Asset not found")
        with self._connect() as conn:
            conn.execute("DELETE FROM media_assets WHERE user_id = ? AND id = ?", (user_id, asset_id))
        return asset


def save_uploaded_asset(
    store: MediaAssetStore,
    settings: Settings,
    user_id: str,
    *,
    kind: str,
    filename: str,
    content: bytes,
    allowed_extensions: set[str],
    target: str = "both",
    meta: dict[str, Any] | None = None,
) -> MediaAsset:
    if not content:
        raise ValueError("Empty file")
    safe_name = safe_upload_name(filename, fallback_extension=next(iter(allowed_extensions)))
    suffix = Path(safe_name).suffix.lower()
    if suffix not in allowed_extensions:
        raise ValueError("Unsupported file type")
    directory = asset_directory(settings, kind, user_id)
    unique_name = f"{kind}_{uuid.uuid4().hex[:10]}_{safe_name}"
    path = directory / unique_name
    path.write_bytes(content)
    return store.add_asset(user_id, kind=kind, file_path=path, file_name=safe_name, target=target, meta=meta)


def delete_asset_file(asset: MediaAsset) -> None:
    path = Path(asset.file_path)
    if path.exists():
        path.unlink()


def asset_directory(settings: Settings, kind: str, user_id: str) -> Path:
    path = settings.data_dir / "media" / kind / user_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def normalize_reference_target(target: str | None) -> str:
    normalized = (target or "both").strip().lower()
    if normalized in {"youtube", "landscape", "horizontal"}:
        normalized = "horizontal"
    elif normalized in {"shorts", "reels", "portrait", "vertical", "9:16"}:
        normalized = "vertical"
    if normalized not in REFERENCE_TARGETS:
        raise ValueError("Unsupported target")
    return normalized


def safe_upload_name(filename: str | None, *, fallback_extension: str) -> str:
    raw_name = Path(filename or f"asset{fallback_extension}").name
    stem = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in Path(raw_name).stem).strip("_")
    suffix = Path(raw_name).suffix.lower() or fallback_extension
    return f"{stem or 'asset'}{suffix}"


def row_to_asset(row: sqlite3.Row) -> MediaAsset:
    return MediaAsset(
        id=int(row["id"]),
        user_id=str(row["user_id"]),
        kind=str(row["kind"]),
        file_path=str(row["file_path"]),
        file_name=str(row["file_name"]),
        target=str(row["target"]),
        meta=json.loads(row["meta_json"] or "{}"),
        created_at=str(row["created_at"]),
    )
