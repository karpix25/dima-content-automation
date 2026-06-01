from content_automation.kie_image import _model_candidates


def test_gpt_image_2_model_candidates_include_text_to_image_alias():
    assert _model_candidates("gpt-image-2") == ["gpt-image-2", "gpt-image-2-text-to-image"]


def test_gpt_image_2_text_to_image_can_fall_back_to_marketplace_model():
    assert _model_candidates("gpt-image-2-text-to-image") == ["gpt-image-2-text-to-image", "gpt-image-2"]
