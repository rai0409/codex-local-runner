# Prompt271 result: Codex execution gate for routed bridge prompts

## Scope
Modified:
- `automation/orchestration/planned_execution_runner.py`

## What changed
- Added `_build_project_browser_autonomous_codex_execution_gate_state(...)`.
- Detects routed prompt surfaces:
  - `/tmp/codex-local-runner-decision/generated_next_prompt.txt`
  - `/tmp/codex-local-runner-decision/generated_fix_prompt.txt`
- Reads routed prompts boundedly:
  - max 32768 bytes
- Preserves prompt metadata:
  - selected prompt path
  - prompt size bytes
  - normalized/truncated preview
  - SHA-256 fingerprint
- Added default-off gate flags:
  - `project_browser_autonomous_codex_execution_gate_enabled`
  - `project_browser_autonomous_codex_execution_gate_execute_enabled`
- Added normalized gate fields:
  - `project_browser_autonomous_codex_execution_gate_status`
  - `project_browser_autonomous_codex_execution_gate_next_action`
  - `project_browser_autonomous_codex_execution_gate_enabled`
  - `project_browser_autonomous_codex_execution_gate_execute_enabled`
  - `project_browser_autonomous_codex_execution_gate_prompt_kind`
  - `project_browser_autonomous_codex_execution_gate_prompt_path`
  - `project_browser_autonomous_codex_execution_gate_prompt_size_bytes`
  - `project_browser_autonomous_codex_execution_gate_prompt_fingerprint`
  - `project_browser_autonomous_codex_execution_gate_prompt_preview`
  - `project_browser_autonomous_codex_execution_gate_threshold_passed`
  - `project_browser_autonomous_codex_execution_gate_approved_for_execution`
  - `project_browser_autonomous_codex_execution_gate_blocked_reason`
- Added status handling:
  - `codex_execution_gate_not_requested`
  - `codex_execution_gate_blocked_missing_routed_prompt`
  - `codex_execution_gate_blocked_duplicate_prompt`
  - `codex_execution_gate_blocked_unsafe_prompt`
  - `codex_execution_gate_blocked_threshold`
  - `codex_execution_gate_blocked_no_existing_codex_route`
  - `codex_execution_gate_ready`
  - `codex_execution_gate_decision_only`
- Threshold passes only when:
  - routed prompt exists
  - routed prompt is a file
  - prompt is non-empty
  - prompt read succeeds
  - prompt is not unsafe
  - prompt is not duplicate vs prior payload/state
  - bounded loop status is `loop_ready_or_routed_to_codex` or `loop_ready_or_routed_to_codex_fix`
- Blocks unsafe prompt categories:
  - Playwright ChatGPT automation
  - ChatGPT/OpenAI API usage
  - CAPTCHA/Verify bypass
  - cookie/token/session storage
  - unbounded loops
  - daemon/scheduler/queue drain
  - new shell/Codex execution mechanisms
  - commit/tag/PR/merge automation
  - destructive repo-external operations
- Existing route handling:
  - recognizes existing route signals:
    - `run_existing_codex_implementation_step`
    - `run_existing_codex_fix_step`
  - blocks with `codex_execution_gate_blocked_no_existing_codex_route` if not detected
- `enabled=true` + `execute_enabled=false` gives decision-only.
- `enabled=true` + `execute_enabled=true` gives readiness-only for existing route.
- Does not run Codex.
- Does not add a new command path.
- Exposes gate state in:
  - compact planning summary
  - supporting truth refs
  - final approved restart payload

## Validation
- `python -m py_compile automation/orchestration/planned_execution_runner.py` passed.

## Manual smoke
- Not executed in this run.

## Known follow-up
Prompt272 should connect this gate to existing Codex execution/capture flow:
- detect `codex_execution_gate_ready`
- use only existing safe execution/capture mechanisms
- ingest `scripts/capture_prompt_diff.sh` output
- normalize changed files / diff summary / validation summary

## Not included
- No tests.
- No Playwright.
- No ChatGPT API calls.
- No CAPTCHA/Verify bypass.
- No cookie/token/session storage.
- No runner daemon/scheduler.
- No multi-task queue.
- No unbounded loop.
- No new shell/Codex execution path.
- No commit/tag/PR automation.
- No duplicate-send path.
- No git mutation during implementation.
