from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from .vizard_models import VizardClip, VizardProjectResult


class VizardApiError(RuntimeError):
    pass


@dataclass(frozen=True)
class VizardApiClient:
    api_key: str | None
    base_url: str = "https://elb-api.vizard.ai/hvizard-server-front/open-api/v1"
    timeout_seconds: float = 60

    def submit_youtube(self, payload: dict[str, object]) -> str:
        data = self._request("POST", "/project/create", json=payload)
        project_id = str(data.get("projectId") or "").strip()
        if not project_id:
            raise VizardApiError(f"Vizard did not return projectId: {data}")
        return project_id

    def query_project(self, project_id: str) -> VizardProjectResult:
        data = self._request("GET", f"/project/query/{project_id}")
        return parse_project_result(data)

    def _request(self, method: str, path: str, *, json: dict[str, object] | None = None) -> dict[str, Any]:
        if not self.api_key:
            raise VizardApiError("VIZARD_API_KEY is not configured")
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        try:
            response = httpx.request(method, url, headers=self._headers(json is not None), json=json, timeout=self.timeout_seconds)
        except httpx.HTTPError as exc:
            raise VizardApiError(f"Vizard request failed: {exc}") from exc
        if response.status_code >= 400:
            raise VizardApiError(f"Vizard HTTP {response.status_code}: {response.text[:1000]}")
        try:
            data = response.json()
        except ValueError as exc:
            raise VizardApiError(f"Vizard returned non-JSON response: {response.text[:1000]}") from exc
        code = int(data.get("code") or 0)
        if code not in {1000, 2000}:
            raise VizardApiError(f"Vizard API error {code}: {data}")
        return data

    def _headers(self, has_json: bool) -> dict[str, str]:
        headers = {"VIZARDAI_API_KEY": self.api_key or ""}
        if has_json:
            headers["Content-Type"] = "application/json"
        return headers


def parse_project_result(data: dict[str, Any]) -> VizardProjectResult:
    videos = data.get("videos") if isinstance(data.get("videos"), list) else []
    return VizardProjectResult(
        project_id=str(data.get("projectId") or ""),
        project_name=str(data.get("projectName") or ""),
        share_link=str(data.get("shareLink") or "") or None,
        clips=[parse_clip(item) for item in videos if isinstance(item, dict)],
    )


def parse_clip(data: dict[str, Any]) -> VizardClip:
    duration = data.get("videoMsDuration")
    return VizardClip(
        video_id=str(data.get("videoId") or ""),
        video_url=str(data.get("videoUrl") or ""),
        duration_ms=int(duration) if isinstance(duration, int | float) else None,
        title=str(data.get("title") or ""),
        transcript=str(data.get("transcript") or ""),
        viral_score=str(data.get("viralScore") or ""),
        viral_reason=str(data.get("viralReason") or ""),
        clip_editor_url=str(data.get("clipEditorUrl") or ""),
    )
