import httpx

from content_automation.kie_text import KieTextClient, KieTextConfig


def test_kie_text_client_uses_openai_compatible_chat_endpoint(monkeypatch):
    requests = []
    original_client = httpx.Client

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"choices": [{"message": {"content": "Rewritten text"}}]})

    monkeypatch.setattr(httpx, "Client", lambda **kwargs: original_client(transport=httpx.MockTransport(handler)))

    client = KieTextClient(KieTextConfig(api_key="key", base_url="https://api.kie.ai", model="gemini-3-flash", timeout_seconds=30))

    assert client.complete(system="system", user="user") == "Rewritten text"
    assert requests[0].url.path == "/v1/chat/completions"
    assert requests[0].headers["authorization"] == "Bearer key"
