PROMPT644A_CURRENT_CAPABILITY_ACCEPTANCE_RUN

Repository:
- /home/rai/codex-local-runner

Goal:
Confirm the currently implemented codex-local-runner capabilities after Prompt643 by running a bounded current-capability acceptance test.

This is validation-only.
Do not implement new features.
Do not modify source code.
Do not stage source changes.
Do not commit source changes unless the prompt explicitly says all PASS and only report/prompt artifacts are being recorded.
Do not push.
Do not PR.
Do not merge.
Do not touch artifacts/archive.
Do not modify handoff_reports.
Proceed autonomously without asking for confirmation.

Current confirmed baseline:
- Branch: local/prompt299-one-cycle-controller-v1
- Latest accepted implementation:
  - commit: 128d1dd
  - tag: prompt643-daemon-queue-targeted-fix-retry-integration
- Prompt643 implemented:
  - daemon queue runner can invoke run_targeted_fix_retry automatically
  - opt-in --max-fix-attempts
  - strict effect gate remains authoritative
  - tests passed
  - main repo safe

User goal:
Eventually reach project-level autonomous development:
project intent -> task planning -> queue execution -> verification -> targeted fix -> commit/tag -> next task -> completion.

Before building the project planner stack, confirm the current execution/self-healing layer actually works end-to-end.

Required validation:

1. Baseline checks
- Print/record HEAD commit and tags at HEAD.
- Confirm working tree source files are clean or record any untracked report/prompt artifacts.
- Confirm artifacts/archive and handoff_reports are not modified by this validation.
- Confirm Python compile/import smoke for relevant modules.

2. Unit/regression tests
Run bounded relevant tests, at minimum:
- tests/test_daemon_queue_targeted_fix_retry_integration.py
- tests/test_daemon_queue_effect_failed_blocks_commit_tag.py
- tests/test_targeted_fix_retry.py
- tests/test_sandbox_commit_tag_gate.py
- tests/test_autonomous_live_loop_effect_failed_blocks_success.py

If the repo has a known targeted test command for daemon candidate acceptance, run it too.
Do not run unbounded daemon loops.

3. Live /tmp current-capability acceptance
Use only /tmp clones/sandboxes.
Create a fresh work root:
- /tmp/prompt644a_current_capability_acceptance

Run daemon queue with Prompt643 capabilities enabled:
- --max-fix-attempts 1
- sandbox commit/tag enabled
- bounded jobs/cycles/seconds
- no remote operations

Use the existing supported task kind only.
Do not expand task kinds.

Create at least three queued jobs:
A. Passed-effect task:
   - should pass on first attempt
   - expected: success + sandbox commit/tag + queue done

B. Resolved self-healing task:
   - first attempt should fail effect verification
   - daemon should automatically invoke targeted fix retry
   - final fixed effect should pass
   - expected: success + sandbox commit/tag + queue done
   - assert commit/tag happens only after the fixed effect passes

C. Unresolved failed task:
   - deterministic always-failing effect
   - targeted fix may be attempted but must not converge
   - expected: queue failed + no sandbox commit/tag + no queue done

4. Strict safety assertions
Assert:
- effect_failed_wrongly_succeeded_count == 0
- strict_gate_violations == 0
- unresolved failed task has no commit/tag
- resolved task has post-retry passed effect before commit/tag
- main repo HEAD unchanged during runtime
- main repo tag at HEAD unchanged during runtime
- runtime work happened only in /tmp
- generated Python artifacts leftover count == 0
- artifacts/archive untouched
- handoff_reports untouched

5. Current capability classification
Classify current capability after validation:
- L7.5_confirmed
- L8_candidate_blocked_by_project_planner
- blocked
- partial

Use L7.5_confirmed if:
- multiple queue tasks processed
- daemon self-healing path works
- strict gates hold
- main repo safety holds
- task kinds remain limited and project planner is absent

Use L8_candidate_blocked_by_project_planner only if all execution/self-healing acceptance passes and the only major missing layer is project-level planner/orchestrator.

6. Report requirements
Write:
- artifacts/autonomous_runtime/prompt644a_current_capability_acceptance_report.json
- artifacts/autonomous_runtime/prompt644a_current_capability_acceptance_summary.md

Required report fields:
- prompt644a_status
- prompt644a_base_commit
- prompt644a_tags_at_head
- prompt644a_tests_result
- prompt644a_runtime_validation_status
- prompt644a_jobs_processed
- prompt644a_passed_effect_task_done
- prompt644a_resolved_self_healing_task_done
- prompt644a_unresolved_task_failed
- prompt644a_targeted_fix_invoked
- prompt644a_targeted_fix_resolved
- prompt644a_resolved_commit_tag_only_after_fixed_effect_passed
- prompt644a_unresolved_no_commit_tag
- prompt644a_effect_failed_wrongly_succeeded_count
- prompt644a_strict_gate_violations
- prompt644a_main_repo_head_unchanged_during_runtime
- prompt644a_main_repo_source_modified
- prompt644a_generated_artifacts_leftover_count
- prompt644a_archive_touched
- prompt644a_handoff_reports_touched
- prompt644a_current_capability_classification
- prompt644a_confirmed_capabilities
- prompt644a_remaining_gaps
- prompt644a_next_recommended_prompt
- prompt644a_final_decision

7. Commit/tag policy
This validation should not modify source.
If and only if all PASS conditions are met, you may commit/tag ONLY the validation prompt/report/summary artifacts for traceability.
Do not stage artifacts/archive.
Do not stage handoff_reports.
Suggested commit message:
- prompt644a confirm current self-healing daemon capabilities
Suggested tag:
- prompt644a-current-capability-acceptance

8. Final stdout contract
Print only:

prompt644a_status=<success|partial|blocked>
prompt644a_tests_result=<passed|failed|not_run>
prompt644a_runtime_validation_status=<passed|partial|failed|not_run>
prompt644a_jobs_processed=<int>
prompt644a_passed_effect_task_done=<true|false>
prompt644a_resolved_self_healing_task_done=<true|false>
prompt644a_unresolved_task_failed=<true|false>
prompt644a_targeted_fix_invoked=<true|false>
prompt644a_targeted_fix_resolved=<true|false>
prompt644a_effect_failed_wrongly_succeeded_count=<int>
prompt644a_strict_gate_violations=<int>
prompt644a_main_repo_head_unchanged_during_runtime=<true|false>
prompt644a_generated_artifacts_leftover_count=<int>
prompt644a_current_capability_classification=<L7.5_confirmed|L8_candidate_blocked_by_project_planner|partial|blocked>
prompt644a_commit=<commit_hash_if_committed|none>
prompt644a_tag=<tag_if_created|none>
prompt644a_report_path=artifacts/autonomous_runtime/prompt644a_current_capability_acceptance_report.json
prompt644a_summary_path=artifacts/autonomous_runtime/prompt644a_current_capability_acceptance_summary.md
prompt644a_next_recommended_prompt=<project_intent_schema_and_task_plan_model|fix_current_capability_regression|manual_review_required>
