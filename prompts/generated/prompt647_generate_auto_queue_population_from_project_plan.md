PROMPT647_GENERATE_AUTO_QUEUE_POPULATION_FROM_PROJECT_PLAN

Repository:
- /home/rai/codex-local-runner

Goal:
Analyze the confirmed Prompt646 state and generate the next executable implementation prompt for:

auto_queue_population_from_project_plan

This is prompt-generation only.
Do not implement source changes.
Do not stage.
Do not commit.
Do not tag.
Do not push.
Do not PR.
Do not merge.
Do not touch artifacts/archive.
Do not modify handoff_reports.
Proceed autonomously without asking for confirmation.

Current confirmed state:
- Branch: local/prompt299-one-cycle-controller-v1
- Current HEAD:
  - commit: 894fac8
  - tag: prompt646-project-task-generator-from-intent
- Prompt646 confirmed:
  - prompt646_status=success
  - prompt646_project_task_generator_created=true
  - prompt646_intent_to_plan_generation_created=true
  - prompt646_generated_plan_validation_passed=true
  - prompt646_deterministic_generation_tests_passed=true
  - prompt646_no_execution_side_effects=true
  - prompt646_existing_model_tests_passed=true
  - prompt646_existing_runtime_regression_tests_passed=true
  - prompt646_next_action=auto_queue_population_from_project_plan

Prompt645 created:
- automation/orchestration/planned_runner/project_intent.py
- automation/orchestration/planned_runner/project_plan.py

Prompt646 created:
- automation/orchestration/planned_runner/project_task_generator.py
- tests/test_project_task_generator_from_intent.py

Confirmed capabilities:
- ProjectIntent model
- ProjectTaskPlan model
- validation and JSON round-trip
- deterministic ProjectIntent + structured descriptors -> ProjectTaskPlan generator
- generated plan validation
- deterministic generation
- backward-compatible task_spec conversion
- no execution side effects

Remaining gaps:
- automatic queue population from a ProjectTaskPlan
- project progress / completion gate
- project-level iterate-until-done controller
- broad task-kind support beyond add_function
- long-running daemon soak proof

Required task:
1. Inspect the repo and Prompt646 evidence.
2. Confirm Prompt646 is the correct base.
3. Generate one executable implementation prompt for Prompt647.
4. The generated prompt should implement the next minimal layer only:
   auto_queue_population_from_project_plan.

Expected next implementation target:
auto_queue_population_from_project_plan

Prompt647 must create a deterministic, local queue-population layer that takes a validated ProjectTaskPlan and materializes daemon-queue-compatible task entries into an explicit caller-provided queue/output directory.

Important:
Prompt647 may create queue-entry files only in explicit caller-provided output directories, preferably test tmpdirs.
Prompt647 must not run daemon queue.
Prompt647 must not run Codex.
Prompt647 must not execute generated tasks.
Prompt647 must not implement project completion gate.
Prompt647 must not implement iterate-until-done controller.
Prompt647 must not expand task kinds.
Prompt647 must not write to any live/default queue unless explicitly requested by a caller API and covered by tests.
Prompt647 should be the safe bridge from generated ProjectTaskPlan to daemon queue input files.

Required repo inspection:
Inspect at minimum:
- git log -1 --oneline
- git tag --points-at HEAD
- git status --short
- artifacts/autonomous_runtime/prompt646_report.json
- artifacts/autonomous_runtime/prompt646_summary.md
- automation/orchestration/planned_runner/project_intent.py
- automation/orchestration/planned_runner/project_plan.py
- automation/orchestration/planned_runner/project_task_generator.py
- automation/orchestration/planned_runner/task_spec.py
- automation/orchestration/planned_runner/daemon_queue.py
- scripts/run_task_queue_daemon.py
- existing tests for project intent/plan/generator, task specs, daemon queue

If the next target is auto_queue_population_from_project_plan, the generated implementation prompt must include:

1. Goal
Create a minimal deterministic queue-population layer that takes a validated ProjectTaskPlan and writes daemon-queue-compatible task entries to an explicit output queue directory without running the daemon or Codex.

