# AGENTS

## Repository Role

- This repository remains `codex-local-runner`.
- In Phase 1, it also acts as a logical control-plane orchestration kernel.

## Phase 1 Rules

- Do not rename repository/package/import paths/directories.
- Dispatch is intake-only and may return only `pending`, `accepted`, or `failed`.
- Provider adapters are stubs and must raise `NotImplementedError` when executed.
- Do not fake provider execution success.
- Registered adapter stubs: `codex_cli`, `chatgpt_tasks`, `local_llm`.
- Provider names are resolved through `config/providers.yaml`; invalid providers fail explicitly.

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
