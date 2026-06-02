const evenPositive = (value, fallback) => {
  const rounded = Math.max(2, Math.round(Number(value) || fallback));
  return rounded % 2 === 0 ? rounded : rounded + 1;
};

const clampScale = (value) => Math.min(1, Math.max(0.35, Number(value) || 1));

export const createOverlayRenderSizing = ({renderLayout, envNumber}) => {
  const outputWidth = renderLayout.width;
  const outputHeight = renderLayout.height;
  const renderScale = renderLayout.isVerticalHeygen
    ? clampScale(envNumber('HYPERFRAMES_VERTICAL_OVERLAY_SCALE', 0.5))
    : 1;
  const usesScaledOverlay = renderLayout.isVerticalHeygen && renderScale < 0.999;

  return {
    outputWidth,
    outputHeight,
    compositionWidth: usesScaledOverlay ? evenPositive(outputWidth * renderScale, outputWidth) : outputWidth,
    compositionHeight: usesScaledOverlay ? evenPositive(outputHeight * renderScale, outputHeight) : outputHeight,
    renderScale,
    usesScaledOverlay,
  };
};

export const overlayScaleCss = (sizing) => {
  if (!sizing.usesScaledOverlay) return '';
  return `
      .overlay-design {
        position: absolute;
        left: 0;
        top: 0;
        width: ${sizing.outputWidth}px;
        height: ${sizing.outputHeight}px;
        transform: scale(${sizing.renderScale});
        transform-origin: top left;
      }`;
};

export const wrapOverlayClips = (overlayClips, sizing) => {
  if (!sizing.usesScaledOverlay) return overlayClips;
  return `<div class="overlay-design">
${overlayClips}
      </div>`;
};

export const createCompositeFilter = (sizing) => {
  const baseFilter =
    `[0:v]scale=${sizing.outputWidth}:${sizing.outputHeight}:force_original_aspect_ratio=increase,` +
    `crop=${sizing.outputWidth}:${sizing.outputHeight},` +
    'scale=ceil(iw*1.01/2)*2:ceil(ih*1.01/2)*2,' +
    `crop=${sizing.outputWidth}:${sizing.outputHeight}[base]`;
  const overlayInput = sizing.usesScaledOverlay
    ? `[1:v]scale=${sizing.outputWidth}:${sizing.outputHeight}:flags=lanczos[overlay];[base][overlay]`
    : '[base][1:v]';
  return `${baseFilter};${overlayInput}overlay=0:0:eof_action=pass:format=auto[v]`;
};
