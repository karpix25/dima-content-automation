export function renderScriptHookMetadata(script, escapeHtml) {
  const rows = [
    ["Тип хука", script.hook_type],
    ["Паттерн", script.hook_pattern],
    ["Механизм", script.mechanism],
    ["Первый кадр", script.first_frame_text],
    ["Визуальное доказательство", script.visual_proof],
    ["План удержания", script.visual_retention_plan],
  ].filter(([, value]) => String(value || "").trim());
  if (!rows.length) return "";
  return `
    <div class="hook-metadata">
      ${rows.map(([label, value]) => `
        <div>
          <span>${escapeHtml(label)}</span>
          <strong>${escapeHtml(value)}</strong>
        </div>
      `).join("")}
    </div>
  `;
}

