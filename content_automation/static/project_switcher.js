import { chooseProject, projectLabel, saveProjectId, savedProjectId } from "/static/session_context.js";

export async function loadProjectContext({ state, api }) {
  const actorQuery = encodeURIComponent(state.actorUserId);
  const activeQuery = encodeURIComponent(savedProjectId(state.actorUserId));
  state.projects = await api(`/api/projects?user_id=${actorQuery}&active_project_id=${activeQuery}`).catch(() => []);
  state.userId = chooseProject(state.projects, state.actorUserId);
  if (!state.projects.length) {
    state.projects = [{ project_id: state.userId, member_user_id: state.actorUserId, role: "owner", is_active: true }];
  }
  saveProjectId(state.actorUserId, state.userId);
  await saveActiveProjectOnServer({ state, api }, state.userId).catch(() => {});
}

export function renderProjectSwitcher(deps) {
  const { state, escapeHtml } = deps;
  const root = document.getElementById("project-switcher");
  if (!root) return;
  if (!state.projects.length) {
    root.classList.add("hidden");
    root.innerHTML = "";
    return;
  }
  root.classList.remove("hidden");
  if (state.projects.length === 1) {
    root.innerHTML = `<span class="project-badge">${escapeHtml(projectLabel(state.projects[0]))}</span>`;
    return;
  }
  root.innerHTML = `
    <select id="project-select" aria-label="Проект">
      ${state.projects.map((project) => `
        <option value="${escapeHtml(project.project_id)}" ${project.project_id === state.userId ? "selected" : ""}>
          ${escapeHtml(projectLabel(project))}
        </option>
      `).join("")}
    </select>
  `;
  document.getElementById("project-select")?.addEventListener("change", () => {
    switchProject(deps, document.getElementById("project-select").value).catch(deps.showError);
  });
}

async function switchProject(deps, projectId) {
  const { state } = deps;
  if (!projectId || projectId === state.userId) return;
  deps.stopPolling();
  saveProjectId(state.actorUserId, projectId);
  state.userId = projectId;
  await saveActiveProjectOnServer(deps, projectId).catch(() => {});
  resetProjectData(state);
  await deps.reload();
}

function saveActiveProjectOnServer({ state, api }, projectId) {
  return api("/api/projects/active", {
    method: "POST",
    body: JSON.stringify({ user_id: state.actorUserId, project_id: projectId }),
  });
}

function resetProjectData(state) {
  state.jobs = [];
  state.scripts = [];
  state.pendingScripts = [];
  state.ideas = [];
  state.activeJob = null;
  state.output = "";
}
