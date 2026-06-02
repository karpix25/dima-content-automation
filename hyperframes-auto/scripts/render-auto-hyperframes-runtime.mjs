export const createHyperframesRuntime = ({isVerticalHeygenLayout, envNumber, baseEnv = process.env}) => {
  if (!isVerticalHeygenLayout) {
    return {
      env: baseEnv,
      renderArgs: [],
      summary: '',
    };
  }

  const workers = Math.max(1, Math.round(envNumber('HYPERFRAMES_VERTICAL_WORKERS', 1)));
  const env = {
    ...baseEnv,
    PRODUCER_BROWSER_GPU_MODE: 'software',
    PRODUCER_DISABLE_GPU: 'true',
    PRODUCER_ENABLE_STREAMING_ENCODE: 'false',
    PRODUCER_MAX_WORKERS: String(workers),
  };

  return {
    env,
    renderArgs: ['--quiet', '--workers', String(workers)],
    summary: `quiet, workers=${workers}, streaming-encode=off, browser-gpu=software`,
  };
};
