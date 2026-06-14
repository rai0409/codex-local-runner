# Prompt657 — External Analysis Handoff Controller

**Status:** success · **Base:** fca0bd9 (tag prompt656-minimal-safe-task-kind-expansion)

## What was built (safe, offline, artifact-based)
`external_analysis_handoff.py` — the handoff layer between browser-side ChatGPT analysis
and repo-side Claude Code/Codex implementation, with **no browser automation, no network,
no API calls, no credential/cookie storage, and no prompt execution**:
- `validate_analysis_request` / `create_analysis_request` — build a repo-relative ChatGPT
  request file (absolute/traversal output rejected).
- `prepare_next_chatgpt_instruction` — deterministic instruction describing the required
  `analysis_artifact_v1` output.
- `load_analysis_artifact` / `validate_analysis_artifact` — non-raising validation:
  rejects wrong schema, missing required fields, empty recommended-prompt bodies,
  >10 recommended prompts, out-of-range score, unsafe paths/tags.
- `evaluate_analysis_artifact` — scores the artifact /100 with a breakdown.
- `analysis_artifact_to_prompt_batch` — converts an accepted `generate_prompt_batch`
  artifact into **path-safe prompt files inside the batch dir** + a **Prompt655-compatible
  manifest**, validated by the Prompt655 validator.
- CLI `scripts/run_external_analysis_handoff.py`: `create-request | validate-artifact |
  to-batch | evaluate | next-instruction` (safe defaults).
- Examples: `prompts/analysis_requests/example_chatgpt_analysis_request.md`,
  `artifacts/autonomous_runtime/external_analysis/example_analysis_artifact.json`.

## Safety
No `exec`/`eval`/`subprocess`/`requests`/`urllib` in the module (test-asserted). No
network, no credentials, no arbitrary prompt execution. Generated prompt files stay
inside the chosen batch dir; absolute/traversal paths rejected; max 10 recommended prompts.

## Validation
- 23 handoff tests (request/artifact validation, safe-fail, empty-body rejection,
  absolute/traversal rejection, cap enforcement, Prompt655-compatible conversion,
  generated files inside batch dir, no-execution, CLI in tmpdir).
- **154 total tests green** (all prior project-layer + daemon + add_file suites).

## Result & next
The orchestration loop now connects **ChatGPT analysis → validated artifact →
Prompt655 prompt batch → Claude Code/Codex implementation** — safely, without browser
credential automation.

**Next:** `browser_analysis_to_prompt_batch_live_acceptance` (an operator-driven, bounded
end-to-end run from a real ChatGPT artifact through a batch).
