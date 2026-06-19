from __future__ import annotations

from .storage import FormatJob, Storage


DELETED_VIDEO_NOTICE = "Файл удален с сервера после отправки в Telegram."


def mark_script_used_after_output_delivery(storage: Storage, user_id: str, script_id: int) -> None:
    record = storage.get_script(user_id, script_id)
    if not record or record.status != "approved":
        return
    storage.update_script_status(user_id, script_id, "used_for_video")


def queued_output(job: FormatJob) -> str:
    return (
        f"Задача #{job.id} поставлена в очередь.\n"
        "Можно закрыть окно: статус обновится в истории, а готовый файл придёт в Telegram."
    )


def processing_output(job: FormatJob) -> str:
    if job.format_key == "infographic_reels":
        return "Генерирую карточку через Kie, собираю 5-секундное видео и отправляю в Telegram."
    if job.format_key in {"avatar_reels", "avatar_horizontal"}:
        return "Генерирую озвучку, HeyGen avatar video, визуальные вставки/обложку и отправляю в Telegram."
    if job.format_key == "all":
        return "Запускаю все форматы по очереди. Готовые файлы будут отправлены в Telegram."
    return "Задача выполняется."


def with_delivery_actor(raw: dict, project_user_id: str, actor_user_id: str | None) -> dict:
    actor = (actor_user_id or "").strip()
    if not actor or actor == project_user_id:
        return raw
    return {**raw, "delivery_actor_user_id": actor}


def format_job_delivery_actor_user_id(job: FormatJob) -> str | None:
    actor = str(job.raw.get("delivery_actor_user_id") or "").strip()
    return actor or None


def delivered_video_url(result: object) -> str | None:
    return None if getattr(result, "video_deleted", False) else str(getattr(result, "video_path"))


def delivered_video_line(result: object) -> str:
    if getattr(result, "video_deleted", False):
        return DELETED_VIDEO_NOTICE
    return f"Файл: {getattr(result, 'video_path')}"
