PROMPT645_PROJECT_INTENT_SCHEMA_AND_TASK_PLAN_MODEL

Repository:
- /home/rai/codex-local-runner

## Goal
Create a minimal, machine-readable **Project Intent** and **Task Plan** data model
that can describe a project-level development goal and a bounded, ordered plan of
tasks to be executed LATER by the existing daemon queue. This is the first layer of
the project-autonomy stack (Prompt641 architecture): the "container/model" layer
only — no planning, no decomposition, no enqueue, no execution.

This is an EXECUTION task (implement + test + validate + report). It is a pure,
offline, deterministic data-model layer with NO side effects.

## Current state (confirmed)
- Branch: local/prompt299-one-cycle-controller-v1
- HEAD: 3170ddc, tag: prompt644a-current-capability-acceptance
- Prompt644A confirmed the execution/self-healing layer at **L7.5_confirmed**:
  bounded daemon queue, strict effect gate, /tmp sandbox isolation + cleanup,
  commit/tag only after a strictly-passed effect, automatic targeted-fix retry
  (resolved -> done; unresolved -> failed/no-commit-tag), main-repo runtime safety.
- The daemon consumes pre-written task spec JSON. The validated task spec schema
  (automation/orchestration/planned_runner/task_spec.py) requires:
  task_id (^[a-z0-9][a-z0-9._-]{0,63}$), kind (SUPPORTED_TASK_KINDS=("add_function",)),
  repo_path (existing dir), target_file (repo-relative, no '..'), function_name
  (identifier), expression, optional verify_commands (list of non-empty argv lists),
  optional expected_unmodified_files (list), optional allow_extra_files (bool).
- daemon_queue.enqueue_task(queue_dir, spec) writes pending/<task_id>.json.

## Root gap addressed
There is no project-level data model: nothing can represent "a project goal + its
success criteria + safety limits + an ordered set of planned tasks." Every higher
layer (planner, task generator, queue orchestrator, completion gate, auto loop)
needs this model to exist first. This prompt creates ONLY that model.

## Scope (container/model layer ONLY)
Implement:
- a Project Intent schema/model + validation
- a Project Task Plan schema/model (a plan = intent + ordered planned tasks) + validation
- serialization / deserialization (to/from plain dict + JSON)
- validation-error reporting (structured, never raises on invalid input — returns errors)
- example/fixture(s)
- tests
- a report/summary

## Required behavior / fields

### Project Intent
- project_id (slug, validated pattern, reuse the task_id-style pattern ^[a-z0-9][a-z0-9._-]{0,63}$)
- project_name (human-readable, non-empty)
- goal (non-empty description of the project-level development goal)
- success_criteria (list of strings; may be empty but field present)
- constraints (list of strings)
- allowed_task_kinds (list; each must be within task_spec.SUPPORTED_TASK_KINDS;
  default to ["add_function"]; reject unknown kinds)
- safety_limits: max_tasks (int>0, bounded), max_cycles_per_task (int>0, bounded),
  max_total_seconds (int>0, bounded) — mirror/respect the daemon caps
  (MAX_JOBS_CAP, MAX_CYCLES_CAP, MAX_SECONDS_TOTAL_CAP) as hard upper bounds
- human_approval_policy / risk_boundary fields: e.g. require_human_approval (bool),
  approval_required_for (list of risk categories, e.g. ["push","merge","new_task_kind"])
- repo_target: the repo the project operates on (recorded for provenance; the model
  does NOT verify it exists — that is an execution-time concern)
- provenance/audit: schema_version, created_by, source ("manual"|"generated"), notes

