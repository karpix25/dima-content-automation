import { loadSettingsData, renderSettingsPanel } from "/static/settings.js";

const tg = window.Telegram?.WebApp;
tg?.ready?.();
tg?.expand?.();

const state = {
  userId: new URLSearchParams(window.location.search).get("tg_id")
    || String(tg?.initDataUnsafe?.user?.id || "")
    || localStorage.getItem("dima_tg_id")
    || "",
  formats: [],
  scripts: [],
  jobs: [],
  settings: null,
  avatars: [],
  voices: [],
  thumbnailReferences: [],
  thumbnailFaces: [],
  avatarInserts: [],
  fiveSecondSettings: null,
  tab: localStorage.getItem("dima_active_tab") || "formats",
  output: "",
};

const tabTitles = {
  formats: "Форматы",
  result: "Результат",
  history: "История",
  settings: "Настройки",
};

const $ = (id) => document.getElementById(id);

function setStatus(text) {
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
  $("status-pill").textContent = labels[text] || text;
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
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Запрос не выполнен: ${res.status}`);
  }
  return res.json();
}

async function loadAll() {
  if (!state.userId) {
    document.querySelector(".app").classList.add("login-mode");
    $("login").classList.remove("hidden");
    $("formats-panel").classList.add("hidden");
    $("result-panel").classList.add("hidden");
    $("settings-panel").classList.add("hidden");
    $("history-panel").classList.add("hidden");
    setStatus("Login");
    return;
  }
  localStorage.setItem("dima_tg_id", state.userId);
  document.querySelector(".app").classList.remove("login-mode");
  $("login").classList.add("hidden");
  setStatus("Loading");
  const userQuery = encodeURIComponent(state.userId);
  const [formats, scripts, jobs] = await Promise.all([
    api("/api/formats"),
    api(`/api/scripts/approved?user_id=${userQuery}`),
    api(`/api/format-jobs?user_id=${userQuery}`),
  ]);
  state.formats = formats;
  state.scripts = scripts;
  state.jobs = jobs;
  await loadSettingsData(settingsDeps(), false);
  renderScripts();
  renderJobs();
  renderSettings();
  renderTabs();
  setStatus("Ready");
}

function settingsDeps() {
  return { state, api, setStatus, showError, escapeHtml };
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
  if (!state.scripts.length) {
    root.innerHTML = `<p>Пока нет одобренных сценариев. Сначала одобрите сценарий в Telegram.</p>`;
    return;
  }
  root.innerHTML = state.scripts.map((script) => `
    <article class="card">
      <h3>#${script.id} ${escapeHtml(script.title || script.hook)}</h3>
      <p>${escapeHtml(script.hook)}</p>
      <div class="formats">
        ${state.formats.map((format) => `
          <button class="${formatButtonClass(format.key)}"
            data-script="${script.id}" data-format="${format.key}">
            ${escapeHtml(format.label)}
          </button>
        `).join("")}
        <button class="bundle" data-script="${script.id}" data-format="all">Все форматы</button>
      </div>
    </article>
  `).join("");
  root.querySelectorAll("button[data-script]").forEach((button) => {
    button.addEventListener("click", () => createJob(button.dataset.script, button.dataset.format));
  });
}

function formatButtonClass(formatKey) {
  if (formatKey === "infographic_reels") return "gold";
  if (formatKey === "avatar_horizontal") return "green";
  return "";
}

function renderJobs() {
  const root = $("jobs");
  if (!state.jobs.length) {
    root.innerHTML = `<p>Пока нет созданных форматов.</p>`;
    return;
  }
  root.innerHTML = state.jobs.slice(0, 8).map((job) => `
    <article class="card job-card" data-job="${job.id}">
      <h3>${escapeHtml(job.title)}</h3>
      <p>${escapeHtml(job.task_type)} · сценарий #${job.script_id}</p>
    </article>
  `).join("");
  root.querySelectorAll(".job-card").forEach((card) => {
    card.addEventListener("click", () => showJob(card.dataset.job));
  });
}

async function createJob(scriptId, formatKey) {
  setStatus("Working");
  const job = await api(`/api/scripts/${scriptId}/format-jobs`, {
    method: "POST",
    body: JSON.stringify({ user_id: state.userId, format_key: formatKey }),
  });
  state.output = job.output_text;
  $("output").textContent = state.output;
  $("copy").disabled = false;
  state.tab = "result";
  await loadAll();
  setStatus("Ready");
}

async function showJob(jobId) {
  setStatus("Opening");
  const userQuery = encodeURIComponent(state.userId);
  const job = await api(`/api/format-jobs/${jobId}?user_id=${userQuery}`);
  state.output = job.output_text;
  $("output").textContent = state.output;
  $("copy").disabled = false;
  setStatus("Ready");
}

$("save-user").addEventListener("click", () => {
  state.userId = $("tg-id").value.trim();
  loadAll().catch(showError);
});

$("refresh").addEventListener("click", () => loadAll().catch(showError));
$("refresh-settings").addEventListener("click", () => loadSettingsData(settingsDeps()).catch(showError));

document.querySelectorAll(".nav-item").forEach((button) => {
  button.addEventListener("click", () => {
    state.tab = button.dataset.tab;
    renderTabs();
  });
});

$("logout").addEventListener("click", () => {
  if (!window.confirm("Выйти из аккаунта?")) return;
  localStorage.removeItem("dima_tg_id");
  state.userId = "";
  $("tg-id").value = "";
  document.querySelector(".app").classList.add("login-mode");
  $("login").classList.remove("hidden");
  $("formats-panel").classList.add("hidden");
  $("result-panel").classList.add("hidden");
  $("settings-panel").classList.add("hidden");
  $("history-panel").classList.add("hidden");
  setStatus("Login");
});

$("copy").addEventListener("click", async () => {
  try {
    if (!navigator.clipboard?.writeText) throw new Error("Буфер обмена недоступен");
    await navigator.clipboard.writeText(state.output);
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

function showError(error) {
  console.error(error);
  setStatus("Error");
  $("output").textContent = error.message || String(error);
}

loadAll().catch(showError);
