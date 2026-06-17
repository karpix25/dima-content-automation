from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from .notebooklm_mcp import notebook_ref_to_url
from .notebooklm_runtime import NotebookLMAskClient

logger = logging.getLogger(__name__)

KEEPALIVE_PROMPT = 'Reply with exactly this JSON and nothing else: {"ok": true}'


@dataclass(frozen=True)
class NotebookLMHealthStatus:
    ok: bool
    status: str
    checked_at: str
    message: str
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def classify_notebooklm_error(error: BaseException | str) -> tuple[str, str]:
    text = str(error)
    lower = text.lower()
    if "accounts.google.com" in lower or "authentication expired" in lower or "re-authenticate" in lower:
        return "auth_expired", "NotebookLM needs Google re-login."
    if "could not find notebooklm chat input" in lower or "notebook page has loaded" in lower:
        return "auth_or_page_unavailable", "NotebookLM page did not open into the chat."
    if "executable doesn't exist" in lower or "playwright was just updated" in lower:
        return "browser_runtime_error", "NotebookLM browser runtime is missing or mismatched."
    if "timed out" in lower:
        return "timeout", "NotebookLM did not answer before timeout."
    return "error", "NotebookLM check failed."


async def check_notebooklm_health(
    client: NotebookLMAskClient,
    *,
    notebook_ref: str | None,
) -> NotebookLMHealthStatus:
    checked_at = _now()
    if not notebook_ref:
        return NotebookLMHealthStatus(
            ok=False,
            status="not_configured",
            checked_at=checked_at,
            message="NotebookLM notebook id is not configured.",
        )
    try:
        await asyncio.to_thread(client.ask, KEEPALIVE_PROMPT, notebook_url=notebook_ref_to_url(notebook_ref))
    except Exception as exc:
        status, message = classify_notebooklm_error(exc)
        logger.warning("NotebookLM health check failed: %s: %s", status, exc)
        return NotebookLMHealthStatus(
            ok=False,
            status=status,
            checked_at=checked_at,
            message=message,
            detail=str(exc)[-1000:],
        )
    return NotebookLMHealthStatus(
        ok=True,
        status="ok",
        checked_at=checked_at,
        message="NotebookLM answered keepalive.",
    )


class NotebookLMKeepAlive:
    def __init__(
        self,
        client: NotebookLMAskClient,
        *,
        notebook_ref: str | None,
        enabled: bool,
        interval_seconds: int,
        startup_delay_seconds: int,
    ) -> None:
        self.client = client
        self.notebook_ref = notebook_ref
        self.enabled = enabled and bool(notebook_ref)
        self.interval_seconds = interval_seconds
        self.startup_delay_seconds = startup_delay_seconds
        self.last_status: NotebookLMHealthStatus | None = None
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if not self.enabled or self._task:
            return
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if not self._task:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def run_once(self) -> NotebookLMHealthStatus:
        self.last_status = await check_notebooklm_health(self.client, notebook_ref=self.notebook_ref)
        return self.last_status

    async def _loop(self) -> None:
        if self.startup_delay_seconds:
            await asyncio.sleep(self.startup_delay_seconds)
        while True:
            try:
                await self.run_once()
            except Exception:
                logger.exception("Unexpected NotebookLM keepalive failure")
            await asyncio.sleep(self.interval_seconds)


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")
