export function renderAvatarSelectors(state, escapeHtml) {
  const settings = state.settings;
  return `
    <div class="avatar-current-grid">
      ${currentAvatarCard(
        "YouTube / горизонтальный",
        settings.heygen_avatar_name,
        settings.heygen_avatar_id,
        "dark",
        escapeHtml,
      )}
      ${currentAvatarCard(
        "Shorts/Reels / вертикальный",
        settings.heygen_vertical_avatar_name,
        settings.heygen_vertical_avatar_id,
        "blue",
        escapeHtml,
      )}
    </div>
    <div class="box-head avatar-load-row">
      <p>Выберите отдельный avatar для каждого формата, как в Turan.</p>
      <button data-action="load-avatars">Загрузить аватары</button>
    </div>
    <div class="asset-list">${renderAvatarList(state, escapeHtml)}</div>
  `;
}

export function bindAvatarEvents(root, deps, renderSettingsPanel) {
  root.querySelectorAll("[data-action='load-avatars']").forEach((button) => {
    button.addEventListener("click", () => loadAvatars(deps, renderSettingsPanel).catch(deps.showError));
  });
  root.querySelectorAll("[data-action='select-avatar']").forEach((button) => {
    button.addEventListener("click", () => selectAvatar(deps, button.dataset, renderSettingsPanel).catch(deps.showError));
  });
}

function currentAvatarCard(label, name, id, tone, escapeHtml) {
  return `
    <div class="avatar-current ${tone}">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(name || "Не выбран")}</strong>
      <code>${escapeHtml(id || "")}</code>
    </div>
  `;
}

function renderAvatarList(state, escapeHtml) {
  if (!state.avatars.length) {
    return `<div class="empty-box">Нажмите “Загрузить аватары”, чтобы получить список HeyGen.</div>`;
  }
  return state.avatars.map((avatar) => {
    const isHorizontal = avatar.id === state.settings.heygen_avatar_id;
    const isVertical = avatar.id === state.settings.heygen_vertical_avatar_id;
    return `
      <article class="asset-card avatar-card ${isHorizontal || isVertical ? "active" : ""}">
        ${avatar.preview_image_url ? `<img src="${escapeHtml(avatar.preview_image_url)}" alt="" />` : `<div class="avatar-placeholder"></div>`}
        <div>
          <strong>${escapeHtml(avatar.name)}</strong>
          <small>${escapeHtml(avatar.id)}</small>
        </div>
        <div class="avatar-target-row">
          <button
            class="${isHorizontal ? "active dark" : ""}"
            data-action="select-avatar"
            data-target="horizontal"
            data-id="${escapeHtml(avatar.id)}"
            data-name="${escapeHtml(avatar.name)}"
          >YouTube</button>
          <button
            class="${isVertical ? "active" : ""}"
            data-action="select-avatar"
            data-target="vertical"
            data-id="${escapeHtml(avatar.id)}"
            data-name="${escapeHtml(avatar.name)}"
          >Shorts</button>
        </div>
      </article>
    `;
  }).join("");
}

async function loadAvatars(deps, renderSettingsPanel) {
  const { state, api, setStatus } = deps;
  setStatus("Аватары");
  state.avatars = await api("/api/settings/heygen-avatars");
  renderSettingsPanel(deps);
  setStatus("Готово");
}

async function selectAvatar(deps, dataset, renderSettingsPanel) {
  deps.setStatus("Сохраняю");
  deps.state.settings = await deps.api("/api/settings/heygen-avatar", {
    method: "POST",
    body: JSON.stringify({
      user_id: deps.state.userId,
      id: dataset.id,
      name: dataset.name,
      target: dataset.target || "both",
    }),
  });
  renderSettingsPanel(deps);
  deps.setStatus("Сохранено");
}
