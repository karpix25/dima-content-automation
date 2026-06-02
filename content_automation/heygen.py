from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx


class HeyGenError(RuntimeError):
    pass


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HeyGenAvatar:
    id: str
    name: str
    preview_image_url: str | None
    preview_video_url: str | None
    avatar_type: str
    supported_engines: list[str]
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
        private_avatars_only: bool = True,
    ):
        self.api_key = api_key
        self.api_base_url = api_base_url.rstrip("/")
        self.upload_base_url = upload_base_url.rstrip("/")
        self.aspect_ratio = aspect_ratio
        self.resolution = resolution
        self.output_format = output_format
        self.poll_seconds = poll_seconds
        self.timeout_seconds = timeout_seconds
        self.private_avatars_only = private_avatars_only

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def headers(self) -> dict[str, str]:
        if not self.api_key:
            raise HeyGenError("HEYGEN_API_KEY не задан")
        return {"x-api-key": self.api_key, "accept": "application/json"}

    async def list_avatar_looks(self, *, limit: int = 50) -> list[HeyGenAvatar]:
        params = {"ownership": "private"} if self.private_avatars_only else None
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self.api_base_url}/v3/avatars/looks",
                headers=self.headers(),
                params=params,
            )
        if response.status_code >= 400:
            fallback = await self.list_avatars_v2(limit=limit)
            if fallback:
                return fallback
            raise HeyGenError(f"HeyGen avatars error {response.status_code}: {response.text[:1000]}")

        payload = response.json()
        items = _extract_items(payload, "avatar_looks", "looks", "avatars", "items")
        avatars: list[HeyGenAvatar] = []
        for item in items[:limit]:
            if self.private_avatars_only and not _is_private_avatar(item, trusted_private_endpoint=True):
                continue
            avatar = _parse_avatar(item)
            if avatar:
                avatars.append(avatar)
        if avatars:
            return avatars

        fallback = await self.list_avatars_v2(limit=limit)
        if fallback:
            return fallback
        if self.private_avatars_only:
            raise HeyGenError("HeyGen не вернул приватных аватаров. Проверь, что в аккаунте есть свои AI avatars и API key от этого аккаунта.")
        raise HeyGenError("HeyGen вернул пустой список аватаров")

    async def list_avatars_v2(self, *, limit: int = 50) -> list[HeyGenAvatar]:
        params = {"avatar_type": "custom"} if self.private_avatars_only else None
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(f"{self.api_base_url}/v2/avatars", headers=self.headers(), params=params)
        if response.status_code >= 400:
            return []
        payload = response.json()
        items = _extract_items(payload, "avatars", "avatar_list", "items")
        avatars: list[HeyGenAvatar] = []
        for item in items[:limit]:
            if self.private_avatars_only and not _is_private_avatar(item, trusted_private_endpoint=False):
                continue
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

    async def create_video_from_audio(
        self,
        *,
        avatar_id: str,
        audio_asset_id: str,
        title: str | None = None,
        api_version: str = "v2",
        engine: str = "avatar_iv",
        motion_prompt: str | None = None,
        expressiveness: str | None = None,
    ) -> HeyGenVideoResult:
        api_version_value = (api_version or "v2").strip().lower()
        if api_version_value == "v3":
            body = self._video_v3_body(
                avatar_id=avatar_id,
                audio_asset_id=audio_asset_id,
                title=title,
                engine=engine,
                motion_prompt=motion_prompt,
                expressiveness=expressiveness,
            )
            endpoint = f"{self.api_base_url}/v3/videos"
        else:
            body = self._video_v2_body(avatar_id=avatar_id, audio_asset_id=audio_asset_id)
            endpoint = f"{self.api_base_url}/v2/video/generate"
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                endpoint,
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

    def _video_v3_body(
        self,
        *,
        avatar_id: str,
        audio_asset_id: str,
        title: str | None,
        engine: str,
        motion_prompt: str | None,
        expressiveness: str | None,
    ) -> dict[str, Any]:
        engine_type = (engine or "avatar_iv").strip().lower()
        if engine_type not in {"avatar_iv", "avatar_v"}:
            engine_type = "avatar_iv"
        body: dict[str, Any] = {
            "type": "avatar",
            "avatar_id": avatar_id,
            "audio_asset_id": audio_asset_id,
            "title": title or "Telegram approved script",
            "aspect_ratio": self.aspect_ratio,
            "resolution": self.resolution,
            "output_format": self.output_format,
            "engine": {"type": engine_type},
        }
        if engine_type == "avatar_iv":
            motion_prompt_value = (motion_prompt or "").strip()
            expressiveness_value = (expressiveness or "").strip().lower()
            if motion_prompt_value:
                body["motion_prompt"] = motion_prompt_value[:500]
            if expressiveness_value in {"low", "medium", "high"}:
                body["expressiveness"] = expressiveness_value
        return body

    def _video_v2_body(self, *, avatar_id: str, audio_asset_id: str) -> dict[str, Any]:
        is_vertical = self.aspect_ratio.strip() == "9:16"
        return {
            "video_inputs": [
                {
                    "character": {
                        "type": "avatar",
                        "avatar_id": avatar_id,
                        "avatar_style": "normal",
                    },
                    "voice": {
                        "type": "audio",
                        "audio_asset_id": audio_asset_id,
                    },
                }
            ],
            "dimension": {
                "width": 1080 if is_vertical else 1920,
                "height": 1920 if is_vertical else 1080,
            },
        }

    async def get_video(self, video_id: str) -> HeyGenVideoResult:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(f"{self.api_base_url}/v3/videos/{video_id}", headers=self.headers())
            if response.status_code in {404, 405}:
                response = await client.get(
                    f"{self.api_base_url}/v1/video_status.get",
                    headers=self.headers(),
                    params={"video_id": video_id},
                )
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
        poll_count = 0
        while time.monotonic() < deadline:
            last = await self.get_video(video_id)
            poll_count += 1
            logger.info(
                "HeyGen video poll: video_id=%s status=%s has_url=%s poll=%s",
                video_id,
                last.status,
                bool(last.video_url),
                poll_count,
            )
            if last.status in {"completed", "complete", "done", "success", "ready"} and last.video_url:
                logger.info("HeyGen video ready: video_id=%s url=%s", video_id, last.video_url)
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
    supported = item.get("supported_api_engines") or item.get("supported_engines") or []
    if not isinstance(supported, list):
        supported = []
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
        avatar_type=str(item.get("avatar_type") or item.get("type") or "").strip(),
        supported_engines=[str(engine).strip() for engine in supported if str(engine).strip()],
    )


def _is_private_avatar(item: dict[str, Any], *, trusted_private_endpoint: bool) -> bool:
    if item.get("is_public") is True or item.get("public") is True:
        return False
    ownership = str(
        item.get("ownership")
        or item.get("avatar_type")
        or item.get("type")
        or item.get("source")
        or ""
    ).strip().lower()
    if ownership:
        return ownership in {"private", "custom", "user", "personal", "digital_twin", "photo_avatar"}
    return trusted_private_endpoint


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
