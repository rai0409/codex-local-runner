PROMPT646_PROJECT_TASK_GENERATOR_FROM_INTENT

Repository:
- /home/rai/codex-local-runner

## Goal
Create a minimal, deterministic, local (non-LLM) **project task generator** that
takes a validated ProjectIntent plus structured task descriptors and produces a
bounded ProjectTaskPlan that passes the Prompt645 model validators and is backward
compatible with the daemon's task-spec contract. This is the safe bridge from a
project intent to an executable-later task plan. It performs NO execution, NO
enqueue, NO Codex, NO LLM decomposition.

This is an EXECUTION task (implement + test + validate + report). Pure, offline,
deterministic.

## Current state (confirmed)
- Branch: local/prompt299-one-cycle-controller-v1
- HEAD: 8d46ca4, tag: prompt645-project-intent-schema-task-plan-model
- Prompt645 delivered the model layer (all PASS):
  - `automation/orchestration/planned_runner/project_intent.py`
    - `validate_project_intent(payload) -> (intent, errors)` (non-raising)
    - intent fields incl. `allowed_task_kinds`, `safety_limits.max_tasks`,
      `repo_target`, `human_approval_policy`, provenance
    - `project_intent_to_json` / `project_intent_from_json` / `load_project_intent`
    - caps: `DAEMON_MAX_JOBS_CAP=5`, `DAEMON_MAX_CYCLES_CAP=2`, `DAEMON_MAX_SECONDS_TOTAL_CAP=1800`
  - `automation/orchestration/planned_runner/project_plan.py`
    - `validate_project_task_plan(payload) -> (plan, errors)` (non-raising;
      rejects duplicate ids, dependency cycles, dangling/self deps, not-allowed
      kinds, task count > intent.safety_limits.max_tasks)
    - planned task entry: `task_id`, `kind`, `task_spec_payload` OR
      `generated_task_spec_ref`, `depends_on`, `order`, `status` (in
      `PLANNED_TASK_STATUSES`), `generated_task_spec_path`
    - `planned_task_to_task_spec(task, overrides=None)` pure offline conversion
    - `project_plan_to_json` / `project_plan_from_json` / `load_project_task_plan`
- `task_spec.SUPPORTED_TASK_KINDS = ("add_function",)`; an add_function task spec
  needs task_id, kind, repo_path (existing dir at execution time), target_file
  (repo-relative, no '..'), function_name (identifier), expression, optional
  verify_commands / expected_unmodified_files / allow_extra_files.

## Root gap addressed
There is no component that turns a ProjectIntent into a ProjectTaskPlan. Every
higher layer (queue population, completion gate, auto loop) needs a deterministic,
safe generator first. This prompt adds ONLY that generator. It deliberately does
NOT use an LLM — generation is rule/template-based over caller-provided structured
descriptors, so it is fully deterministic and testable. (A real LLM planner is a
later prompt.)

## Scope (generator layer ONLY)
Implement:
- input validation (delegate to `validate_project_intent`; reject invalid intents safely)
- deterministic ProjectTaskPlan generation from (intent, task_descriptors)
- bounded generation honoring `intent.safety_limits.max_tasks`
- `allowed_task_kinds` filtering/enforcement
- simple template/rule-based task creation (no LLM)
- deterministic task_id / order assignment and dependency wiring
- validation of the generated plan via `validate_project_task_plan`
- a structured generation result (status, errors, warnings, plan)
- JSON + report/summary support
- tests

## Required behavior
Provide a primary function, e.g.:
`generate_project_task_plan(intent, task_descriptors, *, generated_at="") -> dict`
returning a structured result:
`{"status": "success"|"blocked", "errors": [...], "warnings": [...], "plan": {...}}`.

It must:
- accept an intent as a dict or already-normalized intent; validate it via
  `validate_project_intent`. If the intent is invalid, return status="blocked" with
  the intent errors and NO plan (or an empty plan) — never raise.
