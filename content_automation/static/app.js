import { loadSettingsData, renderSettingsPanel } from "/static/settings.js?v=20260619-plan-feedback";
import { formatButtonState, usageSummary } from "/static/format_usage.js?v=20260617-plan-buttons";
import { canRetryJob, canStopJob, isErrorStatus, isLiveStatus, isStaleJob, jobStatusLabel, jobStatusMessage } from "/static/job_status.js?v=20260617-plan-buttons";
import { withButtonPending } from "/static/action_feedback.js?v=20260618-auto-scripts";
import { bindCreateIdeasPrompt, renderCreateIdeasPrompt } from "/static/create_ideas_prompt.js?v=20260619-auto-idea-scripts";
import { startAutoIdeaScripts } from "/static/idea_auto_scripts.js?v=20260619-auto-idea-scripts";
import { bindScriptReviewDeck, renderScriptReviewDeck } from "/static/script_review_deck.js?v=20260618-review-deck";
import { loadProjectContext, renderProjectSwitcher } from "/static/project_switcher.js?v=20260619-project-context";
import { initialActorUserId } from "/static/session_context.js?v=20260619-project-context";

const tg = window.Telegram?.WebApp;
tg?.ready?.();
tg?.expand?.();

const state = {
  actorUserId: initialActorUserId(tg),
  userId: "",
  projects: [],
  formats: [],
  scripts: [],
  pendingScripts: [],
  jobs: [],
  settings: null,
  avatars: [],
  voices: [],
  thumbnailReferences: [],
  thumbnailFaces: [],
  avatarInserts: [],
  fiveSecondSettings: null,
  ideas: [],
  tab: localStorage.getItem("dima_active_tab") || "formats",
  output: "",
  activeJob: null,
  creating: null,
  pollTimer: null,
  pollFailures: 0,
  autoScriptProjects: new Set(),
};

const tabTitles = {
  formats: "Создать",
  result: "Результат",
  history: "История",
  settings: "Настройки",
};

const $ = (id) => document.getElementById(id);

function setStatus(text) {
  const states = {
    Loading: "loading",
    Login: "idle",
    Ready: "ready",
    Working: "working",
    Opening: "loading",
    Copied: "ready",
    Error: "error",
    "Select text": "error",
    "Сохраняю": "working",
    "Загружаю": "working",
    "Сохранено": "ready",
    "Готово": "ready",
    "Аватары": "working",
    "Голоса": "working",
    "Идеи": "working",
  };
  const labels = {
    Loading: "Загрузка",
    Login: "Вход",
    Ready: "Готово",
    Working: "Создаю",
    Opening: "Открываю",
    Copied: "Скопировано",
    Error: "Ошибка",
    "Select text": "Выделите текст",
  };
  const pill = $("status-pill");
  pill.className = `pill ${states[text] || "ready"}`;
  pill.textContent = labels[text] || text;
}

