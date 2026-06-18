import { withButtonPending } from "/static/action_feedback.js?v=20260617-plan-buttons";

export function renderScriptReviewDeck({ pendingScripts, escapeHtml }) {
  if (!pendingScripts?.length) return "";
  const script = pendingScripts[0];
  return `
    <article class="review-deck-card">
      <div class="idea-card-head">
        <span>Проверка сценариев</span>
        <span>${escapeHtml(pendingScripts.length)} в очереди</span>
      </div>
      <h3>${escapeHtml(script.title || script.hook || `Сценарий #${script.id}`)}</h3>
      ${script.hook ? `<p class="review-hook">${escapeHtml(script.hook)}</p>` : ""}
      ${script.voiceover ? `<div class="review-copy">${escapeHtml(script.voiceover)}</div>` : ""}
      <div class="review-actions">
        <button class="secondary-button danger" type="button" data-review-action="reject" data-script-id="${escapeHtml(script.id)}">Отклонить</button>
        <button type="button" data-review-action="approve" data-script-id="${escapeHtml(script.id)}">Принять</button>
      </div>
      <p class="review-help">После принятия здесь сразу появятся форматы для запуска.</p>
    </article>
  `;
}

export function bindScriptReviewDeck(root, deps) {
  root.querySelectorAll("[data-review-action]").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();
      const action = button.dataset.reviewAction;
      withButtonPending(button, () => reviewScript(button.dataset.scriptId, action, deps), {
        pendingLabel: action === "approve" ? "Принимаю..." : "Отклоняю...",
      }).catch(deps.showError);
    });
  });
}

async function reviewScript(scriptId, action, deps) {
  deps.setStatus("Working");
  await deps.api(`/api/scripts/${scriptId}/review`, {
    method: "POST",
    body: JSON.stringify({ user_id: deps.state.userId, action }),
  });
  await deps.refresh();
  deps.setStatus("Готово");
}
