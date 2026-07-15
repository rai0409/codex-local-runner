PROMPT647_AUTO_QUEUE_POPULATION_FROM_PROJECT_PLAN

Repository:
- /home/rai/codex-local-runner

## Goal
Create a minimal, deterministic, local queue-population layer that takes a validated
ProjectTaskPlan and materializes daemon-queue-compatible task spec files into an
EXPLICIT caller-provided output queue directory, in dependency-respecting
(topological) order — WITHOUT running the daemon, Codex, or any task.

This is an EXECUTION task (implement + test + validate + report). It is the safe
bridge from a generated ProjectTaskPlan to daemon queue input files.

## Current state (confirmed)
- Branch: local/prompt299-one-cycle-controller-v1
- HEAD: 894fac8, tag: prompt646-project-task-generator-from-intent
- Available building blocks (all PASS):
  - `project_intent.py` (validate_project_intent)
  - `project_plan.py`: `validate_project_task_plan(payload) -> (plan, errors)`;
    planned task entry has `task_id`, `kind`, `task_spec_payload` OR
    `generated_task_spec_ref`, `depends_on`, `order`, `status`,
    `generated_task_spec_path`; `planned_task_to_task_spec(task, overrides=None)`
    (pure offline conversion to daemon task-spec dict).
  - `project_task_generator.py`: `generate_project_task_plan(...)`.
  - `task_spec.py`: `validate_task_spec(payload) -> (spec, errors)`; an add_function
    spec needs task_id, kind, repo_path (existing dir at EXECUTION time), target_file,
    function_name, expression (+ optional verify_commands / expected_unmodified_files
    / allow_extra_files).
- Daemon queue contract (`daemon_queue.py`):
  - `ensure_queue_dirs(queue_dir)` creates pending/running/done/failed.
  - `enqueue_task(queue_dir, spec)` writes `pending/<task_id>.json`.
  - `claim_next_task` processes `pending/*.json` in **sorted filename order, one at a
    time** (FIFO by lexical filename).
  - There is **NO dependency field**: the queue cannot hard-enforce dependencies; it
    only processes pending tasks sequentially in sorted filename order.

## Root gap addressed
Nothing turns a ProjectTaskPlan into daemon queue input files. This prompt adds ONLY
that population layer. Because the daemon queue has no dependency primitive,
dependencies are represented as **processing order** (topological order encoded in
filenames) for a sequential daemon, with a deterministic WARNING that the queue does
not hard-enforce dependencies.

## Scope (queue-population layer ONLY)
Implement:
- accept a ProjectTaskPlan (dict or normalized) and validate it via
  `validate_project_task_plan`; reject invalid plans safely (never raise)
- require an EXPLICIT output queue directory (no default/live queue)
- compute a deterministic topological order of the plan's tasks (stable tie-break by
  `order` then `task_id`); detect/skip is unnecessary since the plan validator already
  rejects cycles, but re-guard defensively
- convert each planned task to a daemon task spec via `planned_task_to_task_spec`
  (optionally with a caller-supplied repo_path override)
- materialize queue files deterministically into `<output_dir>/pending/` using an
  order-encoding filename (e.g. `<NNN>-<task_id>.json`, NNN = zero-padded topological
  index) so a sequential daemon claims them in dependency order; the spec INSIDE keeps
  the clean `task_id` (so commit/tag naming is unaffected)
- return a structured population result: status, errors, warnings, output_dir,
  written_files (ordered), task_count
- emit a deterministic warning when the plan contains any `depends_on` edges, stating
  dependencies are represented as queue ordering only (not hard-enforced)
- tests using tmpdirs only
- report/summary

## Required behavior
Provide a primary function, e.g.:
`populate_queue_from_plan(plan, output_queue_dir, *, repo_path_override=None,
create_dirs=True) -> dict` returning
`{"status": "success"|"blocked", "errors": [...], "warnings": [...],
"output_dir": "...", "written_files": [...], "task_count": N}` — never raises.

It must:
- validate the plan with `validate_project_task_plan`; on errors -> status="blocked",
  errors populated, NO files written
- require `output_queue_dir` to be a non-empty explicit path; reject empty/missing
  with status="blocked" (do NOT fall back to any default/live queue)
- create the queue dirs only under the explicit caller-provided path (via
  `ensure_queue_dirs`) when `create_dirs` is true; otherwise require it to exist
- write one `pending/<NNN>-<task_id>.json` per task, in topological order, content =
  the daemon task spec (from `planned_task_to_task_spec`, with optional
  `repo_path_override`), serialized deterministically (sorted keys) so identical
  inputs produce byte-identical files
- preserve task ids (inside the spec) and a deterministic, dependency-consistent order
- be DETERMINISTIC: same (plan, output_dir, override) -> identical filenames + content
- run NO daemon, NO Codex, NO task execution, NO network, NO git, and NOT mutate any
  live/default queue
- the written specs must be structurally compatible with `task_spec.validate_task_spec`
  (i.e. given a real repo_path, validation passes); the layer itself does NOT require
  repo_path to exist (that is an execution-time check)

## Integration boundary (hard — do NOT cross)
- Do NOT run the daemon queue runner / claim / complete tasks.
- Do NOT run Codex / live gate / autonomous loop / targeted-fix retry.
- Do NOT execute tasks.
- Do NOT implement planner / LLM decomposition.
- Do NOT implement a project completion-gate evaluator.
- Do NOT implement a project-level iterate-until-done loop controller.
- Do NOT expand `SUPPORTED_TASK_KINDS`.
- Do NOT write to any live/default queue; only the explicit caller-provided dir
  (tests use tmpdirs).
