import { chip } from "/static/settings_sections.js?v=20260617-plan-buttons";

export function renderCoverAssetsSection(state, escapeHtml) {
  return `
    <div class="settings-two cover-grid">
      ${faceReferenceBox(state, "horizontal", escapeHtml, "Лицо для YouTube")}
      ${faceReferenceBox(state, "vertical", escapeHtml, "Лицо для Instagram и инфографики")}
    </div>
    ${thumbnailLibraryBox(state, escapeHtml)}
  `;
}

export function faceReferenceBox(state, target, escapeHtml, title = "Референс лица") {
  return `
    <div class="soft-box">
      <div class="box-head">
        <h3>${escapeHtml(title)}</h3>
        <label class="upload-button">
          Загрузить
          <input type="file" multiple accept="image/png,image/jpeg,image/webp" data-upload="thumbnail-faces" />
        </label>
      </div>
      ${renderFaceReferences(state, escapeHtml, target)}
    </div>
  `;
}

export function thumbnailLibraryBox(state, escapeHtml) {
  return `
    <div class="soft-box">
      <div class="box-head">
        <h3>Общая медиатека обложек</h3>
        <label class="upload-button blue">
          Добавить
          <input type="file" multiple accept="image/png,image/jpeg,image/webp" data-upload="thumbnail-references" />
        </label>
      </div>
      <p>Здесь можно включать один референс для YouTube, Instagram или обоих форматов.</p>
      ${renderAllThumbnailReferences(state, escapeHtml)}
    </div>
  `;
}

export function coverSummaryChips(state, target) {
  const facePath = target === "horizontal" ? state.settings.thumbnail_face_path : state.settings.vertical_thumbnail_face_path;
  const refs = state.thumbnailReferences.filter((item) => targetHas(item.target, target)).length;
  return [
    chip(facePath ? "лицо выбрано" : "лицо не выбрано", !facePath),
    chip(`refs: ${refs}`, refs === 0),
  ];
}

export function commonCoverSummaryChips(state) {
  const faceCount = [state.settings.thumbnail_face_path, state.settings.vertical_thumbnail_face_path].filter(Boolean).length;
  return [
    chip(`лиц: ${faceCount}/2`, faceCount === 0),
    chip(`refs: ${state.thumbnailReferences.length}`, state.thumbnailReferences.length === 0),
  ];
}

function renderFaceReferences(state, escapeHtml, target) {
  if (!state.thumbnailFaces.length) return `<div class="empty-box">Фото лица не загружено</div>`;
  return `<div class="asset-grid">${state.thumbnailFaces.map((item) => {
    const activePath = target === "horizontal" ? state.settings.thumbnail_face_path : state.settings.vertical_thumbnail_face_path;
    const isActive = item.url && item.file_path === activePath;
    return `
      <article class="thumb-card ${isActive ? "selected" : ""}">
        <img src="${item.url}" alt="" />
        <button class="delete-chip" data-action="delete-face" data-id="${item.id}" title="Удалить">x</button>
        <div class="target-row">
          <button class="${isActive ? "active" : ""}" data-face-target="${target}" data-id="${item.id}">${targetLabel(target)}</button>
        </div>
        <small>${escapeHtml(item.file_name)}</small>
      </article>
    `;
  }).join("")}</div>`;
}

function renderAllThumbnailReferences(state, escapeHtml) {
  if (!state.thumbnailReferences.length) return `<div class="empty-box">Референсы обложек не загружены</div>`;
  return `<div class="asset-grid">${state.thumbnailReferences.map((item) => {
    const isYoutube = targetHas(item.target, "horizontal");
    const isShorts = targetHas(item.target, "vertical");
    return `
      <article class="thumb-card ${isYoutube || isShorts ? "selected" : ""}">
        <img src="${item.url}" alt="" />
        <button class="delete-chip" data-action="delete-ref" data-id="${item.id}" title="Удалить">x</button>
        <div class="target-row">
          <button class="${isYoutube ? "active dark" : ""}" data-target-ref="horizontal" data-id="${item.id}">YouTube</button>
          <button class="${isShorts ? "active" : ""}" data-target-ref="vertical" data-id="${item.id}">Instagram</button>
        </div>
        <small>${escapeHtml(item.file_name)}</small>
      </article>
    `;
  }).join("")}</div>`;
}

function targetHas(value, target) {
  return value === "both" || value === target;
}

function targetLabel(target) {
  return target === "horizontal" ? "YouTube" : "Instagram";
}
