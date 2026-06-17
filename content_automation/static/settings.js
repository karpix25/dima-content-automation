import { bindAvatarEvents } from "/static/settings_avatars.js?v=20260617-plan-buttons";
import { bindVoiceEvents } from "/static/settings_voices.js?v=20260617-plan-buttons";
import { activeSettingsTab, renderSettingsContent } from "/static/settings_format_sections.js?v=20260617-plan-buttons";
import { pendingLabelForAction, withButtonPending, withUploadPending } from "/static/action_feedback.js?v=20260617-plan-buttons";

export async function loadSettingsData(deps, render = true) {
  const { state, api } = deps;
  if (!state.userId) return;
  const userQuery = encodeURIComponent(state.userId);
  state.settingsLoadError = "";
  state.settingsLoadWarnings = [];
  try {
    state.settings = await api(`/api/settings?user_id=${userQuery}`);
  } catch (error) {
    state.settings = null;
    state.settingsLoadError = settingsErrorMessage("settings", error);
    if (render) renderSettingsPanel(deps);
    return;
  }
  const [refs, faces, inserts, fiveSecond] = await Promise.all([
    optionalSettingsApi(deps, "thumbnail references", `/api/settings/thumbnail-references?user_id=${userQuery}`, []),
    optionalSettingsApi(deps, "thumbnail face references", `/api/settings/thumbnail-face-references?user_id=${userQuery}`, []),
    optionalSettingsApi(deps, "avatar inserts", `/api/settings/avatar-inserts?user_id=${userQuery}`, []),
    optionalSettingsApi(deps, "5-second settings", `/api/settings/instagram-post-5s?user_id=${userQuery}`, null),
  ]);
  state.thumbnailReferences = refs;
  state.thumbnailFaces = faces;
  state.avatarInserts = inserts;
  state.fiveSecondSettings = fiveSecond;
  state.settingsFormatTab = activeSettingsTab(state);
  if (render) renderSettingsPanel(deps);
}

export function renderSettingsPanel(deps) {
  const root = document.getElementById("settings");
  if (!deps.state.settings) {
    root.innerHTML = deps.state.settingsLoadError
      ? `<article class="empty-state"><h3>Настройки не загрузились</h3><p>${deps.escapeHtml(deps.state.settingsLoadError)}</p></article>`
      : `<p>Настройки загружаются.</p>`;
    return;
  }
  root.innerHTML = `${settingsWarnings(deps)}${renderSettingsContent(deps)}`;
  bindSettingsEvents(root, deps);
}

async function optionalSettingsApi(deps, label, path, fallback) {
  try {
    return await deps.api(path);
  } catch (error) {
    deps.state.settingsLoadWarnings.push(settingsErrorMessage(label, error));
    return fallback;
  }
}

function settingsErrorMessage(label, error) {
  return `${label}: ${error?.message || String(error)}`;
}

function settingsWarnings(deps) {
  const warnings = deps.state.settingsLoadWarnings || [];
  if (!warnings.length) return "";
  return `<article class="empty-state"><h3>Часть настроек не загрузилась</h3><p>${deps.escapeHtml(warnings.join("; "))}</p></article>`;
}

