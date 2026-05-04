# Prompt284.7 result: Codex live network blocker classified deterministically

## Result

Prompt284.7 added deterministic Codex invocation blocker classification for live connector failures.

Changed source:

- `automation/orchestration/planned_execution_runner.py`

## Validation

- `python -m py_compile automation/orchestration/planned_execution_runner.py`
- one-shot live reproduction through the existing live runner path

## Confirmed behavior

The live Codex connector path is still the existing path:

- `codex exec - --cd <repo> --sandbox read-only`

Prompt284.7 did not change the command path, sandbox mode, live authorization scope, or connector route.

## Classified blocker

The current live Codex invocation fails due to network denial:

- `project_browser_autonomous_codex_execution_connector_blocked_reason=codex_invocation_blocked_network_denied`
- `project_browser_autonomous_codex_execution_connector_invocation_blocker_class=network_denied`
- `project_browser_autonomous_codex_execution_connector_invocation_blocked_reason=codex_invocation_blocked_network_denied`
- `project_browser_autonomous_codex_execution_connector_invocation_retry_likely_repeats=true`

Receipt surface also records:

- `blocker_class=network_denied`
- `blocked_reason=codex_invocation_blocked_network_denied`
- `retry_likely_repeats=true`

Observed stderr summary:

- websocket connect failure
- `Operation not permitted`
- `wss://api.openai.com/v1/responses`

## Meaning

The live Codex invocation blocker is no longer ambiguous. The runner can now identify this environment as network-denied instead of treating the invocation failure as a generic completed failure.

## Remaining

Prompt285 diff capture is still blocked because no Codex diff was produced.

Next: Prompt284.8 should add a contract-level deterministic stop surface so future automation can short-circuit immediately when `network_denied` is detected, without repeated live attempts.

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
