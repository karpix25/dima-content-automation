from __future__ import annotations

from dataclasses import dataclass


VIZARD_LENGTH_OPTIONS = {
    0: "auto",
    1: "less than 30s",
    2: "30s to 60s",
    3: "60s to 90s",
    4: "90s to 3min",
}
VIZARD_RATIO_OPTIONS = {
    1: "9:16 vertical",
    2: "1:1 square",
    3: "4:5 portrait",
    4: "16:9 horizontal",
}


@dataclass(frozen=True)
class VizardUserSettings:
    lang: str
    ratio_of_clip: int
    prefer_length: list[int]
    max_clip_number: int | None
    keywords: str
    subtitle_switch: bool
    headline_switch: bool
    emoji_switch: bool
    highlight_switch: bool
    auto_broll_switch: bool
    remove_silence_switch: bool
    template_id: int | None


@dataclass(frozen=True)
class VizardClip:
    video_id: str
    video_url: str
    duration_ms: int | None
    title: str
    transcript: str
    viral_score: str
    viral_reason: str
    clip_editor_url: str


@dataclass(frozen=True)
class VizardProjectResult:
    project_id: str
    project_name: str
    share_link: str | None
    clips: list[VizardClip]


def default_vizard_settings() -> VizardUserSettings:
    return VizardUserSettings(
        lang="en",
        ratio_of_clip=1,
        prefer_length=[0],
        max_clip_number=10,
        keywords="",
        subtitle_switch=False,
        headline_switch=False,
        emoji_switch=False,
        highlight_switch=False,
        auto_broll_switch=False,
        remove_silence_switch=False,
        template_id=None,
    )


def normalize_vizard_settings(values: dict[str, str | None]) -> VizardUserSettings:
    defaults = default_vizard_settings()
    return VizardUserSettings(
        lang=normalize_lang(values.get("vizard_lang") or defaults.lang),
        ratio_of_clip=normalize_int_choice(values.get("vizard_ratio_of_clip"), VIZARD_RATIO_OPTIONS, defaults.ratio_of_clip),
        prefer_length=normalize_prefer_length(values.get("vizard_prefer_length")),
        max_clip_number=normalize_optional_int(values.get("vizard_max_clip_number"), minimum=1, maximum=100, default=defaults.max_clip_number),
        keywords=(values.get("vizard_keywords") or defaults.keywords).strip(),
        subtitle_switch=normalize_bool(values.get("vizard_subtitle_switch"), defaults.subtitle_switch),
        headline_switch=normalize_bool(values.get("vizard_headline_switch"), defaults.headline_switch),
        emoji_switch=normalize_bool(values.get("vizard_emoji_switch"), defaults.emoji_switch),
        highlight_switch=normalize_bool(values.get("vizard_highlight_switch"), defaults.highlight_switch),
        auto_broll_switch=normalize_bool(values.get("vizard_auto_broll_switch"), defaults.auto_broll_switch),
        remove_silence_switch=normalize_bool(values.get("vizard_remove_silence_switch"), defaults.remove_silence_switch),
        template_id=normalize_optional_int(values.get("vizard_template_id"), minimum=1, maximum=999999999, default=defaults.template_id),
    )


def vizard_settings_to_payload(settings: VizardUserSettings, *, video_url: str, project_name: str | None = None) -> dict[str, object]:
    payload: dict[str, object] = {
        "lang": settings.lang,
        "preferLength": settings.prefer_length,
        "videoUrl": video_url,
        "videoType": 2,
        "ratioOfClip": settings.ratio_of_clip,
        "subtitleSwitch": int(settings.subtitle_switch),
        "headlineSwitch": int(settings.headline_switch),
        "emojiSwitch": int(settings.emoji_switch),
        "highlightSwitch": int(settings.highlight_switch),
        "autoBrollSwitch": int(settings.auto_broll_switch),
        "removeSilenceSwitch": int(settings.remove_silence_switch),
    }
    if settings.max_clip_number:
        payload["maxClipNumber"] = settings.max_clip_number
    if settings.keywords:
        payload["keywords"] = settings.keywords
    if settings.template_id:
        payload["templateId"] = settings.template_id
    if project_name:
        payload["projectName"] = project_name
    return payload


def normalize_vizard_setting_value(key: str, value: str) -> str:
    normalized = value.strip()
    if key == "vizard_lang":
        return normalize_lang(normalized)
    if key == "vizard_ratio_of_clip":
        return str(normalize_int_choice(normalized, VIZARD_RATIO_OPTIONS, 1))
    if key == "vizard_prefer_length":
        return ",".join(str(item) for item in normalize_prefer_length(normalized))
    if key == "vizard_max_clip_number":
        parsed = normalize_optional_int(normalized, minimum=1, maximum=100, default=10)
        return "" if parsed is None else str(parsed)
    if key == "vizard_template_id":
        parsed = normalize_optional_int(normalized, minimum=1, maximum=999999999, default=None)
        return "" if parsed is None else str(parsed)
    if key in {
        "vizard_subtitle_switch",
        "vizard_headline_switch",
        "vizard_emoji_switch",
        "vizard_highlight_switch",
        "vizard_auto_broll_switch",
        "vizard_remove_silence_switch",
    }:
        return "1" if normalize_bool(normalized, False) else "0"
    if key == "vizard_keywords":
        return " ".join(normalized.split())[:300]
    raise ValueError("Unknown Vizard setting")


def normalize_prefer_length(value: str | None) -> list[int]:
    if not value:
        return [0]
    items: list[int] = []
    for part in value.replace(";", ",").split(","):
        stripped = part.strip()
        if not stripped:
            continue
        parsed = parse_int(stripped, 0)
        if parsed in VIZARD_LENGTH_OPTIONS and parsed not in items:
            items.append(parsed)
    return items or [0]


def normalize_bool(value: str | None, default: bool) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def normalize_lang(value: str) -> str:
    normalized = "".join(ch for ch in (value or "en").strip().lower() if ch.isalpha() or ch == "-")
    return normalized[:12] or "en"


def normalize_int_choice(value: str | None, choices: dict[int, str], default: int) -> int:
    parsed = parse_int(value or "", default)
    return parsed if parsed in choices else default


def normalize_optional_int(value: str | None, *, minimum: int, maximum: int, default: int | None) -> int | None:
    if value is None or not str(value).strip():
        return default
    parsed = parse_int(str(value), default or minimum)
    return max(minimum, min(maximum, parsed))


def parse_int(value: str, default: int) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default
