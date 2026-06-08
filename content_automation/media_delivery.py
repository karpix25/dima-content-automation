from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, replace
from pathlib import Path

import httpx

from .config import Settings
from .deepgram_transcription import DeepgramConfig
from .elevenlabs_mcp import ElevenLabsMCPClient
from .heygen import HeyGenClient
from .kie_image import KieImageClient
from .media_assets import MediaAssetStore
from .montage_renderer import MontageRendererConfig, render_montage_if_configured
from .post_heygen_video import apply_cover_frame, apply_post_heygen_visuals
from .reference_paths import selected_thumbnail_style_reference_paths, target_from_record_format, thumbnail_face_reference_paths
from .script_length import WordBudget, count_spoken_words, vertical_word_budget, youtube_word_budget
from .settings_service import get_overlay_start_percent, get_random_overlay_path, get_user_settings
from .storage import ScriptRecord, Storage
from .video_overlay import VideoOverlayError, apply_overlay, cleanup_old_videos, download_video
from .video_geometry import video_size_for_format
from .voice_speed_profile import calibrated_voice_wpm
from .voiceover_timing import analyze_voiceover_timing, estimate_initial_voiceover_speed
from .visual_assets import generate_post_heygen_assets

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AvatarDeliveryResult:
    video_path: Path
    telegram_message_id: str | None
    heygen_video_id: str


def create_and_send_avatar_video(
    *,
    record: ScriptRecord,
    user_id: str,
    format_key: str,
    settings: Settings,
    storage: Storage,
    asset_store: MediaAssetStore,
    kie_client: KieImageClient,
) -> AvatarDeliveryResult:
    target = "horizontal" if format_key == "avatar_horizontal" else "vertical"
    output_record = replace(record, format=output_format_for_job(format_key))
    state = get_user_settings(storage, settings, user_id)
    avatar_id = state.heygen_avatar_id if target == "horizontal" else state.heygen_vertical_avatar_id
    avatar_name = state.heygen_avatar_name if target == "horizontal" else state.heygen_vertical_avatar_name
    if not avatar_id:
        raise RuntimeError(f"HeyGen avatar для {target} не выбран")

    voice_wpm = calibrated_voice_wpm(storage, user_id, state.elevenlabs_voice_id)
    word_budget = (
        youtube_word_budget(state.youtube_long_duration_minutes, wpm=voice_wpm)
        if target == "horizontal"
        else vertical_word_budget(state.vertical_avatar_duration_mode, wpm=voice_wpm)
    )
    audio_path = _generate_audio(
        record,
        user_id,
        settings,
        state.elevenlabs_voice_id,
        state.elevenlabs_voice_name,
        word_budget=word_budget,
        voice_wpm=voice_wpm,
    )
    heygen = _heygen_client(settings, target)
    if not heygen.is_configured():
        raise RuntimeError("HEYGEN_API_KEY не задан")

    ready = asyncio.run(_create_heygen_video(heygen, output_record, Path(audio_path), avatar_id, state.heygen_video_api_version, state.heygen_avatar_engine))
    if not ready.video_url:
        raise RuntimeError(f"HeyGen не вернул ссылку на видео: {ready.raw}")

    final_path = _download_and_finish_video(
        record=output_record,
        user_id=user_id,
        settings=settings,
        storage=storage,
        asset_store=asset_store,
        kie_client=kie_client,
        video_url=ready.video_url,
    )
    message_id = send_video_document_to_telegram(
        token=settings.telegram_bot_token,
        chat_id=user_id,
        video_path=final_path,
        caption=f"🎬 {avatar_name or 'HeyGen avatar'}\nСценарий #{record.id}: {record.title or record.hook}",
    )
    return AvatarDeliveryResult(video_path=final_path, telegram_message_id=message_id, heygen_video_id=ready.video_id)


