# Prompt276 result: strict explicit local commit/tag execution

## Scope
Modified:
- `automation/orchestration/planned_execution_runner.py`

## What changed
- Added `_build_project_browser_autonomous_commit_tag_execution_state_prompt276(...)`.
- Consumes Prompt275 commit/tag readiness gate state.
- Proceeds only when Prompt275 is ready:
  - `project_browser_autonomous_commit_tag_gate_status=commit_tag_gate_ready`
  - `project_browser_autonomous_commit_tag_gate_ready=true`
  - `project_browser_autonomous_commit_tag_gate_next_action=prepare_explicit_commit_tag_execution_step`
- Added default-off execution controls:
  - `project_browser_autonomous_commit_tag_execution_enabled`
  - `project_browser_autonomous_commit_tag_execution_execute_enabled`
- `enabled=false`:
  - returns `commit_tag_execution_not_requested`
  - runs no git commands
- `enabled=true` and `execute_enabled=false`:
  - returns `commit_tag_execution_decision_only`
  - runs no git commands
- Added strict local git allowlist, only when explicitly execute-enabled and preflight passes:
  - `git status --short`
  - `git tag --list <tag_name>`
  - `git add -- <changed_files...>`
  - `git commit -m <commit_message>`
  - `git rev-parse HEAD`
  - `git tag -a <tag_name> -m <tag_message>`
- `git rev-parse HEAD` is used only after successful commit to record commit SHA.
- Blocks all non-allowed git operations:
  - reset
  - checkout
  - clean
  - push
  - pull
  - fetch
  - merge
  - rebase
  - stash
  - amend
  - branch deletion
  - force operations
- Added conservative preflight checks:
  - repo path exists and is a directory
  - Prompt275 gate ready
  - compact non-empty commit message
  - safe non-empty tag name
  - non-empty changed files
  - changed file count limit, default 25
  - repo-local relative paths only
  - no absolute paths
  - no `..`
  - no `.git/`
  - no malformed or ambiguous paths
  - validation summary not missing/failing
  - `git status --short` contains expected changed files
  - `git status --short` has no extra changed files outside Prompt275 changed files
  - ambiguous status / rename / copy / unmerged entries are blocked
  - tag must not already exist
- Added execution order:
  1. `git add -- <changed_files...>`
  2. `git commit -m <commit_message>`
  3. `git rev-parse HEAD`
  4. `git tag -a <tag_name> -m <tag_message>`
  5. `git status --short`
- Added failure semantics:
  - git add failure: no commit/tag attempted
  - git commit failure: no tag attempted
  - commit success + tag failure: `commit_tag_execution_committed_tag_failed`
  - no rollback path
  - no reset/checkout/clean
- Added post-execution state:
  - `project_browser_autonomous_commit_tag_execution_post_git_status_short`
  - success remains success only if remaining changes do not include the expected committed file set
- Added normalized fields:
  - `project_browser_autonomous_commit_tag_execution_status`
  - `project_browser_autonomous_commit_tag_execution_next_action`
  - `project_browser_autonomous_commit_tag_execution_enabled`
  - `project_browser_autonomous_commit_tag_execution_execute_enabled`
  - `project_browser_autonomous_commit_tag_execution_commit_message`
  - `project_browser_autonomous_commit_tag_execution_tag_name`
  - `project_browser_autonomous_commit_tag_execution_changed_files`
  - `project_browser_autonomous_commit_tag_execution_commit_sha`
  - `project_browser_autonomous_commit_tag_execution_tag_created`
  - `project_browser_autonomous_commit_tag_execution_git_status_short`
  - `project_browser_autonomous_commit_tag_execution_post_git_status_short`
  - `project_browser_autonomous_commit_tag_execution_blocked_reason`
- Added status handling:
  - `commit_tag_execution_not_requested`
  - `commit_tag_execution_decision_only`
  - `commit_tag_execution_blocked_missing_gate`
  - `commit_tag_execution_blocked_preflight`
  - `commit_tag_execution_blocked_large_change`
  - `commit_tag_execution_blocked_unexpected_changes`
  - `commit_tag_execution_blocked_existing_tag`
  - `commit_tag_execution_blocked_git_failed`
  - `commit_tag_execution_committed_tag_failed`
  - `commit_tag_execution_committed_and_tagged`
- Exposes execution state in:
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
Prompt277 should add PR queue state management:
- detect `commit_tag_execution_committed_and_tagged`
- record commit SHA, tag name, changed files, and review summary
- mark the active local PR slice as committed
- prepare the next PR slice
- do not push, create PRs, merge, fetch, pull, rebase, or delete branches

## Not included
- No tests.
- No Playwright.
- No ChatGPT/OpenAI API calls.
- No CAPTCHA/Verify bypass.
- No cookie/token/session storage.
- No runner daemon/scheduler.
- No multi-task queue.
- No unbounded loop.
- No arbitrary shell/Codex execution path.
- No git reset/checkout/clean.
- No git push/pull/fetch/merge/rebase/stash/amend.
- No PR creation.
- No branch deletion.
- No duplicate-send path.
