import pytest

from content_automation.service_alerts import ServiceAlertNotifier, is_kie_balance_error


def test_detects_kie_balance_error():
    assert is_kie_balance_error("KIE text response has no content: {'code': 402, 'msg': 'Credits insufficient'}")
    assert is_kie_balance_error("Your current balance isn’t enough to run this request.")
    assert not is_kie_balance_error("temporary timeout")


@pytest.mark.asyncio
async def test_service_alert_notifier_respects_cooldown():
    sent = []

    class FakeNotifier(ServiceAlertNotifier):
        async def _send_to_chats(self, text: str) -> None:
            sent.append(text)

    notifier = FakeNotifier(telegram_bot_token="token", chat_ids=("42",), cooldown_seconds=3600)

    assert await notifier.notify_kie_balance_if_needed("Credits insufficient")
    assert not await notifier.notify_kie_balance_if_needed("Credits insufficient")

    assert len(sent) == 1
