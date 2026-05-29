#!/usr/bin/env bash
set -euo pipefail

export DISPLAY="${DISPLAY:-:99}"
export NOTEBOOKLM_PY_STORAGE_PATH="${NOTEBOOKLM_PY_STORAGE_PATH:-/app/.data/notebooklm-py/storage_state.json}"

mkdir -p "$(dirname "$NOTEBOOKLM_PY_STORAGE_PATH")"

echo "Starting virtual display for notebooklm-py auth..."
Xvfb "$DISPLAY" -screen 0 1440x1000x24 -ac +extension GLX +render -noreset &

fluxbox >/tmp/fluxbox.log 2>&1 &
x11vnc -display "$DISPLAY" -forever -shared -nopw -listen 0.0.0.0 -xkb >/tmp/x11vnc.log 2>&1 &
websockify --web=/usr/share/novnc/ 0.0.0.0:"${NOVNC_PORT:-6080}" localhost:5900 >/tmp/novnc.log 2>&1 &

cat <<EOF

noVNC is running on port ${NOVNC_PORT:-6080}.
Open the noVNC URL in Coolify, then run this command from the Coolify container terminal:

DISPLAY=$DISPLAY notebooklm --storage "$NOTEBOOKLM_PY_STORAGE_PATH" login

Log in inside the noVNC browser window. When NotebookLM opens successfully,
go back to the terminal and press Enter so notebooklm-py saves the session.

After login, set:
APP_MODE=bot
NOTEBOOKLM_BACKEND=py
NOTEBOOKLM_PY_STORAGE_PATH=$NOTEBOOKLM_PY_STORAGE_PATH

Then redeploy.

EOF

tail -f /dev/null
