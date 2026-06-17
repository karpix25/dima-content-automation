import { renderAvatarSelectors } from "/static/settings_avatars.js?v=20260617-feedback";
import { chip, formatHeader, settingsDisclosure } from "/static/settings_sections.js?v=20260617-feedback";
import { renderVizardTab } from "/static/settings_vizard.js?v=20260617-feedback";
import { renderVoiceSelector } from "/static/settings_voices.js?v=20260617-feedback";
import { renderIdeasTab } from "/static/settings_ideas.js?v=20260617-feedback";

const FORMAT_TABS = [
  { key: "youtube", label: "YouTube", hint: "Горизонтальный" },
  { key: "shorts", label: "Instagram", hint: "Вертикальный" },
  { key: "five", label: "5 секунд", hint: "Инфографика" },
  { key: "vizard", label: "Vizard", hint: "YouTube clips" },
  { key: "ideas", label: "Идеи", hint: "Reddit" },
  { key: "common", label: "Общие", hint: "База" },
];

export function renderSettingsContent(deps) {
  const { state, escapeHtml } = deps;
  const active = activeSettingsTab(state);
  return `
    <div class="format-settings-shell">
      <div class="format-tabbar" role="tablist" aria-label="Разделы настроек">
        ${FORMAT_TABS.map((tab) => formatTabButton(tab, active, escapeHtml)).join("")}
      </div>
      <div class="format-tab-panel">
        ${renderActiveFormatTab(active, deps)}
      </div>
    </div>
  `;
}

export function activeSettingsTab(state) {
  const saved = state.settingsFormatTab || localStorage.getItem("dima_settings_format_tab") || "youtube";
  return FORMAT_TABS.some((tab) => tab.key === saved) ? saved : "youtube";
}

function formatTabButton(tab, active, escapeHtml) {
  return `
    <button
      type="button"
      class="${active === tab.key ? "active" : ""}"
      data-settings-format-tab="${escapeHtml(tab.key)}"
      role="tab"
      aria-selected="${active === tab.key ? "true" : "false"}"
    >
      <strong>${escapeHtml(tab.label)}</strong>
      <span>${escapeHtml(tab.hint)}</span>
    </button>
  `;
}

function renderActiveFormatTab(active, deps) {
  if (active === "shorts") return renderShortsTab(deps);
  if (active === "five") return renderFiveSecondTab(deps);
  if (active === "vizard") return renderVizardTab(deps);
  if (active === "ideas") return renderIdeasTab(deps);
  if (active === "common") return renderCommonTab(deps);
  return renderYoutubeTab(deps);
}

function renderYoutubeTab({ state, escapeHtml }) {
  const settings = state.settings;
  return `
    ${formatHeader("YouTube горизонтальный", "Аватар, обложка, вставки и финальная плашка для long-ролика.", youtubeSummaryChips(state), escapeHtml)}
    <section class="settings-stack">
      ${settingsDisclosure("Выход и длительность", youtubeOutputChips(state), `
        <div class="settings-two">
          ${durationCard("youtube_long_duration_minutes", "Длина long YouTube сценария", `${settings.youtube_long_duration_minutes || 10}`, "мин", [
            ["5", "5 мин"],
            ["7", "7 мин"],
            ["10", "10 мин"],
            ["12", "12 мин"],
            ["15", "15 мин"],
          ], escapeHtml)}
          ${overlayCard(state, "youtube", escapeHtml)}
        </div>
      `, escapeHtml)}
      ${settingsDisclosure("HeyGen avatar", [chip(state.settings.heygen_avatar_name || "не выбран", !state.settings.heygen_avatar_name)], `
        <div class="soft-box compact-host">
          ${renderAvatarSelectors(state, escapeHtml, { target: "horizontal" })}
        </div>
      `, escapeHtml)}
      ${settingsDisclosure("Обложки и лицо", coverSummaryChips(state, "horizontal"), `
        <div class="settings-two cover-grid">
          ${faceReferenceBox(state, "horizontal", escapeHtml)}
          ${thumbnailReferenceBox(state, "horizontal", escapeHtml)}
        </div>
      `, escapeHtml)}
      ${settingsDisclosure("Видео-вставки", avatarInsertSummaryChips(state), avatarInsertBox(state, escapeHtml), escapeHtml)}
      ${settingsDisclosure("Описание YouTube", [chip(settings.youtube_description_template ? "шаблон задан" : "пусто", !settings.youtube_description_template)], textAreaSetting("youtube_description_template", "Шаблон описания YouTube", settings.youtube_description_template || "", 5, escapeHtml), escapeHtml)}
    </section>
  `;
}

