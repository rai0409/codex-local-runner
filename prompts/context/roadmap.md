# Autonomous Development Roadmap

## Current status

This repository is not yet a complete always-on autonomous development system.

The current system has strong deterministic planning, control, safety, receipt, ledger, retry, and short-batch invocation foundations. It can determine next actions and prove safe invocation paths for bounded short-batch steps.

It does not yet reliably execute an unattended max-two-launch rolling loop, and it does not yet provide a complete always-on autonomous development workflow.

## Completed or mostly completed foundations

The following foundations are considered present:

```text
planning artifacts
roadmap / PR slicing
implementation prompt compilation
planned execution runner foundation
Codex executor adapter foundation
normalized execution result surfaces
deterministic next_action controller
authority / routing / progression contracts
bounded execution and authorization contracts
approval safety / bounded restart posture
retry / re-entry posture
verification / closure posture
failure memory / suppression posture
quality gate / branch lifecycle posture
queue / handoff state surfaces
human escalation state
fleet safety / retention / artifact surfaces
```

## Local autonomous browser/development stack

The local `planned_execution_runner.py` stack has reached:

```text
PR132 short-batch next_action producer
PR136 bounded rolling multi-launch gate
PR137 short-batch invocation adapter
```

PR137 is considered completed as a dependency for the next bounded rolling execution work.

Primary PR137 builder:

```text
_build_project_browser_autonomous_short_batch_invocation_state
```

Important PR137 fields:

```text
project_browser_autonomous_short_batch_invocation_status
project_browser_autonomous_short_batch_invocation_permission
project_browser_autonomous_short_batch_invocation_receipt_status
project_browser_autonomous_short_batch_invocation_path_status
project_browser_autonomous_short_batch_invocation_runtime_capability
project_browser_autonomous_short_batch_invocation_next_action
project_browser_autonomous_short_batch_invocation_delegation_mode
project_browser_autonomous_short_batch_invocation_call_path_ref
project_browser_autonomous_short_batch_invocation_missing_inputs
```

Verified PR137 next_action call-path refs:

```text
run_one_md_apply        -> project_browser_autonomous_md_apply_state
run_one_browser_command -> project_browser_autonomous_browser_execution_state
run_one_codex_attempt   -> project_browser_autonomous_codex_execution_state
assimilate_result       -> project_browser_autonomous_codex_result_assimilation_state
persist_ledger          -> project_browser_autonomous_run_ledger_persistence_state
stop                    -> no_runtime_invocation_stop
```

## Strict PR137 rule

For non-stop actions, `actual_bounded_invocation` is valid only when all are true:

```text
project_browser_autonomous_short_batch_invocation_path_status=available
project_browser_autonomous_short_batch_invocation_runtime_capability=actual_bounded_invocation
project_browser_autonomous_short_batch_invocation_receipt_status=ready
project_browser_autonomous_short_batch_invocation_delegation_mode in {
  reused_existing_state_call_path,
  invoked_existing_builder
}
project_browser_autonomous_short_batch_invocation_call_path_ref != none
project_browser_autonomous_short_batch_invocation_missing_inputs == []
```

For `next_action=stop`:

```text
project_browser_autonomous_short_batch_invocation_delegation_mode=no_runtime_invocation_stop
project_browser_autonomous_short_batch_invocation_call_path_ref=none
```

## Critical gap

The next missing component is:

```text
project_browser_autonomous_rolling_execution_*
```

This should consume:

```text
PR136 rolling_multi_launch gate
PR137 short_batch_invocation adapter
```

and produce a bounded rolling execution state.

## Prompt138 target

Prompt138 must implement B first:

```text
B. Prepare a bounded max-two-launch rolling_execution_* state.
```

Prompt138 must not claim complete autonomy.

Prompt138 may implement A only if a safe existing bounded launch execution helper is already available:

```text
A. Actually execute up to two launches.
```

A is allowed only when:

```text
an existing bounded launch execution helper exists
no new executor is created
no daemon / scheduler / sleep loop is created
no queue is drained
no GitHub mutation path is introduced
launches_attempted is incremented only after a real attempt
launches_completed is incremented only after receipt/ledger-confirmed completion
```

If A is not possible in Prompt138:

```text
status=prepared
launches_attempted=0
launches_completed=0
runtime_capability=prepared_only
block_reason or stop_reason=bounded_launch_helper_missing
```

## Future roadmap after Prompt138

```text
Prompt138:
  bounded rolling execution state and strict gates.

Prompt139:
  actual bounded launch helper connection if not completed in Prompt138.

Later:
  runner entrypoint integration.

Later:
  approval / GitHub write / PR creation integration.

Later:
  scheduler / queue integration.

Later:
  fully unattended autonomous development only after all safety, receipt, ledger, and stop gates are proven.
```

## Explicit non-goals until proven

Do not claim or add:

