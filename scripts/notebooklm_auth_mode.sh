#!/usr/bin/env bash
set -euo pipefail

export HEADLESS=false

. scripts/novnc_display.sh
start_novnc_display

echo
echo "In Coolify, expose/open port ${NOVNC_PORT:-6080}, then open the generated URL."
echo "A browser window should appear there for Google/NotebookLM login."
echo

sleep 3
echo "Calling NotebookLM setup_auth..."
python scripts/mcp_call.py setup_auth '{}'

echo
echo "Auth command finished. Keeping container alive so you can inspect noVNC/logs."
echo "After login succeeds, set APP_MODE=bot and redeploy."
tail -f /dev/null
