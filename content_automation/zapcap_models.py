from __future__ import annotations

from dataclasses import dataclass


ZAPCAP_POSTPROCESS_OFF = "off"
ZAPCAP_POSTPROCESS_ZAPCAP = "zapcap"
ZAPCAP_POSTPROCESS_HYPERFRAMES = "hyperframes"
ZAPCAP_POSTPROCESS_VALUES = {
    ZAPCAP_POSTPROCESS_OFF,
    ZAPCAP_POSTPROCESS_ZAPCAP,
    ZAPCAP_POSTPROCESS_HYPERFRAMES,
}

ZAPCAP_OUTPUT_MODES = {"composited", "greenScreen", "transparent"}
ZAPCAP_QUALITIES = {"standard", "quadHD", "ultraHD"}


@dataclass(frozen=True)
class ZapCapUserSettings:
    postprocess_provider: str
    subtitles_enabled: bool
    template_id: str
    language: str
    emoji: bool
    emoji_animation: bool
    emphasize_keywords: bool
    animation: bool
    punctuation: bool
    display_words: int
    font_uppercase: bool
    font_size: int
    font_color: str
    stroke: int
    stroke_color: str
    top: int
    highlight_color: str
    broll_percent: int


@dataclass(frozen=True)
class ZapCapRuntimeSettings:
    api_key: str | None
    api_base_url: str
    enabled: bool
    poll_seconds: int
    timeout_seconds: int
    request_timeout_seconds: int
    ttl: str | None
    output_mode: str
    quality: str
    export_speed: str


def default_zapcap_user_settings() -> ZapCapUserSettings:
    return ZapCapUserSettings(
        postprocess_provider=ZAPCAP_POSTPROCESS_HYPERFRAMES,
        subtitles_enabled=True,
        template_id="",
        language="auto",
        emoji=True,
        emoji_animation=True,
        emphasize_keywords=True,
        animation=True,
        punctuation=True,
        display_words=3,
        font_uppercase=False,
        font_size=70,
        font_color="#FFFFFF",
        stroke=8,
        stroke_color="#000000",
        top=62,
        highlight_color="#FFE45C",
        broll_percent=0,
    )


def normalize_zapcap_settings(values: dict[str, str | None]) -> ZapCapUserSettings:
    defaults = default_zapcap_user_settings()
    return ZapCapUserSettings(
        postprocess_provider=normalize_postprocess_provider(values.get("postprocess_provider"), defaults.postprocess_provider),
        subtitles_enabled=normalize_bool(values.get("zapcap_subtitles_enabled"), defaults.subtitles_enabled),
        template_id=(values.get("zapcap_template_id") or defaults.template_id).strip(),
        language=normalize_language(values.get("zapcap_language") or defaults.language),
        emoji=normalize_bool(values.get("zapcap_emoji"), defaults.emoji),
        emoji_animation=normalize_bool(values.get("zapcap_emoji_animation"), defaults.emoji_animation),
        emphasize_keywords=normalize_bool(values.get("zapcap_emphasize_keywords"), defaults.emphasize_keywords),
        animation=normalize_bool(values.get("zapcap_animation"), defaults.animation),
        punctuation=normalize_bool(values.get("zapcap_punctuation"), defaults.punctuation),
        display_words=normalize_int(values.get("zapcap_display_words"), minimum=1, maximum=8, default=defaults.display_words),
        font_uppercase=normalize_bool(values.get("zapcap_font_uppercase"), defaults.font_uppercase),
        font_size=normalize_int(values.get("zapcap_font_size"), minimum=24, maximum=70, default=defaults.font_size),
        font_color=normalize_color(values.get("zapcap_font_color"), defaults.font_color),
        stroke=normalize_int(values.get("zapcap_stroke"), minimum=0, maximum=24, default=defaults.stroke),
        stroke_color=normalize_color(values.get("zapcap_stroke_color"), defaults.stroke_color),
        top=normalize_int(values.get("zapcap_top"), minimum=0, maximum=100, default=defaults.top),
        highlight_color=normalize_color(values.get("zapcap_highlight_color"), defaults.highlight_color),
        broll_percent=normalize_int(values.get("zapcap_broll_percent"), minimum=0, maximum=100, default=defaults.broll_percent),
    )


def normalize_zapcap_setting_value(key: str, value: str) -> str:
    if key == "postprocess_provider":
        return normalize_postprocess_provider(value, default_zapcap_user_settings().postprocess_provider)
    if key == "zapcap_language":
        return normalize_language(value)
    if key in {
        "zapcap_subtitles_enabled",
        "zapcap_emoji",
        "zapcap_emoji_animation",
        "zapcap_emphasize_keywords",
        "zapcap_animation",
        "zapcap_punctuation",
        "zapcap_font_uppercase",
    }:
        return "1" if normalize_bool(value, True) else "0"
    if key == "zapcap_display_words":
        return str(normalize_int(value, minimum=1, maximum=8, default=3))
    if key == "zapcap_font_size":
        return str(normalize_int(value, minimum=24, maximum=70, default=70))
    if key == "zapcap_stroke":
        return str(normalize_int(value, minimum=0, maximum=24, default=8))
    if key == "zapcap_top":
        return str(normalize_int(value, minimum=0, maximum=100, default=62))
    if key == "zapcap_broll_percent":
        return str(normalize_int(value, minimum=0, maximum=100, default=0))
    if key in {"zapcap_font_color", "zapcap_stroke_color", "zapcap_highlight_color"}:
        return normalize_color(value, "#FFFFFF")
    if key == "zapcap_template_id":
        return value.strip()[:120]
    raise ValueError("Unknown ZapCap setting")


def normalize_postprocess_provider(value: str | None, fallback: str = ZAPCAP_POSTPROCESS_HYPERFRAMES) -> str:
    normalized = (value or fallback).strip().lower()
    return normalized if normalized in ZAPCAP_POSTPROCESS_VALUES else fallback


def normalize_language(value: str | None) -> str:
    normalized = (value or "auto").strip().lower()
    if normalized in {"", "auto"}:
        return "auto"
    return normalized[:12]


def normalize_bool(value: str | bool | None, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    normalized = (value or "").strip().lower()
    if not normalized:
        return default
    return normalized in {"1", "true", "yes", "y", "on", "вкл"}


def normalize_int(value: str | int | None, *, minimum: int, maximum: int, default: int) -> int:
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def normalize_color(value: str | None, default: str) -> str:
    normalized = (value or default).strip()
    if len(normalized) == 7 and normalized.startswith("#"):
        hex_part = normalized[1:]
        if all(char in "0123456789abcdefABCDEF" for char in hex_part):
            return f"#{hex_part.upper()}"
    return default
