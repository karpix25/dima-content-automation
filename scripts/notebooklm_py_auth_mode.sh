#!/usr/bin/env bash
set -euo pipefail

export NOTEBOOKLM_PY_STORAGE_PATH="${NOTEBOOKLM_PY_STORAGE_PATH:-/app/.data/notebooklm-py/storage_state.json}"

mkdir -p "$(dirname "$NOTEBOOKLM_PY_STORAGE_PATH")"

. scripts/novnc_display.sh
start_novnc_display

cat <<EOF

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
