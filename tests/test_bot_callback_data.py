from content_automation.bot_callback_data import parse_script_callback_data


def test_parse_script_callback_with_flow():
    parsed = parse_script_callback_data("script:approve:42:review")

    assert parsed is not None
    assert parsed.action == "approve"
    assert parsed.script_id == 42
    assert parsed.flow == "review"


def test_parse_script_callback_without_flow_defaults_to_review():
    parsed = parse_script_callback_data("script:reject:42")

    assert parsed is not None
    assert parsed.action == "reject"
    assert parsed.script_id == 42
    assert parsed.flow == "review"


def test_parse_script_callback_rejects_invalid_id():
    assert parse_script_callback_data("script:approve:not-a-number:review") is None
