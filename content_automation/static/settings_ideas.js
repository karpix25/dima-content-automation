import { chip, formatHeader, settingsDisclosure } from "/static/settings_sections.js";

const TIMEFRAME_OPTIONS = [
  ["day", "1 день"],
  ["week", "7 дней"],
  ["month", "30 дней"],
];

export function renderIdeasTab({ state, escapeHtml }) {
  const timeframe = state.settings.reddit_timeframe || "week";
  const subreddits = state.settings.reddit_subreddits || "";
  return `
    ${formatHeader("Идеи из Reddit", "Источники и период поиска для команды /reddit_radar.", [chip(timeframeLabel(timeframe)), chip(subredditCount(subreddits))], escapeHtml)}
    <section class="settings-stack">
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
