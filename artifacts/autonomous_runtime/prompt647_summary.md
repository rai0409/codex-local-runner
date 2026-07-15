# Prompt647 — Auto Queue Population From Project Plan

**Status:** success
**Base:** `894fac8` (tag `prompt646-project-task-generator-from-intent`)

## What was built
`automation/orchestration/planned_runner/project_queue_population.py` — a pure,
offline, deterministic layer:

`populate_queue_from_plan(plan, output_queue_dir, *, repo_path_override=None,
create_dirs=True) -> {status, errors, warnings, output_dir, written_files,
task_count}` (never raises).

- Validates the plan via `validate_project_task_plan`; invalid → `blocked`, no files.
- **Requires an explicit output queue dir** — never falls back to a live/default queue.
- Computes a **deterministic topological order** (Kahn, tie-break by order then
  task_id) and writes `pending/<NNN>-<task_id>.json` so a sequential daemon claims
  tasks in dependency order; the clean `task_id` is preserved inside each spec.
- Converts via `planned_task_to_task_spec` (optional `repo_path_override`); written
  specs are `task_spec.validate_task_spec`-compatible (repo existence is execution-time).
- Emits a **deterministic warning** when the plan has dependency edges (the daemon
  queue has no dependency primitive; deps are represented as processing order only).
- Deterministic output (sorted-keys JSON + index-prefixed filenames); no daemon/Codex/
  network/git; no live-queue mutation.

## Validation
- New tests `tests/test_project_queue_population_from_plan.py`: **10 OK** — valid plan
  populates pending files; written specs pass `validate_task_spec` (repo_path
  override); invalid plan safe-fail (no files); explicit output dir required;
  deterministic filenames+content+order; topological order respects deps; dependency
  warning emitted / absent when no deps; create_dirs=False guard; no side effects.
- Regression: **49 OK** total (with model, generator, daemon_queue, targeted_fix
  suites). No existing source modified — additive only.

## Boundaries respected
No daemon run · no Codex · no task execution · no planner/LLM · no completion gate ·
no loop controller · no task-kind expansion · no live/default queue mutation · no
network/git. Main repo safe; `artifacts/archive` and `handoff_reports` untouched.

## Result & next
The bridge `ProjectTaskPlan → explicit daemon queue input files` now exists,
deterministic and dependency-ordered.

**Next action:** `project_progress_and_completion_gate`.
