from pathlib import Path

from content_automation import final_video_variants
from content_automation.final_video_variants import build_final_video_variants
from content_automation.overlay_catalog import add_overlay_path
from content_automation.storage import Storage


class FakeOverlayResult:
    def __init__(self, output_path: Path):
        self.output_path = output_path


def test_final_video_variants_applies_youtube_shorts_and_reels_overlays(tmp_path, monkeypatch):
    storage = Storage(tmp_path / "db.sqlite3")
    user_id = "42"
    source = tmp_path / "source.mp4"
    source.write_bytes(b"video")
    youtube_overlay = tmp_path / "youtube.png"
    shorts_overlay = tmp_path / "shorts.png"
    reels_overlay = tmp_path / "reels.png"
    youtube_overlay.write_bytes(b"youtube")
    shorts_overlay.write_bytes(b"shorts")
    reels_overlay.write_bytes(b"reels")
    storage.set_setting(user_id, "youtube_overlay_path", str(youtube_overlay))
    storage.set_setting(user_id, "shorts_overlay_path", str(shorts_overlay))
    storage.set_setting(user_id, "reels_overlay_path", str(reels_overlay))

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

    assert [item.platform for item in variants] == ["youtube", "shorts", "reels"]
    assert calls[0][1] == youtube_overlay
    assert calls[1][1] == shorts_overlay
    assert calls[2][1] == reels_overlay


def test_final_video_variants_uses_legacy_vertical_overlay_as_fallback(tmp_path, monkeypatch):
    storage = Storage(tmp_path / "db.sqlite3")
    user_id = "42"
    source = tmp_path / "source.mp4"
    source.write_bytes(b"video")
    legacy_overlay = tmp_path / "legacy.png"
    legacy_overlay.write_bytes(b"legacy")
    storage.set_setting(user_id, "short_overlay_path", str(legacy_overlay))

    calls = []

    def fake_apply_overlay(*, video_path, overlay_path, output_path, start_percent):
        calls.append(overlay_path)
        output_path.write_bytes(b"output")
        return FakeOverlayResult(output_path)

    monkeypatch.setattr(final_video_variants, "apply_overlay", fake_apply_overlay)

    variants = build_final_video_variants(
        storage=storage,
        user_id=user_id,
        source_path=source,
        output_dir=tmp_path,
        output_stem="clip",
        platforms=("shorts", "reels"),
    )

    assert [item.platform for item in variants] == ["shorts", "reels"]
    assert calls == [legacy_overlay, legacy_overlay]


def test_final_video_variants_uses_multi_overlay_pool(tmp_path, monkeypatch):
    storage = Storage(tmp_path / "db.sqlite3")
    user_id = "42"
    source = tmp_path / "source.mp4"
    source.write_bytes(b"video")
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    add_overlay_path(storage, user_id, "shorts", first)
    add_overlay_path(storage, user_id, "shorts", second)
    calls = []

    def fake_apply_overlay(*, video_path, overlay_path, output_path, start_percent):
        calls.append(overlay_path)
        output_path.write_bytes(b"output")
        return FakeOverlayResult(output_path)

    monkeypatch.setattr(final_video_variants, "apply_overlay", fake_apply_overlay)

    variants = build_final_video_variants(
        storage=storage,
        user_id=user_id,
        source_path=source,
        output_dir=tmp_path,
        output_stem="clip",
        platforms=("shorts",),
    )

    assert [item.platform for item in variants] == ["shorts"]
    assert calls[0] in {first, second}
