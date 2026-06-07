export function renderAvatarSelectors(state, escapeHtml, options = {}) {
  const settings = state.settings;
  const model = selectedModel(settings);
  const explicitModel = selectedModel(settings, { explicitOnly: true });
  const horizontal = findAvatar(state, settings.heygen_avatar_id);
  const vertical = findAvatar(state, settings.heygen_vertical_avatar_id);
  const visibleAvatars = visibleSelectedAvatars(options.target, horizontal, vertical);
  const hasMismatch = visibleAvatars.some((avatar) => !supportsModel(avatar, model));
  const usesPhotoAvatar = model === "avatar_iii" && visibleAvatars.some((avatar) => avatar?.avatar_type === "photo_avatar");
  if (options.mode === "model") {
    return `
      <div class="heygen-model-grid">
        ${modelButton("avatar_iii", "Avatar III", "$1/min 1080p", explicitModel, escapeHtml)}
        ${modelButton("avatar_iv", "Avatar IV", "TURAN ~$4/min", explicitModel, escapeHtml)}
        ${modelButton("avatar_v", "Avatar V", "TURAN ~$4/min", explicitModel, escapeHtml)}
      </div>
      <p>Модель общая для горизонтального и вертикального HeyGen avatar.</p>
    `;
  }
  return `
    <div class="heygen-model-grid">
      ${modelButton("avatar_iii", "Avatar III", "$1/min 1080p", explicitModel, escapeHtml)}
      ${modelButton("avatar_iv", "Avatar IV", "TURAN ~$4/min", explicitModel, escapeHtml)}
      ${modelButton("avatar_v", "Avatar V", "TURAN ~$4/min", explicitModel, escapeHtml)}
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
    <div class="avatar-gallery" data-avatar-autoload="true">${renderAvatarList(state, escapeHtml, options.target)}</div>
  `;
}

export function bindAvatarEvents(root, deps, renderSettingsPanel) {
  root.querySelectorAll("[data-avatar-autoload='true']").forEach(() => {
    if (!deps.state.avatars.length && !deps.state.avatarsLoading && !deps.state.avatarsLoadAttempted) {
      loadAvatars(deps, renderSettingsPanel).catch(deps.showError);
    }
  });
  root.querySelectorAll("[data-action='select-heygen-model']").forEach((button) => {
    button.addEventListener("click", () => selectModel(deps, button.dataset.model, renderSettingsPanel).catch(deps.showError));
  });
  root.querySelectorAll("[data-action='select-avatar']").forEach((button) => {
    button.addEventListener("click", () => selectAvatar(deps, button.dataset, renderSettingsPanel).catch(deps.showError));
  });
}

function selectedModel(settings, options = {}) {
  if (options.explicitOnly && !settings.heygen_model_selected) return "";
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

function renderAvatarList(state, escapeHtml, target) {
  if (state.avatarsLoading) {
    return `<div class="empty-box">Загружаю аватары HeyGen...</div>`;
  }
  if (!state.avatars.length) {
    return `<div class="empty-box">Список HeyGen avatars загрузится автоматически.</div>`;
  }
  const model = selectedModel(state.settings);
  const avatars = state.avatars.filter((avatar) => supportsModel(avatar, model));
  if (!avatars.length) {
    return `<div class="empty-box">Для ${escapeHtml(modelLabel(model))} нет подходящих аватаров.</div>`;
  }
  return avatars.map((avatar) => {
    const isHorizontal = avatar.id === state.settings.heygen_avatar_id;
    const isVertical = avatar.id === state.settings.heygen_vertical_avatar_id;
    return `
      <article class="avatar-tile ${isHorizontal || isVertical ? "active" : ""}">
        ${renderTilePreview(avatar, escapeHtml)}
        <div class="avatar-tile-info">
          <strong>${escapeHtml(avatar.name)}</strong>
          <small>${escapeHtml(avatarMeta(avatar))}</small>
        </div>
        <div class="avatar-tile-actions">${renderAvatarActions(avatar, { isHorizontal, isVertical, target, escapeHtml })}</div>
      </article>
    `;
  }).join("");
}

function renderAvatarActions(avatar, options) {
  const { isHorizontal, isVertical, target, escapeHtml } = options;
  if (target === "horizontal") return avatarActionButton(avatar, "horizontal", "YouTube", isHorizontal, "youtube", escapeHtml);
  if (target === "vertical") return avatarActionButton(avatar, "vertical", "Instagram", isVertical, "shorts", escapeHtml);
  return `
    ${avatarActionButton(avatar, "horizontal", "YouTube", isHorizontal, "youtube", escapeHtml)}
    ${avatarActionButton(avatar, "vertical", "Instagram", isVertical, "shorts", escapeHtml)}
  `;
}

function avatarActionButton(avatar, target, label, active, activeClass, escapeHtml) {
  return `
    <button
      class="${active ? `active ${activeClass}` : ""}"
      data-action="select-avatar"
      data-target="${target}"
      data-id="${escapeHtml(avatar.id)}"
      data-name="${escapeHtml(avatar.name)}"
      data-preview-image-url="${escapeHtml(avatar.preview_image_url || "")}"
      data-preview-video-url="${escapeHtml(avatar.preview_video_url || "")}"
    ><span>${label}</span></button>
  `;
}

function renderTilePreview(avatar, escapeHtml) {
  if (avatar.preview_video_url) {
    return `<video class="avatar-tile-media" src="${escapeHtml(avatar.preview_video_url)}" muted playsinline preload="metadata"></video>`;
  }
  if (avatar.preview_image_url) {
    return `<img class="avatar-tile-media" src="${escapeHtml(avatar.preview_image_url)}" alt="" />`;
  }
  return `<div class="avatar-tile-media avatar-placeholder"></div>`;
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

function modelLabel(model) {
  if (model === "avatar_iii") return "Avatar III";
  if (model === "avatar_v") return "Avatar V";
  return "Avatar IV";
}

function avatarMeta(avatar) {
  if (avatar.supported_engines?.length) {
    return `${avatar.avatar_type || "avatar"} · ${avatar.supported_engines.join(", ")}`;
  }
  return avatar.id;
}

function visibleSelectedAvatars(target, horizontal, vertical) {
  if (target === "horizontal") return [horizontal];
  if (target === "vertical") return [vertical];
  return [horizontal, vertical];
}

function avatarHint(target) {
  if (target === "horizontal") return "Выберите avatar только для горизонтального YouTube формата.";
  if (target === "vertical") return "Выберите avatar только для вертикального Instagram/Reels.";
  return "Выберите отдельный avatar для каждого выхода.";
}

async function loadAvatars(deps, renderSettingsPanel) {
  const { state, api, setStatus } = deps;
  if (state.avatarsLoading) return;
  state.avatarsLoadAttempted = true;
  state.avatarsLoading = true;
  setStatus("Аватары");
  renderSettingsPanel(deps);
  try {
    state.avatars = await api("/api/settings/heygen-avatars");
    setStatus("Готово");
  } finally {
    state.avatarsLoading = false;
    renderSettingsPanel(deps);
  }
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
      preview_image_url: dataset.previewImageUrl || "",
      preview_video_url: dataset.previewVideoUrl || "",
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
