import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from content_automation.storage import ScriptRecord
from content_automation.zapcap_models import normalize_zapcap_settings


os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456:ABCdefGHIjklMNOpqrSTUvwxYZ123456789")


@pytest.mark.asyncio
async def test_bot_zapcap_mode_skips_hyperframes(tmp_path: Path, monkeypatch):
    from content_automation import bot

    source = tmp_path / "heygen.mp4"
    result = tmp_path / "zapcap.mp4"
    source.write_bytes(b"video")
    result.write_bytes(b"zapcap")
    calls = []

    def fake_get_user_settings(storage, settings, user_id):
        return SimpleNamespace(
            zapcap=normalize_zapcap_settings(
                {
                    "postprocess_provider": "zapcap",
                    "zapcap_template_id": "tpl-1",
                }
            )
        )

    def fake_process_video_with_zapcap(**kwargs):
        calls.append(kwargs)
        return result

    def fail_render_montage_if_configured(**kwargs):
        raise AssertionError("HyperFrames montage must not run in ZapCap mode")

    monkeypatch.setattr(bot, "settings", _settings(tmp_path))
    monkeypatch.setattr(bot, "get_user_settings", fake_get_user_settings)
    monkeypatch.setattr(bot, "process_video_with_zapcap", fake_process_video_with_zapcap)
    monkeypatch.setattr(bot, "render_montage_if_configured", fail_render_montage_if_configured)

    output = await bot.process_post_heygen_visuals_if_enabled(_record(), source)

    assert output == result
    assert calls[0]["video_path"] == source


def _settings(tmp_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        video_output_directory=tmp_path,
        zapcap_api_key="key",
        zapcap_api_base_url="https://api.zapcap.ai",
        zapcap_enabled=True,
        zapcap_poll_seconds=3,
        zapcap_timeout_seconds=60,
        zapcap_request_timeout_seconds=10,
        zapcap_ttl="7d",
        zapcap_output_mode="composited",
        zapcap_quality="standard",
        zapcap_export_speed="fast",
        post_heygen_visuals_enabled=True,
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
