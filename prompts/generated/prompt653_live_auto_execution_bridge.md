PROMPT653_LIVE_AUTO_EXECUTION_BRIDGE

Repository:
- /home/rai/codex-local-runner

## Goal
Implement the live auto-execution bridge: the one missing layer that turns the proven
OFFLINE project chain into a real (but safe, operator-triggered, bounded) autonomous
loop. It connects:

  ProjectIntent + descriptors
    -> generate_project_task_plan (Prompt646)
    -> populate_queue_from_plan (Prompt647, explicit queue dir)
    -> [bounded, opt-in, token-gated daemon execution over that queue]
    -> read REAL run_reports
    -> map outcomes into evaluate_project_completion (Prompt648)
    -> project-level next decision

This is an EXECUTION task (implement + test + report). It MUST be dry-run by default
and MUST NOT run a live daemon/Codex in tests.

## Current state (confirmed)
- HEAD: 650c2b7; latest tagged implementation: prompt651. project_level_autonomy_complete=false.
- Capability boundary: offline_project_autonomy_chain_complete_and_e2e_proven_live_auto_execution_pending.
- Available building blocks (all present, tested, tagged):
  - generate_project_task_plan(intent, descriptors, *, generated_at) -> {status, errors, warnings, plan}
  - populate_queue_from_plan(plan, output_queue_dir, *, repo_path_override, create_dirs) -> {status, errors, warnings, output_dir, written_files, task_count}
  - evaluate_project_completion(plan, task_results=None, *, completion_criteria, required_task_ids) -> {status, complete, counts, task_states, ...}
  - run_project_loop(...) (Prompt649 offline controller)
- Daemon (`scripts/run_task_queue_daemon.py`):
  - `main(argv: list[str]|None) -> int` (exit code). Args: --queue-dir, --runs-dir,
    --work-dir, --max-jobs, --max-seconds-total, --max-cycles, --max-fix-attempts,
    --live-timeout-seconds, --autonomous-enable-token, --live-codex-enable-token,
    --sandbox-commit-tag, --commit-tag-enable-token, --json.
  - Writes `<runs-dir>/<task_filename_stem>/run_report.json` per task (each carries a
    clean `task_id`, `status`, `sandbox_commit_performed`, `per_cycle_effect_verification_statuses`,
    `targeted_fix_*`) and `<runs-dir>/daemon_run_report.json`.
  - Consumes `pending/*.json` in sorted order; strict effect gate + targeted-fix retry
    already wired (Prompt643/644a).
  - Live tokens: autonomous=LOCAL_AUTONOMOUS_RUNTIME_ENABLE, live=LOCAL_LIVE_CODEX_GATE_ENABLE.

## Root gap addressed
The controller stops at next_step=wait_for_execution_results and the completion gate
consumes SIMULATED results. Nothing runs the daemon over the populated queue and feeds
REAL run_reports back. This bridge closes that gap — safely.

## Scope (bridge layer ONLY)
Implement:
- automation/orchestration/planned_runner/project_live_execution_bridge.py
- the primary function `run_project_live_execution_bridge(...)` (signature below)
- a DRY-RUN-by-default path (plan + queue population + summary; NO daemon/Codex)
- a token-gated, bounded LIVE path that runs the daemon via an injectable adapter
- REAL run_report ingestion -> completion-gate mapping -> next project decision
- tests with a FAKE daemon adapter (no live daemon/Codex in tests)
- report/summary
Optionally (if justified): scripts/run_project_live_bridge.py (a thin operator CLI;
dry-run default, explicit flags for live). Keep it minimal or omit.

## Required primary function
```
run_project_live_execution_bridge(
    intent,
    task_descriptors,
    output_queue_dir,
    *,
    enable_live=False,
    enable_token="",
    expected_enable_token="I_UNDERSTAND_THIS_RUNS_LIVE_CODEX",
    max_project_cycles=1,
    max_daemon_jobs=1,
    max_fix_attempts=1,
    repo_path_override=None,
    dry_run=True,
    daemon_runner=None,
) -> dict
```
Structured return (always; never raises):
```
{
  "status": "success" | "blocked" | "partial",
  "live_execution_performed": bool,
  "dry_run": bool,
  "errors": [...],
  "warnings": [...],
  "queue_dir": "...",
  "plan_result": {...},               # generate_project_task_plan result
  "queue_population_result": {...},   # populate_queue_from_plan result
  "daemon_run_summary": {...},        # {} in dry-run; adapter summary + per-task statuses in live
  "completion_gate_result": {...},    # {} in dry-run; evaluate_project_completion result in live
  "project_complete": bool,
  "next_action": "complete" | "continue_project_loop" | "manual_review_required" | "blocked"
}
```

