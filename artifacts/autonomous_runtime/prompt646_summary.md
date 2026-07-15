# Prompt646 — Project Task Generator From Intent

**Status:** success
**Base:** `8d46ca4` (tag `prompt645-project-intent-schema-task-plan-model`)

## What was built (generator layer only)
`automation/orchestration/planned_runner/project_task_generator.py` — a pure,
offline, **deterministic, non-LLM** generator:

`generate_project_task_plan(intent, task_descriptors, *, generated_at="")
-> {status, errors, warnings, plan}` (never raises).

- Validates the intent via `validate_project_intent`; invalid intent → `blocked`
  with errors and an empty plan.
- Builds tasks from **caller-supplied structured descriptors** (no free-text/LLM):
  add_function payloads from `intent.repo_target` + descriptor `target_file` /
  `function_name` / `expression` (+ optional verify_commands etc.).
- **Deterministic**: stable task_ids (`<project_id>-t<index>` or a sanitized
  descriptor id/name), `order` = index, deterministic dependency wiring; no
  Date.now/random (timestamp is an input).
- **Enforces** `allowed_task_kinds` and `safety_limits.max_tasks` (blocks on
  over-bound — no silent truncation); rejects unresolved/self deps and missing
  required fields safely.
- Assembles the plan and validates it with `validate_project_task_plan`; surfaces
  any plan errors. Backward compatible: `planned_task_to_task_spec` on a generated
  task is accepted by `validate_task_spec`.

## Validation
- New tests `tests/test_project_task_generator_from_intent.py`: **12 OK** — valid
  intent→valid plan, deterministic ids/order/deps, repeatable output,
  allowed_task_kinds enforced, max_tasks bound enforced, invalid intent safe-fail,
  empty descriptors blocked, missing add_function fields blocked, unresolved
  dependency blocked, valid DAG accepted, **backward-compatible task-spec
  conversion**, **no-execution-side-effects**.
- Regression: **39 OK** total (with `test_project_intent_plan_model`,
  `test_daemon_queue`, `test_targeted_fix_retry`). No existing source modified.

## Boundaries respected
No enqueue · no daemon-queue · no Codex · no LLM decomposition · no completion gate ·
no loop controller · no task-kind expansion · no network. Main repo safe;
`artifacts/archive` and `handoff_reports` untouched.

## Result & next
The intent→plan bridge exists, is deterministic, validated, and backward compatible —
unblocking automatic queue population.

**Next action:** `auto_queue_population_from_project_plan`.

> All PASS conditions met → committed and tagged `prompt646-project-task-generator-from-intent`.
