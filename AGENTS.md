# AGENTS

## Repository Role

- `codex-local-runner` is a local execution + orchestration repository.
- Phase 1 keeps acceptance semantics stable while adding minimal execution plumbing.

## Phase 1 Rules

- Do not rename repository/package/import paths/directories.
- Dispatch is intake-only and may return only `pending`, `accepted`, or `failed`.
- Top-level `accepted`/`failed` remains orchestration acceptance only.
- Provider adapters are stubs and must raise `NotImplementedError` when executed.
- Do not fake provider execution success.
- Registered adapter stubs: `codex_cli`, `chatgpt_tasks`, `local_llm`.
- Provider names are resolved through `config/providers.yaml`; invalid providers fail explicitly.
- PR2 allows minimal `codex_cli` execution result tracking via `result.json.execution`.

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
