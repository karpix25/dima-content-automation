from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


class KieTextError(RuntimeError):
    pass


@dataclass(frozen=True)
class KieTextConfig:
    api_key: str | None
    base_url: str
    model: str
    timeout_seconds: int


class KieTextClient:
    def __init__(self, config: KieTextConfig) -> None:
        self.config = config

    def is_configured(self) -> bool:
        return bool(self.config.api_key)

    def complete(self, *, system: str, user: str) -> str:
        if not self.config.api_key:
            raise KieTextError("KIE_API_KEY не задан")
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.25,
        }
        errors: list[str] = []
        for endpoint in _chat_endpoints(self.config.model):
            try:
                with httpx.Client(timeout=self.config.timeout_seconds) as client:
                    response = client.post(f"{self.config.base_url}{endpoint}", headers=headers, json=payload)
                response.raise_for_status()
                return _extract_content(response.json())
            except Exception as exc:
                errors.append(f"{endpoint}: {exc}")
        raise KieTextError("; ".join(errors))


def _extract_content(data: dict[str, Any]) -> str:
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else choices[0].get("text")
        if isinstance(content, str) and content.strip():
            return content.strip()
    payload = data.get("data")
    if isinstance(payload, dict):
        for key in ("content", "text", "answer", "output"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    raise KieTextError(f"KIE text response has no content: {data}")


def _chat_endpoints(model: str) -> tuple[str, ...]:
    normalized = (model or "").strip().strip("/")
    endpoints: list[str] = []
    if normalized:
        endpoints.append(f"/{normalized}/v1/chat/completions")
    endpoints.extend(["/v1/chat/completions", "/api/v1/chat/completions"])
    return tuple(dict.fromkeys(endpoints))
