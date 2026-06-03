from content_automation.editorial import (
    apply_editorial_brief,
    build_editorial_briefs,
    editorial_briefs_prompt,
    script_editorial_summary,
)


def test_editorial_briefs_rotate_and_are_generic():
    briefs = build_editorial_briefs(start_index=0, count=3)

    assert [brief.content_format for brief in briefs] == ["money_leak", "teardown", "myth_vs_reality"]
    assert "Amazon" not in editorial_briefs_prompt(briefs).split("Editorial briefs to assign in order:", 1)[0]
    assert "adapt" in editorial_briefs_prompt(briefs)


def test_apply_editorial_brief_adds_metadata_without_overwriting_model_choice():
    brief = build_editorial_briefs(start_index=0, count=1)[0]
    payload = {"title": "Margin leak", "content_format": "case_study"}

    enriched = apply_editorial_brief(payload, brief)

    assert enriched["content_format"] == "case_study"
    assert enriched["content_pillar"] == "profit_economics"
    assert enriched["series_name"] == "Hidden Leaks"


def test_script_editorial_summary_is_human_readable():
    summary = script_editorial_summary(
        {
            "content_format_label": "Money Leak",
            "content_pillar_label": "Profit & economics",
            "proof_type_label": "Numbers",
            "emotion_angle_label": "Shock",
            "series_name": "Hidden Leaks",
        }
    )

    assert summary == "Money Leak · Profit & economics · Numbers · Shock · Hidden Leaks"
