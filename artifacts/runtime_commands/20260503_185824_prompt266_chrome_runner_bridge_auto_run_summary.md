# Prompt266 result: opt-in Chrome Runner Bridge auto-run mode

## Scope
Modified:
- `browser_extension/chatgpt_runner_bridge/background.js`
- `browser_extension/chatgpt_runner_bridge/content.js`
- `browser_extension/chatgpt_runner_bridge/manifest.json`

## What changed
- Added default-off auto-run state in `chrome.storage.local`.
- Added `chrome.alarms` polling with conservative 1 minute interval.
- Reused existing `/next-task` bridge path; no new bridge protocol.
- Finds existing ChatGPT tabs only:
  - `https://chatgpt.com/*`
  - `https://chat.openai.com/*`
- Does not open login pages.
- Sends one `RUN_CHATGPT_BRIDGE_ONCE` per task fingerprint.
- Added deterministic request fingerprinting for duplicate-send protection.
- Added terminal-state pause handling:
  - `response_saved`
  - `result_saved`
  - `human_verification_required`
  - `submit_not_confirmed`
  - `bridge_error`
  - `response_timeout`
  - `composer_not_found`
  - `prompt_insert_failed`
  - `run_in_progress`
  - `chatgpt_tab_not_found`
- Added compact background state endpoints:
  - `BRIDGE_SET_AUTORUN_ENABLED`
  - `BRIDGE_GET_AUTORUN_STATUS`
  - `BRIDGE_RUN_RESULT`
- Preserved existing manual icon-click one-shot behavior.
- Added `alarms` permission to `manifest.json`.

## Validation
- `node --check browser_extension/chatgpt_runner_bridge/background.js` passed.
- `node --check browser_extension/chatgpt_runner_bridge/content.js` passed.

## Manual smoke
- Not executed in this run.

## Known follow-up
Prompt266.5 should minimally harden:
- auto-run enable/disable/status operator instructions
- service-worker restart recovery when `auto_run_enabled=true`
- stale blocked-state reset path
- retry/reset behavior without adding a new bridge protocol

## Not included
- No tests.
- No Playwright.
- No ChatGPT API calls.
- No CAPTCHA/Verify bypass.
- No cookie/token/session storage.
- No runner daemon/scheduler.
- No new bridge protocol.
- No git mutation during implementation.
