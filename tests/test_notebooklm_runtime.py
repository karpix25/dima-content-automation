from __future__ import annotations

from types import SimpleNamespace

from content_automation.notebooklm_fallback import NotebookLMFallbackClient
from content_automation.notebooklm_storage import sync_playwright_storage_to_mcp


def test_notebooklm_fallback_client_uses_fallback_after_primary_error():
    calls = []

    class Primary:
        def ask(self, question, *, notebook_url=None, notebook_id=None):
            calls.append(("primary", question, notebook_url, notebook_id))
            raise RuntimeError("No parseable chunks in streaming chat response")

    class Fallback:
        def ask(self, question, *, notebook_url=None, notebook_id=None):
            calls.append(("fallback", question, notebook_url, notebook_id))
            return SimpleNamespace(answer='{"plan":[]}')

    result = NotebookLMFallbackClient(primary=Primary(), fallback=Fallback()).ask(
        "prompt",
        notebook_url="https://notebooklm.google.com/notebook/abc",
    )

    assert result.answer == '{"plan":[]}'
    assert calls == [
        ("primary", "prompt", "https://notebooklm.google.com/notebook/abc", None),
        ("fallback", "prompt", "https://notebooklm.google.com/notebook/abc", None),
    ]


def test_notebooklm_fallback_runs_hook_before_fallback():
    calls = []

    class Primary:
        def ask(self, question, *, notebook_url=None, notebook_id=None):
            calls.append("primary")
            raise RuntimeError("broken")

    class Fallback:
        def ask(self, question, *, notebook_url=None, notebook_id=None):
            calls.append("fallback")
            return SimpleNamespace(answer="ok")

    result = NotebookLMFallbackClient(
        primary=Primary(),
        fallback=Fallback(),
        before_fallback=lambda: calls.append("hook"),
    ).ask("prompt")

    assert result.answer == "ok"
    assert calls == ["primary", "hook", "fallback"]


def test_sync_playwright_storage_to_mcp_copies_state(tmp_path):
    source = tmp_path / "storage_state.json"
    destination = tmp_path / "browser_state" / "state.json"
    source.write_text('{"cookies":[]}', encoding="utf-8")

    assert sync_playwright_storage_to_mcp(source, destination_path=destination)
    assert destination.read_text(encoding="utf-8") == '{"cookies":[]}'
    assert oct(destination.stat().st_mode & 0o777) == "0o600"
