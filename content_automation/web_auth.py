from __future__ import annotations

import hashlib
import hmac
import json
import re
import time
from urllib.parse import parse_qsl

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .project_store import ProjectStore


PUBLIC_API_PATHS = {"/api/formats"}
INIT_DATA_HEADER = "x-telegram-init-data"


def install_miniapp_auth(
    app: FastAPI,
    *,
    bot_token: str,
    required: bool,
    max_age_seconds: int = 86400,
    project_store: ProjectStore | None = None,
) -> None:
    app.add_middleware(
        MiniAppAuthMiddleware,
        bot_token=bot_token,
        required=required,
        max_age_seconds=max_age_seconds,
        project_store=project_store,
    )


class MiniAppAuthMiddleware:
    def __init__(
        self,
        app,
        *,
        bot_token: str,
        required: bool,
        max_age_seconds: int = 86400,
        project_store: ProjectStore | None = None,
    ) -> None:
        self.app = app
        self.bot_token = bot_token
        self.required = required
        self.max_age_seconds = max_age_seconds
        self.project_store = project_store

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        if not _should_check(request):
            await self.app(scope, receive, send)
            return

        init_data = request.headers.get(INIT_DATA_HEADER, "")
        if not init_data:
            if self.required:
                await JSONResponse({"detail": "Telegram Mini App auth is required"}, status_code=401)(scope, receive, send)
                return
            await self.app(scope, receive, send)
            return

        try:
            telegram_user_id = validate_init_data(
                init_data,
                bot_token=self.bot_token,
                max_age_seconds=self.max_age_seconds,
            )
        except ValueError as exc:
            await JSONResponse({"detail": str(exc)}, status_code=401)(scope, receive, send)
            return

        requested_user_id = _query_user_id(request)
        body: bytes | None = None
        if not requested_user_id and _may_contain_body_user_id(request):
            body = await _read_body(receive)
            requested_user_id = _body_user_id(request, body)
        if requested_user_id and not self._has_requested_user_access(requested_user_id, telegram_user_id):
            await JSONResponse({"detail": "Telegram user does not match request user_id"}, status_code=403)(
                scope,
                _replay_body_receive(body) if body is not None else receive,
                send,
            )
            return

        scope.setdefault("state", {})["telegram_user_id"] = telegram_user_id
        await self.app(scope, _replay_body_receive(body) if body is not None else receive, send)

    def _has_requested_user_access(self, requested_user_id: str, telegram_user_id: str) -> bool:
        if requested_user_id == telegram_user_id:
            if self.project_store:
                self.project_store.ensure_default_project(telegram_user_id)
            return True
        return bool(self.project_store and self.project_store.is_member(requested_user_id, telegram_user_id))


def validate_init_data(init_data: str, *, bot_token: str, max_age_seconds: int | None = 86400) -> str:
    values = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = values.pop("hash", "")
    if not received_hash:
        raise ValueError("Telegram initData hash is missing")
    data_check_string = "\n".join(f"{key}={values[key]}" for key in sorted(values))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_hash, received_hash):
        raise ValueError("Telegram initData signature is invalid")
    if max_age_seconds is not None:
        auth_date = _int_or_none(values.get("auth_date"))
        if not auth_date or time.time() - auth_date > max_age_seconds:
            raise ValueError("Telegram initData is expired")
    user = json.loads(values.get("user") or "{}")
    user_id = str(user.get("id") or "").strip()
    if not user_id:
        raise ValueError("Telegram initData user is missing")
    return user_id


def _should_check(request: Request) -> bool:
    return request.url.path.startswith("/api/") and request.url.path not in PUBLIC_API_PATHS and request.method != "OPTIONS"


def _query_user_id(request: Request) -> str:
    return (request.query_params.get("user_id") or request.query_params.get("tg_id") or "").strip()


def _may_contain_body_user_id(request: Request) -> bool:
    return request.method in {"POST", "PUT", "PATCH", "DELETE"}


def _body_user_id(request: Request, body: bytes) -> str:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type and body:
        try:
            parsed = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            return ""
        return str(parsed.get("user_id") or "").strip() if isinstance(parsed, dict) else ""
    if "application/x-www-form-urlencoded" in content_type and body:
        values = dict(parse_qsl(body.decode("utf-8"), keep_blank_values=True))
        return str(values.get("user_id") or "").strip()
    if "multipart/form-data" in content_type and body:
        match = re.search(rb'name="user_id"\r?\n\r?\n([^\r\n]+)', body)
        return match.group(1).decode("utf-8").strip() if match else ""
    return ""


async def _read_body(receive) -> bytes:
    chunks: list[bytes] = []
    while True:
        message = await receive()
        if message["type"] != "http.request":
            break
        chunks.append(message.get("body", b""))
        if not message.get("more_body", False):
            break
    return b"".join(chunks)


def _replay_body_receive(body: bytes | None):
    sent = False

    async def receive() -> dict:
        nonlocal sent
        if sent:
            return {"type": "http.disconnect"}
        sent = True
        return {"type": "http.request", "body": body or b"", "more_body": False}

    return receive


def _int_or_none(value: str | None) -> int | None:
    try:
        return int(value or "")
    except ValueError:
        return None