2. Scope
Implement queue population layer only:
- load/accept ProjectTaskPlan
- validate ProjectTaskPlan
- convert planned tasks to daemon task specs using Prompt645/646-compatible helpers
- enforce order/dependencies as far as the existing daemon queue contract supports
- materialize queue task files in deterministic order
- return structured population result with status/errors/warnings/output paths
- tests using tmpdirs only
- report/summary

3. Required behavior
The implementation should support:
- accept plan as dict or normalized model
- validate with validate_project_task_plan
- reject invalid plans safely, never crash
- require explicit output queue directory
- create output directory if safe and caller-provided
- write deterministic queue files from planned tasks
- preserve task order
- preserve task ids
- include task spec payload compatible with task_spec.validate_task_spec
- block or warn clearly if dependencies cannot be represented by current daemon queue format
- produce deterministic output for same plan and output directory
- no daemon execution
- no Codex execution
- no network
- no git runtime
- no live queue mutation by default

4. Integration boundary
The implementation should NOT run daemon queue.
The implementation should NOT call Codex.
The implementation should NOT execute tasks.
The implementation should NOT implement planner/LLM decomposition.
The implementation should NOT implement project completion gate.
The implementation should NOT implement project-level loop controller.
The implementation should NOT expand task kinds beyond existing supported task_spec kinds.

5. Likely files to modify/create
The generated prompt should decide exact files after repo inspection, but likely:
- automation/orchestration/planned_runner/project_queue_population.py
- tests/test_project_queue_population_from_plan.py
- artifacts/autonomous_runtime/prompt647_report.json
- artifacts/autonomous_runtime/prompt647_summary.md
- optionally examples/fixtures under tests/ only if useful
- optionally update __init__/registry only if necessary

6. Tests
The generated implementation prompt must require tests for:
- valid ProjectTaskPlan populates queue files into tmpdir
- generated queue task files pass task_spec.validate_task_spec
- invalid plan fails safely
- explicit output directory is required
- deterministic filenames/content/order
- max task/order preservation
- dependency behavior is explicit: represented if supported, otherwise warning/blocking is deterministic
- no daemon execution side effects
- no Codex side effects
- no network/git side effects
- artifacts/archive and handoff_reports untouched
- existing Prompt645 model tests still pass
- existing Prompt646 generator tests still pass
- cheap daemon queue/task_spec regressions still pass

7. Report requirements
The generated implementation prompt must require:
- artifacts/autonomous_runtime/prompt647_report.json
- artifacts/autonomous_runtime/prompt647_summary.md

8. Final stdout contract for generated implementation prompt
The generated implementation prompt must require final stdout like:
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

9. Commit/tag policy for generated implementation prompt
The generated implementation prompt should allow commit/tag only if all PASS conditions are met.
Suggested tag:
prompt647-auto-queue-population-from-project-plan
Do not stage artifacts/archive or handoff_reports.

Required output files from this prompt-generation run:
- prompts/generated/prompt647_auto_queue_population_from_project_plan.md
- artifacts/autonomous_runtime/prompt647_prompt_generation_report.json
- artifacts/autonomous_runtime/prompt647_prompt_generation_summary.md

Required generation report fields:
- prompt647_generator_status
- prompt647_generator_base_commit
- prompt647_generator_tags_at_head
- prompt647_generator_prompt646_verified
- prompt647_generator_next_target_selected
- prompt647_generator_next_target_rationale
- prompt647_generator_prompt_path
- prompt647_generator_prompt_created
- prompt647_generator_scope
- prompt647_generator_excluded_scope
- prompt647_generator_recommended_files
- prompt647_generator_recommended_tests
- prompt647_generator_safety_constraints_included
- prompt647_generator_final_decision
- prompt647_generator_next_action

Expected final stdout:
Print only:
prompt647_generator_status=<success|blocked|partial>
prompt647_generator_base_commit=<commit>
prompt647_generator_next_target_selected=<target>
prompt647_generator_prompt_path=prompts/generated/prompt647_auto_queue_population_from_project_plan.md
prompt647_generator_next_action=execute_prompt647_auto_queue_population_from_project_plan
prompt647_generator_report_path=artifacts/autonomous_runtime/prompt647_prompt_generation_report.json
prompt647_generator_summary_path=artifacts/autonomous_runtime/prompt647_prompt_generation_summary.md
