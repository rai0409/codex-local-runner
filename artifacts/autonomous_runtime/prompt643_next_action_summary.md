# Prompt643 — Daemon Queue ↔ Targeted-Fix Retry Integration

**Status:** success
**Base:** `714bb11` (tag `prompt639-multi-cycle-targeted-fix-acceptance`)

## Chosen step (highest leverage toward L8)
Wire `run_targeted_fix_retry` into the daemon queue runner — the single missing
execution-layer capability Prompt641 flagged. A project-level autonomous loop is
only robust if each queued task can self-heal a fixable effect failure; the retry
mechanism was proven standalone (Prompt639) but not yet invoked by the daemon.

## What changed
`scripts/run_task_queue_daemon.py`:
- New opt-in `--max-fix-attempts` (default **0** = original behavior; hard-capped at
  `MAX_FIX_ATTEMPTS_CAP`=2).
- When `> 0`, the daemon drives `run_targeted_fix_retry` as the execution engine, so
  an effect-verification failure is automatically retried with a fix prompt.
- The success tail (cleanup → commit/tag → final clean → done) was factored into a
  shared `_finalize_success` helper, reached **only after a strictly-passed effect** —
  so commit/tag can never precede a passed effect.
- Post-retry strict gate: the task proceeds to commit/tag/done only when the retry
  **converged AND the final attempt's effect strictly passed**; otherwise it stays
  blocked (`stage=targeted_fix_unresolved`), no commit/tag, queue failed, evidence
  preserved.

Minimal, backward-compatible: with `--max-fix-attempts 0` the original single-shot
live-loop path is unchanged.

## Tests (`tests/test_daemon_queue_targeted_fix_retry_integration.py`, 4 new)
- effect-failed task **auto-triggers** targeted_fix_retry and **resolves → done**
  (commit/tag only after the fixed effect passed).
- unresolved fix → **queue failed**, no commit/tag, digest/state preserved.
- strict gate **blocks false success** (converged claim but final effect not passed → blocked).
- **backward compatible** at `--max-fix-attempts 0` (retry not invoked; loop path).

### Validation
- New suite: **4 OK**. Affected suites: **58 OK**. Full suite: **579 passed, 1 skipped, 1 error**.
- The only full-suite failure is a **pre-existing, unrelated** import error in
  `test_planned_execution_runner` (`_augment_run_state_with_closed_loop` absent at
  HEAD; that module was not touched). **No regression introduced.**

### Bounded live runtime (real Codex, /tmp, `--max-fix-attempts 1`)
| Task | targeted_fix_invoked | converged | status | commit/tag | queue |
|------|----------------------|-----------|--------|-----------|-------|
| live-normal | true | true | success | yes | done |
| live-unresolved (always-fail verify) | true | false | blocked | no | failed |

Both tasks auto-invoked the retry; the passing task committed/tagged to done; the
unresolved task (base + 1 fix attempt) was safely blocked with no commit/tag.

## Safety
- Main repo HEAD `714bb11` unchanged during runtime; tag unchanged; only
  `run_task_queue_daemon.py` + the new test changed.
- Sandbox isolation (/tmp only) preserved; strict effect verification preserved;
  `effect_failed_wrongly_succeeded_count=0`, `strict_gate_violations=0`;
  0 leftover generated artifacts; archive & handoff_reports untouched.

## Result & next
The daemon execution layer is now **self-healing end-to-end** — the prerequisite for
the project-level autonomous loop. Committed and tagged. Next highest-leverage step:
`implement_project_intent_schema` (begin the project planner stack on top of the now
self-healing daemon).
