from __future__ import annotations

from pathlib import Path

import httpx


def send_video_document_to_telegram(*, token: str, chat_id: str, video_path: Path, caption: str) -> str | None:
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN не задан")
    with video_path.open("rb") as video_file:
        response = httpx.post(
            f"https://api.telegram.org/bot{token}/sendDocument",
            data={"chat_id": chat_id, "caption": caption},
            files={"document": (video_path.name, video_file, "video/mp4")},
            timeout=180,
        )
    if response.status_code >= 400:
        raise RuntimeError(f"Telegram sendDocument error {response.status_code}: {response.text[:1000]}")
    payload = response.json()
    return str(payload.get("result", {}).get("message_id") or "") or None
