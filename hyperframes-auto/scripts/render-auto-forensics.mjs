const compact = (value) => String(value || '').replace(/\s+/g, ' ').trim();

const pickTerms = (scene, visualElements) => {
  const source = [
    ...(Array.isArray(visualElements) ? visualElements : []),
    scene.keyword,
    scene.title,
    scene.chapterTitle,
    scene.insight,
  ]
    .map(compact)
    .filter(Boolean)
    .join(' ');
  const words = source.match(/[\p{L}\p{N}$+.-]{3,}/gu) || [];
  return [...new Set(words.map((word) => word.replace(/[.,;:!?]+$/g, '')))].slice(0, 5);
};

export const forensicsVisualMarkup = ({scene, index, title, subtitle, visualElements, escapeHtml}) => {
  const terms = pickTerms(scene, visualElements);
  const sku = `SKU-${String(index + 1).padStart(2, '0')}`;
  const headline = compact(title || scene.title || 'Catalog audit');
  const note = compact(subtitle || scene.insight || scene.cta || 'Hidden marketplace issue found');
  const primary = terms[0] || 'FBA';
  const secondary = terms[1] || 'tier';
  const tertiary = terms[2] || 'margin';

  return `<div class="forensics-board" aria-hidden="true">
          <div class="forensics-grid"></div>
          <div class="forensics-thread thread-a"></div>
          <div class="forensics-thread thread-b"></div>
          <div class="evidence-card listing-card">
            <div class="evidence-thumb"></div>
            <div class="listing-lines">
              <span></span><span></span><span></span>
            </div>
            <div class="listing-price">+$1.12 / unit</div>
          </div>
          <div class="evidence-card document-card">
            <div class="doc-label">${escapeHtml(sku)}</div>
            <div class="doc-line strong"></div>
            <div class="doc-line"></div>
            <div class="doc-line short"></div>
            <div class="audit-stamp">CHECK</div>
          </div>
          <div class="evidence-card note-card">
            <div class="note-title">${escapeHtml(primary)}</div>
            <div class="note-copy">${escapeHtml(note)}</div>
          </div>
          <div class="red-circle circle-one"></div>
          <div class="red-circle circle-two"></div>
          <div class="pin pin-a"></div>
          <div class="pin pin-b"></div>
          <div class="tag tag-main">${escapeHtml(tertiary)}</div>
          <div class="tag tag-side">${escapeHtml(secondary)}</div>
          <div class="forensics-caption">${escapeHtml(headline)}</div>
        </div>`;
};

