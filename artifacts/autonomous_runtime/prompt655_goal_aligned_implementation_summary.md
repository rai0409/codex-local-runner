# Prompt655 — Project Prompt-Batch Execution Controller

**Status:** success · **Base:** 8050153 (tag prompt654-project-level-live-e2e-acceptance)

## What was built (safe, offline, additive)
- `project_prompt_batch.py` — manifest model + non-raising validation (slug batch_id;
  `max_prompts` cap 10; batch-relative prompt paths, **no absolute / no `..`**; prompt
  files must exist; safe tags; repo-relative artifact paths).
- `project_prompt_batch_controller.py` — `analyze_prompt_batch`, `determine_next_prompt`,
  `record_prompt_receipt`, `evaluate_prompt_result`, `advance_prompt_batch`.
  Verifies post-prompt **evidence** (expected tag via injectable read-only checker,
  report+summary files, status-field match); scores each prompt **/100** (objective 40 +
  constraint 30 + evidence 20 + risk 10) with a continue/stop decision; advances **only
  on PASS**; blocks on invalid manifest, prior failure (`stop_on_failure`), or dirty
  source (injectable provider). Emits a clear next-Claude-Code instruction.
- `scripts/run_project_prompt_batch.py` — CLI modes `analyze|next|record-receipt|evaluate|advance`,
  safe by default (no prompt execution, no test execution, no git mutation).
- Example batch under `prompts/project_batches/example/`.

## Safety
**Never executes prompt text** (no `exec`/`eval`), never runs tests/daemon/Codex,
never mutates git or live/default queues. External reads (tag existence, source
cleanliness) go through injectable providers so tests use fakes — no real git mutation.

## Validation
- 19 controller/model/CLI tests (path-traversal/absolute/missing-file rejection,
  max_prompts bound, deterministic ordering, next-selection, advance-only-on-pass,
  failure-blocks-next, dirty-source-blocks, score breakdown, next-instruction references
  the prompt file, no-arbitrary-execution, CLI in tmpdir, no side effects).
- 111 total tests OK (with all existing project-layer + daemon + targeted_fix suites).

## Result & next
The operator/Claude-Code workflow is now supported: drop prompt files + a manifest into
a batch dir → analyze → run each prompt (manually/Claude Code) → evaluate evidence →
advance only on PASS. Core project-level autonomy remains complete (live-proven).

**Next:** `task_kind_expansion_minimal_safe`.
