from pathlib import Path

from content_automation.post_heygen_video import _broll_starts
from content_automation.storage import ScriptRecord
from content_automation.visual_assets import generate_post_heygen_assets


def test_generate_post_heygen_assets_creates_cover_and_broll(tmp_path: Path):
    record = _record()

    assets = generate_post_heygen_assets(record=record, output_dir=tmp_path, broll_count=2)

    assert assets.cover_path.exists()
    assert len(assets.broll_paths) == 2
    assert all(path.exists() for path in assets.broll_paths)


def test_broll_starts_fit_inside_video_duration():
    starts = _broll_starts(duration=20.0, count=3, broll_seconds=1.2)

    assert len(starts) == 3
    assert starts[0] >= 1.5
    assert starts[-1] + 1.2 <= 19.0


def test_generate_post_heygen_assets_prefers_kie_when_configured(tmp_path: Path):
    record = _record()
    client = FakeKieClient()

    assets = generate_post_heygen_assets(record=record, output_dir=tmp_path, broll_count=1, kie_client=client)

    assert assets.cover_path.read_text() == "kie"
    assert assets.broll_paths[0].read_text() == "kie"
    assert len(client.prompts) == 2


class FakeKieClient:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def is_configured(self) -> bool:
        return True

    def generate_image(self, *, prompt: str, output_path: Path) -> Path:
        self.prompts.append(prompt)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("kie")
        return output_path


def _record() -> ScriptRecord:
    return ScriptRecord(
        id=8,
        user_id="42",
        format="short",
        status="approved",
        title="Amazon PPC leak",
        angle="Cash flow angle",
        hook="Stop scaling this campaign",
        trigger="Hidden ACOS drag",
        voiceover="Your PPC can look profitable while it quietly kills cash flow.",
        cta="Audit contribution margin before scaling.",
        why_it_works="Clear pain and action.",
        source_basis="NotebookLM notes.",
        raw={},
    )
