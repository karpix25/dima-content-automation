from __future__ import annotations

import json
import logging
import select
import shlex
import subprocess
import time
from dataclasses import dataclass
from typing import Any


class NotebookLMMCPError(RuntimeError):
    pass


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MCPAskResult:
    answer: str
    session_id: str | None = None
    raw: dict[str, Any] | None = None


class NotebookLMMCPClient:
    def __init__(self, command: str = "npx --yes notebooklm-mcp@latest", timeout_seconds: int = 240):
        self.command = command
        self.timeout_seconds = timeout_seconds

    def ask(self, question: str, *, notebook_url: str | None = None, notebook_id: str | None = None) -> MCPAskResult:
        args: dict[str, Any] = {
            "question": question,
            "source_format": "none",
            "browser_options": {
                "headless": True,
                "timeout_ms": max(90_000, self.timeout_seconds * 1000),
            },
        }
        if notebook_url:
            args["notebook_url"] = notebook_url
        elif notebook_id:
            args["notebook_id"] = notebook_id

        last_error: NotebookLMMCPError | None = None
        for attempt in range(1, 4):
            logger.info("Calling NotebookLM MCP ask_question, timeout=%ss, attempt=%s/3", self.timeout_seconds, attempt)
            try:
                payload = self.call_tool("ask_question", args)
                data = extract_mcp_text_json(payload)
                if not data.get("success"):
                    raise NotebookLMMCPError(str(data.get("error") or data))
                break
            except NotebookLMMCPError as exc:
                last_error = exc
                if attempt >= 3 or not _is_retriable_notebooklm_error(str(exc)):
                    raise
                wait_seconds = 5 * attempt
                logger.warning("NotebookLM MCP transient error, retrying in %ss: %s", wait_seconds, exc)
                time.sleep(wait_seconds)
        else:
            raise last_error or NotebookLMMCPError("NotebookLM MCP failed")

        result = data.get("data") if isinstance(data.get("data"), dict) else {}
        answer = str(result.get("answer") or "").strip()
        if not answer:
            raise NotebookLMMCPError(f"MCP returned an empty answer: {data}")
        return MCPAskResult(answer=answer, session_id=result.get("session_id"), raw=data)

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        started = time.monotonic()
        proc = subprocess.Popen(
            shlex.split(self.command),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        try:
            logger.info("Started NotebookLM MCP command: %s", self.command)
            self._send(proc, {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "content-automation", "version": "0.1"},
                },
            })
            self._read_response(proc, 1, timeout=45)
            self._send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
            self._send(proc, {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            })
            response = self._read_response(proc, 2, timeout=self.timeout_seconds)
            if "error" in response:
                raise NotebookLMMCPError(json.dumps(response["error"], ensure_ascii=False))
            logger.info("NotebookLM MCP tool %s completed in %.1fs", name, time.monotonic() - started)
            return response
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()

    @staticmethod
    def _send(proc: subprocess.Popen[str], payload: dict[str, Any]) -> None:
        if proc.stdin is None:
            raise NotebookLMMCPError("MCP stdin is not available")
        proc.stdin.write(json.dumps(payload) + "\n")
        proc.stdin.flush()

    @staticmethod
    def _read_response(proc: subprocess.Popen[str], target_id: int, timeout: float) -> dict[str, Any]:
        if proc.stdout is None:
            raise NotebookLMMCPError("MCP stdout is not available")
        deadline = time.time() + timeout
        while time.time() < deadline:
            remaining = deadline - time.time()
            readable, _, _ = select.select([proc.stdout], [], [], min(0.25, max(0.0, remaining)))
            if not readable:
                if proc.poll() is not None:
                    stderr = _read_available_stderr(proc)
                    raise NotebookLMMCPError(f"MCP exited early: {stderr[-2000:]}")
                continue
            line = proc.stdout.readline()
            if not line:
                if proc.poll() is not None:
                    stderr = _read_available_stderr(proc)
                    raise NotebookLMMCPError(f"MCP exited early: {stderr[-2000:]}")
                time.sleep(0.05)
                continue
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if payload.get("id") == target_id:
                return payload
        stderr = _read_available_stderr(proc)
        suffix = f": {stderr[-2000:]}" if stderr else ""
        raise NotebookLMMCPError(f"MCP response timed out for id={target_id}{suffix}")


def _read_available_stderr(proc: subprocess.Popen[str]) -> str:
    if proc.stderr is None:
        return ""
    chunks: list[str] = []
    while True:
        readable, _, _ = select.select([proc.stderr], [], [], 0)
        if not readable:
            break
        line = proc.stderr.readline()
        if not line:
            break
        chunks.append(line)
    return "".join(chunks)


def _is_retriable_notebooklm_error(message: str) -> bool:
    text = message.lower()
    if text.startswith("mcp response timed out"):
        return False
    markers = (
        "could not find notebooklm chat input",
        "waiting for chat input",
        "notebook page has loaded",
        "target page",
        "browser has been closed",
        "execution context was destroyed",
    )
    return any(marker in text for marker in markers)


def extract_mcp_text_json(payload: dict[str, Any]) -> dict[str, Any]:
    result = payload.get("result") if isinstance(payload, dict) else None
    content = result.get("content") if isinstance(result, dict) else None
    if not isinstance(content, list) or not content:
        raise NotebookLMMCPError(f"Unexpected MCP response: {payload}")
    text = ""
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text":
            text = str(item.get("text") or "")
            break
    if not text:
        raise NotebookLMMCPError(f"MCP response has no text content: {payload}")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise NotebookLMMCPError(f"MCP text is not JSON: {text[:1000]}") from exc
    if not isinstance(parsed, dict):
        raise NotebookLMMCPError(f"MCP JSON is not an object: {parsed}")
    return parsed


def notebook_ref_to_url(value: str | None) -> str | None:
    raw = (value or "").strip()
    if not raw:
        return None
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    return f"https://notebooklm.google.com/notebook/{raw}"
