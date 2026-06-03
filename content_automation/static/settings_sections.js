export function formatHeader(title, subtitle, chips, escapeHtml) {
  return `
    <header class="format-settings-head">
      <div>
        <h2>${escapeHtml(title)}</h2>
        <p>${escapeHtml(subtitle)}</p>
      </div>
      <div class="summary-chips">${renderChips(chips, escapeHtml)}</div>
    </header>
  `;
}

export function settingsDisclosure(title, chips, body, escapeHtml) {
  return `
    <details class="settings-section">
      <summary>
        <span class="summary-title">${escapeHtml(title)}</span>
        <span class="summary-chips">${renderChips(chips, escapeHtml)}</span>
      </summary>
      <div class="settings-section-body">${body}</div>
    </details>
  `;
}

export function chip(label, muted = false) {
  return { label, muted };
}

function renderChips(chips, escapeHtml) {
  return chips.map((chip) => `<span class="summary-chip ${chip.muted ? "muted" : ""}">${escapeHtml(chip.label)}</span>`).join("");
}
