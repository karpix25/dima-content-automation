from pathlib import Path

import content_automation.video_overlay as video_overlay


def test_apply_overlay_scales_overlay_inside_source_video(tmp_path, monkeypatch):
    video = tmp_path / "video.mp4"
    overlay = tmp_path / "overlay.png"
    output = tmp_path / "out.mp4"
    video.write_bytes(b"video")
    overlay.write_bytes(b"overlay")
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)

        class Result:
            returncode = 0
            stdout = ""
            stderr = ""

        return Result()

    monkeypatch.setattr(video_overlay, "probe_duration_seconds", lambda path: 10.0)
    monkeypatch.setattr(video_overlay.subprocess, "run", fake_run)

    video_overlay.apply_overlay(
        video_path=video,
        overlay_path=overlay,
        output_path=output,
        start_percent=70,
    )

    command = calls[0]
    filter_complex = command[command.index("-filter_complex") + 1]
    assert "scale2ref" in filter_complex
    assert "force_original_aspect_ratio=decrease" in filter_complex
    assert "overlay=(W-w)/2:(H-h)/2" in filter_complex
