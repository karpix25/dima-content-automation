from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from .storage import FormatJob


@dataclass(frozen=True)
class TuranSubmissionResult:
    status: str
    external_task_id: str | None
    raw: dict[str, Any]
    error: str | None = None


class TuranApiClient:
    def __init__(self, base_url: str, *, timeout_seconds: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def create_task(self, telegram_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = httpx.post(
            f"{self.base_url}/tasks/{telegram_id}",
            json=payload,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, dict) else {"response": data}


def submit_format_job(job: FormatJob, client: TuranApiClient, telegram_id: str) -> TuranSubmissionResult:
    raw = dict(job.raw or {})
    try:
        payloads = _job_task_payloads(raw)
        submissions = [client.create_task(telegram_id, payload) for payload in payloads]
    except Exception as exc:
        raw["turan_submission"] = {
            "status": "failed",
            "error": str(exc),
        }
        return TuranSubmissionResult(
            status="submit_failed",
            external_task_id=None,
            raw=raw,
            error=str(exc),
        )

    task_ids = [str(item.get("task_id")) for item in submissions if item.get("task_id") is not None]
    raw["turan_submission"] = {
        "status": "submitted",
        "tasks": submissions,
    }
    return TuranSubmissionResult(
        status="submitted",
        external_task_id=",".join(task_ids) if task_ids else None,
        raw=raw,
    )


def _job_task_payloads(raw: dict[str, Any]) -> list[dict[str, Any]]:
    if "turan_task_input" in raw and isinstance(raw["turan_task_input"], dict):
        return [raw["turan_task_input"]]
    payloads: list[dict[str, Any]] = []
    for item in raw.get("formats") or []:
        if isinstance(item, dict) and isinstance(item.get("turan_task_input"), dict):
            payloads.append(item["turan_task_input"])
        elif isinstance(item, dict) and "source_url" in item and "type" in item:
            payloads.append(item)
    if not payloads:
        raise ValueError("Format job has no Turan task input payload")
    return payloads
