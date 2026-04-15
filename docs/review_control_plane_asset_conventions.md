# Review Control Plane Asset Conventions

## Purpose
This document defines naming and placement conventions for prompt assets, run records, archive bundles, and related review-control-plane documentation.

The goal is to keep assets deterministic, searchable, and easy to reuse in future semi-automation.

---

## 1. Asset categories

### 1.1 Prompt examples
Location:
- `prompts/examples/good/`
- `prompts/examples/bad/`

Purpose:
- store reusable prompt examples
- separate successful and unsuccessful prompt patterns

### 1.2 Run records
Recommended location:
- `prompts/examples/good/`
- `prompts/examples/bad/`

Purpose:
- preserve one execution summary per task
- record what changed, what was run, and why it passed or failed

### 1.3 Archive bundles
Location:
- `prompts/archive/<bundle_id>/`

Purpose:
- preserve a re-evaluable implementation attempt as a complete bundle

### 1.4 Repo profiles
Location:
- `prompts/repo_profiles/`

Purpose:
- provide stable repo-specific context for future prompt generation

---

## 2. Naming conventions

### 2.1 Standalone prompt files
Pattern:
- `prompt<task_id>_<short_name>.md`

Examples:
- `prompt7a_advisory_readonly.md`
- `prompt7b_execution_bridge_readonly.md`
- `prompt7c_mode_visibility_readonly.md`

Rule:
- use lowercase
- use underscores, not spaces
- keep the name short but specific

### 2.2 Run record files
Pattern:
- `YYYY-MM-<task_id>-<short-name>-run-record.md`

Examples:
- `2026-04-7a-inspect-advisory-run-record.md`
- `2026-04-7b-execution-bridge-run-record.md`
- `2026-04-7c-mode-visibility-run-record.md`

Rule:
- include date prefix for ordering
- include task identifier for cross-reference
- use hyphens in run-record filenames

### 2.3 Archive bundle directories
Pattern:
- `YYYY-MM-DD_<task_id_or_short_name>`

Examples:
- `2026-04-14_prompt7c`
- `2026-04-16_archive-index`
- `2026-04-18_asset-conventions`

Rule:
- one task = one directory
- keep identifiers stable
- do not reuse bundle ids for different attempts

### 2.4 Repo profile files
Pattern:
- `<repo_name>.md`

Examples:
- `codex_local_runner.md`

---

## 3. Required archive bundle files

Each archive bundle should contain:

- `prompt.md`
- `codex_output.md`
- `diff.patch`
- `commands.txt`
- `test_results.txt`
- `evaluation.md`
- `decision.md`

Rule:
- all seven files are preferred
- `prompt.md` may be a source note when the original prompt is embedded elsewhere
- `diff.patch` must use real git output

---

## 4. Prompt handling rules

### 4.1 Preferred state
Preferred:
- standalone prompt file exists
- run-record exists separately

### 4.2 Allowed temporary state
Allowed:
- prompt text embedded inside run-record
- archive `prompt.md` contains a source note instead of duplicated prompt text

### 4.3 Cleanup rule
When time permits:
- split embedded prompt text into standalone prompt file
- keep run-record focused on execution history

---

## 5. Run-record minimum contents

A run-record should include:
- metadata
- repository reading proof
- implementation map
- exact files changed
- commands run
- test results
- evaluation summary
- final decision
- next-step note

---

## 6. Evaluation vs decision separation

### 6.1 evaluation.md
Records:
- score
- analysis
- strengths
- weaknesses
- merge safety assessment

### 6.2 decision.md
Records:
- final pass / revise / rollback judgment
- why that judgment was chosen
- why the alternatives were rejected
- next action

Rule:
- do not merge these into one file in archive bundles

---

## 7. Indexing rules

### 7.1 Example index
`prompts/examples/index.json` tracks reusable prompt examples.

### 7.2 Archive index
`prompts/archive/index.json` tracks archive bundles.

Rule:
- examples and archive bundles are related but distinct
- examples index stores reusable prompt assets
- archive index stores concrete execution attempts

---

## 8. Branch naming guidance

Recommended patterns:
- `feat/<short-task-name>`
- `docs/<short-task-name>`
- `chore/<short-task-name>`

Examples:
- `feat/inspect-mode-visibility-7c`
- `docs/archive-asset-conventions`
- `chore/archive-index-bootstrap`

Rule:
- branch name should reflect task scope
- docs-only work should prefer `docs/` or `chore/`

---

## 9. Current repository-specific guidance

For `codex-local-runner` in its current phase:
- prefer inspect-only or docs/contract tasks
- prefer additive visibility and documentation
- do not imply autonomous execution
- keep explicit human decision path intact unless explicitly requested

---

## 10. Future semi-automation readiness

These conventions exist to make future automation possible for:
- example lookup
- retry prompt generation
- archive bundle creation
- evaluation assistance
- decision support

They do not imply that execution behavior is automated today.
