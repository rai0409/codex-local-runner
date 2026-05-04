# Prompt273 result: ChatGPT diff review request generation

## Scope
Modified:
- `automation/orchestration/planned_execution_runner.py`

## What changed
- Added `_build_project_browser_autonomous_chatgpt_diff_review_request_state(...)`.
- Consumes Prompt272 Codex capture gate state.
- Proceeds only when:
  - `project_browser_autonomous_codex_capture_gate_status=codex_capture_gate_captured`
- Added default-off controls:
  - `project_browser_autonomous_chatgpt_diff_review_request_enabled`
  - `project_browser_autonomous_chatgpt_diff_review_request_write_enabled`
- Builds a bounded compact ChatGPT diff review request from:
  - changed files
  - diff summary
  - validation summary
  - Codex output summary
  - capture artifact paths
  - prompt kind
  - prompt fingerprint
- Does not include unbounded/full patch content.
- Requires structured ChatGPT review output:
  - `decision`
  - `confidence`
  - `risk`
  - `blocking_issues`
  - `fix_prompt`
  - `revert_reason`
  - `commit_recommendation`
  - `summary`
- Adds conservative review policy:
  - approve only if scope is correct and validation is acceptable
  - fix if direction is right but corrections are needed
  - revert if unsafe, wrong-scope, or worse than baseline
  - manual_review if unclear or high-risk
  - no commit recommendation for high risk or blocking issues
- Added normalized request state fields:
  - `project_browser_autonomous_chatgpt_diff_review_request_status`
  - `project_browser_autonomous_chatgpt_diff_review_request_next_action`
  - `project_browser_autonomous_chatgpt_diff_review_request_enabled`
  - `project_browser_autonomous_chatgpt_diff_review_request_write_enabled`
  - `project_browser_autonomous_chatgpt_diff_review_request_prompt`
  - `project_browser_autonomous_chatgpt_diff_review_request_prompt_fingerprint`
  - `project_browser_autonomous_chatgpt_diff_review_request_changed_files`
  - `project_browser_autonomous_chatgpt_diff_review_request_blocked_reason`
- Added status handling:
  - `chatgpt_diff_review_request_not_requested`
  - `chatgpt_diff_review_request_decision_only`
  - `chatgpt_diff_review_request_ready`
  - `chatgpt_diff_review_request_written`
  - `chatgpt_diff_review_request_blocked_missing_capture`
  - `chatgpt_diff_review_request_blocked_empty_review_prompt`
  - `chatgpt_diff_review_request_blocked_duplicate_prompt`
  - `chatgpt_diff_review_request_blocked_write_failed`
- `enabled=true` + `write_enabled=false` exposes decision/prompt only.
- `enabled=true` + `write_enabled=true` writes only to:
  - `/tmp/codex-local-runner-chatgpt-bridge/request.md`
- Uses duplicate prompt fingerprint blocking.
- Clears stale bridge `response.md` and `status.json` using existing safe bridge cleanup pattern.
- Does not trigger Chrome auto-run directly.
- Does not parse or branch on review result.
- Exposes request state in:
  - compact planning summary
  - supporting truth refs
  - final approved restart payload

## Validation
- `python -m py_compile automation/orchestration/planned_execution_runner.py` passed.

## Manual smoke
- Not executed in this run.

## Known follow-up
Prompt274 should parse/assimilate ChatGPT diff review response and branch:
- approve -> commit/tag gate readiness
- fix -> route fix prompt
- revert -> generate revert plan
- manual_review -> stop

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
- No commit/tag/PR/merge automation.
- No review-result branching.
- No duplicate-send path.
- No git mutation during implementation.
