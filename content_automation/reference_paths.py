from __future__ import annotations

from pathlib import Path

from .config import Settings
from .media_assets import MediaAssetStore
from .settings_service import get_user_settings
from .storage import Storage


def thumbnail_reference_paths(
    *,
    storage: Storage,
    asset_store: MediaAssetStore,
    settings: Settings,
    user_id: str,
    target: str,
) -> list[Path]:
    normalized_target = "horizontal" if target == "horizontal" else "vertical"
    state = get_user_settings(storage, settings, user_id)
    face_path = state.thumbnail_face_path if normalized_target == "horizontal" else state.vertical_thumbnail_face_path
    paths = [_existing_path(face_path)]
    paths.extend(
        _existing_path(item.file_path)
        for item in asset_store.list_assets(user_id, "thumbnail_reference")
        if item.target in {normalized_target, "both"}
    )
    return [path for path in paths if path is not None][:16]


def thumbnail_style_reference_paths(
    *,
    asset_store: MediaAssetStore,
    user_id: str,
    target: str,
) -> list[Path]:
    normalized_target = "horizontal" if target == "horizontal" else "vertical"
    return [
        path
        for item in asset_store.list_assets(user_id, "thumbnail_reference")
        if item.target in {normalized_target, "both"}
        if (path := _existing_path(item.file_path)) is not None
    ][:15]


def thumbnail_face_reference_paths(
    *,
    storage: Storage,
    settings: Settings,
    user_id: str,
    target: str,
) -> list[Path]:
    normalized_target = "horizontal" if target == "horizontal" else "vertical"
    state = get_user_settings(storage, settings, user_id)
    face_path = state.thumbnail_face_path if normalized_target == "horizontal" else state.vertical_thumbnail_face_path
    path = _existing_path(face_path)
    return [path] if path else []


def infographic_design_reference_paths(*, asset_store: MediaAssetStore, user_id: str) -> list[Path]:
    return [
        path
        for item in asset_store.list_assets(user_id, "instagram_post_5s_reference")
        if (path := _existing_path(item.file_path)) is not None
    ][:8]


def target_from_record_format(format_name: str) -> str:
    return "horizontal" if format_name == "youtube" else "vertical"


def _existing_path(value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path if path.exists() else None
