# Operator Runbook

This runbook is operator-facing control-plane guidance for constrained local merge/rollback execution.
It complements reviewer-facing docs and does not redefine reviewer handoff contracts.

## Local-Only Execution Boundary

Merge and rollback execution are local-only:

- no remote push
- no GitHub API integration
- no authorization from visibility tooling output alone

## Merge and Rollback Authorization Model

Execution authorization is state-driven:

- merge execution requires persisted execution-target identity linkage
- rollback execution requires a persisted rollback-trace record

Read-only tooling output is visibility-only and is not authorization.

## What `rollback_eligible` Means

`rollback_eligible` is fact-based eligibility from persisted merge execution linkage.
At minimum it requires successful merge execution facts with complete pre/post linkage for that candidate identity.

It is not inferred from:

- candidate visibility alone
- merge-gate output alone
- inspect output alone

## Why Current-State Consistency Checks Exist

Before constrained rollback executes, the runner checks current local state against recorded rollback-trace linkage (including current head and target-ref consistency).
If drift is detected, rollback is explicitly skipped/failed instead of forcing history changes.

## Persistence Observability: `written` / `failed` / `skipped`

For `result.json.persistence` fields:

- `written`: persistence was attempted and completed successfully
- `failed`: persistence was attempted and failed non-fatally
- `skipped`: persistence was not attempted in the current control flow

These states are observability signals and do not reinterpret top-level orchestration acceptance semantics.

## Read-Only Visibility Tooling

These commands are read-only visibility surfaces:

- `python scripts/evaluate_job.py --job-dir <path>`
- `python scripts/inspect_job.py --job-id <id>`
- `python scripts/inspect_job.py --latest`
- `python scripts/list_merge_candidates.py`

They are for inspection and candidate visibility only.
They do not authorize or execute merge/rollback actions.

## Constrained Rollback Invocation

Rollback execution requires explicit trace targeting:

```bash
python -m orchestrator.main \
  --repo codex-local-runner \
  --task-type orchestration \
  --goal "constrained local rollback" \
  --provider codex_cli \
  --execution-repo-path /path/to/repo \
  --execute-rollback \
  --rollback-trace-id <rollback_trace_id>
```

## Intentional Non-Goals

Current implementation intentionally does not:

- push to remotes
- call GitHub APIs
- use destructive reset/rebase rollback flows
- treat inspect/list/evaluate output as execution authorization
