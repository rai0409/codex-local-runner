# Prompt284.8 result: Codex live network deterministic stop surface

## Result

Prompt284.8 added a contract-level deterministic stop surface for Codex live network denial.

Changed source:

- `automation/orchestration/planned_execution_runner.py`

## Validation

- `python -m py_compile automation/orchestration/planned_execution_runner.py`
- one-shot live reproduction through the existing supported live runner path

## Confirmed stop surface

Observed in `approved_restart_execution_contract.json`:

- `project_browser_autonomous_codex_live_network_status=blocked`
- `project_browser_autonomous_codex_live_network_blocker_class=network_denied`
- `project_browser_autonomous_codex_live_network_blocked_reason=codex_invocation_blocked_network_denied`
- `project_browser_autonomous_codex_live_retry_allowed=false`
- `project_browser_autonomous_codex_live_retry_likely_repeats=true`
- `project_browser_autonomous_codex_live_next_action=stop_live_network_unavailable`
- `project_browser_autonomous_codex_live_manual_action_required=true`

## Detection source

Primary detection source:

- `project_browser_autonomous_codex_execution_connector_invocation_blocker_class`

Fallbacks:

- `project_browser_autonomous_codex_invocation_result_blocker_class`
- `project_browser_autonomous_codex_invocation_execution_blocker_class`

Reason fallbacks:

- connector invocation blocked reason
- invocation result blocked reason
- invocation execution blocked reason

## Meaning

The current live Codex blocker is now surfaced as a deterministic stop condition instead of a generic completed failure.

Automation can now detect that live Codex retry is not useful in the current environment.

## Remaining

Prompt284.9 should wire this stop surface into top-level continuation / launch guards so live Codex retries are automatically short-circuited when:

- `project_browser_autonomous_codex_live_network_status=blocked`
- `project_browser_autonomous_codex_live_next_action=stop_live_network_unavailable`
- `project_browser_autonomous_codex_live_retry_allowed=false`

Prompt285 diff capture remains blocked until Codex produces a diff.

## Safety

- no commit/tag execution from runner
- no push
- no PR creation
- no merge
- no branch cleanup
- no daemon
- no scheduler
- no unbounded loop
- no Codex-produced repo diff
