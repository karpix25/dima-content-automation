export function renderAvatarSelectors(state, escapeHtml) {
  const settings = state.settings;
  const model = selectedModel(settings);
  const horizontal = findAvatar(state, settings.heygen_avatar_id);
  const vertical = findAvatar(state, settings.heygen_vertical_avatar_id);
  const hasMismatch = !supportsModel(horizontal, model) || !supportsModel(vertical, model);
  const usesPhotoAvatar = model === "avatar_iii" && [horizontal, vertical].some((avatar) => avatar?.avatar_type === "photo_avatar");
  return `
    <div class="heygen-model-grid">
      ${modelButton("avatar_iii", "Avatar III", "$1/min 1080p", model, escapeHtml)}
      ${modelButton("avatar_iv", "Avatar IV", "TURAN ~$4/min", model, escapeHtml)}
      ${modelButton("avatar_v", "Avatar V", "TURAN ~$4/min", model, escapeHtml)}
    </div>
    ${hasMismatch ? `
      <div class="model-warning amber">
        Выбранный avatar поддерживает Avatar IV/V, а сверху включен Avatar III. В таком режиме HeyGen может дать только слабый lip-sync без движения рук.
      </div>
    ` : ""}
    ${usesPhotoAvatar ? `
      <div class="model-warning blue">
        Photo Avatar будет отправлен через Avatar III. Motion prompt применяется только для Avatar IV.
      </div>
    ` : ""}
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
  root.querySelectorAll("[data-action='select-heygen-model']").forEach((button) => {
    button.addEventListener("click", () => selectModel(deps, button.dataset.model, renderSettingsPanel).catch(deps.showError));
  });
  root.querySelectorAll("[data-action='select-avatar']").forEach((button) => {
    button.addEventListener("click", () => selectAvatar(deps, button.dataset, renderSettingsPanel).catch(deps.showError));
  });
}

function selectedModel(settings) {
  if (settings.heygen_video_api_version === "v2") return "avatar_iii";
  return settings.heygen_avatar_engine === "avatar_v" ? "avatar_v" : "avatar_iv";
}

function modelButton(id, label, hint, selected, escapeHtml) {
  return `
    <button
      type="button"
      class="${selected === id ? "active" : ""}"
      data-action="select-heygen-model"
      data-model="${escapeHtml(id)}"
    >
      <span>${escapeHtml(label)}</span>
      <small>${escapeHtml(hint)}</small>
    </button>
  `;
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
  const model = selectedModel(state.settings);
  return state.avatars.map((avatar) => {
    const isHorizontal = avatar.id === state.settings.heygen_avatar_id;
    const isVertical = avatar.id === state.settings.heygen_vertical_avatar_id;
    const supported = supportsModel(avatar, model);
    return `
      <article class="asset-card avatar-card ${isHorizontal || isVertical ? "active" : ""} ${supported ? "" : "disabled"}">
        ${avatar.preview_image_url ? `<img src="${escapeHtml(avatar.preview_image_url)}" alt="" />` : `<div class="avatar-placeholder"></div>`}
        <div>
          <strong>${escapeHtml(avatar.name)}</strong>
          <small>${escapeHtml(avatarMeta(avatar))}</small>
        </div>
        ${supported ? "" : `<div class="avatar-model-lock">Нужен Avatar IV/V</div>`}
        <div class="avatar-target-row">
          <button
            class="${isHorizontal ? "active dark" : ""}"
            ${supported ? "" : "disabled"}
            data-action="select-avatar"
            data-target="horizontal"
            data-id="${escapeHtml(avatar.id)}"
            data-name="${escapeHtml(avatar.name)}"
          >YouTube</button>
          <button
            class="${isVertical ? "active" : ""}"
            ${supported ? "" : "disabled"}
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

function findAvatar(state, id) {
  return state.avatars.find((avatar) => avatar.id === id);
}

function supportsModel(avatar, model) {
  if (!avatar) return true;
  const engines = (avatar.supported_engines || []).map((engine) => String(engine).trim().toLowerCase()).filter(Boolean);
  if (model === "avatar_iii" && avatar.avatar_type === "photo_avatar" && engines.includes("avatar_iv")) return true;
  if (!engines.length) return true;
  if (model === "avatar_iii") return engines.some((engine) => ["avatar_iii", "avatar_3", "avatar3", "v2"].includes(engine));
  return engines.includes(model);
}

function avatarMeta(avatar) {
  if (avatar.supported_engines?.length) {
    return `${avatar.avatar_type || "avatar"} · ${avatar.supported_engines.join(", ")}`;
  }
  return avatar.id;
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

async function selectModel(deps, model, renderSettingsPanel) {
  deps.setStatus("Сохраняю");
  deps.state.settings = await deps.api("/api/settings/heygen-model", {
    method: "POST",
    body: JSON.stringify({ user_id: deps.state.userId, model }),
  });
  renderSettingsPanel(deps);
  deps.setStatus("Сохранено");
}
