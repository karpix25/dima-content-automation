from __future__ import annotations

from pathlib import Path

from .config import Settings
from .storage import Storage


def delivery_face_reference_paths(
    *,
    storage: Storage,
    settings: Settings,
    user_id: str,
    target: str,
    delivery_actor_user_id: str | None = None,
) -> list[Path]:
    project_paths = _face_reference_paths(storage=storage, user_id=user_id, target=target)
    if project_paths or not delivery_actor_user_id or delivery_actor_user_id == user_id:
        return project_paths
    return _face_reference_paths(storage=storage, user_id=delivery_actor_user_id, target=target)


def _face_reference_paths(*, storage: Storage, user_id: str, target: str) -> list[Path]:
    key = "thumbnail_face_path" if target == "horizontal" else "vertical_thumbnail_face_path"
    value = storage.get_setting(user_id, key)
    if not value:
        return []
    path = Path(value)
    return [path] if path.exists() else []
