from pathlib import Path

from content_automation.delivered_video_cleanup import cleanup_delivered_video_files


def test_cleanup_delivered_video_files_removes_related_mp4s(tmp_path: Path):
    final_path = tmp_path / "hyperframes_8_cover.mp4"
    source_path = tmp_path / "miniapp_heygen_8_reels.mp4"
    montage_dir = tmp_path / "miniapp_montage" / "8"
    montage_path = montage_dir / "hyperframes_8.mp4"
    image_path = tmp_path / "miniapp_visual_assets" / "8" / "cover_8.png"
    for path in (final_path, source_path, montage_path, image_path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"file")

    removed = cleanup_delivered_video_files(root=tmp_path, final_path=final_path, record_id=8, enabled=True)

    assert final_path in removed
    assert source_path in removed
    assert montage_path in removed
    assert not final_path.exists()
    assert not source_path.exists()
    assert not montage_path.exists()
    assert image_path.exists()


def test_cleanup_delivered_video_files_keeps_files_outside_output_root(tmp_path: Path):
    output_root = tmp_path / "outputs"
    output_root.mkdir()
    outside_path = tmp_path / "outside.mp4"
    outside_path.write_bytes(b"video")

    removed = cleanup_delivered_video_files(
        root=output_root,
        final_path=outside_path,
        record_id=8,
        enabled=True,
    )

    assert removed == []
    assert outside_path.exists()


def test_cleanup_delivered_video_files_can_be_disabled(tmp_path: Path):
    final_path = tmp_path / "hyperframes_8_cover.mp4"
    final_path.write_bytes(b"video")

    removed = cleanup_delivered_video_files(root=tmp_path, final_path=final_path, record_id=8, enabled=False)

    assert removed == []
    assert final_path.exists()
