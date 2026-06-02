from dataclasses import dataclass
from pathlib import Path

import content_automation.montage_assets as montage_assets
from content_automation.montage_plan import build_montage_plan
from content_automation.storage import ScriptRecord


def test_vertical_director_uses_transcript_language_for_titles():
    plan = build_montage_plan(
        _record(),
        duration_seconds=12,
        max_scenes=3,
        transcript_words=_words(
            "You are fighting your supplier over ten cents.",
            "Amazon is charging a dollar extra per unit on FBA fees.",
            "The box is two millimeters too wide.",
        ),
    )

    assert plan.scenes
    assert all(scene["language"] == "en" for scene in plan.scenes)
    assert all("Ошибка" not in scene["title"] for scene in plan.scenes)
    assert all(len(scene["title"].split()) <= 7 for scene in plan.scenes)
    assert "Do not include Russian text" in plan.scenes[0]["imagePrompt"]
    assert all(scene["motionPattern"] for scene in plan.scenes)
    assert all(scene["metricValue"] for scene in plan.scenes)
    assert all(scene["evidenceLabel"] for scene in plan.scenes)


def test_vertical_director_subtitle_ends_on_complete_phrase():
    plan = build_montage_plan(
        _record(),
        duration_seconds=18,
        max_scenes=2,
        transcript_words=_words(
            "If by 12PM, sales drop by more than 50%, the product is price sensitive.",
            "But if velocity holds, we keep the bump.",
        ),
    )

    assert plan.scenes
    subtitles = [scene["subtitle"] for scene in plan.scenes if scene["subtitle"]]
    assert not any(subtitle.endswith("the product is") for subtitle in subtitles)
    assert not any(
        subtitle.split()[-1].lower() in {"from", "is", "the", "because", "of", "to"}
        for subtitle in subtitles
    )


def test_prepare_vertical_montage_assets_generates_expected_kie_files(tmp_path, monkeypatch):
    client = FakeKieClient()
    monkeypatch.setattr(montage_assets, "KieImageClient", FakeKieClient)

    montage_assets.prepare_vertical_montage_assets(
        project_dir=tmp_path,
        scenes=[{"title": "FBA fee leak", "imagePrompt": "Create square evidence image."}],
        kie_client=client,
    )

    assert (tmp_path / "assets" / "generated" / "youtube-scene-01.png").exists()
    generated_client = FakeKieClient.instances[-1]
    assert generated_client.aspect_ratio == "1:1"
    assert generated_client.resolution == "1K"


@dataclass
class FakeConfig:
    api_key: str | None = "key"
    base_url: str = "https://example.test"
    upload_base_url: str = "https://upload.example.test"
    model: str = "gpt-image-2"
    aspect_ratio: str = "9:16"
    resolution: str = "2K"
    poll_timeout_seconds: float = 1
    poll_interval_seconds: float = 1
    create_task_max_attempts: int = 1
    create_task_retry_delay_seconds: float = 1


class FakeKieClient:
    instances = []

    def __init__(self, config=None):
        self.config = config or FakeConfig()
        self.aspect_ratio = ""
        self.resolution = ""
        self.instances.append(self)

    def is_configured(self):
        return True

    def generate_image(self, *, prompt: str, output_path: Path, reference_paths=None):
        self.aspect_ratio = self.config.aspect_ratio
        self.resolution = self.config.resolution
        output_path.write_bytes(b"png")
        return output_path


def _words(*sentences: str) -> list[dict]:
    words = []
    time = 0.5
    for sentence in sentences:
        parts = sentence.split()
        for index, raw in enumerate(parts):
            text = raw if index + 1 < len(parts) else raw.rstrip(".") + "."
            words.append({"word": raw.strip("."), "punctuated_word": text, "start": time, "end": time + 0.2})
            time += 0.26
    return words


def _record() -> ScriptRecord:
    return ScriptRecord(
        id=4,
        user_id="38061745",
        format="short",
        status="approved",
        title="Ошибка TikTok-дизайна",
        angle="Русский угол",
        hook="Русский хук",
        trigger="Русский триггер",
        voiceover="",
        cta="Check the fee tier.",
        why_it_works="",
        source_basis="",
        raw={},
    )