## Required behavior
- Always: validate intent + generate plan; if generation blocked -> status blocked,
  next_action manual_review_required, no queue written.
- Always: populate the EXPLICIT output_queue_dir (no live/default fallback). If
  output_queue_dir is empty/None -> blocked.
- DRY-RUN (default, or whenever any live precondition is unmet): produce plan_result +
  queue_population_result + a daemon_run_summary describing what WOULD run; set
  live_execution_performed=false, project_complete=false, next_action
  continue_project_loop (or manual_review_required if plan/queue blocked). DO NOT run
  the daemon/Codex.
- LIVE path requires ALL of: dry_run=False AND enable_live=True AND
  enable_token == expected_enable_token AND a non-empty explicit output_queue_dir AND
  bounded positive max_project_cycles / max_daemon_jobs / max_fix_attempts. If ANY is
  unmet, fall back to DRY-RUN with a deterministic warning explaining which condition
  blocked live execution (status success or blocked as appropriate; never silently
  "succeed" as if live ran).
- Bounds: clamp max_project_cycles / max_daemon_jobs / max_fix_attempts to existing
  daemon caps (MAX_JOBS_CAP / MAX_CYCLES_CAP and MAX_FIX_ATTEMPTS_CAP). NEVER an
  uncontrolled loop.
- daemon_runner adapter: a callable invoked in the LIVE path to run the bounded daemon
  over the queue dir; default = a real adapter that calls
  scripts.run_task_queue_daemon.main with a bounded argv (explicit queue/runs/work dirs
  under output_queue_dir's parent or a sibling runs dir, --max-jobs, --max-cycles,
  --max-fix-attempts, --sandbox-commit-tag, the live tokens). Tests MUST inject a FAKE
  adapter; the real adapter boundary must be explicit and isolated so tests never touch
  live Codex/daemon.
- Outcome ingestion: after the adapter runs, read the per-task run_reports (each
  run_report.json under the runs dir). Map by run_report["task_id"] (the CLEAN id,
  which equals the plan task_id) -> status: run_report.status == "success" -> "done";
  "blocked"/"failed" -> "failed"; missing/unreadable -> "unknown". Build a task_results
  dict and call evaluate_project_completion(plan, task_results).
- Safe parsing: if run_reports are missing/unreadable/ambiguous, mark affected tasks
  "unknown" and DO NOT mark the project complete; surface a warning; status "partial".
- Failure outcomes NEVER produce project_complete=true (the completion gate already
  enforces this; the bridge must not override it).
- project_complete = completion_gate_result["complete"]; next_action:
  complete if project_complete; continue_project_loop if in_progress; fix_failures ->
  represent as manual_review_required or continue_project_loop per status; blocked/failed
  -> manual_review_required.
- Bounded iterate: across up to max_project_cycles, the bridge may re-run the bounded
  daemon over remaining not-done tasks; stop as soon as complete/failed/blocked or
  cycles exhausted. (A single live daemon invocation per cycle; no nested unbounded loop.)
- DETERMINISTIC dry-run output for identical inputs (no Date.now()/random in the
  dry-run path; any timestamp is an input).

## Integration boundary (hard — do NOT cross)
- DRY-RUN by default; live path strictly gated by all preconditions above.
- Never mutate a live/default queue; only the explicit output_queue_dir (and a sibling
  runs/work dir derived from it or caller-provided).
- Never bypass the strict effect gate (the daemon enforces it; the bridge must not
  re-classify a failed task as success).
- Never invent success from queue files or plan generation alone — only REAL
  run_reports may mark tasks done.
- Tests MUST use a fake daemon adapter; NO live daemon/Codex/network in tests.
- Additive only: do NOT modify daemon_queue.py / task_spec.py / effect_gate.py /
  run_task_queue_daemon.py behavior (importing main is fine). Do NOT expand task kinds.

## Required tests (python -m unittest; fake adapter; tmpdirs only)
tests/test_project_live_execution_bridge.py must cover:
- dry_run=True (default): plan + queue summary produced, live_execution_performed=false,
  no daemon adapter invoked, deterministic output
