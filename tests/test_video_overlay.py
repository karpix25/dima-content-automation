from pathlib import Path
from types import SimpleNamespace

import content_automation.video_overlay as video_overlay


def test_probe_video_size_reads_first_video_stream(tmp_path, monkeypatch):
    video = tmp_path / "video.mp4"
    video.write_bytes(b"video")

    def fake_run(command, **kwargs):
        assert "-select_streams" in command
        return SimpleNamespace(returncode=0, stdout='{"streams":[{"width":1280,"height":720}]}', stderr="")

    monkeypatch.setattr(video_overlay.subprocess, "run", fake_run)

    assert video_overlay.probe_video_size(video) == (1280, 720)


def test_probe_video_size_uses_display_aspect_ratio(tmp_path, monkeypatch):
    video = tmp_path / "video.mp4"
    video.write_bytes(b"video")

    def fake_run(command, **kwargs):
        payload = '{"streams":[{"width":1080,"height":1080,"display_aspect_ratio":"16:9"}]}'
        return SimpleNamespace(returncode=0, stdout=payload, stderr="")

    monkeypatch.setattr(video_overlay.subprocess, "run", fake_run)

    assert video_overlay.probe_video_size(video) == (1920, 1080)


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
