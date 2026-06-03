from pathlib import Path

from content_automation import post_heygen_video
from content_automation.post_heygen_video import _broll_starts, apply_cover_frame
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


def test_apply_cover_frame_overlays_until_cover_seconds(tmp_path: Path, monkeypatch):
    video = tmp_path / "video.mp4"
    cover = tmp_path / "cover.png"
    output = tmp_path / "out.mp4"
    video.write_bytes(b"video")
    cover.write_bytes(b"cover")
    seen = {}

    def fake_run(cmd, check, capture_output, text):
        seen["cmd"] = cmd
        output.write_bytes(b"out")
        return FakeProc()

    monkeypatch.setattr(post_heygen_video.subprocess, "run", fake_run)

    assert apply_cover_frame(video_path=video, cover_path=cover, output_path=output, cover_seconds=0.10) == output
    assert "enable='lt(t,0.100)'" in ";".join(seen["cmd"])


def test_generate_post_heygen_assets_prefers_kie_when_configured(tmp_path: Path):
    record = _record()
    client = FakeKieClient()

    assets = generate_post_heygen_assets(record=record, output_dir=tmp_path, broll_count=1, kie_client=client)

    assert assets.cover_path.read_text() == "kie"
    assert assets.broll_paths[0].read_text() == "kie"
    assert len(client.prompts) == 2


def test_generate_post_heygen_assets_passes_references_to_kie(tmp_path: Path):
    record = _record()
    client = FakeKieClient()
    reference = tmp_path / "style.jpg"
    reference.write_text("style")

    generate_post_heygen_assets(
        record=record,
        output_dir=tmp_path / "out",
        broll_count=1,
        kie_client=client,
        face_reference_paths=[reference],
    )

    assert client.reference_batches == [[reference], [reference]]
    assert "mandatory references" in client.prompts[0]
    assert "AUTHOR FACE" in client.prompts[0]
    assert "must match that face identity" in client.prompts[0]


def test_generate_post_heygen_assets_labels_face_and_style_references(tmp_path: Path):
    record = _record()
    client = FakeKieClient()
    face = tmp_path / "face.jpg"
    style = tmp_path / "style.jpg"
    face.write_text("face")
    style.write_text("style")

    generate_post_heygen_assets(
        record=record,
        output_dir=tmp_path / "out",
        broll_count=0,
        kie_client=client,
        face_reference_paths=[face],
        style_reference_paths=[style],
    )

    assert client.reference_batches == [[face, style]]
    assert "AUTHOR FACE references" in client.prompts[0]
    assert "STYLE ONLY references" in client.prompts[0]
    assert "Do not invent a different presenter" in client.prompts[0]


class FakeKieClient:
    def __init__(self) -> None:
        self.prompts: list[str] = []
        self.reference_batches: list[list[Path]] = []

    def is_configured(self) -> bool:
        return True

    def generate_image(self, *, prompt: str, output_path: Path, reference_paths: list[Path] | None = None) -> Path:
        self.prompts.append(prompt)
        self.reference_batches.append(reference_paths or [])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("kie")
        return output_path


class FakeProc:
    returncode = 0
    stderr = ""


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
