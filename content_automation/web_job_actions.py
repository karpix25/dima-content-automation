from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request

from .config import Settings
from .media_assets import MediaAssetStore
from .storage import FormatJob, Storage
from .web_format_jobs import (
    ScriptNotFoundError,
    create_queued_existing_heygen_job,
    create_queued_format_job,
    deliver_existing_format_job,
    deliver_existing_heygen_video_job,
)
from .web_serializers import job_to_out


LIVE_STATUSES = {"queued", "processing", "submitted", "ready"}
RETRYABLE_STATUSES = {"failed", "submit_failed"}
STALE_AFTER = timedelta(minutes=30)


def build_job_actions_router(*, storage: Storage, asset_store: MediaAssetStore, settings: Settings) -> APIRouter:
    router = APIRouter()

    @router.post("/api/format-jobs/{job_id}/retry")
    def retry_format_job(
        job_id: int,
        background_tasks: BackgroundTasks,
        request: Request,
        user_id: str = Query(..., min_length=1),
        actor_user_id: str | None = Query(None),
    ):
        job = _get_job(storage, user_id, job_id)
        if not can_retry_job(job):
            raise HTTPException(status_code=400, detail="Эту задачу пока нельзя повторить")
        delivery_actor_user_id = _delivery_actor_user_id(request, actor_user_id, job)
        try:
            video_id = str(job.raw.get("existing_heygen_video_id") or "").strip()
            if video_id:
                next_job = create_queued_existing_heygen_job(
                    storage=storage,
                    asset_store=asset_store,
                    settings=settings,
                    user_id=user_id,
                    script_id=job.script_id,
                    format_key=job.format_key,
                    heygen_video_id=video_id,
                    delivery_actor_user_id=delivery_actor_user_id,
                )
                background_tasks.add_task(
                    deliver_existing_heygen_video_job,
                    storage=storage,
                    asset_store=asset_store,
                    settings=settings,
                    user_id=user_id,
                    job_id=next_job.id,
                    heygen_video_id=video_id,
                )
            else:
                next_job = create_queued_format_job(
                    storage=storage,
                    asset_store=asset_store,
                    settings=settings,
                    user_id=user_id,
                    script_id=job.script_id,
                    format_key=job.format_key,
                    delivery_actor_user_id=delivery_actor_user_id,
                )
                background_tasks.add_task(
                    deliver_existing_format_job,
                    storage=storage,
                    asset_store=asset_store,
                    settings=settings,
                    user_id=user_id,
                    job_id=next_job.id,
                )
        except ScriptNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return job_to_out(next_job)

    @router.post("/api/format-jobs/{job_id}/mark-failed")
    def mark_format_job_failed(job_id: int, user_id: str = Query(..., min_length=1)):
        job = _get_job(storage, user_id, job_id)
        if job.status not in LIVE_STATUSES:
            raise HTTPException(status_code=400, detail="Можно остановить только активную задачу")
        updated = storage.update_format_job_delivery(
            user_id,
            job.id,
            status="failed",
            error="Stopped manually after stale status",
            output_text="⚠️ Задача остановлена вручную. Можно запустить повтор из этой карточки.",
        )
        return job_to_out(updated)

    return router


def can_retry_job(job: FormatJob) -> bool:
    return job.status in RETRYABLE_STATUSES or is_stale_job(job)


def is_stale_job(job: FormatJob, *, now: datetime | None = None) -> bool:
    if job.status not in LIVE_STATUSES:
        return False
    updated_at = _parse_datetime(job.updated_at)
    if not updated_at:
        return False
    return (now or datetime.now()) - updated_at >= STALE_AFTER


def _get_job(storage: Storage, user_id: str, job_id: int) -> FormatJob:
    job = storage.get_format_job(user_id, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Format job not found")
    return job


def _delivery_actor_user_id(request: Request, actor_user_id: str | None, job: FormatJob) -> str | None:
    return (
        getattr(request.state, "telegram_user_id", None)
        or (actor_user_id or "").strip()
        or str(job.raw.get("delivery_actor_user_id") or "").strip()
        or None
    )


def _parse_datetime(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None
