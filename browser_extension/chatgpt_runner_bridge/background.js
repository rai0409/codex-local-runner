// Prompt658 keeps the bridge local by default. The repo-side adapter validates
// response envelopes offline; this extension only relays explicit operator actions.
const DEFAULT_BRIDGE_BASE_URL = "http://127.0.0.1:8765";
const BRIDGE_BASE_URL_STORAGE_KEY = "bridge_base_url";
const AUTO_RUN_ALARM_NAME = "chatgpt_runner_bridge_auto_run_poll";
const AUTO_RUN_POLL_PERIOD_MINUTES = 1;

const TERMINAL_REASONS = new Set([
  "result_saved",
  "human_verification_required",
  "submit_not_confirmed",
  "bridge_error",
  "response_timeout",
  "composer_not_found",
  "prompt_insert_failed",
  "run_in_progress",
  "chatgpt_tab_not_found"
]);

const TERMINAL_STATUSES = new Set([
  "response_saved",
  "result_saved"
]);

const STATE_DEFAULTS = {
  auto_run_enabled: false,
  auto_run_polling: false,
  target_tab_found: false,
  bridge_base_url: DEFAULT_BRIDGE_BASE_URL,
  run_in_progress: false,
  last_task_id: "",
  last_task_fingerprint: "",
  last_dispatched_task_id: "",
  last_dispatched_task_fingerprint: "",
  last_terminal_status: "",
  last_terminal_reason: "",
  last_run_result: "",
  last_blocked_reason: ""
};

let stateCache = { ...STATE_DEFAULTS };
let autoRunTickInFlight = false;

