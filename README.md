# Бот апрува контента из NotebookLM

Telegram-бот для контент-автоматизации:

- берет сценарии из NotebookLM через `notebooklm-mcp@latest`;
- пишет в стиле автора;
- использует high-ticket воронку в духе Alex Hormozi;
- отправляет сценарии в Telegram на принятие или отклонение;
- хранит банк одобренных сценариев для дальнейшего производства видео;
- после апрува озвучивает текст через ElevenLabs, отправляет аудио в активный HeyGen avatar и присылает готовый ролик в ту же группу/тему Telegram;
- дает Telegram-кнопки выбора HeyGen avatar с preview и ElevenLabs voice с preview;
- накладывает локально сохраненную плашку на финальное видео через `ffmpeg`;
- перед генерацией передает NotebookLM последние темы/хуки и фильтрует похожие повторы перед сохранением;
- дает кнопки настройки контекста оффера, микса CTA, голоса автора и NotebookLM-базы.

## Установка

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Заполни `.env`:

```text
TELEGRAM_BOT_TOKEN=...
NOTEBOOKLM_CLI_COMMAND=notebooklm
NOTEBOOKLM_BACKEND=mcp
NOTEBOOKLM_MCP_COMMAND=npx --yes notebooklm-mcp@latest
NOTEBOOKLM_MCP_TIMEOUT_SECONDS=900
NOTEBOOKLM_PY_STORAGE_PATH=/app/.data/notebooklm-py/storage_state.json
NOTEBOOKLM_SHORT_BATCH_SIZE=1
DEFAULT_NOTEBOOK_ID=...
DATA_DIR=.data
APP_MODE=bot
ELEVENLABS_API_KEY=...
ELEVENLABS_MCP_OUTPUT_MODE=files
ELEVENLABS_OUTPUT_DIRECTORY=outputs/elevenlabs
VIDEO_OUTPUT_DIRECTORY=outputs/videos
VIDEO_KEEP_DAYS=14
POST_HEYGEN_VISUALS_ENABLED=true
POST_HEYGEN_COVER_SECONDS=0.10
POST_HEYGEN_BROLL_COUNT=3
POST_HEYGEN_BROLL_SECONDS=1.2
KIE_API_KEY=...
KIE_BASE_URL=https://api.kie.ai
KIE_UPLOAD_BASE_URL=https://kieai.redpandaai.co
KIE_IMAGE_MODEL=gpt-image-2
KIE_IMAGE_ASPECT_RATIO=9:16
KIE_IMAGE_RESOLUTION=1K
MONTAGE_RENDERER=auto
HYPERFRAMES_PROJECT_DIR=/app/hyperframes-auto
REMOTION_PROJECT_DIR=
MONTAGE_RENDER_TIMEOUT_SECONDS=3600
MONTAGE_MAX_SCENES=8
ELEVENLABS_VOICE_ID=
ELEVENLABS_VOICE_NAME=Dima Kubrak 1
ELEVENLABS_MODEL_ID=eleven_multilingual_v2
ELEVENLABS_SPEED=1.05
ELEVENLABS_STABILITY=0.90
ELEVENLABS_SIMILARITY_BOOST=0.97
ELEVENLABS_STYLE=0.0
ELEVENLABS_LANGUAGE=en
HEYGEN_API_KEY=...
HEYGEN_API_BASE_URL=https://api.heygen.com
HEYGEN_UPLOAD_BASE_URL=https://upload.heygen.com
HEYGEN_PRIVATE_AVATARS_ONLY=true
HEYGEN_ASPECT_RATIO=9:16
HEYGEN_RESOLUTION=720p
HEYGEN_OUTPUT_FORMAT=mp4
HEYGEN_VIDEO_POLL_SECONDS=15
HEYGEN_VIDEO_TIMEOUT_SECONDS=900
```

NotebookLM MCP должен быть авторизован. При первом запуске авторизации:

```bash
npx notebooklm-mcp@latest
```

Затем используйте MCP-инструмент `setup_auth`, либо заранее авторизуйте профиль через браузерную настройку. В этом проекте MCP уже проверен с выбранной базой.

