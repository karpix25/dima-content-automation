from pathlib import Path

import pytest

from content_automation.storage import ScriptRecord
from content_automation.zapcap_models import ZapCapRuntimeSettings, normalize_zapcap_settings
from content_automation.zapcap_postprocess import (
    ZapCapPostprocessError,
    build_zapcap_task_payload,
    process_video_with_zapcap,
    size_token,
    zapcap_broll_settings,
)


def test_build_zapcap_task_payload_uses_auto_transcription():
    user_settings = normalize_zapcap_settings(
        {
            "postprocess_provider": "zapcap",
            "zapcap_template_id": "tpl-1",
            "zapcap_language": "ru",
            "zapcap_broll_percent": "35",
        }
    )

    payload = build_zapcap_task_payload(user_settings=user_settings, runtime=_runtime())

    assert payload["templateId"] == "tpl-1"
    assert payload["autoApprove"] is True
    assert payload["language"] == "ru"
    assert "transcript" not in payload
    assert payload["renderOptions"]["subsOptions"]["displayWords"] == 3
    assert payload["renderOptions"]["styleOptions"]["fontSize"] <= 70
    assert payload["renderOptions"]["styleOptions"]["fontShadow"] == "m"
    assert payload["renderOptions"]["styleOptions"]["stroke"] == "m"
    assert payload["renderOptions"]["highlightOptions"]["randomColourOne"] == "#FFE45C"
    assert payload["transcribeSettings"] == {"broll": {"brollPercent": 35}}


def test_process_video_with_zapcap_roundtrip(tmp_path: Path):
    source = tmp_path / "heygen.mp4"
    source.write_bytes(b"video")
    client = FakeZapCapClient()
    output = process_video_with_zapcap(
        record=_record(),
        video_path=source,
        output_dir=tmp_path,
        runtime=_runtime(),
        user_settings=normalize_zapcap_settings({"postprocess_provider": "zapcap", "zapcap_template_id": "tpl-1"}),
        client=client,
    )

    assert output.exists()
    assert output.read_bytes() == b"zapcap"
    assert client.uploaded == source
    assert client.payloads[0]["templateId"] == "tpl-1"


def test_process_video_with_zapcap_requires_template(tmp_path: Path):
    source = tmp_path / "heygen.mp4"
    source.write_bytes(b"video")

    with pytest.raises(ZapCapPostprocessError, match="template"):
        process_video_with_zapcap(
            record=_record(),
            video_path=source,
            output_dir=tmp_path,
            runtime=_runtime(),
            user_settings=normalize_zapcap_settings({"postprocess_provider": "zapcap"}),
            client=FakeZapCapClient(),
        )


def test_broll_percent_maps_to_zapcap_payload():
    assert zapcap_broll_settings(0) is None
    assert zapcap_broll_settings(10) == {"broll": {"brollPercent": 10}}
    assert zapcap_broll_settings(150) == {"broll": {"brollPercent": 100}}


def test_size_token_maps_ui_stroke_to_zapcap_enum():
    assert size_token(0) == "none"
    assert size_token(3) == "s"
    assert size_token(8) == "m"
    assert size_token(20) == "l"


class FakeVideo:
    id = "video-1"


class FakeTask:
    id = "task-1"
    status = "completed"
    download_url = "https://download.test/video.mp4"
    raw = {}


class FakeZapCapClient:
    def __init__(self):
        self.uploaded = None
        self.payloads = []

    def upload_video(self, video_path, *, ttl=None):
        self.uploaded = video_path
        return FakeVideo()

    def create_task(self, video_id, payload, *, ttl=None):
        self.payloads.append(payload)
        return FakeTask()

    def wait_for_task(self, video_id, task_id, *, poll_seconds, timeout_seconds):
        return FakeTask()

    def download(self, url, output_path):
        output_path.write_bytes(b"zapcap")
        return output_path


def _runtime() -> ZapCapRuntimeSettings:
    return ZapCapRuntimeSettings(
        api_key="key",
        api_base_url="https://api.zapcap.ai",
        enabled=True,
        poll_seconds=3,
        timeout_seconds=60,
        request_timeout_seconds=10,
        ttl="7d",
        output_mode="composited",
        quality="standard",
        export_speed="fast",
    )


def _record() -> ScriptRecord:
    return ScriptRecord(
        id=8,
        user_id="42",
        format="short",
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