function bindSettingsEvents(root, deps) {
  bindFormatTabs(root, deps);
  bindAvatarEvents(root, deps, renderSettingsPanel);
  bindVoiceEvents(root, deps, renderSettingsPanel);
  root.querySelectorAll("[data-action='save-text']").forEach((button) => bindAction(button, deps, () => saveTextSetting(deps, button.dataset.key)));
  root.querySelectorAll("[data-action='save-section']").forEach((button) => bindAction(button, deps, () => saveSettingsSection(deps, button)));
  root.querySelectorAll("[data-action='generate-notebooklm-plan']").forEach((button) => bindAction(button, deps, () => generateNotebookLMPlan(deps)));
  root.querySelectorAll("[data-action='extend-notebooklm-plan']").forEach((button) => bindAction(button, deps, () => extendNotebookLMPlan(deps)));
  root.querySelectorAll("[data-action='generate-notebooklm-ideas']").forEach((button) => bindAction(button, deps, () => generateNotebookLMIdeas(deps)));
  root.querySelectorAll("[data-action='idea-script']").forEach((button) => bindAction(button, deps, () => createScriptFromIdea(deps, button.dataset.ideaId)));
  root.querySelectorAll("[data-action='idea-reject']").forEach((button) => bindAction(button, deps, () => rejectIdea(deps, button.dataset.ideaId)));
  root.querySelectorAll("[data-action='save-overlay-percent']").forEach((button) => bindAction(button, deps, () => saveOverlayPercent(deps, button.dataset.format)));
  root.querySelectorAll("[data-action='delete-overlay']").forEach((button) => bindAction(button, deps, () => deleteOverlay(deps, button.dataset.format)));
  root.querySelectorAll("[data-action='delete-overlay-file']").forEach((button) => bindAction(button, deps, () => deleteOverlayFile(deps, button.dataset.format, button.dataset.index)));
  root.querySelectorAll("[data-action='delete-ref']").forEach((button) => bindAction(button, deps, () => deleteMedia(deps, "thumbnail-references", button.dataset.id)));
  root.querySelectorAll("[data-action='delete-face']").forEach((button) => bindAction(button, deps, () => deleteMedia(deps, "thumbnail-face-references", button.dataset.id)));
  root.querySelectorAll("[data-action='delete-avatar-insert']").forEach((button) => bindAction(button, deps, () => deleteMedia(deps, "avatar-inserts", button.dataset.id)));
  root.querySelectorAll("[data-action='delete-five-audio']").forEach((button) => bindAction(button, deps, () => deleteFiveAudio(deps, button.dataset.id)));
  root.querySelectorAll("[data-action='delete-five-reference']").forEach((button) => bindAction(button, deps, () => deleteFiveReference(deps, button.dataset.id)));
  root.querySelectorAll("[data-target-ref]").forEach((button) => bindAction(button, deps, () => toggleRefTarget(deps, button.dataset.id, button.dataset.targetRef)));
  root.querySelectorAll("[data-face-target]").forEach((button) => bindAction(button, deps, () => activateFace(deps, button.dataset.id, button.dataset.faceTarget)));
  root.querySelectorAll("[data-upload]").forEach((input) => input.addEventListener("change", () => handleUpload(deps, input).catch(deps.showError)));
  root.querySelectorAll("[data-overlay-file]").forEach((input) => input.addEventListener("change", () => uploadOverlay(deps, input.dataset.overlayFile, input.files[0]).catch(deps.showError)));
}

function bindAction(button, deps, handler) {
  button.addEventListener("click", (event) => {
    event.preventDefault();
    withButtonPending(button, handler, { pendingLabel: pendingLabelForAction(button.dataset.action) }).catch(deps.showError);
  });
}

function bindFormatTabs(root, deps) {
  root.querySelectorAll("[data-settings-format-tab]").forEach((button) => {
    button.addEventListener("click", () => {
      deps.state.settingsFormatTab = button.dataset.settingsFormatTab;
      localStorage.setItem("dima_settings_format_tab", deps.state.settingsFormatTab);
      renderSettingsPanel(deps);
    });
  });
}

async function saveTextSetting(deps, key) {
  const field = document.querySelector(`[data-setting="${key}"]`);
  const value = settingFieldValue(field);
  deps.setStatus("Сохраняю");
  deps.state.settings = await deps.api("/api/settings/text", {
    method: "PATCH",
    body: JSON.stringify({ user_id: deps.state.userId, key, value }),
  });
  await loadSettingsData(deps);
  deps.setStatus("Сохранено");
}

