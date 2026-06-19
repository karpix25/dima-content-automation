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
      <p>${escapeHtml(autoScriptMessage || "Пишу сценарии по новым темам. Карточки появятся здесь автоматически.")}</p>
      <div class="create-idea-list">
        ${ideas.slice(0, 5).map((idea) => createIdeaRow(idea, escapeHtml)).join("")}
      </div>
      <button class="secondary-button" type="button" data-open-ideas>Открыть весь банк тем</button>
    </article>
  `;
}

export function bindCreateIdeasPrompt(root, deps) {
  root.querySelector("[data-open-ideas]")?.addEventListener("click", () => {
    deps.openIdeas();
  });
}

function createIdeaRow(idea, escapeHtml) {
  return `
    <div class="create-idea-row">
      <div>
        <strong>${escapeHtml(idea.title)}</strong>
        ${idea.angle ? `<p>${escapeHtml(idea.angle)}</p>` : ""}
      </div>
    </div>
  `;
}

function emptyState(title, text) {
  return `<article class="empty-state"><h3>${title}</h3><p>${text}</p></article>`;
}
