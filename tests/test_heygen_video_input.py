from content_automation.heygen_video_input import extract_heygen_video_id


def test_extract_heygen_video_id_from_plain_id():
    assert extract_heygen_video_id("48eb7ab7f2794dae9670277639759123") == "48eb7ab7f2794dae9670277639759123"


def test_extract_heygen_video_id_from_url():
    assert (
        extract_heygen_video_id("https://api.heygen.com/v3/videos/48eb7ab7f2794dae9670277639759123")
        == "48eb7ab7f2794dae9670277639759123"
    )


def test_extract_heygen_video_id_ignores_commands_and_normal_text():
    assert extract_heygen_video_id("/status") is None
    assert extract_heygen_video_id("обычный текст без id") is None

