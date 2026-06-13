# Prompt638a — Task1 Effect-Failure Root Cause Analysis

**Status:** success (analysis-only; no source modified, nothing staged/committed/tagged/pushed)
**Root cause:** `effect_failed_not_gated_before_success_commit_tag`
**General safety bug confirmed:** **true**
**Next action:** `implement_strict_effect_verification_success_gate`

## Base repo
- Live HEAD: `2a87cb17a999984c6b33b970201d8ed21178013f` — "Record Fable runtime validation and commit-tag reports"
- Tag at HEAD: `codex-runner-fable-runtime-evidence-20260613`
- Note: prompt context stated HEAD=`409b0fa` (prompt637 cleanup policy); actual HEAD is one commit ahead with `409b0fa` as a confirmed ancestor. No effect on the analysis.
- Main repo source modified: **no** (only untracked artifacts/handoff/prompt files).

## What actually happened in Task1

Codex was asked to add `is_generated_artifact_count(a, b)` returning `1 if a else b`. It produced a **correct, well-formed** function — but with a type-annotated signature:

```python
def is_generated_artifact_count(a: Any, b: Any) -> int:
    return 1 if a else b
```

The effect spec's `required_text` is an **exact substring** check requiring the literal `def is_generated_artifact_count(a, b):`. The typed signature does not contain that substring, so:

- `return 1 if a else b` → **present**
- `def is_generated_artifact_count(a, b):` → **missing**

The live gate therefore **correctly failed** effect verification:
- `effect_verification_status = failed`
- live gate `status = failed`, `returncode = 0`, `returncode_classification = failed`, `stop_reason = effect_verification_failed`
- error: `required text missing ... 'def is_generated_artifact_count(a, b):'`

## The safety bug: a correct failure became a final success + commit + tag

Despite `per_cycle_effect_verification_statuses = ['failed']`, the task ended:
`status=success`, `loop_status=success`, `sandbox_commit_performed=true` (commit `c183c26`), `sandbox_tag_performed=true` (tag `sandbox-task1-cleanup-add-function`), `queue=done`.

Three independent layers each failed to gate on the effect failure:

1. **Cycle classifier** — `automation/orchestration/planned_runner/autonomous_cycle.py::_result_status` (lines 92–115).
   With `status='failed'`, `returncode_classification='failed'`, `returncode=0`, line 107 (`returncode==0 → 'success'`) is checked **before** the failed-signal checks on lines 109–114. The zero exit code silently overrides the explicit failure → cycle classified `codex_result_success`.

2. **Autonomous live loop** — `autonomous_live_loop.py` (lines 530–532, 558–578, 610).
   `final_status` is taken purely from `_cycle_stop_state(classification=...)`. `per_cycle_effect_statuses` is recorded into the payload but **never consulted** when computing `final_status`/`status` → loop reports `success`.

3. **Daemon task runner** — `scripts/run_task_queue_daemon.py::_process_task` (lines 153–202).
   Records `per_cycle_effect_verification_statuses` (154–156) but the only gate (line 158) checks `loop_state['status'] != 'success'`. It never inspects the effect statuses, so it proceeds to cleanup → commit/tag → `status=success`.

This is **not Task1-specific**: any task whose Codex run exits 0 while effect verification fails will be marked success and committed/tagged.

## Fix recommendation (do NOT implement here)

Strict effect-verification success gate, defense-in-depth:

- **Should task success require every per-cycle effect status to be `passed`?** Yes.
- **Should sandbox commit/tag be blocked if any effect verification failed?** Yes.
- **Should the queue final path be `failed` instead of `done`?** Yes.
- **Should run_report status be blocked/failed instead of success?** Yes.
- **Should `loop_status=success` be ignored if effect statuses contain `failed`?** Yes — the loop should not report success, and the daemon must independently re-gate.
- **Gate owner:** primarily `autonomous_live_loop.py` (final_status must reflect effect verification); defense-in-depth in `autonomous_cycle._result_status` (explicit `failed` must beat `returncode==0`) and `run_task_queue_daemon._process_task` (block commit/tag + route to failed when any effect status ≠ passed).
- Secondary (non-safety-critical): the `required_text` exact-substring is brittle — effect-spec generation should match the function regardless of type annotations. The gate is the safety fix; the spec is a quality fix.

### Files to modify
- `automation/orchestration/planned_runner/autonomous_cycle.py`
- `automation/orchestration/planned_runner/autonomous_live_loop.py`
- `scripts/run_task_queue_daemon.py`

### Tests to add
- `tests/test_autonomous_cycle_result_status_failed_with_zero_returncode.py`
- `tests/test_autonomous_live_loop_effect_failed_blocks_success.py`
- `tests/test_daemon_queue_effect_failed_blocks_commit_tag.py`

### Rerun
**Required.** After the gate lands, rerun Task1 as a regression: with the same brittle spec, the failed effect verification must yield a failed/blocked task with **no** sandbox commit/tag.

## Final decision
Task1's effect verification correctly failed (legitimate `required_text` mismatch), but the runtime converted that failure into a final success with commit and tag. This is a **general safety bug**. Implement the strict effect-verification success gate before any further real-task acceptance.