### Project Task Plan
- a plan references/embeds a validated Project Intent
- tasks: an ordered list of planned-task entries; each planned-task entry contains:
  - task_id (validated slug, unique within the plan)
  - kind (must be in the intent's allowed_task_kinds)
  - a task_spec_payload OR a generated_task_spec_ref: enough to later produce a
    valid daemon task spec (do NOT require repo_path to exist at model time)
  - depends_on: list of task_ids in this plan (no cycles, no dangling refs)
  - order/priority (int) and/or topological position
  - status: one of {"planned","queued","running","done","failed","blocked","skipped"}
    (default "planned")
  - generated_task_spec_path (optional reference, may be empty until generation)
- completion_criteria placeholder: a field describing when the project is "done"
  (e.g. all required tasks done) — recorded but NOT evaluated in this prompt
- plan-level provenance/audit (schema_version, generated_at supplied by caller, source)
- validation must reject: duplicate task_ids, dependency cycles, dangling depends_on,
  unsupported kinds, kinds not in allowed_task_kinds, bounds exceeding daemon caps,
  empty required fields

### Validation contract
- Provide a validate function returning (normalized_model: dict, errors: list[str]),
  MIRRORING task_spec.validate_task_spec's style (never raise on invalid input).
- Provide load/dump helpers (dict <-> JSON string/file) that round-trip exactly.
- Deterministic: no Date.now()/random; timestamps are inputs, not generated inside.

## Integration boundary (hard — do NOT cross)
- Do NOT enqueue tasks (no daemon_queue.enqueue_task calls).
- Do NOT run Codex / live gate / autonomous loop.
- Do NOT call the daemon queue runner.
- Do NOT implement planner / LLM decomposition / auto task-spec generation.
- Do NOT populate the queue from a plan.
- Do NOT implement a completion gate evaluator or loop controller.
- Do NOT expand SUPPORTED_TASK_KINDS or add new task kinds.
- The model may include a pure, offline helper that CONVERTS a planned-task entry
  into a daemon task-spec dict shape (no I/O, no enqueue) so future prompts can use
  it — but it must not write to the queue or run anything.

## Likely files to create/modify (decide exact set during implementation)
- automation/orchestration/planned_runner/project_intent.py (new)
- automation/orchestration/planned_runner/project_plan.py (new)
- tests/test_project_intent_plan_model.py (new)
- optionally an example fixture under tests/ or artifacts/autonomous_runtime/
  (do NOT place under artifacts/archive)
- Touch existing source ONLY if strictly necessary (e.g. a re-export); keep additive
  and backward compatible. Do NOT modify task_spec.py / daemon_queue.py behavior.

## Required tests (python -m unittest)
tests/test_project_intent_plan_model.py must cover:
- valid project intent loads and validates (no errors)
- invalid intent fails safely (returns errors, does not raise): missing goal, bad
  project_id, unknown allowed_task_kind, bounds exceeding daemon caps
- valid task plan with ordered tasks validates
- unsupported / not-allowed task kind is rejected
- dependency/ordering validation: duplicate task_ids rejected, dependency cycle
  rejected, dangling depends_on rejected, valid DAG accepted
- bounds validation (max_tasks/max_cycles/max_total_seconds within daemon caps)
- serialization round-trip (dict->json->dict and model dump/load are stable/equal)
- no execution side effects (no files written to any queue, no network, no Codex):
  assert the model functions perform no queue/enqueue/git operations
- planned-task -> daemon task-spec conversion helper produces a dict that
  task_spec.validate_task_spec accepts (use a /tmp existing dir for repo_path in the
  test so the existing validator passes) — proving backward compatibility
- existing targeted tests still pass:
  tests.test_daemon_queue, tests.test_daemon_queue_targeted_fix_retry_integration,
  tests.test_targeted_fix_retry, tests.test_sandbox_commit_tag_gate

## Safety constraints (hard)
- Pure offline data model: no network, no Codex, no daemon queue, no git, no /tmp
  runtime jobs.
- No modification of artifacts/archive. No modification of handoff_reports.
- Do NOT change existing daemon/task-spec/effect-gate behavior; additive only.
- Deterministic (no Date.now()/random inside the model).
- Respect daemon caps as hard upper bounds for safety_limits.

## Report requirements
Write:
- artifacts/autonomous_runtime/prompt645_report.json
- artifacts/autonomous_runtime/prompt645_summary.md
Required report fields:
- prompt645_status
- prompt645_base_commit
- prompt645_base_tags_at_head
- prompt645_project_intent_model_created
- prompt645_task_plan_model_created
- prompt645_files_created
- prompt645_files_modified
- prompt645_validation_tests_passed
- prompt645_no_execution_side_effects
- prompt645_backward_compatible_task_spec_conversion
- prompt645_existing_runtime_regression_tests_passed
- prompt645_main_repo_safe
- prompt645_archive_touched
- prompt645_handoff_reports_touched
- prompt645_final_decision
- prompt645_next_action

## Final stdout contract
Print only:
prompt645_status=<success|partial|blocked>
prompt645_project_intent_model_created=<true|false>
prompt645_task_plan_model_created=<true|false>
prompt645_validation_tests_passed=<true|false>
prompt645_no_execution_side_effects=<true|false>
prompt645_existing_runtime_regression_tests_passed=<true|false>
prompt645_files_modified=<list>
prompt645_commit=<commit_hash_if_committed|none>
prompt645_tag=<tag_if_created|none>
prompt645_report_path=artifacts/autonomous_runtime/prompt645_report.json
prompt645_summary_path=artifacts/autonomous_runtime/prompt645_summary.md
prompt645_next_action=<project_task_generator_from_intent|fix_project_intent_model|manual_review_required>

## Decision rules
- If both models are created, validation + round-trip + regression tests pass, the
  planned-task->task-spec conversion is backward compatible, and there are NO
  execution side effects and main repo is safe:
    prompt645_status=success
    prompt645_next_action=project_task_generator_from_intent
  (Commit + tag prompt645-project-intent-schema-task-plan-model ONLY if ALL PASS.)
- If the model is incomplete or a model test fails:
    prompt645_status=partial|blocked
    prompt645_next_action=fix_project_intent_model
- If existing runtime regression tests regress or main repo safety is violated:
    prompt645_status=blocked
    prompt645_next_action=manual_review_required

## Commit/tag policy
Commit/tag ONLY if all PASS conditions are met. Stage only the new model source,
the new test, and the prompt645 report/summary (+ optional fixture). Do NOT stage
artifacts/archive or handoff_reports.
Suggested commit message: "prompt645 project intent schema and task plan model"
Suggested tag: prompt645-project-intent-schema-task-plan-model

## Out of scope (do NOT do in Prompt645)
- Planner / automatic task decomposition / LLM-driven generation
- Automatic queue population from a plan
- Project completion-gate evaluation or auto loop controller
- Broad task-kind expansion
- Long-running daemon soak
- Any Codex / daemon / network / git runtime execution
