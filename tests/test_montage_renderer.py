from pathlib import Path

from content_automation.montage_renderer import _command
from content_automation.storage import ScriptRecord


def test_hyperframes_command_uses_youtube_layout_for_horizontal():
    command = _command(
        "hyperframes",
        record=_record(format="youtube"),
        video_path=Path("source.mp4"),
        scene_plan_path=Path("scenes.json"),
        word_cues_path=Path("words.json"),
        output_path=Path("out.mp4"),
    )

    assert command[-2:] == ["--layout", "horizontal_youtube"]


def _record(*, format: str) -> ScriptRecord:
    return ScriptRecord(
        id=1,
        user_id="42",
        format=format,
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