- enable_live=False blocks live execution (falls back to dry-run with a warning)
- wrong/missing enable_token blocks live execution
- missing/empty output_queue_dir blocks (status blocked, no queue written)
- live path with a FAKE adapter that writes success run_reports -> outcomes feed the
  completion gate -> project can be project_complete=true, next_action=complete
- live path with a FAKE adapter that writes a failed run_report -> project_complete=false,
  failure never marked complete, next_action manual_review_required/continue
- missing/unreadable run_report -> task "unknown", project not complete, status partial
- bounds: max_project_cycles / max_daemon_jobs / max_fix_attempts clamped; no uncontrolled loop
- deterministic dry-run output for identical inputs
- no live daemon/Codex/network/git side effects (assert adapter is the fake; only
  explicit tmp dirs written)
- existing project-layer tests remain green
Run at least:
- tests.test_project_live_execution_bridge, tests.test_project_loop_controller,
  tests.test_project_completion_gate, tests.test_project_queue_population_from_plan,
  tests.test_project_task_generator_from_intent, tests.test_project_intent_plan_model,
  tests.test_daemon_queue, tests.test_targeted_fix_retry

## Hard safety boundaries (forbidden)
push / PR / merge; touching artifacts/archive; modifying handoff_reports; reading or
printing secrets; modifying .env files; network operations; uncontrolled daemon loops;
live/default queue mutation; live daemon/Codex in tests; bypassing the strict effect
gate; inventing success without real run_reports; task-kind expansion; long-running soak.

## Report requirements
Write:
- artifacts/autonomous_runtime/prompt653_report.json
- artifacts/autonomous_runtime/prompt653_summary.md
- artifacts/autonomous_runtime/prompt653_goal_aligned_implementation_report.json
- artifacts/autonomous_runtime/prompt653_goal_aligned_implementation_summary.md
Each must record: status, base/head, files_modified, tests_run/passed, dry_run_default
proven, live_path_gating proven, fake_adapter_used, real_run_report_ingestion proven,
failure_never_complete proven, bounded proven, no_side_effects, commit, tag,
confirmed/missing capabilities after, project_level_autonomy_complete, evaluation score,
next_recommended_action, final_decision.

## Final stdout contract
Print only:
prompt653_status=<success|partial|blocked>
prompt653_live_execution_bridge_created=<true|false>
prompt653_dry_run_default_proven=<true|false>
prompt653_live_path_gated_proven=<true|false>
prompt653_real_run_report_ingestion_proven=<true|false>
prompt653_failure_never_marked_complete_proven=<true|false>
prompt653_bounded_execution_proven=<true|false>
prompt653_no_execution_side_effects_in_tests=<true|false>
prompt653_existing_project_layer_tests_passed=<true|false>
prompt653_files_modified=<list>
prompt653_commit=<commit_hash_if_committed|none>
prompt653_tag=<tag_if_created|none>
prompt653_report_path=artifacts/autonomous_runtime/prompt653_report.json
prompt653_summary_path=artifacts/autonomous_runtime/prompt653_summary.md
prompt653_next_action=<project_level_live_e2e_acceptance|task_kind_expansion_minimal_safe|fix_live_auto_execution_bridge|manual_review_required>

## Decision rules
- If the bridge is created, dry-run is the default and proven, the live path is strictly
  gated (enable_live + token + explicit dir + bounds), a fake-adapter live run ingests
  REAL run_reports into the completion gate, failures never mark complete, bounds hold,
  tests have no live side effects, and existing project-layer tests pass:
    prompt653_status=success
    prompt653_next_action=project_level_live_e2e_acceptance
  (Commit + tag prompt653-live-auto-execution-bridge ONLY if ALL PASS.)
- If a bridge test fails or gating is not enforced:
    prompt653_status=partial|blocked
    prompt653_next_action=fix_live_auto_execution_bridge
- If existing project-layer tests regress, main-repo safety is violated, or any live
  daemon/Codex ran in tests:
    prompt653_status=blocked
    prompt653_next_action=manual_review_required

## Commit/tag policy
Commit/tag ONLY if all PASS. Stage only the new bridge source, the new test, the
prompt653 report/summary + goal-aligned report/summary (+ optional CLI + this prompt).
Do NOT stage artifacts/archive or handoff_reports.
Suggested commit message: "prompt653 live auto execution bridge"
Suggested tag: prompt653-live-auto-execution-bridge

## Out of scope (do NOT do in Prompt653)
- Running an actual live daemon/Codex in tests or CI
- Task-kind expansion
- Long-running daemon soak
- Any network/git runtime beyond the final local commit/tag on all-PASS
