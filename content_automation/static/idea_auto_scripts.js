let refreshTimer = null;

export async function startAutoIdeaScripts(deps, { count = 30 } = {}) {
  deps.setStatus("Пишу");
  const result = await deps.api("/api/ideas/scripts/auto", {
    method: "POST",
    body: JSON.stringify({ user_id: deps.state.userId, count }),
  });
  deps.state.autoScriptMessage = result.accepted
    ? `Пишу сценарии по ${result.accepted} темам. Карточки будут появляться здесь.`
    : "Новых тем для сценариев нет.";
  scheduleAutoRefresh(deps);
  return result;
}

export function scheduleAutoRefresh(deps, attempts = 24) {
  if (refreshTimer) window.clearTimeout(refreshTimer);
  const tick = async (left) => {
    if (left <= 0) return;
    try {
      await deps.refresh();
    } finally {
      refreshTimer = window.setTimeout(() => tick(left - 1), 5000);
    }
  };
  refreshTimer = window.setTimeout(() => tick(attempts), 3000);
}