```text
complete always-on autopilot
unbounded autonomous execution
daemon
scheduler
sleep loop
queue drain
third launch
new browser executor
new Codex executor
new ledger persistence mechanism
automatic GitHub PR creation
automatic push / merge
CI auto-fix loop
```


---

## Prompt138 result — B-only bounded rolling execution state

### Status

Prompt138 completed the B-only prepared bounded rolling execution layer.

This does not mean complete autonomous development is finished.

Prompt138 intentionally did not implement A, actual launch execution.

### Primary implementation file

```text
automation/orchestration/planned_execution_runner.py
```

### New builder

```text
_build_project_browser_autonomous_rolling_execution_state
```

### New field prefix

```text
project_browser_autonomous_rolling_execution_*
```

### Added rolling_execution fields

```text
project_browser_autonomous_rolling_execution_status
project_browser_autonomous_rolling_execution_kind
project_browser_autonomous_rolling_execution_permission
project_browser_autonomous_rolling_execution_source_status
project_browser_autonomous_rolling_execution_block_reason
project_browser_autonomous_rolling_execution_receipt_status
project_browser_autonomous_rolling_execution_receipt_kind
project_browser_autonomous_rolling_execution_next_action
project_browser_autonomous_rolling_execution_runtime_capability
project_browser_autonomous_rolling_execution_launches_allowed
project_browser_autonomous_rolling_execution_launches_attempted
project_browser_autonomous_rolling_execution_launches_completed
project_browser_autonomous_rolling_execution_max_launches
project_browser_autonomous_rolling_execution_per_launch_max_steps
project_browser_autonomous_rolling_execution_total_step_budget
project_browser_autonomous_rolling_execution_failure_budget
project_browser_autonomous_rolling_execution_stop_reason
project_browser_autonomous_rolling_execution_invocation_runtime_capability
project_browser_autonomous_rolling_execution_invocation_delegation_mode
project_browser_autonomous_rolling_execution_invocation_call_path_ref
project_browser_autonomous_rolling_execution_invocation_receipt_status
project_browser_autonomous_rolling_execution_runtime_posture
```

### Consumed PR136 gates

Prompt138 consumes:

```text
project_browser_autonomous_rolling_multi_launch_status == prepared
project_browser_autonomous_rolling_multi_launch_permission == allowed_candidate
project_browser_autonomous_rolling_multi_launch_receipt_status == ready
project_browser_autonomous_rolling_multi_launch_next_action == launch_up_to_two_short_batches
```

Failures map to:

```text
rolling_multi_launch_not_ready
rolling_multi_launch_action_not_launch
```

### Consumed PR137 gates

Prompt138 consumes:

```text
project_browser_autonomous_short_batch_invocation_path_status == available
project_browser_autonomous_short_batch_invocation_runtime_capability == actual_bounded_invocation
project_browser_autonomous_short_batch_invocation_receipt_status == ready
project_browser_autonomous_short_batch_invocation_delegation_mode in {
  reused_existing_state_call_path,
  invoked_existing_builder,
  no_runtime_invocation_stop
}
```

For non-stop invocation actions, Prompt138 also requires:

```text
project_browser_autonomous_short_batch_invocation_call_path_ref != none
project_browser_autonomous_short_batch_invocation_missing_inputs == []
```

For invocation `next_action=stop`, Prompt138 emits terminal-stop posture without runtime invocation.

### B-only behavior

Prompt138 implemented prepared-only bounded rolling execution:

```text
project_browser_autonomous_rolling_execution_runtime_capability=prepared_only
project_browser_autonomous_rolling_execution_launches_allowed=2
project_browser_autonomous_rolling_execution_launches_attempted=0
project_browser_autonomous_rolling_execution_launches_completed=0
```

The builder returns 0 for both `launches_attempted` and `launches_completed` in all branches.

Normalization hard-clamps any non-zero value back to 0.

### What Prompt138 did not implement

Prompt138 did not implement A:

```text
actual launch execution
bounded launch helper invocation
launches_attempted > 0
launches_completed > 0
```

Prompt138 also did not add:

```text
complete autonomy claim
daemon
scheduler
sleep loop
queue drain
unbounded autonomous execution
third launch
new browser executor
new Codex executor
new ledger persistence mechanism
new GitHub write path
GitHub mutation
PR creation
PR merge
CI auto-fix loop
```

### Validation

Prompt138 validation:

```text
python -m py_compile automation/orchestration/planned_execution_runner.py
```

Result:

```text
passed
```

### Next roadmap item

Next step is Prompt139.

Prompt139 must not create a new executor.

Prompt139 should first search for an existing safe bounded launch helper or call path.

If an existing helper exists and can be safely invoked:

```text
connect it to project_browser_autonomous_rolling_execution_*
attempt at most 2 launches
increment launches_attempted only after real invocation
increment launches_completed only after receipt/ledger-confirmed completion
never attempt a third launch
```

If no safe helper exists:

```text
do not fake execution
keep launches_attempted=0
keep launches_completed=0
emit bounded_launch_helper_missing
```

