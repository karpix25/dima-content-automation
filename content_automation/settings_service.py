from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import Settings
from .overlay_catalog import add_overlay_path, clear_overlay_paths, list_overlay_paths, select_overlay_path
from .prompts import DEFAULT_AUTHOR_STYLE, DEFAULT_CTA_MIX, DEFAULT_OFFER_CONTEXT
from .storage import Storage
from .vizard_models import VizardUserSettings, normalize_vizard_setting_value, normalize_vizard_settings
from .voice_speed_profile import clear_voice_wpm


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
    "youtube_long_duration_minutes",
    "vertical_avatar_duration_mode",
    "vizard_lang",
    "vizard_ratio_of_clip",
    "vizard_prefer_length",
    "vizard_max_clip_number",
    "vizard_keywords",
    "vizard_subtitle_switch",
    "vizard_headline_switch",
    "vizard_emoji_switch",
    "vizard_highlight_switch",
    "vizard_auto_broll_switch",
    "vizard_remove_silence_switch",
    "vizard_template_id",
}
OVERLAY_FORMATS = {"short", "youtube", "instagram", "shorts", "reels"}


@dataclass(frozen=True)
class OverlayState:
    format: str
    label: str
    has_file: bool
    file_name: str | None
    start_percent: int
    file_count: int = 0


@dataclass(frozen=True)
class UserSettingsState:
    notebook_id: str | None
    author_style: str
    offer_context: str
    cta_mix: str
    heygen_avatar_id: str | None
    heygen_avatar_name: str | None
    heygen_avatar_preview_image_url: str | None
    heygen_avatar_preview_video_url: str | None
    heygen_vertical_avatar_id: str | None
    heygen_vertical_avatar_name: str | None
    heygen_vertical_avatar_preview_image_url: str | None
    heygen_vertical_avatar_preview_video_url: str | None
    heygen_video_api_version: str
    heygen_avatar_engine: str
    heygen_model_selected: bool
    elevenlabs_voice_id: str | None
    elevenlabs_voice_name: str
    thumbnail_face_path: str | None
    vertical_thumbnail_face_path: str | None
    youtube_description_template: str
    avatar_insert_start_percent: int
    avatar_insert_end_percent: int
    avatar_insert_clips_count: int
    youtube_long_duration_minutes: int
    vertical_avatar_duration_mode: str
    instagram_post_5s_cta_text: str
    vizard: VizardUserSettings
    overlays: list[OverlayState]


def get_user_settings(storage: Storage, settings: Settings, user_id: str) -> UserSettingsState:
    return UserSettingsState(
        notebook_id=get_notebook_ref(storage, settings, user_id),
        author_style=storage.get_setting(user_id, "author_style") or DEFAULT_AUTHOR_STYLE.strip(),
        offer_context=storage.get_setting(user_id, "offer_context") or DEFAULT_OFFER_CONTEXT.strip(),
        cta_mix=storage.get_setting(user_id, "cta_mix") or DEFAULT_CTA_MIX,
        heygen_avatar_id=storage.get_setting(user_id, "heygen_avatar_id"),
        heygen_avatar_name=storage.get_setting(user_id, "heygen_avatar_name"),
        heygen_avatar_preview_image_url=storage.get_setting(user_id, "heygen_avatar_preview_image_url"),
        heygen_avatar_preview_video_url=storage.get_setting(user_id, "heygen_avatar_preview_video_url"),
        heygen_vertical_avatar_id=storage.get_setting(user_id, "heygen_vertical_avatar_id"),
        heygen_vertical_avatar_name=storage.get_setting(user_id, "heygen_vertical_avatar_name"),
        heygen_vertical_avatar_preview_image_url=storage.get_setting(user_id, "heygen_vertical_avatar_preview_image_url"),
        heygen_vertical_avatar_preview_video_url=storage.get_setting(user_id, "heygen_vertical_avatar_preview_video_url"),
        heygen_video_api_version=get_heygen_video_api_version(storage, user_id),
        heygen_avatar_engine=get_heygen_avatar_engine(storage, user_id),
        heygen_model_selected=bool(storage.get_setting(user_id, "heygen_model_selected")),
        elevenlabs_voice_id=storage.get_setting(user_id, "elevenlabs_voice_id") or settings.elevenlabs_voice_id,
        elevenlabs_voice_name=storage.get_setting(user_id, "elevenlabs_voice_name") or settings.elevenlabs_voice_name,
        thumbnail_face_path=storage.get_setting(user_id, "thumbnail_face_path"),
        vertical_thumbnail_face_path=storage.get_setting(user_id, "vertical_thumbnail_face_path"),
        youtube_description_template=storage.get_setting(user_id, "youtube_description_template") or "",
        avatar_insert_start_percent=get_percent_setting(storage, user_id, "avatar_insert_start_percent", default=50, minimum=0, maximum=99),
        avatar_insert_end_percent=get_percent_setting(storage, user_id, "avatar_insert_end_percent", default=95, minimum=1, maximum=100),
        avatar_insert_clips_count=get_int_setting(storage, user_id, "avatar_insert_clips_count", default=2, minimum=0, maximum=20),
        youtube_long_duration_minutes=get_int_setting(storage, user_id, "youtube_long_duration_minutes", default=10, minimum=3, maximum=30),
        vertical_avatar_duration_mode=get_duration_mode(storage, user_id),
        instagram_post_5s_cta_text=storage.get_setting(user_id, "instagram_post_5s_cta_text") or "",
        vizard=get_vizard_settings(storage, user_id),
        overlays=[get_overlay_state(storage, user_id, item) for item in ("youtube", "shorts", "reels")],
    )


