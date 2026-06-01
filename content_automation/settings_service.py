from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import Settings
from .prompts import DEFAULT_AUTHOR_STYLE, DEFAULT_CTA_MIX, DEFAULT_OFFER_CONTEXT
from .storage import Storage


TEXT_SETTING_KEYS = {"offer_context", "author_style", "cta_mix", "notebook_id"}
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
    elevenlabs_voice_id: str | None
    elevenlabs_voice_name: str
    overlays: list[OverlayState]


def get_user_settings(storage: Storage, settings: Settings, user_id: str) -> UserSettingsState:
    return UserSettingsState(
        notebook_id=get_notebook_ref(storage, settings, user_id),
        author_style=storage.get_setting(user_id, "author_style") or DEFAULT_AUTHOR_STYLE.strip(),
        offer_context=storage.get_setting(user_id, "offer_context") or DEFAULT_OFFER_CONTEXT.strip(),
        cta_mix=storage.get_setting(user_id, "cta_mix") or DEFAULT_CTA_MIX,
        heygen_avatar_id=storage.get_setting(user_id, "heygen_avatar_id"),
        heygen_avatar_name=storage.get_setting(user_id, "heygen_avatar_name"),
        elevenlabs_voice_id=storage.get_setting(user_id, "elevenlabs_voice_id") or settings.elevenlabs_voice_id,
        elevenlabs_voice_name=storage.get_setting(user_id, "elevenlabs_voice_name") or settings.elevenlabs_voice_name,
        overlays=[get_overlay_state(storage, user_id, item) for item in ("short", "youtube")],
    )


def get_notebook_ref(storage: Storage, settings: Settings, user_id: str) -> str | None:
    return storage.get_setting(user_id, "notebook_id") or settings.default_notebook_id


def set_text_setting(storage: Storage, user_id: str, key: str, value: str) -> None:
    if key not in TEXT_SETTING_KEYS:
        raise ValueError("Unknown setting")
    storage.set_setting(user_id, key, value.strip())


def set_active_heygen_avatar(storage: Storage, user_id: str, avatar_id: str, avatar_name: str) -> None:
    storage.set_setting(user_id, "heygen_avatar_id", avatar_id)
    storage.set_setting(user_id, "heygen_avatar_name", avatar_name)


def set_active_elevenlabs_voice(storage: Storage, user_id: str, voice_id: str, voice_name: str) -> None:
    storage.set_setting(user_id, "elevenlabs_voice_id", voice_id)
    storage.set_setting(user_id, "elevenlabs_voice_name", voice_name)


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
    value = storage.get_setting(user_id, f"{format}_overlay_start_percent")
    if not value:
        return 70
    try:
        return max(0, min(100, int(value)))
    except ValueError:
        return 70


def overlay_directory(settings: Settings, user_id: str) -> Path:
    path = settings.data_dir / "overlays" / user_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def format_label(format: str) -> str:
    return "YouTube" if format == "youtube" else "Shorts"


def validate_overlay_format(format: str) -> None:
    if format not in OVERLAY_FORMATS:
        raise ValueError("Unknown overlay format")
