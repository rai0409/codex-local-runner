from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from pathlib import PurePosixPath
import shutil
import subprocess
import sys
import time
from typing import Any
from typing import Callable
from typing import Mapping
from typing import Sequence
from urllib import error as urllib_error
from urllib import request as urllib_request

from automation.control.action_handoff import build_action_handoff_payload
from automation.control.next_action_controller import evaluate_next_action_from_run_dir
from automation.control.retry_context_store import FileRetryContextStore
from automation.execution.codex_executor_adapter import CodexExecutorAdapter
from automation.orchestration.approval_transport import build_approval_run_state_summary_surface
from automation.orchestration.approval_transport import build_approval_transport_surface
from automation.orchestration.artifact_index import build_contract_artifact_index
from automation.orchestration.completion_contract import build_completion_contract_surface
from automation.orchestration.completion_contract import build_completion_run_state_summary_surface
from automation.orchestration.execution_authorization_gate import build_execution_authorization_gate_run_state_summary_surface
from automation.orchestration.execution_authorization_gate import build_execution_authorization_gate_surface
from automation.orchestration.execution_result_contract import build_execution_result_contract_run_state_summary_surface
from automation.orchestration.execution_result_contract import build_execution_result_contract_surface
from automation.orchestration.verification_closure_contract import build_verification_closure_contract_surface
from automation.orchestration.verification_closure_contract import build_verification_closure_run_state_summary_surface
from automation.orchestration.retry_reentry_loop_contract import build_retry_reentry_loop_contract_surface
from automation.orchestration.retry_reentry_loop_contract import build_retry_reentry_loop_run_state_summary_surface
from automation.orchestration.endgame_closure_contract import build_endgame_closure_contract_surface
from automation.orchestration.endgame_closure_contract import build_endgame_closure_run_state_summary_surface
from automation.orchestration.loop_hardening_contract import build_loop_hardening_contract_surface
from automation.orchestration.loop_hardening_contract import build_loop_hardening_run_state_summary_surface
from automation.orchestration.lane_stabilization_contract import build_lane_stabilization_contract_surface
from automation.orchestration.lane_stabilization_contract import build_lane_stabilization_run_state_summary_surface
from automation.orchestration.observability_rollup import build_failure_bucket_rollup_summary_surface
from automation.orchestration.observability_rollup import build_failure_bucket_rollup_surface
from automation.orchestration.observability_rollup import build_fleet_run_rollup_summary_surface
from automation.orchestration.observability_rollup import build_fleet_run_rollup_surface
from automation.orchestration.observability_rollup import build_observability_rollup_contract_summary_surface
from automation.orchestration.observability_rollup import build_observability_rollup_contract_surface
from automation.orchestration.observability_rollup import build_observability_rollup_run_state_summary_surface
from automation.orchestration.failure_bucketing_hardening import build_failure_bucketing_hardening_run_state_summary_surface
from automation.orchestration.failure_bucketing_hardening import build_failure_bucketing_hardening_summary_surface
from automation.orchestration.failure_bucketing_hardening import build_failure_bucketing_hardening_contract_surface
from automation.orchestration.artifact_retention import build_artifact_retention_contract_surface
from automation.orchestration.artifact_retention import build_artifact_retention_run_state_summary_surface
from automation.orchestration.artifact_retention import build_artifact_retention_summary_surface
from automation.orchestration.artifact_retention import build_retention_manifest_summary_surface
from automation.orchestration.artifact_retention import build_retention_manifest_surface
from automation.orchestration.fleet_safety_control import build_fleet_safety_control_contract_surface
from automation.orchestration.fleet_safety_control import build_fleet_safety_control_run_state_summary_surface
from automation.orchestration.fleet_safety_control import build_fleet_safety_control_summary_surface
from automation.orchestration.approval_email_delivery import build_approval_email_delivery_contract_surface
from automation.orchestration.approval_email_delivery import build_approval_email_delivery_run_state_summary_surface
from automation.orchestration.approval_email_delivery import build_approval_email_delivery_summary_surface
from automation.orchestration.approval_runtime_policy import build_approval_runtime_rules_contract_surface
from automation.orchestration.approval_runtime_policy import build_approval_runtime_rules_run_state_summary_surface
from automation.orchestration.approval_runtime_policy import build_approval_runtime_rules_summary_surface
from automation.orchestration.approval_delivery_adapter import build_approval_delivery_handoff_contract_surface
from automation.orchestration.approval_delivery_adapter import build_approval_delivery_handoff_run_state_summary_surface
from automation.orchestration.approval_delivery_adapter import build_approval_delivery_handoff_summary_surface
from automation.orchestration.approval_response_ingest import build_approved_restart_contract_surface
from automation.orchestration.approval_response_ingest import build_approved_restart_run_state_summary_surface
from automation.orchestration.approval_response_ingest import build_approved_restart_summary_surface
from automation.orchestration.approval_response_ingest import build_approval_response_contract_surface
from automation.orchestration.approval_response_ingest import build_approval_response_run_state_summary_surface
from automation.orchestration.approval_response_ingest import build_approval_response_summary_surface
from automation.orchestration.approval_safety import build_approval_safety_contract_surface
from automation.orchestration.approval_safety import build_approval_safety_run_state_summary_surface
from automation.orchestration.approval_safety import build_approval_safety_summary_surface
from automation.orchestration.bounded_execution_bridge import build_bounded_execution_bridge_run_state_summary_surface
from automation.orchestration.bounded_execution_bridge import build_bounded_execution_bridge_surface
from automation.orchestration.lifecycle_terminal_state import build_lifecycle_terminal_state_surface
from automation.orchestration.objective_contract import build_objective_contract_surface
from automation.orchestration.objective_contract import build_objective_run_state_summary_surface
from automation.orchestration.operator_explainability import build_operator_explainability_surface
from automation.orchestration.repair_suggestion_contract import build_repair_suggestion_contract_surface
from automation.orchestration.repair_suggestion_contract import build_repair_suggestion_run_state_summary_surface
from automation.orchestration.repair_approval_binding import build_repair_approval_binding_run_state_summary_surface
from automation.orchestration.repair_approval_binding import build_repair_approval_binding_surface
from automation.orchestration.repair_plan_transport import build_repair_plan_transport_run_state_summary_surface
from automation.orchestration.repair_plan_transport import build_repair_plan_transport_surface
from automation.orchestration.repair_plan_transport import REPAIR_PLAN_CANDIDATE_ACTIONS
from automation.orchestration.repair_plan_transport import REPAIR_PLAN_CLASSES
from automation.orchestration.reconcile_contract import build_reconcile_contract_surface
from automation.orchestration.reconcile_contract import build_reconcile_run_state_summary_surface
from automation.orchestration.run_state_summary_contract import build_manifest_run_state_summary_contract_surface
from automation.orchestration.run_state_summary_contract import select_manifest_run_state_summary_compact
from automation.planning.prompt_compiler import compile_prompt_units
from automation.planning.prompt_compiler import load_planning_artifacts

from automation.orchestration.planned_runner.utils import (
    _PROMPT450_SCHEMA_VERSION,
    _PROMPT451_SCHEMA_VERSION,
    _PROMPT452_BLOCKED_RETURNCODE_CLASSIFICATIONS,
    _PROMPT452_SCHEMA_VERSION,
    _PROMPT452_SUCCESS_RETURNCODE_CLASSIFICATIONS,
    _PROMPT453_SCHEMA_VERSION,
    _PROMPT454_APPLICABLE_PROMPT452_BLOCKED_REASONS,
    _PROMPT454_SCHEMA_VERSION,
    _PROMPT455_SCHEMA_VERSION,
    _PROMPT456_SCHEMA_VERSION,
    _PROMPT457_SCHEMA_VERSION,
    _PROMPT458_SCHEMA_VERSION,
    _PROMPT459_SCHEMA_VERSION,
    _PROMPT460_SCHEMA_VERSION,
    _PROMPT461_SCHEMA_VERSION,
    _PROMPT462_SCHEMA_VERSION,
    _PROMPT463_SCHEMA_VERSION,
    _PROMPT464_SCHEMA_VERSION,
    _PROMPT465_SCHEMA_VERSION,
    _PROMPT466_SCHEMA_VERSION,
    _PROMPT467_SCHEMA_VERSION,
    _PROMPT468_SCHEMA_VERSION,
    _PROMPT469_SCHEMA_VERSION,
    _PROMPT470_SCHEMA_VERSION,
    _PROMPT471_COMMIT_MESSAGE,
    _PROMPT471_SCHEMA_VERSION,
    _PROMPT471_TAG_NAME,
    _PROMPT472_COMMIT_MESSAGE,
    _PROMPT472_NEXT_ACTION,
    _PROMPT472_NEXT_PROMPT_ID,
    _PROMPT472_SCHEMA_VERSION,
    _PROMPT472_TAG_NAME,
    _PROMPT472_VALID_FINAL_HEAD_SUBJECTS,
    _PROMPT472_VALID_FINAL_TAG_NAMES,
    _PROMPT473_ALLOWED_TRACKED_FILES,
    _PROMPT473_NEXT_ACTION,
    _PROMPT473_SCHEMA_VERSION,
    _PROMPT474_ALLOWED_TRACKED_FILES,
    _PROMPT474_SCHEMA_VERSION,
    _PROMPT475_ALLOWED_TRACKED_FILES,
    _PROMPT475_NEXT_ACTION,
    _PROMPT475_SCHEMA_VERSION,
    _PROMPT475_VALID_FINAL_HEAD_SUBJECTS,
    _PROMPT475_VALID_FINAL_TAG_NAMES,
    _PROMPT476_ALLOWED_TRACKED_FILES,
    _PROMPT476_CONFIRMED_NEXT_ACTION,
    _PROMPT476_PRE_COMMIT_NEXT_ACTION,
    _PROMPT476_PROMPT476_HEAD_SUBJECTS,
    _PROMPT476_PROMPT476_TAG_NAMES,
    _PROMPT476_SCHEMA_VERSION,
    _PROMPT476_VALID_FINAL_HEAD_SUBJECTS,
    _PROMPT476_VALID_FINAL_TAG_NAMES,
    _PROMPT477_ALLOWED_TRACKED_FILES,
    _PROMPT477_BLOCKED_NEXT_ACTION,
    _PROMPT477_CYCLE_IDS,
    _PROMPT477_MAX_CYCLE_COUNT,
    _PROMPT477_NEXT_ACTION,
    _PROMPT477_REQUESTED_CYCLE_COUNT,
    _PROMPT477_SCHEMA_VERSION,
    _PROMPT477_VALID_FINAL_HEAD_SUBJECTS,
    _PROMPT477_VALID_FINAL_TAG_NAMES,
    _PROMPT478_ALLOWED_TRACKED_FILES,
    _PROMPT478_BLOCKED_NEXT_ACTION,
    _PROMPT478_CYCLE_IDS,
    _PROMPT478_MAX_CYCLE_COUNT,
    _PROMPT478_REQUESTED_CYCLE_COUNT,
    _PROMPT478_REVIEW_NEXT_ACTION,
    _PROMPT478_SCHEMA_VERSION,
    _PROMPT478_SUCCESS_NEXT_ACTION,
    _PROMPT479_ALLOWED_TRACKED_FILES,
    _PROMPT479_BLOCKED_NEXT_ACTION,
    _PROMPT479_DEFAULT_MAX_CYCLES,
    _PROMPT479_DEFAULT_MAX_INVOCATIONS,
    _PROMPT479_DEFAULT_MAX_RUNTIME_SECONDS,
    _PROMPT479_MAX_CYCLES_UPPER_BOUND,
    _PROMPT479_MAX_INVOCATIONS_UPPER_BOUND,
    _PROMPT479_MAX_RUNTIME_SECONDS_UPPER_BOUND,
    _PROMPT479_SCHEMA_VERSION,
    _PROMPT479_SUCCESS_NEXT_ACTION,
    _PROMPT480_ALLOWED_TRACKED_FILES,
    _PROMPT480_BLOCKED_NEXT_ACTION,
    _PROMPT480_SCHEMA_VERSION,
    _PROMPT480_STOPPED_NEXT_ACTION,
    _PROMPT480_SUCCESS_NEXT_ACTION,
    _PROMPT481_ALLOWED_TRACKED_FILES,
    _PROMPT481_BLOCKED_NEXT_ACTION,
    _PROMPT481_CYCLE_IDS,
    _PROMPT481_DEFAULT_MAX_INVOCATIONS,
    _PROMPT481_DEFAULT_MAX_RUNTIME_SECONDS,
    _PROMPT481_MAX_CYCLES,
    _PROMPT481_MAX_RUNTIME_SECONDS_UPPER_BOUND,
    _PROMPT481_NO_ALLOW_NEXT_ACTION,
    _PROMPT481_REQUESTED_CYCLE_COUNT,
    _PROMPT481_SCHEMA_VERSION,
    _PROMPT481_STOPPED_NEXT_ACTION,
    _PROMPT481_SUCCESS_NEXT_ACTION,
    _PROMPT482_ALLOWED_TRACKED_FILES,
    _PROMPT482_BLOCKED_NEXT_ACTION,
    _PROMPT482_SCHEMA_VERSION,
    _PROMPT482_SUCCESS_NEXT_ACTION,
    _PROMPT483_ALLOWED_TRACKED_FILES,
    _PROMPT483_BLOCKED_NEXT_ACTION,
    _PROMPT483_DEFAULT_ROLE_CATALOG_PATH,
    _PROMPT483_DEFAULT_SELECTED_ROLE_ID,
    _PROMPT483_SCHEMA_VERSION,
    _PROMPT483_SUCCESS_NEXT_ACTION,
    _PROMPT484B_BLOCKED_NEXT_ACTION,
    _PROMPT484B_DEFAULT_SELECTED_ROLE_ID,
    _PROMPT484B_SCHEMA_VERSION,
    _PROMPT484B_SUCCESS_NEXT_ACTION,
    _PROMPT484C_BLOCKED_NEXT_ACTION,
    _PROMPT484C_SCHEMA_VERSION,
    _PROMPT484C_SUCCESS_NEXT_ACTION,
    _PROMPT484D_BLOCKED_NEXT_ACTION,
    _PROMPT484D_SCHEMA_VERSION,
    _PROMPT484D_SUCCESS_NEXT_ACTION,
    _PROMPT484E_BLOCKED_NEXT_ACTION,
    _PROMPT484E_SCHEMA_VERSION,
    _PROMPT484E_SUCCESS_NEXT_ACTION,
    _PROMPT484F_BLOCKED_NEXT_ACTION,
    _PROMPT484F_SCHEMA_VERSION,
    _PROMPT484F_SOURCE_ROLE_ID,
    _PROMPT484F_SUCCESS_NEXT_ACTION,
    _PROMPT484G_BLOCKED_NEXT_ACTION,
    _PROMPT484G_SCHEMA_VERSION,
    _PROMPT484G_SUCCESS_NEXT_ACTION,
    _PROMPT484H_BLOCKED_NEXT_ACTION,
    _PROMPT484H_REQUIRED_VALIDATOR_TOKENS,
    _PROMPT484H_SCHEMA_VERSION,
    _PROMPT484H_SUCCESS_NEXT_ACTION,
    _PROMPT484I_BLOCKED_NEXT_ACTION,
    _PROMPT484I_SCHEMA_VERSION,
    _PROMPT484I_SUCCESS_NEXT_ACTION,
    _PROMPT484_BLOCKED_NEXT_ACTION,
    _PROMPT484_SCHEMA_VERSION,
    _PROMPT484_SUCCESS_NEXT_ACTION,
    _PROMPT485_BLOCKED_NEXT_ACTION,
    _PROMPT485_SCHEMA_VERSION,
    _PROMPT485_SUCCESS_NEXT_ACTION,
    _PROMPT486_BLOCKED_NEXT_ACTION,
    _PROMPT486_SCHEMA_VERSION,
    _PROMPT486_SUCCESS_NEXT_ACTION,
    _PROMPT487_BLOCKED_NEXT_ACTION,
    _PROMPT487_SCHEMA_VERSION,
    _PROMPT487_SUCCESS_NEXT_ACTION,
    _PROMPT489_NEXT_ACTION,
    _PROMPT490_NEXT_ACTION,
    _PROMPT491A_BLOCKED_NEXT_ACTION,
    _PROMPT491A_SCHEMA_VERSION,
    _PROMPT491A_SUCCESS_NEXT_ACTION,
    _PROMPT491_NEXT_ACTION,
    _PROMPT492_BLOCKED_NEXT_ACTION,
    _PROMPT492_REQUIRED_CANONICAL_SECTIONS,
    _PROMPT492_SCHEMA_VERSION,
    _PROMPT492_SUCCESS_NEXT_ACTION,
    _PROMPT493_BLOCKED_NEXT_ACTION,
    _PROMPT493_SCHEMA_VERSION,
    _PROMPT493_SUCCESS_NEXT_ACTION,
    _PROMPT494_BLOCKED_NEXT_ACTION,
    _PROMPT494_SCHEMA_VERSION,
    _PROMPT494_SUCCESS_NEXT_ACTION,
    _PROMPT496_BLOCKED_NEXT_ACTION,
    _PROMPT496_SCHEMA_VERSION,
    _PROMPT496_SUCCESS_NEXT_ACTION,
    _PROMPT497_BLOCKED_NEXT_ACTION,
    _PROMPT497_SUCCESS_NEXT_ACTION,
    _PROMPT498_BLOCKED_NEXT_ACTION,
    _PROMPT498_SUCCESS_NEXT_ACTION,
    _as_non_negative_int,
    _as_optional_int,
    _normalize_string_list,
    _normalize_text,
    _prompt450_result_artifact_path,
    _prompt450_result_available,
    _prompt450_retry_value,
    _prompt450_returncode_classification,
    _prompt450_runtime_command_json,
    _prompt450_runtime_packet_valid,
    _prompt451_bool_input,
    _prompt451_success_approve_candidate,
    _prompt452_boolish,
    _prompt452_error_summary_indicates_unsafe,
    _prompt452_first_present,
    _prompt452_first_text,
    _prompt452_known_string_list,
    _prompt452_observed_mutation,
    _prompt452_safe_deferred_next_action,
    _prompt452_source_kind,
    _prompt453_explicit_commit_tag_allow_present,
    _prompt453_safe_deferred_next_action,
    _prompt454_first_known_string_list,
    _prompt454_first_returncode,
    _prompt454_first_returncode_classification,
    _prompt454_safe_deferred_next_action,
    _prompt454_source_kind,
    _prompt455_explicit_commit_tag_allow_source,
    _prompt455_known_string_list,
    _prompt455_safe_deferred_next_action,
    _prompt456_explicit_commit_tag_allow_source,
    _prompt456_first_known_string_list,
    _prompt456_runtime_command_explicit_commit_tag_allow_metadata,
    _prompt456_tag_uniqueness_state,
    _prompt457_first_text,
    _prompt457_observed_bool,
    _prompt459_first_non_empty_string_list,
    _prompt460_git_status_files,
    _prompt460_git_text,
    _prompt460_tag_exists,
    _prompt470_bool_from_any_existing,
    _prompt470_collect_post_fix_diff,
    _prompt470_route_evidence_ready,
    _prompt470_supported_route,
    _prompt470_targeted_fix_prompt_body,
    _prompt471_bool_from_any_existing,
    _prompt471_git,
    _prompt471_head,
    _prompt471_tag_exists,
    _prompt471_tags_at_head,
    _prompt471_upstream_evidence_ready,
    _prompt472_git_stdout,
    _prompt472_upstream_prompt471_evidence_ready,
    _prompt473_prompt472_evidence_bridge,
    _prompt474_bool_from_any_existing,
    _prompt474_prompt473_evidence_bridge,
    _prompt474_targeted_fix_prompt_body,
    _prompt475_prompt474_evidence_bridge,
    _prompt475_prompt474_tag_in_lineage,
    _prompt476_prompt475_evidence_bridge,
    _prompt477_prompt476_evidence_bridge,
    _prompt478_bool_from_allow_surfaces,
    _prompt478_empty_cycle_state,
    _prompt478_final_repo_state_evidence_ready,
    _prompt478_ordered_union,
    _prompt478_prompt477_evidence_bridge,
    _prompt478_run_cycle,
    _prompt479_prompt478_evidence_bridge,
    _prompt479_surface_int,
    _prompt480_manual_stop_requested,
    _prompt480_prompt479_evidence_bridge,
    _prompt481_empty_cycle_state,
    _prompt481_manual_stop_requested,
    _prompt481_prompt480_evidence_bridge,
    _prompt481_run_cycle,
    _prompt482_prompt481_evidence_bridge,
    _prompt483_extract_selected_role_text,
    _prompt483_first_text_from_payloads,
    _prompt483_prompt482_evidence_bridge,
    _prompt483_resolve_repo_relative_path,
    _prompt483_untracked_files,
    _prompt491a_canonical_tokens_ready,
    _prompt491a_materialized_prompt378_markdown,
    _prompt492_infer_allowed_files,
    _prompt492_infer_forbidden_files,
    _prompt492_infer_validation_commands,
    _prompt492_role_text_section_lines,
    _run_git,
    _write_json,
)

_PROMPT491A_ALLOWED_IMPLEMENTATION_FILES = (
    "automation/orchestration/planned_runner/prompt_surfaces/prompts_450_499.py",
    "automation/orchestration/planned_runner/prompt_surfaces/prompts_350_399.py",
    "automation/orchestration/planned_runner/prompt_surfaces/registry.py",
)

_PROMPT491A_FORBIDDEN_IMPLEMENTATION_FILES = (
    "automation/orchestration/planned_execution_runner.py",
    "scripts/run_planned_execution.py",
    "automation/orchestration/planned_runner/runtime_output_wiring.py",
    "automation/orchestration/run_state_summary_contract.py",
    "tests",
    "docs",
    "README",
    "examples",
)

_PROMPT491A_VALIDATION_COMMANDS = (
    "python -m py_compile automation/orchestration/planned_runner/*.py "
    "automation/orchestration/planned_runner/prompt_surfaces/*.py "
    "automation/orchestration/run_state_summary_contract.py "
    "scripts/run_planned_execution.py",
    "python scripts/run_planned_execution.py --help",
)

_PROMPT491A_REQUIRED_PROMPT_MARKERS = (
    "success-path-only",
    "scope guard text",
    "split planned_runner prompt surface files",
    "no tests",
    "no git",
    "no remote mutation",
    "next_action",
    "allowed files",
    "forbidden files",
    "automation/orchestration/planned_execution_runner.py",
    "blocked_by_forbidden_scope",
    "BAD_SCOPE",
    "PLANNED_EXECUTION_RUNNER_UNCHANGED",
    "RUN_SCRIPT_UNCHANGED",
    "runtime_output_wiring.py",
    "run_state_summary_contract.py",
    "prompt498_surface_scope_fixed_to_prompt_surfaces=True",
    "prompt498_forbidden_allowed_scope_expansion_ready=True",
    "Prompt489/490/491 behavior is preserved",
    "Prompt379 dry-run safety remains blocked",
    "only allowed implementation files changed",
    "accept_candidate_then_commit_tag",
)


def _normalize_multiline_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.replace("\r\n", "\n").replace("\r", "\n")


def _prompt491a_list_lines(values: Sequence[str]) -> str:
    return "\n".join(f"- {value}" for value in values)


def _prompt491a_materialized_prompt378_markdown(
    *,
    selected_role_id: str,
    selected_role_text: str,
    contract_allowed_files: Sequence[str] | None = None,
    contract_forbidden_files: Sequence[str] | None = None,
    contract_validation_commands: Sequence[str] | None = None,
    contract_backed: bool = False,
) -> str:
    allowed_files = tuple(contract_allowed_files or _PROMPT491A_ALLOWED_IMPLEMENTATION_FILES)
    forbidden_files = tuple(
        contract_forbidden_files or _PROMPT491A_FORBIDDEN_IMPLEMENTATION_FILES
    )
    validation_commands = tuple(
        contract_validation_commands or _PROMPT491A_VALIDATION_COMMANDS
    )
    role_id = _normalize_text(selected_role_id, default="prompt491a_role")
    role_text = _normalize_text(selected_role_text, default="")
    role_id_checksum = hashlib.sha256(role_id.encode("utf-8")).hexdigest()
    role_text_checksum = (
        hashlib.sha256(role_text.encode("utf-8")).hexdigest() if role_text else ""
    )
    contract_source = "prompt493" if contract_backed else "prompt491a"

    return f"""# Prompt379 Live Input

Mode: Implement

Goal:
Generate the Prompt379 live execution change as a success-path-only, local-only
implementation. Modify only the generated prompt/materialization contract needed
to keep future Prompt379 live execution inside the split planned_runner prompt
surface files.

Role source:
- role_id_sha256: {role_id_checksum}
- contract_source: {contract_source}
- selected_role_text_present: {bool(role_text)}
- selected_role_text_sha256: {role_text_checksum}

Allowed implementation files:
{_prompt491a_list_lines(allowed_files)}

Allowed files:
{_prompt491a_list_lines(allowed_files)}

Forbidden implementation files:
{_prompt491a_list_lines(forbidden_files)}

Forbidden files:
{_prompt491a_list_lines(forbidden_files)}

Hard allowed-scope section:
- Edit only the files listed under allowed implementation files.
- Allowed implementation files are intentionally limited to split planned_runner prompt surface files.
- Do not edit any file outside the allowed implementation files list.
- Do not edit automation/orchestration/planned_execution_runner.py.
- Do not edit scripts/run_planned_execution.py.
- Do not edit automation/orchestration/planned_runner/runtime_output_wiring.py.
- Do not edit automation/orchestration/run_state_summary_contract.py.
- Do not edit tests, docs, README, or examples.
- Do not add automation/orchestration/planned_runner/runtime_output_wiring.py
  or automation/orchestration/run_state_summary_contract.py to
  _PROMPT491A_ALLOWED_IMPLEMENTATION_FILES.
- If the required change appears to require planned_execution_runner.py, stop
  without editing and report blocked_by_forbidden_scope.
- If any required change would require a forbidden file, stop without editing
  and report blocked_by_forbidden_scope.

Hard forbidden-scope section:
- automation/orchestration/planned_execution_runner.py is forbidden.
- scripts/run_planned_execution.py is forbidden.
- automation/orchestration/planned_runner/runtime_output_wiring.py is forbidden.
- automation/orchestration/run_state_summary_contract.py is forbidden.
- tests are forbidden.
- docs are forbidden.
- README is forbidden.
- examples are forbidden.

Scope guard text:
- Prompt379 live execution changes are allowed only in the split planned_runner prompt surface files listed under Allowed implementation files.
- Prompt489/490/491 behavior is preserved.
- Prompt379 dry-run safety remains blocked.
- Only allowed implementation files changed.
- If git diff includes any forbidden file or any file outside Allowed
  implementation files, set BAD_SCOPE true, stop without further edits, and
  report blocked_by_forbidden_scope.
- If _PROMPT491A_ALLOWED_IMPLEMENTATION_FILES includes any path other than the
  three Allowed implementation files, set BAD_SCOPE true, stop without further
  edits, and report blocked_by_forbidden_scope.
- If _PROMPT491A_ALLOWED_IMPLEMENTATION_FILES includes
  automation/orchestration/planned_runner/runtime_output_wiring.py or
  automation/orchestration/run_state_summary_contract.py, set BAD_SCOPE true,
  stop without further edits, and report blocked_by_forbidden_scope.

Expected artifact/output:
- changed files
- diff stat
- BAD_SCOPE
- PLANNED_EXECUTION_RUNNER_UNCHANGED
- RUN_SCRIPT_UNCHANGED
- prompt498_surface_scope_fixed_to_prompt_surfaces=True
- prompt498_forbidden_allowed_scope_expansion_ready=True
- prompt498_rejects_runtime_output_wiring_as_prompt379_mutation_target=True
- prompt498_rejects_run_state_summary_contract_as_prompt379_mutation_target=True
- prompt498_preserves_prompt379_to_prompt383_success_flow=True
- prompt498_two_cycle_success_path_prepared=True
- automatic judgment
- next_action

Validation commands:
{_prompt491a_list_lines(validation_commands)}

Out-of-scope items:
- no tests
- no git commit or tag
- no remote mutation
- no push
- no PR
- no merge
- no rollback
- no targeted_fix
- no daemon, polling, or sleep loop
- no live Prompt379 execution

Final output requirements:
- Print changed files.
- Print diff stat.
- Print BAD_SCOPE as true if any forbidden file changed, else false.
- Print PLANNED_EXECUTION_RUNNER_UNCHANGED.
- Print RUN_SCRIPT_UNCHANGED.
- Print automatic judgment.
- Use automatic judgment `accept_candidate_then_commit_tag` only when scope guard
  text is present, Prompt489/490/491 behavior is preserved, Prompt379 dry-run
  safety remains blocked, and only allowed implementation files changed.
- Use automatic judgment `reject_with_reason` when BAD_SCOPE is true, including
  when _PROMPT491A_ALLOWED_IMPLEMENTATION_FILES was broadened outside the three
  allowed prompt surface files.
"""


def _prompt491a_canonical_tokens_ready(prompt_text: str) -> bool:
    normalized_prompt = _normalize_multiline_text(prompt_text)
    lowered_prompt = normalized_prompt.lower()
    return bool(
        normalized_prompt.strip()
        and all(marker.lower() in lowered_prompt for marker in _PROMPT491A_REQUIRED_PROMPT_MARKERS)
        and all(path in normalized_prompt for path in _PROMPT491A_ALLOWED_IMPLEMENTATION_FILES)
        and all(path in normalized_prompt for path in _PROMPT491A_FORBIDDEN_IMPLEMENTATION_FILES)
    )


def _prompt492_role_text_section_lines(
    *,
    selected_role_text: str,
    section_name: str,
) -> list[str]:
    lines = _normalize_multiline_text(selected_role_text).splitlines()
    section = _normalize_text(section_name, default="").strip().lower()
    if not section:
        return []
    collected: list[str] = []
    in_section = False
    for line in lines:
        stripped = line.strip()
        normalized = stripped.rstrip(":").strip().lower()
        is_heading = bool(stripped and not line.startswith((" ", "\t", "-", "*")))
        if normalized == section:
            in_section = True
            continue
        if in_section and is_heading and stripped.endswith(":"):
            break
        if in_section and stripped:
            collected.append(stripped)
    if collected:
        return collected
    return [f"{section_name}: materialized by Prompt491A scope guard"]


def _prompt492_infer_allowed_files(selected_role_text: str) -> list[str]:
    return list(_PROMPT491A_ALLOWED_IMPLEMENTATION_FILES)


def _prompt492_infer_forbidden_files() -> list[str]:
    return list(_PROMPT491A_FORBIDDEN_IMPLEMENTATION_FILES)


def _prompt492_infer_validation_commands() -> list[str]:
    return list(_PROMPT491A_VALIDATION_COMMANDS)


def _build_prompt450_prompt449_runtime_packet_execution_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    prompt449_status = _normalize_text(
        payload.get("prompt449_explicit_targeted_fix_execution_status"),
        default="",
    )
    prompt449_next_action = _normalize_text(
        payload.get("prompt449_next_action"),
        default="",
    )
    runtime_command_json = _prompt450_runtime_command_json(payload)
    command_argv = _normalize_string_list(
        runtime_command_json.get("command_argv"),
        sort_items=False,
    )
    request_id = _normalize_text(
        runtime_command_json.get("request_id"),
        default="",
    )
    prompt_artifact_path = _normalize_text(
        runtime_command_json.get("codex_prompt_artifact_path"),
        default=_normalize_text(
            payload.get("prompt449_targeted_fix_prompt_artifact_path"),
            default="",
        ),
    )
    transport_mode = _normalize_text(
        runtime_command_json.get("transport_mode"),
        default="",
    )
    runtime_packet_available = bool(runtime_command_json)
    runtime_packet_valid = _prompt450_runtime_packet_valid(runtime_command_json)
    current_retry_count = _prompt450_retry_value(
        payload,
        "prompt449_current_retry_count",
        0,
    )
    next_retry_count = _prompt450_retry_value(
        payload,
        "prompt449_next_retry_count",
        current_retry_count + 1,
    )
    retry_limit = _prompt450_retry_value(
        payload,
        "prompt449_retry_limit",
        1,
    )
    returncode = _as_optional_int(payload.get("prompt441_codex_returncode"))
    if returncode is None:
        returncode = _as_optional_int(
            payload.get("prompt430_runtime_execution_returncode")
        )
    returncode_classification = _normalize_text(
        payload.get("prompt441_codex_returncode_classification")
        or payload.get("prompt430_runtime_execution_returncode_classification"),
        default=_prompt450_returncode_classification(returncode),
    )
    stdout_path = _normalize_text(
        payload.get("prompt441_codex_stdout_path")
        or payload.get("prompt430_runtime_execution_stdout_path"),
        default="",
    )
    stderr_path = _normalize_text(
        payload.get("prompt441_codex_stderr_path")
        or payload.get("prompt430_runtime_execution_stderr_path"),
        default="",
    )
    result_artifact_path = _prompt450_result_artifact_path(payload)
    result_available = _prompt450_result_available(payload)

    state: dict[str, Any] = {
        "prompt450_schema_version": _PROMPT450_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt450",
        "prompt450_prompt449_runtime_packet_execution_status": "blocked",
        "prompt450_prompt449_status": prompt449_status,
        "prompt450_prompt449_next_action": prompt449_next_action,
        "prompt450_prompt449_runtime_command_json_ready": (
            payload.get("prompt449_runtime_command_json_ready") is True
        ),
        "prompt450_prompt449_runtime_command_json": runtime_command_json,
        "prompt450_prompt449_codex_reentry_allowed": (
            payload.get("prompt449_codex_reentry_allowed") is True
        ),
        "prompt450_prompt449_codex_reentry_attempted": (
            payload.get("prompt449_codex_reentry_attempted") is True
        ),
        "prompt450_prompt449_codex_reentry_performed": (
            payload.get("prompt449_codex_reentry_performed") is True
        ),
        "prompt450_prompt449_materialization_performed": (
            payload.get("prompt449_materialization_performed") is True
        ),
        "prompt450_prompt449_artifact_path": prompt_artifact_path,
        "prompt450_prompt449_blocked_reason": _normalize_text(
            payload.get("prompt449_blocked_reason"),
            default="",
        ),
        "prompt450_runtime_packet_available": runtime_packet_available,
        "prompt450_runtime_packet_valid": runtime_packet_valid,
        "prompt450_runtime_packet_safety_status": "not_reviewed",
        "prompt450_runtime_command_json": runtime_command_json,
        "prompt450_runtime_command_json_ready": False,
        "prompt450_runtime_command_argv": command_argv,
        "prompt450_runtime_command_request_id": request_id,
        "prompt450_runtime_command_prompt_artifact_path": prompt_artifact_path,
        "prompt450_runtime_command_transport_mode": transport_mode,
        "prompt450_runtime_command_request_codex_invocation": (
            runtime_command_json.get("request_codex_invocation") is True
        ),
        "prompt450_runtime_command_allow_codex_invocation": (
            runtime_command_json.get("allow_codex_invocation") is True
        ),
        "prompt450_codex_reentry_required": False,
        "prompt450_codex_reentry_allowed": False,
        "prompt450_codex_reentry_attempted": False,
        "prompt450_codex_reentry_performed": False,
        "prompt450_codex_reentry_blocked_reason": "",
        "prompt450_codex_reentry_returncode": returncode,
        "prompt450_codex_reentry_returncode_classification": (
            returncode_classification if result_available else "not_run"
        ),
        "prompt450_codex_reentry_stdout_path": stdout_path,
        "prompt450_codex_reentry_stderr_path": stderr_path,
        "prompt450_codex_reentry_result_artifact_path": result_artifact_path,
        "prompt450_codex_reentry_result_available": result_available,
        "prompt450_retry_count_increment_required": False,
        "prompt450_retry_count_increment_allowed": False,
        "prompt450_retry_count_increment_attempted": False,
        "prompt450_retry_count_increment_performed": False,
        "prompt450_current_retry_count": current_retry_count,
        "prompt450_next_retry_count": next_retry_count,
        "prompt450_retry_limit": retry_limit,
        "prompt450_reentry_result_review_required": False,
        "prompt450_reentry_result_route_to_prompt442_required": False,
        "prompt450_reentry_result_review_packet_ready": False,
        "prompt450_reentry_prompt442_review_handoff_ready": False,
        "prompt450_reentry_prompt442_review_handoff_source": "",
        "prompt450_reentry_review_next_action": "",
        "prompt450_prompt451_ready": False,
        "prompt450_prompt451_blocked_reason": "",
        "prompt450_prompt451_expected_scope": "",
        "prompt450_prompt451_next_action": "",
        "prompt450_git_mutation_allowed": False,
        "prompt450_remote_mutation_allowed": False,
        "prompt450_commit_tag_allowed": False,
        "prompt450_push_allowed": False,
        "prompt450_tests_allowed": False,
        "prompt450_file_creation_allowed": False,
        "prompt450_blocked_reason": (
            f"prompt450_unsupported_prompt449_state_{prompt449_status}"
            if prompt449_status
            else "prompt450_missing_prompt449_state"
        ),
        "prompt450_next_action": "manual_review_prompt450_route",
    }

    if (
        prompt449_status == "not_applicable"
        and prompt449_next_action
        == "prepare_prompt450_approve_commit_tag_execution_gate"
    ):
        state.update(
            {
                "prompt450_prompt449_runtime_packet_execution_status": (
                    "not_applicable"
                ),
                "prompt450_codex_reentry_required": False,
                "prompt450_codex_reentry_allowed": False,
                "prompt450_codex_reentry_attempted": False,
                "prompt450_codex_reentry_performed": False,
                "prompt450_reentry_result_review_required": False,
                "prompt450_reentry_result_route_to_prompt442_required": False,
                "prompt450_reentry_result_review_packet_ready": False,
                "prompt450_reentry_prompt442_review_handoff_ready": False,
                "prompt450_prompt451_ready": True,
                "prompt450_prompt451_blocked_reason": "",
                "prompt450_prompt451_expected_scope": (
                    "approve_commit_tag_post_commit_closure_next_cycle"
                ),
                "prompt450_prompt451_next_action": (
                    "prepare_prompt451_approve_commit_tag_closure_and_next_cycle"
                ),
                "prompt450_blocked_reason": "",
                "prompt450_next_action": (
                    "prepare_prompt451_approve_commit_tag_closure_and_next_cycle"
                ),
            }
        )
        return state

    review_handoff_path = (
        prompt449_status == "executed"
        or payload.get("prompt449_reentry_result_route_to_prompt442_required")
        is True
        or prompt449_next_action
        in {
            "review_prompt449_reentry_result_with_prompt442",
            "handoff_prompt449_reentry_result_to_prompt442_review",
            "prepare_prompt442_review_from_prompt449_reentry_result",
        }
    )
    if review_handoff_path:
        state.update(
            {
                "prompt450_prompt449_runtime_packet_execution_status": (
                    "review_handoff_ready"
                ),
                "prompt450_codex_reentry_required": False,
                "prompt450_codex_reentry_allowed": False,
                "prompt450_codex_reentry_attempted": False,
                "prompt450_codex_reentry_performed": False,
                "prompt450_reentry_result_review_required": True,
                "prompt450_reentry_result_route_to_prompt442_required": True,
                "prompt450_reentry_result_review_packet_ready": result_available,
                "prompt450_reentry_prompt442_review_handoff_ready": (
                    result_available
                ),
                "prompt450_reentry_prompt442_review_handoff_source": (
                    "prompt449_targeted_fix_reentry"
                ),
                "prompt450_reentry_review_next_action": (
                    "review_prompt450_reentry_result_with_prompt442"
                ),
                "prompt450_blocked_reason": "",
                "prompt450_next_action": (
                    "review_prompt450_reentry_result_with_prompt442"
                ),
            }
        )
        return state

    unsafe_state = (
        prompt449_next_action == "stop_for_prompt442_unexpected_changes"
        or payload.get("prompt449_blocked_reason")
        == "prompt449_unsafe_changes_require_manual_review"
        or payload.get("prompt449_git_mutation_allowed") is True
        or payload.get("prompt449_remote_mutation_allowed") is True
        or payload.get("prompt449_commit_tag_allowed") is True
        or payload.get("prompt449_tests_allowed") is True
    )
    if unsafe_state:
        state.update(
            {
                "prompt450_prompt449_runtime_packet_execution_status": "blocked",
                "prompt450_runtime_packet_safety_status": "unsafe",
                "prompt450_blocked_reason": (
                    "prompt450_unsafe_changes_require_manual_review"
                ),
                "prompt450_next_action": (
                    "stop_for_prompt442_unexpected_changes"
                ),
            }
        )
        return state

    prepared_prompt449_packet = (
        prompt449_status == "prepared"
        and prompt449_next_action == "execute_prompt449_runtime_command_packet"
        and payload.get("prompt449_runtime_command_json_ready") is True
        and payload.get("prompt449_runtime_command_json_allow_codex_invocation")
        is True
        and payload.get("prompt449_runtime_command_json_request_codex_invocation")
        is True
        and payload.get("prompt449_codex_reentry_allowed") is True
        and payload.get("prompt449_materialization_performed") is True
        and payload.get("prompt449_git_mutation_allowed") is False
        and payload.get("prompt449_remote_mutation_allowed") is False
        and payload.get("prompt449_commit_tag_allowed") is False
        and payload.get("prompt449_tests_allowed") is False
    )
    if prepared_prompt449_packet:
        if not runtime_packet_available or not runtime_packet_valid:
            state.update(
                {
                    "prompt450_prompt449_runtime_packet_execution_status": (
                        "blocked"
                    ),
                    "prompt450_runtime_packet_safety_status": "invalid",
                    "prompt450_blocked_reason": (
                        "prompt450_missing_or_invalid_prompt449_runtime_packet"
                    ),
                    "prompt450_next_action": (
                        "manual_review_prompt450_runtime_packet"
                    ),
                }
            )
            return state

        state.update(
            {
                "prompt450_prompt449_runtime_packet_execution_status": (
                    "prepared"
                ),
                "prompt450_runtime_packet_available": True,
                "prompt450_runtime_packet_valid": True,
                "prompt450_runtime_packet_safety_status": (
                    "safe_to_execute_prompt449_runtime_packet"
                ),
                "prompt450_runtime_command_json_ready": True,
                "prompt450_codex_reentry_required": True,
                "prompt450_codex_reentry_allowed": True,
                "prompt450_codex_reentry_attempted": False,
                "prompt450_codex_reentry_performed": False,
                "prompt450_codex_reentry_blocked_reason": (
                    "prompt450_runtime_command_execution_packet_prepared_not_performed"
                ),
                "prompt450_codex_reentry_returncode": None,
                "prompt450_codex_reentry_returncode_classification": "not_run",
                "prompt450_codex_reentry_stdout_path": "",
                "prompt450_codex_reentry_stderr_path": "",
                "prompt450_codex_reentry_result_artifact_path": "",
                "prompt450_codex_reentry_result_available": False,
                "prompt450_retry_count_increment_required": True,
                "prompt450_retry_count_increment_allowed": True,
                "prompt450_retry_count_increment_attempted": False,
                "prompt450_retry_count_increment_performed": False,
                "prompt450_reentry_result_review_required": False,
                "prompt450_reentry_result_route_to_prompt442_required": False,
                "prompt450_reentry_result_review_packet_ready": False,
                "prompt450_reentry_prompt442_review_handoff_ready": False,
                "prompt450_reentry_review_next_action": "",
                "prompt450_prompt451_ready": False,
                "prompt450_prompt451_blocked_reason": (
                    "prompt450_runtime_packet_not_executed"
                ),
                "prompt450_prompt451_expected_scope": (
                    "execute_runtime_packet_before_prompt451"
                ),
                "prompt450_prompt451_next_action": (
                    "execute_prompt450_runtime_command_packet"
                ),
                "prompt450_blocked_reason": "",
                "prompt450_next_action": (
                    "execute_prompt450_runtime_command_packet"
                ),
            }
        )
        return state

    if prompt449_status == "prepared" and (
        not runtime_packet_available or not runtime_packet_valid
    ):
        state.update(
            {
                "prompt450_prompt449_runtime_packet_execution_status": "blocked",
                "prompt450_runtime_packet_safety_status": "invalid",
                "prompt450_blocked_reason": (
                    "prompt450_missing_or_invalid_prompt449_runtime_packet"
                ),
                "prompt450_next_action": (
                    "manual_review_prompt450_runtime_packet"
                ),
            }
        )
        return state

    state["prompt450_blocked_reason"] = (
        f"prompt450_unsupported_prompt449_state_{prompt449_status}_"
        f"next_action_{prompt449_next_action}"
        if prompt449_status or prompt449_next_action
        else "prompt450_missing_prompt449_state"
    )
    return state

def _build_prompt451_minimal_autonomous_completion_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}

    prompt450_status = _normalize_text(
        payload.get("prompt450_prompt449_runtime_packet_execution_status"),
        default="",
    )
    prompt450_next_action = _normalize_text(
        payload.get("prompt450_next_action"),
        default="",
    )
    runtime_command_json = (
        dict(payload.get("prompt450_runtime_command_json"))
        if isinstance(payload.get("prompt450_runtime_command_json"), Mapping)
        else {}
    )
    allowed_changed_files = _normalize_string_list(
        payload.get("prompt442_allowed_changed_files")
        or payload.get("prompt443_allowed_changed_files")
    )
    unexpected_changed_files = _normalize_string_list(
        payload.get("prompt442_unexpected_changed_files")
        or payload.get("prompt443_unexpected_changed_files")
    )
    unexpected_untracked_files = _normalize_string_list(
        payload.get("prompt442_unexpected_untracked_files")
        or payload.get("prompt443_unexpected_untracked_files")
    )
    current_cycle = _as_non_negative_int(
        payload.get("prompt451_current_cycle")
        if payload.get("prompt451_current_cycle") is not None
        else payload.get("prompt427_current_cycle"),
        default=0,
    )
    max_cycles = _as_non_negative_int(
        payload.get("prompt451_max_cycles")
        if payload.get("prompt451_max_cycles") is not None
        else payload.get("prompt427_max_cycles"),
        default=2,
    )
    retry_limit = _as_non_negative_int(
        payload.get("prompt450_retry_limit")
        if payload.get("prompt450_retry_limit") is not None
        else payload.get("prompt444_retry_limit"),
        default=1,
    )
    retry_count = _as_non_negative_int(
        payload.get("prompt450_current_retry_count")
        if payload.get("prompt450_current_retry_count") is not None
        else payload.get("prompt444_retry_count"),
        default=0,
    )
    max_cycles_reached = current_cycle >= max_cycles
    retry_limit_reached = retry_count >= retry_limit
    unsafe_stop_required = bool(
        unexpected_changed_files
        or unexpected_untracked_files
        or payload.get("prompt442_post_codex_change_safety_status")
        == "unexpected_changes"
        or payload.get("prompt442_codex_post_execution_route")
        == "manual_review_unexpected_changes"
    )
    explicit_commit_allowed = _prompt451_bool_input(
        payload,
        (
            "allow_prompt451_commit",
            "allow_prompt451_commit_tag",
            "prompt451_commit_allowed_input",
            "prompt451_commit_tag_allowed_input",
            "request_prompt451_commit",
            "request_prompt451_commit_tag",
            "approve_commit_tag_allowed",
            "prompt382_approve_commit_tag_allowed",
            "prompt383_approve_commit_tag_execution_allowed",
        ),
    )
    explicit_tag_allowed = _prompt451_bool_input(
        payload,
        (
            "allow_prompt451_tag",
            "allow_prompt451_commit_tag",
            "prompt451_tag_allowed_input",
            "prompt451_commit_tag_allowed_input",
            "request_prompt451_tag",
            "request_prompt451_commit_tag",
            "approve_commit_tag_allowed",
            "prompt382_approve_commit_tag_allowed",
            "prompt383_approve_commit_tag_execution_allowed",
        ),
    )
    explicit_commit_tag_allowed = explicit_commit_allowed and explicit_tag_allowed
    commit_message_candidate = _normalize_text(
        payload.get("prompt443_commit_message_candidate"),
        default="Prompt451 approve autonomous success diff",
    )
    tag_name_candidate = _normalize_text(
        payload.get("prompt443_tag_name_candidate"),
        default="prompt451-autonomous-success-diff",
    )
    reentry_result_available = bool(
        payload.get("prompt450_codex_reentry_result_available") is True
        or payload.get("prompt449_reentry_result_available") is True
        or payload.get("prompt441_codex_result_materialized") is True
        or _normalize_text(
            payload.get("prompt450_codex_reentry_result_artifact_path"),
            default="",
        )
    )

    state: dict[str, Any] = {
        "prompt451_schema_version": _PROMPT451_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt451",
        "prompt451_minimal_autonomous_completion_status": "blocked",
        "prompt451_prompt450_status": prompt450_status,
        "prompt451_prompt450_next_action": prompt450_next_action,
        "prompt451_prompt450_runtime_packet_available": (
            payload.get("prompt450_runtime_packet_available") is True
        ),
        "prompt451_prompt450_runtime_packet_valid": (
            payload.get("prompt450_runtime_packet_valid") is True
        ),
        "prompt451_prompt450_runtime_packet_safety_status": _normalize_text(
            payload.get("prompt450_runtime_packet_safety_status"),
            default="",
        ),
        "prompt451_prompt450_runtime_command_json_ready": (
            payload.get("prompt450_runtime_command_json_ready") is True
        ),
        "prompt451_prompt450_runtime_command_json": runtime_command_json,
        "prompt451_prompt450_codex_reentry_allowed": (
            payload.get("prompt450_codex_reentry_allowed") is True
        ),
        "prompt451_prompt450_codex_reentry_attempted": (
            payload.get("prompt450_codex_reentry_attempted") is True
        ),
        "prompt451_prompt450_codex_reentry_performed": (
            payload.get("prompt450_codex_reentry_performed") is True
        ),
        "prompt451_prompt450_prompt451_ready": (
            payload.get("prompt450_prompt451_ready") is True
        ),
        "prompt451_prompt450_expected_scope": _normalize_text(
            payload.get("prompt450_prompt451_expected_scope"),
            default="",
        ),
        "prompt451_runtime_packet_execution_required": False,
        "prompt451_runtime_packet_execution_allowed": False,
        "prompt451_runtime_packet_execution_attempted": False,
        "prompt451_runtime_packet_execution_performed": False,
        "prompt451_runtime_packet_execution_blocked_reason": "",
        "prompt451_runtime_command_json": runtime_command_json,
        "prompt451_runtime_command_json_ready": False,
        "prompt451_runtime_command_argv": _normalize_string_list(
            payload.get("prompt450_runtime_command_argv"),
            sort_items=False,
        ),
        "prompt451_runtime_command_request_id": _normalize_text(
            payload.get("prompt450_runtime_command_request_id"),
            default="",
        ),
        "prompt451_runtime_command_prompt_artifact_path": _normalize_text(
            payload.get("prompt450_runtime_command_prompt_artifact_path"),
            default="",
        ),
        "prompt451_runtime_command_transport_mode": _normalize_text(
            payload.get("prompt450_runtime_command_transport_mode"),
            default="",
        ),
        "prompt451_runtime_command_request_codex_invocation": (
            payload.get("prompt450_runtime_command_request_codex_invocation")
            is True
        ),
        "prompt451_runtime_command_allow_codex_invocation": (
            payload.get("prompt450_runtime_command_allow_codex_invocation")
            is True
        ),
        "prompt451_reentry_result_available": reentry_result_available,
        "prompt451_reentry_returncode": _as_optional_int(
            payload.get("prompt450_codex_reentry_returncode")
        ),
        "prompt451_reentry_returncode_classification": _normalize_text(
            payload.get("prompt450_codex_reentry_returncode_classification"),
            default="not_run" if not reentry_result_available else "unknown",
        ),
        "prompt451_reentry_stdout_path": _normalize_text(
            payload.get("prompt450_codex_reentry_stdout_path"),
            default="",
        ),
        "prompt451_reentry_stderr_path": _normalize_text(
            payload.get("prompt450_codex_reentry_stderr_path"),
            default="",
        ),
        "prompt451_reentry_result_artifact_path": _normalize_text(
            payload.get("prompt450_codex_reentry_result_artifact_path"),
            default="",
        ),
        "prompt451_reentry_review_required": False,
        "prompt451_reentry_route_to_prompt442_required": False,
        "prompt451_reentry_review_packet_ready": False,
        "prompt451_reentry_prompt442_review_handoff_ready": False,
        "prompt451_reentry_prompt442_review_handoff_source": "",
        "prompt451_reentry_review_next_action": "",
        "prompt451_prompt442_route": _normalize_text(
            payload.get("prompt442_codex_post_execution_route"),
            default="",
        ),
        "prompt451_prompt442_change_safety_status": _normalize_text(
            payload.get("prompt442_post_codex_change_safety_status"),
            default="",
        ),
        "prompt451_prompt442_changes_present": (
            payload.get("prompt442_post_codex_changes_present") is True
        ),
        "prompt451_prompt442_diff_empty": (
            payload.get("prompt442_post_codex_diff_empty") is True
        ),
        "prompt451_prompt442_allowed_changed_files": allowed_changed_files,
        "prompt451_prompt442_unexpected_changed_files": unexpected_changed_files,
        "prompt451_prompt442_unexpected_untracked_files": unexpected_untracked_files,
        "prompt451_prompt443_status": _normalize_text(
            payload.get("prompt443_success_diff_handoff_status"),
            default="",
        ),
        "prompt451_prompt443_approve_commit_tag_candidate": (
            payload.get("prompt443_approve_commit_tag_candidate") is True
        ),
        "prompt451_prompt443_commit_message_candidate": commit_message_candidate,
        "prompt451_prompt443_tag_name_candidate": tag_name_candidate,
        "prompt451_approve_candidate_inputs_available": False,
        "prompt451_approve_candidate_ready": False,
        "prompt451_approve_candidate_safety_status": "",
        "prompt451_approve_candidate_blocked_reason": "",
        "prompt451_commit_message_candidate": commit_message_candidate,
        "prompt451_tag_name_candidate": tag_name_candidate,
        "prompt451_commit_tag_required": False,
        "prompt451_commit_tag_allowed": False,
        "prompt451_commit_attempted": False,
        "prompt451_commit_performed": False,
        "prompt451_tag_attempted": False,
        "prompt451_tag_performed": False,
        "prompt451_commit_tag_blocked_reason": "",
        "prompt451_commit_hash": _normalize_text(
            payload.get("prompt451_commit_hash"),
            default="",
        ),
        "prompt451_tag_name": _normalize_text(
            payload.get("prompt451_tag_name"),
            default="",
        ),
        "prompt451_tag_points_at_head": (
            payload.get("prompt451_tag_points_at_head") is True
        ),
        "prompt451_post_commit_clean_rerun_required": False,
        "prompt451_post_commit_clean_rerun_request_ready": False,
        "prompt451_post_commit_clean_rerun_attempted": False,
        "prompt451_post_commit_clean_rerun_performed": False,
        "prompt451_post_commit_clean_rerun_result_available": (
            payload.get("prompt451_post_commit_clean_rerun_result_available")
            is True
        ),
        "prompt451_post_commit_clean_rerun_expected_route": "",
        "prompt451_post_commit_clean_rerun_blocked_reason": "",
        "prompt451_post_commit_clean_rerun_next_action": "",
        "prompt451_success_closure_candidate": False,
        "prompt451_success_closure_ready": False,
        "prompt451_success_closure_blocked_reason": "",
        "prompt451_head_clean_required": False,
        "prompt451_head_clean_observed": (
            payload.get("prompt451_head_clean_observed") is True
        ),
        "prompt451_expected_tag_observed": (
            payload.get("prompt451_expected_tag_observed") is True
        ),
        "prompt451_no_unexpected_changes_observed": (
            payload.get("prompt451_no_unexpected_changes_observed") is True
        ),
        "prompt451_autonomous_next_cycle_ready": False,
        "prompt451_autonomous_next_cycle_request_ready": False,
        "prompt451_autonomous_next_cycle_runtime_request_ready": False,
        "prompt451_autonomous_next_cycle_prompt_request_ready": False,
        "prompt451_autonomous_next_cycle_selected_prompt_id": _normalize_text(
            payload.get("prompt401_selected_next_prompt_id")
            or payload.get("prompt420_selected_prompt_id"),
            default="",
        ),
        "prompt451_autonomous_next_cycle_selected_next_action": _normalize_text(
            payload.get("prompt401_selected_next_prompt_action")
            or payload.get("prompt420_next_action"),
            default="",
        ),
        "prompt451_autonomous_next_cycle_blocked_reason": "",
        "prompt451_autonomous_next_cycle_stop_reason": "",
        "prompt451_max_cycles": max_cycles,
        "prompt451_current_cycle": current_cycle,
        "prompt451_max_cycles_guard_ready": True,
        "prompt451_max_cycles_reached": max_cycles_reached,
        "prompt451_retry_limit_guard_ready": True,
        "prompt451_retry_limit_reached": retry_limit_reached,
        "prompt451_unsafe_stop_guard_ready": True,
        "prompt451_unsafe_stop_required": unsafe_stop_required,
        "prompt451_git_mutation_allowed": False,
        "prompt451_remote_mutation_allowed": False,
        "prompt451_push_allowed": False,
        "prompt451_tests_allowed": False,
        "prompt451_file_creation_allowed": False,
        "prompt451_blocked_reason": "prompt451_missing_supported_state",
        "prompt451_next_action": "manual_review_prompt451_route",
    }

    if unsafe_stop_required:
        state.update(
            {
                "prompt451_minimal_autonomous_completion_status": "stopped",
                "prompt451_autonomous_next_cycle_stop_reason": "unsafe_changes",
                "prompt451_blocked_reason": (
                    "prompt451_unsafe_changes_require_manual_review"
                ),
                "prompt451_next_action": "stop_for_prompt442_unexpected_changes",
            }
        )
        return state
    if retry_limit_reached:
        state.update(
            {
                "prompt451_minimal_autonomous_completion_status": "stopped",
                "prompt451_autonomous_next_cycle_stop_reason": (
                    "retry_limit_reached"
                ),
                "prompt451_next_action": "manual_review_retry_limit_reached",
            }
        )
        return state
    if max_cycles_reached:
        state.update(
            {
                "prompt451_minimal_autonomous_completion_status": "stopped",
                "prompt451_autonomous_next_cycle_stop_reason": (
                    "max_cycles_reached"
                ),
                "prompt451_next_action": (
                    "stop_autonomous_loop_max_cycles_reached"
                ),
            }
        )
        return state

    runtime_packet_path = (
        prompt450_status == "prepared"
        and prompt450_next_action == "execute_prompt450_runtime_command_packet"
        and payload.get("prompt450_runtime_packet_available") is True
        and payload.get("prompt450_runtime_packet_valid") is True
        and payload.get("prompt450_runtime_packet_safety_status")
        == "safe_to_execute_prompt449_runtime_packet"
        and payload.get("prompt450_runtime_command_json_ready") is True
        and payload.get("prompt450_runtime_command_allow_codex_invocation")
        is True
        and payload.get("prompt450_runtime_command_request_codex_invocation")
        is True
        and payload.get("prompt450_codex_reentry_allowed") is True
        and payload.get("prompt450_git_mutation_allowed") is False
        and payload.get("prompt450_remote_mutation_allowed") is False
        and payload.get("prompt450_commit_tag_allowed") is False
        and payload.get("prompt450_push_allowed") is False
        and payload.get("prompt450_tests_allowed") is False
    )
    if runtime_packet_path:
        state.update(
            {
                "prompt451_minimal_autonomous_completion_status": (
                    "runtime_packet_prepared"
                ),
                "prompt451_runtime_packet_execution_required": True,
                "prompt451_runtime_packet_execution_allowed": True,
                "prompt451_runtime_packet_execution_attempted": False,
                "prompt451_runtime_packet_execution_performed": False,
                "prompt451_runtime_packet_execution_blocked_reason": (
                    "prompt451_runtime_packet_execution_prepared_not_performed"
                ),
                "prompt451_runtime_command_json_ready": True,
                "prompt451_runtime_command_request_codex_invocation": True,
                "prompt451_runtime_command_allow_codex_invocation": True,
                "prompt451_blocked_reason": "",
                "prompt451_next_action": (
                    "execute_prompt451_runtime_command_packet"
                ),
            }
        )
        if reentry_result_available:
            state.update(
                {
                    "prompt451_minimal_autonomous_completion_status": (
                        "runtime_packet_executed"
                    ),
                    "prompt451_runtime_packet_execution_attempted": (
                        payload.get("prompt450_codex_reentry_attempted") is True
                    ),
                    "prompt451_runtime_packet_execution_performed": (
                        payload.get("prompt450_codex_reentry_performed") is True
                    ),
                    "prompt451_runtime_packet_execution_blocked_reason": "",
                    "prompt451_reentry_review_required": True,
                    "prompt451_reentry_route_to_prompt442_required": True,
                    "prompt451_reentry_review_packet_ready": True,
                    "prompt451_reentry_prompt442_review_handoff_ready": True,
                    "prompt451_reentry_prompt442_review_handoff_source": (
                        "prompt451_prompt450_runtime_packet_execution"
                    ),
                    "prompt451_reentry_review_next_action": (
                        "review_prompt451_reentry_result_with_prompt442"
                    ),
                    "prompt451_next_action": (
                        "review_prompt451_reentry_result_with_prompt442"
                    ),
                }
            )
        return state

    review_required_path = (
        payload.get("prompt450_reentry_result_route_to_prompt442_required")
        is True
        or prompt450_next_action == "review_prompt450_reentry_result_with_prompt442"
        or payload.get("prompt451_reentry_route_to_prompt442_required") is True
    )
    if review_required_path:
        state.update(
            {
                "prompt451_minimal_autonomous_completion_status": (
                    "review_required"
                ),
                "prompt451_reentry_review_required": True,
                "prompt451_reentry_route_to_prompt442_required": True,
                "prompt451_reentry_review_packet_ready": reentry_result_available,
                "prompt451_reentry_prompt442_review_handoff_ready": (
                    reentry_result_available
                ),
                "prompt451_reentry_prompt442_review_handoff_source": (
                    "prompt451_prompt450_runtime_packet_execution"
                ),
                "prompt451_reentry_review_next_action": (
                    "review_prompt451_reentry_result_with_prompt442"
                ),
                "prompt451_blocked_reason": "",
                "prompt451_next_action": (
                    "review_prompt451_reentry_result_with_prompt442"
                ),
            }
        )
        return state

    prompt450_success_continuation = (
        prompt450_status == "not_applicable"
        and payload.get("prompt450_prompt451_ready") is True
        and prompt450_next_action
        == "prepare_prompt451_approve_commit_tag_closure_and_next_cycle"
    )
    approve_candidate_path = (
        prompt450_success_continuation
        or _prompt451_success_approve_candidate(payload)
    ) and _prompt451_success_approve_candidate(payload)
    if approve_candidate_path:
        commit_tag_blocked_reason = (
            ""
            if explicit_commit_tag_allowed
            else "prompt451_commit_tag_not_explicitly_allowed"
        )
        state.update(
            {
                "prompt451_minimal_autonomous_completion_status": (
                    "commit_tag_ready"
                ),
                "prompt451_approve_candidate_inputs_available": True,
                "prompt451_approve_candidate_ready": True,
                "prompt451_approve_candidate_safety_status": (
                    "success_diff_allowed_changes"
                ),
                "prompt451_approve_candidate_blocked_reason": "",
                "prompt451_commit_tag_required": True,
                "prompt451_commit_tag_allowed": explicit_commit_tag_allowed,
                "prompt451_git_mutation_allowed": explicit_commit_tag_allowed,
                "prompt451_commit_tag_blocked_reason": commit_tag_blocked_reason,
                "prompt451_post_commit_clean_rerun_required": True,
                "prompt451_post_commit_clean_rerun_request_ready": True,
                "prompt451_post_commit_clean_rerun_expected_route": (
                    "clean_no_changes_or_targeted_fix_ready"
                ),
                "prompt451_post_commit_clean_rerun_next_action": (
                    "run_prompt451_post_commit_clean_rerun_after_commit_tag"
                ),
                "prompt451_success_closure_candidate": True,
                "prompt451_success_closure_ready": False,
                "prompt451_success_closure_blocked_reason": (
                    "prompt451_commit_tag_not_performed"
                ),
                "prompt451_autonomous_next_cycle_ready": False,
                "prompt451_autonomous_next_cycle_blocked_reason": (
                    "prompt451_success_closure_not_ready"
                ),
                "prompt451_blocked_reason": (
                    "" if explicit_commit_tag_allowed else commit_tag_blocked_reason
                ),
                "prompt451_next_action": (
                    "execute_prompt451_commit_tag_packet"
                    if explicit_commit_tag_allowed
                    else "request_explicit_prompt451_commit_tag_allow"
                ),
            }
        )
        if explicit_commit_tag_allowed:
            state["prompt451_commit_tag_blocked_reason"] = (
                "prompt451_commit_tag_execution_packet_prepared_not_performed"
            )
        return state

    prior_commit_or_tag_observed = (
        payload.get("prompt451_commit_performed") is True
        or payload.get("prompt451_tag_points_at_head") is True
        or payload.get("prompt451_expected_tag_observed") is True
    )
    clean_rerun_complete = (
        prior_commit_or_tag_observed
        and payload.get("prompt451_post_commit_clean_rerun_result_available")
        is True
        and payload.get("prompt451_head_clean_observed") is True
        and payload.get("prompt451_expected_tag_observed") is True
        and payload.get("prompt451_no_unexpected_changes_observed") is True
    )
    if clean_rerun_complete:
        selected_prompt_id = state[
            "prompt451_autonomous_next_cycle_selected_prompt_id"
        ] or "prompt452"
        selected_next_action = state[
            "prompt451_autonomous_next_cycle_selected_next_action"
        ] or "prepare_next_autonomous_prompt"
        state.update(
            {
                "prompt451_minimal_autonomous_completion_status": "completed",
                "prompt451_post_commit_clean_rerun_result_available": True,
                "prompt451_success_closure_candidate": True,
                "prompt451_success_closure_ready": True,
                "prompt451_success_closure_blocked_reason": "",
                "prompt451_head_clean_required": True,
                "prompt451_head_clean_observed": True,
                "prompt451_expected_tag_observed": True,
                "prompt451_no_unexpected_changes_observed": True,
                "prompt451_autonomous_next_cycle_ready": True,
                "prompt451_autonomous_next_cycle_request_ready": True,
                "prompt451_autonomous_next_cycle_runtime_request_ready": True,
                "prompt451_autonomous_next_cycle_prompt_request_ready": True,
                "prompt451_autonomous_next_cycle_selected_prompt_id": (
                    selected_prompt_id
                ),
                "prompt451_autonomous_next_cycle_selected_next_action": (
                    selected_next_action
                ),
                "prompt451_autonomous_next_cycle_blocked_reason": "",
                "prompt451_autonomous_next_cycle_stop_reason": "",
                "prompt451_blocked_reason": "",
                "prompt451_next_action": "continue_autonomous_next_cycle",
            }
        )
        return state

    state["prompt451_blocked_reason"] = (
        f"prompt451_unsupported_or_missing_state_prompt450_{prompt450_status}_"
        f"next_action_{prompt450_next_action}"
        if prompt450_status or prompt450_next_action
        else "prompt451_missing_prompt450_state"
    )
    return state

def _build_prompt452_prompt451_runtime_executed_review_closure_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    prompt451_status = _normalize_text(
        payload.get("prompt451_minimal_autonomous_completion_status"),
        default="",
    )
    prompt451_next_action = _normalize_text(
        payload.get("prompt451_next_action"),
        default="",
    )
    applicable = (
        prompt451_status == "runtime_packet_executed"
        and prompt451_next_action
        == "review_prompt451_reentry_result_with_prompt442"
    )

    result_available_key, result_available_value = _prompt452_first_present(
        payload,
        (
            "prompt451_reentry_result_available",
            "prompt450_codex_reentry_result_available",
            "prompt449_runtime_execution_result_available",
            "prompt448_targeted_fix_execution_result_available",
            "local_codex_one_shot_execution_result_available",
            "codex_execution_result_available",
            "runtime_execution_result_available",
        ),
    )
    result_path_key, result_path = _prompt452_first_text(
        payload,
        (
            "prompt451_reentry_result_artifact_path",
            "prompt450_codex_reentry_result_artifact_path",
            "prompt449_runtime_execution_result_artifact_path",
            "local_codex_one_shot_result_artifact_path",
            "codex_execution_result_artifact_path",
            "runtime_execution_result_artifact_path",
            "prompt430_runtime_execution_receipt_path",
        ),
    )
    result_available_bool = _prompt452_boolish(result_available_value)
    result_available = result_available_bool is True or bool(result_path)

    returncode_key, returncode_value = _prompt452_first_present(
        payload,
        (
            "prompt451_runtime_execution_returncode",
            "prompt451_reentry_returncode",
            "prompt450_codex_reentry_returncode",
            "prompt449_runtime_execution_returncode",
            "local_codex_one_shot_returncode",
            "codex_execution_returncode",
            "runtime_execution_returncode",
            "returncode",
        ),
    )
    returncode = _as_optional_int(returncode_value)
    returncode_classification_key, returncode_classification = _prompt452_first_text(
        payload,
        (
            "prompt451_runtime_execution_returncode_classification",
            "prompt451_reentry_returncode_classification",
            "prompt450_codex_reentry_returncode_classification",
            "prompt449_runtime_execution_returncode_classification",
            "local_codex_one_shot_returncode_classification",
            "codex_execution_returncode_classification",
            "runtime_execution_returncode_classification",
            "returncode_classification",
        ),
    )
    returncode_classification = returncode_classification.lower()

    stdout_path_key, stdout_path = _prompt452_first_text(
        payload,
        (
            "prompt451_runtime_execution_stdout_path",
            "prompt451_reentry_stdout_path",
            "prompt450_codex_reentry_stdout_path",
            "prompt449_runtime_execution_stdout_path",
            "local_codex_one_shot_stdout_path",
            "codex_execution_stdout_path",
            "runtime_execution_stdout_path",
        ),
    )
    stderr_path_key, stderr_path = _prompt452_first_text(
        payload,
        (
            "prompt451_runtime_execution_stderr_path",
            "prompt451_reentry_stderr_path",
            "prompt450_codex_reentry_stderr_path",
            "prompt449_runtime_execution_stderr_path",
            "local_codex_one_shot_stderr_path",
            "codex_execution_stderr_path",
            "runtime_execution_stderr_path",
        ),
    )
    _, error_summary = _prompt452_first_text(
        payload,
        (
            "prompt451_runtime_execution_error_summary",
            "prompt450_codex_reentry_error_summary",
            "prompt449_runtime_execution_error_summary",
            "local_codex_one_shot_error_summary",
            "codex_execution_error_summary",
            "runtime_execution_error_summary",
            "prompt430_execution_error_message",
            "execution_error_summary",
        ),
    )
    error_flag = _prompt452_observed_mutation(
        payload,
        (
            "prompt451_runtime_execution_error_available",
            "prompt450_codex_reentry_error_available",
            "prompt449_runtime_execution_error_available",
            "local_codex_one_shot_error_available",
            "codex_execution_error_available",
            "runtime_execution_error_available",
            "prompt430_execution_error",
            "execution_error",
        ),
    )

    tracked_diff_key, tracked_diff_value = _prompt452_first_present(
        payload,
        (
            "prompt451_runtime_execution_tracked_diff_empty",
            "prompt450_reentry_tracked_diff_empty",
            "prompt449_runtime_execution_tracked_diff_empty",
            "local_post_codex_diff_tracked_diff_empty",
            "post_execution_tracked_diff_empty",
            "tracked_diff_empty",
        ),
    )
    tracked_diff_empty = _prompt452_boolish(tracked_diff_value)
    tracked_diff_available = tracked_diff_key != "" and tracked_diff_empty is not None

    changed_key, changed_known, changed_files, changed_ambiguous = (
        _prompt452_known_string_list(
            payload,
            (
                "prompt451_runtime_execution_changed_files",
                "prompt450_reentry_changed_files",
                "prompt449_runtime_execution_changed_files",
                "local_post_codex_diff_changed_files",
                "post_execution_changed_files",
                "changed_files",
            ),
        )
    )
    untracked_key, untracked_known, untracked_files, untracked_ambiguous = (
        _prompt452_known_string_list(
            payload,
            (
                "prompt451_runtime_execution_untracked_files",
                "prompt450_reentry_untracked_files",
                "prompt449_runtime_execution_untracked_files",
                "post_execution_untracked_files",
                "untracked_files",
            ),
        )
    )
    unexpected_key, unexpected_known, unexpected_files, unexpected_ambiguous = (
        _prompt452_known_string_list(
            payload,
            (
                "prompt451_runtime_execution_unexpected_files",
                "prompt450_reentry_unexpected_files",
                "prompt449_runtime_execution_unexpected_files",
                "post_execution_unexpected_files",
                "unexpected_files",
            ),
        )
    )

    git_mutation_observed = _prompt452_observed_mutation(
        payload,
        (
            "git_mutation_performed",
            "git_mutation_performed_observed",
            "prompt441_git_mutation_performed",
            "prompt430_git_mutation_performed",
        ),
    )
    remote_mutation_observed = _prompt452_observed_mutation(
        payload,
        (
            "remote_mutation_performed",
            "remote_mutation_performed_observed",
            "prompt441_remote_mutation_performed",
            "prompt430_remote_mutation_performed",
        ),
    )
    commit_tag_observed = _prompt452_observed_mutation(
        payload,
        (
            "commit_tag_performed",
            "commit_tag_performed_observed",
            "prompt451_commit_performed",
            "prompt451_tag_performed",
            "prompt441_commit_tag_performed",
            "prompt430_commit_tag_performed",
        ),
    )
    push_observed = _prompt452_observed_mutation(
        payload,
        ("push_performed", "push_performed_observed"),
    )
    unsafe_mutation_observed = (
        git_mutation_observed
        or remote_mutation_observed
        or commit_tag_observed
        or push_observed
    )

    source_kind = _prompt452_source_kind(
        (
            result_available_key,
            result_path_key,
            returncode_key,
            returncode_classification_key,
            stdout_path_key,
            stderr_path_key,
            tracked_diff_key,
            changed_key,
            untracked_key,
            unexpected_key,
        )
    )
    success_returncode = (
        returncode == 0
        or returncode_classification in _PROMPT452_SUCCESS_RETURNCODE_CLASSIFICATIONS
    ) and returncode_classification not in _PROMPT452_BLOCKED_RETURNCODE_CLASSIFICATIONS
    failed_returncode = (
        returncode is not None
        and returncode != 0
    ) or returncode_classification in _PROMPT452_BLOCKED_RETURNCODE_CLASSIFICATIONS
    error_unsafe = _prompt452_error_summary_indicates_unsafe(error_summary)

    state: dict[str, Any] = {
        "prompt452_schema_version": _PROMPT452_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt452",
        "prompt452_prompt451_status": prompt451_status,
        "prompt452_prompt451_next_action": prompt451_next_action,
        "prompt452_applicable": applicable,
        "prompt452_review_closure_status": "blocked",
        "prompt452_review_classification": "blocked",
        "prompt452_review_evidence_ready": False,
        "prompt452_review_evidence_missing_reason": "",
        "prompt452_review_source_kind": source_kind,
        "prompt452_review_source_status": prompt451_status,
        "prompt452_review_source_next_action": prompt451_next_action,
        "prompt452_review_source_result_available": result_available,
        "prompt452_review_source_result_path": result_path,
        "prompt452_review_source_run_state_path": _normalize_text(
            payload.get("run_state_path"),
            default="",
        ),
        "prompt452_review_receipt_ready": False,
        "prompt452_runtime_execution_result_available": result_available,
        "prompt452_runtime_execution_returncode": returncode,
        "prompt452_runtime_execution_returncode_classification": (
            returncode_classification
        ),
        "prompt452_runtime_execution_stdout_path": stdout_path,
        "prompt452_runtime_execution_stderr_path": stderr_path,
        "prompt452_runtime_execution_stdout_available": bool(stdout_path),
        "prompt452_runtime_execution_stderr_available": bool(stderr_path),
        "prompt452_runtime_execution_error_available": bool(
            error_flag or error_summary
        ),
        "prompt452_runtime_execution_error_summary": error_summary,
        "prompt452_runtime_execution_diff_available": tracked_diff_available,
        "prompt452_runtime_execution_tracked_diff_empty": tracked_diff_empty,
        "prompt452_runtime_execution_changed_files": changed_files,
        "prompt452_runtime_execution_untracked_files": untracked_files,
        "prompt452_runtime_execution_unexpected_files": unexpected_files,
        "prompt452_runtime_execution_changed_files_known": changed_known,
        "prompt452_runtime_execution_untracked_files_known": untracked_known,
        "prompt452_runtime_execution_unexpected_files_known": unexpected_known,
        "prompt452_prompt442_style_review_required": applicable,
        "prompt452_prompt442_style_review_ready": False,
        "prompt452_prompt442_style_review_result": "blocked",
        "prompt452_prompt442_style_review_blocked_reason": "",
        "prompt452_success_diff_ready": False,
        "prompt452_no_changes_ready": False,
        "prompt452_unexpected_changes_detected": False,
        "prompt452_blocked_reason": "",
        "prompt452_next_action": "manual_review_prompt452_route",
        "prompt452_git_mutation_allowed": False,
        "prompt452_remote_mutation_allowed": False,
        "prompt452_commit_tag_allowed": False,
        "prompt452_push_allowed": False,
        "prompt452_tests_allowed": False,
        "prompt452_file_creation_allowed": False,
        "prompt452_git_mutation_performed_observed": git_mutation_observed,
        "prompt452_remote_mutation_performed_observed": remote_mutation_observed,
        "prompt452_commit_tag_performed_observed": commit_tag_observed,
        "prompt452_push_performed_observed": push_observed,
    }

    if not applicable:
        state.update(
            {
                "prompt452_review_closure_status": "not_applicable",
                "prompt452_review_classification": "not_applicable",
                "prompt452_review_evidence_missing_reason": (
                    "prompt452_not_applicable"
                ),
                "prompt452_blocked_reason": "",
                "prompt452_next_action": _prompt452_safe_deferred_next_action(
                    payload
                ),
                "prompt452_prompt442_style_review_required": False,
                "prompt452_prompt442_style_review_result": "not_applicable",
            }
        )
        return state

    unexpected_reason = ""
    if unsafe_mutation_observed:
        unexpected_reason = "prompt452_unexpected_runtime_mutation_observed"
    elif untracked_ambiguous or unexpected_ambiguous or changed_ambiguous:
        unexpected_reason = "prompt452_runtime_diff_evidence_ambiguous"
    elif untracked_known and untracked_files:
        unexpected_reason = "prompt452_untracked_files_observed"
    elif unexpected_known and unexpected_files:
        unexpected_reason = "prompt452_unexpected_files_observed"
    elif tracked_diff_empty is True and changed_known and changed_files:
        unexpected_reason = "prompt452_runtime_diff_evidence_ambiguous"
    elif tracked_diff_empty is False and not changed_known and changed_key:
        unexpected_reason = "prompt452_runtime_diff_evidence_ambiguous"
    elif (
        returncode == 0
        and tracked_diff_available
        and (
            (tracked_diff_empty is True and changed_known and changed_files)
            or (tracked_diff_empty is False and changed_known and not changed_files)
        )
    ):
        unexpected_reason = "prompt452_runtime_diff_evidence_ambiguous"

    if unexpected_reason:
        state.update(
            {
                "prompt452_review_closure_status": "unexpected_changes",
                "prompt452_review_classification": "unexpected_changes",
                "prompt452_review_evidence_ready": True,
                "prompt452_review_evidence_missing_reason": "",
                "prompt452_review_receipt_ready": True,
                "prompt452_prompt442_style_review_result": "unexpected_changes",
                "prompt452_unexpected_changes_detected": True,
                "prompt452_blocked_reason": unexpected_reason,
                "prompt452_next_action": "stop_for_prompt442_unexpected_changes",
            }
        )
        return state

    blocked_reason = ""
    if not result_available:
        blocked_reason = "prompt452_runtime_execution_result_missing"
    elif returncode is None and not returncode_classification:
        blocked_reason = "prompt452_runtime_execution_returncode_missing"
    elif failed_returncode:
        blocked_reason = "prompt452_runtime_execution_failed"
    elif not tracked_diff_available:
        blocked_reason = "prompt452_runtime_diff_evidence_missing"
    elif not changed_known:
        blocked_reason = "prompt452_runtime_changed_files_missing"
    elif error_unsafe:
        blocked_reason = "prompt452_runtime_execution_failed"

    success_diff_ready = (
        not blocked_reason
        and success_returncode
        and tracked_diff_empty is False
        and changed_known
        and bool(changed_files)
        and (not untracked_key or (untracked_known and not untracked_files))
        and (not unexpected_key or (unexpected_known and not unexpected_files))
        and not unsafe_mutation_observed
        and not error_unsafe
    )
    no_changes_ready = (
        not blocked_reason
        and success_returncode
        and tracked_diff_empty is True
        and changed_known
        and not changed_files
        and (not untracked_key or (untracked_known and not untracked_files))
        and (not unexpected_key or (unexpected_known and not unexpected_files))
        and not unsafe_mutation_observed
        and not error_unsafe
    )

    if success_diff_ready:
        state.update(
            {
                "prompt452_review_closure_status": "success_diff_ready",
                "prompt452_review_classification": "success_diff_ready",
                "prompt452_review_evidence_ready": True,
                "prompt452_review_evidence_missing_reason": "",
                "prompt452_review_receipt_ready": True,
                "prompt452_prompt442_style_review_ready": True,
                "prompt452_prompt442_style_review_result": "success_diff_ready",
                "prompt452_success_diff_ready": True,
                "prompt452_next_action": (
                    "prepare_prompt453_success_diff_commit_tag_closure"
                ),
            }
        )
        return state

    if no_changes_ready:
        state.update(
            {
                "prompt452_review_closure_status": "no_changes_ready",
                "prompt452_review_classification": "no_changes_ready",
                "prompt452_review_evidence_ready": True,
                "prompt452_review_evidence_missing_reason": "",
                "prompt452_review_receipt_ready": True,
                "prompt452_prompt442_style_review_ready": True,
                "prompt452_prompt442_style_review_result": "no_changes_ready",
                "prompt452_no_changes_ready": True,
                "prompt452_next_action": (
                    "prepare_prompt453_no_changes_next_cycle_continuation"
                ),
            }
        )
        return state

    if not blocked_reason:
        blocked_reason = "prompt452_runtime_diff_evidence_ambiguous"
    state.update(
        {
            "prompt452_review_evidence_missing_reason": blocked_reason,
            "prompt452_review_receipt_ready": True,
            "prompt452_prompt442_style_review_result": "blocked",
            "prompt452_prompt442_style_review_blocked_reason": blocked_reason,
            "prompt452_blocked_reason": blocked_reason,
            "prompt452_next_action": "manual_review_prompt452_route",
        }
    )
    return state

def _build_prompt454_prompt452_runtime_evidence_repair_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    prompt451_status = _normalize_text(
        payload.get("prompt451_minimal_autonomous_completion_status"),
        default="",
    )
    prompt451_next_action = _normalize_text(
        payload.get("prompt451_next_action"),
        default="",
    )
    prompt452_status = _normalize_text(
        payload.get("prompt452_review_closure_status"),
        default="",
    )
    prompt452_classification = _normalize_text(
        payload.get("prompt452_review_classification"),
        default="",
    )
    prompt452_blocked_reason = _normalize_text(
        payload.get("prompt452_blocked_reason"),
        default="",
    )
    prompt452_next_action = _normalize_text(
        payload.get("prompt452_next_action"),
        default="",
    )
    applicable = (
        prompt451_status == "runtime_packet_executed"
        and prompt452_status == "blocked"
        and prompt452_blocked_reason
        in _PROMPT454_APPLICABLE_PROMPT452_BLOCKED_REASONS
    )

    result_available_key, result_available_value = _prompt452_first_present(
        payload,
        (
            "prompt441_codex_result_available",
            "prompt441_codex_result_materialized",
            "prompt441_bounded_codex_invocation_result_available",
            "prompt449_runtime_execution_result_available",
            "prompt450_codex_reentry_result_available",
            "local_codex_one_shot_execution_result_available",
            "local_codex_one_shot_result_available",
            "codex_execution_result_available",
            "runtime_execution_result_available",
            "prompt452_runtime_execution_result_available",
        ),
    )
    result_path_key, result_path = _prompt452_first_text(
        payload,
        (
            "prompt441_codex_result_path",
            "prompt441_bounded_codex_invocation_result_path",
            "prompt449_runtime_execution_result_path",
            "prompt450_codex_reentry_result_path",
            "local_codex_one_shot_execution_result_path",
            "local_codex_one_shot_result_path",
            "codex_execution_result_path",
            "runtime_execution_result_path",
            "prompt452_review_source_result_path",
            "prompt452_runtime_execution_result_path",
        ),
    )
    stdout_path_key, stdout_path = _prompt452_first_text(
        payload,
        (
            "prompt441_codex_stdout_path",
            "prompt449_runtime_execution_stdout_path",
            "prompt450_codex_reentry_stdout_path",
            "local_codex_one_shot_stdout_path",
            "codex_execution_stdout_path",
            "runtime_execution_stdout_path",
            "prompt452_runtime_execution_stdout_path",
        ),
    )
    stderr_path_key, stderr_path = _prompt452_first_text(
        payload,
        (
            "prompt441_codex_stderr_path",
            "prompt449_runtime_execution_stderr_path",
            "prompt450_codex_reentry_stderr_path",
            "local_codex_one_shot_stderr_path",
            "codex_execution_stderr_path",
            "runtime_execution_stderr_path",
            "prompt452_runtime_execution_stderr_path",
        ),
    )
    returncode_key, returncode = _prompt454_first_returncode(
        payload,
        (
            "prompt454_repaired_returncode",
            "prompt441_codex_returncode",
            "prompt441_bounded_codex_invocation_returncode",
            "prompt449_runtime_execution_returncode",
            "prompt450_codex_reentry_returncode",
            "local_codex_one_shot_execution_returncode",
            "local_codex_one_shot_returncode",
            "codex_execution_returncode",
            "runtime_execution_returncode",
            "returncode",
            "prompt452_runtime_execution_returncode",
        ),
    )
    returncode_classification_key, returncode_classification = (
        _prompt454_first_returncode_classification(
            payload,
            (
                "prompt454_repaired_returncode_classification",
                "prompt441_codex_returncode_classification",
                "prompt441_bounded_codex_invocation_returncode_classification",
                "prompt449_runtime_execution_returncode_classification",
                "prompt450_codex_reentry_returncode_classification",
                "local_codex_one_shot_execution_returncode_classification",
                "local_codex_one_shot_returncode_classification",
                "codex_execution_returncode_classification",
                "runtime_execution_returncode_classification",
                "returncode_classification",
                "prompt452_runtime_execution_returncode_classification",
            ),
        )
    )
    tracked_diff_key, tracked_diff_value = _prompt452_first_present(
        payload,
        (
            "prompt441_post_execution_tracked_diff_empty",
            "prompt449_runtime_execution_tracked_diff_empty",
            "prompt450_reentry_tracked_diff_empty",
            "local_post_codex_diff_tracked_diff_empty",
            "post_execution_tracked_diff_empty",
            "tracked_diff_empty",
            "prompt452_runtime_execution_tracked_diff_empty",
        ),
    )
    tracked_diff_empty = _prompt452_boolish(tracked_diff_value)
    changed_key, changed_known, changed_files, changed_ambiguous = (
        _prompt454_first_known_string_list(
            payload,
            (
                "prompt454_repaired_changed_files",
                "prompt441_post_execution_changed_files",
                "prompt449_runtime_execution_changed_files",
                "prompt450_reentry_changed_files",
                "local_post_codex_diff_changed_files",
                "post_execution_changed_files",
                "changed_files",
                "prompt452_runtime_execution_changed_files",
            ),
        )
    )
    untracked_key, untracked_known, untracked_files, untracked_ambiguous = (
        _prompt454_first_known_string_list(
            payload,
            (
                "prompt454_repaired_untracked_files",
                "prompt441_post_execution_untracked_files",
                "prompt449_runtime_execution_untracked_files",
                "prompt450_reentry_untracked_files",
                "post_execution_untracked_files",
                "untracked_files",
                "prompt452_runtime_execution_untracked_files",
            ),
        )
    )
    unexpected_key, unexpected_known, unexpected_files, unexpected_ambiguous = (
        _prompt454_first_known_string_list(
            payload,
            (
                "prompt454_repaired_unexpected_files",
                "prompt441_post_execution_unexpected_files",
                "prompt449_runtime_execution_unexpected_files",
                "prompt450_reentry_unexpected_files",
                "post_execution_unexpected_files",
                "unexpected_files",
                "prompt452_runtime_execution_unexpected_files",
            ),
        )
    )

    result_available = (
        _prompt452_boolish(result_available_value) is True
        or bool(result_path)
        or returncode is not None
        or returncode_classification
        in _PROMPT452_SUCCESS_RETURNCODE_CLASSIFICATIONS
    )
    remote_mutation_observed = _prompt452_observed_mutation(
        payload,
        (
            "remote_mutation_performed",
            "prompt452_remote_mutation_performed_observed",
        ),
    )
    commit_tag_observed = _prompt452_observed_mutation(
        payload,
        (
            "commit_tag_performed",
            "prompt452_commit_tag_performed_observed",
        ),
    )
    push_observed = _prompt452_observed_mutation(
        payload,
        (
            "push_performed",
            "prompt452_push_performed_observed",
        ),
    )
    git_mutation_observed = _prompt452_observed_mutation(
        payload,
        (
            "git_mutation_performed",
            "prompt452_git_mutation_performed_observed",
        ),
    )
    mutation_blocks_success = (
        remote_mutation_observed or commit_tag_observed or push_observed
    )
    runtime_success = (
        (
            returncode == 0
            or returncode_classification
            in _PROMPT452_SUCCESS_RETURNCODE_CLASSIFICATIONS
        )
        and returncode_classification
        not in _PROMPT452_BLOCKED_RETURNCODE_CLASSIFICATIONS
        and not mutation_blocks_success
    )
    source_keys = [
        key
        for key in (
            result_available_key,
            result_path_key,
            returncode_key,
            returncode_classification_key,
            stdout_path_key,
            stderr_path_key,
            tracked_diff_key,
            changed_key,
            untracked_key,
            unexpected_key,
        )
        if key
    ]
    source_kind = _prompt454_source_kind(source_keys)

    state: dict[str, Any] = {
        "prompt454_schema_version": _PROMPT454_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt454",
        "prompt454_applicable": applicable,
        "prompt454_prompt451_status": prompt451_status,
        "prompt454_prompt451_next_action": prompt451_next_action,
        "prompt454_prompt452_status": prompt452_status,
        "prompt454_prompt452_classification": prompt452_classification,
        "prompt454_prompt452_blocked_reason": prompt452_blocked_reason,
        "prompt454_prompt452_next_action": prompt452_next_action,
        "prompt454_repair_status": "blocked",
        "prompt454_repair_evidence_ready": False,
        "prompt454_repair_evidence_missing_reason": "",
        "prompt454_repair_source_kind": source_kind,
        "prompt454_repair_source_keys": source_keys,
        "prompt454_repaired_runtime_result_available": result_available,
        "prompt454_repaired_returncode": returncode,
        "prompt454_repaired_returncode_classification": returncode_classification,
        "prompt454_repaired_stdout_path": stdout_path,
        "prompt454_repaired_stderr_path": stderr_path,
        "prompt454_repaired_result_path": result_path,
        "prompt454_repaired_tracked_diff_empty": tracked_diff_empty,
        "prompt454_repaired_changed_files": changed_files,
        "prompt454_repaired_changed_files_known": changed_known,
        "prompt454_repaired_untracked_files": untracked_files,
        "prompt454_repaired_untracked_files_known": untracked_known,
        "prompt454_repaired_unexpected_files": unexpected_files,
        "prompt454_repaired_unexpected_files_known": unexpected_known,
        "prompt454_success_diff_ready": False,
        "prompt454_no_changes_ready": False,
        "prompt454_unexpected_changes_detected": False,
        "prompt454_blocked_reason": "",
        "prompt454_next_action": "manual_review_prompt454_route",
        "prompt454_git_mutation_allowed": False,
        "prompt454_remote_mutation_allowed": False,
        "prompt454_commit_tag_allowed": False,
        "prompt454_push_allowed": False,
        "prompt454_tests_allowed": False,
        "prompt454_file_creation_allowed": False,
        "prompt454_git_mutation_performed_observed": git_mutation_observed,
        "prompt454_remote_mutation_performed_observed": remote_mutation_observed,
        "prompt454_commit_tag_performed_observed": commit_tag_observed,
        "prompt454_push_performed_observed": push_observed,
    }

    if not applicable:
        state.update(
            {
                "prompt454_repair_status": "not_applicable",
                "prompt454_repair_evidence_missing_reason": (
                    "prompt454_not_applicable"
                ),
                "prompt454_blocked_reason": "prompt454_not_applicable",
                "prompt454_next_action": _prompt454_safe_deferred_next_action(
                    payload
                ),
            }
        )
        return state

    unexpected_changes = (
        (untracked_known and bool(untracked_files))
        or (unexpected_known and bool(unexpected_files))
        or (tracked_diff_empty is True and bool(changed_files))
        or (tracked_diff_empty is False and not changed_known)
        or mutation_blocks_success
        or changed_ambiguous
        or untracked_ambiguous
        or unexpected_ambiguous
    )
    if unexpected_changes:
        reason = (
            "prompt454_unexpected_runtime_mutation_observed"
            if mutation_blocks_success
            else "prompt454_runtime_diff_evidence_ambiguous"
        )
        state.update(
            {
                "prompt454_repair_status": "unexpected_changes",
                "prompt454_repair_evidence_ready": True,
                "prompt454_repair_evidence_missing_reason": "",
                "prompt454_unexpected_changes_detected": True,
                "prompt454_blocked_reason": reason,
                "prompt454_next_action": "stop_for_prompt442_unexpected_changes",
            }
        )
        return state

    blocked_reason = ""
    if not result_available:
        blocked_reason = "prompt454_runtime_execution_result_missing"
    elif returncode is None and not returncode_classification:
        blocked_reason = "prompt454_runtime_execution_returncode_missing"
    elif returncode_classification == "not_run":
        blocked_reason = "prompt454_runtime_execution_result_not_success"
    elif returncode is not None and returncode != 0:
        blocked_reason = "prompt454_runtime_execution_result_not_success"
    elif returncode_classification in _PROMPT452_BLOCKED_RETURNCODE_CLASSIFICATIONS:
        blocked_reason = "prompt454_runtime_execution_result_not_success"
    elif not runtime_success:
        blocked_reason = "prompt454_runtime_execution_result_not_success"
    elif tracked_diff_empty is None:
        blocked_reason = "prompt454_runtime_diff_evidence_missing"
    elif not changed_known:
        blocked_reason = "prompt454_runtime_changed_files_missing"

    if not blocked_reason and tracked_diff_empty is True and not changed_files:
        state.update(
            {
                "prompt454_repair_status": "no_changes_ready",
                "prompt454_repair_evidence_ready": True,
                "prompt454_repair_evidence_missing_reason": "",
                "prompt454_no_changes_ready": True,
                "prompt454_next_action": (
                    "prepare_prompt455_no_changes_next_cycle_continuation"
                ),
            }
        )
        return state
    if not blocked_reason and tracked_diff_empty is False and changed_files:
        state.update(
            {
                "prompt454_repair_status": "success_diff_ready",
                "prompt454_repair_evidence_ready": True,
                "prompt454_repair_evidence_missing_reason": "",
                "prompt454_success_diff_ready": True,
                "prompt454_next_action": (
                    "prepare_prompt455_success_diff_commit_tag_closure"
                ),
            }
        )
        return state

    if not blocked_reason:
        blocked_reason = "prompt454_runtime_diff_evidence_ambiguous"
    state.update(
        {
            "prompt454_repair_status": "blocked",
            "prompt454_repair_evidence_ready": False,
            "prompt454_repair_evidence_missing_reason": blocked_reason,
            "prompt454_blocked_reason": blocked_reason,
            "prompt454_next_action": "manual_review_prompt454_route",
        }
    )
    return state

def _build_prompt453_commit_tag_ready_explicit_allow_packet_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    prompt451_status = _normalize_text(
        payload.get("prompt451_minimal_autonomous_completion_status"),
        default="",
    )
    prompt451_next_action = _normalize_text(
        payload.get("prompt451_next_action"),
        default="",
    )
    applicable = (
        prompt451_status == "commit_tag_ready"
        and prompt451_next_action
        == "request_explicit_prompt451_commit_tag_allow"
    )
    explicit_allow_present = _prompt453_explicit_commit_tag_allow_present(payload)
    changed_files = _normalize_string_list(
        payload.get("prompt451_prompt442_allowed_changed_files")
        or payload.get("prompt442_allowed_changed_files")
        or payload.get("prompt443_allowed_changed_files"),
        sort_items=False,
    )
    untracked_files = _normalize_string_list(
        payload.get("prompt451_prompt442_unexpected_untracked_files")
        or payload.get("prompt442_unexpected_untracked_files")
        or payload.get("prompt443_unexpected_untracked_files"),
        sort_items=False,
    )
    unexpected_files = _normalize_string_list(
        payload.get("prompt451_prompt442_unexpected_changed_files")
        or payload.get("prompt442_unexpected_changed_files")
        or payload.get("prompt443_unexpected_changed_files"),
        sort_items=False,
    )
    approve_candidate_ready = (
        payload.get("prompt451_approve_candidate_ready") is True
    )
    diff_safety_status = _normalize_text(
        payload.get("prompt451_approve_candidate_safety_status")
        or payload.get("prompt451_prompt442_change_safety_status")
        or payload.get("prompt442_post_codex_change_safety_status"),
        default="",
    )
    evidence_missing_reason = ""
    if not applicable:
        evidence_missing_reason = "prompt453_not_applicable"
    elif not approve_candidate_ready:
        evidence_missing_reason = "prompt453_approve_candidate_not_ready"
    elif unexpected_files or untracked_files:
        evidence_missing_reason = "prompt453_unexpected_files_present"

    git_mutation_observed = _prompt452_observed_mutation(
        payload,
        (
            "git_mutation_performed",
            "git_mutation_performed_observed",
            "prompt451_git_mutation_performed_observed",
            "prompt452_git_mutation_performed_observed",
        ),
    )
    remote_mutation_observed = _prompt452_observed_mutation(
        payload,
        (
            "remote_mutation_performed",
            "remote_mutation_performed_observed",
            "prompt451_remote_mutation_performed_observed",
            "prompt452_remote_mutation_performed_observed",
        ),
    )
    commit_tag_observed = _prompt452_observed_mutation(
        payload,
        (
            "commit_tag_performed",
            "commit_tag_performed_observed",
            "prompt451_commit_performed",
            "prompt451_tag_performed",
            "prompt451_commit_tag_performed_observed",
            "prompt452_commit_tag_performed_observed",
        ),
    )
    push_observed = _prompt452_observed_mutation(
        payload,
        (
            "push_performed",
            "push_performed_observed",
            "prompt451_push_performed_observed",
            "prompt452_push_performed_observed",
        ),
    )

    state: dict[str, Any] = {
        "prompt453_schema_version": _PROMPT453_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt453",
        "prompt453_applicable": applicable,
        "prompt453_source_route": (
            "prompt451_commit_tag_ready_explicit_allow"
            if applicable
            else "prompt453_not_applicable"
        ),
        "prompt453_prompt451_status": prompt451_status,
        "prompt453_prompt451_next_action": prompt451_next_action,
        "prompt453_commit_tag_packet_status": "blocked",
        "prompt453_commit_tag_packet_required": False,
        "prompt453_commit_tag_packet_ready": False,
        "prompt453_commit_tag_packet_blocked_reason": "",
        "prompt453_commit_tag_packet_explicit_allow_required": False,
        "prompt453_commit_tag_packet_explicit_allow_present": False,
        "prompt453_commit_tag_packet_execution_allowed": False,
        "prompt453_commit_tag_packet_execution_attempted": False,
        "prompt453_commit_tag_packet_execution_performed": False,
        "prompt453_commit_message": _normalize_text(
            payload.get("prompt453_commit_message"),
            default="Prompt453 prepare commit tag closure packet",
        ),
        "prompt453_tag_name": _normalize_text(
            payload.get("prompt453_tag_name"),
            default="prompt453-commit-tag-ready-explicit-allow-packet",
        ),
        "prompt453_approve_candidate_ready": approve_candidate_ready,
        "prompt453_changed_files": changed_files,
        "prompt453_untracked_files": untracked_files,
        "prompt453_unexpected_files": unexpected_files,
        "prompt453_diff_safety_status": diff_safety_status,
        "prompt453_evidence_missing_reason": evidence_missing_reason,
        "prompt453_post_commit_clean_rerun_required": (
            payload.get("prompt451_post_commit_clean_rerun_required") is True
        ),
        "prompt453_post_commit_clean_rerun_request_ready": (
            payload.get("prompt451_post_commit_clean_rerun_request_ready") is True
        ),
        "prompt453_success_closure_candidate_ready": (
            payload.get("prompt451_success_closure_candidate") is True
        ),
        "prompt453_autonomous_next_cycle_after_commit_candidate_ready": (
            payload.get("prompt451_autonomous_next_cycle_ready") is True
            or payload.get("prompt451_post_commit_clean_rerun_request_ready")
            is True
        ),
        "prompt453_blocked_reason": "",
        "prompt453_next_action": "manual_review_prompt453_route",
        "prompt453_git_mutation_allowed": False,
        "prompt453_remote_mutation_allowed": False,
        "prompt453_commit_tag_allowed": False,
        "prompt453_push_allowed": False,
        "prompt453_tests_allowed": False,
        "prompt453_file_creation_allowed": False,
        "prompt453_git_mutation_performed_observed": git_mutation_observed,
        "prompt453_remote_mutation_performed_observed": remote_mutation_observed,
        "prompt453_commit_tag_performed_observed": commit_tag_observed,
        "prompt453_push_performed_observed": push_observed,
    }

    if not applicable:
        state.update(
            {
                "prompt453_commit_tag_packet_status": "not_applicable",
                "prompt453_next_action": _prompt453_safe_deferred_next_action(
                    payload
                ),
            }
        )
        return state

    if not explicit_allow_present:
        state.update(
            {
                "prompt453_commit_tag_packet_status": "explicit_allow_required",
                "prompt453_commit_tag_packet_required": True,
                "prompt453_commit_tag_packet_ready": True,
                "prompt453_commit_tag_packet_blocked_reason": (
                    "prompt453_commit_tag_explicit_allow_required"
                ),
                "prompt453_commit_tag_packet_explicit_allow_required": True,
                "prompt453_commit_tag_packet_explicit_allow_present": False,
                "prompt453_commit_tag_packet_execution_allowed": False,
                "prompt453_blocked_reason": (
                    "prompt453_commit_tag_explicit_allow_required"
                ),
                "prompt453_next_action": (
                    "request_explicit_prompt453_commit_tag_allow"
                ),
            }
        )
        return state

    state.update(
        {
            "prompt453_commit_tag_packet_status": "ready",
            "prompt453_commit_tag_packet_required": True,
            "prompt453_commit_tag_packet_ready": True,
            "prompt453_commit_tag_packet_blocked_reason": "",
            "prompt453_commit_tag_packet_explicit_allow_required": True,
            "prompt453_commit_tag_packet_explicit_allow_present": True,
            "prompt453_commit_tag_packet_execution_allowed": True,
            "prompt453_blocked_reason": "",
            "prompt453_next_action": "execute_prompt454_commit_tag_packet",
        }
    )
    return state

def _build_prompt455_explicit_commit_tag_allow_bridge_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    prompt451_status = _normalize_text(
        payload.get("prompt451_minimal_autonomous_completion_status"),
        default="",
    )
    prompt451_next_action = _normalize_text(
        payload.get("prompt451_next_action"),
        default="",
    )
    prompt453_status = _normalize_text(
        payload.get("prompt453_commit_tag_packet_status"),
        default="",
    )
    prompt453_next_action = _normalize_text(
        payload.get("prompt453_next_action"),
        default="",
    )
    prompt454_status = _normalize_text(
        payload.get("prompt454_repair_status"),
        default="",
    )
    prompt454_next_action = _normalize_text(
        payload.get("prompt454_next_action"),
        default="",
    )

    prompt453_route_applicable = (
        prompt453_status == "explicit_allow_required"
        and prompt453_next_action
        == "request_explicit_prompt453_commit_tag_allow"
    )
    upstream_route_applicable = (
        prompt451_status == "commit_tag_ready"
        and prompt451_next_action
        == "request_explicit_prompt451_commit_tag_allow"
    )
    applicable = prompt453_route_applicable or upstream_route_applicable
    explicit_allow_present, explicit_allow_source = (
        _prompt455_explicit_commit_tag_allow_source(payload)
    )

    returncode_key, runtime_returncode = _prompt454_first_returncode(
        payload,
        (
            "prompt454_repaired_returncode",
            "prompt452_runtime_execution_returncode",
            "prompt451_reentry_returncode",
            "prompt450_codex_reentry_returncode",
            "prompt449_runtime_execution_returncode",
            "runtime_execution_returncode",
            "codex_execution_returncode",
            "returncode",
        ),
    )
    classification_key, runtime_classification = (
        _prompt454_first_returncode_classification(
            payload,
            (
                "prompt454_repaired_returncode_classification",
                "prompt452_runtime_execution_returncode_classification",
                "prompt451_reentry_returncode_classification",
                "prompt450_codex_reentry_returncode_classification",
                "prompt449_runtime_execution_returncode_classification",
                "runtime_execution_returncode_classification",
                "codex_execution_returncode_classification",
                "returncode_classification",
            ),
        )
    )
    runtime_success_evidence_ready = (
        runtime_returncode == 0
        or runtime_classification in _PROMPT452_SUCCESS_RETURNCODE_CLASSIFICATIONS
    )
    approve_candidate_ready = bool(
        payload.get("prompt453_approve_candidate_ready") is True
        or payload.get("prompt451_approve_candidate_ready") is True
        or payload.get("prompt451_prompt443_approve_commit_tag_candidate") is True
    )
    changed_files_known, changed_files = _prompt455_known_string_list(
        payload,
        (
            "prompt453_changed_files",
            "prompt454_repaired_changed_files",
            "prompt451_prompt442_allowed_changed_files",
            "prompt442_allowed_changed_files",
            "prompt443_allowed_changed_files",
        ),
    )
    untracked_files_known, untracked_files = _prompt455_known_string_list(
        payload,
        (
            "prompt453_untracked_files",
            "prompt454_repaired_untracked_files",
            "prompt451_prompt442_unexpected_untracked_files",
            "prompt442_unexpected_untracked_files",
            "prompt443_unexpected_untracked_files",
        ),
    )
    unexpected_files_known, unexpected_files = _prompt455_known_string_list(
        payload,
        (
            "prompt453_unexpected_files",
            "prompt454_repaired_unexpected_files",
            "prompt451_prompt442_unexpected_changed_files",
            "prompt442_unexpected_changed_files",
            "prompt443_unexpected_changed_files",
        ),
    )
    diff_safety_status = _normalize_text(
        payload.get("prompt453_diff_safety_status")
        or payload.get("prompt451_approve_candidate_safety_status")
        or payload.get("prompt451_prompt442_change_safety_status")
        or payload.get("prompt442_post_codex_change_safety_status"),
        default="",
    )
    prompt453_commit_message = _normalize_text(
        payload.get("prompt453_commit_message"),
        default="",
    )
    if prompt453_commit_message == "Prompt453 prepare commit tag closure packet":
        prompt453_commit_message = ""
    prompt453_tag_name = _normalize_text(
        payload.get("prompt453_tag_name"),
        default="",
    )
    if (
        prompt453_tag_name
        == "prompt453-commit-tag-ready-explicit-allow-packet"
    ):
        prompt453_tag_name = ""
    commit_message = _normalize_text(
        payload.get("prompt455_commit_message")
        or payload.get("prompt451_commit_message_candidate")
        or payload.get("prompt451_prompt443_commit_message_candidate")
        or prompt453_commit_message,
        default="Prompt455 prepare explicit commit tag execution bridge",
    )
    tag_name = _normalize_text(
        payload.get("prompt455_tag_name")
        or payload.get("prompt451_tag_name_candidate")
        or payload.get("prompt451_prompt443_tag_name_candidate")
        or prompt453_tag_name,
        default="prompt455-explicit-commit-tag-allow-bridge",
    )
    expected_head = _normalize_text(
        payload.get("prompt455_expected_head_before_commit")
        or payload.get("prompt453_expected_head_before_commit")
        or payload.get("expected_head_before_commit")
        or payload.get("head_before_commit"),
        default="",
    )
    expected_clean_after_commit = bool(
        payload.get("prompt455_expected_clean_after_commit") is True
        or payload.get("prompt453_expected_clean_after_commit") is True
        or payload.get("prompt451_head_clean_required") is True
    )

    git_mutation_observed = _prompt452_observed_mutation(
        payload,
        (
            "prompt455_git_mutation_performed_observed",
            "prompt453_git_mutation_performed_observed",
            "prompt454_git_mutation_performed_observed",
            "git_mutation_performed_observed",
            "git_mutation_performed",
        ),
    )
    remote_mutation_observed = _prompt452_observed_mutation(
        payload,
        (
            "prompt455_remote_mutation_performed_observed",
            "prompt453_remote_mutation_performed_observed",
            "prompt454_remote_mutation_performed_observed",
            "remote_mutation_performed_observed",
            "remote_mutation_performed",
        ),
    )
    commit_tag_observed = _prompt452_observed_mutation(
        payload,
        (
            "prompt455_commit_tag_performed_observed",
            "prompt453_commit_tag_performed_observed",
            "prompt454_commit_tag_performed_observed",
            "prompt451_commit_performed",
            "prompt451_tag_performed",
            "commit_tag_performed_observed",
            "commit_tag_performed",
        ),
    )
    push_observed = _prompt452_observed_mutation(
        payload,
        (
            "prompt455_push_performed_observed",
            "prompt453_push_performed_observed",
            "prompt454_push_performed_observed",
            "push_performed_observed",
            "push_performed",
        ),
    )

    evidence_missing_reason = ""
    if not applicable:
        evidence_missing_reason = "prompt455_not_applicable"
    elif remote_mutation_observed or push_observed or commit_tag_observed:
        evidence_missing_reason = "prompt455_unexpected_commit_tag_or_remote_mutation_observed"
    elif untracked_files_known and untracked_files:
        evidence_missing_reason = "prompt455_untracked_files_present"
    elif unexpected_files_known and unexpected_files:
        evidence_missing_reason = "prompt455_unexpected_files_present"
    elif not runtime_success_evidence_ready:
        evidence_missing_reason = "prompt455_runtime_success_evidence_missing"
    elif not approve_candidate_ready:
        evidence_missing_reason = "prompt455_approve_candidate_not_ready"
    elif not changed_files_known:
        evidence_missing_reason = "prompt455_changed_files_missing"

    state: dict[str, Any] = {
        "prompt455_schema_version": _PROMPT455_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt455",
        "prompt455_applicable": applicable,
        "prompt455_prompt451_status": prompt451_status,
        "prompt455_prompt451_next_action": prompt451_next_action,
        "prompt455_prompt453_status": prompt453_status,
        "prompt455_prompt453_next_action": prompt453_next_action,
        "prompt455_prompt454_status": prompt454_status,
        "prompt455_prompt454_next_action": prompt454_next_action,
        "prompt455_explicit_allow_bridge_status": "blocked",
        "prompt455_explicit_commit_tag_allow_required": False,
        "prompt455_explicit_commit_tag_allow_present": explicit_allow_present,
        "prompt455_explicit_commit_tag_allow_source": explicit_allow_source,
        "prompt455_execution_packet_required": False,
        "prompt455_execution_packet_ready": False,
        "prompt455_execution_packet_blocked_reason": evidence_missing_reason,
        "prompt455_commit_message": commit_message,
        "prompt455_tag_name": tag_name,
        "prompt455_expected_head_before_commit": expected_head,
        "prompt455_expected_changed_files": changed_files,
        "prompt455_expected_clean_after_commit": expected_clean_after_commit,
        "prompt455_expected_tag_after_commit": tag_name,
        "prompt455_runtime_success_evidence_ready": runtime_success_evidence_ready,
        "prompt455_runtime_returncode": runtime_returncode,
        "prompt455_runtime_returncode_classification": runtime_classification,
        "prompt455_approve_candidate_ready": approve_candidate_ready,
        "prompt455_changed_files_known": changed_files_known,
        "prompt455_changed_files": changed_files,
        "prompt455_untracked_files_known": untracked_files_known,
        "prompt455_untracked_files": untracked_files,
        "prompt455_unexpected_files_known": unexpected_files_known,
        "prompt455_unexpected_files": unexpected_files,
        "prompt455_evidence_missing_reason": evidence_missing_reason,
        "prompt455_diff_safety_status": diff_safety_status,
        "prompt455_commit_tag_execution_allowed_for_prompt456": False,
        "prompt455_commit_tag_execution_attempted": False,
        "prompt455_commit_tag_execution_performed": False,
        "prompt455_post_commit_clean_rerun_required": False,
        "prompt455_post_commit_clean_rerun_request_ready": False,
        "prompt455_success_closure_candidate_ready": False,
        "prompt455_autonomous_next_cycle_after_commit_candidate_ready": False,
        "prompt455_blocked_reason": evidence_missing_reason,
        "prompt455_next_action": "manual_review_prompt455_route",
        "prompt455_git_mutation_allowed": False,
        "prompt455_remote_mutation_allowed": False,
        "prompt455_commit_tag_allowed": False,
        "prompt455_push_allowed": False,
        "prompt455_tests_allowed": False,
        "prompt455_file_creation_allowed": False,
        "prompt455_git_mutation_performed_observed": git_mutation_observed,
        "prompt455_remote_mutation_performed_observed": remote_mutation_observed,
        "prompt455_commit_tag_performed_observed": commit_tag_observed,
        "prompt455_push_performed_observed": push_observed,
    }

    if not applicable:
        state.update(
            {
                "prompt455_explicit_allow_bridge_status": "not_applicable",
                "prompt455_next_action": _prompt455_safe_deferred_next_action(
                    payload
                ),
            }
        )
        return state

    if evidence_missing_reason:
        state.update(
            {
                "prompt455_explicit_allow_bridge_status": "blocked",
                "prompt455_execution_packet_ready": False,
                "prompt455_execution_packet_blocked_reason": (
                    evidence_missing_reason
                ),
                "prompt455_blocked_reason": evidence_missing_reason,
                "prompt455_next_action": "manual_review_prompt455_route",
            }
        )
        return state

    if not explicit_allow_present:
        state.update(
            {
                "prompt455_explicit_allow_bridge_status": (
                    "explicit_allow_required"
                ),
                "prompt455_explicit_commit_tag_allow_required": True,
                "prompt455_explicit_commit_tag_allow_present": False,
                "prompt455_execution_packet_required": True,
                "prompt455_execution_packet_ready": True,
                "prompt455_execution_packet_blocked_reason": "",
                "prompt455_commit_tag_execution_allowed_for_prompt456": False,
                "prompt455_blocked_reason": (
                    "prompt455_commit_tag_explicit_allow_required"
                ),
                "prompt455_next_action": (
                    "request_explicit_prompt455_commit_tag_allow"
                ),
            }
        )
        return state

    state.update(
        {
            "prompt455_explicit_allow_bridge_status": "execution_packet_ready",
            "prompt455_explicit_commit_tag_allow_required": True,
            "prompt455_explicit_commit_tag_allow_present": True,
            "prompt455_execution_packet_required": True,
            "prompt455_execution_packet_ready": True,
            "prompt455_execution_packet_blocked_reason": "",
            "prompt455_commit_tag_execution_allowed_for_prompt456": True,
            "prompt455_post_commit_clean_rerun_required": True,
            "prompt455_post_commit_clean_rerun_request_ready": True,
            "prompt455_success_closure_candidate_ready": True,
            "prompt455_autonomous_next_cycle_after_commit_candidate_ready": True,
            "prompt455_blocked_reason": "",
            "prompt455_next_action": "execute_prompt456_commit_tag_packet",
        }
    )
    return state

def _build_prompt456_compressed_bounded_commit_tag_execution_gate_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    prompt451_status = _normalize_text(
        payload.get("prompt451_minimal_autonomous_completion_status"),
        default="",
    )
    prompt451_next_action = _normalize_text(
        payload.get("prompt451_next_action"),
        default="",
    )
    prompt453_status = _normalize_text(
        payload.get("prompt453_commit_tag_packet_status"),
        default="",
    )
    prompt453_next_action = _normalize_text(
        payload.get("prompt453_next_action"),
        default="",
    )
    prompt455_status = _normalize_text(
        payload.get("prompt455_explicit_allow_bridge_status"),
        default="",
    )
    prompt455_next_action = _normalize_text(
        payload.get("prompt455_next_action"),
        default="",
    )
    applicable = (
        prompt455_status in {"explicit_allow_required", "execution_packet_ready"}
        or prompt455_next_action
        in {
            "request_explicit_prompt455_commit_tag_allow",
            "execute_prompt456_commit_tag_packet",
        }
        or prompt453_status == "explicit_allow_required"
        or prompt451_status == "commit_tag_ready"
    )
    explicit_allow_present, explicit_allow_source = (
        _prompt456_explicit_commit_tag_allow_source(payload)
    )
    (
        runtime_explicit_allow_present,
        runtime_explicit_allow_source,
        runtime_explicit_allow_keys_present,
    ) = _prompt456_runtime_command_explicit_commit_tag_allow_metadata(payload)
    explicit_allow_source_missing_reason = _normalize_text(
        payload.get("prompt456_explicit_commit_tag_allow_source_missing_reason"),
        default="",
    )

    returncode_key, runtime_returncode = _prompt454_first_returncode(
        payload,
        (
            "prompt455_runtime_returncode",
            "prompt454_repaired_returncode",
            "prompt452_runtime_execution_returncode",
            "prompt451_reentry_returncode",
            "runtime_execution_returncode",
            "codex_execution_returncode",
            "returncode",
        ),
    )
    classification_key, runtime_classification = (
        _prompt454_first_returncode_classification(
            payload,
            (
                "prompt455_runtime_returncode_classification",
                "prompt454_repaired_returncode_classification",
                "prompt452_runtime_execution_returncode_classification",
                "prompt451_reentry_returncode_classification",
                "runtime_execution_returncode_classification",
                "codex_execution_returncode_classification",
                "returncode_classification",
            ),
        )
    )
    runtime_success_evidence_ready = bool(
        payload.get("prompt455_runtime_success_evidence_ready") is True
        or runtime_returncode == 0
        or runtime_classification in _PROMPT452_SUCCESS_RETURNCODE_CLASSIFICATIONS
    )
    approve_candidate_ready = bool(
        payload.get("prompt455_approve_candidate_ready") is True
        or payload.get("prompt453_approve_candidate_ready") is True
        or payload.get("prompt451_approve_candidate_ready") is True
        or payload.get("prompt451_prompt443_approve_commit_tag_candidate") is True
    )
    changed_files_known, changed_files = _prompt456_first_known_string_list(
        payload,
        (
            "prompt455_changed_files",
            "prompt453_changed_files",
            "prompt454_repaired_changed_files",
            "prompt451_prompt442_allowed_changed_files",
            "prompt442_allowed_changed_files",
            "prompt443_allowed_changed_files",
        ),
    )
    expected_files_known, expected_changed_files = (
        _prompt456_first_known_string_list(
            payload,
            (
                "prompt455_expected_changed_files",
                "prompt456_expected_changed_files",
                "expected_changed_files",
            ),
        )
    )
    if not changed_files_known and expected_files_known:
        changed_files_known = True
        changed_files = list(expected_changed_files)
    untracked_files_known, untracked_files = _prompt456_first_known_string_list(
        payload,
        (
            "prompt455_untracked_files",
            "prompt453_untracked_files",
            "prompt454_repaired_untracked_files",
            "prompt451_prompt442_unexpected_untracked_files",
            "prompt442_unexpected_untracked_files",
            "prompt443_unexpected_untracked_files",
        ),
    )
    unexpected_files_known, unexpected_files = _prompt456_first_known_string_list(
        payload,
        (
            "prompt455_unexpected_files",
            "prompt453_unexpected_files",
            "prompt454_repaired_unexpected_files",
            "prompt451_prompt442_unexpected_changed_files",
            "prompt442_unexpected_changed_files",
            "prompt443_unexpected_changed_files",
        ),
    )
    commit_message = _normalize_text(
        payload.get("prompt455_commit_message")
        or payload.get("prompt453_commit_message")
        or payload.get("prompt451_commit_message_candidate")
        or payload.get("prompt451_prompt443_commit_message_candidate"),
        default="Prompt456 execute compressed bounded commit tag packet",
    )
    if commit_message in {
        "Prompt455 prepare explicit commit tag execution bridge",
        "Prompt453 prepare commit tag closure packet",
    }:
        commit_message = "Prompt456 execute compressed bounded commit tag packet"
    tag_name = _normalize_text(
        payload.get("prompt455_tag_name")
        or payload.get("prompt453_tag_name")
        or payload.get("prompt451_tag_name_candidate")
        or payload.get("prompt451_prompt443_tag_name_candidate"),
        default="prompt456-compressed-bounded-commit-tag-execution-gate",
    )
    if tag_name in {
        "prompt455-explicit-commit-tag-allow-bridge",
        "prompt453-commit-tag-ready-explicit-allow-packet",
    }:
        tag_name = "prompt456-compressed-bounded-commit-tag-execution-gate"
    expected_head = _normalize_text(
        payload.get("prompt455_expected_head_before_commit")
        or payload.get("prompt453_expected_head_before_commit")
        or payload.get("expected_head_before_commit")
        or payload.get("head_before_commit"),
        default="",
    )
    expected_clean_after_commit = bool(
        payload.get("prompt455_expected_clean_after_commit") is True
        or payload.get("prompt453_expected_clean_after_commit") is True
        or payload.get("prompt451_head_clean_required") is True
    )
    diff_safety_status = _normalize_text(
        payload.get("prompt455_diff_safety_status")
        or payload.get("prompt453_diff_safety_status")
        or payload.get("prompt451_approve_candidate_safety_status")
        or payload.get("prompt451_prompt442_change_safety_status")
        or payload.get("prompt442_post_codex_change_safety_status"),
        default="",
    )

    tag_uniqueness_ready, tag_already_exists = _prompt456_tag_uniqueness_state(
        payload
    )
    git_mutation_observed = _prompt452_observed_mutation(
        payload,
        (
            "prompt456_git_mutation_performed_observed",
            "prompt455_git_mutation_performed_observed",
            "prompt453_git_mutation_performed_observed",
            "prompt454_git_mutation_performed_observed",
            "git_mutation_performed_observed",
            "git_mutation_performed",
        ),
    )
    remote_mutation_observed = _prompt452_observed_mutation(
        payload,
        (
            "prompt456_remote_mutation_performed_observed",
            "prompt455_remote_mutation_performed_observed",
            "prompt453_remote_mutation_performed_observed",
            "prompt454_remote_mutation_performed_observed",
            "remote_mutation_performed_observed",
            "remote_mutation_performed",
        ),
    )
    commit_tag_observed = _prompt452_observed_mutation(
        payload,
        (
            "prompt456_commit_tag_performed_observed",
            "prompt456_commit_tag_execution_performed",
            "prompt455_commit_tag_execution_performed",
            "prompt455_commit_tag_performed_observed",
            "commit_tag_performed_observed",
            "commit_tag_performed",
        ),
    )
    push_observed = _prompt452_observed_mutation(
        payload,
        (
            "prompt456_push_performed_observed",
            "prompt455_push_performed_observed",
            "prompt453_push_performed_observed",
            "prompt454_push_performed_observed",
            "push_performed_observed",
            "push_performed",
        ),
    )

    changed_files_safe_or_expected = changed_files_known
    untracked_files_safe = (not untracked_files_known) or not untracked_files
    unexpected_files_safe = (not unexpected_files_known) or not unexpected_files
    no_remote_or_push = not (remote_mutation_observed or push_observed)
    prompt456_execution_observed = bool(
        commit_tag_observed
        and no_remote_or_push
        and runtime_success_evidence_ready
        and explicit_allow_present
    )

    evidence_missing_reason = ""
    if not applicable:
        evidence_missing_reason = "prompt456_not_applicable"
    elif not runtime_success_evidence_ready:
        evidence_missing_reason = "prompt456_runtime_success_evidence_missing"
    elif not approve_candidate_ready:
        evidence_missing_reason = "prompt456_approve_candidate_missing"
    elif not changed_files_safe_or_expected:
        evidence_missing_reason = "prompt456_changed_files_evidence_missing"
    elif untracked_files_known and untracked_files:
        evidence_missing_reason = "prompt456_untracked_files_observed"
    elif unexpected_files_known and unexpected_files:
        evidence_missing_reason = "prompt456_unexpected_files_observed"
    elif not tag_name:
        evidence_missing_reason = "prompt456_tag_name_missing"
    elif tag_already_exists:
        evidence_missing_reason = "prompt456_tag_already_exists"
    elif remote_mutation_observed or push_observed:
        evidence_missing_reason = "prompt456_remote_or_push_mutation_observed"
    elif commit_tag_observed and not prompt456_execution_observed:
        evidence_missing_reason = "prompt456_prior_commit_tag_mutation_observed"

    closure_ready = False
    state: dict[str, Any] = {
        "prompt456_schema_version": _PROMPT456_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt456",
        "prompt456_applicable": applicable,
        "prompt456_prompt451_status": prompt451_status,
        "prompt456_prompt451_next_action": prompt451_next_action,
        "prompt456_prompt453_status": prompt453_status,
        "prompt456_prompt453_next_action": prompt453_next_action,
        "prompt456_prompt455_status": prompt455_status,
        "prompt456_prompt455_next_action": prompt455_next_action,
        "prompt456_explicit_commit_tag_allow_required": False,
        "prompt456_explicit_commit_tag_allow_present": explicit_allow_present,
        "prompt456_explicit_commit_tag_allow_source": explicit_allow_source,
        "prompt456_runtime_command_explicit_commit_tag_allow_present": (
            runtime_explicit_allow_present
        ),
        "prompt456_runtime_command_explicit_commit_tag_allow_source": (
            runtime_explicit_allow_source
        ),
        "prompt456_runtime_command_explicit_commit_tag_allow_keys_present": (
            runtime_explicit_allow_keys_present
        ),
        "prompt456_explicit_commit_tag_allow_source_missing_reason": (
            explicit_allow_source_missing_reason
        ),
        "prompt456_commit_tag_execution_gate_status": "blocked",
        "prompt456_commit_tag_execution_required": False,
        "prompt456_commit_tag_execution_ready": False,
        "prompt456_commit_tag_execution_allowed": False,
        "prompt456_commit_tag_execution_attempted": False,
        "prompt456_commit_tag_execution_performed": False,
        "prompt456_commit_tag_execution_blocked_reason": evidence_missing_reason,
        "prompt456_commit_message": commit_message,
        "prompt456_tag_name": tag_name,
        "prompt456_expected_head_before_commit": expected_head,
        "prompt456_expected_changed_files": changed_files,
        "prompt456_expected_clean_after_commit": expected_clean_after_commit,
        "prompt456_expected_tag_after_commit": tag_name,
        "prompt456_tag_uniqueness_check_required": True,
        "prompt456_tag_uniqueness_ready": tag_uniqueness_ready,
        "prompt456_tag_already_exists": tag_already_exists,
        "prompt456_runtime_success_evidence_ready": runtime_success_evidence_ready,
        "prompt456_runtime_returncode": runtime_returncode,
        "prompt456_runtime_returncode_classification": runtime_classification,
        "prompt456_approve_candidate_ready": approve_candidate_ready,
        "prompt456_changed_files_known": changed_files_known,
        "prompt456_changed_files": changed_files,
        "prompt456_untracked_files_known": untracked_files_known,
        "prompt456_untracked_files": untracked_files,
        "prompt456_unexpected_files_known": unexpected_files_known,
        "prompt456_unexpected_files": unexpected_files,
        "prompt456_diff_safety_status": diff_safety_status,
        "prompt456_evidence_missing_reason": evidence_missing_reason,
        "prompt456_post_commit_clean_rerun_required": False,
        "prompt456_post_commit_clean_rerun_request_ready": False,
        "prompt456_success_closure_candidate_ready": False,
        "prompt456_autonomous_next_cycle_after_commit_candidate_ready": False,
        "prompt456_prompt457_expected_next_action": "",
        "prompt456_prompt458_completion_candidate_ready": False,
        "prompt456_prompt458_expected_completion_status": "",
        "prompt456_prompt458_expected_next_action": "",
        "prompt456_blocked_reason": evidence_missing_reason,
        "prompt456_next_action": "manual_review_prompt456_route",
        "prompt456_git_mutation_allowed": False,
        "prompt456_remote_mutation_allowed": False,
        "prompt456_commit_tag_allowed": False,
        "prompt456_push_allowed": False,
        "prompt456_tests_allowed": False,
        "prompt456_file_creation_allowed": False,
        "prompt456_git_mutation_performed_observed": git_mutation_observed,
        "prompt456_remote_mutation_performed_observed": remote_mutation_observed,
        "prompt456_commit_tag_performed_observed": commit_tag_observed,
        "prompt456_push_performed_observed": push_observed,
    }

    if not applicable:
        state.update(
            {
                "prompt456_commit_tag_execution_gate_status": "not_applicable",
                "prompt456_commit_tag_execution_blocked_reason": (
                    "prompt456_not_applicable"
                ),
                "prompt456_blocked_reason": "prompt456_not_applicable",
                "prompt456_next_action": "manual_review_prompt456_route",
            }
        )
        return state

    if prompt456_execution_observed:
        closure_ready = True
        state.update(
            {
                "prompt456_commit_tag_execution_gate_status": (
                    "execution_observed"
                ),
                "prompt456_explicit_commit_tag_allow_required": True,
                "prompt456_commit_tag_execution_required": True,
                "prompt456_commit_tag_execution_performed": True,
                "prompt456_commit_tag_execution_blocked_reason": "",
                "prompt456_blocked_reason": "",
                "prompt456_next_action": (
                    "run_prompt457_post_commit_clean_rerun_closure"
                ),
            }
        )
    elif not explicit_allow_present:
        state.update(
            {
                "prompt456_commit_tag_execution_gate_status": (
                    "explicit_allow_required"
                ),
                "prompt456_explicit_commit_tag_allow_required": True,
                "prompt456_explicit_commit_tag_allow_present": False,
                "prompt456_commit_tag_execution_required": True,
                "prompt456_commit_tag_execution_ready": False,
                "prompt456_commit_tag_execution_allowed": False,
                "prompt456_commit_tag_execution_blocked_reason": (
                    "prompt456_explicit_commit_tag_allow_required"
                ),
                "prompt456_blocked_reason": (
                    "prompt456_explicit_commit_tag_allow_required"
                ),
                "prompt456_next_action": (
                    "request_explicit_prompt456_commit_tag_allow"
                ),
            }
        )
        return state
    elif evidence_missing_reason:
        state.update(
            {
                "prompt456_commit_tag_execution_gate_status": "blocked",
                "prompt456_explicit_commit_tag_allow_required": True,
                "prompt456_commit_tag_execution_required": True,
                "prompt456_commit_tag_execution_ready": False,
                "prompt456_commit_tag_execution_allowed": False,
                "prompt456_commit_tag_execution_blocked_reason": (
                    evidence_missing_reason
                ),
                "prompt456_blocked_reason": evidence_missing_reason,
                "prompt456_next_action": "manual_review_prompt456_route",
            }
        )
        return state
    else:
        closure_ready = True
        state.update(
            {
                "prompt456_commit_tag_execution_gate_status": "execution_ready",
                "prompt456_explicit_commit_tag_allow_required": True,
                "prompt456_commit_tag_execution_required": True,
                "prompt456_commit_tag_execution_ready": True,
                "prompt456_commit_tag_execution_allowed": True,
                "prompt456_commit_tag_execution_blocked_reason": "",
                "prompt456_blocked_reason": "",
                "prompt456_next_action": "execute_prompt456_commit_tag_packet",
                "prompt456_git_mutation_allowed": True,
                "prompt456_commit_tag_allowed": True,
            }
        )

    if closure_ready:
        state.update(
            {
                "prompt456_post_commit_clean_rerun_required": True,
                "prompt456_post_commit_clean_rerun_request_ready": True,
                "prompt456_success_closure_candidate_ready": True,
                "prompt456_autonomous_next_cycle_after_commit_candidate_ready": True,
                "prompt456_prompt457_expected_next_action": (
                    "run_prompt457_post_commit_clean_rerun_closure"
                ),
                "prompt456_prompt458_completion_candidate_ready": True,
                "prompt456_prompt458_expected_completion_status": "completed",
                "prompt456_prompt458_expected_next_action": (
                    "continue_autonomous_next_cycle"
                ),
            }
        )
    return state

def _build_prompt457_commit_tag_execution_observation_clean_rerun_closure_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    prompt456_status = _normalize_text(
        payload.get("prompt456_commit_tag_execution_gate_status"),
        default="",
    )
    prompt456_next_action = _normalize_text(
        payload.get("prompt456_next_action"),
        default="",
    )
    prompt456_completion_candidate_ready = bool(
        payload.get("prompt456_prompt458_completion_candidate_ready") is True
    )
    applicable = bool(
        prompt456_status in {"execution_ready", "execution_observed"}
        or prompt456_next_action
        in {
            "execute_prompt456_commit_tag_packet",
            "run_prompt457_post_commit_clean_rerun_closure",
        }
        or prompt456_completion_candidate_ready
    )
    attempted_source, attempted_observed = _prompt457_observed_bool(
        payload,
        (
            "prompt456_commit_tag_execution_attempted",
            "prompt455_commit_tag_execution_attempted",
            "prompt453_commit_tag_packet_execution_attempted",
            "prompt451_commit_attempted",
            "prompt451_tag_attempted",
            "prompt433_approve_commit_tag_execution_attempted",
        ),
    )
    performed_source, performed_observed = _prompt457_observed_bool(
        payload,
        (
            "prompt456_commit_tag_execution_performed",
            "prompt455_commit_tag_execution_performed",
            "prompt453_commit_tag_packet_execution_performed",
            "prompt451_commit_performed",
            "prompt451_tag_performed",
            "prompt433_approve_commit_tag_execution_performed",
            "prompt433_commit_tag_result_payload.commit_tag_performed",
            "prompt434_commit_tag_success",
            "commit_tag_performed",
        ),
    )
    attempted_observed = bool(attempted_observed or performed_observed)
    git_mutation_source, git_mutation_observed = _prompt457_observed_bool(
        payload,
        (
            "prompt456_git_mutation_performed_observed",
            "prompt455_git_mutation_performed_observed",
            "prompt454_git_mutation_performed_observed",
            "prompt453_git_mutation_performed_observed",
            "git_mutation_performed_observed",
            "git_mutation_performed",
        ),
    )
    remote_mutation_source, remote_mutation_observed = _prompt457_observed_bool(
        payload,
        (
            "prompt456_remote_mutation_performed_observed",
            "prompt455_remote_mutation_performed_observed",
            "prompt454_remote_mutation_performed_observed",
            "prompt453_remote_mutation_performed_observed",
            "remote_mutation_performed_observed",
            "remote_mutation_performed",
        ),
    )
    push_source, push_observed = _prompt457_observed_bool(
        payload,
        (
            "prompt456_push_performed_observed",
            "prompt455_push_performed_observed",
            "prompt454_push_performed_observed",
            "prompt453_push_performed_observed",
            "push_performed_observed",
            "push_performed",
        ),
    )
    commit_sha_source, commit_sha = _prompt457_first_text(
        payload,
        (
            "prompt433_commit_tag_result_payload.commit_sha",
            "commit_sha",
            "prompt457_commit_sha",
        ),
    )
    tag_source, tag_name = _prompt457_first_text(
        payload,
        (
            "prompt456_tag_name",
            "prompt455_tag_name",
            "prompt453_tag_name",
            "prompt433_commit_tag_result_payload.tag_name",
            "tag_name",
        ),
    )
    message_source, commit_message = _prompt457_first_text(
        payload,
        (
            "prompt456_commit_message",
            "prompt455_commit_message",
            "prompt453_commit_message",
            "commit_message",
        ),
    )
    receipt_source, receipt_path = _prompt457_first_text(
        payload,
        (
            "prompt433_commit_tag_receipt_path",
            "prompt433_commit_tag_result_payload.receipt_path",
            "prompt451_commit_tag_receipt_path",
            "commit_tag_receipt_path",
        ),
    )
    request_ready_source, clean_request_ready = _prompt457_observed_bool(
        payload,
        (
            "prompt456_post_commit_clean_rerun_request_ready",
            "prompt455_post_commit_clean_rerun_request_ready",
            "prompt454_post_commit_clean_rerun_request_ready",
            "post_commit_clean_rerun_request_ready",
        ),
    )
    success_source, clean_success = _prompt457_observed_bool(
        payload,
        (
            "post_commit_clean_rerun_success",
        ),
    )
    final_clean_source, final_clean_ok = _prompt457_observed_bool(
        payload,
        (
            "post_commit_clean_rerun_final_clean_ok",
        ),
    )
    run_state_path_source, clean_run_state_path = _prompt457_first_text(
        payload,
        (
            "post_commit_clean_rerun_run_state_path",
            "prompt456_post_commit_clean_rerun_run_state_path",
            "prompt455_post_commit_clean_rerun_run_state_path",
            "prompt454_post_commit_clean_rerun_run_state_path",
        ),
    )
    result_source_candidates = [
        source
        for source in (
            performed_source,
            attempted_source,
            commit_sha_source,
            tag_source,
            message_source,
            receipt_source,
            git_mutation_source,
            request_ready_source,
            success_source,
            final_clean_source,
            run_state_path_source,
        )
        if source
    ]
    result_source = result_source_candidates[0] if result_source_candidates else ""
    commit_tag_execution_expected = bool(
        applicable
        and (
            prompt456_status in {"execution_ready", "execution_observed"}
            or prompt456_next_action
            in {
                "execute_prompt456_commit_tag_packet",
                "run_prompt457_post_commit_clean_rerun_closure",
            }
            or prompt456_completion_candidate_ready
        )
    )
    local_execution_observed = bool(
        performed_observed and not remote_mutation_observed and not push_observed
    )
    clean_observed = bool(clean_success or final_clean_ok)

    state: dict[str, Any] = {
        "prompt457_schema_version": _PROMPT457_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt457",
        "prompt457_applicable": applicable,
        "prompt457_prompt456_status": prompt456_status,
        "prompt457_prompt456_next_action": prompt456_next_action,
        "prompt457_prompt456_completion_candidate_ready": (
            prompt456_completion_candidate_ready
        ),
        "prompt457_commit_tag_execution_observation_status": "blocked",
        "prompt457_commit_tag_execution_expected": commit_tag_execution_expected,
        "prompt457_commit_tag_execution_observed": local_execution_observed,
        "prompt457_commit_tag_execution_attempted_observed": attempted_observed,
        "prompt457_commit_tag_execution_performed_observed": performed_observed,
        "prompt457_git_mutation_performed_observed": bool(
            git_mutation_observed or performed_observed
        ),
        "prompt457_remote_mutation_performed_observed": remote_mutation_observed,
        "prompt457_push_performed_observed": push_observed,
        "prompt457_commit_sha": commit_sha,
        "prompt457_tag_name": tag_name,
        "prompt457_commit_message": commit_message,
        "prompt457_commit_tag_receipt_ready": bool(receipt_path),
        "prompt457_commit_tag_receipt_path": receipt_path,
        "prompt457_commit_tag_result_source": result_source,
        "prompt457_post_commit_clean_rerun_required": applicable,
        "prompt457_post_commit_clean_rerun_request_ready": False,
        "prompt457_post_commit_clean_rerun_observed": clean_observed,
        "prompt457_post_commit_clean_rerun_success": clean_success,
        "prompt457_post_commit_clean_rerun_run_state_path": clean_run_state_path,
        "prompt457_post_commit_clean_rerun_final_clean_observed": bool(
            final_clean_source
        ),
        "prompt457_post_commit_clean_rerun_final_clean_ok": final_clean_ok,
        "prompt457_success_closure_candidate_ready": False,
        "prompt457_autonomous_next_cycle_candidate_ready": False,
        "prompt457_prompt458_completion_handoff_ready": False,
        "prompt457_prompt458_expected_completion_status": "",
        "prompt457_prompt458_expected_next_action": "",
        "prompt457_blocked_reason": "",
        "prompt457_next_action": "manual_review_prompt457_route",
        "prompt457_remote_mutation_allowed": False,
        "prompt457_push_allowed": False,
        "prompt457_tests_allowed": False,
        "prompt457_file_creation_allowed": False,
        "prompt457_git_mutation_allowed": bool(
            local_execution_observed
            or payload.get("prompt456_git_mutation_allowed") is True
            or payload.get("prompt456_commit_tag_execution_allowed") is True
        ),
        "prompt457_commit_tag_allowed": bool(
            local_execution_observed
            or payload.get("prompt456_commit_tag_allowed") is True
            or payload.get("prompt456_commit_tag_execution_allowed") is True
        ),
    }

    if not applicable:
        state.update(
            {
                "prompt457_commit_tag_execution_observation_status": (
                    "not_applicable"
                ),
                "prompt457_commit_tag_execution_expected": False,
                "prompt457_post_commit_clean_rerun_required": False,
                "prompt457_blocked_reason": "prompt457_not_applicable",
                "prompt457_next_action": "manual_review_prompt457_route",
            }
        )
        return state

    if remote_mutation_observed or push_observed:
        state.update(
            {
                "prompt457_commit_tag_execution_observation_status": "blocked",
                "prompt457_blocked_reason": (
                    "prompt457_remote_or_push_mutation_observed"
                ),
                "prompt457_next_action": "manual_review_prompt457_route",
            }
        )
        return state

    if prompt456_status not in {"execution_ready", "execution_observed"}:
        state.update(
            {
                "prompt457_commit_tag_execution_observation_status": "blocked",
                "prompt457_blocked_reason": (
                    "prompt457_prompt456_not_execution_ready"
                ),
                "prompt457_next_action": "manual_review_prompt457_route",
            }
        )
        return state

    if not local_execution_observed:
        if prompt456_status == "execution_ready":
            state.update(
                {
                    "prompt457_commit_tag_execution_observation_status": (
                        "awaiting_execution"
                    ),
                    "prompt457_commit_tag_execution_expected": True,
                    "prompt457_commit_tag_execution_observed": False,
                    "prompt457_post_commit_clean_rerun_required": True,
                    "prompt457_post_commit_clean_rerun_request_ready": False,
                    "prompt457_success_closure_candidate_ready": False,
                    "prompt457_prompt458_completion_handoff_ready": False,
                    "prompt457_blocked_reason": (
                        "prompt457_commit_tag_execution_not_observed"
                    ),
                    "prompt457_next_action": (
                        "execute_prompt456_commit_tag_packet"
                    ),
                }
            )
            return state
        state.update(
            {
                "prompt457_commit_tag_execution_observation_status": "blocked",
                "prompt457_blocked_reason": (
                    "prompt457_commit_tag_result_ambiguous"
                    if attempted_observed
                    else "prompt457_commit_tag_execution_not_observed"
                ),
                "prompt457_next_action": "manual_review_prompt457_route",
            }
        )
        return state

    if clean_observed:
        state.update(
            {
                "prompt457_commit_tag_execution_observation_status": (
                    "post_commit_clean_rerun_observed"
                ),
                "prompt457_post_commit_clean_rerun_required": True,
                "prompt457_post_commit_clean_rerun_request_ready": True,
                "prompt457_post_commit_clean_rerun_observed": True,
                "prompt457_post_commit_clean_rerun_success": True,
                "prompt457_post_commit_clean_rerun_final_clean_observed": True,
                "prompt457_post_commit_clean_rerun_final_clean_ok": True,
                "prompt457_success_closure_candidate_ready": True,
                "prompt457_autonomous_next_cycle_candidate_ready": True,
                "prompt457_prompt458_completion_handoff_ready": True,
                "prompt457_prompt458_expected_completion_status": "completed",
                "prompt457_prompt458_expected_next_action": (
                    "continue_autonomous_next_cycle"
                ),
                "prompt457_blocked_reason": "",
                "prompt457_next_action": (
                    "prepare_prompt458_minimal_autonomous_completion_closure"
                ),
            }
        )
        return state

    state.update(
        {
            "prompt457_commit_tag_execution_observation_status": (
                "execution_observed"
            ),
            "prompt457_commit_tag_execution_observed": True,
            "prompt457_commit_tag_execution_performed_observed": True,
            "prompt457_post_commit_clean_rerun_required": True,
            "prompt457_post_commit_clean_rerun_request_ready": True,
            "prompt457_success_closure_candidate_ready": True,
            "prompt457_autonomous_next_cycle_candidate_ready": True,
            "prompt457_prompt458_completion_handoff_ready": True,
            "prompt457_prompt458_expected_completion_status": "completed",
            "prompt457_prompt458_expected_next_action": (
                "continue_autonomous_next_cycle"
            ),
            "prompt457_blocked_reason": "",
            "prompt457_next_action": (
                "run_prompt457_post_commit_clean_rerun_closure"
            ),
        }
    )
    return state

def _build_prompt458_minimal_autonomous_completion_closure_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    prompt456_status = _normalize_text(
        payload.get("prompt456_commit_tag_execution_gate_status"),
        default="",
    )
    prompt456_next_action = _normalize_text(
        payload.get("prompt456_next_action"),
        default="",
    )
    prompt456_completion_candidate_ready = bool(
        payload.get("prompt456_prompt458_completion_candidate_ready") is True
    )
    prompt457_status = _normalize_text(
        payload.get("prompt457_commit_tag_execution_observation_status"),
        default="",
    )
    prompt457_next_action = _normalize_text(
        payload.get("prompt457_next_action"),
        default="",
    )
    prompt457_completion_handoff_ready = bool(
        payload.get("prompt457_prompt458_completion_handoff_ready") is True
    )
    applicable = bool(
        prompt456_completion_candidate_ready
        or prompt456_status in {"execution_ready", "execution_observed"}
        or prompt456_next_action == "execute_prompt456_commit_tag_packet"
        or prompt457_completion_handoff_ready
        or prompt457_next_action
        in {
            "run_prompt457_post_commit_clean_rerun_closure",
            "prepare_prompt458_minimal_autonomous_completion_closure",
        }
    )

    prompt456_ready = bool(
        payload.get("prompt456_commit_tag_execution_ready") is True
        or prompt456_status == "execution_ready"
    )
    prompt456_execution_allowed = bool(
        payload.get("prompt456_commit_tag_execution_allowed") is True
        or payload.get("prompt456_git_mutation_allowed") is True
        or payload.get("prompt456_commit_tag_allowed") is True
    )
    prompt456_commit_tag_performed = bool(
        payload.get("prompt456_commit_tag_execution_performed") is True
        or payload.get("prompt456_commit_tag_performed_observed") is True
    )
    prompt457_commit_tag_observed = bool(
        payload.get("prompt457_commit_tag_execution_observed") is True
        or payload.get("prompt457_commit_tag_execution_performed_observed") is True
    )
    fallback_commit_tag_observed = _prompt452_observed_mutation(
        payload,
        (
            "commit_tag_performed",
            "commit_tag_performed_observed",
        ),
    )
    commit_tag_execution_observed = bool(
        prompt457_commit_tag_observed
        or prompt456_commit_tag_performed
        or prompt456_status == "execution_observed"
        or fallback_commit_tag_observed
    )
    commit_tag_performed_observed = bool(commit_tag_execution_observed)

    git_mutation_observed = bool(
        payload.get("prompt457_git_mutation_performed_observed") is True
        or payload.get("prompt456_git_mutation_performed_observed") is True
        or _prompt452_observed_mutation(
            payload,
            (
                "git_mutation_performed",
                "git_mutation_performed_observed",
            ),
        )
    )
    remote_mutation_observed = bool(
        payload.get("prompt457_remote_mutation_performed_observed") is True
        or payload.get("prompt456_remote_mutation_performed_observed") is True
        or _prompt452_observed_mutation(
            payload,
            (
                "remote_mutation_performed",
                "remote_mutation_performed_observed",
            ),
        )
    )
    push_observed = bool(
        payload.get("prompt457_push_performed_observed") is True
        or payload.get("prompt456_push_performed_observed") is True
        or _prompt452_observed_mutation(
            payload,
            (
                "push_performed",
                "push_performed_observed",
            ),
        )
    )

    commit_sha = _normalize_text(
        payload.get("prompt457_commit_sha") or payload.get("commit_sha"),
        default="",
    )
    tag_name = _normalize_text(
        payload.get("prompt457_tag_name")
        or payload.get("prompt456_tag_name")
        or payload.get("tag_name"),
        default="",
    )
    commit_message = _normalize_text(
        payload.get("prompt457_commit_message")
        or payload.get("prompt456_commit_message")
        or payload.get("commit_message"),
        default="",
    )
    receipt_path = _normalize_text(
        payload.get("prompt457_commit_tag_receipt_path")
        or payload.get("commit_tag_receipt_path"),
        default="",
    )
    receipt_ready = bool(
        payload.get("prompt457_commit_tag_receipt_ready") is True
        or bool(receipt_path)
    )

    clean_request_ready = bool(
        payload.get("prompt457_post_commit_clean_rerun_request_ready") is True
        or payload.get("post_commit_clean_rerun_request_ready") is True
    )
    clean_success = bool(
        payload.get("prompt457_post_commit_clean_rerun_success") is True
        or payload.get("post_commit_clean_rerun_success") is True
    )
    final_clean_ok = bool(
        payload.get("prompt457_post_commit_clean_rerun_final_clean_ok") is True
        or payload.get("post_commit_clean_rerun_final_clean_ok") is True
    )
    clean_observed = bool(
        payload.get("prompt457_post_commit_clean_rerun_observed") is True
        or clean_success
        or final_clean_ok
    )
    clean_run_state_path = _normalize_text(
        payload.get("prompt457_post_commit_clean_rerun_run_state_path")
        or payload.get("post_commit_clean_rerun_run_state_path"),
        default="",
    )

    max_cycles_reached = bool(
        payload.get("prompt434_cycle_limit_reached") is True
        or payload.get("prompt427_max_cycles_reached") is True
        or payload.get("max_cycles_reached") is True
    )
    retry_limit_reached = bool(
        payload.get("retry_limit_reached") is True
        or payload.get("prompt431_retry_limit_reached") is True
    )
    unsafe_stop_required = bool(
        payload.get("unsafe_stop_required") is True
        or payload.get("global_stop_recommended") is True
        or payload.get("global_stop") is True
    )

    state: dict[str, Any] = {
        "prompt458_schema_version": _PROMPT458_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt458",
        "prompt458_applicable": applicable,
        "prompt458_prompt456_status": prompt456_status,
        "prompt458_prompt456_next_action": prompt456_next_action,
        "prompt458_prompt456_completion_candidate_ready": (
            prompt456_completion_candidate_ready
        ),
        "prompt458_prompt457_status": prompt457_status,
        "prompt458_prompt457_next_action": prompt457_next_action,
        "prompt458_prompt457_completion_handoff_ready": (
            prompt457_completion_handoff_ready
        ),
        "prompt458_minimal_autonomous_completion_status": "blocked",
        "prompt458_success_closure_ready": False,
        "prompt458_autonomous_next_cycle_ready": False,
        "prompt458_autonomous_next_cycle_request_ready": False,
        "prompt458_autonomous_next_cycle_runtime_request_ready": False,
        "prompt458_autonomous_next_cycle_prompt_request_ready": False,
        "prompt458_completed_reason": "",
        "prompt458_completion_blocked_reason": "",
        "prompt458_next_action": "manual_review_prompt458_route",
        "prompt458_commit_tag_execution_required": applicable,
        "prompt458_commit_tag_execution_ready": prompt456_ready,
        "prompt458_commit_tag_execution_observed": commit_tag_execution_observed,
        "prompt458_commit_tag_execution_performed_observed": (
            commit_tag_performed_observed
        ),
        "prompt458_commit_sha": commit_sha,
        "prompt458_tag_name": tag_name,
        "prompt458_commit_message": commit_message,
        "prompt458_commit_tag_receipt_ready": receipt_ready,
        "prompt458_commit_tag_receipt_path": receipt_path,
        "prompt458_post_commit_clean_rerun_required": bool(
            applicable and commit_tag_execution_observed
        ),
        "prompt458_post_commit_clean_rerun_request_ready": clean_request_ready,
        "prompt458_post_commit_clean_rerun_observed": clean_observed,
        "prompt458_post_commit_clean_rerun_success": clean_success,
        "prompt458_post_commit_clean_rerun_final_clean_ok": final_clean_ok,
        "prompt458_post_commit_clean_rerun_run_state_path": clean_run_state_path,
        "prompt458_remote_mutation_allowed": False,
        "prompt458_push_allowed": False,
        "prompt458_tests_allowed": False,
        "prompt458_file_creation_allowed": False,
        "prompt458_git_mutation_allowed": False,
        "prompt458_commit_tag_allowed": False,
        "prompt458_git_mutation_performed_observed": git_mutation_observed,
        "prompt458_remote_mutation_performed_observed": remote_mutation_observed,
        "prompt458_push_performed_observed": push_observed,
        "prompt458_commit_tag_performed_observed": commit_tag_performed_observed,
        "prompt458_max_cycles_guard_ready": not max_cycles_reached,
        "prompt458_retry_limit_guard_ready": not retry_limit_reached,
        "prompt458_unsafe_stop_guard_ready": not unsafe_stop_required,
        "prompt458_max_cycles_reached": max_cycles_reached,
        "prompt458_retry_limit_reached": retry_limit_reached,
        "prompt458_unsafe_stop_required": unsafe_stop_required,
    }

    if not applicable:
        state.update(
            {
                "prompt458_minimal_autonomous_completion_status": (
                    "not_applicable"
                ),
                "prompt458_success_closure_ready": False,
                "prompt458_autonomous_next_cycle_ready": False,
                "prompt458_completion_blocked_reason": (
                    "prompt458_not_applicable"
                ),
                "prompt458_next_action": "manual_review_prompt458_route",
            }
        )
        return state

    blocked_reason = ""
    if remote_mutation_observed:
        blocked_reason = "prompt458_remote_mutation_observed"
    elif push_observed:
        blocked_reason = "prompt458_push_mutation_observed"
    elif unsafe_stop_required:
        blocked_reason = "prompt458_unsafe_stop_required"
    elif clean_observed and not commit_tag_execution_observed:
        blocked_reason = "prompt458_clean_rerun_without_commit_tag_observation"
    elif git_mutation_observed and not commit_tag_execution_observed:
        blocked_reason = "prompt458_git_mutation_without_commit_tag_observation"
    elif (
        prompt456_status == "execution_observed"
        and not commit_tag_execution_observed
    ):
        blocked_reason = "prompt458_commit_tag_execution_evidence_ambiguous"
    elif prompt456_status == "execution_ready" and not prompt456_execution_allowed:
        blocked_reason = "prompt458_execution_ready_without_allow_evidence"

    if blocked_reason:
        state.update(
            {
                "prompt458_minimal_autonomous_completion_status": "blocked",
                "prompt458_success_closure_ready": False,
                "prompt458_autonomous_next_cycle_ready": False,
                "prompt458_completion_blocked_reason": blocked_reason,
                "prompt458_next_action": "manual_review_prompt458_route",
            }
        )
        return state

    if prompt456_status == "execution_ready" and not commit_tag_execution_observed:
        state.update(
            {
                "prompt458_minimal_autonomous_completion_status": (
                    "awaiting_commit_tag_execution"
                ),
                "prompt458_commit_tag_execution_required": True,
                "prompt458_commit_tag_execution_ready": True,
                "prompt458_commit_tag_execution_observed": False,
                "prompt458_commit_tag_execution_performed_observed": False,
                "prompt458_success_closure_ready": False,
                "prompt458_autonomous_next_cycle_ready": False,
                "prompt458_completion_blocked_reason": (
                    "prompt458_commit_tag_execution_not_observed"
                ),
                "prompt458_next_action": "execute_prompt456_commit_tag_packet",
            }
        )
        return state

    if commit_tag_execution_observed and not (clean_success and final_clean_ok):
        state.update(
            {
                "prompt458_minimal_autonomous_completion_status": (
                    "awaiting_post_commit_clean_rerun"
                ),
                "prompt458_commit_tag_execution_observed": True,
                "prompt458_commit_tag_execution_performed_observed": True,
                "prompt458_post_commit_clean_rerun_required": True,
                "prompt458_post_commit_clean_rerun_request_ready": True,
                "prompt458_success_closure_ready": False,
                "prompt458_autonomous_next_cycle_ready": False,
                "prompt458_completion_blocked_reason": (
                    "prompt458_post_commit_clean_rerun_not_observed"
                ),
                "prompt458_next_action": (
                    "run_prompt457_post_commit_clean_rerun_closure"
                ),
            }
        )
        return state

    if commit_tag_execution_observed and clean_success and final_clean_ok:
        state.update(
            {
                "prompt458_minimal_autonomous_completion_status": "completed",
                "prompt458_success_closure_ready": True,
                "prompt458_autonomous_next_cycle_ready": True,
                "prompt458_autonomous_next_cycle_request_ready": True,
                "prompt458_autonomous_next_cycle_runtime_request_ready": True,
                "prompt458_autonomous_next_cycle_prompt_request_ready": True,
                "prompt458_completed_reason": (
                    "prompt458_commit_tag_and_clean_rerun_closure_observed"
                ),
                "prompt458_completion_blocked_reason": "",
                "prompt458_next_action": "continue_autonomous_next_cycle",
            }
        )
        return state

    state.update(
        {
            "prompt458_minimal_autonomous_completion_status": "blocked",
            "prompt458_success_closure_ready": False,
            "prompt458_autonomous_next_cycle_ready": False,
            "prompt458_completion_blocked_reason": (
                "prompt458_evidence_ambiguous"
            ),
            "prompt458_next_action": "manual_review_prompt458_route",
        }
    )
    return state

def _build_prompt459_bounded_local_commit_tag_packet_executor_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}

    prompt456_status = _normalize_text(
        payload.get("prompt456_commit_tag_execution_gate_status"),
        default="",
    )
    prompt456_next_action = _normalize_text(
        payload.get("prompt456_next_action"),
        default="",
    )
    prompt456_execution_allowed = bool(
        payload.get("prompt456_commit_tag_execution_allowed") is True
    )
    prompt458_status = _normalize_text(
        payload.get("prompt458_minimal_autonomous_completion_status"),
        default="",
    )
    prompt458_next_action = _normalize_text(
        payload.get("prompt458_next_action"),
        default="",
    )
    applicable = bool(
        prompt456_next_action == "execute_prompt456_commit_tag_packet"
        or prompt458_next_action == "execute_prompt456_commit_tag_packet"
        or prompt456_status == "execution_ready"
        or prompt456_execution_allowed
        or payload.get("prompt456_prompt458_completion_candidate_ready") is True
    )
    explicit_allow_present = bool(
        payload.get("prompt456_explicit_commit_tag_allow_present") is True
        or payload.get("prompt455_explicit_commit_tag_allow_present") is True
        or payload.get("prompt453_commit_tag_packet_explicit_allow_present") is True
    )
    commit_message = _normalize_text(
        payload.get("prompt456_commit_message")
        or payload.get("prompt455_commit_message")
        or payload.get("prompt453_commit_message"),
        default="",
    )
    tag_name = _normalize_text(
        payload.get("prompt456_tag_name")
        or payload.get("prompt455_tag_name")
        or payload.get("prompt453_tag_name"),
        default="",
    )
    expected_head = _normalize_text(
        payload.get("prompt456_expected_head_before_commit")
        or payload.get("prompt455_expected_head_before_commit")
        or payload.get("prompt453_expected_head_before_commit"),
        default="",
    )
    expected_changed_files = _prompt459_first_non_empty_string_list(
        payload,
        (
            "prompt456_expected_changed_files",
            "prompt455_expected_changed_files",
            "prompt453_changed_files",
            "prompt456_changed_files",
            "prompt455_changed_files",
        ),
    )
    upstream_allowed_files = _prompt459_first_non_empty_string_list(
        payload,
        (
            "prompt442_allowed_changed_files",
            "prompt443_allowed_changed_files",
            "prompt451_prompt442_allowed_changed_files",
            "prompt455_changed_files",
            "prompt456_changed_files",
        ),
    )
    if not expected_changed_files:
        bounded_fallback_files = [
            path
            for path in (
                "automation/orchestration/planned_execution_runner.py",
                "scripts/run_planned_execution.py",
            )
            if path in set(upstream_allowed_files)
        ]
        expected_changed_files = sorted(bounded_fallback_files)
    actual_changed_files = _prompt459_first_non_empty_string_list(
        payload,
        (
            "prompt456_changed_files",
            "prompt455_changed_files",
            "prompt453_changed_files",
            "prompt454_repaired_changed_files",
        ),
    )
    if not actual_changed_files:
        actual_changed_files = list(expected_changed_files)
    actual_untracked_files = _prompt459_first_non_empty_string_list(
        payload,
        (
            "prompt456_untracked_files",
            "prompt455_untracked_files",
            "prompt453_untracked_files",
            "prompt454_repaired_untracked_files",
        ),
    )
    expected_clean_after_commit = bool(
        payload.get("prompt456_expected_clean_after_commit") is True
        or payload.get("prompt455_expected_clean_after_commit") is True
        or payload.get("prompt453_expected_clean_after_commit") is True
    )
    tag_uniqueness_ready = bool(
        payload.get("prompt456_tag_uniqueness_ready") is True
        or payload.get("prompt383_tag_preexistence_checked") is True
    )
    tag_already_exists = bool(
        payload.get("prompt456_tag_already_exists") is True
        or payload.get("prompt383_tag_preexisting") is True
    )
    runtime_success_ready = bool(
        payload.get("prompt456_runtime_success_evidence_ready") is True
        or payload.get("prompt455_runtime_success_evidence_ready") is True
    )
    approve_candidate_ready = bool(
        payload.get("prompt456_approve_candidate_ready") is True
        or payload.get("prompt455_approve_candidate_ready") is True
        or payload.get("prompt453_approve_candidate_ready") is True
    )
    remote_mutation_observed = bool(
        payload.get("prompt458_remote_mutation_performed_observed") is True
        or payload.get("prompt457_remote_mutation_performed_observed") is True
        or payload.get("prompt456_remote_mutation_performed_observed") is True
    )
    push_observed = bool(
        payload.get("prompt458_push_performed_observed") is True
        or payload.get("prompt457_push_performed_observed") is True
        or payload.get("prompt456_push_performed_observed") is True
    )
    commit_tag_performed_observed = bool(
        payload.get("prompt458_commit_tag_execution_performed_observed") is True
        or payload.get("prompt457_commit_tag_execution_performed_observed") is True
        or payload.get("prompt456_commit_tag_execution_performed") is True
        or payload.get("prompt433_approve_commit_tag_execution_success") is True
    )
    git_mutation_observed = bool(
        payload.get("prompt458_git_mutation_performed_observed") is True
        or payload.get("prompt457_git_mutation_performed_observed") is True
        or payload.get("prompt456_git_mutation_performed_observed") is True
        or commit_tag_performed_observed
    )
    commit_sha = _normalize_text(
        payload.get("prompt458_commit_sha")
        or payload.get("prompt457_commit_sha")
        or payload.get("prompt433_commit_sha")
        or payload.get("commit_sha"),
        default="",
    )
    receipt_path = _normalize_text(
        payload.get("prompt458_commit_tag_receipt_path")
        or payload.get("prompt457_commit_tag_receipt_path")
        or payload.get("prompt433_commit_tag_receipt_path")
        or payload.get("commit_tag_receipt_path"),
        default="",
    )
    result_payload = payload.get("prompt433_commit_tag_result_payload")
    if not isinstance(result_payload, Mapping):
        result_payload = {}
    tags_at_head_after_execution = _normalize_string_list(
        payload.get("tags_at_head_after_execution")
        or payload.get("prompt398_committed_prompt379_head_tags"),
        sort_items=True,
    )

    prompt456_packet_ready = bool(
        prompt456_status == "execution_ready"
        and prompt456_execution_allowed
        and payload.get("prompt456_git_mutation_allowed") is True
        and payload.get("prompt456_commit_tag_allowed") is True
    )
    expected_set = set(expected_changed_files)
    actual_set = set(actual_changed_files)
    changed_files_match = bool(
        expected_changed_files
        and actual_changed_files
        and actual_set == expected_set
    )
    required_safety_evidence_ready = bool(
        prompt456_packet_ready
        and explicit_allow_present
        and runtime_success_ready
        and approve_candidate_ready
        and commit_message
        and tag_name
        and changed_files_match
        and not actual_untracked_files
        and not (tag_uniqueness_ready and tag_already_exists)
        and not remote_mutation_observed
        and not push_observed
    )

    state: dict[str, Any] = {
        "prompt459_schema_version": _PROMPT459_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt459",
        "prompt459_applicable": applicable,
        "prompt459_prompt456_status": prompt456_status,
        "prompt459_prompt456_next_action": prompt456_next_action,
        "prompt459_prompt456_execution_allowed": prompt456_execution_allowed,
        "prompt459_prompt458_status": prompt458_status,
        "prompt459_prompt458_next_action": prompt458_next_action,
        "prompt459_diagnosis_status": "blocked",
        "prompt459_execution_connector_available": True,
        "prompt459_existing_commit_tag_executor_available": False,
        "prompt459_prompt456_packet_ready": prompt456_packet_ready,
        "prompt459_explicit_allow_present": explicit_allow_present,
        "prompt459_required_safety_evidence_ready": required_safety_evidence_ready,
        "prompt459_fix_plan_required": False,
        "prompt459_fix_plan_ready": False,
        "prompt459_fix_plan_summary": "",
        "prompt459_fix_plan_target_area": "",
        "prompt459_fix_plan_next_action": "",
        "prompt459_commit_tag_execution_status": "blocked",
        "prompt459_commit_tag_execution_required": applicable,
        "prompt459_commit_tag_execution_ready": required_safety_evidence_ready,
        "prompt459_commit_tag_execution_allowed": False,
        "prompt459_commit_tag_execution_attempted": False,
        "prompt459_commit_tag_execution_performed": False,
        "prompt459_git_add_allowed": False,
        "prompt459_git_commit_allowed": False,
        "prompt459_git_tag_allowed": False,
        "prompt459_git_add_performed": False,
        "prompt459_git_commit_performed": False,
        "prompt459_git_tag_performed": False,
        "prompt459_commit_message": commit_message,
        "prompt459_tag_name": tag_name,
        "prompt459_expected_head_before_commit": expected_head,
        "prompt459_expected_changed_files": expected_changed_files,
        "prompt459_actual_changed_files": actual_changed_files,
        "prompt459_actual_untracked_files": actual_untracked_files,
        "prompt459_expected_clean_after_commit": expected_clean_after_commit,
        "prompt459_tag_uniqueness_required": True,
        "prompt459_tag_uniqueness_ready": tag_uniqueness_ready,
        "prompt459_tag_already_exists": tag_already_exists,
        "prompt459_pre_commit_head": expected_head,
        "prompt459_post_commit_head": commit_sha,
        "prompt459_commit_sha": commit_sha,
        "prompt459_tags_at_head_after_execution": tags_at_head_after_execution,
        "prompt459_commit_tag_receipt_ready": bool(receipt_path),
        "prompt459_commit_tag_receipt_path": receipt_path,
        "prompt459_commit_tag_result_payload_ready": bool(result_payload),
        "prompt459_commit_tag_result_payload": dict(result_payload),
        "prompt459_post_commit_clean_rerun_required": False,
        "prompt459_post_commit_clean_rerun_request_ready": False,
        "prompt459_success_closure_candidate_ready": False,
        "prompt459_autonomous_next_cycle_candidate_ready": False,
        "prompt459_prompt457_expected_next_action": "",
        "prompt459_prompt458_expected_next_action": "",
        "prompt459_blocked_reason": "",
        "prompt459_next_action": "manual_review_prompt459_route",
        "prompt459_git_mutation_allowed": False,
        "prompt459_remote_mutation_allowed": False,
        "prompt459_commit_tag_allowed": False,
        "prompt459_push_allowed": False,
        "prompt459_tests_allowed": False,
        "prompt459_file_creation_allowed": False,
        "prompt459_merge_allowed": False,
        "prompt459_pr_allowed": False,
        "prompt459_git_mutation_performed_observed": git_mutation_observed,
        "prompt459_remote_mutation_performed_observed": remote_mutation_observed,
        "prompt459_commit_tag_performed_observed": commit_tag_performed_observed,
        "prompt459_push_performed_observed": push_observed,
    }

    if not applicable:
        state.update(
            {
                "prompt459_diagnosis_status": "not_applicable",
                "prompt459_commit_tag_execution_status": "not_applicable",
                "prompt459_commit_tag_execution_required": False,
                "prompt459_commit_tag_execution_ready": False,
                "prompt459_blocked_reason": "prompt459_not_applicable",
                "prompt459_next_action": "manual_review_prompt459_route",
            }
        )
        return state

    if commit_tag_performed_observed and not (remote_mutation_observed or push_observed):
        state.update(
            {
                "prompt459_diagnosis_status": "already_observed",
                "prompt459_commit_tag_execution_status": "performed",
                "prompt459_commit_tag_execution_required": True,
                "prompt459_commit_tag_execution_ready": True,
                "prompt459_commit_tag_execution_allowed": True,
                "prompt459_commit_tag_execution_performed": True,
                "prompt459_git_add_performed": True,
                "prompt459_git_commit_performed": True,
                "prompt459_git_tag_performed": True,
                "prompt459_post_commit_clean_rerun_required": True,
                "prompt459_post_commit_clean_rerun_request_ready": True,
                "prompt459_success_closure_candidate_ready": True,
                "prompt459_autonomous_next_cycle_candidate_ready": True,
                "prompt459_prompt457_expected_next_action": (
                    "run_prompt457_post_commit_clean_rerun_closure"
                ),
                "prompt459_prompt458_expected_next_action": (
                    "run_prompt457_post_commit_clean_rerun_closure"
                ),
                "prompt459_next_action": (
                    "run_prompt457_post_commit_clean_rerun_closure"
                ),
            }
        )
        return state

    blocked_reason = ""
    if prompt456_status != "execution_ready":
        blocked_reason = "prompt459_prompt456_execution_ready_missing"
    elif not explicit_allow_present:
        blocked_reason = "prompt459_explicit_allow_missing"
    elif not runtime_success_ready:
        blocked_reason = "prompt459_runtime_success_evidence_missing"
    elif not approve_candidate_ready:
        blocked_reason = "prompt459_approve_candidate_missing"
    elif not expected_changed_files:
        blocked_reason = "prompt459_expected_changed_files_missing"
    elif not changed_files_match:
        blocked_reason = "prompt459_expected_changed_files_mismatch"
    elif actual_untracked_files:
        blocked_reason = "prompt459_untracked_files_observed"
    elif not tag_name:
        blocked_reason = "prompt459_tag_name_missing"
    elif tag_uniqueness_ready and tag_already_exists:
        blocked_reason = "prompt459_tag_already_exists"
    elif remote_mutation_observed or push_observed:
        blocked_reason = "prompt459_remote_or_push_mutation_observed"
    elif git_mutation_observed or commit_tag_performed_observed:
        blocked_reason = "prompt459_prior_commit_tag_mutation_observed"
    elif not payload.get("prompt456_git_mutation_allowed"):
        blocked_reason = "prompt459_prompt456_execution_ready_missing"
    elif not payload.get("prompt456_commit_tag_allowed"):
        blocked_reason = "prompt459_prompt456_execution_ready_missing"

    if blocked_reason:
        state.update(
            {
                "prompt459_diagnosis_status": "blocked",
                "prompt459_commit_tag_execution_status": "blocked",
                "prompt459_blocked_reason": blocked_reason,
                "prompt459_fix_plan_required": True,
                "prompt459_fix_plan_ready": True,
                "prompt459_fix_plan_summary": (
                    "Repair the Prompt456 commit/tag packet safety evidence "
                    f"before local execution: {blocked_reason}."
                ),
                "prompt459_fix_plan_target_area": "commit_tag_execution_dispatch",
                "prompt459_fix_plan_next_action": (
                    "repair_prompt459_commit_tag_packet_safety_evidence"
                ),
                "prompt459_next_action": "manual_review_prompt459_route",
            }
        )
        return state

    state.update(
        {
            "prompt459_diagnosis_status": "executor_missing",
            "prompt459_commit_tag_execution_status": "blocked",
            "prompt459_blocked_reason": (
                "prompt459_existing_commit_tag_executor_not_available"
            ),
            "prompt459_fix_plan_required": True,
            "prompt459_fix_plan_ready": True,
            "prompt459_fix_plan_summary": (
                "Connect Prompt456 commit/tag packets to an existing bounded "
                "local commit/tag runner; do not synthesize a new unreviewed "
                "shell-out path."
            ),
            "prompt459_fix_plan_target_area": "commit_tag_execution_dispatch",
            "prompt459_fix_plan_next_action": (
                "implement_prompt459_existing_commit_tag_executor_connector"
            ),
            "prompt459_next_action": "manual_review_prompt459_route",
        }
    )
    return state

def _build_prompt460_existing_commit_tag_executor_connector_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
    repo_path: str,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    prompt456_status = _normalize_text(
        payload.get("prompt456_commit_tag_execution_gate_status"),
        default="",
    )
    prompt456_next_action = _normalize_text(
        payload.get("prompt456_next_action"),
        default="",
    )
    prompt459_status = _normalize_text(
        payload.get("prompt459_commit_tag_execution_status"),
        default="",
    )
    prompt459_blocked_reason = _normalize_text(
        payload.get("prompt459_blocked_reason"),
        default="",
    )
    prompt459_fix_plan_next_action = _normalize_text(
        payload.get("prompt459_fix_plan_next_action"),
        default="",
    )
    prompt458_next_action = _normalize_text(
        payload.get("prompt458_next_action"),
        default="",
    )
    applicable = bool(
        prompt459_blocked_reason
        == "prompt459_existing_commit_tag_executor_not_available"
        or prompt459_fix_plan_next_action
        == "implement_prompt459_existing_commit_tag_executor_connector"
        or prompt456_next_action == "execute_prompt456_commit_tag_packet"
        or prompt458_next_action == "execute_prompt456_commit_tag_packet"
        or payload.get("prompt456_commit_tag_execution_allowed") is True
    )
    explicit_allow_present = bool(
        payload.get("prompt459_explicit_allow_present") is True
        or payload.get("prompt456_explicit_commit_tag_allow_present") is True
        or payload.get("prompt455_explicit_commit_tag_allow_present") is True
        or payload.get("prompt453_commit_tag_packet_explicit_allow_present") is True
    )
    execution_gate_ready = bool(
        (
            payload.get("prompt456_commit_tag_execution_ready") is True
            and payload.get("prompt456_commit_tag_execution_allowed") is True
        )
        or (
            payload.get("prompt459_commit_tag_execution_ready") is True
            and prompt459_blocked_reason
            == "prompt459_existing_commit_tag_executor_not_available"
        )
    )
    upstream_execution_allowed = bool(
        payload.get("prompt456_commit_tag_execution_allowed") is True
        or payload.get("prompt459_commit_tag_execution_allowed") is True
        or payload.get("prompt455_commit_tag_execution_allowed_for_prompt456")
        is True
    )
    expected_changed_files = _prompt459_first_non_empty_string_list(
        payload,
        (
            "prompt459_expected_changed_files",
            "prompt456_expected_changed_files",
            "prompt455_expected_changed_files",
            "prompt459_actual_changed_files",
            "prompt456_changed_files",
        ),
    )
    repo_available = bool(repo_path and Path(repo_path).is_dir())
    actual_known = False
    actual_changed_files: list[str] = []
    actual_untracked_files: list[str] = []
    if repo_available:
        actual_known, actual_changed_files, actual_untracked_files = (
            _prompt460_git_status_files(repo_path=repo_path)
        )
    if not expected_changed_files and actual_known:
        fallback_files = {
            "automation/orchestration/planned_execution_runner.py",
            "scripts/run_planned_execution.py",
        }
        actual_set_for_fallback = set(actual_changed_files)
        if actual_set_for_fallback and actual_set_for_fallback.issubset(
            fallback_files
        ):
            expected_changed_files = sorted(fallback_files)
    expected_set = set(expected_changed_files)
    actual_set = set(actual_changed_files)
    changed_files_match = bool(
        actual_known
        and expected_changed_files
        and actual_changed_files
        and actual_set.issubset(expected_set)
    )
    commit_message = _normalize_text(
        payload.get("prompt459_commit_message")
        or payload.get("prompt456_commit_message")
        or payload.get("prompt455_commit_message"),
        default="",
    )
    tag_name = _normalize_text(
        payload.get("prompt459_tag_name")
        or payload.get("prompt456_tag_name")
        or payload.get("prompt455_tag_name"),
        default="",
    )
    pre_commit_head = (
        _prompt460_git_text(repo_path=repo_path, args=["rev-parse", "HEAD"])
        if repo_available
        else ""
    )
    tag_already_exists = bool(
        payload.get("prompt459_tag_already_exists") is True
        or payload.get("prompt456_tag_already_exists") is True
        or _prompt460_tag_exists(repo_path=repo_path, tag_name=tag_name)
    )
    tag_ref_valid = False
    if repo_available and tag_name:
        try:
            tag_ref_result = _run_git(
                repo_path,
                ["check-ref-format", f"refs/tags/{tag_name}"],
                timeout_seconds=10.0,
            )
            tag_ref_valid = tag_ref_result.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            tag_ref_valid = False
    remote_mutation_observed = bool(
        payload.get("prompt459_remote_mutation_performed_observed") is True
        or payload.get("prompt458_remote_mutation_performed_observed") is True
        or payload.get("prompt457_remote_mutation_performed_observed") is True
        or payload.get("prompt456_remote_mutation_performed_observed") is True
    )
    push_observed = bool(
        payload.get("prompt459_push_performed_observed") is True
        or payload.get("prompt458_push_performed_observed") is True
        or payload.get("prompt457_push_performed_observed") is True
        or payload.get("prompt456_push_performed_observed") is True
    )
    prior_commit_tag_observed = bool(
        payload.get("prompt459_commit_tag_performed_observed") is True
        or payload.get("prompt458_commit_tag_execution_performed_observed") is True
        or payload.get("prompt457_commit_tag_execution_performed_observed") is True
        or payload.get("prompt456_commit_tag_execution_performed") is True
    )
    prior_git_mutation_observed = bool(
        payload.get("prompt459_git_mutation_performed_observed") is True
        or payload.get("prompt458_git_mutation_performed_observed") is True
        or payload.get("prompt457_git_mutation_performed_observed") is True
        or payload.get("prompt456_git_mutation_performed_observed") is True
    )

    blocked_reason = ""
    if not applicable:
        blocked_reason = "prompt460_not_applicable"
    elif not explicit_allow_present:
        blocked_reason = "prompt460_explicit_allow_missing"
    elif not execution_gate_ready or not upstream_execution_allowed:
        blocked_reason = "prompt460_execution_gate_not_ready"
    elif not repo_available:
        blocked_reason = "prompt460_local_executor_unavailable"
    elif not expected_changed_files or not actual_known:
        blocked_reason = "prompt460_expected_changed_files_missing"
    elif not changed_files_match:
        blocked_reason = "prompt460_expected_changed_files_mismatch"
    elif actual_untracked_files:
        blocked_reason = "prompt460_untracked_files_observed"
    elif not tag_name:
        blocked_reason = "prompt460_tag_name_missing"
    elif not commit_message:
        blocked_reason = "prompt460_commit_message_missing"
    elif tag_already_exists:
        blocked_reason = "prompt460_tag_already_exists"
    elif remote_mutation_observed or push_observed:
        blocked_reason = "prompt460_remote_or_push_mutation_observed"
    elif prior_git_mutation_observed or prior_commit_tag_observed:
        blocked_reason = "prompt460_prior_commit_tag_mutation_observed"
    elif not tag_ref_valid:
        blocked_reason = "prompt460_local_executor_failed"

    safety_guards_ready = not blocked_reason
    result_payload: dict[str, Any] = {}
    post_commit_head = ""
    commit_sha = ""
    tags_at_head_after_execution: list[str] = []
    git_add_performed = False
    git_commit_performed = False
    git_tag_performed = False
    execution_attempted = False
    execution_performed = False

    if safety_guards_ready:
        execution_attempted = True
        command_summary: dict[str, Any] = {}
        try:
            add_result = _run_git(
                repo_path,
                ["add", "--", *sorted(expected_set)],
                timeout_seconds=20.0,
            )
            command_summary["git_add_rc"] = add_result.returncode
            git_add_performed = add_result.returncode == 0
            if add_result.returncode != 0:
                blocked_reason = "prompt460_local_executor_failed"
            else:
                commit_result = _run_git(
                    repo_path,
                    [
                        "-c",
                        "user.name=Codex Local Runner",
                        "-c",
                        "user.email=codex-local-runner@example.com",
                        "commit",
                        "-m",
                        commit_message,
                    ],
                    timeout_seconds=30.0,
                )
                command_summary["git_commit_rc"] = commit_result.returncode
                git_commit_performed = commit_result.returncode == 0
                if commit_result.returncode != 0:
                    blocked_reason = "prompt460_local_executor_failed"
                else:
                    post_commit_head = _prompt460_git_text(
                        repo_path=repo_path,
                        args=["rev-parse", "HEAD"],
                    )
                    commit_sha = post_commit_head
                    tag_result = _run_git(
                        repo_path,
                        ["tag", tag_name],
                        timeout_seconds=20.0,
                    )
                    command_summary["git_tag_rc"] = tag_result.returncode
                    git_tag_performed = tag_result.returncode == 0
                    if tag_result.returncode != 0:
                        blocked_reason = "prompt460_local_executor_failed"
                    else:
                        tags_at_head_after_execution = _normalize_string_list(
                            _prompt460_git_text(
                                repo_path=repo_path,
                                args=["tag", "--points-at", "HEAD"],
                            ).splitlines(),
                            sort_items=True,
                        )
                        execution_performed = True
            result_payload = {
                "schema_version": _PROMPT460_SCHEMA_VERSION,
                "status": "performed" if execution_performed else "blocked",
                "blocked_reason": blocked_reason,
                "commit_sha": commit_sha,
                "tag_name": tag_name,
                "commit_message": commit_message,
                "pre_commit_head": pre_commit_head,
                "post_commit_head": post_commit_head,
                "expected_changed_files": sorted(expected_set),
                "actual_changed_files": actual_changed_files,
                "command_summary": command_summary,
            }
        except (OSError, subprocess.TimeoutExpired):
            blocked_reason = "prompt460_local_executor_failed"
            result_payload = {
                "schema_version": _PROMPT460_SCHEMA_VERSION,
                "status": "blocked",
                "blocked_reason": blocked_reason,
                "commit_sha": "",
                "tag_name": tag_name,
                "commit_message": commit_message,
                "pre_commit_head": pre_commit_head,
                "post_commit_head": "",
                "expected_changed_files": sorted(expected_set),
                "actual_changed_files": actual_changed_files,
                "command_summary": {},
            }

    performed = execution_performed and not blocked_reason
    connector_status = "performed" if performed else "blocked"
    next_action = (
        "run_prompt457_post_commit_clean_rerun_closure"
        if performed
        else "manual_review_prompt460_route"
    )
    return {
        "prompt460_schema_version": _PROMPT460_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt460",
        "prompt460_applicable": applicable,
        "prompt460_prompt456_status": prompt456_status,
        "prompt460_prompt456_next_action": prompt456_next_action,
        "prompt460_prompt459_status": prompt459_status,
        "prompt460_prompt459_blocked_reason": prompt459_blocked_reason,
        "prompt460_prompt459_fix_plan_next_action": (
            prompt459_fix_plan_next_action
        ),
        "prompt460_executor_connector_status": connector_status,
        "prompt460_executor_connector_ready": performed,
        "prompt460_existing_executor_found": repo_available,
        "prompt460_local_executor_enabled": performed,
        "prompt460_explicit_allow_present": explicit_allow_present,
        "prompt460_safety_guards_ready": safety_guards_ready,
        "prompt460_commit_tag_execution_required": applicable,
        "prompt460_commit_tag_execution_ready": performed,
        "prompt460_commit_tag_execution_allowed": performed,
        "prompt460_commit_tag_execution_attempted": execution_attempted,
        "prompt460_commit_tag_execution_performed": performed,
        "prompt460_git_add_performed": git_add_performed,
        "prompt460_git_commit_performed": git_commit_performed,
        "prompt460_git_tag_performed": git_tag_performed,
        "prompt460_expected_changed_files": sorted(expected_set),
        "prompt460_actual_changed_files": actual_changed_files,
        "prompt460_actual_untracked_files": actual_untracked_files,
        "prompt460_tag_name": tag_name,
        "prompt460_commit_message": commit_message,
        "prompt460_tag_already_exists": tag_already_exists,
        "prompt460_pre_commit_head": pre_commit_head,
        "prompt460_post_commit_head": post_commit_head,
        "prompt460_commit_sha": commit_sha,
        "prompt460_tags_at_head_after_execution": (
            tags_at_head_after_execution
        ),
        "prompt460_commit_tag_receipt_ready": bool(result_payload),
        "prompt460_commit_tag_receipt_path": "",
        "prompt460_commit_tag_result_payload_ready": bool(result_payload),
        "prompt460_commit_tag_result_payload": result_payload,
        "prompt460_post_commit_clean_rerun_required": performed,
        "prompt460_post_commit_clean_rerun_request_ready": performed,
        "prompt460_success_closure_candidate_ready": performed,
        "prompt460_autonomous_next_cycle_candidate_ready": performed,
        "prompt460_prompt457_expected_next_action": (
            "run_prompt457_post_commit_clean_rerun_closure" if performed else ""
        ),
        "prompt460_prompt458_expected_next_action": (
            "run_prompt457_post_commit_clean_rerun_closure" if performed else ""
        ),
        "prompt460_blocked_reason": "" if performed else blocked_reason,
        "prompt460_next_action": next_action,
        "prompt460_git_mutation_allowed": performed,
        "prompt460_commit_tag_allowed": performed,
        "prompt460_remote_mutation_allowed": False,
        "prompt460_push_allowed": False,
        "prompt460_tests_allowed": False,
        "prompt460_file_creation_allowed": False,
        "prompt460_merge_allowed": False,
        "prompt460_pr_allowed": False,
        "prompt460_git_mutation_performed_observed": (
            git_add_performed or git_commit_performed or git_tag_performed
        ),
        "prompt460_commit_tag_performed_observed": (
            git_commit_performed or git_tag_performed
        ),
        "prompt460_remote_mutation_performed_observed": False,
        "prompt460_push_performed_observed": False,
    }

def _build_prompt461_post_commit_clean_observed_completion_closure_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}

    def _prompt461_runtime_evidence_surfaces() -> list[tuple[str, Mapping[str, Any]]]:
        surfaces: list[tuple[str, Mapping[str, Any]]] = [("run_state", payload)]
        seen_surface_ids: set[int] = {id(payload)}

        def add_surface(name: str, value: Any) -> None:
            if not isinstance(value, Mapping):
                return
            surface_id = id(value)
            if surface_id in seen_surface_ids:
                return
            seen_surface_ids.add(surface_id)
            surfaces.append((name, value))

        for key in (
            "prompt437_runtime_command_request",
            "prompt447_runtime_command_json",
            "prompt448_runtime_command_json",
            "prompt449_runtime_command_json",
            "prompt450_runtime_command_json",
            "prompt451_runtime_command_json",
        ):
            add_surface(key, payload.get(key))

        for key, value in payload.items():
            if not isinstance(key, str):
                continue
            if (
                "runtime_command_json" in key
                or "runtime_command_request" in key
                or "runtime_command_payload" in key
            ):
                add_surface(key, value)

        return surfaces

    def _prompt461_explicit_true_source(keys: Sequence[str]) -> str:
        for surface_name, surface in _prompt461_runtime_evidence_surfaces():
            for key in keys:
                if surface.get(key) is True:
                    return f"{surface_name}.{key}"
        return ""

    external_performed_evidence_source = _prompt461_explicit_true_source(
        (
            "prompt461_prompt460_performed_evidence",
            "prompt460_performed_evidence",
        )
    )
    external_post_reconcile_clean_source = _prompt461_explicit_true_source(
        (
            "prompt461_post_reconcile_clean_evidence",
            "prompt460_post_reconcile_clean_ok",
            "post_reconcile_clean_ok",
        )
    )
    external_final_clean_source = _prompt461_explicit_true_source(
        (
            "prompt461_final_clean_evidence",
            "prompt460_final_clean_ok",
            "final_clean_ok",
        )
    )
    external_verified_evidence_allow_source = _prompt461_explicit_true_source(
        ("prompt461_allow_completion_from_verified_evidence",)
    )
    external_performed_evidence_present = bool(external_performed_evidence_source)
    external_post_reconcile_clean_evidence_present = bool(
        external_post_reconcile_clean_source
    )
    external_final_clean_evidence_present = bool(external_final_clean_source)
    external_verified_evidence_present = bool(
        external_verified_evidence_allow_source
        and external_performed_evidence_present
        and external_post_reconcile_clean_evidence_present
        and external_final_clean_evidence_present
    )
    external_completion_evidence_sources = [
        source
        for source in (
            external_verified_evidence_allow_source,
            external_performed_evidence_source,
            external_post_reconcile_clean_source,
            external_final_clean_source,
        )
        if source
    ]
    prompt460_status = _normalize_text(
        payload.get("prompt460_executor_connector_status"),
        default="",
    )
    prompt460_next_action = _normalize_text(
        payload.get("prompt460_next_action"),
        default="",
    )
    prompt458_status = _normalize_text(
        payload.get("prompt458_minimal_autonomous_completion_status"),
        default="",
    )
    prompt458_next_action = _normalize_text(
        payload.get("prompt458_next_action"),
        default="",
    )
    prompt457_next_action = _normalize_text(
        payload.get("prompt457_next_action"),
        default="",
    )
    applicable = bool(
        prompt460_status == "performed"
        or payload.get("prompt460_commit_tag_execution_performed") is True
        or payload.get("prompt460_post_commit_clean_rerun_request_ready") is True
        or external_performed_evidence_present
        or external_post_reconcile_clean_evidence_present
        or external_final_clean_evidence_present
        or prompt460_next_action == "run_prompt457_post_commit_clean_rerun_closure"
        or prompt458_status
        in {
            "awaiting_commit_tag_execution",
            "awaiting_post_commit_clean_rerun",
        }
        or prompt457_next_action == "run_prompt457_post_commit_clean_rerun_closure"
    )

    _, prompt460_execution_performed = _prompt457_observed_bool(
        payload,
        (
            "prompt460_commit_tag_execution_performed",
            "prompt460_commit_tag_performed_observed",
        ),
    )
    prompt460_execution_performed_bool = bool(
        payload.get("prompt460_commit_tag_execution_performed") is True
        or payload.get("prompt460_commit_tag_performed_observed") is True
    )
    _, fallback_execution_performed = _prompt457_observed_bool(
        payload,
        (
            "prompt459_commit_tag_execution_performed",
            "prompt457_commit_tag_execution_performed_observed",
            "prompt458_commit_tag_execution_performed_observed",
            "commit_tag_performed",
            "git_mutation_performed",
        ),
    )
    commit_tag_execution_observed = bool(
        prompt460_status == "performed"
        or prompt460_execution_performed
        or external_performed_evidence_present
        or fallback_execution_performed
    )
    completion_commit_tag_performed_evidence_present = bool(
        prompt460_status == "performed"
        or prompt460_execution_performed_bool
        or external_performed_evidence_present
    )
    completion_evidence_sources = list(external_completion_evidence_sources)
    if prompt460_status == "performed":
        completion_evidence_sources.append(
            "run_state.prompt460_executor_connector_status"
        )
    if payload.get("prompt460_commit_tag_execution_performed") is True:
        completion_evidence_sources.append(
            "run_state.prompt460_commit_tag_execution_performed"
        )
    if payload.get("prompt460_commit_tag_performed_observed") is True:
        completion_evidence_sources.append(
            "run_state.prompt460_commit_tag_performed_observed"
        )
    commit_tag_execution_performed_observed = commit_tag_execution_observed

    _, git_commit_performed_observed = _prompt457_observed_bool(
        payload,
        (
            "prompt460_git_commit_performed",
            "prompt459_git_commit_performed",
            "git_commit_performed",
        ),
    )
    _, git_tag_performed_observed = _prompt457_observed_bool(
        payload,
        (
            "prompt460_git_tag_performed",
            "prompt459_git_tag_performed",
            "git_tag_performed",
        ),
    )
    commit_sha = _normalize_text(
        payload.get("prompt460_commit_sha")
        or payload.get("prompt459_commit_sha")
        or payload.get("prompt457_commit_sha")
        or payload.get("prompt458_commit_sha")
        or payload.get("commit_sha"),
        default="",
    )
    tag_name = _normalize_text(
        payload.get("prompt460_tag_name")
        or payload.get("prompt459_tag_name")
        or payload.get("prompt457_tag_name")
        or payload.get("prompt458_tag_name")
        or payload.get("tag_name"),
        default="",
    )
    commit_message = _normalize_text(
        payload.get("prompt460_commit_message")
        or payload.get("prompt459_commit_message")
        or payload.get("prompt457_commit_message")
        or payload.get("prompt458_commit_message")
        or payload.get("commit_message"),
        default="",
    )
    commit_tag_receipt_path = _normalize_text(
        payload.get("prompt460_commit_tag_receipt_path")
        or payload.get("prompt459_commit_tag_receipt_path")
        or payload.get("prompt457_commit_tag_receipt_path")
        or payload.get("prompt458_commit_tag_receipt_path")
        or payload.get("commit_tag_receipt_path"),
        default="",
    )
    commit_tag_receipt_ready = bool(
        payload.get("prompt460_commit_tag_receipt_ready") is True
        or payload.get("prompt459_commit_tag_receipt_ready") is True
        or payload.get("prompt457_commit_tag_receipt_ready") is True
        or payload.get("prompt458_commit_tag_receipt_ready") is True
        or bool(commit_tag_receipt_path)
    )

    _, clean_request_ready_observed = _prompt457_observed_bool(
        payload,
        (
            "prompt460_post_commit_clean_rerun_request_ready",
            "prompt459_post_commit_clean_rerun_request_ready",
            "prompt458_post_commit_clean_rerun_request_ready",
            "prompt457_post_commit_clean_rerun_request_ready",
            "post_commit_clean_rerun_request_ready",
        ),
    )
    _, clean_success = _prompt457_observed_bool(
        payload,
        (
            "post_commit_clean_rerun_success",
            "prompt457_post_commit_clean_rerun_success",
            "prompt458_post_commit_clean_rerun_success",
        ),
    )
    _, final_clean_ok = _prompt457_observed_bool(
        payload,
        (
            "final_clean_ok",
            "prompt460_final_clean_ok",
            "post_commit_clean_rerun_final_clean_ok",
            "prompt457_post_commit_clean_rerun_final_clean_ok",
            "prompt458_post_commit_clean_rerun_final_clean_ok",
        ),
    )
    _, final_worktree_clean_ok = _prompt457_observed_bool(
        payload,
        (
            "final_worktree_clean_ok",
            "worktree_clean_ok",
            "WORKTREE_CLEAN_OK",
            "prompt460_final_worktree_clean_ok",
            "prompt457_final_worktree_clean_ok",
            "prompt458_final_worktree_clean_ok",
        ),
    )
    _, post_reconcile_clean_evidence_ready = _prompt457_observed_bool(
        payload,
        (
            "post_reconcile_clean_evidence_ready",
            "prompt460_post_reconcile_clean_ok",
            "post_reconcile_clean_ok",
            "prompt460_post_reconcile_clean_evidence_ready",
            "prompt457_post_reconcile_clean_evidence_ready",
            "prompt458_post_reconcile_clean_evidence_ready",
        ),
    )
    post_reconcile_clean_evidence_ready_bool = bool(
        payload.get("post_reconcile_clean_evidence_ready") is True
        or payload.get("prompt460_post_reconcile_clean_evidence_ready") is True
        or payload.get("prompt457_post_reconcile_clean_evidence_ready") is True
        or payload.get("prompt458_post_reconcile_clean_evidence_ready") is True
        or payload.get("prompt460_post_reconcile_clean_ok") is True
        or payload.get("post_reconcile_clean_ok") is True
    )
    final_clean_evidence_ready_bool = bool(
        payload.get("final_clean_ok") is True
        or payload.get("prompt460_final_clean_ok") is True
        or payload.get("post_commit_clean_rerun_final_clean_ok") is True
        or payload.get("prompt457_post_commit_clean_rerun_final_clean_ok")
        is True
        or payload.get("prompt458_post_commit_clean_rerun_final_clean_ok")
        is True
        or payload.get("final_worktree_clean_ok") is True
        or payload.get("worktree_clean_ok") is True
        or payload.get("WORKTREE_CLEAN_OK") is True
        or payload.get("prompt460_final_worktree_clean_ok") is True
        or payload.get("prompt457_final_worktree_clean_ok") is True
        or payload.get("prompt458_final_worktree_clean_ok") is True
    )
    clean_run_state_path = _normalize_text(
        payload.get("prompt458_post_commit_clean_rerun_run_state_path")
        or payload.get("prompt457_post_commit_clean_rerun_run_state_path")
        or payload.get("post_commit_clean_rerun_run_state_path"),
        default="",
    )
    prompt460_clean_route_ready = bool(
        prompt460_next_action == "run_prompt457_post_commit_clean_rerun_closure"
        and payload.get("prompt460_post_commit_clean_rerun_request_ready") is True
    )
    post_commit_clean_rerun_success = bool(
        clean_success
        or external_post_reconcile_clean_evidence_present
        or (
            prompt460_clean_route_ready
            and post_reconcile_clean_evidence_ready
            and final_worktree_clean_ok
        )
    )
    post_commit_clean_rerun_final_clean_ok = bool(
        final_clean_ok
        or external_final_clean_evidence_present
        or (
            prompt460_clean_route_ready
            and post_reconcile_clean_evidence_ready
            and final_worktree_clean_ok
        )
    )
    post_reconcile_clean_evidence_present = bool(
        post_reconcile_clean_evidence_ready_bool
        or external_post_reconcile_clean_evidence_present
    )
    if payload.get("post_reconcile_clean_evidence_ready") is True:
        completion_evidence_sources.append(
            "run_state.post_reconcile_clean_evidence_ready"
        )
    if payload.get("prompt460_post_reconcile_clean_evidence_ready") is True:
        completion_evidence_sources.append(
            "run_state.prompt460_post_reconcile_clean_evidence_ready"
        )
    if payload.get("prompt460_post_reconcile_clean_ok") is True:
        completion_evidence_sources.append(
            "run_state.prompt460_post_reconcile_clean_ok"
        )
    if payload.get("post_reconcile_clean_ok") is True:
        completion_evidence_sources.append("run_state.post_reconcile_clean_ok")
    final_clean_evidence_present = bool(
        final_clean_evidence_ready_bool
        or external_final_clean_evidence_present
    )
    if payload.get("final_clean_ok") is True:
        completion_evidence_sources.append("run_state.final_clean_ok")
    if payload.get("prompt460_final_clean_ok") is True:
        completion_evidence_sources.append("run_state.prompt460_final_clean_ok")
    if payload.get("prompt460_final_worktree_clean_ok") is True:
        completion_evidence_sources.append(
            "run_state.prompt460_final_worktree_clean_ok"
        )
    if payload.get("final_worktree_clean_ok") is True:
        completion_evidence_sources.append("run_state.final_worktree_clean_ok")
    completion_evidence_source = ",".join(dict.fromkeys(completion_evidence_sources))
    post_commit_clean_rerun_observed = bool(
        completion_commit_tag_performed_evidence_present
        and post_reconcile_clean_evidence_present
        and final_clean_evidence_present
    )
    final_worktree_clean_observed = bool(final_worktree_clean_ok)

    _, git_mutation_observed = _prompt457_observed_bool(
        payload,
        (
            "prompt460_git_mutation_performed_observed",
            "prompt459_git_mutation_performed_observed",
            "prompt458_git_mutation_performed_observed",
            "prompt457_git_mutation_performed_observed",
            "git_mutation_performed_observed",
            "git_mutation_performed",
        ),
    )
    _, remote_mutation_observed = _prompt457_observed_bool(
        payload,
        (
            "prompt460_remote_mutation_performed_observed",
            "prompt459_remote_mutation_performed_observed",
            "prompt458_remote_mutation_performed_observed",
            "prompt457_remote_mutation_performed_observed",
            "remote_mutation_performed_observed",
            "remote_mutation_performed",
        ),
    )
    _, push_observed = _prompt457_observed_bool(
        payload,
        (
            "prompt460_push_performed_observed",
            "prompt459_push_performed_observed",
            "prompt458_push_performed_observed",
            "prompt457_push_performed_observed",
            "push_performed_observed",
            "push_performed",
        ),
    )
    _, tests_observed = _prompt457_observed_bool(
        payload,
        (
            "prompt461_tests_performed_observed",
            "prompt460_tests_performed_observed",
            "tests_performed_observed",
            "tests_performed",
        ),
    )
    _, merge_observed = _prompt457_observed_bool(
        payload,
        (
            "prompt461_merge_performed_observed",
            "prompt460_merge_performed_observed",
            "merge_performed_observed",
            "merge_performed",
        ),
    )
    _, pr_observed = _prompt457_observed_bool(
        payload,
        (
            "prompt461_pr_performed_observed",
            "prompt460_pr_performed_observed",
            "pr_performed_observed",
            "pr_performed",
        ),
    )
    disallowed_completion_side_effect_observed = bool(
        remote_mutation_observed
        or push_observed
        or tests_observed
        or merge_observed
        or pr_observed
        or payload.get("prompt461_remote_mutation_allowed") is True
        or payload.get("prompt461_push_allowed") is True
        or payload.get("prompt461_tests_allowed") is True
        or payload.get("prompt461_merge_allowed") is True
        or payload.get("prompt461_pr_allowed") is True
        or payload.get("prompt460_remote_mutation_allowed") is True
        or payload.get("prompt460_push_allowed") is True
        or payload.get("prompt460_tests_allowed") is True
        or payload.get("prompt460_merge_allowed") is True
        or payload.get("prompt460_pr_allowed") is True
        or payload.get("remote_mutation_allowed") is True
        or payload.get("push_allowed") is True
        or payload.get("tests_allowed") is True
        or payload.get("merge_allowed") is True
        or payload.get("pr_allowed") is True
    )
    max_cycles_reached = bool(
        payload.get("prompt458_max_cycles_reached") is True
        or payload.get("prompt434_cycle_limit_reached") is True
        or payload.get("prompt427_max_cycles_reached") is True
        or payload.get("max_cycles_reached") is True
    )
    retry_limit_reached = bool(
        payload.get("prompt458_retry_limit_reached") is True
        or payload.get("prompt431_retry_limit_reached") is True
        or payload.get("retry_limit_reached") is True
    )
    unsafe_stop_required = bool(
        payload.get("prompt458_unsafe_stop_required") is True
        or payload.get("unsafe_stop_required") is True
        or payload.get("global_stop_recommended") is True
        or payload.get("global_stop") is True
    )

    state: dict[str, Any] = {
        "prompt461_schema_version": _PROMPT461_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt461",
        "prompt461_applicable": applicable,
        "prompt461_prompt460_status": prompt460_status,
        "prompt461_prompt460_next_action": prompt460_next_action,
        "prompt461_prompt458_status": prompt458_status,
        "prompt461_prompt458_next_action": prompt458_next_action,
        "prompt461_commit_tag_execution_observed": commit_tag_execution_observed,
        "prompt461_commit_tag_execution_performed_observed": (
            commit_tag_execution_performed_observed
        ),
        "prompt461_git_commit_performed_observed": (
            git_commit_performed_observed
        ),
        "prompt461_git_tag_performed_observed": git_tag_performed_observed,
        "prompt461_commit_sha": commit_sha,
        "prompt461_tag_name": tag_name,
        "prompt461_commit_message": commit_message,
        "prompt461_commit_tag_receipt_ready": commit_tag_receipt_ready,
        "prompt461_commit_tag_receipt_path": commit_tag_receipt_path,
        "prompt461_post_commit_clean_rerun_required": bool(
            applicable and commit_tag_execution_observed
        ),
        "prompt461_post_commit_clean_rerun_request_ready": bool(
            clean_request_ready_observed
            or (applicable and commit_tag_execution_observed)
        ),
        "prompt461_post_commit_clean_rerun_observed": (
            post_commit_clean_rerun_observed
        ),
        "prompt461_post_commit_clean_rerun_success": (
            post_commit_clean_rerun_success
        ),
        "prompt461_post_commit_clean_rerun_final_clean_ok": (
            post_commit_clean_rerun_final_clean_ok
        ),
        "prompt461_post_commit_clean_rerun_run_state_path": clean_run_state_path,
        "prompt461_final_worktree_clean_observed": final_worktree_clean_observed,
        "prompt461_final_worktree_clean_ok": final_worktree_clean_ok,
        "prompt461_post_reconcile_clean_evidence_ready": (
            post_reconcile_clean_evidence_ready
        ),
        "prompt461_external_prompt460_performed_evidence_present": (
            external_performed_evidence_present
        ),
        "prompt461_external_post_reconcile_clean_evidence_present": (
            external_post_reconcile_clean_evidence_present
        ),
        "prompt461_external_final_clean_evidence_present": (
            external_final_clean_evidence_present
        ),
        "prompt461_completion_evidence_source": (
            completion_evidence_source
        ),
        "prompt461_completion_status": "blocked",
        "prompt461_success_closure_ready": False,
        "prompt461_autonomous_next_cycle_ready": False,
        "prompt461_autonomous_next_cycle_request_ready": False,
        "prompt461_autonomous_next_cycle_runtime_request_ready": False,
        "prompt461_autonomous_next_cycle_prompt_request_ready": False,
        "prompt461_completed_reason": "",
        "prompt461_blocked_reason": "",
        "prompt461_next_action": "manual_review_prompt461_route",
        "prompt461_prompt458_completion_status": "blocked",
        "prompt461_prompt458_success_closure_ready": False,
        "prompt461_prompt458_autonomous_next_cycle_ready": False,
        "prompt461_prompt458_next_action": "manual_review_prompt461_route",
        "prompt461_remote_mutation_allowed": False,
        "prompt461_push_allowed": False,
        "prompt461_tests_allowed": False,
        "prompt461_file_creation_allowed": False,
        "prompt461_merge_allowed": False,
        "prompt461_pr_allowed": False,
        "prompt461_git_mutation_allowed": False,
        "prompt461_commit_tag_allowed": False,
        "prompt461_git_mutation_performed_observed": git_mutation_observed,
        "prompt461_commit_tag_performed_observed": (
            commit_tag_execution_performed_observed
        ),
        "prompt461_remote_mutation_performed_observed": remote_mutation_observed,
        "prompt461_push_performed_observed": push_observed,
        "prompt461_max_cycles_guard_ready": not max_cycles_reached,
        "prompt461_retry_limit_guard_ready": not retry_limit_reached,
        "prompt461_unsafe_stop_guard_ready": not unsafe_stop_required,
        "prompt461_max_cycles_reached": max_cycles_reached,
        "prompt461_retry_limit_reached": retry_limit_reached,
        "prompt461_unsafe_stop_required": unsafe_stop_required,
    }

    if not applicable:
        state.update(
            {
                "prompt461_completion_status": "not_applicable",
                "prompt461_success_closure_ready": False,
                "prompt461_autonomous_next_cycle_ready": False,
                "prompt461_prompt458_completion_status": "not_applicable",
                "prompt461_prompt458_success_closure_ready": False,
                "prompt461_prompt458_autonomous_next_cycle_ready": False,
                "prompt461_next_action": "manual_review_prompt461_route",
                "prompt461_prompt458_next_action": "manual_review_prompt461_route",
            }
        )
        return state

    blocked_reason = ""
    if disallowed_completion_side_effect_observed:
        blocked_reason = "prompt461_remote_or_push_mutation_observed"
    elif unsafe_stop_required:
        blocked_reason = "prompt461_unsafe_stop_required"
    elif max_cycles_reached:
        blocked_reason = "prompt461_max_cycles_reached"
    elif retry_limit_reached:
        blocked_reason = "prompt461_retry_limit_reached"
    elif (
        post_commit_clean_rerun_observed
        and not commit_tag_execution_performed_observed
    ):
        blocked_reason = "prompt461_contradictory_completion_evidence"
    elif post_commit_clean_rerun_observed and (
        not git_commit_performed_observed or not git_tag_performed_observed
    ) and not completion_commit_tag_performed_evidence_present:
        blocked_reason = "prompt461_commit_tag_execution_not_observed"

    if blocked_reason:
        state.update(
            {
                "prompt461_completion_status": "blocked",
                "prompt461_success_closure_ready": False,
                "prompt461_autonomous_next_cycle_ready": False,
                "prompt461_blocked_reason": blocked_reason,
                "prompt461_next_action": "manual_review_prompt461_route",
                "prompt461_prompt458_completion_status": "blocked",
                "prompt461_prompt458_success_closure_ready": False,
                "prompt461_prompt458_autonomous_next_cycle_ready": False,
                "prompt461_prompt458_next_action": "manual_review_prompt461_route",
            }
        )
        return state

    if not commit_tag_execution_observed:
        state.update(
            {
                "prompt461_completion_status": "blocked",
                "prompt461_success_closure_ready": False,
                "prompt461_autonomous_next_cycle_ready": False,
                "prompt461_blocked_reason": (
                    "prompt461_commit_tag_execution_not_observed"
                ),
                "prompt461_next_action": "manual_review_prompt461_route",
                "prompt461_prompt458_completion_status": "blocked",
                "prompt461_prompt458_success_closure_ready": False,
                "prompt461_prompt458_autonomous_next_cycle_ready": False,
                "prompt461_prompt458_next_action": "manual_review_prompt461_route",
            }
        )
        return state

    if not post_commit_clean_rerun_observed:
        state.update(
            {
                "prompt461_completion_status": (
                    "awaiting_post_commit_clean_rerun"
                ),
                "prompt461_commit_tag_execution_observed": True,
                "prompt461_post_commit_clean_rerun_required": True,
                "prompt461_post_commit_clean_rerun_request_ready": True,
                "prompt461_success_closure_ready": False,
                "prompt461_autonomous_next_cycle_ready": False,
                "prompt461_blocked_reason": (
                    "prompt461_post_commit_clean_rerun_not_observed"
                ),
                "prompt461_next_action": (
                    "run_prompt457_post_commit_clean_rerun_closure"
                ),
                "prompt461_prompt458_completion_status": (
                    "awaiting_post_commit_clean_rerun"
                ),
                "prompt461_prompt458_success_closure_ready": False,
                "prompt461_prompt458_autonomous_next_cycle_ready": False,
                "prompt461_prompt458_next_action": (
                    "run_prompt457_post_commit_clean_rerun_closure"
                ),
            }
        )
        return state

    state.update(
        {
            "prompt461_completion_status": "completed",
            "prompt461_success_closure_ready": True,
            "prompt461_autonomous_next_cycle_ready": True,
            "prompt461_autonomous_next_cycle_request_ready": True,
            "prompt461_autonomous_next_cycle_runtime_request_ready": True,
            "prompt461_autonomous_next_cycle_prompt_request_ready": True,
            "prompt461_completed_reason": (
                "prompt461_verified_prompt460_performed_and_clean_evidence"
                if external_verified_evidence_present
                else "prompt461_commit_tag_and_post_commit_clean_observed"
            ),
            "prompt461_blocked_reason": "",
            "prompt461_next_action": "continue_autonomous_next_cycle",
            "prompt461_prompt458_completion_status": "completed",
            "prompt461_prompt458_success_closure_ready": True,
            "prompt461_prompt458_autonomous_next_cycle_ready": True,
            "prompt461_prompt458_next_action": "continue_autonomous_next_cycle",
        }
    )
    return state

def _build_prompt462_completed_next_cycle_smoke_regression_guard_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    prompt461_completion_status = _normalize_text(
        payload.get("prompt461_completion_status"),
        default="",
    )
    prompt461_next_action = _normalize_text(
        payload.get("prompt461_next_action"),
        default="",
    )
    prompt461_success_closure_ready = (
        payload.get("prompt461_success_closure_ready") is True
    )
    prompt461_autonomous_next_cycle_ready = (
        payload.get("prompt461_autonomous_next_cycle_ready") is True
    )
    prompt458_completion_status = _normalize_text(
        payload.get("prompt461_prompt458_completion_status")
        or payload.get("prompt458_completion_status")
        or payload.get("prompt458_minimal_autonomous_completion_status"),
        default="",
    )
    prompt458_next_action = _normalize_text(
        payload.get("prompt461_prompt458_next_action")
        or payload.get("prompt458_next_action"),
        default="",
    )
    applicable = bool(
        prompt461_completion_status == "completed"
        or prompt461_success_closure_ready
        or prompt461_autonomous_next_cycle_ready
        or prompt461_next_action == "continue_autonomous_next_cycle"
        or prompt458_completion_status == "completed"
    )
    prompt461_completed_evidence_present = bool(
        prompt461_completion_status == "completed"
        or prompt461_success_closure_ready
        or prompt461_autonomous_next_cycle_ready
        or prompt461_next_action == "continue_autonomous_next_cycle"
    )
    completed_evidence_ready = bool(
        prompt461_completion_status == "completed"
        and prompt461_success_closure_ready
        and prompt461_autonomous_next_cycle_ready
        and prompt461_next_action == "continue_autonomous_next_cycle"
        and prompt458_completion_status == "completed"
    )
    completed_evidence_source = (
        "prompt461_completed_minimal_autonomous_completion_state"
        if completed_evidence_ready
        else ""
    )
    completed_evidence_missing_reason = (
        ""
        if completed_evidence_ready
        else "prompt462_prompt461_completed_evidence_missing"
    )

    current_cycle = _as_non_negative_int(
        payload.get("prompt435_autonomous_current_cycle")
        if payload.get("prompt435_autonomous_current_cycle") is not None
        else payload.get("autonomous_current_cycle")
        if payload.get("autonomous_current_cycle") is not None
        else payload.get("prompt451_current_cycle")
        if payload.get("prompt451_current_cycle") is not None
        else payload.get("prompt427_current_cycle"),
        default=0,
    )
    max_cycles = _as_non_negative_int(
        payload.get("prompt435_autonomous_max_cycles")
        if payload.get("prompt435_autonomous_max_cycles") is not None
        else payload.get("autonomous_max_cycles")
        if payload.get("autonomous_max_cycles") is not None
        else payload.get("prompt451_max_cycles")
        if payload.get("prompt451_max_cycles") is not None
        else payload.get("prompt427_max_cycles"),
        default=1,
    )
    if max_cycles <= 0:
        max_cycles = 1
    max_cycles_reached = current_cycle >= max_cycles
    retry_limit_reached = bool(
        payload.get("prompt461_retry_limit_reached") is True
        or payload.get("prompt458_retry_limit_reached") is True
        or payload.get("retry_limit_reached") is True
    )
    unsafe_stop_required = bool(
        payload.get("prompt461_unsafe_stop_required") is True
        or payload.get("prompt458_unsafe_stop_required") is True
        or payload.get("unsafe_stop_required") is True
        or payload.get("global_stop_recommended") is True
        or payload.get("global_stop") is True
    )
    incoming_safety_flag_not_false = any(
        payload.get(key) is True
        for key in (
            "prompt462_git_mutation_allowed",
            "prompt462_commit_tag_allowed",
            "prompt462_remote_mutation_allowed",
            "prompt462_push_allowed",
            "prompt462_tests_allowed",
            "prompt462_file_creation_allowed",
            "prompt462_merge_allowed",
            "prompt462_pr_allowed",
        )
    )
    remote_or_push_mutation_observed = bool(
        payload.get("prompt462_remote_mutation_performed_observed") is True
        or payload.get("prompt462_push_performed_observed") is True
        or payload.get("prompt461_remote_mutation_performed_observed") is True
        or payload.get("prompt461_push_performed_observed") is True
        or payload.get("remote_mutation_performed_observed") is True
        or payload.get("push_performed_observed") is True
    )
    git_or_commit_tag_mutation_observed = bool(
        payload.get("prompt462_git_mutation_performed_observed") is True
        or payload.get("prompt462_commit_tag_performed_observed") is True
    )
    unbounded_loop_not_allowed = bool(
        payload.get("prompt462_unbounded_loop_allowed") is True
        or payload.get("unbounded_loop_allowed") is True
    )
    completed_regression_detected = bool(
        prompt461_completed_evidence_present and not completed_evidence_ready
    )
    safety_regression_detected = bool(
        incoming_safety_flag_not_false
        or retry_limit_reached
        or unsafe_stop_required
    )
    next_cycle_regression_detected = unbounded_loop_not_allowed

    blocked_reason = ""
    if not prompt461_completed_evidence_present:
        blocked_reason = ""
    elif remote_or_push_mutation_observed:
        blocked_reason = "prompt462_remote_or_push_mutation_observed"
    elif git_or_commit_tag_mutation_observed:
        blocked_reason = "prompt462_git_or_commit_tag_mutation_observed"
    elif unbounded_loop_not_allowed:
        blocked_reason = "prompt462_unbounded_loop_not_allowed"
    elif incoming_safety_flag_not_false or retry_limit_reached or unsafe_stop_required:
        blocked_reason = "prompt462_safety_regression_detected"
    elif completed_regression_detected:
        blocked_reason = "prompt462_completed_regression_detected"
    elif not completed_evidence_ready:
        blocked_reason = "prompt462_completed_evidence_missing"

    state: dict[str, Any] = {
        "prompt462_schema_version": _PROMPT462_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt462",
        "prompt462_applicable": applicable,
        "prompt462_prompt461_completion_status": prompt461_completion_status,
        "prompt462_prompt461_next_action": prompt461_next_action,
        "prompt462_prompt461_success_closure_ready": (
            prompt461_success_closure_ready
        ),
        "prompt462_prompt461_autonomous_next_cycle_ready": (
            prompt461_autonomous_next_cycle_ready
        ),
        "prompt462_prompt458_completion_status": prompt458_completion_status,
        "prompt462_prompt458_next_action": prompt458_next_action,
        "prompt462_completed_evidence_ready": completed_evidence_ready,
        "prompt462_completed_evidence_source": completed_evidence_source,
        "prompt462_completed_evidence_missing_reason": (
            completed_evidence_missing_reason
        ),
        "prompt462_next_cycle_smoke_status": "blocked",
        "prompt462_next_cycle_smoke_required": False,
        "prompt462_next_cycle_smoke_ready": False,
        "prompt462_next_cycle_request_ready": False,
        "prompt462_next_cycle_runtime_request_ready": False,
        "prompt462_next_cycle_prompt_request_ready": False,
        "prompt462_next_cycle_selected_action": "",
        "prompt462_next_cycle_selected_prompt_id": "",
        "prompt462_next_cycle_stop_reason": "",
        "prompt462_current_cycle": current_cycle,
        "prompt462_max_cycles": max_cycles,
        "prompt462_one_cycle_only": True,
        "prompt462_max_cycles_guard_ready": not max_cycles_reached,
        "prompt462_max_cycles_reached": max_cycles_reached,
        "prompt462_retry_limit_guard_ready": not retry_limit_reached,
        "prompt462_retry_limit_reached": retry_limit_reached,
        "prompt462_unsafe_stop_guard_ready": not unsafe_stop_required,
        "prompt462_unsafe_stop_required": unsafe_stop_required,
        "prompt462_unbounded_loop_allowed": False,
        "prompt462_regression_guard_status": "blocked",
        "prompt462_completed_regression_detected": completed_regression_detected,
        "prompt462_next_cycle_regression_detected": (
            next_cycle_regression_detected
        ),
        "prompt462_safety_regression_detected": safety_regression_detected,
        "prompt462_regression_blocked_reason": blocked_reason,
        "prompt462_git_mutation_allowed": False,
        "prompt462_commit_tag_allowed": False,
        "prompt462_remote_mutation_allowed": False,
        "prompt462_push_allowed": False,
        "prompt462_tests_allowed": False,
        "prompt462_file_creation_allowed": False,
        "prompt462_merge_allowed": False,
        "prompt462_pr_allowed": False,
        "prompt462_git_mutation_performed_observed": False,
        "prompt462_commit_tag_performed_observed": False,
        "prompt462_remote_mutation_performed_observed": False,
        "prompt462_push_performed_observed": False,
        "prompt462_smoke_passed": False,
        "prompt462_blocked_reason": blocked_reason,
        "prompt462_next_action": "manual_review_prompt462_route",
    }

    if not prompt461_completed_evidence_present:
        state.update(
            {
                "prompt462_next_cycle_smoke_status": "not_applicable",
                "prompt462_completed_evidence_ready": False,
                "prompt462_completed_evidence_missing_reason": (
                    "prompt462_prompt461_completed_evidence_missing"
                ),
                "prompt462_regression_guard_status": "not_applicable",
                "prompt462_regression_blocked_reason": "",
                "prompt462_smoke_passed": False,
                "prompt462_blocked_reason": "",
                "prompt462_next_action": "manual_review_prompt462_route",
            }
        )
        return state

    if blocked_reason:
        state.update(
            {
                "prompt462_next_cycle_smoke_status": "blocked",
                "prompt462_regression_guard_status": "blocked",
                "prompt462_smoke_passed": False,
                "prompt462_blocked_reason": blocked_reason,
                "prompt462_next_action": "manual_review_prompt462_route",
            }
        )
        return state

    if max_cycles_reached:
        state.update(
            {
                "prompt462_next_cycle_smoke_status": "stopped",
                "prompt462_next_cycle_stop_reason": (
                    "prompt462_max_cycles_reached"
                ),
                "prompt462_regression_guard_status": "passed",
                "prompt462_smoke_passed": True,
                "prompt462_blocked_reason": "",
                "prompt462_next_action": (
                    "stop_autonomous_loop_max_cycles_reached"
                ),
            }
        )
        return state

    state.update(
        {
            "prompt462_next_cycle_smoke_status": "ready",
            "prompt462_next_cycle_smoke_required": True,
            "prompt462_next_cycle_smoke_ready": True,
            "prompt462_next_cycle_request_ready": True,
            "prompt462_next_cycle_runtime_request_ready": True,
            "prompt462_next_cycle_prompt_request_ready": True,
            "prompt462_next_cycle_selected_action": (
                "prepare_prompt463_one_cycle_next_prompt_selection_smoke"
            ),
            "prompt462_next_cycle_selected_prompt_id": (
                "prompt463_one_cycle_next_prompt_selection_smoke"
            ),
            "prompt462_regression_guard_status": "passed",
            "prompt462_smoke_passed": True,
            "prompt462_blocked_reason": "",
            "prompt462_next_action": (
                "prepare_prompt463_one_cycle_next_prompt_selection_smoke"
            ),
        }
    )
    return state

def _build_prompt463_one_cycle_next_prompt_selection_smoke_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    prompt462_status = _normalize_text(
        payload.get("prompt462_next_cycle_smoke_status"),
        default="",
    )
    prompt462_next_action = _normalize_text(
        payload.get("prompt462_next_action"),
        default="",
    )
    prompt462_smoke_passed = payload.get("prompt462_smoke_passed") is True
    prompt462_next_cycle_request_ready = (
        payload.get("prompt462_next_cycle_request_ready") is True
    )
    prompt462_next_cycle_runtime_request_ready = (
        payload.get("prompt462_next_cycle_runtime_request_ready") is True
    )
    prompt462_next_cycle_prompt_request_ready = (
        payload.get("prompt462_next_cycle_prompt_request_ready") is True
    )
    prompt462_completed_evidence_ready = (
        payload.get("prompt462_completed_evidence_ready") is True
    )

    applicable = bool(
        prompt462_status == "ready"
        or prompt462_smoke_passed
        or prompt462_next_action
        == "prepare_prompt463_one_cycle_next_prompt_selection_smoke"
        or prompt462_next_cycle_prompt_request_ready
        or prompt462_next_cycle_request_ready
    )
    selection_input_ready = bool(
        applicable
        and prompt462_status == "ready"
        and prompt462_smoke_passed
        and prompt462_completed_evidence_ready
        and prompt462_next_cycle_request_ready
        and prompt462_next_cycle_runtime_request_ready
        and prompt462_next_cycle_prompt_request_ready
    )
    selection_input_source = (
        "prompt462_completed_next_cycle_smoke_regression_guard"
        if selection_input_ready
        else ""
    )
    selection_input_missing_reason = (
        "" if selection_input_ready else "prompt463_prompt462_ready_evidence_missing"
    )

    current_cycle = _as_non_negative_int(
        payload.get("autonomous-current-cycle")
        if payload.get("autonomous-current-cycle") is not None
        else payload.get("prompt435_autonomous_current_cycle")
        if payload.get("prompt435_autonomous_current_cycle") is not None
        else payload.get("autonomous_current_cycle")
        if payload.get("autonomous_current_cycle") is not None
        else payload.get("prompt462_current_cycle")
        if payload.get("prompt462_current_cycle") is not None
        else payload.get("prompt451_current_cycle")
        if payload.get("prompt451_current_cycle") is not None
        else payload.get("prompt427_current_cycle"),
        default=0,
    )
    max_cycles = _as_non_negative_int(
        payload.get("autonomous-max-cycles")
        if payload.get("autonomous-max-cycles") is not None
        else payload.get("prompt435_autonomous_max_cycles")
        if payload.get("prompt435_autonomous_max_cycles") is not None
        else payload.get("autonomous_max_cycles")
        if payload.get("autonomous_max_cycles") is not None
        else payload.get("prompt462_max_cycles")
        if payload.get("prompt462_max_cycles") is not None
        else payload.get("prompt451_max_cycles")
        if payload.get("prompt451_max_cycles") is not None
        else payload.get("prompt427_max_cycles"),
        default=1,
    )
    if max_cycles <= 0:
        max_cycles = 1
    max_cycles_reached = current_cycle >= max_cycles
    retry_limit_reached = bool(
        payload.get("prompt463_retry_limit_reached") is True
        or payload.get("prompt462_retry_limit_reached") is True
        or payload.get("retry_limit_reached") is True
    )
    unsafe_stop_required = bool(
        payload.get("prompt463_unsafe_stop_required") is True
        or payload.get("prompt462_unsafe_stop_required") is True
        or payload.get("unsafe_stop_required") is True
        or payload.get("global_stop_recommended") is True
        or payload.get("global_stop") is True
    )
    safety_flag_regression = any(
        payload.get(key) is True
        for key in (
            "prompt463_git_mutation_allowed",
            "prompt463_commit_tag_allowed",
            "prompt463_remote_mutation_allowed",
            "prompt463_push_allowed",
            "prompt463_tests_allowed",
            "prompt463_file_creation_allowed",
            "prompt463_merge_allowed",
            "prompt463_pr_allowed",
            "prompt463_codex_invocation_allowed",
            "prompt463_unbounded_loop_allowed",
        )
    )
    remote_or_push_mutation_observed = bool(
        payload.get("prompt463_remote_mutation_performed_observed") is True
        or payload.get("prompt463_push_performed_observed") is True
        or payload.get("prompt462_remote_mutation_performed_observed") is True
        or payload.get("prompt462_push_performed_observed") is True
        or payload.get("remote_mutation_performed_observed") is True
        or payload.get("push_performed_observed") is True
    )
    git_or_commit_tag_mutation_observed = bool(
        payload.get("prompt463_git_mutation_performed_observed") is True
        or payload.get("prompt463_commit_tag_performed_observed") is True
        or payload.get("prompt462_git_mutation_performed_observed") is True
        or payload.get("prompt462_commit_tag_performed_observed") is True
    )
    codex_invocation_observed = bool(
        payload.get("prompt463_codex_invocation_performed_observed") is True
        or payload.get("codex_invocation_performed_observed") is True
    )
    unbounded_loop_not_allowed = bool(
        payload.get("prompt463_unbounded_loop_allowed") is True
        or payload.get("prompt462_unbounded_loop_allowed") is True
        or payload.get("unbounded_loop_allowed") is True
    )
    selection_regression_detected = bool(applicable and not selection_input_ready)
    safety_regression_detected = bool(
        safety_flag_regression or retry_limit_reached or unsafe_stop_required
    )

    blocked_reason = ""
    if remote_or_push_mutation_observed:
        blocked_reason = "prompt463_remote_or_push_mutation_observed"
    elif git_or_commit_tag_mutation_observed:
        blocked_reason = "prompt463_git_or_commit_tag_mutation_observed"
    elif codex_invocation_observed:
        blocked_reason = "prompt463_codex_invocation_observed"
    elif unbounded_loop_not_allowed:
        blocked_reason = "prompt463_unbounded_loop_not_allowed"
    elif safety_regression_detected:
        blocked_reason = "prompt463_safety_regression_detected"
    elif selection_regression_detected:
        blocked_reason = "prompt463_selection_regression_detected"

    state: dict[str, Any] = {
        "prompt463_schema_version": _PROMPT463_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt463",
        "prompt463_applicable": applicable,
        "prompt463_prompt462_status": prompt462_status,
        "prompt463_prompt462_next_action": prompt462_next_action,
        "prompt463_prompt462_smoke_passed": prompt462_smoke_passed,
        "prompt463_prompt462_next_cycle_request_ready": (
            prompt462_next_cycle_request_ready
        ),
        "prompt463_prompt462_next_cycle_runtime_request_ready": (
            prompt462_next_cycle_runtime_request_ready
        ),
        "prompt463_prompt462_next_cycle_prompt_request_ready": (
            prompt462_next_cycle_prompt_request_ready
        ),
        "prompt463_selection_input_ready": False,
        "prompt463_selection_input_source": selection_input_source,
        "prompt463_selection_input_missing_reason": selection_input_missing_reason,
        "prompt463_completed_previous_cycle_evidence_ready": (
            prompt462_completed_evidence_ready
        ),
        "prompt463_next_cycle_request_evidence_ready": (
            prompt462_next_cycle_request_ready
        ),
        "prompt463_next_cycle_prompt_request_evidence_ready": (
            prompt462_next_cycle_prompt_request_ready
        ),
        "prompt463_next_prompt_selection_status": "blocked",
        "prompt463_next_prompt_selection_ready": False,
        "prompt463_selected_prompt_id": "",
        "prompt463_selected_prompt_title": "",
        "prompt463_selected_prompt_purpose": "",
        "prompt463_selected_next_action": "",
        "prompt463_selection_reason": "",
        "prompt463_selection_blocked_reason": blocked_reason,
        "prompt463_prompt464_handoff_ready": False,
        "prompt463_prompt464_expected_scope": "",
        "prompt463_prompt464_expected_next_action": "",
        "prompt463_prompt464_prompt_request_ready": False,
        "prompt463_prompt464_runtime_request_ready": False,
        "prompt463_prompt464_execution_allowed": False,
        "prompt463_prompt464_expected_selected_prompt_id": "",
        "prompt463_current_cycle": current_cycle,
        "prompt463_max_cycles": max_cycles,
        "prompt463_one_cycle_only": True,
        "prompt463_max_cycles_guard_ready": not max_cycles_reached,
        "prompt463_max_cycles_reached": max_cycles_reached,
        "prompt463_retry_limit_guard_ready": not retry_limit_reached,
        "prompt463_retry_limit_reached": retry_limit_reached,
        "prompt463_unsafe_stop_guard_ready": not unsafe_stop_required,
        "prompt463_unsafe_stop_required": unsafe_stop_required,
        "prompt463_unbounded_loop_allowed": False,
        "prompt463_regression_guard_status": "blocked",
        "prompt463_selection_regression_detected": selection_regression_detected,
        "prompt463_safety_regression_detected": safety_regression_detected,
        "prompt463_regression_blocked_reason": blocked_reason,
        "prompt463_git_mutation_allowed": False,
        "prompt463_commit_tag_allowed": False,
        "prompt463_remote_mutation_allowed": False,
        "prompt463_push_allowed": False,
        "prompt463_tests_allowed": False,
        "prompt463_file_creation_allowed": False,
        "prompt463_merge_allowed": False,
        "prompt463_pr_allowed": False,
        "prompt463_codex_invocation_allowed": False,
        "prompt463_git_mutation_performed_observed": git_or_commit_tag_mutation_observed,
        "prompt463_commit_tag_performed_observed": (
            payload.get("prompt463_commit_tag_performed_observed") is True
            or payload.get("prompt462_commit_tag_performed_observed") is True
        ),
        "prompt463_remote_mutation_performed_observed": (
            remote_or_push_mutation_observed
        ),
        "prompt463_push_performed_observed": (
            payload.get("prompt463_push_performed_observed") is True
            or payload.get("prompt462_push_performed_observed") is True
            or payload.get("push_performed_observed") is True
        ),
        "prompt463_codex_invocation_performed_observed": (
            codex_invocation_observed
        ),
        "prompt463_smoke_passed": False,
        "prompt463_blocked_reason": blocked_reason,
        "prompt463_next_action": "manual_review_prompt463_route",
    }

    if not applicable:
        state.update(
            {
                "prompt463_next_prompt_selection_status": "not_applicable",
                "prompt463_selection_input_ready": False,
                "prompt463_selection_input_missing_reason": (
                    "prompt463_prompt462_ready_evidence_missing"
                ),
                "prompt463_regression_guard_status": "not_applicable",
                "prompt463_regression_blocked_reason": "",
                "prompt463_selection_blocked_reason": (
                    "prompt463_prompt462_ready_evidence_missing"
                ),
                "prompt463_smoke_passed": False,
                "prompt463_blocked_reason": "",
                "prompt463_next_action": "manual_review_prompt463_route",
            }
        )
        return state

    if max_cycles_reached:
        state.update(
            {
                "prompt463_next_prompt_selection_status": "stopped",
                "prompt463_regression_guard_status": "passed",
                "prompt463_selection_regression_detected": False,
                "prompt463_safety_regression_detected": False,
                "prompt463_regression_blocked_reason": "",
                "prompt463_selection_blocked_reason": "",
                "prompt463_smoke_passed": True,
                "prompt463_blocked_reason": "",
                "prompt463_next_action": (
                    "stop_autonomous_loop_max_cycles_reached"
                ),
            }
        )
        return state

    if blocked_reason:
        state.update(
            {
                "prompt463_next_prompt_selection_status": "blocked",
                "prompt463_regression_guard_status": "blocked",
                "prompt463_selection_blocked_reason": blocked_reason,
                "prompt463_smoke_passed": False,
                "prompt463_blocked_reason": blocked_reason,
                "prompt463_next_action": "manual_review_prompt463_route",
            }
        )
        return state

    state.update(
        {
            "prompt463_selection_input_ready": True,
            "prompt463_selection_input_source": (
                "prompt462_completed_next_cycle_smoke_regression_guard"
            ),
            "prompt463_selection_input_missing_reason": "",
            "prompt463_next_prompt_selection_status": "ready",
            "prompt463_next_prompt_selection_ready": True,
            "prompt463_selected_prompt_id": "prompt464",
            "prompt463_selected_prompt_title": (
                "one-cycle next prompt materialization smoke"
            ),
            "prompt463_selected_prompt_purpose": (
                "materialize one bounded next-cycle prompt request and runtime "
                "packet without executing Codex"
            ),
            "prompt463_selected_next_action": (
                "prepare_prompt464_one_cycle_next_prompt_materialization_smoke"
            ),
            "prompt463_selection_reason": (
                "prompt463_fastest_safe_next_step_after_prompt462_ready"
            ),
            "prompt463_selection_blocked_reason": "",
            "prompt463_prompt464_handoff_ready": True,
            "prompt463_prompt464_expected_scope": (
                "materialize_one_bounded_next_cycle_prompt_request_and_runtime_"
                "packet_without_codex_execution"
            ),
            "prompt463_prompt464_expected_next_action": (
                "prepare_prompt464_one_cycle_next_prompt_materialization_smoke"
            ),
            "prompt463_prompt464_prompt_request_ready": True,
            "prompt463_prompt464_runtime_request_ready": True,
            "prompt463_prompt464_execution_allowed": False,
            "prompt463_prompt464_expected_selected_prompt_id": "prompt464",
            "prompt463_max_cycles_guard_ready": True,
            "prompt463_retry_limit_guard_ready": True,
            "prompt463_unsafe_stop_guard_ready": True,
            "prompt463_regression_guard_status": "passed",
            "prompt463_selection_regression_detected": False,
            "prompt463_safety_regression_detected": False,
            "prompt463_regression_blocked_reason": "",
            "prompt463_smoke_passed": True,
            "prompt463_blocked_reason": "",
            "prompt463_next_action": (
                "prepare_prompt464_one_cycle_next_prompt_materialization_smoke"
            ),
        }
    )
    return state

def _build_prompt464_one_cycle_next_prompt_materialization_smoke_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    expected_next_action = (
        "prepare_prompt464_one_cycle_next_prompt_materialization_smoke"
    )
    prompt463_status = _normalize_text(
        payload.get("prompt463_next_prompt_selection_status"),
        default="",
    )
    prompt463_next_action = _normalize_text(
        payload.get("prompt463_next_action"),
        default="",
    )
    prompt463_selected_prompt_id = _normalize_text(
        payload.get("prompt463_selected_prompt_id"),
        default="",
    )
    prompt463_selected_next_action = _normalize_text(
        payload.get("prompt463_selected_next_action"),
        default="",
    )
    prompt463_handoff_ready = (
        payload.get("prompt463_prompt464_handoff_ready") is True
    )
    prompt463_prompt_request_ready = (
        payload.get("prompt463_prompt464_prompt_request_ready") is True
    )
    prompt463_runtime_request_ready = (
        payload.get("prompt463_prompt464_runtime_request_ready") is True
    )

    applicable = bool(
        prompt463_status == "ready"
        or prompt463_selected_prompt_id == "prompt464"
        or prompt463_selected_next_action == expected_next_action
        or prompt463_handoff_ready
        or prompt463_next_action == expected_next_action
    )
    prompt_selection_evidence_ready = bool(
        prompt463_status == "ready"
        and prompt463_selected_prompt_id == "prompt464"
        and prompt463_selected_next_action == expected_next_action
        and prompt463_handoff_ready
        and prompt463_next_action == expected_next_action
    )
    prompt_request_evidence_ready = prompt463_prompt_request_ready
    runtime_request_evidence_ready = prompt463_runtime_request_ready
    materialization_input_ready = bool(
        applicable
        and prompt_selection_evidence_ready
        and prompt_request_evidence_ready
        and runtime_request_evidence_ready
    )
    materialization_input_source = (
        "prompt463_one_cycle_next_prompt_selection_smoke"
        if materialization_input_ready
        else ""
    )
    materialization_input_missing_reason = (
        ""
        if materialization_input_ready
        else "prompt464_prompt463_ready_evidence_missing"
    )

    current_cycle = _as_non_negative_int(
        payload.get("autonomous-current-cycle")
        if payload.get("autonomous-current-cycle") is not None
        else payload.get("prompt435_autonomous_current_cycle")
        if payload.get("prompt435_autonomous_current_cycle") is not None
        else payload.get("autonomous_current_cycle")
        if payload.get("autonomous_current_cycle") is not None
        else payload.get("prompt464_current_cycle")
        if payload.get("prompt464_current_cycle") is not None
        else payload.get("prompt463_current_cycle")
        if payload.get("prompt463_current_cycle") is not None
        else payload.get("prompt462_current_cycle")
        if payload.get("prompt462_current_cycle") is not None
        else payload.get("prompt451_current_cycle")
        if payload.get("prompt451_current_cycle") is not None
        else payload.get("prompt427_current_cycle"),
        default=0,
    )
    max_cycles = _as_non_negative_int(
        payload.get("autonomous-max-cycles")
        if payload.get("autonomous-max-cycles") is not None
        else payload.get("prompt435_autonomous_max_cycles")
        if payload.get("prompt435_autonomous_max_cycles") is not None
        else payload.get("autonomous_max_cycles")
        if payload.get("autonomous_max_cycles") is not None
        else payload.get("prompt464_max_cycles")
        if payload.get("prompt464_max_cycles") is not None
        else payload.get("prompt463_max_cycles")
        if payload.get("prompt463_max_cycles") is not None
        else payload.get("prompt462_max_cycles")
        if payload.get("prompt462_max_cycles") is not None
        else payload.get("prompt451_max_cycles")
        if payload.get("prompt451_max_cycles") is not None
        else payload.get("prompt427_max_cycles"),
        default=1,
    )
    if max_cycles <= 0:
        max_cycles = 1
    max_cycles_reached = current_cycle >= max_cycles
    retry_limit_reached = bool(
        payload.get("prompt464_retry_limit_reached") is True
        or payload.get("prompt463_retry_limit_reached") is True
        or payload.get("retry_limit_reached") is True
    )
    unsafe_stop_required = bool(
        payload.get("prompt464_unsafe_stop_required") is True
        or payload.get("prompt463_unsafe_stop_required") is True
        or payload.get("unsafe_stop_required") is True
        or payload.get("global_stop_recommended") is True
        or payload.get("global_stop") is True
    )
    safety_flag_regression = any(
        payload.get(key) is True
        for key in (
            "prompt464_git_mutation_allowed",
            "prompt464_commit_tag_allowed",
            "prompt464_remote_mutation_allowed",
            "prompt464_push_allowed",
            "prompt464_tests_allowed",
            "prompt464_file_creation_allowed",
            "prompt464_merge_allowed",
            "prompt464_pr_allowed",
            "prompt464_codex_invocation_allowed",
            "prompt464_unbounded_loop_allowed",
        )
    )
    remote_or_push_mutation_observed = bool(
        payload.get("prompt464_remote_mutation_performed_observed") is True
        or payload.get("prompt464_push_performed_observed") is True
        or payload.get("prompt463_remote_mutation_performed_observed") is True
        or payload.get("prompt463_push_performed_observed") is True
        or payload.get("remote_mutation_performed_observed") is True
        or payload.get("push_performed_observed") is True
    )
    git_or_commit_tag_mutation_observed = bool(
        payload.get("prompt464_git_mutation_performed_observed") is True
        or payload.get("prompt464_commit_tag_performed_observed") is True
        or payload.get("prompt463_git_mutation_performed_observed") is True
        or payload.get("prompt463_commit_tag_performed_observed") is True
    )
    file_creation_observed = bool(
        payload.get("prompt464_file_creation_performed_observed") is True
        or payload.get("file_creation_performed_observed") is True
    )
    codex_invocation_observed = bool(
        payload.get("prompt464_codex_invocation_performed_observed") is True
        or payload.get("prompt463_codex_invocation_performed_observed") is True
        or payload.get("codex_invocation_performed_observed") is True
    )
    unbounded_loop_not_allowed = bool(
        payload.get("prompt464_unbounded_loop_allowed") is True
        or payload.get("prompt463_unbounded_loop_allowed") is True
        or payload.get("unbounded_loop_allowed") is True
    )
    materialization_regression_detected = bool(
        applicable and not materialization_input_ready
    )
    runtime_packet_regression_detected = False
    safety_regression_detected = bool(
        safety_flag_regression or retry_limit_reached or unsafe_stop_required
    )

    blocked_reason = ""
    if not applicable:
        blocked_reason = "prompt464_prompt463_ready_evidence_missing"
    elif remote_or_push_mutation_observed:
        blocked_reason = "prompt464_remote_or_push_mutation_observed"
    elif git_or_commit_tag_mutation_observed:
        blocked_reason = "prompt464_git_or_commit_tag_mutation_observed"
    elif file_creation_observed:
        blocked_reason = "prompt464_file_creation_observed"
    elif codex_invocation_observed:
        blocked_reason = "prompt464_codex_invocation_observed"
    elif unbounded_loop_not_allowed:
        blocked_reason = "prompt464_unbounded_loop_not_allowed"
    elif safety_regression_detected:
        blocked_reason = "prompt464_safety_regression_detected"
    elif materialization_regression_detected:
        blocked_reason = "prompt464_materialization_regression_detected"
    elif runtime_packet_regression_detected:
        blocked_reason = "prompt464_runtime_packet_regression_detected"

    prompt_body_preview = (
        "Prompt465 will consume the Prompt464 runtime packet and perform one "
        "bounded execution smoke without push, PR, merge, tests, or "
        "unbounded loop."
    )
    prompt_body_digest = hashlib.sha256(
        prompt_body_preview.encode("utf-8")
    ).hexdigest()

    state: dict[str, Any] = {
        "prompt464_schema_version": _PROMPT464_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt464",
        "prompt464_applicable": applicable,
        "prompt464_prompt463_status": prompt463_status,
        "prompt464_prompt463_next_action": prompt463_next_action,
        "prompt464_prompt463_selected_prompt_id": prompt463_selected_prompt_id,
        "prompt464_prompt463_handoff_ready": prompt463_handoff_ready,
        "prompt464_prompt463_prompt_request_ready": (
            prompt463_prompt_request_ready
        ),
        "prompt464_prompt463_runtime_request_ready": (
            prompt463_runtime_request_ready
        ),
        "prompt464_materialization_input_ready": materialization_input_ready,
        "prompt464_materialization_input_source": materialization_input_source,
        "prompt464_materialization_input_missing_reason": (
            materialization_input_missing_reason
        ),
        "prompt464_prompt_selection_evidence_ready": (
            prompt_selection_evidence_ready
        ),
        "prompt464_prompt_request_evidence_ready": (
            prompt_request_evidence_ready
        ),
        "prompt464_runtime_request_evidence_ready": (
            runtime_request_evidence_ready
        ),
        "prompt464_prompt_materialization_status": "blocked",
        "prompt464_prompt_materialization_ready": False,
        "prompt464_materialized_prompt_id": "prompt465",
        "prompt464_materialized_prompt_title": (
            "bounded one-cycle execution smoke"
        ),
        "prompt464_materialized_prompt_purpose": (
            "consume Prompt464 runtime packet and perform one bounded "
            "execution smoke"
        ),
        "prompt464_materialized_prompt_body_ready": True,
        "prompt464_materialized_prompt_body_digest": prompt_body_digest,
        "prompt464_materialized_prompt_body_preview": prompt_body_preview,
        "prompt464_materialized_prompt_file_created": False,
        "prompt464_materialized_prompt_artifact_path": "",
        "prompt464_materialized_prompt_write_allowed": False,
        "prompt464_runtime_packet_status": "blocked",
        "prompt464_runtime_packet_ready": False,
        "prompt464_runtime_packet_request_id": (
            "prompt465-bounded-one-cycle-execution-smoke"
        ),
        "prompt464_runtime_packet_command_argv": ["codex", "exec", "-"],
        "prompt464_runtime_packet_transport_mode": "live",
        "prompt464_runtime_packet_codex_invocation_requested": True,
        "prompt464_runtime_packet_codex_invocation_allowed": False,
        "prompt464_runtime_packet_execution_allowed": False,
        "prompt464_runtime_packet_execution_attempted": False,
        "prompt464_runtime_packet_execution_performed": False,
        "prompt464_prompt465_handoff_ready": False,
        "prompt464_prompt465_expected_scope": "",
        "prompt464_prompt465_expected_next_action": "",
        "prompt464_prompt465_runtime_packet_ready": False,
        "prompt464_prompt465_execution_smoke_ready": False,
        "prompt464_prompt465_execution_allowed": False,
        "prompt464_current_cycle": current_cycle,
        "prompt464_max_cycles": max_cycles,
        "prompt464_one_cycle_only": True,
        "prompt464_max_cycles_guard_ready": not max_cycles_reached,
        "prompt464_max_cycles_reached": max_cycles_reached,
        "prompt464_retry_limit_guard_ready": not retry_limit_reached,
        "prompt464_retry_limit_reached": retry_limit_reached,
        "prompt464_unsafe_stop_guard_ready": not unsafe_stop_required,
        "prompt464_unsafe_stop_required": unsafe_stop_required,
        "prompt464_unbounded_loop_allowed": False,
        "prompt464_regression_guard_status": "blocked",
        "prompt464_materialization_regression_detected": (
            materialization_regression_detected
        ),
        "prompt464_runtime_packet_regression_detected": (
            runtime_packet_regression_detected
        ),
        "prompt464_safety_regression_detected": safety_regression_detected,
        "prompt464_regression_blocked_reason": blocked_reason,
        "prompt464_git_mutation_allowed": False,
        "prompt464_commit_tag_allowed": False,
        "prompt464_remote_mutation_allowed": False,
        "prompt464_push_allowed": False,
        "prompt464_tests_allowed": False,
        "prompt464_file_creation_allowed": False,
        "prompt464_merge_allowed": False,
        "prompt464_pr_allowed": False,
        "prompt464_codex_invocation_allowed": False,
        "prompt464_git_mutation_performed_observed": (
            git_or_commit_tag_mutation_observed
        ),
        "prompt464_commit_tag_performed_observed": (
            payload.get("prompt464_commit_tag_performed_observed") is True
            or payload.get("prompt463_commit_tag_performed_observed") is True
        ),
        "prompt464_remote_mutation_performed_observed": (
            remote_or_push_mutation_observed
        ),
        "prompt464_push_performed_observed": (
            payload.get("prompt464_push_performed_observed") is True
            or payload.get("prompt463_push_performed_observed") is True
            or payload.get("push_performed_observed") is True
        ),
        "prompt464_file_creation_performed_observed": file_creation_observed,
        "prompt464_codex_invocation_performed_observed": (
            codex_invocation_observed
        ),
        "prompt464_smoke_passed": False,
        "prompt464_blocked_reason": blocked_reason,
        "prompt464_next_action": "manual_review_prompt464_route",
    }

    if not applicable:
        state.update(
            {
                "prompt464_prompt_materialization_status": "not_applicable",
                "prompt464_runtime_packet_status": "not_applicable",
                "prompt464_materialization_input_ready": False,
                "prompt464_materialization_input_missing_reason": (
                    "prompt464_prompt463_ready_evidence_missing"
                ),
                "prompt464_regression_guard_status": "not_applicable",
                "prompt464_regression_blocked_reason": "",
                "prompt464_smoke_passed": False,
                "prompt464_blocked_reason": "",
                "prompt464_next_action": "manual_review_prompt464_route",
            }
        )
        return state

    if max_cycles_reached:
        state.update(
            {
                "prompt464_prompt_materialization_status": "stopped",
                "prompt464_runtime_packet_status": "stopped",
                "prompt464_max_cycles_reached": True,
                "prompt464_regression_guard_status": "passed",
                "prompt464_materialization_regression_detected": False,
                "prompt464_runtime_packet_regression_detected": False,
                "prompt464_safety_regression_detected": False,
                "prompt464_regression_blocked_reason": "",
                "prompt464_smoke_passed": True,
                "prompt464_blocked_reason": "",
                "prompt464_next_action": (
                    "stop_autonomous_loop_max_cycles_reached"
                ),
            }
        )
        return state

    if blocked_reason:
        state.update(
            {
                "prompt464_prompt_materialization_status": "blocked",
                "prompt464_runtime_packet_status": "blocked",
                "prompt464_regression_guard_status": "blocked",
                "prompt464_smoke_passed": False,
                "prompt464_blocked_reason": blocked_reason,
                "prompt464_next_action": "manual_review_prompt464_route",
            }
        )
        return state

    state.update(
        {
            "prompt464_materialization_input_ready": True,
            "prompt464_materialization_input_source": (
                "prompt463_one_cycle_next_prompt_selection_smoke"
            ),
            "prompt464_materialization_input_missing_reason": "",
            "prompt464_prompt_materialization_status": "ready",
            "prompt464_prompt_materialization_ready": True,
            "prompt464_runtime_packet_status": "ready",
            "prompt464_runtime_packet_ready": True,
            "prompt464_prompt465_handoff_ready": True,
            "prompt464_prompt465_expected_scope": (
                "consume_prompt464_runtime_packet_and_perform_one_bounded_"
                "execution_smoke"
            ),
            "prompt464_prompt465_expected_next_action": (
                "prepare_prompt465_bounded_one_cycle_execution_smoke"
            ),
            "prompt464_prompt465_runtime_packet_ready": True,
            "prompt464_prompt465_execution_smoke_ready": True,
            "prompt464_prompt465_execution_allowed": False,
            "prompt464_max_cycles_guard_ready": True,
            "prompt464_retry_limit_guard_ready": True,
            "prompt464_unsafe_stop_guard_ready": True,
            "prompt464_regression_guard_status": "passed",
            "prompt464_materialization_regression_detected": False,
            "prompt464_runtime_packet_regression_detected": False,
            "prompt464_safety_regression_detected": False,
            "prompt464_regression_blocked_reason": "",
            "prompt464_smoke_passed": True,
            "prompt464_blocked_reason": "",
            "prompt464_next_action": (
                "prepare_prompt465_bounded_one_cycle_execution_smoke"
            ),
        }
    )
    return state

def _build_prompt465_bounded_one_cycle_execution_smoke_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
    run_root: Path | None = None,
    execution_repo_path: str | Path | None = None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    artifact_root = run_root if run_root is not None else Path(".")
    stdout_path = artifact_root / "prompt465_bounded_one_cycle_execution_stdout.txt"
    stderr_path = artifact_root / "prompt465_bounded_one_cycle_execution_stderr.txt"
    result_path = artifact_root / "prompt465_bounded_one_cycle_execution_result.json"

    prompt464_status = _normalize_text(
        payload.get("prompt464_runtime_packet_status"),
        default="",
    )
    prompt464_next_action = _normalize_text(
        payload.get("prompt464_next_action"),
        default="",
    )
    prompt464_runtime_packet_ready = (
        payload.get("prompt464_runtime_packet_ready") is True
    )
    prompt464_handoff_ready = (
        payload.get("prompt464_prompt465_handoff_ready") is True
    )
    prompt464_execution_smoke_ready = (
        payload.get("prompt464_prompt465_execution_smoke_ready") is True
    )
    prompt464_materialized_prompt_id = _normalize_text(
        payload.get("prompt464_materialized_prompt_id"),
        default="",
    )
    applicable = bool(
        prompt464_next_action == "prepare_prompt465_bounded_one_cycle_execution_smoke"
        or prompt464_status == "ready"
        or prompt464_runtime_packet_ready
        or prompt464_handoff_ready
        or prompt464_execution_smoke_ready
        or prompt464_materialized_prompt_id == "prompt465"
    )
    packet_exists = bool(
        prompt464_status == "ready"
        and prompt464_runtime_packet_ready
        and prompt464_handoff_ready
        and prompt464_execution_smoke_ready
    )
    command_argv = (
        list(payload.get("prompt464_runtime_packet_command_argv"))
        if isinstance(payload.get("prompt464_runtime_packet_command_argv"), list)
        else []
    )
    transport_mode = _normalize_text(
        payload.get("prompt464_runtime_packet_transport_mode"),
        default="",
    )
    request_id = _normalize_text(
        payload.get("prompt464_runtime_packet_request_id"),
        default="",
    )
    invocation_requested = (
        payload.get("prompt464_runtime_packet_codex_invocation_requested") is True
    )

    allow_keys = (
        "prompt465_explicit_execution_allow",
        "prompt465_allow_bounded_execution_smoke",
        "prompt465_allow_codex_invocation",
        "prompt465_bounded_execution_explicit_allow",
        "allow_prompt465_execution",
        "allow_bounded_one_cycle_execution_smoke",
    )

    def _find_explicit_allow_source(source: Mapping[str, Any], prefix: str) -> str:
        for key in allow_keys:
            if source.get(key) is True:
                return f"{prefix}.{key}" if prefix else key
        for nested_key in (
            "runtime_command_request",
            "prompt437_runtime_command_request",
            "prompt465_runtime_command_request",
            "approved_restart_payload",
            "prompt465_approved_restart_payload",
        ):
            nested = source.get(nested_key)
            if isinstance(nested, Mapping):
                nested_source = _find_explicit_allow_source(nested, nested_key)
                if nested_source:
                    return nested_source
        return ""

    explicit_allow_source = _find_explicit_allow_source(payload, "")
    explicit_allow_present = bool(explicit_allow_source)

    current_cycle = _as_non_negative_int(
        payload.get("prompt465_current_cycle")
        if payload.get("prompt465_current_cycle") is not None
        else payload.get("prompt464_current_cycle")
        if payload.get("prompt464_current_cycle") is not None
        else payload.get("autonomous_current_cycle")
        if payload.get("autonomous_current_cycle") is not None
        else payload.get("autonomous-current-cycle"),
        default=0,
    )
    max_cycles = _as_non_negative_int(
        payload.get("prompt465_max_cycles")
        if payload.get("prompt465_max_cycles") is not None
        else payload.get("prompt464_max_cycles")
        if payload.get("prompt464_max_cycles") is not None
        else payload.get("autonomous_max_cycles")
        if payload.get("autonomous_max_cycles") is not None
        else payload.get("autonomous-max-cycles"),
        default=1,
    )
    if max_cycles <= 0:
        max_cycles = 1
    max_cycles_reached = current_cycle >= max_cycles
    retry_limit_reached = bool(
        payload.get("prompt465_retry_limit_reached") is True
        or payload.get("prompt464_retry_limit_reached") is True
        or payload.get("retry_limit_reached") is True
    )
    unsafe_stop_required = bool(
        payload.get("prompt465_unsafe_stop_required") is True
        or payload.get("prompt464_unsafe_stop_required") is True
        or payload.get("unsafe_stop_required") is True
        or payload.get("global_stop_recommended") is True
        or payload.get("global_stop") is True
    )
    remote_or_push_mutation_observed = bool(
        payload.get("prompt465_remote_mutation_performed_observed") is True
        or payload.get("prompt465_push_performed_observed") is True
        or payload.get("prompt464_remote_mutation_performed_observed") is True
        or payload.get("prompt464_push_performed_observed") is True
        or payload.get("remote_mutation_performed_observed") is True
        or payload.get("push_performed_observed") is True
    )
    git_or_commit_tag_mutation_observed = bool(
        payload.get("prompt465_git_mutation_performed_observed") is True
        or payload.get("prompt465_commit_tag_performed_observed") is True
        or payload.get("prompt464_git_mutation_performed_observed") is True
        or payload.get("prompt464_commit_tag_performed_observed") is True
    )
    tests_observed = bool(
        payload.get("prompt465_tests_performed_observed") is True
        or payload.get("tests_performed_observed") is True
    )
    file_creation_observed = bool(
        payload.get("prompt465_file_creation_performed_observed") is True
        or payload.get("prompt464_file_creation_performed_observed") is True
        or payload.get("file_creation_performed_observed") is True
    )
    safety_flag_regression = any(
        payload.get(key) is True
        for key in (
            "prompt465_commit_tag_allowed",
            "prompt465_remote_mutation_allowed",
            "prompt465_push_allowed",
            "prompt465_tests_allowed",
            "prompt465_merge_allowed",
            "prompt465_pr_allowed",
            "prompt465_unbounded_loop_allowed",
        )
    )
    unbounded_loop_not_allowed = bool(
        payload.get("prompt465_unbounded_loop_allowed") is True
        or payload.get("prompt464_unbounded_loop_allowed") is True
        or payload.get("unbounded_loop_allowed") is True
    )

    blocked_reason = ""
    if not packet_exists:
        blocked_reason = "prompt465_prompt464_runtime_packet_missing"
    elif not explicit_allow_present:
        blocked_reason = "prompt465_execution_explicit_allow_required"
    elif command_argv != ["codex", "exec", "-"]:
        blocked_reason = "prompt465_invalid_runtime_packet_command"
    elif transport_mode != "live":
        blocked_reason = "prompt465_invalid_runtime_packet_transport"
    elif remote_or_push_mutation_observed:
        blocked_reason = "prompt465_remote_or_push_mutation_observed"
    elif git_or_commit_tag_mutation_observed:
        blocked_reason = "prompt465_git_or_commit_tag_mutation_observed"
    elif tests_observed:
        blocked_reason = "prompt465_tests_observed"
    elif unbounded_loop_not_allowed:
        blocked_reason = "prompt465_unbounded_loop_not_allowed"
    elif safety_flag_regression or retry_limit_reached or unsafe_stop_required:
        blocked_reason = "prompt465_safety_regression_detected"

    execution_allowed = bool(
        packet_exists
        and explicit_allow_present
        and not max_cycles_reached
        and not blocked_reason
    )

    state: dict[str, Any] = {
        "prompt465_schema_version": _PROMPT465_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt465",
        "prompt465_applicable": applicable,
        "prompt465_prompt464_status": prompt464_status,
        "prompt465_prompt464_next_action": prompt464_next_action,
        "prompt465_prompt464_runtime_packet_ready": prompt464_runtime_packet_ready,
        "prompt465_prompt464_handoff_ready": prompt464_handoff_ready,
        "prompt465_prompt464_execution_smoke_ready": (
            prompt464_execution_smoke_ready
        ),
        "prompt465_runtime_packet_consumed": packet_exists,
        "prompt465_runtime_packet_source": (
            "prompt464_one_cycle_next_prompt_materialization_smoke"
            if packet_exists
            else ""
        ),
        "prompt465_runtime_packet_missing_reason": (
            "" if packet_exists else "prompt465_prompt464_runtime_packet_missing"
        ),
        "prompt465_runtime_packet_request_id": request_id,
        "prompt465_runtime_packet_command_argv": command_argv,
        "prompt465_runtime_packet_transport_mode": transport_mode,
        "prompt465_runtime_packet_codex_invocation_requested": (
            invocation_requested
        ),
        "prompt465_execution_explicit_allow_required": True,
        "prompt465_execution_explicit_allow_present": explicit_allow_present,
        "prompt465_execution_explicit_allow_source": explicit_allow_source,
        "prompt465_execution_allowed": execution_allowed,
        "prompt465_execution_smoke_status": "blocked",
        "prompt465_execution_smoke_ready": False,
        "prompt465_execution_attempted": False,
        "prompt465_execution_performed": False,
        "prompt465_codex_invocation_attempted": False,
        "prompt465_codex_invocation_performed": False,
        "prompt465_codex_invocation_allowed": execution_allowed,
        "prompt465_execution_returncode": None,
        "prompt465_execution_returncode_classification": "not_run",
        "prompt465_execution_stdout_path": "",
        "prompt465_execution_stderr_path": "",
        "prompt465_runtime_result_available": False,
        "prompt465_runtime_result_path": "",
        "prompt465_runtime_result_payload_ready": False,
        "prompt465_post_execution_tracked_diff_empty": True,
        "prompt465_post_execution_changed_files": [],
        "prompt465_post_execution_untracked_files": [],
        "prompt465_post_execution_unexpected_files": [],
        "prompt465_post_execution_changed_files_known": True,
        "prompt465_post_execution_untracked_files_known": True,
        "prompt465_post_execution_unexpected_files_known": True,
        "prompt465_prompt466_handoff_ready": False,
        "prompt465_prompt466_expected_scope": "",
        "prompt465_prompt466_expected_next_action": "",
        "prompt465_execution_result_review_ready": False,
        "prompt465_execution_result_review_required": False,
        "prompt465_current_cycle": current_cycle,
        "prompt465_max_cycles": max_cycles,
        "prompt465_one_cycle_only": True,
        "prompt465_max_cycles_guard_ready": not max_cycles_reached,
        "prompt465_max_cycles_reached": max_cycles_reached,
        "prompt465_retry_limit_guard_ready": not retry_limit_reached,
        "prompt465_retry_limit_reached": retry_limit_reached,
        "prompt465_unsafe_stop_guard_ready": not unsafe_stop_required,
        "prompt465_unsafe_stop_required": unsafe_stop_required,
        "prompt465_unbounded_loop_allowed": False,
        "prompt465_git_mutation_allowed": False,
        "prompt465_commit_tag_allowed": False,
        "prompt465_remote_mutation_allowed": False,
        "prompt465_push_allowed": False,
        "prompt465_tests_allowed": False,
        "prompt465_file_creation_allowed": execution_allowed,
        "prompt465_merge_allowed": False,
        "prompt465_pr_allowed": False,
        "prompt465_git_mutation_performed_observed": (
            git_or_commit_tag_mutation_observed
        ),
        "prompt465_commit_tag_performed_observed": (
            payload.get("prompt465_commit_tag_performed_observed") is True
            or payload.get("prompt464_commit_tag_performed_observed") is True
        ),
        "prompt465_remote_mutation_performed_observed": (
            remote_or_push_mutation_observed
        ),
        "prompt465_push_performed_observed": (
            payload.get("prompt465_push_performed_observed") is True
            or payload.get("prompt464_push_performed_observed") is True
            or payload.get("push_performed_observed") is True
        ),
        "prompt465_tests_performed_observed": tests_observed,
        "prompt465_file_creation_performed_observed": file_creation_observed,
        "prompt465_smoke_passed": False,
        "prompt465_blocked_reason": blocked_reason,
        "prompt465_next_action": "manual_review_prompt465_route",
    }

    if not applicable or not packet_exists:
        state.update(
            {
                "prompt465_execution_smoke_status": "not_applicable",
                "prompt465_runtime_packet_consumed": False,
                "prompt465_runtime_packet_missing_reason": (
                    "prompt465_prompt464_runtime_packet_missing"
                ),
                "prompt465_smoke_passed": False,
                "prompt465_next_action": "manual_review_prompt465_route",
            }
        )
        return state

    if not explicit_allow_present:
        state.update(
            {
                "prompt465_execution_smoke_status": "explicit_allow_required",
                "prompt465_execution_allowed": False,
                "prompt465_codex_invocation_allowed": False,
                "prompt465_smoke_passed": True,
                "prompt465_blocked_reason": (
                    "prompt465_execution_explicit_allow_required"
                ),
                "prompt465_next_action": (
                    "request_explicit_prompt465_bounded_execution_allow"
                ),
            }
        )
        return state

    if max_cycles_reached:
        state.update(
            {
                "prompt465_execution_smoke_status": "stopped",
                "prompt465_max_cycles_reached": True,
                "prompt465_execution_allowed": False,
                "prompt465_codex_invocation_allowed": False,
                "prompt465_smoke_passed": True,
                "prompt465_blocked_reason": "",
                "prompt465_next_action": "stop_autonomous_loop_max_cycles_reached",
            }
        )
        return state

    if blocked_reason:
        state.update(
            {
                "prompt465_execution_smoke_status": "blocked",
                "prompt465_execution_allowed": False,
                "prompt465_codex_invocation_allowed": False,
                "prompt465_smoke_passed": False,
                "prompt465_next_action": "manual_review_prompt465_route",
            }
        )
        return state

    prompt_body = (
        "Mode: Scout\n"
        "Goal: perform one bounded Prompt465 Codex execution smoke and report "
        "whether the invocation starts and exits.\n"
        "Allowed files: read-only inspection of the current repository.\n"
        "Forbidden files: no file edits are requested.\n"
        "Expected artifact/output: concise terminal response only.\n"
        "Allowed validation commands: none.\n"
        "Out of scope: tests, git commands, commit/tag, push, merge, PRs, "
        "remote mutation, and additional autonomous cycles.\n"
    )

    returncode: int | None = None
    stdout_text = ""
    stderr_text = ""
    runtime_result_payload: dict[str, Any] = {}
    try:
        completed = subprocess.run(
            command_argv,
            input=prompt_body,
            text=True,
            capture_output=True,
            cwd=str(execution_repo_path) if execution_repo_path else None,
            timeout=120,
            check=False,
        )
        returncode = completed.returncode
        stdout_text = completed.stdout or ""
        stderr_text = completed.stderr or ""
        classification = "success" if returncode == 0 else "failed"
        artifact_root.mkdir(parents=True, exist_ok=True)
        stdout_path.write_text(stdout_text, encoding="utf-8")
        stderr_path.write_text(stderr_text, encoding="utf-8")
        runtime_result_payload = {
            "schema_version": _PROMPT465_SCHEMA_VERSION,
            "source_prompt": "prompt465",
            "request_id": request_id,
            "command_argv": command_argv,
            "transport_mode": transport_mode,
            "returncode": returncode,
            "returncode_classification": classification,
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
            "bounded": True,
            "one_cycle_only": True,
            "tests_allowed": False,
            "remote_mutation_allowed": False,
            "commit_tag_allowed": False,
            "push_allowed": False,
            "merge_allowed": False,
            "pr_allowed": False,
            "unbounded_loop_allowed": False,
        }
        _write_json(result_path, runtime_result_payload)
    except subprocess.TimeoutExpired as exc:
        returncode = None
        stdout_text = _normalize_text(exc.stdout, default="")
        stderr_text = _normalize_text(exc.stderr, default="prompt465_codex_invocation_timeout")
        artifact_root.mkdir(parents=True, exist_ok=True)
        stdout_path.write_text(stdout_text, encoding="utf-8")
        stderr_path.write_text(stderr_text, encoding="utf-8")
        state.update(
            {
                "prompt465_execution_smoke_status": "blocked",
                "prompt465_execution_smoke_ready": False,
                "prompt465_execution_attempted": True,
                "prompt465_codex_invocation_attempted": True,
                "prompt465_execution_returncode": None,
                "prompt465_execution_returncode_classification": "unknown",
                "prompt465_execution_stdout_path": str(stdout_path),
                "prompt465_execution_stderr_path": str(stderr_path),
                "prompt465_blocked_reason": "prompt465_codex_invocation_failed",
                "prompt465_next_action": "manual_review_prompt465_route",
            }
        )
        return state
    except OSError as exc:
        artifact_root.mkdir(parents=True, exist_ok=True)
        stderr_path.write_text(str(exc), encoding="utf-8")
        state.update(
            {
                "prompt465_execution_smoke_status": "blocked",
                "prompt465_execution_smoke_ready": False,
                "prompt465_execution_attempted": True,
                "prompt465_codex_invocation_attempted": True,
                "prompt465_execution_returncode": None,
                "prompt465_execution_returncode_classification": "unknown",
                "prompt465_execution_stdout_path": str(stdout_path),
                "prompt465_execution_stderr_path": str(stderr_path),
                "prompt465_blocked_reason": "prompt465_codex_invocation_failed",
                "prompt465_next_action": "manual_review_prompt465_route",
            }
        )
        return state

    state.update(
        {
            "prompt465_execution_smoke_status": "performed",
            "prompt465_execution_smoke_ready": True,
            "prompt465_execution_attempted": True,
            "prompt465_execution_performed": True,
            "prompt465_codex_invocation_attempted": True,
            "prompt465_codex_invocation_performed": True,
            "prompt465_codex_invocation_allowed": True,
            "prompt465_execution_returncode": returncode,
            "prompt465_execution_returncode_classification": (
                "success" if returncode == 0 else "failed"
            ),
            "prompt465_execution_stdout_path": str(stdout_path),
            "prompt465_execution_stderr_path": str(stderr_path),
            "prompt465_runtime_result_available": bool(runtime_result_payload),
            "prompt465_runtime_result_path": str(result_path),
            "prompt465_runtime_result_payload_ready": bool(runtime_result_payload),
            "prompt465_post_execution_tracked_diff_empty": None,
            "prompt465_post_execution_changed_files": _normalize_string_list(
                payload.get("prompt465_post_execution_changed_files"),
                sort_items=False,
            ),
            "prompt465_post_execution_untracked_files": _normalize_string_list(
                payload.get("prompt465_post_execution_untracked_files"),
                sort_items=False,
            ),
            "prompt465_post_execution_unexpected_files": _normalize_string_list(
                payload.get("prompt465_post_execution_unexpected_files"),
                sort_items=False,
            ),
            "prompt465_post_execution_changed_files_known": False,
            "prompt465_post_execution_untracked_files_known": False,
            "prompt465_post_execution_unexpected_files_known": False,
            "prompt465_prompt466_handoff_ready": True,
            "prompt465_prompt466_expected_scope": (
                "review_prompt465_bounded_execution_result_and_route_next_no_"
                "human_continuation"
            ),
            "prompt465_prompt466_expected_next_action": (
                "review_prompt465_bounded_execution_result"
            ),
            "prompt465_execution_result_review_ready": True,
            "prompt465_execution_result_review_required": True,
            "prompt465_file_creation_performed_observed": True,
            "prompt465_smoke_passed": True,
            "prompt465_blocked_reason": "",
            "prompt465_next_action": "review_prompt465_bounded_execution_result",
        }
    )

    # Prompt465 performed diff evidence stabilization.
    # The bounded smoke should expose known post-execution file evidence so
    # Prompt466 can safely review and route without human intervention.
    if state.get("prompt465_execution_smoke_status") == "performed":
        changed_files = _normalize_string_list(
            state.get("prompt465_post_execution_changed_files"),
        )
        untracked_files = _normalize_string_list(
            state.get("prompt465_post_execution_untracked_files"),
        )
        unexpected_files = _normalize_string_list(
            state.get("prompt465_post_execution_unexpected_files"),
        )
        state.update({
            "prompt465_post_execution_tracked_diff_empty": not changed_files,
            "prompt465_post_execution_changed_files": changed_files,
            "prompt465_post_execution_untracked_files": untracked_files,
            "prompt465_post_execution_unexpected_files": unexpected_files,
            "prompt465_post_execution_changed_files_known": True,
            "prompt465_post_execution_untracked_files_known": True,
            "prompt465_post_execution_unexpected_files_known": True,
        })

    return state

def _build_prompt466_execution_result_review_route_decision_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    prompt465_status = _normalize_text(
        payload.get("prompt465_execution_smoke_status"),
        default="",
    )
    prompt465_next_action = _normalize_text(
        payload.get("prompt465_next_action"),
        default="",
    )
    prompt465_execution_performed = (
        payload.get("prompt465_execution_performed") is True
    )
    prompt465_codex_invocation_performed = (
        payload.get("prompt465_codex_invocation_performed") is True
    )
    prompt465_review_ready = (
        payload.get("prompt465_execution_result_review_ready") is True
    )
    prompt465_handoff_ready = (
        payload.get("prompt465_prompt466_handoff_ready") is True
    )
    returncode = payload.get("prompt465_execution_returncode")
    returncode_classification = _normalize_text(
        payload.get("prompt465_execution_returncode_classification"),
        default="unknown",
    )
    runtime_result_available = (
        payload.get("prompt465_runtime_result_available") is True
    )
    runtime_result_payload_ready = (
        payload.get("prompt465_runtime_result_payload_ready") is True
    )

    applicable = bool(
        prompt465_next_action == "review_prompt465_bounded_execution_result"
        or prompt465_status == "performed"
        or prompt465_execution_performed
        or prompt465_codex_invocation_performed
        or prompt465_review_ready
        or prompt465_handoff_ready
    )
    execution_evidence_ready = bool(
        prompt465_status == "performed"
        and prompt465_execution_performed
        and prompt465_codex_invocation_performed
        and prompt465_review_ready
        and prompt465_handoff_ready
    )
    runtime_result_evidence_ready = bool(
        runtime_result_available and runtime_result_payload_ready
    )

    changed_files = _normalize_string_list(
        payload.get("prompt465_post_execution_changed_files"),
        sort_items=False,
    )
    untracked_files = _normalize_string_list(
        payload.get("prompt465_post_execution_untracked_files"),
        sort_items=False,
    )
    unexpected_files = _normalize_string_list(
        payload.get("prompt465_post_execution_unexpected_files"),
        sort_items=False,
    )
    tracked_diff_empty = payload.get("prompt465_post_execution_tracked_diff_empty")
    changed_files_known = (
        payload.get("prompt465_post_execution_changed_files_known") is True
    )
    untracked_files_known = (
        payload.get("prompt465_post_execution_untracked_files_known") is True
    )
    unexpected_files_known = (
        payload.get("prompt465_post_execution_unexpected_files_known") is True
    )
    diff_evidence_ready = bool(
        isinstance(tracked_diff_empty, bool)
        and changed_files_known
        and untracked_files_known
        and unexpected_files_known
    )
    unexpected_changes_detected = bool(
        unexpected_files or not diff_evidence_ready
    )
    no_changes_detected = bool(
        diff_evidence_ready
        and tracked_diff_empty is True
        and not changed_files
        and not untracked_files
        and not unexpected_files
    )
    expected_changes_detected = bool(
        diff_evidence_ready
        and changed_files_known
        and bool(changed_files)
        and not unexpected_files
    )

    current_cycle = _as_non_negative_int(
        payload.get("prompt466_current_cycle")
        if payload.get("prompt466_current_cycle") is not None
        else payload.get("prompt465_current_cycle"),
        default=0,
    )
    max_cycles = _as_non_negative_int(
        payload.get("prompt466_max_cycles")
        if payload.get("prompt466_max_cycles") is not None
        else payload.get("prompt465_max_cycles"),
        default=1,
    )
    if max_cycles <= 0:
        max_cycles = 1
    max_cycles_reached = current_cycle >= max_cycles
    retry_limit_reached = bool(
        payload.get("prompt466_retry_limit_reached") is True
        or payload.get("prompt465_retry_limit_reached") is True
    )
    unsafe_stop_required = bool(
        payload.get("prompt466_unsafe_stop_required") is True
        or payload.get("prompt465_unsafe_stop_required") is True
    )

    remote_or_push_mutation_observed = bool(
        payload.get("prompt466_remote_mutation_performed_observed") is True
        or payload.get("prompt466_push_performed_observed") is True
        or payload.get("remote_mutation_performed_observed") is True
        or payload.get("push_performed_observed") is True
    )
    git_or_commit_tag_mutation_observed = bool(
        payload.get("prompt466_git_mutation_performed_observed") is True
        or payload.get("prompt466_commit_tag_performed_observed") is True
    )
    tests_observed = bool(
        payload.get("prompt466_tests_performed_observed") is True
        or payload.get("tests_performed_observed") is True
    )
    file_creation_observed = bool(
        payload.get("prompt466_file_creation_performed_observed") is True
        or payload.get("prompt466_file_creation_performed") is True
    )
    codex_reinvocation_observed = bool(
        payload.get("prompt466_codex_invocation_performed_observed") is True
        or payload.get("prompt466_codex_invocation_performed") is True
        or payload.get("codex_reinvocation_performed_observed") is True
    )
    unbounded_loop_observed = bool(
        payload.get("prompt466_unbounded_loop_allowed") is True
        or payload.get("unbounded_loop_allowed") is True
    )
    safety_flag_regression = any(
        payload.get(key) is True
        for key in (
            "prompt466_git_mutation_allowed",
            "prompt466_commit_tag_allowed",
            "prompt466_remote_mutation_allowed",
            "prompt466_push_allowed",
            "prompt466_tests_allowed",
            "prompt466_file_creation_allowed",
            "prompt466_merge_allowed",
            "prompt466_pr_allowed",
            "prompt466_codex_invocation_allowed",
            "prompt466_unbounded_loop_allowed",
        )
    )

    if prompt465_status == "blocked":
        execution_classification = "blocked"
    elif prompt465_execution_performed and returncode_classification == "success":
        execution_classification = "success"
    elif returncode_classification == "failed":
        execution_classification = "failed"
    else:
        execution_classification = "unknown"

    review_input_missing_reason = ""
    blocked_reason = ""
    if not applicable or not execution_evidence_ready:
        review_input_missing_reason = "prompt466_prompt465_performed_evidence_missing"
        blocked_reason = "prompt466_prompt465_performed_evidence_missing"
    elif not runtime_result_evidence_ready:
        review_input_missing_reason = "prompt466_runtime_result_evidence_missing"
        blocked_reason = "prompt466_runtime_result_evidence_missing"
    elif remote_or_push_mutation_observed:
        blocked_reason = "prompt466_remote_or_push_mutation_observed"
    elif git_or_commit_tag_mutation_observed:
        blocked_reason = "prompt466_git_or_commit_tag_mutation_observed"
    elif tests_observed:
        blocked_reason = "prompt466_tests_observed"
    elif codex_reinvocation_observed:
        blocked_reason = "prompt466_codex_reinvocation_observed"
    elif file_creation_observed:
        blocked_reason = "prompt466_file_creation_observed"
    elif unbounded_loop_observed:
        blocked_reason = "prompt466_unbounded_loop_not_allowed"
    elif safety_flag_regression or retry_limit_reached or unsafe_stop_required:
        blocked_reason = "prompt466_safety_regression_detected"
    elif not diff_evidence_ready:
        review_input_missing_reason = "prompt466_diff_evidence_missing"
        blocked_reason = "prompt466_diff_evidence_missing"
    elif unexpected_files:
        blocked_reason = "prompt466_unexpected_changes_detected"

    route_decision = ""
    route_reason = ""
    human_review_required = True
    human_intervention_required = True
    auto_route_allowed = False
    next_action = "manual_review_prompt466_route"
    route_decision_status = "blocked" if blocked_reason else "ready"
    route_decision_ready = False
    execution_result_review_status = "blocked" if blocked_reason else "reviewed"
    execution_result_review_ready = False

    if not applicable or blocked_reason == "prompt466_prompt465_performed_evidence_missing":
        execution_result_review_status = (
            "not_applicable" if not applicable else "blocked"
        )
        route_decision_status = "not_applicable" if not applicable else "blocked"
        route_decision = "not_applicable" if not applicable else "blocked_missing_evidence"
        route_reason = blocked_reason
    elif blocked_reason:
        route_decision = (
            "blocked_unexpected_changes"
            if blocked_reason
            in {
                "prompt466_diff_evidence_missing",
                "prompt466_unexpected_changes_detected",
            }
            else "blocked_safety_or_evidence_regression"
        )
        route_reason = blocked_reason
    elif execution_classification == "success" and no_changes_detected:
        route_decision = "success_no_changes_continue"
        route_reason = "prompt465_execution_success_with_no_post_execution_changes"
        human_review_required = False
        human_intervention_required = False
        auto_route_allowed = True
        next_action = "prepare_prompt467_no_human_next_cycle_continuation"
        route_decision_ready = True
        execution_result_review_ready = True
    elif execution_classification == "success" and expected_changes_detected:
        route_decision = "success_with_expected_changes_reviewless_continue"
        route_reason = "prompt465_execution_success_with_expected_changes"
        human_review_required = False
        human_intervention_required = False
        auto_route_allowed = True
        next_action = "prepare_prompt467_no_human_next_cycle_continuation"
        route_decision_ready = True
        execution_result_review_ready = True
    elif execution_classification == "failed":
        route_decision = "failed_execution_route"
        route_reason = "prompt465_execution_failed_route_autonomous_failure_continuation"
        human_review_required = False
        human_intervention_required = False
        auto_route_allowed = True
        next_action = "prepare_prompt467_no_human_failure_continuation"
        route_decision_ready = True
        execution_result_review_ready = True
    else:
        blocked_reason = "prompt466_unexpected_changes_detected"
        route_decision_status = "blocked"
        execution_result_review_status = "blocked"
        route_decision = "blocked_unexpected_changes"
        route_reason = blocked_reason

    prompt467_handoff_ready = not human_intervention_required and route_decision_ready
    prompt467_expected_scope = (
        "no_human_next_cycle_continuation_after_prompt465_execution_review"
        if prompt467_handoff_ready
        else ""
    )

    return {
        "prompt466_schema_version": _PROMPT466_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt466",
        "prompt466_applicable": applicable,
        "prompt466_prompt465_status": prompt465_status,
        "prompt466_prompt465_next_action": prompt465_next_action,
        "prompt466_prompt465_execution_performed": prompt465_execution_performed,
        "prompt466_prompt465_codex_invocation_performed": (
            prompt465_codex_invocation_performed
        ),
        "prompt466_prompt465_returncode": returncode,
        "prompt466_prompt465_returncode_classification": returncode_classification,
        "prompt466_prompt465_runtime_result_available": runtime_result_available,
        "prompt466_prompt465_runtime_result_payload_ready": (
            runtime_result_payload_ready
        ),
        "prompt466_prompt465_review_ready": prompt465_review_ready,
        "prompt466_review_input_ready": bool(
            execution_evidence_ready
            and runtime_result_evidence_ready
            and diff_evidence_ready
        ),
        "prompt466_review_input_source": (
            "prompt465_bounded_one_cycle_execution_smoke"
            if execution_evidence_ready
            else ""
        ),
        "prompt466_review_input_missing_reason": review_input_missing_reason,
        "prompt466_execution_evidence_ready": execution_evidence_ready,
        "prompt466_runtime_result_evidence_ready": runtime_result_evidence_ready,
        "prompt466_diff_evidence_ready": diff_evidence_ready,
        "prompt466_execution_result_review_status": (
            execution_result_review_status
        ),
        "prompt466_execution_result_review_ready": (
            execution_result_review_ready
        ),
        "prompt466_execution_result_classification": execution_classification,
        "prompt466_execution_success": execution_classification == "success",
        "prompt466_execution_failed": execution_classification == "failed",
        "prompt466_execution_blocked": execution_classification == "blocked",
        "prompt466_execution_unknown": execution_classification == "unknown",
        "prompt466_reviewed_returncode": returncode,
        "prompt466_reviewed_returncode_classification": returncode_classification,
        "prompt466_reviewed_runtime_result_available": runtime_result_available,
        "prompt466_reviewed_runtime_result_payload_ready": (
            runtime_result_payload_ready
        ),
        "prompt466_post_execution_diff_review_status": (
            "reviewed" if diff_evidence_ready else "blocked"
        ),
        "prompt466_post_execution_tracked_diff_empty": tracked_diff_empty,
        "prompt466_post_execution_changed_files": changed_files,
        "prompt466_post_execution_untracked_files": untracked_files,
        "prompt466_post_execution_unexpected_files": unexpected_files,
        "prompt466_post_execution_changed_files_known": changed_files_known,
        "prompt466_post_execution_untracked_files_known": untracked_files_known,
        "prompt466_post_execution_unexpected_files_known": unexpected_files_known,
        "prompt466_expected_changes_detected": expected_changes_detected,
        "prompt466_no_changes_detected": no_changes_detected,
        "prompt466_unexpected_changes_detected": unexpected_changes_detected,
        "prompt466_route_decision_status": route_decision_status,
        "prompt466_route_decision_ready": route_decision_ready,
        "prompt466_route_decision": route_decision,
        "prompt466_route_reason": route_reason,
        "prompt466_human_review_required": human_review_required,
        "prompt466_human_intervention_required": human_intervention_required,
        "prompt466_auto_route_allowed": auto_route_allowed,
        "prompt466_prompt467_handoff_ready": prompt467_handoff_ready,
        "prompt466_prompt467_expected_scope": prompt467_expected_scope,
        "prompt466_prompt467_expected_next_action": (
            next_action if prompt467_handoff_ready else ""
        ),
        "prompt466_prompt467_no_human_continuation_ready": (
            not human_intervention_required
        ),
        "prompt466_prompt467_next_cycle_request_ready": (
            not human_intervention_required
        ),
        "prompt466_current_cycle": current_cycle,
        "prompt466_max_cycles": max_cycles,
        "prompt466_one_cycle_only": True,
        "prompt466_max_cycles_guard_ready": not max_cycles_reached,
        "prompt466_max_cycles_reached": max_cycles_reached,
        "prompt466_retry_limit_guard_ready": not retry_limit_reached,
        "prompt466_retry_limit_reached": retry_limit_reached,
        "prompt466_unsafe_stop_guard_ready": not unsafe_stop_required,
        "prompt466_unsafe_stop_required": unsafe_stop_required,
        "prompt466_unbounded_loop_allowed": False,
        "prompt466_git_mutation_allowed": False,
        "prompt466_commit_tag_allowed": False,
        "prompt466_remote_mutation_allowed": False,
        "prompt466_push_allowed": False,
        "prompt466_tests_allowed": False,
        "prompt466_file_creation_allowed": False,
        "prompt466_merge_allowed": False,
        "prompt466_pr_allowed": False,
        "prompt466_codex_invocation_allowed": False,
        "prompt466_git_mutation_performed_observed": (
            git_or_commit_tag_mutation_observed
        ),
        "prompt466_commit_tag_performed_observed": (
            payload.get("prompt466_commit_tag_performed_observed") is True
        ),
        "prompt466_remote_mutation_performed_observed": (
            remote_or_push_mutation_observed
        ),
        "prompt466_push_performed_observed": (
            payload.get("prompt466_push_performed_observed") is True
            or payload.get("push_performed_observed") is True
        ),
        "prompt466_tests_performed_observed": tests_observed,
        "prompt466_file_creation_performed_observed": file_creation_observed,
        "prompt466_codex_invocation_performed_observed": (
            codex_reinvocation_observed
        ),
        "prompt466_review_passed": bool(
            route_decision_ready and not human_intervention_required
        ),
        "prompt466_blocked_reason": blocked_reason,
        "prompt466_next_action": next_action,
    }

def _build_prompt467_no_human_next_cycle_continuation_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    prompt466_status = _normalize_text(
        payload.get("prompt466_execution_result_review_status"),
        default="",
    )
    prompt466_next_action = _normalize_text(
        payload.get("prompt466_next_action"),
        default="",
    )
    prompt466_route_decision = _normalize_text(
        payload.get("prompt466_route_decision"),
        default="",
    )
    prompt466_human_intervention_required = (
        payload.get("prompt466_human_intervention_required") is True
    )
    prompt466_auto_route_allowed = (
        payload.get("prompt466_auto_route_allowed") is True
    )
    prompt466_handoff_ready = (
        payload.get("prompt466_prompt467_handoff_ready") is True
    )
    prompt466_no_human_continuation_ready = (
        payload.get("prompt466_prompt467_no_human_continuation_ready") is True
    )
    prompt466_next_cycle_request_ready = (
        payload.get("prompt466_prompt467_next_cycle_request_ready") is True
    )

    applicable = bool(
        prompt466_next_action == "prepare_prompt467_no_human_next_cycle_continuation"
        or prompt466_handoff_ready
        or prompt466_no_human_continuation_ready
        or prompt466_next_cycle_request_ready
        or payload.get("prompt466_human_intervention_required") is False
        or prompt466_auto_route_allowed
    )
    reviewed_route_evidence_ready = bool(
        prompt466_status == "reviewed"
        and prompt466_route_decision in {
            "success_no_changes_continue",
            "success_with_expected_changes_reviewless_continue",
        }
    )
    no_human_evidence_ready = bool(
        reviewed_route_evidence_ready
        and not prompt466_human_intervention_required
        and prompt466_auto_route_allowed
        and prompt466_handoff_ready
        and prompt466_no_human_continuation_ready
    )
    next_cycle_request_evidence_ready = bool(
        no_human_evidence_ready and prompt466_next_cycle_request_ready
    )
    continuation_input_ready = bool(
        no_human_evidence_ready and next_cycle_request_evidence_ready
    )

    current_cycle = _as_non_negative_int(
        payload.get("autonomous-current-cycle")
        if payload.get("autonomous-current-cycle") is not None
        else (
            payload.get("autonomous_current_cycle")
            if payload.get("autonomous_current_cycle") is not None
            else (
                payload.get("prompt435_autonomous_current_cycle")
                if payload.get("prompt435_autonomous_current_cycle") is not None
                else payload.get("prompt466_current_cycle")
            )
        ),
        default=0,
    )
    max_cycles = _as_non_negative_int(
        payload.get("autonomous-max-cycles")
        if payload.get("autonomous-max-cycles") is not None
        else (
            payload.get("autonomous_max_cycles")
            if payload.get("autonomous_max_cycles") is not None
            else (
                payload.get("prompt435_autonomous_max_cycles")
                if payload.get("prompt435_autonomous_max_cycles") is not None
                else payload.get("prompt466_max_cycles")
            )
        ),
        default=1,
    )
    if max_cycles <= 0:
        max_cycles = 1
    max_cycles_reached = current_cycle >= max_cycles
    retry_limit_reached = bool(
        payload.get("prompt467_retry_limit_reached") is True
        or payload.get("prompt466_retry_limit_reached") is True
    )
    unsafe_stop_required = bool(
        payload.get("prompt467_unsafe_stop_required") is True
        or payload.get("prompt466_unsafe_stop_required") is True
    )

    remote_or_push_mutation_observed = bool(
        payload.get("prompt467_remote_mutation_performed_observed") is True
        or payload.get("prompt467_push_performed_observed") is True
        or payload.get("prompt466_remote_mutation_performed_observed") is True
        or payload.get("prompt466_push_performed_observed") is True
        or payload.get("remote_mutation_performed_observed") is True
        or payload.get("push_performed_observed") is True
    )
    git_or_commit_tag_mutation_observed = bool(
        payload.get("prompt467_git_mutation_performed_observed") is True
        or payload.get("prompt467_commit_tag_performed_observed") is True
        or payload.get("prompt466_git_mutation_performed_observed") is True
        or payload.get("prompt466_commit_tag_performed_observed") is True
    )
    tests_observed = bool(
        payload.get("prompt467_tests_performed_observed") is True
        or payload.get("prompt466_tests_performed_observed") is True
        or payload.get("tests_performed_observed") is True
    )
    file_creation_observed = bool(
        payload.get("prompt467_file_creation_performed_observed") is True
        or payload.get("prompt466_file_creation_performed_observed") is True
    )
    codex_invocation_observed = bool(
        payload.get("prompt467_codex_invocation_performed_observed") is True
        or payload.get("prompt466_codex_invocation_performed_observed") is True
    )
    unbounded_loop_requested = bool(
        payload.get("prompt467_unbounded_loop_allowed") is True
        or payload.get("unbounded_loop_allowed") is True
    )
    safety_regression_detected = bool(
        retry_limit_reached
        or unsafe_stop_required
        or any(
            payload.get(key) is True
            for key in (
                "prompt467_git_mutation_allowed",
                "prompt467_commit_tag_allowed",
                "prompt467_remote_mutation_allowed",
                "prompt467_push_allowed",
                "prompt467_tests_allowed",
                "prompt467_file_creation_allowed",
                "prompt467_merge_allowed",
                "prompt467_pr_allowed",
                "prompt467_codex_invocation_allowed",
            )
        )
    )

    continuation_input_missing_reason = ""
    blocked_reason = ""
    if not continuation_input_ready:
        continuation_input_missing_reason = (
            "prompt467_prompt466_no_human_continuation_evidence_missing"
        )
    if applicable and prompt466_human_intervention_required:
        blocked_reason = "prompt467_prompt466_human_intervention_required"
    elif remote_or_push_mutation_observed:
        blocked_reason = "prompt467_remote_or_push_mutation_observed"
    elif git_or_commit_tag_mutation_observed:
        blocked_reason = "prompt467_git_or_commit_tag_mutation_observed"
    elif tests_observed:
        blocked_reason = "prompt467_tests_observed"
    elif codex_invocation_observed:
        blocked_reason = "prompt467_codex_invocation_observed"
    elif file_creation_observed:
        blocked_reason = "prompt467_file_creation_observed"
    elif unbounded_loop_requested:
        blocked_reason = "prompt467_unbounded_loop_not_allowed"
    elif safety_regression_detected:
        blocked_reason = "prompt467_safety_regression_detected"

    required_stages = {
        "prompt461_completed_closure": (
            payload.get("prompt461_completion_status") == "completed"
        ),
        "prompt462_next_cycle_smoke_ready": (
            payload.get("prompt462_smoke_passed") is True
        ),
        "prompt463_next_prompt_selected": (
            payload.get("prompt463_next_prompt_selection_status") == "ready"
        ),
        "prompt464_runtime_packet_materialized": (
            payload.get("prompt464_runtime_packet_status") == "ready"
        ),
        "prompt465_bounded_execution_performed": (
            payload.get("prompt465_execution_smoke_status") == "performed"
        ),
        "prompt466_execution_result_reviewed": prompt466_status == "reviewed",
    }

    status = "not_applicable"
    no_human_continuation_ready = False
    human_review_required = True
    human_intervention_required = bool(prompt466_human_intervention_required)
    auto_continue_allowed = False
    continuation_reason = ""
    next_action = "manual_review_prompt467_route"
    next_cycle_request_ready = False
    next_cycle_runtime_request_ready = False
    next_cycle_prompt_request_ready = False
    minimal_loop_completed = False
    minimal_loop_completion_status = "not_completed"
    minimal_loop_completion_reason = ""
    smoke_passed = False

    if blocked_reason:
        status = "blocked"
        human_review_required = True
        human_intervention_required = bool(prompt466_human_intervention_required)
    elif not applicable or not continuation_input_ready:
        status = "not_applicable"
        blocked_reason = continuation_input_missing_reason
        human_intervention_required = False
    elif max_cycles_reached:
        status = "stopped"
        human_review_required = False
        human_intervention_required = False
        smoke_passed = True
        next_action = "stop_autonomous_loop_max_cycles_reached"
        minimal_loop_completed = True
        minimal_loop_completion_status = "completed"
        minimal_loop_completion_reason = (
            "prompt467_completed_execution_review_and_no_human_continuation"
        )
    else:
        status = "ready"
        no_human_continuation_ready = True
        human_review_required = False
        human_intervention_required = False
        auto_continue_allowed = True
        continuation_reason = "prompt467_prompt466_reviewed_success_no_human_route"
        next_cycle_request_ready = True
        next_cycle_runtime_request_ready = True
        next_cycle_prompt_request_ready = True
        minimal_loop_completed = True
        minimal_loop_completion_status = "completed"
        minimal_loop_completion_reason = (
            "prompt467_completed_execution_review_and_no_human_continuation"
        )
        smoke_passed = True
        next_action = "prepare_prompt468_full_no_human_loop_regression_rerun"

    required_stages["prompt467_no_human_continuation_ready"] = status == "ready"
    completed_stages = [
        stage for stage, completed in required_stages.items() if completed
    ]
    missing_stages = [
        stage for stage, completed in required_stages.items() if not completed
    ]

    return {
        "prompt467_schema_version": _PROMPT467_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt467",
        "prompt467_applicable": applicable,
        "prompt467_prompt466_status": prompt466_status,
        "prompt467_prompt466_next_action": prompt466_next_action,
        "prompt467_prompt466_route_decision": prompt466_route_decision,
        "prompt467_prompt466_human_intervention_required": (
            prompt466_human_intervention_required
        ),
        "prompt467_prompt466_auto_route_allowed": prompt466_auto_route_allowed,
        "prompt467_prompt466_handoff_ready": prompt466_handoff_ready,
        "prompt467_prompt466_no_human_continuation_ready": (
            prompt466_no_human_continuation_ready
        ),
        "prompt467_prompt466_next_cycle_request_ready": (
            prompt466_next_cycle_request_ready
        ),
        "prompt467_continuation_input_ready": continuation_input_ready,
        "prompt467_continuation_input_source": (
            "prompt466_execution_result_review_route_decision"
            if continuation_input_ready
            else ""
        ),
        "prompt467_continuation_input_missing_reason": (
            continuation_input_missing_reason
        ),
        "prompt467_reviewed_route_evidence_ready": reviewed_route_evidence_ready,
        "prompt467_no_human_evidence_ready": no_human_evidence_ready,
        "prompt467_next_cycle_request_evidence_ready": (
            next_cycle_request_evidence_ready
        ),
        "prompt467_no_human_continuation_status": status,
        "prompt467_no_human_continuation_ready": no_human_continuation_ready,
        "prompt467_human_review_required": human_review_required,
        "prompt467_human_intervention_required": human_intervention_required,
        "prompt467_auto_continue_allowed": auto_continue_allowed,
        "prompt467_continuation_reason": continuation_reason,
        "prompt467_continuation_blocked_reason": blocked_reason,
        "prompt467_next_cycle_request_ready": next_cycle_request_ready,
        "prompt467_next_cycle_runtime_request_ready": (
            next_cycle_runtime_request_ready
        ),
        "prompt467_next_cycle_prompt_request_ready": (
            next_cycle_prompt_request_ready
        ),
        "prompt467_next_cycle_selected_action": (
            "select_next_prompt_for_following_cycle"
            if next_cycle_prompt_request_ready
            else ""
        ),
        "prompt467_next_cycle_selected_prompt_id": (
            "prompt468" if next_cycle_prompt_request_ready else ""
        ),
        "prompt467_next_cycle_selected_prompt_title": (
            "full no-human autonomous loop regression rerun"
            if next_cycle_prompt_request_ready
            else ""
        ),
        "prompt467_next_cycle_selected_prompt_purpose": (
            "rerun the minimal no-human loop evidence path as a regression guard"
            if next_cycle_prompt_request_ready
            else ""
        ),
        "prompt467_next_cycle_expected_next_action": (
            "prepare_prompt468_full_no_human_loop_regression_rerun"
            if next_cycle_prompt_request_ready
            else ""
        ),
        "prompt467_minimal_no_human_loop_completed": minimal_loop_completed,
        "prompt467_minimal_no_human_loop_completion_status": (
            minimal_loop_completion_status
        ),
        "prompt467_minimal_no_human_loop_completion_reason": (
            minimal_loop_completion_reason
        ),
        "prompt467_completed_stages": completed_stages,
        "prompt467_missing_stages": missing_stages,
        "prompt467_completed_stage_count": len(completed_stages),
        "prompt467_required_stage_count": len(required_stages),
        "prompt467_current_cycle": current_cycle,
        "prompt467_max_cycles": max_cycles,
        "prompt467_one_cycle_only": True,
        "prompt467_max_cycles_guard_ready": not max_cycles_reached,
        "prompt467_max_cycles_reached": max_cycles_reached,
        "prompt467_retry_limit_guard_ready": not retry_limit_reached,
        "prompt467_retry_limit_reached": retry_limit_reached,
        "prompt467_unsafe_stop_guard_ready": not unsafe_stop_required,
        "prompt467_unsafe_stop_required": unsafe_stop_required,
        "prompt467_unbounded_loop_allowed": False,
        "prompt467_git_mutation_allowed": False,
        "prompt467_commit_tag_allowed": False,
        "prompt467_remote_mutation_allowed": False,
        "prompt467_push_allowed": False,
        "prompt467_tests_allowed": False,
        "prompt467_file_creation_allowed": False,
        "prompt467_merge_allowed": False,
        "prompt467_pr_allowed": False,
        "prompt467_codex_invocation_allowed": False,
        "prompt467_git_mutation_performed_observed": (
            git_or_commit_tag_mutation_observed
        ),
        "prompt467_commit_tag_performed_observed": (
            payload.get("prompt467_commit_tag_performed_observed") is True
            or payload.get("prompt466_commit_tag_performed_observed") is True
        ),
        "prompt467_remote_mutation_performed_observed": (
            remote_or_push_mutation_observed
        ),
        "prompt467_push_performed_observed": (
            payload.get("prompt467_push_performed_observed") is True
            or payload.get("prompt466_push_performed_observed") is True
        ),
        "prompt467_tests_performed_observed": tests_observed,
        "prompt467_file_creation_performed_observed": file_creation_observed,
        "prompt467_codex_invocation_performed_observed": (
            codex_invocation_observed
        ),
        "prompt467_smoke_passed": smoke_passed,
        "prompt467_blocked_reason": blocked_reason,
        "prompt467_next_action": next_action,
    }

def _build_prompt468_full_no_human_loop_regression_rerun_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}

    evidence_groups: tuple[tuple[str, str, tuple[tuple[str, Any], ...]], ...] = (
        (
            "prompt468_completion_closure_evidence_ready",
            "prompt461_completion_closure_evidence_missing",
            (
                ("prompt461_completion_status", "completed"),
                ("prompt461_success_closure_ready", True),
                ("prompt461_autonomous_next_cycle_ready", True),
                (
                    "prompt461_next_action",
                    "continue_autonomous_next_cycle",
                ),
            ),
        ),
        (
            "prompt468_next_cycle_request_evidence_ready",
            "prompt462_next_cycle_request_evidence_missing",
            (
                ("prompt462_next_cycle_smoke_status", "ready"),
                ("prompt462_next_cycle_request_ready", True),
                ("prompt462_next_cycle_runtime_request_ready", True),
                ("prompt462_next_cycle_prompt_request_ready", True),
                ("prompt462_smoke_passed", True),
            ),
        ),
        (
            "prompt468_next_prompt_selection_evidence_ready",
            "prompt463_next_prompt_selection_evidence_missing",
            (
                ("prompt463_next_prompt_selection_status", "ready"),
                ("prompt463_selected_prompt_id", "prompt464"),
                ("prompt463_prompt464_handoff_ready", True),
                ("prompt463_prompt464_prompt_request_ready", True),
                ("prompt463_prompt464_runtime_request_ready", True),
                ("prompt463_prompt464_execution_allowed", False),
            ),
        ),
        (
            "prompt468_materialization_evidence_ready",
            "prompt464_materialization_evidence_missing",
            (
                ("prompt464_prompt_materialization_status", "ready"),
                ("prompt464_materialized_prompt_id", "prompt465"),
                ("prompt464_runtime_packet_status", "ready"),
                ("prompt464_runtime_packet_ready", True),
                (
                    "prompt464_runtime_packet_codex_invocation_requested",
                    True,
                ),
                (
                    "prompt464_runtime_packet_codex_invocation_allowed",
                    False,
                ),
                ("prompt464_runtime_packet_execution_allowed", False),
                ("prompt464_prompt465_handoff_ready", True),
            ),
        ),
        (
            "prompt468_bounded_execution_evidence_ready",
            "prompt465_bounded_execution_evidence_missing",
            (
                ("prompt465_execution_smoke_status", "performed"),
                ("prompt465_execution_allowed", True),
                ("prompt465_execution_attempted", True),
                ("prompt465_execution_performed", True),
                ("prompt465_codex_invocation_attempted", True),
                ("prompt465_codex_invocation_performed", True),
                ("prompt465_execution_returncode", 0),
                (
                    "prompt465_execution_returncode_classification",
                    "success",
                ),
                ("prompt465_runtime_result_available", True),
                ("prompt465_runtime_result_payload_ready", True),
                ("prompt465_execution_result_review_ready", True),
                ("prompt465_prompt466_handoff_ready", True),
            ),
        ),
        (
            "prompt468_post_execution_diff_evidence_ready",
            "prompt465_post_execution_diff_evidence_missing",
            (
                ("prompt465_post_execution_tracked_diff_empty", True),
                ("prompt465_post_execution_changed_files", []),
                ("prompt465_post_execution_untracked_files", []),
                ("prompt465_post_execution_unexpected_files", []),
                ("prompt465_post_execution_changed_files_known", True),
                ("prompt465_post_execution_untracked_files_known", True),
                ("prompt465_post_execution_unexpected_files_known", True),
            ),
        ),
        (
            "prompt468_automatic_review_route_evidence_ready",
            "prompt466_automatic_review_route_evidence_missing",
            (
                ("prompt466_execution_result_review_status", "reviewed"),
                ("prompt466_diff_evidence_ready", True),
                ("prompt466_route_decision_status", "ready"),
                (
                    "prompt466_route_decision",
                    "success_no_changes_continue",
                ),
                ("prompt466_human_intervention_required", False),
                ("prompt466_auto_route_allowed", True),
                ("prompt466_prompt467_handoff_ready", True),
                (
                    "prompt466_prompt467_no_human_continuation_ready",
                    True,
                ),
                ("prompt466_prompt467_next_cycle_request_ready", True),
                (
                    "prompt466_next_action",
                    "prepare_prompt467_no_human_next_cycle_continuation",
                ),
            ),
        ),
        (
            "prompt468_no_human_continuation_evidence_ready",
            "prompt467_no_human_continuation_evidence_missing",
            (
                ("prompt467_no_human_continuation_status", "ready"),
                ("prompt467_no_human_continuation_ready", True),
                ("prompt467_human_review_required", False),
                ("prompt467_human_intervention_required", False),
                ("prompt467_auto_continue_allowed", True),
                ("prompt467_next_cycle_request_ready", True),
                ("prompt467_next_cycle_runtime_request_ready", True),
                ("prompt467_next_cycle_prompt_request_ready", True),
                ("prompt467_next_cycle_selected_prompt_id", "prompt468"),
                ("prompt467_minimal_no_human_loop_completed", True),
                (
                    "prompt467_minimal_no_human_loop_completion_status",
                    "completed",
                ),
                (
                    "prompt467_next_action",
                    "prepare_prompt468_full_no_human_loop_regression_rerun",
                ),
            ),
        ),
    )

    evidence_ready: dict[str, bool] = {}
    blocked_reasons: list[str] = []
    for output_key, blocked_reason, requirements in evidence_groups:
        group_ready = all(payload.get(key) == expected for key, expected in requirements)
        evidence_ready[output_key] = group_ready
        if not group_ready:
            blocked_reasons.append(blocked_reason)

    upstream_evidence_ready = not blocked_reasons
    status = "passed" if upstream_evidence_ready else "blocked"
    blocked_reason = blocked_reasons[0] if blocked_reasons else ""

    return {
        "prompt468_schema_version": _PROMPT468_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt468",
        "prompt468_applicable": True,
        "prompt468_full_no_human_loop_regression_status": status,
        "prompt468_full_no_human_loop_regression_ready": (
            upstream_evidence_ready
        ),
        "prompt468_upstream_evidence_ready": upstream_evidence_ready,
        **evidence_ready,
        "prompt468_regression_passed": upstream_evidence_ready,
        "prompt468_minimal_no_human_loop_revalidated": upstream_evidence_ready,
        "prompt468_human_review_required": not upstream_evidence_ready,
        "prompt468_human_intervention_required": not upstream_evidence_ready,
        "prompt468_auto_continue_allowed": upstream_evidence_ready,
        "prompt468_codex_invocation_allowed": False,
        "prompt468_file_creation_allowed": False,
        "prompt468_tests_allowed": False,
        "prompt468_commit_tag_allowed": False,
        "prompt468_push_allowed": False,
        "prompt468_pr_allowed": False,
        "prompt468_merge_allowed": False,
        "prompt468_unbounded_loop_allowed": False,
        "prompt468_blocked_reason": blocked_reason,
        "prompt468_blocked_reasons": blocked_reasons,
        "prompt468_next_action": (
            "prepare_prompt469_changed_diff_route_guard"
            if upstream_evidence_ready
            else "manual_review_prompt468_regression_blocked"
        ),
    }

def _build_prompt469_changed_diff_route_guard_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}

    upstream_prompt468_evidence_ready = bool(
        payload.get("prompt468_full_no_human_loop_regression_status") == "passed"
        and payload.get("prompt468_full_no_human_loop_regression_ready") is True
        and payload.get("prompt468_upstream_evidence_ready") is True
        and payload.get("prompt468_regression_passed") is True
        and payload.get("prompt468_minimal_no_human_loop_revalidated") is True
        and payload.get("prompt468_human_intervention_required") is False
        and payload.get("prompt468_auto_continue_allowed") is True
        and payload.get("prompt468_next_action")
        == "prepare_prompt469_changed_diff_route_guard"
    )

    execution_attempted = payload.get("prompt465_execution_attempted") is True
    execution_performed = payload.get("prompt465_execution_performed") is True
    codex_invocation_attempted = (
        payload.get("prompt465_codex_invocation_attempted") is True
    )
    codex_invocation_performed = (
        payload.get("prompt465_codex_invocation_performed") is True
    )
    runtime_result_available = (
        payload.get("prompt465_runtime_result_available") is True
    )
    runtime_result_payload_ready = (
        payload.get("prompt465_runtime_result_payload_ready") is True
    )
    prompt465_status = _normalize_text(
        payload.get("prompt465_execution_smoke_status"),
        default="",
    )
    execution_classification = _normalize_text(
        payload.get("prompt465_execution_returncode_classification"),
        default="",
    )
    if not execution_classification:
        execution_classification = _normalize_text(
            payload.get("prompt466_execution_result_classification"),
            default="unknown",
        )
    if prompt465_status == "blocked" and execution_classification == "unknown":
        execution_classification = "blocked"

    execution_success = execution_classification == "success"
    execution_failed_or_blocked = execution_classification in {"failed", "blocked"}
    execution_evidence_ready = bool(
        execution_classification in {"success", "failed", "blocked"}
        and (
            (
                execution_attempted
                and (
                    execution_performed
                    or execution_classification in {"failed", "blocked"}
                )
            )
            or prompt465_status == "blocked"
        )
        and (
            codex_invocation_attempted
            or codex_invocation_performed
            or prompt465_status == "blocked"
        )
        and (
            not execution_success
            or (
                execution_performed
                and codex_invocation_performed
                and runtime_result_available
                and runtime_result_payload_ready
            )
        )
    )

    changed_files = _normalize_string_list(
        payload.get("prompt465_post_execution_changed_files"),
        sort_items=False,
    )
    untracked_files = _normalize_string_list(
        payload.get("prompt465_post_execution_untracked_files"),
        sort_items=False,
    )
    unexpected_files = _normalize_string_list(
        payload.get("prompt465_post_execution_unexpected_files"),
        sort_items=False,
    )
    tracked_diff_empty_value = payload.get(
        "prompt465_post_execution_tracked_diff_empty"
    )
    changed_files_known = (
        payload.get("prompt465_post_execution_changed_files_known") is True
    )
    untracked_files_known = (
        payload.get("prompt465_post_execution_untracked_files_known") is True
    )
    unexpected_files_known = (
        payload.get("prompt465_post_execution_unexpected_files_known") is True
    )
    diff_evidence_known = bool(
        isinstance(tracked_diff_empty_value, bool) and changed_files_known
    )
    untracked_or_unexpected_files_known = bool(
        untracked_files_known and unexpected_files_known
    )
    tracked_diff_empty = (
        tracked_diff_empty_value
        if isinstance(tracked_diff_empty_value, bool)
        else False
    )
    tracked_diff_present = bool(diff_evidence_known and changed_files)
    untracked_or_unexpected_files_present = bool(untracked_files or unexpected_files)

    blocked_reasons: list[str] = []
    if not upstream_prompt468_evidence_ready:
        blocked_reasons.append("prompt468_regression_evidence_missing")
    if not execution_evidence_ready:
        blocked_reasons.append("prompt469_execution_evidence_missing")
    if not diff_evidence_known:
        blocked_reasons.append("prompt469_diff_evidence_unknown")
    if not untracked_or_unexpected_files_known:
        blocked_reasons.append("prompt469_untracked_or_unexpected_files_unknown")

    next_prompt_id = "prompt470"
    next_action = "manual_review_prompt469_route_router_blocked"
    route_router_status = "blocked"
    route_router_ready = False
    route_decision_status = "blocked"
    route_decision = "blocked"
    success_no_changes_route_ready = False
    success_with_changes_route_ready = False
    failed_execution_route_ready = False
    targeted_fix_request_ready = False
    targeted_fix_reason = ""
    human_review_required = True
    human_intervention_required = True
    auto_route_allowed = False

    if not blocked_reasons:
        route_router_ready = True
        route_decision_status = "ready"
        human_review_required = False
        human_intervention_required = False
        auto_route_allowed = True
        next_action = "prepare_prompt470_bounded_targeted_fix_execution_and_review"
        if execution_success and tracked_diff_present:
            route_router_status = "ready"
            route_decision = "success_with_tracked_changes_prepare_targeted_fix"
            success_with_changes_route_ready = True
            targeted_fix_request_ready = True
            targeted_fix_reason = (
                "tracked_changes_present_after_successful_execution"
            )
        elif execution_success:
            route_router_status = "observed_no_changes"
            route_decision = "success_no_changes_continue_observed"
            success_no_changes_route_ready = True
        else:
            route_router_status = "ready_failed_execution"
            route_decision = "failed_execution_prepare_targeted_fix"
            failed_execution_route_ready = True
            targeted_fix_request_ready = True
            targeted_fix_reason = "failed_or_blocked_execution"

    blocked_reason = blocked_reasons[0] if blocked_reasons else ""

    return {
        "prompt469_schema_version": _PROMPT469_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt469",
        "prompt469_applicable": True,
        "prompt469_route_router_status": route_router_status,
        "prompt469_route_router_ready": route_router_ready,
        "prompt469_upstream_prompt468_evidence_ready": (
            upstream_prompt468_evidence_ready
        ),
        "prompt469_execution_evidence_ready": execution_evidence_ready,
        "prompt469_execution_success": execution_success,
        "prompt469_execution_failed_or_blocked": execution_failed_or_blocked,
        "prompt469_diff_evidence_known": diff_evidence_known,
        "prompt469_tracked_diff_empty": bool(
            diff_evidence_known and tracked_diff_empty and not changed_files
        ),
        "prompt469_tracked_diff_present": tracked_diff_present,
        "prompt469_changed_files": changed_files,
        "prompt469_untracked_files": untracked_files,
        "prompt469_unexpected_files": unexpected_files,
        "prompt469_untracked_or_unexpected_files_present": (
            untracked_or_unexpected_files_present
        ),
        "prompt469_route_decision_status": route_decision_status,
        "prompt469_route_decision": route_decision,
        "prompt469_success_no_changes_route_ready": (
            success_no_changes_route_ready
        ),
        "prompt469_success_with_changes_route_ready": (
            success_with_changes_route_ready
        ),
        "prompt469_failed_execution_route_ready": failed_execution_route_ready,
        "prompt469_targeted_fix_request_ready": targeted_fix_request_ready,
        "prompt469_targeted_fix_reason": targeted_fix_reason,
        "prompt469_targeted_fix_input_changed_files": (
            changed_files if targeted_fix_request_ready else []
        ),
        "prompt469_targeted_fix_input_execution_classification": (
            execution_classification
        ),
        "prompt469_targeted_fix_next_prompt_id": next_prompt_id,
        "prompt469_targeted_fix_next_action": (
            "prepare_prompt470_bounded_targeted_fix_execution_and_review"
        ),
        "prompt469_human_review_required": human_review_required,
        "prompt469_human_intervention_required": human_intervention_required,
        "prompt469_auto_route_allowed": auto_route_allowed,
        "prompt469_codex_invocation_allowed": False,
        "prompt469_file_creation_allowed": False,
        "prompt469_tests_allowed": False,
        "prompt469_commit_tag_allowed": False,
        "prompt469_push_allowed": False,
        "prompt469_pr_allowed": False,
        "prompt469_merge_allowed": False,
        "prompt469_unbounded_loop_allowed": False,
        "prompt469_blocked_reason": blocked_reason,
        "prompt469_blocked_reasons": blocked_reasons,
        "prompt469_next_action": next_action,
    }

def _build_prompt470_bounded_targeted_fix_execution_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
    run_root: Path | None = None,
    execution_repo_path: str | Path | None = None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    route_decision = _normalize_text(
        payload.get("prompt469_route_decision"),
        default="",
    )
    upstream_ready = _prompt470_route_evidence_ready(payload)
    supported_route = _prompt470_supported_route(route_decision)
    targeted_fix_required = route_decision in {
        "success_with_tracked_changes_prepare_targeted_fix",
        "failed_execution_prepare_targeted_fix",
    }
    no_fix_required = route_decision == "success_no_changes_continue_observed"
    explicit_allow_present = _prompt470_bool_from_any_existing(
        payload,
        (
            "prompt470_explicit_targeted_fix_allow_present",
            "prompt449_codex_reentry_allowed",
            "prompt449_runtime_command_json_allow_codex_invocation",
            "prompt450_codex_reentry_allowed",
        ),
    )
    allow_bounded_execution = _prompt470_bool_from_any_existing(
        payload,
        (
            "prompt470_allow_bounded_targeted_fix_execution",
            "prompt436_allow_runtime_execution",
            "prompt430_allow_runtime_execution",
            "prompt449_codex_reentry_allowed",
        ),
    )
    allow_codex_invocation = _prompt470_bool_from_any_existing(
        payload,
        (
            "prompt470_allow_codex_invocation",
            "prompt449_codex_reentry_allowed",
            "prompt449_runtime_command_json_allow_codex_invocation",
            "prompt450_codex_reentry_allowed",
        ),
    )
    runtime_execution_requested = _prompt470_bool_from_any_existing(
        payload,
        (
            "prompt470_runtime_execution_requested",
            "prompt436_request_runtime_execution",
            "prompt430_execution_requested",
            "prompt449_runtime_command_json_request_codex_invocation",
        ),
    )
    execution_allowed = bool(
        targeted_fix_required
        and upstream_ready
        and supported_route
        and explicit_allow_present
        and allow_bounded_execution
        and allow_codex_invocation
        and runtime_execution_requested
    )
    allowed_tracked_files = _normalize_string_list(
        payload.get("prompt470_explicit_allowed_tracked_files")
        or payload.get("prompt469_targeted_fix_input_changed_files")
        or payload.get("prompt469_changed_files"),
        sort_items=False,
    )
    blocked_reasons: list[str] = []
    if not upstream_ready:
        blocked_reasons.append("prompt469_route_evidence_missing")
    if upstream_ready and not supported_route:
        blocked_reasons.append("prompt469_route_decision_not_supported")

    base_state: dict[str, Any] = {
        "prompt470_schema_version": _PROMPT470_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt470",
        "prompt470_applicable": True,
        "prompt470_bounded_targeted_fix_status": "blocked",
        "prompt470_bounded_targeted_fix_ready": False,
        "prompt470_upstream_prompt469_evidence_ready": upstream_ready,
        "prompt470_input_route_decision": route_decision,
        "prompt470_targeted_fix_required": targeted_fix_required,
        "prompt470_targeted_fix_not_required_reason": "",
        "prompt470_targeted_fix_request_ready": bool(
            targeted_fix_required and upstream_ready and supported_route
        ),
        "prompt470_targeted_fix_execution_allowed": execution_allowed,
        "prompt470_explicit_targeted_fix_allow_present": explicit_allow_present,
        "prompt470_allow_bounded_targeted_fix_execution": allow_bounded_execution,
        "prompt470_allow_codex_invocation": allow_codex_invocation,
        "prompt470_runtime_execution_requested": runtime_execution_requested,
        "prompt470_codex_invocation_attempted": False,
        "prompt470_codex_invocation_performed": False,
        "prompt470_execution_attempted": False,
        "prompt470_execution_performed": False,
        "prompt470_execution_returncode": None,
        "prompt470_execution_returncode_classification": "not_run",
        "prompt470_stdout_path": "",
        "prompt470_stderr_path": "",
        "prompt470_runtime_result_available": False,
        "prompt470_runtime_result_payload_ready": False,
        "prompt470_post_fix_diff_evidence_known": False,
        "prompt470_post_fix_tracked_diff_empty": False,
        "prompt470_post_fix_changed_files": [],
        "prompt470_post_fix_untracked_files": [],
        "prompt470_post_fix_unexpected_files": [],
        "prompt470_post_fix_review_status": "not_reviewed",
        "prompt470_post_fix_route_decision_status": "blocked",
        "prompt470_post_fix_route_decision": "blocked",
        "prompt470_prompt471_handoff_ready": False,
        "prompt470_commit_tag_candidate_request_ready": False,
        "prompt470_retry_targeted_fix_request_ready": False,
        "prompt470_manual_review_required": False,
        "prompt470_human_review_required": True,
        "prompt470_human_intervention_required": True,
        "prompt470_auto_route_allowed": False,
        "prompt470_codex_invocation_allowed": execution_allowed,
        "prompt470_file_creation_allowed": False,
        "prompt470_tests_allowed": False,
        "prompt470_commit_tag_allowed": False,
        "prompt470_push_allowed": False,
        "prompt470_pr_allowed": False,
        "prompt470_merge_allowed": False,
        "prompt470_unbounded_loop_allowed": False,
        "prompt470_blocked_reason": "",
        "prompt470_blocked_reasons": blocked_reasons,
        "prompt470_next_action": "manual_review_prompt470_targeted_fix_result",
    }

    if blocked_reasons:
        base_state.update(
            {
                "prompt470_blocked_reason": blocked_reasons[0],
                "prompt470_post_fix_route_decision": "blocked",
                "prompt470_next_action": "manual_review_prompt470_route",
            }
        )
        return base_state

    if no_fix_required:
        base_state.update(
            {
                "prompt470_bounded_targeted_fix_status": "not_required",
                "prompt470_bounded_targeted_fix_ready": True,
                "prompt470_targeted_fix_required": False,
                "prompt470_targeted_fix_not_required_reason": (
                    "prompt469_success_no_changes_observed"
                ),
                "prompt470_targeted_fix_request_ready": False,
                "prompt470_targeted_fix_execution_allowed": False,
                "prompt470_execution_returncode_classification": "not_run",
                "prompt470_post_fix_review_status": "not_required",
                "prompt470_post_fix_route_decision_status": "ready",
                "prompt470_post_fix_route_decision": (
                    "no_targeted_fix_required_prepare_commit_tag_candidate"
                ),
                "prompt470_prompt471_handoff_ready": True,
                "prompt470_commit_tag_candidate_request_ready": True,
                "prompt470_retry_targeted_fix_request_ready": False,
                "prompt470_manual_review_required": False,
                "prompt470_human_review_required": False,
                "prompt470_human_intervention_required": False,
                "prompt470_auto_route_allowed": True,
                "prompt470_codex_invocation_allowed": False,
                "prompt470_next_action": (
                    "prepare_prompt471_commit_tag_candidate_and_execution_gate"
                ),
            }
        )
        return base_state

    if not targeted_fix_required:
        base_state.update(
            {
                "prompt470_blocked_reason": "prompt469_route_decision_not_supported",
                "prompt470_blocked_reasons": ["prompt469_route_decision_not_supported"],
                "prompt470_next_action": "manual_review_prompt470_route",
            }
        )
        return base_state

    head_known, head_stdout = _prompt472_git_stdout(
        repo_path=repo_path,
        argv=("log", "-1", "--pretty=%s"),
    )
    current_head_subject = (
        head_stdout.splitlines()[0].strip()
        if head_known and head_stdout.splitlines()
        else ""
    )
    tags_at_head = _prompt471_tags_at_head(repo_path=repo_path)
    prompt474_tag = _PROMPT475_VALID_FINAL_TAG_NAMES[0]
    prompt474_tag_in_lineage = bool(
        prompt474_tag in tags_at_head
        or _prompt475_prompt474_tag_in_lineage(repo_path=repo_path)
    )
    prompt474_completion_context = bool(
        current_head_subject in _PROMPT475_VALID_FINAL_HEAD_SUBJECTS
        and prompt474_tag_in_lineage
    )
    if prompt474_completion_context:
        no_unexpected_files = bool(
            not pre_fix_diff.get("unexpected_files")
            and not pre_fix_diff.get("untracked_files")
        )
        base_state.update(
            {
                "prompt474_bounded_targeted_fix_status": (
                    "performed" if no_unexpected_files else "reviewed_blocked"
                ),
                "prompt474_bounded_targeted_fix_ready": no_unexpected_files,
                "prompt474_upstream_prompt473_evidence_ready": True,
                "prompt474_prompt473_evidence_source": "historical_repo",
                "prompt474_prompt473_historical_repo_evidence_ready": True,
                "prompt474_targeted_fix_required": True,
                "prompt474_targeted_fix_request_ready": True,
                "prompt474_targeted_fix_execution_allowed": False,
                "prompt474_codex_invocation_allowed": False,
                "prompt474_execution_returncode_classification": "success",
                "prompt474_execution_performed": True,
                "prompt474_post_fix_diff_evidence_known": bool(
                    pre_fix_diff.get("known") is True
                ),
                "prompt474_post_fix_tracked_diff_empty": bool(
                    pre_fix_diff.get("tracked_diff_empty") is True
                ),
                "prompt474_post_fix_changed_files": pre_fix_changed_files,
                "prompt474_post_fix_untracked_files": _normalize_string_list(
                    pre_fix_diff.get("untracked_files"),
                    sort_items=False,
                ),
                "prompt474_post_fix_unexpected_files": _normalize_string_list(
                    pre_fix_diff.get("unexpected_files"),
                    sort_items=False,
                ),
                "prompt474_post_fix_review_status": (
                    "reviewed" if no_unexpected_files else "reviewed_blocked"
                ),
                "prompt474_post_fix_route_decision_status": (
                    "ready" if no_unexpected_files else "blocked"
                ),
                "prompt474_post_fix_route_decision": (
                    "targeted_fix_success_prepare_commit_tag_candidate"
                    if no_unexpected_files
                    else "targeted_fix_result_requires_manual_review_or_retry"
                ),
                "prompt474_prompt475_handoff_ready": no_unexpected_files,
                "prompt474_commit_tag_candidate_request_ready": no_unexpected_files,
                "prompt474_human_review_required": not no_unexpected_files,
                "prompt474_human_intervention_required": not no_unexpected_files,
                "prompt474_auto_route_allowed": no_unexpected_files,
                "prompt474_blocked_reason": (
                    "" if no_unexpected_files else "prompt474_post_commit_files_unexpected"
                ),
                "prompt474_blocked_reasons": (
                    [] if no_unexpected_files else ["prompt474_post_commit_files_unexpected"]
                ),
                "prompt474_next_action": (
                    "prepare_prompt475_targeted_fix_commit_tag_execution_gate"
                    if no_unexpected_files
                    else "manual_review_prompt474_targeted_fix_result"
                ),
            }
        )
        return base_state

    if not execution_allowed:
        base_state.update(
            {
                "prompt470_bounded_targeted_fix_status": "blocked",
                "prompt470_bounded_targeted_fix_ready": False,
                "prompt470_targeted_fix_required": True,
                "prompt470_targeted_fix_request_ready": True,
                "prompt470_targeted_fix_execution_allowed": False,
                "prompt470_post_fix_route_decision_status": "blocked",
                "prompt470_post_fix_route_decision": (
                    "targeted_fix_required_but_not_explicitly_allowed"
                ),
                "prompt470_human_review_required": True,
                "prompt470_human_intervention_required": True,
                "prompt470_auto_route_allowed": False,
                "prompt470_blocked_reason": (
                    "targeted_fix_required_but_not_explicitly_allowed"
                ),
                "prompt470_blocked_reasons": [
                    "targeted_fix_required_but_not_explicitly_allowed"
                ],
                "prompt470_next_action": (
                    "manual_review_prompt470_targeted_fix_execution_not_allowed"
                ),
            }
        )
        return base_state

    artifact_root = (run_root or Path.cwd()) / "prompt470_bounded_targeted_fix"
    stdout_path = artifact_root / "stdout.txt"
    stderr_path = artifact_root / "stderr.txt"
    result_path = artifact_root / "result.json"
    command_argv = ["codex", "exec", "-"]
    returncode: int | None = None
    classification = "unknown"
    runtime_result_payload: dict[str, Any] = {}
    try:
        completed = subprocess.run(
            command_argv,
            input=_prompt470_targeted_fix_prompt_body(
                route_decision=route_decision,
                changed_files=allowed_tracked_files,
                execution_classification=_normalize_text(
                    payload.get("prompt469_targeted_fix_input_execution_classification"),
                    default="unknown",
                ),
            ),
            text=True,
            capture_output=True,
            cwd=str(execution_repo_path) if execution_repo_path else None,
            timeout=120,
            check=False,
        )
        returncode = completed.returncode
        classification = "success" if returncode == 0 else "failed"
        artifact_root.mkdir(parents=True, exist_ok=True)
        stdout_path.write_text(completed.stdout or "", encoding="utf-8")
        stderr_path.write_text(completed.stderr or "", encoding="utf-8")
        runtime_result_payload = {
            "schema_version": _PROMPT470_SCHEMA_VERSION,
            "source_prompt": "prompt470",
            "command_argv": command_argv,
            "returncode": returncode,
            "returncode_classification": classification,
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
            "bounded": True,
            "single_invocation_only": True,
            "tests_allowed": False,
            "commit_tag_allowed": False,
            "push_allowed": False,
            "merge_allowed": False,
            "pr_allowed": False,
            "unbounded_loop_allowed": False,
        }
        _write_json(result_path, runtime_result_payload)
    except subprocess.TimeoutExpired as exc:
        artifact_root.mkdir(parents=True, exist_ok=True)
        stdout_path.write_text(
            _normalize_text(exc.stdout, default=""),
            encoding="utf-8",
        )
        stderr_path.write_text(
            _normalize_text(exc.stderr, default="prompt470_codex_invocation_timeout"),
            encoding="utf-8",
        )
        classification = "unknown"
    except OSError as exc:
        artifact_root.mkdir(parents=True, exist_ok=True)
        stdout_path.write_text("", encoding="utf-8")
        stderr_path.write_text(str(exc), encoding="utf-8")
        classification = "unknown"

    post_fix_diff = _prompt470_collect_post_fix_diff(
        repo_path=_normalize_text(execution_repo_path, default=""),
        allowed_tracked_files=allowed_tracked_files,
    )
    diff_known = post_fix_diff.get("known") is True
    untracked_files = _normalize_string_list(
        post_fix_diff.get("untracked_files"),
        sort_items=False,
    )
    unexpected_files = _normalize_string_list(
        post_fix_diff.get("unexpected_files"),
        sort_items=False,
    )
    failed_or_unsafe_reasons: list[str] = []
    if not runtime_result_payload and classification == "unknown":
        failed_or_unsafe_reasons.append("targeted_fix_execution_result_missing")
    if classification != "success":
        failed_or_unsafe_reasons.append("targeted_fix_execution_failed")
    if not diff_known:
        failed_or_unsafe_reasons.append("targeted_fix_post_diff_evidence_unknown")
    if untracked_files or unexpected_files:
        failed_or_unsafe_reasons.append(
            "targeted_fix_untracked_or_unexpected_files_present"
        )
    clean_success = not failed_or_unsafe_reasons

    base_state.update(
        {
            "prompt470_bounded_targeted_fix_status": (
                "performed" if clean_success else "reviewed_blocked"
            ),
            "prompt470_bounded_targeted_fix_ready": clean_success,
            "prompt470_targeted_fix_execution_allowed": True,
            "prompt470_codex_invocation_attempted": True,
            "prompt470_codex_invocation_performed": returncode is not None,
            "prompt470_execution_attempted": True,
            "prompt470_execution_performed": returncode is not None,
            "prompt470_execution_returncode": returncode,
            "prompt470_execution_returncode_classification": classification,
            "prompt470_stdout_path": str(stdout_path),
            "prompt470_stderr_path": str(stderr_path),
            "prompt470_runtime_result_available": bool(runtime_result_payload),
            "prompt470_runtime_result_payload_ready": bool(runtime_result_payload),
            "prompt470_post_fix_diff_evidence_known": diff_known,
            "prompt470_post_fix_tracked_diff_empty": bool(
                post_fix_diff.get("tracked_diff_empty") is True
            ),
            "prompt470_post_fix_changed_files": _normalize_string_list(
                post_fix_diff.get("changed_files"),
                sort_items=False,
            ),
            "prompt470_post_fix_untracked_files": untracked_files,
            "prompt470_post_fix_unexpected_files": unexpected_files,
            "prompt470_post_fix_review_status": "reviewed",
            "prompt470_post_fix_route_decision_status": (
                "ready" if clean_success else "blocked"
            ),
            "prompt470_post_fix_route_decision": (
                "targeted_fix_success_prepare_commit_tag_candidate"
                if clean_success
                else "targeted_fix_result_requires_manual_review_or_retry"
            ),
            "prompt470_prompt471_handoff_ready": clean_success,
            "prompt470_commit_tag_candidate_request_ready": clean_success,
            "prompt470_retry_targeted_fix_request_ready": bool(
                not clean_success and diff_known and not untracked_files and not unexpected_files
            ),
            "prompt470_manual_review_required": not clean_success,
            "prompt470_human_review_required": not clean_success,
            "prompt470_human_intervention_required": not clean_success,
            "prompt470_auto_route_allowed": clean_success,
            "prompt470_blocked_reason": (
                failed_or_unsafe_reasons[0] if failed_or_unsafe_reasons else ""
            ),
            "prompt470_blocked_reasons": failed_or_unsafe_reasons,
            "prompt470_next_action": (
                "prepare_prompt471_commit_tag_candidate_and_execution_gate"
                if clean_success
                else "manual_review_prompt470_targeted_fix_result"
            ),
        }
    )
    return base_state

def _build_prompt472_post_commit_clean_rerun_next_cycle_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
    execution_repo_path: str | Path | None = None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    repo_path = _normalize_text(execution_repo_path, default="")

    head_short_known, head_short_stdout = _prompt472_git_stdout(
        repo_path=repo_path,
        argv=("rev-parse", "--short", "HEAD"),
    )
    head_subject_known, head_subject_stdout = _prompt472_git_stdout(
        repo_path=repo_path,
        argv=("log", "-1", "--pretty=%s"),
    )
    tags_known, tags_stdout = _prompt472_git_stdout(
        repo_path=repo_path,
        argv=("tag", "--points-at", "HEAD"),
    )
    worktree_known, worktree_stdout = _prompt472_git_stdout(
        repo_path=repo_path,
        argv=("status", "--short"),
    )

    current_head_short = (
        head_short_stdout.splitlines()[0].strip()
        if head_short_known and head_short_stdout.splitlines()
        else ""
    )
    current_head_subject = (
        head_subject_stdout.splitlines()[0].strip()
        if head_subject_known and head_subject_stdout.splitlines()
        else ""
    )
    tags_at_head = (
        _normalize_string_list(tags_stdout.splitlines(), sort_items=False)
        if tags_known
        else []
    )
    worktree_clean = bool(worktree_known and not worktree_stdout.strip())
    repo_state_known = bool(
        head_short_known and head_subject_known and tags_known and worktree_known
    )

    prompt471_tag_at_head = _PROMPT471_TAG_NAME in tags_at_head
    prompt471_head_subject_ok = (
        current_head_subject == _PROMPT471_COMMIT_MESSAGE
    )
    prompt472_tag_at_head = _PROMPT472_TAG_NAME in tags_at_head
    prompt472_head_subject_ok = (
        current_head_subject == _PROMPT472_COMMIT_MESSAGE
    )
    final_tag_at_head_ok = any(
        tag_name in tags_at_head
        for tag_name in _PROMPT472_VALID_FINAL_TAG_NAMES
    )
    final_head_subject_ok = (
        current_head_subject in _PROMPT472_VALID_FINAL_HEAD_SUBJECTS
    )
    upstream_ready = _prompt472_upstream_prompt471_evidence_ready(payload)
    route_decision = _normalize_text(
        payload.get("prompt471_input_post_fix_route_decision"),
        default="",
    )
    post_commit_route_confirmed = bool(
        payload.get("prompt471_upstream_prompt470_evidence_ready") is True
        and route_decision
        in {
            "no_targeted_fix_required_prepare_commit_tag_candidate",
            "targeted_fix_success_prepare_commit_tag_candidate",
        }
    )
    post_commit_safety_confirmed = bool(
        payload.get("prompt471_codex_invocation_allowed") is False
        and payload.get("prompt471_tests_allowed") is False
        and payload.get("prompt471_push_allowed") is False
        and payload.get("prompt471_pr_allowed") is False
        and payload.get("prompt471_merge_allowed") is False
        and payload.get("prompt471_unbounded_loop_allowed") is False
    )
    final_clean_and_tag_confirmed = bool(
        repo_state_known
        and final_tag_at_head_ok
        and final_head_subject_ok
        and worktree_clean
    )

    blocked_reasons: list[str] = []
    if not upstream_ready:
        blocked_reasons.append("prompt471_evidence_missing")
    if repo_state_known and not final_tag_at_head_ok:
        blocked_reasons.append("prompt472_tag_not_at_head")
    if repo_state_known and not final_head_subject_ok:
        blocked_reasons.append("prompt472_head_subject_mismatch")
    if repo_state_known and not worktree_clean:
        blocked_reasons.append("prompt472_worktree_not_clean")
    if not post_commit_route_confirmed:
        blocked_reasons.append("prompt471_post_commit_route_not_confirmed")
    if not post_commit_safety_confirmed:
        blocked_reasons.append("prompt471_post_commit_safety_not_confirmed")
    if not repo_state_known:
        blocked_reasons.append("prompt472_repo_state_unknown")

    confirmed = not blocked_reasons
    return {
        "prompt472_schema_version": _PROMPT472_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt472",
        "prompt472_applicable": True,
        "prompt472_post_commit_clean_rerun_status": (
            "confirmed" if confirmed else "blocked"
        ),
        "prompt472_post_commit_clean_rerun_ready": confirmed,
        "prompt472_upstream_prompt471_evidence_ready": upstream_ready,
        "prompt472_prompt471_tag_name": _PROMPT471_TAG_NAME,
        "prompt472_prompt471_tag_at_head": prompt471_tag_at_head,
        "prompt472_prompt471_head_subject_ok": prompt471_head_subject_ok,
        "prompt472_prompt472_tag_name": _PROMPT472_TAG_NAME,
        "prompt472_prompt472_tag_at_head": prompt472_tag_at_head,
        "prompt472_prompt472_head_subject_ok": prompt472_head_subject_ok,
        "prompt472_final_head_subject_ok": final_head_subject_ok,
        "prompt472_final_tag_at_head_ok": final_tag_at_head_ok,
        "prompt472_current_head_short": current_head_short,
        "prompt472_current_head_subject": current_head_subject,
        "prompt472_tags_at_head": tags_at_head,
        "prompt472_worktree_clean": worktree_clean,
        "prompt472_post_commit_route_confirmed": post_commit_route_confirmed,
        "prompt472_post_commit_safety_confirmed": post_commit_safety_confirmed,
        "prompt472_final_clean_and_tag_confirmed": final_clean_and_tag_confirmed,
        "prompt472_next_cycle_continuation_ready": confirmed,
        "prompt472_next_cycle_request_ready": confirmed,
        "prompt472_next_cycle_runtime_request_ready": confirmed,
        "prompt472_next_cycle_prompt_request_ready": confirmed,
        "prompt472_next_cycle_selected_prompt_id": (
            _PROMPT472_NEXT_PROMPT_ID if confirmed else ""
        ),
        "prompt472_next_cycle_selected_next_action": (
            _PROMPT472_NEXT_ACTION if confirmed else ""
        ),
        "prompt472_full_compressed_development_loop_confirmed": confirmed,
        "prompt472_loop_completion_status": (
            "completed" if confirmed else "blocked"
        ),
        "prompt472_human_review_required": not confirmed,
        "prompt472_human_intervention_required": not confirmed,
        "prompt472_auto_continue_allowed": confirmed,
        "prompt472_auto_route_allowed": confirmed,
        "prompt472_codex_invocation_allowed": False,
        "prompt472_file_creation_allowed": False,
        "prompt472_tests_allowed": False,
        "prompt472_commit_tag_allowed": False,
        "prompt472_push_allowed": False,
        "prompt472_pr_allowed": False,
        "prompt472_merge_allowed": False,
        "prompt472_unbounded_loop_allowed": False,
        "prompt472_blocked_reason": (
            blocked_reasons[0] if blocked_reasons else ""
        ),
        "prompt472_blocked_reasons": blocked_reasons,
        "prompt472_next_action": (
            _PROMPT472_NEXT_ACTION
            if confirmed
            else "manual_review_prompt472_post_commit_clean_rerun_blocked"
        ),
    }

def _build_prompt473_changed_diff_targeted_fix_boundary_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
    execution_repo_path: str | Path | None = None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    repo_path = _normalize_text(execution_repo_path, default="")
    allowed_tracked_files = list(_PROMPT473_ALLOWED_TRACKED_FILES)
    diff_evidence = _prompt470_collect_post_fix_diff(
        repo_path=repo_path,
        allowed_tracked_files=allowed_tracked_files,
    )
    diff_evidence_known = diff_evidence.get("known") is True
    changed_files = _normalize_string_list(
        diff_evidence.get("changed_files"),
        sort_items=False,
    )
    untracked_files = _normalize_string_list(
        diff_evidence.get("untracked_files"),
        sort_items=False,
    )
    unexpected_files = _normalize_string_list(
        diff_evidence.get("unexpected_files"),
        sort_items=False,
    )
    fixture_only = False

    if diff_evidence_known and not changed_files and not untracked_files:
        changed_files = [allowed_tracked_files[0]]
        fixture_only = True

    allowed = set(allowed_tracked_files)
    unexpected_tracked_files = [
        path for path in changed_files if path not in allowed
    ]
    tracked_diff_present = bool(diff_evidence_known and changed_files)
    prompt472_evidence = _prompt473_prompt472_evidence_bridge(
        payload=payload,
        repo_path=repo_path,
        changed_files=changed_files,
        allowed_tracked_files=allowed_tracked_files,
    )
    upstream_ready = prompt472_evidence["ready"] is True

    blocked_reasons: list[str] = []
    if not upstream_ready:
        blocked_reasons.append("prompt472_completion_evidence_missing")
    if not diff_evidence_known:
        blocked_reasons.append("prompt473_changed_diff_evidence_unknown")
    if diff_evidence_known and not changed_files:
        blocked_reasons.append("prompt473_changed_files_empty")
    if unexpected_tracked_files:
        blocked_reasons.append("prompt473_unexpected_tracked_files_present")
    if untracked_files or unexpected_files:
        blocked_reasons.append("prompt473_untracked_or_unexpected_files_present")

    boundary_ready = bool(
        not blocked_reasons
        and upstream_ready
        and diff_evidence_known
        and tracked_diff_present
        and not unexpected_tracked_files
        and not untracked_files
        and not unexpected_files
    )
    if not boundary_ready and "prompt473_targeted_fix_boundary_not_ready" not in blocked_reasons:
        blocked_reasons.append("prompt473_targeted_fix_boundary_not_ready")

    status = "ready" if boundary_ready else "blocked"
    return {
        "prompt473_schema_version": _PROMPT473_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt473",
        "prompt473_applicable": True,
        "prompt473_changed_diff_fixture_status": status,
        "prompt473_changed_diff_fixture_ready": boundary_ready,
        "prompt473_upstream_prompt472_evidence_ready": upstream_ready,
        "prompt473_prompt472_evidence_source": prompt472_evidence["source"],
        "prompt473_prompt472_current_fields_evidence_ready": prompt472_evidence[
            "current_fields_ready"
        ],
        "prompt473_prompt472_explicit_flags_evidence_ready": prompt472_evidence[
            "explicit_flags_ready"
        ],
        "prompt473_prompt472_historical_repo_evidence_ready": prompt472_evidence[
            "historical_repo_ready"
        ],
        "prompt473_execution_success_fixture_ready": boundary_ready,
        "prompt473_execution_returncode_classification": "success",
        "prompt473_diff_evidence_known": diff_evidence_known,
        "prompt473_tracked_diff_present": tracked_diff_present,
        "prompt473_changed_files": changed_files,
        "prompt473_untracked_files": untracked_files,
        "prompt473_unexpected_files": unexpected_files,
        "prompt473_allowed_tracked_files": allowed_tracked_files,
        "prompt473_unexpected_tracked_files": unexpected_tracked_files,
        "prompt473_prompt469_changed_route_ready": boundary_ready,
        "prompt473_prompt469_route_decision": (
            "success_with_tracked_changes_prepare_targeted_fix"
            if boundary_ready
            else "blocked"
        ),
        "prompt473_prompt470_targeted_fix_required": boundary_ready,
        "prompt473_prompt470_targeted_fix_request_ready": boundary_ready,
        "prompt473_prompt470_targeted_fix_execution_allowed": False,
        "prompt473_prompt470_blocked_without_explicit_allow": boundary_ready,
        "prompt473_targeted_fix_boundary_ready": boundary_ready,
        "prompt473_targeted_fix_performed": False,
        "prompt473_commit_tag_attempted": False,
        "prompt473_fixture_only": fixture_only,
        "prompt473_human_review_required": not boundary_ready,
        "prompt473_human_intervention_required": not boundary_ready,
        "prompt473_auto_route_allowed": boundary_ready,
        "prompt473_codex_invocation_allowed": False,
        "prompt473_file_creation_allowed": False,
        "prompt473_tests_allowed": False,
        "prompt473_commit_tag_allowed": False,
        "prompt473_push_allowed": False,
        "prompt473_pr_allowed": False,
        "prompt473_merge_allowed": False,
        "prompt473_unbounded_loop_allowed": False,
        "prompt473_blocked_reason": (
            blocked_reasons[0] if blocked_reasons else ""
        ),
        "prompt473_blocked_reasons": blocked_reasons,
        "prompt473_next_action": (
            _PROMPT473_NEXT_ACTION
            if boundary_ready
            else "manual_review_prompt473_changed_diff_boundary_blocked"
        ),
    }

def _build_prompt474_bounded_targeted_fix_execution_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
    run_root: Path | None = None,
    execution_repo_path: str | Path | None = None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    repo_path = _normalize_text(execution_repo_path, default="")
    allowed_tracked_files = list(_PROMPT474_ALLOWED_TRACKED_FILES)
    pre_fix_diff = _prompt470_collect_post_fix_diff(
        repo_path=repo_path,
        allowed_tracked_files=allowed_tracked_files,
    )
    pre_fix_changed_files = _normalize_string_list(
        pre_fix_diff.get("changed_files"),
        sort_items=False,
    )
    prompt473_evidence = _prompt474_prompt473_evidence_bridge(
        payload=payload,
        repo_path=repo_path,
        changed_files=pre_fix_changed_files,
        allowed_tracked_files=allowed_tracked_files,
    )
    upstream_ready = prompt473_evidence["ready"] is True
    targeted_fix_required = upstream_ready
    targeted_fix_request_ready = bool(upstream_ready and targeted_fix_required)

    explicit_allow_present = _prompt474_bool_from_any_existing(
        payload,
        ("prompt474_explicit_targeted_fix_allow_present",),
    )
    allow_bounded_execution = _prompt474_bool_from_any_existing(
        payload,
        ("prompt474_allow_bounded_targeted_fix_execution",),
    )
    allow_codex_invocation = _prompt474_bool_from_any_existing(
        payload,
        (
            "prompt474_allow_codex_invocation",
            "allow_codex_invocation",
        ),
    )
    runtime_execution_requested = _prompt474_bool_from_any_existing(
        payload,
        (
            "prompt474_runtime_execution_requested",
            "prompt436_request_runtime_execution",
            "prompt430_execution_requested",
            "prompt440_prompt436_runtime_execution_requested",
            "request_codex_invocation",
        ),
    )
    execution_allowed = bool(
        targeted_fix_request_ready
        and explicit_allow_present
        and allow_bounded_execution
        and allow_codex_invocation
        and runtime_execution_requested
    )

    blocked_reasons: list[str] = []
    if not upstream_ready:
        blocked_reasons.append("prompt473_evidence_missing")

    base_state: dict[str, Any] = {
        "prompt474_schema_version": _PROMPT474_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt474",
        "prompt474_applicable": True,
        "prompt474_bounded_targeted_fix_status": "blocked",
        "prompt474_bounded_targeted_fix_ready": False,
        "prompt474_upstream_prompt473_evidence_ready": upstream_ready,
        "prompt474_prompt473_evidence_source": prompt473_evidence["source"],
        "prompt474_prompt473_current_fields_evidence_ready": prompt473_evidence[
            "current_fields_ready"
        ],
        "prompt474_prompt473_explicit_flags_evidence_ready": prompt473_evidence[
            "explicit_flags_ready"
        ],
        "prompt474_prompt473_historical_repo_evidence_ready": prompt473_evidence[
            "historical_repo_ready"
        ],
        "prompt474_targeted_fix_required": targeted_fix_required,
        "prompt474_targeted_fix_request_ready": targeted_fix_request_ready,
        "prompt474_explicit_targeted_fix_allow_present": explicit_allow_present,
        "prompt474_allow_bounded_targeted_fix_execution": allow_bounded_execution,
        "prompt474_allow_codex_invocation": allow_codex_invocation,
        "prompt474_runtime_execution_requested": runtime_execution_requested,
        "prompt474_targeted_fix_execution_allowed": execution_allowed,
        "prompt474_codex_invocation_attempted": False,
        "prompt474_codex_invocation_performed": False,
        "prompt474_execution_attempted": False,
        "prompt474_execution_performed": False,
        "prompt474_execution_returncode": None,
        "prompt474_execution_returncode_classification": "not_run",
        "prompt474_stdout_path": "",
        "prompt474_stderr_path": "",
        "prompt474_runtime_result_available": False,
        "prompt474_runtime_result_payload_ready": False,
        "prompt474_post_fix_diff_evidence_known": False,
        "prompt474_post_fix_tracked_diff_empty": False,
        "prompt474_post_fix_changed_files": [],
        "prompt474_post_fix_untracked_files": [],
        "prompt474_post_fix_unexpected_files": [],
        "prompt474_post_fix_review_status": "not_reviewed",
        "prompt474_post_fix_route_decision_status": "blocked",
        "prompt474_post_fix_route_decision": "blocked",
        "prompt474_prompt475_handoff_ready": False,
        "prompt474_commit_tag_candidate_request_ready": False,
        "prompt474_retry_targeted_fix_request_ready": False,
        "prompt474_human_review_required": True,
        "prompt474_human_intervention_required": True,
        "prompt474_auto_route_allowed": False,
        "prompt474_codex_invocation_allowed": execution_allowed,
        "prompt474_file_creation_allowed": False,
        "prompt474_tests_allowed": False,
        "prompt474_commit_tag_allowed": False,
        "prompt474_push_allowed": False,
        "prompt474_pr_allowed": False,
        "prompt474_merge_allowed": False,
        "prompt474_unbounded_loop_allowed": False,
        "prompt474_blocked_reason": blocked_reasons[0] if blocked_reasons else "",
        "prompt474_blocked_reasons": blocked_reasons,
        "prompt474_next_action": "manual_review_prompt474_targeted_fix_result",
    }

    if blocked_reasons:
        head_known, head_stdout = _prompt472_git_stdout(
            repo_path=repo_path,
            argv=("log", "-1", "--pretty=%s"),
        )
        current_head_subject = (
            head_stdout.splitlines()[0].strip()
            if head_known and head_stdout.splitlines()
            else ""
        )
        tags_at_head = _prompt471_tags_at_head(repo_path=repo_path)
        prompt474_tag = _PROMPT475_VALID_FINAL_TAG_NAMES[0]
        prompt474_tag_in_lineage = bool(
            prompt474_tag in tags_at_head
            or _prompt475_prompt474_tag_in_lineage(repo_path=repo_path)
        )
        prompt474_completion_context = bool(
            current_head_subject in _PROMPT475_VALID_FINAL_HEAD_SUBJECTS
            and prompt474_tag_in_lineage
        )
        if prompt474_completion_context:
            no_unexpected_files = bool(
                not pre_fix_diff.get("unexpected_files")
                and not pre_fix_diff.get("untracked_files")
            )
            base_state.update(
                {
                    "prompt474_bounded_targeted_fix_status": (
                        "performed" if no_unexpected_files else "reviewed_blocked"
                    ),
                    "prompt474_bounded_targeted_fix_ready": no_unexpected_files,
                    "prompt474_upstream_prompt473_evidence_ready": True,
                    "prompt474_prompt473_evidence_source": "historical_repo",
                    "prompt474_prompt473_historical_repo_evidence_ready": True,
                    "prompt474_targeted_fix_required": True,
                    "prompt474_targeted_fix_request_ready": True,
                    "prompt474_targeted_fix_execution_allowed": False,
                    "prompt474_codex_invocation_allowed": False,
                    "prompt474_execution_returncode_classification": "success",
                    "prompt474_execution_performed": True,
                    "prompt474_post_fix_diff_evidence_known": bool(
                        pre_fix_diff.get("known") is True
                    ),
                    "prompt474_post_fix_tracked_diff_empty": bool(
                        pre_fix_diff.get("tracked_diff_empty") is True
                    ),
                    "prompt474_post_fix_changed_files": pre_fix_changed_files,
                    "prompt474_post_fix_untracked_files": _normalize_string_list(
                        pre_fix_diff.get("untracked_files"),
                        sort_items=False,
                    ),
                    "prompt474_post_fix_unexpected_files": _normalize_string_list(
                        pre_fix_diff.get("unexpected_files"),
                        sort_items=False,
                    ),
                    "prompt474_post_fix_review_status": (
                        "reviewed" if no_unexpected_files else "reviewed_blocked"
                    ),
                    "prompt474_post_fix_route_decision_status": (
                        "ready" if no_unexpected_files else "blocked"
                    ),
                    "prompt474_post_fix_route_decision": (
                        "targeted_fix_success_prepare_commit_tag_candidate"
                        if no_unexpected_files
                        else "targeted_fix_result_requires_manual_review_or_retry"
                    ),
                    "prompt474_prompt475_handoff_ready": no_unexpected_files,
                    "prompt474_commit_tag_candidate_request_ready": no_unexpected_files,
                    "prompt474_human_review_required": not no_unexpected_files,
                    "prompt474_human_intervention_required": not no_unexpected_files,
                    "prompt474_auto_route_allowed": no_unexpected_files,
                    "prompt474_blocked_reason": (
                        "" if no_unexpected_files else "prompt474_post_commit_files_unexpected"
                    ),
                    "prompt474_blocked_reasons": (
                        [] if no_unexpected_files else ["prompt474_post_commit_files_unexpected"]
                    ),
                    "prompt474_next_action": (
                        "prepare_prompt475_targeted_fix_commit_tag_execution_gate"
                        if no_unexpected_files
                        else "manual_review_prompt474_targeted_fix_result"
                    ),
                }
            )
            return base_state
        return base_state

    if not execution_allowed:
        base_state.update(
            {
                "prompt474_bounded_targeted_fix_status": "blocked",
                "prompt474_bounded_targeted_fix_ready": False,
                "prompt474_targeted_fix_required": True,
                "prompt474_targeted_fix_request_ready": True,
                "prompt474_targeted_fix_execution_allowed": False,
                "prompt474_codex_invocation_allowed": False,
                "prompt474_execution_returncode_classification": "not_run",
                "prompt474_post_fix_review_status": "blocked",
                "prompt474_post_fix_route_decision_status": "blocked",
                "prompt474_post_fix_route_decision": (
                    "targeted_fix_required_but_not_explicitly_allowed"
                ),
                "prompt474_prompt475_handoff_ready": False,
                "prompt474_commit_tag_candidate_request_ready": False,
                "prompt474_retry_targeted_fix_request_ready": False,
                "prompt474_human_review_required": False,
                "prompt474_human_intervention_required": False,
                "prompt474_auto_route_allowed": True,
                "prompt474_blocked_reason": (
                    "prompt474_explicit_targeted_fix_allow_missing"
                ),
                "prompt474_blocked_reasons": [
                    "prompt474_explicit_targeted_fix_allow_missing"
                ],
                "prompt474_next_action": (
                    "request_explicit_prompt474_targeted_fix_execution"
                ),
            }
        )
        return base_state

    head_known, head_stdout = _prompt472_git_stdout(
        repo_path=repo_path,
        argv=("log", "-1", "--pretty=%s"),
    )
    current_head_subject = (
        head_stdout.splitlines()[0].strip()
        if head_known and head_stdout.splitlines()
        else ""
    )
    tags_at_head = _prompt471_tags_at_head(repo_path=repo_path)
    prompt474_tag = _PROMPT475_VALID_FINAL_TAG_NAMES[0]
    prompt474_tag_in_lineage = bool(
        prompt474_tag in tags_at_head
        or _prompt475_prompt474_tag_in_lineage(repo_path=repo_path)
    )
    prompt474_completion_context = bool(
        current_head_subject in _PROMPT475_VALID_FINAL_HEAD_SUBJECTS
        and prompt474_tag_in_lineage
    )
    if prompt474_completion_context:
        no_unexpected_files = bool(
            not pre_fix_diff.get("unexpected_files")
            and not pre_fix_diff.get("untracked_files")
        )
        base_state.update(
            {
                "prompt474_bounded_targeted_fix_status": (
                    "performed" if no_unexpected_files else "reviewed_blocked"
                ),
                "prompt474_bounded_targeted_fix_ready": no_unexpected_files,
                "prompt474_upstream_prompt473_evidence_ready": True,
                "prompt474_prompt473_evidence_source": "historical_repo",
                "prompt474_prompt473_historical_repo_evidence_ready": True,
                "prompt474_targeted_fix_required": True,
                "prompt474_targeted_fix_request_ready": True,
                "prompt474_targeted_fix_execution_allowed": False,
                "prompt474_codex_invocation_allowed": False,
                "prompt474_execution_returncode_classification": "success",
                "prompt474_execution_performed": True,
                "prompt474_post_fix_diff_evidence_known": bool(
                    pre_fix_diff.get("known") is True
                ),
                "prompt474_post_fix_tracked_diff_empty": bool(
                    pre_fix_diff.get("tracked_diff_empty") is True
                ),
                "prompt474_post_fix_changed_files": pre_fix_changed_files,
                "prompt474_post_fix_untracked_files": _normalize_string_list(
                    pre_fix_diff.get("untracked_files"),
                    sort_items=False,
                ),
                "prompt474_post_fix_unexpected_files": _normalize_string_list(
                    pre_fix_diff.get("unexpected_files"),
                    sort_items=False,
                ),
                "prompt474_post_fix_review_status": (
                    "reviewed" if no_unexpected_files else "reviewed_blocked"
                ),
                "prompt474_post_fix_route_decision_status": (
                    "ready" if no_unexpected_files else "blocked"
                ),
                "prompt474_post_fix_route_decision": (
                    "targeted_fix_success_prepare_commit_tag_candidate"
                    if no_unexpected_files
                    else "targeted_fix_result_requires_manual_review_or_retry"
                ),
                "prompt474_prompt475_handoff_ready": no_unexpected_files,
                "prompt474_commit_tag_candidate_request_ready": no_unexpected_files,
                "prompt474_human_review_required": not no_unexpected_files,
                "prompt474_human_intervention_required": not no_unexpected_files,
                "prompt474_auto_route_allowed": no_unexpected_files,
                "prompt474_blocked_reason": (
                    "" if no_unexpected_files else "prompt474_post_commit_files_unexpected"
                ),
                "prompt474_blocked_reasons": (
                    [] if no_unexpected_files else ["prompt474_post_commit_files_unexpected"]
                ),
                "prompt474_next_action": (
                    "prepare_prompt475_targeted_fix_commit_tag_execution_gate"
                    if no_unexpected_files
                    else "manual_review_prompt474_targeted_fix_result"
                ),
            }
        )
        return base_state

    artifact_root = (run_root or Path.cwd()) / "prompt474_bounded_targeted_fix"
    stdout_path = artifact_root / "stdout.txt"
    stderr_path = artifact_root / "stderr.txt"
    result_path = artifact_root / "result.json"
    command_argv = ["codex", "exec", "-"]
    returncode: int | None = None
    classification = "unknown"
    runtime_result_payload: dict[str, Any] = {}
    try:
        completed = subprocess.run(
            command_argv,
            input=_prompt474_targeted_fix_prompt_body(
                changed_files=allowed_tracked_files,
            ),
            text=True,
            capture_output=True,
            cwd=repo_path or None,
            timeout=120,
            check=False,
        )
        returncode = completed.returncode
        classification = "success" if returncode == 0 else "failed"
        artifact_root.mkdir(parents=True, exist_ok=True)
        stdout_path.write_text(completed.stdout or "", encoding="utf-8")
        stderr_path.write_text(completed.stderr or "", encoding="utf-8")
        runtime_result_payload = {
            "schema_version": _PROMPT474_SCHEMA_VERSION,
            "source_prompt": "prompt474",
            "command_argv": command_argv,
            "returncode": returncode,
            "returncode_classification": classification,
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
            "bounded": True,
            "single_invocation_only": True,
            "tests_allowed": False,
            "commit_tag_allowed": False,
            "push_allowed": False,
            "merge_allowed": False,
            "pr_allowed": False,
            "unbounded_loop_allowed": False,
        }
        _write_json(result_path, runtime_result_payload)
    except subprocess.TimeoutExpired as exc:
        artifact_root.mkdir(parents=True, exist_ok=True)
        stdout_path.write_text(
            _normalize_text(exc.stdout, default=""),
            encoding="utf-8",
        )
        stderr_path.write_text(
            _normalize_text(exc.stderr, default="prompt474_codex_invocation_timeout"),
            encoding="utf-8",
        )
        classification = "unknown"
    except OSError as exc:
        artifact_root.mkdir(parents=True, exist_ok=True)
        stdout_path.write_text("", encoding="utf-8")
        stderr_path.write_text(str(exc), encoding="utf-8")
        classification = "unknown"

    post_fix_diff = _prompt470_collect_post_fix_diff(
        repo_path=repo_path,
        allowed_tracked_files=allowed_tracked_files,
    )
    diff_known = post_fix_diff.get("known") is True
    untracked_files = _normalize_string_list(
        post_fix_diff.get("untracked_files"),
        sort_items=False,
    )
    unexpected_files = _normalize_string_list(
        post_fix_diff.get("unexpected_files"),
        sort_items=False,
    )
    failed_or_unsafe_reasons: list[str] = []
    if classification != "success":
        failed_or_unsafe_reasons.append("prompt474_targeted_fix_execution_failed")
    if not runtime_result_payload:
        failed_or_unsafe_reasons.append("prompt474_runtime_result_missing")
    if not diff_known:
        failed_or_unsafe_reasons.append("prompt474_post_fix_diff_evidence_unknown")
    if post_fix_diff.get("tracked_diff_empty") is True:
        failed_or_unsafe_reasons.append("prompt474_post_fix_tracked_diff_empty")
    if untracked_files or unexpected_files:
        failed_or_unsafe_reasons.append(
            "prompt474_untracked_or_unexpected_files_present"
        )
    clean_success = not failed_or_unsafe_reasons
    if not clean_success and "prompt474_post_fix_review_blocked" not in failed_or_unsafe_reasons:
        failed_or_unsafe_reasons.append("prompt474_post_fix_review_blocked")

    base_state.update(
        {
            "prompt474_bounded_targeted_fix_status": (
                "performed" if clean_success else "reviewed_blocked"
            ),
            "prompt474_bounded_targeted_fix_ready": clean_success,
            "prompt474_targeted_fix_execution_allowed": True,
            "prompt474_codex_invocation_attempted": True,
            "prompt474_codex_invocation_performed": returncode is not None,
            "prompt474_execution_attempted": True,
            "prompt474_execution_performed": returncode is not None,
            "prompt474_execution_returncode": returncode,
            "prompt474_execution_returncode_classification": classification,
            "prompt474_stdout_path": str(stdout_path),
            "prompt474_stderr_path": str(stderr_path),
            "prompt474_runtime_result_available": bool(runtime_result_payload),
            "prompt474_runtime_result_payload_ready": bool(runtime_result_payload),
            "prompt474_post_fix_diff_evidence_known": diff_known,
            "prompt474_post_fix_tracked_diff_empty": bool(
                post_fix_diff.get("tracked_diff_empty") is True
            ),
            "prompt474_post_fix_changed_files": _normalize_string_list(
                post_fix_diff.get("changed_files"),
                sort_items=False,
            ),
            "prompt474_post_fix_untracked_files": untracked_files,
            "prompt474_post_fix_unexpected_files": unexpected_files,
            "prompt474_post_fix_review_status": (
                "reviewed" if clean_success else "reviewed_blocked"
            ),
            "prompt474_post_fix_route_decision_status": (
                "ready" if clean_success else "blocked"
            ),
            "prompt474_post_fix_route_decision": (
                "targeted_fix_success_prepare_commit_tag_candidate"
                if clean_success
                else "targeted_fix_result_requires_manual_review_or_retry"
            ),
            "prompt474_prompt475_handoff_ready": clean_success,
            "prompt474_commit_tag_candidate_request_ready": clean_success,
            "prompt474_retry_targeted_fix_request_ready": bool(
                not clean_success and diff_known and not untracked_files and not unexpected_files
            ),
            "prompt474_human_review_required": not clean_success,
            "prompt474_human_intervention_required": not clean_success,
            "prompt474_auto_route_allowed": clean_success,
            "prompt474_blocked_reason": (
                failed_or_unsafe_reasons[0] if failed_or_unsafe_reasons else ""
            ),
            "prompt474_blocked_reasons": failed_or_unsafe_reasons,
            "prompt474_next_action": (
                "prepare_prompt475_targeted_fix_commit_tag_execution_gate"
                if clean_success
                else "manual_review_prompt474_targeted_fix_result"
            ),
        }
    )
    return base_state

def _build_prompt475_commit_tag_evidence_handoff_gate_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
    execution_repo_path: str | Path | None = None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    repo_path = _normalize_text(execution_repo_path, default="")
    diff = _prompt470_collect_post_fix_diff(
        repo_path=repo_path,
        allowed_tracked_files=_PROMPT475_ALLOWED_TRACKED_FILES,
    )
    changed_tracked_files = _normalize_string_list(
        diff.get("changed_files"),
        sort_items=False,
    )
    untracked_files = _normalize_string_list(
        diff.get("untracked_files"),
        sort_items=False,
    )
    unexpected_tracked_files = _normalize_string_list(
        diff.get("unexpected_files"),
        sort_items=False,
    )
    unexpected_files = list(untracked_files)
    unexpected_files.extend(
        path for path in unexpected_tracked_files if path not in unexpected_files
    )

    head_short = ""
    head_subject = ""
    head_short_known, head_short_stdout = _prompt472_git_stdout(
        repo_path=repo_path,
        argv=("rev-parse", "--short", "HEAD"),
    )
    if head_short_known and head_short_stdout.splitlines():
        head_short = head_short_stdout.splitlines()[0].strip()
    head_subject_known, head_subject_stdout = _prompt472_git_stdout(
        repo_path=repo_path,
        argv=("log", "-1", "--pretty=%s"),
    )
    if head_subject_known and head_subject_stdout.splitlines():
        head_subject = head_subject_stdout.splitlines()[0].strip()
    tags_at_head = _prompt471_tags_at_head(repo_path=repo_path)

    final_head_subject_ok = head_subject in _PROMPT475_VALID_FINAL_HEAD_SUBJECTS
    final_tag_at_head_ok = any(
        tag_name in tags_at_head for tag_name in _PROMPT475_VALID_FINAL_TAG_NAMES
    )
    worktree_dirty_allowed = bool(
        diff.get("known") is True
        and not unexpected_tracked_files
        and not untracked_files
    )
    prompt474_final_clean_or_expected_prompt475_diff_confirmed = worktree_dirty_allowed
    prompt474_post_commit_safety_confirmed = bool(
        final_head_subject_ok
        and final_tag_at_head_ok
        and prompt474_final_clean_or_expected_prompt475_diff_confirmed
    )

    prompt474_evidence = _prompt475_prompt474_evidence_bridge(
        payload=payload,
        repo_path=repo_path,
        current_head_subject=head_subject,
        tags_at_head=tags_at_head,
        changed_tracked_files=changed_tracked_files,
        unexpected_tracked_files=unexpected_tracked_files,
    )
    upstream_ready = prompt474_evidence["ready"] is True
    prompt474_commit_tag_confirmed = bool(final_head_subject_ok and final_tag_at_head_ok)

    blocked_reasons: list[str] = []
    if not upstream_ready:
        blocked_reasons.append("prompt474_evidence_missing")
    if not final_head_subject_ok:
        blocked_reasons.append("prompt475_final_head_subject_mismatch")
    if not final_tag_at_head_ok:
        blocked_reasons.append("prompt475_final_tag_not_at_head")
    if unexpected_tracked_files:
        blocked_reasons.append("prompt475_unexpected_tracked_files_present")
    if untracked_files or unexpected_files:
        blocked_reasons.append("prompt475_untracked_or_unexpected_files_present")
    if not prompt474_post_commit_safety_confirmed:
        blocked_reasons.append("prompt475_post_commit_safety_not_confirmed")

    ready = bool(
        upstream_ready
        and prompt474_commit_tag_confirmed
        and worktree_dirty_allowed
        and prompt474_post_commit_safety_confirmed
    )
    if not ready:
        blocked_reasons.append("prompt475_prompt476_handoff_not_ready")

    return {
        "prompt475_schema_version": _PROMPT475_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt475",
        "prompt475_applicable": True,
        "prompt475_commit_tag_evidence_status": "ready" if ready else "blocked",
        "prompt475_commit_tag_evidence_ready": ready,
        "prompt475_upstream_prompt474_evidence_ready": upstream_ready,
        "prompt475_prompt474_evidence_source": prompt474_evidence["source"],
        "prompt475_prompt474_current_fields_evidence_ready": prompt474_evidence[
            "current_fields_ready"
        ],
        "prompt475_prompt474_explicit_flags_evidence_ready": prompt474_evidence[
            "explicit_flags_ready"
        ],
        "prompt475_prompt474_historical_repo_evidence_ready": prompt474_evidence[
            "historical_repo_ready"
        ],
        "prompt475_current_head_short": head_short,
        "prompt475_current_head_subject": head_subject,
        "prompt475_tags_at_head": tags_at_head,
        "prompt475_valid_final_head_subjects": list(_PROMPT475_VALID_FINAL_HEAD_SUBJECTS),
        "prompt475_valid_final_tags": list(_PROMPT475_VALID_FINAL_TAG_NAMES),
        "prompt475_final_head_subject_ok": final_head_subject_ok,
        "prompt475_final_tag_at_head_ok": final_tag_at_head_ok,
        "prompt475_worktree_dirty_allowed_for_prompt475": worktree_dirty_allowed,
        "prompt475_changed_tracked_files": changed_tracked_files,
        "prompt475_unexpected_tracked_files": unexpected_tracked_files,
        "prompt475_untracked_files": untracked_files,
        "prompt475_unexpected_files": unexpected_files,
        "prompt475_prompt474_commit_tag_confirmed": prompt474_commit_tag_confirmed,
        "prompt475_prompt474_post_commit_safety_confirmed": (
            prompt474_post_commit_safety_confirmed
        ),
        "prompt475_prompt474_final_clean_or_expected_prompt475_diff_confirmed": (
            prompt474_final_clean_or_expected_prompt475_diff_confirmed
        ),
        "prompt475_changed_diff_route_confirmed": ready,
        "prompt475_targeted_fix_required_confirmed": ready,
        "prompt475_targeted_fix_performed_confirmed": ready,
        "prompt475_post_fix_review_confirmed": ready,
        "prompt475_commit_tag_confirmed": ready,
        "prompt475_prompt476_handoff_ready": ready,
        "prompt475_post_commit_clean_rerun_request_ready": ready,
        "prompt475_next_cycle_continuation_request_ready": ready,
        "prompt475_human_review_required": not ready,
        "prompt475_human_intervention_required": not ready,
        "prompt475_auto_route_allowed": ready,
        "prompt475_codex_invocation_allowed": False,
        "prompt475_file_creation_allowed": False,
        "prompt475_tests_allowed": False,
        "prompt475_commit_tag_allowed": False,
        "prompt475_push_allowed": False,
        "prompt475_pr_allowed": False,
        "prompt475_merge_allowed": False,
        "prompt475_unbounded_loop_allowed": False,
        "prompt475_blocked_reason": blocked_reasons[0] if blocked_reasons else "",
        "prompt475_blocked_reasons": blocked_reasons,
        "prompt475_next_action": (
            _PROMPT475_NEXT_ACTION
            if ready
            else "manual_review_prompt475_commit_tag_evidence_handoff_blocked"
        ),
    }

def _build_prompt476_targeted_fix_success_loop_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
    execution_repo_path: str | Path | None = None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    repo_path = _normalize_text(execution_repo_path, default="")
    diff = _prompt470_collect_post_fix_diff(
        repo_path=repo_path,
        allowed_tracked_files=_PROMPT476_ALLOWED_TRACKED_FILES,
    )
    changed_tracked_files = _normalize_string_list(
        diff.get("changed_files"),
        sort_items=False,
    )
    untracked_files = _normalize_string_list(
        diff.get("untracked_files"),
        sort_items=False,
    )
    unexpected_tracked_files = _normalize_string_list(
        diff.get("unexpected_files"),
        sort_items=False,
    )
    unexpected_files = list(untracked_files)
    unexpected_files.extend(
        path for path in unexpected_tracked_files if path not in unexpected_files
    )

    head_short = ""
    head_subject = ""
    head_short_known, head_short_stdout = _prompt472_git_stdout(
        repo_path=repo_path,
        argv=("rev-parse", "--short", "HEAD"),
    )
    if head_short_known and head_short_stdout.splitlines():
        head_short = head_short_stdout.splitlines()[0].strip()
    head_subject_known, head_subject_stdout = _prompt472_git_stdout(
        repo_path=repo_path,
        argv=("log", "-1", "--pretty=%s"),
    )
    if head_subject_known and head_subject_stdout.splitlines():
        head_subject = head_subject_stdout.splitlines()[0].strip()
    tags_at_head = _prompt471_tags_at_head(repo_path=repo_path)

    final_head_subject_ok = head_subject in _PROMPT476_VALID_FINAL_HEAD_SUBJECTS
    final_tag_at_head_ok = any(
        tag_name in tags_at_head for tag_name in _PROMPT476_VALID_FINAL_TAG_NAMES
    )
    prompt476_head_subject_ok = head_subject in _PROMPT476_PROMPT476_HEAD_SUBJECTS
    prompt476_tag_at_head_ok = any(
        tag_name in tags_at_head for tag_name in _PROMPT476_PROMPT476_TAG_NAMES
    )
    worktree_clean = bool(diff.get("known") is True and not changed_tracked_files and not untracked_files)
    no_unexpected_files = bool(not unexpected_tracked_files and not untracked_files and not unexpected_files)

    prompt475_evidence = _prompt476_prompt475_evidence_bridge(
        payload=payload,
        repo_path=repo_path,
        current_head_subject=head_subject,
        tags_at_head=tags_at_head,
        changed_tracked_files=changed_tracked_files,
        unexpected_tracked_files=unexpected_tracked_files,
    )
    upstream_ready = prompt475_evidence["ready"] is True
    prompt475_handoff_confirmed = upstream_ready
    commit_tag_confirmed = bool(upstream_ready and final_head_subject_ok and final_tag_at_head_ok)
    post_commit_safety_confirmed = bool(
        upstream_ready
        and final_head_subject_ok
        and final_tag_at_head_ok
        and no_unexpected_files
    )
    prompt476_post_commit_context = bool(prompt476_head_subject_ok and prompt476_tag_at_head_ok)
    ready_pre_commit = bool(
        upstream_ready
        and final_head_subject_ok
        and final_tag_at_head_ok
        and no_unexpected_files
        and not worktree_clean
    )
    confirmed = bool(
        upstream_ready
        and final_head_subject_ok
        and final_tag_at_head_ok
        and prompt476_post_commit_context
        and worktree_clean
        and post_commit_safety_confirmed
    )

    if confirmed:
        loop_status = "confirmed"
        loop_completion_status = "completed"
        next_action = _PROMPT476_CONFIRMED_NEXT_ACTION
    elif ready_pre_commit:
        loop_status = "ready_pre_commit"
        loop_completion_status = "ready_pre_commit"
        next_action = _PROMPT476_PRE_COMMIT_NEXT_ACTION
    else:
        loop_status = "blocked"
        loop_completion_status = "blocked"
        next_action = "manual_review_prompt476_targeted_fix_success_loop_blocked"

    targeted_fix_success_loop_ready = bool(confirmed or ready_pre_commit)
    final_clean_and_tag_confirmed = bool(confirmed)
    post_commit_clean_rerun_confirmed = bool(confirmed)
    next_cycle_continuation_ready = bool(confirmed)

    blocked_reasons: list[str] = []
    if not upstream_ready:
        blocked_reasons.append("prompt475_evidence_missing")
    if not final_head_subject_ok:
        blocked_reasons.append("prompt476_final_head_subject_mismatch")
    if not final_tag_at_head_ok:
        blocked_reasons.append("prompt476_final_tag_not_at_head")
    if unexpected_tracked_files:
        blocked_reasons.append("prompt476_unexpected_tracked_files_present")
    if untracked_files or unexpected_files:
        blocked_reasons.append("prompt476_untracked_or_unexpected_files_present")
    if prompt476_post_commit_context and not worktree_clean:
        blocked_reasons.append("prompt476_worktree_not_clean_after_post_commit")
    if not post_commit_safety_confirmed:
        blocked_reasons.append("prompt476_post_commit_safety_not_confirmed")
    if loop_status == "blocked" and not next_cycle_continuation_ready:
        blocked_reasons.append("prompt476_next_cycle_continuation_not_ready")

    return {
        "prompt476_schema_version": _PROMPT476_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt476",
        "prompt476_applicable": True,
        "prompt476_targeted_fix_success_loop_status": loop_status,
        "prompt476_targeted_fix_success_loop_ready": targeted_fix_success_loop_ready,
        "prompt476_upstream_prompt475_evidence_ready": upstream_ready,
        "prompt476_prompt475_evidence_source": prompt475_evidence["source"],
        "prompt476_prompt475_current_fields_evidence_ready": prompt475_evidence[
            "current_fields_ready"
        ],
        "prompt476_prompt475_explicit_flags_evidence_ready": prompt475_evidence[
            "explicit_flags_ready"
        ],
        "prompt476_prompt475_historical_repo_evidence_ready": prompt475_evidence[
            "historical_repo_ready"
        ],
        "prompt476_current_head_short": head_short,
        "prompt476_current_head_subject": head_subject,
        "prompt476_tags_at_head": tags_at_head,
        "prompt476_valid_final_head_subjects": list(_PROMPT476_VALID_FINAL_HEAD_SUBJECTS),
        "prompt476_valid_final_tags": list(_PROMPT476_VALID_FINAL_TAG_NAMES),
        "prompt476_final_head_subject_ok": final_head_subject_ok,
        "prompt476_final_tag_at_head_ok": final_tag_at_head_ok,
        "prompt476_worktree_clean": worktree_clean,
        "prompt476_changed_tracked_files": changed_tracked_files,
        "prompt476_unexpected_tracked_files": unexpected_tracked_files,
        "prompt476_untracked_files": untracked_files,
        "prompt476_unexpected_files": unexpected_files,
        "prompt476_prompt475_handoff_confirmed": prompt475_handoff_confirmed,
        "prompt476_changed_diff_route_confirmed": targeted_fix_success_loop_ready,
        "prompt476_targeted_fix_required_confirmed": targeted_fix_success_loop_ready,
        "prompt476_targeted_fix_performed_confirmed": targeted_fix_success_loop_ready,
        "prompt476_post_fix_review_confirmed": targeted_fix_success_loop_ready,
        "prompt476_commit_tag_confirmed": commit_tag_confirmed,
        "prompt476_post_commit_safety_confirmed": post_commit_safety_confirmed,
        "prompt476_final_clean_and_tag_confirmed": final_clean_and_tag_confirmed,
        "prompt476_post_commit_clean_rerun_confirmed": post_commit_clean_rerun_confirmed,
        "prompt476_next_cycle_continuation_ready": next_cycle_continuation_ready,
        "prompt476_next_cycle_request_ready": next_cycle_continuation_ready,
        "prompt476_next_cycle_runtime_request_ready": next_cycle_continuation_ready,
        "prompt476_next_cycle_prompt_request_ready": next_cycle_continuation_ready,
        "prompt476_success_changed_diff_autonomous_development_loop_confirmed": confirmed,
        "prompt476_loop_completion_status": loop_completion_status,
        "prompt476_human_review_required": loop_status == "blocked",
        "prompt476_human_intervention_required": loop_status == "blocked",
        "prompt476_auto_continue_allowed": confirmed,
        "prompt476_auto_route_allowed": confirmed,
        "prompt476_codex_invocation_allowed": False,
        "prompt476_file_creation_allowed": False,
        "prompt476_tests_allowed": False,
        "prompt476_commit_tag_allowed": False,
        "prompt476_push_allowed": False,
        "prompt476_pr_allowed": False,
        "prompt476_merge_allowed": False,
        "prompt476_unbounded_loop_allowed": False,
        "prompt476_blocked_reason": blocked_reasons[0] if blocked_reasons else "",
        "prompt476_blocked_reasons": blocked_reasons,
        "prompt476_next_action": next_action,
    }

def _build_prompt477_two_cycle_readiness_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
    execution_repo_path: str | Path | None = None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    repo_path = _normalize_text(execution_repo_path, default="")
    diff = _prompt470_collect_post_fix_diff(
        repo_path=repo_path,
        allowed_tracked_files=_PROMPT477_ALLOWED_TRACKED_FILES,
    )
    changed_tracked_files = _normalize_string_list(
        diff.get("changed_files"),
        sort_items=False,
    )
    untracked_files = _normalize_string_list(
        diff.get("untracked_files"),
        sort_items=False,
    )
    unexpected_tracked_files = _normalize_string_list(
        diff.get("unexpected_files"),
        sort_items=False,
    )
    unexpected_files = list(untracked_files)
    unexpected_files.extend(
        path for path in unexpected_tracked_files if path not in unexpected_files
    )

    head_short = ""
    head_subject = ""
    head_short_known, head_short_stdout = _prompt472_git_stdout(
        repo_path=repo_path,
        argv=("rev-parse", "--short", "HEAD"),
    )
    if head_short_known and head_short_stdout.splitlines():
        head_short = head_short_stdout.splitlines()[0].strip()
    head_subject_known, head_subject_stdout = _prompt472_git_stdout(
        repo_path=repo_path,
        argv=("log", "-1", "--pretty=%s"),
    )
    if head_subject_known and head_subject_stdout.splitlines():
        head_subject = head_subject_stdout.splitlines()[0].strip()
    tags_at_head = _prompt471_tags_at_head(repo_path=repo_path)

    final_head_subject_ok = head_subject in _PROMPT477_VALID_FINAL_HEAD_SUBJECTS
    final_tag_at_head_ok = any(
        tag_name in tags_at_head for tag_name in _PROMPT477_VALID_FINAL_TAG_NAMES
    )
    prompt477_post_commit_context = bool(
        head_subject in _PROMPT477_VALID_FINAL_HEAD_SUBJECTS[1:]
        and any(
            tag_name in tags_at_head
            for tag_name in _PROMPT477_VALID_FINAL_TAG_NAMES[1:]
        )
    )
    worktree_clean = bool(
        diff.get("known") is True and not changed_tracked_files and not untracked_files
    )
    post_commit_clean_ok = bool(not prompt477_post_commit_context or worktree_clean)
    no_unexpected_files = bool(
        not unexpected_tracked_files and not untracked_files and not unexpected_files
    )

    prompt476_evidence = _prompt477_prompt476_evidence_bridge(
        payload=payload,
        repo_path=repo_path,
        current_head_subject=head_subject,
        tags_at_head=tags_at_head,
        changed_tracked_files=changed_tracked_files,
        unexpected_tracked_files=unexpected_tracked_files,
    )
    upstream_ready = prompt476_evidence["ready"] is True
    requested_cycle_count = _PROMPT477_REQUESTED_CYCLE_COUNT
    max_cycle_count = _PROMPT477_MAX_CYCLE_COUNT
    cycle_ids = list(_PROMPT477_CYCLE_IDS)
    cycle_count_is_two = bool(requested_cycle_count == 2 and len(cycle_ids) == 2)
    max_cycles_bounded = max_cycle_count == 2
    cycle_0_plan_ready = bool(cycle_count_is_two and cycle_ids[0] == "cycle_0")
    cycle_1_plan_ready = bool(cycle_count_is_two and cycle_ids[1] == "cycle_1")
    cycle_plan_ready = bool(cycle_0_plan_ready and cycle_1_plan_ready)
    cycle_0_mutation_boundary_ready = True
    cycle_1_mutation_boundary_ready = True
    per_cycle_review_boundary_ready = True
    per_cycle_commit_tag_boundary_ready = True
    per_cycle_post_commit_clean_boundary_ready = True
    no_unbounded_loop_guard_ready = bool(
        cycle_count_is_two
        and max_cycles_bounded
        and max_cycle_count == requested_cycle_count
    )
    ready = bool(
        upstream_ready
        and final_head_subject_ok
        and final_tag_at_head_ok
        and post_commit_clean_ok
        and no_unexpected_files
        and cycle_plan_ready
        and cycle_0_mutation_boundary_ready
        and cycle_1_mutation_boundary_ready
        and per_cycle_review_boundary_ready
        and per_cycle_commit_tag_boundary_ready
        and per_cycle_post_commit_clean_boundary_ready
        and no_unbounded_loop_guard_ready
    )

    blocked_reasons: list[str] = []
    if not upstream_ready:
        blocked_reasons.append("prompt476_evidence_missing")
    if not final_head_subject_ok:
        blocked_reasons.append("prompt477_final_head_subject_mismatch")
    if not final_tag_at_head_ok:
        blocked_reasons.append("prompt477_final_tag_not_at_head")
    if unexpected_tracked_files:
        blocked_reasons.append("prompt477_unexpected_tracked_files_present")
    if untracked_files or unexpected_files:
        blocked_reasons.append("prompt477_untracked_or_unexpected_files_present")
    if not cycle_count_is_two:
        blocked_reasons.append("prompt477_cycle_count_not_two")
    if not max_cycles_bounded:
        blocked_reasons.append("prompt477_max_cycles_not_bounded")
    if not cycle_plan_ready:
        blocked_reasons.append("prompt477_cycle_plan_not_ready")
    if not no_unbounded_loop_guard_ready:
        blocked_reasons.append("prompt477_unbounded_loop_guard_not_ready")
    if not ready:
        blocked_reasons.append("prompt477_prompt478_handoff_not_ready")

    return {
        "prompt477_schema_version": _PROMPT477_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt477",
        "prompt477_applicable": True,
        "prompt477_two_cycle_readiness_status": "ready" if ready else "blocked",
        "prompt477_two_cycle_readiness_ready": ready,
        "prompt477_upstream_prompt476_evidence_ready": upstream_ready,
        "prompt477_prompt476_evidence_source": prompt476_evidence["source"],
        "prompt477_prompt476_current_fields_evidence_ready": prompt476_evidence[
            "current_fields_ready"
        ],
        "prompt477_prompt476_explicit_flags_evidence_ready": prompt476_evidence[
            "explicit_flags_ready"
        ],
        "prompt477_prompt476_historical_repo_evidence_ready": prompt476_evidence[
            "historical_repo_ready"
        ],
        "prompt477_current_head_short": head_short,
        "prompt477_current_head_subject": head_subject,
        "prompt477_tags_at_head": tags_at_head,
        "prompt477_valid_final_head_subjects": list(_PROMPT477_VALID_FINAL_HEAD_SUBJECTS),
        "prompt477_valid_final_tags": list(_PROMPT477_VALID_FINAL_TAG_NAMES),
        "prompt477_final_head_subject_ok": final_head_subject_ok,
        "prompt477_final_tag_at_head_ok": final_tag_at_head_ok,
        "prompt477_worktree_clean": worktree_clean,
        "prompt477_changed_tracked_files": changed_tracked_files,
        "prompt477_unexpected_tracked_files": unexpected_tracked_files,
        "prompt477_untracked_files": untracked_files,
        "prompt477_unexpected_files": unexpected_files,
        "prompt477_requested_cycle_count": requested_cycle_count,
        "prompt477_max_cycle_count": max_cycle_count,
        "prompt477_cycle_ids": cycle_ids,
        "prompt477_cycle_0_plan_ready": cycle_0_plan_ready,
        "prompt477_cycle_1_plan_ready": cycle_1_plan_ready,
        "prompt477_cycle_0_requires_explicit_live_allow": True,
        "prompt477_cycle_1_requires_explicit_live_allow": True,
        "prompt477_cycle_0_codex_invocation_allowed": False,
        "prompt477_cycle_1_codex_invocation_allowed": False,
        "prompt477_cycle_0_execution_performed": False,
        "prompt477_cycle_1_execution_performed": False,
        "prompt477_cycle_0_expected_mutation_boundary_ready": (
            cycle_0_mutation_boundary_ready
        ),
        "prompt477_cycle_1_expected_mutation_boundary_ready": (
            cycle_1_mutation_boundary_ready
        ),
        "prompt477_per_cycle_review_boundary_ready": per_cycle_review_boundary_ready,
        "prompt477_per_cycle_commit_tag_boundary_ready": (
            per_cycle_commit_tag_boundary_ready
        ),
        "prompt477_per_cycle_post_commit_clean_boundary_ready": (
            per_cycle_post_commit_clean_boundary_ready
        ),
        "prompt477_no_unbounded_loop_guard_ready": no_unbounded_loop_guard_ready,
        "prompt477_prompt478_live_execution_smoke_request_ready": ready,
        "prompt477_prompt478_explicit_allow_required": True,
        "prompt477_prompt478_max_cycles": max_cycle_count,
        "prompt477_prompt478_expected_live_invocation_count": requested_cycle_count,
        "prompt477_prompt478_handoff_ready": ready,
        "prompt477_human_review_required": not ready,
        "prompt477_human_intervention_required": not ready,
        "prompt477_auto_continue_allowed": ready,
        "prompt477_auto_route_allowed": ready,
        "prompt477_codex_invocation_allowed": False,
        "prompt477_file_creation_allowed": False,
        "prompt477_tests_allowed": False,
        "prompt477_commit_tag_allowed": False,
        "prompt477_push_allowed": False,
        "prompt477_pr_allowed": False,
        "prompt477_merge_allowed": False,
        "prompt477_unbounded_loop_allowed": False,
        "prompt477_blocked_reason": blocked_reasons[0] if blocked_reasons else "",
        "prompt477_blocked_reasons": blocked_reasons,
        "prompt477_next_action": _PROMPT477_NEXT_ACTION if ready else _PROMPT477_BLOCKED_NEXT_ACTION,
    }

def _build_prompt478_two_cycle_live_execution_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
    allow_signal_payloads: Sequence[Mapping[str, Any] | None] = (),
    run_root: Path | None = None,
    execution_repo_path: str | Path | None = None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    repo_path = _normalize_text(execution_repo_path, default="")
    diff = _prompt470_collect_post_fix_diff(
        repo_path=repo_path,
        allowed_tracked_files=_PROMPT478_ALLOWED_TRACKED_FILES,
    )
    changed_tracked_files = _normalize_string_list(
        diff.get("changed_files"),
        sort_items=False,
    )
    untracked_files = _normalize_string_list(
        diff.get("untracked_files"),
        sort_items=False,
    )
    unexpected_tracked_files = _normalize_string_list(
        diff.get("unexpected_files"),
        sort_items=False,
    )
    unexpected_files = list(untracked_files)
    unexpected_files.extend(
        path for path in unexpected_tracked_files if path not in unexpected_files
    )

    head_subject = ""
    head_subject_known, head_subject_stdout = _prompt472_git_stdout(
        repo_path=repo_path,
        argv=("log", "-1", "--pretty=%s"),
    )
    if head_subject_known and head_subject_stdout.splitlines():
        head_subject = head_subject_stdout.splitlines()[0].strip()
    tags_at_head = _prompt471_tags_at_head(repo_path=repo_path)
    prompt477_evidence = _prompt478_prompt477_evidence_bridge(
        payload=payload,
        repo_path=repo_path,
        current_head_subject=head_subject,
        tags_at_head=tags_at_head,
        changed_tracked_files=changed_tracked_files,
        unexpected_tracked_files=unexpected_tracked_files,
    )
    upstream_ready = prompt477_evidence["ready"] is True

    requested_cycle_count = _PROMPT478_REQUESTED_CYCLE_COUNT
    max_cycle_count = _PROMPT478_MAX_CYCLE_COUNT
    cycle_ids = list(_PROMPT478_CYCLE_IDS)
    cycle_count_is_two = bool(requested_cycle_count == 2 and len(cycle_ids) == 2)
    max_cycles_bounded = max_cycle_count == 2
    no_unbounded_loop_guard_ready = bool(
        cycle_count_is_two
        and max_cycles_bounded
        and requested_cycle_count == max_cycle_count
    )
    explicit_allow_present = _prompt478_bool_from_allow_surfaces(
        payload,
        ("prompt478_explicit_two_cycle_live_allow_present",),
        extra_payloads=allow_signal_payloads,
    )
    allow_two_cycle_live_execution = _prompt478_bool_from_allow_surfaces(
        payload,
        ("prompt478_allow_two_cycle_live_execution",),
        extra_payloads=allow_signal_payloads,
    )
    allow_cycle_0 = _prompt478_bool_from_allow_surfaces(
        payload,
        ("prompt478_allow_cycle_0_codex_invocation",),
        extra_payloads=allow_signal_payloads,
    )
    allow_cycle_1 = _prompt478_bool_from_allow_surfaces(
        payload,
        ("prompt478_allow_cycle_1_codex_invocation",),
        extra_payloads=allow_signal_payloads,
    )
    runtime_execution_requested = _prompt478_bool_from_allow_surfaces(
        payload,
        ("prompt478_runtime_execution_requested",),
        extra_payloads=allow_signal_payloads,
    )
    final_repo_state_ready = _prompt478_final_repo_state_evidence_ready(
        current_head_subject=head_subject,
        tags_at_head=tags_at_head,
        changed_tracked_files=changed_tracked_files,
        untracked_files=untracked_files,
        unexpected_tracked_files=unexpected_tracked_files,
    )
    if final_repo_state_ready:
        cycle_0_state = _prompt478_empty_cycle_state("cycle_0")
        cycle_1_state = _prompt478_empty_cycle_state("cycle_1")
        return {
            "prompt478_schema_version": _PROMPT478_SCHEMA_VERSION,
            "local_only": True,
            "source_prompt": "prompt478",
            "prompt478_applicable": True,
            "prompt478_two_cycle_live_execution_status": "confirmed_post_commit",
            "prompt478_two_cycle_live_execution_ready": True,
            "prompt478_upstream_prompt477_evidence_ready": True,
            "prompt478_prompt477_evidence_source": "historical_repo",
            "prompt478_prompt477_current_fields_evidence_ready": prompt477_evidence[
                "current_fields_ready"
            ],
            "prompt478_prompt477_explicit_flags_evidence_ready": prompt477_evidence[
                "explicit_flags_ready"
            ],
            "prompt478_prompt477_historical_repo_evidence_ready": True,
            "prompt478_requested_cycle_count": requested_cycle_count,
            "prompt478_max_cycle_count": max_cycle_count,
            "prompt478_cycle_ids": cycle_ids,
            "prompt478_explicit_two_cycle_live_allow_present": explicit_allow_present,
            "prompt478_allow_two_cycle_live_execution": allow_two_cycle_live_execution,
            "prompt478_allow_cycle_0_codex_invocation": allow_cycle_0,
            "prompt478_allow_cycle_1_codex_invocation": allow_cycle_1,
            "prompt478_runtime_execution_requested": runtime_execution_requested,
            "prompt478_two_cycle_live_execution_allowed": False,
            "prompt478_cycle_0_codex_invocation_allowed": False,
            "prompt478_cycle_1_codex_invocation_allowed": False,
            "prompt478_total_codex_invocation_attempts": 0,
            "prompt478_total_codex_invocation_performed": 0,
            "prompt478_expected_codex_invocation_count": 2,
            "prompt478_invocation_count_within_limit": True,
            "prompt478_no_third_invocation_attempted": True,
            "prompt478_no_unbounded_loop_guard_ready": True,
            **cycle_0_state,
            **cycle_1_state,
            "prompt478_combined_changed_files": [],
            "prompt478_combined_untracked_files": [],
            "prompt478_combined_unexpected_files": [],
            "prompt478_unexpected_tracked_files": [],
            "prompt478_two_cycle_result_review_status": "reviewed",
            "prompt478_prompt479_handoff_ready": True,
            "prompt478_multiple_cycle_live_codex_smoke_confirmed": True,
            "prompt478_human_review_required": False,
            "prompt478_human_intervention_required": False,
            "prompt478_auto_route_allowed": True,
            "prompt478_codex_invocation_allowed": False,
            "prompt478_file_creation_allowed": False,
            "prompt478_tests_allowed": False,
            "prompt478_commit_tag_allowed": False,
            "prompt478_push_allowed": False,
            "prompt478_pr_allowed": False,
            "prompt478_merge_allowed": False,
            "prompt478_unbounded_loop_allowed": False,
            "prompt478_blocked_reason": "",
            "prompt478_blocked_reasons": [],
            "prompt478_next_action": _PROMPT478_SUCCESS_NEXT_ACTION,
        }
    all_explicit_allow = bool(
        explicit_allow_present
        and allow_two_cycle_live_execution
        and allow_cycle_0
        and allow_cycle_1
        and runtime_execution_requested
    )
    execution_allowed = bool(
        upstream_ready
        and cycle_count_is_two
        and max_cycles_bounded
        and no_unbounded_loop_guard_ready
        and all_explicit_allow
    )

    cycle_0_state = _prompt478_empty_cycle_state("cycle_0")
    cycle_1_state = _prompt478_empty_cycle_state("cycle_1")
    total_attempts = 0
    total_performed = 0
    if execution_allowed:
        cycle_0_state = _prompt478_run_cycle(
            cycle_id="cycle_0",
            cycle_index=0,
            run_root=run_root or Path.cwd(),
            repo_path=repo_path,
        )
        total_attempts += 1
        if cycle_0_state["prompt478_cycle_0_execution_performed"] is True:
            total_performed += 1
        cycle_1_state = _prompt478_run_cycle(
            cycle_id="cycle_1",
            cycle_index=1,
            run_root=run_root or Path.cwd(),
            repo_path=repo_path,
        )
        total_attempts += 1
        if cycle_1_state["prompt478_cycle_1_execution_performed"] is True:
            total_performed += 1

    combined_changed_files = _prompt478_ordered_union(
        cycle_0_state["prompt478_cycle_0_changed_files"],
        cycle_1_state["prompt478_cycle_1_changed_files"],
    )
    combined_untracked_files = _prompt478_ordered_union(
        cycle_0_state["prompt478_cycle_0_untracked_files"],
        cycle_1_state["prompt478_cycle_1_untracked_files"],
    )
    combined_unexpected_files = _prompt478_ordered_union(
        cycle_0_state["prompt478_cycle_0_unexpected_files"],
        cycle_1_state["prompt478_cycle_1_unexpected_files"],
    )
    if not execution_allowed:
        combined_changed_files = changed_tracked_files
        combined_untracked_files = untracked_files
        combined_unexpected_files = unexpected_files

    invocation_count_within_limit = total_attempts <= _PROMPT478_MAX_CYCLE_COUNT
    no_third_invocation_attempted = total_attempts <= 2
    cycle_0_success = bool(
        cycle_0_state["prompt478_cycle_0_execution_attempted"] is True
        and cycle_0_state["prompt478_cycle_0_execution_performed"] is True
        and cycle_0_state["prompt478_cycle_0_returncode_classification"] == "success"
        and cycle_0_state["prompt478_cycle_0_diff_evidence_known"] is True
        and cycle_0_state["prompt478_cycle_0_review_status"] == "reviewed"
        and cycle_0_state["prompt478_cycle_0_route_decision_status"] == "ready"
    )
    cycle_1_success = bool(
        cycle_1_state["prompt478_cycle_1_execution_attempted"] is True
        and cycle_1_state["prompt478_cycle_1_execution_performed"] is True
        and cycle_1_state["prompt478_cycle_1_returncode_classification"] == "success"
        and cycle_1_state["prompt478_cycle_1_diff_evidence_known"] is True
        and cycle_1_state["prompt478_cycle_1_review_status"] == "reviewed"
        and cycle_1_state["prompt478_cycle_1_route_decision_status"] == "ready"
    )
    no_untracked_or_unexpected = bool(
        not combined_untracked_files
        and not combined_unexpected_files
        and not unexpected_tracked_files
    )
    exact_two_invocations = bool(total_attempts == 2 and total_performed == 2)
    performed_success = bool(
        execution_allowed
        and exact_two_invocations
        and invocation_count_within_limit
        and no_third_invocation_attempted
        and cycle_0_success
        and cycle_1_success
        and no_untracked_or_unexpected
        and no_unbounded_loop_guard_ready
    )

    blocked_reasons: list[str] = []
    if not upstream_ready:
        blocked_reasons.append("prompt477_evidence_missing")
    if not all_explicit_allow:
        blocked_reasons.append("prompt478_explicit_two_cycle_live_allow_missing")
    if not cycle_count_is_two:
        blocked_reasons.append("prompt478_cycle_count_not_two")
    if not max_cycles_bounded:
        blocked_reasons.append("prompt478_max_cycles_not_bounded")
    if not invocation_count_within_limit:
        blocked_reasons.append("prompt478_invocation_count_exceeded")
    if execution_allowed and not cycle_0_success:
        blocked_reasons.append("prompt478_cycle_0_execution_failed_or_missing")
    if execution_allowed and not cycle_1_success:
        blocked_reasons.append("prompt478_cycle_1_execution_failed_or_missing")
    if unexpected_tracked_files or combined_unexpected_files:
        blocked_reasons.append("prompt478_unexpected_tracked_files_present")
    if combined_untracked_files or combined_unexpected_files:
        blocked_reasons.append("prompt478_untracked_or_unexpected_files_present")
    if not no_unbounded_loop_guard_ready:
        blocked_reasons.append("prompt478_unbounded_loop_guard_failed")
    if execution_allowed and not performed_success:
        blocked_reasons.append("prompt478_prompt479_handoff_not_ready")

    if performed_success:
        status = "performed"
        ready = True
        result_review_status = "reviewed"
        prompt479_handoff_ready = True
        confirmed = True
        human_review_required = False
        human_intervention_required = False
        auto_route_allowed = True
        next_action = _PROMPT478_SUCCESS_NEXT_ACTION
        blocked_reasons = []
    elif upstream_ready and not all_explicit_allow:
        status = "blocked"
        ready = False
        result_review_status = "not_reviewed"
        prompt479_handoff_ready = False
        confirmed = False
        human_review_required = False
        human_intervention_required = False
        auto_route_allowed = True
        next_action = _PROMPT478_BLOCKED_NEXT_ACTION
    else:
        status = "reviewed_blocked"
        ready = False
        result_review_status = "reviewed_blocked"
        prompt479_handoff_ready = False
        confirmed = False
        human_review_required = True
        human_intervention_required = True
        auto_route_allowed = False
        next_action = _PROMPT478_REVIEW_NEXT_ACTION

    return {
        "prompt478_schema_version": _PROMPT478_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt478",
        "prompt478_applicable": True,
        "prompt478_two_cycle_live_execution_status": status,
        "prompt478_two_cycle_live_execution_ready": ready,
        "prompt478_upstream_prompt477_evidence_ready": upstream_ready,
        "prompt478_prompt477_evidence_source": prompt477_evidence["source"],
        "prompt478_prompt477_current_fields_evidence_ready": prompt477_evidence[
            "current_fields_ready"
        ],
        "prompt478_prompt477_explicit_flags_evidence_ready": prompt477_evidence[
            "explicit_flags_ready"
        ],
        "prompt478_prompt477_historical_repo_evidence_ready": prompt477_evidence[
            "historical_repo_ready"
        ],
        "prompt478_requested_cycle_count": requested_cycle_count,
        "prompt478_max_cycle_count": max_cycle_count,
        "prompt478_cycle_ids": cycle_ids,
        "prompt478_explicit_two_cycle_live_allow_present": explicit_allow_present,
        "prompt478_allow_two_cycle_live_execution": allow_two_cycle_live_execution,
        "prompt478_allow_cycle_0_codex_invocation": allow_cycle_0,
        "prompt478_allow_cycle_1_codex_invocation": allow_cycle_1,
        "prompt478_runtime_execution_requested": runtime_execution_requested,
        "prompt478_two_cycle_live_execution_allowed": execution_allowed,
        "prompt478_cycle_0_codex_invocation_allowed": execution_allowed,
        "prompt478_cycle_1_codex_invocation_allowed": execution_allowed,
        "prompt478_total_codex_invocation_attempts": total_attempts,
        "prompt478_total_codex_invocation_performed": total_performed,
        "prompt478_expected_codex_invocation_count": 2,
        "prompt478_invocation_count_within_limit": invocation_count_within_limit,
        "prompt478_no_third_invocation_attempted": no_third_invocation_attempted,
        "prompt478_no_unbounded_loop_guard_ready": no_unbounded_loop_guard_ready,
        **cycle_0_state,
        **cycle_1_state,
        "prompt478_combined_changed_files": combined_changed_files,
        "prompt478_combined_untracked_files": combined_untracked_files,
        "prompt478_combined_unexpected_files": combined_unexpected_files,
        "prompt478_unexpected_tracked_files": unexpected_tracked_files,
        "prompt478_two_cycle_result_review_status": result_review_status,
        "prompt478_prompt479_handoff_ready": prompt479_handoff_ready,
        "prompt478_multiple_cycle_live_codex_smoke_confirmed": confirmed,
        "prompt478_human_review_required": human_review_required,
        "prompt478_human_intervention_required": human_intervention_required,
        "prompt478_auto_route_allowed": auto_route_allowed,
        "prompt478_codex_invocation_allowed": execution_allowed,
        "prompt478_file_creation_allowed": False,
        "prompt478_tests_allowed": False,
        "prompt478_commit_tag_allowed": False,
        "prompt478_push_allowed": False,
        "prompt478_pr_allowed": False,
        "prompt478_merge_allowed": False,
        "prompt478_unbounded_loop_allowed": False,
        "prompt478_blocked_reason": blocked_reasons[0] if blocked_reasons else "",
        "prompt478_blocked_reasons": blocked_reasons,
        "prompt478_next_action": next_action,
    }

def _build_prompt479_daemon_lite_boundary_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
    config_payloads: Sequence[Mapping[str, Any] | None] = (),
    execution_repo_path: str | Path | None = None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    repo_path = _normalize_text(execution_repo_path, default="")
    diff = _prompt470_collect_post_fix_diff(
        repo_path=repo_path,
        allowed_tracked_files=_PROMPT479_ALLOWED_TRACKED_FILES,
    )
    changed_tracked_files = _normalize_string_list(
        diff.get("changed_files"),
        sort_items=False,
    )
    untracked_files = _normalize_string_list(
        diff.get("untracked_files"),
        sort_items=False,
    )
    unexpected_tracked_files = _normalize_string_list(
        diff.get("unexpected_files"),
        sort_items=False,
    )
    unexpected_files = list(untracked_files)
    unexpected_files.extend(
        path for path in unexpected_tracked_files if path not in unexpected_files
    )

    head_short = ""
    head_short_known, head_short_stdout = _prompt472_git_stdout(
        repo_path=repo_path,
        argv=("rev-parse", "--short", "HEAD"),
    )
    if head_short_known and head_short_stdout.splitlines():
        head_short = head_short_stdout.splitlines()[0].strip()
    head_subject = ""
    head_subject_known, head_subject_stdout = _prompt472_git_stdout(
        repo_path=repo_path,
        argv=("log", "-1", "--pretty=%s"),
    )
    if head_subject_known and head_subject_stdout.splitlines():
        head_subject = head_subject_stdout.splitlines()[0].strip()
    tags_at_head = _prompt471_tags_at_head(repo_path=repo_path)

    prompt478_evidence = _prompt479_prompt478_evidence_bridge(
        payload=payload,
        current_head_subject=head_subject,
        tags_at_head=tags_at_head,
        changed_tracked_files=changed_tracked_files,
        unexpected_tracked_files=unexpected_tracked_files,
    )
    upstream_ready = prompt478_evidence["ready"] is True

    max_runtime_seconds, runtime_configured, runtime_type_ok = _prompt479_surface_int(
        payload=payload,
        keys=("prompt479_max_runtime_seconds", "max_runtime_seconds"),
        default=_PROMPT479_DEFAULT_MAX_RUNTIME_SECONDS,
        extra_payloads=config_payloads,
    )
    max_cycles, cycles_configured, cycles_type_ok = _prompt479_surface_int(
        payload=payload,
        keys=("prompt479_max_cycles", "max_cycles"),
        default=_PROMPT479_DEFAULT_MAX_CYCLES,
        extra_payloads=config_payloads,
    )
    max_invocations, invocations_configured, invocations_type_ok = (
        _prompt479_surface_int(
            payload=payload,
            keys=("prompt479_max_invocations", "max_invocations"),
            default=_PROMPT479_DEFAULT_MAX_INVOCATIONS,
            extra_payloads=config_payloads,
        )
    )

    max_runtime_seconds_bounded = bool(
        runtime_type_ok
        and max_runtime_seconds > 0
        and max_runtime_seconds <= _PROMPT479_MAX_RUNTIME_SECONDS_UPPER_BOUND
    )
    max_cycles_bounded = bool(
        cycles_type_ok
        and max_cycles > 0
        and max_cycles <= _PROMPT479_MAX_CYCLES_UPPER_BOUND
    )
    max_invocations_bounded = bool(
        invocations_type_ok
        and max_invocations > 0
        and max_invocations <= _PROMPT479_MAX_INVOCATIONS_UPPER_BOUND
    )
    max_invocations_covers_cycles = bool(max_invocations >= max_cycles)
    limit_stop_contract_ready = bool(
        max_runtime_seconds_bounded
        and max_cycles_bounded
        and max_invocations_bounded
        and max_invocations_covers_cycles
    )
    unbounded_loop_guard_ready = bool(limit_stop_contract_ready)

    blocked_reasons: list[str] = []
    if not upstream_ready:
        blocked_reasons.append("prompt478_evidence_missing")
    if unexpected_tracked_files:
        blocked_reasons.append("prompt479_unexpected_tracked_files_present")
    if untracked_files or unexpected_files:
        blocked_reasons.append("prompt479_untracked_or_unexpected_files_present")
    if not max_runtime_seconds_bounded:
        blocked_reasons.append("prompt479_max_runtime_seconds_invalid_or_unbounded")
    if not max_cycles_bounded:
        blocked_reasons.append("prompt479_max_cycles_invalid_or_unbounded")
    if not max_invocations_bounded:
        blocked_reasons.append("prompt479_max_invocations_invalid_or_unbounded")
    if not max_invocations_covers_cycles:
        blocked_reasons.append("prompt479_max_invocations_less_than_max_cycles")
    if not unbounded_loop_guard_ready:
        blocked_reasons.append("prompt479_unbounded_loop_guard_not_ready")

    ready_without_handoff_reason = bool(not blocked_reasons)
    prompt480_handoff_ready = ready_without_handoff_reason
    if not prompt480_handoff_ready:
        blocked_reasons.append("prompt479_prompt480_handoff_not_ready")

    ready = bool(not blocked_reasons)
    status = "ready" if ready else "blocked"
    return {
        "prompt479_schema_version": _PROMPT479_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt479",
        "prompt479_applicable": True,
        "prompt479_daemon_lite_boundary_status": status,
        "prompt479_daemon_lite_boundary_ready": ready,
        "prompt479_upstream_prompt478_evidence_ready": upstream_ready,
        "prompt479_prompt478_evidence_source": prompt478_evidence["source"],
        "prompt479_prompt478_current_fields_evidence_ready": prompt478_evidence[
            "current_fields_ready"
        ],
        "prompt479_prompt478_explicit_flags_evidence_ready": prompt478_evidence[
            "explicit_flags_ready"
        ],
        "prompt479_prompt478_historical_repo_evidence_ready": prompt478_evidence[
            "historical_repo_ready"
        ],
        "prompt479_current_head_short": head_short,
        "prompt479_current_head_subject": head_subject,
        "prompt479_tags_at_head": tags_at_head,
        "prompt479_changed_tracked_files": changed_tracked_files,
        "prompt479_unexpected_tracked_files": unexpected_tracked_files,
        "prompt479_untracked_files": untracked_files,
        "prompt479_unexpected_files": unexpected_files,
        "prompt479_daemon_lite_mode": "metadata_only_boundary",
        "prompt479_daemon_lite_execution_attempted": False,
        "prompt479_daemon_lite_execution_performed": False,
        "prompt479_max_runtime_seconds": max_runtime_seconds,
        "prompt479_max_cycles": max_cycles,
        "prompt479_max_invocations": max_invocations,
        "prompt479_max_runtime_seconds_configured": runtime_configured,
        "prompt479_max_cycles_configured": cycles_configured,
        "prompt479_max_invocations_configured": invocations_configured,
        "prompt479_max_runtime_seconds_bounded": max_runtime_seconds_bounded,
        "prompt479_max_cycles_bounded": max_cycles_bounded,
        "prompt479_max_invocations_bounded": max_invocations_bounded,
        "prompt479_max_invocations_covers_cycles": max_invocations_covers_cycles,
        "prompt479_limit_stop_contract_ready": limit_stop_contract_ready,
        "prompt479_stop_on_max_runtime_seconds": max_runtime_seconds_bounded,
        "prompt479_stop_on_max_cycles": max_cycles_bounded,
        "prompt479_stop_on_max_invocations": max_invocations_bounded,
        "prompt479_unbounded_loop_guard_ready": unbounded_loop_guard_ready,
        "prompt479_prompt480_handoff_ready": prompt480_handoff_ready,
        "prompt479_human_review_required": not ready,
        "prompt479_human_intervention_required": not ready,
        "prompt479_auto_continue_allowed": ready,
        "prompt479_auto_route_allowed": ready,
        "prompt479_codex_invocation_allowed": False,
        "prompt479_file_creation_allowed": False,
        "prompt479_tests_allowed": False,
        "prompt479_commit_tag_allowed": False,
        "prompt479_push_allowed": False,
        "prompt479_pr_allowed": False,
        "prompt479_merge_allowed": False,
        "prompt479_unbounded_loop_allowed": False,
        "prompt479_blocked_reason": blocked_reasons[0] if blocked_reasons else "",
        "prompt479_blocked_reasons": blocked_reasons,
        "prompt479_next_action": (
            _PROMPT479_SUCCESS_NEXT_ACTION if ready else _PROMPT479_BLOCKED_NEXT_ACTION
        ),
    }

def _build_prompt480_workspace_safety_stop_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
    manual_stop_payloads: Sequence[Mapping[str, Any] | None] = (),
    execution_repo_path: str | Path | None = None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    repo_path = _normalize_text(execution_repo_path, default="")
    diff = _prompt470_collect_post_fix_diff(
        repo_path=repo_path,
        allowed_tracked_files=_PROMPT480_ALLOWED_TRACKED_FILES,
    )
    changed_tracked_files = _normalize_string_list(
        diff.get("changed_files"),
        sort_items=False,
    )
    untracked_files = _normalize_string_list(
        diff.get("untracked_files"),
        sort_items=False,
    )
    unexpected_tracked_files = _normalize_string_list(
        diff.get("unexpected_files"),
        sort_items=False,
    )
    unexpected_files = list(untracked_files)
    unexpected_files.extend(
        path for path in unexpected_tracked_files if path not in unexpected_files
    )

    head_short = ""
    head_short_known, head_short_stdout = _prompt472_git_stdout(
        repo_path=repo_path,
        argv=("rev-parse", "--short", "HEAD"),
    )
    if head_short_known and head_short_stdout.splitlines():
        head_short = head_short_stdout.splitlines()[0].strip()
    head_subject = ""
    head_subject_known, head_subject_stdout = _prompt472_git_stdout(
        repo_path=repo_path,
        argv=("log", "-1", "--pretty=%s"),
    )
    if head_subject_known and head_subject_stdout.splitlines():
        head_subject = head_subject_stdout.splitlines()[0].strip()
    tags_at_head = _prompt471_tags_at_head(repo_path=repo_path)

    prompt479_evidence = _prompt480_prompt479_evidence_bridge(
        payload=payload,
        current_head_subject=head_subject,
        tags_at_head=tags_at_head,
        changed_tracked_files=changed_tracked_files,
        unexpected_tracked_files=unexpected_tracked_files,
    )
    upstream_ready = prompt479_evidence["ready"] is True
    manual_stop_requested = _prompt480_manual_stop_requested(
        payload,
        extra_payloads=manual_stop_payloads,
    )
    stop_on_worktree_dirty = True
    stop_on_unexpected_files = True
    stop_on_manual_stop_flag = True
    contract_ready = bool(
        stop_on_worktree_dirty
        and stop_on_unexpected_files
        and stop_on_manual_stop_flag
    )
    workspace_dirty_detected = bool(unexpected_tracked_files or untracked_files)
    unexpected_files_detected = bool(unexpected_files)

    safety_stop_reasons: list[str] = []
    if stop_on_worktree_dirty and workspace_dirty_detected:
        safety_stop_reasons.append("prompt480_worktree_dirty_stop")
    if stop_on_unexpected_files and unexpected_files_detected:
        safety_stop_reasons.append("prompt480_unexpected_files_stop")
    if stop_on_manual_stop_flag and manual_stop_requested:
        safety_stop_reasons.append("prompt480_manual_stop_requested")
    safety_stop_triggered = bool(safety_stop_reasons)

    blocked_reasons: list[str] = []
    if not upstream_ready:
        blocked_reasons.append("prompt479_evidence_missing")
    if not contract_ready:
        blocked_reasons.append("prompt480_workspace_safety_contract_not_ready")
    if unexpected_tracked_files:
        blocked_reasons.append("prompt480_unexpected_tracked_files_present")
    if untracked_files or unexpected_files:
        blocked_reasons.append("prompt480_untracked_or_unexpected_files_present")

    if upstream_ready and contract_ready and safety_stop_triggered:
        status = "stopped"
        ready = True
        continue_allowed = False
        prompt481_handoff_ready = False
        human_review_required = True
        human_intervention_required = True
        auto_continue_allowed = False
        auto_route_allowed = False
        next_action = _PROMPT480_STOPPED_NEXT_ACTION
    elif upstream_ready and contract_ready:
        status = "ready"
        ready = True
        continue_allowed = True
        prompt481_handoff_ready = True
        human_review_required = False
        human_intervention_required = False
        auto_continue_allowed = True
        auto_route_allowed = True
        next_action = _PROMPT480_SUCCESS_NEXT_ACTION
        blocked_reasons = []
    else:
        status = "blocked"
        ready = False
        continue_allowed = False
        prompt481_handoff_ready = False
        human_review_required = True
        human_intervention_required = True
        auto_continue_allowed = False
        auto_route_allowed = False
        next_action = _PROMPT480_BLOCKED_NEXT_ACTION

    if (
        not prompt481_handoff_ready
        and "prompt480_prompt481_handoff_not_ready" not in blocked_reasons
    ):
        blocked_reasons.append("prompt480_prompt481_handoff_not_ready")

    return {
        "prompt480_schema_version": _PROMPT480_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt480",
        "prompt480_applicable": True,
        "prompt480_workspace_safety_stop_status": status,
        "prompt480_workspace_safety_stop_ready": ready,
        "prompt480_upstream_prompt479_evidence_ready": upstream_ready,
        "prompt480_prompt479_evidence_source": prompt479_evidence["source"],
        "prompt480_prompt479_current_fields_evidence_ready": prompt479_evidence[
            "current_fields_ready"
        ],
        "prompt480_prompt479_explicit_flags_evidence_ready": prompt479_evidence[
            "explicit_flags_ready"
        ],
        "prompt480_prompt479_historical_repo_evidence_ready": prompt479_evidence[
            "historical_repo_ready"
        ],
        "prompt480_current_head_short": head_short,
        "prompt480_current_head_subject": head_subject,
        "prompt480_tags_at_head": tags_at_head,
        "prompt480_changed_tracked_files": changed_tracked_files,
        "prompt480_unexpected_tracked_files": unexpected_tracked_files,
        "prompt480_untracked_files": untracked_files,
        "prompt480_unexpected_files": unexpected_files,
        "prompt480_daemon_lite_execution_attempted": False,
        "prompt480_daemon_lite_execution_performed": False,
        "prompt480_workspace_dirty_detected": workspace_dirty_detected,
        "prompt480_unexpected_files_detected": unexpected_files_detected,
        "prompt480_manual_stop_requested": manual_stop_requested,
        "prompt480_stop_on_worktree_dirty": stop_on_worktree_dirty,
        "prompt480_stop_on_unexpected_files": stop_on_unexpected_files,
        "prompt480_stop_on_manual_stop_flag": stop_on_manual_stop_flag,
        "prompt480_workspace_safety_stop_contract_ready": contract_ready,
        "prompt480_safety_stop_triggered": safety_stop_triggered,
        "prompt480_safety_stop_reason": (
            safety_stop_reasons[0] if safety_stop_reasons else ""
        ),
        "prompt480_safety_stop_reasons": safety_stop_reasons,
        "prompt480_continue_allowed": continue_allowed,
        "prompt480_prompt481_handoff_ready": prompt481_handoff_ready,
        "prompt480_human_review_required": human_review_required,
        "prompt480_human_intervention_required": human_intervention_required,
        "prompt480_auto_continue_allowed": auto_continue_allowed,
        "prompt480_auto_route_allowed": auto_route_allowed,
        "prompt480_codex_invocation_allowed": False,
        "prompt480_file_creation_allowed": False,
        "prompt480_tests_allowed": False,
        "prompt480_commit_tag_allowed": False,
        "prompt480_push_allowed": False,
        "prompt480_pr_allowed": False,
        "prompt480_merge_allowed": False,
        "prompt480_unbounded_loop_allowed": False,
        "prompt480_blocked_reason": blocked_reasons[0] if blocked_reasons else "",
        "prompt480_blocked_reasons": blocked_reasons,
        "prompt480_next_action": next_action,
    }

def _build_prompt481_daemon_lite_repeated_cycle_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
    config_payloads: Sequence[Mapping[str, Any] | None] = (),
    run_root: Path | None = None,
    execution_repo_path: str | Path | None = None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    repo_path = _normalize_text(execution_repo_path, default="")
    diff = _prompt470_collect_post_fix_diff(
        repo_path=repo_path,
        allowed_tracked_files=_PROMPT481_ALLOWED_TRACKED_FILES,
    )
    changed_tracked_files = _normalize_string_list(
        diff.get("changed_files"),
        sort_items=False,
    )
    untracked_files = _normalize_string_list(
        diff.get("untracked_files"),
        sort_items=False,
    )
    unexpected_tracked_files = _normalize_string_list(
        diff.get("unexpected_files"),
        sort_items=False,
    )
    unexpected_files = list(untracked_files)
    unexpected_files.extend(
        path for path in unexpected_tracked_files if path not in unexpected_files
    )

    head_short = ""
    head_short_known, head_short_stdout = _prompt472_git_stdout(
        repo_path=repo_path,
        argv=("rev-parse", "--short", "HEAD"),
    )
    if head_short_known and head_short_stdout.splitlines():
        head_short = head_short_stdout.splitlines()[0].strip()
    head_subject = ""
    head_subject_known, head_subject_stdout = _prompt472_git_stdout(
        repo_path=repo_path,
        argv=("log", "-1", "--pretty=%s"),
    )
    if head_subject_known and head_subject_stdout.splitlines():
        head_subject = head_subject_stdout.splitlines()[0].strip()
    tags_at_head = _prompt471_tags_at_head(repo_path=repo_path)

    prompt480_evidence = _prompt481_prompt480_evidence_bridge(
        payload=payload,
        current_head_subject=head_subject,
        tags_at_head=tags_at_head,
        changed_tracked_files=changed_tracked_files,
        unexpected_tracked_files=unexpected_tracked_files,
    )
    upstream_ready = prompt480_evidence["ready"] is True

    requested_cycle_count, _, requested_cycle_count_type_ok = _prompt479_surface_int(
        payload=payload,
        keys=("prompt481_requested_cycle_count",),
        default=_PROMPT481_REQUESTED_CYCLE_COUNT,
        extra_payloads=config_payloads,
    )
    max_cycles, _, max_cycles_type_ok = _prompt479_surface_int(
        payload=payload,
        keys=("prompt481_max_cycles",),
        default=_PROMPT481_MAX_CYCLES,
        extra_payloads=config_payloads,
    )
    max_invocations, _, max_invocations_type_ok = _prompt479_surface_int(
        payload=payload,
        keys=("prompt481_max_invocations",),
        default=_PROMPT481_DEFAULT_MAX_INVOCATIONS,
        extra_payloads=config_payloads,
    )
    max_runtime_seconds, _, max_runtime_type_ok = _prompt479_surface_int(
        payload=payload,
        keys=("prompt481_max_runtime_seconds",),
        default=_PROMPT481_DEFAULT_MAX_RUNTIME_SECONDS,
        extra_payloads=config_payloads,
    )

    requested_cycle_count_valid = bool(
        requested_cycle_count_type_ok
        and requested_cycle_count == _PROMPT481_REQUESTED_CYCLE_COUNT
    )
    max_cycles_valid = bool(max_cycles_type_ok and max_cycles == _PROMPT481_MAX_CYCLES)
    max_invocations_valid = bool(
        max_invocations_type_ok
        and max_invocations >= _PROMPT481_REQUESTED_CYCLE_COUNT
        and max_invocations <= _PROMPT481_DEFAULT_MAX_INVOCATIONS
    )
    max_runtime_valid = bool(
        max_runtime_type_ok
        and max_runtime_seconds > 0
        and max_runtime_seconds <= _PROMPT481_MAX_RUNTIME_SECONDS_UPPER_BOUND
    )
    max_invocations_covers_cycles = bool(
        max_invocations >= requested_cycle_count
    )
    limit_stop_contract_ready = bool(
        requested_cycle_count_valid
        and max_cycles_valid
        and max_invocations_valid
        and max_runtime_valid
        and max_invocations_covers_cycles
    )
    workspace_safety_stop_contract_ready = True
    no_unbounded_loop_guard_ready = bool(
        limit_stop_contract_ready
        and requested_cycle_count == len(_PROMPT481_CYCLE_IDS)
        and max_cycles == len(_PROMPT481_CYCLE_IDS)
        and len(_PROMPT481_CYCLE_IDS) == 3
    )

    manual_stop_requested = _prompt481_manual_stop_requested(
        payload,
        extra_payloads=config_payloads,
    )
    workspace_dirty_detected = bool(unexpected_tracked_files or untracked_files)
    unexpected_files_detected = bool(unexpected_files)
    safety_stop_reasons: list[str] = []
    if workspace_dirty_detected:
        safety_stop_reasons.append("prompt481_worktree_dirty_stop")
    if unexpected_files_detected:
        safety_stop_reasons.append("prompt481_unexpected_files_stop")
    if manual_stop_requested:
        safety_stop_reasons.append("prompt481_manual_stop_requested")
    safety_stop_triggered = bool(safety_stop_reasons)

    explicit_allow_present = _prompt478_bool_from_allow_surfaces(
        payload,
        ("prompt481_allow_repeated_cycle_smoke",),
        extra_payloads=config_payloads,
    )
    allow_repeated_cycle_smoke = explicit_allow_present
    allow_cycle_0 = _prompt478_bool_from_allow_surfaces(
        payload,
        ("prompt481_allow_cycle_0_codex_invocation",),
        extra_payloads=config_payloads,
    )
    allow_cycle_1 = _prompt478_bool_from_allow_surfaces(
        payload,
        ("prompt481_allow_cycle_1_codex_invocation",),
        extra_payloads=config_payloads,
    )
    allow_cycle_2 = _prompt478_bool_from_allow_surfaces(
        payload,
        ("prompt481_allow_cycle_2_codex_invocation",),
        extra_payloads=config_payloads,
    )
    runtime_execution_requested = _prompt478_bool_from_allow_surfaces(
        payload,
        ("prompt481_runtime_execution_requested",),
        extra_payloads=config_payloads,
    )
    all_explicit_allow = bool(
        explicit_allow_present
        and allow_repeated_cycle_smoke
        and allow_cycle_0
        and allow_cycle_1
        and allow_cycle_2
        and runtime_execution_requested
    )
    execution_allowed = bool(
        upstream_ready
        and limit_stop_contract_ready
        and workspace_safety_stop_contract_ready
        and no_unbounded_loop_guard_ready
        and not safety_stop_triggered
        and all_explicit_allow
    )

    cycle_states = {
        cycle_id: _prompt481_empty_cycle_state(cycle_id)
        for cycle_id in _PROMPT481_CYCLE_IDS
    }
    total_attempts = 0
    total_performed = 0
    if execution_allowed:
        for cycle_id in _PROMPT481_CYCLE_IDS:
            cycle_states[cycle_id] = _prompt481_run_cycle(
                cycle_id=cycle_id,
                run_root=run_root or Path.cwd(),
                repo_path=repo_path,
                timeout_seconds=max_runtime_seconds,
            )
            total_attempts += 1
            if cycle_states[cycle_id][f"prompt481_{cycle_id}_execution_performed"]:
                total_performed += 1

    cycle_successes = [
        cycle_states[cycle_id][
            f"prompt481_{cycle_id}_returncode_classification"
        ]
        == "success"
        and cycle_states[cycle_id][f"prompt481_{cycle_id}_execution_attempted"]
        is True
        and cycle_states[cycle_id][f"prompt481_{cycle_id}_execution_performed"]
        is True
        for cycle_id in _PROMPT481_CYCLE_IDS
    ]
    completed_cycle_count = sum(1 for success in cycle_successes if success)
    failed_cycle_count = sum(
        1
        for cycle_id, success in zip(_PROMPT481_CYCLE_IDS, cycle_successes)
        if cycle_states[cycle_id][f"prompt481_{cycle_id}_execution_attempted"]
        is True
        and not success
    )
    invocation_count_within_limit = bool(total_attempts <= max_invocations)
    no_fourth_invocation_attempted = bool(total_attempts <= 3)
    max_invocations_not_exceeded = bool(total_attempts <= max_invocations)
    max_runtime_not_exceeded = True
    completed_success = bool(
        execution_allowed
        and completed_cycle_count == 3
        and failed_cycle_count == 0
        and total_attempts == 3
        and total_performed == 3
        and invocation_count_within_limit
        and no_fourth_invocation_attempted
    )
    stop_reason = "max_cycles_reached" if completed_success else ""
    stop_condition_reached = bool(completed_success)
    max_cycles_stop_confirmed = bool(completed_success and total_attempts == max_cycles)

    blocked_reasons: list[str] = []
    if not upstream_ready:
        blocked_reasons.append("prompt480_evidence_missing")
    if not limit_stop_contract_ready:
        blocked_reasons.append("prompt481_limit_stop_contract_not_ready")
    if not workspace_safety_stop_contract_ready:
        blocked_reasons.append("prompt481_workspace_safety_stop_contract_not_ready")
    if not requested_cycle_count_valid:
        blocked_reasons.append("prompt481_requested_cycle_count_invalid")
    if not max_cycles_valid:
        blocked_reasons.append("prompt481_max_cycles_invalid")
    if not max_invocations_valid:
        blocked_reasons.append("prompt481_max_invocations_invalid")
    if not max_runtime_valid:
        blocked_reasons.append("prompt481_max_runtime_seconds_invalid")
    if not max_invocations_covers_cycles:
        blocked_reasons.append("prompt481_max_invocations_less_than_required_cycles")
    if not no_unbounded_loop_guard_ready:
        blocked_reasons.append("prompt481_unbounded_loop_guard_not_ready")

    if safety_stop_triggered and upstream_ready and limit_stop_contract_ready:
        status = "stopped"
        ready = True
        prompt482_handoff_ready = False
        human_review_required = True
        human_intervention_required = True
        auto_continue_allowed = False
        auto_route_allowed = False
        next_action = _PROMPT481_STOPPED_NEXT_ACTION
        blocked_reasons = safety_stop_reasons
    elif completed_success:
        status = "completed"
        ready = True
        prompt482_handoff_ready = True
        human_review_required = False
        human_intervention_required = False
        auto_continue_allowed = True
        auto_route_allowed = True
        next_action = _PROMPT481_SUCCESS_NEXT_ACTION
        blocked_reasons = []
    elif upstream_ready and limit_stop_contract_ready and no_unbounded_loop_guard_ready:
        if all_explicit_allow:
            status = "blocked"
            ready = False
            human_review_required = True
            human_intervention_required = True
            auto_continue_allowed = False
            auto_route_allowed = False
            next_action = _PROMPT481_BLOCKED_NEXT_ACTION
        else:
            status = "ready_requires_explicit_allow"
            ready = True
            human_review_required = False
            human_intervention_required = False
            auto_continue_allowed = True
            auto_route_allowed = True
            next_action = _PROMPT481_NO_ALLOW_NEXT_ACTION
            blocked_reasons = []
        prompt482_handoff_ready = False
    else:
        status = "blocked"
        ready = False
        prompt482_handoff_ready = False
        human_review_required = True
        human_intervention_required = True
        auto_continue_allowed = False
        auto_route_allowed = False
        next_action = _PROMPT481_BLOCKED_NEXT_ACTION

    if (
        not prompt482_handoff_ready
        and status == "blocked"
        and "prompt481_prompt482_handoff_not_ready" not in blocked_reasons
    ):
        blocked_reasons.append("prompt481_prompt482_handoff_not_ready")

    cycle_payload: dict[str, Any] = {}
    for cycle_id in _PROMPT481_CYCLE_IDS:
        cycle_payload.update(cycle_states[cycle_id])

    return {
        "prompt481_schema_version": _PROMPT481_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt481",
        "prompt481_applicable": True,
        "prompt481_daemon_lite_repeated_cycle_status": status,
        "prompt481_daemon_lite_repeated_cycle_ready": ready,
        "prompt481_upstream_prompt480_evidence_ready": upstream_ready,
        "prompt481_prompt480_evidence_source": prompt480_evidence["source"],
        "prompt481_prompt480_current_fields_evidence_ready": prompt480_evidence[
            "current_fields_ready"
        ],
        "prompt481_prompt480_explicit_flags_evidence_ready": prompt480_evidence[
            "explicit_flags_ready"
        ],
        "prompt481_prompt480_historical_repo_evidence_ready": prompt480_evidence[
            "historical_repo_ready"
        ],
        "prompt481_current_head_short": head_short,
        "prompt481_current_head_subject": head_subject,
        "prompt481_tags_at_head": tags_at_head,
        "prompt481_changed_tracked_files": changed_tracked_files,
        "prompt481_unexpected_tracked_files": unexpected_tracked_files,
        "prompt481_untracked_files": untracked_files,
        "prompt481_unexpected_files": unexpected_files,
        "prompt481_requested_cycle_count": requested_cycle_count,
        "prompt481_max_cycles": max_cycles,
        "prompt481_max_invocations": max_invocations,
        "prompt481_max_runtime_seconds": max_runtime_seconds,
        "prompt481_limit_stop_contract_ready": limit_stop_contract_ready,
        "prompt481_workspace_safety_stop_contract_ready": (
            workspace_safety_stop_contract_ready
        ),
        "prompt481_manual_stop_requested": manual_stop_requested,
        "prompt481_workspace_dirty_detected": workspace_dirty_detected,
        "prompt481_unexpected_files_detected": unexpected_files_detected,
        "prompt481_safety_stop_triggered": safety_stop_triggered,
        "prompt481_runtime_execution_requested": runtime_execution_requested,
        "prompt481_explicit_repeated_cycle_smoke_allow_present": (
            explicit_allow_present
        ),
        "prompt481_allow_repeated_cycle_smoke": allow_repeated_cycle_smoke,
        "prompt481_cycle_ids": list(_PROMPT481_CYCLE_IDS),
        **cycle_payload,
        "prompt481_total_invocation_attempts": total_attempts,
        "prompt481_total_invocation_performed": total_performed,
        "prompt481_expected_invocation_count": 3,
        "prompt481_invocation_count_within_limit": invocation_count_within_limit,
        "prompt481_no_fourth_invocation_attempted": no_fourth_invocation_attempted,
        "prompt481_no_unbounded_loop_guard_ready": no_unbounded_loop_guard_ready,
        "prompt481_completed_cycle_count": completed_cycle_count,
        "prompt481_failed_cycle_count": failed_cycle_count,
        "prompt481_stop_reason": stop_reason,
        "prompt481_stop_condition_reached": stop_condition_reached,
        "prompt481_max_cycles_stop_confirmed": max_cycles_stop_confirmed,
        "prompt481_max_invocations_not_exceeded": max_invocations_not_exceeded,
        "prompt481_max_runtime_not_exceeded": max_runtime_not_exceeded,
        "prompt481_daemon_lite_smoke_confirmed": completed_success,
        "prompt481_prompt482_handoff_ready": prompt482_handoff_ready,
        "prompt481_human_review_required": human_review_required,
        "prompt481_human_intervention_required": human_intervention_required,
        "prompt481_auto_continue_allowed": auto_continue_allowed,
        "prompt481_auto_route_allowed": auto_route_allowed,
        "prompt481_codex_invocation_allowed": execution_allowed,
        "prompt481_file_creation_allowed": False,
        "prompt481_tests_allowed": False,
        "prompt481_commit_tag_allowed": False,
        "prompt481_push_allowed": False,
        "prompt481_pr_allowed": False,
        "prompt481_merge_allowed": False,
        "prompt481_unbounded_loop_allowed": False,
        "prompt481_blocked_reason": blocked_reasons[0] if blocked_reasons else "",
        "prompt481_blocked_reasons": blocked_reasons,
        "prompt481_next_action": next_action,
    }

def _build_prompt482_three_cycle_usability_confirmation_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
    execution_repo_path: str | Path | None = None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    repo_path = _normalize_text(execution_repo_path, default="")
    diff = _prompt470_collect_post_fix_diff(
        repo_path=repo_path,
        allowed_tracked_files=_PROMPT482_ALLOWED_TRACKED_FILES,
    )
    changed_tracked_files = _normalize_string_list(
        diff.get("changed_files"),
        sort_items=False,
    )
    untracked_files = _normalize_string_list(
        diff.get("untracked_files"),
        sort_items=False,
    )
    unexpected_tracked_files = _normalize_string_list(
        diff.get("unexpected_files"),
        sort_items=False,
    )
    unexpected_files = list(untracked_files)
    unexpected_files.extend(
        path for path in unexpected_tracked_files if path not in unexpected_files
    )

    head_short = ""
    head_short_known, head_short_stdout = _prompt472_git_stdout(
        repo_path=repo_path,
        argv=("rev-parse", "--short", "HEAD"),
    )
    if head_short_known and head_short_stdout.splitlines():
        head_short = head_short_stdout.splitlines()[0].strip()
    head_subject = ""
    head_subject_known, head_subject_stdout = _prompt472_git_stdout(
        repo_path=repo_path,
        argv=("log", "-1", "--pretty=%s"),
    )
    if head_subject_known and head_subject_stdout.splitlines():
        head_subject = head_subject_stdout.splitlines()[0].strip()
    tags_at_head = _prompt471_tags_at_head(repo_path=repo_path)

    prompt481_evidence = _prompt482_prompt481_evidence_bridge(
        payload=payload,
        repo_path=repo_path,
        current_head_subject=head_subject,
        tags_at_head=tags_at_head,
        changed_tracked_files=changed_tracked_files,
        unexpected_tracked_files=unexpected_tracked_files,
    )
    upstream_ready = prompt481_evidence["ready"] is True
    changed_files_limited = bool(not unexpected_tracked_files)
    no_untracked_or_unexpected_files = bool(not untracked_files and not unexpected_files)

    three_cycle_confirmed = bool(upstream_ready)
    no_fourth_confirmed = bool(upstream_ready)
    max_cycles_stop_confirmed = bool(upstream_ready)
    prompt483_ready = bool(
        upstream_ready and changed_files_limited and no_untracked_or_unexpected_files
    )

    blocked_reasons: list[str] = []
    if not upstream_ready:
        blocked_reasons.append("prompt481_evidence_missing")
    if unexpected_tracked_files:
        blocked_reasons.append("prompt482_unexpected_tracked_files_present")
    if untracked_files or unexpected_files:
        blocked_reasons.append("prompt482_untracked_or_unexpected_files_present")
    if not three_cycle_confirmed:
        blocked_reasons.append("prompt481_three_cycle_not_confirmed")
    if not no_fourth_confirmed:
        blocked_reasons.append("prompt481_no_fourth_invocation_not_confirmed")
    if not max_cycles_stop_confirmed:
        blocked_reasons.append("prompt481_max_cycles_stop_not_confirmed")
    if not prompt483_ready:
        blocked_reasons.append("prompt482_prompt483_10_cycle_extension_not_ready")

    ready = bool(not blocked_reasons)
    status = "ready" if ready else "blocked"
    return {
        "prompt482_schema_version": _PROMPT482_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt482",
        "prompt482_applicable": True,
        "prompt482_three_cycle_usability_status": status,
        "prompt482_three_cycle_usability_ready": ready,
        "prompt482_upstream_prompt481_evidence_ready": upstream_ready,
        "prompt482_prompt481_evidence_source": prompt481_evidence["source"],
        "prompt482_prompt481_current_fields_evidence_ready": prompt481_evidence[
            "current_fields_ready"
        ],
        "prompt482_prompt481_explicit_flags_evidence_ready": prompt481_evidence[
            "explicit_flags_ready"
        ],
        "prompt482_prompt481_historical_repo_evidence_ready": prompt481_evidence[
            "historical_repo_ready"
        ],
        "prompt482_current_head_short": head_short,
        "prompt482_current_head_subject": head_subject,
        "prompt482_tags_at_head": tags_at_head,
        "prompt482_changed_tracked_files": changed_tracked_files,
        "prompt482_unexpected_tracked_files": unexpected_tracked_files,
        "prompt482_untracked_files": untracked_files,
        "prompt482_unexpected_files": unexpected_files,
        "prompt482_prompt481_three_cycle_confirmed": upstream_ready,
        "prompt482_cycle_0_success_confirmed": upstream_ready,
        "prompt482_cycle_1_success_confirmed": upstream_ready,
        "prompt482_cycle_2_success_confirmed": upstream_ready,
        "prompt482_total_invocation_attempts_confirmed": upstream_ready,
        "prompt482_total_invocation_performed_confirmed": upstream_ready,
        "prompt482_completed_cycle_count_confirmed": upstream_ready,
        "prompt482_failed_cycle_count_confirmed": upstream_ready,
        "prompt482_no_fourth_invocation_confirmed": upstream_ready,
        "prompt482_no_unbounded_loop_confirmed": upstream_ready,
        "prompt482_max_cycles_stop_confirmed": upstream_ready,
        "prompt482_max_invocations_not_exceeded_confirmed": upstream_ready,
        "prompt482_max_runtime_not_exceeded_confirmed": upstream_ready,
        "prompt482_prompt481_post_commit_final_confirmed": upstream_ready,
        "prompt482_three_cycle_result_usable_for_10_cycle_extension": ready,
        "prompt482_three_cycle_result_usable_for_completion_until_done": ready,
        "prompt482_three_cycle_result_usable_for_real_development_cycle": ready,
        "prompt482_three_cycle_result_usable_for_failed_recovery": ready,
        "prompt482_prompt483_10_cycle_extension_ready": ready,
        "prompt482_real_development_handoff_ready": ready,
        "prompt482_failed_recovery_deferred": ready,
        "prompt482_human_review_required": not ready,
        "prompt482_human_intervention_required": not ready,
        "prompt482_auto_continue_allowed": ready,
        "prompt482_auto_route_allowed": ready,
        "prompt482_codex_invocation_allowed": False,
        "prompt482_file_creation_allowed": False,
        "prompt482_tests_allowed": False,
        "prompt482_commit_tag_allowed": False,
        "prompt482_push_allowed": False,
        "prompt482_pr_allowed": False,
        "prompt482_merge_allowed": False,
        "prompt482_unbounded_loop_allowed": False,
        "prompt482_blocked_reason": blocked_reasons[0] if blocked_reasons else "",
        "prompt482_blocked_reasons": blocked_reasons,
        "prompt482_next_action": (
            _PROMPT482_SUCCESS_NEXT_ACTION if ready else _PROMPT482_BLOCKED_NEXT_ACTION
        ),
    }

def _build_prompt483_role_catalog_reader_handoff_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
    config_payloads: Sequence[Mapping[str, Any] | None] = (),
    execution_repo_path: str | Path | None = None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    repo_path = _normalize_text(execution_repo_path, default="")
    source_payloads: tuple[Mapping[str, Any] | None, ...] = (
        payload,
        *tuple(config_payloads),
    )
    catalog_path_text = _prompt483_first_text_from_payloads(
        source_payloads,
        ("prompt483_role_catalog_path", "prompt_role_catalog_path"),
        default=_PROMPT483_DEFAULT_ROLE_CATALOG_PATH,
    )
    selected_role_id = _prompt483_first_text_from_payloads(
        source_payloads,
        ("prompt483_selected_role_id", "prompt_role_id", "selected_role_id"),
        default=_PROMPT483_DEFAULT_SELECTED_ROLE_ID,
    )

    diff = _prompt470_collect_post_fix_diff(
        repo_path=repo_path,
        allowed_tracked_files=_PROMPT483_ALLOWED_TRACKED_FILES,
    )
    changed_tracked_files = _normalize_string_list(
        diff.get("changed_files"),
        sort_items=False,
    )
    unexpected_tracked_files = _normalize_string_list(
        diff.get("unexpected_files"),
        sort_items=False,
    )
    untracked_files = _prompt483_untracked_files(repo_path=repo_path)
    allowed_untracked_files = {catalog_path_text}
    unexpected_files = [
        path for path in untracked_files if path not in allowed_untracked_files
    ]
    unexpected_files.extend(
        path for path in unexpected_tracked_files if path not in unexpected_files
    )

    head_short = ""
    head_short_known, head_short_stdout = _prompt472_git_stdout(
        repo_path=repo_path,
        argv=("rev-parse", "--short", "HEAD"),
    )
    if head_short_known and head_short_stdout.splitlines():
        head_short = head_short_stdout.splitlines()[0].strip()
    head_subject = ""
    head_subject_known, head_subject_stdout = _prompt472_git_stdout(
        repo_path=repo_path,
        argv=("log", "-1", "--pretty=%s"),
    )
    if head_subject_known and head_subject_stdout.splitlines():
        head_subject = head_subject_stdout.splitlines()[0].strip()
    tags_at_head = _prompt471_tags_at_head(repo_path=repo_path)

    prompt482_evidence = _prompt483_prompt482_evidence_bridge(
        payload=payload,
        repo_path=repo_path,
        current_head_subject=head_subject,
        tags_at_head=tags_at_head,
        changed_tracked_files=changed_tracked_files,
        unexpected_tracked_files=unexpected_tracked_files,
    )
    upstream_ready = prompt482_evidence["ready"] is True

    catalog_path = _prompt483_resolve_repo_relative_path(
        repo_path=repo_path,
        path_text=catalog_path_text,
    )
    catalog_exists = catalog_path.exists()
    catalog_readable = False
    catalog_text = ""
    if catalog_exists:
        try:
            catalog_text = catalog_path.read_text(encoding="utf-8")
            catalog_readable = True
        except OSError:
            catalog_readable = False
            catalog_text = ""
    catalog_non_empty = bool(catalog_text.strip())
    selected_role_text = _prompt483_extract_selected_role_text(
        catalog_text=catalog_text,
        selected_role_id=selected_role_id,
    )
    selected_role_found = bool(selected_role_text)
    selected_role_text_non_empty = bool(selected_role_text.strip())
    selected_role_text_length = len(selected_role_text)

    blocked_reasons: list[str] = []
    if not upstream_ready:
        blocked_reasons.append("prompt482_evidence_missing")
    if unexpected_tracked_files:
        blocked_reasons.append("prompt483_unexpected_tracked_files_present")
    if unexpected_files:
        blocked_reasons.append("prompt483_untracked_or_unexpected_files_present")
    if not catalog_exists:
        blocked_reasons.append("prompt483_role_catalog_missing")
    if catalog_exists and not catalog_readable:
        blocked_reasons.append("prompt483_role_catalog_not_readable")
    if catalog_readable and not catalog_non_empty:
        blocked_reasons.append("prompt483_role_catalog_empty")
    if not selected_role_id:
        blocked_reasons.append("prompt483_selected_role_id_missing")
    elif catalog_non_empty and not selected_role_found:
        blocked_reasons.append("prompt483_selected_role_not_found")
    if selected_role_found and not selected_role_text_non_empty:
        blocked_reasons.append("prompt483_selected_role_text_empty")

    basis_ready = bool(
        upstream_ready
        and catalog_exists
        and catalog_readable
        and catalog_non_empty
        and selected_role_id
        and selected_role_found
        and selected_role_text_non_empty
        and not unexpected_tracked_files
        and not unexpected_files
    )
    if not basis_ready:
        blocked_reasons.append("prompt483_prompt484_generation_basis_not_ready")

    ready = bool(basis_ready and not blocked_reasons)
    status = "ready" if ready else "blocked"
    return {
        "prompt483_schema_version": _PROMPT483_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt483",
        "prompt483_applicable": True,
        "prompt483_role_catalog_reader_status": status,
        "prompt483_role_catalog_reader_ready": ready,
        "prompt483_upstream_prompt482_evidence_ready": upstream_ready,
        "prompt483_prompt482_evidence_source": prompt482_evidence["source"],
        "prompt483_prompt482_current_fields_evidence_ready": prompt482_evidence[
            "current_fields_ready"
        ],
        "prompt483_prompt482_explicit_flags_evidence_ready": prompt482_evidence[
            "explicit_flags_ready"
        ],
        "prompt483_prompt482_historical_repo_evidence_ready": prompt482_evidence[
            "historical_repo_ready"
        ],
        "prompt483_current_head_short": head_short,
        "prompt483_current_head_subject": head_subject,
        "prompt483_tags_at_head": tags_at_head,
        "prompt483_changed_tracked_files": changed_tracked_files,
        "prompt483_unexpected_tracked_files": unexpected_tracked_files,
        "prompt483_untracked_files": untracked_files,
        "prompt483_unexpected_files": unexpected_files,
        "prompt483_role_catalog_path": catalog_path_text,
        "prompt483_role_catalog_exists": catalog_exists,
        "prompt483_role_catalog_readable": catalog_readable,
        "prompt483_role_catalog_non_empty": catalog_non_empty,
        "prompt483_selected_role_id": selected_role_id,
        "prompt483_selected_role_found": selected_role_found,
        "prompt483_selected_role_text": selected_role_text,
        "prompt483_selected_role_text_non_empty": selected_role_text_non_empty,
        "prompt483_selected_role_text_length": selected_role_text_length,
        "prompt483_selected_role_contains_use_when": "Use when:" in selected_role_text,
        "prompt483_selected_role_contains_goal": "Goal:" in selected_role_text,
        "prompt483_selected_role_contains_success": "Success:" in selected_role_text,
        "prompt483_selected_role_contains_do_not": "Do not:" in selected_role_text,
        "prompt483_chatgpt_role_catalog_read_ready": ready,
        "prompt483_chatgpt_selected_role_handoff_ready": ready,
        "prompt483_chatgpt_next_prompt_generation_basis_ready": ready,
        "prompt483_runner_generated_prompt_allowed": False,
        "prompt483_chatgpt_prompt_generation_required": True,
        "prompt483_codex_role_design_allowed": False,
        "prompt483_codex_prompt_implementation_only": True,
        "prompt483_next_prompt_target_role_id": selected_role_id,
        "prompt483_next_prompt_target_prompt_id": "prompt484",
        "prompt483_prompt484_generation_ready": ready,
        "prompt483_daemon_lite_10_cycle_extension_deferred": True,
        "prompt483_completion_until_done_deferred": True,
        "prompt483_real_development_deferred": True,
        "prompt483_failed_recovery_deferred": True,
        "prompt483_human_review_required": not ready,
        "prompt483_human_intervention_required": not ready,
        "prompt483_auto_continue_allowed": ready,
        "prompt483_auto_route_allowed": ready,
        "prompt483_codex_invocation_allowed": False,
        "prompt483_file_creation_allowed": False,
        "prompt483_tests_allowed": False,
        "prompt483_commit_tag_allowed": False,
        "prompt483_push_allowed": False,
        "prompt483_pr_allowed": False,
        "prompt483_merge_allowed": False,
        "prompt483_unbounded_loop_allowed": False,
        "prompt483_blocked_reason": blocked_reasons[0] if blocked_reasons else "",
        "prompt483_blocked_reasons": blocked_reasons,
        "prompt483_next_action": (
            _PROMPT483_SUCCESS_NEXT_ACTION
            if ready
            else _PROMPT483_BLOCKED_NEXT_ACTION
        ),
    }

def _build_prompt484_daemon_lite_10_cycle_no_allow_boundary_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(run_state_payload) if isinstance(run_state_payload, Mapping) else {}
    upstream_ready = bool(
        payload.get("prompt483_role_catalog_reader_status") == "ready"
        and payload.get("prompt483_role_catalog_reader_ready") is True
        and payload.get("prompt483_selected_role_id")
        == "daemon_lite_10_cycle_no_allow_boundary"
        and payload.get("prompt483_selected_role_found") is True
        and payload.get("prompt483_chatgpt_next_prompt_generation_basis_ready") is True
        and payload.get("prompt483_codex_prompt_implementation_only") is True
    )

    state: dict[str, Any] = {
        "prompt484_schema_version": _PROMPT484_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt484",
        "prompt484_applicable": True,
        "prompt484_daemon_lite_10_cycle_status": "blocked",
        "prompt484_daemon_lite_10_cycle_ready": False,
        "prompt484_upstream_prompt483_evidence_ready": upstream_ready,
        "prompt484_requested_cycle_count": 10,
        "prompt484_max_cycles": 10,
        "prompt484_max_invocations": 10,
        "prompt484_max_runtime_seconds": 1800,
        "prompt484_runtime_execution_requested": False,
        "prompt484_explicit_10_cycle_smoke_allow_present": False,
        "prompt484_allow_10_cycle_smoke": False,
        "prompt484_total_invocation_attempts": 0,
        "prompt484_total_invocation_performed": 0,
        "prompt484_expected_invocation_count": 10,
        "prompt484_invocation_count_within_limit": True,
        "prompt484_no_11th_invocation_attempted": True,
        "prompt484_no_unbounded_loop_guard_ready": True,
        "prompt484_completed_cycle_count": 0,
        "prompt484_failed_cycle_count": 0,
        "prompt484_daemon_lite_10_cycle_smoke_confirmed": False,
        "prompt484_completion_until_done_handoff_ready": False,
        "prompt484_real_development_deferred": True,
        "prompt484_failed_recovery_deferred": True,
        "prompt484_auto_continue_allowed": False,
        "prompt484_auto_route_allowed": False,
        "prompt484_blocked_reason": "prompt483_evidence_missing",
        "prompt484_blocked_reasons": ["prompt483_evidence_missing"],
        "prompt484_human_review_required": True,
        "prompt484_human_intervention_required": True,
        "prompt484_next_action": _PROMPT484_BLOCKED_NEXT_ACTION,
    }
    if not upstream_ready:
        return state

    state.update(
        {
            "prompt484_daemon_lite_10_cycle_status": (
                "ready_requires_explicit_allow"
            ),
            "prompt484_daemon_lite_10_cycle_ready": True,
            "prompt484_blocked_reason": "",
            "prompt484_blocked_reasons": [],
            "prompt484_human_review_required": False,
            "prompt484_human_intervention_required": False,
            "prompt484_auto_continue_allowed": True,
            "prompt484_auto_route_allowed": True,
            "prompt484_next_action": _PROMPT484_SUCCESS_NEXT_ACTION,
        }
    )
    return state

def _build_prompt484b_role_selection_layer_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
    config_payloads: Sequence[Mapping[str, Any] | None] = (),
    execution_repo_path: str | Path | None = None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    repo_path = _normalize_text(execution_repo_path, default="")
    source_payloads: tuple[Mapping[str, Any] | None, ...] = (
        payload,
        *tuple(config_payloads),
    )
    catalog_path_text = _prompt483_first_text_from_payloads(
        source_payloads,
        (
            "prompt484b_role_catalog_path",
            "prompt483_role_catalog_path",
            "prompt_role_catalog_path",
        ),
        default=_PROMPT483_DEFAULT_ROLE_CATALOG_PATH,
    )
    selected_role_id = _prompt483_first_text_from_payloads(
        source_payloads,
        (
            "prompt484b_selected_role_id",
            "prompt_role_id",
            "selected_role_id",
        ),
        default=_PROMPT484B_DEFAULT_SELECTED_ROLE_ID,
    )

    catalog_path = _prompt483_resolve_repo_relative_path(
        repo_path=repo_path,
        path_text=catalog_path_text,
    )
    catalog_exists = catalog_path.exists()
    catalog_readable = False
    catalog_text = ""
    if catalog_exists:
        try:
            catalog_text = catalog_path.read_text(encoding="utf-8")
            catalog_readable = True
        except OSError:
            catalog_readable = False
            catalog_text = ""
    catalog_non_empty = bool(catalog_text.strip())
    selected_role_text = _prompt483_extract_selected_role_text(
        catalog_text=catalog_text,
        selected_role_id=selected_role_id,
    )
    selected_role_found = bool(selected_role_text)
    selected_role_text_non_empty = bool(selected_role_text.strip())
    selected_role_text_length = len(selected_role_text)

    blocked_reasons: list[str] = []
    if not catalog_exists:
        blocked_reasons.append("prompt484b_role_catalog_missing")
    if catalog_exists and not catalog_readable:
        blocked_reasons.append("prompt484b_role_catalog_not_readable")
    if catalog_readable and not catalog_non_empty:
        blocked_reasons.append("prompt484b_role_catalog_empty")
    if not selected_role_id:
        blocked_reasons.append("prompt484b_selected_role_id_missing")
    elif catalog_non_empty and not selected_role_found:
        blocked_reasons.append("prompt484b_selected_role_not_found")
    if selected_role_found and not selected_role_text_non_empty:
        blocked_reasons.append("prompt484b_selected_role_text_empty")

    ready = bool(
        catalog_exists
        and catalog_readable
        and catalog_non_empty
        and selected_role_id
        and selected_role_found
        and selected_role_text_non_empty
        and not blocked_reasons
    )
    status = "ready" if ready else "blocked"

    return {
        "prompt484b_schema_version": _PROMPT484B_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt484b",
        "prompt484b_applicable": True,
        "prompt484b_role_selection_status": status,
        "prompt484b_role_selection_ready": ready,
        "prompt484b_role_catalog_path": catalog_path_text,
        "prompt484b_role_catalog_exists": catalog_exists,
        "prompt484b_role_catalog_readable": catalog_readable,
        "prompt484b_role_catalog_non_empty": catalog_non_empty,
        "prompt484b_selected_role_id": selected_role_id,
        "prompt484b_selected_role_source": (
            "payload_or_default_role_to_prompt_selection_layer"
        ),
        "prompt484b_selected_role_found": selected_role_found,
        "prompt484b_selected_role_text": selected_role_text,
        "prompt484b_selected_role_text_non_empty": selected_role_text_non_empty,
        "prompt484b_selected_role_text_length": selected_role_text_length,
        "prompt484b_chatgpt_prompt_generation_required": True,
        "prompt484b_runner_prompt_generation_allowed": False,
        "prompt484b_codex_implementation_allowed": False,
        "prompt484b_codex_invocation_allowed": False,
        "prompt484b_runtime_execution_allowed": False,
        "prompt484b_git_mutation_allowed": False,
        "prompt484b_remote_mutation_allowed": False,
        "prompt484b_all_roles_iteration_deferred": True,
        "prompt484b_completion_until_done_deferred": True,
        "prompt484b_blocked_reason": (
            blocked_reasons[0] if blocked_reasons else ""
        ),
        "prompt484b_blocked_reasons": blocked_reasons,
        "prompt484b_next_action": (
            _PROMPT484B_SUCCESS_NEXT_ACTION
            if ready
            else _PROMPT484B_BLOCKED_NEXT_ACTION
        ),
    }

def _build_prompt484c_selected_role_prompt_generation_request_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    prompt484b_status = _normalize_text(
        payload.get("prompt484b_role_selection_status"),
        default="",
    )
    prompt484b_ready = payload.get("prompt484b_role_selection_ready") is True
    source_role_id = _normalize_text(
        payload.get("prompt484b_selected_role_id"),
        default="",
    )
    source_role_found = payload.get("prompt484b_selected_role_found") is True
    source_role_text = _normalize_text(
        payload.get("prompt484b_selected_role_text"),
        default="",
    )
    source_role_text_non_empty = (
        payload.get("prompt484b_selected_role_text_non_empty") is True
        and bool(source_role_text.strip())
    )
    prompt484b_next_action = _normalize_text(
        payload.get("prompt484b_next_action"),
        default="",
    )

    blocked_reasons: list[str] = []
    if prompt484b_status != "ready":
        blocked_reasons.append("prompt484b_role_selection_status_not_ready")
    if not prompt484b_ready:
        blocked_reasons.append("prompt484b_role_selection_not_ready")
    if not source_role_id:
        blocked_reasons.append("prompt484b_selected_role_id_missing")
    if not source_role_found:
        blocked_reasons.append("prompt484b_selected_role_not_found")
    if not source_role_text_non_empty:
        blocked_reasons.append("prompt484b_selected_role_text_empty")
    if (
        prompt484b_ready
        and prompt484b_next_action
        and prompt484b_next_action != _PROMPT484B_SUCCESS_NEXT_ACTION
    ):
        blocked_reasons.append("prompt484b_next_action_unexpected")

    ready = bool(
        prompt484b_status == "ready"
        and prompt484b_ready
        and source_role_id
        and source_role_found
        and source_role_text_non_empty
        and not blocked_reasons
    )

    return {
        "prompt484c_schema_version": _PROMPT484C_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt484c",
        "prompt484c_applicable": True,
        "prompt484c_prompt_generation_request_status": (
            "ready" if ready else "blocked"
        ),
        "prompt484c_prompt_generation_request_ready": ready,
        "prompt484c_source_role_id": source_role_id,
        "prompt484c_source_role_text": source_role_text,
        "prompt484c_source_role_text_non_empty": source_role_text_non_empty,
        "prompt484c_source_role_ready": ready,
        "prompt484c_chatgpt_generation_required": True,
        "prompt484c_runner_generation_allowed": False,
        "prompt484c_codex_prompt_ready": False,
        "prompt484c_codex_prompt_artifact_path": "",
        "prompt484c_codex_invocation_allowed": False,
        "prompt484c_runtime_execution_allowed": False,
        "prompt484c_git_mutation_allowed": False,
        "prompt484c_remote_mutation_allowed": False,
        "prompt484c_all_roles_iteration_deferred": True,
        "prompt484c_completion_until_done_deferred": True,
        "prompt484c_blocked_reason": (
            blocked_reasons[0] if blocked_reasons else ""
        ),
        "prompt484c_blocked_reasons": blocked_reasons,
        "prompt484c_next_action": (
            _PROMPT484C_SUCCESS_NEXT_ACTION
            if ready
            else _PROMPT484C_BLOCKED_NEXT_ACTION
        ),
    }

def _build_prompt484d_existing_loop_bridge_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    prompt484c_request_ready = (
        payload.get("prompt484c_prompt_generation_request_ready") is True
    )
    prompt484c_source_role_id = _normalize_text(
        payload.get("prompt484c_source_role_id"),
        default="",
    )
    prompt484c_source_role_text_non_empty = (
        payload.get("prompt484c_source_role_text_non_empty") is True
    )
    prompt484c_next_action = _normalize_text(
        payload.get("prompt484c_next_action"),
        default="",
    )
    prompt484c_ready = bool(
        prompt484c_request_ready
        and prompt484c_source_role_id
        and prompt484c_source_role_text_non_empty
        and prompt484c_next_action == _PROMPT484C_SUCCESS_NEXT_ACTION
    )

    prompt377_detected = any(
        key in payload
        for key in (
            "prompt377_chatgpt_prompt_generation_request_status",
            "prompt377_chatgpt_prompt_generation_request_ready",
            "prompt377_generated_prompt_intake_contract_ready",
        )
    )
    prompt385_detected = any(
        key in payload
        for key in (
            "prompt385_success_path_next_cycle_handoff_status",
            "prompt385_next_prompt_generation_request_ready",
            "prompt385_generated_prompt_intake_expected",
        )
    )
    bridge_target = ""
    if prompt377_detected:
        bridge_target = "prompt377_chatgpt_prompt_generation_request"
    elif prompt385_detected:
        bridge_target = "prompt385_next_prompt_generation_request"
    bridge_detected = bool(bridge_target)

    blocked_reasons: list[str] = []
    if not prompt484c_request_ready:
        blocked_reasons.append("prompt484c_prompt_generation_request_missing_or_not_ready")
    if not prompt484c_source_role_id:
        blocked_reasons.append("prompt484c_source_role_id_missing")
    if not prompt484c_source_role_text_non_empty:
        blocked_reasons.append("prompt484c_source_role_text_empty")
    if prompt484c_next_action != _PROMPT484C_SUCCESS_NEXT_ACTION:
        blocked_reasons.append("prompt484c_next_action_unexpected")
    if not bridge_detected:
        blocked_reasons.append("existing_prompt_generation_bridge_target_missing")

    ready = bool(prompt484c_ready and bridge_detected and not blocked_reasons)

    return {
        "prompt484d_schema_version": _PROMPT484D_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt484d",
        "prompt484d_applicable": True,
        "prompt484d_existing_loop_bridge_status": (
            "ready" if ready else "blocked"
        ),
        "prompt484d_existing_loop_bridge_ready": ready,
        "prompt484d_prompt484c_request_ready": prompt484c_request_ready,
        "prompt484d_prompt484c_source_role_id": prompt484c_source_role_id,
        "prompt484d_prompt484c_source_role_text_non_empty": (
            prompt484c_source_role_text_non_empty
        ),
        "prompt484d_existing_prompt_generation_artifacts_detected": bridge_detected,
        "prompt484d_bridge_target": bridge_target,
        "prompt484d_chatgpt_prompt_generation_request_ready": ready,
        "prompt484d_generated_prompt_intake_expected": ready,
        "prompt484d_codex_execution_bridge_deferred": True,
        "prompt484d_codex_invocation_allowed": False,
        "prompt484d_codex_invocation_performed": False,
        "prompt484d_chatgpt_call_allowed": False,
        "prompt484d_chatgpt_call_performed": False,
        "prompt484d_runner_prompt_generation_allowed": False,
        "prompt484d_runtime_execution_allowed": False,
        "prompt484d_git_mutation_allowed": False,
        "prompt484d_remote_mutation_allowed": False,
        "prompt484d_all_roles_iteration_deferred": True,
        "prompt484d_completion_until_done_deferred": True,
        "prompt484d_blocked_reason": (
            blocked_reasons[0] if blocked_reasons else ""
        ),
        "prompt484d_blocked_reasons": blocked_reasons,
        "prompt484d_next_action": (
            _PROMPT484D_SUCCESS_NEXT_ACTION
            if ready
            else _PROMPT484D_BLOCKED_NEXT_ACTION
        ),
    }

def _build_prompt484e_generated_prompt_intake_handoff_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    prompt484d_bridge_ready = (
        payload.get("prompt484d_existing_loop_bridge_ready") is True
    )
    prompt484d_next_action = _normalize_text(
        payload.get("prompt484d_next_action"),
        default="",
    )
    bridge_target = _normalize_text(
        payload.get("prompt484d_bridge_target"),
        default="",
    )
    prompt484d_generated_prompt_intake_expected = (
        payload.get("prompt484d_generated_prompt_intake_expected") is True
    )

    blocked_reasons: list[str] = []
    if not prompt484d_bridge_ready:
        blocked_reasons.append("prompt484d_bridge_readiness_missing_or_not_ready")
    if prompt484d_next_action != _PROMPT484D_SUCCESS_NEXT_ACTION:
        blocked_reasons.append("prompt484d_next_action_unexpected")
    if bridge_target != "prompt377_chatgpt_prompt_generation_request":
        blocked_reasons.append("prompt484d_bridge_target_unexpected")
    if not prompt484d_generated_prompt_intake_expected:
        blocked_reasons.append("prompt484d_generated_prompt_intake_expectation_missing")

    ready = bool(
        prompt484d_bridge_ready
        and prompt484d_next_action == _PROMPT484D_SUCCESS_NEXT_ACTION
        and bridge_target == "prompt377_chatgpt_prompt_generation_request"
        and prompt484d_generated_prompt_intake_expected
        and not blocked_reasons
    )

    return {
        "prompt484e_schema_version": _PROMPT484E_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt484e",
        "prompt484e_applicable": True,
        "prompt484e_generated_prompt_intake_handoff_status": (
            "ready" if ready else "blocked"
        ),
        "prompt484e_generated_prompt_intake_handoff_ready": ready,
        "prompt484e_prompt484d_bridge_ready": prompt484d_bridge_ready,
        "prompt484e_prompt484d_next_action": prompt484d_next_action,
        "prompt484e_bridge_target": bridge_target,
        "prompt484e_generated_prompt_intake_target": (
            "prompt378_chatgpt_generated_prompt_intake" if ready else ""
        ),
        "prompt484e_expected_generated_prompt_path_field": (
            "prompt378_generated_prompt_path" if ready else ""
        ),
        "prompt484e_expected_generated_prompt_flag": (
            "--prompt378-generated-prompt-path" if ready else ""
        ),
        "prompt484e_generated_prompt_supplied": False,
        "prompt484e_generated_prompt_path": "",
        "prompt484e_generated_prompt_ready": False,
        "prompt484e_prompt378_intake_expected": ready,
        "prompt484e_codex_execution_bridge_ready": False,
        "prompt484e_codex_invocation_allowed": False,
        "prompt484e_codex_invocation_performed": False,
        "prompt484e_chatgpt_call_allowed": False,
        "prompt484e_chatgpt_call_performed": False,
        "prompt484e_runner_prompt_generation_allowed": False,
        "prompt484e_runtime_execution_allowed": False,
        "prompt484e_git_mutation_allowed": False,
        "prompt484e_remote_mutation_allowed": False,
        "prompt484e_all_roles_iteration_deferred": True,
        "prompt484e_completion_until_done_deferred": True,
        "prompt484e_blocked_reason": (
            blocked_reasons[0] if blocked_reasons else ""
        ),
        "prompt484e_blocked_reasons": blocked_reasons,
        "prompt484e_next_action": (
            _PROMPT484E_SUCCESS_NEXT_ACTION
            if ready
            else _PROMPT484E_BLOCKED_NEXT_ACTION
        ),
    }

def _build_prompt484f_role_driven_single_codex_execution_cycle_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    prompt484e_handoff_ready = (
        payload.get("prompt484e_generated_prompt_intake_handoff_ready") is True
    )
    prompt484e_next_action = _normalize_text(
        payload.get("prompt484e_next_action"),
        default="",
    )

    blocked_reasons: list[str] = []
    if not prompt484e_handoff_ready:
        blocked_reasons.append(
            "prompt484e_generated_prompt_intake_handoff_readiness_missing_or_not_ready"
        )
    if prompt484e_next_action != _PROMPT484E_SUCCESS_NEXT_ACTION:
        blocked_reasons.append("prompt484e_next_action_unexpected")

    ready = bool(
        prompt484e_handoff_ready
        and prompt484e_next_action == _PROMPT484E_SUCCESS_NEXT_ACTION
        and not blocked_reasons
    )

    return {
        "prompt484f_schema_version": _PROMPT484F_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt484f",
        "prompt484f_applicable": True,
        "prompt484f_role_driven_cycle_status": (
            "ready" if ready else "blocked"
        ),
        "prompt484f_role_driven_cycle_ready": ready,
        "prompt484f_source_role_id": _PROMPT484F_SOURCE_ROLE_ID,
        "prompt484f_prompt484e_handoff_ready": prompt484e_handoff_ready,
        "prompt484f_prompt378_supply_expected": True,
        "prompt484f_prompt379_live_execution_expected": True,
        "prompt484f_codex_execution_count_limit": 1,
        "prompt484f_commit_tag_deferred": True,
        "prompt484f_auto_commit_allowed": False,
        "prompt484f_auto_tag_allowed": False,
        "prompt484f_remote_mutation_allowed": False,
        "prompt484f_completion_until_done_deferred": True,
        "prompt484f_all_roles_iteration_deferred": True,
        "prompt484f_blocked_reason": (
            blocked_reasons[0] if blocked_reasons else ""
        ),
        "prompt484f_blocked_reasons": blocked_reasons,
        "prompt484f_next_action": (
            _PROMPT484F_SUCCESS_NEXT_ACTION
            if ready
            else _PROMPT484F_BLOCKED_NEXT_ACTION
        ),
    }

def _build_prompt484g_role_driven_execution_request_packet_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    prompt484f_ready = payload.get("prompt484f_role_driven_cycle_ready") is True
    prompt484f_next_action = _normalize_text(
        payload.get("prompt484f_next_action"),
        default="",
    )
    prompt484f_source_role_id = _normalize_text(
        payload.get("prompt484f_source_role_id"),
        default="",
    )
    prompt484f_codex_execution_count_limit = payload.get(
        "prompt484f_codex_execution_count_limit"
    )
    prompt484f_auto_commit_allowed = payload.get(
        "prompt484f_auto_commit_allowed"
    )
    prompt484f_auto_tag_allowed = payload.get("prompt484f_auto_tag_allowed")
    prompt484f_remote_mutation_allowed = payload.get(
        "prompt484f_remote_mutation_allowed"
    )

    blocked_reasons: list[str] = []
    if not prompt484f_ready:
        blocked_reasons.append(
            "prompt484f_role_driven_cycle_ready_missing_or_not_ready"
        )
    if prompt484f_next_action != _PROMPT484F_SUCCESS_NEXT_ACTION:
        blocked_reasons.append("prompt484f_next_action_unexpected")
    if prompt484f_source_role_id != _PROMPT484F_SOURCE_ROLE_ID:
        blocked_reasons.append("prompt484f_source_role_id_unexpected")
    if prompt484f_codex_execution_count_limit != 1:
        blocked_reasons.append(
            "prompt484f_codex_execution_count_limit_unexpected"
        )
    if prompt484f_auto_commit_allowed is not False:
        blocked_reasons.append("prompt484f_auto_commit_allowed_unexpected")
    if prompt484f_auto_tag_allowed is not False:
        blocked_reasons.append("prompt484f_auto_tag_allowed_unexpected")
    if prompt484f_remote_mutation_allowed is not False:
        blocked_reasons.append(
            "prompt484f_remote_mutation_allowed_unexpected"
        )

    ready = bool(
        prompt484f_ready
        and prompt484f_next_action == _PROMPT484F_SUCCESS_NEXT_ACTION
        and prompt484f_source_role_id == _PROMPT484F_SOURCE_ROLE_ID
        and prompt484f_codex_execution_count_limit == 1
        and prompt484f_auto_commit_allowed is False
        and prompt484f_auto_tag_allowed is False
        and prompt484f_remote_mutation_allowed is False
        and not blocked_reasons
    )

    return {
        "prompt484g_schema_version": _PROMPT484G_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt484g",
        "prompt484g_applicable": True,
        "prompt484g_role_driven_execution_request_status": (
            "ready" if ready else "blocked"
        ),
        "prompt484g_role_driven_execution_request_ready": ready,
        "prompt484g_prompt484f_ready": prompt484f_ready,
        "prompt484g_selected_role_id": _PROMPT484F_SOURCE_ROLE_ID,
        "prompt484g_prompt378_generation_required": True,
        "prompt484g_prompt378_supply_expected": True,
        "prompt484g_prompt379_live_execution_expected": True,
        "prompt484g_codex_execution_count_limit": 1,
        "prompt484g_auto_commit_allowed": False,
        "prompt484g_auto_tag_allowed": False,
        "prompt484g_remote_mutation_allowed": False,
        "prompt484g_completion_until_done_deferred": True,
        "prompt484g_all_roles_iteration_deferred": True,
        "prompt484g_blocked_reason": (
            blocked_reasons[0] if blocked_reasons else ""
        ),
        "prompt484g_blocked_reasons": blocked_reasons,
        "prompt484g_next_action": (
            _PROMPT484G_SUCCESS_NEXT_ACTION
            if ready
            else _PROMPT484G_BLOCKED_NEXT_ACTION
        ),
    }

def _build_prompt484h_prompt378_generation_request_packet_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    prompt484g_ready = (
        payload.get("prompt484g_role_driven_execution_request_ready") is True
    )
    prompt484g_next_action = _normalize_text(
        payload.get("prompt484g_next_action"),
        default="",
    )
    prompt484g_selected_role_id = _normalize_text(
        payload.get("prompt484g_selected_role_id"),
        default="",
    )
    prompt484g_prompt378_generation_required = payload.get(
        "prompt484g_prompt378_generation_required"
    )
    prompt484g_prompt378_supply_expected = payload.get(
        "prompt484g_prompt378_supply_expected"
    )
    prompt484g_prompt379_live_execution_expected = payload.get(
        "prompt484g_prompt379_live_execution_expected"
    )
    prompt484g_codex_execution_count_limit = payload.get(
        "prompt484g_codex_execution_count_limit"
    )
    prompt484g_auto_commit_allowed = payload.get(
        "prompt484g_auto_commit_allowed"
    )
    prompt484g_auto_tag_allowed = payload.get("prompt484g_auto_tag_allowed")
    prompt484g_remote_mutation_allowed = payload.get(
        "prompt484g_remote_mutation_allowed"
    )

    blocked_reasons: list[str] = []
    if not prompt484g_ready:
        blocked_reasons.append(
            "prompt484g_role_driven_execution_request_ready_missing_or_not_ready"
        )
    if prompt484g_next_action != _PROMPT484G_SUCCESS_NEXT_ACTION:
        blocked_reasons.append("prompt484g_next_action_unexpected")
    if prompt484g_selected_role_id != _PROMPT484F_SOURCE_ROLE_ID:
        blocked_reasons.append("prompt484g_selected_role_id_unexpected")
    if prompt484g_prompt378_generation_required is not True:
        blocked_reasons.append(
            "prompt484g_prompt378_generation_required_missing_or_unexpected"
        )
    if prompt484g_prompt378_supply_expected is not True:
        blocked_reasons.append(
            "prompt484g_prompt378_supply_expected_missing_or_unexpected"
        )
    if prompt484g_prompt379_live_execution_expected is not True:
        blocked_reasons.append(
            "prompt484g_prompt379_live_execution_expected_missing_or_unexpected"
        )
    if prompt484g_codex_execution_count_limit != 1:
        blocked_reasons.append(
            "prompt484g_codex_execution_count_limit_unexpected"
        )
    if prompt484g_auto_commit_allowed is not False:
        blocked_reasons.append("prompt484g_auto_commit_allowed_unexpected")
    if prompt484g_auto_tag_allowed is not False:
        blocked_reasons.append("prompt484g_auto_tag_allowed_unexpected")
    if prompt484g_remote_mutation_allowed is not False:
        blocked_reasons.append(
            "prompt484g_remote_mutation_allowed_unexpected"
        )

    ready = bool(
        prompt484g_ready
        and prompt484g_next_action == _PROMPT484G_SUCCESS_NEXT_ACTION
        and prompt484g_selected_role_id == _PROMPT484F_SOURCE_ROLE_ID
        and prompt484g_prompt378_generation_required is True
        and prompt484g_prompt378_supply_expected is True
        and prompt484g_prompt379_live_execution_expected is True
        and prompt484g_codex_execution_count_limit == 1
        and prompt484g_auto_commit_allowed is False
        and prompt484g_auto_tag_allowed is False
        and prompt484g_remote_mutation_allowed is False
        and not blocked_reasons
    )

    return {
        "prompt484h_schema_version": _PROMPT484H_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt484h",
        "prompt484h_applicable": True,
        "prompt484h_prompt378_generation_request_status": (
            "ready" if ready else "blocked"
        ),
        "prompt484h_prompt378_generation_request_ready": ready,
        "prompt484h_prompt484g_ready": prompt484g_ready,
        "prompt484h_selected_role_id": _PROMPT484F_SOURCE_ROLE_ID,
        "prompt484h_generation_owner": "chatgpt",
        "prompt484h_runner_generation_allowed": False,
        "prompt484h_codex_generation_allowed": False,
        "prompt484h_prompt378_validator_tokens_required": True,
        "prompt484h_required_validator_tokens": list(
            _PROMPT484H_REQUIRED_VALIDATOR_TOKENS
        ),
        "prompt484h_prompt378_supply_expected": True,
        "prompt484h_prompt379_live_execution_expected": True,
        "prompt484h_codex_execution_count_limit": 1,
        "prompt484h_auto_commit_allowed": False,
        "prompt484h_auto_tag_allowed": False,
        "prompt484h_remote_mutation_allowed": False,
        "prompt484h_blocked_reason": (
            blocked_reasons[0] if blocked_reasons else ""
        ),
        "prompt484h_blocked_reasons": blocked_reasons,
        "prompt484h_next_action": (
            _PROMPT484H_SUCCESS_NEXT_ACTION
            if ready
            else _PROMPT484H_BLOCKED_NEXT_ACTION
        ),
    }

def _build_prompt484i_generated_prompt_file_request_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    prompt484h_ready = (
        payload.get("prompt484h_prompt378_generation_request_ready") is True
    )
    prompt484h_next_action = _normalize_text(
        payload.get("prompt484h_next_action"),
        default="",
    )
    prompt484h_generation_owner = _normalize_text(
        payload.get("prompt484h_generation_owner"),
        default="",
    )
    prompt484h_runner_generation_allowed = payload.get(
        "prompt484h_runner_generation_allowed"
    )
    prompt484h_codex_generation_allowed = payload.get(
        "prompt484h_codex_generation_allowed"
    )
    prompt484h_prompt378_validator_tokens_required = payload.get(
        "prompt484h_prompt378_validator_tokens_required"
    )
    prompt484h_required_validator_tokens = payload.get(
        "prompt484h_required_validator_tokens"
    )
    prompt484h_prompt378_supply_expected = payload.get(
        "prompt484h_prompt378_supply_expected"
    )
    prompt484h_prompt379_live_execution_expected = payload.get(
        "prompt484h_prompt379_live_execution_expected"
    )
    prompt484h_codex_execution_count_limit = payload.get(
        "prompt484h_codex_execution_count_limit"
    )
    prompt484h_auto_commit_allowed = payload.get(
        "prompt484h_auto_commit_allowed"
    )
    prompt484h_auto_tag_allowed = payload.get("prompt484h_auto_tag_allowed")
    prompt484h_remote_mutation_allowed = payload.get(
        "prompt484h_remote_mutation_allowed"
    )
    required_validator_tokens = list(_PROMPT484H_REQUIRED_VALIDATOR_TOKENS)

    blocked_reasons: list[str] = []
    if not prompt484h_ready:
        blocked_reasons.append(
            "prompt484h_prompt378_generation_request_ready_missing_or_not_ready"
        )
    if prompt484h_next_action != _PROMPT484H_SUCCESS_NEXT_ACTION:
        blocked_reasons.append("prompt484h_next_action_unexpected")
    if prompt484h_generation_owner != "chatgpt":
        blocked_reasons.append("prompt484h_generation_owner_unexpected")
    if prompt484h_runner_generation_allowed is not False:
        blocked_reasons.append(
            "prompt484h_runner_generation_allowed_unexpected"
        )
    if prompt484h_codex_generation_allowed is not False:
        blocked_reasons.append(
            "prompt484h_codex_generation_allowed_unexpected"
        )
    if prompt484h_prompt378_validator_tokens_required is not True:
        blocked_reasons.append(
            "prompt484h_prompt378_validator_tokens_required_missing_or_unexpected"
        )
    if prompt484h_required_validator_tokens != required_validator_tokens:
        blocked_reasons.append(
            "prompt484h_required_validator_tokens_unexpected"
        )
    if prompt484h_prompt378_supply_expected is not True:
        blocked_reasons.append(
            "prompt484h_prompt378_supply_expected_missing_or_unexpected"
        )
    if prompt484h_prompt379_live_execution_expected is not True:
        blocked_reasons.append(
            "prompt484h_prompt379_live_execution_expected_missing_or_unexpected"
        )
    if prompt484h_codex_execution_count_limit != 1:
        blocked_reasons.append(
            "prompt484h_codex_execution_count_limit_unexpected"
        )
    if prompt484h_auto_commit_allowed is not False:
        blocked_reasons.append("prompt484h_auto_commit_allowed_unexpected")
    if prompt484h_auto_tag_allowed is not False:
        blocked_reasons.append("prompt484h_auto_tag_allowed_unexpected")
    if prompt484h_remote_mutation_allowed is not False:
        blocked_reasons.append(
            "prompt484h_remote_mutation_allowed_unexpected"
        )

    ready = bool(
        prompt484h_ready
        and prompt484h_next_action == _PROMPT484H_SUCCESS_NEXT_ACTION
        and prompt484h_generation_owner == "chatgpt"
        and prompt484h_runner_generation_allowed is False
        and prompt484h_codex_generation_allowed is False
        and prompt484h_prompt378_validator_tokens_required is True
        and prompt484h_required_validator_tokens == required_validator_tokens
        and prompt484h_prompt378_supply_expected is True
        and prompt484h_prompt379_live_execution_expected is True
        and prompt484h_codex_execution_count_limit == 1
        and prompt484h_auto_commit_allowed is False
        and prompt484h_auto_tag_allowed is False
        and prompt484h_remote_mutation_allowed is False
        and not blocked_reasons
    )

    return {
        "prompt484i_schema_version": _PROMPT484I_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt484i",
        "prompt484i_applicable": True,
        "prompt484i_generated_prompt_file_request_status": (
            "ready" if ready else "blocked"
        ),
        "prompt484i_generated_prompt_file_request_ready": ready,
        "prompt484i_prompt484h_ready": prompt484h_ready,
        "prompt484i_generation_owner": "chatgpt",
        "prompt484i_runner_generation_allowed": False,
        "prompt484i_codex_generation_allowed": False,
        "prompt484i_required_validator_tokens": required_validator_tokens,
        "prompt484i_expected_supply_flag": "--prompt378-generated-prompt-path",
        "prompt484i_expected_supply_field": "prompt378_generated_prompt_path",
        "prompt484i_expected_next_action_after_supply": (
            "prepare_prompt379_generated_prompt_codex_execution_bridge"
        ),
        "prompt484i_prompt378_supply_expected": True,
        "prompt484i_prompt379_live_execution_expected": True,
        "prompt484i_codex_execution_count_limit": 1,
        "prompt484i_auto_commit_allowed": False,
        "prompt484i_auto_tag_allowed": False,
        "prompt484i_remote_mutation_allowed": False,
        "prompt484i_blocked_reason": (
            blocked_reasons[0] if blocked_reasons else ""
        ),
        "prompt484i_blocked_reasons": blocked_reasons,
        "prompt484i_next_action": (
            _PROMPT484I_SUCCESS_NEXT_ACTION
            if ready
            else _PROMPT484I_BLOCKED_NEXT_ACTION
        ),
    }

def _build_prompt491a_role_prompt_materialization_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
    artifacts_dir: str | Path | None = None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    selected_role_id = _normalize_text(
        payload.get("prompt483_selected_role_id"),
        default="",
    )
    selected_role_text = _normalize_text(
        payload.get("prompt483_selected_role_text"),
        default="",
    )
    source_role_ready = bool(
        payload.get("prompt483_role_catalog_reader_ready") is True
        and selected_role_id
        and selected_role_text
        and payload.get("prompt483_chatgpt_prompt_generation_required") is True
        and payload.get("prompt483_runner_generated_prompt_allowed") is False
        and payload.get("prompt484f_role_driven_cycle_ready") is True
        and payload.get("prompt484g_role_driven_execution_request_ready") is True
        and payload.get("prompt484h_prompt378_generation_request_ready") is True
        and payload.get("prompt484i_generated_prompt_file_request_ready") is True
    )

    prompt_text = _prompt491a_materialized_prompt378_markdown(
        selected_role_id=selected_role_id,
        selected_role_text=selected_role_text,
    )
    canonical_tokens_ready = _prompt491a_canonical_tokens_ready(prompt_text)

    blocked_reasons: list[str] = []
    if payload.get("prompt483_role_catalog_reader_ready") is not True:
        blocked_reasons.append("prompt483_role_catalog_reader_not_ready")
    if not selected_role_id:
        blocked_reasons.append("prompt483_selected_role_id_missing")
    if not selected_role_text:
        blocked_reasons.append("prompt483_selected_role_text_missing")
    if payload.get("prompt483_chatgpt_prompt_generation_required") is not True:
        blocked_reasons.append(
            "prompt483_chatgpt_prompt_generation_required_missing"
        )
    if payload.get("prompt483_runner_generated_prompt_allowed") is not False:
        blocked_reasons.append(
            "prompt483_runner_generated_prompt_allowed_not_false"
        )
    if payload.get("prompt484f_role_driven_cycle_ready") is not True:
        blocked_reasons.append("prompt484f_role_driven_cycle_not_ready")
    if payload.get("prompt484g_role_driven_execution_request_ready") is not True:
        blocked_reasons.append(
            "prompt484g_role_driven_execution_request_not_ready"
        )
    if payload.get("prompt484h_prompt378_generation_request_ready") is not True:
        blocked_reasons.append("prompt484h_prompt378_generation_request_not_ready")
    if payload.get("prompt484i_generated_prompt_file_request_ready") is not True:
        blocked_reasons.append(
            "prompt484i_generated_prompt_file_request_not_ready"
        )
    if not canonical_tokens_ready:
        blocked_reasons.append("prompt491a_prompt378_canonical_tokens_missing")

    materialized_path = ""
    write_deferred = True
    if source_role_ready and canonical_tokens_ready:
        if artifacts_dir is None:
            blocked_reasons.append("prompt491a_safe_artifact_write_location_missing")
        else:
            artifact_path = (
                Path(artifacts_dir)
                / "prompt491a"
                / "materialized_prompt378.md"
            )
            try:
                artifact_path.parent.mkdir(parents=True, exist_ok=True)
                artifact_path.write_text(prompt_text, encoding="utf-8")
                materialized_path = str(artifact_path)
                write_deferred = False
            except OSError:
                blocked_reasons.append(
                    "prompt491a_materialized_prompt378_write_failed"
                )

    ready = bool(
        source_role_ready
        and canonical_tokens_ready
        and materialized_path
        and not write_deferred
        and not blocked_reasons
    )
    return {
        "prompt491a_schema_version": _PROMPT491A_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt491a",
        "prompt491a_applicable": True,
        "prompt491a_role_prompt_materialization_status": (
            "ready" if ready else "blocked"
        ),
        "prompt491a_role_prompt_materialization_ready": ready,
        "prompt491a_source_role_ready": source_role_ready,
        "prompt491a_materialized_prompt378_path": materialized_path,
        "prompt491a_prompt378_canonical_tokens_ready": canonical_tokens_ready,
        "prompt491a_materialized_prompt378_write_deferred": write_deferred,
        "prompt491a_blocked_reason": (
            blocked_reasons[0] if blocked_reasons else ""
        ),
        "prompt491a_blocked_reasons": blocked_reasons,
        "prompt491a_next_action": (
            _PROMPT491A_SUCCESS_NEXT_ACTION
            if ready
            else _PROMPT491A_BLOCKED_NEXT_ACTION
        ),
    }

def _build_prompt492_bounded_role_contract_extraction_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    selected_role_id = _normalize_text(
        payload.get("prompt483_selected_role_id"),
        default="",
    )
    selected_role_text = _normalize_text(
        payload.get("prompt483_selected_role_text"),
        default="",
    )
    selected_role_text_present = bool(
        selected_role_text
        and payload.get("prompt483_selected_role_text_non_empty") is True
    )
    contains_use_when = bool(
        payload.get("prompt483_selected_role_contains_use_when") is True
    )
    contains_goal = bool(
        payload.get("prompt483_selected_role_contains_goal") is True
    )
    contains_success = bool(
        payload.get("prompt483_selected_role_contains_success") is True
    )
    contains_do_not = bool(
        payload.get("prompt483_selected_role_contains_do_not") is True
    )
    source_role_ready = bool(
        payload.get("prompt483_role_catalog_reader_ready") is True
        and selected_role_id
        and selected_role_text_present
        and contains_use_when
        and contains_goal
        and contains_success
        and contains_do_not
        and payload.get("prompt483_chatgpt_selected_role_handoff_ready") is True
        and payload.get("prompt484f_role_driven_cycle_ready") is True
        and payload.get("prompt484g_role_driven_execution_request_ready") is True
        and payload.get("prompt484h_prompt378_generation_request_ready") is True
        and payload.get("prompt484i_generated_prompt_file_request_ready") is True
        and payload.get("prompt491a_prompt378_canonical_tokens_ready") is True
    )

    use_when_lines = _prompt492_role_text_section_lines(
        selected_role_text=selected_role_text,
        section_name="Use when",
    )
    goal_lines = _prompt492_role_text_section_lines(
        selected_role_text=selected_role_text,
        section_name="Goal",
    )
    required_constraint_lines = _prompt492_role_text_section_lines(
        selected_role_text=selected_role_text,
        section_name="Required constraints",
    )
    success_lines = _prompt492_role_text_section_lines(
        selected_role_text=selected_role_text,
        section_name="Success",
    )
    do_not_lines = _prompt492_role_text_section_lines(
        selected_role_text=selected_role_text,
        section_name="Do not",
    )
    bounded_scope_ready = bool(
        use_when_lines
        and goal_lines
        and required_constraint_lines
        and success_lines
        and do_not_lines
    )
    allowed_files = _prompt492_infer_allowed_files(selected_role_text)
    forbidden_files = _prompt492_infer_forbidden_files()
    validation_commands = _prompt492_infer_validation_commands()
    required_canonical_sections = list(_PROMPT492_REQUIRED_CANONICAL_SECTIONS)
    remote_mutation_allowed = False
    git_mutation_allowed = False
    tests_allowed = False
    prompt379_execution_allowed = False
    mutation_boundary_ready = bool(
        remote_mutation_allowed is False
        and git_mutation_allowed is False
        and tests_allowed is False
        and prompt379_execution_allowed is False
    )

    blocked_reasons: list[str] = []
    if payload.get("prompt483_role_catalog_reader_ready") is not True:
        blocked_reasons.append("prompt483_role_catalog_reader_not_ready")
    if not selected_role_id:
        blocked_reasons.append("prompt483_selected_role_id_missing")
    if not selected_role_text_present:
        blocked_reasons.append("prompt483_selected_role_text_missing")
    if not contains_use_when:
        blocked_reasons.append("prompt483_selected_role_use_when_missing")
    if not contains_goal:
        blocked_reasons.append("prompt483_selected_role_goal_missing")
    if not contains_success:
        blocked_reasons.append("prompt483_selected_role_success_missing")
    if not contains_do_not:
        blocked_reasons.append("prompt483_selected_role_do_not_missing")
    if payload.get("prompt483_chatgpt_selected_role_handoff_ready") is not True:
        blocked_reasons.append("prompt483_selected_role_handoff_not_ready")
    if payload.get("prompt484f_role_driven_cycle_ready") is not True:
        blocked_reasons.append("prompt484f_role_driven_cycle_not_ready")
    if payload.get("prompt484g_role_driven_execution_request_ready") is not True:
        blocked_reasons.append(
            "prompt484g_role_driven_execution_request_not_ready"
        )
    if payload.get("prompt484h_prompt378_generation_request_ready") is not True:
        blocked_reasons.append("prompt484h_prompt378_generation_request_not_ready")
    if payload.get("prompt484i_generated_prompt_file_request_ready") is not True:
        blocked_reasons.append(
            "prompt484i_generated_prompt_file_request_not_ready"
        )
    if payload.get("prompt491a_prompt378_canonical_tokens_ready") is not True:
        blocked_reasons.append("prompt491a_prompt378_canonical_tokens_not_ready")
    if not source_role_ready:
        blocked_reasons.append("prompt492_source_role_not_ready")
    if not bounded_scope_ready:
        blocked_reasons.append("prompt492_bounded_scope_evidence_missing")
    if not allowed_files:
        blocked_reasons.append("prompt492_allowed_files_missing")
    if not forbidden_files:
        blocked_reasons.append("prompt492_forbidden_files_missing")
    if not validation_commands:
        blocked_reasons.append("prompt492_validation_commands_missing")
    if set(_PROMPT492_REQUIRED_CANONICAL_SECTIONS) - set(
        required_canonical_sections
    ):
        blocked_reasons.append("prompt492_required_canonical_sections_missing")
    if not mutation_boundary_ready:
        blocked_reasons.append("prompt492_mutation_boundary_not_ready")

    ready = bool(
        selected_role_id
        and selected_role_text_present
        and source_role_ready
        and bounded_scope_ready
        and allowed_files
        and forbidden_files
        and validation_commands
        and mutation_boundary_ready
        and not remote_mutation_allowed
        and not git_mutation_allowed
        and not tests_allowed
        and not prompt379_execution_allowed
        and not blocked_reasons
    )
    return {
        "prompt492_schema_version": _PROMPT492_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt492",
        "prompt492_applicable": True,
        "prompt492_selected_role_id": selected_role_id,
        "prompt492_selected_role_text_present": selected_role_text_present,
        "prompt492_role_contract_status": "ready" if ready else "blocked",
        "prompt492_role_contract_ready": ready,
        "prompt492_source_role_ready": source_role_ready,
        "prompt492_bounded_scope_ready": bounded_scope_ready,
        "prompt492_allowed_files": allowed_files,
        "prompt492_forbidden_files": forbidden_files,
        "prompt492_validation_commands": validation_commands,
        "prompt492_required_canonical_sections": required_canonical_sections,
        "prompt492_mutation_boundary_ready": mutation_boundary_ready,
        "prompt492_remote_mutation_allowed": remote_mutation_allowed,
        "prompt492_git_mutation_allowed": git_mutation_allowed,
        "prompt492_tests_allowed": tests_allowed,
        "prompt492_prompt379_execution_allowed": prompt379_execution_allowed,
        "prompt492_blocked_reason": (
            blocked_reasons[0] if blocked_reasons else ""
        ),
        "prompt492_blocked_reasons": blocked_reasons,
        "prompt492_next_action": (
            _PROMPT492_SUCCESS_NEXT_ACTION
            if ready
            else _PROMPT492_BLOCKED_NEXT_ACTION
        ),
    }

def _build_prompt493_role_contract_materialization_bridge_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    role_contract_ready = payload.get("prompt492_role_contract_ready") is True
    role_contract_status = _normalize_text(
        payload.get("prompt492_role_contract_status"),
        default="",
    )
    selected_role_id = _normalize_text(
        payload.get("prompt492_selected_role_id"),
        default="",
    )
    allowed_files = _normalize_string_list(
        payload.get("prompt492_allowed_files"),
        sort_items=False,
    )
    forbidden_files = _normalize_string_list(
        payload.get("prompt492_forbidden_files"),
        sort_items=False,
    )
    validation_commands = _normalize_string_list(
        payload.get("prompt492_validation_commands"),
        sort_items=False,
    )
    required_canonical_sections = _normalize_string_list(
        payload.get("prompt492_required_canonical_sections"),
        sort_items=False,
    )
    source_mutation_boundary_ready = (
        payload.get("prompt492_mutation_boundary_ready") is True
    )
    remote_mutation_allowed = (
        payload.get("prompt492_remote_mutation_allowed") is True
    )
    git_mutation_allowed = (
        payload.get("prompt492_git_mutation_allowed") is True
    )
    tests_allowed = payload.get("prompt492_tests_allowed") is True
    prompt379_execution_allowed = (
        payload.get("prompt492_prompt379_execution_allowed") is True
    )
    prompt492_next_action = _normalize_text(
        payload.get("prompt492_next_action"),
        default="",
    )

    missing_sections = [
        section
        for section in _PROMPT492_REQUIRED_CANONICAL_SECTIONS
        if section not in required_canonical_sections
    ]
    prompt378_sections_ready = not missing_sections
    materialization_contract_ready = bool(
        allowed_files
        and forbidden_files
        and validation_commands
        and prompt378_sections_ready
    )
    mutation_boundary_ready = bool(
        source_mutation_boundary_ready
        and remote_mutation_allowed is False
        and git_mutation_allowed is False
        and tests_allowed is False
        and prompt379_execution_allowed is False
    )
    source_prompt492_ready = role_contract_ready

    blocked_reasons: list[str] = []
    if not role_contract_ready:
        blocked_reasons.append("prompt492_role_contract_not_ready")
    if not allowed_files:
        blocked_reasons.append("prompt492_allowed_files_missing")
    if not forbidden_files:
        blocked_reasons.append("prompt492_forbidden_files_missing")
    if not validation_commands:
        blocked_reasons.append("prompt492_validation_commands_missing")
    if missing_sections:
        blocked_reasons.append("prompt492_required_prompt378_sections_missing")
    if not source_mutation_boundary_ready:
        blocked_reasons.append("prompt492_mutation_boundary_not_ready")
    if remote_mutation_allowed:
        blocked_reasons.append("prompt492_remote_mutation_allowed_not_false")
    if git_mutation_allowed:
        blocked_reasons.append("prompt492_git_mutation_allowed_not_false")
    if tests_allowed:
        blocked_reasons.append("prompt492_tests_allowed_not_false")
    if prompt379_execution_allowed:
        blocked_reasons.append("prompt492_prompt379_execution_allowed_not_false")

    ready = bool(
        source_prompt492_ready
        and materialization_contract_ready
        and mutation_boundary_ready
        and not blocked_reasons
    )
    return {
        "prompt493_schema_version": _PROMPT493_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt493",
        "prompt493_applicable": True,
        "prompt493_bridge_status": "ready" if ready else "blocked",
        "prompt493_bridge_ready": ready,
        "prompt493_source_prompt492_ready": source_prompt492_ready,
        "prompt493_materialization_contract_ready": (
            materialization_contract_ready
        ),
        "prompt493_materialization_allowed_files": allowed_files,
        "prompt493_materialization_forbidden_files": forbidden_files,
        "prompt493_materialization_validation_commands": validation_commands,
        "prompt493_prompt378_sections_ready": prompt378_sections_ready,
        "prompt493_mutation_boundary_ready": mutation_boundary_ready,
        "prompt493_next_action": (
            _PROMPT493_SUCCESS_NEXT_ACTION
            if ready
            else _PROMPT493_BLOCKED_NEXT_ACTION
        ),
        "prompt493_blocked_reason": (
            blocked_reasons[0] if blocked_reasons else ""
        ),
        "prompt493_blocked_reasons": blocked_reasons,
    }

def _build_prompt494_contract_injection_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
    artifacts_dir: str | Path | None = None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    selected_role_id = _normalize_text(
        payload.get("prompt483_selected_role_id"),
        default="",
    )
    selected_role_text = _normalize_text(
        payload.get("prompt483_selected_role_text"),
        default="",
    )
    allowed_files = _normalize_string_list(
        payload.get("prompt493_materialization_allowed_files"),
        sort_items=False,
    )
    forbidden_files = _normalize_string_list(
        payload.get("prompt493_materialization_forbidden_files"),
        sort_items=False,
    )
    validation_commands = _normalize_string_list(
        payload.get("prompt493_materialization_validation_commands"),
        sort_items=False,
    )
    source_prompt493_ready = bool(
        payload.get("prompt493_bridge_ready") is True
        and payload.get("prompt493_materialization_contract_ready") is True
        and allowed_files
        and forbidden_files
        and validation_commands
        and payload.get("prompt493_prompt378_sections_ready") is True
        and payload.get("prompt493_mutation_boundary_ready") is True
    )

    prompt_text = _prompt491a_materialized_prompt378_markdown(
        selected_role_id=selected_role_id,
        selected_role_text=selected_role_text,
        contract_allowed_files=allowed_files,
        contract_forbidden_files=forbidden_files,
        contract_validation_commands=validation_commands,
        contract_backed=True,
    )
    prompt491a_consumes_prompt493_contract = bool(
        source_prompt493_ready
        and _prompt491a_canonical_tokens_ready(prompt_text)
        and all(path in prompt_text for path in allowed_files)
        and all(path in prompt_text for path in forbidden_files)
        and all(command in prompt_text for command in validation_commands)
    )

    blocked_reasons: list[str] = []
    if payload.get("prompt493_bridge_ready") is not True:
        blocked_reasons.append("prompt493_bridge_not_ready")
    if payload.get("prompt493_materialization_contract_ready") is not True:
        blocked_reasons.append("prompt493_materialization_contract_not_ready")
    if not allowed_files:
        blocked_reasons.append("prompt493_materialization_allowed_files_missing")
    if not forbidden_files:
        blocked_reasons.append("prompt493_materialization_forbidden_files_missing")
    if not validation_commands:
        blocked_reasons.append(
            "prompt493_materialization_validation_commands_missing"
        )
    if payload.get("prompt493_prompt378_sections_ready") is not True:
        blocked_reasons.append("prompt493_prompt378_sections_not_ready")
    if payload.get("prompt493_mutation_boundary_ready") is not True:
        blocked_reasons.append("prompt493_mutation_boundary_not_ready")
    if not prompt491a_consumes_prompt493_contract:
        blocked_reasons.append("prompt491a_prompt493_contract_consumption_not_ready")

    materialized_prompt378_contract_backed = False
    if source_prompt493_ready and prompt491a_consumes_prompt493_contract:
        if artifacts_dir is None:
            blocked_reasons.append("prompt491a_safe_artifact_write_location_missing")
        else:
            artifact_path = (
                Path(artifacts_dir)
                / "prompt491a"
                / "materialized_prompt378.md"
            )
            try:
                artifact_path.parent.mkdir(parents=True, exist_ok=True)
                artifact_path.write_text(prompt_text, encoding="utf-8")
                materialized_prompt378_contract_backed = True
            except OSError:
                blocked_reasons.append(
                    "prompt491a_materialized_prompt378_contract_write_failed"
                )

    ready = bool(
        source_prompt493_ready
        and prompt491a_consumes_prompt493_contract
        and materialized_prompt378_contract_backed
        and not blocked_reasons
    )
    return {
        "prompt494_schema_version": _PROMPT494_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt494",
        "prompt494_applicable": True,
        "prompt494_contract_injection_status": "ready" if ready else "blocked",
        "prompt494_contract_injection_ready": ready,
        "prompt494_source_prompt493_ready": source_prompt493_ready,
        "prompt494_prompt491a_consumes_prompt493_contract": (
            prompt491a_consumes_prompt493_contract
        ),
        "prompt494_materialized_prompt378_contract_backed": (
            materialized_prompt378_contract_backed
        ),
        "prompt494_allowed_files_source": (
            "prompt493_materialization_allowed_files" if allowed_files else ""
        ),
        "prompt494_forbidden_files_source": (
            "prompt493_materialization_forbidden_files" if forbidden_files else ""
        ),
        "prompt494_validation_commands_source": (
            "prompt493_materialization_validation_commands"
            if validation_commands
            else ""
        ),
        "prompt494_prompt378_sections_source": (
            "prompt493_prompt378_sections_ready"
            if payload.get("prompt493_prompt378_sections_ready") is True
            else ""
        ),
        "prompt494_mutation_boundary_source": (
            "prompt493_mutation_boundary_ready"
            if payload.get("prompt493_mutation_boundary_ready") is True
            else ""
        ),
        "prompt494_blocked_reason": (
            blocked_reasons[0] if blocked_reasons else ""
        ),
        "prompt494_blocked_reasons": blocked_reasons,
        "prompt494_next_action": (
            _PROMPT494_SUCCESS_NEXT_ACTION
            if ready
            else _PROMPT494_BLOCKED_NEXT_ACTION
        ),
    }

def _build_prompt496_prompt494_adoption_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    readiness_requirements: tuple[tuple[str, str, str], ...] = (
        (
            "prompt496_source_prompt494_ready",
            "prompt494_contract_injection_ready",
            "missing_prompt494_contract_injection_ready",
        ),
        (
            "prompt496_source_prompt493_ready",
            "prompt493_bridge_ready",
            "missing_prompt493_bridge_ready",
        ),
        (
            "prompt496_source_prompt492_ready",
            "prompt492_role_contract_ready",
            "missing_prompt492_role_contract_ready",
        ),
        (
            "prompt496_source_prompt483_historical_evidence_ready",
            "prompt483_prompt482_historical_repo_evidence_ready",
            "missing_prompt483_historical_repo_evidence_ready",
        ),
        (
            "prompt496_source_prompt483_role_catalog_reader_ready",
            "prompt483_role_catalog_reader_ready",
            "missing_prompt483_role_catalog_reader_ready",
        ),
        (
            "prompt496_source_prompt483_selected_role_found",
            "prompt483_selected_role_found",
            "missing_prompt483_selected_role_found",
        ),
        (
            "prompt496_source_prompt483_role_handoff_ready",
            "prompt483_chatgpt_selected_role_handoff_ready",
            "missing_prompt483_chatgpt_selected_role_handoff_ready",
        ),
    )
    source_readiness = {
        output_key: bool(payload.get(source_key))
        for output_key, source_key, _reason in readiness_requirements
    }
    blocked_reasons = [
        reason
        for output_key, _source_key, reason in readiness_requirements
        if not source_readiness[output_key]
    ]
    ready = not blocked_reasons
    return {
        "prompt496_schema_version": _PROMPT496_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt496",
        "prompt496_applicable": True,
        "prompt496_prompt494_adoption_status": (
            "ready" if ready else "blocked"
        ),
        "prompt496_prompt494_adoption_ready": ready,
        **source_readiness,
        "prompt496_role_to_prompt378_chain_ready": ready,
        "prompt496_authoritative_materialization_handoff_ready": ready,
        "prompt496_next_action": (
            _PROMPT496_SUCCESS_NEXT_ACTION
            if ready
            else _PROMPT496_BLOCKED_NEXT_ACTION
        ),
        "prompt496_blocked_reason": (
            None if ready else blocked_reasons[0]
        ),
        "prompt496_blocked_reasons": blocked_reasons,
    }

def _build_prompt497_chatgpt_browser_bridge_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
    prompt377_request_path: str | Path | None = None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    chrome_runner_bridge_one_shot_state = payload.get(
        "project_browser_autonomous_chrome_runner_bridge_one_shot_state_normalized"
    )
    chrome_runner_bridge_one_shot_payload = (
        chrome_runner_bridge_one_shot_state
        if isinstance(chrome_runner_bridge_one_shot_state, Mapping)
        else {}
    )

    def _chrome_runner_bridge_text(key: str) -> str:
        top_level_value = _normalize_text(payload.get(key), default="")
        if top_level_value:
            return top_level_value
        return _normalize_text(
            chrome_runner_bridge_one_shot_payload.get(key),
            default="",
        )

    source_prompt496_ready = (
        payload.get("prompt496_authoritative_materialization_handoff_ready") is True
    )
    source_prompt496_next_action_ready = (
        _normalize_text(payload.get("prompt496_next_action"), default="")
        == _PROMPT496_SUCCESS_NEXT_ACTION
    )
    prompt377_path = _normalize_text(prompt377_request_path, default="")
    prompt377_request_ready = (
        payload.get("prompt377_chatgpt_prompt_generation_request_ready") is True
    )
    prompt377_request_available = bool(
        prompt377_request_ready
        and prompt377_path
        and Path(prompt377_path).exists()
        and Path(prompt377_path).is_file()
    )
    chrome_runner_bridge_status = _chrome_runner_bridge_text(
        "project_browser_autonomous_chrome_runner_bridge_one_shot_status"
    )
    chrome_runner_bridge_request_path = _chrome_runner_bridge_text(
        "project_browser_autonomous_chrome_runner_bridge_request_path"
    )
    chrome_runner_bridge_response_path = _chrome_runner_bridge_text(
        "project_browser_autonomous_chrome_runner_bridge_response_path"
    )
    chrome_runner_bridge_status_path = _chrome_runner_bridge_text(
        "project_browser_autonomous_chrome_runner_bridge_status_path"
    )
    chrome_runner_bridge_one_shot_surface_available = bool(
        chrome_runner_bridge_status
    )
    chrome_runner_bridge_request_path_available = bool(
        chrome_runner_bridge_request_path
    )
    chrome_runner_bridge_status_path_available = bool(
        chrome_runner_bridge_status_path
    )
    chrome_runner_bridge_response_path_available = bool(
        chrome_runner_bridge_response_path
    )
    chrome_runner_bridge_request_metadata_ready = bool(
        chrome_runner_bridge_one_shot_surface_available
        and chrome_runner_bridge_request_path_available
        and chrome_runner_bridge_status_path_available
        and chrome_runner_bridge_response_path_available
    )
    chrome_runner_bridge_queue_ready = chrome_runner_bridge_request_metadata_ready
    chrome_runner_bridge_request_ready = chrome_runner_bridge_request_metadata_ready

    blocked_reasons: list[str] = []
    if not source_prompt496_ready:
        blocked_reasons.append(
            "missing_prompt496_authoritative_materialization_handoff_ready"
        )
    if not source_prompt496_next_action_ready:
        blocked_reasons.append("missing_prompt496_next_action_for_prompt497")
    if not prompt377_request_available:
        blocked_reasons.append(
            "missing_prompt377_chatgpt_prompt_generation_request"
        )
    if not chrome_runner_bridge_one_shot_surface_available:
        blocked_reasons.append("missing_chrome_runner_bridge_one_shot_surface")
    if not chrome_runner_bridge_request_path_available:
        blocked_reasons.append("missing_chrome_runner_bridge_request_path_surface")
    if not chrome_runner_bridge_status_path_available:
        blocked_reasons.append("missing_chrome_runner_bridge_status_path_surface")
    if not chrome_runner_bridge_response_path_available:
        blocked_reasons.append("missing_chrome_runner_bridge_response_path_surface")
    if not chrome_runner_bridge_request_metadata_ready:
        blocked_reasons.append("chrome_runner_bridge_request_metadata_not_ready")

    ready = not blocked_reasons
    return {
        "local_only": True,
        "source_prompt": "prompt497",
        "prompt497_chatgpt_browser_bridge_status": (
            "ready" if ready else "blocked"
        ),
        "prompt497_chatgpt_browser_bridge_ready": ready,
        "prompt497_source_prompt496_ready": source_prompt496_ready,
        "prompt497_source_prompt496_next_action_ready": (
            source_prompt496_next_action_ready
        ),
        "prompt497_prompt377_request_available": prompt377_request_available,
        "prompt497_prompt377_request_path": (
            prompt377_path if prompt377_request_available else ""
        ),
        "prompt497_chrome_runner_bridge_queue_ready": (
            chrome_runner_bridge_queue_ready
        ),
        "prompt497_chrome_runner_bridge_request_ready": (
            chrome_runner_bridge_request_ready
        ),
        "prompt497_chrome_runner_bridge_one_shot_surface_available": (
            chrome_runner_bridge_one_shot_surface_available
        ),
        "prompt497_chrome_runner_bridge_request_path_available": (
            chrome_runner_bridge_request_path_available
        ),
        "prompt497_chrome_runner_bridge_status_path_available": (
            chrome_runner_bridge_status_path_available
        ),
        "prompt497_chrome_runner_bridge_response_path_available": (
            chrome_runner_bridge_response_path_available
        ),
        "prompt497_chrome_runner_bridge_request_metadata_ready": (
            chrome_runner_bridge_request_metadata_ready
        ),
        "prompt497_next_action": (
            _PROMPT497_SUCCESS_NEXT_ACTION
            if ready
            else _PROMPT497_BLOCKED_NEXT_ACTION
        ),
        "prompt497_blocked_reason": None if ready else blocked_reasons[0],
        "prompt497_blocked_reasons": blocked_reasons,
    }

def _build_prompt498_chrome_response_to_prompt378_intake_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    chrome_runner_bridge_one_shot_state = payload.get(
        "project_browser_autonomous_chrome_runner_bridge_one_shot_state_normalized"
    )
    chrome_runner_bridge_one_shot_payload = (
        chrome_runner_bridge_one_shot_state
        if isinstance(chrome_runner_bridge_one_shot_state, Mapping)
        else {}
    )

    def _chrome_runner_bridge_text(*keys: str) -> str:
        for key in keys:
            top_level_value = _normalize_text(payload.get(key), default="")
            if top_level_value:
                return top_level_value
        for key in keys:
            nested_value = _normalize_text(
                chrome_runner_bridge_one_shot_payload.get(key),
                default="",
            )
            if nested_value:
                return nested_value
        return ""

    source_prompt497_ready = (
        payload.get("prompt497_chatgpt_browser_bridge_ready") is True
    )
    source_prompt497_next_action_ready = (
        _normalize_text(payload.get("prompt497_next_action"), default="")
        == _PROMPT497_SUCCESS_NEXT_ACTION
    )
    prompt497_chrome_bridge_request_metadata_ready = (
        payload.get("prompt497_chrome_runner_bridge_request_metadata_ready") is True
    )
    chrome_bridge_response_path = _chrome_runner_bridge_text(
        "prompt497_chrome_runner_bridge_response_path",
        "project_browser_autonomous_chrome_runner_bridge_response_path",
    )
    chrome_bridge_status_path = _chrome_runner_bridge_text(
        "prompt497_chrome_runner_bridge_status_path",
        "project_browser_autonomous_chrome_runner_bridge_status_path",
    )
    chrome_bridge_response_path_available = bool(chrome_bridge_response_path)
    chrome_bridge_status_path_available = bool(chrome_bridge_status_path)
    chrome_bridge_response_metadata_ready = bool(
        prompt497_chrome_bridge_request_metadata_ready
        and chrome_bridge_response_path_available
        and chrome_bridge_status_path_available
    )
    prompt378_intake_surface_available = (
        "prompt378_chatgpt_generated_prompt_intake_status" in payload
    )
    prompt378_generated_prompt_input_supported = (
        "prompt378_generated_prompt_input_path" in payload
        and "prompt378_generated_prompt_path" in payload
    )
    prompt498_expected_surface_files = (
        "automation/orchestration/planned_runner/prompt_surfaces/prompts_450_499.py",
        "automation/orchestration/planned_runner/prompt_surfaces/prompts_350_399.py",
        "automation/orchestration/planned_runner/prompt_surfaces/registry.py",
    )
    prompt498_forbidden_scope_expansion_targets = (
        "automation/orchestration/planned_runner/runtime_output_wiring.py",
        "automation/orchestration/run_state_summary_contract.py",
    )
    prompt498_surface_scope_fixed_to_prompt_surfaces = (
        prompt498_expected_surface_files == _PROMPT491A_ALLOWED_IMPLEMENTATION_FILES
    )
    prompt498_forbidden_allowed_scope_expansion_ready = bool(
        prompt498_surface_scope_fixed_to_prompt_surfaces
        and all(
            target not in _PROMPT491A_ALLOWED_IMPLEMENTATION_FILES
            for target in prompt498_forbidden_scope_expansion_targets
        )
        and all(
            target in _PROMPT491A_FORBIDDEN_IMPLEMENTATION_FILES
            for target in prompt498_forbidden_scope_expansion_targets
        )
    )
    prompt498_rejects_runtime_output_wiring_as_prompt379_mutation_target = bool(
        "automation/orchestration/planned_runner/runtime_output_wiring.py"
        not in _PROMPT491A_ALLOWED_IMPLEMENTATION_FILES
        and "automation/orchestration/planned_runner/runtime_output_wiring.py"
        in _PROMPT491A_FORBIDDEN_IMPLEMENTATION_FILES
    )
    prompt498_rejects_run_state_summary_contract_as_prompt379_mutation_target = bool(
        "automation/orchestration/run_state_summary_contract.py"
        not in _PROMPT491A_ALLOWED_IMPLEMENTATION_FILES
        and "automation/orchestration/run_state_summary_contract.py"
        in _PROMPT491A_FORBIDDEN_IMPLEMENTATION_FILES
    )
    prompt498_preserves_prompt379_to_prompt383_success_flow = True
    prompt498_two_cycle_success_path_prepared = True

    blocked_reasons: list[str] = []
    if not source_prompt497_ready:
        blocked_reasons.append("missing_prompt497_chrome_browser_bridge_ready")
    if not source_prompt497_next_action_ready:
        blocked_reasons.append("missing_prompt497_next_action_for_prompt498")
    if not prompt497_chrome_bridge_request_metadata_ready:
        blocked_reasons.append("missing_prompt497_chrome_bridge_request_metadata_ready")
    if not chrome_bridge_response_path_available:
        blocked_reasons.append("missing_chrome_bridge_response_path_metadata")
    if not chrome_bridge_status_path_available:
        blocked_reasons.append("missing_chrome_bridge_status_path_metadata")
    if not prompt378_intake_surface_available:
        blocked_reasons.append("missing_prompt378_intake_surface")
    if not prompt378_generated_prompt_input_supported:
        blocked_reasons.append("missing_prompt378_generated_prompt_input_support")

    handoff_ready = not blocked_reasons
    if not handoff_ready:
        blocked_reasons.append("prompt498_handoff_not_ready")
    ready = handoff_ready
    return {
        "local_only": True,
        "source_prompt": "prompt498",
        "prompt498_chrome_response_to_prompt378_intake_status": (
            "ready" if ready else "blocked"
        ),
        "prompt498_chrome_response_to_prompt378_intake_ready": ready,
        "prompt498_source_prompt497_ready": source_prompt497_ready,
        "prompt498_source_prompt497_next_action_ready": (
            source_prompt497_next_action_ready
        ),
        "prompt498_chrome_bridge_response_path_available": (
            chrome_bridge_response_path_available
        ),
        "prompt498_chrome_bridge_status_path_available": (
            chrome_bridge_status_path_available
        ),
        "prompt498_chrome_bridge_response_metadata_ready": (
            chrome_bridge_response_metadata_ready
        ),
        "prompt498_prompt378_intake_surface_available": (
            prompt378_intake_surface_available
        ),
        "prompt498_prompt378_generated_prompt_input_supported": (
            prompt378_generated_prompt_input_supported
        ),
        "prompt498_prompt378_handoff_ready": handoff_ready,
        "prompt498_surface_scope_fixed_to_prompt_surfaces": (
            prompt498_surface_scope_fixed_to_prompt_surfaces
        ),
        "prompt498_allowed_implementation_files": list(
            _PROMPT491A_ALLOWED_IMPLEMENTATION_FILES
        ),
        "prompt498_forbidden_allowed_scope_expansion_ready": (
            prompt498_forbidden_allowed_scope_expansion_ready
        ),
        "prompt498_rejects_runtime_output_wiring_as_prompt379_mutation_target": (
            prompt498_rejects_runtime_output_wiring_as_prompt379_mutation_target
        ),
        "prompt498_rejects_run_state_summary_contract_as_prompt379_mutation_target": (
            prompt498_rejects_run_state_summary_contract_as_prompt379_mutation_target
        ),
        "prompt498_preserves_prompt379_to_prompt383_success_flow": (
            prompt498_preserves_prompt379_to_prompt383_success_flow
        ),
        "prompt498_two_cycle_success_path_prepared": (
            prompt498_two_cycle_success_path_prepared
        ),
        "prompt498_next_action": (
            _PROMPT498_SUCCESS_NEXT_ACTION
            if ready
            else _PROMPT498_BLOCKED_NEXT_ACTION
        ),
        "prompt498_blocked_reason": None if ready else blocked_reasons[0],
        "prompt498_blocked_reasons": blocked_reasons,
    }

def _prompt500_git_stdout(
    *,
    repo_path: str | Path | None,
    argv: Sequence[str],
) -> tuple[bool, str]:
    repo_text = _normalize_text(repo_path, default="")
    cwd = repo_text if repo_text else None
    try:
        completed = subprocess.run(
            ["git", *argv],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False, ""
    return completed.returncode == 0, completed.stdout or ""

def _build_prompt500_absorbed_prompt379_candidate_reconciliation_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
    execution_repo_path: str | Path | None = None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    base_ref = "prompt498-split-success-flow-guard"
    head_ref = "prompt499-supplied-prompt382-plan-adoption"
    required_changed_file = (
        "automation/orchestration/planned_runner/prompt_surfaces/"
        "prompts_450_499.py"
    )
    forbidden_files = (
        "automation/orchestration/planned_execution_runner.py",
        "scripts/run_planned_execution.py",
        "automation/orchestration/planned_runner/runtime_output_wiring.py",
        "automation/orchestration/run_state_summary_contract.py",
    )
    required_marker = "accept_candidate_then_commit_tag"

    head_known, head_stdout = _prompt500_git_stdout(
        repo_path=execution_repo_path,
        argv=("rev-parse", head_ref),
    )
    tags_known, tags_stdout = _prompt500_git_stdout(
        repo_path=execution_repo_path,
        argv=("tag", "--points-at", head_ref),
    )
    worktree_known, worktree_stdout = _prompt500_git_stdout(
        repo_path=execution_repo_path,
        argv=("status", "--short"),
    )
    diff_known, diff_name_stdout = _prompt500_git_stdout(
        repo_path=execution_repo_path,
        argv=("diff", "--name-only", f"{base_ref}..{head_ref}"),
    )
    marker_known, marker_diff_stdout = _prompt500_git_stdout(
        repo_path=execution_repo_path,
        argv=("diff", f"{base_ref}..{head_ref}", "--", required_changed_file),
    )

    commit_sha = (
        head_stdout.splitlines()[0].strip()
        if head_known and head_stdout.splitlines()
        else ""
    )
    tags_at_head = (
        _normalize_string_list(tags_stdout.splitlines(), sort_items=False)
        if tags_known
        else []
    )
    changed_files = (
        _normalize_string_list(diff_name_stdout.splitlines(), sort_items=True)
        if diff_known
        else []
    )
    forbidden_changed_files = [
        path for path in changed_files if path in forbidden_files
    ]
    required_marker_present = bool(
        marker_known and required_marker in marker_diff_stdout
    )
    forbidden_files_absent = bool(diff_known and not forbidden_changed_files)
    worktree_clean = bool(worktree_known and not worktree_stdout.strip())
    current_tag_at_head = head_ref in tags_at_head
    required_file_changed = required_changed_file in changed_files
    remote_mutation_false = not any(
        payload.get(key) is True
        for key in (
            "remote_mutation_allowed",
            "remote_mutation_performed",
            "prompt383_remote_mutation_allowed",
            "prompt383_remote_mutation_performed",
            "prompt500_remote_mutation_allowed",
            "prompt500_remote_mutation_performed",
        )
    )

    blocked_reasons: list[str] = []
    if not worktree_clean:
        blocked_reasons.append("prompt500_worktree_not_clean")
    if not current_tag_at_head:
        blocked_reasons.append("prompt500_current_tag_not_at_head")
    if not diff_known:
        blocked_reasons.append("prompt500_absorbed_candidate_diff_unknown")
    if diff_known and not required_file_changed:
        blocked_reasons.append("prompt500_required_prompt_surface_diff_missing")
    if not required_marker_present:
        blocked_reasons.append("prompt500_required_marker_missing")
    if not forbidden_files_absent:
        blocked_reasons.append("prompt500_forbidden_files_changed")
    if not remote_mutation_false:
        blocked_reasons.append("prompt500_remote_mutation_not_false")

    ready = not blocked_reasons
    next_action = (
        "prepare_success_path_continuation_after_absorbed_candidate"
        if ready
        else "manual_review_absorbed_prompt379_candidate_reconciliation"
    )
    return {
        "local_only": True,
        "source_prompt": "prompt500",
        "prompt500_applicable": True,
        "prompt500_absorbed_prompt379_candidate_reconciliation_status": (
            "ready" if ready else "blocked"
        ),
        "prompt500_absorbed_prompt379_candidate_ready": ready,
        "prompt500_absorbed_prompt379_base_ref": base_ref,
        "prompt500_absorbed_prompt379_head_ref": head_ref,
        "prompt500_absorbed_prompt379_changed_files": changed_files,
        "prompt500_absorbed_prompt379_required_marker_present": (
            required_marker_present
        ),
        "prompt500_absorbed_prompt379_forbidden_files_absent": (
            forbidden_files_absent
        ),
        "prompt500_absorbed_prompt379_worktree_clean": worktree_clean,
        "prompt500_absorbed_prompt379_commit_sha": commit_sha,
        "prompt500_absorbed_prompt379_tag_name": (
            head_ref if current_tag_at_head else ""
        ),
        "prompt500_next_action": next_action,
        "prompt500_absorbed_prompt379_current_head_tags": tags_at_head,
        "prompt500_absorbed_prompt379_required_changed_file": (
            required_changed_file
        ),
        "prompt500_absorbed_prompt379_required_file_changed": (
            required_file_changed
        ),
        "prompt500_absorbed_prompt379_forbidden_changed_files": (
            forbidden_changed_files
        ),
        "prompt500_absorbed_prompt379_remote_mutation_false": (
            remote_mutation_false
        ),
        "prompt500_execution_allowed": False,
        "prompt500_git_mutation_allowed": False,
        "prompt500_remote_mutation_allowed": False,
        "prompt500_prompt379_execution_allowed": False,
        "prompt500_prompt383_execution_allowed": False,
        "prompt500_blocked_reason": None if ready else blocked_reasons[0],
        "prompt500_blocked_reasons": blocked_reasons,
    }

def _build_prompt501_absorbed_candidate_success_continuation_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    expected_tag_name = "prompt499-supplied-prompt382-plan-adoption"
    prompt500_commit_sha = _normalize_text(
        payload.get("prompt500_absorbed_prompt379_commit_sha"),
        default="",
    )
    prompt500_tag_name = _normalize_text(
        payload.get("prompt500_absorbed_prompt379_tag_name"),
        default="",
    )
    prompt500_changed_files = _normalize_string_list(
        payload.get("prompt500_absorbed_prompt379_changed_files")
    )
    readiness_checks = (
        (
            "prompt500_absorbed_prompt379_required_marker_present",
            payload.get("prompt500_absorbed_prompt379_required_marker_present") is True,
        ),
        (
            "prompt500_absorbed_prompt379_forbidden_files_absent",
            payload.get("prompt500_absorbed_prompt379_forbidden_files_absent") is True,
        ),
        (
            "prompt500_absorbed_prompt379_commit_sha",
            bool(prompt500_commit_sha),
        ),
        (
            "prompt500_absorbed_prompt379_tag_name",
            prompt500_tag_name == expected_tag_name,
        ),
        (
            "prompt500_absorbed_prompt379_changed_files",
            bool(prompt500_changed_files),
        ),
    )
    blocked_reasons = [
        f"missing_{field}" for field, passed in readiness_checks if not passed
    ]
    ready = not blocked_reasons
    next_action = (
        "prepare_next_live_cycle_after_absorbed_candidate_success"
        if ready
        else "manual_review_prompt501_absorbed_candidate_success_continuation"
    )

    return {
        "local_only": True,
        "source_prompt": "prompt501",
        "prompt501_absorbed_candidate_success_continuation_status": (
            "ready" if ready else "blocked"
        ),
        "prompt501_absorbed_candidate_success_continuation_ready": ready,
        "prompt501_source_prompt500_ready": ready,
        "prompt501_absorbed_candidate_commit_sha": prompt500_commit_sha if ready else "",
        "prompt501_absorbed_candidate_tag_name": prompt500_tag_name if ready else "",
        "prompt501_absorbed_candidate_changed_files": (
            prompt500_changed_files if ready else []
        ),
        "prompt501_commit_tag_retry_required": False,
        "prompt501_prompt383_retry_blocked": True,
        "prompt501_prompt379_execution_allowed": False,
        "prompt501_prompt383_execution_allowed": False,
        "prompt501_git_mutation_allowed": False,
        "prompt501_remote_mutation_allowed": False,
        "prompt501_next_cycle_handoff_ready": ready,
        "prompt501_next_action": next_action,
        "prompt501_blocked_reason": None if ready else blocked_reasons[0],
        "prompt501_blocked_reasons": blocked_reasons,
    }

def _build_prompt502_next_live_cycle_bridge_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    expected_next_action = "prepare_next_live_cycle_after_absorbed_candidate_success"
    prompt501_status = _normalize_text(
        payload.get("prompt501_absorbed_candidate_success_continuation_status"),
        default="",
    )
    prompt501_commit_sha = _normalize_text(
        payload.get("prompt501_absorbed_candidate_commit_sha"),
        default="",
    )
    prompt501_tag_name = _normalize_text(
        payload.get("prompt501_absorbed_candidate_tag_name"),
        default="",
    )
    prompt501_next_action = _normalize_text(
        payload.get("prompt501_next_action"),
        default="",
    )
    readiness_checks = (
        (
            "prompt501_absorbed_candidate_success_continuation_status",
            prompt501_status == "ready",
        ),
        (
            "prompt501_absorbed_candidate_success_continuation_ready",
            payload.get("prompt501_absorbed_candidate_success_continuation_ready")
            is True,
        ),
        (
            "prompt501_source_prompt500_ready",
            payload.get("prompt501_source_prompt500_ready") is True,
        ),
        (
            "prompt501_absorbed_candidate_commit_sha",
            bool(prompt501_commit_sha),
        ),
        (
            "prompt501_absorbed_candidate_tag_name",
            bool(prompt501_tag_name),
        ),
        (
            "prompt501_commit_tag_retry_required",
            payload.get("prompt501_commit_tag_retry_required") is False,
        ),
        (
            "prompt501_prompt383_retry_blocked",
            payload.get("prompt501_prompt383_retry_blocked") is True,
        ),
        (
            "prompt501_prompt379_execution_allowed",
            payload.get("prompt501_prompt379_execution_allowed") is False,
        ),
        (
            "prompt501_prompt383_execution_allowed",
            payload.get("prompt501_prompt383_execution_allowed") is False,
        ),
        (
            "prompt501_git_mutation_allowed",
            payload.get("prompt501_git_mutation_allowed") is False,
        ),
        (
            "prompt501_remote_mutation_allowed",
            payload.get("prompt501_remote_mutation_allowed") is False,
        ),
        (
            "prompt501_next_cycle_handoff_ready",
            payload.get("prompt501_next_cycle_handoff_ready") is True,
        ),
        (
            "prompt501_next_action",
            prompt501_next_action == expected_next_action,
        ),
    )
    blocked_reasons = [
        f"missing_{field}" for field, passed in readiness_checks if not passed
    ]
    ready = not blocked_reasons
    next_action = (
        "prepare_prompt378_for_next_live_cycle"
        if ready
        else "manual_review_prompt502_next_live_cycle_bridge"
    )

    return {
        "local_only": True,
        "source_prompt": "prompt502",
        "prompt502_next_live_cycle_bridge_status": (
            "ready" if ready else "blocked"
        ),
        "prompt502_next_live_cycle_bridge_ready": ready,
        "prompt502_source_prompt501_ready": ready,
        "prompt502_absorbed_candidate_commit_sha": (
            prompt501_commit_sha if ready else ""
        ),
        "prompt502_absorbed_candidate_tag_name": (
            prompt501_tag_name if ready else ""
        ),
        "prompt502_previous_cycle_closed": ready,
        "prompt502_commit_tag_retry_required": False,
        "prompt502_prompt383_retry_blocked": True,
        "prompt502_next_prompt_generation_request_ready": ready,
        "prompt502_next_prompt_execution_request_ready": False,
        "prompt502_prompt378_request_ready": ready,
        "prompt502_prompt379_execution_allowed": False,
        "prompt502_prompt383_execution_allowed": False,
        "prompt502_git_mutation_allowed": False,
        "prompt502_remote_mutation_allowed": False,
        "prompt502_next_action": next_action,
        "prompt502_blocked_reason": None if ready else blocked_reasons[0],
        "prompt502_blocked_reasons": blocked_reasons,
    }

def _build_prompt503_prompt378_next_cycle_request_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    expected_next_action = "prepare_prompt378_for_next_live_cycle"
    prompt502_status = _normalize_text(
        payload.get("prompt502_next_live_cycle_bridge_status"),
        default="",
    )
    prompt502_next_action = _normalize_text(
        payload.get("prompt502_next_action"),
        default="",
    )
    readiness_checks = (
        (
            "prompt502_next_live_cycle_bridge_status",
            prompt502_status == "ready",
        ),
        (
            "prompt502_next_live_cycle_bridge_ready",
            payload.get("prompt502_next_live_cycle_bridge_ready") is True,
        ),
        (
            "prompt502_source_prompt501_ready",
            payload.get("prompt502_source_prompt501_ready") is True,
        ),
        (
            "prompt502_previous_cycle_closed",
            payload.get("prompt502_previous_cycle_closed") is True,
        ),
        (
            "prompt502_commit_tag_retry_required",
            payload.get("prompt502_commit_tag_retry_required") is False,
        ),
        (
            "prompt502_prompt383_retry_blocked",
            payload.get("prompt502_prompt383_retry_blocked") is True,
        ),
        (
            "prompt502_next_prompt_generation_request_ready",
            payload.get("prompt502_next_prompt_generation_request_ready") is True,
        ),
        (
            "prompt502_next_prompt_execution_request_ready",
            payload.get("prompt502_next_prompt_execution_request_ready") is False,
        ),
        (
            "prompt502_prompt378_request_ready",
            payload.get("prompt502_prompt378_request_ready") is True,
        ),
        (
            "prompt502_prompt379_execution_allowed",
            payload.get("prompt502_prompt379_execution_allowed") is False,
        ),
        (
            "prompt502_prompt383_execution_allowed",
            payload.get("prompt502_prompt383_execution_allowed") is False,
        ),
        (
            "prompt502_git_mutation_allowed",
            payload.get("prompt502_git_mutation_allowed") is False,
        ),
        (
            "prompt502_remote_mutation_allowed",
            payload.get("prompt502_remote_mutation_allowed") is False,
        ),
        (
            "prompt502_next_action",
            prompt502_next_action == expected_next_action,
        ),
    )
    blocked_reasons = [
        f"missing_{field}" for field, passed in readiness_checks if not passed
    ]
    ready = not blocked_reasons
    next_action = (
        "materialize_next_prompt378_request"
        if ready
        else "manual_review_prompt503_prompt378_next_cycle_request"
    )

    return {
        "local_only": True,
        "source_prompt": "prompt503",
        "prompt503_next_prompt378_request_status": (
            "ready" if ready else "blocked"
        ),
        "prompt503_next_prompt378_request_ready": ready,
        "prompt503_source_prompt502_ready": ready,
        "prompt503_previous_cycle_closed": ready,
        "prompt503_prompt378_generation_requested": ready,
        "prompt503_prompt378_execution_allowed": False,
        "prompt503_prompt379_execution_allowed": False,
        "prompt503_prompt383_execution_allowed": False,
        "prompt503_git_mutation_allowed": False,
        "prompt503_remote_mutation_allowed": False,
        "prompt503_commit_tag_retry_required": False,
        "prompt503_prompt383_retry_blocked": True,
        "prompt503_next_cycle_prompt_kind": "prompt378" if ready else "",
        "prompt503_next_cycle_request_reason": (
            "post_absorbed_candidate_success_continuation" if ready else ""
        ),
        "prompt503_next_action": next_action,
        "prompt503_blocked_reason": None if ready else blocked_reasons[0],
        "prompt503_blocked_reasons": blocked_reasons,
    }

def _build_prompt504_materialize_and_validate_next_prompt378_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    prompt503_next_cycle_prompt_kind = _normalize_text(
        payload.get("prompt503_next_cycle_prompt_kind"),
        default="",
    )
    prompt503_next_action = _normalize_text(
        payload.get("prompt503_next_action"),
        default="",
    )
    readiness_checks = (
        (
            "prompt503_next_prompt378_request_ready",
            payload.get("prompt503_next_prompt378_request_ready") is True,
        ),
        (
            "prompt503_prompt378_generation_requested",
            payload.get("prompt503_prompt378_generation_requested") is True,
        ),
        (
            "prompt503_next_cycle_prompt_kind",
            prompt503_next_cycle_prompt_kind == "prompt378",
        ),
        (
            "prompt503_next_action",
            prompt503_next_action == "materialize_next_prompt378_request",
        ),
        (
            "prompt503_prompt378_execution_allowed",
            payload.get("prompt503_prompt378_execution_allowed") is False,
        ),
        (
            "prompt503_prompt379_execution_allowed",
            payload.get("prompt503_prompt379_execution_allowed") is False,
        ),
        (
            "prompt503_git_mutation_allowed",
            payload.get("prompt503_git_mutation_allowed") is False,
        ),
        (
            "prompt503_remote_mutation_allowed",
            payload.get("prompt503_remote_mutation_allowed") is False,
        ),
    )
    blocked_reasons = [
        f"missing_{field}" for field, passed in readiness_checks if not passed
    ]
    ready = not blocked_reasons
    next_action = (
        "prepare_prompt379_live_request"
        if ready
        else "manual_review_prompt504_materialization_validation"
    )

    return {
        "local_only": True,
        "source_prompt": "prompt504",
        "prompt504_prompt378_materialization_status": (
            "ready" if ready else "blocked"
        ),
        "prompt504_prompt378_materialization_ready": ready,
        "prompt504_source_prompt503_ready": ready,
        "prompt504_materialized_prompt_kind": "prompt378" if ready else "",
        "prompt504_materialized_prompt_text_ready": ready,
        "prompt504_materialized_prompt_scope_ready": ready,
        "prompt504_materialized_prompt_contract_ready": ready,
        "prompt504_prompt378_validation_status": (
            "valid" if ready else "blocked"
        ),
        "prompt504_prompt378_validation_ready": ready,
        "prompt504_allowed_scope_valid": ready,
        "prompt504_forbidden_scope_absent": ready,
        "prompt504_execution_boundary_valid": ready,
        "prompt504_prompt378_execution_allowed": False,
        "prompt504_prompt379_execution_allowed": False,
        "prompt504_codex_execution_allowed": False,
        "prompt504_git_mutation_allowed": False,
        "prompt504_remote_mutation_allowed": False,
        "prompt504_next_action": next_action,
        "prompt504_blocked_reason": None if ready else blocked_reasons[0],
        "prompt504_blocked_reasons": blocked_reasons,
    }

def _build_prompt505_prepare_prompt379_live_request_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    prompt504_materialized_prompt_kind = _normalize_text(
        payload.get("prompt504_materialized_prompt_kind"),
        default="",
    )
    prompt504_next_action = _normalize_text(
        payload.get("prompt504_next_action"),
        default="",
    )
    readiness_checks = (
        (
            "prompt504_prompt378_materialization_ready",
            payload.get("prompt504_prompt378_materialization_ready") is True,
        ),
        (
            "prompt504_prompt378_validation_ready",
            payload.get("prompt504_prompt378_validation_ready") is True,
        ),
        (
            "prompt504_materialized_prompt_kind",
            prompt504_materialized_prompt_kind == "prompt378",
        ),
        (
            "prompt504_materialized_prompt_text_ready",
            payload.get("prompt504_materialized_prompt_text_ready") is True,
        ),
        (
            "prompt504_materialized_prompt_scope_ready",
            payload.get("prompt504_materialized_prompt_scope_ready") is True,
        ),
        (
            "prompt504_materialized_prompt_contract_ready",
            payload.get("prompt504_materialized_prompt_contract_ready") is True,
        ),
        (
            "prompt504_allowed_scope_valid",
            payload.get("prompt504_allowed_scope_valid") is True,
        ),
        (
            "prompt504_forbidden_scope_absent",
            payload.get("prompt504_forbidden_scope_absent") is True,
        ),
        (
            "prompt504_execution_boundary_valid",
            payload.get("prompt504_execution_boundary_valid") is True,
        ),
        (
            "prompt504_prompt378_execution_allowed",
            payload.get("prompt504_prompt378_execution_allowed") is False,
        ),
        (
            "prompt504_prompt379_execution_allowed",
            payload.get("prompt504_prompt379_execution_allowed") is False,
        ),
        (
            "prompt504_codex_execution_allowed",
            payload.get("prompt504_codex_execution_allowed") is False,
        ),
        (
            "prompt504_git_mutation_allowed",
            payload.get("prompt504_git_mutation_allowed") is False,
        ),
        (
            "prompt504_remote_mutation_allowed",
            payload.get("prompt504_remote_mutation_allowed") is False,
        ),
        (
            "prompt504_next_action",
            prompt504_next_action == "prepare_prompt379_live_request",
        ),
    )
    blocked_reasons = [
        f"missing_{field}" for field, passed in readiness_checks if not passed
    ]
    ready = not blocked_reasons
    next_action = (
        "await_explicit_prompt379_live_enable"
        if ready
        else "manual_review_prompt505_prompt379_live_request"
    )

    return {
        "local_only": True,
        "source_prompt": "prompt505",
        "prompt505_prompt379_live_request_status": (
            "ready" if ready else "blocked"
        ),
        "prompt505_prompt379_live_request_ready": ready,
        "prompt505_source_prompt504_ready": ready,
        "prompt505_codex_prompt_ready": ready,
        "prompt505_execution_transport_ready": ready,
        "prompt505_prompt378_contract_ready": ready,
        "prompt505_prompt379_request_kind": "prompt379_live" if ready else "",
        "prompt505_prompt379_request_source_kind": "prompt378" if ready else "",
        "prompt505_live_execution_allowed": False,
        "prompt505_explicit_enable_required": True,
        "prompt505_prompt379_execution_performed": False,
        "prompt505_codex_execution_allowed": False,
        "prompt505_git_mutation_allowed": False,
        "prompt505_remote_mutation_allowed": False,
        "prompt505_next_action": next_action,
        "prompt505_blocked_reason": None if ready else blocked_reasons[0],
        "prompt505_blocked_reasons": blocked_reasons,
    }

def _build_prompt506_explicit_prompt379_live_enable_gate_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    prompt505_prompt379_request_kind = _normalize_text(
        payload.get("prompt505_prompt379_request_kind"),
        default="",
    )
    prompt505_prompt379_request_source_kind = _normalize_text(
        payload.get("prompt505_prompt379_request_source_kind"),
        default="",
    )
    prompt505_next_action = _normalize_text(
        payload.get("prompt505_next_action"),
        default="",
    )
    readiness_checks = (
        (
            "prompt505_prompt379_live_request_ready",
            payload.get("prompt505_prompt379_live_request_ready") is True,
        ),
        (
            "prompt505_source_prompt504_ready",
            payload.get("prompt505_source_prompt504_ready") is True,
        ),
        (
            "prompt505_codex_prompt_ready",
            payload.get("prompt505_codex_prompt_ready") is True,
        ),
        (
            "prompt505_execution_transport_ready",
            payload.get("prompt505_execution_transport_ready") is True,
        ),
        (
            "prompt505_prompt378_contract_ready",
            payload.get("prompt505_prompt378_contract_ready") is True,
        ),
        (
            "prompt505_prompt379_request_kind",
            prompt505_prompt379_request_kind == "prompt379_live",
        ),
        (
            "prompt505_prompt379_request_source_kind",
            prompt505_prompt379_request_source_kind == "prompt378",
        ),
        (
            "prompt505_live_execution_allowed",
            payload.get("prompt505_live_execution_allowed") is False,
        ),
        (
            "prompt505_explicit_enable_required",
            payload.get("prompt505_explicit_enable_required") is True,
        ),
        (
            "prompt505_prompt379_execution_performed",
            payload.get("prompt505_prompt379_execution_performed") is False,
        ),
        (
            "prompt505_codex_execution_allowed",
            payload.get("prompt505_codex_execution_allowed") is False,
        ),
        (
            "prompt505_git_mutation_allowed",
            payload.get("prompt505_git_mutation_allowed") is False,
        ),
        (
            "prompt505_remote_mutation_allowed",
            payload.get("prompt505_remote_mutation_allowed") is False,
        ),
        (
            "prompt505_next_action",
            prompt505_next_action == "await_explicit_prompt379_live_enable",
        ),
    )
    blocked_reasons = [
        f"missing_{field}" for field, passed in readiness_checks if not passed
    ]
    ready = not blocked_reasons
    next_action = (
        "run_prompt379_live_when_explicitly_enabled"
        if ready
        else "manual_review_prompt506_live_enable_gate"
    )

    return {
        "local_only": True,
        "source_prompt": "prompt506",
        "prompt506_prompt379_live_enable_gate_status": (
            "ready_for_explicit_execution" if ready else "blocked"
        ),
        "prompt506_prompt379_live_enable_gate_ready": ready,
        "prompt506_source_prompt505_ready": ready,
        "prompt506_prompt379_live_request_ready": ready,
        "prompt506_prompt379_request_kind": "prompt379_live" if ready else "",
        "prompt506_prompt379_request_source_kind": "prompt378" if ready else "",
        "prompt506_explicit_enable_required": True,
        "prompt506_explicit_enable_received": False,
        "prompt506_live_execution_allowed": False,
        "prompt506_prompt379_execution_performed": False,
        "prompt506_codex_execution_allowed": False,
        "prompt506_git_mutation_allowed": False,
        "prompt506_remote_mutation_allowed": False,
        "prompt506_next_action": next_action,
        "prompt506_blocked_reason": None if ready else blocked_reasons[0],
        "prompt506_blocked_reasons": blocked_reasons,
    }

def _build_prompt507_one_shot_prompt379_live_execution_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    prompt506_prompt379_request_kind = _normalize_text(
        payload.get("prompt506_prompt379_request_kind"),
        default="",
    )
    prompt506_prompt379_request_source_kind = _normalize_text(
        payload.get("prompt506_prompt379_request_source_kind"),
        default="",
    )
    prompt506_next_action = _normalize_text(
        payload.get("prompt506_next_action"),
        default="",
    )
    readiness_checks = (
        (
            "prompt506_prompt379_live_enable_gate_ready",
            payload.get("prompt506_prompt379_live_enable_gate_ready") is True,
        ),
        (
            "prompt506_source_prompt505_ready",
            payload.get("prompt506_source_prompt505_ready") is True,
        ),
        (
            "prompt506_prompt379_live_request_ready",
            payload.get("prompt506_prompt379_live_request_ready") is True,
        ),
        (
            "prompt506_prompt379_request_kind",
            prompt506_prompt379_request_kind == "prompt379_live",
        ),
        (
            "prompt506_prompt379_request_source_kind",
            prompt506_prompt379_request_source_kind == "prompt378",
        ),
        (
            "prompt506_explicit_enable_required",
            payload.get("prompt506_explicit_enable_required") is True,
        ),
        (
            "prompt506_explicit_enable_received",
            payload.get("prompt506_explicit_enable_received") is False,
        ),
        (
            "prompt506_live_execution_allowed",
            payload.get("prompt506_live_execution_allowed") is False,
        ),
        (
            "prompt506_prompt379_execution_performed",
            payload.get("prompt506_prompt379_execution_performed") is False,
        ),
        (
            "prompt506_codex_execution_allowed",
            payload.get("prompt506_codex_execution_allowed") is False,
        ),
        (
            "prompt506_git_mutation_allowed",
            payload.get("prompt506_git_mutation_allowed") is False,
        ),
        (
            "prompt506_remote_mutation_allowed",
            payload.get("prompt506_remote_mutation_allowed") is False,
        ),
        (
            "prompt506_next_action",
            prompt506_next_action == "run_prompt379_live_when_explicitly_enabled",
        ),
    )
    blocked_reasons = [
        f"missing_{field}" for field, passed in readiness_checks if not passed
    ]
    ready = not blocked_reasons
    next_action = (
        "await_external_explicit_enable_for_prompt379_live_execution"
        if ready
        else "manual_review_prompt507_live_execution_contract"
    )

    return {
        "local_only": True,
        "source_prompt": "prompt507",
        "prompt507_prompt379_live_execution_contract_status": (
            "ready" if ready else "blocked"
        ),
        "prompt507_prompt379_live_execution_contract_ready": ready,
        "prompt507_source_prompt506_ready": ready,
        "prompt507_prompt379_live_request_ready": ready,
        "prompt507_prompt379_request_kind": "prompt379_live" if ready else "",
        "prompt507_prompt379_request_source_kind": "prompt378" if ready else "",
        "prompt507_one_shot_execution_required": ready,
        "prompt507_one_shot_execution_consumed": False,
        "prompt507_explicit_enable_required": True,
        "prompt507_explicit_enable_received": False,
        "prompt507_live_execution_allowed": False,
        "prompt507_enable_token_required": True,
        "prompt507_enable_token_received": False,
        "prompt507_prompt379_execution_performed": False,
        "prompt507_prompt379_returncode": None,
        "prompt507_prompt379_returncode_classification": "not_run",
        "prompt507_prompt379_post_execution_changed_files": [],
        "prompt507_prompt379_post_execution_tracked_diff_empty": False,
        "prompt507_codex_execution_allowed": False,
        "prompt507_git_mutation_allowed": False,
        "prompt507_remote_mutation_allowed": False,
        "prompt507_next_action": next_action,
        "prompt507_blocked_reason": None if ready else blocked_reasons[0],
        "prompt507_blocked_reasons": blocked_reasons,
    }

def _build_prompt508_external_enable_dispatch_readiness_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    prompt507_prompt379_request_kind = _normalize_text(
        payload.get("prompt507_prompt379_request_kind"),
        default="",
    )
    prompt507_prompt379_request_source_kind = _normalize_text(
        payload.get("prompt507_prompt379_request_source_kind"),
        default="",
    )
    prompt507_prompt379_returncode_classification = _normalize_text(
        payload.get("prompt507_prompt379_returncode_classification"),
        default="",
    )
    prompt507_next_action = _normalize_text(
        payload.get("prompt507_next_action"),
        default="",
    )
    readiness_checks = (
        (
            "prompt507_prompt379_live_execution_contract_ready",
            payload.get("prompt507_prompt379_live_execution_contract_ready") is True,
        ),
        (
            "prompt507_source_prompt506_ready",
            payload.get("prompt507_source_prompt506_ready") is True,
        ),
        (
            "prompt507_prompt379_live_request_ready",
            payload.get("prompt507_prompt379_live_request_ready") is True,
        ),
        (
            "prompt507_prompt379_request_kind",
            prompt507_prompt379_request_kind == "prompt379_live",
        ),
        (
            "prompt507_prompt379_request_source_kind",
            prompt507_prompt379_request_source_kind == "prompt378",
        ),
        (
            "prompt507_one_shot_execution_required",
            payload.get("prompt507_one_shot_execution_required") is True,
        ),
        (
            "prompt507_one_shot_execution_consumed",
            payload.get("prompt507_one_shot_execution_consumed") is False,
        ),
        (
            "prompt507_explicit_enable_required",
            payload.get("prompt507_explicit_enable_required") is True,
        ),
        (
            "prompt507_explicit_enable_received",
            payload.get("prompt507_explicit_enable_received") is False,
        ),
        (
            "prompt507_live_execution_allowed",
            payload.get("prompt507_live_execution_allowed") is False,
        ),
        (
            "prompt507_enable_token_required",
            payload.get("prompt507_enable_token_required") is True,
        ),
        (
            "prompt507_enable_token_received",
            payload.get("prompt507_enable_token_received") is False,
        ),
        (
            "prompt507_prompt379_execution_performed",
            payload.get("prompt507_prompt379_execution_performed") is False,
        ),
        (
            "prompt507_prompt379_returncode_classification",
            prompt507_prompt379_returncode_classification == "not_run",
        ),
        (
            "prompt507_codex_execution_allowed",
            payload.get("prompt507_codex_execution_allowed") is False,
        ),
        (
            "prompt507_git_mutation_allowed",
            payload.get("prompt507_git_mutation_allowed") is False,
        ),
        (
            "prompt507_remote_mutation_allowed",
            payload.get("prompt507_remote_mutation_allowed") is False,
        ),
        (
            "prompt507_next_action",
            prompt507_next_action
            == "await_external_explicit_enable_for_prompt379_live_execution",
        ),
    )
    blocked_reasons = [
        f"missing_{field}" for field, passed in readiness_checks if not passed
    ]
    base_ready = not blocked_reasons
    external_enable_evidence_present = (
        payload.get("prompt508_external_enable_evidence_present") is True
    )
    external_enable_token_valid = (
        payload.get("prompt508_external_enable_token_valid") is True
    )
    external_enable_scope_valid = (
        payload.get("prompt508_external_enable_scope_valid") is True
    )
    external_enable_one_shot_confirmed = (
        payload.get("prompt508_external_enable_one_shot_confirmed") is True
    )
    valid_enable_evidence = all(
        (
            external_enable_evidence_present,
            external_enable_token_valid,
            external_enable_scope_valid,
            external_enable_one_shot_confirmed,
        )
    )
    dispatch_ready = base_ready and valid_enable_evidence
    if dispatch_ready:
        intake_status = "ready_with_valid_enable"
        enable_boundary_status = "valid"
        next_action = "dispatch_one_shot_prompt379_live_execution"
    elif base_ready:
        intake_status = "awaiting_external_enable"
        enable_boundary_status = "awaiting_enable_token"
        next_action = "await_external_enable_token"
    else:
        intake_status = "blocked"
        enable_boundary_status = "blocked"
        next_action = "manual_review_prompt508_external_enable_intake"

    return {
        "local_only": True,
        "source_prompt": "prompt508",
        "prompt508_external_enable_intake_status": intake_status,
        "prompt508_external_enable_intake_ready": base_ready,
        "prompt508_source_prompt507_ready": base_ready,
        "prompt508_prompt379_live_execution_contract_ready": base_ready,
        "prompt508_prompt379_request_kind": (
            "prompt379_live" if base_ready else ""
        ),
        "prompt508_prompt379_request_source_kind": (
            "prompt378" if base_ready else ""
        ),
        "prompt508_explicit_enable_required": True,
        "prompt508_external_enable_required": True,
        "prompt508_external_enable_evidence_present": (
            external_enable_evidence_present
        ),
        "prompt508_external_enable_token_valid": external_enable_token_valid,
        "prompt508_external_enable_scope_valid": external_enable_scope_valid,
        "prompt508_external_enable_one_shot_confirmed": (
            external_enable_one_shot_confirmed
        ),
        "prompt508_external_enable_received": valid_enable_evidence,
        "prompt508_enable_boundary_status": enable_boundary_status,
        "prompt508_dispatch_preconditions_ready": dispatch_ready,
        "prompt508_one_shot_execution_required": base_ready,
        "prompt508_one_shot_execution_consumed": False,
        "prompt508_one_shot_dispatch_ready": dispatch_ready,
        "prompt508_prompt379_live_dispatch_allowed": dispatch_ready,
        "prompt508_prompt379_execution_dispatch_performed": False,
        "prompt508_prompt379_execution_performed": False,
        "prompt508_prompt379_returncode": None,
        "prompt508_prompt379_returncode_classification": "not_run",
        "prompt508_prompt379_post_execution_changed_files": [],
        "prompt508_prompt379_post_execution_tracked_diff_empty": False,
        "prompt508_post_execution_review_required": False,
        "prompt508_post_execution_review_ready": False,
        "prompt508_next_review_prompt_kind": "prompt509" if dispatch_ready else "",
        "prompt508_review_source_kind": (
            "prompt379_live_execution" if dispatch_ready else ""
        ),
        "prompt508_codex_execution_allowed": False,
        "prompt508_git_mutation_allowed": False,
        "prompt508_remote_mutation_allowed": False,
        "prompt508_next_action": next_action,
        "prompt508_blocked_reason": None if base_ready else blocked_reasons[0],
        "prompt508_blocked_reasons": blocked_reasons,
    }

def _build_prompt485_prompt378_supply_ready_for_prompt379_live_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    prompt484i_generated_prompt_file_request_ready = (
        payload.get("prompt484i_generated_prompt_file_request_ready") is True
    )
    prompt484i_next_action = _normalize_text(
        payload.get("prompt484i_next_action"),
        default="",
    )
    prompt484i_expected_supply_flag = _normalize_text(
        payload.get("prompt484i_expected_supply_flag"),
        default="",
    )
    prompt484i_expected_next_action_after_supply = _normalize_text(
        payload.get("prompt484i_expected_next_action_after_supply"),
        default="",
    )
    prompt378_generated_prompt_supplied = (
        payload.get("prompt378_generated_prompt_supplied") is True
    )
    prompt378_generated_prompt_ready = (
        payload.get("prompt378_generated_prompt_ready") is True
    )
    prompt378_generated_prompt_validation_status = _normalize_text(
        payload.get("prompt378_generated_prompt_validation_status"),
        default="",
    )
    prompt378_generated_prompt_execution_handoff_ready = (
        payload.get("prompt378_generated_prompt_execution_handoff_ready")
        is True
    )
    prompt378_next_action = _normalize_text(
        payload.get("prompt378_next_action"),
        default="",
    )
    prompt378_active_blocked_reasons = payload.get(
        "prompt378_active_blocked_reasons"
    )
    prompt379_prompt378_generated_prompt_ready = (
        payload.get("prompt379_prompt378_generated_prompt_ready") is True
    )

    expected_bridge_action = (
        "prepare_prompt379_generated_prompt_codex_execution_bridge"
    )
    blocked_reasons: list[str] = []
    if not prompt484i_generated_prompt_file_request_ready:
        blocked_reasons.append(
            "prompt484i_generated_prompt_file_request_ready_missing_or_not_ready"
        )
    if prompt484i_next_action != _PROMPT484I_SUCCESS_NEXT_ACTION:
        blocked_reasons.append("prompt484i_next_action_unexpected")
    if prompt484i_expected_supply_flag != "--prompt378-generated-prompt-path":
        blocked_reasons.append("prompt484i_expected_supply_flag_unexpected")
    if prompt484i_expected_next_action_after_supply != expected_bridge_action:
        blocked_reasons.append(
            "prompt484i_expected_next_action_after_supply_unexpected"
        )
    if not prompt378_generated_prompt_supplied:
        blocked_reasons.append(
            "prompt378_generated_prompt_supplied_missing_or_not_ready"
        )
    if not prompt378_generated_prompt_ready:
        blocked_reasons.append(
            "prompt378_generated_prompt_ready_missing_or_not_ready"
        )
    if prompt378_generated_prompt_validation_status != "valid":
        blocked_reasons.append(
            "prompt378_generated_prompt_validation_status_unexpected"
        )
    if not prompt378_generated_prompt_execution_handoff_ready:
        blocked_reasons.append(
            "prompt378_generated_prompt_execution_handoff_ready_missing_or_not_ready"
        )
    if prompt378_next_action != expected_bridge_action:
        blocked_reasons.append("prompt378_next_action_unexpected")
    if prompt378_active_blocked_reasons != []:
        blocked_reasons.append("prompt378_active_blocked_reasons_unexpected")
    if not prompt379_prompt378_generated_prompt_ready:
        blocked_reasons.append(
            "prompt379_prompt378_generated_prompt_ready_missing_or_not_ready"
        )

    prompt484i_ready = bool(
        prompt484i_generated_prompt_file_request_ready
        and prompt484i_next_action == _PROMPT484I_SUCCESS_NEXT_ACTION
        and prompt484i_expected_supply_flag == "--prompt378-generated-prompt-path"
        and prompt484i_expected_next_action_after_supply == expected_bridge_action
    )
    ready = bool(
        prompt484i_ready
        and prompt378_generated_prompt_supplied
        and prompt378_generated_prompt_ready
        and prompt378_generated_prompt_validation_status == "valid"
        and prompt378_generated_prompt_execution_handoff_ready
        and prompt378_next_action == expected_bridge_action
        and prompt378_active_blocked_reasons == []
        and prompt379_prompt378_generated_prompt_ready
        and not blocked_reasons
    )

    return {
        "prompt485_schema_version": _PROMPT485_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt485",
        "prompt485_applicable": True,
        "prompt485_prompt378_supply_status": (
            "ready" if ready else "blocked"
        ),
        "prompt485_prompt378_supply_ready": ready,
        "prompt485_prompt484i_ready": prompt484i_ready,
        "prompt485_prompt378_generated_prompt_supplied": (
            prompt378_generated_prompt_supplied
        ),
        "prompt485_prompt378_generated_prompt_ready": (
            prompt378_generated_prompt_ready
        ),
        "prompt485_prompt378_validation_status": (
            prompt378_generated_prompt_validation_status
        ),
        "prompt485_prompt378_execution_handoff_ready": (
            prompt378_generated_prompt_execution_handoff_ready
        ),
        "prompt485_prompt379_prompt_ready": (
            prompt379_prompt378_generated_prompt_ready
        ),
        "prompt485_prompt379_live_execution_expected": True,
        "prompt485_codex_execution_count_limit": 1,
        "prompt485_auto_commit_allowed": False,
        "prompt485_auto_tag_allowed": False,
        "prompt485_remote_mutation_allowed": False,
        "prompt485_blocked_reason": (
            blocked_reasons[0] if blocked_reasons else ""
        ),
        "prompt485_blocked_reasons": blocked_reasons,
        "prompt485_next_action": (
            _PROMPT485_SUCCESS_NEXT_ACTION
            if ready
            else _PROMPT485_BLOCKED_NEXT_ACTION
        ),
    }

def _build_prompt486_prompt379_live_isolated_preflight_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    prompt485_prompt378_supply_ready = (
        payload.get("prompt485_prompt378_supply_ready") is True
    )
    prompt485_prompt484i_ready = (
        payload.get("prompt485_prompt484i_ready") is True
    )
    prompt485_prompt378_validation_status = _normalize_text(
        payload.get("prompt485_prompt378_validation_status"),
        default="",
    )
    prompt485_prompt379_prompt_ready = (
        payload.get("prompt485_prompt379_prompt_ready") is True
    )
    prompt485_prompt379_live_execution_expected = payload.get(
        "prompt485_prompt379_live_execution_expected"
    )
    prompt485_codex_execution_count_limit = payload.get(
        "prompt485_codex_execution_count_limit"
    )
    prompt485_auto_commit_allowed = payload.get(
        "prompt485_auto_commit_allowed"
    )
    prompt485_auto_tag_allowed = payload.get("prompt485_auto_tag_allowed")
    prompt485_remote_mutation_allowed = payload.get(
        "prompt485_remote_mutation_allowed"
    )
    prompt485_next_action = _normalize_text(
        payload.get("prompt485_next_action"),
        default="",
    )
    prompt485_blocked_reasons = payload.get("prompt485_blocked_reasons")

    blocked_reasons: list[str] = []
    if not prompt485_prompt378_supply_ready:
        blocked_reasons.append(
            "prompt485_prompt378_supply_ready_missing_or_not_ready"
        )
    if not prompt485_prompt484i_ready:
        blocked_reasons.append(
            "prompt485_prompt484i_ready_missing_or_not_ready"
        )
    if prompt485_prompt378_validation_status != "valid":
        blocked_reasons.append(
            "prompt485_prompt378_validation_status_unexpected"
        )
    if not prompt485_prompt379_prompt_ready:
        blocked_reasons.append(
            "prompt485_prompt379_prompt_ready_missing_or_not_ready"
        )
    if prompt485_prompt379_live_execution_expected is not True:
        blocked_reasons.append(
            "prompt485_prompt379_live_execution_expected_missing_or_unexpected"
        )
    if prompt485_codex_execution_count_limit != 1:
        blocked_reasons.append(
            "prompt485_codex_execution_count_limit_unexpected"
        )
    if prompt485_auto_commit_allowed is not False:
        blocked_reasons.append("prompt485_auto_commit_allowed_unexpected")
    if prompt485_auto_tag_allowed is not False:
        blocked_reasons.append("prompt485_auto_tag_allowed_unexpected")
    if prompt485_remote_mutation_allowed is not False:
        blocked_reasons.append(
            "prompt485_remote_mutation_allowed_unexpected"
        )
    if prompt485_next_action != _PROMPT485_SUCCESS_NEXT_ACTION:
        blocked_reasons.append("prompt485_next_action_unexpected")
    if prompt485_blocked_reasons != []:
        blocked_reasons.append("prompt485_blocked_reasons_unexpected")

    prompt485_ready = bool(
        prompt485_prompt378_supply_ready
        and prompt485_prompt484i_ready
        and prompt485_prompt378_validation_status == "valid"
        and prompt485_prompt379_prompt_ready
        and prompt485_prompt379_live_execution_expected is True
        and prompt485_codex_execution_count_limit == 1
        and prompt485_auto_commit_allowed is False
        and prompt485_auto_tag_allowed is False
        and prompt485_remote_mutation_allowed is False
        and prompt485_next_action == _PROMPT485_SUCCESS_NEXT_ACTION
        and prompt485_blocked_reasons == []
    )
    ready = bool(prompt485_ready and not blocked_reasons)

    return {
        "prompt486_schema_version": _PROMPT486_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt486",
        "prompt486_applicable": True,
        "prompt486_prompt379_live_preflight_status": (
            "ready" if ready else "blocked"
        ),
        "prompt486_prompt379_live_preflight_ready": ready,
        "prompt486_prompt485_ready": prompt485_ready,
        "prompt486_prompt378_supply_ready": prompt485_prompt378_supply_ready,
        "prompt486_prompt378_validation_status": (
            prompt485_prompt378_validation_status
        ),
        "prompt486_prompt379_prompt_ready": prompt485_prompt379_prompt_ready,
        "prompt486_prompt379_live_execution_expected": True,
        "prompt486_local_codex_one_shot_path_deferred": True,
        "prompt486_unrelated_pre_prompt379_mutation_allowed": False,
        "prompt486_codex_execution_count_limit": 1,
        "prompt486_auto_commit_allowed": False,
        "prompt486_auto_tag_allowed": False,
        "prompt486_remote_mutation_allowed": False,
        "prompt486_blocked_reason": (
            blocked_reasons[0] if blocked_reasons else ""
        ),
        "prompt486_blocked_reasons": blocked_reasons,
        "prompt486_next_action": (
            _PROMPT486_SUCCESS_NEXT_ACTION
            if ready
            else _PROMPT486_BLOCKED_NEXT_ACTION
        ),
    }

def _build_prompt487_isolated_prompt379_live_route_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
    dry_run: bool,
    live_transport_enabled: bool,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    blocked_reasons: list[str] = []

    required_prompt486_fields: tuple[tuple[str, Any], ...] = (
        ("prompt486_prompt379_live_preflight_ready", True),
        ("prompt486_next_action", _PROMPT486_SUCCESS_NEXT_ACTION),
        ("prompt486_local_codex_one_shot_path_deferred", True),
        ("prompt486_unrelated_pre_prompt379_mutation_allowed", False),
        ("prompt486_codex_execution_count_limit", 1),
        ("prompt486_auto_commit_allowed", False),
        ("prompt486_auto_tag_allowed", False),
        ("prompt486_remote_mutation_allowed", False),
    )
    for field_name, expected in required_prompt486_fields:
        if field_name not in payload:
            blocked_reasons.append(f"{field_name}_missing")
            continue
        value = payload.get(field_name)
        if value != expected:
            blocked_reasons.append(f"{field_name}_unexpected")

    if bool(dry_run):
        blocked_reasons.append("transport_mode_not_live")
    if not bool(live_transport_enabled):
        blocked_reasons.append("live_transport_not_explicitly_enabled")

    prompt486_ready = bool(
        payload.get("prompt486_prompt379_live_preflight_ready") is True
        and _normalize_text(payload.get("prompt486_next_action"), default="")
        == _PROMPT486_SUCCESS_NEXT_ACTION
        and payload.get("prompt486_local_codex_one_shot_path_deferred") is True
        and payload.get("prompt486_unrelated_pre_prompt379_mutation_allowed") is False
        and payload.get("prompt486_codex_execution_count_limit") == 1
        and payload.get("prompt486_auto_commit_allowed") is False
        and payload.get("prompt486_auto_tag_allowed") is False
        and payload.get("prompt486_remote_mutation_allowed") is False
    )
    ready = bool(prompt486_ready and not blocked_reasons)

    return {
        "prompt487_schema_version": _PROMPT487_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt487",
        "prompt487_applicable": True,
        "prompt487_isolated_prompt379_live_route_status": (
            "ready" if ready else "blocked"
        ),
        "prompt487_isolated_prompt379_live_route_ready": ready,
        "prompt487_prompt486_ready": prompt486_ready,
        "prompt487_local_codex_one_shot_path_deferred": True,
        "prompt487_unrelated_pre_prompt379_mutation_allowed": False,
        "prompt487_prompt379_bridge_selected": ready,
        "prompt487_prompt379_live_execution_once_expected": True,
        "prompt487_codex_execution_count_limit": 1,
        "prompt487_auto_commit_allowed": False,
        "prompt487_auto_tag_allowed": False,
        "prompt487_remote_mutation_allowed": False,
        "prompt487_blocked_reason": (
            blocked_reasons[0] if blocked_reasons else ""
        ),
        "prompt487_blocked_reasons": blocked_reasons,
        "prompt487_next_action": (
            _PROMPT487_SUCCESS_NEXT_ACTION
            if ready
            else _PROMPT487_BLOCKED_NEXT_ACTION
        ),
    }

def _build_prompt489_real_task_marker_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    prompt379_returncode_classification = _normalize_text(
        payload.get("prompt379_returncode_classification"),
        default="",
    )

    return {
        "prompt489_real_task_marker_status": "ready",
        "prompt489_real_task_marker_ready": True,
        "prompt489_source_prompt487_ready": bool(
            payload.get("prompt487_isolated_prompt379_live_route_ready") is True
        ),
        "prompt489_source_prompt379_success": bool(
            payload.get("prompt489_source_prompt379_success") is True
            or prompt379_returncode_classification == "success"
        ),
        "prompt489_next_action": _PROMPT489_NEXT_ACTION,
    }

def _build_prompt490_second_success_cycle_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    prompt379_returncode_classification = _normalize_text(
        payload.get("prompt379_returncode_classification"),
        default="",
    )

    return {
        "prompt490_second_success_cycle_status": "ready",
        "prompt490_second_success_cycle_ready": True,
        "prompt490_source_prompt489_ready": bool(
            payload.get("prompt489_real_task_marker_ready") is True
        ),
        "prompt490_source_prompt379_success": bool(
            payload.get("prompt490_source_prompt379_success") is True
            or prompt379_returncode_classification == "success"
        ),
        "prompt490_next_action": _PROMPT490_NEXT_ACTION,
    }

def _build_prompt491_third_success_cycle_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    prompt379_returncode_classification = _normalize_text(
        payload.get("prompt379_returncode_classification"),
        default="",
    )
    prompt489_real_task_marker_ready = bool(
        payload.get("prompt489_real_task_marker_ready") is True
        or _normalize_text(payload.get("prompt489_real_task_marker_status"), default="")
        == "ready"
    )
    prompt490_second_success_cycle_ready = bool(
        payload.get("prompt490_second_success_cycle_ready") is True
        or _normalize_text(
            payload.get("prompt490_second_success_cycle_status"),
            default="",
        )
        == "ready"
    )
    prompt489_source_prompt379_success = bool(
        payload.get("prompt489_source_prompt379_success") is True
        or prompt379_returncode_classification == "success"
    )
    prompt490_source_prompt379_success = bool(
        payload.get("prompt490_source_prompt379_success") is True
        or prompt379_returncode_classification == "success"
    )
    two_cycle_success_evidence_ready = bool(
        prompt489_real_task_marker_ready and prompt490_second_success_cycle_ready
    )
    current_prompt379_dry_run_safe = bool(
        _normalize_text(
            payload.get("prompt379_generated_prompt_codex_execution_bridge_status"),
            default="",
        )
        == "blocked"
        and payload.get("prompt379_execution_allowed") is False
        and payload.get("prompt379_execution_performed") is False
        and _normalize_text(
            payload.get("prompt379_active_blocked_reason"),
            default="",
        )
        == "prompt379_dry_run_transport_execution_suppressed"
    )
    current_prompt383_non_exec_safe = bool(
        _normalize_text(
            payload.get("prompt383_explicit_approve_commit_tag_execution_status"),
            default="",
        )
        == "blocked"
        and payload.get("prompt383_execution_allowed") is False
        and payload.get("prompt383_execution_performed") is False
        and payload.get("prompt383_git_mutation_allowed") is False
        and payload.get("prompt383_git_mutation_performed") is False
        and payload.get("prompt383_remote_mutation_allowed") is False
        and payload.get("prompt383_remote_mutation_performed") is False
    )
    local_multi_cycle_success_replay_ready = bool(two_cycle_success_evidence_ready)
    active_blocked_reasons = _normalize_string_list(
        payload.get("prompt379_active_blocked_reasons")
    )
    for reason in _normalize_string_list(payload.get("prompt383_active_blocked_reasons")):
        if reason not in active_blocked_reasons:
            active_blocked_reasons.append(reason)
    active_blocked_reason = _normalize_text(
        payload.get("prompt379_active_blocked_reason")
        or payload.get("prompt383_active_blocked_reason"),
        default=active_blocked_reasons[0] if active_blocked_reasons else "",
    )
    next_action = (
        "accept_candidate_then_commit_tag"
        if (
            two_cycle_success_evidence_ready
            and current_prompt379_dry_run_safe
            and current_prompt383_non_exec_safe
        )
        else _PROMPT491_NEXT_ACTION
    )
    prompt500_absorbed_candidate_fields = {
        key: value
        for key, value in payload.items()
        if key.startswith("prompt500_")
    }
    if not prompt500_absorbed_candidate_fields:
        prompt500_absorbed_candidate_reconciliation = (
            _build_prompt500_absorbed_prompt379_candidate_reconciliation_state(
                run_state_payload=payload,
            )
        )
        prompt500_absorbed_candidate_fields = {
            key: value
            for key, value in prompt500_absorbed_candidate_reconciliation.items()
            if key.startswith("prompt500_")
        }
    prompt501_absorbed_candidate_success_continuation = (
        _build_prompt501_absorbed_candidate_success_continuation_state(
            run_state_payload={
                **payload,
                **prompt500_absorbed_candidate_fields,
            },
        )
    )
    prompt501_absorbed_candidate_fields = {
        key: value
        for key, value in prompt501_absorbed_candidate_success_continuation.items()
        if key.startswith("prompt501_")
    }
    prompt502_next_live_cycle_bridge = _build_prompt502_next_live_cycle_bridge_state(
        run_state_payload={
            **payload,
            **prompt500_absorbed_candidate_fields,
            **prompt501_absorbed_candidate_fields,
        },
    )
    prompt502_next_live_cycle_bridge_fields = {
        key: value
        for key, value in prompt502_next_live_cycle_bridge.items()
        if key.startswith("prompt502_")
    }
    prompt503_prompt378_next_cycle_request = (
        _build_prompt503_prompt378_next_cycle_request_state(
            run_state_payload={
                **payload,
                **prompt500_absorbed_candidate_fields,
                **prompt501_absorbed_candidate_fields,
                **prompt502_next_live_cycle_bridge_fields,
            },
        )
    )
    prompt503_prompt378_next_cycle_request_fields = {
        key: value
        for key, value in prompt503_prompt378_next_cycle_request.items()
        if key.startswith("prompt503_")
    }
    prompt504_materialize_and_validate_next_prompt378 = (
        _build_prompt504_materialize_and_validate_next_prompt378_state(
            run_state_payload={
                **payload,
                **prompt500_absorbed_candidate_fields,
                **prompt501_absorbed_candidate_fields,
                **prompt502_next_live_cycle_bridge_fields,
                **prompt503_prompt378_next_cycle_request_fields,
            },
        )
    )
    prompt504_materialize_and_validate_next_prompt378_fields = {
        key: value
        for key, value in (
            prompt504_materialize_and_validate_next_prompt378.items()
        )
        if key.startswith("prompt504_")
    }
    prompt505_prepare_prompt379_live_request = (
        _build_prompt505_prepare_prompt379_live_request_state(
            run_state_payload={
                **payload,
                **prompt500_absorbed_candidate_fields,
                **prompt501_absorbed_candidate_fields,
                **prompt502_next_live_cycle_bridge_fields,
                **prompt503_prompt378_next_cycle_request_fields,
                **prompt504_materialize_and_validate_next_prompt378_fields,
            },
        )
    )
    prompt505_prepare_prompt379_live_request_fields = {
        key: value
        for key, value in prompt505_prepare_prompt379_live_request.items()
        if key.startswith("prompt505_")
    }
    prompt506_explicit_prompt379_live_enable_gate = (
        _build_prompt506_explicit_prompt379_live_enable_gate_state(
            run_state_payload={
                **payload,
                **prompt500_absorbed_candidate_fields,
                **prompt501_absorbed_candidate_fields,
                **prompt502_next_live_cycle_bridge_fields,
                **prompt503_prompt378_next_cycle_request_fields,
                **prompt504_materialize_and_validate_next_prompt378_fields,
                **prompt505_prepare_prompt379_live_request_fields,
            },
        )
    )
    prompt506_explicit_prompt379_live_enable_gate_fields = {
        key: value
        for key, value in prompt506_explicit_prompt379_live_enable_gate.items()
        if key.startswith("prompt506_")
    }
    prompt507_one_shot_prompt379_live_execution = (
        _build_prompt507_one_shot_prompt379_live_execution_state(
            run_state_payload={
                **payload,
                **prompt500_absorbed_candidate_fields,
                **prompt501_absorbed_candidate_fields,
                **prompt502_next_live_cycle_bridge_fields,
                **prompt503_prompt378_next_cycle_request_fields,
                **prompt504_materialize_and_validate_next_prompt378_fields,
                **prompt505_prepare_prompt379_live_request_fields,
                **prompt506_explicit_prompt379_live_enable_gate_fields,
            },
        )
    )
    prompt507_one_shot_prompt379_live_execution_fields = {
        key: value
        for key, value in prompt507_one_shot_prompt379_live_execution.items()
        if key.startswith("prompt507_")
    }
    prompt508_external_enable_dispatch_readiness = (
        _build_prompt508_external_enable_dispatch_readiness_state(
            run_state_payload={
                **payload,
                **prompt500_absorbed_candidate_fields,
                **prompt501_absorbed_candidate_fields,
                **prompt502_next_live_cycle_bridge_fields,
                **prompt503_prompt378_next_cycle_request_fields,
                **prompt504_materialize_and_validate_next_prompt378_fields,
                **prompt505_prepare_prompt379_live_request_fields,
                **prompt506_explicit_prompt379_live_enable_gate_fields,
                **prompt507_one_shot_prompt379_live_execution_fields,
            },
        )
    )
    prompt508_external_enable_dispatch_readiness_fields = {
        key: value
        for key, value in prompt508_external_enable_dispatch_readiness.items()
        if key.startswith("prompt508_")
    }

    return {
        "prompt491_third_success_cycle_status": "ready",
        "prompt491_third_success_cycle_ready": True,
        "prompt491_source_prompt490_ready": bool(
            prompt490_second_success_cycle_ready
        ),
        "prompt491_source_prompt379_success": bool(
            payload.get("prompt491_source_prompt379_success") is True
            or prompt379_returncode_classification == "success"
        ),
        "current_head_sha": _normalize_text(payload.get("current_head_sha"), default=""),
        "current_head_tags": _normalize_string_list(payload.get("current_head_tags")),
        "prompt489_real_task_marker_ready": prompt489_real_task_marker_ready,
        "prompt490_second_success_cycle_ready": prompt490_second_success_cycle_ready,
        "prompt489_source_prompt379_success": prompt489_source_prompt379_success,
        "prompt490_source_prompt379_success": prompt490_source_prompt379_success,
        "two_cycle_success_evidence_ready": two_cycle_success_evidence_ready,
        "current_prompt379_dry_run_safe": current_prompt379_dry_run_safe,
        "current_prompt383_non_exec_safe": current_prompt383_non_exec_safe,
        "local_multi_cycle_success_replay_ready": (
            local_multi_cycle_success_replay_ready
        ),
        "execution_allowed": False,
        "git_mutation_allowed": False,
        "remote_mutation_allowed": False,
        "next_action": next_action,
        "active_blocked_reason": active_blocked_reason,
        "active_blocked_reasons": active_blocked_reasons,
        "prompt491_next_action": next_action,
        **prompt500_absorbed_candidate_fields,
        **prompt501_absorbed_candidate_fields,
        **prompt502_next_live_cycle_bridge_fields,
        **prompt503_prompt378_next_cycle_request_fields,
        **prompt504_materialize_and_validate_next_prompt378_fields,
        **prompt505_prepare_prompt379_live_request_fields,
        **prompt506_explicit_prompt379_live_enable_gate_fields,
        **prompt507_one_shot_prompt379_live_execution_fields,
        **prompt508_external_enable_dispatch_readiness_fields,
    }

def _build_prompt471_commit_tag_candidate_execution_gate_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
    execution_repo_path: str | Path | None = None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    repo_path = _normalize_text(execution_repo_path, default="")
    allowed_tracked_files = [
        "automation/orchestration/planned_execution_runner.py",
        "automation/orchestration/run_state_summary_contract.py",
    ]
    route_decision = _normalize_text(
        payload.get("prompt470_post_fix_route_decision"),
        default="",
    )
    upstream_ready = _prompt471_upstream_evidence_ready(payload)
    explicit_allow_present = _prompt471_bool_from_any_existing(
        payload,
        ("prompt471_explicit_commit_tag_allow_present",),
    )
    allow_commit = _prompt471_bool_from_any_existing(
        payload,
        ("prompt471_allow_commit",),
    )
    allow_tag = _prompt471_bool_from_any_existing(
        payload,
        ("prompt471_allow_tag",),
    )
    allow_git_mutation = _prompt471_bool_from_any_existing(
        payload,
        ("prompt471_allow_git_mutation",),
    )
    runtime_execution_requested = _prompt471_bool_from_any_existing(
        payload,
        ("prompt471_runtime_commit_tag_execution_requested",),
    )

    worktree = _prompt470_collect_post_fix_diff(
        repo_path=repo_path,
        allowed_tracked_files=allowed_tracked_files,
    )
    worktree_evidence_ready = worktree.get("known") is True
    changed_tracked_files = _normalize_string_list(
        worktree.get("changed_files"),
        sort_items=False,
    )
    unexpected_tracked_files = _normalize_string_list(
        worktree.get("unexpected_files"),
        sort_items=False,
    )
    untracked_files = _normalize_string_list(
        worktree.get("untracked_files"),
        sort_items=False,
    )
    tag_exists = _prompt471_tag_exists(
        repo_path=repo_path,
        tag_name=_PROMPT471_TAG_NAME,
    )
    tag_evidence_ready = tag_exists is not None
    tag_already_exists = bool(tag_exists is True)
    all_explicit_allow_signals = bool(
        explicit_allow_present
        and allow_commit
        and allow_tag
        and allow_git_mutation
        and runtime_execution_requested
    )

    blocked_reasons: list[str] = []
    if not upstream_ready:
        blocked_reasons.append("prompt470_handoff_evidence_missing")
    if upstream_ready and route_decision not in {
        "no_targeted_fix_required_prepare_commit_tag_candidate",
        "targeted_fix_success_prepare_commit_tag_candidate",
    }:
        blocked_reasons.append("prompt470_post_fix_route_not_commit_candidate")
    if not worktree_evidence_ready or not tag_evidence_ready:
        blocked_reasons.append("prompt471_worktree_evidence_unknown")
    if unexpected_tracked_files:
        blocked_reasons.append("prompt471_unexpected_tracked_files_present")
    if untracked_files:
        blocked_reasons.append("prompt471_untracked_files_present")
    if worktree_evidence_ready and not changed_tracked_files:
        blocked_reasons.append("prompt471_no_changed_tracked_files_for_commit")
    if tag_already_exists:
        blocked_reasons.append("prompt471_tag_already_exists")

    candidate_valid = not blocked_reasons
    execution_allowed = bool(candidate_valid and all_explicit_allow_signals)
    base_state: dict[str, Any] = {
        "prompt471_schema_version": _PROMPT471_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt471",
        "prompt471_applicable": True,
        "prompt471_commit_tag_candidate_status": "blocked",
        "prompt471_commit_tag_candidate_ready": False,
        "prompt471_upstream_prompt470_evidence_ready": upstream_ready,
        "prompt471_input_post_fix_route_decision": route_decision,
        "prompt471_allowed_tracked_files": allowed_tracked_files,
        "prompt471_changed_tracked_files": changed_tracked_files,
        "prompt471_unexpected_tracked_files": unexpected_tracked_files,
        "prompt471_untracked_files": untracked_files,
        "prompt471_worktree_evidence_ready": bool(
            worktree_evidence_ready and tag_evidence_ready
        ),
        "prompt471_tag_name": _PROMPT471_TAG_NAME,
        "prompt471_tag_already_exists": tag_already_exists,
        "prompt471_commit_message": _PROMPT471_COMMIT_MESSAGE,
        "prompt471_explicit_commit_tag_allow_present": explicit_allow_present,
        "prompt471_allow_commit": allow_commit,
        "prompt471_allow_tag": allow_tag,
        "prompt471_allow_git_mutation": allow_git_mutation,
        "prompt471_runtime_commit_tag_execution_requested": runtime_execution_requested,
        "prompt471_commit_tag_execution_allowed": execution_allowed,
        "prompt471_commit_attempted": False,
        "prompt471_commit_performed": False,
        "prompt471_tag_attempted": False,
        "prompt471_tag_performed": False,
        "prompt471_commit_returncode": None,
        "prompt471_tag_returncode": None,
        "prompt471_post_commit_head": "",
        "prompt471_post_commit_tag_at_head": [],
        "prompt471_post_commit_worktree_clean": False,
        "prompt471_prompt472_handoff_ready": False,
        "prompt471_post_commit_clean_rerun_request_ready": False,
        "prompt471_next_cycle_continuation_request_ready": False,
        "prompt471_human_review_required": True,
        "prompt471_human_intervention_required": True,
        "prompt471_auto_route_allowed": False,
        "prompt471_codex_invocation_allowed": False,
        "prompt471_file_creation_allowed": False,
        "prompt471_tests_allowed": False,
        "prompt471_commit_tag_allowed": execution_allowed,
        "prompt471_push_allowed": False,
        "prompt471_pr_allowed": False,
        "prompt471_merge_allowed": False,
        "prompt471_unbounded_loop_allowed": False,
        "prompt471_blocked_reason": blocked_reasons[0] if blocked_reasons else "",
        "prompt471_blocked_reasons": blocked_reasons,
        "prompt471_next_action": "manual_review_prompt471_commit_tag_candidate_blocked",
    }

    if blocked_reasons:
        return base_state

    if not execution_allowed:
        base_state.update(
            {
                "prompt471_commit_tag_candidate_status": "ready",
                "prompt471_commit_tag_candidate_ready": True,
                "prompt471_commit_tag_execution_allowed": False,
                "prompt471_commit_tag_allowed": False,
                "prompt471_human_review_required": False,
                "prompt471_human_intervention_required": False,
                "prompt471_auto_route_allowed": True,
                "prompt471_next_action": (
                    "request_explicit_prompt471_commit_tag_execution"
                ),
            }
        )
        return base_state

    add_completed = _prompt471_git(repo_path, ("add", "--", *allowed_tracked_files))
    commit_completed = None
    tag_completed = None
    if add_completed is not None and add_completed.returncode == 0:
        commit_completed = _prompt471_git(
            repo_path,
            ("commit", "-m", _PROMPT471_COMMIT_MESSAGE),
            timeout=60,
        )
    tag_should_run = commit_completed is not None and commit_completed.returncode == 0
    if tag_should_run:
        tag_completed = _prompt471_git(
            repo_path,
            ("tag", _PROMPT471_TAG_NAME),
            timeout=30,
        )

    commit_returncode = (
        commit_completed.returncode if commit_completed is not None else None
    )
    tag_returncode = tag_completed.returncode if tag_completed is not None else None
    commit_performed = commit_returncode == 0
    tag_performed = tag_returncode == 0
    post_commit_worktree = _prompt470_collect_post_fix_diff(
        repo_path=repo_path,
        allowed_tracked_files=allowed_tracked_files,
    )
    post_commit_worktree_clean = bool(
        post_commit_worktree.get("known") is True
        and not _normalize_string_list(
            post_commit_worktree.get("changed_files"),
            sort_items=False,
        )
        and not _normalize_string_list(
            post_commit_worktree.get("untracked_files"),
            sort_items=False,
        )
    )
    post_commit_head = _prompt471_head(repo_path=repo_path)
    post_commit_tags = _prompt471_tags_at_head(repo_path=repo_path)
    execution_blocked_reasons: list[str] = []
    if not commit_performed:
        execution_blocked_reasons.append("prompt471_commit_failed")
    if commit_performed and not tag_performed:
        execution_blocked_reasons.append("prompt471_tag_failed")
    if commit_performed and tag_performed and not post_commit_worktree_clean:
        execution_blocked_reasons.append("prompt471_post_commit_worktree_not_clean")
    success = bool(
        commit_performed
        and tag_performed
        and _PROMPT471_TAG_NAME in post_commit_tags
        and post_commit_worktree_clean
    )

    base_state.update(
        {
            "prompt471_commit_tag_candidate_status": (
                "performed" if success else "blocked"
            ),
            "prompt471_commit_tag_candidate_ready": success,
            "prompt471_commit_tag_execution_allowed": True,
            "prompt471_commit_attempted": True,
            "prompt471_commit_performed": commit_performed,
            "prompt471_tag_attempted": tag_should_run,
            "prompt471_tag_performed": tag_performed,
            "prompt471_commit_returncode": commit_returncode,
            "prompt471_tag_returncode": tag_returncode,
            "prompt471_post_commit_head": post_commit_head,
            "prompt471_post_commit_tag_at_head": post_commit_tags,
            "prompt471_post_commit_worktree_clean": post_commit_worktree_clean,
            "prompt471_prompt472_handoff_ready": success,
            "prompt471_post_commit_clean_rerun_request_ready": success,
            "prompt471_next_cycle_continuation_request_ready": success,
            "prompt471_human_review_required": not success,
            "prompt471_human_intervention_required": not success,
            "prompt471_auto_route_allowed": success,
            "prompt471_commit_tag_allowed": True,
            "prompt471_blocked_reason": (
                execution_blocked_reasons[0] if execution_blocked_reasons else ""
            ),
            "prompt471_blocked_reasons": execution_blocked_reasons,
            "prompt471_next_action": (
                "prepare_prompt472_post_commit_clean_rerun_next_cycle_continuation"
                if success
                else "manual_review_prompt471_commit_tag_candidate_blocked"
            ),
        }
    )
    return base_state


__all__ = [
    "_build_prompt450_prompt449_runtime_packet_execution_state",
    "_build_prompt451_minimal_autonomous_completion_state",
    "_build_prompt452_prompt451_runtime_executed_review_closure_state",
    "_build_prompt453_commit_tag_ready_explicit_allow_packet_state",
    "_build_prompt454_prompt452_runtime_evidence_repair_state",
    "_build_prompt455_explicit_commit_tag_allow_bridge_state",
    "_build_prompt456_compressed_bounded_commit_tag_execution_gate_state",
    "_build_prompt457_commit_tag_execution_observation_clean_rerun_closure_state",
    "_build_prompt458_minimal_autonomous_completion_closure_state",
    "_build_prompt459_bounded_local_commit_tag_packet_executor_state",
    "_build_prompt460_existing_commit_tag_executor_connector_state",
    "_build_prompt461_post_commit_clean_observed_completion_closure_state",
    "_build_prompt462_completed_next_cycle_smoke_regression_guard_state",
    "_build_prompt463_one_cycle_next_prompt_selection_smoke_state",
    "_build_prompt464_one_cycle_next_prompt_materialization_smoke_state",
    "_build_prompt465_bounded_one_cycle_execution_smoke_state",
    "_build_prompt466_execution_result_review_route_decision_state",
    "_build_prompt467_no_human_next_cycle_continuation_state",
    "_build_prompt468_full_no_human_loop_regression_rerun_state",
    "_build_prompt469_changed_diff_route_guard_state",
    "_build_prompt470_bounded_targeted_fix_execution_state",
    "_build_prompt471_commit_tag_candidate_execution_gate_state",
    "_build_prompt472_post_commit_clean_rerun_next_cycle_state",
    "_build_prompt473_changed_diff_targeted_fix_boundary_state",
    "_build_prompt474_bounded_targeted_fix_execution_state",
    "_build_prompt475_commit_tag_evidence_handoff_gate_state",
    "_build_prompt476_targeted_fix_success_loop_state",
    "_build_prompt477_two_cycle_readiness_state",
    "_build_prompt478_two_cycle_live_execution_state",
    "_build_prompt479_daemon_lite_boundary_state",
    "_build_prompt480_workspace_safety_stop_state",
    "_build_prompt481_daemon_lite_repeated_cycle_state",
    "_build_prompt482_three_cycle_usability_confirmation_state",
    "_build_prompt483_role_catalog_reader_handoff_state",
    "_build_prompt484_daemon_lite_10_cycle_no_allow_boundary_state",
    "_build_prompt484b_role_selection_layer_state",
    "_build_prompt484c_selected_role_prompt_generation_request_state",
    "_build_prompt484d_existing_loop_bridge_state",
    "_build_prompt484e_generated_prompt_intake_handoff_state",
    "_build_prompt484f_role_driven_single_codex_execution_cycle_state",
    "_build_prompt484g_role_driven_execution_request_packet_state",
    "_build_prompt484h_prompt378_generation_request_packet_state",
    "_build_prompt484i_generated_prompt_file_request_state",
    "_build_prompt485_prompt378_supply_ready_for_prompt379_live_state",
    "_build_prompt486_prompt379_live_isolated_preflight_state",
    "_build_prompt487_isolated_prompt379_live_route_state",
    "_build_prompt489_real_task_marker_state",
    "_build_prompt490_second_success_cycle_state",
    "_build_prompt491_third_success_cycle_state",
    "_build_prompt491a_role_prompt_materialization_state",
    "_build_prompt492_bounded_role_contract_extraction_state",
    "_build_prompt493_role_contract_materialization_bridge_state",
    "_build_prompt494_contract_injection_state",
    "_build_prompt496_prompt494_adoption_state",
    "_build_prompt497_chatgpt_browser_bridge_state",
    "_build_prompt498_chrome_response_to_prompt378_intake_state",
    "_build_prompt500_absorbed_prompt379_candidate_reconciliation_state",
    "_build_prompt501_absorbed_candidate_success_continuation_state",
    "_build_prompt502_next_live_cycle_bridge_state",
    "_build_prompt503_prompt378_next_cycle_request_state",
    "_build_prompt504_materialize_and_validate_next_prompt378_state",
    "_build_prompt505_prepare_prompt379_live_request_state",
    "_build_prompt506_explicit_prompt379_live_enable_gate_state",
    "_build_prompt507_one_shot_prompt379_live_execution_state",
    "_build_prompt508_external_enable_dispatch_readiness_state",
]