function renderShortsTab({ state, escapeHtml }) {
  const settings = state.settings;
  return `
    ${formatHeader("Вертикальное видео", "Один входной ролик, два выхода: Shorts и Reels со своими финальными плашками.", shortsSummaryChips(state), escapeHtml)}
    <section class="settings-stack">
      ${settingsDisclosure("Финальные плашки", verticalOverlayChips(state), `
        <div class="settings-two">
          ${overlayCard(state, "shorts", escapeHtml)}
          ${overlayCard(state, "reels", escapeHtml)}
        </div>
      `, escapeHtml)}
      ${settingsDisclosure("Avatar и длительность", [chip(state.settings.heygen_vertical_avatar_name || "avatar не выбран", !state.settings.heygen_vertical_avatar_name), chip(verticalLabel(settings.vertical_avatar_duration_mode))], `
        <div class="settings-two">
          ${durationCard("vertical_avatar_duration_mode", "Длина вертикального AI-аватара", settings.vertical_avatar_duration_mode || "original", "", [
            ["original", "по оригиналу"],
            ["30", "30 сек"],
            ["45", "45 сек"],
            ["60", "60 сек"],
            ["90", "90 сек"],
          ], escapeHtml)}
          <div class="soft-box compact-host">
            ${renderAvatarSelectors(state, escapeHtml, { target: "vertical" })}
          </div>
        </div>
      `, escapeHtml)}
      ${settingsDisclosure("Обложки и лицо", coverSummaryChips(state, "vertical"), `
        <div class="settings-two cover-grid">
          ${faceReferenceBox(state, "vertical", escapeHtml)}
          ${thumbnailReferenceBox(state, "vertical", escapeHtml)}
        </div>
      `, escapeHtml)}
    </section>
  `;
}

function renderFiveSecondTab({ state, escapeHtml }) {
  const five = state.fiveSecondSettings || { audio_tracks: [], infographic_references: [] };
  return `
    ${formatHeader("5 секунд / золотая инфографика", "Kie генерирует карточку по сценарию, лицу и референсам дизайна. Обложка здесь не используется.", fiveSecondSummaryChips(five, state), escapeHtml)}
    <section class="settings-stack">
      ${settingsDisclosure("CTA", [chip(five.cta_text ? "задан" : "пусто", !five.cta_text)], textInputSetting("instagram_post_5s_cta_text", "CTA в нижнем белом фрейме", five.cta_text || "", 180, escapeHtml), escapeHtml)}
      ${settingsDisclosure("Лицо и дизайн", fiveSecondSummaryChips(five, state), `
        <div class="settings-two cover-grid">
          ${faceReferenceBox(state, "vertical", escapeHtml, "Референс лица для инфографики")}
          ${fiveSecondReferenceBox(five, escapeHtml)}
        </div>
      `, escapeHtml)}
      ${settingsDisclosure("Аудио", [chip(`аудио: ${five.audio_tracks.length}`, five.audio_tracks.length === 0)], fiveSecondAudioBox(five, escapeHtml), escapeHtml)}
    </section>
  `;
}