- accept `task_descriptors`: an explicit, structured, caller-provided list. Each
  descriptor is the deterministic source of one task (NO free-text decomposition).
  A descriptor for the add_function kind carries at minimum: `target_file`,
  `function_name`, `expression`, optional `verify_commands`,
  optional `expected_unmodified_files`, optional `depends_on` (referring to other
  descriptors by their index or a descriptor-supplied `name`/`task_id`),
  optional `kind` (defaults to the intent's first allowed kind).
- enforce `kind in intent.allowed_task_kinds`; descriptors with a disallowed/unknown
  kind are rejected safely (status="blocked" with a clear error), never crash.
- enforce `len(task_descriptors) <= intent.safety_limits.max_tasks`; if exceeded,
  return status="blocked" with a bound error (do NOT silently truncate; a `warnings`
  channel may note near-bound counts).
- produce DETERMINISTIC output for the same inputs: stable task_ids (e.g. a slug
  derived from `intent.project_id` + zero-padded index, or a sanitized
  descriptor-provided id), stable `order` (descriptor index), and stable dependency
  wiring. No Date.now()/random inside generation (timestamps are inputs).
- build each planned task with a `task_spec_payload` that is add_function-compatible:
  set `repo_path` from `intent.repo_target` (recorded as-is; existence is an
  execution-time concern, NOT checked here), plus the descriptor's target_file /
  function_name / expression / verify_commands. When a descriptor cannot form a full
  payload, emit a `generated_task_spec_ref` stub so the plan still validates.
- assemble a ProjectTaskPlan dict (embedding the validated intent) and validate it
  with `validate_project_task_plan`; surface any plan errors in the result and set
  status="blocked" if the generated plan is invalid.
- guarantee `planned_task_to_task_spec(task, overrides={"repo_path": <existing dir>})`
  on a generated task is accepted by `task_spec.validate_task_spec` (backward compat).
- perform NO queue insertion, NO daemon execution, NO Codex.

## Integration boundary (hard — do NOT cross)
- Do NOT enqueue tasks / call daemon_queue.
- Do NOT run the daemon queue runner / Codex / live gate / autonomous loop.
- Do NOT implement LLM decomposition or any network call.
- Do NOT implement a project completion-gate evaluator.
- Do NOT implement a project-level iterate-until-done loop controller.
- Do NOT expand `SUPPORTED_TASK_KINDS` or add new task kinds.
- Additive only: do NOT change project_intent.py / project_plan.py / task_spec.py /
  daemon behavior (importing them is fine).

## Likely files to create/modify (decide exact set during implementation)
- automation/orchestration/planned_runner/project_task_generator.py (new)
- tests/test_project_task_generator_from_intent.py (new)
- artifacts/autonomous_runtime/prompt646_report.json, prompt646_summary.md
- optional example fixture under tests/ (NOT under artifacts/archive)
- touch existing source only if strictly necessary (e.g. a re-export); keep additive.

## Required tests (python -m unittest)
tests/test_project_task_generator_from_intent.py must cover:
- valid intent + valid descriptors -> status success and a plan that passes
  `validate_project_task_plan` with no errors
- generated tasks respect `allowed_task_kinds` (a disallowed-kind descriptor -> blocked)
- generated tasks respect `safety_limits.max_tasks` (descriptors over the bound -> blocked)
- deterministic output: generating twice from identical inputs yields identical plans
  (deep-equal), including task_ids/order/deps
- invalid intent fails safely (status blocked, errors present, no raise)
- dependency wiring produces a valid DAG accepted by the plan validator
- backward compatibility: `planned_task_to_task_spec` on a generated task (with a
  /tmp existing dir override for repo_path) is accepted by `validate_task_spec`
- no execution side effects (no queue dirs/files created, no network, no Codex,
  no git) — assert cwd contents unchanged across generation
- existing Prompt645 model tests still pass (tests.test_project_intent_plan_model)
- cheap targeted regression remains green (tests.test_daemon_queue,
  tests.test_targeted_fix_retry)

## Safety constraints (hard)
- Pure offline deterministic generator: no network/Codex/daemon/queue/git/runtime.
- Deterministic (no Date.now()/random inside generation; timestamps are inputs).
- No modification of artifacts/archive. No modification of handoff_reports.
- Additive only; respect intent safety_limits and daemon caps; reject unsafe intents.

## Report requirements
Write:
- artifacts/autonomous_runtime/prompt646_report.json
- artifacts/autonomous_runtime/prompt646_summary.md
Required report fields:
- prompt646_status
- prompt646_base_commit
- prompt646_base_tags_at_head
- prompt646_project_task_generator_created
- prompt646_intent_to_plan_generation_created
- prompt646_generated_plan_validation_passed
- prompt646_deterministic_generation_tests_passed
- prompt646_allowed_task_kinds_enforced
- prompt646_max_tasks_bound_enforced
- prompt646_backward_compatible_task_spec_conversion
- prompt646_no_execution_side_effects
- prompt646_existing_model_tests_passed
- prompt646_existing_runtime_regression_tests_passed
- prompt646_files_modified
- prompt646_main_repo_safe
- prompt646_archive_touched
- prompt646_handoff_reports_touched
- prompt646_final_decision
- prompt646_next_action

## Final stdout contract
Print only:
prompt646_status=<success|partial|blocked>
prompt646_project_task_generator_created=<true|false>
prompt646_intent_to_plan_generation_created=<true|false>
prompt646_generated_plan_validation_passed=<true|false>
prompt646_deterministic_generation_tests_passed=<true|false>
prompt646_no_execution_side_effects=<true|false>
prompt646_existing_model_tests_passed=<true|false>
prompt646_existing_runtime_regression_tests_passed=<true|false>
prompt646_files_modified=<list>
prompt646_commit=<commit_hash_if_committed|none>
prompt646_tag=<tag_if_created|none>
prompt646_report_path=artifacts/autonomous_runtime/prompt646_report.json
prompt646_summary_path=artifacts/autonomous_runtime/prompt646_summary.md
prompt646_next_action=<auto_queue_population_from_project_plan|fix_project_task_generator|manual_review_required>

## Decision rules
- If the generator is created, generates a plan that passes the Prompt645 validators,
  enforces allowed_task_kinds and max_tasks, is deterministic, is backward compatible
  with task_spec conversion, has NO execution side effects, the existing model tests
  and cheap regression tests pass, and main repo is safe:
    prompt646_status=success
    prompt646_next_action=auto_queue_population_from_project_plan
  (Commit + tag prompt646-project-task-generator-from-intent ONLY if ALL PASS.)
- If generation or a generator test fails / plan invalid:
    prompt646_status=partial|blocked
    prompt646_next_action=fix_project_task_generator
- If existing model/regression tests regress or main repo safety is violated:
    prompt646_status=blocked
    prompt646_next_action=manual_review_required

## Commit/tag policy
Commit/tag ONLY if all PASS conditions are met. Stage only the new generator source,
the new test, and the prompt646 report/summary (+ optional fixture and this prompt
file). Do NOT stage artifacts/archive or handoff_reports.
Suggested commit message: "prompt646 project task generator from intent"
Suggested tag: prompt646-project-task-generator-from-intent

## Out of scope (do NOT do in Prompt646)
- LLM / free-text decomposition
- Automatic queue population from the plan (next prompt)
- Project completion-gate evaluation or iterate-until-done loop controller
- Broad task-kind expansion
- Any Codex / daemon / network / git runtime execution
