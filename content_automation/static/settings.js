import { bindAvatarEvents, renderAvatarSelectors } from "/static/settings_avatars.js";
import { renderDurationSection } from "/static/settings_duration.js";
import { bindVoiceEvents, renderVoiceSelector } from "/static/settings_voices.js";

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
  if (render) renderSettingsPanel(deps);
}

export function renderSettingsPanel(deps) {
  const root = document.getElementById("settings");
  const { state } = deps;
  if (!state.settings) {
    root.innerHTML = `<p>Настройки загружаются.</p>`;
    return;
  }
  root.innerHTML = `
    ${renderIdentitySection(deps)}
    ${renderDurationSection(state, deps.escapeHtml)}
    ${renderCoverSection(deps)}
    ${renderAvatarInsertSection(deps)}
    ${renderFiveSecondSection(deps)}
    ${renderTextSection(deps)}
    ${renderOverlaySection(deps)}
  `;
  bindSettingsEvents(root, deps);
}

function renderIdentitySection({ state, escapeHtml }) {
  const settings = state.settings;
  return `
    <details class="tg-card settings-section">
      ${renderSummary("Аватар и голос", identitySummaryChips(settings), escapeHtml)}
      <div class="settings-two">
        <div class="soft-box">
          <h3>Выбор ИИ Аватара (HeyGen)</h3>
          ${renderAvatarSelectors(state, escapeHtml)}
        </div>
        <div class="soft-box">
          <h3>Голос ElevenLabs</h3>
          ${renderVoiceSelector(state, escapeHtml)}
        </div>
      </div>
    </details>
  `;
}

function renderCoverSection({ state, escapeHtml }) {
  return `
    <details class="tg-card settings-section">
      ${renderSummary("Обложки: лицо и референсы", coverSummaryChips(state), escapeHtml)}
      <div class="settings-two cover-grid">
        <div class="soft-box">
          <div class="box-head">
            <h3>Референс лица</h3>
            <label class="upload-button">
              Загрузить
              <input type="file" multiple accept="image/png,image/jpeg,image/webp" data-upload="thumbnail-faces" />
            </label>
          </div>
          ${renderFaceReferences(state, escapeHtml)}
        </div>
        <div class="soft-box">
          <div class="box-head">
            <h3>Референсы обложек</h3>
            <label class="upload-button blue">
              Добавить
              <input type="file" multiple accept="image/png,image/jpeg,image/webp" data-upload="thumbnail-references" />
            </label>
          </div>
          ${renderThumbnailReferences(state, escapeHtml)}
          <p>Каждую картинку можно включить для YouTube, Shorts или обоих форматов.</p>
        </div>
      </div>
    </details>
  `;
}

function renderAvatarInsertSection({ state, escapeHtml }) {
  const settings = state.settings;
  return `
    <details class="tg-card settings-section">
      ${renderSummary("Видео-вставки для горизонтального аватара", avatarInsertSummaryChips(state), escapeHtml)}
      <div class="settings-three">
        ${numberField("avatar_insert_start_percent", "Старт вставок (%)", settings.avatar_insert_start_percent, 0, 99)}
        ${numberField("avatar_insert_end_percent", "Финиш вставок (%)", settings.avatar_insert_end_percent, 1, 100)}
        ${numberField("avatar_insert_clips_count", "Сколько вставок", settings.avatar_insert_clips_count, 0, 20)}
      </div>
      <div class="box-head">
        <p>Видео для перебивок в горизонтальном формате с аватаром. Система выберет нужные клипы в указанном диапазоне.</p>
        <label class="upload-button blue">
          Добавить видео
          <input type="file" multiple accept="video/mp4,video/quicktime,video/webm,video/x-matroska,video/x-m4v" data-upload="avatar-inserts" />
        </label>
      </div>
      <div class="asset-list">${renderSimpleAssetList(state.avatarInserts, escapeHtml, "delete-avatar-insert")}</div>
    </details>
  `;
}

