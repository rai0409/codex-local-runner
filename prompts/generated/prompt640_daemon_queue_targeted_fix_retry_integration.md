PROMPT640_DAEMON_QUEUE_TARGETED_FIX_RETRY_INTEGRATION

Repository:
- /home/rai/codex-local-runner

## Goal
Wire the standalone targeted-fix retry capability into the daemon queue runner so
that a queued task which fails effect verification is automatically retried via
`run_targeted_fix_retry`, under the existing Prompt638B strict effect gate, and is
committed/tagged ONLY after a fixed effect strictly passes.

This is an EXECUTION task (implement + test + bounded-validate + report). It is not
a design or analysis task.

## Current state (confirmed)
- Branch: local/prompt299-one-cycle-controller-v1
- HEAD: 714bb11, tag: prompt639-multi-cycle-targeted-fix-acceptance
- Prompt638B strict effect gate is committed and enforced at three layers
  (autonomous_cycle._result_status, autonomous_live_loop final status,
  run_task_queue_daemon._process_task).
- Prompt639 proved (all PASS, accepted):
  - The daemon queue (`scripts/run_task_queue_daemon.py`) processes multiple real
    /tmp tasks; passed-effect tasks become success + sandbox commit/tag + queue
    done; a deterministic failed-effect task is blocked with no commit/tag and
    routed to queue failed.
  - `automation/orchestration/planned_runner/targeted_fix_retry.run_targeted_fix_retry`
    works STANDALONE: attempt 0 effect-failed (never marked success), attempt 1
    fix resolved it (effect passed), with no commit/tag.

## Root gap
`scripts/run_task_queue_daemon.py::_process_task` executes a task with
`run_autonomous_live_loop` only. On effect-verification failure it stops at the
strict effect gate (stage="effect_verification_gate", status="blocked") and returns
— it never invokes `run_targeted_fix_retry`. So the daemon cannot auto-recover a
task whose first attempt fails effect verification, even though the retry mechanism
exists and is proven. Prompt640 closes this single integration gap.

## Exact implementation requirements

1. Add a bounded daemon CLI option for fix attempts:
   - Add `--max-fix-attempts` to the argparser in `main()` (default 0).
   - Clamp it to `automation.orchestration.planned_runner.targeted_fix_retry.MAX_FIX_ATTEMPTS_CAP`
     (currently 2). Negative values clamp to 0.
   - `--max-fix-attempts 0` MUST preserve today's behavior exactly (no retry,
     backward compatible). Retry is opt-in.
   - Thread the clamped value into `_process_task` (e.g. via `args`).

2. Integrate targeted fix retry into `_process_task` after the strict effect gate
   detects an effect-verification failure (the existing block at the
   `if not effect_gate["passed"]:` branch, ~lines 175-185):
   - If `args.max_fix_attempts <= 0`: keep current behavior (blocked, no commit/tag,
     queue failed).
   - If `args.max_fix_attempts > 0` AND the failure is a retryable effect
     verification failure: invoke
     `run_targeted_fix_retry(generated_prompt_path=plan["generated_prompt_path"],
     effect_spec_path=plan["effect_spec_path"], out_dir=run_dir/"targeted_fix",
     live_codex_enable_token=args.live_codex_enable_token,
     sandbox_mode="workspace-write", timeout_seconds=args.live_timeout_seconds,
     max_fix_attempts=args.max_fix_attempts)`.
   - The retry result is AUTHORITATIVE for the post-retry decision. Do NOT trust the
     prior loop status. Treat the task as recoverable only when the retry result is
     `converged is True` AND its final attempt `effect_verification_status == "passed"`.

