from pathlib import Path
from types import SimpleNamespace

import pytest

from content_automation.infographic_delivery import generate_gold_card_with_kie, gold_card_prompt, render_five_second_video
from content_automation.storage import ScriptRecord


def test_generate_gold_card_with_kie_uses_prompt_and_output_path(tmp_path: Path):
    record = _record()
    client = FakeKieClient(configured=True)
    output_path = tmp_path / "card.png"

    generated = generate_gold_card_with_kie(record=record, path=output_path, kie_client=client)

    assert generated == output_path
    assert output_path.read_text() == "kie-card"
    assert "exact color #EBC97C" in client.prompts[0]
    assert "off-white/milky rounded rectangle block" in client.prompts[0]
    assert "Montserrat" in client.prompts[0]
    assert 'H1/top headline exact text: "Revenue is not profit"' in client.prompts[0]
    assert client.reference_paths == []


def test_generate_gold_card_with_kie_passes_reference_paths(tmp_path: Path):
    record = _record()
    client = FakeKieClient(configured=True)
    reference = tmp_path / "face.jpg"
    reference.write_text("face")

    generate_gold_card_with_kie(
        record=record,
        path=tmp_path / "card.png",
        kie_client=client,
        reference_paths=[reference],
    )

    assert client.reference_paths == [reference]
    assert "face reference image only" in client.prompts[0]
    assert "realistic cutout sticker of the author" in client.prompts[0]


def test_generate_gold_card_with_kie_passes_face_and_design_references(tmp_path: Path):
    client = FakeKieClient(configured=True)
    face = tmp_path / "face.jpg"
    design = tmp_path / "layout.png"
    face.write_text("face")
    design.write_text("design")

    generate_gold_card_with_kie(
        record=_record(),
        path=tmp_path / "card.png",
        kie_client=client,
        face_reference_paths=[face],
        design_reference_paths=[design],
    )

    assert client.reference_paths == [face, design]
    assert "author identity and face likeness" in client.prompts[0]
    assert "infographic design references as a style board" in client.prompts[0]
    assert "cleanest least text-heavy direction" in client.prompts[0]


def test_gold_card_prompt_limits_h1_h2_and_prevents_broken_words():
    record = _record(
        hook="If your Amazon margins are shrinking stop listening to agencies telling you to increase ad spend immediately",
        angle="This is an extremely long subtitle that should be reduced before it reaches the Kie design prompt",
    )

    prompt = gold_card_prompt(record)

    assert "H1 max 48 characters" in prompt
    assert "Target 52-68 visible words" in prompt
    assert "immediately" not in prompt
    assert "Kie design prompt" not in prompt
    assert "Final thought:" not in prompt


def test_gold_card_prompt_uses_hook_before_trigger_heuristic():
    record = _record(
        hook="If your Amazon margins are shrinking, stop listening to agencies.",
        voiceover="Your revenue can grow while your cash disappears.",
        trigger="Fix the bottleneck before scaling PPC ads.",
    )

    prompt = gold_card_prompt(record)

    assert 'H1/top headline exact text: "If your Amazon margins are shrinking, stop"' in prompt
    assert "exactly 5 expert points" in prompt
    assert "5-second video card designed to take 14-16 seconds to read" in prompt


def test_gold_card_prompt_uses_first_frame_text_before_hook():
    record = _record(raw={"first_frame_text": "CHECK THIS FEE"})

    prompt = gold_card_prompt(record)

    assert 'H1/top headline exact text: "CHECK THIS FEE"' in prompt
    assert "Revenue is not profit" not in prompt


def test_generate_gold_card_with_kie_uses_configured_cta(tmp_path: Path):
    client = FakeKieClient(configured=True)

    generate_gold_card_with_kie(record=_record(), path=tmp_path / "card.png", kie_client=client, cta_text="Join the Dima audit.")

    assert "Join the Dima audit." in client.prompts[0]


def test_generate_gold_card_with_kie_requires_api_key(tmp_path: Path):
    with pytest.raises(RuntimeError, match="KIE_API_KEY"):
        generate_gold_card_with_kie(record=_record(), path=tmp_path / "card.png", kie_client=FakeKieClient(configured=False))


def test_gold_card_prompt_includes_script_fields():
    prompt = gold_card_prompt(_record())

    assert 'H1/top headline exact text: "Revenue is not profit"' in prompt
    assert "Cash conversion" in prompt
    assert "Check contribution margin" in prompt
    assert "#EBC97C" in prompt


def test_gold_card_prompt_keeps_expert_specificity_from_bullets():
    record = _record(
        hook="If your Amazon margins are shrinking, stop listening to agencies.",
        trigger="Stop listening to agencies and fix the bottleneck using SQP.",
    )

    prompt = gold_card_prompt(
        _record(
            hook="If your Amazon margins are shrinking, stop listening to agencies.",
            trigger="Stop listening to agencies and fix the bottleneck using SQP.",
            source_basis=(
                "Decreasing profit margins despite high sales volume and operator burnout. "
                "First, put a hard cap on your daily PPC so it never exceeds your daily profit. "
                "Second, pull your Search Query Performance report and filter by Lost Keywords."
            ),
        )
    )

    assert 'H1/top headline exact text: "If your Amazon margins are shrinking, stop"' in prompt
    assert "High sales can hide a broken contribution margin" in prompt
    assert "Daily PPC caps protect cash before scale" in prompt
    assert "Lost Keywords show where profit is leaking" in prompt


def test_render_five_second_video_normalizes_kie_image_size(tmp_path: Path, monkeypatch):
    image_path = tmp_path / "odd.png"
    image_path.write_bytes(b"png")
    commands = []

    def fake_run(cmd, **kwargs):
        commands.append(cmd)
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr("content_automation.infographic_delivery.subprocess.run", fake_run)

    render_five_second_video(image_path=image_path, video_path=tmp_path / "out.mp4", audio_path=None)

    command = commands[0]
    assert "-vf" in command
    assert command[command.index("-vf") + 1] == (
        "scale=1080:1920:force_original_aspect_ratio=decrease,"
        "pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1"
    )
    assert "yuv420p" in command


class FakeKieClient:
    def __init__(self, *, configured: bool) -> None:
        self.configured = configured
        self.prompts: list[str] = []

    def is_configured(self) -> bool:
        return self.configured

    def generate_image(self, *, prompt: str, output_path: Path, reference_paths: list[Path] | None = None) -> Path:
        self.prompts.append(prompt)
        self.reference_paths = reference_paths or []
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("kie-card")
        return output_path


def _record(**overrides) -> ScriptRecord:
    values = {
        "title": "Margin trap",
        "hook": "Revenue is not profit",
        "angle": "Profit angle",
        "trigger": "Cash conversion",
        "voiceover": "Your revenue can grow while your cash disappears.",
        "cta": "Check contribution margin.",
        "why_it_works": "Sharp seller pain.",
        "source_basis": "NotebookLM notes.",
        "raw": {},
    }
    values.update(overrides)
    return ScriptRecord(
        id=1,
        user_id="42",
        format="short",
        status="approved",
        title=values["title"],
        angle=values["angle"],
        hook=values["hook"],
        trigger=values["trigger"],
        voiceover=values["voiceover"],
        cta=values["cta"],
        why_it_works=values["why_it_works"],
        source_basis=values["source_basis"],
        raw=values["raw"],
    )
