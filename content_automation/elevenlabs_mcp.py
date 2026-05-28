from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import sysconfig
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ElevenLabsMCPError(RuntimeError):
    pass


@dataclass(frozen=True)
class ElevenLabsAudioResult:
    message: str
    file_path: str | None
    raw: dict[str, Any]


class ElevenLabsMCPClient:
    def __init__(
        self,
        *,
        api_key: str | None,
        command: str | None = None,
        output_directory: Path | None = None,
        timeout_seconds: int = 180,
    ):
        self.api_key = api_key
        self.command = command
        self.output_directory = output_directory
        self.timeout_seconds = timeout_seconds

    def text_to_speech(
        self,
        *,
        text: str,
        voice_name: str | None,
        voice_id: str | None = None,
        model_id: str,
        speed: float,
        stability: float,
        similarity_boost: float,
        style: float,
        language: str,
    ) -> ElevenLabsAudioResult:
        if not self.api_key:
            raise ElevenLabsMCPError("ELEVENLABS_API_KEY не задан в .env")
        if not text.strip():
            raise ElevenLabsMCPError("Пустой текст озвучки")

        arguments = {
            "text": text.strip(),
            "model_id": model_id,
            "speed": speed,
            "stability": stability,
            "similarity_boost": similarity_boost,
            "style": style,
            "use_speaker_boost": True,
            "language": language,
            "output_format": "mp3_44100_128",
        }
        if voice_id:
            arguments["voice_id"] = voice_id
        elif voice_name:
            arguments["voice_name"] = voice_name
        else:
            raise ElevenLabsMCPError("Не задан voice_id или voice_name для ElevenLabs")
        if self.output_directory:
            self.output_directory.mkdir(parents=True, exist_ok=True)
            arguments["output_directory"] = str(self.output_directory)

        payload = self.call_tool("text_to_speech", arguments)
        message = extract_text_content(payload)
        return ElevenLabsAudioResult(message=message, file_path=extract_file_path(message), raw=payload)

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        proc = subprocess.Popen(
            self.command_args(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=self.env(),
        )
        try:
            self._send(
                proc,
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "content-automation", "version": "0.1"},
                    },
                },
            )
            self._read_response(proc, 1, timeout=30)
            self._send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
            self._send(
                proc,
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": name, "arguments": arguments},
                },
            )
            response = self._read_response(proc, 2, timeout=self.timeout_seconds)
            if "error" in response:
                raise ElevenLabsMCPError(json.dumps(response["error"], ensure_ascii=False))
            return response
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()

    def command_args(self) -> list[str]:
        if self.command:
            return shlex.split(self.command)
        server_path = Path(sysconfig.get_path("purelib")) / "elevenlabs_mcp" / "server.py"
        return [sys.executable, str(server_path)]

    def env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["ELEVENLABS_API_KEY"] = self.api_key or ""
        env["ELEVENLABS_MCP_OUTPUT_MODE"] = "files"
        if self.output_directory:
            env["ELEVENLABS_MCP_BASE_PATH"] = str(self.output_directory)
        return env

    @staticmethod
    def _send(proc: subprocess.Popen[str], payload: dict[str, Any]) -> None:
        if proc.stdin is None:
            raise ElevenLabsMCPError("MCP stdin is not available")
        proc.stdin.write(json.dumps(payload) + "\n")
        proc.stdin.flush()

    @staticmethod
    def _read_response(proc: subprocess.Popen[str], target_id: int, timeout: float) -> dict[str, Any]:
        if proc.stdout is None:
            raise ElevenLabsMCPError("MCP stdout is not available")
        deadline = time.time() + timeout
        while time.time() < deadline:
            line = proc.stdout.readline()
            if not line:
                if proc.poll() is not None:
                    stderr = proc.stderr.read() if proc.stderr else ""
                    raise ElevenLabsMCPError(f"MCP exited early: {stderr[-2000:]}")
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
        raise ElevenLabsMCPError(f"MCP response timed out for id={target_id}")


def extract_text_content(payload: dict[str, Any]) -> str:
    result = payload.get("result") if isinstance(payload, dict) else None
    content = result.get("content") if isinstance(result, dict) else None
    if not isinstance(content, list) or not content:
        raise ElevenLabsMCPError(f"Unexpected MCP response: {payload}")
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text":
            return str(item.get("text") or "").strip()
    raise ElevenLabsMCPError(f"MCP response has no text content: {payload}")


def extract_file_path(message: str) -> str | None:
    marker = "File saved as:"
    if marker not in message:
        return None
    after = message.split(marker, 1)[1].strip()
    return after.split(". Voice used:", 1)[0].strip() or None
