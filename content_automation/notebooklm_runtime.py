from __future__ import annotations

from typing import Protocol

from .config import Settings
from .notebooklm_fallback import NotebookLMFallbackClient
from .notebooklm_mcp import NotebookLMMCPClient
from .notebooklm_py import NotebookLMPyClient
from .notebooklm_storage import sync_playwright_storage_to_mcp


class NotebookLMAskClient(Protocol):
    def ask(self, question: str, *, notebook_url: str | None = None, notebook_id: str | None = None):
        ...


def build_notebooklm_client(settings: Settings) -> NotebookLMAskClient:
    if settings.notebooklm_backend == "py":
        py_storage_path = settings.notebooklm_py_storage_path
        return NotebookLMFallbackClient(
            primary=NotebookLMPyClient(
                storage_path=py_storage_path,
                timeout_seconds=settings.notebooklm_mcp_timeout_seconds,
            ),
            fallback=NotebookLMMCPClient(
                command=settings.notebooklm_mcp_command,
                timeout_seconds=settings.notebooklm_mcp_timeout_seconds,
            ),
            before_fallback=lambda: sync_playwright_storage_to_mcp(py_storage_path),
        )
    return NotebookLMMCPClient(
        command=settings.notebooklm_mcp_command,
        timeout_seconds=settings.notebooklm_mcp_timeout_seconds,
    )
