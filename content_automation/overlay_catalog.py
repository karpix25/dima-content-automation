from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .storage import Storage


def add_overlay_path(storage: Storage, user_id: str, format: str, path: Path) -> list[Path]:
    paths = [item for item in list_overlay_paths(storage, user_id, format) if item != path]
    paths.append(path)
    storage.set_setting(user_id, _paths_key(format), json.dumps([str(item) for item in paths], ensure_ascii=False))
    storage.set_setting(user_id, _legacy_path_key(format), str(path))
    return paths


def list_overlay_paths(storage: Storage, user_id: str, format: str) -> list[Path]:
    values: list[str] = []
    raw = storage.get_setting(user_id, _paths_key(format))
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                values.extend(str(item) for item in parsed if str(item).strip())
        except json.JSONDecodeError:
            pass
    legacy = storage.get_setting(user_id, _legacy_path_key(format))
    if not legacy and format in {"shorts", "reels"}:
        legacy = storage.get_setting(user_id, "short_overlay_path")
    if legacy:
        values.append(legacy)
    paths: list[Path] = []
    seen: set[str] = set()
    for value in values:
        path = Path(value)
        key = str(path)
        if key not in seen and path.exists():
            paths.append(path)
            seen.add(key)
    return paths


def select_overlay_path(storage: Storage, user_id: str, format: str, *, seed: str | int | None = None) -> Path | None:
    paths = list_overlay_paths(storage, user_id, format)
    if not paths:
        return None
    if seed is None:
        return paths[0]
    digest = hashlib.sha256(f"{user_id}:{format}:{seed}".encode("utf-8")).hexdigest()
    return paths[int(digest[:8], 16) % len(paths)]


def clear_overlay_paths(storage: Storage, user_id: str, format: str) -> list[Path]:
    paths = list_overlay_paths(storage, user_id, format)
    for path in paths:
        if path.exists():
            path.unlink()
    storage.set_setting(user_id, _paths_key(format), "[]")
    storage.set_setting(user_id, _legacy_path_key(format), "")
    return []


def remove_overlay_path(storage: Storage, user_id: str, format: str, index: int) -> list[Path]:
    paths = list_overlay_paths(storage, user_id, format)
    if index < 0 or index >= len(paths):
        raise IndexError("Overlay file not found")
    removed = paths.pop(index)
    if removed.exists():
        removed.unlink()
    storage.set_setting(user_id, _paths_key(format), json.dumps([str(item) for item in paths], ensure_ascii=False))
    storage.set_setting(user_id, _legacy_path_key(format), str(paths[-1]) if paths else "")
    return paths


def _paths_key(format: str) -> str:
    return f"{format}_overlay_paths"


def _legacy_path_key(format: str) -> str:
    return f"{format}_overlay_path"
