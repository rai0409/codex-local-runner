# Reviewer Runbook

This runbook explains how to consume the existing `reviewer_handoff` package in practice. For the contract shape and field definitions, use [reviewer_handoff.md](reviewer_handoff.md).

## Reading Order

1. Read `reviewer_handoff.summary`.
2. Read `reviewer_handoff.execution` if you need execution mechanics.
3. Read `reviewer_handoff.validation` if you need validation outcome details.
4. Fall back to the raw payload only when the compact handoff is not enough.

## When `summary` Is Enough

`summary` is enough for initial triage when you only need the compact final outcome:

- final execution status
- final verify status and reason
- whether retry was attempted and how it ended
- the existing `result_interpretation`
- the existing `review_recommendation`

If that is all you need to decide whether deeper inspection is warranted, stop there.

## When To Inspect `execution`

Inspect `execution` when you need the run mechanics rather than the top-level outcome:

- confirm whether execution finished as `completed`, `failed`, or another final status
- confirm `attempt_count`, especially when retry context matters
- confirm the final `return_code`

Use `execution` to verify what happened operationally. Do not treat it as a replacement for the top-level summary.

## When To Inspect `validation`

Inspect `validation` when you need verify-specific detail:

- confirm `verify_status`
- confirm `verify_reason`
- use `validation.summary` when present for aggregate pass/fail counts

If `validation.summary` is omitted, treat that as "not present in the structured verify result", not as zero commands and not as a contract error.

## When To Fall Back To The Raw Payload

Use the raw payload only when `reviewer_handoff` does not answer the review question. Typical cases:

- you need command-level validation detail
- you need artifact paths or execution logs
- you need fields that are intentionally not mirrored into `reviewer_handoff`

The handoff is a compact reviewer package, not a full execution record.

## How To Treat Omitted Optional Sections

Treat omitted optional reviewer-facing sections literally:

- omitted means omitted
- omitted sections are not represented as empty objects
- do not infer pass, fail, or absence of activity from omission alone

Stay with the fields that are present unless the review requires the raw payload.

## How To Use `review_recommendation`

Use `review_recommendation` as a review hint:

- it helps decide whether a deeper review pass is warranted
- it does not approve, reject, or score the run by itself
- it should be read together with `summary`, and with `execution` or `validation` when needed

## Control-Plane Execution Guardrails (Operator Notes)

This repository also has constrained local merge/rollback execution paths.
These paths are separate from `reviewer_handoff` and are controlled by persisted state, not by read-only summaries.

### When Rollback Is Allowed

Rollback execution is allowed only when all are true:

- a persisted rollback trace record exists (`rollback_trace_id`)
- that trace has `rollback_eligible = true`
- trace linkage includes both pre/post merge identities
- request repo and trace repo are consistent
- current-state consistency checks pass in the local repo

### What `rollback_eligible` Means

`rollback_eligible` is fact-based eligibility from persisted merge execution linkage.
It indicates that the system has a successful merge execution record with complete pre/post linkage for that candidate identity.
It is not derived from candidate visibility, policy output alone, or inspect output alone.

### Why Current-State Consistency Checks Exist

Before rollback, the runner verifies that current local state still matches the recorded post-merge identity and target ref.
If drift is detected, rollback is skipped/failed explicitly to avoid ambiguous or unsafe local history changes.

### Visibility Is Not Authorization

`scripts/inspect_job.py`, `scripts/evaluate_job.py`, and `scripts/list_merge_candidates.py` are read-only visibility tools.
They do not authorize merge or rollback execution.
Execution authorization comes from persisted execution/rollback trace records and invariant checks in orchestration flow.

### `written` / `failed` / `skipped`

For persistence observability fields:

- `written`: persistence was attempted and succeeded
- `failed`: persistence was attempted and failed non-fatally
- `skipped`: persistence was not attempted in the current control flow

### Intentional Non-Goals

Current implementation intentionally does not:

- push to remotes
- call GitHub APIs
- treat visibility output as authorization
- use destructive reset/rebase rollback flows
