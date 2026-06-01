from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx


class KieImageError(RuntimeError):
    pass


@dataclass(frozen=True)
class KieImageConfig:
    api_key: str | None
    base_url: str
    model: str
    aspect_ratio: str
    resolution: str
    poll_timeout_seconds: float
    poll_interval_seconds: float
    create_task_max_attempts: int
    create_task_retry_delay_seconds: float


class KieImageClient:
    def __init__(self, config: KieImageConfig) -> None:
        self.config = config

    def is_configured(self) -> bool:
        return bool(self.config.api_key)

    def generate_image(self, *, prompt: str, output_path: Path) -> Path | None:
        clean_prompt = " ".join((prompt or "").split())
        if not clean_prompt or not self.config.api_key:
            return None
        task_id = self._create_task(
            {
                "model": self.config.model,
                "input": {
                    "prompt": clean_prompt,
                    "aspect_ratio": self.config.aspect_ratio,
                    "resolution": self.config.resolution,
                },
            }
        )
        result_url = self._poll_result_url(task_id)
        return self._download(result_url, output_path)

    def _create_task(self, payload: dict[str, Any]) -> str:
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        last_error = ""
        with httpx.Client(timeout=60) as client:
            for attempt in range(1, self.config.create_task_max_attempts + 1):
                try:
                    response = client.post(f"{self.config.base_url}/api/v1/jobs/createTask", headers=headers, json=payload)
                    response.raise_for_status()
                    data = response.json()
                    task_id = str(((data or {}).get("data") or {}).get("taskId") or "").strip()
                    if task_id:
                        return task_id
                    raise KieImageError(f"KIE response has no taskId: {data}")
                except Exception as exc:
                    last_error = str(exc)
                    if attempt >= self.config.create_task_max_attempts:
                        break
                    time.sleep(self.config.create_task_retry_delay_seconds * attempt)
        raise KieImageError(f"KIE createTask failed: {last_error}")

    def _poll_result_url(self, task_id: str) -> str:
        headers = {"Authorization": f"Bearer {self.config.api_key}"}
        deadline = time.time() + self.config.poll_timeout_seconds
        with httpx.Client(timeout=60) as client:
            while time.time() < deadline:
                response = client.get(
                    f"{self.config.base_url}/api/v1/jobs/recordInfo",
                    headers=headers,
                    params={"taskId": task_id},
                )
                response.raise_for_status()
                data = response.json()
                record = (data or {}).get("data") or {}
                state = str(record.get("state") or "").strip().lower()
                if state == "success":
                    return _result_url(record)
                if state == "fail":
                    raise KieImageError(f"KIE task failed: {record.get('failMsg') or record}")
                time.sleep(self.config.poll_interval_seconds)
        raise KieImageError(f"KIE task timed out: {task_id}")

    def _download(self, image_url: str, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with httpx.Client(timeout=180, follow_redirects=True) as client:
            response = client.get(image_url)
            response.raise_for_status()
        output_path.write_bytes(response.content)
        return output_path


def _result_url(record: dict[str, Any]) -> str:
    raw = record.get("resultJson")
    payload = json.loads(raw) if isinstance(raw, str) and raw.strip() else {}
    urls = payload.get("resultUrls") or payload.get("urls") or []
    if urls and isinstance(urls[0], str) and urls[0].strip():
        return urls[0].strip()
    raise KieImageError(f"KIE result has no image url: {record}")
