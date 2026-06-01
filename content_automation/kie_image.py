from __future__ import annotations

import json
import mimetypes
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx


class KieImageError(RuntimeError):
    pass


KIE_GPT_IMAGE_2_ASPECT_RATIOS = {
    "auto",
    "1:1",
    "3:2",
    "2:3",
    "4:3",
    "3:4",
    "5:4",
    "4:5",
    "16:9",
    "9:16",
    "2:1",
    "1:2",
    "3:1",
    "1:3",
    "21:9",
    "9:21",
}
KIE_GPT_IMAGE_2_RESOLUTIONS = {"1K", "2K", "4K"}


@dataclass(frozen=True)
class KieImageConfig:
    api_key: str | None
    base_url: str
    upload_base_url: str
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

    def generate_image(self, *, prompt: str, output_path: Path, reference_paths: list[Path] | None = None) -> Path | None:
        clean_prompt = " ".join((prompt or "").split())
        if not clean_prompt or not self.config.api_key:
            return None
        input_urls = self._upload_references(reference_paths or [])
        last_error = ""
        for model in _model_candidates(self.config.model, has_references=bool(input_urls)):
            try:
                task_id = self._create_task(_task_payload(model=model, prompt=clean_prompt, config=self.config, input_urls=input_urls))
                break
            except KieImageError as exc:
                last_error = str(exc)
                if "not supported" not in last_error.lower():
                    raise
        else:
            raise KieImageError(last_error)
        result_url = self._poll_result_url(task_id)
        return self._download(result_url, output_path)

    def _upload_references(self, paths: list[Path]) -> list[str]:
        valid_paths = [path for path in paths[:16] if path.exists()]
        if not valid_paths:
            return []
        urls: list[str] = []
        with httpx.Client(timeout=180, follow_redirects=True) as client:
            for path in valid_paths:
                urls.append(self._upload_reference(client, path))
        return urls

    def _upload_reference(self, client: httpx.Client, path: Path) -> str:
        headers = {"Authorization": f"Bearer {self.config.api_key}"}
        mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        with path.open("rb") as file_obj:
            response = client.post(
                f"{self.config.upload_base_url}/api/file-stream-upload",
                headers=headers,
                data={"uploadPath": "dima-references", "fileName": path.name},
                files={"file": (path.name, file_obj, mime_type)},
            )
        response.raise_for_status()
        data = response.json()
        if int((data or {}).get("code") or 200) != 200 and not (data or {}).get("success"):
            raise KieImageError(f"KIE reference upload failed: {data}")
        payload = (data or {}).get("data") or {}
        url = str(payload.get("fileUrl") or payload.get("downloadUrl") or "").strip()
        if not url:
            raise KieImageError(f"KIE reference upload returned no file URL: {data}")
        return url

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
                    if int((data or {}).get("code") or 200) != 200:
                        raise KieImageError(str(data))
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


def _task_payload(*, model: str, prompt: str, config: KieImageConfig, input_urls: list[str]) -> dict[str, Any]:
    input_payload: dict[str, Any] = {
        "prompt": prompt,
        "aspect_ratio": _normalize_aspect_ratio(config.aspect_ratio),
        "resolution": _normalize_resolution(config.resolution),
    }
    if input_urls:
        input_payload["input_urls"] = input_urls
    return {
        "model": model,
        "input": input_payload,
    }


def _model_candidates(model: str, *, has_references: bool = False) -> list[str]:
    primary = (model or "gpt-image-2").strip()
    if has_references:
        candidates = ["gpt-image-2-image-to-image", primary]
        return list(dict.fromkeys(item for item in candidates if item and item != "gpt-image-2-text-to-image"))
    aliases = {
        "gpt-image-2": ["gpt-image-2-text-to-image", "gpt-image-2"],
        "gpt-image-2-text-to-image": ["gpt-image-2-text-to-image", "gpt-image-2"],
    }
    candidates = aliases.get(primary, [primary])
    return list(dict.fromkeys(item for item in candidates if item))


def _normalize_aspect_ratio(value: str) -> str:
    normalized = (value or "").strip() or "9:16"
    return normalized if normalized in KIE_GPT_IMAGE_2_ASPECT_RATIOS else "9:16"


def _normalize_resolution(value: str) -> str:
    normalized = (value or "").strip().upper() or "1K"
    return normalized if normalized in KIE_GPT_IMAGE_2_RESOLUTIONS else "1K"
