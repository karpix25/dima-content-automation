from __future__ import annotations

import logging

from .config import Settings
from .infographic_delivery import build_kie_client, create_and_send_infographic_reels
from .media_delivery import create_and_send_avatar_video, create_and_send_existing_heygen_video
from .media_assets import MediaAssetStore
from .reference_paths import infographic_design_reference_paths, thumbnail_face_reference_paths
from .settings_service import get_user_settings
from .storage import FormatJob, Storage
from .turan_client import TuranApiClient, submit_format_job
from .turan_formats import list_turan_formats
from .turan_service import create_format_job


logger = logging.getLogger(__name__)
DELETED_VIDEO_NOTICE = "Файл удален с сервера после отправки в Telegram."


class ScriptNotFoundError(RuntimeError):
    pass


def create_queued_format_job(
    *,
    storage: Storage,
    asset_store: MediaAssetStore,
    settings: Settings,
    user_id: str,
    script_id: int,
    format_key: str,
) -> FormatJob:
    job = create_format_job(storage, user_id, script_id, format_key, asset_store=asset_store, settings=settings)
    logger.info(
        "Queued format job created: user_id=%s script_id=%s job_id=%s format_key=%s",
        user_id,
        script_id,
        job.id,
        format_key,
    )
    return storage.update_format_job_delivery(
        user_id,
        job.id,
        status="queued",
        output_text=_queued_output(job),
    )


def create_queued_existing_heygen_job(
    *,
    storage: Storage,
    asset_store: MediaAssetStore,
    settings: Settings,
    user_id: str,
    script_id: int,
    format_key: str,
    heygen_video_id: str,
) -> FormatJob:
    video_id = heygen_video_id.strip()
    if not video_id:
        raise ValueError("HeyGen video id is required")
    if format_key not in {"avatar_reels", "avatar_horizontal"}:
        raise ValueError("Existing HeyGen video can be used only with avatar formats")
    job = create_format_job(storage, user_id, script_id, format_key, asset_store=asset_store, settings=settings)
    return storage.update_format_job_delivery(
        user_id,
        job.id,
        status="queued",
        external_task_id=video_id,
        output_text=(
            f"Задача #{job.id} поставлена в очередь.\n"
            f"Использую готовый HeyGen video id: {video_id}.\n"
            "Новый HeyGen ролик генерироваться не будет."
        ),
        raw={**job.raw, "existing_heygen_video_id": video_id},
    )


def deliver_existing_format_job(
    *,
    storage: Storage,
    asset_store: MediaAssetStore,
    settings: Settings,
    user_id: str,
    job_id: int,
) -> None:
    logger.info("Starting queued format job delivery: user_id=%s job_id=%s", user_id, job_id)
    existing = storage.get_format_job(user_id, job_id)
    if existing and existing.status != "queued":
        logger.info("Format job delivery skipped because status is %s: job_id=%s", existing.status, job_id)
        return
    job = storage.claim_queued_format_job(user_id, job_id, output_text=_processing_output(existing)) if existing else None
    if not job:
        logger.warning("Queued format job disappeared before delivery: user_id=%s job_id=%s", user_id, job_id)
        return
    logger.info(
        "Claimed queued format job: user_id=%s job_id=%s script_id=%s format_key=%s",
        user_id,
        job.id,
        job.script_id,
        job.format_key,
    )
    try:
        if job.format_key == "all":
            _deliver_existing_all_formats(
                storage=storage,
                asset_store=asset_store,
                settings=settings,
                user_id=user_id,
                script_id=job.script_id,
                bundle=job,
            )
            return
        _deliver_existing_single_format(
            storage=storage,
            asset_store=asset_store,
            settings=settings,
            user_id=user_id,
            script_id=job.script_id,
            job=job,
        )
    except Exception as exc:
        logger.exception("Queued format job delivery crashed: job_id=%s", job_id)
        storage.update_format_job_delivery(
            user_id,
            job_id,
            status="failed",
            error=str(exc),
            output_text=f"⚠️ Не удалось выполнить формат: {exc}",
        )


