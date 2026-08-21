# R1.1 Long-running Codex execution policy

## Goal

Extend the existing R1 execution path for bounded multi-hour Codex work.

## Non-goals

No new execution pipeline, no changes to planned_runner, no unbounded retries,
and no relaxation of Git, lock, receipt, or source-integrity safeguards.

## Verified current state

- Base: R1 commit `136637e` on `feat/bounded-codex-timeout-recovery`.
- R1 implementation timeout is 900 seconds with a 1800-second cap.
- Validation commands already have strict per-command timeouts in Repository
  Profile; completion evaluator inherits `run_codex`; multi-cycle has no total
  wall-clock deadline.

## Stages

1. Classify timeout boundaries and preserve safety-only deadlines.
2. Expand bounded implementation, validation, evaluator, and rework policies.
3. Add focused regression coverage and run full validation.

## Progress

All implementation stages and the listed validation gates passed. The change is
intentionally left uncommitted for the requested handoff.

## Validation

- focused execution, adapter, validation-repair, evaluator/R0, multi-cycle and
  supervisor tests
- full unittest discovery
- py_compile for changed Python files
- git diff --check

## Risks

Longer individual subprocess limits increase worst-case elapsed time, but all
attempt counts, protocol retries, validation repair limits, locks, and
integrity checks remain bounded.

# R2 Deterministic safe changed-path scope recovery

## Goal

Allow a strictly bounded, runner-owned recovery only for omitted test and
documentation support paths in a single repository-resolved task.

## Non-goals

No new execution pipeline, no changes to planned_runner or multi-cycle
lifecycle, no LLM scope decision, and no relaxation of Git, receipt, or
source-integrity safeguards. R0 and R1.1 contracts remain frozen.

## Verified current state

- Base: R1.1 commit `420444b` on `feat/bounded-codex-timeout-recovery`.
- Declared task scope is immutable evidence. Effective scope may add at most
  four normalized repository-relative paths only when every original
  unexpected path is in a `tests` or `docs` directory and passes hard-block
  checks.
- Any mixed, unsafe, external, traversal, symlink-escape, or excessive set
  remains blocked atomically.

## Stages

1. Trace declared scope, actual paths, evaluator inputs, receipts, and commit
   enforcement.
2. Add deterministic scope recovery with complete receipt evidence.
3. Add focused regression coverage and run full validation.

## Progress

Implementation and all listed validation gates passed. The change remains
uncommitted for the requested handoff.

## Validation

- focused scope-policy, controller, evaluator/R0, and timeout regressions
- full unittest discovery
- py_compile for changed Python files
- git diff --check

## Risks

Safe support-file classification must remain component-based and fail closed;
the existing profile-wide changed-file limit can still be stricter than the
four-file automatic-expansion cap.
