from pathlib import Path

from content_automation.telegram_file_delivery import send_video_document_to_telegram


def test_send_video_document_to_telegram_uses_document_endpoint(tmp_path: Path, monkeypatch):
    video_path = tmp_path / "result.mp4"
    video_path.write_bytes(b"video")
    calls = []

    def fake_post(url, *, data, files, timeout):
        calls.append({"url": url, "data": data, "files": files, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr("content_automation.telegram_file_delivery.httpx.post", fake_post)

    message_id = send_video_document_to_telegram(token="token", chat_id="42", video_path=video_path, caption="Done")

    assert message_id == "777"
    assert calls[0]["url"] == "https://api.telegram.org/bottoken/sendDocument"
    assert calls[0]["data"] == {"chat_id": "42", "caption": "Done"}
    assert "document" in calls[0]["files"]
    assert "video" not in calls[0]["files"]


class FakeResponse:
    status_code = 200

    def json(self):
        return {"result": {"message_id": 777}}
