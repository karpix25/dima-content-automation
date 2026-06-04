import { chip, formatHeader, settingsDisclosure } from "/static/settings_sections.js";

const TIMEFRAME_OPTIONS = [
  ["day", "1 день"],
  ["week", "7 дней"],
  ["month", "30 дней"],
];

export function renderIdeasTab({ state, escapeHtml }) {
  const timeframe = state.settings.reddit_timeframe || "week";
  return `
    ${formatHeader("Идеи из Reddit", "Период поиска для команды /reddit_radar.", [chip(timeframeLabel(timeframe))], escapeHtml)}
    <section class="settings-stack">
      ${settingsDisclosure("Reddit Radar", [chip(timeframeLabel(timeframe))], `
        <div class="soft-box">
          <h3>Период поиска</h3>
          <select data-setting="reddit_timeframe">
            ${TIMEFRAME_OPTIONS.map(([value, label]) => `
              <option value="${escapeHtml(value)}" ${timeframe === value ? "selected" : ""}>${escapeHtml(label)}</option>
            `).join("")}
          </select>
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
