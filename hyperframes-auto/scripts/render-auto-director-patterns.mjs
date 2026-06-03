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
  if (!metricValue && !metricLabel) return '';
  return `
          <div class="director-metric">
            ${metricValue ? `<strong>${escapeHtml(metricValue)}</strong>` : ''}
            ${metricLabel ? `<span>${escapeHtml(metricLabel)}</span>` : ''}
          </div>`;
};

export const directorPatternTweens = ({index, scene, start, duration}) => {
  const metricSelector = `#director-${index} .director-metric`;
  const pattern = safePattern(scene);
  const metricScale = pattern === 'demand_drop' ? 1.15 : 1.08;
  return `
      tl.fromTo("${metricSelector}", { opacity: 0, y: 16, scale: 0.92 }, { opacity: 1, y: 0, scale: ${metricScale}, duration: 0.34, ease: "back.out(1.7)" }, ${(start + 0.32).toFixed(3)});
      tl.to("${metricSelector}", { scale: 1, duration: 0.22, ease: "power2.out" }, ${(start + 0.72).toFixed(3)});`;
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
