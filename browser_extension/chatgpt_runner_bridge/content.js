const RESPONSE_TIMEOUT_MS = 600000;
const RESPONSE_POLL_INTERVAL_MS = 10000;
const STABLE_POLLS_REQUIRED = 3;
const USER_MESSAGE_CONFIRM_TIMEOUT_MS = 30000;
const USER_MESSAGE_RETRY_INTERVAL_MS = 10000;
const DIAG_MARKER = "[BRIDGE_DIAGNOSE_ONLY]";

let runInProgress = false;
let runOverlay = null;
const runHighlightCleanups = [];

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function normalizeText(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function compactPreview(value, maxLength = 160) {
  const text = normalizeText(value);
  if (text.length <= maxLength) {
    return text;
  }
  return `${text.slice(0, maxLength)}…`;
}

function createBridgeError(reason, details = {}) {
  const error = new Error(reason);
  error.bridgeReason = reason;
  error.bridgeDetails = details;
  return error;
}

function containsPromptText(haystack, prompt) {
  const lhs = normalizeText(haystack);
  const rhs = normalizeText(prompt);
  if (!rhs) {
    return false;
  }
  return lhs.includes(rhs);
}

function readComposerText(composer) {
  if (!composer) {
    return "";
  }
  const tag = (composer.tagName || "").toLowerCase();
  if (tag === "textarea") {
    return composer.value || "";
  }
  return composer.innerText || composer.textContent || "";
}

function isVisibleElement(el) {
  if (!el || !(el instanceof Element)) {
    return false;
  }
  if (!el.isConnected) {
    return false;
  }

  const rect = el.getBoundingClientRect();
  if (!rect || rect.width <= 0 || rect.height <= 0) {
    return false;
  }

  const style = window.getComputedStyle(el);
  if (!style || style.display === "none" || style.visibility === "hidden") {
    return false;
  }

  const opacity = Number.parseFloat(style.opacity || "1");
  if (Number.isFinite(opacity) && opacity <= 0) {
    return false;
  }

  const ariaHidden = (el.getAttribute("aria-hidden") || "").toLowerCase();
  if (ariaHidden === "true") {
    return false;
  }

  if ("disabled" in el && el.disabled) {
    return false;
  }

  return true;
}

function elementRect(el) {
  if (!el || !(el instanceof Element)) {
    return { x: 0, y: 0, width: 0, height: 0 };
  }
  const rect = el.getBoundingClientRect();
  return {
    x: Math.round(rect.x),
    y: Math.round(rect.y),
    width: Math.round(rect.width),
    height: Math.round(rect.height)
  };
}

function summarizeComposerCandidate(candidate) {
  if (!candidate) {
    return {};
  }
  return {
    tag: candidate.tag,
    role: candidate.role,
    aria_label: compactPreview(candidate.aria_label, 120),
    placeholder: compactPreview(candidate.placeholder, 120),
    data_testid: compactPreview(candidate.data_testid, 120),
    contenteditable: candidate.contenteditable,
    visible: candidate.visible,
    disabled: candidate.disabled,
    rect: candidate.rect,
    text_length: candidate.text_length,
    in_form: candidate.in_form,
    selector_hint: candidate.selector_hint
  };
}

function summarizeSubmitCandidate(candidate) {
  if (!candidate) {
    return {};
  }
  return {
    text: compactPreview(candidate.text, 120),
    aria_label: compactPreview(candidate.aria_label, 120),
    title: compactPreview(candidate.title, 120),
    data_testid: compactPreview(candidate.data_testid, 120),
    type: candidate.type,
    disabled: candidate.disabled,
    visible: candidate.visible,
    rect: candidate.rect,
    in_same_form_as_composer: candidate.in_same_form_as_composer,
    distance_to_composer: candidate.distance_to_composer,
    selector_hint: candidate.selector_hint
  };
}

function previewCandidates(candidates, summarizeFn, maxItems = 8) {
  return (candidates || []).slice(0, maxItems).map(summarizeFn);
}

function addHighlight(el, color) {
  if (!el || !(el instanceof Element)) {
    return;
  }
  const prevOutline = el.style.outline;
  const prevOutlineOffset = el.style.outlineOffset;
  el.style.outline = `3px solid ${color}`;
  el.style.outlineOffset = "2px";
  runHighlightCleanups.push(() => {
    el.style.outline = prevOutline;
    el.style.outlineOffset = prevOutlineOffset;
  });
}

function showRunOverlay(message, details = "") {
  if (!runOverlay) {
    runOverlay = document.createElement("div");
    runOverlay.style.position = "fixed";
    runOverlay.style.top = "10px";
    runOverlay.style.right = "10px";
    runOverlay.style.zIndex = "2147483647";
    runOverlay.style.background = "rgba(15, 23, 42, 0.95)";
    runOverlay.style.color = "#fff";
    runOverlay.style.fontSize = "12px";
    runOverlay.style.fontFamily = "ui-monospace, SFMono-Regular, Menlo, monospace";
    runOverlay.style.padding = "8px 10px";
    runOverlay.style.border = "1px solid #22d3ee";
    runOverlay.style.borderRadius = "6px";
    runOverlay.style.maxWidth = "360px";
    runOverlay.style.whiteSpace = "pre-wrap";
    document.documentElement.appendChild(runOverlay);
  }
  runOverlay.textContent = details ? `${message}\n${details}` : message;
}

function cleanupRunDiagnostics() {
  for (const cleanup of runHighlightCleanups.splice(0)) {
    try {
      cleanup();
    } catch (_error) {
      // Ignore cleanup failures.
    }
  }
  if (runOverlay && runOverlay.parentNode) {
    runOverlay.parentNode.removeChild(runOverlay);
  }
  runOverlay = null;
}

function collectComposerCandidates() {
  const selectorGroups = [
    "textarea",
    "[contenteditable='true']",
    "div[role='textbox']",
    "[data-testid*='composer']",
    "[data-testid*='prompt']",
    "form textarea",
    "form [contenteditable='true']"
  ];

  const seen = new Set();
  const candidates = [];

  for (const selector of selectorGroups) {
    const nodes = document.querySelectorAll(selector);
    for (const node of nodes) {
      if (!(node instanceof Element)) {
        continue;
      }
      if (seen.has(node)) {
        continue;
      }
      seen.add(node);

      const rect = elementRect(node);
      const text = readComposerText(node);
      const candidate = {
        el: node,
        tag: (node.tagName || "").toLowerCase(),
        role: node.getAttribute("role") || "",
        aria_label: node.getAttribute("aria-label") || "",
        placeholder: node.getAttribute("placeholder") || "",
        data_testid: node.getAttribute("data-testid") || "",
        contenteditable: node.getAttribute("contenteditable") || "",
        visible: isVisibleElement(node),
        disabled: Boolean("disabled" in node && node.disabled),
        rect,
        text_length: normalizeText(text).length,
        in_form: Boolean(node.closest("form")),
        selector_hint: selector,
        aria_hidden: (node.getAttribute("aria-hidden") || "").toLowerCase()
      };
      candidates.push(candidate);
    }
  }

  return candidates;
}

function pickBestComposerCandidate(candidates) {
  const viewportHeight = Math.max(window.innerHeight || 0, 1);

  const rank = (candidate) => {
    let score = 0;
    if (candidate.visible) score += 100;
    if (candidate.tag === "textarea") score += 30;
    if (candidate.contenteditable === "true") score += 25;
    if (candidate.role === "textbox") score += 20;
    if (candidate.in_form) score += 18;
    if (!candidate.disabled) score += 15;
    if (candidate.aria_hidden !== "true") score += 10;

    const centerY = candidate.rect.y + candidate.rect.height / 2;
    const normalizedY = Math.max(0, Math.min(1, centerY / viewportHeight));
    score += Math.round(normalizedY * 20);

    const area = candidate.rect.width * candidate.rect.height;
    if (area > 1200) {
      score += 8;
    }

    return score;
  };

  const eligible = (candidates || []).filter((candidate) => candidate.visible && !candidate.disabled);
  if (!eligible.length) {
    return null;
  }

  eligible.sort((a, b) => rank(b) - rank(a));
  return eligible[0] || null;
}

function dispatchComposerInputEvents(composer, text) {
  try {
    composer.dispatchEvent(new InputEvent("beforeinput", {
      bubbles: true,
      cancelable: true,
      data: text,
      inputType: "insertText"
    }));
  } catch (_error) {
    // Ignore beforeinput constructor incompatibility.
  }

  composer.dispatchEvent(new InputEvent("input", {
    bubbles: true,
    cancelable: true,
    data: text,
    inputType: "insertText"
  }));
  composer.dispatchEvent(new Event("change", { bubbles: true }));
}

function clearComposer(composer) {
  const tag = (composer.tagName || "").toLowerCase();

  if (tag === "textarea") {
    composer.value = "";
    dispatchComposerInputEvents(composer, "");
    return;
  }

  if (composer.isContentEditable || composer.getAttribute("contenteditable") === "true" || composer.getAttribute("role") === "textbox") {
    composer.focus();

    try {
      const selection = window.getSelection();
      if (selection) {
        const range = document.createRange();
        range.selectNodeContents(composer);
        selection.removeAllRanges();
        selection.addRange(range);
      }

      if (typeof document.execCommand === "function") {
        document.execCommand("delete", false);
      }
    } catch (_error) {
      // Fallback below.
    }

    composer.textContent = "";
    dispatchComposerInputEvents(composer, "");
    return;
  }

  throw createBridgeError("composer_unsupported");
}

function fillComposer(composer, prompt) {
  if (!isVisibleElement(composer)) {
    throw createBridgeError("composer_not_found");
  }

  const tag = (composer.tagName || "").toLowerCase();

  if (tag === "textarea") {
    composer.focus();
    clearComposer(composer);
    composer.value = prompt;
    dispatchComposerInputEvents(composer, prompt);
  } else if (composer.isContentEditable || composer.getAttribute("contenteditable") === "true" || composer.getAttribute("role") === "textbox") {
    composer.focus();
    clearComposer(composer);

    let inserted = false;
    try {
      if (typeof document.execCommand === "function") {
        inserted = document.execCommand("insertText", false, prompt) === true;
      }
    } catch (_error) {
      inserted = false;
    }

    if (!inserted) {
      composer.textContent = prompt;
    }

    dispatchComposerInputEvents(composer, prompt);
  } else {
    throw createBridgeError("composer_unsupported");
  }

  const composerText = readComposerText(composer);
  const composerTextLength = normalizeText(composerText).length;
  const promptLength = normalizeText(prompt).length;

  if (!containsPromptText(composerText, prompt)) {
    throw createBridgeError("prompt_insert_failed", {
      composer_text_length: composerTextLength,
      prompt_length: promptLength
    });
  }

  return {
    composerTextLength,
    promptLength,
    composerText
  };
}

function isVerificationVisible() {
  const bodyText = (document.body?.innerText || "").toLowerCase();
  const signals = [
    "verify you are human",
    "verify you’re human",
    "verify that you are human",
    "captcha",
    "i am human",
    "i'm human",
    "cloudflare"
  ];
  return signals.some((signal) => bodyText.includes(signal));
}

function isTransientAssistantText(text) {
  const normalized = normalizeText(text).toLowerCase();

  if (!normalized) {
    return true;
  }

  const exactTransientTexts = new Set([
    "思考中",
    "考え中",
    "thinking",
    "thinking...",
    "generating",
    "generating...",
    "応答を生成しています",
    "応答を生成しています...",
    "...",
    "…"
  ]);

  if (exactTransientTexts.has(normalized)) {
    return true;
  }

  const compact = normalized.replace(/[.。…\s]/g, "");
  if (compact === "thinking" || compact === "generating" || compact === "思考中" || compact === "考え中") {
    return true;
  }

  const shortTransientSignals = [
    "thinking",
    "generating",
    "思考中",
    "考え中",
    "生成しています",
    "応答を生成"
  ];

  return normalized.length <= 40 && shortTransientSignals.some((signal) => normalized.includes(signal));
}

function isStopGeneratingVisible() {
  const selectors = [
    'button[aria-label*="Stop"]',
    'button[aria-label*="stop"]',
    'button[aria-label*="停止"]',
    'button[data-testid*="stop"]',
    'button[data-testid*="composer-stop"]'
  ];

  for (const selector of selectors) {
    for (const node of Array.from(document.querySelectorAll(selector))) {
      if (isVisibleElement(node)) {
        return true;
      }
    }
  }

  const buttons = Array.from(document.querySelectorAll("button"));
  return buttons.some((button) => {
    if (!isVisibleElement(button)) {
      return false;
    }
    const label = normalizeText([
      button.innerText || "",
      button.textContent || "",
      button.getAttribute("aria-label") || "",
      button.getAttribute("title") || "",
      button.getAttribute("data-testid") || ""
    ].join(" ")).toLowerCase();

    return label.includes("stop") || label.includes("停止");
  });
}

function isLoadingIndicatorVisible() {
  const selectors = [
    '[aria-label*="Loading"]',
    '[aria-label*="loading"]',
    '[aria-label*="読み込み"]',
    '[data-testid*="loading"]',
    '[data-testid*="spinner"]',
    '[class*="loading"]',
    '[class*="spinner"]',
    '[role="progressbar"]'
  ];

  for (const selector of selectors) {
    for (const node of Array.from(document.querySelectorAll(selector))) {
      if (isVisibleElement(node)) {
        return true;
      }
    }
  }

  const bodyText = normalizeText(document.body?.innerText || "");
  return bodyText.includes("思考中") || bodyText.toLowerCase().includes("thinking");
}

async function postStatus(status, reason, extra = {}) {
  const payload = {
    status,
    reason,
    page_url: window.location.href,
    timestamp: new Date().toISOString(),
    ...extra
  };

  try {
    await bridgePostStatus(payload);
  } catch (error) {
    console.warn("Failed to POST /status", error);
  }
}

async function fetchNextTask() {
  const data = await bridgeGetNextTask();
  return {
    hasTask: Boolean(data && data.has_task),
    prompt: typeof data?.prompt === "string" ? data.prompt : ""
  };
}

function pressEnterFallback(el) {
  el.focus();

  const events = [
    new KeyboardEvent("keydown", {
      bubbles: true,
      cancelable: true,
      key: "Enter",
      code: "Enter",
      which: 13,
      keyCode: 13
    }),
    new KeyboardEvent("keypress", {
      bubbles: true,
      cancelable: true,
      key: "Enter",
      code: "Enter",
      which: 13,
      keyCode: 13
    }),
    new KeyboardEvent("keyup", {
      bubbles: true,
      cancelable: true,
      key: "Enter",
      code: "Enter",
      which: 13,
      keyCode: 13
    })
  ];

  for (const ev of events) {
    el.dispatchEvent(ev);
  }
}

function pressCtrlEnterFallback(el) {
  el.focus();

  const events = [
    new KeyboardEvent("keydown", {
      bubbles: true,
      cancelable: true,
      key: "Enter",
      code: "Enter",
      which: 13,
      keyCode: 13,
      ctrlKey: true
    }),
    new KeyboardEvent("keyup", {
      bubbles: true,
      cancelable: true,
      key: "Enter",
      code: "Enter",
      which: 13,
      keyCode: 13,
      ctrlKey: true
    })
  ];

  for (const ev of events) {
    el.dispatchEvent(ev);
  }
}

function distanceBetweenRects(a, b) {
  const ax = a.x + a.width / 2;
  const ay = a.y + a.height / 2;
  const bx = b.x + b.width / 2;
  const by = b.y + b.height / 2;
  const dx = ax - bx;
  const dy = ay - by;
  return Math.round(Math.sqrt(dx * dx + dy * dy));
}

function collectSubmitCandidates(composer) {
  const composerRect = elementRect(composer);
  const composerForm = composer ? composer.closest("form") : null;
  const selectors = [
    'button[data-testid="send-button"]',
    'button[data-testid="composer-submit-button"]',
    'button[data-testid="composer-send-button"]',
    'button[aria-label*="Send"]',
    'button[aria-label*="送信"]',
    'button[type="submit"]',
    'form button',
    'button:has(svg)'
  ];

  const seen = new Set();
  const candidates = [];

  for (const selector of selectors) {
    let nodes = [];
    try {
      nodes = Array.from(document.querySelectorAll(selector));
    } catch (_error) {
      if (selector === 'button:has(svg)') {
        nodes = Array.from(document.querySelectorAll("button")).filter((button) => button.querySelector("svg"));
      }
    }

    for (const node of nodes) {
      if (!(node instanceof HTMLButtonElement)) {
        continue;
      }
      if (seen.has(node)) {
        continue;
      }
      seen.add(node);

      const rect = elementRect(node);
      const sameForm = Boolean(composerForm && node.closest("form") === composerForm);
      const candidate = {
        el: node,
        text: normalizeText(node.innerText || node.textContent || "").slice(0, 160),
        aria_label: node.getAttribute("aria-label") || "",
        title: node.getAttribute("title") || "",
        data_testid: node.getAttribute("data-testid") || "",
        type: node.getAttribute("type") || "",
        disabled: Boolean(node.disabled),
        visible: isVisibleElement(node),
        rect,
        in_same_form_as_composer: sameForm,
        distance_to_composer: distanceBetweenRects(composerRect, rect),
        selector_hint: selector
      };
      candidates.push(candidate);
    }
  }

  return candidates;
}

function pickBestSubmitCandidate(candidates) {
  const score = (candidate) => {
    let value = 0;
    if (candidate.visible) value += 100;
    if (!candidate.disabled) value += 30;
    if (candidate.in_same_form_as_composer) value += 40;
    if (candidate.data_testid.includes("send") || candidate.data_testid.includes("submit")) value += 25;

    const label = `${candidate.aria_label} ${candidate.text} ${candidate.title}`.toLowerCase();
    if (label.includes("send") || label.includes("送信")) value += 20;

    value += Math.max(0, 100 - Math.min(100, candidate.distance_to_composer));
    return value;
  };

  const eligible = (candidates || []).filter((candidate) => candidate.visible && !candidate.disabled);
  if (!eligible.length) {
    return null;
  }

  eligible.sort((a, b) => score(b) - score(a));
  return eligible[0] || null;
}

async function waitForUserMessage(prompt, timeoutMs = USER_MESSAGE_CONFIRM_TIMEOUT_MS) {
  const start = Date.now();
  const normalizedPrompt = normalizeText(prompt);
  if (!normalizedPrompt) {
    return false;
  }
  const probe = normalizedPrompt.slice(0, 200);

  while (Date.now() - start < timeoutMs) {
    if (isVerificationVisible()) {
      throw createBridgeError("human_verification_required");
    }

    const selectors = [
      "[data-message-author-role='user']",
      "[data-testid^='conversation-turn-']",
      "article",
      "main article"
    ];

    for (const selector of selectors) {
      const nodes = document.querySelectorAll(selector);
      for (const node of nodes) {
        const text = normalizeText(node.innerText || node.textContent || "");
        if (!text) {
          continue;
        }
        if (text.includes(probe)) {
          return true;
        }
      }
    }

    await sleep(USER_MESSAGE_RETRY_INTERVAL_MS);
  }

  return false;
}

function collectAssistantCandidates() {
  const candidates = [];
  const seen = new Set();

  const addNode = (node, selectorUsed) => {
    if (!(node instanceof Element)) {
      return;
    }
    if (seen.has(node)) {
      return;
    }
    seen.add(node);

    const text = normalizeText(node.innerText || node.textContent || "");
    if (!text) {
      return;
    }

    candidates.push({
      text,
      selector_used: selectorUsed,
      length: text.length,
      transient: isTransientAssistantText(text),
      visible: isVisibleElement(node),
      rect: elementRect(node)
    });
  };

  const assistantRoleNodes = Array.from(document.querySelectorAll("[data-message-author-role='assistant']"));
  for (const node of assistantRoleNodes) {
    addNode(node, "[data-message-author-role='assistant']");
  }

  const assistantTurnSelectors = [
    "[data-testid^='conversation-turn-'] [data-message-author-role='assistant']",
    "article [data-message-author-role='assistant']",
    "main article [data-message-author-role='assistant']",
    "[data-message-author-role='assistant'] .markdown",
    "[data-message-author-role='assistant'] [class*='markdown']"
  ];

  for (const selector of assistantTurnSelectors) {
    for (const node of Array.from(document.querySelectorAll(selector))) {
      addNode(node, selector);
    }
  }

  if (!candidates.length) {
    const fallbackSelectors = [
      "[data-testid^='conversation-turn-']",
      "main article",
      "article",
      ".markdown",
      "[class*='markdown']"
    ];

    for (const selector of fallbackSelectors) {
      for (const node of Array.from(document.querySelectorAll(selector))) {
        const text = normalizeText(node.innerText || node.textContent || "");
        if (!text) {
          continue;
        }

        const lower = text.toLowerCase();
        const looksLikeGlobalOrComposer =
          lower.includes("chatgpt とチャットする") ||
          lower.includes("質問してみましょう") ||
          lower.includes("ファイルの追加") ||
          lower.includes("プロンプトを送信") ||
          lower.includes("音声入力");

        if (looksLikeGlobalOrComposer) {
          continue;
        }

        addNode(node, selector);
      }
    }
  }

  return candidates;
}

function collectLatestAssistantResponse() {
  const candidates = collectAssistantCandidates();
  const nonTransient = candidates.filter((candidate) => !candidate.transient && candidate.text);

  if (nonTransient.length > 0) {
    const latest = nonTransient[nonTransient.length - 1];
    return {
      text: latest.text,
      selector_used: latest.selector_used,
      candidate_count: candidates.length,
      latest_candidate_length: latest.length,
      latest_candidate_preview: compactPreview(latest.text),
      transient_candidate_seen: candidates.some((candidate) => candidate.transient)
    };
  }

  const latest = candidates[candidates.length - 1] || null;
  return {
    text: "",
    selector_used: latest ? latest.selector_used : "",
    candidate_count: candidates.length,
    latest_candidate_length: latest ? latest.length : 0,
    latest_candidate_preview: latest ? compactPreview(latest.text) : "",
    transient_candidate_seen: candidates.some((candidate) => candidate.transient)
  };
}

async function waitForStableAssistantResponse() {
  const start = Date.now();
  let previous = "";
  let stableCount = 0;
  let responseSelectorUsed = "";
  let transientCandidateSeen = false;
  let latestDiagnostics = {
    candidate_count: 0,
    latest_candidate_length: 0,
    latest_candidate_preview: "",
    selector_used: ""
  };

  while (Date.now() - start < RESPONSE_TIMEOUT_MS) {
    if (isVerificationVisible()) {
      throw createBridgeError("human_verification_required");
    }

    const stopButtonVisible = isStopGeneratingVisible();
    const loadingIndicatorVisible = isLoadingIndicatorVisible();
    const current = collectLatestAssistantResponse();

    transientCandidateSeen = transientCandidateSeen || current.transient_candidate_seen;
    latestDiagnostics = {
      candidate_count: current.candidate_count,
      latest_candidate_length: current.latest_candidate_length,
      latest_candidate_preview: current.latest_candidate_preview,
      selector_used: current.selector_used
    };

    if (!current.text || isTransientAssistantText(current.text)) {
      stableCount = 0;
      previous = "";
      await sleep(RESPONSE_POLL_INTERVAL_MS);
      continue;
    }

    if (stopButtonVisible || loadingIndicatorVisible) {
      stableCount = 0;
      previous = current.text;
      await sleep(RESPONSE_POLL_INTERVAL_MS);
      continue;
    }

    if (current.text === previous) {
      stableCount += 1;
      if (stableCount >= STABLE_POLLS_REQUIRED) {
        return {
          text: current.text,
          selector_used: current.selector_used,
          stable_polls: stableCount,
          transient_candidate_seen: transientCandidateSeen
        };
      }
    } else {
      stableCount = 1;
      previous = current.text;
      responseSelectorUsed = current.selector_used;
    }

    await sleep(RESPONSE_POLL_INTERVAL_MS);
  }

  throw createBridgeError("response_timeout", {
    transient_candidate_seen: transientCandidateSeen,
    assistant_candidate_count: latestDiagnostics.candidate_count,
    latest_candidate_length: latestDiagnostics.latest_candidate_length,
    latest_candidate_preview: latestDiagnostics.latest_candidate_preview,
    response_selector_used: responseSelectorUsed || latestDiagnostics.selector_used,
    stop_button_visible: isStopGeneratingVisible(),
    loading_indicator_visible: isLoadingIndicatorVisible(),
    body_text_length: normalizeText(document.body?.innerText || "").length
  });
}

async function postResult(responseText, metadata) {
  await bridgePostResult({ response: responseText, metadata });
}

function runtimeSendMessage(payload) {
  return new Promise((resolve, reject) => {
    try {
      chrome.runtime.sendMessage(payload, (response) => {
        const runtimeError = chrome.runtime.lastError;
        if (runtimeError) {
          reject(new Error(`bridge_runtime_error:${runtimeError.message}`));
          return;
        }
        resolve(response || {});
      });
    } catch (error) {
      reject(error);
    }
  });
}

async function bridgeGetNextTask() {
  const response = await runtimeSendMessage({ type: "BRIDGE_GET_NEXT_TASK" });
  if (!response || response.ok !== true) {
    throw createBridgeError("bridge_error", {
      detail: `bridge_fetch_failed:${response?.detail || response?.error || "unknown"}`
    });
  }
  return response.response || {};
}

async function bridgePostStatus(payload) {
  const response = await runtimeSendMessage({
    type: "BRIDGE_POST_STATUS",
    payload
  });
  if (!response || response.ok !== true) {
    throw createBridgeError("bridge_error", {
      detail: `bridge_fetch_failed:${response?.detail || response?.error || "unknown"}`
    });
  }
  return response.response || {};
}

async function bridgePostResult(payload) {
  const response = await runtimeSendMessage({
    type: "BRIDGE_POST_RESULT",
    payload
  });
  if (!response || response.ok !== true) {
    throw createBridgeError("bridge_error", {
      detail: `bridge_fetch_failed:${response?.detail || response?.error || "unknown"}`
    });
  }
  return response.response || {};
}

function mapFailureReason(error) {
  if (error && typeof error === "object" && typeof error.bridgeReason === "string") {
    return error.bridgeReason;
  }

  const msg = String(error?.message || error || "bridge_error");
  if (msg.includes("human_verification_required")) {
    return "human_verification_required";
  }
  if (msg.includes("composer_not_found") || msg.includes("composer_unsupported")) {
    return "composer_not_found";
  }
  if (msg.includes("prompt_insert_failed")) {
    return "prompt_insert_failed";
  }
  if (msg.includes("submit_not_confirmed")) {
    return "submit_not_confirmed";
  }
  if (msg.includes("response_timeout")) {
    return "response_timeout";
  }
  return "bridge_error";
}

async function runChatGptBridgeOnce() {
  if (runInProgress) {
    await postStatus("blocked", "bridge_error", { detail: "run_in_progress" });
    return;
  }

  runInProgress = true;

  let composerCandidates = [];
  let selectedComposerCandidate = null;
  let submitCandidates = [];
  let selectedSubmitCandidate = null;

  try {
    if (isVerificationVisible()) {
      await postStatus("blocked", "human_verification_required");
      return;
    }

    const task = await fetchNextTask();
    if (!task.hasTask || !task.prompt.trim()) {
      await postStatus("idle", "no_task");
      return;
    }

    let promptToUse = task.prompt;
    const normalizedPrompt = normalizeText(task.prompt);
    const diagnosticOnly = normalizedPrompt.startsWith(DIAG_MARKER);

    if (diagnosticOnly) {
      promptToUse = task.prompt.replace(/^\s*\[BRIDGE_DIAGNOSE_ONLY\]\s*/u, "");
    }

    await postStatus("running", "task_fetched", {
      step: "task_fetched",
      prompt_length: normalizeText(promptToUse).length
    });

    composerCandidates = collectComposerCandidates();
    selectedComposerCandidate = pickBestComposerCandidate(composerCandidates);

    if (!selectedComposerCandidate || !selectedComposerCandidate.el) {
      await postStatus("blocked", "composer_not_found", {
        step: "composer_not_found",
        composer_candidate_count: composerCandidates.length,
        composer_candidates_preview: previewCandidates(composerCandidates, summarizeComposerCandidate),
        body_text_length: normalizeText(document.body?.innerText || "").length,
        page_url: window.location.href
      });
      return;
    }

    const composer = selectedComposerCandidate.el;
    const composerSummary = summarizeComposerCandidate(selectedComposerCandidate);

    addHighlight(composer, "#84cc16");
    showRunOverlay(
      "ChatGPT Runner Bridge: composer selected",
      `${composerSummary.tag} rect=${JSON.stringify(composerSummary.rect)}`
    );

    await postStatus("running", "composer_found", {
      step: "composer_found",
      composer_tag: composerSummary.tag,
      composer_role: composerSummary.role,
      selected_composer_summary: composerSummary,
      composer_candidate_count: composerCandidates.length,
      composer_candidates_preview: previewCandidates(composerCandidates, summarizeComposerCandidate)
    });

    const fillInfo = fillComposer(composer, promptToUse);
    await postStatus("running", "prompt_inserted", {
      step: "prompt_inserted",
      composer_text_length: fillInfo.composerTextLength,
      prompt_length: fillInfo.promptLength
    });

    if (!containsPromptText(readComposerText(composer), promptToUse)) {
      throw createBridgeError("prompt_insert_failed", {
        composer_text_length: normalizeText(readComposerText(composer)).length,
        prompt_length: normalizeText(promptToUse).length,
        selected_composer_summary: composerSummary,
        composer_candidates_preview: previewCandidates(composerCandidates, summarizeComposerCandidate)
      });
    }

    submitCandidates = collectSubmitCandidates(composer);
    await postStatus("running", "submit_candidates_collected", {
      step: "submit_candidates_collected",
      submit_candidate_count: submitCandidates.length,
      submit_candidates_preview: previewCandidates(submitCandidates, summarizeSubmitCandidate)
    });

    selectedSubmitCandidate = pickBestSubmitCandidate(submitCandidates);
    if (selectedSubmitCandidate && selectedSubmitCandidate.el) {
      addHighlight(selectedSubmitCandidate.el, "#22d3ee");
      showRunOverlay(
        "ChatGPT Runner Bridge: submit candidate selected",
        `${selectedSubmitCandidate.data_testid || selectedSubmitCandidate.aria_label || selectedSubmitCandidate.text || "button"} rect=${JSON.stringify(selectedSubmitCandidate.rect)}`
      );
    }

    if (diagnosticOnly) {
      await postStatus("diagnostic_ready", "diagnostic_only", {
        step: "diagnostic_only",
        selected_composer_summary: composerSummary,
        composer_candidates_preview: previewCandidates(composerCandidates, summarizeComposerCandidate),
        submit_candidates_preview: previewCandidates(submitCandidates, summarizeSubmitCandidate)
      });
      return;
    }

    const trySubmitAndConfirm = async (sendMethod, submitFn) => {
      submitFn();
      await postStatus("running", "submit_attempted", {
        step: "submit_attempted",
        send_method: sendMethod
      });
      return waitForUserMessage(promptToUse);
    };

    let sendMethod = "";
    let userMessageDetected = false;

    const promptStillInComposer = () => containsPromptText(readComposerText(composer), promptToUse);

    if (selectedSubmitCandidate && selectedSubmitCandidate.el) {
      userMessageDetected = await trySubmitAndConfirm("button_click", () => selectedSubmitCandidate.el.click());
      sendMethod = "button_click";
    }

    if (!userMessageDetected && promptStillInComposer()) {
      userMessageDetected = await trySubmitAndConfirm("enter_fallback", () => pressEnterFallback(composer));
      sendMethod = "enter_fallback";
    }

    if (!userMessageDetected && promptStillInComposer()) {
      userMessageDetected = await trySubmitAndConfirm("ctrl_enter_fallback", () => pressCtrlEnterFallback(composer));
      sendMethod = "ctrl_enter_fallback";
    }

    if (!userMessageDetected) {
      throw createBridgeError("submit_not_confirmed", {
        send_method: sendMethod || "unknown",
        selected_composer_summary: composerSummary,
        selected_submit_candidate: summarizeSubmitCandidate(selectedSubmitCandidate),
        composer_text_after_submit_length: normalizeText(readComposerText(composer)).length,
        body_text_length: normalizeText(document.body?.innerText || "").length,
        submit_candidate_count: submitCandidates.length,
        submit_candidates_preview: previewCandidates(submitCandidates, summarizeSubmitCandidate)
      });
    }

    await postStatus("sent", "user_message_detected", {
      step: "user_message_detected",
      send_method: sendMethod
    });

    const response = await waitForStableAssistantResponse();
    const metadata = {
      page_url: window.location.href,
      sent_at: new Date().toISOString(),
      response_length: response.text.length,
      response_selector_used: response.selector_used,
      stable_polls: response.stable_polls,
      transient_candidate_seen: response.transient_candidate_seen
    };

    await postResult(response.text, metadata);
    await postStatus("response_saved", "result_saved", {
      ...metadata,
      step: "response_saved"
    });
  } catch (error) {
    const reason = mapFailureReason(error);
    const errorDetails = (error && typeof error === "object" && error.bridgeDetails && typeof error.bridgeDetails === "object")
      ? error.bridgeDetails
      : {};

    await postStatus("blocked", reason, {
      step: reason,
      detail: String(error?.message || error || "unknown_error"),
      ...errorDetails
    });
  } finally {
    cleanupRunDiagnostics();
    runInProgress = false;
  }
}

chrome.runtime.onMessage.addListener((message) => {
  if (message && message.type === "RUN_CHATGPT_BRIDGE_ONCE") {
    void runChatGptBridgeOnce();
  }
});