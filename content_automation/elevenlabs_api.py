from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


class ElevenLabsAPIError(RuntimeError):
    pass


@dataclass(frozen=True)
class ElevenLabsVoice:
    id: str
    name: str
    category: str | None
    preview_url: str | None
    raw: dict[str, Any]


class ElevenLabsAPIClient:
    def __init__(self, *, api_key: str | None, base_url: str = "https://api.elevenlabs.io"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def list_voices(self) -> list[ElevenLabsVoice]:
        if not self.api_key:
            raise ElevenLabsAPIError("ELEVENLABS_API_KEY не задан")

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self.base_url}/v1/voices",
                headers={"xi-api-key": self.api_key, "accept": "application/json"},
            )
        if response.status_code >= 400:
            raise ElevenLabsAPIError(f"ElevenLabs voices error {response.status_code}: {response.text[:1000]}")

        payload = response.json()
        raw_voices = payload.get("voices") if isinstance(payload, dict) else None
        if not isinstance(raw_voices, list):
            raise ElevenLabsAPIError("ElevenLabs вернул неожиданный формат списка голосов")

        voices: list[ElevenLabsVoice] = []
        for item in raw_voices:
            if not isinstance(item, dict):
                continue
            voice_id = str(item.get("voice_id") or item.get("id") or "").strip()
            name = str(item.get("name") or "").strip()
            if not voice_id or not name:
                continue
            voices.append(
                ElevenLabsVoice(
                    id=voice_id,
                    name=name,
                    category=str(item.get("category") or "").strip() or None,
                    preview_url=str(item.get("preview_url") or "").strip() or None,
                    raw=item,
                )
            )
        return voices
