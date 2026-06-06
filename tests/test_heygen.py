import pytest

from content_automation.heygen import HeyGenClient


class FakeResponse:
    status_code = 200
    text = ""

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


class FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def get(self, *args, **kwargs):
        return FakeResponse(
            {
                "data": {
                    "avatar_looks": [
                        {
                            "id": "motion-avatar",
                            "name": "Motion Avatar",
                            "ownership": "private",
                            "supported_api_engines": ["avatar_iv"],
                        },
                        {
                            "id": "static-avatar",
                            "name": "Static Avatar",
                            "ownership": "private",
                            "supported_api_engines": ["avatar_v"],
                        },
                    ]
                }
            }
        )


class FakeVideoStatusClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def get(self, *args, **kwargs):
        return FakeResponse(
            {
                "data": {
                    "status": "completed",
                    "video_url": {
                        "caption": "https://example.com/ready.mp4",
                    },
                }
            }
        )


class FakeVideoStatusFallbackClient:
    def __init__(self, *args, **kwargs):
        self.calls = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def get(self, *args, **kwargs):
        self.calls += 1
        if self.calls == 1:
            response = FakeResponse({"error": "bad id for v3"})
            response.status_code = 400
            response.text = "bad id for v3"
            return response
        return FakeResponse(
            {
                "data": {
                    "status": "completed",
                    "video_url": "https://example.com/legacy.mp4",
                }
            }
        )


@pytest.mark.asyncio
async def test_list_avatar_looks_returns_supported_avatar_versions(monkeypatch):
    monkeypatch.setattr("content_automation.heygen.httpx.AsyncClient", FakeAsyncClient)

    client = HeyGenClient(api_key="key")
    avatars = await client.list_avatar_looks()

    assert [avatar.id for avatar in avatars] == ["motion-avatar", "static-avatar"]


@pytest.mark.asyncio
async def test_get_video_extracts_nested_download_url(monkeypatch):
    monkeypatch.setattr("content_automation.heygen.httpx.AsyncClient", FakeVideoStatusClient)

    client = HeyGenClient(api_key="key")
    result = await client.get_video("video-123")

    assert result.status == "completed"
    assert result.video_url == "https://example.com/ready.mp4"


@pytest.mark.asyncio
async def test_get_video_falls_back_to_legacy_status_on_v3_400(monkeypatch):
    monkeypatch.setattr("content_automation.heygen.httpx.AsyncClient", FakeVideoStatusFallbackClient)

    client = HeyGenClient(api_key="key")
    result = await client.get_video("legacy-video")

    assert result.status == "completed"
    assert result.video_url == "https://example.com/legacy.mp4"
