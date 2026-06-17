export async function withButtonPending(button, task, options = {}) {
  if (!button) return task();
  const pendingLabel = options.pendingLabel || "Ждите...";
  const doneLabel = options.doneLabel || "";
  const label = button.querySelector("span") || button;
  const previous = label.textContent;
  button.disabled = true;
  button.classList.add("is-busy");
  button.setAttribute("aria-busy", "true");
  label.textContent = pendingLabel;
  try {
    const result = await task();
    if (doneLabel && button.isConnected) {
      label.textContent = doneLabel;
      setTimeout(() => {
        if (button.isConnected) label.textContent = previous;
      }, options.doneMs || 1200);
    }
    return result;
  } finally {
    if (button.isConnected) {
      button.disabled = false;
      button.classList.remove("is-busy");
      button.removeAttribute("aria-busy");
      if (!doneLabel) label.textContent = previous;
    }
  }
}


export async function withUploadPending(input, task, options = {}) {
  const label = input?.closest(".upload-button");
  if (!label) return task();
  const previous = label.firstChild?.textContent || label.textContent;
  label.classList.add("is-busy");
  label.setAttribute("aria-busy", "true");
  if (label.firstChild) label.firstChild.textContent = options.pendingLabel || "Загружаю...";
  try {
    return await task();
  } finally {
    if (label.isConnected) {
      label.classList.remove("is-busy");
      label.removeAttribute("aria-busy");
      if (label.firstChild) label.firstChild.textContent = previous;
    }
  }
}


export function pendingLabelForAction(action) {
  if (String(action || "").startsWith("delete")) return "Удаляю...";
  if (action === "save-section" || action === "save-text" || action === "save-overlay-percent") return "Сохраняю...";
  return "Ждите...";
}
