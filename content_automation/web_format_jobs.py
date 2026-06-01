from __future__ import annotations

import logging

from .config import Settings
from .infographic_delivery import create_and_send_infographic_reels
from .media_assets import MediaAssetStore
from .reference_paths import thumbnail_reference_paths
from .storage import FormatJob, Storage
from .turan_client import TuranApiClient, submit_format_job
from .turan_service import create_format_job


logger = logging.getLogger(__name__)


class ScriptNotFoundError(RuntimeError):
    pass


def create_and_deliver_format_job(
    *,
    storage: Storage,
    asset_store: MediaAssetStore,
    settings: Settings,
    user_id: str,
    script_id: int,
    format_key: str,
) -> FormatJob:
    logger.info("Creating format job: user_id=%s script_id=%s format_key=%s", user_id, script_id, format_key)
    job = create_format_job(storage, user_id, script_id, format_key, asset_store=asset_store, settings=settings)
    if job.format_key == "infographic_reels":
        return _deliver_infographic_job(
            storage=storage,
            asset_store=asset_store,
            settings=settings,
            user_id=user_id,
            script_id=script_id,
            job=job,
        )
    if settings.turan_api_base_url:
        result = submit_format_job(job, TuranApiClient(settings.turan_api_base_url), settings.turan_api_telegram_id or user_id)
        job = storage.update_format_job_delivery(
            user_id,
            job.id,
            status=result.status,
            external_task_id=result.external_task_id,
            error=result.error,
            raw=result.raw,
        )
    return job


def _deliver_infographic_job(
    *,
    storage: Storage,
    asset_store: MediaAssetStore,
    settings: Settings,
    user_id: str,
    script_id: int,
    job: FormatJob,
) -> FormatJob:
    logger.info("Running infographic delivery for format job %s", job.id)
    record = storage.get_script(user_id, script_id)
    if not record:
        raise ScriptNotFoundError("Script not found")
    try:
        result = create_and_send_infographic_reels(
            record=record,
            user_id=user_id,
            settings=settings,
            asset_store=asset_store,
            reference_paths=thumbnail_reference_paths(
                storage=storage,
                asset_store=asset_store,
                settings=settings,
                user_id=user_id,
                target="vertical",
            ),
        )
        job = storage.update_format_job_delivery(
            user_id,
            job.id,
            status="delivered",
            external_task_id=result.telegram_message_id,
            output_url=str(result.video_path),
            output_text=(
                "✅ Золотой фон / инфографика 5 сек. создана через Kie и отправлена в Telegram.\n"
                f"Файл: {result.video_path}"
            ),
        )
        logger.info(
            "Infographic format job delivered: job_id=%s telegram_message_id=%s output=%s",
            job.id,
            result.telegram_message_id,
            result.video_path,
        )
    except Exception as exc:
        logger.exception("Infographic format job failed: job_id=%s", job.id)
        job = storage.update_format_job_delivery(
            user_id,
            job.id,
            status="failed",
            error=str(exc),
            output_text=f"⚠️ Не удалось создать или отправить золотой фон: {exc}",
        )
    return job
