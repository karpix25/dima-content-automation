from content_automation.vizard_models import normalize_vizard_settings, vizard_settings_to_payload
from content_automation.vizard_youtube import extract_youtube_url


def test_vizard_payload_uses_youtube_format_ratio_and_length():
    settings = normalize_vizard_settings(
        {
            "vizard_lang": "en",
            "vizard_ratio_of_clip": "4",
            "vizard_prefer_length": "2,3",
            "vizard_max_clip_number": "7",
            "vizard_subtitle_switch": "1",
            "vizard_headline_switch": "0",
            "vizard_keywords": "price elasticity",
        }
    )

    payload = vizard_settings_to_payload(settings, video_url="https://www.youtube.com/watch?v=abc123")

    assert payload["videoType"] == 2
    assert payload["ratioOfClip"] == 4
    assert payload["preferLength"] == [2, 3]
    assert payload["maxClipNumber"] == 7
    assert payload["subtitleSwitch"] == 1
    assert payload["headlineSwitch"] == 0
    assert payload["keywords"] == "price elasticity"


def test_extract_youtube_url_from_text():
    assert extract_youtube_url("go https://youtu.be/abc123?si=x now") == "https://youtu.be/abc123?si=x"
