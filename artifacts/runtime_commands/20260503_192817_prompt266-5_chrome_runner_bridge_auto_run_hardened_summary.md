# Prompt266.5 result: hardened Chrome Runner Bridge auto-run usability

## Scope
Modified:
- `browser_extension/chatgpt_runner_bridge/background.js`
- `artifacts/runtime_commands/20260503_185824_prompt266_chrome_runner_bridge_auto_run_summary.md`

## What changed
- Hardened service-worker restart recovery:
  - if `auto_run_enabled=true`, startup recreates the auto-run alarm even when `auto_run_polling` was stale or false.
- Cleaned stale polling state:
  - if `auto_run_enabled=false` but `auto_run_polling=true`, startup clears the alarm and sets polling false.
- Improved enable behavior:
  - `BRIDGE_SET_AUTORUN_ENABLED(true)` clears stale non-fingerprint blocking fields:
    - `last_blocked_reason`
    - `last_terminal_status`
    - `last_terminal_reason`
    - `last_run_result`
    - `run_in_progress`
- Added operator reset endpoint:
  - `BRIDGE_RESET_AUTORUN_STATE`
  - clears local auto-run dispatch/dedupe/run state
  - does not fetch a task
  - does not send a prompt
- Added concise operator commands for:
  - enable
  - disable
  - status
  - reset
- Preserved manual icon-click one-shot behavior.

## Validation
- `node --check browser_extension/chatgpt_runner_bridge/background.js` passed.
- `node --check browser_extension/chatgpt_runner_bridge/content.js` passed.

## Manual smoke
- Not executed in this run.

## Not included
- No tests.
- No Playwright.
- No ChatGPT API calls.
- No CAPTCHA/Verify bypass.
- No cookie/token/session storage.
- No runner daemon/scheduler.
- No new bridge protocol.
- No duplicate-send path.
- No git mutation during implementation.

## Next
- Prompt267: add task identity / fingerprint / dedupe state across the existing bridge flow.
