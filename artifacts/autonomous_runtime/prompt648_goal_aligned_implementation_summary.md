# Prompt648 — Project Progress / Completion Gate

**Status:** success · **Base:** 1dae3f7

`project_completion_gate.py` → `evaluate_project_completion(plan, task_results, *, completion_criteria, required_task_ids)`: pure/offline, never raises. Maps per-task status (results override else plan status) to done/failed/blocked/pending/unknown; returns status `complete|in_progress|blocked|failed|invalid` with counts/task_states/reasons. **Never marks complete while a required task is failed/blocked/pending/unknown.** Criteria: `all_tasks_done`, `no_failed_required_tasks`.

Tests: 10 OK (gate) + 59 OK regression. No daemon/Codex/queue/network; additive only; main repo safe.

Next: `project_level_iterate_until_done_controller`.
