from __future__ import annotations

from .storage import FormatJob, Storage, row_to_format_job

ACTIVE_FORMAT_JOB_STATUSES = ("queued", "processing", "submitted")


class ActiveFormatJobError(RuntimeError):
    def __init__(self, job: FormatJob) -> None:
        self.job = job
        super().__init__(
            f"Уже идет генерация формата: задача #{job.id}. "
            "Дождись завершения или останови зависшую задачу перед новым запуском."
        )


def assert_no_active_format_job(storage: Storage, user_id: str) -> None:
    active = find_active_format_job(storage, user_id)
    if active:
        raise ActiveFormatJobError(active)


def find_active_format_job(storage: Storage, user_id: str) -> FormatJob | None:
    status_marks = ", ".join("?" for _ in ACTIVE_FORMAT_JOB_STATUSES)
    with storage._connect() as conn:
        row = conn.execute(
            f"""
            SELECT *
            FROM format_jobs
            WHERE user_id = ?
            AND status IN ({status_marks})
            ORDER BY id DESC
            LIMIT 1
            """,
            (user_id, *ACTIVE_FORMAT_JOB_STATUSES),
        ).fetchone()
    return row_to_format_job(row) if row else None
