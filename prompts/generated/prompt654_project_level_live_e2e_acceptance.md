PROMPT654_PROJECT_LEVEL_LIVE_E2E_ACCEPTANCE

Repository:
- /home/rai/codex-local-runner

## Goal
Prove, in a bounded /tmp environment, that the project-level LIVE loop runs end to end:
ProjectIntent → structured descriptors → ProjectTaskPlan → explicit /tmp queue dir →
Prompt653 live bridge → bounded daemon/Codex execution → REAL run_report ingestion →
completion gate → project final status. Operator-triggered, dry-run-default, safe.

This is an EXECUTION task: implement the harness + tests, run unit tests, then run ONE
bounded live acceptance under the explicit safety gate.

## Current state
HEAD 7d4cff1, tag prompt653-live-auto-execution-bridge. The live bridge
`run_project_live_execution_bridge(intent, task_descriptors, output_queue_dir, *,
enable_live, enable_token, expected_enable_token, max_project_cycles, max_daemon_jobs,
max_fix_attempts, repo_path_override, dry_run, daemon_runner)` exists and is fake-adapter
tested (dry-run default; token+dir+bounds gated; real run_report ingestion; failures
never complete). Real run of the daemon happens via the bridge's default adapter.

## Scope (acceptance harness ONLY)
- scripts/run_project_level_live_e2e_acceptance.py — operator CLI + a testable core
  function (inject `bridge_runner` and `cloner` for tests).
- tests/test_project_level_live_e2e_acceptance.py — non-live tests (fake bridge/cloner).
- report/summary artifacts.
Additive only; do NOT modify protected modules (bridge, daemon, gate, task_spec, etc.).

## Required harness behavior (core function, e.g. run_live_e2e_acceptance(...))
- Inputs: repo (source to clone), work_root (/tmp), queue_dir (/tmp), enable_live,
  enable_token, expected token = I_UNDERSTAND_THIS_RUNS_LIVE_CODEX, max_project_cycles,
  max_daemon_jobs, max_fix_attempts, dry_run (default True), injectable bridge_runner +
  cloner.
- Safety validation FIRST (never raises): work_root AND queue_dir MUST be under /tmp;
  otherwise blocked. The source repo must exist.
- Clone the source repo into work_root (git clone --no-hardlinks; via injectable
  cloner). Build a ProjectIntent whose repo_target is the /tmp CLONE path, plus a
  minimal add_function descriptor on a harmless existing file in the clone
  (function_name deterministic, expression "a + b", cheap py_compile verify command).
- Capture the SOURCE (main) repo HEAD before and after; assert unchanged.
- Call bridge_runner(intent, descriptors, queue_dir, enable_live=..., enable_token=...,
  max_project_cycles=..., max_daemon_jobs=..., max_fix_attempts=..., dry_run=...).
- Dry-run by default → no daemon/Codex; report dry_run success. Live path only when
  dry_run=False AND enable_live=True AND token matches AND queue/work under /tmp AND
  bounded caps. Outcomes come ONLY from the bridge's real run_report ingestion. Failures
  never mark complete. Unreliable parsing → manual_review_required.
- Return structured result with all required report fields (below).

## Live acceptance policy (run ONCE, bounded)
Run live only if: harness + tests written, all unit tests pass, /tmp clone/sandbox only,
dry_run=False, enable_live=True, token == I_UNDERSTAND_THIS_RUNS_LIVE_CODEX, explicit
/tmp queue dir, max_project_cycles<=1, max_daemon_jobs<=1, max_fix_attempts<=1, main repo
HEAD verified unchanged, no default/live queue mutated, artifacts/archive +
handoff_reports untouched. If any unmet or live Codex unavailable / run_report unparseable
→ status partial|blocked, do NOT claim success, do NOT create the success tag.

## Required tests (non-live; fake bridge + fake cloner)
- dry-run default does not invoke the live bridge's daemon (bridge_runner called with
  dry_run True / not at all in live mode)
- live mode requires token (wrong/missing → blocked, no live)
- live mode requires explicit /tmp queue dir (non-/tmp → blocked)
- live mode requires /tmp clone/sandbox (non-/tmp work_root → blocked)
- bad/missing run_report (fake bridge returns partial) never marks complete
- fake successful bridge result marks complete only via completion gate result
- fake failed bridge result does not mark complete
- bounded caps enforced/clamped
- no main-repo mutation during non-live tests
- generated report has all required fields
Run: tests.test_project_level_live_e2e_acceptance + the existing project-layer + daemon
+ targeted_fix suites.

## Required live command (after unit tests pass)
python scripts/run_project_level_live_e2e_acceptance.py --repo /home/rai/codex-local-runner
  --work-root /tmp/codex-local-runner-prompt654-live-e2e
  --queue-dir /tmp/codex-local-runner-prompt654-live-e2e/queue
  --enable-live --enable-token I_UNDERSTAND_THIS_RUNS_LIVE_CODEX
  --max-project-cycles 1 --max-daemon-jobs 1 --max-fix-attempts 1

## Hard safety boundaries
No push/PR/merge/delete; no artifacts/archive; no handoff_reports; no secrets/.env; no
network beyond what the existing gated Codex/daemon path performs; no default/live queue
mutation; no uncontrolled loops; no strict-gate bypass; no invented success; no task-kind
expansion; no soak; no arbitrary shell outside the daemon/effect-gated path; do NOT mark
project-level autonomy complete unless real live E2E proves it.

## Report fields (prompt654_report.json + goal_aligned report)
prompt654_status, current_head_before, selected_target, prompt_generated,
implementation_performed, live_e2e_harness_created, dry_run_default_proven,
live_gate_required, tmp_clone_or_sandbox_used, explicit_tmp_queue_used,
bounded_live_execution_used, real_daemon_execution_attempted, real_run_report_ingested,
completion_gate_evaluated_real_outcomes, failure_never_marked_complete,
main_repo_head_unchanged_during_live_run, protected_paths_untouched, tests_run,
tests_passed, live_acceptance_status, files_modified, commit, tag,
current_capability_boundary_after, project_level_autonomy_complete,
evaluation_score_out_of_100, next_recommended_action, final_decision.

## Decision / commit-tag
PASS (status success) requires: prompt generated; harness+tests created; unit tests pass;
one bounded /tmp live acceptance run that attempts real daemon execution and ingests a
REAL run_report into the completion gate; completion based on real outcome; failures
proven not to mark complete; main repo HEAD unchanged by the live run; protected paths
untouched. Then commit "prompt654 project level live e2e acceptance" + tag
prompt654-project-level-live-e2e-acceptance. If live Codex unavailable or run_report
unparseable → status partial|blocked, no success tag, next_action
manual_review_required|fix_live_e2e_acceptance.
