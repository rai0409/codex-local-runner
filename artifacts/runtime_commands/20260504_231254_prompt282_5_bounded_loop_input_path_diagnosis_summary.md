# Prompt282/282.5 result: bounded local loop real-runner exposure and input-path diagnosis

## Result

Prompt282 confirmed that real planned-runner dry-run output exposes `project_browser_autonomous_bounded_local_loop_*` fields in `approved_restart_execution_contract.json`.

Observed Prompt282 state:

- `project_browser_autonomous_bounded_local_loop_status=bounded_local_loop_not_requested`
- `project_browser_autonomous_bounded_local_loop_next_action=enable_bounded_local_loop`
- `project_browser_autonomous_bounded_local_loop_enabled=false`
- `project_browser_autonomous_bounded_local_loop_continue_enabled=false`
- `project_browser_autonomous_bounded_local_loop_blocked_reason=bounded_local_loop_disabled`

Prompt282.5 then attempted to enable bounded local loop controls through:

- `--retry-context`
- `--policy-snapshot`

Both inputs provided:

- `project_browser_autonomous_bounded_local_loop_enabled=true`
- `project_browser_autonomous_bounded_local_loop_continue_enabled=false`
- `project_browser_autonomous_bounded_local_loop_max_iterations=1`
- `project_browser_autonomous_bounded_local_loop_iteration=0`
- `project_browser_autonomous_bounded_local_loop_max_consecutive_failures=1`
- `project_browser_autonomous_bounded_local_loop_consecutive_failures=0`

Observed output still remained:

- `project_browser_autonomous_bounded_local_loop_enabled=false`
- `project_browser_autonomous_bounded_local_loop_status=bounded_local_loop_not_requested`
- `project_browser_autonomous_bounded_local_loop_next_action=enable_bounded_local_loop`

## Diagnosis

The runner loads retry context and policy snapshot, but bounded local loop control keys are not currently wired into the `approved_restart` payload consumed by `_build_project_browser_autonomous_bounded_local_loop_coordinator_state(...)`.

Observed implementation anchors:

- `_build_project_browser_autonomous_bounded_local_loop_coordinator_state(...)` is called with `approved_restart_payload=approved_restart`.
- retry context and policy snapshot are loaded in the runner, but their bounded loop control keys are not reflected in the approved restart execution contract.

## Next

Prompt282.6 should add allowlist-only wiring from explicit real-runner input into the approved restart payload passed to the bounded local loop coordinator.

Allowed keys only:

- `project_browser_autonomous_bounded_local_loop_enabled`
- `project_browser_autonomous_bounded_local_loop_continue_enabled`
- `project_browser_autonomous_bounded_local_loop_max_iterations`
- `project_browser_autonomous_bounded_local_loop_iteration`
- `project_browser_autonomous_bounded_local_loop_max_consecutive_failures`
- `project_browser_autonomous_bounded_local_loop_consecutive_failures`

Priority should be:

`retry_context > policy_snapshot > approved_restart > defaults`

## Safety

No source mutation was performed by the runner checks.

The checks were:

- dry-run only
- no live Codex execution
- no git mutation from runner
- no GitHub mutation
- no daemon
- no unbounded loop
