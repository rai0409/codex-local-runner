const BRIDGE_BASE_URL = "http://172.25.238.255:8765";

async function bridgeFetch(path, options = {}) {
  try {
    const response = await fetch(`${BRIDGE_BASE_URL}${path}`, options);
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

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (!message || typeof message !== "object") {
    return false;
  }

  if (message.type === "BRIDGE_GET_NEXT_TASK") {
    void bridgeFetch("/next-task", { method: "GET" }).then(sendResponse);
    return true;
  }

  if (message.type === "BRIDGE_POST_STATUS") {
    const payload = message.payload && typeof message.payload === "object" ? message.payload : {};
    void bridgeFetch("/status", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }).then(sendResponse);
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

  return false;
});