function escapeHtml(value) {
  return String(value || "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  })[char]);
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...telegramAuthHeaders(), ...(options.headers || {}) },
    ...options,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Запрос не выполнен: ${res.status}`);
  }
  return res.json();
}

function telegramAuthHeaders() {
  return tg?.initData ? { "X-Telegram-Init-Data": tg.initData } : {};
}

async function loadAll() {
  if (!state.actorUserId) {
    stopPolling();
    document.querySelector(".app").classList.add("login-mode");
    $("project-switcher")?.classList.add("hidden");
    $("login").classList.remove("hidden");
    $("formats-panel").classList.add("hidden");
    $("result-panel").classList.add("hidden");
    $("settings-panel").classList.add("hidden");
    $("history-panel").classList.add("hidden");
    setStatus("Login");
    return;
  }
  localStorage.setItem("dima_tg_id", state.actorUserId);
  document.querySelector(".app").classList.remove("login-mode");
  $("login").classList.add("hidden");
  setStatus("Loading");
  await loadProjectContext(projectDeps());
  renderProjectSwitcher(projectDeps());
  const userQuery = encodeURIComponent(state.userId);
  const [formats, scripts, pendingScripts, jobs] = await Promise.all([
    api("/api/formats"),
    api(`/api/scripts/approved?user_id=${userQuery}`),
    api(`/api/scripts/review?user_id=${userQuery}`),
    api(`/api/format-jobs?user_id=${userQuery}&limit=100`),
  ]);
  state.formats = formats;
  state.scripts = scripts;
  state.pendingScripts = pendingScripts;
  state.jobs = jobs;
  await loadSettingsData(settingsDeps(), false);
  state.ideas = await api(`/api/ideas?user_id=${userQuery}&limit=30`).catch(() => []);
  const autoStarted = await autoStartIdeaScriptsIfNeeded();
  renderScripts();
  renderJobs();
  renderSettings();
  renderTabs();
  const liveJob = state.jobs.find((job) => isLiveStatus(job.status));
  if (liveJob) pollJob(liveJob.id);
  setStatus(liveJob ? "Working" : autoStarted ? "Пишу" : "Ready");
}

async function autoStartIdeaScriptsIfNeeded() {
  if (state.scripts.length || state.pendingScripts.length || !state.ideas.length) return false;
  if (state.autoScriptProjects.has(state.userId)) return false;
  state.autoScriptProjects.add(state.userId);
  try {
    const result = await startAutoIdeaScripts(settingsDeps(), { count: 30 });
    return Boolean(result.accepted);
  } catch (error) {
    state.autoScriptMessage = `Не смог автоматически написать сценарии: ${error.message}`;
    showSettingsError(error);
    return false;
  }
}

function projectDeps() {
  return { state, api, escapeHtml, reload: loadAll, stopPolling, showError };
}

function settingsDeps() {
  return { state, api, setStatus, showError: showSettingsError, escapeHtml, refresh: loadAll };
}

function renderSettings() {
  renderSettingsPanel(settingsDeps());
}

function renderTabs() {
  if (!tabTitles[state.tab]) state.tab = "formats";
  localStorage.setItem("dima_active_tab", state.tab);
  $("page-title").textContent = tabTitles[state.tab] || "DIMA";
  document.querySelectorAll(".nav-item").forEach((button) => {
    button.classList.toggle("active", button.dataset.tab === state.tab);
  });
  $("formats-panel").classList.toggle("hidden", state.tab !== "formats");
  $("result-panel").classList.toggle("hidden", state.tab !== "result");
  $("settings-panel").classList.toggle("hidden", state.tab !== "settings");
  $("history-panel").classList.toggle("hidden", state.tab !== "history");
}

function renderScripts() {
  const root = $("scripts");
  if (state.pendingScripts.length) {
    root.innerHTML = renderScriptReviewDeck({ pendingScripts: state.pendingScripts, escapeHtml });
    bindScriptReviewDeck(root, { state, api, setStatus, showError, refresh: loadAll });
    return;
  }
  if (!state.scripts.length) {
    root.innerHTML = renderCreateIdeasPrompt({ ideas: state.ideas, escapeHtml, autoScriptMessage: state.autoScriptMessage });
    bindCreateIdeasPrompt(root, {
      state,
      api,
      setStatus,
      showError,
      refresh: loadAll,
      autoScriptMessage: () => state.autoScriptMessage,
      openIdeas: () => {
        state.tab = "settings";
        state.settingsFormatTab = "ideas";
        renderSettings();
        renderTabs();
      },
    });
    return;
  }
  root.innerHTML = state.scripts.map((script) => `
    <article class="card">
      <h3>#${script.id} ${escapeHtml(script.title || script.hook)}</h3>
      ${window.editorialBadges ? window.editorialBadges(script) : ""}
      <p>${escapeHtml(script.hook)}</p>
      <details class="script-details">
        <summary>Показать сценарий</summary>
        <div class="review-copy">${escapeHtml(script.voiceover || "Текст сценария пуст.")}</div>
        ${script.trigger ? `<p><strong>Триггер:</strong> ${escapeHtml(script.trigger)}</p>` : ""}
        ${script.cta ? `<p><strong>CTA:</strong> ${escapeHtml(script.cta)}</p>` : ""}
      </details>
      <div class="formats">
        ${state.formats.map((format) => `
          <button class="${formatButtonClass(format.key, script.id)}"
            ${formatButtonStateFor(script.id, format.key).disabled ? "disabled" : ""}
            data-script="${script.id}" data-format="${format.key}">
            ${escapeHtml(formatButtonStateFor(script.id, format.key).label)}
          </button>
        `).join("")}
        <button class="${formatButtonClass("all", script.id)}"
          ${formatButtonStateFor(script.id, "all").disabled ? "disabled" : ""}
          data-script="${script.id}" data-format="all">
          ${escapeHtml(formatButtonStateFor(script.id, "all").label)}
        </button>
      </div>
      ${formatUsage(script.id)}
      ${formatReadiness(script.id)}
      <div class="settings-actions">
        <button class="secondary-button danger" type="button" data-delete-script="${escapeHtml(script.id)}">Удалить сценарий</button>
      </div>
    </article>
  `).join("");
  root.querySelectorAll("button[data-script]").forEach((button) => {
    if (state.creating || button.disabled) button.disabled = true;
    button.addEventListener("click", () => createJob(button.dataset.script, button.dataset.format).catch(showError));
  });
  root.querySelectorAll("[data-delete-script]").forEach((button) => {
    button.addEventListener("click", () => deleteScript(button.dataset.deleteScript).catch(showError));
  });
}

async function deleteScript(scriptId) {
  if (!scriptId) return;
  if (!window.confirm("Удалить этот сценарий из проекта?")) return;
  setStatus("Удаляю");
  await api(`/api/scripts/${scriptId}`, {
    method: "DELETE",
    body: JSON.stringify({ user_id: state.userId, action: "delete" }),
  });
  await loadAll();
  setStatus("Удалено");
}

function formatButtonClass(formatKey, scriptId) {
  const buttonState = formatButtonStateFor(scriptId, formatKey);
  const classes = [];
  if (formatKey === "infographic_reels") classes.push("gold");
  if (formatKey === "avatar_horizontal") classes.push("green");
  if (formatKey === "all") classes.push("bundle");
  if (buttonState.creating) classes.push("busy");
  if (buttonState.used) classes.push("used");
  if (buttonState.live) classes.push("live");
  return classes.join(" ");
}

function formatButtonStateFor(scriptId, formatKey) {
  return formatButtonState({
    jobs: state.jobs,
    formats: state.formats,
    scriptId,
    formatKey,
    creating: state.creating,
  });
}

function formatUsage(scriptId) {
  const summary = usageSummary(state.jobs, state.formats, scriptId);
  return summary ? `<div class="usage-summary">${escapeHtml(summary)}</div>` : "";
}

function renderJobs() {
  const root = $("jobs");
  if (!state.jobs.length) {
    root.innerHTML = emptyState("История пока пустая", "Здесь появятся статусы, ошибки и готовые результаты после запуска видео.");
    return;
  }
  root.innerHTML = state.jobs.slice(0, 8).map((job) => `
    <article class="card job-card" data-job="${job.id}">
      <div class="job-row">
        <h3>${escapeHtml(job.title)}</h3>
        ${statusChip(job.status, job)}
      </div>
      <p>${escapeHtml(formatDisplayName(job.format_key, job.task_type))} · сценарий #${job.script_id}</p>
      <p>${escapeHtml(formatDate(job.updated_at || job.created_at))}</p>
      <button class="secondary-button" type="button">Открыть результат</button>
    </article>
  `).join("");
  root.querySelectorAll(".job-card").forEach((card) => {
    card.addEventListener("click", () => showJob(card.dataset.job));
  });
}

async function createJob(scriptId, formatKey) {
  state.creating = { scriptId, formatKey };
  setStatus("Working");
  state.tab = "result";
  state.activeJob = null;
  renderResultPending(scriptId, formatKey);
  $("copy").disabled = true;
  renderTabs();
  renderScripts();
  try {
    const job = await api(`/api/scripts/${scriptId}/format-jobs`, {
      method: "POST",
      body: JSON.stringify({ user_id: state.userId, format_key: formatKey }),
    });
    upsertJob(job);
    renderJobs();
    renderResultJob(job);
    pollJob(job.id);
    setStatus(isErrorStatus(job.status) ? "Error" : "Working");
  } finally {
    state.creating = null;
    renderScripts();
  }
}

async function showJob(jobId) {
  setStatus("Opening");
  const userQuery = encodeURIComponent(state.userId);
  const job = await api(`/api/format-jobs/${jobId}?user_id=${userQuery}`);
  upsertJob(job);
  state.tab = "result";
  renderTabs();
  renderJobs();
  renderResultJob(job);
  if (isLiveStatus(job.status)) pollJob(job.id);
  setStatus(isErrorStatus(job.status) ? "Error" : isLiveStatus(job.status) ? "Working" : "Ready");
}

function pendingMessage(scriptId, formatKey) {
  const format = state.formats.find((item) => item.key === formatKey);
  const label = format?.label || (formatKey === "all" ? "Все форматы" : formatKey);
  const lines = [
    `⏳ Запустил задачу: ${label}`,
    `Сценарий #${scriptId}`,
    "",
    "Можно оставить это окно открытым. Когда сервисы закончат работу, здесь появится результат.",
  ];
  if (formatKey === "infographic_reels") {
    lines.push("", "Для 5-секундного ролика сейчас генерирую карточку через Kie, затем собираю MP4 и отправляю в Telegram.");
  }
  return lines.join("\n");
}