function renderFiveSecondSection({ state, escapeHtml }) {
  const five = state.fiveSecondSettings || { audio_tracks: [] };
  return `
    <details class="tg-card settings-section">
      ${renderSummary("5 секунд", fiveSecondSummaryChips(five), escapeHtml)}
      <label>CTA в нижнем белом фрейме</label>
      <input data-setting="instagram_post_5s_cta_text" maxlength="180" value="${escapeHtml(five.cta_text || "")}" />
      <button data-action="save-text" data-key="instagram_post_5s_cta_text">Сохранить CTA</button>
      <div class="settings-two">
        <div class="soft-box">
          <div class="box-head">
            <h3>Аудиобиблиотека</h3>
            <label class="upload-button blue">
              Добавить
              <input type="file" multiple accept="audio/*,video/mp4,video/quicktime" data-upload="five-second-audio" />
            </label>
          </div>
          <span class="mini-badge">Треков ${five.audio_tracks.length}</span>
          <div class="asset-list">${renderSimpleAssetList(five.audio_tracks, escapeHtml, "delete-five-audio")}</div>
        </div>
        <div class="soft-box">
          <div class="box-head">
            <h3>Плашка с 2 секунды</h3>
            <label class="icon-button" title="Загрузить плашку">
              +
              <input type="file" accept="image/png,image/jpeg,image/webp" data-upload="five-second-overlay" />
            </label>
          </div>
          ${five.overlay_url ? `
            <article class="asset-card media-card selected">
              <img src="${five.overlay_url}" alt="" />
              <div><strong>${escapeHtml((five.overlay_path || "").split("/").pop())}</strong></div>
              <button data-action="delete-five-overlay">Удалить</button>
            </article>
          ` : `<div class="empty-box compact-empty">Плашка не загружена</div>`}
        </div>
      </div>
    </details>
  `;
}

function renderTextSection({ state, escapeHtml }) {
  const rows = [
    ["notebook_id", "NotebookLM ID", state.settings.notebook_id || ""],
    ["author_style", "Стиль автора", state.settings.author_style || ""],
    ["offer_context", "Контекст оффера", state.settings.offer_context || ""],
    ["cta_mix", "Логика CTA", state.settings.cta_mix || ""],
    ["youtube_description_template", "Шаблон описания YouTube", state.settings.youtube_description_template || ""],
  ];
  return `
    <details class="tg-card settings-section">
      ${renderSummary("Текстовые настройки", textSummaryChips(rows), escapeHtml)}
      ${rows.map(([key, label, value]) => `
        <label>${label}</label>
        <textarea data-setting="${key}" rows="${key === "notebook_id" ? 2 : 5}">${escapeHtml(value)}</textarea>
        <button data-action="save-text" data-key="${key}">Сохранить</button>
      `).join("")}
    </details>
  `;
}

function renderOverlaySection({ state, escapeHtml }) {
  return `
    <details class="tg-card settings-section">
      ${renderSummary("Финальные плашки поверх видео", overlaySummaryChips(state), escapeHtml)}
      ${state.settings.overlays.map((overlay) => `
        <article class="overlay-card ${overlay.has_file ? "selected" : ""}">
          <div>
            <strong>${escapeHtml(overlay.label)}</strong>
            <p>${overlay.has_file ? escapeHtml(overlay.file_name) : "Файл не загружен"}</p>
          </div>
          ${overlay.has_file ? `<img src="/api/settings/overlay/file?user_id=${encodeURIComponent(state.userId)}&format=${encodeURIComponent(overlay.format)}&t=${Date.now()}" alt="" />` : ""}
          <label>Старт %</label>
          <input type="number" min="0" max="100" value="${overlay.start_percent}" data-overlay-percent="${overlay.format}" />
          <input type="file" accept="image/png,image/jpeg,image/webp" data-overlay-file="${overlay.format}" />
          <div class="settings-actions">
            <button data-action="save-overlay-percent" data-format="${overlay.format}">Сохранить</button>
            <button data-action="delete-overlay" data-format="${overlay.format}" ${overlay.has_file ? "" : "disabled"}>Удалить</button>
          </div>
        </article>
      `).join("")}
    </details>
  `;
}

