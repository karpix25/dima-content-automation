from __future__ import annotations

import hashlib
import hmac
import json
import re
import time
from urllib.parse import parse_qsl

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


PUBLIC_API_PATHS = {"/api/formats"}
INIT_DATA_HEADER = "x-telegram-init-data"


def install_miniapp_auth(app: FastAPI, *, bot_token: str, required: bool, max_age_seconds: int = 86400) -> None:
    @app.middleware("http")
    async def miniapp_auth(request: Request, call_next):
        if not _should_check(request):
            return await call_next(request)

        init_data = request.headers.get(INIT_DATA_HEADER, "")
        if not init_data:
            if required:
                return JSONResponse({"detail": "Telegram Mini App auth is required"}, status_code=401)
            return await call_next(request)

        try:
            telegram_user_id = validate_init_data(init_data, bot_token=bot_token, max_age_seconds=max_age_seconds)
        except ValueError as exc:
            return JSONResponse({"detail": str(exc)}, status_code=401)

        body = await request.body()
        requested_user_id = _request_user_id(request, body)
        if requested_user_id and requested_user_id != telegram_user_id:
            return JSONResponse({"detail": "Telegram user does not match request user_id"}, status_code=403)

        await _restore_body(request, body)
        request.state.telegram_user_id = telegram_user_id
        return await call_next(request)


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


def _request_user_id(request: Request, body: bytes) -> str:
    query_user_id = (request.query_params.get("user_id") or request.query_params.get("tg_id") or "").strip()
    if query_user_id:
        return query_user_id
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


async def _restore_body(request: Request, body: bytes) -> None:
    async def receive() -> dict:
        return {"type": "http.request", "body": body, "more_body": False}

    request._receive = receive  # noqa: SLF001 - Starlette requires this pattern after middleware body reads.


def _int_or_none(value: str | None) -> int | None:
    try:
        return int(value or "")
    except ValueError:
        return None
