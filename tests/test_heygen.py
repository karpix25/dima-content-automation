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


@pytest.mark.asyncio
async def test_list_avatar_looks_returns_supported_avatar_versions(monkeypatch):
    monkeypatch.setattr("content_automation.heygen.httpx.AsyncClient", FakeAsyncClient)

    client = HeyGenClient(api_key="key")
    avatars = await client.list_avatar_looks()

    assert [avatar.id for avatar in avatars] == ["motion-avatar", "static-avatar"]
