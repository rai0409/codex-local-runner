# Prompt280 result: safe revert gate + tracked-file revert execution

## Scope
Modified:
- `automation/orchestration/planned_execution_runner.py`

## What changed
- Added `_build_project_browser_autonomous_safe_revert_state(...)`.
- Consumes normalized states from:
  - `project_browser_autonomous_chatgpt_diff_review_decision_*`
  - `project_browser_autonomous_codex_capture_gate_*`
  - `project_browser_autonomous_local_loop_*`
- Proceeds only for revert flow:
  - `project_browser_autonomous_chatgpt_diff_review_decision=revert` with revert reason/plan, or
  - `project_browser_autonomous_local_loop_status=local_loop_ready_prepare_safe_revert`
  - `project_browser_autonomous_local_loop_next_action=prepare_safe_revert`
- Added default-off controls:
  - `project_browser_autonomous_safe_revert_enabled`
  - `project_browser_autonomous_safe_revert_execute_enabled`
- `enabled=false`:
  - returns `safe_revert_not_requested`
  - runs no git commands
- `enabled=true` and `execute_enabled=false`:
  - returns `safe_revert_decision_only`
  - exposes preflight readiness
  - runs no mutating git commands
- Uses captured changed files only:
  - `project_browser_autonomous_codex_capture_gate_changed_files`
- Does not invent paths or revert files outside captured changed files.
- Adds safe path checks:
  - no absolute paths
  - no `..`
  - no `.git/`
  - no malformed/ambiguous paths
- Adds conservative large-change blocking:
  - default max changed files: 25
  - requires existing explicit large-change approval to exceed limit
- Adds conservative `git status --short` parsing:
  - blocks malformed status lines
  - blocks quoted/ambiguous paths
  - blocks rename/copy/unmerged status
  - blocks duplicate status entries
- Preflight requires:
  - repo path exists and is a directory
  - changed files non-empty
  - git status paths exactly match captured changed files
  - no extra changed/staged/untracked files outside captured changed files
  - no untracked files in changed_files
- Adds strict safe-revert git allowlist, only when explicitly execute-enabled and preflight passes:
  - `git status --short`
  - `git restore --staged -- <changed_files...>`
  - `git restore -- <changed_files...>`
  - `git status --short`
- Does not run:
  - `git clean`
  - `git reset`
  - `git checkout`
  - `git push`
  - `git pull`
  - `git fetch`
  - `git merge`
  - `git rebase`
  - `git stash`
  - `git commit`
  - `git tag`
- Does not delete untracked files.
- Adds post-status validation:
  - if changed files remain after restore, status becomes `safe_revert_blocked_post_status_not_clean`
- Adds normalized fields:
  - `project_browser_autonomous_safe_revert_status`
  - `project_browser_autonomous_safe_revert_next_action`
  - `project_browser_autonomous_safe_revert_enabled`
  - `project_browser_autonomous_safe_revert_execute_enabled`
  - `project_browser_autonomous_safe_revert_reverted`
  - `project_browser_autonomous_safe_revert_changed_files`
  - `project_browser_autonomous_safe_revert_revert_reason`
  - `project_browser_autonomous_safe_revert_revert_plan`
  - `project_browser_autonomous_safe_revert_pre_git_status_short`
  - `project_browser_autonomous_safe_revert_post_git_status_short`
  - `project_browser_autonomous_safe_revert_blocked_reason`
- Added status handling:
  - `safe_revert_not_requested`
  - `safe_revert_decision_only`
  - `safe_revert_blocked_missing_revert_decision`
  - `safe_revert_blocked_missing_changed_files`
  - `safe_revert_blocked_unsafe_paths`
  - `safe_revert_blocked_large_change`
  - `safe_revert_blocked_unexpected_changes`
  - `safe_revert_blocked_ambiguous_status`
  - `safe_revert_blocked_untracked_files`
  - `safe_revert_blocked_git_failed`
  - `safe_revert_blocked_post_status_not_clean`
  - `safe_revert_reverted`
- Added next-action mapping:
  - `enable_safe_revert`
  - `set_execute_enabled_for_safe_revert`
  - `manual_review_required`
  - `regenerate_pr_prompt_or_continue_loop`
- Exposes safe revert state in:
  - compact planning summary
  - supporting truth refs
  - final approved restart payload
  - nested `project_browser_autonomous_safe_revert_state_normalized`

## Validation
- `python -m py_compile automation/orchestration/planned_execution_runner.py` passed.

## Manual smoke
- Not executed in this run.

## Git mutation during implementation
- None.

## Clarification
- A strict safe-revert git allowlist was added.
- No arbitrary git command path was added.
- No git mutation was performed during implementation.

## Known follow-up
Prompt281 should add bounded local autonomous loop coordination:
- consume local loop, Codex connector, capture gate, ChatGPT review decision, safe revert, commit/tag, and PR queue states
- advance one bounded local iteration at a time
- stop on manual review, duplicate/no progress, iteration limit, or project complete
- do not add unbounded loop, daemon, scheduler, GitHub push/PR/merge, or branch cleanup

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
- No Codex execution.
- No capture script execution.
- No commit/tag execution.
- No push/fetch/pull/merge/rebase.
- No GitHub PR creation.
- No branch deletion.
- No untracked deletion.
- No duplicate-send path.