def get_notebook_ref(storage: Storage, settings: Settings, user_id: str) -> str | None:
    return storage.get_setting(user_id, "notebook_id") or settings.default_notebook_id


def set_text_setting(storage: Storage, user_id: str, key: str, value: str) -> None:
    if key not in TEXT_SETTING_KEYS:
        raise ValueError("Unknown setting")
    normalized = normalize_text_setting(key, value)
    storage.set_setting(user_id, key, normalized)


def set_active_heygen_avatar(
    storage: Storage,
    user_id: str,
    avatar_id: str,
    avatar_name: str,
    target: str = "both",
    preview_image_url: str | None = None,
    preview_video_url: str | None = None,
) -> None:
    normalized = (target or "both").strip().lower()
    if normalized in {"youtube", "horizontal", "landscape"}:
        storage.set_setting(user_id, "heygen_avatar_id", avatar_id)
        storage.set_setting(user_id, "heygen_avatar_name", avatar_name)
        storage.set_setting(user_id, "heygen_avatar_preview_image_url", preview_image_url or "")
        storage.set_setting(user_id, "heygen_avatar_preview_video_url", preview_video_url or "")
    elif normalized in {"shorts", "reels", "vertical", "portrait", "9:16"}:
        storage.set_setting(user_id, "heygen_vertical_avatar_id", avatar_id)
        storage.set_setting(user_id, "heygen_vertical_avatar_name", avatar_name)
        storage.set_setting(user_id, "heygen_vertical_avatar_preview_image_url", preview_image_url or "")
        storage.set_setting(user_id, "heygen_vertical_avatar_preview_video_url", preview_video_url or "")
    elif normalized == "both":
        storage.set_setting(user_id, "heygen_avatar_id", avatar_id)
        storage.set_setting(user_id, "heygen_avatar_name", avatar_name)
        storage.set_setting(user_id, "heygen_avatar_preview_image_url", preview_image_url or "")
        storage.set_setting(user_id, "heygen_avatar_preview_video_url", preview_video_url or "")
        storage.set_setting(user_id, "heygen_vertical_avatar_id", avatar_id)
        storage.set_setting(user_id, "heygen_vertical_avatar_name", avatar_name)
        storage.set_setting(user_id, "heygen_vertical_avatar_preview_image_url", preview_image_url or "")
        storage.set_setting(user_id, "heygen_vertical_avatar_preview_video_url", preview_video_url or "")
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
    storage.set_setting(user_id, "heygen_model_selected", "1")


def get_heygen_video_api_version(storage: Storage, user_id: str) -> str:
    value = (storage.get_setting(user_id, "heygen_video_api_version") or "v2").strip().lower()
    return value if value in {"v2", "v3"} else "v2"


def get_heygen_avatar_engine(storage: Storage, user_id: str) -> str:
    value = (storage.get_setting(user_id, "heygen_avatar_engine") or "avatar_iv").strip().lower()
    return value if value in {"avatar_iv", "avatar_v"} else "avatar_iv"


def set_active_elevenlabs_voice(storage: Storage, user_id: str, voice_id: str, voice_name: str) -> None:
    storage.set_setting(user_id, "elevenlabs_voice_id", voice_id)
    storage.set_setting(user_id, "elevenlabs_voice_name", voice_name)
    clear_voice_wpm(storage, user_id)


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
    if key == "youtube_long_duration_minutes":
        return str(max(3, min(30, parse_int(stripped, 10))))
    if key == "vertical_avatar_duration_mode":
        return normalize_duration_mode(stripped)
    if key.startswith("vizard_"):
        return normalize_vizard_setting_value(key, stripped)
    return stripped


