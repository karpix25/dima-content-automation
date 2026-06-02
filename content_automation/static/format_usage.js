const USED_STATUSES = new Set(["draft", "submitted", "queued", "processing", "delivered"]);
const LIVE_STATUSES = new Set(["submitted", "queued", "processing"]);

export function formatButtonState({ jobs, formats, scriptId, formatKey, creating }) {
  const usage = usageForScript(jobs, formats, scriptId);
  const creatingThis = Boolean(
    creating
      && String(creating.scriptId) === String(scriptId)
      && creating.formatKey === formatKey,
  );
  const used = formatKey === "all" ? usage.hasAnyUsed : usage.usedKeys.has(formatKey) || usage.usedKeys.has("all");
  const live = formatKey === "all" ? usage.hasAnyLive : usage.liveKeys.has(formatKey) || usage.liveKeys.has("all");
  return {
    disabled: creatingThis || used,
    creating: creatingThis,
    used,
    live,
    label: buttonLabel(formats, formatKey, { creating: creatingThis, used, live }),
  };
}

export function usageSummary(jobs, formats, scriptId) {
  const usage = usageForScript(jobs, formats, scriptId);
  if (!usage.labels.length) return "";
  return `Уже запускали: ${usage.labels.join(", ")}`;
}

function usageForScript(jobs, formats, scriptId) {
  const usedKeys = new Set();
  const liveKeys = new Set();
  for (const job of jobs || []) {
    if (String(job.script_id) !== String(scriptId) || !USED_STATUSES.has(job.status)) continue;
    usedKeys.add(job.format_key);
    if (LIVE_STATUSES.has(job.status)) liveKeys.add(job.format_key);
  }
  const labels = [...usedKeys]
    .filter((key) => key !== "all")
    .map((key) => formatLabel(formats, key))
    .filter(Boolean);
  if (usedKeys.has("all")) labels.unshift("Все форматы");
  return {
    usedKeys,
    liveKeys,
    labels: [...new Set(labels)],
    hasAnyUsed: usedKeys.size > 0,
    hasAnyLive: liveKeys.size > 0,
  };
}

function buttonLabel(formats, formatKey, state) {
  if (state.creating) return "Создаю...";
  if (state.live) return "Уже в работе";
  if (state.used) return "Уже использовано";
  return formatLabel(formats, formatKey);
}

function formatLabel(formats, formatKey) {
  if (formatKey === "all") return "Все форматы";
  return formats.find((item) => item.key === formatKey)?.label || formatKey;
}
