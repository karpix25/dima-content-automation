export function initialActorUserId(tg) {
  return new URLSearchParams(window.location.search).get("tg_id")
    || String(tg?.initDataUnsafe?.user?.id || "")
    || localStorage.getItem("dima_tg_id")
    || "";
}

export function activeProjectStorageKey(actorUserId) {
  return `dima_active_project:${actorUserId || "anonymous"}`;
}

export function savedProjectId(actorUserId) {
  return localStorage.getItem(activeProjectStorageKey(actorUserId)) || "";
}

export function saveProjectId(actorUserId, projectId) {
  if (!actorUserId || !projectId) return;
  localStorage.setItem(activeProjectStorageKey(actorUserId), projectId);
}

export function chooseProject(projects, actorUserId) {
  const saved = savedProjectId(actorUserId);
  return projects.find((item) => item.is_active)?.project_id
    || projects.find((item) => item.project_id === saved)?.project_id
    || projects[0]?.project_id
    || actorUserId;
}

export function projectLabel(project) {
  if (!project) return "Проект";
  return project.role === "owner" ? `Мой проект ${project.project_id}` : `Проект ${project.project_id}`;
}
