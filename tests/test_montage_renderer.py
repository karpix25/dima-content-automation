from pathlib import Path
from types import SimpleNamespace

import content_automation.montage_renderer as montage_renderer
from content_automation.montage_renderer import MontageRendererConfig, _command, _render
from content_automation.storage import ScriptRecord


def test_hyperframes_command_uses_youtube_layout_for_horizontal():
    command = _command(
        "hyperframes",
        record=_record(format="youtube"),
        video_path=Path("source.mp4"),
        scene_plan_path=Path("scenes.json"),
        word_cues_path=Path("words.json"),
        output_path=Path("out.mp4"),
    )

    assert command[-2:] == ["--layout", "horizontal_youtube"]


def test_render_montage_if_configured_uses_hyperframes_for_short_with_package_json(tmp_path, monkeypatch):
    project_dir = tmp_path / "hyperframes"
    project_dir.mkdir()
    (project_dir / "package.json").write_text("{}", encoding="utf-8")
    output_path = tmp_path / "rendered.mp4"
    calls = []

    def fake_render(**kwargs):
        calls.append(kwargs)
        return output_path

    monkeypatch.setattr(montage_renderer, "_render", fake_render)

    rendered = montage_renderer.render_montage_if_configured(
        record=_record(format="short"),
        video_path=tmp_path / "source.mp4",
        output_dir=tmp_path / "out",
        config=MontageRendererConfig(
            hyperframes_project_dir=project_dir,
            remotion_project_dir=None,
            renderer="auto",
            timeout_seconds=30,
            max_scenes=3,
        ),
    )

    assert rendered == output_path
    assert calls[0]["name"] == "hyperframes"
    assert calls[0]["project_dir"] == project_dir


def test_hyperframes_command_uses_vertical_heygen_layout_for_short_avatar_reels():
    for record_format in ("short", "shorts", "reels", "avatar_reels"):
        command = _command(
            "hyperframes",
            record=_record(format=record_format),
            video_path=Path("source.mp4"),
            scene_plan_path=Path("scenes.json"),
            word_cues_path=Path("words.json"),
            output_path=Path("out.mp4"),
        )

        assert command[-2:] == ["--layout", "vertical_heygen"]


def test_render_prepares_vertical_images_for_reels(tmp_path, monkeypatch):
    project_dir = tmp_path / "hyperframes"
    project_dir.mkdir()
    video_path = tmp_path / "source.mp4"
    video_path.write_bytes(b"video")
    calls = []

    monkeypatch.setattr(montage_renderer, "probe_duration_seconds", lambda _: 10.0)
    monkeypatch.setattr(montage_renderer, "_transcribe_for_timing", lambda **_: None)
    monkeypatch.setattr(
        montage_renderer,
        "build_montage_plan",
        lambda *_, **__: SimpleNamespace(
            scenes=[{"start": 0, "end": 2, "title": "Scene", "imagePrompt": "Amazon dashboard"}],
            word_cues=[],
        ),
    )
    monkeypatch.setattr(montage_renderer, "prepare_vertical_montage_assets", lambda **kwargs: calls.append(kwargs))

    def fake_run(cmd, **kwargs):
        out_path = Path(cmd[cmd.index("--out") + 1])
        out_path.write_bytes(b"rendered")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(montage_renderer.subprocess, "run", fake_run)

    rendered = _render(
        name="hyperframes",
        project_dir=project_dir,
        record=_record(format="reels"),
        video_path=video_path,
        output_dir=tmp_path / "out",
        timeout_seconds=30,
        max_scenes=3,
        deepgram=None,
        kie_client=None,
        content_language="en",
    )

    assert rendered and rendered.exists()
    assert calls[0]["project_dir"] == project_dir
    assert calls[0]["scenes"][0]["imagePrompt"] == "Amazon dashboard"


def test_hyperframes_command_passes_transcript_when_available():
    command = _command(
        "hyperframes",
        record=_record(format="short"),
        video_path=Path("source.mp4"),
        scene_plan_path=Path("scenes.json"),
        word_cues_path=Path("words.json"),
        output_path=Path("out.mp4"),
        transcript_path=Path("transcript.deepgram.json"),
    )

    assert "--transcript" in command
    assert command[-1] == "transcript.deepgram.json"


def _record(*, format: str) -> ScriptRecord:
    return ScriptRecord(
        id=1,
        user_id="42",
        format=format,
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
