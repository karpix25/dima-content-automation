#!/usr/bin/env bash
set -euo pipefail

python -m uvicorn content_automation.web_app:app --host "${WEB_HOST:-0.0.0.0}" --port "${WEB_PORT:-8000}" &
web_pid=$!

cleanup() {
  kill "$web_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

python -m content_automation.bot