function renderResultPending(scriptId, formatKey) {
  const label = getFormatLabel(formatKey);
  state.output = pendingMessage(scriptId, formatKey);
  $("output").innerHTML = `
    <article class="result-card working">
      <div class="result-head">
        <div>
          <span class="eyebrow">Создание запущено</span>
          <h3>${escapeHtml(label)}</h3>
        </div>
        ${statusChip("queued")}
      </div>
      <ol class="timeline">
        <li class="active">Создаю задачу</li>
        <li>Генерация Kie / HeyGen</li>
        <li>Сборка видео</li>
        <li>Отправка в Telegram</li>
      </ol>
      <p>Сценарий #${escapeHtml(scriptId)}. Можно оставить окно открытым: статус будет обновляться здесь.</p>
    </article>
  `;
}

function renderResultJob(job) {
  state.activeJob = job;
  state.output = resultCopyText(job);
  $("copy").disabled = !state.output;
  $("output").innerHTML = `
    <article class="result-card ${escapeHtml(job.status || "")}">
      <div class="result-head">
        <div>
          <span class="eyebrow">Задача #${job.id}</span>
          <h3>${escapeHtml(formatDisplayName(job.format_key, job.task_type))}</h3>
        </div>
        ${statusChip(job.status, job)}
      </div>
      ${renderResultMeta(job)}
      ${renderResultBody(job)}
      ${renderResultActions(job)}
    </article>
  `;
}

