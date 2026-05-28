FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    DATA_DIR=/app/.data \
    ELEVENLABS_OUTPUT_DIRECTORY=/app/outputs/elevenlabs

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        nodejs \
        npm \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt package.json package-lock.json ./

RUN python -m pip install --upgrade pip \
    && pip install -r requirements.txt

RUN npm ci \
    && npx playwright install --with-deps chromium \
    && npm cache clean --force

COPY content_automation ./content_automation
COPY scripts ./scripts
COPY README.md ./

RUN mkdir -p /app/.data /app/outputs/elevenlabs

CMD ["python", "-m", "content_automation.bot"]
