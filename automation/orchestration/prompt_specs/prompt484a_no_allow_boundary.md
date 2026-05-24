# Prompt484a Prompt Spec: daemon-lite 10-cycle no-allow boundary

This file is a repo prompt spec for ChatGPT prompt generation.
This file is not the Codex prompt itself.

## Prompt ID

Prompt484a

## Selected role

daemon_lite_10_cycle_no_allow_boundary

## Goal

Add only metadata/run_state support for the Prompt484 10-cycle no-allow boundary.

Do not implement explicit 10-cycle execution.

## Target config

- requested_cycle_count=10
- max_cycles=10
- max_invocations=10
- max_runtime_seconds=1800

## Required implementation anchors

In `automation/orchestration/planned_execution_runner.py`:

- Refer to existing Prompt481 builder:
  `_build_prompt481_daemon_lite_repeated_cycle_state`

- Refer to existing Prompt483 builder:
  `_build_prompt483_role_catalog_reader_handoff_state`

- Add new builder immediately after:
  `_build_prompt483_role_catalog_reader_handoff_state`

- Add payload wiring immediately after:
  `prompt483_role_catalog_reader_handoff_payload`

- Existing wiring call anchor:
  `_build_prompt483_role_catalog_reader_handoff_state(`

In `automation/orchestration/run_state_summary_contract.py`:

- Add Prompt484a fields near Prompt483 fields:
  `prompt483_role_catalog_reader_status`
  `prompt483_selected_role_id`
  `prompt483_prompt484_generation_ready`

## Required builder name

`_build_prompt484_daemon_lite_10_cycle_no_allow_boundary_state`

## Allowed files

- `automation/orchestration/planned_execution_runner.py`
- `automation/orchestration/run_state_summary_contract.py`

## Forbidden edit areas

Do not edit code related to:

- `_LOCAL_CODEX_ONE_SHOT_EXECUTION_TIMEOUT_SECONDS`
- `_build_local_codex_one_shot_execution_result_state`
- `_build_dry_run_local_codex_one_shot_execution_result_state`
- `_build_local_codex_one_shot_execution_receipt_v2`
- `subprocess.run`
- `TimeoutExpired`
- Codex one-shot timeout behavior
- local Codex one-shot execution allowlist behavior
- old Prompt332 / unrelated Prompt4xx logic

## Required fields

- `prompt484_schema_version`
- `prompt484_applicable`
- `prompt484_daemon_lite_10_cycle_status`
- `prompt484_daemon_lite_10_cycle_ready`
- `prompt484_upstream_prompt483_evidence_ready`
- `prompt484_prompt483_evidence_source`
- `prompt484_requested_cycle_count`
- `prompt484_max_cycles`
- `prompt484_max_invocations`
- `prompt484_max_runtime_seconds`
- `prompt484_runtime_execution_requested`
- `prompt484_explicit_10_cycle_smoke_allow_present`
- `prompt484_allow_10_cycle_smoke`
- `prompt484_cycle_ids`
- `prompt484_total_invocation_attempts`
- `prompt484_total_invocation_performed`
- `prompt484_expected_invocation_count`
- `prompt484_invocation_count_within_limit`
- `prompt484_no_11th_invocation_attempted`
- `prompt484_no_unbounded_loop_guard_ready`
- `prompt484_completed_cycle_count`
- `prompt484_failed_cycle_count`
- `prompt484_stop_reason`
- `prompt484_stop_condition_reached`
- `prompt484_max_cycles_stop_confirmed`
- `prompt484_max_invocations_not_exceeded`
- `prompt484_max_runtime_not_exceeded`
- `prompt484_daemon_lite_10_cycle_smoke_confirmed`
- `prompt484_completion_until_done_handoff_ready`
- `prompt484_real_development_deferred`
- `prompt484_failed_recovery_deferred`
- `prompt484_human_review_required`
- `prompt484_human_intervention_required`
- `prompt484_auto_continue_allowed`
- `prompt484_auto_route_allowed`
- `prompt484_codex_invocation_allowed`
- `prompt484_file_creation_allowed`
- `prompt484_tests_allowed`
- `prompt484_commit_tag_allowed`
- `prompt484_push_allowed`
- `prompt484_pr_allowed`
- `prompt484_merge_allowed`
- `prompt484_unbounded_loop_allowed`
- `prompt484_blocked_reason`
- `prompt484_blocked_reasons`
- `prompt484_next_action`