function renderResultMeta(job) {
  return `
    <div class="result-meta">
      <span>Сценарий #${job.script_id}</span>
      <span>${escapeHtml(formatDate(job.updated_at || job.created_at))}</span>
      ${job.external_task_id ? `<span>TG/ID: ${escapeHtml(job.external_task_id)}</span>` : ""}
    </div>
  `;
}

function renderResultBody(job) {
  if (isErrorStatus(job.status)) {
    return `<div class="result-error">${escapeHtml(job.error || job.output_text || "Задача завершилась с ошибкой.")}</div>`;
  }
  if (isLiveStatus(job.status)) {
    return `
      <ol class="timeline">
        <li class="done">Задача создана</li>
        <li class="active">${isStaleJob(job) ? "Давно без обновлений" : job.status === "queued" ? "Ожидает запуска" : "Генерация и отправка"}</li>
        <li>Готовый файл придёт в Telegram</li>
      </ol>
      <p>${escapeHtml(jobStatusMessage(job))}</p>
    `;
  }
  return `
    <div class="result-success">Готово. Видео отправлено в Telegram${job.output_url ? " и сохранено в файле." : "."}</div>
    ${job.output_url ? `<p class="file-path">${escapeHtml(job.output_url)}</p>` : ""}
    ${safeResultText(job) ? `<pre class="result-text">${escapeHtml(safeResultText(job))}</pre>` : ""}
  `;
}