export const FORENSICS_CSS = `
      body.layout-vertical-heygen .director-card {
        background:
          linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(241, 245, 249, 0.96)),
          #f8fafc;
        border-color: rgba(15, 23, 42, 0.18);
      }
      body.layout-vertical-heygen .director-copy::before {
        background: #d13f2f;
      }
      body.layout-vertical-heygen .director-visual {
        background: #f4f0e8;
        border: 2px solid rgba(15, 23, 42, 0.18);
        box-shadow:
          inset 0 0 0 1px rgba(255, 255, 255, 0.68),
          0 18px 46px rgba(15, 23, 42, 0.16);
      }
      .forensics-board {
        position: relative;
        width: 100%;
        height: 100%;
        overflow: hidden;
        background:
          linear-gradient(135deg, rgba(255, 255, 255, 0.88), rgba(238, 231, 219, 0.92)),
          #f4f0e8;
      }
      .forensics-grid {
        position: absolute;
        inset: 0;
        background:
          linear-gradient(90deg, rgba(15, 23, 42, 0.065) 1px, transparent 1px),
          linear-gradient(0deg, rgba(15, 23, 42, 0.055) 1px, transparent 1px);
        background-size: 44px 44px;
      }
      .evidence-card {
        position: absolute;
        border-radius: 7px;
        background: rgba(255, 255, 255, 0.92);
        border: 1px solid rgba(15, 23, 42, 0.16);
        box-shadow: 0 18px 40px rgba(15, 23, 42, 0.16);
      }
      .listing-card {
        left: 42px;
        top: 52px;
        width: 46%;
        height: 42%;
        padding: 20px;
      }
      .evidence-thumb {
        width: 48%;
        height: 62%;
        border-radius: 6px;
        background:
          linear-gradient(135deg, rgba(209, 63, 47, 0.18), rgba(245, 158, 11, 0.18)),
          #e2e8f0;
      }
      .listing-lines {
        position: absolute;
        left: 55%;
        top: 34px;
        right: 20px;
        display: grid;
        gap: 12px;
      }
      .listing-lines span {
        display: block;
        height: 17px;
        border-radius: 999px;
        background: rgba(15, 23, 42, 0.22);
      }
      .listing-lines span:nth-child(2) {
        width: 78%;
      }
      .listing-lines span:nth-child(3) {
        width: 56%;
        background: rgba(209, 63, 47, 0.32);
      }
      .listing-price {
        position: absolute;
        left: 20px;
        bottom: 18px;
        color: #b42318;
        font-size: 28px;
        line-height: 1;
        font-weight: 900;
      }
      .document-card {
        right: 44px;
        top: 108px;
        width: 42%;
        height: 34%;
        padding: 22px;
        transform: rotate(3deg);
      }
      .doc-label {
        color: #0f172a;
        font-size: 24px;
        font-weight: 900;
        letter-spacing: 0;
      }
      .doc-line {
        height: 14px;
        margin-top: 18px;
        border-radius: 999px;
        background: rgba(15, 23, 42, 0.18);
      }
      .doc-line.strong {
        width: 82%;
        background: rgba(15, 23, 42, 0.32);
      }
      .doc-line.short {
        width: 54%;
      }
      .audit-stamp {
        position: absolute;
        right: 18px;
        bottom: 18px;
        padding: 8px 12px;
        border: 3px solid #d13f2f;
        color: #d13f2f;
        font-size: 21px;
        font-weight: 950;
        transform: rotate(-7deg);
      }
      .note-card {
        left: 98px;
        right: 72px;
        bottom: 78px;
        min-height: 30%;
        padding: 26px 30px;
        background: rgba(255, 251, 235, 0.96);
        transform: rotate(-1.6deg);
      }
      .note-title {
        color: #0f172a;
        font-size: 42px;
        line-height: 1.02;
        font-weight: 950;
        letter-spacing: 0;
      }
      .note-copy {
        margin-top: 16px;
        color: #475569;
        font-size: 25px;
        line-height: 1.18;
        font-weight: 800;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
      }
      .red-circle {
        position: absolute;
        border: 6px solid rgba(209, 63, 47, 0.82);
        border-radius: 999px;
        transform: rotate(-12deg);
      }
      .circle-one {
        left: 318px;
        top: 182px;
        width: 176px;
        height: 88px;
      }
      .circle-two {
        right: 112px;
        top: 288px;
        width: 150px;
        height: 72px;
      }
      .forensics-thread {
        position: absolute;
        height: 4px;
        background: rgba(209, 63, 47, 0.62);
        transform-origin: left center;
      }
      .thread-a {
        left: 392px;
        top: 330px;
        width: 260px;
        transform: rotate(19deg);
      }
      .thread-b {
        left: 512px;
        top: 604px;
        width: 210px;
        transform: rotate(-24deg);
      }
      .pin {
        position: absolute;
        width: 22px;
        height: 22px;
        border-radius: 999px;
        background: #d13f2f;
        box-shadow: 0 0 0 6px rgba(209, 63, 47, 0.16);
      }
      .pin-a {
        left: 382px;
        top: 320px;
      }
      .pin-b {
        right: 238px;
        top: 414px;
      }
      .tag {
        position: absolute;
        padding: 9px 13px;
        border-radius: 4px;
        background: #0f172a;
        color: #fff;
        font-size: 23px;
        line-height: 1;
        font-weight: 900;
        box-shadow: 0 12px 24px rgba(15, 23, 42, 0.22);
      }
      .tag-main {
        right: 58px;
        bottom: 312px;
      }
      .tag-side {
        left: 54px;
        bottom: 306px;
        background: #d97706;
      }
      .forensics-caption {
        position: absolute;
        left: 34px;
        right: 34px;
        bottom: 24px;
        color: rgba(15, 23, 42, 0.72);
        font-size: 24px;
        line-height: 1.1;
        font-weight: 850;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
`;

