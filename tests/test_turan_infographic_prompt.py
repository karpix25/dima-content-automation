from content_automation.storage import ScriptRecord
from content_automation.turan_infographic_prompt import build_turan_infographic_prompt


def test_turan_infographic_prompt_uses_original_design_with_dima_text():
    prompt = build_turan_infographic_prompt(
        record=_record(),
        bullets=["Fix SQP bottlenecks", "Reduce wasted PPC spend"],
        cta_text="Book a Dima audit",
        has_references=True,
    )

    assert "#EBC97C" in prompt
    assert "off-white/milky rounded rectangle block" in prompt
    assert "Montserrat" in prompt
    assert "realistic cutout sticker of the author" in prompt
    assert "bottom 22% of the 9:16 frame" in prompt
    assert "right 16% of the frame" in prompt
    assert "CTA window above the bottom safe zone" in prompt
    assert "Fix SQP bottlenecks" in prompt
    assert "Book a Dima audit" in prompt
    assert "тендеры" not in prompt.lower()


def _record() -> ScriptRecord:
    return ScriptRecord(
        id=1,
        user_id="42",
        format="short",
        status="approved",
        title="Margin trap",
        angle="Profit angle",
        hook="Revenue is not profit",
        trigger="Cash conversion",
        voiceover="Your revenue can grow while your cash disappears.",
        cta="Check contribution margin.",
        why_it_works="Sharp seller pain.",
        source_basis="NotebookLM notes.",
        raw={},
    )