function safeResultText(job) {
  const text = String(job.output_text || "").trim();
  if (!text) return "";
  if (text.includes("Turan format:") || text.includes("Turan text-source input JSON")) {
    return "Техническое описание старой задачи скрыто. Готовый файл и статус доступны выше.";
  }
  return text;
}

function renderResultActions(job) {
  const parts = [`<button class="secondary-button" type="button" data-refresh-job="${job.id}">Обновить статус</button>`];
  if (canRetryJob(job)) parts.push(`<button class="secondary-button" type="button" data-retry-job="${job.id}">Повторить</button>`);
  if (canStopJob(job)) parts.push(`<button class="secondary-button danger" type="button" data-stop-job="${job.id}">Остановить</button>`);
  if (job.output_url) parts.push(`<button class="secondary-button" type="button" data-copy-path>Скопировать путь</button>`);
  return `<div class="result-actions">${parts.join("")}</div>`;
}

function statusChip(status, job = null) {
  const label = job && isStaleJob(job) ? "зависло?" : jobStatusLabel(status);
  return `<span class="status-chip ${escapeHtml(status || "ready")}">${escapeHtml(label)}</span>`;
}

function formatDisplayName(formatKey, fallback) {
  return getFormatLabel(formatKey) || fallback || formatKey || "Формат";
}

function getFormatLabel(formatKey) {
  if (formatKey === "all") return "Все форматы";
  return state.formats.find((item) => item.key === formatKey)?.label || formatKey;
}

