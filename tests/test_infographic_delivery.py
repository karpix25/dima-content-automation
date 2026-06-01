from pathlib import Path

import pytest

from content_automation.infographic_delivery import generate_gold_card_with_kie, gold_card_prompt
from content_automation.storage import ScriptRecord


def test_generate_gold_card_with_kie_uses_prompt_and_output_path(tmp_path: Path):
    record = _record()
    client = FakeKieClient(configured=True)
    output_path = tmp_path / "card.png"

    generated = generate_gold_card_with_kie(record=record, path=output_path, kie_client=client)

    assert generated == output_path
    assert output_path.read_text() == "kie-card"
    assert "premium vertical 9:16" in client.prompts[0]
    assert "Revenue is not profit" in client.prompts[0]
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
    assert "face/style reference" in client.prompts[0]


def test_generate_gold_card_with_kie_uses_configured_cta(tmp_path: Path):
    client = FakeKieClient(configured=True)

    generate_gold_card_with_kie(record=_record(), path=tmp_path / "card.png", kie_client=client, cta_text="Join the Dima audit.")

    assert "Join the Dima audit." in client.prompts[0]


def test_generate_gold_card_with_kie_requires_api_key(tmp_path: Path):
    with pytest.raises(RuntimeError, match="KIE_API_KEY"):
        generate_gold_card_with_kie(record=_record(), path=tmp_path / "card.png", kie_client=FakeKieClient(configured=False))


def test_gold_card_prompt_includes_script_fields():
    prompt = gold_card_prompt(_record())

    assert "Revenue is not profit" in prompt
    assert "Cash conversion" in prompt
    assert "Check contribution margin" in prompt


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