function renderCommonTab({ state, escapeHtml }) {
  const settings = state.settings;
  return `
    ${formatHeader("Общие настройки", "База для контента: NotebookLM, голос, модель HeyGen и стиль текстов.", commonSummaryChips(state), escapeHtml)}
    <section class="settings-stack">
      ${settingsDisclosure("Голос и модель", commonSummaryChips(state), `
        <div class="settings-two">
          <div class="soft-box">
            <h3>Голос ElevenLabs</h3>
            ${renderVoiceSelector(state, escapeHtml)}
          </div>
          <div class="soft-box">
            <h3>Модель HeyGen</h3>
            ${renderAvatarSelectors(state, escapeHtml, { mode: "model" })}
          </div>
        </div>
      `, escapeHtml)}
      ${settingsDisclosure("NotebookLM", [chip(settings.notebook_id ? "задан" : "пустой", !settings.notebook_id)], textAreaSetting("notebook_id", "NotebookLM ID", settings.notebook_id || "", 2, escapeHtml), escapeHtml)}
      ${settingsDisclosure("Язык контента", [chip(contentLanguageLabel(settings.content_language || "auto"))], `
        ${durationCard("content_language", "Язык для сценариев, обложек и Kie", settings.content_language || "auto", "", [
          ["auto", "Auto: как в оригинале"],
          ["en", "English"],
          ["ru", "Русский"],
        ], escapeHtml)}
      `, escapeHtml)}
      ${settingsDisclosure("Стиль и оффер", [chip(settings.author_style ? "стиль" : "стиль пустой", !settings.author_style), chip(settings.offer_context ? "оффер" : "оффер пустой", !settings.offer_context)], `
        ${textAreaSetting("author_style", "Стиль автора", settings.author_style || "", 5, escapeHtml)}
        ${textAreaSetting("offer_context", "Контекст оффера", settings.offer_context || "", 5, escapeHtml)}
        ${textAreaSetting("cta_mix", "Логика CTA", settings.cta_mix || "", 5, escapeHtml)}
      `, escapeHtml)}
      ${settingsDisclosure("Медиатека обложек", [chip(`refs: ${state.thumbnailReferences.length}`, state.thumbnailReferences.length === 0)], thumbnailLibraryBox(state, escapeHtml), escapeHtml)}
    </section>
  `;
}

function durationCard(key, title, value, suffix, options, escapeHtml) {
  return `
    <article class="duration-card">
      <div class="duration-icon" aria-hidden="true">${durationIcon()}</div>
      <h3>${escapeHtml(title)}</h3>
      <select data-setting="${escapeHtml(key)}">
        ${options.map(([optionValue, label]) => `
          <option value="${escapeHtml(optionValue)}" ${String(value) === optionValue ? "selected" : ""}>${escapeHtml(label)}</option>
        `).join("")}
      </select>
      ${suffix ? `<span class="duration-suffix">${escapeHtml(suffix)}</span>` : ""}
      <button data-action="save-text" data-key="${escapeHtml(key)}">Сохранить</button>
    </article>
  `;
}