def create_and_send_existing_heygen_video(
    *,
    record: ScriptRecord,
    user_id: str,
    format_key: str,
    heygen_video_id: str,
    settings: Settings,
    storage: Storage,
    asset_store: MediaAssetStore,
    kie_client: KieImageClient,
) -> AvatarDeliveryResult:
    target = "horizontal" if format_key == "avatar_horizontal" else "vertical"
    output_record = replace(record, format=output_format_for_job(format_key))
    video_id = heygen_video_id.strip()
    if not video_id:
        raise RuntimeError("HeyGen video id не задан")
    heygen = _heygen_client(settings, target)
    if not heygen.is_configured():
        raise RuntimeError("HEYGEN_API_KEY не задан")

    ready = asyncio.run(heygen.wait_for_video(video_id))
    if not ready.video_url:
        raise RuntimeError(f"HeyGen не вернул ссылку на готовое видео: {ready.raw}")

    final_path = _download_and_finish_video(
        record=output_record,
        user_id=user_id,
        settings=settings,
        storage=storage,
        asset_store=asset_store,
        kie_client=kie_client,
        video_url=ready.video_url,
    )
    message_id = send_video_document_to_telegram(
        token=settings.telegram_bot_token,
        chat_id=user_id,
        video_path=final_path,
        caption=f"🎬 HeyGen #{video_id}\nСценарий #{record.id}: {record.title or record.hook}",
    )
    return AvatarDeliveryResult(video_path=final_path, telegram_message_id=message_id, heygen_video_id=ready.video_id)


def _generate_audio(
    record: ScriptRecord,
    user_id: str,
    settings: Settings,
    voice_id: str | None,
    voice_name: str,
    *,
    word_budget: WordBudget,
    voice_wpm: int,
) -> str:
    elevenlabs = ElevenLabsMCPClient(
        api_key=settings.elevenlabs_api_key,
        command=settings.elevenlabs_mcp_command,
        output_directory=settings.elevenlabs_output_directory,
        timeout_seconds=180,
    )
    initial_speed = estimate_initial_voiceover_speed(
        text=record.voiceover,
        budget=word_budget,
        base_speed=settings.elevenlabs_speed,
        spoken_wpm=voice_wpm,
    )
    logger.info(
        "Initial voiceover speed estimate: script=%s words=%s target_seconds=%s speed=%.3f",
        record.id,
        count_spoken_words(record.voiceover),
        word_budget.target_seconds,
        initial_speed,
    )
    result = _text_to_speech(
        elevenlabs,
        record=record,
        voice_id=voice_id,
        voice_name=voice_name,
        settings=settings,
        speed=initial_speed,
    )
    if result.file_path:
        try:
            analysis = analyze_voiceover_timing(
                text=record.voiceover,
                audio_path=Path(result.file_path),
                budget=word_budget,
                current_speed=initial_speed,
                spoken_wpm=voice_wpm,
            )
            logger.info(
                "Voiceover timing: script=%s words=%s duration=%.2fs wpm=%.1f target=%.2fs speed=%.3f",
                record.id,
                analysis.words,
                analysis.duration_seconds,
                analysis.words_per_minute,
                analysis.target_duration_seconds,
                analysis.current_speed,
            )
            if analysis.should_regenerate:
                logger.info(
                    "Regenerating voiceover with adjusted ElevenLabs speed: %.3f -> %.3f",
                    analysis.current_speed,
                    analysis.recommended_speed,
                )
                result = _text_to_speech(
                    elevenlabs,
                    record=record,
                    voice_id=voice_id,
                    voice_name=voice_name,
                    settings=settings,
                    speed=analysis.recommended_speed,
                )
        except VideoOverlayError:
            logger.exception("Voiceover timing analysis failed; using first generated audio")
    if not result.file_path:
        raise RuntimeError(f"ElevenLabs не вернул audio file для пользователя {user_id}: {result.message}")
    return result.file_path


def _text_to_speech(
    elevenlabs: ElevenLabsMCPClient,
    *,
    record: ScriptRecord,
    voice_id: str | None,
    voice_name: str,
    settings: Settings,
    speed: float,
):
    return elevenlabs.text_to_speech(
        text=record.voiceover,
        voice_name=voice_name,
        voice_id=voice_id,
        model_id=settings.elevenlabs_model_id,
        speed=speed,
        stability=settings.elevenlabs_stability,
        similarity_boost=settings.elevenlabs_similarity_boost,
        style=settings.elevenlabs_style,
        language=settings.elevenlabs_language,
    )


