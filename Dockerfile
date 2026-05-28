FROM mcr.microsoft.com/playwright:v1.60.0-noble

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
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
        fluxbox \
        git \
        novnc \
        python3 \
        python3-pip \
        python3-venv \
        websockify \
        x11vnc \
        xvfb \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./

RUN python3 -m venv /opt/venv \
    && python -m pip install --upgrade pip \
    && pip install -r requirements.txt

COPY content_automation ./content_automation
COPY scripts ./scripts
COPY README.md ./

RUN mkdir -p /app/.data /app/outputs/elevenlabs /app/outputs/videos
RUN chmod +x scripts/entrypoint.sh scripts/notebooklm_auth_mode.sh

EXPOSE 6080

CMD ["bash", "scripts/entrypoint.sh"]