## No-allow success behavior

When Prompt483 evidence is ready and explicit 10-cycle allow is missing:

- `prompt484_daemon_lite_10_cycle_status="ready_requires_explicit_allow"`
- `prompt484_daemon_lite_10_cycle_ready=True`
- `prompt484_upstream_prompt483_evidence_ready=True`
- `prompt484_requested_cycle_count=10`
- `prompt484_max_cycles=10`
- `prompt484_max_invocations=10`
- `prompt484_max_runtime_seconds=1800`
- `prompt484_runtime_execution_requested=False`
- `prompt484_explicit_10_cycle_smoke_allow_present=False`
- `prompt484_allow_10_cycle_smoke=False`
- `prompt484_cycle_ids=["cycle_0","cycle_1","cycle_2","cycle_3","cycle_4","cycle_5","cycle_6","cycle_7","cycle_8","cycle_9"]`
- `prompt484_total_invocation_attempts=0`
- `prompt484_total_invocation_performed=0`
- `prompt484_expected_invocation_count=10`
- `prompt484_invocation_count_within_limit=True`
- `prompt484_no_11th_invocation_attempted=True`
- `prompt484_no_unbounded_loop_guard_ready=True`
- `prompt484_completed_cycle_count=0`
- `prompt484_failed_cycle_count=0`
- `prompt484_stop_reason=""`
- `prompt484_stop_condition_reached=False`
- `prompt484_max_cycles_stop_confirmed=False`
- `prompt484_max_invocations_not_exceeded=True`
- `prompt484_max_runtime_not_exceeded=True`
- `prompt484_daemon_lite_10_cycle_smoke_confirmed=False`
- `prompt484_completion_until_done_handoff_ready=False`
- `prompt484_real_development_deferred=True`
- `prompt484_failed_recovery_deferred=True`
- `prompt484_human_review_required=False`
- `prompt484_human_intervention_required=False`
- `prompt484_auto_continue_allowed=True`
- `prompt484_auto_route_allowed=True`
- `prompt484_codex_invocation_allowed=False`
- `prompt484_file_creation_allowed=False`
- `prompt484_tests_allowed=False`
- `prompt484_commit_tag_allowed=False`
- `prompt484_push_allowed=False`
- `prompt484_pr_allowed=False`
- `prompt484_merge_allowed=False`
- `prompt484_unbounded_loop_allowed=False`
- `prompt484_blocked_reason=""`
- `prompt484_blocked_reasons=[]`
- `prompt484_next_action="request_explicit_prompt484_daemon_lite_10_cycle_smoke_execution"`

## Out of scope

Do not implement:

- explicit 10-cycle execution
- real development task selection
- failed execution recovery
- completion-until-done
- commit/tag execution
- tests
- push / PR / merge
- unbounded loop
- timeout fixes
- subprocess timeout changes
- unrelated safety fixes

## Acceptance anchors

The generated Codex prompt must require static checks for:

- `_build_prompt484_daemon_lite_10_cycle_no_allow_boundary_state`
- `prompt484_daemon_lite_10_cycle_status`
- `prompt484_daemon_lite_10_cycle_ready`
- `prompt484_requested_cycle_count`
- `prompt484_max_cycles`
- `prompt484_max_invocations`
- `prompt484_max_runtime_seconds`
- `prompt484_cycle_ids`
- `prompt484_no_11th_invocation_attempted`
- `request_explicit_prompt484_daemon_lite_10_cycle_smoke_execution`

The generated Codex prompt must explicitly reject changes containing:

- `_LOCAL_CODEX_ONE_SHOT_EXECUTION_TIMEOUT_SECONDS`
- `timeout=_LOCAL_CODEX_ONE_SHOT_EXECUTION_TIMEOUT_SECONDS`
- `_PROMPT484_ROLE_TO_CODEX_PROBE_MARKER`
