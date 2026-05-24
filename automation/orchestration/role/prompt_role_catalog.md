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

## role: role_to_prompt_selection_layer

Use when:
Prompt484a no-allow boundary fields are implemented and verified, and the next step is to add a metadata-only role selection layer for the role-to-prompt loop.

Goal:
ChatGPT generates a Codex implementation prompt for Prompt484b.
The prompt must add a metadata-only role selection layer that selects the current role from the role catalog and exposes it in run_state for ChatGPT prompt generation.

Required constraints:
- read/select the current role from automation/orchestration/role/prompt_role_catalog.md
- default current role may be daemon_lite_10_cycle_no_allow_boundary until iteration support is added
- do not depend on Prompt482 evidence
- do not modify Prompt483 default selected role
- do not invoke Codex
- do not execute runtime cycles
- do not run tests
- do not commit/tag
- do not push/PR/merge
- do not implement all-role iteration yet

Success:
- prompt484b_role_selection_status="ready"
- prompt484b_role_selection_ready=True
- prompt484b_selected_role_id is non-empty
- prompt484b_selected_role_found=True
- prompt484b_selected_role_text_non_empty=True
- prompt484b_chatgpt_prompt_generation_required=True
- prompt484b_runner_prompt_generation_allowed=False
- prompt484b_next_action="chatgpt_generate_codex_prompt_from_selected_role"

Do not:
- implement explicit 10-cycle execution
- implement all-role automatic iteration
- implement completion-until-done
- modify Prompt482/Prompt483 behavior
- modify Codex one-shot timeout behavior
- modify subprocess timeout logic
- implement unrelated fixes

ChatGPT note:
Use this role as a prompt-generation basis.
Do not paste this role directly as the Codex prompt.
Generate a separate detailed Codex implementation prompt for Prompt484b.