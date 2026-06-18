export function renderVoiceSelector(state, escapeHtml) {
  const settings = state.settings;
  return `
    <div class="voice-compact">
      <label>Голос диктора</label>
      <div class="voice-row">
        <select data-voice-select>
          <option value="">${escapeHtml(settings.elevenlabs_voice_name || "Не выбран")}</option>
          ${state.voices.map((voice) => `
            <option
              value="${escapeHtml(voice.id)}"
              data-name="${escapeHtml(voice.name)}"
              ${voice.id === settings.elevenlabs_voice_id ? "selected" : ""}
            >${escapeHtml(voice.name)}</option>
          `).join("")}
        </select>
        <button data-action="load-voices">Обновить список</button>
      </div>
      <code>${escapeHtml(settings.elevenlabs_voice_id || "")}</code>
      ${state.voices.length ? "" : `<p>Список голосов загрузится автоматически при открытии настроек.</p>`}
    </div>
  `;
}

export function bindVoiceEvents(root, deps, renderSettingsPanel) {
  root.querySelectorAll("[data-action='load-voices']").forEach((button) => {
    button.addEventListener("click", () => loadVoices(deps, renderSettingsPanel).catch(deps.showError));
  });
  root.querySelectorAll("[data-voice-select]").forEach((select) => {
    select.addEventListener("change", () => selectVoice(deps, select, renderSettingsPanel).catch(deps.showError));
  });
}

async function loadVoices(deps, renderSettingsPanel) {
  deps.setStatus("Голоса");
  deps.state.voices = await deps.api("/api/settings/elevenlabs-voices");
  renderSettingsPanel(deps);
  deps.setStatus("Готово");
}

async function selectVoice(deps, select, renderSettingsPanel) {
  const option = select.selectedOptions[0];
  if (!option?.value) return;
  deps.setStatus("Сохраняю");
  deps.state.settings = await deps.api("/api/settings/elevenlabs-voice", {
    method: "POST",
    body: JSON.stringify({
      user_id: deps.state.userId,
      id: option.value,
      name: option.dataset.name || option.textContent || option.value,
    }),
  });
  renderSettingsPanel(deps);
  deps.setStatus("Сохранено");
}
