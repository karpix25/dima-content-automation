from content_automation.montage_plan import build_montage_plan
from content_automation.storage import ScriptRecord


def test_build_montage_plan_uses_transcript_word_timings():
    record = ScriptRecord(
        id=7,
        user_id="42",
        format="short",
        status="approved",
        title="Margin trap",
        angle="Amazon fee angle",
        hook="Amazon fees eat profit",
        trigger="FBA tier changes",
        voiceover="Amazon fees eat profit when FBA tier changes. Check your box size.",
        cta="Audit the package.",
        why_it_works="Concrete seller pain.",
        source_basis="NotebookLM notes.",
        raw={},
    )
    transcript_words = [
        {"word": "intro", "start": 0.1, "end": 0.3},
        {"word": "amazon", "start": 1.2, "end": 1.5},
        {"word": "fees", "start": 1.5, "end": 1.7},
        {"word": "eat", "start": 1.7, "end": 1.9},
        {"word": "profit", "start": 1.9, "end": 2.2},
        {"word": "when", "start": 2.2, "end": 2.4},
        {"word": "fba", "start": 4.0, "end": 4.2},
        {"word": "tier", "start": 4.2, "end": 4.5},
        {"word": "changes", "start": 4.5, "end": 4.9},
    ]

    plan = build_montage_plan(
        record,
        duration_seconds=12,
        max_scenes=3,
        transcript_words=transcript_words,
    )

    assert plan.scenes[0]["start"] == 1.2
    assert plan.scenes[1]["start"] == 4.0
    assert plan.word_cues[0]["start"] == 0.1
