from __future__ import annotations

from typing import Protocol

from .config import Settings
from .notebooklm_mcp import NotebookLMMCPClient
from .notebooklm_py import NotebookLMPyClient


class NotebookLMAskClient(Protocol):
    def ask(self, question: str, *, notebook_url: str | None = None, notebook_id: str | None = None):
        ...


def build_notebooklm_client(settings: Settings) -> NotebookLMAskClient:
    if settings.notebooklm_backend == "py":
        return NotebookLMPyClient(
            storage_path=settings.notebooklm_py_storage_path,
            timeout_seconds=settings.notebooklm_mcp_timeout_seconds,
        )
    return NotebookLMMCPClient(
        command=settings.notebooklm_mcp_command,
        timeout_seconds=settings.notebooklm_mcp_timeout_seconds,
    )
