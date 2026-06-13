PROMPT638A_TASK1_EFFECT_FAILURE_ROOT_CAUSE_ANALYSIS

Repository:
- /home/rai/codex-local-runner

Goal:
Analyze the Prompt638 no-Claude real-task batch result, especially Task1, and determine exactly what must be fixed before continuing real task batch acceptance.

This is analysis-only.
Do not implement the fix yet.
Do not modify source files.
Do not stage.
Do not commit.
Do not tag.
Do not push.

Confirmed context:
The repo is at:
- branch: local/prompt299-one-cycle-controller-v1
- HEAD: 409b0fa prompt637 sandbox generated artifact cleanup policy
- tag at HEAD: prompt637-sandbox-generated-artifact-cleanup-policy

Prompt637 is committed/tagged and proven:
- sandbox cleanup works
- final sandbox status can be clean
- generated Python artifacts are removed
- daemon candidate acceptance succeeds cleanly

Prompt638 no-Claude real-task batch was attempted with 3 task specs against /tmp clones:
- task1-cleanup-add-function
- task2-queue-add-function
- task3-spec-add-function

After retrying with correct tokens:
- daemon queue processed 3 jobs
- queue done=3
- queue failed=0
- each task had codex_invoked_count=1
- each task performed sandbox commit/tag
- each sandbox final status was clean
- main repo HEAD stayed unchanged

However Task1 has an important inconsistency:
- task1 status=success
- task1 stage=done
- task1 loop_status=success
- task1 codex_invoked_count=1
- task1 sandbox_commit_performed=true
- task1 sandbox_tag_performed=true
- task1 sandbox_final_status_clean=true
- BUT task1 per_cycle_effect_verification_statuses=['failed']

Task1 required text check also only showed:
- return 1 if a else b

It did not show the expected:
- def is_generated_artifact_count(a, b):

Task2 and Task3 appeared normal:
- task2 required def and return were present
- task3 required def and return were present
- both had per_cycle_effect_verification_statuses=['passed']

Required analysis:
1. Inspect the Task1 sandbox repo:
   - /tmp/prompt638_no_claude_real_task_batch/repos/task1_cleanup
   - latest commit
   - latest commit diff
   - target file:
     automation/orchestration/planned_runner/sandbox_cleanup.py

2. Inspect Task1 run artifacts:
   - /tmp/prompt638_no_claude_real_task_batch/runs_retry_correct_tokens/task1-cleanup-add-function/run_report.json
   - /tmp/prompt638_no_claude_real_task_batch/runs_retry_correct_tokens/task1-cleanup-add-function/loop/autonomous_live_loop_state.json
   - /tmp/prompt638_no_claude_real_task_batch/runs_retry_correct_tokens/task1-cleanup-add-function/plan/task1-cleanup-add-function_effect_spec.json
   - /tmp/prompt638_no_claude_real_task_batch/runs_retry_correct_tokens/task1-cleanup-add-function/plan/task1-cleanup-add-function_prompt.md

3. Determine exactly why Task1 effect verification failed:
   Possible causes to check:
   - Codex inserted only the return line without the expected function definition.
   - Codex inserted the function in a malformed location.
   - The effect spec required text is too strict or mismatched.
   - The effect verifier correctly failed, but later flow incorrectly converted the task to success.
   - The live loop reports success even when one or more per-cycle effect statuses failed.
   - The daemon queue task runner treats loop_status=success as final success without checking per_cycle_effect_verification_statuses.
   - sandbox commit/tag gate runs even after effect verification failed.

4. Determine which code path is responsible for the incorrect final success:
   Inspect at minimum:
   - scripts/run_task_queue_daemon.py
   - automation/orchestration/planned_runner/autonomous_live_loop.py
   - automation/orchestration/planned_runner/live_codex_gate.py
   - automation/orchestration/planned_runner/task_planner.py
   - related tests

5. Determine whether this is a Task1-only Codex output issue or a general safety bug.
   The key question:
   If any per_cycle_effect_verification_statuses contains failed, can the daemon queue still mark the task success and commit/tag?
   If yes, this is a general safety bug and must be fixed before more real-task acceptance.

6. Produce a strict fix recommendation, but do not implement it.
   The recommendation must answer:
   - Should task success require every per_cycle_effect_verification_status to be passed?
   - Should sandbox commit/tag be blocked if any effect verification failed?
   - Should queue final path be failed instead of done?
   - Should run_report status be blocked/failed instead of success?
   - Should loop_status=success be ignored if effect statuses contain failed?
   - Which module should own this gate?
   - Which tests must be added?
   - Should Task1 be rerun after the fix as a regression case?

Expected final decision:
If effect failed can become final success:
- prompt638a_status=success
- prompt638a_root_cause=effect_failed_not_gated_before_success_commit_tag
- prompt638a_next_action=implement_strict_effect_verification_success_gate

If Task1 failed only because the effect spec was wrong and final success is otherwise safe:
- prompt638a_status=success
- prompt638a_root_cause=task1_effect_spec_mismatch
- prompt638a_next_action=fix_task_spec_or_effect_spec_generation

If evidence is insufficient:
- prompt638a_status=blocked
- prompt638a_next_action=collect_missing_task1_artifacts

Required report:
Write:
- artifacts/autonomous_runtime/prompt638a_task1_effect_failure_root_cause_analysis_report.json
- artifacts/autonomous_runtime/prompt638a_task1_effect_failure_root_cause_analysis_summary.md

Required report fields:
- prompt638a_status
- prompt638a_base_commit
- prompt638a_base_tags_at_head
- prompt638a_main_repo_modified
- prompt638a_task1_sandbox_repo
- prompt638a_task1_latest_commit
- prompt638a_task1_latest_tags
- prompt638a_task1_target_file
- prompt638a_task1_required_text_present
- prompt638a_task1_required_text_missing
- prompt638a_task1_effect_verification_statuses
- prompt638a_task1_loop_status
- prompt638a_task1_run_report_status
- prompt638a_task1_sandbox_commit_performed
- prompt638a_task1_sandbox_tag_performed
- prompt638a_task1_queue_result
- prompt638a_task1_failure_cause
- prompt638a_general_safety_bug_confirmed
- prompt638a_success_gate_current_behavior
- prompt638a_commit_tag_gate_current_behavior
- prompt638a_recommended_fix_summary
- prompt638a_recommended_files_to_modify
- prompt638a_recommended_tests
- prompt638a_rerun_required
- prompt638a_next_prompt_scope
- prompt638a_final_decision
- prompt638a_next_action

Required final stdout:
Print only:
prompt638a_status=<success|blocked|partial>
prompt638a_root_cause=<short_root_cause>
prompt638a_general_safety_bug_confirmed=<true|false>
prompt638a_recommended_files_to_modify=<comma_separated_files>
prompt638a_recommended_tests=<comma_separated_tests>
prompt638a_report_path=<path>
prompt638a_summary_path=<path>
prompt638a_next_action=<implement_strict_effect_verification_success_gate|fix_task_spec_or_effect_spec_generation|collect_missing_task1_artifacts|manual_review_required>
