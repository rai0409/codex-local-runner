# Prompt638b — Strict Effect-Verification Success Gate

**Status:** success
**Root cause fixed:** `effect_failed_not_gated_before_success_commit_tag` (Prompt638A)
**General safety bug fixed:** **true**
**Next action:** `commit_tag_strict_effect_verification_success_gate`

Base commit: `2a87cb17a999984c6b33b970201d8ed21178013f` (tag `codex-runner-fable-runtime-evidence-20260613`).
No main-repo commit / tag / stage performed. `artifacts/archive` untouched.

## What was broken (638A)

A Codex run that exited 0 (and emitted success-looking JSON) but **failed effect
verification** was promoted all the way to `status=success` + sandbox commit +
sandbox tag + queue `done`. Three layers each failed to gate on the effect
status. Prompt638 Task1 hit this exactly.

## The fix — defense in depth

A new shared helper `automation/orchestration/planned_runner/effect_gate.py`
(`evaluate_strict_effect_gate` / `strict_effect_success`) is the single source of
truth: any explicit hard-failure status blocks success unconditionally; when
effect verification is expected, **every** per-cycle status must be exactly
`passed` (empty / `not_run` / `""` / null all block); legacy no-effect-spec flows
stay green when no hard failure is present.

Three gating points now consume it:

1. **`autonomous_cycle._result_status`** — explicit `failed` status/classification
   and any non-`passed` `effect_verification_status` are evaluated **before** the
   `returncode==0 → success` shortcut. A zero exit code can no longer override an
   effect failure. → the cycle classifies as failed, not `codex_result_success`.

2. **`autonomous_live_loop`** — after the cycle loop, the strict gate runs over
   `per_cycle_effect_verification_statuses` (`effect_expected` = an effect spec was
   provided directly or per manifest). On failure, `final_status` is forced to
   `blocked` with `stop_reason = blocked_reason = "effect_verification_failed"` and
   `next_action = "inspect_missing_expected_effects"`. The per-cycle statuses,
   `effect_gate_passed`, `effect_gate_reason`, and `effect_verification_expected`
   are all surfaced in loop state.

3. **`run_task_queue_daemon._process_task`** — the strict gate runs right after the
   loop-status check and **before** cleanup/commit/tag. On failure it sets
   `stage="effect_verification_gate"`, `status="blocked"`, records the gate verdict,
   and returns early so commit/tag never runs; `main()` routes the task to queue
   `failed/`.

### Files
- Modified: `autonomous_cycle.py`, `autonomous_live_loop.py`, `run_task_queue_daemon.py`, and one legacy assertion in `test_autonomous_live_loop_effect_verification_integration.py` (stop_reason now `effect_verification_failed`).
- New: `effect_gate.py` + 3 test suites.

## Verification

- `py_compile` on all four changed/new source files: OK.
- `python -m unittest` — 3 new suites + 8 affected/related suites = **57 tests OK**.
  - `test_autonomous_cycle_result_status_failed_with_zero_returncode` — returncode 0 + failed effect ≠ success.
  - `test_autonomous_live_loop_effect_failed_blocks_success` — integrated path **and** defense-in-depth (loop blocks even if the classifier is tricked into success).
  - `test_daemon_queue_effect_failed_blocks_commit_tag` — end-to-end daemon: loop reports success but effect failed → blocked, no commit/tag, routed to `failed/`, `done/` empty, sandbox repo has no new commit/tag.

### Live regression (real Codex, `/tmp/prompt638b_regression`)
Deterministic reproduction of the unsafe pattern via an always-failing verify
command. `codex_invoked_count=1`, Codex modified the file, but
`per_cycle_effect_verification_statuses=['failed']` → loop blocked → run_report
blocked → **no commit, no tag**, task in `failed/`, sandbox repo unchanged
(711→711 commits, 0 task tags).

### Live batch rerun (real Codex, `/tmp/prompt638b_batch_rerun`)
Original 3 task specs against 3 fresh clones:

| Task | Effect | Result | Committed | Tagged | Queue |
|------|--------|--------|-----------|--------|-------|
| task1-cleanup | passed | success | yes | yes | done |
| task2-queue | passed | success | yes | yes | done |
| task3-spec | **failed** | **blocked** | no | no | **failed** |

**successful=2, failed=1.** Codex non-determinism flipped which task hit the
brittle `required_text` check (Task1 passed this run; Task3 failed on
`def choose_validated_value(a, b):` because Codex emitted a type-annotated
signature). The gate behaved correctly in both directions — passed-effect tasks
succeeded and committed/tagged; the failed-effect task was blocked with no
commit/tag.

## Decision

Strict effect gate implemented, all tests pass, and a failed effect can no longer
reach success / commit / tag / queue done — proven in unit tests, a deterministic
live regression, and a live mixed batch. Ready to commit/tag the gate.

> Note (follow-up, not safety-critical): the auto-generated `required_text`
> `def {fn}(a, b):` is brittle against Codex type annotations. The safety gate is
> correct as-is; a future prompt could make effect-spec generation tolerant of
> annotated signatures so legitimate edits aren't blocked.