## ElevenLabs MCP

Официальный MCP-сервер ElevenLabs установлен как Python-пакет `elevenlabs-mcp`.

Для работы нужен API key ElevenLabs:

```text
ELEVENLABS_API_KEY=...
```

Локальную MCP-конфигурацию можно вывести так:

```bash
python scripts/elevenlabs_mcp_config.py
```

Она использует сервер из `.venv` и сохраняет сгенерированные файлы в `outputs/elevenlabs`.

После нажатия `Принять` бот отправляет в ElevenLabs только поле `voiceover`, создает mp3, затем передает этот файл в активный HeyGen avatar. Когда ролик готов, бот присылает видео в ту же группу и тему Telegram. Если HeyGen не настроен или avatar не выбран, бот присылает только озвучку и пишет, чего не хватает.

Через `/settings` можно открыть список голосов ElevenLabs, прослушать preview и активировать нужный voice. При наличии `ELEVENLABS_VOICE_ID` он используется как дефолт.

## HeyGen

Для работы нужен API key HeyGen:

```text
HEYGEN_API_KEY=...
HEYGEN_PRIVATE_AVATARS_ONLY=true
```

Через `/settings` открой `🎭 Аватар HeyGen`. Бот покажет avatars с preview-картинкой или ссылкой на preview video, навигацией и кнопкой `Активировать`. Активный avatar используется для всех следующих одобренных short-сценариев.

По умолчанию бот запрашивает только приватные avatars аккаунта:

```text
HEYGEN_PRIVATE_AVATARS_ONLY=true
```

Навигация по avatars редактирует одну и ту же Telegram-карточку, чтобы не засорять группу.

## Плашки на видео

Через `/settings` можно отдельно настроить:

```text
Плашка Shorts
Плашка YouTube
```

Бот принимает PNG/JPG/WebP файлом или фото и хранит плашку локально на сервере в `DATA_DIR/overlays`. Для каждой плашки задается процент появления: например, `70` значит, что плашка появится с 70% хронометража и останется до конца видео.

После HeyGen бот скачивает mp4 в `VIDEO_OUTPUT_DIRECTORY`. В Docker image уже встроен Turan-style `hyperframes-auto`, поэтому для production достаточно оставить `HYPERFRAMES_PROJECT_DIR=/app/hyperframes-auto` и `MONTAGE_RENDERER=auto`. DIMA строит `scene-plan.generated.json` и `scene-word-cues.generated.json` из одобренного NotebookLM-сценария и запускает Hyperframes через `npm run render:auto`. Если Hyperframes не настроен или упал, DIMA генерирует через KIE cover-картинку и карточки-перебивки, накладывает cover на первые `POST_HEYGEN_COVER_SECONDS` (`0.10` по умолчанию), распределяет перебивки поверх видео, затем накладывает настроенную плашку через `ffmpeg` и отправляет финальный mp4 в Telegram как файл/document.

Локальные видео чистятся автоматически. По умолчанию:

```text
VIDEO_KEEP_DAYS=14
```

Оригинал HeyGen удаляется сразу после успешного наложения плашки, финальные mp4 хранятся локально до 14 дней.

## Запуск

```bash
python -m content_automation.bot
```

## Docker / Coolify

Для Coolify лучше выбирать build pack `Dockerfile`.

Приложение работает как Telegram worker через polling, поэтому HTTP-порт ему не нужен.
В обычном режиме оно также поднимает mini app/API на `WEB_PORT` для Turan-форматов одобренных сценариев.

Локально можно проверить так:

```bash
docker compose up --build
```

В Coolify добавь переменные окружения из `.env.example`. Минимально нужны:

