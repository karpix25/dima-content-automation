from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

from fastapi import FastAPI, Request
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient

from content_automation.web_auth import install_miniapp_auth, validate_init_data
from content_automation.project_store import ProjectStore


BOT_TOKEN = "123456:test-token"


class JsonPayload(BaseModel):
    user_id: str
    value: str


def signed_init_data(user_id: str = "42", *, auth_date: int | None = None) -> str:
    values = {
        "auth_date": str(auth_date or int(time.time())),
        "query_id": "test-query",
        "user": json.dumps({"id": int(user_id), "first_name": "Test"}, separators=(",", ":")),
    }
    data_check_string = "\n".join(f"{key}={values[key]}" for key in sorted(values))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode("utf-8"), hashlib.sha256).digest()
    values["hash"] = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    return urlencode(values)


def test_validate_init_data_returns_signed_user_id():
    assert validate_init_data(signed_init_data("77"), bot_token=BOT_TOKEN) == "77"


def test_validate_init_data_rejects_tampering():
    init_data = signed_init_data("42").replace("42", "43")

    try:
        validate_init_data(init_data, bot_token=BOT_TOKEN)
    except ValueError as exc:
        assert "signature" in str(exc)
    else:
        raise AssertionError("tampered initData was accepted")


def test_miniapp_auth_rejects_mismatched_user_id():
    app = FastAPI()
    install_miniapp_auth(app, bot_token=BOT_TOKEN, required=True)

    @app.get("/api/private")
    def private(user_id: str, request: Request):
        return {"user_id": user_id, "telegram_user_id": request.state.telegram_user_id}

    client = TestClient(app)
    response = client.get(
        "/api/private",
        params={"user_id": "99"},
        headers={"X-Telegram-Init-Data": signed_init_data("42")},
    )

    assert response.status_code == 403


def test_miniapp_auth_allows_project_member_user_id(tmp_path):
    project_store = ProjectStore(tmp_path / "projects.sqlite3")
    project_store.ensure_default_project("42")
    project_store.add_member("42", "99", role="manager", actor_user_id="42")
    app = FastAPI()
    install_miniapp_auth(app, bot_token=BOT_TOKEN, required=True, project_store=project_store)

    @app.get("/api/private")
    def private(user_id: str, request: Request):
        return {"project_id": user_id, "telegram_user_id": request.state.telegram_user_id}

    client = TestClient(app)
    response = client.get(
        "/api/private",
        params={"user_id": "42"},
        headers={"X-Telegram-Init-Data": signed_init_data("99")},
    )

    assert response.status_code == 200
    assert response.json() == {"project_id": "42", "telegram_user_id": "99"}


def test_miniapp_auth_passes_matching_json_body():
    app = FastAPI()
    install_miniapp_auth(app, bot_token=BOT_TOKEN, required=True)

    @app.post("/api/private")
    async def private(request: Request):
        return await request.json()

    client = TestClient(app)
    response = client.post(
        "/api/private",
        json={"user_id": "42", "value": "ok"},
        headers={"X-Telegram-Init-Data": signed_init_data("42")},
    )

    assert response.status_code == 200
    assert response.json()["value"] == "ok"


def test_miniapp_auth_allows_pydantic_json_body_without_receive_replay_error():
    app = FastAPI()
    install_miniapp_auth(app, bot_token=BOT_TOKEN, required=True)

    @app.post("/api/private")
    def private(payload: JsonPayload):
        return {"value": payload.value}

    client = TestClient(app)
    response = client.post(
        "/api/private",
        json={"user_id": "42", "value": "ok"},
        headers={"X-Telegram-Init-Data": signed_init_data("42")},
    )

    assert response.status_code == 200
    assert response.json() == {"value": "ok"}


def test_miniapp_auth_does_not_replay_empty_get_body_to_streaming_response():
    app = FastAPI()
    install_miniapp_auth(app, bot_token=BOT_TOKEN, required=True)

    @app.get("/api/stream")
    def stream(user_id: str):
        return StreamingResponse(iter([f"ok:{user_id}".encode("utf-8")]))

    client = TestClient(app)
    response = client.get(
        "/api/stream",
        params={"user_id": "42"},
        headers={"X-Telegram-Init-Data": signed_init_data("42")},
    )

    assert response.status_code == 200
    assert response.content == b"ok:42"