def _heygen_client(settings: Settings, target: str) -> HeyGenClient:
    return HeyGenClient(
        api_key=settings.heygen_api_key,
        api_base_url=settings.heygen_api_base_url,
        upload_base_url=settings.heygen_upload_base_url,
        aspect_ratio="16:9" if target == "horizontal" else "9:16",
        resolution=settings.heygen_resolution,
        output_format=settings.heygen_output_format,
        poll_seconds=settings.heygen_video_poll_seconds,
        timeout_seconds=settings.heygen_video_timeout_seconds,
        private_avatars_only=settings.heygen_private_avatars_only,
    )


async def _create_heygen_video(heygen: HeyGenClient, record: ScriptRecord, audio_path: Path, avatar_id: str, api_version: str, engine: str):
    asset_id = await heygen.upload_audio_file(audio_path)
    motion_prompt = _motion_prompt() if api_version == "v3" and engine == "avatar_iv" else None
    expressiveness = (os.getenv("HEYGEN_PHOTO_AVATAR_EXPRESSIVENESS") or "high").strip().lower() if motion_prompt else None
    created = await heygen.create_video_from_audio(
        avatar_id=avatar_id,
        audio_asset_id=asset_id,
        title=record.title,
        api_version=api_version,
        engine=engine,
        motion_prompt=motion_prompt,
        expressiveness=expressiveness,
    )
    return await heygen.wait_for_video(created.video_id)


def _download_and_finish_video(
    *,
    record: ScriptRecord,
    user_id: str,
    settings: Settings,
    storage: Storage,
    asset_store: MediaAssetStore,
    kie_client: KieImageClient,
    video_url: str,
) -> Path:
    cleanup_old_videos(settings.video_output_directory, keep_days=settings.video_keep_days)
    raw_path = settings.video_output_directory / f"miniapp_heygen_{record.id}_{record.format}.mp4"
    asyncio.run(download_video(video_url, raw_path))
    final_path = _post_heygen_visuals(record, user_id, settings, storage, asset_store, kie_client, raw_path)
    overlay_path = get_random_overlay_path(storage, user_id, record.format, seed=record.id)
    if overlay_path and overlay_path.exists():
        result = apply_overlay(
            video_path=final_path,
            overlay_path=overlay_path,
            output_path=settings.video_output_directory / f"miniapp_overlay_{record.id}_{record.format}.mp4",
            start_percent=get_overlay_start_percent(storage, user_id, record.format),
        )
        final_path = result.output_path
    return final_path