function faceReferenceBox(state, target, escapeHtml, title = "Референс лица") {
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

function thumbnailReferenceBox(state, target, escapeHtml) {
  return `
    <div class="soft-box">
      <div class="box-head">
        <h3>Референсы обложек</h3>
        <label class="upload-button blue">
          Добавить
          <input type="file" multiple accept="image/png,image/jpeg,image/webp" data-upload="thumbnail-references" data-upload-target="${target}" />
        </label>
      </div>
      ${renderThumbnailReferences(state, target)}
      <p>Эти референсы используются только для обложек выбранного формата.</p>
    </div>
  `;
}

function thumbnailLibraryBox(state, escapeHtml) {
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

function avatarInsertBox(state, escapeHtml) {
  const settings = state.settings;
  return `
    <div class="soft-box">
      <div class="box-head">
        <h3>Видео-вставки</h3>
        <label class="upload-button blue">
          Добавить видео
          <input type="file" multiple accept="video/mp4,video/quicktime,video/webm,video/x-matroska,video/x-m4v" data-upload="avatar-inserts" />
        </label>
      </div>
      <div class="settings-three">
        ${numberField("avatar_insert_start_percent", "Старт вставок (%)", settings.avatar_insert_start_percent, 0, 99)}
        ${numberField("avatar_insert_end_percent", "Финиш вставок (%)", settings.avatar_insert_end_percent, 1, 100)}
        ${numberField("avatar_insert_clips_count", "Сколько вставок", settings.avatar_insert_clips_count, 0, 20)}
      </div>
      <div class="asset-list">${renderSimpleAssetList(state.avatarInserts, escapeHtml, "delete-avatar-insert")}</div>
    </div>
  `;
}

function overlayCard(state, format, escapeHtml) {
  const overlay = (state.settings.overlays || []).find((item) => item.format === format);
  if (!overlay) return `<div class="soft-box"><h3>Финальная плашка</h3><div class="empty-box compact-empty">Настройка не найдена</div></div>`;
  return `
    <article class="overlay-card ${overlay.has_file ? "selected" : ""}">
      <div>
        <strong>Финальные плашки ${escapeHtml(overlay.label)}</strong>
        <p>${overlay.has_file ? escapeHtml(overlay.file_name) : "Файлы не загружены"}</p>
      </div>
      ${overlay.has_file ? `<img src="/api/settings/overlay/file?user_id=${encodeURIComponent(state.userId)}&format=${encodeURIComponent(overlay.format)}&t=${Date.now()}" alt="" />` : ""}
      ${window.renderOverlayFiles ? window.renderOverlayFiles(overlay) : ""}
      <label>Старт %</label>
      <input type="number" min="0" max="100" value="${overlay.start_percent}" data-overlay-percent="${overlay.format}" />
      <input type="file" accept="image/png,image/jpeg,image/webp" data-overlay-file="${overlay.format}" />
      <div class="settings-actions">
        <button data-action="save-overlay-percent" data-format="${overlay.format}">Сохранить</button>
        <button data-action="delete-overlay" data-format="${overlay.format}" ${overlay.has_file ? "" : "disabled"}>Удалить все</button>
      </div>
    </article>
  `;
}

function fiveSecondReferenceBox(five, escapeHtml) {
  return `
    <div class="soft-box">
      <div class="box-head">
        <h3>Референсы дизайна инфографики</h3>
        <label class="upload-button blue">
          Добавить
          <input type="file" multiple accept="image/png,image/jpeg,image/webp" data-upload="five-second-reference" />
        </label>
      </div>
      <p>Только дизайн: композиция, иерархия, сетка и стиль. Текст и лица из референсов дизайна не копируются.</p>
      <div class="thumb-grid">${renderFiveSecondReferences(five.infographic_references || [], escapeHtml)}</div>
    </div>
  `;
}

function fiveSecondAudioBox(five, escapeHtml) {
  return `
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
  `;
}

function textInputSetting(key, label, value, maxLength, escapeHtml) {
  return `
    <div class="soft-box">
      <label>${escapeHtml(label)}</label>
      <input data-setting="${escapeHtml(key)}" maxlength="${maxLength}" value="${escapeHtml(value)}" />
      <button data-action="save-text" data-key="${escapeHtml(key)}">Сохранить</button>
    </div>
  `;
}

function textAreaSetting(key, label, value, rows, escapeHtml) {
  return `
    <div class="soft-box">
      <label>${escapeHtml(label)}</label>
      <textarea data-setting="${escapeHtml(key)}" rows="${rows}">${escapeHtml(value)}</textarea>
      <button data-action="save-text" data-key="${escapeHtml(key)}">Сохранить</button>
    </div>
  `;
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
      </article>
    `;
  }).join("")}</div>`;
}

function renderThumbnailReferences(state, target) {
  const items = state.thumbnailReferences.filter((item) => targetHas(item.target, target));
  if (!items.length) return `<div class="empty-box">Референсы для этого формата не загружены</div>`;
  return `<div class="asset-grid">${items.map((item) => `
    <article class="thumb-card selected">
      <img src="${item.url}" alt="" />
      <button class="delete-chip" data-action="delete-ref" data-id="${item.id}" title="Удалить">x</button>
      <div class="target-row">
        <button class="active ${target === "horizontal" ? "dark" : ""}" data-target-ref="${target}" data-id="${item.id}">${targetLabel(target)}</button>
      </div>
    </article>
  `).join("")}</div>`;
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

function renderSimpleAssetList(items, escapeHtml, action) {
  if (!items.length) return `<div class="empty-box compact-empty">Пока пусто</div>`;
  return items.map((item) => `
    <article class="asset-card text-card media-card">
      <div><strong>${escapeHtml(item.file_name)}</strong><small>#${item.id}</small></div>
      <button data-action="${action}" data-id="${item.id}">Удалить</button>
    </article>
  `).join("");
}

function renderFiveSecondReferences(items, escapeHtml) {
  if (!items.length) return `<div class="empty-box compact-empty">Референсы дизайна не загружены</div>`;
  return items.map((item) => `
    <article class="thumb-card selected">
      <img src="${item.url}" alt="" />
      <button class="delete-chip" data-action="delete-five-reference" data-id="${item.id}" title="Удалить">x</button>
      <small>${escapeHtml(item.file_name)}</small>
    </article>
  `).join("");
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

function youtubeSummaryChips(state) {
  return [
    chip(state.settings.heygen_avatar_name || "avatar не выбран", !state.settings.heygen_avatar_name),
    chip(state.settings.thumbnail_face_path ? "лицо выбрано" : "лицо не выбрано", !state.settings.thumbnail_face_path),
    chip(`${state.settings.youtube_long_duration_minutes || 10} мин`),
  ];
}

function youtubeOutputChips(state) {
  const overlay = overlayState(state, "youtube");
  return [
    chip(`${state.settings.youtube_long_duration_minutes || 10} мин`),
    chip(overlay?.has_file ? "плашка есть" : "плашки нет", !overlay?.has_file),
  ];
}

function shortsSummaryChips(state) {
  return [
    chip(state.settings.heygen_vertical_avatar_name || "avatar не выбран", !state.settings.heygen_vertical_avatar_name),
    ...verticalOverlayChips(state),
    chip(verticalLabel(state.settings.vertical_avatar_duration_mode)),
  ];
}

function verticalOverlayChips(state) {
  const shorts = overlayState(state, "shorts");
  const reels = overlayState(state, "reels");
  return [
    chip(shorts?.has_file ? "Shorts есть" : "Shorts нет", !shorts?.has_file),
    chip(reels?.has_file ? "Reels есть" : "Reels нет", !reels?.has_file),
  ];
}

function coverSummaryChips(state, target) {
  const facePath = target === "horizontal" ? state.settings.thumbnail_face_path : state.settings.vertical_thumbnail_face_path;
  const refs = state.thumbnailReferences.filter((item) => targetHas(item.target, target)).length;
  return [
    chip(facePath ? "лицо выбрано" : "лицо не выбрано", !facePath),
    chip(`refs: ${refs}`, refs === 0),
  ];
}

function avatarInsertSummaryChips(state) {
  const settings = state.settings;
  return [
    chip(`вставок: ${settings.avatar_insert_clips_count ?? 0}`, !settings.avatar_insert_clips_count),
    chip(`${settings.avatar_insert_start_percent ?? 50}-${settings.avatar_insert_end_percent ?? 95}%`),
  ];
}

function fiveSecondSummaryChips(five, state) {
  const audioCount = five.audio_tracks?.length || 0;
  const referenceCount = five.infographic_references?.length || 0;
  return [
    chip(state.settings.vertical_thumbnail_face_path ? "лицо выбрано" : "лицо не выбрано", !state.settings.vertical_thumbnail_face_path),
    chip(`дизайн refs: ${referenceCount}`, referenceCount === 0),
    chip(`аудио: ${audioCount}`, audioCount === 0),
  ];
}

function commonSummaryChips(state) {
  return [
    chip(state.settings.elevenlabs_voice_name || "голос не выбран", !state.settings.elevenlabs_voice_name),
    chip(contentLanguageLabel(state.settings.content_language || "auto")),
    chip(state.settings.notebook_id ? "NotebookLM задан" : "NotebookLM пустой", !state.settings.notebook_id),
  ];
}

function contentLanguageLabel(value) {
  if (value === "en") return "English";
  if (value === "ru") return "Русский";
  return "Auto язык";
}

function overlayState(state, format) {
  return (state.settings.overlays || []).find((item) => item.format === format);
}

function targetHas(value, target) {
  return value === "both" || value === target;
}

function targetLabel(target) {
  return target === "horizontal" ? "YouTube" : "Instagram";
}

function verticalLabel(value) {
  if (!value || value === "original") return "по оригиналу";
  return `${value} сек`;
}

function durationIcon() {
  return `<svg viewBox="0 0 24 24" width="20" height="20"><path d="M6 4h12v16H6zM9 4v16M15 4v16M6 8h3M15 8h3M6 12h3M15 12h3M6 16h3M15 16h3" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>`;
}
