#!/usr/bin/env bash
set -euo pipefail

start_novnc_display() {
  local display="${DISPLAY:-:99}"
  local port="${NOVNC_PORT:-6080}"

  for command in Xvfb fluxbox x11vnc websockify xdpyinfo; do
    if ! command -v "$command" >/dev/null 2>&1; then
      echo "Missing auth tool: $command" >&2
      echo "Rebuild the image with INSTALL_AUTH_TOOLS=true, then redeploy." >&2
      exit 127
    fi
  done

  export DISPLAY="$display"

  echo "Starting virtual display on $DISPLAY..."
  Xvfb "$DISPLAY" -screen 0 1440x1000x24 -ac +extension GLX +render -noreset >/tmp/xvfb.log 2>&1 &
  local xvfb_pid=$!

  for _ in {1..30}; do
    if kill -0 "$xvfb_pid" 2>/dev/null; then
      if xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
        break
      fi
      sleep 1
      continue
    fi

    echo "Xvfb exited unexpectedly. Log:" >&2
    cat /tmp/xvfb.log >&2 || true
    exit 1
  done

  if ! xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
    echo "Xvfb did not become ready. Log:" >&2
    cat /tmp/xvfb.log >&2 || true
    exit 1
  fi

  fluxbox >/tmp/fluxbox.log 2>&1 &
  x11vnc -display "$DISPLAY" -forever -shared -nopw -listen 0.0.0.0 -xkb >/tmp/x11vnc.log 2>&1 &
  local x11vnc_pid=$!
  websockify --web=/usr/share/novnc/ 0.0.0.0:"$port" localhost:5900 >/tmp/novnc.log 2>&1 &
  local novnc_pid=$!

  for _ in {1..30}; do
    if ! kill -0 "$x11vnc_pid" 2>/dev/null; then
      echo "x11vnc exited unexpectedly. Log:" >&2
      cat /tmp/x11vnc.log >&2 || true
      exit 1
    fi

    if ! kill -0 "$novnc_pid" 2>/dev/null; then
      echo "websockify exited unexpectedly. Log:" >&2
      cat /tmp/novnc.log >&2 || true
      exit 1
    fi

    if python - "$port" <<'PY' >/dev/null 2>&1
import socket
import sys

with socket.create_connection(("127.0.0.1", int(sys.argv[1])), timeout=1):
    pass
PY
    then
      echo "noVNC is running on port $port."
      return 0
    fi

    sleep 1
  done

  echo "noVNC did not become ready. Logs:" >&2
  cat /tmp/x11vnc.log >&2 || true
  cat /tmp/novnc.log >&2 || true
  exit 1
}
