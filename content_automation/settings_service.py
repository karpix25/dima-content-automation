from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import Settings
from .prompts import DEFAULT_AUTHOR_STYLE, DEFAULT_CTA_MIX, DEFAULT_OFFER_CONTEXT
from .storage import Storage


TEXT_SETTING_KEYS = {
    "offer_context",
    "author_style",
    "cta_mix",
    "notebook_id",
    "youtube_description_template",
    "instagram_post_5s_cta_text",
    "avatar_insert_start_percent",
    "avatar_insert_end_percent",
    "avatar_insert_clips_count",
}
OVERLAY_FORMATS = {"short", "youtube"}


@dataclass(frozen=True)
class OverlayState:
    format: str
    label: str
    has_file: bool
    file_name: str | None
    start_percent: int


@dataclass(frozen=True)
class UserSettingsState:
    notebook_id: str | None
    author_style: str
    offer_context: str
    cta_mix: str
    heygen_avatar_id: str | None
    heygen_avatar_name: str | None
    heygen_vertical_avatar_id: str | None
    heygen_vertical_avatar_name: str | None
    heygen_video_api_version: str
    heygen_avatar_engine: str
    elevenlabs_voice_id: str | None
    elevenlabs_voice_name: str
    thumbnail_face_path: str | None
    vertical_thumbnail_face_path: str | None
    youtube_description_template: str
    avatar_insert_start_percent: int
    avatar_insert_end_percent: int
    avatar_insert_clips_count: int
    instagram_post_5s_cta_text: str
    instagram_post_5s_overlay_path: str | None
    overlays: list[OverlayState]


def get_user_settings(storage: Storage, settings: Settings, user_id: str) -> UserSettingsState:
    return UserSettingsState(
        notebook_id=get_notebook_ref(storage, settings, user_id),
        author_style=storage.get_setting(user_id, "author_style") or DEFAULT_AUTHOR_STYLE.strip(),
        offer_context=storage.get_setting(user_id, "offer_context") or DEFAULT_OFFER_CONTEXT.strip(),
        cta_mix=storage.get_setting(user_id, "cta_mix") or DEFAULT_CTA_MIX,
        heygen_avatar_id=storage.get_setting(user_id, "heygen_avatar_id"),
        heygen_avatar_name=storage.get_setting(user_id, "heygen_avatar_name"),
        heygen_vertical_avatar_id=storage.get_setting(user_id, "heygen_vertical_avatar_id") or storage.get_setting(user_id, "heygen_avatar_id"),
        heygen_vertical_avatar_name=storage.get_setting(user_id, "heygen_vertical_avatar_name") or storage.get_setting(user_id, "heygen_avatar_name"),
        heygen_video_api_version=get_heygen_video_api_version(storage, user_id),
        heygen_avatar_engine=get_heygen_avatar_engine(storage, user_id),
        elevenlabs_voice_id=storage.get_setting(user_id, "elevenlabs_voice_id") or settings.elevenlabs_voice_id,
        elevenlabs_voice_name=storage.get_setting(user_id, "elevenlabs_voice_name") or settings.elevenlabs_voice_name,
        thumbnail_face_path=storage.get_setting(user_id, "thumbnail_face_path"),
        vertical_thumbnail_face_path=storage.get_setting(user_id, "vertical_thumbnail_face_path"),
        youtube_description_template=storage.get_setting(user_id, "youtube_description_template") or "",
        avatar_insert_start_percent=get_percent_setting(storage, user_id, "avatar_insert_start_percent", default=50, minimum=0, maximum=99),
        avatar_insert_end_percent=get_percent_setting(storage, user_id, "avatar_insert_end_percent", default=95, minimum=1, maximum=100),
        avatar_insert_clips_count=get_int_setting(storage, user_id, "avatar_insert_clips_count", default=2, minimum=0, maximum=20),
        instagram_post_5s_cta_text=storage.get_setting(user_id, "instagram_post_5s_cta_text") or "",
        instagram_post_5s_overlay_path=storage.get_setting(user_id, "instagram_post_5s_overlay_path"),
        overlays=[get_overlay_state(storage, user_id, item) for item in ("short", "youtube")],
    )


def get_notebook_ref(storage: Storage, settings: Settings, user_id: str) -> str | None:
    return storage.get_setting(user_id, "notebook_id") or settings.default_notebook_id


def set_text_setting(storage: Storage, user_id: str, key: str, value: str) -> None:
    if key not in TEXT_SETTING_KEYS:
        raise ValueError("Unknown setting")
    normalized = normalize_text_setting(key, value)
    storage.set_setting(user_id, key, normalized)


def set_active_heygen_avatar(storage: Storage, user_id: str, avatar_id: str, avatar_name: str, target: str = "both") -> None:
    normalized = (target or "both").strip().lower()
    if normalized in {"youtube", "horizontal", "landscape"}:
        storage.set_setting(user_id, "heygen_avatar_id", avatar_id)
        storage.set_setting(user_id, "heygen_avatar_name", avatar_name)
    elif normalized in {"shorts", "reels", "vertical", "portrait", "9:16"}:
        storage.set_setting(user_id, "heygen_vertical_avatar_id", avatar_id)
        storage.set_setting(user_id, "heygen_vertical_avatar_name", avatar_name)
    elif normalized == "both":
        storage.set_setting(user_id, "heygen_avatar_id", avatar_id)
        storage.set_setting(user_id, "heygen_avatar_name", avatar_name)
        storage.set_setting(user_id, "heygen_vertical_avatar_id", avatar_id)
        storage.set_setting(user_id, "heygen_vertical_avatar_name", avatar_name)
    else:
        raise ValueError("Unsupported avatar target")


