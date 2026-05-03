# Prompt265 result: Chrome Runner Bridge one-shot handoff

## Scope
- Modified: `automation/orchestration/planned_execution_runner.py`
- Added private builder:
  - `_build_project_browser_autonomous_chrome_runner_bridge_one_shot_state(...)`

## What changed
- Adds runner-side bounded one-shot Chrome Runner Bridge handoff.
- Writes `/tmp/codex-local-runner-chatgpt-bridge/request.md` from existing prepared/approved prompt sources when available.
- Clears stale `response.md` and `status.json`.
- Exposes operator action to click the Chrome extension once.
- Polls `status.json` and `response.md` with bounded wait.
- Classifies response as missing / not_file / empty / transient / ready / read_error.
- Exposes compact summary, supporting truth refs, and final approved restart payload normalized state.

## Exposed compact fields
- `project_browser_autonomous_chrome_runner_bridge_one_shot_status`
- `project_browser_autonomous_chrome_runner_bridge_one_shot_next_action`
- `project_browser_autonomous_chrome_runner_bridge_operator_action_required`
- `project_browser_autonomous_chrome_runner_bridge_wait_exit_reason`

## Final payload
- Merges flattened `project_browser_autonomous_chrome_runner_bridge_*` fields.
- Adds `project_browser_autonomous_chrome_runner_bridge_one_shot_state_normalized`.

## Validation
- `python -m py_compile automation/orchestration/planned_execution_runner.py` passed.

## Not included
- No Playwright.
- No ChatGPT API path.
- No browser executor.
- No Chrome auto-click.
- No bridge server auto-start.
- No daemon / scheduler / unbounded loop.
- No shell command execution feature path.
- No tests.
