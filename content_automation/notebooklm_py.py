from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class NotebookLMPyError(RuntimeError):
    pass


logger = logging.getLogger(__name__)

NOTEBOOK_URL_RE = re.compile(r"notebooklm\.google\.com/notebook/([^/?#]+)")
UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
DEFAULT_MCP_STORAGE_PATH = Path("/root/.local/share/notebooklm-mcp/browser_state/state.json")


@dataclass(frozen=True)
class NotebookLMPyAskResult:
    answer: str
    session_id: str | None = None
    raw: Any | None = None


class NotebookLMPyClient:
    def __init__(self, *, storage_path: Path | None = None, timeout_seconds: int = 240):
        self.storage_path = storage_path
        self.timeout_seconds = timeout_seconds

    def ask(self, question: str, *, notebook_url: str | None = None, notebook_id: str | None = None) -> NotebookLMPyAskResult:
        notebook_ref = notebook_id or extract_notebook_id(notebook_url)
        if not notebook_ref:
            raise NotebookLMPyError("NotebookLM notebook id or URL is required")
        return asyncio.run(self.ask_async(question, notebook_id=notebook_ref))

    async def ask_async(self, question: str, *, notebook_id: str) -> NotebookLMPyAskResult:
        try:
            from notebooklm import NotebookLMClient
        except ImportError as exc:
            raise NotebookLMPyError("notebooklm-py is not installed") from exc

        storage_path = self._resolve_storage_path()
        logger.info(
            "Calling NotebookLM Python API, timeout=%ss, storage=%s",
            self.timeout_seconds,
            storage_path or "default",
        )
        try:
            context = NotebookLMClient.from_storage(str(storage_path)) if storage_path else NotebookLMClient.from_storage()
            async with context as client:
                result = await asyncio.wait_for(client.chat.ask(notebook_id, question), timeout=self.timeout_seconds)
        except Exception as exc:
            raise NotebookLMPyError(str(exc)) from exc

        answer = str(getattr(result, "answer", "") or "").strip()
        if not answer:
            raise NotebookLMPyError(f"NotebookLM Python API returned an empty answer: {result!r}")
        return NotebookLMPyAskResult(answer=answer, raw=result)

    def _resolve_storage_path(self) -> Path | None:
        if self.storage_path:
            return self.storage_path
        if DEFAULT_MCP_STORAGE_PATH.exists():
            return DEFAULT_MCP_STORAGE_PATH
        return None


def extract_notebook_id(value: str | None) -> str | None:
    raw = (value or "").strip()
    if not raw:
        return None
    match = NOTEBOOK_URL_RE.search(raw)
    if match:
        return match.group(1)
    if UUID_RE.match(raw):
        return raw
    return raw
