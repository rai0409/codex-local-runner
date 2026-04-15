# Next Task Queue

## Purpose
This file tracks the next narrow, repository-aligned tasks for codex-local-runner.

The queue should prefer:
- inspect-only
- read-only
- ledger-backed
- contract/documentation clarity
- archive / example / evaluation asset quality

It should avoid:
- runtime execution
- autonomous retry / rollback / merge
- hidden control semantics
- premature orchestration

---

## Priority 1
### Task
Expand `prompts/archive/index.json` from baseline to a stable archive registry.

### Goal
Register current archive bundles in a predictable format.

### Why now
- directly supports semi-automation later
- low risk
- docs/metadata only
- improves discoverability of prior attempts

### Expected files
- `prompts/archive/index.json`
- optional small update to `prompts/archive/README.md`

### Success criteria
- valid JSON
- bundle registry remains lightweight
- no code changes

---

## Priority 2
### Task
Split standalone prompt files from embedded run-record prompt text where practical.

### Goal
Ensure prompt assets and run-records are separate reusable units.

### Why now
- improves prompt reuse
- reduces ambiguity
- makes archive copying easier

### Expected files
- `prompts/examples/good/*.md`
- no code changes

### Success criteria
- at least one embedded prompt is split cleanly
- run-record remains intact
- naming follows conventions

---

## Priority 3
### Task
Create a minimal archive bundle bootstrap script.

### Goal
Reduce repetitive manual setup without adding workflow control semantics.

### Why later
- useful only after conventions and registry stabilize
- should remain thin and non-authoritative

### Expected files
- `scripts/create_archive_bundle.py` or `.sh`
- possible docs update

### Success criteria
- creates bundle directory
- creates expected empty files or starter templates
- does not infer decisions or evaluations
