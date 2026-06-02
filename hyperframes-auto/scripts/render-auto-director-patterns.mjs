const compact = (value) => String(value || '').replace(/\s+/g, ' ').trim();

const safePattern = (scene) =>
  compact(scene.motionPattern || scene.template || 'audit_point')
    .toLowerCase()
    .replace(/[^a-z0-9_-]+/g, '-')
    .replace(/^-+|-+$/g, '') || 'audit-point';

export const directorPatternClass = (scene) => `pattern-${safePattern(scene)}`;

export const directorPatternMarkup = (scene, escapeHtml) => {
  const metricValue = compact(scene.metricValue);
  const metricLabel = compact(scene.metricLabel);
  const evidenceLabel = compact(scene.evidenceLabel);
  if (!metricValue && !metricLabel && !evidenceLabel) return '';
  return `
          <div class="director-metric">
            ${metricValue ? `<strong>${escapeHtml(metricValue)}</strong>` : ''}
            ${metricLabel ? `<span>${escapeHtml(metricLabel)}</span>` : ''}
          </div>
          ${evidenceLabel ? `<div class="director-evidence">${escapeHtml(evidenceLabel)}</div>` : ''}
          <div class="director-rail"><span></span><span></span><span></span></div>`;
};

export const directorPatternTweens = ({index, scene, start, duration}) => {
  const metricSelector = `#director-${index} .director-metric`;
  const railSelector = `#director-${index} .director-rail span`;
  const evidenceSelector = `#director-${index} .director-evidence`;
  const pattern = safePattern(scene);
  const metricScale = pattern === 'demand_drop' ? 1.15 : 1.08;
  const railDelay = pattern === 'velocity_hold' ? 0.42 : 0.22;
  return `
      tl.fromTo("${metricSelector}", { opacity: 0, y: 16, scale: 0.92 }, { opacity: 1, y: 0, scale: ${metricScale}, duration: 0.34, ease: "back.out(1.7)" }, ${(start + 0.32).toFixed(3)});
      tl.to("${metricSelector}", { scale: 1, duration: 0.22, ease: "power2.out" }, ${(start + 0.72).toFixed(3)});
      tl.fromTo("${railSelector}", { scaleX: 0, transformOrigin: "left center" }, { scaleX: 1, duration: 0.42, stagger: 0.09, ease: "power4.out" }, ${(start + railDelay).toFixed(3)});
      tl.fromTo("${evidenceSelector}", { opacity: 0, x: -12 }, { opacity: 1, x: 0, duration: 0.3, ease: "power3.out" }, ${(start + Math.min(duration * 0.38, 1.35)).toFixed(3)});`;
};

export const DIRECTOR_PATTERN_CSS = `
      body.layout-vertical-heygen .director-metric {
        position: absolute;
        right: 18px;
        top: 18px;
        min-width: 148px;
        padding: 12px 14px;
        border-radius: 5px;
        background: rgba(255, 255, 255, 0.92);
        border: 1px solid rgba(15, 23, 42, 0.16);
        box-shadow: 0 16px 36px rgba(15, 23, 42, 0.16);
        z-index: 4;
        color: #0f172a;
        text-align: right;
      }
      body.layout-vertical-heygen .director-metric strong {
        display: block;
        font-size: 35px;
        line-height: 0.95;
        font-weight: 950;
        letter-spacing: 0;
      }
      body.layout-vertical-heygen .director-metric span {
        display: block;
        margin-top: 5px;
        color: #475569;
        font-size: 15px;
        line-height: 1;
        font-weight: 850;
        text-transform: uppercase;
      }
      body.layout-vertical-heygen .director-evidence {
        position: absolute;
        left: 18px;
        right: 18px;
        bottom: 18px;
        padding: 11px 13px;
        border-radius: 5px;
        background: rgba(15, 23, 42, 0.86);
        color: #fff;
        font-size: 22px;
        line-height: 1.05;
        font-weight: 900;
        z-index: 4;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      body.layout-vertical-heygen .director-rail {
        position: absolute;
        left: 24px;
        right: 24px;
        bottom: 76px;
        display: grid;
        gap: 8px;
        z-index: 4;
      }
      body.layout-vertical-heygen .director-rail span {
        display: block;
        height: 8px;
        border-radius: 999px;
        background: rgba(209, 63, 47, 0.72);
      }
      body.layout-vertical-heygen .director-card.pattern-demand_drop .director-metric strong {
        color: #b42318;
      }
      body.layout-vertical-heygen .director-card.pattern-velocity_hold .director-metric strong {
        color: #15803d;
      }
      body.layout-vertical-heygen .director-card.pattern-profit_proof .director-metric strong,
      body.layout-vertical-heygen .director-card.pattern-price_lever .director-metric strong {
        color: #b45309;
      }
`;
