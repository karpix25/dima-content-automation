from __future__ import annotations

from types import SimpleNamespace

from content_automation.notebooklm_fallback import NotebookLMFallbackClient


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
