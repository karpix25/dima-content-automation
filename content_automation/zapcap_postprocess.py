from __future__ import annotations

import logging
from dataclasses import replace
from pathlib import Path
from typing import Any

from .config import Settings
from .storage import ScriptRecord
from .zapcap_client import ZapCapApiClient, ZapCapApiError
from .zapcap_models import (
    ZAPCAP_POSTPROCESS_ZAPCAP,
    ZapCapRuntimeSettings,
    ZapCapUserSettings,
)


class ZapCapPostprocessError(RuntimeError):
    pass


logger = logging.getLogger(__name__)


def process_video_with_zapcap(
    *,
    record: ScriptRecord,
    video_path: Path,
    output_dir: Path,
    runtime: ZapCapRuntimeSettings,
    user_settings: ZapCapUserSettings,
    client: ZapCapApiClient | None = None,
) -> Path:
    if user_settings.postprocess_provider != ZAPCAP_POSTPROCESS_ZAPCAP or not user_settings.subtitles_enabled:
        return video_path
    if not runtime.enabled:
        raise ZapCapPostprocessError("ZapCap postprocess is disabled by ZAPCAP_ENABLED")
    if not user_settings.template_id:
        raise ZapCapPostprocessError("ZapCap template is not selected")
    zapcap = client or ZapCapApiClient(
        api_key=runtime.api_key,
        base_url=runtime.api_base_url,
        timeout_seconds=runtime.request_timeout_seconds,
    )
    try:
        logger.info("Uploading video to ZapCap: script=%s path=%s", record.id, video_path)
        video = zapcap.upload_video(video_path, ttl=runtime.ttl)
        payload = build_zapcap_task_payload(user_settings=user_settings, runtime=runtime)
        logger.info("Creating ZapCap task: script=%s video=%s template=%s", record.id, video.id, user_settings.template_id)
        task = zapcap.create_task(video.id, payload, ttl=runtime.ttl)
        completed = zapcap.wait_for_task(
            video.id,
            task.id,
            poll_seconds=runtime.poll_seconds,
            timeout_seconds=runtime.timeout_seconds,
        )
        if not completed.download_url:
            raise ZapCapPostprocessError(f"ZapCap completed without download URL: {completed.raw}")
        output_path = output_dir / f"zapcap_{record.id}_{video_path.stem}.mp4"
        logger.info("Downloading ZapCap result: script=%s task=%s url=%s", record.id, completed.id, completed.download_url)
        return zapcap.download(completed.download_url, output_path)
    except ZapCapApiError as exc:
        raise ZapCapPostprocessError(str(exc)) from exc


def should_process_with_zapcap(runtime: ZapCapRuntimeSettings, user_settings: ZapCapUserSettings) -> bool:
    return runtime.enabled and user_settings.postprocess_provider == ZAPCAP_POSTPROCESS_ZAPCAP and user_settings.subtitles_enabled


def build_zapcap_task_payload(*, user_settings: ZapCapUserSettings, runtime: ZapCapRuntimeSettings) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "templateId": user_settings.template_id,
        "autoApprove": True,
        "renderOptions": {
            "subsOptions": {
                "emoji": user_settings.emoji,
                "emojiAnimation": user_settings.emoji_animation,
                "emphasizeKeywords": user_settings.emphasize_keywords,
                "animation": user_settings.animation,
                "punctuation": user_settings.punctuation,
                "displayWords": user_settings.display_words,
            },
            "styleOptions": {
                "top": user_settings.top,
                "fontUppercase": user_settings.font_uppercase,
                "fontSize": user_settings.font_size,
                "fontWeight": 900,
                "fontColor": user_settings.font_color,
                "fontShadow": size_token(user_settings.stroke),
                "stroke": size_token(user_settings.stroke),
                "strokeColor": user_settings.stroke_color,
            },
            "highlightOptions": {
                "randomColourOne": user_settings.highlight_color,
                "randomColourTwo": user_settings.highlight_color,
                "randomColourThree": user_settings.highlight_color,
            },
        },
        "exportSettings": {
            "quality": runtime.quality,
            "speed": runtime.export_speed,
            "outputMode": runtime.output_mode,
        },
    }
    if user_settings.language != "auto":
        payload["language"] = user_settings.language
    broll_settings = zapcap_broll_settings(user_settings.broll_percent)
    if broll_settings:
        payload["transcribeSettings"] = broll_settings
    return payload


def zapcap_broll_settings(percent: int) -> dict[str, Any] | None:
    if percent <= 0:
        return None
    return {"broll": {"brollPercent": max(0, min(100, percent))}}


def size_token(value: int) -> str:
    if value <= 0:
        return "none"
    if value <= 4:
        return "s"
    if value <= 10:
        return "m"
    return "l"


def zapcap_runtime_from_settings(settings: Settings) -> ZapCapRuntimeSettings:
    return ZapCapRuntimeSettings(
        api_key=settings.zapcap_api_key,
        api_base_url=settings.zapcap_api_base_url,
        enabled=settings.zapcap_enabled,
        poll_seconds=settings.zapcap_poll_seconds,
        timeout_seconds=settings.zapcap_timeout_seconds,
        request_timeout_seconds=settings.zapcap_request_timeout_seconds,
        ttl=settings.zapcap_ttl,
        output_mode=settings.zapcap_output_mode,
        quality=settings.zapcap_quality,
        export_speed=settings.zapcap_export_speed,
    )


def with_zapcap_disabled(settings: Settings) -> Settings:
    return replace(settings, post_heygen_visuals_enabled=False)
