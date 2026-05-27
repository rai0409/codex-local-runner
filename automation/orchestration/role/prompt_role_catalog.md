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

## role: selected_role_prompt_generation_request

Use when:
Prompt484b role selection layer is committed and verified, and the next step is to expose a metadata-only ChatGPT prompt generation request from the selected role.

Goal:
ChatGPT generates a Codex implementation prompt for Prompt484c.
The prompt must add a metadata-only prompt generation request packet that uses the selected role id/text from Prompt484b and exposes what ChatGPT should generate next.

Required constraints:
- consume Prompt484b selected role metadata from run_state
- do not generate the Codex prompt inside runner
- do not invoke Codex
- do not execute runtime cycles
- do not run tests
- do not commit/tag
- do not push/PR/merge
- do not implement all-role iteration yet

Success:
- prompt484c_prompt_generation_request_status="ready"
- prompt484c_prompt_generation_request_ready=True
- prompt484c_source_role_id="role_to_prompt_selection_layer"
- prompt484c_source_role_text_non_empty=True
- prompt484c_chatgpt_generation_required=True
- prompt484c_runner_generation_allowed=False
- prompt484c_codex_prompt_ready=False
- prompt484c_next_action="chatgpt_generate_codex_prompt_from_prompt484c_request"

Do not:
- implement Codex invocation
- implement prompt text generation by runner
- implement all-role automatic iteration
- implement completion-until-done
- modify Prompt482/Prompt483 behavior
- modify Codex one-shot timeout behavior
- modify subprocess timeout logic
- implement unrelated fixes

ChatGPT note:
Use this role as a prompt-generation basis.
Do not paste this role directly as the Codex prompt.
Generate a separate detailed Codex implementation prompt for Prompt484c.

## role: prompt484c_existing_loop_bridge

Use when:
Prompt484c selected-role prompt generation request is committed and verified, and existing success-loop artifacts prompt377/prompt378/prompt379/prompt385 are present but Prompt484c next_action is not directly consumed by the existing loop.

Goal:
ChatGPT generates a Codex implementation prompt for Prompt484d.
The prompt must add a metadata-only bridge from Prompt484c prompt generation request into the existing ChatGPT prompt generation / generated prompt intake / Codex execution bridge loop.

Required constraints:
- consume Prompt484c fields from run_state
- bridge Prompt484c request into existing prompt377 or prompt385 prompt-generation request semantics
- do not invoke Codex
- do not call ChatGPT inside runner
- do not execute runtime cycles
- do not generate the final Codex prompt text inside runner
- do not run tests
- do not commit/tag
- do not push/PR/merge
- do not modify subprocess timeout logic
- do not modify Prompt482/Prompt483 behavior

Success:
- prompt484d_existing_loop_bridge_status="ready"
- prompt484d_existing_loop_bridge_ready=True
- prompt484d_prompt484c_request_ready=True
- prompt484d_existing_prompt_generation_artifacts_detected=True
- prompt484d_bridge_target is either "prompt377_chatgpt_prompt_generation_request" or "prompt385_next_prompt_generation_request"
- prompt484d_chatgpt_prompt_generation_request_ready=True
- prompt484d_generated_prompt_intake_expected=True
- prompt484d_codex_execution_bridge_deferred=True
- prompt484d_next_action="supply_chatgpt_generated_prompt_to_existing_intake"

Do not:
- implement all-role automatic iteration
- implement completion-until-done
- implement failed execution recovery
- invoke Codex
- mutate git
- modify unrelated prompt builders

ChatGPT note:
Use this role as a prompt-generation basis.
Do not paste this role directly as the Codex prompt.
Generate a separate detailed Codex implementation prompt for Prompt484d.

## role: prompt484d_generated_prompt_intake_handoff

Use when:
Prompt484d existing-loop bridge is committed and verified, and the next step is to supply a ChatGPT-generated Codex prompt into the existing prompt378 generated prompt intake path.

Goal:
ChatGPT generates a Codex implementation prompt for Prompt484e.
The prompt must add a metadata-only handoff that connects Prompt484d bridge output to the existing prompt378 generated prompt intake contract.

Required constraints:
- consume Prompt484d fields from run_state
- require prompt484d_existing_loop_bridge_ready=True
- require prompt484d_next_action="supply_chatgpt_generated_prompt_to_existing_intake"
- expose the expected generated prompt input path/field for prompt378
- do not generate the final Codex prompt text inside runner
- do not invoke Codex
- do not call ChatGPT inside runner
- do not execute runtime cycles
- do not run tests
- do not commit/tag
- do not push/PR/merge
- do not implement all-role automatic iteration yet

