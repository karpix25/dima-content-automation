from __future__ import annotations

from .storage import FormatJob, Storage, row_to_format_job

ACTIVE_FORMAT_JOB_STATUSES = ("queued", "processing", "submitted")
AVATAR_FORMAT_KEYS = {"avatar_reels", "avatar_horizontal"}


class ActiveFormatJobError(RuntimeError):
    def __init__(self, job: FormatJob) -> None:
        self.job = job
        super().__init__(
            f"Уже идет генерация видео: задача #{job.id}. "
            "Дождись завершения или останови зависшую задачу перед новым запуском."
        )


def assert_no_active_avatar_job(storage: Storage, user_id: str, format_key: str) -> None:
    if format_key not in AVATAR_FORMAT_KEYS:
        return
    active = find_active_avatar_job(storage, user_id)
    if active:
        raise ActiveFormatJobError(active)


def find_active_avatar_job(storage: Storage, user_id: str) -> FormatJob | None:
    status_marks = ", ".join("?" for _ in ACTIVE_FORMAT_JOB_STATUSES)
    format_marks = ", ".join("?" for _ in AVATAR_FORMAT_KEYS)
    with storage._connect() as conn:
        row = conn.execute(
            f"""
            SELECT *
            FROM format_jobs
            WHERE user_id = ?
            AND status IN ({status_marks})
            AND format_key IN ({format_marks})
            ORDER BY id DESC
            LIMIT 1
            """,
            (user_id, *ACTIVE_FORMAT_JOB_STATUSES, *AVATAR_FORMAT_KEYS),
        ).fetchone()
    return row_to_format_job(row) if row else None