function normalizeText(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function isPrivateBridgeHost(hostname) {
  const normalized = normalizeText(hostname).toLowerCase();
  if (normalized === "localhost" || normalized === "127.0.0.1") {
    return true;
  }
  const parts = normalized.split(".");
  if (parts.length !== 4) {
    return false;
  }
  if (parts.some((part) => !/^\d+$/.test(part))) {
    return false;
  }
  const nums = parts.map((part) => Number.parseInt(part, 10));
  if (nums.some((part) => !Number.isInteger(part) || part < 0 || part > 255)) {
    return false;
  }
  if (nums[0] === 10) {
    return true;
  }
  if (nums[0] === 172 && nums[1] >= 16 && nums[1] <= 31) {
    return true;
  }
  if (nums[0] === 192 && nums[1] === 168) {
    return true;
  }
  return false;
}

function normalizeBridgeBaseUrl(value) {
  const text = normalizeText(value || DEFAULT_BRIDGE_BASE_URL);
  let parsed;
  try {
    parsed = new URL(text);
  } catch (_error) {
    throw new Error("bridge_base_url_invalid");
  }
  if (parsed.protocol !== "http:") {
    throw new Error("bridge_base_url_must_use_http");
  }
  if (!isPrivateBridgeHost(parsed.hostname)) {
    throw new Error("bridge_base_url_must_use_loopback_or_private_ipv4");
  }
  if (parsed.username || parsed.password) {
    throw new Error("bridge_base_url_must_not_include_credentials");
  }
  if (parsed.pathname !== "/" || parsed.search || parsed.hash) {
    throw new Error("bridge_base_url_must_not_include_path_query_or_hash");
  }
  if (parsed.hostname === "0.0.0.0") {
    throw new Error("bridge_base_url_must_not_use_wildcard_host");
  }
  return `${parsed.protocol}//${parsed.host}`;
}

async function getBridgeBaseUrl() {
  const stored = await chrome.storage.local.get([BRIDGE_BASE_URL_STORAGE_KEY]);
  try {
    return normalizeBridgeBaseUrl(stored[BRIDGE_BASE_URL_STORAGE_KEY] || DEFAULT_BRIDGE_BASE_URL);
  } catch (_error) {
    await chrome.storage.local.set({ [BRIDGE_BASE_URL_STORAGE_KEY]: DEFAULT_BRIDGE_BASE_URL });
    return DEFAULT_BRIDGE_BASE_URL;
  }
}

async function setBridgeBaseUrl(value) {
  const normalized = normalizeBridgeBaseUrl(value);
  await chrome.storage.local.set({ [BRIDGE_BASE_URL_STORAGE_KEY]: normalized });
  await setStatePatch({ bridge_base_url: normalized });
  return normalized;
}

function normalizeTaskIdentityFromPayload(payload = {}) {
  const taskId = typeof payload.task_id === "string" ? payload.task_id : "";
  const requestFingerprint =
    typeof payload.request_fingerprint === "string"
      ? payload.request_fingerprint
      : (typeof payload.task_fingerprint === "string" ? payload.task_fingerprint : "");
  return {
    taskId: taskId.trim(),
    requestFingerprint: requestFingerprint.trim()
  };
}

function computeTaskFingerprint(text) {
  const normalized = normalizeText(text);
  let hash = 2166136261;
  for (let i = 0; i < normalized.length; i += 1) {
    hash ^= normalized.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  const unsigned = hash >>> 0;
  return `fnv1a:${normalized.length}:${unsigned.toString(16).padStart(8, "0")}`;
}

function isTerminalState(status, reason) {
  return TERMINAL_STATUSES.has(status) || TERMINAL_REASONS.has(reason);
}

function toResultLabel(status, reason) {
  return `${status || "unknown"}:${reason || "unknown"}`;
}

async function ensureStateDefaults() {
  const existing = await chrome.storage.local.get(Object.keys(STATE_DEFAULTS));
  const missing = {};
  for (const [key, defaultValue] of Object.entries(STATE_DEFAULTS)) {
    if (typeof existing[key] === "undefined") {
      missing[key] = defaultValue;
    }
  }

  if (Object.keys(missing).length > 0) {
    await chrome.storage.local.set(missing);
  }

  stateCache = { ...STATE_DEFAULTS, ...existing, ...missing };
  return stateCache;
}

async function setStatePatch(patch) {
  stateCache = { ...stateCache, ...patch };
  await chrome.storage.local.set(patch);
  return stateCache;
}

async function clearAutoRunAlarm() {
  await chrome.alarms.clear(AUTO_RUN_ALARM_NAME);
}

async function startAutoRunPolling() {
  await chrome.alarms.create(AUTO_RUN_ALARM_NAME, {
    delayInMinutes: AUTO_RUN_POLL_PERIOD_MINUTES,
    periodInMinutes: AUTO_RUN_POLL_PERIOD_MINUTES
  });
  await setStatePatch({ auto_run_polling: true });
}

async function setAutoRunEnabled(enabled) {
  const normalizedEnabled = Boolean(enabled);
  if (!normalizedEnabled) {
    await clearAutoRunAlarm();
    await setStatePatch({
      auto_run_enabled: false,
      auto_run_polling: false,
      run_in_progress: false
    });
    return stateCache;
  }

  await setStatePatch({
    auto_run_enabled: true,
    auto_run_polling: false,
    run_in_progress: false,
    last_blocked_reason: "",
    last_terminal_status: "",
    last_terminal_reason: "",
    last_run_result: "",
    target_tab_found: false
  });
  await startAutoRunPolling();
  return stateCache;
}

async function resetAutoRunState() {
  await clearAutoRunAlarm();
  const resetPatch = {
    auto_run_polling: false,
    run_in_progress: false,
    last_task_id: "",
    last_task_fingerprint: "",
    last_dispatched_task_id: "",
    last_dispatched_task_fingerprint: "",
    last_terminal_status: "",
    last_terminal_reason: "",
    last_run_result: "",
    last_blocked_reason: "",
    target_tab_found: false
  };
  await setStatePatch(resetPatch);
  return stateCache;
}

async function initializeBackgroundState() {
  await ensureStateDefaults();
  if (stateCache.auto_run_enabled) {
    await startAutoRunPolling();
    return;
  }

  if (stateCache.auto_run_polling) {
    await clearAutoRunAlarm();
    await setStatePatch({ auto_run_polling: false, run_in_progress: false });
  }
}

async function pauseAutoRunOnTerminal(status, reason, extraPatch = {}) {
  await clearAutoRunAlarm();
  const terminalPatch = {
    auto_run_polling: false,
    run_in_progress: false,
    last_run_result: toResultLabel(status, reason),
    last_terminal_status: status || "",
    last_terminal_reason: reason || "",
    last_blocked_reason: status === "blocked" ? reason || "" : "",
    ...extraPatch
  };
  await setStatePatch(terminalPatch);
}

async function bridgeFetch(path, options = {}) {
  try {
    const bridgeBaseUrl = await getBridgeBaseUrl();
    const response = await fetch(`${bridgeBaseUrl}${path}`, options);
    const text = await response.text();
    let parsed = null;
    if (text) {
      try {
        parsed = JSON.parse(text);
      } catch (_error) {
        parsed = null;
      }
    }

    if (!response.ok) {
      return {
        ok: false,
        error: "bridge_fetch_failed",
        detail: `http_${response.status}`,
        response: parsed
      };
    }

    return { ok: true, response: parsed ?? {} };
  } catch (error) {
    return {
      ok: false,
      error: "bridge_fetch_failed",
      detail: String(error?.message || error || "unknown_bridge_error")
    };
  }
}

async function findEligibleChatGptTab() {
  const candidates = await chrome.tabs.query({
    url: [
      "https://chatgpt.com/*",
      "https://chat.openai.com/*"
    ]
  });

  const eligible = candidates
    .filter((tab) => tab && typeof tab.id === "number")
    .sort((lhs, rhs) => {
      const lhsRank = (lhs.active ? 1 : 0) * 1000000 + Number(lhs.lastAccessed || 0);
      const rhsRank = (rhs.active ? 1 : 0) * 1000000 + Number(rhs.lastAccessed || 0);
      return rhsRank - lhsRank;
    });

  return eligible.length > 0 ? eligible[0] : null;
}

async function maybeRunAutoBridgeOnce() {
  if (autoRunTickInFlight) {
    return;
  }
  autoRunTickInFlight = true;

  try {
    if (!stateCache.auto_run_enabled || !stateCache.auto_run_polling) {
      return;
    }

    if (stateCache.run_in_progress) {
      await pauseAutoRunOnTerminal("blocked", "run_in_progress");
      return;
    }

    const nextTaskResult = await bridgeFetch("/next-task", { method: "GET" });
    if (!nextTaskResult.ok) {
      await pauseAutoRunOnTerminal("blocked", "bridge_error", {
        target_tab_found: false
      });
      return;
    }

    const responseBody = nextTaskResult.response || {};
    const prompt = typeof responseBody.prompt === "string" ? responseBody.prompt : "";
    const taskStatus = typeof responseBody.status === "string" ? responseBody.status : "";
    const taskId = typeof responseBody.task_id === "string" ? responseBody.task_id : "";
    const requestFingerprint = typeof responseBody.request_fingerprint === "string"
      ? responseBody.request_fingerprint
      : "";
    const effectiveFingerprint = requestFingerprint || computeTaskFingerprint(prompt);
    const hasTask = Boolean(responseBody.has_task) && normalizeText(prompt).length > 0;
    const terminalTaskState = new Set(["in_progress", "response_saved", "blocked", "consumed"]);

    if (terminalTaskState.has(taskStatus)) {
      await setStatePatch({
        run_in_progress: false,
        target_tab_found: false,
        last_task_id: taskId || stateCache.last_task_id,
        last_task_fingerprint: effectiveFingerprint || stateCache.last_task_fingerprint,
        last_terminal_status: taskStatus,
        last_terminal_reason: taskStatus,
        last_run_result: toResultLabel(taskStatus, taskStatus),
        last_blocked_reason: taskStatus === "blocked" ? "blocked" : stateCache.last_blocked_reason
      });
      return;
    }

    if (!hasTask) {
      await setStatePatch({
        target_tab_found: false,
        run_in_progress: false,
        last_task_id: taskId || stateCache.last_task_id,
        last_task_fingerprint: effectiveFingerprint || stateCache.last_task_fingerprint
      });
      return;
    }

    const taskFingerprint = effectiveFingerprint;
    if (
      (taskId && (taskId === stateCache.last_task_id || taskId === stateCache.last_dispatched_task_id)) ||
      (taskFingerprint &&
        (taskFingerprint === stateCache.last_task_fingerprint ||
          taskFingerprint === stateCache.last_dispatched_task_fingerprint))
    ) {
      return;
    }

    const targetTab = await findEligibleChatGptTab();
    if (!targetTab || typeof targetTab.id !== "number") {
      await pauseAutoRunOnTerminal("blocked", "chatgpt_tab_not_found", {
        target_tab_found: false,
        last_task_id: taskId,
        last_task_fingerprint: taskFingerprint
      });
      return;
    }

    await setStatePatch({
      target_tab_found: true,
      run_in_progress: true,
      last_dispatched_task_id: taskId,
      last_task_id: taskId,
      last_dispatched_task_fingerprint: taskFingerprint,
      last_task_fingerprint: taskFingerprint,
      last_run_result: "running:dispatch_requested",
      last_blocked_reason: ""
    });

    try {
      await chrome.tabs.sendMessage(targetTab.id, {
        type: "RUN_CHATGPT_BRIDGE_ONCE",
        auto_run: true,
        task_id: taskId,
        request_fingerprint: requestFingerprint,
        task_fingerprint: taskFingerprint
      });
    } catch (error) {
      await pauseAutoRunOnTerminal("blocked", "bridge_error", {
        target_tab_found: true,
        last_run_result: toResultLabel("blocked", "bridge_error"),
        last_blocked_reason: `bridge_error:${String(error?.message || error || "dispatch_failed")}`
      });
    }
  } finally {
    autoRunTickInFlight = false;
  }
}

async function updateStateFromRunPayload(payload = {}) {
  const status = typeof payload.status === "string" ? payload.status : "";
  const reason = typeof payload.reason === "string" ? payload.reason : "";
  const identity = normalizeTaskIdentityFromPayload(payload);
  const taskId = identity.taskId;
  const taskFingerprint = identity.requestFingerprint;

  const runInProgress = status === "running" || status === "sent";
  const patch = {
    run_in_progress: runInProgress,
    last_run_result: toResultLabel(status, reason),
    last_blocked_reason: status === "blocked" ? reason : "",
    target_tab_found: true
  };

  if (taskId) {
    patch.last_task_id = taskId;
    patch.last_dispatched_task_id = taskId;
  }
  if (taskFingerprint) {
    patch.last_task_fingerprint = taskFingerprint;
    patch.last_dispatched_task_fingerprint = taskFingerprint;
  }

  await setStatePatch(patch);

  if (isTerminalState(status, reason)) {
    await pauseAutoRunOnTerminal(status || "blocked", reason || "bridge_error", taskFingerprint ? {
      ...(taskId ? {
        last_task_id: taskId,
        last_dispatched_task_id: taskId
      } : {}),
      last_task_fingerprint: taskFingerprint,
      last_dispatched_task_fingerprint: taskFingerprint
    } : (taskId ? {
      last_task_id: taskId,
      last_dispatched_task_id: taskId
    } : {}));
  }
}

chrome.runtime.onInstalled.addListener(() => {
  void initializeBackgroundState();
});

void initializeBackgroundState();

chrome.action.onClicked.addListener(async (tab) => {
  if (!tab || typeof tab.id !== "number") {
    return;
  }

  try {
    await chrome.tabs.sendMessage(tab.id, { type: "RUN_CHATGPT_BRIDGE_ONCE" });
  } catch (error) {
    console.warn("ChatGPT bridge click dispatch failed", error);
  }
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (!alarm || alarm.name !== AUTO_RUN_ALARM_NAME) {
    return;
  }
  void maybeRunAutoBridgeOnce();
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (!message || typeof message !== "object") {
    return false;
  }

  if (message.type === "BRIDGE_GET_NEXT_TASK") {
    void bridgeFetch("/next-task", { method: "GET" }).then(sendResponse);
    return true;
  }

  if (message.type === "BRIDGE_HEALTH_CHECK") {
    void bridgeFetch("/health", { method: "GET" }).then(sendResponse);
    return true;
  }

  if (message.type === "BRIDGE_GET_BASE_URL") {
    void getBridgeBaseUrl()
      .then((bridgeBaseUrl) => sendResponse({ ok: true, bridge_base_url: bridgeBaseUrl }))
      .catch((error) => sendResponse({
        ok: false,
        error: "bridge_base_url_error",
        detail: String(error?.message || error || "bridge_base_url_failed")
      }));
    return true;
  }

  if (message.type === "BRIDGE_SET_BASE_URL") {
    void setBridgeBaseUrl(message.bridge_base_url)
      .then((bridgeBaseUrl) => sendResponse({ ok: true, bridge_base_url: bridgeBaseUrl }))
      .catch((error) => sendResponse({
        ok: false,
        error: "bridge_base_url_rejected",
        detail: String(error?.message || error || "bridge_base_url_rejected")
      }));
    return true;
  }

  if (message.type === "BRIDGE_POST_STATUS") {
    const payload = message.payload && typeof message.payload === "object" ? message.payload : {};
    void bridgeFetch("/status", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }).then((result) => {
      void updateStateFromRunPayload(payload).catch((error) => {
        console.warn("Failed to update run payload state", error);
      });
      sendResponse(result);
    });
    return true;
  }

  if (message.type === "BRIDGE_POST_RESULT") {
    const payload = message.payload && typeof message.payload === "object" ? message.payload : {};
    void bridgeFetch("/result", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }).then(sendResponse);
    return true;
  }

  if (message.type === "BRIDGE_SET_AUTORUN_ENABLED") {
    const enabled = Boolean(message.enabled);
    void setAutoRunEnabled(enabled)
      .then((state) => sendResponse({ ok: true, state }))
      .catch((error) => sendResponse({
        ok: false,
        error: "bridge_fetch_failed",
        detail: String(error?.message || error || "autorun_update_failed")
      }));
    return true;
  }

  if (message.type === "BRIDGE_GET_AUTORUN_STATUS") {
    void ensureStateDefaults()
      .then((state) => sendResponse({ ok: true, state }))
      .catch((error) => sendResponse({
        ok: false,
        error: "bridge_fetch_failed",
        detail: String(error?.message || error || "autorun_status_failed")
      }));
    return true;
  }

  if (message.type === "BRIDGE_RESET_AUTORUN_STATE") {
    void resetAutoRunState()
      .then((state) => sendResponse({ ok: true, state }))
      .catch((error) => sendResponse({
        ok: false,
        error: "bridge_fetch_failed",
        detail: String(error?.message || error || "autorun_reset_failed")
      }));
    return true;
  }

  if (message.type === "BRIDGE_RUN_RESULT") {
    const payload = message.payload && typeof message.payload === "object" ? message.payload : {};
    void updateStateFromRunPayload(payload)
      .then(() => sendResponse({ ok: true, state: stateCache }))
      .catch((error) => sendResponse({
        ok: false,
        error: "bridge_fetch_failed",
        detail: String(error?.message || error || "run_result_update_failed")
      }));
    return true;
  }

  return false;
});
