# Prompt265.5 result: hardened Chrome Runner Bridge one-shot handoff

## Scope
- Modified: `automation/orchestration/planned_execution_runner.py`

## What changed
- Added explicit one-shot execution/wait gates:
  - `project_browser_autonomous_chrome_runner_bridge_one_shot_execution_enabled`
  - `project_browser_autonomous_chrome_runner_bridge_one_shot_wait_enabled`
- Both gates default conservative false.
- Disabled state now returns before bridge directory creation, stale file cleanup, request write, or wait.
- Added prepare-without-wait behavior:
  - execution enabled + wait disabled writes `request.md`, exposes operator action, and exits without polling.
- Removed synthesized project request fallback prompt.
- Uses only existing prepared/project-analysis prompt sources.
- Replaced unbounded `read_bytes()` reads for `response.md` and `status.json` with bounded reads.
- Added:
  - `project_browser_autonomous_chrome_runner_bridge_request_write_error`
- Fixed supporting truth-ref gating for:
  - `approved_restart_execution_contract.project_browser_autonomous_chrome_runner_bridge_operator_action_required`
- Preserved compact summary, supporting truth refs, and final approved restart payload exposure.

## Validation
- `python -m py_compile automation/orchestration/planned_execution_runner.py` passed.

## Not included
- No tests.
- No Playwright.
- No ChatGPT API calls.
- No browser executor.
- No daemon / scheduler / background loop / queue drain.
- No shell execution feature path.
- No git mutation during implementation.
