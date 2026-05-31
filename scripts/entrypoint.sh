#!/usr/bin/env bash
set -euo pipefail

if [[ "${APP_MODE:-bot}" == "notebooklm-auth" ]]; then
  exec bash scripts/notebooklm_auth_mode.sh
fi

if [[ "${APP_MODE:-bot}" == "notebooklm-py-auth" ]]; then
  exec bash scripts/notebooklm_py_auth_mode.sh
fi

exec bash scripts/run_app.sh
