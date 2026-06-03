from pathlib import Path

from content_automation import final_video_variants
from content_automation.final_video_variants import build_final_video_variants
from content_automation.storage import Storage


class FakeOverlayResult:
    def __init__(self, output_path: Path):
        self.output_path = output_path


def test_final_video_variants_applies_youtube_and_instagram_overlays(tmp_path, monkeypatch):
    storage = Storage(tmp_path / "db.sqlite3")
    user_id = "42"
    source = tmp_path / "source.mp4"
    source.write_bytes(b"video")
    youtube_overlay = tmp_path / "youtube.png"
    instagram_overlay = tmp_path / "instagram.png"
    youtube_overlay.write_bytes(b"youtube")
    instagram_overlay.write_bytes(b"instagram")
    storage.set_setting(user_id, "youtube_overlay_path", str(youtube_overlay))
    storage.set_setting(user_id, "short_overlay_path", str(instagram_overlay))

    calls = []

    def fake_apply_overlay(*, video_path, overlay_path, output_path, start_percent):
        calls.append((video_path, overlay_path, output_path, start_percent))
        output_path.write_bytes(b"output")
        return FakeOverlayResult(output_path)

    monkeypatch.setattr(final_video_variants, "apply_overlay", fake_apply_overlay)

    variants = build_final_video_variants(
        storage=storage,
        user_id=user_id,
        source_path=source,
        output_dir=tmp_path,
        output_stem="clip",
    )

    assert [item.platform for item in variants] == ["youtube", "instagram"]
    assert calls[0][1] == youtube_overlay
    assert calls[1][1] == instagram_overlay
