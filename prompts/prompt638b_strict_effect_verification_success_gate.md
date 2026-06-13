PROMPT638B_STRICT_EFFECT_VERIFICATION_SUCCESS_GATE

Repository:
- /home/rai/codex-local-runner

Goal:
Implement a strict safety gate so that any failed effect verification prevents final task success, sandbox commit/tag, and queue done.

This fixes the confirmed Prompt638A general safety bug:
- effect_failed_not_gated_before_success_commit_tag

Confirmed Prompt638A result:
- prompt638a_status=success
- prompt638a_root_cause=effect_failed_not_gated_before_success_commit_tag
- prompt638a_general_safety_bug_confirmed=true
- recommended files:
  - automation/orchestration/planned_runner/autonomous_cycle.py
  - automation/orchestration/planned_runner/autonomous_live_loop.py
  - scripts/run_task_queue_daemon.py
- recommended tests:
  - tests/test_autonomous_cycle_result_status_failed_with_zero_returncode.py
  - tests/test_autonomous_live_loop_effect_failed_blocks_success.py
  - tests/test_daemon_queue_effect_failed_blocks_commit_tag.py

Problem to fix:
In Prompt638 real-task batch, Task1 had:
- status=success
- stage=done
- loop_status=success
- sandbox_commit_performed=true
- sandbox_tag_performed=true
- queue done
- but per_cycle_effect_verification_statuses=['failed']

This is unsafe.
A task must never be marked success if any effect verification failed.
A task must never be committed/tagged if any effect verification failed.
A task must never move to queue done if any effect verification failed.

Execution policy:
- Proceed autonomously.
- Do not ask for confirmation.
- Do not push.
- Do not PR.
- Do not merge.
- Do not touch artifacts/archive.
- Do not modify unrelated legacy summary files.
- Do not run unbounded loops.
- Do not auto-commit or auto-tag the main repo.
- Do not stage files.
- Runtime tests must use /tmp clones/sandboxes only.
- Main repo source may be modified only for this strict gate implementation, tests, and Prompt638B reports.

Implementation requirements:

1. Strict effect status helper
Add or reuse a focused helper that determines whether effect verification is strictly successful.

Required behavior:
- Empty per-cycle effect status list is not strict success when an effect spec was expected/run.
- Any status other than "passed" blocks success.
- Values such as "failed", "blocked", "not_run", "missing", "", null must block success.
- If a live loop state has effect verification details, final success must require all required effect statuses to be "passed".

2. autonomous_cycle.py
Ensure a cycle cannot produce a success classification if effect verification failed, even when:
- Codex returncode is 0
- Codex emitted a success-looking JSON response
- verify commands pass
- cleanup succeeds

Expected behavior:
- effect_verification_status="failed" leads to blocked/failed classification.
- next_action should indicate targeted fix or effect failure handling, not commit/tag.

3. autonomous_live_loop.py
Ensure final loop status cannot be "success" when any cycle has failed effect verification.

Expected behavior:
- final_status/status must be blocked or failed.
- stop_reason or blocked_reason must clearly mention effect verification failure.
- per_cycle_effect_verification_statuses must remain visible in state.
- codex_invoked_count should remain accurate.
- do not hide or rewrite failed effect status.

4. scripts/run_task_queue_daemon.py
Ensure daemon task final success requires strict effect success.

Required behavior:
- If the live loop reports any failed/non-passed effect verification:
  - task run_report status must be blocked or failed
  - stage must not be done
  - sandbox_commit_performed=false
  - sandbox_tag_performed=false
  - queue final path must be failed/
  - task must not move to done/
- sandbox commit/tag must be gated after strict effect success.
- final sandbox clean check may still run if safe, but must not turn failed effect into success.

5. Regression tests
Add the following tests or equivalent focused tests:

A. tests/test_autonomous_cycle_result_status_failed_with_zero_returncode.py
Must prove:
- Codex-like success/returncode 0 plus failed effect verification does not classify as success.

B. tests/test_autonomous_live_loop_effect_failed_blocks_success.py
Must prove:
- a live loop state with per_cycle_effect_verification_statuses containing "failed" cannot end as success.

C. tests/test_daemon_queue_effect_failed_blocks_commit_tag.py
Must prove:
- a task with failed effect verification:
  - is not committed
  - is not tagged
  - goes to queue failed
  - run_report status is blocked/failed
  - queue done remains empty for that task

Use python -m unittest, not pytest.

