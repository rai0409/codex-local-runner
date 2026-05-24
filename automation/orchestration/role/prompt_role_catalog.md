# Prompt Role Catalog

## role: daemon_lite_10_cycle_extension

Use when:
Prompt482 three-cycle usability confirmation is complete, and the next prompt should extend the existing 3-cycle smoke to a bounded 10-cycle smoke.

Goal:
Generate a Codex implementation prompt for daemon-lite 10-cycle extension.

Required config:
- max_cycles=10
- max_invocations=10
- max_runtime_seconds=1800
- requested_cycle_count=10

Success:
- cycle_0 through cycle_9 are attempted and performed
- total_invocation_attempts=10
- total_invocation_performed=10
- no_11th_invocation_attempted=True
- stop_reason="max_cycles_reached"

Do not:
- implement real development
- implement failed recovery
- implement completion-until-done
- commit/tag
- run tests
- push/PR/merge
- allow unbounded loop