3. Post-retry strict gate (must reuse `evaluate_strict_effect_gate`):
   - Build the post-retry per-cycle effect status list from the retry attempts
     (final attempt's effect status, or the full attempt sequence) and re-run
     `evaluate_strict_effect_gate(..., effect_expected=True)`.
   - Commit/tag and queue-done are allowed ONLY if the post-retry gate passes
     (converged + final effect passed). A failed/non-passed effect after retry MUST
     remain blocked with no commit/tag and queue failed.

4. Resolved path (initial effect-failed task that targeted fix resolves):
   - The initial failed effect is never reported as success.
   - After convergence, proceed through the SAME downstream steps as a normal
     success: sandbox cleanup (cleanup_generated_python_artifacts) BEFORE commit/tag
     and final clean check, then `execute_sandbox_commit_tag`, then
     `evaluate_sandbox_cleanliness`, then stage="done", status="success".
   - Sandbox commit/tag MUST occur only after the fixed effect passed.

5. Unresolved path (targeted fix cannot resolve):
   - No sandbox commit/tag.
   - status blocked/failed, stage e.g. "targeted_fix_unresolved".
   - Queue final path = failed; task must NOT be in done.
   - Preserve the failure digest / targeted_fix_retry_state.json path in the report.

6. run_report additions (record regardless of outcome when retry was attempted):
   - targeted_fix_invoked (bool)
   - targeted_fix_converged (bool)
   - targeted_fix_fix_attempts_used (int)
   - targeted_fix_codex_invoked_count (int)
   - targeted_fix_stop_reason (str)
   - targeted_fix_state_path (str)
   - post_retry_effect_gate_passed (bool)
   - post_retry_effect_statuses (list)
   - The existing fields (status, stage, sandbox_commit_performed,
     sandbox_tag_performed, per_cycle_effect_verification_statuses, queue_final_path)
     must remain accurate.

7. Recommended structure (implementer's choice, but keep it clean):
   - Prefer factoring the "passed effect -> cleanup -> commit/tag -> final clean ->
     done" tail into a helper reused by both the normal success path and the
     post-retry resolved path, to avoid divergence.
   - Do NOT double-commit. Do NOT run commit/tag more than once per task.
   - Keep `run_autonomous_live_loop` as the initial execution; only escalate to
     `run_targeted_fix_retry` on effect-verification failure when fix attempts > 0.

## Safety constraints (hard)
- Runtime tasks use ONLY /tmp clones/sandboxes.
- Do NOT modify the main repo working tree during runtime; main repo HEAD and the
  tag at HEAD must be unchanged across the runtime validation.
- No push, no PR, no merge, no remote operations, no network dependency.
- Do NOT touch artifacts/archive. Do NOT modify handoff_reports.
- Sandbox commit/tag remains /tmp-only and strict-gate-gated.
- No failed/non-passed effect may ever reach success, commit, tag, or queue done.
- Generated Python artifacts (__pycache__/*.pyc/*.pyo) must be cleaned from /tmp
  sandboxes before the final clean check.
- Respect the MAX_FIX_ATTEMPTS_CAP and the daemon's existing MAX_JOBS_CAP /
  MAX_CYCLES_CAP / MAX_SECONDS_TOTAL_CAP bounds. No unbounded loops.

## Expected files likely to modify
- scripts/run_task_queue_daemon.py (primary: arg, _process_task integration, report fields)
- (likely) a small shared helper for the success/commit/tag tail — either inside
  run_task_queue_daemon.py or a focused module under
  automation/orchestration/planned_runner/.
- No change required to targeted_fix_retry.py, effect_gate.py, autonomous_cycle.py,
  or autonomous_live_loop.py unless a minimal, well-justified hook is needed; if any
  is touched, keep it additive and backward compatible.

## Required tests (python -m unittest, /tmp sandboxes, mock live Codex where possible)
Add focused tests (suggested names):
- tests/test_daemon_queue_targeted_fix_retry_integration.py
  - daemon invokes targeted fix retry on an effect-verification failure when
    --max-fix-attempts > 0 (assert run_targeted_fix_retry called / targeted_fix_invoked=true).
  - resolved case: a task whose initial effect fails but targeted fix converges
    becomes status success, stage done, sandbox_commit_performed=true,
    sandbox_tag_performed=true, queue done — and commit/tag happened only after the
    fixed effect passed.
  - unresolved case: a task whose targeted fix never converges stays blocked/failed,
    sandbox_commit_performed=false, sandbox_tag_performed=false, queue failed, not in
    done, targeted_fix_state_path/failure digest preserved.
  - backward-compat: with --max-fix-attempts 0, behavior is identical to today
    (no retry invoked; effect-failed task blocked -> failed).
  - strict gate after retry: a retry that ends with a non-passed effect does NOT
    reach commit/tag/done (post_retry_effect_gate_passed=false).
- Ensure existing suites still pass:
  tests.test_daemon_queue, tests.test_daemon_queue_effect_failed_blocks_commit_tag,
  tests.test_targeted_fix_retry, tests.test_sandbox_commit_tag_gate,
  tests.test_autonomous_live_loop_effect_failed_blocks_success,
  tests.test_daemon_candidate_acceptance.
- Prefer mocking run_autonomous_live_loop and run_targeted_fix_retry in the daemon's
  namespace for deterministic unit tests; reserve live Codex for the bounded runtime
  validation only.

## Bounded runtime validation (live Codex, /tmp only)
Run a fresh /tmp work root (e.g. /tmp/prompt640_daemon_targeted_fix_integration) and:
- A resolved scenario: enqueue a task whose effect spec requires a marker the base
  generated prompt omits (mirror Prompt639 Part B), run the daemon with
  --max-fix-attempts 1 and --sandbox-commit-tag; assert it ends success + commit/tag
  + done after a targeted fix, with the initial effect failure never marked success.
- An unresolved scenario: enqueue a task with a deterministic always-failing verify
  command; run the daemon with --max-fix-attempts 1; assert it stays blocked/failed
  with no commit/tag and queue failed.
- Process >= 2 jobs total. Bounds: --max-jobs <=5, --max-cycles 1,
  --max-seconds-total <= 900, --live-timeout-seconds 180.
- Tokens: autonomous=LOCAL_AUTONOMOUS_RUNTIME_ENABLE,
  live=LOCAL_LIVE_CODEX_GATE_ENABLE, commit-tag=ENABLE_SANDBOX_COMMIT_TAG_EXECUTION.
- After the run: assert main repo HEAD unchanged, tag at HEAD unchanged, no main
  repo source modified, 0 leftover generated artifacts in sandboxes, artifacts/archive
  and handoff_reports untouched.
- If live Codex is unavailable, the unit tests (with mocked Codex) plus the
  deterministic always-fail path still constitute acceptance; record runtime as
  partial/not_run with reason and do not fabricate results.

## Report requirements
Write:
- artifacts/autonomous_runtime/prompt640_report.json
- artifacts/autonomous_runtime/prompt640_summary.md
Required report fields:
- prompt640_status
- prompt640_base_commit
- prompt640_base_tags_at_head
- prompt640_modified_files
- prompt640_new_files
- prompt640_daemon_invokes_targeted_fix_on_effect_failure
- prompt640_resolved_task_commit_tag_only_after_fixed_effect_passed
- prompt640_unresolved_task_blocked_no_commit_tag_queue_failed
- prompt640_backward_compatible_when_fix_attempts_zero
- prompt640_strict_gate_enforced_after_retry
- prompt640_effect_failed_wrongly_succeeded_count
- prompt640_strict_gate_violations
- prompt640_tests_added
- prompt640_tests_result
- prompt640_runtime_validation_status
- prompt640_runtime_jobs_processed
- prompt640_runtime_resolved_task_done
- prompt640_runtime_unresolved_task_failed
- prompt640_main_repo_head_unchanged
- prompt640_main_repo_source_modified
- prompt640_generated_artifacts_leftover_count
- prompt640_archive_touched
- prompt640_handoff_reports_touched
- prompt640_main_repo_commit_performed
- prompt640_main_repo_tag_performed
- prompt640_final_decision
- prompt640_next_action

## Final stdout contract
Print only:
prompt640_status=<success|blocked|partial>
prompt640_daemon_invokes_targeted_fix_on_effect_failure=<true|false>
prompt640_resolved_task_commit_tag_only_after_fixed_effect_passed=<true|false>
prompt640_unresolved_task_blocked_no_commit_tag_queue_failed=<true|false>
prompt640_backward_compatible_when_fix_attempts_zero=<true|false>
prompt640_strict_gate_enforced_after_retry=<true|false>
prompt640_effect_failed_wrongly_succeeded_count=<int>
prompt640_tests_result=<passed|failed|not_run>
prompt640_runtime_validation_status=<passed|partial|not_run>
prompt640_main_repo_head_unchanged=<true|false>
prompt640_generated_artifacts_leftover_count=<int>
prompt640_report_path=artifacts/autonomous_runtime/prompt640_report.json
prompt640_summary_path=artifacts/autonomous_runtime/prompt640_summary.md
prompt640_next_action=<commit_tag_daemon_queue_targeted_fix_retry_integration|fix_targeted_fix_integration_bypass|manual_review_required>

## Decision rules
- If the daemon auto-invokes targeted fix on effect failure, the resolved path
  commits/tags only after a strictly-passed fixed effect, the unresolved path stays
  failed with no commit/tag, --max-fix-attempts 0 is backward compatible, the strict
  gate is enforced after retry (effect_failed_wrongly_succeeded_count=0,
  strict_gate_violations=0), all tests pass, and main repo safety holds:
    prompt640_status=success
    prompt640_next_action=commit_tag_daemon_queue_targeted_fix_retry_integration
  (Commit + tag prompt640-daemon-queue-targeted-fix-retry-integration only if ALL
  PASS conditions are met, mirroring Prompt639's commit/tag policy.)
- If any failed/non-passed effect still reaches success/commit/tag/done after
  integration:
    prompt640_status=blocked
    prompt640_next_action=fix_targeted_fix_integration_bypass
- If the main repo is modified/staged/committed/tagged by runtime (not the final
  authorized result commit), or HEAD changes during runtime:
    prompt640_status=blocked
    prompt640_next_action=manual_review_required
- If live Codex is unavailable but unit tests + deterministic paths pass with no
  safety issue:
    prompt640_status=partial
    prompt640_runtime_validation_status=partial
    prompt640_next_action=manual_review_required

## Out of scope (do NOT do in Prompt640)
- Do NOT expand supported task kinds (add_function stays the only kind).
- Do NOT add long-running/unattended daemon soak.
- Do NOT add external network, push, PR, release, or real remote operations.
- Do NOT modify artifacts/archive or handoff_reports.
