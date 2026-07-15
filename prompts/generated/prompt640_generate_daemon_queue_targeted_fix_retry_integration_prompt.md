PROMPT640_GENERATE_DAEMON_QUEUE_TARGETED_FIX_RETRY_INTEGRATION_PROMPT

Repository:
- /home/rai/codex-local-runner

Goal:
Generate the next implementation prompt file for Prompt640.

The generated Prompt640 must implement:
daemon_queue_targeted_fix_retry_integration

This is prompt-generation only.
Do not implement Prompt640.
Do not modify source code.
Do not run runtime daemon jobs.
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
- Current repo: /home/rai/codex-local-runner
- Current branch: local/prompt299-one-cycle-controller-v1
- Current committed/tagged state:
  - commit: 714bb11
  - tag: prompt639-multi-cycle-targeted-fix-acceptance
- Prompt639 was accepted:
  - prompt639_status=success
  - prompt639_acceptance_decision=accepted
  - prompt639_jobs_processed=4
  - prompt639_successful_task_count=3
  - prompt639_failed_or_blocked_task_count=1
  - prompt639_targeted_fix_triggered=true
  - prompt639_targeted_fix_resolved=true
  - prompt639_targeted_fix_fix_attempts_used=1
  - prompt639_effect_failed_wrongly_succeeded_count=0
  - prompt639_strict_gate_violations=0
  - prompt639_main_repo_head_unchanged_during_runtime=true
  - prompt639_sandbox_cleanup_ok=true
  - prompt639_generated_artifacts_leftover_count=0
  - prompt639_archive_touched=false
  - prompt639_handoff_reports_touched=false

Important interpretation:
Prompt639 proved:
1. daemon queue can process multiple real tasks.
2. successful passed-effect tasks can become success + sandbox commit/tag + queue done.
3. deterministic failed-effect task is safely blocked with no commit/tag.
4. run_targeted_fix_retry is proven standalone:
   - attempt 0 failed effect
   - attempt 1 targeted fix resolved it
5. But daemon queue runner is not yet wired to invoke run_targeted_fix_retry automatically.

Therefore Prompt640 should integrate targeted fix retry into the daemon queue runner.

Required work for this prompt-generation task:
1. Inspect the repo enough to generate an accurate implementation prompt.
2. Inspect at minimum:
   - scripts/run_task_queue_daemon.py
   - automation/orchestration/planned_runner/autonomous_live_loop.py
   - automation/orchestration/planned_runner/autonomous_cycle.py
   - automation/orchestration/planned_runner/effect_gate.py
   - any module/function implementing run_targeted_fix_retry
   - existing tests related to daemon queue, targeted fix retry, strict effect gate, sandbox commit/tag, cleanup, and Prompt639
   - artifacts/autonomous_runtime/prompt639_report.json
   - artifacts/autonomous_runtime/prompt639_summary.md
3. Determine the exact Prompt640 implementation scope.
4. Generate a complete Prompt640 implementation prompt at:
   - prompts/generated/prompt640_daemon_queue_targeted_fix_retry_integration.md
5. The generated Prompt640 must be executable by Claude Code and must include:
   - goal
   - current state
   - root gap
   - exact implementation requirements
   - safety constraints
   - expected files likely to modify
   - required tests
   - bounded runtime validation
   - report requirements
   - final stdout contract
   - decision rules
6. Do not over-broaden Prompt640 into task kind expansion.
7. Do not implement Prompt640 in this run.

Prompt640 required target behavior:
The daemon queue runner must automatically invoke targeted fix retry when a task fails due to effect verification failure and a fix attempt is allowed.

Expected behavior after Prompt640:
1. Passed-effect task:
   - success
   - sandbox commit/tag
   - queue done

2. Initial effect-failed task that targeted fix resolves:
   - initial failed effect is never success
   - targeted fix retry is invoked automatically by daemon queue runner
   - final fixed effect passes
   - sandbox commit/tag occurs only after fixed effect passes
   - queue done

3. Initial effect-failed task that targeted fix cannot resolve:
   - no sandbox commit/tag
   - queue failed
   - failure digest/report preserved
   - strict gate violations=0

4. Runtime safety:
   - main repo HEAD unchanged during runtime
   - runtime uses /tmp clones/sandboxes
   - artifacts/archive untouched
   - handoff_reports untouched
   - generated Python artifacts cleaned
   - no failed effect wrongly succeeds

Generated Prompt640 must include required tests such as:
- daemon queue invokes targeted fix retry on effect failure
- targeted fix resolved task becomes done only after fixed effect passed
- targeted fix unresolved task remains failed with no commit/tag
- strict effect gate remains enforced after retry integration
- main repo safety remains true
- no generated artifact leftovers

Generated Prompt640 must not require:
- expanding task kinds
- long-running daemon soak
- external network
- push/PR/release
- real remote operations
- modifying artifacts/archive
- modifying handoff_reports

Required output files from this prompt-generation run:
- prompts/generated/prompt640_daemon_queue_targeted_fix_retry_integration.md
- artifacts/autonomous_runtime/prompt640_prompt_generation_report.json
- artifacts/autonomous_runtime/prompt640_prompt_generation_summary.md

Required report fields:
- prompt640_generator_status
- prompt640_generator_base_commit
- prompt640_generator_tags_at_head
- prompt640_generator_prompt_path
- prompt640_generator_prompt_created
- prompt640_generator_repo_inspected_files
- prompt640_generator_prompt_scope
- prompt640_generator_excluded_scope
- prompt640_generator_recommended_files_to_modify_by_prompt640
- prompt640_generator_recommended_tests_for_prompt640
- prompt640_generator_safety_constraints_included
- prompt640_generator_final_decision
- prompt640_generator_next_action

Expected final stdout:
Print only:
prompt640_generator_status=<success|blocked|partial>
prompt640_generator_prompt_path=prompts/generated/prompt640_daemon_queue_targeted_fix_retry_integration.md
prompt640_generator_recommended_next_action=execute_prompt640_daemon_queue_targeted_fix_retry_integration
prompt640_generator_report_path=artifacts/autonomous_runtime/prompt640_prompt_generation_report.json
prompt640_generator_summary_path=artifacts/autonomous_runtime/prompt640_prompt_generation_summary.md