```text
TELEGRAM_BOT_TOKEN=...
NOTEBOOKLM_BACKEND=mcp
NOTEBOOKLM_MCP_COMMAND=npx --yes notebooklm-mcp@latest
NOTEBOOKLM_MCP_TIMEOUT_SECONDS=900
NOTEBOOKLM_PY_STORAGE_PATH=/app/.data/notebooklm-py/storage_state.json
NOTEBOOKLM_SHORT_BATCH_SIZE=1
DEFAULT_NOTEBOOK_ID=...
DATA_DIR=/app/.data
WEB_PORT=8000
MINIAPP_URL=https://your-miniapp-domain.example
ELEVENLABS_API_KEY=...
ELEVENLABS_OUTPUT_DIRECTORY=/app/outputs/elevenlabs
VIDEO_OUTPUT_DIRECTORY=/app/outputs/videos
VIDEO_KEEP_DAYS=14
POST_HEYGEN_VISUALS_ENABLED=true
POST_HEYGEN_COVER_SECONDS=0.10
POST_HEYGEN_BROLL_COUNT=3
POST_HEYGEN_BROLL_SECONDS=1.2
HEYGEN_API_KEY=...
```

На VPS надежнее держать:

```text
NOTEBOOKLM_SHORT_BATCH_SIZE=1
```

Так бот делает 10 маленьких запросов вместо одного тяжелого JSON-ответа. Если NotebookLM на сервере работает стабильно, можно поднять до `2` или `4`.

Если хочешь заменить браузерный MCP на более прямой неофициальный Python-клиент NotebookLM, включи:

```text
NOTEBOOKLM_BACKEND=py
NOTEBOOKLM_PY_STORAGE_PATH=/app/.data/notebooklm-py/storage_state.json
```

Этот режим использует `notebooklm-py` и отдельный сохраненный Google storage state. Если Google изменит внутренние NotebookLM RPC, верни `NOTEBOOKLM_BACKEND=mcp`.
Для `py` режима в `DEFAULT_NOTEBOOK_ID` или `/set_notebook` используй реальный URL NotebookLM или UUID из URL, а не локальный alias из MCP-библиотеки.

Для постоянного хранения базы и аудио в Coolify стоит добавить volumes:

```text
/app/.data
/app/outputs
```

Важно: NotebookLM MCP использует браузерную авторизацию. На сервере может понадобиться отдельно пройти/перенести авторизацию NotebookLM для контейнера.

### Авторизация NotebookLM на сервере

Для первого Google login через старый MCP включи временный auth-mode:

```text
APP_MODE=notebooklm-auth
INSTALL_AUTH_TOOLS=true
```

`INSTALL_AUTH_TOOLS=true` нужен именно при сборке образа. После изменения этой переменной пересобери контейнер, а не только перезапусти его.

Для первого Google login через `notebooklm-py` включи:

```text
APP_MODE=notebooklm-py-auth
INSTALL_AUTH_TOOLS=true
NOTEBOOKLM_PY_STORAGE_PATH=/app/.data/notebooklm-py/storage_state.json
```

После запуска открой noVNC URL и в Coolify Terminal выполни команду, которую покажет контейнер:

```text
DISPLAY=:99 notebooklm --storage "/app/.data/notebooklm-py/storage_state.json" login
```

Залогинься в браузере noVNC. Когда NotebookLM откроется, вернись в терминал и нажми Enter, чтобы сохранить session.

В Coolify нужно открыть порт:

```text
6080
```

После деплоя открой noVNC URL, залогинься в Google/NotebookLM в браузере внутри контейнера, затем верни:

```text
APP_MODE=bot
```

и сделай redeploy. Профиль сохранится в volume:

```text
/root/.config/notebooklm-mcp
/root/.local/share/notebooklm-mcp
```

## Команды Telegram

```text
/set_notebook <id или https://notebooklm.google.com/notebook/...>
/set_style <описание разговорного стиля автора>
/settings
/bank
/refill
/review
/daily_scripts
/daily_scripts фокус: PPC и cash flow
/youtube_script
/vizard <youtube_url>
/formats
/formats <script_id>
/status
```

## Vizard YouTube-нарезка

Добавь Vizard API key:

```text
VIZARD_API_KEY=<ключ из Vizard workspace API>
VIZARD_API_BASE_URL=https://elb-api.vizard.ai/hvizard-server-front/open-api/v1
VIZARD_POLL_SECONDS=30
VIZARD_TIMEOUT_SECONDS=3600
```

