from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

import httpx

from .notebooklm_health import NotebookLMHealthStatus

logger = logging.getLogger(__name__)

AUTH_STATUSES = {"auth_expired", "auth_or_page_unavailable"}


class AuthStartRunner(Protocol):
    async def __call__(self, command: str, timeout_seconds: int) -> tuple[bool, str]:
        ...


@dataclass(frozen=True)
class AuthNotificationConfig:
    telegram_bot_token: str
    auth_url: str | None
    chat_ids: tuple[str, ...]
    cooldown_seconds: int
    start_command: str | None = None
    start_timeout_seconds: int = 30


class NotebookLMAuthNotifier:
    def __init__(
        self,
        config: AuthNotificationConfig,
        *,
        start_runner: AuthStartRunner | None = None,
    ) -> None:
        self.config = config
        self.start_runner = start_runner or run_auth_start_command
        self._last_sent_at: datetime | None = None

    async def notify_if_needed(self, status: NotebookLMHealthStatus) -> bool:
        if status.ok or status.status not in AUTH_STATUSES:
            return False
        if not self.config.auth_url or not self.config.chat_ids:
            logger.warning("NotebookLM auth notification skipped: auth URL or chat ids are not configured")
            return False
        if self._is_in_cooldown():
            logger.info("NotebookLM auth notification skipped: cooldown is active")
            return False

        started, start_detail = await self._start_auth_browser()
        text = build_auth_message(self.config.auth_url, status, started=started, start_detail=start_detail)
        await self._send_to_chats(text)
        self._last_sent_at = datetime.now(UTC)
        return True

    def _is_in_cooldown(self) -> bool:
        if self._last_sent_at is None:
            return False
        return datetime.now(UTC) < self._last_sent_at + timedelta(seconds=self.config.cooldown_seconds)

    async def _start_auth_browser(self) -> tuple[bool, str]:
        command = self.config.start_command
        if not command:
            return False, "Auth browser start command is not configured."
        try:
            return await self.start_runner(command, self.config.start_timeout_seconds)
        except Exception as exc:
            logger.exception("NotebookLM auth browser start command failed")
            return False, str(exc)

    async def _send_to_chats(self, text: str) -> None:
        async with httpx.AsyncClient(timeout=20) as client:
            for chat_id in self.config.chat_ids:
                response = await client.post(
                    f"https://api.telegram.org/bot{self.config.telegram_bot_token}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": text,
                        "disable_web_page_preview": True,
                    },
                )
                response.raise_for_status()


async def run_auth_start_command(command: str, timeout_seconds: int) -> tuple[bool, str]:
    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    try:
        output, _ = await asyncio.wait_for(process.communicate(), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        process.kill()
        await process.communicate()
        return False, f"Start command timed out after {timeout_seconds}s."

    detail = output.decode("utf-8", errors="replace")[-1000:].strip()
    return process.returncode == 0, detail


def build_auth_message(
    auth_url: str,
    status: NotebookLMHealthStatus,
    *,
    started: bool,
    start_detail: str,
) -> str:
    start_line = "Браузер авторизации запущен." if started else "Браузер авторизации может требовать ручного запуска."
    detail = f"\nДеталь запуска: {start_detail}" if start_detail and not started else ""
    return (
        "⚠️ NotebookLM разлогинился.\n"
        f"{start_line}\n\n"
        f"Открой ссылку и войди в Google:\n{auth_url}\n\n"
        "После входа можно снова запускать план/темы в mini app."
        f"\n\nСтатус: {status.status}. {status.message}"
        f"{detail}"
    )
