PROMPT646_GENERATE_PROJECT_TASK_GENERATOR_FROM_INTENT

Repository:
- /home/rai/codex-local-runner

Goal:
Analyze the confirmed Prompt645 state and generate the next executable implementation prompt for:

project_task_generator_from_intent

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
  - commit: 8d46ca4
  - tag: prompt645-project-intent-schema-task-plan-model
- Prompt645 confirmed:
  - prompt645_status=success
  - prompt645_project_intent_model_created=true
  - prompt645_task_plan_model_created=true
  - prompt645_validation_tests_passed=true
  - prompt645_no_execution_side_effects=true
  - prompt645_existing_runtime_regression_tests_passed=true
  - prompt645_next_action=project_task_generator_from_intent

Prompt645 created:
- automation/orchestration/planned_runner/project_intent.py
- automation/orchestration/planned_runner/project_plan.py
- tests/test_project_intent_plan_model.py

Confirmed Prompt645 capabilities:
- Project Intent model
- Project Task Plan model
- validation
- JSON serialization/deserialization
- dependency/ordering validation
- bounds validation
- safety limits bounded by daemon caps
- planned_task_to_task_spec() pure offline conversion helper
- no execution side effects
- backward compatibility with existing task_spec contract

Remaining gaps:
- Planner Layer: goal -> bounded task decomposition / task generation
- automatic queue population from project plan
- project progress / completion gate
- project-level iterate-until-done controller
- broad task-kind support beyond add_function
- long-running daemon soak proof

Required task:
1. Inspect the repo and Prompt645 evidence.
2. Confirm Prompt645 is the correct base.
3. Generate one executable implementation prompt for Prompt646.
4. The generated prompt should implement the next minimal layer only:
   project_task_generator_from_intent.

Expected next implementation target:
project_task_generator_from_intent

Prompt646 must create a deterministic, local, non-LLM task generator that converts a validated ProjectIntent into a bounded ProjectTaskPlan using the Prompt645 model layer.

Important:
Prompt646 should not implement a real LLM planner yet.
Prompt646 should not enqueue tasks.
Prompt646 should not call the daemon queue.
Prompt646 should not run Codex.
Prompt646 should not implement project completion gate.
Prompt646 should not implement iterate-until-done loop controller.
Prompt646 should not expand broad task kinds.
Prompt646 should be a safe bridge from project intent to task plan.

Required repo inspection:
Inspect at minimum:
- git log -1 --oneline
- git tag --points-at HEAD
- git status --short
- artifacts/autonomous_runtime/prompt645_report.json
- artifacts/autonomous_runtime/prompt645_summary.md
- automation/orchestration/planned_runner/project_intent.py
- automation/orchestration/planned_runner/project_plan.py
- automation/orchestration/planned_runner/task_spec.py
- automation/orchestration/planned_runner/task_planner.py, if present
- automation/orchestration/planned_runner/daemon_queue.py
- existing tests for project intent/plan and task specs

If the next target is project_task_generator_from_intent, the generated implementation prompt must include:

1. Goal
Create a minimal deterministic project task generator that takes a validated ProjectIntent and produces a bounded ProjectTaskPlan compatible with the Prompt645 model layer and future queue population.

2. Scope
Implement generator layer only:
- project intent input validation
- deterministic task-plan generation from intent
- bounded task generation based on safety limits
- allowed_task_kinds filtering
- simple template/rule-based task creation
- dependency/order assignment
- validation of generated ProjectTaskPlan
- JSON/report/summary support
- tests

3. Required behavior
The implementation should support:
- load ProjectIntent from dict/json
- generate ProjectTaskPlan from intent
- respect intent.allowed_task_kinds
- respect safety_limits.max_tasks
- produce deterministic task ids/order
- produce generated task spec references or payload stubs compatible with ProjectPlan validation
- support at least add_function-compatible minimal task generation if current task kinds are limited
- reject unsupported or unsafe intents safely
- return structured generation result with status, errors, warnings, and plan
- validate the generated plan using Prompt645 validators
- no queue insertion
- no daemon execution
- no Codex execution

4. Integration boundary
The implementation should NOT enqueue tasks.
The implementation should NOT call daemon queue.
The implementation should NOT run Codex.
The implementation should NOT implement LLM decomposition.
The implementation should NOT implement completion gate.
The implementation should NOT implement project-level loop controller.
The implementation should NOT expand task kinds beyond existing supported task_spec kinds.

5. Likely files to modify/create
The generated prompt should decide exact files after repo inspection, but likely:
- automation/orchestration/planned_runner/project_task_generator.py
- tests/test_project_task_generator_from_intent.py
- artifacts/autonomous_runtime/prompt646_report.json
- artifacts/autonomous_runtime/prompt646_summary.md
- optionally examples/fixtures under a safe existing test fixture path if appropriate
- optionally update __init__/registry only if necessary

6. Tests
The generated implementation prompt must require tests for:
- valid ProjectIntent generates valid ProjectTaskPlan
- generated plan passes Prompt645 plan validation
- generated tasks respect allowed_task_kinds
- generated tasks respect max_tasks
- deterministic output for same intent
- invalid intent fails safely
- unsupported allowed task kind fails safely or is rejected by existing validators
- no queue/daemon/Codex side effects
- backward compatibility with task_spec validation where applicable
- existing Prompt645 model tests still pass
- targeted runtime regression tests still pass if relevant and cheap

7. Report requirements
The generated implementation prompt must require:
- artifacts/autonomous_runtime/prompt646_report.json
- artifacts/autonomous_runtime/prompt646_summary.md

8. Final stdout contract for generated implementation prompt
The generated implementation prompt must require final stdout like:
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

9. Commit/tag policy for generated implementation prompt
The generated implementation prompt should allow commit/tag only if all PASS conditions are met.
Suggested tag:
prompt646-project-task-generator-from-intent
Do not stage artifacts/archive or handoff_reports.

Required output files from this prompt-generation run:
- prompts/generated/prompt646_project_task_generator_from_intent.md
- artifacts/autonomous_runtime/prompt646_prompt_generation_report.json
- artifacts/autonomous_runtime/prompt646_prompt_generation_summary.md

Required generation report fields:
- prompt646_generator_status
- prompt646_generator_base_commit
- prompt646_generator_tags_at_head
- prompt646_generator_prompt645_verified
- prompt646_generator_next_target_selected
- prompt646_generator_next_target_rationale
- prompt646_generator_prompt_path
- prompt646_generator_prompt_created
- prompt646_generator_scope
- prompt646_generator_excluded_scope
- prompt646_generator_recommended_files
- prompt646_generator_recommended_tests
- prompt646_generator_safety_constraints_included
- prompt646_generator_final_decision
- prompt646_generator_next_action

Expected final stdout:
Print only:
prompt646_generator_status=<success|blocked|partial>
prompt646_generator_base_commit=<commit>
prompt646_generator_next_target_selected=<target>
prompt646_generator_prompt_path=prompts/generated/prompt646_project_task_generator_from_intent.md
prompt646_generator_next_action=execute_prompt646_project_task_generator_from_intent
prompt646_generator_report_path=artifacts/autonomous_runtime/prompt646_prompt_generation_report.json
prompt646_generator_summary_path=artifacts/autonomous_runtime/prompt646_prompt_generation_summary.md
