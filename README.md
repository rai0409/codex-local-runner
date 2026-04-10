# codex-local-runner

`codex-local-runner` is a local-only repository.
In Phase 1, it also works as a logical **control-plane** kernel for coarse-grained orchestration.

## Scope

- Keep existing local Flask runner behavior (`app.py`) for direct Codex execution.
- Add a provider-agnostic orchestration skeleton under `orchestrator/` and `adapters/`.
- Keep dispatch semantics intake-only in Phase 1.

## Current Architecture (Phase 1)

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

## Task Status Policy

Phase 1 allows only:

- `pending`
- `accepted`
- `failed`

`accepted` means orchestration intake accepted. It does not mean provider execution success.

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

Artifacts are written under `tasks/control_plane_dispatches/<timestamp>/`:

- `request.json`
- `result.json`

`request.json` and `result.json` include `job_id`.
`result.json` also includes `dispatcher` and `artifacts`.
Provider resolution is validated against `config/providers.yaml` before acceptance.
Unknown, disabled, or unsupported providers fail explicitly with `status=failed`.

## Existing Flask Runner (unchanged)

- Run: `python app.py`
- Listens on `0.0.0.0:8765`
- Browser form submission persists task/prompt and runs `codex exec` via existing flow

## License

This repository is source-available for personal study, research, and evaluation.
Commercial use requires prior written permission and a separate paid license.
See `LICENSE` for details.