def set_heygen_generation_model(storage: Storage, user_id: str, model: str) -> None:
    normalized = (model or "avatar_iii").strip().lower()
    if normalized == "avatar_iii":
        storage.set_setting(user_id, "heygen_video_api_version", "v2")
        storage.set_setting(user_id, "heygen_avatar_engine", "avatar_iv")
    elif normalized in {"avatar_iv", "avatar_v"}:
        storage.set_setting(user_id, "heygen_video_api_version", "v3")
        storage.set_setting(user_id, "heygen_avatar_engine", normalized)
    else:
        raise ValueError("Unsupported HeyGen model")


def get_heygen_video_api_version(storage: Storage, user_id: str) -> str:
    value = (storage.get_setting(user_id, "heygen_video_api_version") or "v2").strip().lower()
    return value if value in {"v2", "v3"} else "v2"


def get_heygen_avatar_engine(storage: Storage, user_id: str) -> str:
    value = (storage.get_setting(user_id, "heygen_avatar_engine") or "avatar_iv").strip().lower()
    return value if value in {"avatar_iv", "avatar_v"} else "avatar_iv"


def set_active_elevenlabs_voice(storage: Storage, user_id: str, voice_id: str, voice_name: str) -> None:
    storage.set_setting(user_id, "elevenlabs_voice_id", voice_id)
    storage.set_setting(user_id, "elevenlabs_voice_name", voice_name)


def set_active_thumbnail_face(storage: Storage, user_id: str, file_path: str | None, target: str) -> None:
    normalized = (target or "both").strip().lower()
    if normalized in {"youtube", "horizontal", "landscape"}:
        storage.set_setting(user_id, "thumbnail_face_path", file_path or "")
    elif normalized in {"shorts", "reels", "vertical", "portrait", "9:16"}:
        storage.set_setting(user_id, "vertical_thumbnail_face_path", file_path or "")
    elif normalized == "both":
        storage.set_setting(user_id, "thumbnail_face_path", file_path or "")
        storage.set_setting(user_id, "vertical_thumbnail_face_path", file_path or "")
    else:
        raise ValueError("Unsupported face target")


def set_instagram_post_5s_overlay(storage: Storage, user_id: str, file_path: str | None) -> None:
    storage.set_setting(user_id, "instagram_post_5s_overlay_path", file_path or "")


def normalize_text_setting(key: str, value: str) -> str:
    stripped = value.strip()
    if key == "instagram_post_5s_cta_text":
        return " ".join(stripped.split())[:180]
    if key == "avatar_insert_start_percent":
        return str(max(0, min(99, parse_int(stripped, 50))))
    if key == "avatar_insert_end_percent":
        return str(max(1, min(100, parse_int(stripped, 95))))
    if key == "avatar_insert_clips_count":
        return str(max(0, min(20, parse_int(stripped, 2))))
    return stripped


def get_overlay_state(storage: Storage, user_id: str, format: str) -> OverlayState:
    path = get_overlay_path(storage, user_id, format)
    exists = bool(path and path.exists())
    return OverlayState(
        format=format,
        label=format_label(format),
        has_file=exists,
        file_name=path.name if exists and path else None,
        start_percent=get_overlay_start_percent(storage, user_id, format),
    )


def get_overlay_path(storage: Storage, user_id: str, format: str) -> Path | None:
    validate_overlay_format(format)
    value = storage.get_setting(user_id, f"{format}_overlay_path")
    return Path(value) if value else None


def save_overlay_file(storage: Storage, settings: Settings, user_id: str, format: str, file_name: str, content: bytes) -> OverlayState:
    validate_overlay_format(format)
    suffix = Path(file_name or "").suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
        suffix = ".png"
    directory = overlay_directory(settings, user_id)
    path = directory / f"{format}_overlay{suffix}"
    path.write_bytes(content)
    storage.set_setting(user_id, f"{format}_overlay_path", str(path))
    return get_overlay_state(storage, user_id, format)


def delete_overlay_file(storage: Storage, user_id: str, format: str) -> OverlayState:
    path = get_overlay_path(storage, user_id, format)
    if path and path.exists():
        path.unlink()
    storage.set_setting(user_id, f"{format}_overlay_path", "")
    return get_overlay_state(storage, user_id, format)


def set_overlay_start_percent(storage: Storage, user_id: str, format: str, value: int) -> OverlayState:
    validate_overlay_format(format)
    percent = max(0, min(100, int(value)))
    storage.set_setting(user_id, f"{format}_overlay_start_percent", str(percent))
    return get_overlay_state(storage, user_id, format)


def get_overlay_start_percent(storage: Storage, user_id: str, format: str) -> int:
    validate_overlay_format(format)
    return get_percent_setting(storage, user_id, f"{format}_overlay_start_percent", default=70, minimum=0, maximum=100)


def get_percent_setting(storage: Storage, user_id: str, key: str, *, default: int, minimum: int, maximum: int) -> int:
    value = storage.get_setting(user_id, key)
    if not value:
        return default
    return max(minimum, min(maximum, parse_int(value, default)))


def get_int_setting(storage: Storage, user_id: str, key: str, *, default: int, minimum: int, maximum: int) -> int:
    value = storage.get_setting(user_id, key)
    if not value:
        return default
    return max(minimum, min(maximum, parse_int(value, default)))


def parse_int(value: str, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def overlay_directory(settings: Settings, user_id: str) -> Path:
    path = settings.data_dir / "overlays" / user_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def format_label(format: str) -> str:
    return "YouTube" if format == "youtube" else "Shorts"


def validate_overlay_format(format: str) -> None:
    if format not in OVERLAY_FORMATS:
        raise ValueError("Unknown overlay format")