function formatDate(value) {
  if (!value) return "";
  const date = new Date(value.includes("T") ? value : value.replace(" ", "T"));
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("ru-RU", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

function emptyState(title, text) {
  return `<article class="empty-state"><h3>${escapeHtml(title)}</h3><p>${escapeHtml(text)}</p></article>`;
}

function formatReadiness() {
  const items = [];
  if (state.settings?.elevenlabs_voice_name) items.push(`Голос: ${state.settings.elevenlabs_voice_name}`);
  if (state.settings?.heygen_avatar_name || state.settings?.heygen_vertical_avatar_name) items.push("Аватары выбраны");
  if (state.thumbnailFaces?.length) items.push(`Лицо для обложек: ${state.thumbnailFaces.length}`);
  if (state.thumbnailReferences?.length) items.push(`Стиль-референсы: ${state.thumbnailReferences.length}`);
  if (!items.length) return "";
  return `<div class="readiness">${items.map((item) => `<span>${escapeHtml(item)}</span>`).join("")}</div>`;
}

function resultCopyText(job) {
  return [
    `Задача #${job.id}: ${formatDisplayName(job.format_key, job.task_type)}`,
    `Статус: ${jobStatusLabel(job.status)}`,
    job.output_url ? `Файл: ${job.output_url}` : "",
    job.error ? `Ошибка: ${job.error}` : "",
    job.output_text || "",
  ].filter(Boolean).join("\n");
}

function upsertJob(job) {
  state.jobs = [job, ...state.jobs.filter((item) => item.id !== job.id)];
}

function liveJob() {
  return state.jobs.find((job) => isLiveStatus(job.status));
}

function statusForJob(job) {
  if (!job) return "Ready";
  if (isErrorStatus(job.status)) return "Error";
  return isLiveStatus(job.status) ? "Working" : "Ready";
}

function pollJob(jobId) {
  stopPolling();
  state.pollFailures = 0;
  state.pollTimer = window.setInterval(async () => {
    try {
      const userQuery = encodeURIComponent(state.userId);
      const job = await api(`/api/format-jobs/${jobId}?user_id=${userQuery}`);
      state.pollFailures = 0;
      upsertJob(job);
      renderJobs();
      if (state.tab === "result") renderResultJob(job);
      setStatus(statusForJob(job));
      if (!isLiveStatus(job.status)) stopPolling();
    } catch (error) {
      state.pollFailures += 1;
      console.warn("Job polling failed", error);
      if (state.pollFailures < 3) {
        setStatus(liveJob() ? "Working" : "Loading");
        return;
      }
      stopPolling();
      showError(error);
    }
  }, 5000);
}

function stopPolling() {
  if (!state.pollTimer) return;
  window.clearInterval(state.pollTimer);
  state.pollTimer = null;
}

$("save-user").addEventListener("click", () => {
  state.actorUserId = $("tg-id").value.trim();
  loadAll().catch(showError);
});

$("refresh").addEventListener("click", () => loadAll().catch(showError));
$("refresh-settings").addEventListener("click", () => loadSettingsData(settingsDeps()).catch(showSettingsError));

document.querySelectorAll(".nav-item").forEach((button) => {
  button.addEventListener("click", () => {
    state.tab = button.dataset.tab;
    renderTabs();
  });
});

$("logout").addEventListener("click", () => {
  if (!window.confirm("Выйти из аккаунта?")) return;
  stopPolling();
  localStorage.removeItem("dima_tg_id");
  state.actorUserId = "";
  state.userId = "";
  $("project-switcher")?.classList.add("hidden");
  $("tg-id").value = "";
  document.querySelector(".app").classList.add("login-mode");
  $("login").classList.remove("hidden");
  ["formats-panel", "result-panel", "settings-panel", "history-panel"].forEach((id) => $(id).classList.add("hidden"));
  setStatus("Login");
});

$("copy").addEventListener("click", async () => {
  try {
    await copyText(state.output);
    setStatus("Copied");
    setTimeout(() => setStatus("Ready"), 1200);
  } catch (error) {
    const range = document.createRange();
    range.selectNodeContents($("output"));
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
    setStatus("Select text");
  }
});

$("output").addEventListener("click", (event) => {
  const refresh = event.target.closest("[data-refresh-job]");
  if (refresh) withButtonPending(refresh, () => showJob(refresh.dataset.refreshJob), { pendingLabel: "Обновляю..." }).catch(showError);
  const retry = event.target.closest("[data-retry-job]");
  if (retry) withButtonPending(retry, () => retryJob(retry.dataset.retryJob), { pendingLabel: "Повторяю..." }).catch(showError);
  const stop = event.target.closest("[data-stop-job]");
  if (stop) withButtonPending(stop, () => stopJob(stop.dataset.stopJob), { pendingLabel: "Останавливаю..." }).catch(showError);
  const copyPath = event.target.closest("[data-copy-path]");
  if (!copyPath || !state.activeJob?.output_url) return;
  withButtonPending(
    copyPath,
    () => copyText(state.activeJob.output_url),
    { pendingLabel: "Копирую...", doneLabel: "Путь скопирован" },
  ).catch(showError);
});

async function retryJob(jobId) {
  setStatus("Working");
  const userQuery = encodeURIComponent(state.userId);
  const job = await api(`/api/format-jobs/${jobId}/retry?user_id=${userQuery}`, { method: "POST" });
  upsertJob(job);
  renderJobs();
  renderResultJob(job);
  pollJob(job.id);
}

async function stopJob(jobId) {
  setStatus("Working");
  const userQuery = encodeURIComponent(state.userId);
  const job = await api(`/api/format-jobs/${jobId}/mark-failed?user_id=${userQuery}`, { method: "POST" });
  upsertJob(job);
  renderJobs();
  renderResultJob(job);
  setStatus("Error");
}

function showError(error) {
  console.error(error);
  state.creating = null;
  setStatus("Error");
  state.tab = "result";
  state.output = error.message || String(error);
  $("output").innerHTML = `<article class="result-card failed"><div class="result-error">${escapeHtml(state.output)}</div></article>`;
  $("copy").disabled = !state.output;
  renderTabs();
  renderScripts();
}

function showSettingsError(error) {
  console.error(error);
  state.creating = null;
  const message = error.message || String(error);
  state.settingsLoadWarnings = [message];
  setStatus(liveJob() ? "Working" : "Error");
  renderSettingsPanel(settingsDeps());
}

async function copyText(text) {
  if (!navigator.clipboard?.writeText) throw new Error("Буфер обмена недоступен");
  await navigator.clipboard.writeText(text);
}

loadAll().catch(showError);
