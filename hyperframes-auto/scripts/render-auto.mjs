#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {createRenderLayout} from './render-auto-layouts.mjs';
import {
  createCompositeFilter,
  createOverlayRenderSizing,
  overlayScaleCss,
  wrapOverlayClips,
} from './render-auto-overlay-scale.mjs';
import {createHyperframesRuntime} from './render-auto-hyperframes-runtime.mjs';
import {
  DIRECTOR_PATTERN_CSS,
  directorPatternClass,
  directorPatternMarkup,
  directorPatternTweens,
} from './render-auto-director-patterns.mjs';
import {
  VERTICAL_DOCK_CSS,
  verticalDockClip,
  verticalDockTimelineTween,
} from './render-auto-vertical-dock.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '..');
const argv = process.argv.slice(2);

const getArgValue = (name, fallback) => {
  const index = argv.indexOf(`--${name}`);
  if (index === -1) return fallback;
  const next = argv[index + 1];
  if (!next || next.startsWith('--')) return fallback;
  return next;
};

const hasFlag = (name) => argv.includes(`--${name}`);
const resolveFromProject = (inputPath) =>
  path.isAbsolute(inputPath) ? inputPath : path.resolve(projectRoot, inputPath);

const envFlag = (name, fallback = false) => {
  const raw = String(process.env[name] ?? '').trim().toLowerCase();
  if (!raw) return fallback;
  return ['1', 'true', 'yes', 'on'].includes(raw);
};

const envNumber = (name, fallback) => {
  const value = Number(process.env[name]);
  return Number.isFinite(value) && value > 0 ? value : fallback;
};

const normalizeHyperframesFps = (value, fallback = 24) => {
  const fpsValue = Math.round(Number(value));
  return [24, 30, 60].includes(fpsValue) ? fpsValue : fallback;
};

const defaultVideo = '../hf-montage-test/source_optimized_45s.mp4';
const defaultScenePlan = '../hf-montage-test/data/scene-plan.generated.json';
const defaultWordCues = '../hf-montage-test/data/scene-word-cues.generated.json';
const defaultOutput = '../hf-montage-test/renders/hyperframes-auto.mp4';

const sourceVideoPath = resolveFromProject(getArgValue('video', defaultVideo));
const scenePlanPath = resolveFromProject(getArgValue('scene-plan', defaultScenePlan));
const wordCuesPath = resolveFromProject(getArgValue('word-cues', defaultWordCues));
const transcriptPath = getArgValue('transcript', '');
const outputPath = resolveFromProject(getArgValue('out', defaultOutput));
const maxDurationSecArg = Number(getArgValue('max-duration-sec', '0'));
const layout = getArgValue('layout', 'horizontal_simple');
const renderLayout = createRenderLayout({layout, envFlag});
const isYoutubeLayout = renderLayout.isYoutube;
const isVerticalHeygenLayout = renderLayout.isVerticalHeygen;
const isSmartDirectorLayout = renderLayout.isSmartDirector;
const defaultFps = isYoutubeLayout
  ? (process.env.HYPERFRAMES_YOUTUBE_FPS || process.env.HYPERFRAMES_RENDER_FPS || '24')
  : isVerticalHeygenLayout
    ? (process.env.HYPERFRAMES_VERTICAL_FPS || process.env.HYPERFRAMES_RENDER_FPS || '24')
    : (process.env.HYPERFRAMES_RENDER_FPS || '30');
const fps = normalizeHyperframesFps(getArgValue('fps', defaultFps), isYoutubeLayout || isVerticalHeygenLayout ? 24 : 30);
const compositeSourceVideo = renderLayout.compositeSourceVideo;
const youtubeCaptionsEnabled =
  (isYoutubeLayout && envFlag('HYPERFRAMES_YOUTUBE_CAPTIONS', false)) ||
  (isVerticalHeygenLayout && envFlag('HYPERFRAMES_VERTICAL_CAPTIONS', true));
const youtubeChapterRibbonEnabled =
  isYoutubeLayout && envFlag('HYPERFRAMES_YOUTUBE_CHAPTER_RIBBON', false);
const youtubeRequireAllImages =
  isYoutubeLayout && envFlag('HYPERFRAMES_YOUTUBE_REQUIRE_ALL_IMAGES', true);
const useVerticalDockCards =
  isVerticalHeygenLayout && envFlag('HYPERFRAMES_VERTICAL_DOCK_CARDS', true);
const verticalRequireAllImages =
  isVerticalHeygenLayout &&
  !useVerticalDockCards &&
  envFlag('HYPERFRAMES_VERTICAL_REQUIRE_ALL_IMAGES', true);
const renderQuality = getArgValue(
  'quality',
  process.env.HYPERFRAMES_RENDER_QUALITY || (isYoutubeLayout ? 'high' : 'standard')
);
const renderCrf = getArgValue(
  'crf',
  process.env.HYPERFRAMES_RENDER_CRF || (isYoutubeLayout ? '18' : '')
);
const renderVideoBitrate = getArgValue(
  'video-bitrate',
  process.env.HYPERFRAMES_RENDER_VIDEO_BITRATE || ''
);
const ffmpegPreset = process.env.FFMPEG_X264_PRESET || 'veryfast';
const ffmpegCompositeTimeoutMs = envNumber('FFMPEG_ENCODE_TIMEOUT_MS', 7200000);
const dryRun = hasFlag('dry-run');
const {generatedCompositionName} = renderLayout;
const overlaySizing = createOverlayRenderSizing({renderLayout, envNumber});
const {compositionWidth, compositionHeight} = overlaySizing;
const hyperframesRuntime = createHyperframesRuntime({isVerticalHeygenLayout, envNumber});