async function saveSettingsSection(deps, button) {
  const section = button.closest(".settings-section-body") || button.closest(".settings-section") || document;
  const fields = Array.from(section.querySelectorAll("[data-setting]"));
  if (!fields.length) return;
  const values = Object.fromEntries(fields.map((field) => [field.dataset.setting, settingFieldValue(field)]));
  deps.setStatus("Сохраняю");
  deps.state.settings = await deps.api("/api/settings/section", {
    method: "PATCH",
    body: JSON.stringify({ user_id: deps.state.userId, values }),
  });
  await loadSettingsData(deps);
  deps.setStatus("Сохранено");
}

async function generateNotebookLMIdeas(deps) {
  deps.setStatus("Идеи");
  const result = await deps.api("/api/ideas/notebooklm", {
    method: "POST",
    body: JSON.stringify({ user_id: deps.state.userId, count: 8 }),
  });
  deps.state.ideas = await loadIdeas(deps).catch(() => result.ideas || []);
  await loadSettingsData(deps, false);
  renderSettingsPanel(deps);
  deps.setStatus("Готово");
}

async function generateNotebookLMPlan(deps) {
  deps.setStatus("План");
  const result = await deps.api("/api/ideas/notebooklm-plan", {
    method: "POST",
    body: JSON.stringify({ user_id: deps.state.userId, count: 30 }),
  });
  deps.state.ideas = await loadIdeas(deps).catch(() => result.ideas || []);
  await loadSettingsData(deps, false);
  renderSettingsPanel(deps);
  deps.setStatus("Готово");
}

async function extendNotebookLMPlan(deps) {
  deps.setStatus("План");
  const result = await deps.api("/api/ideas/notebooklm-plan/extend", {
    method: "POST",
    body: JSON.stringify({ user_id: deps.state.userId, count: 30 }),
  });
  deps.state.ideas = await loadIdeas(deps).catch(() => result.ideas || []);
  await loadSettingsData(deps, false);
  renderSettingsPanel(deps);
  deps.setStatus("Готово");
}

async function createScriptFromIdea(deps, ideaId) {
  deps.setStatus("Идеи");
  await deps.api(`/api/ideas/${ideaId}/script`, {
    method: "POST",
    body: JSON.stringify({ user_id: deps.state.userId, count: 1 }),
  });
  deps.state.ideas = await loadIdeas(deps);
  await loadSettingsData(deps, false);
  renderSettingsPanel(deps);
  deps.setStatus("Готово");
}

async function rejectIdea(deps, ideaId) {
  await deps.api(`/api/ideas/${ideaId}/reject`, {
    method: "POST",
    body: JSON.stringify({ user_id: deps.state.userId, count: 1 }),
  });
  deps.state.ideas = await loadIdeas(deps);
  renderSettingsPanel(deps);
}

function loadIdeas(deps) {
  return deps.api(`/api/ideas?user_id=${encodeURIComponent(deps.state.userId)}&limit=30`);
}

function settingFieldValue(field) {
  return field.multiple ? Array.from(field.selectedOptions).map((option) => option.value).join(",") : field.value;
}

async function saveOverlayPercent(deps, format) {
  const field = document.querySelector(`[data-overlay-percent="${format}"]`);
  deps.setStatus("Сохраняю");
  await deps.api("/api/settings/overlay", {
    method: "PATCH",
    body: JSON.stringify({ user_id: deps.state.userId, format, start_percent: Number(field.value || 70) }),
  });
  await loadSettingsData(deps);
  deps.setStatus("Сохранено");
}

async function uploadOverlay(deps, format, file) {
  if (!file) return;
  await withUploadPending(document.querySelector(`[data-overlay-file="${format}"]`), async () => {
    deps.setStatus("Загружаю");
    const form = formWithUser(deps.state.userId);
    form.append("format", format);
    form.append("file", file);
    await postForm("/api/settings/overlay", form);
    await loadSettingsData(deps);
    deps.setStatus("Сохранено");
  });
}

