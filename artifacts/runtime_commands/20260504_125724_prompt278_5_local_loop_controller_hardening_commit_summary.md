# Prompt278.5 result: local loop controller hardening

## Scope
Modified:
- `automation/orchestration/planned_execution_runner.py`

## What changed
- Hardened `_build_project_browser_autonomous_local_loop_state(...)`.
- Adjusted local loop routing priority to prefer PR queue state before raw commit/tag execution:
  - manual/blocking
  - `pr_queue_state_project_complete`
  - `pr_queue_state_updated` with `next_pr_index >= 0`
  - revert
  - fix
  - approve -> commit/tag gate
  - commit/tag execution update only when queue does not already reflect the commit result
  - implementation prompt ready
  - blocked no-next-step
- Added queue-reflection guard:
  - compares `project_browser_autonomous_commit_tag_execution_commit_sha` against:
    - `project_browser_autonomous_pr_queue_state_completed_commit_sha`
    - active queue item `commit_sha`
  - prevents re-routing to `update_pr_queue_or_prepare_next_pr` when already reflected.
- Made next PR prompt lookup order explicit:
  - `prompt`
  - `prompt_text`
  - `implementation_prompt`
  - `pr_prompt`
- If next PR prompt text is missing:
  - generates bounded single-item ChatGPT request only
  - does not invent a full roadmap
- Hardened local prompt writes:
  - `/tmp/codex-local-runner-decision/generated_next_prompt.txt`
  - `/tmp/codex-local-runner-decision/generated_fix_prompt.txt`
- Local prompt writes now enforce:
  - non-empty prompt
  - bounded prompt size
  - symlink/not-file/parent checks
  - duplicate selected-step fingerprint blocking before write
- Hardened bridge request write for next-PR prompt request:
  - `/tmp/codex-local-runner-chatgpt-bridge/request.md`
  - bounded prompt-only write
  - duplicate fingerprint blocking
  - stale `response.md` / `status.json` cleanup using safe checks
  - temp write + `os.replace`
  - no Chrome auto-run trigger
- Hardened iteration/fingerprint continuity:
  - route write success increments iteration exactly by +1
  - no write means no iteration increment
  - duplicate selected-step fingerprint blocks with:
    - `local_loop_blocked_duplicate_step`
    - `manual_review_required`
- Preserved Prompt278 status taxonomy and normalized field names.

## Validation
- `python -m py_compile automation/orchestration/planned_execution_runner.py` passed.

## Manual smoke
- Not executed in this run.

## Git mutation during implementation
- None.

## Known follow-up
Prompt279 should add an existing Codex execution connector:
- consume local loop `run_codex_implementation` / `run_codex_fix`
- require Codex execution gate readiness
- use only existing safe Codex/local runner route if available
- default-off / execute-off
- run at most one Codex step when explicitly enabled
- no arbitrary shell executor
- no unbounded loop
- no commit/tag/push/PR/merge

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
