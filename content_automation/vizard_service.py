from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from .config import Settings
from .video_overlay import download_video
from .vizard_client import VizardApiClient, VizardApiError
from .vizard_models import VizardClip, VizardProjectResult, VizardUserSettings, vizard_settings_to_payload


class VizardServiceError(RuntimeError):
    pass


@dataclass(frozen=True)
class DownloadedVizardClip:
    clip: VizardClip
    path: Path


@dataclass(frozen=True)
class VizardDeliveryResult:
    project: VizardProjectResult
    downloaded_clips: list[DownloadedVizardClip]


def submit_and_wait_for_vizard_clips(
    *,
    client: VizardApiClient,
    user_settings: VizardUserSettings,
    video_url: str,
    poll_seconds: int,
    timeout_seconds: int,
    project_name: str | None = None,
) -> VizardProjectResult:
    project_id = client.submit_youtube(vizard_settings_to_payload(user_settings, video_url=video_url, project_name=project_name))
    deadline = time.monotonic() + timeout_seconds
    last_result: VizardProjectResult | None = None
    while time.monotonic() < deadline:
        last_result = client.query_project(project_id)
        if last_result.clips:
            return last_result
        time.sleep(max(5, poll_seconds))
    if last_result:
        return last_result
    raise VizardServiceError(f"Vizard project {project_id} did not return clips before timeout")


async def download_vizard_clips(
    *,
    settings: Settings,
    user_id: str,
    project: VizardProjectResult,
) -> list[DownloadedVizardClip]:
    output_dir = settings.video_output_directory / "vizard" / user_id / (project.project_id or "project")
    downloaded: list[DownloadedVizardClip] = []
    for index, clip in enumerate(project.clips, start=1):
        if not clip.video_url:
            continue
        path = output_dir / f"vizard_clip_{index:02d}_{clip.video_id or 'clip'}.mp4"
        await download_video(clip.video_url, path)
        downloaded.append(DownloadedVizardClip(clip=clip, path=path))
    return downloaded


def build_vizard_client(settings: Settings) -> VizardApiClient:
    return VizardApiClient(
        api_key=settings.vizard_api_key,
        base_url=settings.vizard_api_base_url,
        timeout_seconds=settings.vizard_request_timeout_seconds,
    )
