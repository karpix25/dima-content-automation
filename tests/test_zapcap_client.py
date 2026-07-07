from pathlib import Path

import httpx
import pytest

from content_automation.zapcap_client import ZapCapApiClient, ZapCapApiError


def test_zapcap_client_upload_create_poll_and_download(tmp_path: Path, monkeypatch):
    video_path = tmp_path / "source.mp4"
    video_path.write_bytes(b"video")
    output_path = tmp_path / "final.mp4"
    requests = []

    def fake_request(method, url, **kwargs):
        requests.append((method, url, kwargs))
        if method == "POST" and url.endswith("/videos/video-1/task"):
            return _json_response({"taskId": "task-1", "status": "pending"})
        if method == "GET" and url.endswith("/videos/video-1/task/task-1"):
            return _json_response({"id": "task-1", "status": "completed", "downloadUrl": "https://cdn.test/final.mp4"})
        raise AssertionError(f"Unexpected request: {method} {url}")

    class FakeClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def post(self, url, **kwargs):
            requests.append(("POST", url, kwargs))
            return _json_response({"id": "video-1"})

        def get(self, url):
            assert url == "https://cdn.test/final.mp4"
            return httpx.Response(200, content=b"final")

    monkeypatch.setattr(httpx, "Client", FakeClient)
    monkeypatch.setattr(httpx, "request", fake_request)

    client = ZapCapApiClient(api_key="key", timeout_seconds=10)
    video = client.upload_video(video_path, ttl="7d")
    task = client.create_task(video.id, {"templateId": "tpl-1"}, ttl="7d")
    completed = client.wait_for_task(video.id, task.id, poll_seconds=3, timeout_seconds=10)
    result = client.download(completed.download_url, output_path)

    assert video.id == "video-1"
    assert task.id == "task-1"
    assert result.read_bytes() == b"final"
    assert requests[0][2]["headers"] == {"x-api-key": "key"}
    assert requests[0][2]["params"] == {"ttl": "7d"}
    assert requests[1][2]["json"] == {"templateId": "tpl-1"}


def test_zapcap_client_raises_on_failed_task(monkeypatch):
    def fake_request(method, url, **kwargs):
        return _json_response({"id": "task-1", "status": "failed", "error": "bad video"})

    monkeypatch.setattr(httpx, "request", fake_request)

    client = ZapCapApiClient(api_key="key")

    with pytest.raises(ZapCapApiError, match="failed"):
        client.wait_for_task("video-1", "task-1", poll_seconds=3, timeout_seconds=10)


def test_zapcap_client_lists_templates(monkeypatch):
    def fake_request(method, url, **kwargs):
        assert method == "GET"
        assert url.endswith("/templates")
        return _json_response({"templates": [{"id": "tpl-1", "name": "Bold Pop"}]})

    monkeypatch.setattr(httpx, "request", fake_request)

    templates = ZapCapApiClient(api_key="key").list_templates()

    assert templates[0].id == "tpl-1"
    assert templates[0].name == "Bold Pop"


def test_zapcap_client_lists_templates_from_array_response(monkeypatch):
    def fake_request(method, url, **kwargs):
        return _json_response([{"id": "tpl-1", "name": "Celine"}])

    monkeypatch.setattr(httpx, "request", fake_request)

    templates = ZapCapApiClient(api_key="key").list_templates()

    assert templates[0].id == "tpl-1"
    assert templates[0].name == "Celine"


def test_zapcap_client_requires_api_key(tmp_path: Path):
    video_path = tmp_path / "source.mp4"
    video_path.write_bytes(b"video")
    client = ZapCapApiClient(api_key=None)

    with pytest.raises(ZapCapApiError, match="ZAPCAP_API_KEY"):
        client.upload_video(video_path)


def _json_response(payload: dict) -> httpx.Response:
    return httpx.Response(200, json=payload)
