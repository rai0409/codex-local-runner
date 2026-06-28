# Evidence Index

## Current capability summary
codex-local-runner has proven bounded local-only multi-prompt orchestration, no-confirmation profile wiring, real code change, and failing-test-to-bugfix acceptance.
complete_as_real_no_human_autonomous_development=false.
live_codex_execution_proven_after=false.
new_safe_goal_operational_daemon_proven_after=false.

## Exact proven prompt history
- Prompt677: commit=17842f08d7189dfe2f62fea98aa405aa6aeeb0ba tag=prompt677-increase-multi-prompt-queue-length prompt_item_count=7 prompt_tick_count=7
- Prompt679: commit=106f6503816c24febcbd5c3f67167de9e09d7a5f tag=prompt679-wire-no-confirmation-profile-into-multi-prompt-queue all_prompt_items_use_no_confirmation_profile=true
- Prompt680: commit=e067e468ee3ac023ada566ceb9afabd0564d267f tag=prompt680-multi-prompt-real-task-chain-acceptance prompt_item_count=7 prompt_tick_count=7
- Prompt682: commit=198069c3759687ed663f305072855e37bb189f77 tag=prompt682-real-code-change-inside-multi-prompt-chain real_code_change_proven_after=true
- Prompt683: commit=9da246eae7f8bec4a09d6c7f1fa473d3dced6b95 tag=prompt683-bugfix-from-failing-test-inside-multi-prompt-chain bugfix_from_failing_test_proven_after=true

## Not-yet-proven items
- live_codex_execution_proven_after=false
- new_safe_goal_operational_daemon_proven_after=false
- complete_as_real_no_human_autonomous_development=false while those gaps remain

## Architecture overview
The repository acts as a local-first orchestration control plane with prompt queues, durable state, evidence files, safety gates, and bounded validation.

## Local-only usage flow
Use pre-approved bounded prompt queues, workspace-local uv cache validation, and explicit commit/tag only after full local PASS.

## Safety model
Remote actions, destructive cleanup, credentials, cookies, browser profiles, .env values, private sessions, arbitrary free-text prompts, yolo, and sandbox bypass are blocked.

## No-confirmation execution policy
Safe pre-approved local-only bounded items may use no_confirmation_workspace_write. Missing approval or unsafe content blocks execution.

## Multi-prompt queue explanation
Prompt677 proved a 7-item prompt-level queue; Prompt680 proved a 7-item real-task chain.

## Real code change proof
Prompt682 changed automation/orchestration/planned_runner/operational_readiness_gap.py and recorded real_code_change_proven_after=true.

## Bugfix from failing test proof
Prompt683 created a controlled failing test, applied a minimal bugfix, and recorded bugfix_from_failing_test_proven_after=true.

## Validation commands
UV_CACHE_DIR=.uv-cache PYTHONPATH=. uv run python -m pytest tests/test_chatgpt_runner_bridge_server.py -q
UV_CACHE_DIR=.uv-cache PYTHONPATH=. uv run pytest tests/test_release_docs_demo_pack.py -q
node --check browser_extension/chatgpt_runner_bridge/content.js
node --check browser_extension/chatgpt_runner_bridge/background.js
node --check browser_extension/chatgpt_runner_bridge/options.js

## Demo scenario
Run a bounded local prompt queue that verifies baselines, generates docs, validates evidence, and writes acceptance reports without remote services.

## Limitations
This demo pack is local-only and does not prove live Codex subprocess execution or repeated new safe-goal daemon operation.

## Next operational gaps
Prompt685 should address a new safe-goal operational daemon acceptance. A separate prompt must resolve live Codex execution or keep it explicitly dry-run-only.

## Evidence index
See docs/release_demo/EVIDENCE_INDEX.md and artifacts/autonomous_runtime/prompt684_release_docs_demo_pack/evidence_summary.json.
