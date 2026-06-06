from content_automation.media_delivery import output_format_for_job


def test_output_format_for_avatar_jobs():
    assert output_format_for_job("avatar_horizontal") == "youtube"
    assert output_format_for_job("avatar_reels") == "reels"
    assert output_format_for_job("avatar_shorts") == "short"