function bindSettingsEvents(root, deps) {
  bindAvatarEvents(root, deps, renderSettingsPanel);
  bindVoiceEvents(root, deps, renderSettingsPanel);
  root.querySelectorAll("[data-action='save-text']").forEach((button) => button.addEventListener("click", () => saveTextSetting(deps, button.dataset.key).catch(deps.showError)));
  root.querySelectorAll("[data-action='save-overlay-percent']").forEach((button) => button.addEventListener("click", () => saveOverlayPercent(deps, button.dataset.format).catch(deps.showError)));
  root.querySelectorAll("[data-action='delete-overlay']").forEach((button) => button.addEventListener("click", () => deleteOverlay(deps, button.dataset.format).catch(deps.showError)));
  root.querySelectorAll("[data-action='delete-ref']").forEach((button) => button.addEventListener("click", () => deleteMedia(deps, "thumbnail-references", button.dataset.id).catch(deps.showError)));
  root.querySelectorAll("[data-action='delete-face']").forEach((button) => button.addEventListener("click", () => deleteMedia(deps, "thumbnail-face-references", button.dataset.id).catch(deps.showError)));
  root.querySelectorAll("[data-action='delete-avatar-insert']").forEach((button) => button.addEventListener("click", () => deleteMedia(deps, "avatar-inserts", button.dataset.id).catch(deps.showError)));
  root.querySelectorAll("[data-action='delete-five-audio']").forEach((button) => button.addEventListener("click", () => deleteFiveAudio(deps, button.dataset.id).catch(deps.showError)));
  root.querySelectorAll("[data-action='delete-five-overlay']").forEach((button) => button.addEventListener("click", () => deleteFiveOverlay(deps).catch(deps.showError)));
  root.querySelectorAll("[data-target-ref]").forEach((button) => button.addEventListener("click", () => toggleRefTarget(deps, button.dataset.id, button.dataset.targetRef).catch(deps.showError)));
  root.querySelectorAll("[data-face-target]").forEach((button) => button.addEventListener("click", () => activateFace(deps, button.dataset.id, button.dataset.faceTarget).catch(deps.showError)));
  root.querySelectorAll("[data-upload]").forEach((input) => input.addEventListener("change", () => handleUpload(deps, input).catch(deps.showError)));
  root.querySelectorAll("[data-overlay-file]").forEach((input) => input.addEventListener("change", () => uploadOverlay(deps, input.dataset.overlayFile, input.files[0]).catch(deps.showError)));
}

