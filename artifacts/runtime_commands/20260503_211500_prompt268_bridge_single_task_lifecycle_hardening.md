# Prompt268 result: single-task lifecycle hardening

## Lifecycle states
- `ready`
- `in_progress`
- `response_saved`
- `blocked`
- `consumed`

## Allowed transitions
- `ready -> in_progress`
- `ready -> blocked`
- `in_progress -> response_saved`
- `in_progress -> blocked`
- `response_saved -> consumed`

Invalid transitions are preserved at the prior task state and recorded in `task_transition_blocked`.

## Compatibility
`GET /next-task` still returns:
- `has_task`
- `prompt`

And now consistently includes:
- `task_id`
- `request_fingerprint`
- `created_at`
- `attempt_count`
- `status`

## New minimal controls
- `POST /consume-result`
  - marks current task as `consumed` when transition is valid
  - does not delete `request.md` or `response.md`
- `POST /task-reset`
  - resets lifecycle state for operator recovery only
  - does not fetch/send prompts
