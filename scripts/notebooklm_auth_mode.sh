#!/usr/bin/env bash
set -euo pipefail

export DISPLAY="${DISPLAY:-:99}"
export HEADLESS=false

echo "Starting virtual display for NotebookLM auth..."
Xvfb "$DISPLAY" -screen 0 1440x1000x24 -ac +extension GLX +render -noreset &

fluxbox >/tmp/fluxbox.log 2>&1 &
x11vnc -display "$DISPLAY" -forever -shared -nopw -listen 0.0.0.0 -xkb >/tmp/x11vnc.log 2>&1 &
websockify --web=/usr/share/novnc/ 0.0.0.0:"${NOVNC_PORT:-6080}" localhost:5900 >/tmp/novnc.log 2>&1 &

echo
echo "noVNC is running on port ${NOVNC_PORT:-6080}."
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
