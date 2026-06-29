PROMPT638D_REAL_BATCH_REACCEPTANCE_AFTER_STRICT_GATE

Repository:
- /home/rai/codex-local-runner

Goal:
Run a fresh bounded real-task daemon queue reacceptance after Prompt638B strict effect verification gate, and determine whether the current L7 daemon candidate behaves correctly in real /tmp task batches.

This is validation-only.
Do not modify main repo source files.
Do not stage.
Do not commit.
Do not tag.
Do not push.
Do not PR.
Do not merge.
Do not touch artifacts/archive.
Do not modify handoff_reports.
Use only /tmp clones/sandboxes for runtime tasks.
Proceed autonomously without asking for confirmation.

Known current verified state:
- HEAD: ab668e7 prompt638b enforce strict effect verification success gate
- tag at HEAD: prompt638b-strict-effect-verification-success-gate
- Prompt638C verified current capability level: L7
- Prompt638C next action: prompt638c_real_batch_reacceptance_after_strict_gate

Relevant strict gate behavior from Prompt638B:
- effect failed blocks success
- effect failed blocks sandbox commit
- effect failed blocks sandbox tag
- effect failed goes to queue failed
- targeted tests passed
- regression proof passed

Required validation:
Run a fresh Prompt638D real-task batch under /tmp using scripts/run_task_queue_daemon.py with correct tokens:
- autonomous token: LOCAL_AUTONOMOUS_RUNTIME_ENABLE
- live codex token: LOCAL_LIVE_CODEX_GATE_ENABLE
- sandbox commit/tag token: ENABLE_SANDBOX_COMMIT_TAG_EXECUTION

Use a fresh work root:
- /tmp/prompt638d_real_batch_reacceptance_after_strict_gate

Create 3 independent /tmp clones from /home/rai/codex-local-runner.
Create 3 task specs in queue/pending using the existing supported task kind:
- kind=add_function

Suggested tasks:
1. task1-cleanup-add-function
   - repo_path: /tmp/prompt638d_real_batch_reacceptance_after_strict_gate/repos/task1_cleanup
   - target_file: automation/orchestration/planned_runner/sandbox_cleanup.py
   - function_name: prompt638d_cleanup_marker
   - expression: a if a else b
   - verify: python -m py_compile automation/orchestration/planned_runner/sandbox_cleanup.py

2. task2-queue-add-function
   - repo_path: /tmp/prompt638d_real_batch_reacceptance_after_strict_gate/repos/task2_queue
   - target_file: automation/orchestration/planned_runner/daemon_queue.py
   - function_name: prompt638d_queue_marker
   - expression: a if a else b
   - verify: python -m py_compile automation/orchestration/planned_runner/daemon_queue.py

3. task3-spec-add-function
   - repo_path: /tmp/prompt638d_real_batch_reacceptance_after_strict_gate/repos/task3_spec
   - target_file: automation/orchestration/planned_runner/task_spec.py
   - function_name: prompt638d_spec_marker
   - expression: a if a else b
   - verify: python -m py_compile automation/orchestration/planned_runner/task_spec.py

Important acceptance rule:
Do not require all 3 tasks to succeed.
Instead, classify each task strictly:
- If per_cycle_effect_verification_statuses are all passed:
  - task may be success
  - sandbox_commit_performed must be true
  - sandbox_tag_performed must be true
  - sandbox_final_status_clean must be true
  - queue final path must be done
- If any per_cycle_effect_verification_status is failed/non-passed:
  - task must be blocked or failed
  - sandbox_commit_performed must be false
  - sandbox_tag_performed must be false
  - queue final path must be failed
  - task must not be in done

The whole Prompt638D validation succeeds if:
- daemon processes the batch
- no task violates the strict gate
- main repo HEAD remains ab668e7
- main repo tag at HEAD remains prompt638b-strict-effect-verification-success-gate
- no main repo source files are modified
- artifacts/archive is not touched
- handoff_reports is not touched
- generated Python artifacts are cleaned from /tmp sandbox repos
- final report clearly states how many tasks succeeded and how many were correctly blocked/failed

Required checks:
1. Preflight:
- git branch --show-current
- git log -1 --oneline
- git tag --points-at HEAD
- git status --short

