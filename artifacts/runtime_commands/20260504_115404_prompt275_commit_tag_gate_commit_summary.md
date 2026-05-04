# Prompt275 result: commit/tag readiness gate

## Scope
Modified:
- `automation/orchestration/planned_execution_runner.py`

## What changed
- Added `_build_project_browser_autonomous_commit_tag_gate_state(...)`.
- Consumes Prompt274 ChatGPT diff review decision state.
- Consumes Prompt272 Codex capture evidence state.
- Added default-off control:
  - `project_browser_autonomous_commit_tag_gate_enabled`
- Proceeds only when Prompt274 approval is valid:
  - `project_browser_autonomous_chatgpt_diff_review_decision_status=chatgpt_diff_review_decision_approved_for_commit_gate`
  - `project_browser_autonomous_chatgpt_diff_review_decision=approve`
  - `project_browser_autonomous_chatgpt_diff_review_decision_next_action=prepare_commit_or_pr_gate`
- Gate readiness requires:
  - gate enabled
  - confidence >= 0.80
  - risk low or medium
  - no blocking issues
  - commit_recommendation=true
  - changed files non-empty
  - validation not failing
  - no unsafe changed paths
- Blocks unsafe changed paths:
  - absolute paths
  - `..` traversal
  - `.git/` paths
  - malformed or repo-external style paths
- Blocks validation failure:
  - `error`
  - `failed`
  - `failure`
  - `diff_check_has_errors`
- Blocks missing/unavailable validation unless an existing allow-missing flag is explicitly set.
- Generates deterministic metadata only:
  - commit message candidate
  - tag name candidate
  - readiness summary
- Added normalized fields:
  - `project_browser_autonomous_commit_tag_gate_status`
  - `project_browser_autonomous_commit_tag_gate_next_action`
  - `project_browser_autonomous_commit_tag_gate_enabled`
  - `project_browser_autonomous_commit_tag_gate_ready`
  - `project_browser_autonomous_commit_tag_gate_commit_message`
  - `project_browser_autonomous_commit_tag_gate_tag_name`
  - `project_browser_autonomous_commit_tag_gate_changed_files`
  - `project_browser_autonomous_commit_tag_gate_validation_summary`
  - `project_browser_autonomous_commit_tag_gate_review_summary`
  - `project_browser_autonomous_commit_tag_gate_blocked_reason`
  - `project_browser_autonomous_commit_tag_gate_fix_recommendations`
- Added status handling:
  - `commit_tag_gate_not_requested`
  - `commit_tag_gate_blocked_missing_approval`
  - `commit_tag_gate_blocked_policy`
  - `commit_tag_gate_blocked_validation`
  - `commit_tag_gate_blocked_unsafe_paths`
  - `commit_tag_gate_ready`
- Adds compact fix recommendations when blocked.
- Exposes commit/tag gate state in:
  - compact planning summary
  - supporting truth refs
  - final approved restart payload

## Validation
- `python -m py_compile automation/orchestration/planned_execution_runner.py` passed.

## Manual smoke
- Not executed in this run.

## Known follow-up
Prompt276 should add explicit local commit/tag execution:
- require `commit_tag_gate_ready`
- require explicit execution enable
- verify git status / changed files / tag uniqueness
- run local `git add`, `git commit`, and `git tag` only when all checks pass
- no push, PR, merge, branch cleanup, or remote operation

## Not included
- No tests.
- No Playwright.
- No ChatGPT/OpenAI API calls.
- No CAPTCHA/Verify bypass.
- No cookie/token/session storage.
- No runner daemon/scheduler.
- No multi-task queue.
- No unbounded loop.
- No new shell/Codex execution path.
- No git reset/checkout/clean.
- No commit/tag/push/PR/merge automation.
- No duplicate-send path.
- No git mutation during implementation.
