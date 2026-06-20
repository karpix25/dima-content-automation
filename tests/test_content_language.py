from content_automation.content_language import normalize_content_language, resolve_content_language, should_reject_cyrillic_scripts
from content_automation.settings_service import normalize_text_setting


def test_normalize_content_language_accepts_expected_values_and_aliases():
    assert normalize_content_language("en") == "en"
    assert normalize_content_language("Russian") == "ru"
    assert normalize_content_language("source") == "auto"
    assert normalize_content_language("bad-value") == "auto"


def test_settings_service_normalizes_content_language():
    assert normalize_text_setting("content_language", "RU") == "ru"
    assert normalize_text_setting("content_language", "bad-value") == "auto"


def test_resolve_content_language_detects_auto_from_text():
    assert resolve_content_language("auto", "Привет, это русский текст") == "ru"
    assert resolve_content_language("auto", "This is English text") == "en"
    assert resolve_content_language("en", "Привет") == "en"


def test_cyrillic_scripts_are_rejected_only_for_english_projects():
    assert should_reject_cyrillic_scripts("en") is True
    assert should_reject_cyrillic_scripts("ru") is False
    assert should_reject_cyrillic_scripts("auto") is False
