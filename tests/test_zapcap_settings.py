from content_automation.zapcap_models import normalize_zapcap_setting_value, normalize_zapcap_settings


def test_zapcap_settings_defaults_to_hyperframes():
    settings = normalize_zapcap_settings({})

    assert settings.postprocess_provider == "hyperframes"
    assert settings.subtitles_enabled is True
    assert settings.broll_percent == 0


def test_zapcap_settings_clamps_numbers_and_colors():
    settings = normalize_zapcap_settings(
        {
            "postprocess_provider": "zapcap",
            "zapcap_broll_percent": "150",
            "zapcap_font_size": "999",
            "zapcap_top": "-10",
            "zapcap_font_color": "#12abEF",
            "zapcap_stroke_color": "black",
        }
    )

    assert settings.postprocess_provider == "zapcap"
    assert settings.broll_percent == 100
    assert settings.font_size == 70
    assert settings.top == 0
    assert settings.font_color == "#12ABEF"
    assert settings.stroke_color == "#000000"


def test_zapcap_setting_value_normalizes_ui_values():
    assert normalize_zapcap_setting_value("zapcap_subtitles_enabled", "0") == "0"
    assert normalize_zapcap_setting_value("zapcap_broll_percent", "42") == "42"
    assert normalize_zapcap_setting_value("postprocess_provider", "unknown") == "hyperframes"
