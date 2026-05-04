# Prompt274 result: ChatGPT diff review decision branch

## Scope
Modified:
- `automation/orchestration/planned_execution_runner.py`

## What changed
- Added `_build_project_browser_autonomous_chatgpt_diff_review_decision_state(...)`.
- Reads saved ChatGPT review responses from:
  - `/tmp/codex-local-runner-chatgpt-bridge/status.json`
  - `/tmp/codex-local-runner-chatgpt-bridge/response.md`
- Branches only when bridge lifecycle resolves to `response_saved`.
- Blocks missing / empty / transient / read-error / in-progress / blocked / consumed / not-saved responses.
- Added bounded reads:
  - `status.json`: 8192 bytes
  - `response.md`: 32768 bytes
- Preserves response metadata:
  - `project_browser_autonomous_chatgpt_diff_review_response_status`
  - `project_browser_autonomous_chatgpt_diff_review_response_size_bytes`
  - `project_browser_autonomous_chatgpt_diff_review_response_preview`
- Parses structured review response conservatively:
  - JSON object first
  - fenced JSON / bounded object extraction
  - bounded fallback extraction for expected fields
- Extracts:
  - `decision`
  - `confidence`
  - `risk`
  - `blocking_issues`
  - `fix_prompt`
  - `revert_reason`
  - `commit_recommendation`
  - `summary`
- Supports decisions:
  - `approve`
  - `fix`
  - `revert`
  - `manual_review`
- Approve policy:
  - `confidence >= 0.80`
  - `risk in {low, medium}`
  - `blocking_issues` empty
  - `commit_recommendation=true`
- Fix policy:
  - requires non-empty `fix_prompt`
  - blocks high-risk / blocking issues / low confidence
  - blocks unsafe fix prompts
  - blocks duplicate fix prompt fingerprints
  - writes approved fix prompt only to:
    - `/tmp/codex-local-runner-decision/generated_fix_prompt.txt`
- Revert policy:
  - requires non-empty `revert_reason`
  - generates revert plan only
  - does not delete files
  - does not mutate working tree
  - does not run git reset / checkout / clean
- Approve behavior:
  - exposes commit/PR gate readiness only
  - does not commit, tag, push, create PR, or merge
- Added normalized fields:
  - `project_browser_autonomous_chatgpt_diff_review_decision_status`
  - `project_browser_autonomous_chatgpt_diff_review_decision_next_action`
  - `project_browser_autonomous_chatgpt_diff_review_decision`
  - `project_browser_autonomous_chatgpt_diff_review_confidence`
  - `project_browser_autonomous_chatgpt_diff_review_risk`
  - `project_browser_autonomous_chatgpt_diff_review_blocking_issues`
  - `project_browser_autonomous_chatgpt_diff_review_fix_prompt`
  - `project_browser_autonomous_chatgpt_diff_review_fix_prompt_fingerprint`
  - `project_browser_autonomous_chatgpt_diff_review_revert_reason`
  - `project_browser_autonomous_chatgpt_diff_review_revert_plan`
  - `project_browser_autonomous_chatgpt_diff_review_commit_recommendation`
  - `project_browser_autonomous_chatgpt_diff_review_summary`
  - `project_browser_autonomous_chatgpt_diff_review_blocked_reason`
  - `project_browser_autonomous_chatgpt_diff_review_routed`
- Added status handling:
  - `chatgpt_diff_review_decision_not_applicable`
  - `chatgpt_diff_review_decision_blocked_missing_response`
  - `chatgpt_diff_review_decision_blocked_parse_failed`
  - `chatgpt_diff_review_decision_manual_review`
  - `chatgpt_diff_review_decision_approved_for_commit_gate`
  - `chatgpt_diff_review_decision_fix_routed`
  - `chatgpt_diff_review_decision_revert_plan_ready`
  - `chatgpt_diff_review_decision_blocked_duplicate_fix_prompt`
  - `chatgpt_diff_review_decision_blocked_unsafe_fix_prompt`
- Exposes decision state in:
  - compact planning summary
  - supporting truth refs
  - final approved restart payload

## Validation
- `python -m py_compile automation/orchestration/planned_execution_runner.py` passed.

## Manual smoke
- Not executed in this run.

## Known follow-up
Prompt275 should add commit/tag gate readiness:
- require `chatgpt_diff_review_decision_status=chatgpt_diff_review_decision_approved_for_commit_gate`
- verify review decision / confidence / risk / blocking issues / commit recommendation
- use captured changed files and validation summary
- generate commit message and tag name candidates
- do not commit or tag yet

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
- No commit/tag/PR/merge automation.
- No duplicate-send path.
- No git mutation during implementation.