2. Run the fresh /tmp batch:
- create fresh /tmp work root
- create queue subdirs
- clone repo 3 times
- write 3 task specs
- run scripts/run_task_queue_daemon.py with correct tokens:
  - --max-jobs 3
  - --max-seconds-total 900
  - --max-cycles 1
  - --live-timeout-seconds 180
  - --sandbox-commit-tag

3. Inspect:
- daemon stdout JSON
- daemon run report
- each task run_report.json
- each task loop/autonomous_live_loop_state.json
- queue pending/running/done/failed
- each sandbox repo git status/log/tag
- generated artifact find for __pycache__/*.pyc/*.pyo
- required text grep for all 3 task functions

4. Strict gate assertions:
For every task:
- if effect status contains failed/non-passed, assert no commit/tag and queue failed
- if status success, assert effect statuses all passed and commit/tag occurred
- no task with failed effect may be in queue done
- no task with failed effect may have sandbox commit/tag

5. Optional direct regression:
If all 3 real tasks pass effects, also confirm existing Prompt638B regression proof remains available in the Prompt638B report and mention that failed-effect path is already proven by Prompt638B.
Do not invent a fake failed live task unless the existing tooling provides a safe deterministic way.

Required report:
Write:
- artifacts/autonomous_runtime/prompt638d_real_batch_reacceptance_after_strict_gate_report.json
- artifacts/autonomous_runtime/prompt638d_real_batch_reacceptance_after_strict_gate_summary.md

Required report fields:
- prompt638d_status
- prompt638d_base_commit
- prompt638d_base_tags_at_head
- prompt638d_work_root
- prompt638d_daemon_status
- prompt638d_jobs_processed
- prompt638d_queue_done_count
- prompt638d_queue_failed_count
- prompt638d_task_results
- prompt638d_successful_task_count
- prompt638d_failed_or_blocked_task_count
- prompt638d_effect_passed_success_count
- prompt638d_effect_failed_correctly_blocked_count
- prompt638d_effect_failed_wrongly_succeeded_count
- prompt638d_commit_tag_correct_for_passed_tasks
- prompt638d_commit_tag_blocked_for_failed_tasks
- prompt638d_sandbox_final_clean_all_applicable
- prompt638d_generated_artifacts_leftover_count
- prompt638d_main_repo_head_unchanged
- prompt638d_main_repo_source_modified
- prompt638d_main_repo_stage_performed
- prompt638d_main_repo_commit_performed
- prompt638d_main_repo_tag_performed
- prompt638d_archive_touched
- prompt638d_handoff_reports_touched
- prompt638d_reacceptance_decision
- prompt638d_remaining_gaps
- prompt638d_next_action

Decision rules:
- If no strict gate violation is found:
  prompt638d_status=success
  prompt638d_reacceptance_decision=accepted
- If any failed effect still reaches success/commit/tag/done:
  prompt638d_status=blocked
  prompt638d_reacceptance_decision=rejected
  prompt638d_next_action=fix_effect_gate_bypass
- If daemon cannot run due to external live Codex availability, but no source safety issue is found:
  prompt638d_status=partial
  prompt638d_reacceptance_decision=not_accepted_due_to_external_runtime
- If main repo is modified/staged/committed/tagged by runtime:
  prompt638d_status=blocked
  prompt638d_reacceptance_decision=rejected_main_repo_safety_violation

Expected final stdout:
Print only:
prompt638d_status=<success|blocked|partial>
prompt638d_reacceptance_decision=<accepted|rejected|not_accepted_due_to_external_runtime|rejected_main_repo_safety_violation>
prompt638d_daemon_status=<success|blocked|failed|partial>
prompt638d_jobs_processed=<int>
prompt638d_successful_task_count=<int>
prompt638d_failed_or_blocked_task_count=<int>
prompt638d_effect_failed_wrongly_succeeded_count=<int>
prompt638d_main_repo_head_unchanged=<true|false>
prompt638d_sandbox_final_clean_all_applicable=<true|false>
prompt638d_generated_artifacts_leftover_count=<int>
prompt638d_next_action=<prompt639_expand_task_kinds|prompt639_multi_cycle_targeted_fix_acceptance|fix_effect_gate_bypass|manual_review_required>
prompt638d_report_path=<path>
prompt638d_summary_path=<path>
