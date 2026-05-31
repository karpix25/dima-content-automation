FROM mcr.microsoft.com/playwright:v1.60.0-noble

ARG INSTALL_AUTH_TOOLS=false

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    DATA_DIR=/app/.data \
    ELEVENLABS_OUTPUT_DIRECTORY=/app/outputs/elevenlabs

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

COPY requirements.txt ./

RUN python3 -m venv /opt/venv \
    && python -m pip install --upgrade pip \
    && for attempt in 1 2 3; do \
        pip install --timeout 120 --retries 10 -r requirements.txt && break; \
        if [ "$attempt" = "3" ]; then exit 1; fi; \
        echo "pip install failed, retrying in 10 seconds..."; \
        sleep 10; \
    done

COPY content_automation ./content_automation
COPY scripts ./scripts
COPY README.md ./

RUN mkdir -p /app/.data /app/outputs/elevenlabs /app/outputs/videos
RUN chmod +x scripts/entrypoint.sh scripts/notebooklm_auth_mode.sh scripts/notebooklm_py_auth_mode.sh scripts/novnc_display.sh

EXPOSE 6080

CMD ["bash", "scripts/entrypoint.sh"]
