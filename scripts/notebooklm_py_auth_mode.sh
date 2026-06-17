#!/usr/bin/env bash
set -euo pipefail

export NOTEBOOKLM_PY_STORAGE_PATH="${NOTEBOOKLM_PY_STORAGE_PATH:-/app/.data/notebooklm-py/storage_state.json}"

mkdir -p "$(dirname "$NOTEBOOKLM_PY_STORAGE_PATH")"

. scripts/novnc_display.sh
start_novnc_display

cat <<EOF

Open the noVNC URL and log in inside the browser window.
The visible NotebookLM login browser is started automatically.

After login, set:
APP_MODE=bot
NOTEBOOKLM_BACKEND=py
NOTEBOOKLM_PY_STORAGE_PATH=$NOTEBOOKLM_PY_STORAGE_PATH

Then redeploy.

EOF

(
  while true; do
    rm -f /tmp/notebooklm-login.log
    env DISPLAY="$DISPLAY" notebooklm --storage "$NOTEBOOKLM_PY_STORAGE_PATH" login >/tmp/notebooklm-login.log 2>&1 || true
    sleep "${NOTEBOOKLM_AUTH_LOGIN_RESTART_SECONDS:-300}"
  done
) &

tail -f /dev/null
