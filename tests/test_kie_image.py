from pathlib import Path

from content_automation.kie_image import KieImageClient, _model_candidates


def test_gpt_image_2_model_candidates_include_text_to_image_alias():
    assert _model_candidates("gpt-image-2") == ["gpt-image-2", "gpt-image-2-text-to-image"]


def test_gpt_image_2_text_to_image_can_fall_back_to_marketplace_model():
    assert _model_candidates("gpt-image-2-text-to-image") == ["gpt-image-2-text-to-image", "gpt-image-2"]


def test_reference_generation_uses_image_to_image_model_first():
    assert _model_candidates("gpt-image-2", has_references=True) == ["gpt-image-2-image-to-image", "gpt-image-2"]


def test_upload_references_skips_missing_paths():
    client = KieImageClient(config=_config())

    assert client._upload_references([Path("/missing/reference.jpg")]) == []


def _config():
    return type(
        "Config",
        (),
        {
            "api_key": "key",
            "base_url": "https://api.kie.ai",
            "upload_base_url": "https://kieai.redpandaai.co",
            "model": "gpt-image-2",
            "aspect_ratio": "9:16",
            "resolution": "1K",
            "poll_timeout_seconds": 1,
            "poll_interval_seconds": 1,
            "create_task_max_attempts": 1,
            "create_task_retry_delay_seconds": 1,
        },
    )()
