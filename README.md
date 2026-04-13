# codex-local-runner

`codex-local-runner` is a local-first, auditable control-plane for constrained orchestration and execution.
It remains local-only.

## Scope

- Keep existing local Flask runner behavior (`app.py`) for direct Codex execution.
- Keep provider-agnostic orchestration under `orchestrator/` and `adapters/`.
- Keep top-level dispatch semantics intake-oriented (`accepted`/`failed`) while execution outcomes remain separate.

## Docs by Audience

- Reviewer-facing handoff contract: [docs/reviewer_handoff.md](docs/reviewer_handoff.md)
- Reviewer-facing consumption runbook: [docs/reviewer_runbook.md](docs/reviewer_runbook.md)
- Operator-facing control-plane runbook: [docs/operator_runbook.md](docs/operator_runbook.md)

## Current Architecture

1. Provider adapter layer: `adapters/*`
2. Task bus layer: `orchestrator/task_bus.py`
3. Provider config: `config/providers.yaml`
4. Routing config: `config/routing_rules.yaml`
5. Managed repos config: `config/repos.yaml`
6. CLI entrypoint: `python -m orchestrator.main`

Registered Phase 1 adapters:
- `codex_cli`
- `chatgpt_tasks`
- `local_llm`

## Deterministic Policy Layer

The repository now includes a deterministic policy/evaluation layer:

- Change classification (`orchestrator/classify.py`)
- Rubric evaluation (`orchestrator/evaluate.py`)
- Merge-gate evaluation (`orchestrator/merge_gate.py`)
- YAML policy sources:
  - `config/change_categories.yaml`
  - `config/merge_gate.yaml`

## Accepted-Job Artifacts and Ledger

Accepted jobs write artifacts under `tasks/control_plane_dispatches/<timestamp>/`:

- `request.json`
- `result.json`
- `rubric.json`
- `merge_gate.json`

Runtime state is persisted in SQLite at `state/jobs.db`, including accepted-job visibility, execution-target identity, merge receipts, merge execution outcomes, rollback traces, and rollback execution outcomes.

## Task Status Policy

Phase 1 allows only:

- `pending`
- `accepted`
- `failed`

`accepted` means orchestration intake accepted. It does not mean provider execution success.
Execution outcomes stay under `result.json.execution`.

## Dispatch CLI

Help:

```bash
python -m orchestrator.main --help
```

Example:

```bash
python -m orchestrator.main \
  --repo codex-local-runner \
  --task-type orchestration \
  --goal "phase1 dispatch artifact check" \
  --provider codex_cli
```

## Constrained Local Merge Execution

Constrained merge execution is optional and local-only.

Requirements:
- `--execute-merge`
- execution-target identity fields: `--target-ref`, `--source-sha`, `--base-sha`
- persisted execution-target identity must match the request identity
- duplicate success for the same candidate identity is skipped

Behavior:
- local `git merge --no-ff --no-edit` only
- no remote push
- no GitHub API integration

Example:

```bash
python -m orchestrator.main \
  --repo codex-local-runner \
  --task-type orchestration \
  --goal "constrained local merge" \
  --provider codex_cli \
  --execution-repo-path /path/to/repo \
  --target-ref refs/heads/main \
  --source-sha <source_sha> \
  --base-sha <base_sha> \
  --execute-merge
```

## Rollback Traceability and Constrained Local Rollback

Rollback is trace-driven.

`rollback_eligible` means:
- a persisted rollback trace exists
- merge execution status is `succeeded`
- pre/post merge linkage is complete in persisted facts

Constrained rollback execution is optional and local-only.

Requirements:
- `--execute-rollback`
- `--rollback-trace-id <id>`
- trace must exist and have `rollback_eligible=true`
- trace linkage must include pre/post merge SHAs
- current-state consistency checks must pass (target ref drift and post-merge head checks)
- duplicate success for the same rollback trace is skipped

Behavior:
- local `git revert --no-edit -m 1 <post_merge_sha>` only
- no remote push
- no GitHub API integration
- no reset/rebase rollback flow

Example:

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

## Local Human Review Decision Gate

Use the local explicit decision CLI for operator review:

- `keep`: bookkeeping-only explicit human outcome
- `rollback`: explicit rollback request through the existing constrained rollback path

Primary target mode is `--job-id`:

```bash
python scripts/operator_review_decision.py --job-id <job_id> --decision keep
python scripts/operator_review_decision.py --job-id <job_id> --decision rollback --execution-repo-path /path/to/repo
```

Optional advanced direct-trace mode:

```bash
python scripts/operator_review_decision.py --rollback-trace-id <rollback_trace_id> --decision rollback --execution-repo-path /path/to/repo
```

Notes:
- `keep` does not trigger merge, rollback, redispatch, or any other execution.
- `rollback` remains subject to existing rollback eligibility and current-state consistency checks; the result may still be `skipped`/`failed` if guardrails deny execution.

## Persistence Observability

`result.json.persistence` is additive observability and uses:

- `written`: persistence was attempted and completed
- `failed`: persistence was attempted and failed non-fatally
- `skipped`: persistence was not attempted in the current flow

Current keys include:
- `evaluation_artifacts`
- `ledger`
- `execution_target`
- `merge_execution`
- `merge_receipt`
- `rollback_trace`
- `rollback_execution`

## Read-Only Evaluation CLI

You can evaluate an already-written job directory without mutating orchestration behavior:

```bash
python scripts/evaluate_job.py --job-dir <path>
```

Operational guidance for these read-only visibility surfaces is in [docs/operator_runbook.md](docs/operator_runbook.md).

## Read-Only Inspection CLI

You can inspect a recorded job from `state/jobs.db` and referenced artifacts without mutation:

```bash
python scripts/inspect_job.py --job-id <id>
python scripts/inspect_job.py --latest
python scripts/inspect_job.py --job-id <id> --json
```

Read-only candidate visibility is also available:

```bash
python scripts/list_merge_candidates.py
python scripts/list_merge_candidates.py --latest 20 --json
```

These CLIs are visibility-only. They are not execution authorization.

## Existing Flask Runner (unchanged)

- Run: `python app.py`
- Listens on `0.0.0.0:8765`
- Browser form submission persists task/prompt and runs `codex exec` via existing flow

## License

This repository is source-available for personal study, research, and evaluation.
Commercial use requires prior written permission and a separate paid license.
See `LICENSE` for details.