- Additive only: do NOT change daemon_queue.py / task_spec.py / project_* behavior
  (importing them is fine; reusing ensure_queue_dirs is fine).

## Likely files to create/modify (decide exact set during implementation)
- automation/orchestration/planned_runner/project_queue_population.py (new)
- tests/test_project_queue_population_from_plan.py (new)
- artifacts/autonomous_runtime/prompt647_report.json, prompt647_summary.md
- optional example fixture under tests/ (NOT under artifacts/archive)
- touch existing source only if strictly necessary (e.g. a re-export); keep additive.

## Required tests (python -m unittest, tmpdirs only)
tests/test_project_queue_population_from_plan.py must cover:
- valid plan populates `pending/` files into a tmpdir; task_count matches; status success
- written queue task files pass `task_spec.validate_task_spec` (use a /tmp existing
  dir as repo_path via override) with no errors
- invalid plan fails safely (status blocked, errors, NO files written, no raise)
- explicit output directory required (empty/missing -> blocked; no live-queue fallback)
- deterministic filenames + byte-identical content + order across repeated runs
- topological order: a plan whose tasks depend on earlier tasks yields filenames whose
  sorted order respects dependencies; task ids preserved inside the specs
- dependency behavior explicit: a plan with depends_on edges produces a deterministic
  WARNING that the daemon queue represents deps as ordering only (not hard-enforced)
- no daemon execution / Codex / network / git side effects (assert only the explicit
  tmpdir is written; cwd unchanged)
- artifacts/archive and handoff_reports untouched
- existing Prompt645 model tests still pass (tests.test_project_intent_plan_model)
- existing Prompt646 generator tests still pass (tests.test_project_task_generator_from_intent)
- cheap regression: tests.test_daemon_queue, tests.test_targeted_fix_retry

## Safety constraints (hard)
- Side effects limited to the EXPLICIT caller-provided output dir (tmpdirs in tests).
- Deterministic (no Date.now()/random; serialize with sorted keys).
- No network/Codex/daemon/queue-run/git; no live/default queue mutation.
- No modification of artifacts/archive. No modification of handoff_reports.
- Additive only; respect existing daemon-queue and task_spec contracts.

## Report requirements
Write:
- artifacts/autonomous_runtime/prompt647_report.json
- artifacts/autonomous_runtime/prompt647_summary.md
Required report fields:
- prompt647_status
- prompt647_base_commit
- prompt647_base_tags_at_head
- prompt647_queue_population_created
- prompt647_plan_to_queue_conversion_created
- prompt647_queue_files_validation_passed
- prompt647_deterministic_population_tests_passed
- prompt647_topological_order_preserved
- prompt647_dependency_representation_explicit
- prompt647_explicit_output_dir_required
- prompt647_no_live_queue_mutation
- prompt647_no_execution_side_effects
- prompt647_existing_model_tests_passed
- prompt647_existing_generator_tests_passed
- prompt647_existing_runtime_regression_tests_passed
- prompt647_files_modified
- prompt647_main_repo_safe
- prompt647_archive_touched
- prompt647_handoff_reports_touched
- prompt647_final_decision
- prompt647_next_action

## Final stdout contract
Print only:
prompt647_status=<success|partial|blocked>
prompt647_queue_population_created=<true|false>
prompt647_plan_to_queue_conversion_created=<true|false>
prompt647_queue_files_validation_passed=<true|false>
prompt647_deterministic_population_tests_passed=<true|false>
prompt647_no_execution_side_effects=<true|false>
prompt647_existing_model_tests_passed=<true|false>
prompt647_existing_generator_tests_passed=<true|false>
prompt647_existing_runtime_regression_tests_passed=<true|false>
prompt647_files_modified=<list>
prompt647_commit=<commit_hash_if_committed|none>
prompt647_tag=<tag_if_created|none>
prompt647_report_path=artifacts/autonomous_runtime/prompt647_report.json
prompt647_summary_path=artifacts/autonomous_runtime/prompt647_summary.md
prompt647_next_action=<project_progress_and_completion_gate|fix_auto_queue_population|manual_review_required>

## Decision rules
- If population is created, writes valid daemon-queue-compatible files in deterministic
  topological order into an explicit dir, requires the explicit dir (no live-queue
  fallback), represents dependencies explicitly (ordering + warning), the written
  specs pass task_spec validation, there are NO execution side effects, the existing
  model/generator/regression tests pass, and main repo is safe:
    prompt647_status=success
    prompt647_next_action=project_progress_and_completion_gate
  (Commit + tag prompt647-auto-queue-population-from-project-plan ONLY if ALL PASS.)
- If population or a population test fails / files invalid:
    prompt647_status=partial|blocked
    prompt647_next_action=fix_auto_queue_population
- If existing tests regress, a live/default queue is mutated, or main repo safety is
  violated:
    prompt647_status=blocked
    prompt647_next_action=manual_review_required

## Commit/tag policy
Commit/tag ONLY if all PASS conditions are met. Stage only the new population source,
the new test, the prompt647 report/summary (+ optional fixture and this prompt file).
Do NOT stage artifacts/archive or handoff_reports.
Suggested commit message: "prompt647 auto queue population from project plan"
Suggested tag: prompt647-auto-queue-population-from-project-plan

## Out of scope (do NOT do in Prompt647)
- Running the daemon / Codex / executing tasks
- Planner / LLM decomposition
- Project completion-gate evaluation or iterate-until-done loop controller
- Broad task-kind expansion
- Live/default queue mutation; any network/git runtime
