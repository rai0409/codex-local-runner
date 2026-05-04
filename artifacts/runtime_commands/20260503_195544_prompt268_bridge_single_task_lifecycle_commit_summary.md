# Prompt268 result: bridge single-task lifecycle hardening

## Scope
Modified:
- `scripts/chatgpt_bridge_server.py`

Added:
- `artifacts/runtime_commands/20260503_211500_prompt268_bridge_single_task_lifecycle_hardening.md`

## What changed
- Enforced explicit single-task lifecycle states:
  - `ready`
  - `in_progress`
  - `response_saved`
  - `blocked`
  - `consumed`
- Enforced allowed transitions:
  - `ready -> in_progress`
  - `ready -> blocked`
  - `in_progress -> response_saved`
  - `in_progress -> blocked`
  - `response_saved -> consumed`
- Invalid transitions are held at prior state and recorded as `task_transition_blocked`.
- Preserved `/next-task` compatibility:
  - `has_task`
  - `prompt`
- Preserved identity fields:
  - `task_id`
  - `request_fingerprint`
  - `created_at`
  - `attempt_count`
  - `status`
- Stabilized `attempt_count`:
  - increments only on accepted `ready -> in_progress`
  - avoids repeated `running/task_fetched` double increments
- Removed double-write behavior for `/status`.
- Added `POST /consume-result`:
  - marks current `response_saved` task as `consumed`
  - does not fetch/send prompts
- Added `POST /task-reset`:
  - resets lifecycle state for operator recovery
  - does not fetch/send prompts
- Added concise runtime note documenting lifecycle and new endpoints.

## Validation
- `python -m py_compile scripts/chatgpt_bridge_server.py` passed.

## Manual smoke
- Not executed in this run.

## Known follow-up
Prompt269 should assimilate saved Chrome Runner Bridge responses into runner next actions:
- detect `response_saved`
- read `response.md` boundedly
- classify into implementation/review/fix/completion/manual-review
- mark consumed after successful assimilation

## Not included
- No tests.
- No Playwright.
- No ChatGPT API calls.
- No CAPTCHA/Verify bypass.
- No cookie/token/session storage.
- No runner daemon/scheduler.
- No multi-task queue.
- No autonomous loop.
- No duplicate-send path.
- No git mutation during implementation.
