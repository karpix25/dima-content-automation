from __future__ import annotations

import sys
import types
from types import SimpleNamespace

import pytest

from content_automation import notebooklm_py
from content_automation.notebooklm_py import NotebookLMPyClient, is_retriable_notebooklm_py_error


def test_streaming_empty_response_error_is_retriable():
    assert is_retriable_notebooklm_py_error(
        "No parseable chunks in streaming chat response (6 lines scanned). "
        "The response was empty or the API wire format may have changed."
    )


@pytest.mark.asyncio
async def test_notebooklm_py_retries_empty_streaming_response(monkeypatch):
    calls = {"count": 0}

    class FakeChat:
        async def ask(self, notebook_id: str, question: str):
            calls["count"] += 1
            if calls["count"] == 1:
                raise RuntimeError("No parseable chunks in streaming chat response (6 lines scanned).")
            return SimpleNamespace(answer='{"scripts": []}')

    class FakeContext:
        async def __aenter__(self):
            return SimpleNamespace(chat=FakeChat())

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeNotebookLMClient:
        @staticmethod
        def from_storage(*args):
            return FakeContext()

    async def fake_sleep(seconds: int) -> None:
        return None

    monkeypatch.setitem(sys.modules, "notebooklm", types.SimpleNamespace(NotebookLMClient=FakeNotebookLMClient))
    monkeypatch.setattr(notebooklm_py.asyncio, "sleep", fake_sleep)

    result = await NotebookLMPyClient(timeout_seconds=1).ask_async("prompt", notebook_id="notebook")

    assert result.answer == '{"scripts": []}'
    assert calls["count"] == 2