const browserPathCandidates = [
  process.env.HYPERFRAMES_BROWSER_PATH,
  process.env.PRODUCER_HEADLESS_SHELL_PATH,
  process.env.PUPPETEER_EXECUTABLE_PATH,
  process.env.CHROME_BIN,
  '/usr/bin/chromium-headless-shell',
].filter(Boolean);
const preferredBrowserPath = browserPathCandidates.find((candidate) => fs.existsSync(candidate));
if (preferredBrowserPath) {
  process.env.HYPERFRAMES_BROWSER_PATH = preferredBrowserPath;
  process.env.PRODUCER_HEADLESS_SHELL_PATH = preferredBrowserPath;
}

const assertExists = (filePath, label) => {
  if (!fs.existsSync(filePath)) {
    throw new Error(`${label} not found: ${filePath}`);
  }
};

const normalizeText = (value) => String(value || '').replace(/\s+/g, ' ').trim();

const meaningfulWords = (value) =>
  (normalizeText(value).toLowerCase().match(/[\p{L}\p{N}-]{4,}/gu) || []);

const textOverlapRatio = (left, right) => {
  const leftWords = meaningfulWords(left);
  const rightWords = new Set(meaningfulWords(right));
  if (!leftWords.length || !rightWords.size) return 0;
  return leftWords.filter((word) => rightWords.has(word)).length / leftWords.length;
};

const shouldHideSubtitle = (title, subtitle) => {
  const cleanTitle = normalizeText(title).toLowerCase();
  const cleanSubtitle = normalizeText(subtitle).toLowerCase();
  if (!cleanSubtitle) return true;
  if (!cleanTitle) return false;
  return (
    cleanSubtitle === cleanTitle ||
    cleanSubtitle.includes(cleanTitle) ||
    cleanTitle.includes(cleanSubtitle) ||
    textOverlapRatio(title, subtitle) >= 0.65
  );
};

const titleDensityClass = (title) => {
  const length = normalizeText(title).length;
  if (length > 58) return 'title-dense';
  if (length > 38) return 'title-compact';
  return 'title-roomy';
};

const motionClass = (index) => `motion-${(index % 3) + 1}`;

const titleMarkup = (title, escapeHtml) => {
  const clean = normalizeText(title);
  const words = clean.split(' ').filter(Boolean);
  if (words.length < 3) return escapeHtml(clean);
  const emphasisCount = words.length > 4 ? 2 : 1;
  const rest = words.slice(0, -emphasisCount).join(' ');
  const emphasis = words.slice(-emphasisCount).join(' ');
  return `${rest ? `<span class="title-rest">${escapeHtml(rest)}</span>` : ''}<span class="title-emphasis">${escapeHtml(emphasis)}</span>`;
};

