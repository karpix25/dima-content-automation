#!/usr/bin/env bash
set -euo pipefail

if [[ "${APP_MODE:-bot}" == "notebooklm-auth" ]]; then
  exec bash scripts/notebooklm_auth_mode.sh
fi

exec python -m content_automation.bot
