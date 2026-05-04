# Prompt278 result: local autonomous loop controller

## Scope
Modified:
- `automation/orchestration/planned_execution_runner.py`

## What changed
- Added `_build_project_browser_autonomous_local_loop_state(...)`.
- Consumes normalized states from:
  - `project_browser_autonomous_chatgpt_diff_review_decision_*`
  - `project_browser_autonomous_commit_tag_gate_*`
  - `project_browser_autonomous_commit_tag_execution_*`
  - `project_browser_autonomous_pr_queue_state_*`
  - `project_browser_autonomous_chrome_runner_bridge_bounded_loop_*`
  - `project_browser_autonomous_codex_execution_gate_*`
- Added default-off loop controls:
  - `project_browser_autonomous_local_autonomous_loop_enabled`
  - `project_browser_autonomous_local_autonomous_loop_route_enabled`
  - `project_browser_autonomous_local_autonomous_loop_max_iterations`
  - `project_browser_autonomous_local_autonomous_loop_iteration`
- Implements local decision routing:
  - manual/blocking -> `manual_review_required`
  - revert -> `prepare_safe_revert`
  - fix with prompt -> `run_codex_fix`
  - approve before commit/tag completion -> `prepare_commit_tag_gate`
  - commit/tag completed -> `update_pr_queue_or_prepare_next_pr`
  - PR queue updated with next item -> `prepare_next_pr_prompt`
  - PR queue complete -> `project_complete`
  - existing implementation prompt ready -> `run_codex_implementation`
  - fallback -> `blocked_no_next_step`
- Adds next PR prompt preparation:
  - selects next PR item from normalized queue
  - exposes existing prompt/prompt_fingerprint when present
  - generates compact single-item ChatGPT request when prompt text is missing
- Adds fix/revert/commit-tag routing behavior without execution:
  - fix routes toward existing `generated_fix_prompt.txt`
  - revert exposes revert plan only
  - approve routes toward commit/tag gate preparation only
- Adds stop conditions:
  - loop disabled
  - iteration limit reached
  - duplicate selected step fingerprint
  - manual-review/blocking state
  - missing required state
  - project complete
- Adds deterministic step fingerprint dedupe using:
  - selected next action
  - selected prompt fingerprint
  - active/next PR ids
  - review decision status
  - commit/tag execution status
- Adds normalized fields:
  - `project_browser_autonomous_local_loop_status`
  - `project_browser_autonomous_local_loop_next_action`
  - `project_browser_autonomous_local_loop_enabled`
  - `project_browser_autonomous_local_loop_route_enabled`
  - `project_browser_autonomous_local_loop_iteration`
  - `project_browser_autonomous_local_loop_max_iterations`
  - `project_browser_autonomous_local_loop_active_pr_index`
  - `project_browser_autonomous_local_loop_active_pr_id`
  - `project_browser_autonomous_local_loop_next_pr_index`
  - `project_browser_autonomous_local_loop_next_pr_id`
  - `project_browser_autonomous_local_loop_selected_prompt`
  - `project_browser_autonomous_local_loop_selected_prompt_fingerprint`
  - `project_browser_autonomous_local_loop_selected_step_fingerprint`
  - `project_browser_autonomous_local_loop_revert_plan`
  - `project_browser_autonomous_local_loop_fix_recommendations`
  - `project_browser_autonomous_local_loop_blocked_reason`
- Adds status handling:
  - `local_loop_not_requested`
  - `local_loop_decision_only`
  - `local_loop_ready_run_codex_implementation`
  - `local_loop_ready_run_codex_fix`
  - `local_loop_ready_prepare_safe_revert`
  - `local_loop_ready_prepare_commit_tag_gate`
  - `local_loop_ready_prepare_next_pr_prompt`
  - `local_loop_project_complete`
  - `local_loop_blocked_iteration_limit`
  - `local_loop_blocked_duplicate_step`
  - `local_loop_blocked_missing_state`
  - `local_loop_blocked_manual_review`
  - `local_loop_blocked_no_next_step`
- Route-enabled writes are constrained to existing surfaces only:
  - `/tmp/codex-local-runner-decision/generated_next_prompt.txt`
  - `/tmp/codex-local-runner-decision/generated_fix_prompt.txt`
  - `/tmp/codex-local-runner-chatgpt-bridge/request.md`
- Exposes local loop state in:
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
Prompt278.5 should harden the controller before Codex execution:
- prefer `pr_queue_state_project_complete` / `pr_queue_state_updated` over raw `commit_tag_execution_committed_and_tagged`
- prevent returning to queue update after queue already reflects commit/tag result
- reuse existing safe bridge request write/cleanup/dedupe behavior
- clarify route success iteration/fingerprint behavior

## Not included
- No tests.
- No Playwright.
- No ChatGPT/OpenAI API calls.
- No CAPTCHA/Verify bypass.
- No cookie/token/session storage.
- No runner daemon/scheduler.
- No unbounded loop.
- No Codex execution.
- No git commands.
- No revert.
- No commit/tag.
- No push/fetch/pull/merge/rebase.
- No GitHub PR creation.
- No branch deletion.
- No duplicate-send path.
- No git mutation during implementation.
