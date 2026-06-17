from __future__ import annotations

from types import SimpleNamespace

import pytest

from content_automation.config import normalize_notebooklm_mcp_command
from content_automation.notebooklm_health import check_notebooklm_health, classify_notebooklm_error


def test_notebooklm_mcp_default_is_pinned():
    assert normalize_notebooklm_mcp_command(None) == "npx --yes notebooklm-mcp@2.0.0"
    assert normalize_notebooklm_mcp_command("npx --yes notebooklm-mcp@latest") == "npx --yes notebooklm-mcp@2.0.0"


def test_classify_notebooklm_auth_error():
    status, message = classify_notebooklm_error(
        "Authentication expired or invalid. Redirected to: https://accounts.google.com/"
    )

    assert status == "auth_expired"
    assert "re-login" in message


@pytest.mark.asyncio
async def test_notebooklm_health_check_success():
    class FakeNotebookLM:
        def ask(self, question, *, notebook_url=None, notebook_id=None):
            assert question.startswith("Reply with exactly")
            assert notebook_url == "https://notebooklm.google.com/notebook/notebook-1"
            return SimpleNamespace(answer='{"ok": true}')

    status = await check_notebooklm_health(FakeNotebookLM(), notebook_ref="notebook-1")

    assert status.ok
    assert status.status == "ok"


@pytest.mark.asyncio
async def test_notebooklm_health_check_auth_failure():
    class FakeNotebookLM:
        def ask(self, question, *, notebook_url=None, notebook_id=None):
            raise RuntimeError("Redirected to https://accounts.google.com/")

    status = await check_notebooklm_health(FakeNotebookLM(), notebook_ref="notebook-1")

    assert not status.ok
    assert status.status == "auth_expired"