async function deleteOverlay(deps, format) {
  await deps.api(`/api/settings/overlay?user_id=${encodeURIComponent(deps.state.userId)}&format=${encodeURIComponent(format)}`, { method: "DELETE" });
  await loadSettingsData(deps);
}

async function deleteOverlayFile(deps, format, index) {
  await deps.api(`/api/settings/overlay/file?user_id=${encodeURIComponent(deps.state.userId)}&format=${encodeURIComponent(format)}&index=${encodeURIComponent(index)}`, { method: "DELETE" });
  await loadSettingsData(deps);
}

async function handleUpload(deps, input) {
  const files = Array.from(input.files || []);
  if (!files.length) return;
  const form = formWithUser(deps.state.userId);
  if (input.dataset.uploadTarget) form.append("target", input.dataset.uploadTarget);
  files.forEach((file) => form.append("files", file));
  const paths = {
    "thumbnail-references": "/api/settings/thumbnail-references",
    "thumbnail-faces": "/api/settings/thumbnail-faces",
    "avatar-inserts": "/api/settings/avatar-inserts",
    "five-second-audio": "/api/settings/instagram-post-5s/audio",
    "five-second-reference": "/api/settings/instagram-post-5s/references",
  };
  await withUploadPending(input, async () => {
    deps.setStatus("Загружаю");
    await postForm(paths[input.dataset.upload], form);
    input.value = "";
    await loadSettingsData(deps);
    deps.setStatus("Сохранено");
  });
}

async function toggleRefTarget(deps, id, target) {
  const item = deps.state.thumbnailReferences.find((ref) => String(ref.id) === String(id));
  const nextTarget = nextReferenceTarget(item?.target || "both", target);
  await deps.api(`/api/settings/thumbnail-references/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ user_id: deps.state.userId, target: nextTarget }),
  });
  await loadSettingsData(deps);
}

async function activateFace(deps, id, target) {
  await deps.api(`/api/settings/thumbnail-face-references/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ user_id: deps.state.userId, target }),
  });
  await loadSettingsData(deps);
}

async function deleteMedia(deps, endpoint, id) {
  await deps.api(`/api/settings/${endpoint}/${id}?user_id=${encodeURIComponent(deps.state.userId)}`, { method: "DELETE" });
  await loadSettingsData(deps);
}

async function deleteFiveAudio(deps, id) {
  await deps.api(`/api/settings/instagram-post-5s/audio/${id}?user_id=${encodeURIComponent(deps.state.userId)}`, { method: "DELETE" });
  await loadSettingsData(deps);
}

async function deleteFiveReference(deps, id) {
  await deps.api(`/api/settings/instagram-post-5s/references/${id}?user_id=${encodeURIComponent(deps.state.userId)}`, { method: "DELETE" });
  await loadSettingsData(deps);
}

function nextReferenceTarget(current, toggled) {
  const hasHorizontal = targetHas(current, "horizontal");
  const hasVertical = targetHas(current, "vertical");
  const nextHorizontal = toggled === "horizontal" ? !hasHorizontal : hasHorizontal;
  const nextVertical = toggled === "vertical" ? !hasVertical : hasVertical;
  if (!nextHorizontal && !nextVertical) return current;
  if (nextHorizontal && nextVertical) return "both";
  return nextHorizontal ? "horizontal" : "vertical";
}

function targetHas(value, target) {
  return value === "both" || value === target;
}

function formWithUser(userId) {
  const form = new FormData();
  form.append("user_id", userId);
  return form;
}

async function postForm(path, form) {
  const res = await fetch(path, { method: "POST", body: form, headers: telegramAuthHeaders() });
  if (!res.ok) throw new Error((await res.json()).detail || "Загрузка не удалась");
  return res.json();
}

function telegramAuthHeaders() {
  const initData = window.Telegram?.WebApp?.initData || "";
  return initData ? { "X-Telegram-Init-Data": initData } : {};
}
