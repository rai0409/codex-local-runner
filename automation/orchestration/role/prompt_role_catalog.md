# Prompt Role Catalog

## role: daemon_lite_10_cycle_extension

Use when:
Prompt482 three-cycle usability confirmation is complete, Prompt483 role catalog reader handoff is complete, and the next step is to extend the existing daemon-lite smoke from 3 cycles to 10 cycles.

Goal:
ChatGPT generates a Codex implementation prompt for Prompt484.
The prompt must implement a bounded daemon-lite 10-cycle smoke based on the existing Prompt481 repeated-cycle smoke pattern.

Required constraints:
- requested_cycle_count=10
- max_cycles=10
- max_invocations=10
- max_runtime_seconds=1800

Success:
- cycle_0 through cycle_9 are attempted and performed
- total_invocation_attempts=10
- total_invocation_performed=10
- no_11th_invocation_attempted=True
- stop_reason="max_cycles_reached"

Do not:
- implement real development task selection
- implement failed execution recovery
- implement completion-until-done
- commit/tag
- run tests
- push/PR/merge
- allow unbounded loop
- implement unrelated fixes

ChatGPT note:
Use this role as a prompt-generation basis.
Do not paste this role directly as the Codex prompt.
Generate a separate detailed Codex implementation prompt for Prompt484.