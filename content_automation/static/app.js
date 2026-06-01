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
  tab: "formats",
  output: "",
};

const $ = (id) => document.getElementById(id);

function setStatus(text) {
  $("status-pill").textContent = text;
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
    throw new Error(detail.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

async function loadAll() {
  if (!state.userId) {
    $("login").classList.remove("hidden");
    setStatus("Login");
    return;
  }
  localStorage.setItem("dima_tg_id", state.userId);
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
  await loadSettings(false);
  renderScripts();
  renderJobs();
  renderSettings();
  renderTabs();
  setStatus("Ready");
}

async function loadSettings(render = true) {
  if (!state.userId) return;
  state.settings = await api(`/api/settings?user_id=${encodeURIComponent(state.userId)}`);
  if (render) renderSettings();
}

function renderTabs() {
  document.querySelectorAll(".tab").forEach((button) => {
    button.classList.toggle("active", button.dataset.tab === state.tab);
  });
  $("formats-panel").classList.toggle("hidden", state.tab !== "formats");
  $("settings-panel").classList.toggle("hidden", state.tab !== "settings");
  $("history-panel").classList.toggle("hidden", state.tab !== "history");
}

function renderScripts() {
  const root = $("scripts");
  if (!state.scripts.length) {
    root.innerHTML = `<p>No approved scripts yet. Approve one in Telegram first.</p>`;
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
        <button class="bundle" data-script="${script.id}" data-format="all">All formats</button>
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
    root.innerHTML = `<p>No generated format jobs yet.</p>`;
    return;
  }
  root.innerHTML = state.jobs.slice(0, 8).map((job) => `
    <article class="card job-card" data-job="${job.id}">
      <h3>${escapeHtml(job.title)}</h3>
      <p>${escapeHtml(job.task_type)} · script #${job.script_id}</p>
    </article>
  `).join("");
  root.querySelectorAll(".job-card").forEach((card) => {
    card.addEventListener("click", () => showJob(card.dataset.job));
  });
}

function renderSettings() {
  const root = $("settings");
  const settings = state.settings;
  if (!settings) {
    root.innerHTML = `<p>Settings are loading.</p>`;
    return;
  }
  root.innerHTML = `
    ${renderActiveAssets(settings)}
    ${renderTextSettings(settings)}
    ${renderOverlaySettings(settings)}
  `;
  bindSettingsEvents(root);
}

function renderActiveAssets(settings) {
  return `
    <section class="settings-section">
      <h3>HeyGen avatar</h3>
      <p>${escapeHtml(settings.heygen_avatar_name || "Not selected")}</p>
      <code>${escapeHtml(settings.heygen_avatar_id || "")}</code>
      <div class="settings-actions">
        <button data-action="load-avatars">Load avatars</button>
      </div>
      <div id="avatars" class="asset-list">${renderAvatarList()}</div>
    </section>
    <section class="settings-section">
      <h3>ElevenLabs voice</h3>
      <p>${escapeHtml(settings.elevenlabs_voice_name || "Not selected")}</p>
      <code>${escapeHtml(settings.elevenlabs_voice_id || "")}</code>
      <div class="settings-actions">
        <button data-action="load-voices">Load voices</button>
      </div>
      <div id="voices" class="asset-list">${renderVoiceList()}</div>
    </section>
  `;
}

function renderAvatarList() {
  if (!state.avatars.length) return "";
  return state.avatars.map((avatar) => `
    <article class="asset-card">
      ${avatar.preview_image_url ? `<img src="${escapeHtml(avatar.preview_image_url)}" alt="" />` : ""}
      <div>
        <strong>${escapeHtml(avatar.name)}</strong>
        <small>${escapeHtml(avatar.id)}</small>
      </div>
      <button data-action="select-avatar" data-id="${escapeHtml(avatar.id)}" data-name="${escapeHtml(avatar.name)}">Use</button>
    </article>
  `).join("");
}

function renderVoiceList() {
  if (!state.voices.length) return "";
  return state.voices.map((voice) => `
    <article class="asset-card text-card">
      <div>
        <strong>${escapeHtml(voice.name)}</strong>
        <small>${escapeHtml(voice.category || voice.id)}</small>
      </div>
      ${voice.preview_url ? `<a href="${escapeHtml(voice.preview_url)}" target="_blank" rel="noreferrer">Preview</a>` : ""}
      <button data-action="select-voice" data-id="${escapeHtml(voice.id)}" data-name="${escapeHtml(voice.name)}">Use</button>
    </article>
  `).join("");
}

function renderTextSettings(settings) {
  const rows = [
    ["notebook_id", "NotebookLM ID", settings.notebook_id || ""],
    ["author_style", "Author voice", settings.author_style || ""],
    ["offer_context", "Offer context", settings.offer_context || ""],
    ["cta_mix", "CTA mix", settings.cta_mix || ""],
  ];
  return `
    <section class="settings-section wide">
      <h3>Content settings</h3>
      ${rows.map(([key, label, value]) => `
        <label>${label}</label>
        <textarea data-setting="${key}" rows="${key === "notebook_id" ? 2 : 5}">${escapeHtml(value)}</textarea>
        <button data-action="save-text" data-key="${key}">Save ${label}</button>
      `).join("")}
    </section>
  `;
}

function renderOverlaySettings(settings) {
  return `
    <section class="settings-section wide">
      <h3>Overlays</h3>
      ${settings.overlays.map((overlay) => `
        <article class="overlay-card">
          <div>
            <strong>${escapeHtml(overlay.label)}</strong>
            <p>${overlay.has_file ? escapeHtml(overlay.file_name) : "No file"}</p>
          </div>
          ${overlay.has_file ? `<img src="/api/settings/overlay/file?user_id=${encodeURIComponent(state.userId)}&format=${encodeURIComponent(overlay.format)}&t=${Date.now()}" alt="" />` : ""}
          <label>Start %</label>
          <input type="number" min="0" max="100" value="${overlay.start_percent}" data-overlay-percent="${overlay.format}" />
          <input type="file" accept="image/png,image/jpeg,image/webp" data-overlay-file="${overlay.format}" />
          <div class="settings-actions">
            <button data-action="save-overlay-percent" data-format="${overlay.format}">Save</button>
            <button data-action="delete-overlay" data-format="${overlay.format}" ${overlay.has_file ? "" : "disabled"}>Delete</button>
          </div>
        </article>
      `).join("")}
    </section>
  `;
}

function bindSettingsEvents(root) {
  root.querySelectorAll("[data-action='load-avatars']").forEach((button) => button.addEventListener("click", () => loadAvatars().catch(showError)));
  root.querySelectorAll("[data-action='load-voices']").forEach((button) => button.addEventListener("click", () => loadVoices().catch(showError)));
  root.querySelectorAll("[data-action='save-text']").forEach((button) =>
    button.addEventListener("click", () => saveTextSetting(button.dataset.key).catch(showError)),
  );
  root.querySelectorAll("[data-action='select-avatar']").forEach((button) =>
    button.addEventListener("click", () => selectAsset("heygen-avatar", button.dataset).catch(showError)),
  );
  root.querySelectorAll("[data-action='select-voice']").forEach((button) =>
    button.addEventListener("click", () => selectAsset("elevenlabs-voice", button.dataset).catch(showError)),
  );
  root.querySelectorAll("[data-action='save-overlay-percent']").forEach((button) =>
    button.addEventListener("click", () => saveOverlayPercent(button.dataset.format).catch(showError)),
  );
  root.querySelectorAll("[data-action='delete-overlay']").forEach((button) =>
    button.addEventListener("click", () => deleteOverlay(button.dataset.format).catch(showError)),
  );
  root.querySelectorAll("[data-overlay-file]").forEach((input) =>
    input.addEventListener("change", () => uploadOverlay(input.dataset.overlayFile, input.files[0]).catch(showError)),
  );
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
  await loadAll();
  setStatus("Ready");
}

async function loadAvatars() {
  setStatus("Avatars");
  state.avatars = await api("/api/settings/heygen-avatars");
  renderSettings();
  setStatus("Ready");
}

async function loadVoices() {
  setStatus("Voices");
  state.voices = await api("/api/settings/elevenlabs-voices");
  renderSettings();
  setStatus("Ready");
}

async function saveTextSetting(key) {
  const field = document.querySelector(`[data-setting="${key}"]`);
  setStatus("Saving");
  state.settings = await api("/api/settings/text", {
    method: "PATCH",
    body: JSON.stringify({ user_id: state.userId, key, value: field.value }),
  });
  renderSettings();
  setStatus("Saved");
}

async function selectAsset(kind, dataset) {
  setStatus("Saving");
  state.settings = await api(`/api/settings/${kind}`, {
    method: "POST",
    body: JSON.stringify({ user_id: state.userId, id: dataset.id, name: dataset.name }),
  });
  renderSettings();
  setStatus("Saved");
}

async function saveOverlayPercent(format) {
  const field = document.querySelector(`[data-overlay-percent="${format}"]`);
  setStatus("Saving");
  await api("/api/settings/overlay", {
    method: "PATCH",
    body: JSON.stringify({ user_id: state.userId, format, start_percent: Number(field.value || 70) }),
  });
  await loadSettings();
  setStatus("Saved");
}

async function uploadOverlay(format, file) {
  if (!file) return;
  const form = new FormData();
  form.append("user_id", state.userId);
  form.append("format", format);
  form.append("file", file);
  setStatus("Uploading");
  const res = await fetch("/api/settings/overlay", { method: "POST", body: form });
  if (!res.ok) throw new Error((await res.json()).detail || "Upload failed");
  await loadSettings();
  setStatus("Uploaded");
}

async function deleteOverlay(format) {
  setStatus("Deleting");
  await api(`/api/settings/overlay?user_id=${encodeURIComponent(state.userId)}&format=${encodeURIComponent(format)}`, { method: "DELETE" });
  await loadSettings();
  setStatus("Deleted");
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
$("refresh-settings").addEventListener("click", () => loadSettings().catch(showError));

document.querySelectorAll(".tab").forEach((button) => {
  button.addEventListener("click", () => {
    state.tab = button.dataset.tab;
    renderTabs();
  });
});

$("copy").addEventListener("click", async () => {
  try {
    if (!navigator.clipboard?.writeText) throw new Error("Clipboard API unavailable");
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
