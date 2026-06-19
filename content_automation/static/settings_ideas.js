import { chip, formatHeader, settingsDisclosure } from "/static/settings_sections.js?v=20260617-plan-buttons";

const TIMEFRAME_OPTIONS = [
  ["day", "1 день"],
  ["week", "7 дней"],
  ["month", "30 дней"],
];

export function renderIdeasTab({ state, escapeHtml }) {
  const timeframe = state.settings.reddit_timeframe || "week";
  const subreddits = state.settings.reddit_subreddits || "";
  const ideas = state.ideas || [];
  const notebookLabel = state.settings.notebook_id ? "база задана" : "проверю серверную базу";
  return `
    ${formatHeader("Идеи", "Собирай темы из NotebookLM и внешних источников, потом бери их в сценарии.", [chip(timeframeLabel(timeframe)), chip(subredditCount(subreddits)), chip(`${ideas.length} тем`)], escapeHtml)}
    <section class="settings-stack">
      ${settingsDisclosure("NotebookLM темы", [chip(notebookLabel, !state.settings.notebook_id), chip(contentLanguageLabel(state.settings.content_language || "auto"))], `
        <div class="soft-box">
          <h3>Темы из базы знаний</h3>
          <p class="muted">NotebookLM найдет темы внутри твоей базы. Если личный NotebookLM ID пустой, попробую серверный ID из деплоя.</p>
          <div class="settings-actions">
            <button data-action="generate-notebooklm-plan">План на месяц</button>
            <button data-action="extend-notebooklm-plan">Добрать еще 30</button>
            <button data-action="generate-notebooklm-ideas">Собрать из NotebookLM</button>
          </div>
        </div>
      `, escapeHtml)}
      ${settingsDisclosure("Reddit Radar", [chip(timeframeLabel(timeframe)), chip(subredditCount(subreddits))], `
        <div class="soft-box">
          <h3>Период поиска</h3>
          <select data-setting="reddit_timeframe">
            ${TIMEFRAME_OPTIONS.map(([value, label]) => `
              <option value="${escapeHtml(value)}" ${timeframe === value ? "selected" : ""}>${escapeHtml(label)}</option>
            `).join("")}
          </select>
          <h3>Сабреддиты</h3>
          <textarea data-setting="reddit_subreddits" rows="4">${escapeHtml(subreddits)}</textarea>
          <div class="settings-actions">
            <button data-action="save-section">Сохранить</button>
          </div>
        </div>
      `, escapeHtml)}
      ${settingsDisclosure("Банк тем", [chip(`${ideas.length} новых`)], `
        <p class="muted">Новые темы автоматически уходят в написание сценариев, когда в проекте нет готовых карточек.</p>
        <div class="idea-list">
          ${ideas.length ? ideas.map((idea) => ideaCard(idea, escapeHtml)).join("") : `<p class="muted">Пока нет новых тем. Собери их из NotebookLM или через Reddit Radar.</p>`}
        </div>
      `, escapeHtml)}
    </section>
  `;
}

function timeframeLabel(value) {
  return TIMEFRAME_OPTIONS.find(([option]) => option === value)?.[1] || "7 дней";
}

function subredditCount(value) {
  const count = String(value || "").split(",").map((item) => item.trim()).filter(Boolean).length;
  return `${count || 0} сабреддитов`;
}

function contentLanguageLabel(value) {
  if (value === "ru") return "русский";
  if (value === "en") return "английский";
  return "язык источника";
}

function ideaCard(idea, escapeHtml) {
  return `
    <article class="idea-card">
      <div class="idea-card-head">
        <span>${escapeHtml(sourceLabel(idea.source))}</span>
        <span>#${escapeHtml(idea.id)}</span>
      </div>
      <h3>${escapeHtml(idea.title)}</h3>
      ${idea.pain ? `<p><strong>Боль:</strong> ${escapeHtml(idea.pain)}</p>` : ""}
      ${idea.angle ? `<p><strong>Угол:</strong> ${escapeHtml(idea.angle)}</p>` : ""}
      ${idea.summary ? `<p>${escapeHtml(idea.summary)}</p>` : ""}
      <div class="settings-actions idea-actions">
        <button class="secondary-button danger" data-action="idea-reject" data-idea-id="${escapeHtml(idea.id)}">Отклонить</button>
      </div>
    </article>
  `;
}

function sourceLabel(source) {
  if (source === "notebooklm_plan") return "NotebookLM план";
  if (source === "notebooklm") return "NotebookLM";
  if (source === "reddit") return "Reddit";
  return source || "Источник";
}
