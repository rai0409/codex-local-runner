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
