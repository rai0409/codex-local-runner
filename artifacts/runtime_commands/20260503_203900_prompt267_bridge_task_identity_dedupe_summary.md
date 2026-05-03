# Prompt267 result: bridge task identity + dedupe state

## Single-task identity fields exposed
- `task_id`
- `request_fingerprint`
- `created_at`
- `attempt_count`
- `status` (`ready|in_progress|response_saved|blocked|consumed`)

`GET /next-task` remains backward compatible with:
- `has_task`
- `prompt`

## Dedupe behavior
- Auto-run dispatch now gates on both `task_id` and `request_fingerprint`.
- A task is not auto-dispatched again when server task status is:
  - `in_progress`
  - `response_saved`
  - `blocked`
  - `consumed`
- Reset endpoint (`BRIDGE_RESET_AUTORUN_STATE`) remains operator recovery only.

## Identity propagation
- `content.js` now relays `task_id` + `request_fingerprint` in:
  - `POST /status`
  - `POST /result`
  - `BRIDGE_RUN_RESULT` relay payload
