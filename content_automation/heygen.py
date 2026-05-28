from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx


class HeyGenError(RuntimeError):
    pass


@dataclass(frozen=True)
class HeyGenAvatar:
    id: str
    name: str
    preview_image_url: str | None
    preview_video_url: str | None
    raw: dict[str, Any]


@dataclass(frozen=True)
class HeyGenVideoResult:
    video_id: str
    status: str
    video_url: str | None
    raw: dict[str, Any]


class HeyGenClient:
    def __init__(
        self,
        *,
        api_key: str | None,
        api_base_url: str = "https://api.heygen.com",
        upload_base_url: str = "https://upload.heygen.com",
        aspect_ratio: str = "9:16",
        resolution: str = "720p",
        output_format: str = "mp4",
        poll_seconds: int = 15,
        timeout_seconds: int = 900,
    ):
        self.api_key = api_key
        self.api_base_url = api_base_url.rstrip("/")
        self.upload_base_url = upload_base_url.rstrip("/")
        self.aspect_ratio = aspect_ratio
        self.resolution = resolution
        self.output_format = output_format
        self.poll_seconds = poll_seconds
        self.timeout_seconds = timeout_seconds

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def headers(self) -> dict[str, str]:
        if not self.api_key:
            raise HeyGenError("HEYGEN_API_KEY не задан")
        return {"x-api-key": self.api_key, "accept": "application/json"}

    async def list_avatar_looks(self, *, limit: int = 50) -> list[HeyGenAvatar]:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(f"{self.api_base_url}/v3/avatars/looks", headers=self.headers())
        if response.status_code >= 400:
            fallback = await self.list_avatars_v2(limit=limit)
            if fallback:
                return fallback
            raise HeyGenError(f"HeyGen avatars error {response.status_code}: {response.text[:1000]}")

        payload = response.json()
        items = _extract_items(payload, "avatar_looks", "looks", "avatars", "items")
        avatars: list[HeyGenAvatar] = []
        for item in items[:limit]:
            avatar = _parse_avatar(item)
            if avatar:
                avatars.append(avatar)
        if avatars:
            return avatars

        fallback = await self.list_avatars_v2(limit=limit)
        if fallback:
            return fallback
        raise HeyGenError("HeyGen вернул пустой список аватаров")

    async def list_avatars_v2(self, *, limit: int = 50) -> list[HeyGenAvatar]:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(f"{self.api_base_url}/v2/avatars", headers=self.headers())
        if response.status_code >= 400:
            return []
        payload = response.json()
        items = _extract_items(payload, "avatars", "avatar_list", "items")
        avatars: list[HeyGenAvatar] = []
        for item in items[:limit]:
            avatar = _parse_avatar(item)
            if avatar:
                avatars.append(avatar)
        return avatars

    async def upload_audio_file(self, path: Path) -> str:
        if not path.exists() or not path.is_file():
            raise HeyGenError(f"Аудиофайл не найден: {path}")
        content_type = "audio/mpeg" if path.suffix.lower() == ".mp3" else "application/octet-stream"
        headers = self.headers()
        async with httpx.AsyncClient(timeout=120) as client:
            with path.open("rb") as audio_file:
                response = await client.post(
                    f"{self.api_base_url}/v3/assets",
                    headers=headers,
                    files={"file": (path.name, audio_file, content_type)},
                )
        if response.status_code >= 400 and self.upload_base_url:
            legacy_headers = {**self.headers(), "content-type": content_type}
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    f"{self.upload_base_url}/v1/asset",
                    headers=legacy_headers,
                    content=path.read_bytes(),
                )
        if response.status_code >= 400:
            raise HeyGenError(f"HeyGen upload error {response.status_code}: {response.text[:1000]}")
        payload = response.json()
        asset_id = _first_text(payload, ("data", "asset_id"), ("data", "id"), ("asset_id",), ("id",))
        if not asset_id:
            raise HeyGenError(f"HeyGen не вернул asset id после upload: {payload}")
        return asset_id

    async def create_video_from_audio(self, *, avatar_id: str, audio_asset_id: str, title: str | None = None) -> HeyGenVideoResult:
        body = {
            "type": "avatar",
            "avatar_id": avatar_id,
            "audio_asset_id": audio_asset_id,
            "title": title or "Telegram approved script",
            "aspect_ratio": self.aspect_ratio,
            "resolution": self.resolution,
            "output_format": self.output_format,
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.api_base_url}/v3/videos",
                headers={**self.headers(), "content-type": "application/json"},
                json=body,
            )
        if response.status_code >= 400:
            raise HeyGenError(f"HeyGen create video error {response.status_code}: {response.text[:1000]}")
        payload = response.json()
        video_id = _first_text(payload, ("data", "video_id"), ("data", "id"), ("video_id",), ("id",))
        if not video_id:
            raise HeyGenError(f"HeyGen не вернул video id: {payload}")
        return HeyGenVideoResult(
            video_id=video_id,
            status=_first_text(payload, ("data", "status"), ("status",)) or "submitted",
            video_url=_first_text(payload, ("data", "video_url"), ("data", "url"), ("video_url",), ("url",)),
            raw=payload,
        )

    async def get_video(self, video_id: str) -> HeyGenVideoResult:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(f"{self.api_base_url}/v3/videos/{video_id}", headers=self.headers())
        if response.status_code >= 400:
            raise HeyGenError(f"HeyGen video status error {response.status_code}: {response.text[:1000]}")
        payload = response.json()
        return HeyGenVideoResult(
            video_id=video_id,
            status=(_first_text(payload, ("data", "status"), ("status",)) or "unknown").lower(),
            video_url=_first_text(
                payload,
                ("data", "video_url"),
                ("data", "url"),
                ("data", "download_url"),
                ("video_url",),
                ("url",),
                ("download_url",),
            ),
            raw=payload,
        )

    async def wait_for_video(self, video_id: str) -> HeyGenVideoResult:
        deadline = time.monotonic() + self.timeout_seconds
        last: HeyGenVideoResult | None = None
        while time.monotonic() < deadline:
            last = await self.get_video(video_id)
            if last.status in {"completed", "complete", "done", "success", "ready"} and last.video_url:
                return last
            if last.status in {"failed", "failure", "error", "canceled", "cancelled"}:
                raise HeyGenError(f"HeyGen video failed: {last.raw}")
            await asyncio.sleep(self.poll_seconds)
        raise HeyGenError(f"HeyGen video timeout: {last.raw if last else video_id}")


