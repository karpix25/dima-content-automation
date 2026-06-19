from pathlib import Path

from content_automation.bot_approved_formats import (
    approved_script_details,
    approved_scripts_keyboard,
    approved_scripts_message,
    list_format_ready_scripts,
    parse_approved_format_callback,
)
from content_automation.bot_keyboards import build_format_output_keyboard, build_main_keyboard
from content_automation.storage import Storage


def test_parse_approved_format_callback():
    assert parse_approved_format_callback("approved:list").action == "list"
    parsed = parse_approved_format_callback("approved:show:42")
    assert parsed.action == "show"
    assert parsed.script_id == 42
    assert parse_approved_format_callback("approved:show:nope") is None


def test_list_format_ready_scripts_includes_used_scripts(tmp_path: Path):
    storage = Storage(tmp_path / "bot.sqlite3")
    approved = _add_script(storage, "42", "approved", title="Approved script")
    used = _add_script(storage, "42", "used_for_video", title="Used script")
    _add_script(storage, "42", "pending", title="Pending script")

    records = list_format_ready_scripts(storage, "42")

    assert [record.id for record in records] == [used.id, approved.id]


def test_approved_scripts_message_and_keyboard(tmp_path: Path):
    storage = Storage(tmp_path / "bot.sqlite3")
    record = _add_script(storage, "42", "approved", title="Amazon margin trap")

    message = approved_scripts_message([record])
    keyboard = approved_scripts_keyboard([record])
    details = approved_script_details(record)

    assert "#1" in message
    assert "Amazon margin trap" in details
    assert keyboard.inline_keyboard[0][0].callback_data == "approved:show:1"


def test_main_keyboard_contains_ready_scripts_button():
    keyboard = build_main_keyboard()
    buttons = [button.text for row in keyboard.inline_keyboard for button in row]

    assert "Готовые сценарии → форматы" in buttons


def test_format_keyboard_strikes_used_format():
    keyboard = build_format_output_keyboard(8, used_format_keys={"avatar_reels"})

    assert keyboard.inline_keyboard[0][0].text.startswith("✓")
    assert "\u0336" in keyboard.inline_keyboard[0][0].text
    assert keyboard.inline_keyboard[0][1].text == "Инфографика"


def test_format_keyboard_strikes_all_outputs_when_all_was_used():
    keyboard = build_format_output_keyboard(8, used_format_keys={"all"})
    buttons = [button.text for row in keyboard.inline_keyboard for button in row]

    assert any("R\u0336" in text for text in buttons)
    assert any("В\u0336" in text for text in buttons)


def _add_script(storage: Storage, user_id: str, status: str, *, title: str):
    record = storage.add_script(
        user_id,
        "short",
        {
            "title": title,
            "hook": "Hook",
            "voiceover": "Voiceover text for the script.",
        },
    )
    return storage.update_script_status(user_id, record.id, status)
