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
  renderScripts();
  renderJobs();
  setStatus("Ready");
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
