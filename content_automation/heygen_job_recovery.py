from __future__ import annotations

import logging

from .config import Settings
from .infographic_delivery import build_kie_client
from .media_assets import MediaAssetStore
from .media_delivery import create_and_send_existing_heygen_video, get_existing_heygen_video_status
from .storage import FormatJob, Storage
from .web_format_job_helpers import (
    delivered_video_line,
    delivered_video_url,
    format_job_delivery_actor_user_id,
    mark_script_used_after_output_delivery,
)

logger = logging.getLogger(__name__)

HEYGEN_READY_STATUSES = {"completed", "complete", "done", "success", "ready"}
HEYGEN_FAILED_STATUSES = {"failed", "failure", "error", "canceled", "cancelled"}
AVATAR_FORMAT_KEYS = {"avatar_reels", "avatar_horizontal"}


def mark_heygen_submitted(storage: Storage, user_id: str, job: FormatJob, video_id: str) -> None:
    storage.update_format_job_delivery(
        user_id,
        job.id,
        status="submitted",
        external_task_id=video_id,
        output_text=(
            f"HeyGen принял ролик: {video_id}.\n"
            "Жду готовый файл. Если ожидание затянется, нажми «Обновить статус» позже."
        ),
    )


def keep_heygen_submitted_after_timeout(storage: Storage, user_id: str, job: FormatJob, exc: Exception) -> FormatJob | None:
    current = storage.get_format_job(user_id, job.id)
    if not current or current.status != "submitted" or not current.external_task_id:
        return None
    if "HeyGen video timeout" not in str(exc):
        return None
    logger.warning("HeyGen still processing after timeout: job_id=%s video_id=%s", job.id, current.external_task_id)
    return storage.update_format_job_delivery(
        user_id,
        job.id,
        status="submitted",
        external_task_id=current.external_task_id,
        error=None,
        output_text=_pending_output(current.external_task_id),
    )


def refresh_submitted_avatar_job(
    *,
    storage: Storage,
    asset_store: MediaAssetStore,
    settings: Settings,
    user_id: str,
    job: FormatJob,
) -> FormatJob:
    if job.status != "submitted" or job.format_key not in AVATAR_FORMAT_KEYS or not job.external_task_id:
        return job
    try:
        status = get_existing_heygen_video_status(settings=settings, format_key=job.format_key, heygen_video_id=job.external_task_id)
    except Exception as exc:
        logger.exception("Failed to refresh submitted HeyGen job: job_id=%s", job.id)
        return storage.update_format_job_delivery(
            user_id,
            job.id,
            status="submitted",
            external_task_id=job.external_task_id,
            output_text=f"Не смог проверить HeyGen сейчас: {exc}\nПовторный запуск не нужен.",
        )
    if status.status in HEYGEN_FAILED_STATUSES:
        return storage.update_format_job_delivery(
            user_id,
            job.id,
            status="failed",
            external_task_id=job.external_task_id,
            error=f"HeyGen video failed: {status.raw}",
            output_text=f"⚠️ HeyGen завершил ролик ошибкой: {status.raw}",
        )
    if status.status not in HEYGEN_READY_STATUSES or not status.video_url:
        return storage.update_format_job_delivery(
            user_id,
            job.id,
            status="submitted",
            external_task_id=job.external_task_id,
            output_text=_pending_output(job.external_task_id),
        )
    return _deliver_ready_heygen_job(
        storage=storage,
        asset_store=asset_store,
        settings=settings,
        user_id=user_id,
        job=job,
    )


def _deliver_ready_heygen_job(
    *,
    storage: Storage,
    asset_store: MediaAssetStore,
    settings: Settings,
    user_id: str,
    job: FormatJob,
) -> FormatJob:
    record = storage.get_script(user_id, job.script_id)
    if not record:
        raise RuntimeError("Script not found")
    result = create_and_send_existing_heygen_video(
        record=record,
        user_id=user_id,
        format_key=job.format_key,
        heygen_video_id=job.external_task_id or "",
        settings=settings,
        storage=storage,
        asset_store=asset_store,
        kie_client=build_kie_client(settings),
        delivery_actor_user_id=format_job_delivery_actor_user_id(job),
    )
    updated = storage.update_format_job_delivery(
        user_id,
        job.id,
        status="delivered",
        external_task_id=result.telegram_message_id or result.heygen_video_id,
        output_url=delivered_video_url(result),
        output_text=(
            "✅ Avatar формат создан и отправлен в Telegram.\n"
            f"HeyGen video id: {job.external_task_id}\n"
            f"{delivered_video_line(result)}"
        ),
    )
    mark_script_used_after_output_delivery(storage, user_id, job.script_id)
    return updated


def _pending_output(video_id: str) -> str:
    return f"HeyGen еще генерирует ролик: {video_id}.\nНажми «Обновить статус» позже. Повторный запуск не нужен."
