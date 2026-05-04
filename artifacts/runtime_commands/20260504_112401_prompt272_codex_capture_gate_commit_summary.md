# Prompt272 result: Codex capture gate and diff intake

## Scope
Modified:
- `automation/orchestration/planned_execution_runner.py`

## What changed
- Added `_build_project_browser_autonomous_codex_capture_gate_state(...)`.
- Consumes Prompt271 Codex execution gate state.
- Proceeds only when:
  - `project_browser_autonomous_codex_execution_gate_status=codex_execution_gate_ready`
  - `project_browser_autonomous_codex_execution_gate_approved_for_execution=true`
- Added default-off capture controls:
  - `project_browser_autonomous_codex_capture_gate_enabled`
  - `project_browser_autonomous_codex_capture_gate_execute_enabled`
- Requires existing route action:
  - `run_existing_codex_implementation_step`
  - `run_existing_codex_fix_step`
- Uses only:
  - `scripts/capture_prompt_diff.sh`
- Does not add arbitrary shell execution.
- Does not add a new Codex executor.
- If execute-enabled, runs only `scripts/capture_prompt_diff.sh`.
- Parses capture stdout for:
  - `REPORT=...`
  - `PATCH=...`
- Falls back only to known output dir:
  - `/tmp/codex-local-runner-diff-logs`
- Reads capture artifacts boundedly:
  - max 32768 bytes per file
- Normalizes:
  - changed files
  - diff summary
  - validation summary
  - Codex output summary
  - capture output path
  - capture artifact paths
- Added capture gate statuses:
  - `codex_capture_gate_not_requested`
  - `codex_capture_gate_decision_only`
  - `codex_capture_gate_ready`
  - `codex_capture_gate_captured`
  - `codex_capture_gate_blocked_missing_execution_gate`
  - `codex_capture_gate_blocked_no_existing_codex_execution_route`
  - `codex_capture_gate_blocked_missing_capture_script`
  - `codex_capture_gate_blocked_capture_unavailable`
  - `codex_capture_gate_blocked_execution_or_capture_failed`
- Exposed capture gate state in:
  - compact planning summary
  - supporting truth refs
  - final approved restart payload

## Validation
- `python -m py_compile automation/orchestration/planned_execution_runner.py` passed.

## Manual smoke
- Not executed in this run.

## Known follow-up
Prompt273 should generate a ChatGPT diff review request from captured Codex diff artifacts:
- require `codex_capture_gate_status=codex_capture_gate_captured`
- use changed files / diff summary / validation summary / Codex output summary
- write or expose a bridge review request prompt
- do not branch on review result yet
- do not commit/tag/PR/merge

## Not included
- No tests.
- No Playwright.
- No ChatGPT API calls.
- No CAPTCHA/Verify bypass.
- No cookie/token/session storage.
- No runner daemon/scheduler.
- No multi-task queue.
- No unbounded loop.
- No new shell/Codex execution path.
- No commit/tag/PR automation.
- No duplicate-send path.
- No git mutation during implementation.
