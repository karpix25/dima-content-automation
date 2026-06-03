from content_automation.prompts import build_short_scripts_prompt, build_youtube_script_prompt
from content_automation.script_length import vertical_word_budget, youtube_word_budget


def test_short_prompt_includes_vertical_word_budget():
    prompt = build_short_scripts_prompt(
        count=1,
        author_style="Direct operator voice.",
        word_budget=vertical_word_budget("60"),
    )

    assert "132-168 spoken words" in prompt
    assert "60s vertical avatar" in prompt


def test_youtube_prompt_includes_minutes_word_budget():
    prompt = build_youtube_script_prompt(
        author_style="Direct operator voice.",
        word_budget=youtube_word_budget(12),
    )

    assert "1656-1944 spoken words" in prompt
    assert "12 min horizontal YouTube" in prompt
    assert "Do not make it shorter" in prompt


def test_youtube_prompt_includes_exclusion_context():
    prompt = build_youtube_script_prompt(
        author_style="Direct operator voice.",
        exclusion_context="- Title: Old angle; Hook: Old hook; Fingerprint: ppc cash leak",
        word_budget=youtube_word_budget(10),
    )

    assert "Avoid repeating these prior title/hook/fingerprint patterns" in prompt
    assert "ppc cash leak" in prompt
