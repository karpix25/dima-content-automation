from __future__ import annotations

import pytest

from content_automation.notebooklm_auth_notifier import AuthNotificationConfig, NotebookLMAuthNotifier
from content_automation.notebooklm_health import NotebookLMHealthStatus


def _status(name: str) -> NotebookLMHealthStatus:
    return NotebookLMHealthStatus(
        ok=False,
        status=name,
        checked_at="2026-06-17T00:00:00+00:00",
        message="NotebookLM needs Google re-login.",
    )


@pytest.mark.asyncio
async def test_notifier_starts_browser_and_sends_auth_link():
    started_commands = []
    sent_messages = []

    async def start_runner(command: str, timeout_seconds: int):
        started_commands.append((command, timeout_seconds))
        return True, "started"

    class FakeNotifier(NotebookLMAuthNotifier):
        async def _send_to_chats(self, text: str) -> None:
            sent_messages.append(text)

    notifier = FakeNotifier(
        AuthNotificationConfig(
            telegram_bot_token="token",
            auth_url="http://server:6080/vnc.html",
            chat_ids=("42",),
            cooldown_seconds=3600,
            start_command="start-auth",
            start_timeout_seconds=9,
        ),
        start_runner=start_runner,
    )

    assert await notifier.notify_if_needed(_status("auth_expired"))

    assert started_commands == [("start-auth", 9)]
    assert "http://server:6080/vnc.html" in sent_messages[0]
    assert "NotebookLM" in sent_messages[0]


@pytest.mark.asyncio
async def test_notifier_skips_non_auth_status():
    sent_messages = []

    class FakeNotifier(NotebookLMAuthNotifier):
        async def _send_to_chats(self, text: str) -> None:
            sent_messages.append(text)

    notifier = FakeNotifier(
        AuthNotificationConfig(
            telegram_bot_token="token",
            auth_url="http://server:6080/vnc.html",
            chat_ids=("42",),
            cooldown_seconds=3600,
        )
    )

    assert not await notifier.notify_if_needed(_status("timeout"))

    assert sent_messages == []


@pytest.mark.asyncio
async def test_notifier_respects_cooldown():
    sent_messages = []

    class FakeNotifier(NotebookLMAuthNotifier):
        async def _send_to_chats(self, text: str) -> None:
            sent_messages.append(text)

    notifier = FakeNotifier(
        AuthNotificationConfig(
            telegram_bot_token="token",
            auth_url="http://server:6080/vnc.html",
            chat_ids=("42",),
            cooldown_seconds=3600,
        )
    )

    assert await notifier.notify_if_needed(_status("auth_or_page_unavailable"))
    assert not await notifier.notify_if_needed(_status("auth_or_page_unavailable"))

    assert len(sent_messages) == 1