def get_vizard_settings(storage: Storage, user_id: str) -> VizardUserSettings:
    keys = (
        "vizard_lang",
        "vizard_ratio_of_clip",
        "vizard_prefer_length",
        "vizard_max_clip_number",
        "vizard_keywords",
        "vizard_subtitle_switch",
        "vizard_headline_switch",
        "vizard_emoji_switch",
        "vizard_highlight_switch",
        "vizard_auto_broll_switch",
        "vizard_remove_silence_switch",
        "vizard_template_id",
    )
    return normalize_vizard_settings({key: storage.get_setting(user_id, key) for key in keys})


def get_duration_mode(storage: Storage, user_id: str) -> str:
    return normalize_duration_mode(storage.get_setting(user_id, "vertical_avatar_duration_mode") or "original")


def normalize_duration_mode(value: str) -> str:
    normalized = (value or "original").strip().lower()
    return normalized if normalized in {"original", "30", "45", "60", "90"} else "original"


def get_overlay_state(storage: Storage, user_id: str, format: str) -> OverlayState:
    paths = get_overlay_paths(storage, user_id, format)
    path = paths[0] if paths else None
    exists = bool(path)
    return OverlayState(
        format=format,
        label=format_label(format),
        has_file=exists,
        file_name=overlay_file_label(paths),
        start_percent=get_overlay_start_percent(storage, user_id, format),
        file_count=len(paths),
    )


def get_overlay_path(storage: Storage, user_id: str, format: str) -> Path | None:
    normalized = normalize_overlay_format(format)
    return select_overlay_path(storage, user_id, normalized)


def get_random_overlay_path(storage: Storage, user_id: str, format: str, *, seed: str | int | None = None) -> Path | None:
    normalized = normalize_overlay_format(format)
    return select_overlay_path(storage, user_id, normalized, seed=seed)


def get_overlay_paths(storage: Storage, user_id: str, format: str) -> list[Path]:
    normalized = normalize_overlay_format(format)
    return list_overlay_paths(storage, user_id, normalized)


def save_overlay_file(storage: Storage, settings: Settings, user_id: str, format: str, file_name: str, content: bytes) -> OverlayState:
    normalized = normalize_overlay_format(format)
    suffix = Path(file_name or "").suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
        suffix = ".png"
    directory = overlay_directory(settings, user_id)
    index = len(get_overlay_paths(storage, user_id, normalized)) + 1
    path = directory / f"{normalized}_overlay_{index}{suffix}"
    while path.exists():
        index += 1
        path = directory / f"{normalized}_overlay_{index}{suffix}"
    path.write_bytes(content)
    add_overlay_path(storage, user_id, normalized, path)
    return get_overlay_state(storage, user_id, normalized)


def delete_overlay_file(storage: Storage, user_id: str, format: str) -> OverlayState:
    normalized = normalize_overlay_format(format)
    clear_overlay_paths(storage, user_id, normalized)
    return get_overlay_state(storage, user_id, normalized)


def set_overlay_start_percent(storage: Storage, user_id: str, format: str, value: int) -> OverlayState:
    normalized = normalize_overlay_format(format)
    percent = max(0, min(100, int(value)))
    storage.set_setting(user_id, f"{normalized}_overlay_start_percent", str(percent))
    return get_overlay_state(storage, user_id, normalized)


def get_overlay_start_percent(storage: Storage, user_id: str, format: str) -> int:
    normalized = normalize_overlay_format(format)
    return get_percent_setting(storage, user_id, f"{normalized}_overlay_start_percent", default=70, minimum=0, maximum=100)


def overlay_file_label(paths: list[Path]) -> str | None:
    if not paths:
        return None
    if len(paths) == 1:
        return paths[0].name
    return f"{len(paths)} файлов, рандомный выбор"


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
    normalized = normalize_overlay_format(format)
    if normalized == "youtube":
        return "YouTube"
    if normalized == "shorts":
        return "Shorts"
    if normalized == "reels":
        return "Reels"
    return "Instagram"


def validate_overlay_format(format: str) -> None:
    if format not in OVERLAY_FORMATS:
        raise ValueError("Unknown overlay format")


def normalize_overlay_format(format: str) -> str:
    validate_overlay_format(format)
    return "shorts" if format in {"short", "instagram"} else format
