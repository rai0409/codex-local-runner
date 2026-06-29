PROMPT645_GENERATE_PROJECT_LEVEL_AUTONOMY_NEXT_PROMPT

Repository:
- /home/rai/codex-local-runner

Goal:
Analyze the current confirmed codex-local-runner state after Prompt644A and generate the next executable implementation prompt that moves the system toward:

"Project-level autonomous development with minimal human intervention."

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
  - commit: 3170ddc
  - tag: prompt644a-current-capability-acceptance
- Prompt644A confirmed:
  - prompt644a_status=success
  - prompt644a_tests_result=passed
  - prompt644a_runtime_validation_status=passed
  - prompt644a_jobs_processed=3
  - prompt644a_passed_effect_task_done=true
  - prompt644a_resolved_self_healing_task_done=true
  - prompt644a_unresolved_task_failed=true
  - prompt644a_targeted_fix_invoked=true
  - prompt644a_targeted_fix_resolved=true
  - prompt644a_effect_failed_wrongly_succeeded_count=0
  - prompt644a_strict_gate_violations=0
  - prompt644a_main_repo_head_unchanged_during_runtime=true
  - prompt644a_generated_artifacts_leftover_count=0
  - prompt644a_current_capability_classification=L7.5_confirmed
- Prompt644A final decision:
  - Current-capability acceptance passed.
  - The Prompt643 self-healing daemon works end-to-end in a live /tmp batch.
  - Passed, resolved-self-healing, and unresolved scenarios all behaved correctly under strict effect gate.
  - Execution/self-healing layer is confirmed at L7.5.
  - Next recommended prompt: project_intent_schema_and_task_plan_model.

Confirmed capabilities:
- bounded daemon queue execution
- multiple queue tasks processed
- strict effect verification gate
- /tmp sandbox isolation
- sandbox cleanup
- sandbox commit/tag only after strictly-passed effect
- automatic targeted-fix retry on effect failure
- resolved self-healing task -> success + commit/tag + done
- unresolved task -> failed/no commit/no tag
- main repo runtime safety
- generated artifact cleanup

Remaining gaps:
- Project Intent Layer
- Planner Layer
- Task Spec Generator
- automatic queue population from project plan
- Project Progress / Completion gate
- project-level auto loop controller
- broad task-kind support beyond add_function
- long-running daemon soak proof

User's real goal:
The user does not merely want prompt-by-prompt automation.
The user wants to give a project-level goal and have Codex/ChatGPT-driven development run as autonomously as possible until completion, minimizing human intervention.

Required task:
1. Inspect the repo and Prompt644A evidence.
2. Decide the next implementation target.
3. Generate one executable implementation prompt for that target.
4. The generated prompt should be the next safest and fastest step toward project-level autonomy.

Expected decision:
The likely next target is:
project_intent_schema_and_task_plan_model

But do not blindly assume.
Analyze whether any prerequisite is still missing.
If the execution/self-healing layer is already sufficiently confirmed by Prompt644A, choose project_intent_schema_and_task_plan_model.
If a critical regression or missing prerequisite is found, choose the prerequisite instead and explain.

Required repo inspection:
Inspect at minimum:
- git log -1 --oneline
- git tag --points-at HEAD
- git status --short
- artifacts/autonomous_runtime/prompt644a_current_capability_acceptance_report.json
- artifacts/autonomous_runtime/prompt644a_current_capability_acceptance_summary.md
- scripts/run_task_queue_daemon.py
- automation/orchestration/planned_runner/daemon_queue.py
- automation/orchestration/planned_runner/task_spec.py
- automation/orchestration/planned_runner/task_planner.py, if present
- automation/orchestration/planned_runner/targeted_fix_retry.py
- automation/orchestration/planned_runner/effect_gate.py
- existing tests for task specs, daemon queue, planning, and autonomous runtime

The generated implementation prompt must:
- be saved at:
  prompts/generated/prompt645_project_intent_schema_and_task_plan_model.md
