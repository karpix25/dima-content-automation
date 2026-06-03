function escapeEditorial(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

window.editorialBadges = function editorialBadges(script) {
  const summary = String(script.editorial_summary || "").trim();
  if (!summary) return "";
  const parts = summary.split(" · ").filter(Boolean).slice(0, 5);
  return `
    <div class="editorial-badges" aria-label="Формат идеи">
      ${parts.map((part) => `<span>${escapeEditorial(part)}</span>`).join("")}
    </div>
  `;
};