После этого можно отправить боту обычную YouTube-ссылку или команду:

```text
/vizard https://www.youtube.com/watch?v=...
```

Бот создаст Vizard project, дождется готовых клипов, скачает временные `videoUrl` и отправит ролики обратно в тот же чат/тред.

Настройки Vizard доступны в `/settings` и Mini App:

- формат финального ролика: `9:16`, `16:9`, `1:1`, `4:5`
- длина единицы ролика: `auto`, `<30s`, `30-60s`, `60-90s`, `90s-3min`
- язык видео
- максимум клипов
- keywords для отбора тем
- субтитры, headline/hook, emoji, highlight words, auto B-roll, remove silence
- custom `templateId`

## Mini app / Turan-форматы

После `Принять` бот показывает кнопки Turan-форматов для одобренного текста из NotebookLM. Если задан `MINIAPP_URL`, в главном меню появится кнопка `Mini App`.

Mini app/API поднимаются вместе с ботом:

```text
WEB_HOST=0.0.0.0
WEB_PORT=8000
MINIAPP_URL=https://<твой Coolify domain>
TURAN_API_BASE_URL=https://<turan-api-domain>
TURAN_API_TELEGRAM_ID=
```

Если `TURAN_API_BASE_URL` задан, mini app сразу отправляет созданные payloads в Turan `POST /tasks/{telegram_id}`. Если переменная пустая, job сохраняется локально и показывает готовый JSON для ручной отправки. `TURAN_API_TELEGRAM_ID` можно оставить пустым, тогда используется Telegram id пользователя mini app.

API:

```text
GET /health
GET /api/formats
GET /api/scripts/approved?user_id=<telegram_id>
POST /api/scripts/<script_id>/format-jobs
GET /api/format-jobs?user_id=<telegram_id>
```

Каждый созданный job содержит `raw.turan_task_input` с входом под сценарный текст:

```json
{
  "source_url": "notebooklm-script://123",
  "type": "avatar_instagram",
  "source_title": "Approved script title",
  "factual_outline": "Hook/angle/source facts",
  "script_text": "Approved NotebookLM voiceover",
  "script_meta": {
    "source": "notebooklm_approved_script",
    "source_script_id": 123,
    "format_key": "avatar_reels"
  }
}
```

## Логика банка сценариев

1. `/refill` держит банк одобренных сценариев выше минимального запаса в 5 сценариев.
2. Если одобренных 5 или меньше и очередь на проверку пустая, бот просит NotebookLM создать 10 новых кандидатов.
3. `/review` открывает одну карточку проверки с прогрессом вроде `Сценарий 1/10`.
4. `Принять` переносит сценарий в банк одобренных и обновляет эту же карточку на следующий сценарий.
5. После принятия бот показывает кнопки Turan-форматов: аватар Reels, золотой фон 5 сек., инфографика Reels, аватар YouTube.
6. `/formats` повторно открывает Turan-форматы для последнего одобренного short-сценария, а `/formats <script_id>` — для конкретного сценария.
7. `Отклонить` убирает сценарий из очереди и обновляет эту же карточку на следующий сценарий.
8. Следующий этап автоматизации должен брать одобренные сценарии для видео и помечать их как использованные.

Vizard в Turan остается отдельным URL/video workflow. NotebookLM text-source payloads идут в avatar/5s/infographic форматы и не меняют Vizard-ветку.

## Настройки оффера и CTA

Используй `/settings` в Telegram. Бот покажет кнопки:

```text
Аватар HeyGen
Голос ElevenLabs
Плашка Shorts
Плашка YouTube
Vizard нарезка
Контекст оффера
Голос автора
Микс CTA
База NotebookLM
Показать текущие
```

CTA не вставляется фиксированным шаблоном. Контекст оффера и микс CTA передаются в NotebookLM, чтобы он писал CTA под конкретный сценарий:

```text
50% none, 50% soft, 0% direct
```

Прямой CTA сейчас отключен: бот не должен просить apply/book a call.
