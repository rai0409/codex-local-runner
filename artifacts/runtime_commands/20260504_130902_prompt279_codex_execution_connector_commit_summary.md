# Prompt279 result: existing Codex execution connector

## Scope
Modified:
- `automation/orchestration/planned_execution_runner.py`

## What changed
- Added `_build_project_browser_autonomous_codex_execution_connector_state(...)`.
- Consumes normalized states from:
  - `project_browser_autonomous_local_loop_*`
  - `project_browser_autonomous_codex_execution_gate_*`
  - `project_browser_autonomous_codex_capture_gate_*`
  - `project_browser_autonomous_chrome_runner_bridge_bounded_loop_*`
- Added default-off controls:
  - `project_browser_autonomous_codex_execution_connector_enabled`
  - `project_browser_autonomous_codex_execution_connector_execute_enabled`
- Enforces local loop gating:
  - implementation requires:
    - `local_loop_status=local_loop_ready_run_codex_implementation`
    - `local_loop_next_action=run_codex_implementation`
  - fix requires:
    - `local_loop_status=local_loop_ready_run_codex_fix`
    - `local_loop_next_action=run_codex_fix`
  - `local_loop_decision_only` is not executable.
- Enforces Prompt271 Codex execution gate readiness:
  - `project_browser_autonomous_codex_execution_gate_status=codex_execution_gate_ready`
  - `project_browser_autonomous_codex_execution_gate_approved_for_execution=true`
- Uses existing route semantics only:
  - `run_existing_codex_implementation_step`
  - `run_existing_codex_fix_step`
- Restricts prompt paths to existing prompt surfaces:
  - `/tmp/codex-local-runner-decision/generated_next_prompt.txt`
  - `/tmp/codex-local-runner-decision/generated_fix_prompt.txt`
- Uses existing `_build_project_browser_autonomous_codex_invocation_execution_state(...)` route only.
- Does not create a new arbitrary shell executor or general Codex executor.
- Adds bounded prompt read and non-empty prompt requirement.
- Adds prompt fingerprint computation/normalization.
- Adds duplicate prompt blocking against prior dispatched/executed fingerprints without self-blocking the current local loop prompt.
- Adds unsafe prompt blocking for prohibited categories:
  - Playwright ChatGPT automation
  - ChatGPT/OpenAI API usage
  - CAPTCHA/Verify bypass
  - credential/session storage
  - unbounded loop
  - daemon/scheduler/queue drain
  - new execution mechanisms
  - commit/tag/PR/merge automation
  - destructive repo-external intent
- Decision-only behavior:
  - `enabled=true` and `execute_enabled=false`
  - status `codex_execution_connector_decision_only`
  - no execution
- Explicit execution behavior:
  - `enabled=true` and `execute_enabled=true`
  - runs at most one existing Codex invocation route
  - no capture script execution
  - success maps to:
    - `codex_execution_connector_executed`
    - `next_action=run_codex_capture_gate`
  - failure maps to:
    - `codex_execution_connector_blocked_execution_failed`
    - `next_action=manual_review_required`
- Captures compact execution metadata only:
  - executed bool
  - prompt kind/path/fingerprint
  - route name
  - bounded output preview
  - blocked reason
- Added normalized fields:
  - `project_browser_autonomous_codex_execution_connector_status`
  - `project_browser_autonomous_codex_execution_connector_next_action`
  - `project_browser_autonomous_codex_execution_connector_enabled`
  - `project_browser_autonomous_codex_execution_connector_execute_enabled`
  - `project_browser_autonomous_codex_execution_connector_executed`
  - `project_browser_autonomous_codex_execution_connector_prompt_kind`
  - `project_browser_autonomous_codex_execution_connector_prompt_path`
  - `project_browser_autonomous_codex_execution_connector_prompt_fingerprint`
  - `project_browser_autonomous_codex_execution_connector_route_name`
  - `project_browser_autonomous_codex_execution_connector_output_preview`
  - `project_browser_autonomous_codex_execution_connector_blocked_reason`
- Added status handling:
  - `codex_execution_connector_not_requested`
  - `codex_execution_connector_decision_only`
  - `codex_execution_connector_blocked_missing_local_loop`
  - `codex_execution_connector_blocked_missing_codex_gate`
  - `codex_execution_connector_blocked_no_existing_route`
  - `codex_execution_connector_blocked_duplicate_prompt`
  - `codex_execution_connector_blocked_unsafe_prompt`
  - `codex_execution_connector_blocked_execution_failed`
  - `codex_execution_connector_executed`
- Exposes connector state in:
  - compact planning summary
  - supporting truth refs
  - final approved restart payload

## Validation
- `python -m py_compile automation/orchestration/planned_execution_runner.py` passed.

## Manual smoke
- Not executed in this run.

## Git mutation during implementation
- None.

## Known follow-up
Prompt280 should add safe revert gate + tracked-file revert execution:
- detect ChatGPT review decision=revert
- require revert_reason/revert_plan
- use captured changed_files only
- verify git status has no extra/ambiguous changes
- default-off / execute-off
- execute only tracked-file restore when explicitly enabled
- do not clean untracked files
- do not reset/checkout/push/merge/rebase

## Not included
- No tests.
- No Playwright.
- No ChatGPT/OpenAI API calls.
- No CAPTCHA/Verify bypass.
- No cookie/token/session storage.
- No runner daemon/scheduler.
- No multi-task queue executor.
- No unbounded loop.
- No arbitrary shell execution.
- No new general Codex executor.
- No capture script execution.
- No git commands.
- No revert.
- No commit/tag.
- No push/fetch/pull/merge/rebase.
- No GitHub PR creation.
- No branch deletion.
- No duplicate-send path.
- No git mutation during implementation.
