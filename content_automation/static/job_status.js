const LIVE_STATUSES = new Set(["queued", "processing", "submitted", "ready"]);
const ERROR_STATUSES = new Set(["failed", "submit_failed"]);
const STALE_AFTER_MS = 30 * 60 * 1000;

export function isLiveStatus(status) {
  return LIVE_STATUSES.has(status);
}

export function isErrorStatus(status) {
  return ERROR_STATUSES.has(status);
}

export function isStaleJob(job, now = Date.now()) {
  if (!isLiveStatus(job?.status)) return false;
  const updated = jobTimestamp(job);
  return Boolean(updated && now - updated >= STALE_AFTER_MS);
}

export function canRetryJob(job) {
  return isErrorStatus(job?.status) || isStaleJob(job);
}

export function canStopJob(job) {
  return isStaleJob(job);
}

export function jobStatusLabel(status) {
  const labels = {
    draft: "черновик",
    ready: "создано",
    submitted: "отправлено",
    submit_failed: "ошибка",
    queued: "в очереди",
    processing: "в работе",
    delivered: "готово",
    failed: "ошибка",
  };
  return labels[status] || status || "создано";
}

export function jobStatusMessage(job) {
  if (isErrorStatus(job?.status)) return job.error || "Задача завершилась с ошибкой.";
  if (isStaleJob(job)) return "Задача давно без обновлений. Можно обновить статус, остановить или запустить повтор.";
  return `Задача ${jobStatusLabel(job?.status)}.`;
}

function jobTimestamp(job) {
  const value = job?.updated_at || job?.created_at || "";
  const date = new Date(value.includes("T") ? value : value.replace(" ", "T"));
  return Number.isNaN(date.getTime()) ? 0 : date.getTime();
}