Success:
- prompt484e_generated_prompt_intake_handoff_status="ready"
- prompt484e_generated_prompt_intake_handoff_ready=True
- prompt484e_prompt484d_bridge_ready=True
- prompt484e_bridge_target="prompt377_chatgpt_prompt_generation_request"
- prompt484e_generated_prompt_intake_target="prompt378_chatgpt_generated_prompt_intake"
- prompt484e_expected_generated_prompt_path_field="prompt378_generated_prompt_path"
- prompt484e_generated_prompt_supplied=False
- prompt484e_codex_execution_bridge_ready=False
- prompt484e_next_action="supply_generated_prompt_file_for_prompt378_intake"

Do not:
- implement Codex invocation
- implement ChatGPT invocation
- implement completion-until-done
- implement failed execution recovery
- mutate git
- modify subprocess timeout logic
- modify Prompt482/Prompt483 behavior
- modify unrelated prompt builders

ChatGPT note:
Use this role as a prompt-generation basis.
Do not paste this role directly as the Codex prompt.
Generate a separate detailed Codex implementation prompt for Prompt484e.

## role: prompt484f_role_driven_single_codex_execution_cycle

Use when:
Prompt484e is committed and verified, Prompt378 supplied generated prompt intake is verified, and the next step is to run one real role-driven Codex implementation cycle through the existing Prompt378→Prompt379 bridge.

Goal:
ChatGPT generates one Prompt378-valid Codex implementation prompt from a selected role.
The generated prompt must be supplied to Prompt378 and executed by Prompt379 through live transport.

Required constraints:
- use existing role catalog as the source of task intent
- generate a Prompt378-valid Codex prompt outside the runner
- supply the generated prompt through --prompt378-generated-prompt-path
- execute through Prompt379 live transport
- allow exactly one Codex execution
- require clean worktree before execution
- after execution, capture changed files and route to review
- do not auto-commit
- do not auto-tag
- do not push/PR/merge
- do not implement completion-until-done yet
- do not implement all-role automatic iteration yet

Success:
- prompt484f_role_driven_cycle_status="ready"
- prompt484f_role_driven_cycle_ready=True
- prompt484f_source_role_id is non-empty
- prompt484f_generated_prompt_for_prompt378_ready=True
- prompt484f_prompt378_supply_expected=True
- prompt484f_prompt379_live_execution_expected=True
- prompt484f_codex_execution_count_limit=1
- prompt484f_commit_tag_deferred=True
- prompt484f_next_action="generate_prompt378_valid_codex_prompt_for_selected_role"

Do not:
- bypass Prompt378 validation
- bypass Prompt379 tracked diff guard
- auto-commit
- auto-tag
- push/PR/merge
- run tests unless the generated prompt explicitly allows only py_compile
- modify Prompt482/Prompt483 behavior
- modify subprocess timeout behavior

ChatGPT note:
Use this role as the basis for generating one concrete Prompt378-valid Codex prompt.
The generated prompt must include literal validator tokens:
- success-path-only
- local-only
- no remote mutation
- no tests
- allowed files
- forbidden files
- expected artifacts or fields
- expected artifact or output
- validation commands
- out of scope
- next_action

## role: daemon_lite_10_cycle_extension

Use when:
Prompt484f role-driven single Codex execution cycle is committed and verified, Prompt483 selects daemon_lite_10_cycle_extension, and the next step is to continue role-to-prompt materialization for a bounded daemon-lite success-path extension.

Goal:
ChatGPT generates a Codex implementation prompt for the next bounded daemon-lite orchestration contract.
The prompt must describe deterministic, metadata-oriented execution contracts for extending the success path across up to 10 cycles without introducing daemon runtime loops or autonomous background execution.

Required constraints:
- continue role-to-prompt materialization from the selected role
- keep the implementation bounded to deterministic orchestration metadata and contracts
- require post-commit clean rerun verification before readiness is claimed
- preserve local-only execution with no remote mutation
- default to no tests unless a generated prompt explicitly narrows validation to allowed commands
- do not execute Prompt379 as part of this role
- do not implement daemon runtime behavior
- do not implement autonomous background execution
- do not implement completion-until-done semantics
- do not allow unbounded execution

Success:
- prompt483_selected_role_id="daemon_lite_10_cycle_extension"
- prompt483_selected_role_found=True
- prompt483_selected_role_text_non_empty=True
- prompt492_source_role_ready=True
- prompt493_bridge_ready=True
- prompt494_contract_injection_ready=True
- next_action="prepare_prompt495b_prompt483_role_catalog_ready_clean_rerun"

Do not:
- implement daemon runtime loops
- implement autonomous background execution
- implement completion-until-done
- invoke Codex
- execute Prompt379
- run tests by default
- push/PR/merge
- mutate remote state
- introduce unbounded execution
- modify Prompt483 parser behavior

ChatGPT note:
Use this role as a prompt-generation basis.
Do not paste this role directly as the Codex prompt.
Generate a separate detailed Codex implementation prompt for the next bounded daemon-lite orchestration contract.