6. Real regression proof using Prompt638 Task1 pattern
Create a bounded /tmp regression scenario that intentionally fails effect verification but returns a success-looking Codex result or otherwise reproduces the unsafe condition without requiring network if possible.

If live Codex is required, run a bounded live test only in /tmp.

Required proof:
- Before fix behavior would have allowed success/commit/tag.
- After fix:
  - per_cycle_effect_verification_statuses contains failed
  - final task status is blocked/failed
  - sandbox_commit_performed=false
  - sandbox_tag_performed=false
  - queue failed contains the task
  - queue done does not contain the task

7. Re-run the Prompt638 no-Claude real-task batch if safe
After unit/regression tests pass, rerun the 3-task Prompt638 batch with correct tokens or an equivalent regenerated batch.

Expected:
- Tasks with passed effects succeed.
- Any task with failed effects is blocked/failed and not committed/tagged.
- If all 3 generated tasks now pass effects, all 3 can succeed.
- If Task1 still fails effect verification, that is acceptable only if it is not committed/tagged and goes to failed.

8. Validation commands
Run:
- python -m py_compile automation/orchestration/planned_runner/autonomous_cycle.py
- python -m py_compile automation/orchestration/planned_runner/autonomous_live_loop.py
- python -m py_compile scripts/run_task_queue_daemon.py
- python -m unittest tests.test_autonomous_cycle_result_status_failed_with_zero_returncode -v
- python -m unittest tests.test_autonomous_live_loop_effect_failed_blocks_success -v
- python -m unittest tests.test_daemon_queue_effect_failed_blocks_commit_tag -v
- run any existing related daemon queue / live loop tests that are directly affected.

Do not run full test suite if known unrelated legacy import errors still exist.

Required reports:
Write:
- artifacts/autonomous_runtime/prompt638b_strict_effect_verification_success_gate_report.json
- artifacts/autonomous_runtime/prompt638b_strict_effect_verification_success_gate_summary.md

Required report fields:
- prompt638b_status
- prompt638b_base_commit
- prompt638b_base_tags_at_head
- prompt638b_modified_files
- prompt638b_new_files
- prompt638b_root_cause_fixed
- prompt638b_general_safety_bug_fixed
- prompt638b_strict_effect_gate_added
- prompt638b_autonomous_cycle_fixed
- prompt638b_autonomous_live_loop_fixed
- prompt638b_daemon_queue_commit_tag_gate_fixed
- prompt638b_effect_failed_blocks_success
- prompt638b_effect_failed_blocks_commit
- prompt638b_effect_failed_blocks_tag
- prompt638b_effect_failed_goes_to_queue_failed
- prompt638b_tests_added
- prompt638b_tests_result
- prompt638b_regression_proof_status
- prompt638b_prompt638_batch_rerun_status
- prompt638b_prompt638_batch_successful_task_count
- prompt638b_prompt638_batch_failed_task_count
- prompt638b_main_repo_source_modified
- prompt638b_main_repo_commit_performed
- prompt638b_main_repo_tag_performed
- prompt638b_main_repo_stage_performed
- prompt638b_archive_touched
- prompt638b_artifact_paths
- prompt638b_final_decision
- prompt638b_next_action

Decision rules:
- If strict effect gate is implemented, tests pass, and failed effect no longer reaches success/commit/tag:
  - prompt638b_status=success
  - prompt638b_next_action=commit_tag_strict_effect_verification_success_gate
- If tests pass but Prompt638 batch still has failed tasks correctly blocked:
  - prompt638b_status=success
  - prompt638b_next_action=commit_tag_strict_effect_verification_success_gate
- If failed effect still reaches success or commit/tag:
  - prompt638b_status=blocked
  - prompt638b_next_action=fix_effect_gate_bypass
- If main repo commit/tag/stage occurs:
  - prompt638b_status=partial
  - prompt638b_next_action=manual_review_required

Expected final stdout:
Print only:
prompt638b_status=<success|blocked|partial>
prompt638b_effect_failed_blocks_success=<true|false>
prompt638b_effect_failed_blocks_commit=<true|false>
prompt638b_effect_failed_blocks_tag=<true|false>
prompt638b_tests_result=<passed|failed|not_run>
prompt638b_regression_proof_status=<passed|failed|not_run>
prompt638b_report_path=<path>
prompt638b_summary_path=<path>
prompt638b_next_action=<commit_tag_strict_effect_verification_success_gate|fix_effect_gate_bypass|manual_review_required>
