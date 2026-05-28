from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv


def main() -> int:
    load_dotenv()
    api_key = (os.getenv("ELEVENLABS_API_KEY") or "").strip() or "PUT_YOUR_ELEVENLABS_API_KEY_HERE"
    python_path = Path.cwd() / ".venv/bin/python"
    server_path = subprocess.check_output(
        [
            str(python_path),
            "-c",
            "import pathlib, sysconfig; print(pathlib.Path(sysconfig.get_path('purelib')) / 'elevenlabs_mcp' / 'server.py')",
        ],
        text=True,
    ).strip()
    config = {
        "mcpServers": {
            "ElevenLabs": {
                "command": str(python_path),
                "args": [server_path],
                "env": {
                    "ELEVENLABS_API_KEY": api_key,
                    "ELEVENLABS_MCP_OUTPUT_MODE": os.getenv("ELEVENLABS_MCP_OUTPUT_MODE", "files"),
                    "ELEVENLABS_MCP_BASE_PATH": str((Path.cwd() / "outputs/elevenlabs").resolve()),
                },
            }
        }
    }
    print(json.dumps(config, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
