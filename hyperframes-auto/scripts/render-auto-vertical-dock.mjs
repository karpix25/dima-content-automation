const compact = (value) => String(value || '').replace(/\s+/g, ' ').trim();

const escapeAttr = (value, escapeHtml) => escapeHtml(compact(value));

const isPlaceholderMetric = (value) => ['check', 'ready', 'n/a', 'na'].includes(compact(value).toLowerCase());

const metricDisplayValue = (value) => {
  const clean = compact(value);
  return clean && !isPlaceholderMetric(clean) ? clean : '';
};

const pickTerms = (scene) => {
  const values = [
    ...(Array.isArray(scene.visualElements) ? scene.visualElements : []),
    ...(Array.isArray(scene.anchorWords) ? scene.anchorWords : []),
    ...(Array.isArray(scene.facts) ? scene.facts.map((fact) => fact?.text || fact) : []),
    scene.keyword,
    metricDisplayValue(scene.metricValue) ? scene.metricLabel : '',
  ];
  const seen = new Set();
  return values
    .map(compact)
    .filter(Boolean)
    .filter((value) => {
      const key = value.toLowerCase();
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .slice(0, 3);
};

const barValues = (scene) => {
  if (Array.isArray(scene.bars) && scene.bars.length >= 2) {
    return scene.bars
      .map((bar) => ({
        label: compact(bar?.label || bar?.name || ''),
        value: Number(bar?.value ?? bar?.score ?? bar?.amount),
      }))
      .filter((bar) => bar.label && Number.isFinite(bar.value) && bar.value > 0)
      .slice(0, 3);
  }

  const metricValue = metricDisplayValue(scene.metricValue);
  const multiplier = Number(String(metricValue).match(/(\d+(?:[.,]\d+)?)\s*x/i)?.[1]?.replace(',', '.'));
  if (Number.isFinite(multiplier) && multiplier > 1) {
    return [
      {label: 'base', value: 1},
      {label: compact(scene.metricLabel) || 'target', value: multiplier},
    ];
  }

  return [];
};

const dockGraphicMarkup = (scene, escapeHtml) => {
  const bars = barValues(scene);
  if (bars.length >= 2) {
    const max = Math.max(...bars.map((bar) => bar.value), 1);
    return `
          <div class="dock-bars">
            ${bars
              .map((bar) => {
                const fill = Math.max(8, Math.min(100, (bar.value / max) * 100));
                const valueText = bar.value >= 10 ? Math.round(bar.value) : Number(bar.value.toFixed(1));
                return `<div class="dock-bar-row"><span>${escapeHtml(bar.label)}</span><div class="dock-bar-track"><div class="dock-bar-fill" style="--fill:${fill.toFixed(1)}%;"></div></div><strong>${escapeHtml(valueText)}</strong></div>`;
              })
              .join('')}
          </div>`;
  }

  const steps = Array.isArray(scene.steps) ? scene.steps.map(compact).filter(Boolean).slice(0, 3) : [];
  if (steps.length >= 2) {
    return `
          <div class="dock-flow">
            ${steps
              .map((step, index) => `${index ? '<div class="dock-arrow">→</div>' : ''}<div class="dock-flow-box">${escapeHtml(step)}</div>`)
              .join('')}
          </div>`;
  }

  const metricValue = metricDisplayValue(scene.metricValue);
  const metricLabel = metricValue ? compact(scene.metricLabel) : '';
  if (metricValue) {
    return `
          <div class="dock-metric">
            ${metricValue ? `<strong>${escapeHtml(metricValue)}</strong>` : ''}
            ${metricLabel ? `<span>${escapeHtml(metricLabel)}</span>` : ''}
          </div>`;
  }

  const terms = pickTerms(scene);
  if (terms.length) {
    return `
          <div class="dock-pills">
            ${terms.map((term) => `<span>${escapeHtml(term)}</span>`).join('')}
          </div>`;
  }

  return '<div class="dock-signal"><span></span><span></span><span></span></div>';
};

export const verticalDockClip = ({scene, index, title, subtitle, duration, escapeHtml}) => `
      <div
        id="director-${index}"
        class="clip director-card dock-card"
        data-start="${scene.start.toFixed(3)}"
        data-duration="${duration.toFixed(3)}"
        data-track-index="1"
      >
        <div class="dock-copy">
          <div class="director-kicker">${escapeAttr(scene.directorCue || scene.cutawayRole || scene.blockName || 'важный момент', escapeHtml)}</div>
          <h2>${escapeHtml(title)}</h2>
          ${subtitle ? `<p>${escapeHtml(subtitle)}</p>` : ''}
        </div>
        <div class="dock-graphic">
          ${dockGraphicMarkup(scene, escapeHtml)}
        </div>
      </div>`;

export const verticalDockTimelineTween = ({index, scene, duration}) => {
  const start = scene.start;
  const fadeOutAt = Math.max(start + 0.6, start + duration - 0.28);
  const barsTween = barValues(scene).length >= 2
    ? `tl.fromTo("#director-${index} .dock-bar-fill", { width: "0%" }, { width: function (_i, el) { return getComputedStyle(el).getPropertyValue("--fill"); }, duration: 0.58, stagger: 0.08, ease: "power2.out" }, ${(start + 0.32).toFixed(3)});`
    : '';
  return `
      tl.set("#director-${index}", { visibility: "visible" }, ${start.toFixed(3)});
      tl.fromTo("#director-${index}", { opacity: 0, y: 22 }, { opacity: 1, y: 0, duration: 0.28, ease: "power2.out" }, ${start.toFixed(3)});
      tl.from("#director-${index} h2", { opacity: 0, y: 18, duration: 0.32, ease: "power3.out" }, ${(start + 0.12).toFixed(3)});
      tl.from("#director-${index} .dock-graphic > *", { opacity: 0, y: 12, duration: 0.28, ease: "power2.out" }, ${(start + 0.28).toFixed(3)});
      ${barsTween}
      tl.to("#director-${index}", { opacity: 0, y: -12, duration: 0.22, ease: "power2.in" }, ${fadeOutAt.toFixed(3)});`;
};

export const VERTICAL_DOCK_CSS = `
      body.layout-vertical-heygen .director-card.dock-card {
        left: 48px;
        right: auto;
        top: 1210px;
        width: 984px;
        height: 320px;
        padding: 28px 30px;
        border-radius: 30px;
        background: rgba(247, 248, 245, 0.96);
        border: 0;
        box-shadow: 0 22px 64px rgba(0, 0, 0, 0.36);
        color: #0b1018;
        display: grid;
        grid-template-columns: minmax(0, 1fr) 410px;
        gap: 28px;
        align-items: center;
        z-index: 4;
      }
      body.layout-vertical-heygen .dock-card .dock-copy {
        min-width: 0;
      }
      body.layout-vertical-heygen .dock-card .director-kicker {
        margin-bottom: 12px;
        color: #ef4444;
        font-size: 18px;
        line-height: 1;
        font-weight: 950;
        letter-spacing: 0;
        text-transform: uppercase;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      body.layout-vertical-heygen .dock-card h2 {
        max-width: 100%;
        font-size: 42px;
        line-height: 1.02;
        font-weight: 950;
        letter-spacing: 0;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
      }
      body.layout-vertical-heygen .dock-card p {
        max-width: 100%;
        margin-top: 14px;
        color: #344054;
        font-size: 24px;
        line-height: 1.18;
        font-weight: 780;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
      }
      body.layout-vertical-heygen .dock-graphic {
        min-width: 0;
      }
      body.layout-vertical-heygen .dock-bars {
        display: grid;
        gap: 14px;
      }
      body.layout-vertical-heygen .dock-bar-row {
        display: grid;
        grid-template-columns: 72px 1fr 62px;
        align-items: center;
        gap: 12px;
        font-size: 21px;
        font-weight: 920;
      }
      body.layout-vertical-heygen .dock-bar-track {
        height: 24px;
        border-radius: 999px;
        background: rgba(16, 24, 40, 0.1);
        overflow: hidden;
      }
      body.layout-vertical-heygen .dock-bar-fill {
        width: var(--fill);
        height: 100%;
        border-radius: 999px;
        background: linear-gradient(90deg, #ef4444, #f7c948);
      }
      body.layout-vertical-heygen .dock-flow {
        display: grid;
        grid-template-columns: 1fr 30px 1fr 30px 1fr;
        align-items: center;
        gap: 8px;
      }
      body.layout-vertical-heygen .dock-flow-box,
      body.layout-vertical-heygen .dock-metric {
        min-height: 80px;
        border-radius: 18px;
        padding: 14px 10px;
        background: rgba(16, 24, 40, 0.07);
        display: grid;
        place-items: center;
        text-align: center;
        font-size: 19px;
        line-height: 1.04;
        font-weight: 930;
      }
      body.layout-vertical-heygen .dock-arrow {
        color: #ef4444;
        text-align: center;
        font-size: 28px;
        font-weight: 950;
      }
      body.layout-vertical-heygen .dock-metric strong {
        display: block;
        font-size: 48px;
        line-height: 1;
        font-weight: 950;
      }
      body.layout-vertical-heygen .dock-metric span {
        display: block;
        margin-top: 8px;
        color: #667085;
        font-size: 18px;
        font-weight: 850;
      }
      body.layout-vertical-heygen .dock-pills {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
      }
      body.layout-vertical-heygen .dock-pills span {
        min-height: 42px;
        padding: 9px 15px;
        border-radius: 999px;
        background: rgba(239, 68, 68, 0.1);
        color: #b42318;
        font-size: 18px;
        font-weight: 900;
      }
      body.layout-vertical-heygen .dock-signal {
        display: grid;
        gap: 14px;
      }
      body.layout-vertical-heygen .dock-signal span {
        height: 24px;
        border-radius: 999px;
        background: linear-gradient(90deg, rgba(239, 68, 68, 0.28), rgba(247, 201, 72, 0.24));
      }
`;
