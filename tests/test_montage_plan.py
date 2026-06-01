from content_automation.montage_plan import build_montage_plan
from content_automation.storage import ScriptRecord


def test_build_montage_plan_has_scenes_and_word_cues():
    record = ScriptRecord(
        id=1,
        user_id="42",
        format="short",
        status="approved",
        title="Amazon PPC leak",
        angle="Cash flow angle",
        hook="Stop scaling this campaign",
        trigger="Hidden ACOS drag",
        voiceover="Your PPC can look profitable while it quietly kills cash flow.",
        cta="Audit before scaling.",
        why_it_works="Clear pain and action.",
        source_basis="NotebookLM notes.",
        raw={},
    )

    plan = build_montage_plan(record, duration_seconds=12, max_scenes=4)

    assert len(plan.scenes) == 4
    assert plan.scenes[0]["start"] == 0
    assert plan.scenes[-1]["end"] <= 12
    assert plan.word_cues[0]["start"] == 0
    assert plan.word_cues[-1]["end"] <= 12
