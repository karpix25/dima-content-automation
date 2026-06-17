from types import SimpleNamespace

from content_automation.bot_format_actions import format_completion_message


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
