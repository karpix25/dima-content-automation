from content_automation.content_language import normalize_content_language, resolve_content_language
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
