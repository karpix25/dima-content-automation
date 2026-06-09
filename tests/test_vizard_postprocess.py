from pathlib import Path
from types import SimpleNamespace

from content_automation import vizard_postprocess
from content_automation.media_assets import MediaAssetStore
from content_automation.storage import Storage
from content_automation.vizard_models import VizardClip
from content_automation.vizard_postprocess import apply_vizard_cover_frame, vizard_clip_to_record


def test_vizard_clip_to_record_uses_clip_title_and_transcript():
    clip = VizardClip(
        video_id="clip-1",
        video_url="https://example.test/clip.mp4",
        duration_ms=30000,
        title="Amazon PPC mistake",
        transcript="Stop wasting money on broad match.",
        viral_score="91",
        viral_reason="Strong pain point.",
        clip_editor_url="https://vizard.test/editor",
    )

    record = vizard_clip_to_record(user_id="42", clip=clip, index=1)

    assert record.format == "short"
    assert record.hook == "Amazon PPC mistake"
    assert record.voiceover == "Stop wasting money on broad match."
    assert record.raw["source"] == "vizard"


def test_apply_vizard_cover_frame_generates_and_applies_cover(tmp_path: Path, monkeypatch):
    storage = Storage(tmp_path / "db.sqlite3")
    asset_store = MediaAssetStore(tmp_path / "db.sqlite3")
    clip_path = tmp_path / "clip.mp4"
    clip_path.write_bytes(b"clip")
    settings = SimpleNamespace(post_heygen_cover_seconds=0.10)
    calls = {}

    def fake_generate_post_heygen_assets(**kwargs):
        calls["record"] = kwargs["record"]
        calls["broll_count"] = kwargs["broll_count"]
        calls["target_size"] = kwargs["target_size"]
        cover = tmp_path / "cover.png"
        cover.write_bytes(b"cover")
        return SimpleNamespace(cover_path=cover, broll_paths=[])

    def fake_apply_cover_frame(*, video_path, cover_path, output_path, cover_seconds, target_size):
        calls["cover"] = (video_path, cover_path, output_path, cover_seconds, target_size)
        output_path.write_bytes(b"out")
        return output_path

    monkeypatch.setattr(vizard_postprocess, "generate_post_heygen_assets", fake_generate_post_heygen_assets)
    monkeypatch.setattr(vizard_postprocess, "apply_cover_frame", fake_apply_cover_frame)
    monkeypatch.setattr(vizard_postprocess, "thumbnail_face_reference_paths", lambda **_: [])
    monkeypatch.setattr(vizard_postprocess, "selected_thumbnail_style_reference_paths", lambda **_: [])

    result = apply_vizard_cover_frame(
        storage=storage,
        settings=settings,
        asset_store=asset_store,
        kie_client=None,
        user_id="42",
        clip=VizardClip(
            video_id="clip-1",
            video_url="",
            duration_ms=None,
            title="Amazon ranking changed",
            transcript="Ranking changed this week.",
            viral_score="",
            viral_reason="",
            clip_editor_url="",
        ),
        clip_path=clip_path,
        output_dir=tmp_path,
        index=1,
        format="short",
        target_size=(1080, 1080),
    )

    assert result == tmp_path / "clip_cover.mp4"
    assert calls["record"].hook == "Amazon ranking changed"
    assert calls["broll_count"] == 0
    assert calls["cover"][4] == (1080, 1080)
    assert calls["target_size"] == (1080, 1080)
    assert calls["record"].format == "short"


def test_apply_vizard_cover_frame_defaults_to_vertical_size(tmp_path: Path, monkeypatch):
    storage = Storage(tmp_path / "db.sqlite3")
    asset_store = MediaAssetStore(tmp_path / "db.sqlite3")
    clip_path = tmp_path / "clip.mp4"
    clip_path.write_bytes(b"clip")
    settings = SimpleNamespace(post_heygen_cover_seconds=0.10)
    calls = {}

    def fake_generate_post_heygen_assets(**kwargs):
        calls.update(kwargs)
        cover = tmp_path / "cover.png"
        cover.write_bytes(b"cover")
        return SimpleNamespace(cover_path=cover, broll_paths=[])

    def fake_apply_cover_frame(**kwargs):
        calls["cover"] = kwargs
        kwargs["output_path"].write_bytes(b"out")
        return kwargs["output_path"]

    monkeypatch.setattr(vizard_postprocess, "generate_post_heygen_assets", fake_generate_post_heygen_assets)
    monkeypatch.setattr(vizard_postprocess, "apply_cover_frame", fake_apply_cover_frame)
    monkeypatch.setattr(vizard_postprocess, "thumbnail_face_reference_paths", lambda **_: [])
    monkeypatch.setattr(vizard_postprocess, "selected_thumbnail_style_reference_paths", lambda **_: [])

    apply_vizard_cover_frame(
        storage=storage,
        settings=settings,
        asset_store=asset_store,
        kie_client=None,
        user_id="42",
        clip=VizardClip("", "", None, "Title", "", "", "", ""),
        clip_path=clip_path,
        output_dir=tmp_path,
        index=1,
        format="short",
    )

    assert calls["cover"]["cover_seconds"] == 0.10
    assert calls["cover"]["target_size"] == (1080, 1920)


def test_apply_vizard_cover_frame_uses_horizontal_size_for_youtube(tmp_path: Path, monkeypatch):
    storage = Storage(tmp_path / "db.sqlite3")
    asset_store = MediaAssetStore(tmp_path / "db.sqlite3")
    clip_path = tmp_path / "clip.mp4"
    clip_path.write_bytes(b"clip")
    settings = SimpleNamespace(post_heygen_cover_seconds=0.10)
    calls = {}

    monkeypatch.setattr(
        vizard_postprocess,
        "generate_post_heygen_assets",
        lambda **_: SimpleNamespace(cover_path=tmp_path / "cover.png", broll_paths=[]),
    )
    (tmp_path / "cover.png").write_bytes(b"cover")

    def fake_apply_cover_frame(**kwargs):
        calls.update(kwargs)
        kwargs["output_path"].write_bytes(b"out")
        return kwargs["output_path"]

    monkeypatch.setattr(vizard_postprocess, "apply_cover_frame", fake_apply_cover_frame)
    monkeypatch.setattr(vizard_postprocess, "thumbnail_face_reference_paths", lambda **_: [])
    monkeypatch.setattr(vizard_postprocess, "selected_thumbnail_style_reference_paths", lambda **_: [])

    apply_vizard_cover_frame(
        storage=storage,
        settings=settings,
        asset_store=asset_store,
        kie_client=None,
        user_id="42",
        clip=VizardClip("", "", None, "Title", "", "", "", ""),
        clip_path=clip_path,
        output_dir=tmp_path,
        index=1,
        format="youtube",
    )

    assert calls["target_size"] == (1920, 1080)
