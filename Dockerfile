FROM mcr.microsoft.com/playwright:v1.61.0-noble

ARG INSTALL_AUTH_TOOLS=false
ARG TARGETARCH

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    DATA_DIR=/app/.data \
    ELEVENLABS_OUTPUT_DIRECTORY=/app/outputs/elevenlabs \
    HYPERFRAMES_PROJECT_DIR=/app/hyperframes-auto \
    HYPERFRAMES_BROWSER_PATH=/usr/local/bin/playwright-chromium \
    PRODUCER_HEADLESS_SHELL_PATH=/usr/local/bin/playwright-chromium \
    PUPPETEER_EXECUTABLE_PATH=/usr/local/bin/playwright-chromium \
    CHROME_BIN=/usr/local/bin/playwright-chromium

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        ffmpeg \
        git \
        python3 \
        python3-pip \
        python3-venv \
        $(if [ "$INSTALL_AUTH_TOOLS" = "true" ]; then echo "fluxbox novnc websockify x11vnc xvfb x11-utils"; fi) \
    && rm -rf /var/lib/apt/lists/*

RUN printf '%s\n' \
    '#!/usr/bin/env bash' \
    'set -euo pipefail' \
    'for candidate in \' \
    '  /ms-playwright/chromium-*/chrome-linux/chrome \' \
    '  /ms-playwright/chromium-*/chrome-linux64/chrome \' \
    '  /ms-playwright/chromium_headless_shell-*/chrome-linux/headless_shell \' \
    '  /ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell \' \
    '  /ms-playwright/chrome-*/chrome-linux64/chrome \' \
    '  /ms-playwright/chrome-*/chrome-linux/chrome \' \
    '  /ms-playwright/chrome_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell \' \
    '  /usr/bin/chromium \' \
    '  /usr/bin/chromium-browser \' \
    '  /usr/bin/chromium-headless-shell; do' \
    '  for browser in $candidate; do' \
    '    if [[ -x "$browser" ]]; then exec "$browser" "$@"; fi' \
    '  done' \
    'done' \
    'echo "No Playwright Chromium executable found." >&2' \
    'find /ms-playwright -maxdepth 3 -type f \( -name chrome -o -name headless_shell -o -name chrome-headless-shell \) -print >&2 || true' \
    'exit 127' \
    > /usr/local/bin/playwright-chromium \
    && chmod +x /usr/local/bin/playwright-chromium

COPY requirements.txt ./
COPY hyperframes-auto/package*.json ./hyperframes-auto/

RUN python3 -m venv /opt/venv \
    && for attempt in 1 2 3; do \
        python -m pip install --timeout 120 --retries 10 -r requirements.txt && break; \
        if [ "$attempt" = "3" ]; then exit 1; fi; \
        echo "pip install failed, retrying in 10 seconds..."; \
        sleep 10; \
    done \
    && PLAYWRIGHT_SKIP_BROWSER_GC=1 python -m playwright install chromium

RUN cd hyperframes-auto \
    && npm config set fetch-retries 5 \
    && npm config set fetch-retry-mintimeout 20000 \
    && npm config set fetch-retry-maxtimeout 120000 \
    && for attempt in 1 2 3; do \
        npm ci --omit=dev --no-audit --no-fund && break; \
        if [ "$attempt" = "3" ]; then exit 1; fi; \
        echo "npm ci failed, retrying in 15 seconds..."; \
        sleep 15; \
    done \
    && keep_arch="$(case "${TARGETARCH:-amd64}" in arm64) echo arm64 ;; *) echo x64 ;; esac)" \
    && if [ -d node_modules/onnxruntime-node/bin/napi-v6 ]; then \
        find node_modules/onnxruntime-node/bin/napi-v6 -mindepth 1 -maxdepth 1 ! -name linux -exec rm -rf {} +; \
        find node_modules/onnxruntime-node/bin/napi-v6/linux -mindepth 1 -maxdepth 1 ! -name "$keep_arch" -exec rm -rf {} +; \
    fi \
    && npm cache clean --force \
    && rm -rf /root/.npm /tmp/*

COPY content_automation ./content_automation
COPY hyperframes-auto ./hyperframes-auto
COPY scripts ./scripts
COPY README.md ./

RUN mkdir -p \
    /app/.data \
    /app/outputs/elevenlabs \
    /app/outputs/videos \
    /app/hyperframes-auto/assets/input \
    /app/hyperframes-auto/assets/generated \
    /app/hyperframes-auto/renders
RUN chmod +x scripts/entrypoint.sh scripts/notebooklm_auth_mode.sh scripts/notebooklm_py_auth_mode.sh scripts/novnc_display.sh scripts/run_app.sh

EXPOSE 6080 8000

CMD ["bash", "scripts/entrypoint.sh"]
