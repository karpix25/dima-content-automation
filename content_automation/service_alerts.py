from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import httpx

logger = logging.getLogger(__name__)


@dataclass
class ServiceAlertNotifier:
    telegram_bot_token: str
    chat_ids: tuple[str, ...]
    cooldown_seconds: int = 3600
    _last_sent_by_key: dict[str, datetime] = field(default_factory=dict)

    async def notify_kie_balance_if_needed(self, error: BaseException | str) -> bool:
        text = str(error)
        if not is_kie_balance_error(text):
            return False
        return await self.send_once(
            key="kie_balance",
            text=(
                "⚠️ KIE не может создавать сценарии: закончился баланс.\n\n"
                "Нужно пополнить KIE credits, после этого снова запусти написание сценариев."
            ),
        )

    async def send_once(self, *, key: str, text: str) -> bool:
        if not self.chat_ids:
            logger.warning("Service alert skipped: chat ids are not configured")
            return False
        if self._is_in_cooldown(key):
            logger.info("Service alert skipped: cooldown is active for %s", key)
            return False
        await self._send_to_chats(text)
        self._last_sent_by_key[key] = datetime.now(UTC)
        return True

    def _is_in_cooldown(self, key: str) -> bool:
        last_sent_at = self._last_sent_by_key.get(key)
        if last_sent_at is None:
            return False
        return datetime.now(UTC) < last_sent_at + timedelta(seconds=self.cooldown_seconds)

    async def _send_to_chats(self, text: str) -> None:
        async with httpx.AsyncClient(timeout=20) as client:
            for chat_id in self.chat_ids:
                response = await client.post(
                    f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage",
                    json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
                )
                response.raise_for_status()


def is_kie_balance_error(error_text: str) -> bool:
    lower = error_text.lower()
    return "credits insufficient" in lower or "current balance" in lower or ("402" in lower and "kie" in lower)
