import { bindAvatarEvents } from "/static/settings_avatars.js";
import { bindVoiceEvents } from "/static/settings_voices.js";
import { activeSettingsTab, renderSettingsContent } from "/static/settings_format_sections.js";

export async function loadSettingsData(deps, render = true) {
  const { state, api } = deps;
  if (!state.userId) return;
  const userQuery = encodeURIComponent(state.userId);
  const [settings, refs, faces, inserts, fiveSecond] = await Promise.all([
    api(`/api/settings?user_id=${userQuery}`),
    api(`/api/settings/thumbnail-references?user_id=${userQuery}`),
    api(`/api/settings/thumbnail-face-references?user_id=${userQuery}`),
    api(`/api/settings/avatar-inserts?user_id=${userQuery}`),
    api(`/api/settings/instagram-post-5s?user_id=${userQuery}`),
  ]);
  state.settings = settings;
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
    root.innerHTML = `<p>Настройки загружаются.</p>`;
    return;
  }
  root.innerHTML = renderSettingsContent(deps);
  bindSettingsEvents(root, deps);
}

function bindSettingsEvents(root, deps) {
  bindFormatTabs(root, deps);
  bindAvatarEvents(root, deps, renderSettingsPanel);
  bindVoiceEvents(root, deps, renderSettingsPanel);
  root.querySelectorAll("[data-action='save-text']").forEach((button) => button.addEventListener("click", () => saveTextSetting(deps, button.dataset.key).catch(deps.showError)));
  root.querySelectorAll("[data-action='save-section']").forEach((button) => button.addEventListener("click", () => saveSettingsSection(deps, button).catch(deps.showError)));
  root.querySelectorAll("[data-action='save-overlay-percent']").forEach((button) => button.addEventListener("click", () => saveOverlayPercent(deps, button.dataset.format).catch(deps.showError)));
  root.querySelectorAll("[data-action='delete-overlay']").forEach((button) => button.addEventListener("click", () => deleteOverlay(deps, button.dataset.format).catch(deps.showError)));
  root.querySelectorAll("[data-action='delete-ref']").forEach((button) => button.addEventListener("click", () => deleteMedia(deps, "thumbnail-references", button.dataset.id).catch(deps.showError)));
  root.querySelectorAll("[data-action='delete-face']").forEach((button) => button.addEventListener("click", () => deleteMedia(deps, "thumbnail-face-references", button.dataset.id).catch(deps.showError)));
  root.querySelectorAll("[data-action='delete-avatar-insert']").forEach((button) => button.addEventListener("click", () => deleteMedia(deps, "avatar-inserts", button.dataset.id).catch(deps.showError)));
  root.querySelectorAll("[data-action='delete-five-audio']").forEach((button) => button.addEventListener("click", () => deleteFiveAudio(deps, button.dataset.id).catch(deps.showError)));
  root.querySelectorAll("[data-action='delete-five-reference']").forEach((button) => button.addEventListener("click", () => deleteFiveReference(deps, button.dataset.id).catch(deps.showError)));
  root.querySelectorAll("[data-target-ref]").forEach((button) => button.addEventListener("click", () => toggleRefTarget(deps, button.dataset.id, button.dataset.targetRef).catch(deps.showError)));
  root.querySelectorAll("[data-face-target]").forEach((button) => button.addEventListener("click", () => activateFace(deps, button.dataset.id, button.dataset.faceTarget).catch(deps.showError)));
  root.querySelectorAll("[data-upload]").forEach((input) => input.addEventListener("change", () => handleUpload(deps, input).catch(deps.showError)));
  root.querySelectorAll("[data-overlay-file]").forEach((input) => input.addEventListener("change", () => uploadOverlay(deps, input.dataset.overlayFile, input.files[0]).catch(deps.showError)));
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
  deps.setStatus("Сохраняю");
  for (const field of fields) {
    await deps.api("/api/settings/text", {
      method: "PATCH",
      body: JSON.stringify({ user_id: deps.state.userId, key: field.dataset.setting, value: settingFieldValue(field) }),
    });
  }
  await loadSettingsData(deps);
  deps.setStatus("Сохранено");
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
  const form = formWithUser(deps.state.userId);
  form.append("format", format);
  form.append("file", file);
  await postForm("/api/settings/overlay", form);
  await loadSettingsData(deps);
}

async function deleteOverlay(deps, format) {
  await deps.api(`/api/settings/overlay?user_id=${encodeURIComponent(deps.state.userId)}&format=${encodeURIComponent(format)}`, { method: "DELETE" });
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
  await postForm(paths[input.dataset.upload], form);
  input.value = "";
  await loadSettingsData(deps);
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
  const res = await fetch(path, { method: "POST", body: form });
  if (!res.ok) throw new Error((await res.json()).detail || "Загрузка не удалась");
  return res.json();
}
