# AGENTS

## Repository Role

- `codex-local-runner` is a local-first execution + orchestration repository.
- The repository acts as an auditable control-plane with constrained local merge/rollback execution paths.

## Phase 1 Rules

- Do not rename repository/package/import paths/directories.
- Dispatch is intake-only and may return only `pending`, `accepted`, or `failed`.
- Top-level `accepted`/`failed` remains orchestration acceptance only.
- Do not fake provider execution or merge/rollback success.
- Keep execution outcomes under `result.json.execution`; do not reinterpret acceptance.
- Provider names are resolved through `config/providers.yaml`; invalid providers fail explicitly.
- `codex_cli` execution is supported; non-primary adapters may remain stubs.
- Execution-target identity, merge receipts, merge execution outcomes, rollback traceability, and rollback execution outcomes are persistent state in `state/jobs.db`.
- Read-only inspection/listing tooling is visibility-only and must not be used as authorization.
- Merge/rollback execution remains local-only: no remote push, no GitHub API integration.

## Managed Repositories

- codex-local-runner
- internal_automation
- chatbot
- contract-ingest
- topix1000_disclosure_platform
- booking_zoom_connect
- ai_router
- Jstocks-prediction
- ccr-python

Detailed external repo metadata is intentionally omitted in Phase 1 unless confirmed inside this repository.

## AI/Codex Operation Rules

- Principle: `1 task = 1 decision`.
- Do not ask Codex to solve multiple major deliverables in one run.
- Large tasks must be split before implementation starts.
- If a task has `3+` follow-up correction rounds, start a fresh Codex run with a narrowed prompt.

### Task Modes

- `Scout`: read/inspect only; no code changes.
- `Implement`: add or change behavior for one scoped deliverable.
- `Repair`: fix a specific regression or failing behavior.
- `Polish`: non-behavioral cleanup (docs, naming, comments, readability).

Rules:
- Do not mix modes in one Codex run.
- A single run must declare exactly one mode.

### Prompt Contract (Required)

Every Codex prompt must explicitly include:
- goal
- allowed files
- forbidden files
- expected artifact/output
- allowed validation commands
- explicitly out-of-scope items

### Artifact Hygiene

- Generated artifacts/logs/caches must not be committed.
- Never commit `__pycache__/`, `*.pyc`, temporary logs, or local build/cache output.