async function saveTextSetting(deps, key) {
  const field = document.querySelector(`[data-setting="${key}"]`);
  deps.setStatus("Сохраняю");
  deps.state.settings = await deps.api("/api/settings/text", {
    method: "PATCH",
    body: JSON.stringify({ user_id: deps.state.userId, key, value: field.value }),
  });
  await loadSettingsData(deps);
  deps.setStatus("Сохранено");
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
  files.forEach((file) => form.append(input.dataset.upload === "five-second-overlay" ? "file" : "files", file));
  const paths = {
    "thumbnail-references": "/api/settings/thumbnail-references",
    "thumbnail-faces": "/api/settings/thumbnail-faces",
    "avatar-inserts": "/api/settings/avatar-inserts",
    "five-second-audio": "/api/settings/instagram-post-5s/audio",
    "five-second-overlay": "/api/settings/instagram-post-5s/overlay",
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

async function deleteFiveOverlay(deps) {
  await deps.api(`/api/settings/instagram-post-5s/overlay?user_id=${encodeURIComponent(deps.state.userId)}`, { method: "DELETE" });
  await loadSettingsData(deps);
}

function renderFaceReferences(state, escapeHtml) {
  if (!state.thumbnailFaces.length) return `<div class="empty-box">Фото лица не загружено</div>`;
  return `<div class="asset-grid">${state.thumbnailFaces.map((item) => {
    const isYoutube = item.url && itemUrlToPath(item) === state.settings.thumbnail_face_path;
    const isShorts = item.url && itemUrlToPath(item) === state.settings.vertical_thumbnail_face_path;
    return `
      <article class="thumb-card ${isYoutube || isShorts ? "selected" : ""}">
        <img src="${item.url}" alt="" />
        <button class="delete-chip" data-action="delete-face" data-id="${item.id}" title="Удалить">x</button>
        <div class="target-row">
          <button class="${isYoutube ? "active dark" : ""}" data-face-target="horizontal" data-id="${item.id}">YouTube</button>
          <button class="${isShorts ? "active" : ""}" data-face-target="vertical" data-id="${item.id}">Shorts</button>
        </div>
      </article>
    `;
  }).join("")}</div>`;
}

function renderThumbnailReferences(state) {
  if (!state.thumbnailReferences.length) return `<div class="empty-box">Референсы не загружены</div>`;
  return `<div class="asset-grid">${state.thumbnailReferences.map((item) => {
    const isYoutube = targetHas(item.target, "horizontal");
    const isShorts = targetHas(item.target, "vertical");
    return `
      <article class="thumb-card ${isYoutube || isShorts ? "selected" : ""}">
        <img src="${item.url}" alt="" />
        <button class="delete-chip" data-action="delete-ref" data-id="${item.id}" title="Удалить">x</button>
        <div class="target-row">
          <button class="${isYoutube ? "active dark" : ""}" data-target-ref="horizontal" data-id="${item.id}">YouTube</button>
          <button class="${isShorts ? "active" : ""}" data-target-ref="vertical" data-id="${item.id}">Shorts</button>
        </div>
      </article>
    `;
  }).join("")}</div>`;
}

function renderSimpleAssetList(items, escapeHtml, action) {
  if (!items.length) return `<div class="empty-box compact-empty">Пока пусто</div>`;
  return items.map((item) => `
    <article class="asset-card text-card media-card">
      <div><strong>${escapeHtml(item.file_name)}</strong><small>#${item.id}</small></div>
      <button data-action="${action}" data-id="${item.id}">Удалить</button>
    </article>
  `).join("");
}

function renderSummary(title, chips, escapeHtml) {
  return `
    <summary>
      <span class="summary-title">${escapeHtml(title)}</span>
      <span class="summary-chips">
        ${chips.map((chip) => `<span class="summary-chip ${chip.muted ? "muted" : ""}">${escapeHtml(chip.label)}</span>`).join("")}
      </span>
    </summary>
  `;
}

function identitySummaryChips(settings) {
  return [
    chip(settings.heygen_avatar_name ? `YT: ${settings.heygen_avatar_name}` : "YT avatar не выбран", !settings.heygen_avatar_name),
    chip(settings.heygen_vertical_avatar_name ? `Shorts: ${settings.heygen_vertical_avatar_name}` : "Shorts avatar не выбран", !settings.heygen_vertical_avatar_name),
    chip(settings.elevenlabs_voice_name || "Голос не выбран", !settings.elevenlabs_voice_name),
  ];
}

function coverSummaryChips(state) {
  const youtubeFace = Boolean(state.settings.thumbnail_face_path);
  const shortsFace = Boolean(state.settings.vertical_thumbnail_face_path);
  const activeRefs = state.thumbnailReferences.filter((item) => targetHas(item.target, "horizontal") || targetHas(item.target, "vertical")).length;
  return [
    chip(`Лицо: ${[youtubeFace && "YT", shortsFace && "Shorts"].filter(Boolean).join(" + ") || "не выбрано"}`, !youtubeFace && !shortsFace),
    chip(`Референсов: ${state.thumbnailReferences.length}`),
    chip(`Активных: ${activeRefs}`, activeRefs === 0),
  ];
}

function avatarInsertSummaryChips(state) {
  const settings = state.settings;
  return [
    chip(`Клипов: ${state.avatarInserts.length}`, state.avatarInserts.length === 0),
    chip(`Вставок: ${settings.avatar_insert_clips_count ?? 0}`),
    chip(`${settings.avatar_insert_start_percent ?? 0}-${settings.avatar_insert_end_percent ?? 100}%`),
  ];
}

function fiveSecondSummaryChips(five) {
  const audioCount = five.audio_tracks?.length || 0;
  return [
    chip(`Аудио: ${audioCount}`, audioCount === 0),
    chip(five.overlay_url ? "Плашка есть" : "Плашки нет", !five.overlay_url),
    chip(five.cta_text ? "CTA заполнен" : "CTA пустой", !five.cta_text),
  ];
}

function textSummaryChips(rows) {
  const filled = rows.filter(([, , value]) => String(value || "").trim()).length;
  return [chip(`Заполнено: ${filled}/${rows.length}`, filled < rows.length)];
}

function overlaySummaryChips(state) {
  const overlays = state.settings.overlays || [];
  const ready = overlays.filter((overlay) => overlay.has_file).length;
  return [chip(`Загружено: ${ready}/${overlays.length}`, ready === 0)];
}

function chip(label, muted = false) {
  return { label, muted };
}

function numberField(key, label, value, min, max) {
  return `
    <div>
      <label>${label}</label>
      <input type="number" min="${min}" max="${max}" value="${value}" data-setting="${key}" />
      <button data-action="save-text" data-key="${key}">Сохранить</button>
    </div>
  `;
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

function itemUrlToPath(item) {
  return item.file_path || "";
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
