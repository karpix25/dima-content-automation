from types import SimpleNamespace

from content_automation.vizard_bot import build_vizard_kie_client, vizard_platforms_for_size, vizard_target_size_for_clip
from content_automation.vizard_models import normalize_vizard_settings, vizard_settings_to_payload
from content_automation.vizard_project import extract_vizard_project_id
from content_automation.vizard_youtube import extract_youtube_url
from content_automation.video_geometry import vizard_platforms_for_ratio


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


def test_extract_vizard_project_id_from_plain_id():
    assert extract_vizard_project_id("/vizard 31375459") == "31375459"


def test_extract_vizard_project_id_from_project_url():
    assert extract_vizard_project_id("https://app.vizard.ai/project/31375459/editor") == "31375459"


def test_extract_vizard_project_id_from_query_url():
    assert extract_vizard_project_id("https://app.vizard.ai/editor?projectId=31375459") == "31375459"


def test_vizard_toggles_default_to_off():
    settings = normalize_vizard_settings({})

    assert settings.subtitle_switch is False
    assert settings.headline_switch is False
    assert settings.emoji_switch is False
    assert settings.highlight_switch is False
    assert settings.auto_broll_switch is False
    assert settings.remove_silence_switch is False


def test_vizard_platforms_follow_ratio():
    assert vizard_platforms_for_ratio(4) == ("youtube",)
    assert vizard_platforms_for_ratio(1) == ("shorts", "reels")


def test_vizard_platforms_follow_downloaded_clip_size():
    assert vizard_platforms_for_size((1920, 1080)) == ("youtube",)
    assert vizard_platforms_for_size((1080, 1920)) == ("shorts", "reels")
    assert vizard_platforms_for_size((1080, 1080)) == ("shorts", "reels")


def test_vizard_target_size_does_not_keep_ambiguous_square_clip():
    assert vizard_target_size_for_clip((1080, 1080), 4) == (1920, 1080)
    assert vizard_target_size_for_clip((1080, 1080), 1) == (1080, 1920)
    assert vizard_target_size_for_clip((1920, 1080), 1) == (1920, 1080)


def test_build_vizard_kie_client_uses_current_config_field_names():
    client = build_vizard_kie_client(
        SimpleNamespace(
            kie_api_key="key",
            kie_base_url="https://api.example.test",
            kie_upload_base_url="https://upload.example.test",
            kie_image_model="gpt-image-2",
            kie_image_aspect_ratio="9:16",
            kie_image_resolution="1K",
            kie_poll_timeout_seconds=30,
            kie_poll_interval_seconds=2,
            kie_create_task_max_attempts=4,
            kie_create_task_retry_delay_seconds=3,
        )
    )

    assert client.config.create_task_max_attempts == 4
    assert client.config.create_task_retry_delay_seconds == 3
