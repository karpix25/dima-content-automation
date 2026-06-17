from __future__ import annotations

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

MCP_BROWSER_STATE_PATH = Path("/root/.local/share/notebooklm-mcp/browser_state/state.json")


def sync_playwright_storage_to_mcp(source_path: Path | None, *, destination_path: Path = MCP_BROWSER_STATE_PATH) -> bool:
    if not source_path or not source_path.exists():
        return False
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_path, destination_path)
    destination_path.chmod(0o600)
    logger.info("Synced NotebookLM storage state to MCP browser_state: %s", destination_path)
    return True
