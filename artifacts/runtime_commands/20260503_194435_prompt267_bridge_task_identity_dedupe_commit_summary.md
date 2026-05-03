# Prompt267 result: bridge task identity and dedupe

## Scope
Modified:
- `scripts/chatgpt_bridge_server.py`
- `browser_extension/chatgpt_runner_bridge/background.js`
- `browser_extension/chatgpt_runner_bridge/content.js`

Added:
- `artifacts/runtime_commands/20260503_203900_prompt267_bridge_task_identity_dedupe_summary.md`

## What changed
- Added single-active-task identity from `request.md`:
  - `task_id`
  - `request_fingerprint`
  - `created_at`
  - `attempt_count`
  - `status`
- Kept `GET /next-task` backward compatible with:
  - `has_task`
  - `prompt`
- `GET /next-task` now returns a task only when task state is `ready`.
- Suppresses prompt delivery when state is:
  - `in_progress`
  - `response_saved`
  - `blocked`
  - `consumed`
- `POST /status` now persists task identity fields into `status.json`.
- `POST /result` now persists task identity and marks task as `response_saved`.
- Extension auto-run dedupe now gates by `task_id` or `request_fingerprint`.
- `content.js` propagates task identity through status/result relay.

## Validation
- `python -m py_compile scripts/chatgpt_bridge_server.py` passed.
- `node --check browser_extension/chatgpt_runner_bridge/background.js` passed.
- `node --check browser_extension/chatgpt_runner_bridge/content.js` passed.

## Manual smoke
- Not executed in this run.

## Known follow-up
Prompt268 should harden the single-task lifecycle:
- make state transitions explicit
- stabilize `attempt_count`
- avoid partial/double status writes
- add minimal result consumption/reset support if needed

## Not included
- No tests.
- No Playwright.
- No ChatGPT API calls.
- No CAPTCHA/Verify bypass.
- No cookie/token/session storage.
- No runner daemon/scheduler.
- No multi-task queue.
- No autonomous loop.
- No duplicate-send path.
- No git mutation during implementation.
