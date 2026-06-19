from types import SimpleNamespace
import asyncio

from content_automation import bot_format_actions
from content_automation.bot_format_actions import BotFormatDeps, format_completion_message, run_format_output_job


def test_format_completion_message_includes_failure_reason():
    message = format_completion_message(
        script_id=1,
        job=SimpleNamespace(status="failed", error="HeyGen avatar для vertical не выбран", output_text=""),
    )

    assert "не создан" in message
    assert "HeyGen avatar для vertical не выбран" in message


def test_format_completion_message_includes_delivery_details():
    message = format_completion_message(
        script_id=2,
        job=SimpleNamespace(status="delivered", error=None, output_text="✅ Avatar формат создан\nФайл: /tmp/out.mp4"),
    )

    assert "готов" in message
    assert "Файл: /tmp/out.mp4" in message


def test_run_format_output_job_passes_actor_user_id(monkeypatch):
    seen = {}
    sent = []

    def fake_create_and_deliver_format_job(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(status="delivered", error=None, output_text="ok")

    async def fake_send_to_chat_thread(*args, **kwargs):
        sent.append((args, kwargs))

    monkeypatch.setattr(bot_format_actions, "create_and_deliver_format_job", fake_create_and_deliver_format_job)
    deps = BotFormatDeps(
        storage=object(),
        asset_store=object(),
        settings=object(),
        logger=SimpleNamespace(exception=lambda *args, **kwargs: None),
        send_to_chat_thread=fake_send_to_chat_thread,
        format_output_keyboard=lambda *_args, **_kwargs: None,
    )

    asyncio.run(
        run_format_output_job(
            chat_id=10,
            thread_id=None,
            user_id="42",
            actor_user_id="99",
            script_id=7,
            format_key="infographic_reels",
            deps=deps,
        )
    )

    assert seen["user_id"] == "42"
    assert seen["delivery_actor_user_id"] == "99"
    assert sent
