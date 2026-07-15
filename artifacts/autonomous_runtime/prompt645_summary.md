# Prompt645 — Project Intent Schema & Task Plan Model

**Status:** success
**Base:** `3170ddc` (tag `prompt644a-current-capability-acceptance`)

## What was built (container/model layer only)
Two new pure, offline, deterministic modules — no execution, no daemon queue, no
Codex, no network, no git, no enqueue:

- **`automation/orchestration/planned_runner/project_intent.py`** — Project Intent
  model: `project_id` (slug), `project_name`, `goal`, `success_criteria`,
  `constraints`, `allowed_task_kinds` (must be a subset of
  `task_spec.SUPPORTED_TASK_KINDS`), `safety_limits`
  (`max_tasks`/`max_cycles_per_task`/`max_total_seconds`, **hard-bounded by the
  daemon caps 5/2/1800**), `human_approval_policy` (`require_human_approval` +
  `approval_required_for` risk categories), `repo_target`, `completion_criteria`
  placeholder, and provenance/audit fields. Non-raising `validate_project_intent`
  + JSON serialization with exact round-trip.

- **`automation/orchestration/planned_runner/project_plan.py`** — Project Task Plan
  model embedding a validated intent + an ordered list of planned tasks
  (`task_id`, `kind`, `task_spec_payload` **or** `generated_task_spec_ref`,
  `depends_on`, `order`, `status`, `generated_task_spec_path`), `completion_criteria`
  placeholder, provenance. Validation rejects duplicate ids, dependency cycles,
  dangling/self deps, unsupported / not-allowed kinds, and task counts over
  `safety_limits.max_tasks`. Includes `planned_task_to_task_spec()` — a **pure
  offline** conversion to the daemon's task-spec dict shape (no I/O, no enqueue).

## Validation
- New tests `tests/test_project_intent_plan_model.py`: **17 OK** — valid/invalid
  intent (safe, non-raising), unknown allowed kind rejected, safety_limits bounded
  by daemon caps, intent round-trip; valid plan, kind-not-allowed, duplicate ids,
  dangling dep, dependency cycle, valid DAG, max_tasks bound, payload-or-ref
  required, plan round-trip, **backward-compatible task-spec conversion** (output
  accepted by `task_spec.validate_task_spec`), and **no-execution-side-effects**.
- Regression: **39 OK** total (with `test_daemon_queue`,
  `test_daemon_queue_targeted_fix_retry_integration`, `test_targeted_fix_retry`,
  `test_sandbox_commit_tag_gate`). No existing source modified — additive only.

## Boundaries respected
No enqueue · no Codex · no daemon-queue call · no planner/LLM decomposition · no
completion-gate/loop controller · no task-kind expansion · no network/git runtime.
Main repo safe; `artifacts/archive` and `handoff_reports` untouched.

## Result & next
The project-level data-model layer exists and is backward compatible with the
daemon's task-spec contract — unblocking the planner/orchestrator stack without
crossing any execution boundary.

**Next action:** `project_task_generator_from_intent`.

> All PASS conditions met → committed and tagged `prompt645-project-intent-schema-task-plan-model`.
