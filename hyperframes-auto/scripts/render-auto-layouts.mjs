export const createRenderLayout = ({layout, envFlag}) => {
  const isYoutube = layout === 'horizontal_youtube';
  const isVerticalHeygen = layout === 'vertical_heygen';

  return {
    id: layout,
    width: isVerticalHeygen ? 1080 : 1920,
    height: isVerticalHeygen ? 1920 : 1080,
    generatedCompositionName: isYoutube
      ? 'horizontal-youtube.generated.html'
      : isVerticalHeygen
        ? 'vertical-heygen.generated.html'
        : 'horizontal-simple.generated.html',
    isYoutube,
    isVerticalHeygen,
    isSmartDirector: isYoutube || isVerticalHeygen,
    compositeSourceVideo: isYoutube
      ? envFlag('HYPERFRAMES_YOUTUBE_COMPOSITE_SOURCE_VIDEO', true)
      : isVerticalHeygen,
  };
};

