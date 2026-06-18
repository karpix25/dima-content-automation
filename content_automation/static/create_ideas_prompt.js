import { withButtonPending } from "/static/action_feedback.js?v=20260618-auto-scripts";
import { startAutoIdeaScripts } from "/static/idea_auto_scripts.js?v=20260618-auto-scripts";

export function renderCreateIdeasPrompt({ ideas, escapeHtml, autoScriptMessage = "" }) {
  if (!ideas?.length) {
    return emptyState("Нет одобренных сценариев", "Сначала одобрите сценарий в Telegram. После этого здесь появятся форматы для запуска.");
  }
  return `
    <article class="empty-state create-ideas-prompt">
      <div class="idea-card-head">
        <span>Банк тем</span>
        <span>${escapeHtml(ideas.length)} новых</span>
      </div>
      <h3>Темы подтянулись</h3>
      <p>${escapeHtml(autoScriptMessage || "Можно сразу написать сценарии по всем темам, а потом принимать их карточками.")}</p>
      <div class="create-idea-list">
        ${ideas.slice(0, 5).map((idea) => createIdeaRow(idea, escapeHtml)).join("")}
      </div>
      <button type="button" data-auto-script-ideas>Написать все темы</button>
      <button class="secondary-button" type="button" data-open-ideas>Открыть весь банк тем</button>
    </article>
  `;
}

export function bindCreateIdeasPrompt(root, deps) {
  root.querySelectorAll("[data-create-script-from-idea]").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();
      withButtonPending(button, () => createScriptFromIdea(button.dataset.createScriptFromIdea, deps), {
        pendingLabel: "Пишу...",
        doneLabel: "Сценарий создан",
      }).catch(deps.showError);
    });
  });
  root.querySelector("[data-open-ideas]")?.addEventListener("click", () => {
    deps.openIdeas();
  });
  root.querySelector("[data-auto-script-ideas]")?.addEventListener("click", (event) => {
    event.preventDefault();
    withButtonPending(
      event.currentTarget,
      () => startAutoIdeaScripts(deps, { count: 30 }),
      { pendingLabel: "Запускаю...", doneLabel: "Пишу сценарии" },
    ).catch(deps.showError);
  });
}

async function createScriptFromIdea(ideaId, deps) {
  deps.setStatus("Идеи");
  await deps.api(`/api/ideas/${ideaId}/script`, {
    method: "POST",
    body: JSON.stringify({ user_id: deps.state.userId, count: 1 }),
  });
  await deps.refresh();
  deps.setStatus("Готово");
}

function createIdeaRow(idea, escapeHtml) {
  return `
    <div class="create-idea-row">
      <div>
        <strong>${escapeHtml(idea.title)}</strong>
        ${idea.angle ? `<p>${escapeHtml(idea.angle)}</p>` : ""}
      </div>
      <button type="button" data-create-script-from-idea="${escapeHtml(idea.id)}">Написать</button>
    </div>
  `;
}

function emptyState(title, text) {
  return `<article class="empty-state"><h3>${title}</h3><p>${text}</p></article>`;
}