const trimOpener = (value) => {
  const clean = normalizeText(value).replace(/["'«»]+/g, '').trim();
  if (!clean) return '';
  const words = clean.split(' ');
  return words.length > 6 ? words.slice(0, 6).join(' ') : clean;
};

const pickSceneOpener = (scene) => {
  if (!scene || typeof scene !== 'object') return '';
  const openerField = trimOpener(normalizeText(scene.chapterOpener || scene.opener));
  if (openerField) return openerField;
  const candidates = [
    normalizeText(scene.chapterTitle),
    normalizeText(scene.title),
    normalizeText(scene.keyword),
    ...(Array.isArray(scene.titleLines) ? scene.titleLines.map(normalizeText) : []),
    normalizeText(scene.insight),
    normalizeText(scene.cta),
  ].filter(Boolean);
  return trimOpener(candidates[0] || '');
};

const pickSceneTitle = (scene) => {
  const candidates = [
    normalizeText(scene.title),
    normalizeText(scene.chapterTitle),
    normalizeText(scene.keyword),
    ...(Array.isArray(scene.titleLines) ? scene.titleLines.map(normalizeText) : []),
    pickSceneOpener(scene),
  ].filter(Boolean);
  return candidates[0] || '';
};

const pickSceneSubtitle = (scene) => {
  const candidates = [
    normalizeText(scene.subtitle),
    normalizeText(scene.chapterSubtitle),
    normalizeText(scene.insight),
    ...(Array.isArray(scene.facts) ? scene.facts.map(normalizeText) : []),
    ...(Array.isArray(scene.steps) ? scene.steps.map(normalizeText) : []),
  ].filter(Boolean);
  return candidates[0] || '';
};

const hasDirectorCard = (scene) => {
  const title = pickSceneTitle(scene);
  const rawSubtitle = pickSceneSubtitle(scene);
  const subtitle = shouldHideSubtitle(title, rawSubtitle) ? '' : rawSubtitle;
  return Boolean(title || subtitle);
};

const sceneDuration = (scene, index, maxDuration) => {
  const nextStart = Number(scenes[index + 1]?.start);
  const sceneEnd = Number.isFinite(nextStart) ? Math.min(scene.end, nextStart - 0.08) : scene.end;
  return Math.max(0.5, Math.min(maxDuration, sceneEnd - scene.start));
};

const generatedImageId = (index) => `youtube-scene-${String(index + 1).padStart(2, '0')}`;
const generatedImageFile = (index) => `${generatedImageId(index)}.png`;
const generatedImagePath = (index) => path.join(projectRoot, 'assets', 'generated', generatedImageFile(index));

const escapeHtml = (value) =>
  String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');

const assertFinitePositive = (value, fallback) =>
  Number.isFinite(value) && value > 0 ? value : fallback;

const readJsonArray = (filePath, label) => {
  const parsed = JSON.parse(fs.readFileSync(filePath, 'utf8'));
  if (!Array.isArray(parsed)) {
    throw new Error(`${label} must be a JSON array: ${filePath}`);
  }
  return parsed;
};

const probeMediaDurationSec = (filePath) => {
  const result = spawnSync(
    'ffprobe',
    [
      '-v',
      'error',
      '-show_entries',
      'format=duration',
      '-of',
      'default=noprint_wrappers=1:nokey=1',
      filePath,
    ],
    {encoding: 'utf8'}
  );
  if (result.status !== 0 || result.error) return 0;
  const duration = Number(String(result.stdout || '').trim());
  return Number.isFinite(duration) && duration > 0 ? duration : 0;
};

assertExists(sourceVideoPath, 'Video file');
assertExists(scenePlanPath, 'Scene plan file');
assertExists(wordCuesPath, 'Word cues file');

const assetsInputDir = path.join(projectRoot, 'assets', 'input');
fs.mkdirSync(assetsInputDir, {recursive: true});

const videoExtension = path.extname(sourceVideoPath) || '.mp4';
const copiedVideoName = `source${videoExtension}`;
const copiedVideoPath = path.join(assetsInputDir, copiedVideoName);
const copiedScenePlanPath = path.join(assetsInputDir, 'scene-plan.generated.json');
const copiedWordCuesPath = path.join(assetsInputDir, 'scene-word-cues.generated.json');
const copiedTranscriptPath = path.join(assetsInputDir, 'transcript.deepgram.json');

fs.copyFileSync(sourceVideoPath, copiedVideoPath);
fs.copyFileSync(scenePlanPath, copiedScenePlanPath);
fs.copyFileSync(wordCuesPath, copiedWordCuesPath);
if (transcriptPath) {
  fs.copyFileSync(resolveFromProject(transcriptPath), copiedTranscriptPath);
}

const scenes = readJsonArray(copiedScenePlanPath, 'Scene plan')
  .map((scene) => ({
    ...scene,
    start: Number(scene?.start),
    end: Number(scene?.end),
  }))
  .filter((scene) => Number.isFinite(scene.start) && Number.isFinite(scene.end) && scene.end > scene.start)
  .sort((a, b) => a.start - b.start);

if (!scenes.length) {
  throw new Error('Scene plan has no valid timed scenes.');
}

fs.writeFileSync(copiedScenePlanPath, `${JSON.stringify(scenes, null, 2)}\n`, 'utf8');

const detectedDurationSec = scenes.reduce((max, scene) => Math.max(max, scene.end), 0);
const sourceDurationSec = probeMediaDurationSec(copiedVideoPath);
const timelineDurationSec = compositeSourceVideo
  ? detectedDurationSec
  : Math.max(detectedDurationSec, sourceDurationSec);
const maxDurationSec = Number.isFinite(maxDurationSecArg) ? maxDurationSecArg : 0;
const durationSec = maxDurationSec > 0 ? Math.min(timelineDurationSec, maxDurationSec) : timelineDurationSec;
const rootDuration = assertFinitePositive(durationSec, 1);
const renderFps = normalizeHyperframesFps(assertFinitePositive(fps, 30), 30);

const wordCues = readJsonArray(copiedWordCuesPath, 'Word cues');
if (youtubeRequireAllImages || verticalRequireAllImages) {
  const missingImages = scenes
    .map((scene, index) => ({ scene, index }))
    .filter(({ scene }) => hasDirectorCard(scene))
    .filter(({ index }) => !fs.existsSync(generatedImagePath(index)))
    .map(({ index }) => generatedImageFile(index));
  if (missingImages.length) {
    throw new Error(
      `Missing required generated image(s): ${missingImages.join(', ')}. ` +
      'Run image prompt generation and npm run generate:images before rendering.'
    );
  }
}
const simpleOverlayClips = scenes
  .map((scene, index) => {
    const text = pickSceneOpener(scene);
    if (!text) return '';
    const visibleDuration = Math.min(3, Math.max(0.5, scene.end - scene.start));
    return `
      <div
        id="opener-${index}"
        class="clip opener"
        data-start="${scene.start.toFixed(3)}"
        data-duration="${visibleDuration.toFixed(3)}"
        data-track-index="1"
      >
        <div class="opener-text">${escapeHtml(text)}</div>
      </div>`;
  })
  .filter(Boolean)
  .join('\n');

const simpleTimelineTweens = scenes
  .map((scene, index) => {
    const text = pickSceneOpener(scene);
    if (!text) return '';
    const visibleDuration = Math.min(3, Math.max(0.5, scene.end - scene.start));
    const fadeOutAt = Math.max(scene.start + 0.5, scene.start + visibleDuration - 0.35);
    return `
      tl.fromTo("#opener-${index}", { opacity: 0, y: 18 }, { opacity: 1, y: 0, duration: 0.34, ease: "power3.out" }, ${scene.start.toFixed(3)});
      tl.to("#opener-${index}", { opacity: 0, y: -10, duration: 0.32, ease: "power2.in" }, ${fadeOutAt.toFixed(3)});`;
  })
  .filter(Boolean)
  .join('\n');

const youtubeDirectorClips = scenes
  .map((scene, index) => {
    const title = pickSceneTitle(scene);
    const rawSubtitle = pickSceneSubtitle(scene);
    const subtitle = shouldHideSubtitle(title, rawSubtitle) ? '' : rawSubtitle;
    const directorCue = normalizeText(scene.directorCue || scene.cutawayRole || '');
    if (!title && !subtitle) return '';
    const duration = sceneDuration(scene, index, 9);
    if (useVerticalDockCards) {
      return verticalDockClip({
        scene,
        index,
        title: title || pickSceneOpener(scene),
        subtitle,
        duration,
        escapeHtml,
      });
    }
    const imageExists = fs.existsSync(generatedImagePath(index));
    let imageMarkup = `<div class="director-fallback" aria-hidden="true">
          <div class="fallback-panel"></div>
          <div class="fallback-line fallback-line-one"></div>
          <div class="fallback-line fallback-line-two"></div>
          <div class="fallback-line fallback-line-three"></div>
        </div>`;
    if (imageExists) {
      imageMarkup = `<img class="director-image" src="./assets/generated/${escapeHtml(generatedImageFile(index))}" />`;
    }
    return `
      <div
        id="director-${index}"
        class="clip director-card ${titleDensityClass(title)} ${motionClass(index)} ${directorPatternClass(scene)}"
        data-start="${scene.start.toFixed(3)}"
        data-duration="${duration.toFixed(3)}"
        data-track-index="1"
      >
        <div class="director-copy">
          ${directorCue ? `<div class="director-kicker">${escapeHtml(directorCue)}</div>` : ''}
          <h2>${titleMarkup(title || pickSceneOpener(scene), escapeHtml)}</h2>
          ${subtitle ? `<p>${escapeHtml(subtitle)}</p>` : ''}
        </div>
        <div class="director-visual">
          <div class="visual-scan"></div>
          ${directorPatternMarkup(scene, escapeHtml)}
          ${imageMarkup}
        </div>
      </div>`;
  })
  .filter(Boolean)
  .join('\n');

const youtubeChapterClips = scenes
  .map((scene, index) => {
    const opener = pickSceneOpener(scene);
    if (!opener) return '';
    const duration = sceneDuration(scene, index, 5.2);
    return `
      <div
        id="chapter-${index}"
        class="clip chapter-ribbon"
        data-start="${scene.start.toFixed(3)}"
        data-duration="${duration.toFixed(3)}"
        data-track-index="2"
      >
        <div class="chapter-mark"></div>
        <div>${escapeHtml(opener)}</div>
      </div>`;
  })
  .filter(Boolean)
  .join('\n');

const normalizedWordCues = wordCues
  .flatMap((cueGroup) => Array.isArray(cueGroup) ? cueGroup : [cueGroup])
  .map((cue) => {
    const start = Number(cue?.start ?? cue?.time);
    const end = Number(cue?.end);
    const text = normalizeText(cue?.punctuated_word || cue?.text || cue?.word);
    return { start, end, text };
  })
  .filter((cue) => Number.isFinite(cue.start) && cue.start <= rootDuration && cue.text)
  .sort((a, b) => a.start - b.start);

const captionChunks = normalizedWordCues.map((cue, index, cues) => {
  const start = Math.max(0, cue.start);
  const nextStart = Number(cues[index + 1]?.start);
  const cueEnd = Number.isFinite(cue.end) ? cue.end : NaN;
  const end = Number.isFinite(cueEnd)
    ? Math.max(start + 0.32, cueEnd)
    : Number.isFinite(nextStart)
      ? Math.max(start + 0.32, nextStart - 0.03)
      : start + 0.55;
  const duration = Math.max(0.34, Math.min(0.9, end - start));
  return {
    start,
    duration,
    text: cue.text.replace(/[.!?,;:]+$/g, ''),
  };
}).filter((caption) => caption.text);

const youtubeCaptionClips = captionChunks
  .map((caption, index) => `
      <div
        id="caption-${index}"
        class="clip caption-strip"
        data-start="${caption.start.toFixed(3)}"
        data-duration="${caption.duration.toFixed(3)}"
        data-track-index="3"
      >${escapeHtml(caption.text)}</div>`)
  .join('\n');

const youtubeTimelineTweens = [
  ...scenes.map((scene, index) => {
    const title = pickSceneTitle(scene);
    const rawSubtitle = pickSceneSubtitle(scene);
    const subtitle = shouldHideSubtitle(title, rawSubtitle) ? '' : rawSubtitle;
    if (!title && !subtitle) return '';
    const duration = sceneDuration(scene, index, 9);
    if (useVerticalDockCards) {
      return verticalDockTimelineTween({index, scene, duration});
    }
    const fadeOutAt = Math.max(scene.start + 0.6, scene.start + duration - 0.4);
    const panStart = index % 2 === 0 ? -14 : 14;
    const panEnd = index % 2 === 0 ? 18 : -18;
    return `
      tl.fromTo("#director-${index}", { opacity: 0, x: 64, scale: 0.985 }, { opacity: 1, x: 0, scale: 1, duration: 0.52, ease: "power3.out" }, ${scene.start.toFixed(3)});
      tl.fromTo("#director-${index} .director-image", { scale: 1.06, x: ${panStart} }, { scale: 1.16, x: ${panEnd}, duration: ${Math.max(0.8, duration - 0.2).toFixed(3)}, ease: "none" }, ${scene.start.toFixed(3)});
      tl.fromTo("#director-${index} .visual-scan", { opacity: 0, y: -90 }, { opacity: 0.36, y: 460, duration: 1.15, ease: "power2.out" }, ${(scene.start + 0.18).toFixed(3)});
      tl.to("#director-${index} .visual-scan", { opacity: 0, duration: 0.28, ease: "power1.out" }, ${(scene.start + 1.35).toFixed(3)});
${directorPatternTweens({index, scene, start: scene.start, duration})}
      tl.to("#director-${index}", { opacity: 0, x: 38, duration: 0.34, ease: "power2.in" }, ${fadeOutAt.toFixed(3)});`;
  }),
  ...(youtubeChapterRibbonEnabled ? scenes.map((scene, index) => {
    const opener = pickSceneOpener(scene);
    if (!opener) return '';
    const duration = sceneDuration(scene, index, 5.2);
    const fadeOutAt = Math.max(scene.start + 0.4, scene.start + duration - 0.28);
    return `
      tl.fromTo("#chapter-${index}", { opacity: 0, y: -18 }, { opacity: 1, y: 0, duration: 0.34, ease: "power3.out" }, ${scene.start.toFixed(3)});
      tl.to("#chapter-${index}", { opacity: 0, y: -12, duration: 0.24, ease: "power2.in" }, ${fadeOutAt.toFixed(3)});`;
  }) : []),
  ...(youtubeCaptionsEnabled ? captionChunks.map((caption, index) => {
    const fadeOutAt = Math.max(caption.start + 0.25, caption.start + caption.duration - 0.18);
    return `
      tl.fromTo("#caption-${index}", { opacity: 0, y: 18, scale: 0.94 }, { opacity: 1, y: 0, scale: 1, duration: 0.12, ease: "power2.out" }, ${caption.start.toFixed(3)});
      tl.to("#caption-${index}", { opacity: 0, y: 10, scale: 0.98, duration: 0.12, ease: "power2.in" }, ${fadeOutAt.toFixed(3)});`;
  }) : []),
].filter(Boolean).join('\n');

const overlayClips = isSmartDirectorLayout
  ? [
      youtubeDirectorClips,
      youtubeChapterRibbonEnabled ? youtubeChapterClips : '',
      youtubeCaptionsEnabled ? youtubeCaptionClips : '',
    ].filter(Boolean).join('\n')
  : simpleOverlayClips;
const timelineTweens = isSmartDirectorLayout ? youtubeTimelineTweens : simpleTimelineTweens;
const pageBackground = compositeSourceVideo ? 'transparent' : '#000';
const sourceMediaClips = compositeSourceVideo
  ? ''
  : `
      <video
        id="source-video"
        class="clip background-video"
        data-start="0"
        data-duration="${rootDuration.toFixed(3)}"
        data-track-index="0"
        data-volume="0"
        data-has-audio="false"
        src="./assets/input/${escapeHtml(copiedVideoName)}"
        muted
        playsinline
        preload="auto"
      ></video>
      <audio
        id="source-audio"
        class="clip"
        data-start="0"
        data-duration="${rootDuration.toFixed(3)}"
        data-track-index="2"
        data-volume="1"
        src="./assets/input/${escapeHtml(copiedVideoName)}"
        preload="auto"
      ></audio>`;

const html = `<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=${compositionWidth}, height=${compositionHeight}" />
    <script src="./node_modules/gsap/dist/gsap.min.js"></script>
    <style>
      * { margin: 0; padding: 0; box-sizing: border-box; }
      html, body {
        width: ${compositionWidth}px;
        height: ${compositionHeight}px;
        overflow: hidden;
        background: ${pageBackground};
        font-family: Montserrat, Arial, sans-serif;
      }
      #main {
        position: relative;
        width: ${compositionWidth}px;
        height: ${compositionHeight}px;
        overflow: hidden;
        background: ${pageBackground};
      }
      .background-video {
        position: absolute;
        inset: 0;
        width: 100%;
        height: 100%;
        object-fit: cover;
        transform: scale(1.01);
        transform-origin: center center;
        z-index: 0;
      }
      .scene-vignette {
        position: absolute;
        inset: 0;
        background:
          linear-gradient(90deg, rgba(4, 8, 15, 0.18) 0%, rgba(4, 8, 15, 0.04) 45%, rgba(4, 8, 15, 0.72) 100%),
          linear-gradient(0deg, rgba(4, 8, 15, 0.46) 0%, rgba(4, 8, 15, 0) 34%);
        z-index: 1;
        pointer-events: none;
      }
      .opener {
        position: absolute;
        left: 50%;
        bottom: 7.5%;
        max-width: 86%;
        padding: 18px 28px;
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.16);
        background: rgba(0, 0, 0, 0.56);
        transform: translateX(-50%);
        backdrop-filter: blur(4px);
        z-index: 2;
        pointer-events: none;
      }
      .opener-text {
        color: #fff;
        font-weight: 800;
        font-size: 58px;
        line-height: 1.15;
        text-align: center;
        -webkit-text-stroke: 2px rgba(0, 0, 0, 0.75);
        paint-order: stroke fill;
        text-shadow: 0 2px 8px rgba(0, 0, 0, 0.45);
        word-break: break-word;
        overflow-wrap: anywhere;
      }
      .director-card {
        position: absolute;
        right: 64px;
        top: 92px;
        width: 600px;
        height: 760px;
        padding: 28px;
        border-radius: 6px;
        background:
          linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(244, 247, 251, 0.94)),
          #f8fafc;
        border: 2px solid rgba(15, 23, 42, 0.14);
        box-shadow: 0 34px 76px rgba(0, 0, 0, 0.36);
        color: #0f172a;
        z-index: 4;
        pointer-events: none;
        display: grid;
        grid-template-rows: 212px 1fr;
        gap: 20px;
      }
      .director-copy {
        position: relative;
        display: flex;
        flex-direction: column;
        justify-content: center;
        gap: 14px;
        min-height: 0;
        padding-left: 22px;
        overflow: hidden;
      }
      .director-copy::before {
        content: "";
        position: absolute;
        left: 0;
        top: 12px;
        bottom: 12px;
        width: 5px;
        border-radius: 999px;
        background: #b43c34;
      }
      .director-card h2 {
        font-size: 44px;
        line-height: 1.04;
        font-weight: 900;
        letter-spacing: 0;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
      }
      .director-card p {
        color: #334155;
        font-size: 25px;
        line-height: 1.2;
        font-weight: 700;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
      }
      .director-visual {
        width: min(100%, 456px);
        aspect-ratio: 1 / 1;
        justify-self: center;
        align-self: center;
        overflow: hidden;
        border-radius: 8px;
        background: #e7edf5;
        border: 2px solid rgba(15, 23, 42, 0.14);
        box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.56);
      }
      .director-image {
        width: 100%;
        height: 100%;
        object-fit: cover;
        display: block;
      }
      .director-fallback {
        position: relative;
        width: 100%;
        height: 100%;
        overflow: hidden;
        background:
          linear-gradient(135deg, rgba(180, 60, 52, 0.15), rgba(29, 79, 143, 0.14)),
          #f8fafc;
      }
      .director-fallback::before {
        content: "";
        position: absolute;
        inset: 0;
        background:
          linear-gradient(90deg, rgba(15, 23, 42, 0.06) 1px, transparent 1px),
          linear-gradient(0deg, rgba(15, 23, 42, 0.05) 1px, transparent 1px);
        background-size: 42px 42px;
      }
      .fallback-panel {
        position: absolute;
        left: 36px;
        top: 44px;
        width: 58%;
        height: 48%;
        border-radius: 6px;
        border: 1px solid rgba(15, 23, 42, 0.14);
        background: rgba(255, 255, 255, 0.58);
        box-shadow: 0 18px 40px rgba(15, 23, 42, 0.10);
      }
      .fallback-line {
        position: absolute;
        left: 72px;
        height: 16px;
        border-radius: 999px;
        background: rgba(15, 23, 42, 0.22);
      }
      .fallback-line-one {
        top: 88px;
        width: 44%;
      }
      .fallback-line-two {
        top: 126px;
        width: 35%;
      }
      .fallback-line-three {
        top: 164px;
        width: 49%;
        background: rgba(180, 60, 52, 0.28);
      }
      .chapter-ribbon {
        position: absolute;
        left: 60px;
        top: 54px;
        max-width: 820px;
        padding: 16px 22px 16px 18px;
        background: rgba(15, 23, 42, 0.78);
        color: #fff;
        border: 1px solid rgba(255, 255, 255, 0.16);
        display: flex;
        align-items: center;
        gap: 14px;
        z-index: 3;
        font-size: 34px;
        line-height: 1.05;
        font-weight: 850;
        pointer-events: none;
      }
      .chapter-mark {
        width: 8px;
        height: 48px;
        background: #b43c34;
        flex: 0 0 auto;
      }
      .caption-strip {
        position: absolute;
        left: 50%;
        bottom: 42px;
        transform: translateX(-50%);
        max-width: 1180px;
        padding: 13px 22px;
        color: #fff;
        font-size: 38px;
        line-height: 1.15;
        font-weight: 850;
        text-align: center;
        background: rgba(4, 8, 15, 0.74);
        border: 1px solid rgba(255, 255, 255, 0.14);
        text-shadow: 0 2px 8px rgba(0, 0, 0, 0.72);
        z-index: 5;
        pointer-events: none;
        overflow-wrap: anywhere;
      }
      body.layout-vertical-heygen .caption-strip {
        display: block;
        left: 50%;
        right: auto;
        bottom: 210px;
        max-width: 92%;
        padding: 0;
        color: #fff;
        background: transparent;
        border: 0;
        box-shadow: none;
        font-size: 86px;
        line-height: 0.95;
        font-weight: 950;
        letter-spacing: 0;
        text-transform: uppercase;
        text-align: center;
        -webkit-text-stroke: 8px rgba(0, 0, 0, 0.88);
        paint-order: stroke fill;
        text-shadow:
          0 3px 0 rgba(0, 0, 0, 0.95),
          0 8px 22px rgba(0, 0, 0, 0.58);
        z-index: 8;
        white-space: nowrap;
        overflow: visible;
      }
      body.layout-vertical-heygen .director-card {
        left: 40px;
        right: auto;
        top: 7%;
        width: calc(100% - 80px);
        height: 80%;
        padding: 32px 38px 34px;
        grid-template-rows: auto auto;
        align-content: center;
        gap: 50px;
        background:
          linear-gradient(180deg, rgba(255, 255, 255, 0.97), rgba(244, 247, 251, 0.95)),
          #f8fafc;
        border-color: rgba(15, 23, 42, 0.16);
        box-shadow: 0 38px 86px rgba(0, 0, 0, 0.38);
      }
      body.layout-vertical-heygen .director-card.motion-2 {
        top: 6.5%;
        height: 80%;
      }
      body.layout-vertical-heygen .director-card.motion-3 {
        top: 8%;
        height: 79%;
      }
      body.layout-vertical-heygen .director-copy {
        padding: 4px 6px 0 30px;
        justify-content: flex-start;
        min-height: 0;
      }
      body.layout-vertical-heygen .director-copy::before {
        top: 5px;
        bottom: 5px;
        width: 6px;
        background: linear-gradient(180deg, #d13f2f, rgba(209, 63, 47, 0.42));
      }
      body.layout-vertical-heygen .director-kicker {
        display: inline-flex;
        width: fit-content;
        max-width: 100%;
        margin-bottom: 8px;
        padding: 5px 9px 5px 0;
        color: #b42318;
        font-size: 18px;
        line-height: 1;
        font-weight: 950;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      body.layout-vertical-heygen .director-card h2 {
        max-width: 96%;
        font-size: 72px;
        line-height: 0.92;
        font-weight: 920;
        text-wrap: balance;
        -webkit-line-clamp: 2;
      }
      body.layout-vertical-heygen .director-card h2 .title-rest,
      body.layout-vertical-heygen .director-card h2 .title-emphasis {
        display: block;
      }
      body.layout-vertical-heygen .director-card h2 .title-rest {
        color: #172033;
        font-weight: 860;
      }
      body.layout-vertical-heygen .director-card h2 .title-emphasis {
        color: #090f1f;
        font-weight: 980;
      }
      body.layout-vertical-heygen .director-card.title-compact h2 {
        font-size: 62px;
        line-height: 0.94;
        -webkit-line-clamp: 3;
      }
      body.layout-vertical-heygen .director-card.title-dense h2 {
        font-size: 54px;
        line-height: 0.96;
        -webkit-line-clamp: 3;
      }
      body.layout-vertical-heygen .director-card p {
        max-width: 92%;
        margin-top: 8px;
        font-size: 29px;
        line-height: 1.16;
        color: #475569;
        font-weight: 760;
        -webkit-line-clamp: 2;
      }
      body.layout-vertical-heygen .director-card.title-dense p,
      body.layout-vertical-heygen .director-card.title-compact p {
        font-size: 26px;
      }
      body.layout-vertical-heygen .director-visual {
        position: relative;
        width: min(100%, 800px);
        border-radius: 8px;
        align-self: center;
      }
      body.layout-vertical-heygen .director-image {
        transform-origin: center center;
        will-change: transform;
      }
      body.layout-vertical-heygen .director-cue {
        position: absolute;
        left: 18px;
        top: 18px;
        max-width: calc(100% - 36px);
        padding: 10px 13px;
        border-radius: 4px;
        background: rgba(15, 23, 42, 0.88);
        color: #fff;
        font-size: 23px;
        line-height: 1;
        font-weight: 900;
        letter-spacing: 0;
        text-transform: uppercase;
        z-index: 3;
        box-shadow: 0 14px 30px rgba(15, 23, 42, 0.24);
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      body.layout-vertical-heygen .visual-scan {
        position: absolute;
        left: -8%;
        right: -8%;
        top: 0;
        height: 76px;
        background: linear-gradient(180deg, rgba(209, 63, 47, 0), rgba(209, 63, 47, 0.38), rgba(209, 63, 47, 0));
        opacity: 0;
        z-index: 2;
        pointer-events: none;
        mix-blend-mode: multiply;
      }
      body.layout-vertical-heygen .chapter-ribbon {
        display: none;
      }
${DIRECTOR_PATTERN_CSS}
${useVerticalDockCards ? VERTICAL_DOCK_CSS : ''}
${overlayScaleCss(overlaySizing)}
    </style>
  </head>
  <body class="layout-${isVerticalHeygenLayout ? 'vertical-heygen' : isYoutubeLayout ? 'youtube' : 'simple'}">
    <div
      id="main"
      data-composition-id="main"
      data-start="0"
      data-duration="${rootDuration.toFixed(3)}"
      data-fps="${renderFps}"
      data-width="${compositionWidth}"
      data-height="${compositionHeight}"
    >
${sourceMediaClips}
      ${isYoutubeLayout ? '<div class="scene-vignette"></div>' : ''}
${wrapOverlayClips(overlayClips, overlaySizing)}
    </div>

    <script>
      window.__timelines = window.__timelines || {};
      const tl = gsap.timeline({ paused: true });
${timelineTweens}
      window.__timelines.main = tl;
    </script>
  </body>
</html>
`;

fs.writeFileSync(path.join(projectRoot, generatedCompositionName), html, 'utf8');

const outputDir = path.dirname(outputPath);
fs.mkdirSync(outputDir, {recursive: true});

const outputExtension = path.extname(outputPath) || '.mp4';
const outputStem = outputPath.slice(0, -outputExtension.length) || outputPath;
const overlayOutputPath = `${outputStem}.overlay.webm`;
const hyperframesOutputPath = compositeSourceVideo ? overlayOutputPath : outputPath;
const hyperframesBin = path.join(projectRoot, 'node_modules', '.bin', 'hyperframes');
const hasLocalHyperframesBin = fs.existsSync(hyperframesBin);
const renderCommand = hasLocalHyperframesBin ? hyperframesBin : 'npx';
const renderCommandPrefix = hasLocalHyperframesBin ? [] : ['--no-install', 'hyperframes'];

const renderArgs = [
  ...renderCommandPrefix,
  'render',
  '--composition',
  generatedCompositionName,
  '--output',
  hyperframesOutputPath,
  '--fps',
  String(renderFps),
  '--quality',
  renderQuality,
  ...hyperframesRuntime.renderArgs,
];

if (compositeSourceVideo) {
  renderArgs.push('--format', 'webm');
} else if (renderCrf) {
  renderArgs.push('--crf', renderCrf);
} else if (renderVideoBitrate) {
  renderArgs.push('--video-bitrate', renderVideoBitrate);
}

const ffmpegArgs = [
  '-y',
  '-i',
  copiedVideoPath,
  '-c:v',
  'libvpx-vp9',
  '-i',
  overlayOutputPath,
  '-filter_complex',
  createCompositeFilter(overlaySizing),
  '-map',
  '[v]',
  '-map',
  '0:a?',
  '-c:v',
  'libx264',
  '-preset',
  ffmpegPreset,
  '-crf',
  renderCrf || '18',
  '-pix_fmt',
  'yuv420p',
  '-movflags',
  '+faststart',
  '-c:a',
  'aac',
  '-b:a',
  '160k',
  outputPath,
];

console.log('[render-auto] Prepared Hyperframes input files:');
console.log(`  video: ${sourceVideoPath}`);
console.log(`  scene-plan: ${scenePlanPath}`);
console.log(`  word-cues: ${wordCuesPath}`);
console.log(`  output: ${outputPath}`);
console.log(`  duration: ${rootDuration}s`);
console.log(`  layout: ${layout}`);
console.log(`  quality: ${renderQuality}`);
if (hyperframesRuntime.summary) {
  console.log(`  hyperframes-runtime: ${hyperframesRuntime.summary}`);
}
console.log(
  `  render-size: ${compositionWidth}x${compositionHeight}` +
  (overlaySizing.usesScaledOverlay
    ? ` scaled overlay -> ${overlaySizing.outputWidth}x${overlaySizing.outputHeight}`
    : '')
);
console.log(`  source-composite: ${compositeSourceVideo ? 'ffmpeg' : 'hyperframes'}`);

if (dryRun) {
  console.log('[render-auto] Dry run mode enabled. Render command:');
  console.log(`${renderCommand} ${renderArgs.join(' ')}`);
  if (compositeSourceVideo) {
    console.log('[render-auto] Composite command:');
    console.log(`ffmpeg ${ffmpegArgs.join(' ')}`);
  }
  process.exit(0);
}

const result = spawnSync(renderCommand, renderArgs, {
  cwd: projectRoot,
  stdio: 'inherit',
  env: hyperframesRuntime.env,
});

if (result.error) {
  throw result.error;
}

if (result.status !== 0) {
  process.exit(result.status ?? 1);
}

if (compositeSourceVideo) {
  console.log('[render-auto] Compositing Hyperframes overlay over source video with ffmpeg...');
  const compositeResult = spawnSync('ffmpeg', ffmpegArgs, {
    cwd: projectRoot,
    stdio: 'inherit',
    timeout: ffmpegCompositeTimeoutMs,
  });

  if (compositeResult.error) {
    throw compositeResult.error;
  }
  if (compositeResult.status !== 0) {
    process.exit(compositeResult.status ?? 1);
  }
  if (process.env.KEEP_TEMP !== '1') {
    fs.rmSync(overlayOutputPath, {force: true});
  }
}

process.exit(0);