- implement the next step only.
- not implement full planner, auto decomposition, queue population, loop controller, broad task-kind expansion, or long-running daemon soak.
- create the minimal project-level data model layer needed before planning.

If the next target is project_intent_schema_and_task_plan_model, the generated prompt must include:

1. Goal
Create a minimal machine-readable Project Intent and Task Plan model that can describe a project-level development goal and a bounded plan of task specs to be executed later by the existing daemon queue.

2. Scope
Implement the "container/model" layer only:
- project intent schema/model
- project task plan schema/model
- validation
- serialization/deserialization
- report/summary support
- examples/fixtures
- tests

3. Required behavior
The implementation should support:
- project id/name
- project goal
- success criteria
- constraints
- allowed task kinds
- max tasks / max cycles / safety limits
- human approval policy or risk boundary fields
- tasks list
- task dependencies or ordering
- task status fields
- generated task spec references
- completion criteria placeholder
- provenance/audit fields
- validation errors for invalid plans
- no execution in this prompt

4. Integration boundary
The implementation should NOT enqueue tasks yet.
The implementation should NOT run Codex.
The implementation should NOT call daemon queue.
The implementation should NOT implement planner/LLM decomposition yet.
It should only make the future project planner and queue orchestrator possible.

5. Likely files to modify/create
The generated prompt should decide exact files after repo inspection, but likely:
- automation/orchestration/planned_runner/project_intent.py
- automation/orchestration/planned_runner/project_plan.py
- tests/test_project_intent_plan_model.py
- optionally examples or artifacts under artifacts/autonomous_runtime/
- optionally update registry/imports only if necessary

6. Tests
The generated implementation prompt must require tests for:
- valid project intent loads and validates
- invalid intent fails safely
- valid task plan with ordered tasks validates
- invalid task kind is rejected or marked unsupported
- dependencies/ordering validation
- bounds validation
- serialization round-trip
- no execution side effects
- backward compatibility with existing daemon queue/task specs
- existing targeted tests still pass

7. Report requirements
The generated implementation prompt must require:
- artifacts/autonomous_runtime/prompt645_report.json
- artifacts/autonomous_runtime/prompt645_summary.md

8. Final stdout contract for generated implementation prompt
The generated implementation prompt must require final stdout like:
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

9. Commit/tag policy for generated implementation prompt
The generated implementation prompt should allow commit/tag only if all PASS conditions are met.
Suggested tag:
prompt645-project-intent-schema-task-plan-model
Do not stage artifacts/archive or handoff_reports.

Required output files from this prompt-generation run:
- prompts/generated/prompt645_project_intent_schema_and_task_plan_model.md
- artifacts/autonomous_runtime/prompt645_prompt_generation_report.json
- artifacts/autonomous_runtime/prompt645_prompt_generation_summary.md

Required generation report fields:
- prompt645_generator_status
- prompt645_generator_base_commit
- prompt645_generator_tags_at_head
- prompt645_generator_current_capability_classification
- prompt645_generator_prompt644a_verified
- prompt645_generator_next_target_selected
- prompt645_generator_next_target_rationale
- prompt645_generator_prompt_path
- prompt645_generator_prompt_created
- prompt645_generator_scope
- prompt645_generator_excluded_scope
- prompt645_generator_recommended_files
- prompt645_generator_recommended_tests
- prompt645_generator_safety_constraints_included
- prompt645_generator_final_decision
- prompt645_generator_next_action

Expected final stdout:
Print only:
prompt645_generator_status=<success|blocked|partial>
prompt645_generator_current_capability_classification=<L7.5_confirmed|unknown|blocked>
prompt645_generator_next_target_selected=<target>
prompt645_generator_prompt_path=prompts/generated/prompt645_project_intent_schema_and_task_plan_model.md
prompt645_generator_next_action=execute_prompt645_project_intent_schema_and_task_plan_model
prompt645_generator_report_path=artifacts/autonomous_runtime/prompt645_prompt_generation_report.json
prompt645_generator_summary_path=artifacts/autonomous_runtime/prompt645_prompt_generation_summary.md
