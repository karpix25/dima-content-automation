export function renderDurationSection(state, escapeHtml) {
  const settings = state.settings;
  return `
    <details class="tg-card settings-section">
      <summary>
        <span class="summary-title">Длина видео</span>
        <span class="summary-chips">
          <span class="summary-chip">${settings.youtube_long_duration_minutes || 10} мин YouTube</span>
          <span class="summary-chip">${verticalLabel(settings.vertical_avatar_duration_mode)}</span>
        </span>
      </summary>
      <div class="duration-grid">
        ${durationSelectCard({
          key: "youtube_long_duration_minutes",
          title: "Длина long YouTube сценария",
          icon: "film",
          value: String(settings.youtube_long_duration_minutes || 10),
          options: [
            ["5", "5 мин"],
            ["7", "7 мин"],
            ["10", "10 мин"],
            ["12", "12 мин"],
            ["15", "15 мин"],
          ],
          escapeHtml,
        })}
        ${durationSelectCard({
          key: "vertical_avatar_duration_mode",
          title: "Длина вертикального AI-аватара",
          icon: "phone",
          value: settings.vertical_avatar_duration_mode || "original",
          options: [
            ["original", "по оригиналу"],
            ["30", "30 сек"],
            ["45", "45 сек"],
            ["60", "60 сек"],
            ["90", "90 сек"],
          ],
          escapeHtml,
        })}
      </div>
    </details>
  `;
}

function durationSelectCard({ key, title, icon, value, options, escapeHtml }) {
  return `
    <article class="duration-card">
      <div class="duration-icon ${escapeHtml(icon)}" aria-hidden="true">${durationIcon()}</div>
      <h3>${escapeHtml(title)}</h3>
      <select data-setting="${escapeHtml(key)}">
        ${options.map(([optionValue, label]) => `
          <option value="${escapeHtml(optionValue)}" ${String(value) === optionValue ? "selected" : ""}>
            ${escapeHtml(label)}
          </option>
        `).join("")}
      </select>
      <button data-action="save-text" data-key="${escapeHtml(key)}">Сохранить</button>
    </article>
  `;
}

function durationIcon() {
  return `<svg viewBox="0 0 24 24" width="20" height="20"><path d="M6 4h12v16H6zM9 4v16M15 4v16M6 8h3M15 8h3M6 12h3M15 12h3M6 16h3M15 16h3" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>`;
}

function verticalLabel(value) {
  if (!value || value === "original") return "по оригиналу";
  return `${value} сек vertical`;
}
