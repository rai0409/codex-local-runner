# Prompt277 result: local PR queue state management

## Scope
Modified:
- `automation/orchestration/planned_execution_runner.py`

## What changed
- Added `_build_project_browser_autonomous_pr_queue_state_state(...)`.
- Consumes Prompt276 local commit/tag execution state.
- Proceeds only when Prompt276 succeeded:
  - `project_browser_autonomous_commit_tag_execution_status=commit_tag_execution_committed_and_tagged`
  - `project_browser_autonomous_commit_tag_execution_tag_created=true`
  - `project_browser_autonomous_commit_tag_execution_commit_sha` non-empty
  - `project_browser_autonomous_commit_tag_execution_next_action=update_pr_queue_or_prepare_next_pr`
- Added default-off controls:
  - `project_browser_autonomous_pr_queue_state_enabled`
  - `project_browser_autonomous_pr_queue_state_update_enabled`
- Reads queue candidates from existing approved/prior payload fields.
- Normalizes PR queue items:
  - `id`
  - `status`
  - `prompt_fingerprint`
  - `commit_sha`
  - `tag_name`
  - `changed_files`
  - `summary`
  - `blocked_reason`
- Supports PR item statuses:
  - `pending`
  - `prompt_ready`
  - `codex_running`
  - `reviewing`
  - `fixing`
  - `ready_to_commit`
  - `committed`
  - `blocked`
- Updates active PR item to `committed` with:
  - commit SHA
  - tag name
  - changed files
  - compact summary
- Computes next PR pointer:
  - `next_pr_index`
  - `next_pr_id`
- Detects project-local completion when no pending/prompt_ready item remains.
- Blocks duplicate commit SHA across queue items.
- If queue is missing:
  - decision-only initialization when update is not enabled
  - single-item fallback queue only when update is enabled
- Adds bounded optional persistence only when an explicit repo-local artifacts path is provided by:
  - `project_browser_autonomous_pr_queue_state_path`
- Does not invent a broad persistence mechanism.
- Added normalized fields:
  - `project_browser_autonomous_pr_queue_state_status`
  - `project_browser_autonomous_pr_queue_state_next_action`
  - `project_browser_autonomous_pr_queue_state_enabled`
  - `project_browser_autonomous_pr_queue_state_update_enabled`
  - `project_browser_autonomous_pr_queue_state_roadmap_id`
  - `project_browser_autonomous_pr_queue_state_active_pr_index`
  - `project_browser_autonomous_pr_queue_state_active_pr_id`
  - `project_browser_autonomous_pr_queue_state_active_pr_status`
  - `project_browser_autonomous_pr_queue_state_next_pr_index`
  - `project_browser_autonomous_pr_queue_state_next_pr_id`
  - `project_browser_autonomous_pr_queue_state_completed_commit_sha`
  - `project_browser_autonomous_pr_queue_state_completed_tag_name`
  - `project_browser_autonomous_pr_queue_state_queue_summary`
  - `project_browser_autonomous_pr_queue_state_blocked_reason`
- Added status handling:
  - `pr_queue_state_not_requested`
  - `pr_queue_state_decision_only`
  - `pr_queue_state_blocked_missing_commit_tag_execution`
  - `pr_queue_state_blocked_missing_or_malformed_queue`
  - `pr_queue_state_blocked_duplicate_commit`
  - `pr_queue_state_updated`
  - `pr_queue_state_project_complete`
- Exposes PR queue state in:
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
Prompt278 should add a local autonomous loop controller:
- consume review decision, commit/tag gate, commit/tag execution, and PR queue state
- decide next local action
- prepare next PR prompt when next_pr_index exists
- route fix/revert/commit/next-pr decisions
- do not execute Codex, revert files, commit/tag, push, create GitHub PRs, merge, or run git commands

## Not included
- No tests.
- No Playwright.
- No ChatGPT/OpenAI API calls.
- No CAPTCHA/Verify bypass.
- No cookie/token/session storage.
- No runner daemon/scheduler.
- No multi-task queue executor.
- No unbounded loop.
- No new shell/Codex execution path.
- No git commands.
- No push/fetch/pull/merge/rebase.
- No GitHub PR creation.
- No branch deletion.
- No duplicate-send path.
- No git mutation during implementation.
