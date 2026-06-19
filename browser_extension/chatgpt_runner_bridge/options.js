const input = document.getElementById("bridgeBaseUrl");
const statusEl = document.getElementById("status");

function setStatus(message) {
  statusEl.textContent = message;
}

function sendMessage(message) {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage(message, (response) => {
      resolve(response || {});
    });
  });
}

async function loadCurrent() {
  const response = await sendMessage({ type: "BRIDGE_GET_BASE_URL" });
  if (response.ok && response.bridge_base_url) {
    input.value = response.bridge_base_url;
  }
}

document.getElementById("save").addEventListener("click", async () => {
  const response = await sendMessage({
    type: "BRIDGE_SET_BASE_URL",
    bridge_base_url: input.value
  });
  if (response.ok) {
    input.value = response.bridge_base_url;
    setStatus(`Saved ${response.bridge_base_url}`);
    return;
  }
  setStatus(`Rejected: ${response.detail || response.error || "invalid bridge URL"}`);
});

document.getElementById("health").addEventListener("click", async () => {
  const response = await sendMessage({ type: "BRIDGE_HEALTH_CHECK" });
  setStatus(JSON.stringify(response, null, 2));
});

void loadCurrent();
