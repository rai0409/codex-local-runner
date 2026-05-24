# Prompt Role Catalog

## role: daemon_lite_10_cycle_no_allow_boundary

Use when:
Prompt482 three-cycle usability confirmation is complete, Prompt483 role catalog reader handoff is complete, and the next step is to add only the no-allow boundary for a bounded 10-cycle daemon-lite smoke.

Goal:
ChatGPT generates a Codex implementation prompt for Prompt484a.
The prompt must add metadata/run_state support for the 10-cycle daemon-lite no-allow boundary only.

Required constraints:
- requested_cycle_count=10
- max_cycles=10
- max_invocations=10
- max_runtime_seconds=1800
- no Codex/runtime cycle execution in this role
- no explicit-allow execution in this role

Success:
- prompt484_daemon_lite_10_cycle_status="ready_requires_explicit_allow"
- prompt484_daemon_lite_10_cycle_ready=True
- prompt484_total_invocation_attempts=0
- prompt484_total_invocation_performed=0
- prompt484_no_11th_invocation_attempted=True
- prompt484_next_action="request_explicit_prompt484_daemon_lite_10_cycle_smoke_execution"

Do not:
- implement explicit 10-cycle execution
- implement real development task selection
- implement failed execution recovery
- implement completion-until-done
- modify Codex one-shot timeout behavior
- modify subprocess timeout logic
- commit/tag
- run tests
- push/PR/merge
- allow unbounded loop
- implement unrelated fixes

ChatGPT note:
Use this role as a prompt-generation basis.
Do not paste this role directly as the Codex prompt.
Generate a separate detailed Codex implementation prompt for Prompt484a.