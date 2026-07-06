import { chip, formatHeader, settingsDisclosure } from "/static/settings_sections.js?v=20260617-plan-buttons";

const PROVIDER_OPTIONS = [
  ["hyperframes", "HyperFrames"],
  ["zapcap", "ZapCap"],
  ["off", "Без обработки"],
];

const LANGUAGE_OPTIONS = [
  ["auto", "Auto"],
  ["ru", "Русский"],
  ["en", "English"],
  ["es", "Español"],
];

export function renderZapcapTab({ state, escapeHtml }) {
  const settings = state.settings.zapcap || {};
  const templates = state.zapcapTemplates || [];
  return `
    ${formatHeader("ZapCap оформление", "HeyGen видео отправляется в ZapCap: транскрибация, дизайнерские субтитры и финальный MP4.", zapcapSummaryChips(settings), escapeHtml)}
    <section class="settings-stack">
      ${settingsDisclosure("Режим", providerChips(settings), `
        <div class="settings-two">
          ${selectSetting("postprocess_provider", "Обработка после HeyGen", settings.postprocess_provider || "hyperframes", PROVIDER_OPTIONS, escapeHtml)}
          ${toggleSetting("zapcap_subtitles_enabled", "Дизайнерские субтитры", settings.subtitles_enabled !== false, escapeHtml)}
        </div>
        <div class="settings-three">
          ${templateSetting(settings.template_id || "", templates, escapeHtml)}
          ${selectSetting("zapcap_language", "Язык транскрибации", settings.language || "auto", LANGUAGE_OPTIONS, escapeHtml)}
          ${numberSetting("zapcap_broll_percent", "B-roll, %", settings.broll_percent || 0, 0, 100)}
        </div>
        ${saveSectionButton(escapeHtml)}
      `, escapeHtml)}
      ${settingsDisclosure("Вид субтитров", subtitleChips(settings), `
        <div class="settings-three">
          ${toggleSetting("zapcap_emoji", "Emoji", settings.emoji !== false, escapeHtml)}
          ${toggleSetting("zapcap_emoji_animation", "Emoji animation", settings.emoji_animation !== false, escapeHtml)}
          ${toggleSetting("zapcap_emphasize_keywords", "Highlight keywords", settings.emphasize_keywords !== false, escapeHtml)}
          ${toggleSetting("zapcap_animation", "Анимация слов", settings.animation !== false, escapeHtml)}
          ${toggleSetting("zapcap_punctuation", "Пунктуация", settings.punctuation !== false, escapeHtml)}
          ${toggleSetting("zapcap_font_uppercase", "Uppercase", settings.font_uppercase === true, escapeHtml)}
        </div>
        <div class="settings-three">
          ${numberSetting("zapcap_display_words", "Слов на экране", settings.display_words || 3, 1, 8)}
          ${numberSetting("zapcap_font_size", "Размер", settings.font_size || 72, 24, 140)}
          ${numberSetting("zapcap_top", "Позиция сверху, %", settings.top || 62, 0, 100)}
          ${numberSetting("zapcap_stroke", "Обводка", settings.stroke || 8, 0, 24)}
          ${colorSetting("zapcap_font_color", "Цвет текста", settings.font_color || "#FFFFFF", escapeHtml)}
          ${colorSetting("zapcap_highlight_color", "Цвет выделения", settings.highlight_color || "#FFE45C", escapeHtml)}
          ${colorSetting("zapcap_stroke_color", "Цвет обводки", settings.stroke_color || "#000000", escapeHtml)}
        </div>
        ${saveSectionButton(escapeHtml)}
      `, escapeHtml)}
    </section>
  `;
}

function templateSetting(value, templates, escapeHtml) {
  if (!templates.length) {
    return textSetting("zapcap_template_id", "ZapCap Template ID", value, 120, escapeHtml);
  }
  const options = templates.map((item) => [item.id, item.name || item.id]);
  const hasSelected = options.some(([id]) => id === value);
  const normalizedOptions = hasSelected || !value ? options : [[value, `Текущий: ${value}`], ...options];
  return selectSetting("zapcap_template_id", "Стиль субтитров", value, normalizedOptions, escapeHtml);
}

function selectSetting(key, label, value, options, escapeHtml) {
  return `
    <div class="soft-box">
      <label>${escapeHtml(label)}</label>
      <select data-setting="${escapeHtml(key)}">
        ${options.map(([optionValue, optionLabel]) => `<option value="${escapeHtml(optionValue)}" ${String(value) === optionValue ? "selected" : ""}>${escapeHtml(optionLabel)}</option>`).join("")}
      </select>
    </div>
  `;
}

function textSetting(key, label, value, maxLength, escapeHtml) {
  return `
    <div>
      <label>${escapeHtml(label)}</label>
      <input data-setting="${escapeHtml(key)}" maxlength="${maxLength}" value="${escapeHtml(value)}" />
    </div>
  `;
}

function numberSetting(key, label, value, min, max) {
  const safeValue = value === null || value === undefined ? "" : String(value);
  return `
    <div>
      <label>${label}</label>
      <input type="number" inputmode="numeric" min="${min}" max="${max}" value="${safeValue}" data-setting="${key}" />
    </div>
  `;
}

function colorSetting(key, label, value, escapeHtml) {
  return `
    <div>
      <label>${escapeHtml(label)}</label>
      <input type="color" value="${escapeHtml(value)}" data-setting="${escapeHtml(key)}" />
    </div>
  `;
}

function toggleSetting(key, label, checked, escapeHtml) {
  return `
    <label class="toggle-row">
      <span>${escapeHtml(label)}</span>
      <select data-setting="${escapeHtml(key)}">
        <option value="1" ${checked ? "selected" : ""}>вкл</option>
        <option value="0" ${checked ? "" : "selected"}>выкл</option>
      </select>
    </label>
  `;
}

function saveSectionButton(escapeHtml) {
  return `<button type="button" data-action="save-section">${escapeHtml("Сохранить секцию")}</button>`;
}

function zapcapSummaryChips(settings) {
  return [
    chip(providerLabel(settings.postprocess_provider || "hyperframes")),
    chip(settings.template_id ? "template выбран" : "template пустой", !settings.template_id),
    chip(`b-roll ${settings.broll_percent || 0}%`, Number(settings.broll_percent || 0) === 0),
  ];
}

function providerChips(settings) {
  return [
    chip(providerLabel(settings.postprocess_provider || "hyperframes")),
    chip(settings.subtitles_enabled === false ? "субтитры выкл" : "субтитры вкл", settings.subtitles_enabled === false),
  ];
}

function subtitleChips(settings) {
  const enabled = [
    settings.emoji !== false && "emoji",
    settings.emphasize_keywords !== false && "highlight",
    settings.animation !== false && "animation",
    settings.font_uppercase && "uppercase",
  ].filter(Boolean);
  return [
    chip(enabled.length ? enabled.join(", ") : "минимально", enabled.length === 0),
    chip(`${settings.display_words || 3} слова`),
  ];
}

function providerLabel(value) {
  const found = PROVIDER_OPTIONS.find(([option]) => option === value);
  return found ? found[1] : "HyperFrames";
}