def _extract_items(payload: Any, *keys: str) -> list[dict[str, Any]]:
    data = payload.get("data") if isinstance(payload, dict) else None
    candidates = [payload, data]
    for candidate in candidates:
        if isinstance(candidate, list):
            return [item for item in candidate if isinstance(item, dict)]
        if not isinstance(candidate, dict):
            continue
        for key in keys:
            value = candidate.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def _parse_avatar(item: dict[str, Any]) -> HeyGenAvatar | None:
    avatar_id = str(
        item.get("id")
        or item.get("avatar_id")
        or item.get("avatar_group_id")
        or item.get("look_id")
        or ""
    ).strip()
    name = str(item.get("name") or item.get("avatar_name") or item.get("display_name") or avatar_id).strip()
    if not avatar_id:
        return None
    return HeyGenAvatar(
        id=avatar_id,
        name=name or avatar_id,
        preview_image_url=_first_text(
            item,
            ("preview_image_url",),
            ("preview_image",),
            ("image_url",),
            ("thumbnail_url",),
            ("thumbnail",),
        ),
        preview_video_url=_first_text(item, ("preview_video_url",), ("preview_video",), ("video_url",)),
        raw=item,
    )


def _first_text(payload: Any, *paths: tuple[str, ...]) -> str | None:
    for path in paths:
        current = payload
        for key in path:
            if not isinstance(current, dict):
                current = None
                break
            current = current.get(key)
        if current is not None and str(current).strip():
            return str(current).strip()
    return None
