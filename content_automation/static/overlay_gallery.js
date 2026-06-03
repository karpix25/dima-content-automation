function escapeOverlayText(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

window.renderOverlayFiles = function renderOverlayFiles(overlay) {
  const files = Array.isArray(overlay.files) ? overlay.files : [];
  if (!files.length) return "";
  return `
    <div class="overlay-files">
      ${files.map((file) => `
        <div class="overlay-file-row">
          <span>${escapeOverlayText(file.file_name)}</span>
          <button data-action="delete-overlay-file" data-format="${escapeOverlayText(overlay.format)}" data-index="${file.index}">Удалить</button>
        </div>
      `).join("")}
    </div>
  `;
};
