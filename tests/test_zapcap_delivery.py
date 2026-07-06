from pathlib import Path
from types import SimpleNamespace

from content_automation import media_delivery
from content_automation.storage import ScriptRecord
from content_automation.zapcap_models import normalize_zapcap_settings


def test_media_delivery_zapcap_mode_skips_hyperframes(tmp_path: Path, monkeypatch):
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

    monkeypatch.setattr(media_delivery, "get_user_settings", fake_get_user_settings)
    monkeypatch.setattr(media_delivery, "process_video_with_zapcap", fake_process_video_with_zapcap)
    monkeypatch.setattr(media_delivery, "render_montage_if_configured", fail_render_montage_if_configured)

    output = media_delivery._post_heygen_visuals(
        record=_record(),
        user_id="42",
        settings=_settings(tmp_path),
        storage=object(),
        asset_store=object(),
        kie_client=object(),
        video_path=source,
    )

    assert output == result
    assert calls[0]["video_path"] == source
    assert calls[0]["user_settings"].postprocess_provider == "zapcap"


def test_media_delivery_non_zapcap_mode_can_return_original_when_visuals_disabled(tmp_path: Path, monkeypatch):
    source = tmp_path / "heygen.mp4"
    source.write_bytes(b"video")

    def fake_get_user_settings(storage, settings, user_id):
        return SimpleNamespace(
            zapcap=normalize_zapcap_settings({"postprocess_provider": "hyperframes"}),
            content_language="en",
        )

    monkeypatch.setattr(media_delivery, "get_user_settings", fake_get_user_settings)
    settings = _settings(tmp_path)
    settings.post_heygen_visuals_enabled = False

    output = media_delivery._post_heygen_visuals(
        record=_record(format="youtube"),
        user_id="42",
        settings=settings,
        storage=object(),
        asset_store=object(),
        kie_client=object(),
        video_path=source,
    )

    assert output == source


def test_media_delivery_off_mode_skips_hyperframes_even_when_visuals_enabled(tmp_path: Path, monkeypatch):
    source = tmp_path / "heygen.mp4"
    source.write_bytes(b"video")

    def fake_get_user_settings(storage, settings, user_id):
        return SimpleNamespace(zapcap=normalize_zapcap_settings({"postprocess_provider": "off"}))

    def fail_render_montage_if_configured(**kwargs):
        raise AssertionError("HyperFrames montage must not run when provider is off")

    monkeypatch.setattr(media_delivery, "get_user_settings", fake_get_user_settings)
    monkeypatch.setattr(media_delivery, "render_montage_if_configured", fail_render_montage_if_configured)

    output = media_delivery._post_heygen_visuals(
        record=_record(format="youtube"),
        user_id="42",
        settings=_settings(tmp_path),
        storage=object(),
        asset_store=object(),
        kie_client=object(),
        video_path=source,
    )

    assert output == source


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


def _record(*, format: str = "short") -> ScriptRecord:
    return ScriptRecord(
        id=8,
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
