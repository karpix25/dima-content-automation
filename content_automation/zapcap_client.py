from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx


class ZapCapApiError(RuntimeError):
    pass


@dataclass(frozen=True)
class ZapCapVideo:
    id: str
    raw: dict[str, Any]


@dataclass(frozen=True)
class ZapCapTask:
    id: str
    status: str
    download_url: str | None
    raw: dict[str, Any]


@dataclass(frozen=True)
class ZapCapTemplate:
    id: str
    name: str
    raw: dict[str, Any]


@dataclass(frozen=True)
class ZapCapApiClient:
    api_key: str | None
    base_url: str = "https://api.zapcap.ai"
    timeout_seconds: float = 60

    def upload_video(self, video_path: Path, *, ttl: str | None = None) -> ZapCapVideo:
        if not self.api_key:
            raise ZapCapApiError("ZAPCAP_API_KEY is not configured")
        if not video_path.exists() or not video_path.is_file():
            raise ZapCapApiError(f"Video file not found: {video_path}")
        params = {"ttl": ttl} if ttl else None
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                with video_path.open("rb") as file:
                    response = client.post(
                        self._url("/videos"),
                        headers=self._headers(),
                        params=params,
                        files={"file": (video_path.name, file, "video/mp4")},
                    )
        except httpx.HTTPError as exc:
            raise ZapCapApiError(f"ZapCap upload failed: {exc}") from exc
        data = self._json_response(response)
        video_id = _first_text(data, "id", "videoId", "video_id")
        if not video_id:
            raise ZapCapApiError(f"ZapCap did not return video id: {data}")
        return ZapCapVideo(id=video_id, raw=data)

    def create_task(self, video_id: str, payload: dict[str, Any], *, ttl: str | None = None) -> ZapCapTask:
        params = {"ttl": ttl} if ttl else None
        response = self._request("POST", f"/videos/{video_id}/task", json=payload, params=params)
        return self._task_from_response(response)

    def get_task(self, video_id: str, task_id: str) -> ZapCapTask:
        response = self._request("GET", f"/videos/{video_id}/task/{task_id}")
        return self._task_from_response(response)

    def list_templates(self) -> list[ZapCapTemplate]:
        data = self._request("GET", "/templates")
        raw_items = data.get("templates") or data.get("items") or data.get("data") or []
        if not isinstance(raw_items, list):
            raise ZapCapApiError(f"ZapCap returned unexpected templates response: {data}")
        templates: list[ZapCapTemplate] = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            template_id = _first_text(item, "id", "templateId", "template_id")
            if not template_id:
                continue
            name = _first_text(item, "name", "title", "label") or template_id
            templates.append(ZapCapTemplate(id=template_id, name=name, raw=item))
        return templates

    def wait_for_task(self, video_id: str, task_id: str, *, poll_seconds: int, timeout_seconds: int) -> ZapCapTask:
        deadline = time.monotonic() + timeout_seconds
        last: ZapCapTask | None = None
        while time.monotonic() < deadline:
            last = self.get_task(video_id, task_id)
            if last.status == "completed":
                return last
            if last.status == "failed":
                raise ZapCapApiError(f"ZapCap task failed: {last.raw}")
            time.sleep(max(3, poll_seconds))
        status = f" last status={last.status}" if last else ""
        raise ZapCapApiError(f"ZapCap task {task_id} timed out after {timeout_seconds}s.{status}")

    def download(self, url: str, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with httpx.Client(timeout=self.timeout_seconds, follow_redirects=True) as client:
                response = client.get(url)
        except httpx.HTTPError as exc:
            raise ZapCapApiError(f"ZapCap download failed: {exc}") from exc
        if response.status_code >= 400:
            raise ZapCapApiError(f"ZapCap download HTTP {response.status_code}: {response.text[:1000]}")
        output_path.write_bytes(response.content)
        return output_path

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        if not self.api_key:
            raise ZapCapApiError("ZAPCAP_API_KEY is not configured")
        try:
            response = httpx.request(
                method,
                self._url(path),
                headers=self._headers(has_json=json is not None),
                json=json,
                params=params,
                timeout=self.timeout_seconds,
            )
        except httpx.HTTPError as exc:
            raise ZapCapApiError(f"ZapCap request failed: {exc}") from exc
        return self._json_response(response)

    def _json_response(self, response: httpx.Response) -> dict[str, Any]:
        if response.status_code >= 400:
            raise ZapCapApiError(f"ZapCap HTTP {response.status_code}: {response.text[:1000]}")
        try:
            data = response.json()
        except ValueError as exc:
            raise ZapCapApiError(f"ZapCap returned non-JSON response: {response.text[:1000]}") from exc
        if not isinstance(data, dict):
            raise ZapCapApiError(f"ZapCap returned unexpected response: {data}")
        return data

    def _task_from_response(self, data: dict[str, Any]) -> ZapCapTask:
        task_id = _first_text(data, "id", "taskId", "task_id")
        status = _first_text(data, "status") or "unknown"
        download_url = _first_text(data, "downloadUrl", "download_url", "renderUrl", "videoUrl")
        if not task_id:
            raise ZapCapApiError(f"ZapCap did not return task id: {data}")
        return ZapCapTask(id=task_id, status=status, download_url=download_url, raw=data)

    def _headers(self, *, has_json: bool = False) -> dict[str, str]:
        headers = {"x-api-key": self.api_key or ""}
        if has_json:
            headers["Content-Type"] = "application/json"
        return headers

    def _url(self, path: str) -> str:
        return f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"


def _first_text(data: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    nested = data.get("data")
    if isinstance(nested, dict):
        return _first_text(nested, *keys)
    return None