def _post_heygen_visuals(
    record: ScriptRecord,
    user_id: str,
    settings: Settings,
    storage: Storage,
    asset_store: MediaAssetStore,
    kie_client: KieImageClient,
    video_path: Path,
) -> Path:
    if not settings.post_heygen_visuals_enabled:
        logger.info("Post-HeyGen visuals disabled for script %s format=%s", record.id, record.format)
        return video_path
    montage_error: VideoOverlayError | None = None
    try:
        logger.info("Starting post-HeyGen montage for script %s format=%s", record.id, record.format)
        montage_path = render_montage_if_configured(
            record=record,
            video_path=video_path,
            output_dir=settings.video_output_directory / "miniapp_montage" / str(record.id),
            config=MontageRendererConfig(
                hyperframes_project_dir=settings.hyperframes_project_dir,
                remotion_project_dir=settings.remotion_project_dir,
                renderer=settings.montage_renderer,
                timeout_seconds=settings.montage_render_timeout_seconds,
                max_scenes=settings.montage_max_scenes,
                kie_client=kie_client,
                deepgram=DeepgramConfig(
                    api_key=settings.deepgram_api_key,
                    api_base_url=settings.deepgram_api_base_url,
                    model=settings.deepgram_model,
                    language=settings.deepgram_language,
                    timeout_seconds=settings.deepgram_timeout_seconds,
                ),
            ),
        )
        if montage_path:
            logger.info("Post-HeyGen montage rendered for script %s: %s", record.id, montage_path)
            cover_assets = generate_post_heygen_assets(
                record=record,
                output_dir=settings.video_output_directory / "miniapp_visual_assets" / str(record.id),
                broll_count=0,
                kie_client=kie_client,
                face_reference_paths=thumbnail_face_reference_paths(
                    storage=storage,
                    settings=settings,
                    user_id=user_id,
                    target=target_from_record_format(record.format),
                ),
                style_reference_paths=selected_thumbnail_style_reference_paths(
                    asset_store=asset_store,
                    user_id=user_id,
                    target=target_from_record_format(record.format),
                    seed=record.id,
                ),
            )
            return apply_cover_frame(
                video_path=montage_path,
                cover_path=cover_assets.cover_path,
                output_path=settings.video_output_directory / f"{montage_path.stem}_cover.mp4",
                cover_seconds=settings.post_heygen_cover_seconds,
                target_size=video_size_for_format(record.format),
            )
    except VideoOverlayError as exc:
        montage_error = exc
        logger.warning(
            "Post-HeyGen montage failed for script %s format=%s: %s",
            record.id,
            record.format,
            montage_error,
        )
    if _requires_smart_montage(record):
        raise VideoOverlayError(
            f"Smart montage is required for vertical HeyGen format, but renderer failed: {montage_error}"
        )
    logger.info("Falling back to primitive KIE+ffmpeg visuals for script %s format=%s", record.id, record.format)
    assets = generate_post_heygen_assets(
        record=record,
        output_dir=settings.video_output_directory / "miniapp_visual_assets" / str(record.id),
        broll_count=settings.post_heygen_broll_count,
        kie_client=kie_client,
        face_reference_paths=thumbnail_face_reference_paths(
            storage=storage,
            settings=settings,
            user_id=user_id,
            target=target_from_record_format(record.format),
        ),
        style_reference_paths=selected_thumbnail_style_reference_paths(
            asset_store=asset_store,
            user_id=user_id,
            target=target_from_record_format(record.format),
            seed=record.id,
        ),
    )
    result = apply_post_heygen_visuals(
        video_path=video_path,
        assets=assets,
        output_path=settings.video_output_directory / f"miniapp_visual_{record.id}_{record.format}.mp4",
        cover_seconds=settings.post_heygen_cover_seconds,
        broll_seconds=settings.post_heygen_broll_seconds,
        target_size=video_size_for_format(record.format),
    )
    return result.output_path


def _requires_smart_montage(record: ScriptRecord) -> bool:
    if record.format not in {"short", "shorts", "reels"}:
        return False
    raw = (os.getenv("ALLOW_PRIMITIVE_VERTICAL_HEYGEN_FALLBACK") or "").strip().lower()
    return raw not in {"1", "true", "yes", "on"}


def output_format_for_job(format_key: str) -> str:
    if format_key == "avatar_horizontal":
        return "youtube"
    if format_key == "avatar_reels":
        return "reels"
    return "short"


def send_video_document_to_telegram(*, token: str, chat_id: str, video_path: Path, caption: str) -> str | None:
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN не задан")
    with video_path.open("rb") as video_file:
        response = httpx.post(
            f"https://api.telegram.org/bot{token}/sendDocument",
            data={"chat_id": chat_id, "caption": caption},
            files={"document": (video_path.name, video_file, "video/mp4")},
            timeout=180,
        )
    if response.status_code >= 400:
        raise RuntimeError(f"Telegram sendDocument error {response.status_code}: {response.text[:1000]}")
    payload = response.json()
    return str(payload.get("result", {}).get("message_id") or "") or None


def _motion_prompt() -> str:
    return (
        os.getenv("HEYGEN_PHOTO_AVATAR_MOTION_PROMPT")
        or "Natural expressive presenter speaking directly to camera with subtle posture, head and hand movement."
    ).strip()