def deliver_existing_heygen_video_job(
    *,
    storage: Storage,
    asset_store: MediaAssetStore,
    settings: Settings,
    user_id: str,
    job_id: int,
    heygen_video_id: str,
) -> None:
    existing = storage.get_format_job(user_id, job_id)
    if existing and existing.status != "queued":
        logger.info("Existing HeyGen job skipped because status is %s: job_id=%s", existing.status, job_id)
        return
    job = storage.claim_queued_format_job(
        user_id,
        job_id,
        output_text=f"Скачиваю готовый HeyGen video id {heygen_video_id}, собираю smart montage и отправляю в Telegram.",
    ) if existing else None
    if not job:
        logger.warning("Queued existing HeyGen job disappeared before delivery: user_id=%s job_id=%s", user_id, job_id)
        return
    _deliver_avatar_job(
        storage=storage,
        asset_store=asset_store,
        settings=settings,
        user_id=user_id,
        script_id=job.script_id,
        job=job,
        existing_heygen_video_id=heygen_video_id,
    )


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
    if format_key == "all":
        return _deliver_all_formats(
            storage=storage,
            asset_store=asset_store,
            settings=settings,
            user_id=user_id,
            script_id=script_id,
        )
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
    if job.format_key in {"avatar_reels", "avatar_horizontal"}:
        return _deliver_avatar_job(
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


def _deliver_existing_single_format(
    *,
    storage: Storage,
    asset_store: MediaAssetStore,
    settings: Settings,
    user_id: str,
    script_id: int,
    job: FormatJob,
) -> FormatJob:
    if job.format_key == "infographic_reels":
        return _deliver_infographic_job(
            storage=storage,
            asset_store=asset_store,
            settings=settings,
            user_id=user_id,
            script_id=script_id,
            job=job,
        )
    if job.format_key in {"avatar_reels", "avatar_horizontal"}:
        return _deliver_avatar_job(
            storage=storage,
            asset_store=asset_store,
            settings=settings,
            user_id=user_id,
            script_id=script_id,
            job=job,
        )
    if settings.turan_api_base_url:
        result = submit_format_job(job, TuranApiClient(settings.turan_api_base_url), settings.turan_api_telegram_id or user_id)
        return storage.update_format_job_delivery(
            user_id,
            job.id,
            status=result.status,
            external_task_id=result.external_task_id,
            error=result.error,
            raw=result.raw,
        )
    return storage.update_format_job_delivery(user_id, job.id, status="delivered")


def _deliver_existing_all_formats(
    *,
    storage: Storage,
    asset_store: MediaAssetStore,
    settings: Settings,
    user_id: str,
    script_id: int,
    bundle: FormatJob,
) -> FormatJob:
    delivered: list[str] = []
    failed: list[str] = []
    for spec in list_turan_formats():
        child = create_and_deliver_format_job(
            storage=storage,
            asset_store=asset_store,
            settings=settings,
            user_id=user_id,
            script_id=script_id,
            format_key=spec.key,
        )
        if child.status == "failed":
            failed.append(f"{spec.label}: {child.error or child.output_text}")
        else:
            delivered.append(f"{spec.label}: {child.output_url or child.external_task_id or child.status}")
    status = "failed" if failed else "delivered"
    output = ["Генерация всех форматов завершена.", "", "Готово:", *delivered]
    if failed:
        output.extend(["", "Ошибки:", *failed])
    updated = storage.update_format_job_delivery(user_id, bundle.id, status=status, output_text="\n".join(output))
    mark_script_used_after_output_delivery(storage, user_id, script_id)
    return updated


def _deliver_all_formats(
    *,
    storage: Storage,
    asset_store: MediaAssetStore,
    settings: Settings,
    user_id: str,
    script_id: int,
) -> FormatJob:
    bundle = create_format_job(storage, user_id, script_id, "all", asset_store=asset_store, settings=settings)
    delivered: list[str] = []
    failed: list[str] = []
    for spec in list_turan_formats():
        child = create_and_deliver_format_job(
            storage=storage,
            asset_store=asset_store,
            settings=settings,
            user_id=user_id,
            script_id=script_id,
            format_key=spec.key,
        )
        if child.status == "failed":
            failed.append(f"{spec.label}: {child.error or child.output_text}")
        else:
            delivered.append(f"{spec.label}: {child.output_url or child.external_task_id or child.status}")
    status = "failed" if failed else "delivered"
    output = ["Генерация всех форматов завершена.", "", "Готово:", *delivered]
    if failed:
        output.extend(["", "Ошибки:", *failed])
    updated = storage.update_format_job_delivery(user_id, bundle.id, status=status, output_text="\n".join(output))
    mark_script_used_after_output_delivery(storage, user_id, script_id)
    return updated


def mark_script_used_after_output_delivery(storage: Storage, user_id: str, script_id: int) -> None:
    record = storage.get_script(user_id, script_id)
    if not record or record.status != "approved":
        return
    storage.update_script_status(user_id, script_id, "used_for_video")


def _queued_output(job: FormatJob) -> str:
    return (
        f"Задача #{job.id} поставлена в очередь.\n"
        "Можно закрыть окно: статус обновится в истории, а готовый файл придёт в Telegram."
    )


def _processing_output(job: FormatJob) -> str:
    if job.format_key == "infographic_reels":
        return "Генерирую карточку через Kie, собираю 5-секундное видео и отправляю в Telegram."
    if job.format_key in {"avatar_reels", "avatar_horizontal"}:
        return "Генерирую озвучку, HeyGen avatar video, визуальные вставки/обложку и отправляю в Telegram."
    if job.format_key == "all":
        return "Запускаю все форматы по очереди. Готовые файлы будут отправлены в Telegram."
    return "Задача выполняется."


def _deliver_avatar_job(
    *,
    storage: Storage,
    asset_store: MediaAssetStore,
    settings: Settings,
    user_id: str,
    script_id: int,
    job: FormatJob,
    existing_heygen_video_id: str | None = None,
) -> FormatJob:
    logger.info(
        "Running avatar delivery for format job %s: script_id=%s format_key=%s existing_heygen=%s",
        job.id,
        script_id,
        job.format_key,
        bool(existing_heygen_video_id),
    )
    record = storage.get_script(user_id, script_id)
    if not record:
        raise ScriptNotFoundError("Script not found")
    try:
        if existing_heygen_video_id:
            result = create_and_send_existing_heygen_video(
                record=record,
                user_id=user_id,
                format_key=job.format_key,
                heygen_video_id=existing_heygen_video_id,
                settings=settings,
                storage=storage,
                asset_store=asset_store,
                kie_client=build_kie_client(settings),
            )
        else:
            result = create_and_send_avatar_video(
                record=record,
                user_id=user_id,
                format_key=job.format_key,
                settings=settings,
                storage=storage,
                asset_store=asset_store,
                kie_client=build_kie_client(settings),
            )
        heygen_line = f"HeyGen video id: {existing_heygen_video_id}\n" if existing_heygen_video_id else ""
        job = storage.update_format_job_delivery(
            user_id,
            job.id,
            status="delivered",
            external_task_id=result.telegram_message_id or result.heygen_video_id,
            output_url=_delivered_video_url(result),
            output_text=(
                "✅ Avatar формат создан и отправлен в Telegram.\n"
                f"{heygen_line}"
                f"{_delivered_video_line(result)}"
            ),
        )
        mark_script_used_after_output_delivery(storage, user_id, script_id)
        logger.info("Avatar format job delivered: job_id=%s script_id=%s file=%s", job.id, script_id, result.video_path)
        return job
    except Exception as exc:
        logger.exception("Avatar format job failed: job_id=%s", job.id)
        return storage.update_format_job_delivery(
            user_id,
            job.id,
            status="failed",
            error=str(exc),
            output_text=f"⚠️ Не удалось создать avatar формат: {exc}",
        )


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
        state = get_user_settings(storage, settings, user_id)
        result = create_and_send_infographic_reels(
            record=record,
            user_id=user_id,
            settings=settings,
            asset_store=asset_store,
            storage=storage,
            cta_text=state.instagram_post_5s_cta_text,
            content_language=state.content_language,
            face_reference_paths=thumbnail_face_reference_paths(
                storage=storage,
                settings=settings,
                user_id=user_id,
                target="vertical",
            ),
            design_reference_paths=infographic_design_reference_paths(asset_store=asset_store, user_id=user_id),
        )
        job = storage.update_format_job_delivery(
            user_id,
            job.id,
            status="delivered",
            external_task_id=result.telegram_message_id,
            output_url=_delivered_video_url(result),
            output_text=(
                "✅ Золотой фон / инфографика 5 сек. создана через Kie и отправлена в Telegram.\n"
                f"{_delivered_video_line(result)}"
            ),
        )
        logger.info(
            "Infographic format job delivered: job_id=%s telegram_message_id=%s output=%s",
            job.id,
            result.telegram_message_id,
            result.video_path,
        )
        mark_script_used_after_output_delivery(storage, user_id, script_id)
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


def _delivered_video_url(result: object) -> str | None:
    return None if getattr(result, "video_deleted", False) else str(getattr(result, "video_path"))


def _delivered_video_line(result: object) -> str:
    if getattr(result, "video_deleted", False):
        return DELETED_VIDEO_NOTICE
    return f"Файл: {getattr(result, 'video_path')}"
