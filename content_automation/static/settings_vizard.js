import { chip, formatHeader, settingsDisclosure } from "/static/settings_sections.js?v=20260617-plan-extend";

const LENGTH_OPTIONS = [
  ["0", "auto"],
  ["1", "< 30 сек"],
  ["2", "30-60 сек"],
  ["3", "60-90 сек"],
  ["4", "90 сек - 3 мин"],
];

const RATIO_OPTIONS = [
  ["1", "9:16 вертикальный"],
  ["4", "16:9 горизонтальный"],
  ["2", "1:1 квадрат"],
  ["3", "4:5 портрет"],
];

export function renderVizardTab({ state, escapeHtml }) {
  const settings = state.settings.vizard || {};
  return `
    ${formatHeader("Vizard нарезка YouTube", "Отправь YouTube-ссылку в бот, Vizard сам найдет клипы и вернет ролики.", vizardSummaryChips(settings), escapeHtml)}
    <section class="settings-stack">
      ${settingsDisclosure("Основные", [chip(ratioLabel(settings.ratio_of_clip || 1)), chip(lengthLabel(settings.prefer_length || [0])), chip(`тишина: ${settings.remove_silence_switch ? "вкл" : "выкл"}`)], `
        <div class="settings-two">
          ${selectSetting("vizard_ratio_of_clip", "Формат финального ролика", String(settings.ratio_of_clip || 1), RATIO_OPTIONS, escapeHtml)}
          ${selectSetting("vizard_prefer_length", "Длина единицы ролика", String((settings.prefer_length || [0])[0] || 0), LENGTH_OPTIONS, escapeHtml)}
        </div>
        <div class="soft-box">
          ${toggleSetting("vizard_remove_silence_switch", "Убрать паузы", settings.remove_silence_switch, escapeHtml)}
        </div>
        ${saveSectionButton(escapeHtml)}
      `, escapeHtml)}
      ${settingsDisclosure("Отбор клипов", [chip(`до ${settings.max_clip_number || 10}`), chip(settings.keywords ? "keywords заданы" : "keywords пустые", !settings.keywords)], `
        <div class="settings-three">
          ${smallTextSetting("vizard_lang", "Язык видео", settings.lang || "en", 12, escapeHtml)}
          ${numberSetting("vizard_max_clip_number", "Максимум клипов", settings.max_clip_number || 10, 1, 100)}
          ${numberSetting("vizard_template_id", "Template ID", settings.template_id || "", 1, 999999999)}
        </div>
        ${textAreaSetting("vizard_keywords", "Keywords для отбора тем", settings.keywords || "", 3, escapeHtml)}
        ${saveSectionButton(escapeHtml)}
      `, escapeHtml)}
      ${settingsDisclosure("Автооформление", autoSwitchChips(settings), `
        <div class="soft-box">
          <div class="settings-three">
            ${toggleSetting("vizard_subtitle_switch", "Субтитры", settings.subtitle_switch, escapeHtml)}
            ${toggleSetting("vizard_headline_switch", "Headline/hook", settings.headline_switch, escapeHtml)}
            ${toggleSetting("vizard_emoji_switch", "Emoji", settings.emoji_switch, escapeHtml)}
            ${toggleSetting("vizard_highlight_switch", "Highlight words", settings.highlight_switch, escapeHtml)}
            ${toggleSetting("vizard_auto_broll_switch", "Auto B-roll", settings.auto_broll_switch, escapeHtml)}
          </div>
        </div>
        ${saveSectionButton(escapeHtml)}
      `, escapeHtml)}
    </section>
  `;
}

function selectSetting(key, label, value, options, escapeHtml) {
  return `
    <div class="soft-box">
      <label>${escapeHtml(label)}</label>
      <select data-setting="${escapeHtml(key)}">
        ${options.map(([optionValue, optionLabel]) => `<option value="${optionValue}" ${value === optionValue ? "selected" : ""}>${escapeHtml(optionLabel)}</option>`).join("")}
      </select>
    </div>
  `;
}

function smallTextSetting(key, label, value, maxLength, escapeHtml) {
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
      <input inputmode="numeric" min="${min}" max="${max}" value="${safeValue}" data-setting="${key}" />
    </div>
  `;
}

function textAreaSetting(key, label, value, rows, escapeHtml) {
  return `
    <div class="soft-box">
      <label>${escapeHtml(label)}</label>
      <textarea data-setting="${escapeHtml(key)}" rows="${rows}">${escapeHtml(value)}</textarea>
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

function vizardSummaryChips(settings) {
  return [
    chip(ratioLabel(settings.ratio_of_clip || 1)),
    chip(lengthLabel(settings.prefer_length || [0])),
    chip(`до ${settings.max_clip_number || 10} клипов`),
  ];
}

function autoSwitchChips(settings) {
  const enabled = [
    settings.subtitle_switch && "subs",
    settings.headline_switch && "headline",
    settings.emoji_switch && "emoji",
    settings.highlight_switch && "highlight",
    settings.auto_broll_switch && "b-roll",
  ].filter(Boolean);
  return [chip(enabled.length ? enabled.join(", ") : "все выкл", enabled.length === 0)];
}

function ratioLabel(value) {
  const found = RATIO_OPTIONS.find(([option]) => option === String(value));
  return found ? found[1] : "9:16 вертикальный";
}

function lengthLabel(values) {
  const selected = new Set(values.map((item) => String(item)));
  return LENGTH_OPTIONS.filter(([option]) => selected.has(option)).map(([, label]) => label).join(", ") || "auto";
}
