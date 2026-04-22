# prompts/base_contract_rules.md

## Purpose
This file defines the standing contract/read-model rules for `codex-local-runner`.
Future implementation prompts should treat this file as the default baseline and specify only the narrow delta for the current PR.

This repository is local-first, auditable, constrained, and deterministic by default.
New work should fit that shape.

## Repository-specific baseline

### 1. Additive-only
- Add new layers without replacing existing truth owners unless explicitly requested.
- Prefer new helper modules, sidecar artifacts, or narrow adapters over broad rewrites.
- Do not redesign controller/scheduler behavior unless the PR explicitly targets that area.

### 2. Compact-first
- `run_state.json` must remain compact.
- Prefer presence-only or narrow summary-safe fields in `run_state.json`.
- Manifest surfaces must remain summary/path-reference only.
- Do not embed full sidecar contract bodies into manifest or broad mirrors into run_state.

### 3. Deterministic-first
- Prefer enum/flag/rule/template-based derivation over narrative reasoning.
- Same compact inputs must produce the same outputs.
- Reason ordering must be stable and deterministic.
- Unsupported or insufficient input must be surfaced explicitly, not guessed.

### 4. Read-model discipline
- New contract layers should classify, summarize, or gate existing truth.
- They must not silently become new truth owners for upstream execution state.
- Preserve clear source linkage back to canonical artifacts.

### 5. Inspect/operator are read-only
- `scripts/inspect_job.py` and `scripts/build_operator_summary.py` may show compact views only.
- These surfaces must not define new truth.
- They must not broaden or reinterpret state beyond canonical compact artifacts.

### 6. Artifact index discipline
- Register new artifact roles only when necessary.
- Keep artifact index deterministic and narrow.
- Do not turn artifact index into a broad secondary manifest.

### 7. Stable summary/path discipline
When adding a new artifact, prefer:
- `<artifact>_summary`
- `<artifact>_path`

Do not add:
- full embedded bodies
- broad duplicated mirrors
- verbose operator-only expansions

### 8. Safety-sensitive flows remain explicit
Do not compress away or “simplify” safety gates such as:
- blocked/held restart posture
- fleet safety gating
- retry/re-entry ceilings
- manual-only posture
- rollback eligibility checks
- write authority guards

These must remain explicit and testable.

### 9. Existing deterministic paths should be reused
Before adding new logic, first check whether the behavior belongs in or should reuse:
- `orchestrator/merge_gate.py`
- deterministic YAML policy in `config/*.yaml`
- compact orchestration helpers under `automation/orchestration/`
- local merge / rollback / review CLIs already present in the repo

### 10. Narrow PR responsibility
Each PR should have one main responsibility.
Good examples:
- one new contract
- one new narrow adapter
- one new helper family
- one new compact safety layer
- one new token-reduction scaffolding layer

Avoid bundling unrelated features.

## Default testing discipline
Every PR should add or update focused tests only.
At minimum validate:
- deterministic derivation or rendering
- compact boundaries
- summary/path-only manifest behavior
- run_state narrowness
- inspect/operator compact surfacing
- stable reason ordering where applicable

Prefer targeted tests over broad unrelated edits.

## Default validation commands

```bash
uv run python -m unittest tests.test_planned_execution_runner -v
uv run python -m unittest tests.test_inspect_job -v
uv run python -m unittest tests.test_build_operator_summary -v
```

If a new focused test module is added, run it too.

## Acceptance bar
A PR is not complete unless:
- derivation is deterministic
- compact discipline is preserved
- run_state is not broadened unnecessarily
- manifest remains summary/path-only
- inspect/operator remain compact and read-only
- safety-sensitive gates remain explicit
- focused tests pass

## Default out-of-scope rules
Unless explicitly requested, do not add:
- controller/scheduler redesign
- broad external services
- broad telemetry/database redesign
- free-form NLP interpretation
- background daemons
- autonomous unsafe execution
- truth-owner mutation
- large operator-only prose surfaces

## Default implementation style
Prefer:
- small helper modules
- compact config-driven policies
- stable enums and flags
- Python templates over prose generation
- explicit mapping functions
- narrow adapters
- conservative defaults

## Prompt usage rule
Future prompts should:
- reference this file as baseline
- describe only the new delta
- avoid repeating all generic compact/additive/read-only rules unless emphasis is necessary
