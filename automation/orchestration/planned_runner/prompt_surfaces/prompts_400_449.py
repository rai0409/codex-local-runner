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
    _PROMPT400_SCHEMA_VERSION,
    _PROMPT401_SCHEMA_VERSION,
    _PROMPT402_SCHEMA_VERSION,
    _PROMPT403_SCHEMA_VERSION,
    _PROMPT404_SCHEMA_VERSION,
    _PROMPT405_SCHEMA_VERSION,
    _PROMPT406_SCHEMA_VERSION,
    _PROMPT407_SCHEMA_VERSION,
    _PROMPT408_SCHEMA_VERSION,
    _PROMPT409_SCHEMA_VERSION,
    _PROMPT410_SCHEMA_VERSION,
    _PROMPT411_SCHEMA_VERSION,
    _PROMPT412_SCHEMA_VERSION,
    _PROMPT413_SCHEMA_VERSION,
    _PROMPT414_SCHEMA_VERSION,
    _PROMPT415_SCHEMA_VERSION,
    _PROMPT416_SCHEMA_VERSION,
    _PROMPT417_SCHEMA_VERSION,
    _PROMPT418_SCHEMA_VERSION,
    _PROMPT419_SCHEMA_VERSION,
    _PROMPT420_SCHEMA_VERSION,
    _PROMPT421_SCHEMA_VERSION,
    _PROMPT422_SCHEMA_VERSION,
    _PROMPT423_SCHEMA_VERSION,
    _PROMPT424_SCHEMA_VERSION,
    _PROMPT425_SCHEMA_VERSION,
    _PROMPT426_SCHEMA_VERSION,
    _PROMPT427_SCHEMA_VERSION,
    _PROMPT428_SCHEMA_VERSION,
    _PROMPT429_SCHEMA_VERSION,
    _PROMPT430_SCHEMA_VERSION,
    _PROMPT431_SCHEMA_VERSION,
    _PROMPT432_SCHEMA_VERSION,
    _PROMPT433_SCHEMA_VERSION,
    _PROMPT434_SCHEMA_VERSION,
    _PROMPT435_SCHEMA_VERSION,
    _PROMPT436_SCHEMA_VERSION,
    _PROMPT437_SCHEMA_VERSION,
    _PROMPT438_SCHEMA_VERSION,
    _PROMPT439_SCHEMA_VERSION,
    _PROMPT440_SCHEMA_VERSION,
    _PROMPT441_CODEX_COMMAND_ARGV,
    _PROMPT441_SCHEMA_VERSION,
    _PROMPT442_SCHEMA_VERSION,
    _PROMPT443_SCHEMA_VERSION,
    _PROMPT444_SCHEMA_VERSION,
    _PROMPT445_SCHEMA_VERSION,
    _PROMPT446_SCHEMA_VERSION,
    _PROMPT447_SCHEMA_VERSION,
    _PROMPT448_SCHEMA_VERSION,
    _PROMPT449_SCHEMA_VERSION,
    _as_optional_int,
    _extract_explicit_commit_tag_allow_metadata_from_mapping,
    _normalize_prompt437_runtime_command_request,
    _normalize_string_list,
    _normalize_text,
    _prompt416_selected_prompt_text,
    _prompt416_text_sha256,
    _prompt416_validate_relative_path,
    _prompt416_write_materialization_files,
    _prompt417_base_state,
    _prompt417_capture_paths,
    _prompt417_normalize_command,
    _prompt417_normalize_timeout,
    _prompt417_normalize_transport_result,
    _prompt417_returncode_classification,
    _prompt417_validate_prompt_path,
    _prompt417_write_capture_text,
    _prompt417_write_result_json,
    _prompt419_commit_tag_plan_valid,
    _prompt419_run_git_command,
    _prompt419_success_approval_ready,
    _prompt419_write_commit_tag_receipt,
    _prompt420_normalize_cycle_value,
    _prompt420_prompt419_success_loop_packet_ready,
    _prompt421_build_targeted_fix_prompt_text,
    _prompt421_prompt418_targeted_fix_route_ready,
    _prompt421_relative_path_valid,
    _prompt422_normalize_command,
    _prompt422_normalize_timeout_seconds,
    _prompt422_prompt421_execution_packet_ready,
    _prompt422_result_json_payload,
    _prompt422_targeted_fix_prompt_path_valid,
    _prompt423_normalize_attempt,
    _prompt423_prompt422_review_packet_ready,
    _prompt424_normalize_cycle_value,
    _prompt427_int_like,
    _prompt440_live_command_allowlisted,
    _prompt440_normalize_timeout_seconds,
    _prompt441_codex_command_allowlisted,
    _prompt444_retry_value,
    _prompt444_summary_metadata_available,
    _prompt444_targeted_fix_prompt_artifact_path,
    _prompt445_prompt_content_summary,
    _prompt445_prompt_inputs_summary,
    _prompt446_prompt_body_preview,
    _prompt446_prompt_body_summary,
    _prompt446_retry_value,
    _prompt447_any_explicit_flag,
    _prompt447_materialize_prompt_artifact,
    _prompt447_retry_value,
    _prompt447_runtime_command_json,
    _prompt447_targeted_fix_prompt_body,
    _prompt448_mark_blocked_no_candidates,
    _prompt448_retry_value,
    _prompt448_runtime_command_json,
    _prompt449_mark_blocked,
    _prompt449_materialize_prompt_artifact,
    _prompt449_retry_value,
    _prompt449_runtime_command_json,
    _prompt449_targeted_fix_prompt_body,
    _write_json,
)

def _build_prompt400_relaxed_next_cycle_handoff_bridge_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    run_state = dict(run_state_payload or {})

    prompt398_status_accepted = (
        _normalize_text(
            run_state.get("prompt398_committed_prompt379_result_status"),
            default="",
        )
        == "accepted"
    )
    prompt398_accepted = bool(
        run_state.get("prompt398_committed_prompt379_accepted", False)
    )
    prompt399_alternate_evidence_ready = bool(
        run_state.get("prompt399_committed_result_alternate_evidence_ready", False)
    )
    prompt399_observation_accepted = (
        _normalize_text(
            run_state.get("prompt399_relaxed_observation_status"),
            default="",
        )
        == "accepted"
    )
    prompt399_handoff_ready = bool(
        run_state.get("prompt399_relaxed_next_cycle_handoff_ready", False)
    )
    prompt399_observation_ready = bool(
        run_state.get("prompt399_relaxed_end_to_end_observation_ready", False)
    )

    required_inputs: tuple[tuple[str, bool], ...] = (
        (
            "prompt398_committed_prompt379_result_status_not_accepted",
            prompt398_status_accepted,
        ),
        ("prompt398_committed_prompt379_accepted_false", prompt398_accepted),
        (
            "prompt399_committed_result_alternate_evidence_not_ready",
            prompt399_alternate_evidence_ready,
        ),
        (
            "prompt399_relaxed_observation_status_not_accepted",
            prompt399_observation_accepted,
        ),
        (
            "prompt399_relaxed_next_cycle_handoff_not_ready",
            prompt399_handoff_ready,
        ),
        (
            "prompt399_relaxed_end_to_end_observation_not_ready",
            prompt399_observation_ready,
        ),
    )
    blocked_reasons = [
        reason for reason, input_ready in required_inputs if not input_ready
    ]
    bridge_ready = not blocked_reasons
    relaxed_bypassed_strict_gates = ["prompt381", "prompt385", "prompt389", "prompt390"]
    gates_applied = list(relaxed_bypassed_strict_gates) if bridge_ready else []
    gates_not_applied = [] if bridge_ready else list(relaxed_bypassed_strict_gates)
    strict_reenable_next_gate = _normalize_text(
        run_state.get("prompt399_strict_reenable_next_gate"),
        default="worktree clean",
    )

    return {
        "prompt400_schema_version": _PROMPT400_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt400",
        "prompt400_relaxed_handoff_bridge_enabled": bridge_ready,
        "prompt400_relaxed_handoff_bridge_status": (
            "accepted" if bridge_ready else "blocked"
        ),
        "prompt400_relaxed_handoff_bridge_blocked_reason": (
            blocked_reasons[0] if blocked_reasons else ""
        ),
        "prompt400_relaxed_handoff_bridge_blocked_reasons": blocked_reasons,
        "prompt400_relaxed_handoff_input_prompt398_accepted": bool(
            prompt398_status_accepted and prompt398_accepted
        ),
        "prompt400_relaxed_handoff_input_prompt399_accepted": bool(
            prompt399_alternate_evidence_ready
            and prompt399_observation_accepted
            and prompt399_handoff_ready
            and prompt399_observation_ready
        ),
        "prompt400_relaxed_handoff_prompt381_strict_block_allowed": bridge_ready,
        "prompt400_relaxed_handoff_prompt385_bridge_ready": bridge_ready,
        "prompt400_relaxed_handoff_prompt389_bridge_ready": bridge_ready,
        "prompt400_relaxed_handoff_prompt390_bridge_ready": bridge_ready,
        "prompt400_relaxed_handoff_gates_applied": gates_applied,
        "prompt400_relaxed_handoff_gates_not_applied": gates_not_applied,
        "prompt400_relaxed_next_cycle_ready": bridge_ready,
        "prompt400_relaxed_next_cycle_observation_ready": bridge_ready,
        "prompt400_relaxed_next_action": (
            "prepare_prompt401_next_prompt_selection_from_relaxed_handoff"
            if bridge_ready
            else "wait_for_prompt399_accepted_relaxed_observation_evidence"
        ),
        "prompt400_remaining_strict_blocked_gates": _normalize_string_list(
            run_state.get("prompt399_all_blocked_gates"),
            sort_items=False,
        ),
        "prompt400_remaining_strict_false_gate_fields": _normalize_string_list(
            run_state.get("prompt399_all_false_gate_fields"),
            sort_items=False,
        ),
        "prompt400_relaxed_bypassed_strict_gates": relaxed_bypassed_strict_gates,
        "prompt400_strict_reenable_next_gate": strict_reenable_next_gate,
    }

def _build_prompt401_next_prompt_selection_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    run_state = dict(run_state_payload or {})
    input_bridge_status = _normalize_text(
        run_state.get("prompt400_relaxed_handoff_bridge_status"),
        default="",
    )
    input_next_cycle_ready = bool(
        run_state.get("prompt400_relaxed_next_cycle_ready", False)
    )
    input_observation_ready = bool(
        run_state.get("prompt400_relaxed_next_cycle_observation_ready", False)
    )
    input_next_action = _normalize_text(
        run_state.get("prompt400_relaxed_next_action"),
        default="",
    )

    required_inputs: tuple[tuple[str, bool], ...] = (
        (
            "prompt400_relaxed_handoff_bridge_status_not_accepted",
            input_bridge_status == "accepted",
        ),
        ("prompt400_relaxed_next_cycle_not_ready", input_next_cycle_ready),
        (
            "prompt400_relaxed_next_cycle_observation_not_ready",
            input_observation_ready,
        ),
        (
            "prompt400_relaxed_next_action_not_prepare_prompt401_next_prompt_selection_from_relaxed_handoff",
            input_next_action
            == "prepare_prompt401_next_prompt_selection_from_relaxed_handoff",
        ),
    )
    blocked_reasons = [
        reason for reason, input_ready in required_inputs if not input_ready
    ]
    selection_enabled = not blocked_reasons

    return {
        "prompt401_schema_version": _PROMPT401_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt401",
        "prompt401_next_prompt_selection_enabled": selection_enabled,
        "prompt401_next_prompt_selection_status": (
            "selected" if selection_enabled else "blocked"
        ),
        "prompt401_next_prompt_selection_blocked_reason": (
            blocked_reasons[0] if blocked_reasons else ""
        ),
        "prompt401_next_prompt_selection_blocked_reasons": blocked_reasons,
        "prompt401_input_prompt400_relaxed_handoff_bridge_status": input_bridge_status,
        "prompt401_input_prompt400_relaxed_next_cycle_ready": input_next_cycle_ready,
        "prompt401_input_prompt400_relaxed_next_cycle_observation_ready": (
            input_observation_ready
        ),
        "prompt401_input_prompt400_relaxed_next_action": input_next_action,
        "prompt401_selected_next_prompt_id": "prompt402" if selection_enabled else "",
        "prompt401_selected_next_prompt_title": (
            "generate_selected_next_prompt_from_relaxed_handoff"
            if selection_enabled
            else ""
        ),
        "prompt401_selected_next_prompt_objective": (
            "create a metadata-only generated-prompt surface for the selected next prompt using Prompt400 relaxed handoff evidence"
            if selection_enabled
            else ""
        ),
        "prompt401_selected_next_prompt_action": (
            "prepare_prompt402_generated_prompt_surface" if selection_enabled else ""
        ),
        "prompt401_selected_next_prompt_reason": (
            "prompt400_relaxed_handoff_ready_requires_next_prompt_generation_surface"
            if selection_enabled
            else ""
        ),
        "prompt401_selection_source": (
            "prompt400_relaxed_handoff" if selection_enabled else ""
        ),
        "prompt401_selection_confidence": "high" if selection_enabled else "none",
        "prompt401_next_action": (
            "prepare_prompt402_generated_prompt_surface"
            if selection_enabled
            else "wait_for_prompt400_relaxed_handoff"
        ),
    }

def _build_prompt402_generated_prompt_surface_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    run_state = dict(run_state_payload or {})
    input_selection_status = _normalize_text(
        run_state.get("prompt401_next_prompt_selection_status"),
        default="",
    )
    input_selected_next_prompt_id = _normalize_text(
        run_state.get("prompt401_selected_next_prompt_id"),
        default="",
    )
    input_selected_next_prompt_action = _normalize_text(
        run_state.get("prompt401_selected_next_prompt_action"),
        default="",
    )
    input_selection_source = _normalize_text(
        run_state.get("prompt401_selection_source"),
        default="",
    )
    input_selection_confidence = _normalize_text(
        run_state.get("prompt401_selection_confidence"),
        default="",
    )

    required_inputs: tuple[tuple[str, bool], ...] = (
        (
            "prompt401_next_prompt_selection_status_not_selected",
            input_selection_status == "selected",
        ),
        (
            "prompt401_selected_next_prompt_id_not_prompt402",
            input_selected_next_prompt_id == "prompt402",
        ),
        (
            "prompt401_selected_next_prompt_action_not_prepare_prompt402_generated_prompt_surface",
            input_selected_next_prompt_action
            == "prepare_prompt402_generated_prompt_surface",
        ),
        (
            "prompt401_selection_source_not_prompt400_relaxed_handoff",
            input_selection_source == "prompt400_relaxed_handoff",
        ),
        (
            "prompt401_selection_confidence_not_high",
            input_selection_confidence == "high",
        ),
    )
    blocked_reasons = [
        reason for reason, input_ready in required_inputs if not input_ready
    ]
    surface_ready = not blocked_reasons

    generated_prompt_required_inputs = [
        "prompt400_relaxed_handoff_bridge_status='accepted'",
        "prompt400_relaxed_next_cycle_ready=True",
        "prompt401_next_prompt_selection_status='selected'",
        "prompt401_selected_next_prompt_id='prompt402'",
    ]
    generated_prompt_required_outputs = [
        "prompt402_generated_prompt_ready=True",
        "prompt402_selected_prompt_execution_handoff_ready=True",
        "prompt402_next_action='prepare_prompt403_selected_prompt_dry_run_handoff'",
    ]
    generated_prompt_prohibited_actions = [
        "Codex invocation",
        "Prompt402 execution",
        "live execution",
        "git stage/commit/tag/push",
        "remote/GitHub operations",
        "generated artifact mutation",
        "scripts/run_planned_execution.py modification",
        "tests/docs/README/workflow modifications",
        "strict gate fabrication",
    ]
    generated_prompt_acceptance_criteria = [
        "source compiles",
        "clean dry-run exposes prompt402_generated_prompt_surface_status='ready'",
        "strict Prompt381/385/389/390 fields may remain blocked/false",
        "no Codex invocation, Prompt402 execution, prompt file creation, or git mutation",
    ]

    return {
        "prompt402_schema_version": _PROMPT402_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt402",
        "prompt402_generated_prompt_surface_enabled": surface_ready,
        "prompt402_generated_prompt_surface_status": (
            "ready" if surface_ready else "blocked"
        ),
        "prompt402_generated_prompt_surface_blocked_reason": (
            blocked_reasons[0] if blocked_reasons else ""
        ),
        "prompt402_generated_prompt_surface_blocked_reasons": blocked_reasons,
        "prompt402_input_prompt401_selection_status": input_selection_status,
        "prompt402_input_prompt401_selected_next_prompt_id": (
            input_selected_next_prompt_id
        ),
        "prompt402_input_prompt401_selected_next_prompt_action": (
            input_selected_next_prompt_action
        ),
        "prompt402_input_prompt401_selection_source": input_selection_source,
        "prompt402_input_prompt401_selection_confidence": input_selection_confidence,
        "prompt402_generated_prompt_id": "prompt402" if surface_ready else "",
        "prompt402_generated_prompt_title": (
            "generate_selected_next_prompt_from_relaxed_handoff"
            if surface_ready
            else ""
        ),
        "prompt402_generated_prompt_source": (
            "prompt401_selected_next_prompt" if surface_ready else ""
        ),
        "prompt402_generated_prompt_mode": "metadata_only" if surface_ready else "",
        "prompt402_generated_prompt_objective": (
            "create a metadata-only generated-prompt surface for the selected next prompt using Prompt400 relaxed handoff evidence"
            if surface_ready
            else ""
        ),
        "prompt402_generated_prompt_required_inputs": (
            generated_prompt_required_inputs if surface_ready else []
        ),
        "prompt402_generated_prompt_required_outputs": (
            generated_prompt_required_outputs if surface_ready else []
        ),
        "prompt402_generated_prompt_prohibited_actions": (
            generated_prompt_prohibited_actions if surface_ready else []
        ),
        "prompt402_generated_prompt_acceptance_criteria": (
            generated_prompt_acceptance_criteria if surface_ready else []
        ),
        "prompt402_generated_prompt_ready": surface_ready,
        "prompt402_selected_prompt_execution_handoff_ready": surface_ready,
        "prompt402_next_action": (
            "prepare_prompt403_selected_prompt_dry_run_handoff"
            if surface_ready
            else "wait_for_prompt401_next_prompt_selection"
        ),
    }

def _build_prompt403_selected_prompt_dry_run_handoff_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    run_state = dict(run_state_payload or {})
    input_surface_status = _normalize_text(
        run_state.get("prompt402_generated_prompt_surface_status"),
        default="",
    )
    input_generated_prompt_ready = bool(
        run_state.get("prompt402_generated_prompt_ready", False)
    )
    input_execution_handoff_ready = bool(
        run_state.get("prompt402_selected_prompt_execution_handoff_ready", False)
    )
    input_generated_prompt_id = _normalize_text(
        run_state.get("prompt402_generated_prompt_id"),
        default="",
    )
    input_generated_prompt_mode = _normalize_text(
        run_state.get("prompt402_generated_prompt_mode"),
        default="",
    )
    input_next_action = _normalize_text(
        run_state.get("prompt402_next_action"),
        default="",
    )

    required_inputs: tuple[tuple[str, bool], ...] = (
        (
            "prompt402_generated_prompt_surface_status_not_ready",
            input_surface_status == "ready",
        ),
        (
            "prompt402_generated_prompt_ready_false",
            input_generated_prompt_ready,
        ),
        (
            "prompt402_selected_prompt_execution_handoff_ready_false",
            input_execution_handoff_ready,
        ),
        (
            "prompt402_generated_prompt_id_not_prompt402",
            input_generated_prompt_id == "prompt402",
        ),
        (
            "prompt402_generated_prompt_mode_not_metadata_only",
            input_generated_prompt_mode == "metadata_only",
        ),
        (
            "prompt402_next_action_not_prepare_prompt403_selected_prompt_dry_run_handoff",
            input_next_action == "prepare_prompt403_selected_prompt_dry_run_handoff",
        ),
    )
    blocked_reasons = [
        reason for reason, input_ready in required_inputs if not input_ready
    ]
    handoff_ready = not blocked_reasons

    return {
        "prompt403_schema_version": _PROMPT403_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt403",
        "prompt403_selected_prompt_dry_run_handoff_enabled": handoff_ready,
        "prompt403_selected_prompt_dry_run_handoff_status": (
            "ready" if handoff_ready else "blocked"
        ),
        "prompt403_selected_prompt_dry_run_handoff_blocked_reason": (
            blocked_reasons[0] if blocked_reasons else ""
        ),
        "prompt403_selected_prompt_dry_run_handoff_blocked_reasons": blocked_reasons,
        "prompt403_input_prompt402_generated_prompt_surface_status": (
            input_surface_status
        ),
        "prompt403_input_prompt402_generated_prompt_ready": input_generated_prompt_ready,
        "prompt403_input_prompt402_selected_prompt_execution_handoff_ready": (
            input_execution_handoff_ready
        ),
        "prompt403_input_prompt402_generated_prompt_id": input_generated_prompt_id,
        "prompt403_input_prompt402_generated_prompt_mode": input_generated_prompt_mode,
        "prompt403_input_prompt402_next_action": input_next_action,
        "prompt403_selected_prompt_id": "prompt402" if handoff_ready else "",
        "prompt403_selected_prompt_source": (
            "prompt402_generated_prompt_surface" if handoff_ready else ""
        ),
        "prompt403_selected_prompt_execution_mode": (
            "dry_run" if handoff_ready else ""
        ),
        "prompt403_selected_prompt_execution_ready": handoff_ready,
        "prompt403_selected_prompt_execution_attempted": False,
        "prompt403_selected_prompt_execution_performed": False,
        "prompt403_selected_prompt_live_execution_allowed": False,
        "prompt403_selected_prompt_physical_prompt_required": False,
        "prompt403_selected_prompt_result_review_ready": False,
        "prompt403_next_action": (
            "prepare_prompt404_selected_prompt_result_review"
            if handoff_ready
            else "wait_for_prompt402_generated_prompt_surface"
        ),
    }

def _build_prompt404_selected_prompt_handoff_review_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    run_state = dict(run_state_payload or {})
    input_handoff_status = _normalize_text(
        run_state.get("prompt403_selected_prompt_dry_run_handoff_status"),
        default="",
    )
    input_selected_prompt_id = _normalize_text(
        run_state.get("prompt403_selected_prompt_id"),
        default="",
    )
    input_execution_mode = _normalize_text(
        run_state.get("prompt403_selected_prompt_execution_mode"),
        default="",
    )
    input_execution_ready = bool(
        run_state.get("prompt403_selected_prompt_execution_ready", False)
    )
    input_execution_attempted = bool(
        run_state.get("prompt403_selected_prompt_execution_attempted", False)
    )
    input_execution_performed = bool(
        run_state.get("prompt403_selected_prompt_execution_performed", False)
    )
    input_live_execution_allowed = bool(
        run_state.get("prompt403_selected_prompt_live_execution_allowed", False)
    )
    input_next_action = _normalize_text(
        run_state.get("prompt403_next_action"),
        default="",
    )

    required_inputs: tuple[tuple[str, bool], ...] = (
        (
            "prompt403_selected_prompt_dry_run_handoff_status_not_ready",
            input_handoff_status == "ready",
        ),
        (
            "prompt403_selected_prompt_execution_ready_false",
            input_execution_ready,
        ),
        (
            "prompt403_selected_prompt_execution_mode_not_dry_run",
            input_execution_mode == "dry_run",
        ),
        (
            "prompt403_selected_prompt_id_not_prompt402",
            input_selected_prompt_id == "prompt402",
        ),
        (
            "prompt403_selected_prompt_execution_attempted_true",
            not input_execution_attempted,
        ),
        (
            "prompt403_selected_prompt_execution_performed_true",
            not input_execution_performed,
        ),
        (
            "prompt403_selected_prompt_live_execution_allowed_true",
            not input_live_execution_allowed,
        ),
        (
            "prompt403_next_action_not_prepare_prompt404_selected_prompt_result_review",
            input_next_action == "prepare_prompt404_selected_prompt_result_review",
        ),
    )
    blocked_reasons = [
        reason for reason, input_ready in required_inputs if not input_ready
    ]
    review_ready = not blocked_reasons

    return {
        "prompt404_schema_version": _PROMPT404_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt404",
        "prompt404_selected_prompt_handoff_review_enabled": review_ready,
        "prompt404_selected_prompt_handoff_review_status": (
            "reviewed" if review_ready else "blocked"
        ),
        "prompt404_selected_prompt_handoff_review_blocked_reason": (
            blocked_reasons[0] if blocked_reasons else ""
        ),
        "prompt404_selected_prompt_handoff_review_blocked_reasons": blocked_reasons,
        "prompt404_input_prompt403_handoff_status": input_handoff_status,
        "prompt404_input_prompt403_selected_prompt_id": input_selected_prompt_id,
        "prompt404_input_prompt403_execution_mode": input_execution_mode,
        "prompt404_input_prompt403_execution_ready": input_execution_ready,
        "prompt404_input_prompt403_execution_attempted": input_execution_attempted,
        "prompt404_input_prompt403_execution_performed": input_execution_performed,
        "prompt404_input_prompt403_live_execution_allowed": (
            input_live_execution_allowed
        ),
        "prompt404_input_prompt403_next_action": input_next_action,
        "prompt404_selected_prompt_result_review_status": (
            "reviewed" if review_ready else "blocked"
        ),
        "prompt404_selected_prompt_execution_classification": (
            "not_executed_handoff_ready" if review_ready else ""
        ),
        "prompt404_selected_prompt_review_route": (
            "ready_for_selected_prompt_execution_planning" if review_ready else ""
        ),
        "prompt404_selected_prompt_review_ready": review_ready,
        "prompt404_selected_prompt_execution_plan_ready": review_ready,
        "prompt404_selected_prompt_approval_candidate": False,
        "prompt404_selected_prompt_fix_required": False,
        "prompt404_selected_prompt_retry_required": False,
        "prompt404_selected_prompt_commit_tag_allowed": False,
        "prompt404_next_action": (
            "prepare_prompt405_selected_prompt_execution_plan"
            if review_ready
            else "wait_for_prompt403_selected_prompt_dry_run_handoff"
        ),
    }

def _build_prompt405_selected_prompt_execution_plan_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    run_state = dict(run_state_payload or {})
    input_handoff_review_status = _normalize_text(
        run_state.get("prompt404_selected_prompt_handoff_review_status"),
        default="",
    )
    input_result_review_status = _normalize_text(
        run_state.get("prompt404_selected_prompt_result_review_status"),
        default="",
    )
    input_execution_classification = _normalize_text(
        run_state.get("prompt404_selected_prompt_execution_classification"),
        default="",
    )
    input_review_route = _normalize_text(
        run_state.get("prompt404_selected_prompt_review_route"),
        default="",
    )
    input_review_ready = bool(
        run_state.get("prompt404_selected_prompt_review_ready", False)
    )
    input_execution_plan_ready = bool(
        run_state.get("prompt404_selected_prompt_execution_plan_ready", False)
    )
    input_approval_candidate = bool(
        run_state.get("prompt404_selected_prompt_approval_candidate", False)
    )
    input_commit_tag_allowed = bool(
        run_state.get("prompt404_selected_prompt_commit_tag_allowed", False)
    )
    input_next_action = _normalize_text(
        run_state.get("prompt404_next_action"),
        default="",
    )

    required_inputs: tuple[tuple[str, bool], ...] = (
        (
            "prompt404_selected_prompt_handoff_review_status_not_reviewed",
            input_handoff_review_status == "reviewed",
        ),
        (
            "prompt404_selected_prompt_result_review_status_not_reviewed",
            input_result_review_status == "reviewed",
        ),
        (
            "prompt404_selected_prompt_execution_classification_not_not_executed_handoff_ready",
            input_execution_classification == "not_executed_handoff_ready",
        ),
        (
            "prompt404_selected_prompt_review_route_not_ready_for_selected_prompt_execution_planning",
            input_review_route == "ready_for_selected_prompt_execution_planning",
        ),
        (
            "prompt404_selected_prompt_review_ready_false",
            input_review_ready,
        ),
        (
            "prompt404_selected_prompt_execution_plan_ready_false",
            input_execution_plan_ready,
        ),
        (
            "prompt404_selected_prompt_approval_candidate_true",
            not input_approval_candidate,
        ),
        (
            "prompt404_selected_prompt_commit_tag_allowed_true",
            not input_commit_tag_allowed,
        ),
        (
            "prompt404_next_action_not_prepare_prompt405_selected_prompt_execution_plan",
            input_next_action == "prepare_prompt405_selected_prompt_execution_plan",
        ),
    )
    blocked_reasons = [
        reason for reason, input_ready in required_inputs if not input_ready
    ]
    plan_ready = not blocked_reasons

    return {
        "prompt405_schema_version": _PROMPT405_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt405",
        "prompt405_selected_prompt_execution_plan_enabled": plan_ready,
        "prompt405_selected_prompt_execution_plan_status": (
            "ready" if plan_ready else "blocked"
        ),
        "prompt405_selected_prompt_execution_plan_blocked_reason": (
            blocked_reasons[0] if blocked_reasons else ""
        ),
        "prompt405_selected_prompt_execution_plan_blocked_reasons": blocked_reasons,
        "prompt405_input_prompt404_handoff_review_status": (
            input_handoff_review_status
        ),
        "prompt405_input_prompt404_result_review_status": input_result_review_status,
        "prompt405_input_prompt404_execution_classification": (
            input_execution_classification
        ),
        "prompt405_input_prompt404_review_route": input_review_route,
        "prompt405_input_prompt404_review_ready": input_review_ready,
        "prompt405_input_prompt404_execution_plan_ready": input_execution_plan_ready,
        "prompt405_input_prompt404_approval_candidate": input_approval_candidate,
        "prompt405_input_prompt404_commit_tag_allowed": input_commit_tag_allowed,
        "prompt405_input_prompt404_next_action": input_next_action,
        "prompt405_selected_prompt_id": "prompt402" if plan_ready else "",
        "prompt405_selected_prompt_source": (
            "prompt404_handoff_review" if plan_ready else ""
        ),
        "prompt405_selected_prompt_execution_mode": "dry_run" if plan_ready else "",
        "prompt405_selected_prompt_execution_plan_ready": plan_ready,
        "prompt405_selected_prompt_execution_allowed": False,
        "prompt405_selected_prompt_execution_requires_explicit_enable": True,
        "prompt405_selected_prompt_execution_attempted": False,
        "prompt405_selected_prompt_execution_performed": False,
        "prompt405_selected_prompt_live_execution_allowed": False,
        "prompt405_selected_prompt_commit_tag_allowed": False,
        "prompt405_selected_prompt_plan_classification": (
            "dry_run_plan_ready_not_executed" if plan_ready else ""
        ),
        "prompt405_selected_prompt_plan_route": (
            "ready_for_bounded_loop_observation" if plan_ready else ""
        ),
        "prompt405_next_action": (
            "prepare_prompt406_bounded_loop_observation"
            if plan_ready
            else "wait_for_prompt404_selected_prompt_handoff_review"
        ),
    }

def _build_prompt406_bounded_loop_observation_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    run_state = dict(run_state_payload or {})
    input_execution_plan_status = _normalize_text(
        run_state.get("prompt405_selected_prompt_execution_plan_status"),
        default="",
    )
    input_execution_plan_ready = bool(
        run_state.get("prompt405_selected_prompt_execution_plan_ready", False)
    )
    input_execution_mode = _normalize_text(
        run_state.get("prompt405_selected_prompt_execution_mode"),
        default="",
    )
    input_execution_allowed = bool(
        run_state.get("prompt405_selected_prompt_execution_allowed", False)
    )
    input_execution_requires_explicit_enable = bool(
        run_state.get(
            "prompt405_selected_prompt_execution_requires_explicit_enable",
            False,
        )
    )
    input_execution_attempted = bool(
        run_state.get("prompt405_selected_prompt_execution_attempted", False)
    )
    input_execution_performed = bool(
        run_state.get("prompt405_selected_prompt_execution_performed", False)
    )
    input_live_execution_allowed = bool(
        run_state.get("prompt405_selected_prompt_live_execution_allowed", False)
    )
    input_commit_tag_allowed = bool(
        run_state.get("prompt405_selected_prompt_commit_tag_allowed", False)
    )
    input_plan_classification = _normalize_text(
        run_state.get("prompt405_selected_prompt_plan_classification"),
        default="",
    )
    input_plan_route = _normalize_text(
        run_state.get("prompt405_selected_prompt_plan_route"),
        default="",
    )
    input_next_action = _normalize_text(
        run_state.get("prompt405_next_action"),
        default="",
    )

    required_inputs: tuple[tuple[str, bool], ...] = (
        (
            "prompt405_selected_prompt_execution_plan_status_not_ready",
            input_execution_plan_status == "ready",
        ),
        (
            "prompt405_selected_prompt_execution_plan_ready_false",
            input_execution_plan_ready,
        ),
        (
            "prompt405_selected_prompt_execution_mode_not_dry_run",
            input_execution_mode == "dry_run",
        ),
        (
            "prompt405_selected_prompt_execution_allowed_true",
            not input_execution_allowed,
        ),
        (
            "prompt405_selected_prompt_execution_requires_explicit_enable_false",
            input_execution_requires_explicit_enable,
        ),
        (
            "prompt405_selected_prompt_execution_attempted_true",
            not input_execution_attempted,
        ),
        (
            "prompt405_selected_prompt_execution_performed_true",
            not input_execution_performed,
        ),
        (
            "prompt405_selected_prompt_live_execution_allowed_true",
            not input_live_execution_allowed,
        ),
        (
            "prompt405_selected_prompt_commit_tag_allowed_true",
            not input_commit_tag_allowed,
        ),
        (
            "prompt405_selected_prompt_plan_classification_not_dry_run_plan_ready_not_executed",
            input_plan_classification == "dry_run_plan_ready_not_executed",
        ),
        (
            "prompt405_selected_prompt_plan_route_not_ready_for_bounded_loop_observation",
            input_plan_route == "ready_for_bounded_loop_observation",
        ),
        (
            "prompt405_next_action_not_prepare_prompt406_bounded_loop_observation",
            input_next_action == "prepare_prompt406_bounded_loop_observation",
        ),
    )
    blocked_reasons = [
        reason for reason, input_ready in required_inputs if not input_ready
    ]
    observation_allowed = not blocked_reasons
    completed_chain = [
        "prompt398_committed_result_evidence",
        "prompt399_relaxed_observation",
        "prompt400_relaxed_handoff",
        "prompt401_next_prompt_selection",
        "prompt402_generated_prompt_surface",
        "prompt403_selected_prompt_dry_run_handoff",
        "prompt404_selected_prompt_handoff_review",
        "prompt405_selected_prompt_execution_plan",
    ]
    remaining_strict_blocked_gates = [
        "prompt381",
        "prompt385",
        "prompt389",
        "prompt390",
    ]
    remaining_strict_false_gate_fields = [
        "prompt381_prompt380_approve_candidate",
        "prompt381_approve_candidate_ready",
        "prompt385_next_cycle_handoff_ready",
        "prompt389_repeated_cycle_execution_gate_ready",
        "prompt389_repeated_cycle_execution_allowed",
        "prompt390_enabled_run_ready",
    ]

    return {
        "prompt406_schema_version": _PROMPT406_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt406",
        "prompt406_bounded_loop_observation_enabled": observation_allowed,
        "prompt406_bounded_loop_observation_status": (
            "observed" if observation_allowed else "blocked"
        ),
        "prompt406_bounded_loop_observation_blocked_reason": (
            blocked_reasons[0] if blocked_reasons else ""
        ),
        "prompt406_bounded_loop_observation_blocked_reasons": blocked_reasons,
        "prompt406_input_prompt405_execution_plan_status": (
            input_execution_plan_status
        ),
        "prompt406_input_prompt405_execution_plan_ready": input_execution_plan_ready,
        "prompt406_input_prompt405_execution_mode": input_execution_mode,
        "prompt406_input_prompt405_execution_allowed": input_execution_allowed,
        "prompt406_input_prompt405_execution_requires_explicit_enable": (
            input_execution_requires_explicit_enable
        ),
        "prompt406_input_prompt405_execution_attempted": input_execution_attempted,
        "prompt406_input_prompt405_execution_performed": input_execution_performed,
        "prompt406_input_prompt405_live_execution_allowed": (
            input_live_execution_allowed
        ),
        "prompt406_input_prompt405_commit_tag_allowed": input_commit_tag_allowed,
        "prompt406_input_prompt405_plan_classification": input_plan_classification,
        "prompt406_input_prompt405_plan_route": input_plan_route,
        "prompt406_input_prompt405_next_action": input_next_action,
        "prompt406_relaxed_local_loop_observed": observation_allowed,
        "prompt406_relaxed_local_loop_observation_mode": (
            "metadata_only" if observation_allowed else ""
        ),
        "prompt406_relaxed_local_loop_execution_scope": (
            "local_only" if observation_allowed else ""
        ),
        "prompt406_relaxed_local_loop_execution_type": (
            "dry_run_plan_observation" if observation_allowed else ""
        ),
        "prompt406_relaxed_local_loop_actual_execution_performed": False,
        "prompt406_relaxed_local_loop_codex_invoked": False,
        "prompt406_relaxed_local_loop_git_mutation_allowed": False,
        "prompt406_relaxed_local_loop_commit_tag_allowed": False,
        "prompt406_relaxed_local_loop_strict_gates_reenabled": False,
        "prompt406_relaxed_local_loop_completion_candidate": observation_allowed,
        "prompt406_relaxed_local_loop_completed_chain": (
            completed_chain if observation_allowed else []
        ),
        "prompt406_remaining_strict_blocked_gates": remaining_strict_blocked_gates,
        "prompt406_remaining_strict_false_gate_fields": (
            remaining_strict_false_gate_fields
        ),
        "prompt406_relaxed_bypassed_strict_gates": remaining_strict_blocked_gates,
        "prompt406_strict_reenable_required": True,
        "prompt406_strict_reenable_next_gate": (
            "prompt407_relaxed_loop_completion_receipt"
        ),
        "prompt406_next_action": (
            "prepare_prompt407_relaxed_loop_completion_receipt"
            if observation_allowed
            else "wait_for_prompt405_selected_prompt_execution_plan"
        ),
    }

def _build_prompt407_relaxed_loop_completion_receipt_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    run_state = dict(run_state_payload or {})
    input_observation_status = _normalize_text(
        run_state.get("prompt406_bounded_loop_observation_status"),
        default="",
    )
    input_loop_observed = bool(
        run_state.get("prompt406_relaxed_local_loop_observed", False)
    )
    input_observation_mode = _normalize_text(
        run_state.get("prompt406_relaxed_local_loop_observation_mode"),
        default="",
    )
    input_execution_scope = _normalize_text(
        run_state.get("prompt406_relaxed_local_loop_execution_scope"),
        default="",
    )
    input_execution_type = _normalize_text(
        run_state.get("prompt406_relaxed_local_loop_execution_type"),
        default="",
    )
    input_actual_execution_performed = bool(
        run_state.get("prompt406_relaxed_local_loop_actual_execution_performed", False)
    )
    input_codex_invoked = bool(
        run_state.get("prompt406_relaxed_local_loop_codex_invoked", False)
    )
    input_git_mutation_allowed = bool(
        run_state.get("prompt406_relaxed_local_loop_git_mutation_allowed", False)
    )
    input_commit_tag_allowed = bool(
        run_state.get("prompt406_relaxed_local_loop_commit_tag_allowed", False)
    )
    input_strict_gates_reenabled = bool(
        run_state.get("prompt406_relaxed_local_loop_strict_gates_reenabled", False)
    )
    input_completion_candidate = bool(
        run_state.get("prompt406_relaxed_local_loop_completion_candidate", False)
    )
    input_strict_reenable_required = bool(
        run_state.get("prompt406_strict_reenable_required", False)
    )
    input_strict_reenable_next_gate = _normalize_text(
        run_state.get("prompt406_strict_reenable_next_gate"),
        default="",
    )
    input_next_action = _normalize_text(
        run_state.get("prompt406_next_action"),
        default="",
    )

    completed_chain_expected = [
        "prompt398_committed_result_evidence",
        "prompt399_relaxed_observation",
        "prompt400_relaxed_handoff",
        "prompt401_next_prompt_selection",
        "prompt402_generated_prompt_surface",
        "prompt403_selected_prompt_dry_run_handoff",
        "prompt404_selected_prompt_handoff_review",
        "prompt405_selected_prompt_execution_plan",
    ]
    completed_chain_observed = _normalize_string_list(
        run_state.get("prompt406_relaxed_local_loop_completed_chain"),
        sort_items=False,
    )
    completed_chain_verified = completed_chain_observed == completed_chain_expected

    required_inputs: tuple[tuple[str, bool], ...] = (
        (
            "prompt406_bounded_loop_observation_status_not_observed",
            input_observation_status == "observed",
        ),
        (
            "prompt406_relaxed_local_loop_observed_false",
            input_loop_observed,
        ),
        (
            "prompt406_relaxed_local_loop_observation_mode_not_metadata_only",
            input_observation_mode == "metadata_only",
        ),
        (
            "prompt406_relaxed_local_loop_execution_scope_not_local_only",
            input_execution_scope == "local_only",
        ),
        (
            "prompt406_relaxed_local_loop_execution_type_not_dry_run_plan_observation",
            input_execution_type == "dry_run_plan_observation",
        ),
        (
            "prompt406_relaxed_local_loop_actual_execution_performed_true",
            not input_actual_execution_performed,
        ),
        (
            "prompt406_relaxed_local_loop_codex_invoked_true",
            not input_codex_invoked,
        ),
        (
            "prompt406_relaxed_local_loop_git_mutation_allowed_true",
            not input_git_mutation_allowed,
        ),
        (
            "prompt406_relaxed_local_loop_commit_tag_allowed_true",
            not input_commit_tag_allowed,
        ),
        (
            "prompt406_relaxed_local_loop_strict_gates_reenabled_true",
            not input_strict_gates_reenabled,
        ),
        (
            "prompt406_relaxed_local_loop_completion_candidate_false",
            input_completion_candidate,
        ),
        (
            "prompt406_strict_reenable_required_false",
            input_strict_reenable_required,
        ),
        (
            "prompt406_strict_reenable_next_gate_not_prompt407_relaxed_loop_completion_receipt",
            input_strict_reenable_next_gate
            == "prompt407_relaxed_loop_completion_receipt",
        ),
        (
            "prompt406_next_action_not_prepare_prompt407_relaxed_loop_completion_receipt",
            input_next_action == "prepare_prompt407_relaxed_loop_completion_receipt",
        ),
        (
            "prompt406_relaxed_local_loop_completed_chain_not_verified",
            completed_chain_verified,
        ),
    )
    blocked_reasons = [
        reason for reason, input_ready in required_inputs if not input_ready
    ]
    receipt_ready = not blocked_reasons

    remaining_strict_blocked_gates = _normalize_string_list(
        run_state.get("prompt406_remaining_strict_blocked_gates"),
        sort_items=False,
    )
    remaining_strict_false_gate_fields = _normalize_string_list(
        run_state.get("prompt406_remaining_strict_false_gate_fields"),
        sort_items=False,
    )
    relaxed_bypassed_strict_gates = _normalize_string_list(
        run_state.get("prompt406_relaxed_bypassed_strict_gates"),
        sort_items=False,
    )

    return {
        "prompt407_schema_version": _PROMPT407_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt407",
        "prompt407_relaxed_loop_completion_receipt_enabled": receipt_ready,
        "prompt407_relaxed_loop_completion_receipt_status": (
            "completed" if receipt_ready else "blocked"
        ),
        "prompt407_relaxed_loop_completion_receipt_blocked_reason": (
            blocked_reasons[0] if blocked_reasons else ""
        ),
        "prompt407_relaxed_loop_completion_receipt_blocked_reasons": blocked_reasons,
        "prompt407_input_prompt406_observation_status": input_observation_status,
        "prompt407_input_prompt406_loop_observed": input_loop_observed,
        "prompt407_input_prompt406_observation_mode": input_observation_mode,
        "prompt407_input_prompt406_execution_scope": input_execution_scope,
        "prompt407_input_prompt406_execution_type": input_execution_type,
        "prompt407_input_prompt406_actual_execution_performed": (
            input_actual_execution_performed
        ),
        "prompt407_input_prompt406_codex_invoked": input_codex_invoked,
        "prompt407_input_prompt406_git_mutation_allowed": (
            input_git_mutation_allowed
        ),
        "prompt407_input_prompt406_commit_tag_allowed": input_commit_tag_allowed,
        "prompt407_input_prompt406_strict_gates_reenabled": (
            input_strict_gates_reenabled
        ),
        "prompt407_input_prompt406_completion_candidate": input_completion_candidate,
        "prompt407_input_prompt406_strict_reenable_required": (
            input_strict_reenable_required
        ),
        "prompt407_input_prompt406_strict_reenable_next_gate": (
            input_strict_reenable_next_gate
        ),
        "prompt407_input_prompt406_next_action": input_next_action,
        "prompt407_completed_chain_expected": completed_chain_expected,
        "prompt407_completed_chain_observed": completed_chain_observed,
        "prompt407_completed_chain_verified": completed_chain_verified,
        "prompt407_relaxed_local_loop_observation_completed": receipt_ready,
        "prompt407_relaxed_local_loop_completion_scope": (
            "local_only" if receipt_ready else ""
        ),
        "prompt407_relaxed_local_loop_completion_mode": (
            "metadata_only" if receipt_ready else ""
        ),
        "prompt407_relaxed_local_loop_completion_type": (
            "dry_run_plan_observation_receipt" if receipt_ready else ""
        ),
        "prompt407_selected_prompt_actual_execution_performed": False,
        "prompt407_codex_invoked": False,
        "prompt407_git_mutation_allowed": False,
        "prompt407_commit_tag_allowed": False,
        "prompt407_strict_gates_reenabled": False,
        "prompt407_remaining_strict_blocked_gates": remaining_strict_blocked_gates,
        "prompt407_remaining_strict_false_gate_fields": (
            remaining_strict_false_gate_fields
        ),
        "prompt407_relaxed_bypassed_strict_gates": relaxed_bypassed_strict_gates,
        "prompt407_strict_reenable_entry_ready": receipt_ready,
        "prompt407_strict_reenable_plan_required": True,
        "prompt407_strict_reenable_plan_target": (
            "prompt408_strict_reenable_plan" if receipt_ready else ""
        ),
        "prompt407_next_action": (
            "prepare_prompt408_strict_reenable_plan"
            if receipt_ready
            else "wait_for_prompt406_bounded_loop_observation"
        ),
    }

def _build_prompt408_strict_reenable_plan_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    run_state = dict(run_state_payload or {})
    input_completion_status = _normalize_text(
        run_state.get("prompt407_relaxed_loop_completion_receipt_status"),
        default="",
    )
    input_completed_chain_verified = bool(
        run_state.get("prompt407_completed_chain_verified", False)
    )
    input_observation_completed = bool(
        run_state.get("prompt407_relaxed_local_loop_observation_completed", False)
    )
    input_completion_scope = _normalize_text(
        run_state.get("prompt407_relaxed_local_loop_completion_scope"),
        default="",
    )
    input_completion_mode = _normalize_text(
        run_state.get("prompt407_relaxed_local_loop_completion_mode"),
        default="",
    )
    input_completion_type = _normalize_text(
        run_state.get("prompt407_relaxed_local_loop_completion_type"),
        default="",
    )
    input_selected_prompt_actual_execution_performed = bool(
        run_state.get("prompt407_selected_prompt_actual_execution_performed", False)
    )
    input_codex_invoked = bool(run_state.get("prompt407_codex_invoked", False))
    input_git_mutation_allowed = bool(
        run_state.get("prompt407_git_mutation_allowed", False)
    )
    input_commit_tag_allowed = bool(
        run_state.get("prompt407_commit_tag_allowed", False)
    )
    input_strict_gates_reenabled = bool(
        run_state.get("prompt407_strict_gates_reenabled", False)
    )
    input_strict_reenable_entry_ready = bool(
        run_state.get("prompt407_strict_reenable_entry_ready", False)
    )
    input_strict_reenable_plan_required = bool(
        run_state.get("prompt407_strict_reenable_plan_required", False)
    )
    input_strict_reenable_plan_target = _normalize_text(
        run_state.get("prompt407_strict_reenable_plan_target"),
        default="",
    )
    input_next_action = _normalize_text(
        run_state.get("prompt407_next_action"),
        default="",
    )

    required_inputs: tuple[tuple[str, bool], ...] = (
        (
            "prompt407_relaxed_loop_completion_receipt_status_not_completed",
            input_completion_status == "completed",
        ),
        (
            "prompt407_completed_chain_verified_false",
            input_completed_chain_verified,
        ),
        (
            "prompt407_relaxed_local_loop_observation_completed_false",
            input_observation_completed,
        ),
        (
            "prompt407_relaxed_local_loop_completion_scope_not_local_only",
            input_completion_scope == "local_only",
        ),
        (
            "prompt407_relaxed_local_loop_completion_mode_not_metadata_only",
            input_completion_mode == "metadata_only",
        ),
        (
            "prompt407_relaxed_local_loop_completion_type_not_dry_run_plan_observation_receipt",
            input_completion_type == "dry_run_plan_observation_receipt",
        ),
        (
            "prompt407_selected_prompt_actual_execution_performed_true",
            not input_selected_prompt_actual_execution_performed,
        ),
        (
            "prompt407_codex_invoked_true",
            not input_codex_invoked,
        ),
        (
            "prompt407_git_mutation_allowed_true",
            not input_git_mutation_allowed,
        ),
        (
            "prompt407_commit_tag_allowed_true",
            not input_commit_tag_allowed,
        ),
        (
            "prompt407_strict_gates_reenabled_true",
            not input_strict_gates_reenabled,
        ),
        (
            "prompt407_strict_reenable_entry_ready_false",
            input_strict_reenable_entry_ready,
        ),
        (
            "prompt407_strict_reenable_plan_required_false",
            input_strict_reenable_plan_required,
        ),
        (
            "prompt407_strict_reenable_plan_target_not_prompt408_strict_reenable_plan",
            input_strict_reenable_plan_target == "prompt408_strict_reenable_plan",
        ),
        (
            "prompt407_next_action_not_prepare_prompt408_strict_reenable_plan",
            input_next_action == "prepare_prompt408_strict_reenable_plan",
        ),
    )
    blocked_reasons = [
        reason for reason, input_ready in required_inputs if not input_ready
    ]
    plan_ready = not blocked_reasons
    target_gates = ["prompt381", "prompt385", "prompt389", "prompt390"]
    reenable_order = [
        "prompt381_approve_candidate_boundary",
        "prompt385_next_cycle_handoff",
        "prompt389_bounded_repeated_success_path_loop",
        "prompt390_enabled_run",
    ]
    remaining_strict_blocked_gates = _normalize_string_list(
        run_state.get("prompt407_remaining_strict_blocked_gates"),
        sort_items=False,
    )
    remaining_strict_false_gate_fields = _normalize_string_list(
        run_state.get("prompt407_remaining_strict_false_gate_fields"),
        sort_items=False,
    )
    relaxed_bypassed_strict_gates = _normalize_string_list(
        run_state.get("prompt407_relaxed_bypassed_strict_gates"),
        sort_items=False,
    )

    return {
        "prompt408_schema_version": _PROMPT408_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt408",
        "prompt408_strict_reenable_plan_enabled": plan_ready,
        "prompt408_strict_reenable_plan_status": (
            "ready" if plan_ready else "blocked"
        ),
        "prompt408_strict_reenable_plan_blocked_reason": (
            blocked_reasons[0] if blocked_reasons else ""
        ),
        "prompt408_strict_reenable_plan_blocked_reasons": blocked_reasons,
        "prompt408_input_prompt407_completion_status": input_completion_status,
        "prompt408_input_prompt407_completed_chain_verified": (
            input_completed_chain_verified
        ),
        "prompt408_input_prompt407_observation_completed": (
            input_observation_completed
        ),
        "prompt408_input_prompt407_completion_scope": input_completion_scope,
        "prompt408_input_prompt407_completion_mode": input_completion_mode,
        "prompt408_input_prompt407_completion_type": input_completion_type,
        "prompt408_input_prompt407_selected_prompt_actual_execution_performed": (
            input_selected_prompt_actual_execution_performed
        ),
        "prompt408_input_prompt407_codex_invoked": input_codex_invoked,
        "prompt408_input_prompt407_git_mutation_allowed": (
            input_git_mutation_allowed
        ),
        "prompt408_input_prompt407_commit_tag_allowed": input_commit_tag_allowed,
        "prompt408_input_prompt407_strict_gates_reenabled": (
            input_strict_gates_reenabled
        ),
        "prompt408_input_prompt407_strict_reenable_entry_ready": (
            input_strict_reenable_entry_ready
        ),
        "prompt408_input_prompt407_strict_reenable_plan_required": (
            input_strict_reenable_plan_required
        ),
        "prompt408_input_prompt407_strict_reenable_plan_target": (
            input_strict_reenable_plan_target
        ),
        "prompt408_input_prompt407_next_action": input_next_action,
        "prompt408_strict_reenable_plan_ready": plan_ready,
        "prompt408_strict_reenable_plan_mode": (
            "metadata_only" if plan_ready else ""
        ),
        "prompt408_strict_reenable_plan_scope": (
            "local_only" if plan_ready else ""
        ),
        "prompt408_strict_reenable_target_gates": target_gates,
        "prompt408_strict_reenable_order": reenable_order,
        "prompt408_strict_reenable_first_gate": reenable_order[0],
        "prompt408_strict_reenable_final_gate": reenable_order[-1],
        "prompt408_remaining_strict_blocked_gates": remaining_strict_blocked_gates,
        "prompt408_remaining_strict_false_gate_fields": (
            remaining_strict_false_gate_fields
        ),
        "prompt408_relaxed_bypassed_strict_gates": relaxed_bypassed_strict_gates,
        "prompt408_strict_reenable_required": True,
        "prompt408_prompt381_reenable_requirements": [
            "committed_prompt379_result_accepted",
            "prompt379_execution_receipt_available_or_committed_evidence_accepted",
            "prompt380_route_decision_approve_candidate",
            "no_strict_field_fabrication",
        ],
        "prompt408_prompt385_reenable_requirements": [
            "prompt381_strict_reenabled_or_authorized_bridge",
            "next_cycle_handoff_inputs_complete",
            "selected_next_prompt_available",
            "no_relaxed_only_evidence_without_marker",
        ],
        "prompt408_prompt389_reenable_requirements": [
            "prompt385_next_cycle_handoff_ready",
            "bounded_loop_max_cycles_defined",
            "repeated_loop_stop_condition_defined",
            "no_unbounded_loop",
        ],
        "prompt408_prompt390_reenable_requirements": [
            "prompt389_repeated_cycle_execution_gate_ready",
            "prompt389_repeated_cycle_execution_allowed",
            "enabled_run_inputs_complete",
            "execution_requires_explicit_enable",
        ],
        "prompt408_strict_reenable_execution_allowed": False,
        "prompt408_strict_reenable_attempted": False,
        "prompt408_strict_reenable_performed": False,
        "prompt408_strict_gates_reenabled": False,
        "prompt408_selected_prompt_execution_allowed": False,
        "prompt408_codex_invocation_allowed": False,
        "prompt408_git_mutation_allowed": False,
        "prompt408_commit_tag_allowed": False,
        "prompt408_next_action": (
            "prepare_prompt409_strict_reenable_gate"
            if plan_ready
            else "wait_for_prompt407_relaxed_loop_completion_receipt"
        ),
    }

def _build_prompt409_strict_reenable_gate_restoration_packet_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    run_state = dict(run_state_payload or {})
    expected_order = [
        "prompt381_approve_candidate_boundary",
        "prompt385_next_cycle_handoff",
        "prompt389_bounded_repeated_success_path_loop",
        "prompt390_enabled_run",
    ]
    expected_targets = ["prompt381", "prompt385", "prompt389", "prompt390"]
    prompt408_plan_status = _normalize_text(
        run_state.get("prompt408_strict_reenable_plan_status"),
        default="",
    )
    prompt408_plan_ready = bool(
        run_state.get("prompt408_strict_reenable_plan_ready", False)
    )
    prompt408_required = bool(
        run_state.get("prompt408_strict_reenable_required", False)
    )
    prompt408_first_gate = _normalize_text(
        run_state.get("prompt408_strict_reenable_first_gate"),
        default="",
    )
    prompt408_final_gate = _normalize_text(
        run_state.get("prompt408_strict_reenable_final_gate"),
        default="",
    )
    prompt408_order = _normalize_string_list(
        run_state.get("prompt408_strict_reenable_order"),
        sort_items=False,
    )

    plan_ready = (
        prompt408_plan_status == "ready"
        and prompt408_plan_ready
        and prompt408_required
        and prompt408_first_gate == expected_order[0]
        and prompt408_final_gate == expected_order[-1]
        and prompt408_order == expected_order
    )
    blocked_reasons = (
        [] if plan_ready else ["prompt408_strict_reenable_plan_not_ready"]
    )

    return {
        "prompt409_schema_version": _PROMPT409_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt409",
        "prompt409_strict_reenable_gate_enabled": True,
        "prompt409_strict_reenable_gate_status": (
            "ready" if plan_ready else "blocked"
        ),
        "prompt409_strict_reenable_gate_ready": plan_ready,
        "prompt409_strict_reenable_gate_blocked_reason": (
            blocked_reasons[0] if blocked_reasons else ""
        ),
        "prompt409_strict_reenable_gate_blocked_reasons": blocked_reasons,
        "prompt409_strict_reenable_source": "prompt408_strict_reenable_plan",
        "prompt409_strict_reenable_first_gate": expected_order[0],
        "prompt409_strict_reenable_final_gate": expected_order[-1],
        "prompt409_strict_reenable_gate_order": expected_order,
        "prompt409_restoration_packet_ready": plan_ready,
        "prompt409_restoration_packet_scope": "strict_route_restore",
        "prompt409_restoration_packet_mode": "metadata_only",
        "prompt409_restoration_packet_target_prompt": "prompt410",
        "prompt409_restoration_packet_targets": expected_targets,
        "prompt409_strict_reenable_execution_allowed": False,
        "prompt409_strict_reenable_attempted": False,
        "prompt409_strict_reenable_performed": False,
        "prompt409_strict_gates_reenabled": False,
        "prompt409_selected_prompt_execution_allowed": False,
        "prompt409_codex_invocation_allowed": False,
        "prompt409_git_mutation_allowed": False,
        "prompt409_commit_tag_allowed": False,
        "prompt409_next_action": (
            "restore_strict_route_in_prompt410"
            if plan_ready
            else "review_prompt408_strict_reenable_plan"
        ),
    }

def _build_prompt410_strict_route_restore_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    run_state = dict(run_state_payload or {})
    required_inputs: tuple[tuple[str, bool], ...] = (
        (
            "prompt409_strict_reenable_gate_status_not_ready",
            _normalize_text(
                run_state.get("prompt409_strict_reenable_gate_status"),
                default="",
            )
            == "ready",
        ),
        (
            "prompt409_strict_reenable_gate_ready_false",
            run_state.get("prompt409_strict_reenable_gate_ready") is True,
        ),
        (
            "prompt409_restoration_packet_ready_false",
            run_state.get("prompt409_restoration_packet_ready") is True,
        ),
        (
            "prompt409_restoration_packet_target_prompt_not_prompt410",
            _normalize_text(
                run_state.get("prompt409_restoration_packet_target_prompt"),
                default="",
            )
            == "prompt410",
        ),
        (
            "prompt409_next_action_not_restore_strict_route_in_prompt410",
            _normalize_text(
                run_state.get("prompt409_next_action"),
                default="",
            )
            == "restore_strict_route_in_prompt410",
        ),
    )
    restoration_ready = all(input_ready for _, input_ready in required_inputs)
    blocked_reason = (
        "" if restoration_ready else "prompt409_restoration_packet_not_ready"
    )
    blocked_reasons = [] if restoration_ready else [blocked_reason]
    restored_gates = ["prompt381", "prompt385", "prompt389", "prompt390"]
    restored_gate_order = [
        "prompt381_approve_candidate_boundary",
        "prompt385_next_cycle_handoff",
        "prompt389_bounded_repeated_success_path_loop",
        "prompt390_enabled_run",
    ]

    return {
        "prompt410_schema_version": _PROMPT410_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt410",
        "prompt410_strict_route_restore_enabled": True,
        "prompt410_strict_route_restore_status": (
            "restored" if restoration_ready else "blocked"
        ),
        "prompt410_strict_route_restore_ready": restoration_ready,
        "prompt410_strict_route_restore_blocked_reason": blocked_reason,
        "prompt410_strict_route_restore_blocked_reasons": blocked_reasons,
        "prompt410_strict_route_restore_source": (
            "prompt409_restoration_packet" if restoration_ready else ""
        ),
        "prompt410_restored_gates": restored_gates,
        "prompt410_restored_gate_order": restored_gate_order,
        "prompt410_prompt381_restore_ready": restoration_ready,
        "prompt410_prompt381_approve_candidate_boundary_restored": (
            restoration_ready
        ),
        "prompt410_prompt381_approve_candidate_boundary_status": (
            "ready" if restoration_ready else "blocked"
        ),
        "prompt410_prompt385_restore_ready": restoration_ready,
        "prompt410_prompt385_next_cycle_handoff_restored": restoration_ready,
        "prompt410_prompt385_next_cycle_handoff_ready": restoration_ready,
        "prompt410_prompt389_restore_ready": restoration_ready,
        "prompt410_prompt389_repeated_cycle_execution_gate_restored": (
            restoration_ready
        ),
        "prompt410_prompt389_repeated_cycle_execution_gate_ready": restoration_ready,
        "prompt410_prompt389_repeated_cycle_execution_allowed": False,
        "prompt410_prompt390_restore_ready": restoration_ready,
        "prompt410_prompt390_enabled_run_restored": restoration_ready,
        "prompt410_prompt390_enabled_run_ready": restoration_ready,
        "prompt410_prompt390_enabled_run_allowed": False,
        "prompt410_selected_prompt_execution_allowed": False,
        "prompt410_codex_invocation_allowed": False,
        "prompt410_git_mutation_allowed": False,
        "prompt410_commit_tag_allowed": False,
        "prompt410_strict_route_restore_execution_allowed": False,
        "prompt410_strict_route_restore_attempted": False,
        "prompt410_strict_route_restore_performed": False,
        "prompt410_next_action": (
            "prepare_prompt411_physical_prompt_materialization"
            if restoration_ready
            else "review_prompt409_restoration_packet"
        ),
    }

def _build_prompt411_physical_prompt_materialization_plan_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    run_state = dict(run_state_payload or {})
    prompt410_ready = (
        _normalize_text(
            run_state.get("prompt410_strict_route_restore_status"),
            default="",
        )
        == "restored"
        and run_state.get("prompt410_strict_route_restore_ready") is True
        and _normalize_text(
            run_state.get("prompt410_next_action"),
            default="",
        )
        == "prepare_prompt411_physical_prompt_materialization"
    )
    blocked_reason = (
        "" if prompt410_ready else "prompt410_strict_route_restore_not_ready"
    )
    blocked_reasons = [] if prompt410_ready else [blocked_reason]

    return {
        "prompt411_schema_version": _PROMPT411_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt411",
        "prompt411_physical_prompt_materialization_enabled": True,
        "prompt411_physical_prompt_materialization_status": (
            "ready" if prompt410_ready else "blocked"
        ),
        "prompt411_physical_prompt_materialization_ready": prompt410_ready,
        "prompt411_physical_prompt_materialization_blocked_reason": (
            blocked_reason
        ),
        "prompt411_physical_prompt_materialization_blocked_reasons": (
            blocked_reasons
        ),
        "prompt411_physical_prompt_materialization_source": (
            "prompt410_strict_route_restore" if prompt410_ready else ""
        ),
        "prompt411_selected_prompt_id": "prompt402" if prompt410_ready else "",
        "prompt411_selected_prompt_source": (
            "prompt402_generated_prompt_surface" if prompt410_ready else ""
        ),
        "prompt411_selected_prompt_materialization_ready": prompt410_ready,
        "prompt411_materialization_mode": "metadata_only",
        "prompt411_materialization_target_prompt": "prompt412",
        "prompt411_physical_prompt_path_planned": prompt410_ready,
        "prompt411_physical_prompt_path": "",
        "prompt411_physical_prompt_write_allowed": False,
        "prompt411_physical_prompt_written": False,
        "prompt411_selected_prompt_execution_allowed": False,
        "prompt411_codex_invocation_allowed": False,
        "prompt411_git_mutation_allowed": False,
        "prompt411_commit_tag_allowed": False,
        "prompt411_next_action": (
            "prepare_prompt412_selected_prompt_execution_adapter"
            if prompt410_ready
            else "review_prompt410_strict_route_restore"
        ),
    }

def _build_prompt412_physical_prompt_materialization_boundary_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    run_state = dict(run_state_payload or {})
    physical_prompt_path = (
        "current_prompt_verify_results/prompt412/selected_prompt_prompt402.md"
    )
    prompt411_ready = (
        _normalize_text(
            run_state.get("prompt411_physical_prompt_materialization_status"),
            default="",
        )
        == "ready"
        and run_state.get("prompt411_physical_prompt_materialization_ready") is True
        and _normalize_text(run_state.get("prompt411_selected_prompt_id"), default="")
        == "prompt402"
        and run_state.get("prompt411_selected_prompt_materialization_ready") is True
        and _normalize_text(
            run_state.get("prompt411_materialization_target_prompt"),
            default="",
        )
        == "prompt412"
        and _normalize_text(run_state.get("prompt411_next_action"), default="")
        == "prepare_prompt412_selected_prompt_execution_adapter"
    )
    blocked_reason = (
        ""
        if prompt411_ready
        else "prompt411_physical_prompt_materialization_not_ready"
    )
    blocked_reasons = [] if prompt411_ready else [blocked_reason]

    return {
        "prompt412_schema_version": _PROMPT412_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt412",
        "prompt412_physical_prompt_materialization_boundary_enabled": True,
        "prompt412_physical_prompt_materialization_boundary_status": (
            "ready" if prompt411_ready else "blocked"
        ),
        "prompt412_physical_prompt_materialization_boundary_ready": (
            prompt411_ready
        ),
        "prompt412_physical_prompt_materialization_boundary_blocked_reason": (
            blocked_reason
        ),
        "prompt412_physical_prompt_materialization_boundary_blocked_reasons": (
            blocked_reasons
        ),
        "prompt412_physical_prompt_materialization_source": (
            "prompt411_physical_prompt_materialization_plan"
            if prompt411_ready
            else ""
        ),
        "prompt412_selected_prompt_id": "prompt402" if prompt411_ready else "",
        "prompt412_selected_prompt_source": (
            "prompt402_generated_prompt_surface" if prompt411_ready else ""
        ),
        "prompt412_physical_prompt_mode": (
            "planned_no_write" if prompt411_ready else "blocked_no_write"
        ),
        "prompt412_physical_prompt_path_planned": prompt411_ready,
        "prompt412_physical_prompt_path": (
            physical_prompt_path if prompt411_ready else ""
        ),
        "prompt412_physical_prompt_write_requested": False,
        "prompt412_physical_prompt_write_allowed": False,
        "prompt412_physical_prompt_written": False,
        "prompt412_physical_prompt_exists": False,
        "prompt412_execution_adapter_packet_ready": prompt411_ready,
        "prompt412_execution_adapter_packet_target_prompt": "prompt413",
        "prompt412_execution_adapter_packet_mode": (
            "selected_prompt_physical_prompt_boundary"
            if prompt411_ready
            else "blocked"
        ),
        "prompt412_execution_adapter_packet_prompt_id": (
            "prompt402" if prompt411_ready else ""
        ),
        "prompt412_execution_adapter_packet_prompt_path": (
            physical_prompt_path if prompt411_ready else ""
        ),
        "prompt412_selected_prompt_execution_allowed": False,
        "prompt412_codex_invocation_allowed": False,
        "prompt412_git_mutation_allowed": False,
        "prompt412_commit_tag_allowed": False,
        "prompt412_next_action": (
            "prepare_prompt413_selected_prompt_execution_adapter"
            if prompt411_ready
            else "review_prompt411_physical_prompt_materialization_plan"
        ),
    }

def _build_prompt413_selected_prompt_execution_adapter_boundary_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    run_state = dict(run_state_payload or {})
    prompt_path = (
        "current_prompt_verify_results/prompt412/selected_prompt_prompt402.md"
    )
    stdout_path = "current_prompt_verify_results/prompt413/prompt402_stdout.txt"
    stderr_path = "current_prompt_verify_results/prompt413/prompt402_stderr.txt"
    result_json_path = (
        "current_prompt_verify_results/prompt413/"
        "prompt402_execution_result.json"
    )
    prompt412_ready = (
        _normalize_text(
            run_state.get(
                "prompt412_physical_prompt_materialization_boundary_status"
            ),
            default="",
        )
        == "ready"
        and run_state.get(
            "prompt412_physical_prompt_materialization_boundary_ready"
        )
        is True
        and run_state.get("prompt412_execution_adapter_packet_ready") is True
        and _normalize_text(
            run_state.get("prompt412_execution_adapter_packet_target_prompt"),
            default="",
        )
        == "prompt413"
        and _normalize_text(
            run_state.get("prompt412_execution_adapter_packet_mode"),
            default="",
        )
        == "selected_prompt_physical_prompt_boundary"
        and _normalize_text(
            run_state.get("prompt412_execution_adapter_packet_prompt_id"),
            default="",
        )
        == "prompt402"
        and _normalize_text(run_state.get("prompt412_next_action"), default="")
        == "prepare_prompt413_selected_prompt_execution_adapter"
    )
    blocked_reason = (
        ""
        if prompt412_ready
        else "prompt412_execution_adapter_packet_not_ready"
    )
    blocked_reasons = [] if prompt412_ready else [blocked_reason]

    return {
        "prompt413_schema_version": _PROMPT413_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt413",
        "prompt413_selected_prompt_execution_adapter_enabled": True,
        "prompt413_selected_prompt_execution_adapter_status": (
            "ready" if prompt412_ready else "blocked"
        ),
        "prompt413_selected_prompt_execution_adapter_ready": prompt412_ready,
        "prompt413_selected_prompt_execution_adapter_blocked_reason": (
            blocked_reason
        ),
        "prompt413_selected_prompt_execution_adapter_blocked_reasons": (
            blocked_reasons
        ),
        "prompt413_selected_prompt_execution_adapter_source": (
            "prompt412_execution_adapter_packet" if prompt412_ready else ""
        ),
        "prompt413_selected_prompt_id": "prompt402" if prompt412_ready else "",
        "prompt413_selected_prompt_source": (
            "prompt402_generated_prompt_surface" if prompt412_ready else ""
        ),
        "prompt413_selected_prompt_prompt_path": (
            prompt_path if prompt412_ready else ""
        ),
        "prompt413_execution_mode": (
            "planned_no_execute" if prompt412_ready else "blocked_no_execute"
        ),
        "prompt413_execution_requested": False,
        "prompt413_execution_allowed": False,
        "prompt413_execution_attempted": False,
        "prompt413_execution_performed": False,
        "prompt413_execution_returncode": None,
        "prompt413_execution_returncode_classification": "not_run",
        "prompt413_capture_plan_ready": prompt412_ready,
        "prompt413_capture_target_prompt": "prompt414",
        "prompt413_stdout_path": stdout_path if prompt412_ready else "",
        "prompt413_stderr_path": stderr_path if prompt412_ready else "",
        "prompt413_result_json_path": (
            result_json_path if prompt412_ready else ""
        ),
        "prompt413_capture_written": False,
        "prompt413_review_packet_ready": prompt412_ready,
        "prompt413_review_packet_target_prompt": "prompt414",
        "prompt413_review_packet_mode": (
            "execution_adapter_boundary_no_execute"
            if prompt412_ready
            else "blocked"
        ),
        "prompt413_review_packet_prompt_id": (
            "prompt402" if prompt412_ready else ""
        ),
        "prompt413_review_packet_result_json_path": (
            result_json_path if prompt412_ready else ""
        ),
        "prompt413_selected_prompt_execution_allowed": False,
        "prompt413_codex_invocation_allowed": False,
        "prompt413_git_mutation_allowed": False,
        "prompt413_commit_tag_allowed": False,
        "prompt413_next_action": (
            "prepare_prompt414_execution_result_review"
            if prompt412_ready
            else "review_prompt412_execution_adapter_packet"
        ),
    }

def _build_prompt414_execution_result_review_boundary_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    run_state = dict(run_state_payload or {})
    prompt413_ready = (
        _normalize_text(
            run_state.get("prompt413_selected_prompt_execution_adapter_status"),
            default="",
        )
        == "ready"
        and run_state.get("prompt413_selected_prompt_execution_adapter_ready")
        is True
        and run_state.get("prompt413_review_packet_ready") is True
        and _normalize_text(
            run_state.get("prompt413_review_packet_target_prompt"),
            default="",
        )
        == "prompt414"
        and _normalize_text(
            run_state.get("prompt413_review_packet_mode"),
            default="",
        )
        == "execution_adapter_boundary_no_execute"
        and run_state.get("prompt413_execution_requested") is False
        and run_state.get("prompt413_execution_allowed") is False
        and run_state.get("prompt413_execution_attempted") is False
        and run_state.get("prompt413_execution_performed") is False
        and run_state.get("prompt413_execution_returncode") is None
        and _normalize_text(
            run_state.get("prompt413_execution_returncode_classification"),
            default="",
        )
        == "not_run"
        and _normalize_text(run_state.get("prompt413_next_action"), default="")
        == "prepare_prompt414_execution_result_review"
    )
    blocked_reason = (
        "" if prompt413_ready else "prompt413_review_packet_not_ready"
    )
    blocked_reasons = [] if prompt413_ready else [blocked_reason]

    return {
        "prompt414_schema_version": _PROMPT414_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt414",
        "prompt414_execution_result_review_enabled": True,
        "prompt414_execution_result_review_status": (
            "reviewed" if prompt413_ready else "blocked"
        ),
        "prompt414_execution_result_review_ready": prompt413_ready,
        "prompt414_execution_result_review_blocked_reason": blocked_reason,
        "prompt414_execution_result_review_blocked_reasons": blocked_reasons,
        "prompt414_execution_result_review_source": (
            "prompt413_review_packet" if prompt413_ready else ""
        ),
        "prompt414_selected_prompt_id": "prompt402" if prompt413_ready else "",
        "prompt414_selected_prompt_source": (
            "prompt402_generated_prompt_surface" if prompt413_ready else ""
        ),
        "prompt414_review_classification": (
            "not_run_boundary" if prompt413_ready else "blocked"
        ),
        "prompt414_review_route": (
            "ready_for_prompt415_guarded_execution_enable_plan"
            if prompt413_ready
            else "review_prompt413_selected_prompt_execution_adapter"
        ),
        "prompt414_execution_result_available": False,
        "prompt414_execution_success": False,
        "prompt414_execution_failed": False,
        "prompt414_execution_not_run": True,
        "prompt414_execution_returncode": None,
        "prompt414_execution_returncode_classification": "not_run",
        "prompt414_approve_candidate": False,
        "prompt414_targeted_fix_required": False,
        "prompt414_retry_required": False,
        "prompt414_commit_tag_allowed": False,
        "prompt414_selected_prompt_execution_allowed": False,
        "prompt414_codex_invocation_allowed": False,
        "prompt414_git_mutation_allowed": False,
        "prompt414_execution_allowed": False,
        "prompt414_execution_attempted": False,
        "prompt414_execution_performed": False,
        "prompt414_next_action": (
            "prepare_prompt415_guarded_execution_enable_plan"
            if prompt413_ready
            else "review_prompt413_selected_prompt_execution_adapter"
        ),
    }

def _build_prompt415_guarded_execution_enable_plan_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    run_state = (
        dict(run_state_payload)
        if isinstance(run_state_payload, Mapping)
        else {}
    )
    prompt414_ready = (
        _normalize_text(
            run_state.get("prompt414_execution_result_review_status"),
            default="",
        )
        == "reviewed"
        and run_state.get("prompt414_execution_result_review_ready") is True
        and _normalize_text(
            run_state.get("prompt414_review_classification"),
            default="",
        )
        == "not_run_boundary"
        and _normalize_text(run_state.get("prompt414_review_route"), default="")
        == "ready_for_prompt415_guarded_execution_enable_plan"
        and run_state.get("prompt414_execution_result_available") is False
        and run_state.get("prompt414_execution_success") is False
        and run_state.get("prompt414_execution_failed") is False
        and run_state.get("prompt414_execution_not_run") is True
        and run_state.get("prompt414_execution_returncode") is None
        and _normalize_text(
            run_state.get("prompt414_execution_returncode_classification"),
            default="",
        )
        == "not_run"
        and run_state.get("prompt414_approve_candidate") is False
        and run_state.get("prompt414_targeted_fix_required") is False
        and run_state.get("prompt414_retry_required") is False
        and run_state.get("prompt414_commit_tag_allowed") is False
        and _normalize_text(run_state.get("prompt414_next_action"), default="")
        == "prepare_prompt415_guarded_execution_enable_plan"
    )
    selected_prompt_id = ""
    selected_prompt_source = ""
    if prompt414_ready:
        selected_prompt_id = _normalize_text(
            run_state.get("prompt414_selected_prompt_id"),
            default="",
        )
        selected_prompt_source = _normalize_text(
            run_state.get("prompt414_selected_prompt_source"),
            default="",
        )
        if not selected_prompt_id:
            selected_prompt_id = "prompt402"
        if not selected_prompt_source:
            selected_prompt_source = "prompt402_generated_prompt_surface"

    physical_prompt_path = (
        "current_prompt_verify_results/prompt416/"
        "selected_prompt_prompt402.md"
    )
    stdout_path = "current_prompt_verify_results/prompt416/prompt402_stdout.txt"
    stderr_path = "current_prompt_verify_results/prompt416/prompt402_stderr.txt"
    result_json_path = (
        "current_prompt_verify_results/prompt416/"
        "prompt402_execution_result.json"
    )
    blocked_reason = (
        ""
        if prompt414_ready
        else "prompt414_not_run_boundary_review_not_ready"
    )
    blocked_reasons = [] if prompt414_ready else [blocked_reason]

    return {
        "prompt415_schema_version": _PROMPT415_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt415",
        "prompt415_guarded_execution_enable_plan_enabled": True,
        "prompt415_guarded_execution_enable_plan_status": (
            "ready" if prompt414_ready else "blocked"
        ),
        "prompt415_guarded_execution_enable_plan_ready": prompt414_ready,
        "prompt415_guarded_execution_enable_plan_blocked_reason": (
            blocked_reason
        ),
        "prompt415_guarded_execution_enable_plan_blocked_reasons": (
            blocked_reasons
        ),
        "prompt415_guarded_execution_enable_plan_source": (
            "prompt414_execution_result_review_boundary"
        ),
        "prompt415_selected_prompt_id": selected_prompt_id,
        "prompt415_selected_prompt_source": selected_prompt_source,
        "prompt415_enable_plan_classification": (
            "guarded_execution_enable_plan" if prompt414_ready else "blocked"
        ),
        "prompt415_enable_plan_route": (
            "ready_for_prompt416_physical_prompt_materialization_write_plan"
            if prompt414_ready
            else "review_prompt414_execution_result_review_boundary"
        ),
        "prompt415_execution_enable_requested": False,
        "prompt415_execution_enable_allowed": False,
        "prompt415_execution_enable_performed": False,
        "prompt415_physical_prompt_write_plan_ready": prompt414_ready,
        "prompt415_physical_prompt_write_plan_target_prompt": "prompt416",
        "prompt415_physical_prompt_write_requested": False,
        "prompt415_physical_prompt_write_allowed": False,
        "prompt415_physical_prompt_written": False,
        "prompt415_physical_prompt_path_planned": prompt414_ready,
        "prompt415_physical_prompt_path": (
            physical_prompt_path if prompt414_ready else ""
        ),
        "prompt415_execution_plan_ready": prompt414_ready,
        "prompt415_execution_plan_target_prompt": "prompt416",
        "prompt415_execution_plan_mode": (
            "guarded_no_execute" if prompt414_ready else "blocked_no_execute"
        ),
        "prompt415_execution_requested": False,
        "prompt415_execution_allowed": False,
        "prompt415_execution_attempted": False,
        "prompt415_execution_performed": False,
        "prompt415_execution_returncode": None,
        "prompt415_execution_returncode_classification": "not_run",
        "prompt415_capture_plan_ready": prompt414_ready,
        "prompt415_capture_target_prompt": "prompt416",
        "prompt415_stdout_path": stdout_path if prompt414_ready else "",
        "prompt415_stderr_path": stderr_path if prompt414_ready else "",
        "prompt415_result_json_path": (
            result_json_path if prompt414_ready else ""
        ),
        "prompt415_capture_written": False,
        "prompt415_review_packet_ready": prompt414_ready,
        "prompt415_review_packet_target_prompt": "prompt416",
        "prompt415_review_packet_mode": (
            "guarded_execution_enable_plan_no_execute"
            if prompt414_ready
            else "blocked"
        ),
        "prompt415_review_packet_prompt_id": selected_prompt_id,
        "prompt415_review_packet_result_json_path": (
            result_json_path if prompt414_ready else ""
        ),
        "prompt415_approve_candidate": False,
        "prompt415_targeted_fix_required": False,
        "prompt415_retry_required": False,
        "prompt415_selected_prompt_execution_allowed": False,
        "prompt415_codex_invocation_allowed": False,
        "prompt415_git_mutation_allowed": False,
        "prompt415_commit_tag_allowed": False,
        "prompt415_next_action": (
            "prepare_prompt416_physical_prompt_write_plan"
            if prompt414_ready
            else "review_prompt414_execution_result_review_boundary"
        ),
    }

def _build_prompt416_physical_prompt_materialization_write_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
    write_requested: bool = False,
    allow_write: bool = False,
    repo_path: str | Path | None = None,
) -> dict[str, Any]:
    run_state = (
        dict(run_state_payload)
        if isinstance(run_state_payload, Mapping)
        else {}
    )
    required_inputs = (
        (
            _normalize_text(
                run_state.get("prompt415_guarded_execution_enable_plan_status"),
                default="",
            )
            == "ready"
        ),
        run_state.get("prompt415_guarded_execution_enable_plan_ready") is True,
        (
            _normalize_text(
                run_state.get("prompt415_enable_plan_classification"),
                default="",
            )
            == "guarded_execution_enable_plan"
        ),
        (
            _normalize_text(run_state.get("prompt415_enable_plan_route"), default="")
            == "ready_for_prompt416_physical_prompt_materialization_write_plan"
        ),
        run_state.get("prompt415_physical_prompt_write_plan_ready") is True,
        (
            _normalize_text(
                run_state.get("prompt415_physical_prompt_write_plan_target_prompt"),
                default="",
            )
            == "prompt416"
        ),
        run_state.get("prompt415_physical_prompt_write_requested") is False,
        run_state.get("prompt415_physical_prompt_write_allowed") is False,
        run_state.get("prompt415_physical_prompt_written") is False,
        run_state.get("prompt415_physical_prompt_path_planned") is True,
        run_state.get("prompt415_execution_plan_ready") is True,
        (
            _normalize_text(
                run_state.get("prompt415_execution_plan_target_prompt"),
                default="",
            )
            == "prompt416"
        ),
        (
            _normalize_text(
                run_state.get("prompt415_execution_plan_mode"),
                default="",
            )
            == "guarded_no_execute"
        ),
        run_state.get("prompt415_execution_requested") is False,
        run_state.get("prompt415_execution_allowed") is False,
        run_state.get("prompt415_execution_attempted") is False,
        run_state.get("prompt415_execution_performed") is False,
        run_state.get("prompt415_execution_returncode") is None,
        (
            _normalize_text(
                run_state.get("prompt415_execution_returncode_classification"),
                default="",
            )
            == "not_run"
        ),
        run_state.get("prompt415_capture_plan_ready") is True,
        (
            _normalize_text(run_state.get("prompt415_capture_target_prompt"), default="")
            == "prompt416"
        ),
        run_state.get("prompt415_capture_written") is False,
        run_state.get("prompt415_review_packet_ready") is True,
        (
            _normalize_text(
                run_state.get("prompt415_review_packet_target_prompt"),
                default="",
            )
            == "prompt416"
        ),
        (
            _normalize_text(
                run_state.get("prompt415_review_packet_mode"),
                default="",
            )
            == "guarded_execution_enable_plan_no_execute"
        ),
        (
            _normalize_text(
                run_state.get("prompt415_review_packet_prompt_id"),
                default="",
            )
            == "prompt402"
        ),
        run_state.get("prompt415_approve_candidate") is False,
        run_state.get("prompt415_targeted_fix_required") is False,
        run_state.get("prompt415_retry_required") is False,
        run_state.get("prompt415_selected_prompt_execution_allowed") is False,
        run_state.get("prompt415_codex_invocation_allowed") is False,
        run_state.get("prompt415_git_mutation_allowed") is False,
        run_state.get("prompt415_commit_tag_allowed") is False,
        (
            _normalize_text(run_state.get("prompt415_next_action"), default="")
            == "prepare_prompt416_physical_prompt_write_plan"
        ),
    )
    prompt415_ready = all(required_inputs)
    requested = bool(write_requested)
    requested_and_allowed = requested and bool(allow_write)
    default_prompt_path = (
        "current_prompt_verify_results/prompt416/"
        "selected_prompt_prompt402.md"
    )
    receipt_path = (
        "current_prompt_verify_results/prompt416/"
        "physical_prompt_materialization_receipt.json"
    )
    stdout_path = "current_prompt_verify_results/prompt417/prompt402_stdout.txt"
    stderr_path = "current_prompt_verify_results/prompt417/prompt402_stderr.txt"
    result_json_path = (
        "current_prompt_verify_results/prompt417/"
        "prompt402_execution_result.json"
    )

    if not prompt415_ready:
        return {
            "prompt416_schema_version": _PROMPT416_SCHEMA_VERSION,
            "local_only": True,
            "source_prompt": "prompt416",
            "prompt416_physical_prompt_materialization_write_enabled": True,
            "prompt416_physical_prompt_materialization_write_status": "blocked",
            "prompt416_physical_prompt_materialization_write_ready": False,
            "prompt416_physical_prompt_materialization_write_blocked_reason": (
                "prompt415_guarded_execution_enable_plan_not_ready"
            ),
            "prompt416_physical_prompt_materialization_write_blocked_reasons": [
                "prompt415_guarded_execution_enable_plan_not_ready"
            ],
            "prompt416_physical_prompt_materialization_write_source": (
                "prompt415_guarded_execution_enable_plan"
            ),
            "prompt416_selected_prompt_id": "",
            "prompt416_selected_prompt_source": "",
            "prompt416_selected_prompt_text_source": "",
            "prompt416_selected_prompt_text_present": False,
            "prompt416_selected_prompt_text_size_bytes": 0,
            "prompt416_selected_prompt_text_sha256": "",
            "prompt416_physical_prompt_path": "",
            "prompt416_physical_prompt_write_requested": requested,
            "prompt416_physical_prompt_write_allowed": False,
            "prompt416_physical_prompt_written": False,
            "prompt416_physical_prompt_exists": False,
            "prompt416_physical_prompt_write_blocked_reason": (
                "prompt415_guarded_execution_enable_plan_not_ready"
            ),
            "prompt416_receipt_path": "",
            "prompt416_receipt_written": False,
            "prompt416_execution_adapter_packet_ready": False,
            "prompt416_execution_adapter_packet_target_prompt": "prompt417",
            "prompt416_execution_adapter_packet_mode": "blocked",
            "prompt416_execution_adapter_packet_prompt_id": "",
            "prompt416_execution_adapter_packet_prompt_path": "",
            "prompt416_execution_adapter_packet_result_json_path": "",
            "prompt416_execution_requested": False,
            "prompt416_execution_allowed": False,
            "prompt416_execution_attempted": False,
            "prompt416_execution_performed": False,
            "prompt416_execution_returncode": None,
            "prompt416_execution_returncode_classification": "not_run",
            "prompt416_capture_plan_ready": False,
            "prompt416_stdout_path": "",
            "prompt416_stderr_path": "",
            "prompt416_result_json_path": "",
            "prompt416_capture_written": False,
            "prompt416_approve_candidate": False,
            "prompt416_targeted_fix_required": False,
            "prompt416_retry_required": False,
            "prompt416_selected_prompt_execution_allowed": False,
            "prompt416_codex_invocation_allowed": False,
            "prompt416_git_mutation_allowed": False,
            "prompt416_commit_tag_allowed": False,
            "prompt416_next_action": (
                "review_prompt415_guarded_execution_enable_plan"
            ),
        }

    physical_prompt_path = _prompt416_validate_relative_path(
        run_state.get("prompt415_physical_prompt_path") or default_prompt_path
    )
    selected_prompt_text, selected_prompt_text_source = (
        _prompt416_selected_prompt_text(run_state)
    )
    selected_prompt_text_bytes = selected_prompt_text.encode("utf-8")
    selected_prompt_source = _normalize_text(
        run_state.get("prompt415_selected_prompt_source"),
        default="prompt402_generated_prompt_surface",
    )
    selected_prompt_sha256 = _prompt416_text_sha256(selected_prompt_text)
    if not physical_prompt_path:
        return {
            "prompt416_schema_version": _PROMPT416_SCHEMA_VERSION,
            "local_only": True,
            "source_prompt": "prompt416",
            "prompt416_physical_prompt_materialization_write_enabled": True,
            "prompt416_physical_prompt_materialization_write_status": "blocked",
            "prompt416_physical_prompt_materialization_write_ready": False,
            "prompt416_physical_prompt_materialization_write_blocked_reason": (
                "invalid_physical_prompt_path"
            ),
            "prompt416_physical_prompt_materialization_write_blocked_reasons": [
                "invalid_physical_prompt_path"
            ],
            "prompt416_physical_prompt_materialization_write_source": (
                "prompt415_guarded_execution_enable_plan"
            ),
            "prompt416_selected_prompt_id": "prompt402",
            "prompt416_selected_prompt_source": selected_prompt_source,
            "prompt416_selected_prompt_text_source": selected_prompt_text_source,
            "prompt416_selected_prompt_text_present": True,
            "prompt416_selected_prompt_text_size_bytes": len(
                selected_prompt_text_bytes
            ),
            "prompt416_selected_prompt_text_sha256": selected_prompt_sha256,
            "prompt416_physical_prompt_path": "",
            "prompt416_physical_prompt_write_requested": requested,
            "prompt416_physical_prompt_write_allowed": False,
            "prompt416_physical_prompt_written": False,
            "prompt416_physical_prompt_exists": False,
            "prompt416_physical_prompt_write_blocked_reason": (
                "invalid_physical_prompt_path"
            ),
            "prompt416_receipt_path": "",
            "prompt416_receipt_written": False,
            "prompt416_execution_adapter_packet_ready": False,
            "prompt416_execution_adapter_packet_target_prompt": "prompt417",
            "prompt416_execution_adapter_packet_mode": "blocked",
            "prompt416_execution_adapter_packet_prompt_id": "prompt402",
            "prompt416_execution_adapter_packet_prompt_path": "",
            "prompt416_execution_adapter_packet_result_json_path": (
                result_json_path
            ),
            "prompt416_execution_requested": False,
            "prompt416_execution_allowed": False,
            "prompt416_execution_attempted": False,
            "prompt416_execution_performed": False,
            "prompt416_execution_returncode": None,
            "prompt416_execution_returncode_classification": "not_run",
            "prompt416_capture_plan_ready": False,
            "prompt416_stdout_path": "",
            "prompt416_stderr_path": "",
            "prompt416_result_json_path": "",
            "prompt416_capture_written": False,
            "prompt416_approve_candidate": False,
            "prompt416_targeted_fix_required": False,
            "prompt416_retry_required": False,
            "prompt416_selected_prompt_execution_allowed": False,
            "prompt416_codex_invocation_allowed": False,
            "prompt416_git_mutation_allowed": False,
            "prompt416_commit_tag_allowed": False,
            "prompt416_next_action": "review_prompt416_physical_prompt_path",
        }

    written = False
    receipt_written = False
    write_blocked_reason = "write_not_requested_or_not_allowed"
    status = "ready"
    next_action = "request_prompt416_physical_prompt_write"
    adapter_ready = False
    adapter_mode = "physical_prompt_not_written"
    if requested_and_allowed and repo_path is None:
        write_blocked_reason = "repo_path_missing"
    elif requested_and_allowed:
        receipt = {
            "schema_version": _PROMPT416_SCHEMA_VERSION,
            "prompt_id": "prompt416",
            "status": "written",
            "selected_prompt_id": "prompt402",
            "selected_prompt_source": selected_prompt_source,
            "prompt_path": physical_prompt_path,
            "prompt_text_source": selected_prompt_text_source,
            "prompt_text_present": True,
            "prompt_text_size_bytes": len(selected_prompt_text_bytes),
            "prompt_text_sha256": selected_prompt_sha256,
            "write_requested": True,
            "write_allowed": True,
            "written": True,
            "execution_requested": False,
            "execution_allowed": False,
            "execution_attempted": False,
            "execution_performed": False,
            "codex_invocation_allowed": False,
            "commit_tag_allowed": False,
        }
        try:
            _prompt416_write_materialization_files(
                repo_path=repo_path,
                prompt_path=physical_prompt_path,
                selected_prompt_text=selected_prompt_text,
                receipt=receipt,
            )
        except OSError:
            status = "blocked"
            write_blocked_reason = "physical_prompt_write_failed"
            next_action = "review_prompt416_physical_prompt_write"
        else:
            written = True
            receipt_written = True
            write_blocked_reason = ""
            status = "written"
            next_action = (
                "prepare_prompt417_selected_prompt_codex_execution_adapter"
            )
            adapter_ready = True
            adapter_mode = "physical_prompt_written_no_execute"

    return {
        "prompt416_schema_version": _PROMPT416_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt416",
        "prompt416_physical_prompt_materialization_write_enabled": True,
        "prompt416_physical_prompt_materialization_write_status": status,
        "prompt416_physical_prompt_materialization_write_ready": (
            status in {"ready", "written"}
        ),
        "prompt416_physical_prompt_materialization_write_blocked_reason": (
            "" if status in {"ready", "written"} else write_blocked_reason
        ),
        "prompt416_physical_prompt_materialization_write_blocked_reasons": (
            [] if status in {"ready", "written"} else [write_blocked_reason]
        ),
        "prompt416_physical_prompt_materialization_write_source": (
            "prompt415_guarded_execution_enable_plan"
        ),
        "prompt416_selected_prompt_id": "prompt402",
        "prompt416_selected_prompt_source": selected_prompt_source,
        "prompt416_selected_prompt_text_source": selected_prompt_text_source,
        "prompt416_selected_prompt_text_present": True,
        "prompt416_selected_prompt_text_size_bytes": len(
            selected_prompt_text_bytes
        ),
        "prompt416_selected_prompt_text_sha256": selected_prompt_sha256,
        "prompt416_physical_prompt_path": physical_prompt_path,
        "prompt416_physical_prompt_write_requested": requested,
        "prompt416_physical_prompt_write_allowed": written,
        "prompt416_physical_prompt_written": written,
        "prompt416_physical_prompt_exists": written,
        "prompt416_physical_prompt_write_blocked_reason": write_blocked_reason,
        "prompt416_receipt_path": receipt_path,
        "prompt416_receipt_written": receipt_written,
        "prompt416_execution_adapter_packet_ready": adapter_ready,
        "prompt416_execution_adapter_packet_target_prompt": "prompt417",
        "prompt416_execution_adapter_packet_mode": adapter_mode,
        "prompt416_execution_adapter_packet_prompt_id": "prompt402",
        "prompt416_execution_adapter_packet_prompt_path": physical_prompt_path,
        "prompt416_execution_adapter_packet_result_json_path": result_json_path,
        "prompt416_execution_requested": False,
        "prompt416_execution_allowed": False,
        "prompt416_execution_attempted": False,
        "prompt416_execution_performed": False,
        "prompt416_execution_returncode": None,
        "prompt416_execution_returncode_classification": "not_run",
        "prompt416_capture_plan_ready": True,
        "prompt416_stdout_path": stdout_path,
        "prompt416_stderr_path": stderr_path,
        "prompt416_result_json_path": result_json_path,
        "prompt416_capture_written": False,
        "prompt416_approve_candidate": False,
        "prompt416_targeted_fix_required": False,
        "prompt416_retry_required": False,
        "prompt416_selected_prompt_execution_allowed": False,
        "prompt416_codex_invocation_allowed": False,
        "prompt416_git_mutation_allowed": False,
        "prompt416_commit_tag_allowed": False,
        "prompt416_next_action": next_action,
    }

def _build_prompt417_selected_prompt_codex_execution_adapter_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
    execute_requested: bool = False,
    allow_execute: bool = False,
    repo_path: str | Path | None = None,
    codex_command: Sequence[str] | None = None,
    timeout_seconds: int = 600,
    transport_runner: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    run_state = (
        dict(run_state_payload)
        if isinstance(run_state_payload, Mapping)
        else {}
    )
    requested = bool(execute_requested)
    stdout_path, stderr_path, result_json_path = _prompt417_capture_paths()
    prompt_path_source = "prompt416_execution_adapter_packet"
    packet_prompt_path = _normalize_text(
        run_state.get("prompt416_execution_adapter_packet_prompt_path"),
        default="",
    )
    fallback_prompt_path = _normalize_text(
        run_state.get("prompt416_physical_prompt_path"),
        default="",
    )
    raw_prompt_path = packet_prompt_path or fallback_prompt_path
    if not packet_prompt_path and fallback_prompt_path:
        prompt_path_source = "prompt416_physical_prompt_path"
    prompt_path = _prompt417_validate_prompt_path(raw_prompt_path)

    prompt416_required_inputs = (
        _normalize_text(
            run_state.get("prompt416_physical_prompt_materialization_write_status"),
            default="",
        )
        == "written",
        run_state.get("prompt416_physical_prompt_materialization_write_ready")
        is True,
        _normalize_text(run_state.get("prompt416_selected_prompt_id"), default="")
        == "prompt402",
        run_state.get("prompt416_physical_prompt_written") is True,
        run_state.get("prompt416_physical_prompt_exists") is True,
        run_state.get("prompt416_receipt_written") is True,
        run_state.get("prompt416_execution_adapter_packet_ready") is True,
        _normalize_text(
            run_state.get("prompt416_execution_adapter_packet_target_prompt"),
            default="",
        )
        == "prompt417",
        _normalize_text(
            run_state.get("prompt416_execution_adapter_packet_mode"),
            default="",
        )
        == "physical_prompt_written_no_execute",
        _normalize_text(
            run_state.get("prompt416_execution_adapter_packet_prompt_id"),
            default="",
        )
        == "prompt402",
        run_state.get("prompt416_execution_requested") is False,
        run_state.get("prompt416_execution_allowed") is False,
        run_state.get("prompt416_execution_attempted") is False,
        run_state.get("prompt416_execution_performed") is False,
        run_state.get("prompt416_execution_returncode") is None,
        _normalize_text(
            run_state.get("prompt416_execution_returncode_classification"),
            default="",
        )
        == "not_run",
        run_state.get("prompt416_capture_plan_ready") is True,
        run_state.get("prompt416_capture_written") is False,
        run_state.get("prompt416_approve_candidate") is False,
        run_state.get("prompt416_targeted_fix_required") is False,
        run_state.get("prompt416_retry_required") is False,
        run_state.get("prompt416_selected_prompt_execution_allowed") is False,
        run_state.get("prompt416_codex_invocation_allowed") is False,
        run_state.get("prompt416_git_mutation_allowed") is False,
        run_state.get("prompt416_commit_tag_allowed") is False,
        _normalize_text(run_state.get("prompt416_next_action"), default="")
        == "prepare_prompt417_selected_prompt_codex_execution_adapter",
    )
    prompt416_ready_except_path = all(prompt416_required_inputs)

    if not prompt416_ready_except_path:
        state = _prompt417_base_state(
            status="blocked",
            ready=False,
            blocked_reason="prompt416_execution_adapter_packet_not_ready",
            blocked_reasons=["prompt416_execution_adapter_packet_not_ready"],
            selected_prompt_id="",
            prompt_path="",
            prompt_path_valid=False,
            execute_requested=requested,
            stdout_path="",
            stderr_path="",
            result_json_path="",
        )
        state.update(
            {
                "prompt417_execution_status": "blocked",
                "prompt417_execution_blocked_reason": (
                    "prompt416_execution_adapter_packet_not_ready"
                ),
                "prompt417_review_packet_mode": "blocked",
                "prompt417_review_packet_prompt_id": "",
                "prompt417_review_packet_result_json_path": "",
                "prompt417_next_action": (
                    "review_prompt416_physical_prompt_materialization_write"
                ),
            }
        )
        return state

    if not prompt_path:
        state = _prompt417_base_state(
            status="blocked",
            ready=False,
            blocked_reason="invalid_prompt_path",
            blocked_reasons=["invalid_prompt_path"],
            selected_prompt_id="prompt402",
            prompt_path="",
            prompt_path_valid=False,
            execute_requested=requested,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            result_json_path=result_json_path,
        )
        state.update(
            {
                "prompt417_execution_status": "blocked",
                "prompt417_execution_blocked_reason": "invalid_prompt_path",
                "prompt417_review_packet_mode": "blocked",
                "prompt417_next_action": "review_prompt417_prompt_path",
            }
        )
        return state

    if not requested or not bool(allow_execute):
        state = _prompt417_base_state(
            status="ready",
            ready=True,
            blocked_reason="",
            blocked_reasons=[],
            selected_prompt_id="prompt402",
            prompt_path=prompt_path,
            prompt_path_valid=True,
            execute_requested=requested,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            result_json_path=result_json_path,
        )
        state.update(
            {
                "prompt417_selected_prompt_codex_execution_adapter_source": (
                    prompt_path_source
                ),
                "prompt417_execution_blocked_reason": (
                    "execution_not_requested_or_not_allowed"
                ),
            }
        )
        return state

    if repo_path is None:
        state = _prompt417_base_state(
            status="blocked",
            ready=False,
            blocked_reason="repo_path_missing",
            blocked_reasons=["repo_path_missing"],
            selected_prompt_id="prompt402",
            prompt_path=prompt_path,
            prompt_path_valid=True,
            execute_requested=requested,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            result_json_path=result_json_path,
        )
        state.update(
            {
                "prompt417_execution_status": "blocked",
                "prompt417_execution_blocked_reason": "repo_path_missing",
                "prompt417_review_packet_mode": "blocked",
                "prompt417_next_action": "review_prompt417_execution_request",
            }
        )
        return state

    command, command_error = _prompt417_normalize_command(codex_command)
    if command_error:
        state = _prompt417_base_state(
            status="blocked",
            ready=False,
            blocked_reason=command_error,
            blocked_reasons=[command_error],
            selected_prompt_id="prompt402",
            prompt_path=prompt_path,
            prompt_path_valid=True,
            execute_requested=requested,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            result_json_path=result_json_path,
        )
        state.update(
            {
                "prompt417_execution_status": "blocked",
                "prompt417_execution_blocked_reason": command_error,
                "prompt417_review_packet_mode": "blocked",
                "prompt417_next_action": "review_prompt417_execution_request",
            }
        )
        return state

    timeout = _prompt417_normalize_timeout(timeout_seconds)
    repo_root = Path(repo_path)
    prompt_file_path = repo_root / Path(prompt_path)
    try:
        prompt_stat = prompt_file_path.lstat()
    except FileNotFoundError:
        state = _prompt417_base_state(
            status="blocked",
            ready=False,
            blocked_reason="prompt_file_missing",
            blocked_reasons=["prompt_file_missing"],
            selected_prompt_id="prompt402",
            prompt_path=prompt_path,
            prompt_path_valid=True,
            execute_requested=requested,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            result_json_path=result_json_path,
        )
        state.update(
            {
                "prompt417_prompt_file_checked": True,
                "prompt417_execution_status": "blocked",
                "prompt417_execution_blocked_reason": "prompt_file_missing",
                "prompt417_review_packet_mode": "blocked",
                "prompt417_next_action": (
                    "review_prompt416_physical_prompt_materialization_write"
                ),
            }
        )
        return state
    if prompt_file_path.is_symlink():
        state = _prompt417_base_state(
            status="blocked",
            ready=False,
            blocked_reason="prompt_file_is_symlink",
            blocked_reasons=["prompt_file_is_symlink"],
            selected_prompt_id="prompt402",
            prompt_path=prompt_path,
            prompt_path_valid=True,
            execute_requested=requested,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            result_json_path=result_json_path,
        )
        state.update(
            {
                "prompt417_prompt_file_checked": True,
                "prompt417_execution_status": "blocked",
                "prompt417_execution_blocked_reason": "prompt_file_is_symlink",
                "prompt417_review_packet_mode": "blocked",
                "prompt417_next_action": "review_prompt417_prompt_path",
            }
        )
        return state
    if not prompt_file_path.is_file():
        state = _prompt417_base_state(
            status="blocked",
            ready=False,
            blocked_reason="prompt_file_missing",
            blocked_reasons=["prompt_file_missing"],
            selected_prompt_id="prompt402",
            prompt_path=prompt_path,
            prompt_path_valid=True,
            execute_requested=requested,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            result_json_path=result_json_path,
        )
        state.update(
            {
                "prompt417_prompt_file_checked": True,
                "prompt417_execution_status": "blocked",
                "prompt417_execution_blocked_reason": "prompt_file_missing",
                "prompt417_review_packet_mode": "blocked",
                "prompt417_next_action": (
                    "review_prompt416_physical_prompt_materialization_write"
                ),
            }
        )
        return state

    prompt_text = prompt_file_path.read_text(encoding="utf-8")
    prompt_text_size_bytes = len(prompt_text.encode("utf-8"))
    prompt_text_sha256 = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()
    stdout_text = ""
    stderr_text = ""
    returncode: int | None = None
    execution_error_type = ""
    execution_error_message = ""
    execution_attempted = True
    execution_performed = False
    execution_status = "completed"
    returncode_classification = "not_run"

    try:
        if transport_runner is not None:
            result = transport_runner(
                command=command,
                input=prompt_text,
                timeout=timeout,
                cwd=str(repo_root),
            )
        else:
            result = subprocess.run(
                command,
                input=prompt_text,
                timeout=timeout,
                cwd=str(repo_root),
                shell=False,
                capture_output=True,
                text=True,
                check=False,
            )
        returncode, stdout_text, stderr_text = (
            _prompt417_normalize_transport_result(result)
        )
        execution_performed = True
        returncode_classification = _prompt417_returncode_classification(
            returncode
        )
    except (TimeoutError, subprocess.TimeoutExpired) as exc:
        execution_status = "timeout"
        returncode_classification = "timeout"
        execution_error_type = type(exc).__name__
        execution_error_message = str(exc)
        if isinstance(exc, subprocess.TimeoutExpired):
            if isinstance(exc.stdout, bytes):
                stdout_text = exc.stdout.decode("utf-8", errors="replace")
            elif exc.stdout is not None:
                stdout_text = str(exc.stdout)
            if isinstance(exc.stderr, bytes):
                stderr_text = exc.stderr.decode("utf-8", errors="replace")
            elif exc.stderr is not None:
                stderr_text = str(exc.stderr)
    except Exception as exc:
        execution_status = "execution_error"
        returncode_classification = "execution_error"
        execution_error_type = type(exc).__name__
        execution_error_message = str(exc)

    result_payload = {
        "schema_version": _PROMPT417_SCHEMA_VERSION,
        "prompt_id": "prompt417",
        "status": execution_status,
        "selected_prompt_id": "prompt402",
        "prompt_path": prompt_path,
        "prompt_text_size_bytes": prompt_text_size_bytes,
        "prompt_text_sha256": prompt_text_sha256,
        "command": list(command),
        "shell": False,
        "timeout_seconds": timeout,
        "execution_requested": True,
        "execution_allowed": True,
        "execution_attempted": execution_attempted,
        "execution_performed": execution_performed,
        "returncode": returncode,
        "returncode_classification": returncode_classification,
        "execution_status": execution_status,
        "execution_error_type": execution_error_type,
        "execution_error_message": execution_error_message,
        "stdout_path": stdout_path,
        "stderr_path": stderr_path,
        "result_json_path": result_json_path,
        "stdout_size_bytes": len(stdout_text.encode("utf-8")),
        "stderr_size_bytes": len(stderr_text.encode("utf-8")),
        "approve_candidate": False,
        "targeted_fix_required": False,
        "retry_required": False,
        "codex_invocation_allowed": False,
        "commit_tag_allowed": False,
    }

    stdout_written = False
    stderr_written = False
    result_json_written = False
    try:
        _prompt417_write_capture_text(
            repo_root=repo_root,
            relative_path=stdout_path,
            text=stdout_text,
        )
        stdout_written = True
        _prompt417_write_capture_text(
            repo_root=repo_root,
            relative_path=stderr_path,
            text=stderr_text,
        )
        stderr_written = True
        _prompt417_write_result_json(
            repo_root=repo_root,
            relative_path=result_json_path,
            payload=result_payload,
        )
        result_json_written = True
    except OSError as exc:
        if not execution_error_type:
            execution_error_type = type(exc).__name__
            execution_error_message = str(exc)
        if returncode_classification not in {"timeout", "execution_error"}:
            returncode_classification = "execution_error"
            execution_status = "execution_error"

    review_packet_ready = result_json_written
    return {
        "prompt417_schema_version": _PROMPT417_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt417",
        "prompt417_selected_prompt_codex_execution_adapter_enabled": True,
        "prompt417_selected_prompt_codex_execution_adapter_status": "executed",
        "prompt417_selected_prompt_codex_execution_adapter_ready": True,
        "prompt417_selected_prompt_codex_execution_adapter_blocked_reason": "",
        "prompt417_selected_prompt_codex_execution_adapter_blocked_reasons": [],
        "prompt417_selected_prompt_codex_execution_adapter_source": (
            prompt_path_source
        ),
        "prompt417_selected_prompt_id": "prompt402",
        "prompt417_prompt_path": prompt_path,
        "prompt417_prompt_path_valid": True,
        "prompt417_prompt_file_required": True,
        "prompt417_prompt_file_checked": True,
        "prompt417_prompt_file_exists": bool(prompt_stat),
        "prompt417_prompt_file_read": True,
        "prompt417_prompt_text_size_bytes": prompt_text_size_bytes,
        "prompt417_prompt_text_sha256": prompt_text_sha256,
        "prompt417_execution_requested": True,
        "prompt417_execution_allowed": True,
        "prompt417_execution_attempted": execution_attempted,
        "prompt417_execution_performed": execution_performed,
        "prompt417_execution_returncode": returncode,
        "prompt417_execution_returncode_classification": (
            returncode_classification
        ),
        "prompt417_execution_status": execution_status,
        "prompt417_execution_blocked_reason": "",
        "prompt417_stdout_path": stdout_path,
        "prompt417_stderr_path": stderr_path,
        "prompt417_result_json_path": result_json_path,
        "prompt417_stdout_written": stdout_written,
        "prompt417_stderr_written": stderr_written,
        "prompt417_result_json_written": result_json_written,
        "prompt417_capture_written": (
            stdout_written and stderr_written and result_json_written
        ),
        "prompt417_review_packet_ready": review_packet_ready,
        "prompt417_review_packet_target_prompt": "prompt418",
        "prompt417_review_packet_mode": (
            "execution_result_captured" if review_packet_ready else "blocked"
        ),
        "prompt417_review_packet_prompt_id": "prompt402",
        "prompt417_review_packet_result_json_path": (
            result_json_path if review_packet_ready else ""
        ),
        "prompt417_approve_candidate": False,
        "prompt417_targeted_fix_required": False,
        "prompt417_retry_required": False,
        "prompt417_selected_prompt_execution_allowed": False,
        "prompt417_codex_invocation_allowed": False,
        "prompt417_git_mutation_allowed": False,
        "prompt417_commit_tag_allowed": False,
        "prompt417_next_action": (
            "prepare_prompt418_execution_result_review"
            if review_packet_ready
            else "review_prompt417_execution_error"
        ),
    }

def _build_prompt418_execution_result_review_and_success_route_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    run_state = (
        dict(run_state_payload)
        if isinstance(run_state_payload, Mapping)
        else {}
    )
    result_json_path = _normalize_text(
        run_state.get("prompt417_review_packet_result_json_path"),
        default="",
    )
    stdout_path = _normalize_text(run_state.get("prompt417_stdout_path"), default="")
    stderr_path = _normalize_text(run_state.get("prompt417_stderr_path"), default="")
    returncode = run_state.get("prompt417_execution_returncode")
    returncode_classification = _normalize_text(
        run_state.get("prompt417_execution_returncode_classification"),
        default="",
    )
    execution_status = _normalize_text(
        run_state.get("prompt417_execution_status"),
        default="",
    )
    prompt417_ready = (
        _normalize_text(
            run_state.get("prompt417_selected_prompt_codex_execution_adapter_status"),
            default="",
        )
        == "executed"
        and run_state.get("prompt417_selected_prompt_codex_execution_adapter_ready")
        is True
        and _normalize_text(run_state.get("prompt417_selected_prompt_id"), default="")
        == "prompt402"
        and run_state.get("prompt417_prompt_path_valid") is True
        and run_state.get("prompt417_prompt_file_required") is True
        and run_state.get("prompt417_prompt_file_checked") is True
        and run_state.get("prompt417_prompt_file_exists") is True
        and run_state.get("prompt417_prompt_file_read") is True
        and run_state.get("prompt417_execution_requested") is True
        and run_state.get("prompt417_execution_allowed") is True
        and run_state.get("prompt417_execution_attempted") is True
        and run_state.get("prompt417_execution_performed") is True
        and execution_status in {"completed", "timeout", "execution_error"}
        and returncode_classification
        in {"success", "failed", "timeout", "execution_error"}
        and run_state.get("prompt417_stdout_written") is True
        and run_state.get("prompt417_stderr_written") is True
        and run_state.get("prompt417_result_json_written") is True
        and run_state.get("prompt417_capture_written") is True
        and run_state.get("prompt417_review_packet_ready") is True
        and _normalize_text(
            run_state.get("prompt417_review_packet_target_prompt"),
            default="",
        )
        == "prompt418"
        and _normalize_text(
            run_state.get("prompt417_review_packet_mode"),
            default="",
        )
        == "execution_result_captured"
        and _normalize_text(
            run_state.get("prompt417_review_packet_prompt_id"),
            default="",
        )
        == "prompt402"
        and bool(result_json_path)
        and run_state.get("prompt417_approve_candidate") is False
        and run_state.get("prompt417_selected_prompt_execution_allowed") is False
        and run_state.get("prompt417_commit_tag_allowed") is False
        and run_state.get("prompt417_git_mutation_allowed") is False
        and run_state.get("prompt417_codex_invocation_allowed") is False
        and _normalize_text(run_state.get("prompt417_next_action"), default="")
        == "prepare_prompt418_execution_result_review"
    )
    success = (
        prompt417_ready
        and returncode == 0
        and returncode_classification == "success"
        and execution_status == "completed"
        and _normalize_text(
            run_state.get("prompt417_execution_blocked_reason"),
            default="",
        )
        == ""
        and run_state.get("prompt417_result_json_written") is True
        and run_state.get("prompt417_capture_written") is True
    )
    failed = (
        prompt417_ready
        and isinstance(returncode, int)
        and not isinstance(returncode, bool)
        and returncode != 0
        and returncode_classification == "failed"
        and execution_status == "completed"
    )
    timeout = (
        prompt417_ready
        and returncode is None
        and returncode_classification == "timeout"
        and execution_status == "timeout"
    )
    execution_error = (
        prompt417_ready
        and returncode is None
        and returncode_classification == "execution_error"
        and execution_status == "execution_error"
    )

    state: dict[str, Any] = {
        "prompt418_schema_version": _PROMPT418_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt418",
        "prompt418_execution_result_review_enabled": True,
        "prompt418_execution_result_review_status": "blocked",
        "prompt418_execution_result_review_ready": False,
        "prompt418_execution_result_review_blocked_reason": (
            "prompt417_execution_result_capture_not_ready"
        ),
        "prompt418_execution_result_review_blocked_reasons": [
            "prompt417_execution_result_capture_not_ready"
        ],
        "prompt418_execution_result_review_source": "prompt417_review_packet",
        "prompt418_selected_prompt_id": "",
        "prompt418_result_json_path": "",
        "prompt418_stdout_path": "",
        "prompt418_stderr_path": "",
        "prompt418_execution_review_classification": "blocked",
        "prompt418_execution_review_route": (
            "review_prompt417_selected_prompt_codex_execution_adapter"
        ),
        "prompt418_execution_result_available": False,
        "prompt418_execution_success": False,
        "prompt418_execution_failed": False,
        "prompt418_execution_timeout": False,
        "prompt418_execution_error": False,
        "prompt418_execution_not_run": True,
        "prompt418_execution_returncode": None,
        "prompt418_execution_returncode_classification": "not_run",
        "prompt418_execution_status": "blocked",
        "prompt418_approve_candidate": False,
        "prompt418_approve_reason": "",
        "prompt418_targeted_fix_required": False,
        "prompt418_retry_required": False,
        "prompt418_stop_required": False,
        "prompt418_failure_route_ready": False,
        "prompt418_failure_route_reason": "",
        "prompt418_failure_route_target_prompt": "",
        "prompt418_commit_tag_plan_ready": False,
        "prompt418_commit_tag_plan_target_prompt": "prompt419",
        "prompt418_commit_tag_plan_mode": "blocked",
        "prompt418_commit_tag_plan_selected_prompt_id": "",
        "prompt418_commit_tag_plan_source_result_json_path": "",
        "prompt418_commit_tag_plan_commit_message": "",
        "prompt418_commit_tag_plan_tag_name": "",
        "prompt418_commit_tag_plan_allowed": False,
        "prompt418_commit_tag_plan_performed": False,
        "prompt418_success_handoff_ready": False,
        "prompt418_success_handoff_target_prompt": "prompt419",
        "prompt418_success_handoff_mode": "blocked",
        "prompt418_success_handoff_selected_prompt_id": "",
        "prompt418_success_handoff_next_cycle_target_prompt": "",
        "prompt418_next_cycle_plan_ready": False,
        "prompt418_next_cycle_plan_target_prompt": "prompt420",
        "prompt418_next_cycle_plan_mode": "blocked",
        "prompt418_next_cycle_plan_allowed": False,
        "prompt418_next_cycle_started": False,
        "prompt418_selected_prompt_execution_allowed": False,
        "prompt418_codex_invocation_allowed": False,
        "prompt418_git_mutation_allowed": False,
        "prompt418_commit_tag_allowed": False,
        "prompt418_commit_tag_performed": False,
        "prompt418_push_allowed": False,
        "prompt418_pr_allowed": False,
        "prompt418_merge_allowed": False,
        "prompt418_rollback_allowed": False,
        "prompt418_next_action": (
            "review_prompt417_selected_prompt_codex_execution_adapter"
        ),
    }

    if not prompt417_ready:
        return state

    state.update(
        {
            "prompt418_execution_result_review_ready": True,
            "prompt418_execution_result_review_blocked_reason": "",
            "prompt418_execution_result_review_blocked_reasons": [],
            "prompt418_selected_prompt_id": "prompt402",
            "prompt418_result_json_path": result_json_path,
            "prompt418_stdout_path": stdout_path,
            "prompt418_stderr_path": stderr_path,
            "prompt418_execution_result_available": True,
            "prompt418_execution_not_run": False,
            "prompt418_execution_returncode": returncode,
            "prompt418_execution_returncode_classification": (
                returncode_classification
            ),
            "prompt418_execution_status": execution_status,
        }
    )

    if success:
        state.update(
            {
                "prompt418_execution_result_review_status": "approved",
                "prompt418_execution_review_classification": "success",
                "prompt418_execution_review_route": "approve_commit_tag_plan",
                "prompt418_execution_success": True,
                "prompt418_execution_returncode": 0,
                "prompt418_execution_returncode_classification": "success",
                "prompt418_execution_status": "completed",
                "prompt418_approve_candidate": True,
                "prompt418_approve_reason": (
                    "selected_prompt_execution_returncode_success"
                ),
                "prompt418_commit_tag_plan_ready": True,
                "prompt418_commit_tag_plan_mode": (
                    "success_only_guarded_commit_tag_plan"
                ),
                "prompt418_commit_tag_plan_selected_prompt_id": "prompt402",
                "prompt418_commit_tag_plan_source_result_json_path": (
                    result_json_path
                ),
                "prompt418_commit_tag_plan_commit_message": (
                    "Prompt402 apply selected prompt execution result"
                ),
                "prompt418_commit_tag_plan_tag_name": (
                    "prompt402-selected-prompt-execution-result"
                ),
                "prompt418_success_handoff_ready": True,
                "prompt418_success_handoff_mode": (
                    "approve_candidate_to_commit_tag_boundary"
                ),
                "prompt418_success_handoff_selected_prompt_id": "prompt402",
                "prompt418_success_handoff_next_cycle_target_prompt": (
                    "prompt420"
                ),
                "prompt418_next_cycle_plan_ready": True,
                "prompt418_next_cycle_plan_mode": (
                    "success_only_bounded_next_cycle_plan"
                ),
                "prompt418_next_action": (
                    "prepare_prompt419_approve_commit_tag_and_success_loop_boundary"
                ),
            }
        )
    elif failed:
        state.update(
            {
                "prompt418_execution_result_review_status": "failed",
                "prompt418_execution_review_classification": "failed",
                "prompt418_execution_review_route": "targeted_fix_required",
                "prompt418_execution_failed": True,
                "prompt418_targeted_fix_required": True,
                "prompt418_retry_required": True,
                "prompt418_failure_route_ready": True,
                "prompt418_failure_route_reason": (
                    "selected_prompt_execution_failed"
                ),
                "prompt418_failure_route_target_prompt": "prompt421",
                "prompt418_commit_tag_plan_mode": "blocked_failure",
                "prompt418_success_handoff_mode": "blocked_failure",
                "prompt418_next_cycle_plan_mode": "blocked_failure",
                "prompt418_next_action": "prepare_prompt421_targeted_fix_route",
            }
        )
    elif timeout:
        state.update(
            {
                "prompt418_execution_result_review_status": "timeout",
                "prompt418_execution_review_classification": "timeout",
                "prompt418_execution_review_route": "targeted_fix_required",
                "prompt418_execution_timeout": True,
                "prompt418_execution_returncode": None,
                "prompt418_targeted_fix_required": True,
                "prompt418_retry_required": True,
                "prompt418_failure_route_ready": True,
                "prompt418_failure_route_reason": (
                    "selected_prompt_execution_timeout"
                ),
                "prompt418_failure_route_target_prompt": "prompt421",
                "prompt418_commit_tag_plan_mode": "blocked_failure",
                "prompt418_success_handoff_mode": "blocked_failure",
                "prompt418_next_cycle_plan_mode": "blocked_failure",
                "prompt418_next_action": "prepare_prompt421_targeted_fix_route",
            }
        )
    elif execution_error:
        state.update(
            {
                "prompt418_execution_result_review_status": "execution_error",
                "prompt418_execution_review_classification": "execution_error",
                "prompt418_execution_review_route": "targeted_fix_required",
                "prompt418_execution_error": True,
                "prompt418_execution_returncode": None,
                "prompt418_targeted_fix_required": True,
                "prompt418_retry_required": True,
                "prompt418_failure_route_ready": True,
                "prompt418_failure_route_reason": (
                    "selected_prompt_execution_error"
                ),
                "prompt418_failure_route_target_prompt": "prompt421",
                "prompt418_commit_tag_plan_mode": "blocked_failure",
                "prompt418_success_handoff_mode": "blocked_failure",
                "prompt418_next_cycle_plan_mode": "blocked_failure",
                "prompt418_next_action": "prepare_prompt421_targeted_fix_route",
            }
        )

    return state

def _build_prompt419_approve_commit_tag_and_success_loop_boundary_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
    commit_tag_requested: bool = False,
    allow_git_mutation: bool = False,
    repo_path: str | Path | None = None,
    git_runner: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    run_state = (
        dict(run_state_payload)
        if isinstance(run_state_payload, Mapping)
        else {}
    )
    receipt_relative_path = (
        "current_prompt_verify_results/prompt419/commit_tag_receipt.json"
    )
    state: dict[str, Any] = {
        "prompt419_schema_version": _PROMPT419_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt419",
        "prompt419_approve_commit_tag_boundary_enabled": True,
        "prompt419_approve_commit_tag_boundary_status": "blocked",
        "prompt419_approve_commit_tag_boundary_ready": False,
        "prompt419_approve_commit_tag_boundary_blocked_reason": (
            "prompt418_success_approval_not_ready"
        ),
        "prompt419_approve_commit_tag_boundary_blocked_reasons": [
            "prompt418_success_approval_not_ready"
        ],
        "prompt419_approve_commit_tag_boundary_source": (
            "prompt418_commit_tag_plan"
        ),
        "prompt419_selected_prompt_id": "",
        "prompt419_approve_candidate": False,
        "prompt419_approve_reason": "",
        "prompt419_commit_tag_requested": bool(commit_tag_requested),
        "prompt419_git_mutation_allowed": False,
        "prompt419_commit_tag_allowed": False,
        "prompt419_commit_tag_attempted": False,
        "prompt419_commit_tag_performed": False,
        "prompt419_commit_performed": False,
        "prompt419_tag_performed": False,
        "prompt419_commit_returncode": None,
        "prompt419_tag_returncode": None,
        "prompt419_commit_tag_status": "blocked",
        "prompt419_commit_tag_blocked_reason": (
            "prompt418_success_approval_not_ready"
        ),
        "prompt419_commit_message": "",
        "prompt419_tag_name": "",
        "prompt419_commit_tag_receipt_ready": False,
        "prompt419_commit_tag_receipt_written": False,
        "prompt419_commit_tag_receipt_path": "",
        "prompt419_success_loop_packet_ready": False,
        "prompt419_success_loop_packet_target_prompt": "prompt420",
        "prompt419_success_loop_packet_mode": "blocked",
        "prompt419_success_loop_packet_selected_prompt_id": "",
        "prompt419_success_loop_packet_commit_tag_status": "blocked",
        "prompt419_next_cycle_plan_ready": False,
        "prompt419_next_cycle_plan_target_prompt": "prompt420",
        "prompt419_next_cycle_plan_mode": "blocked",
        "prompt419_next_cycle_allowed": False,
        "prompt419_next_cycle_started": False,
        "prompt419_targeted_fix_required": False,
        "prompt419_retry_required": False,
        "prompt419_stop_required": False,
        "prompt419_push_allowed": False,
        "prompt419_pr_allowed": False,
        "prompt419_merge_allowed": False,
        "prompt419_rollback_allowed": False,
        "prompt419_next_action": "review_prompt418_execution_result_review",
    }

    if not _prompt419_success_approval_ready(run_state):
        return state

    commit_message = _normalize_text(
        run_state.get("prompt418_commit_tag_plan_commit_message"),
        default="",
    ).strip()
    tag_name = _normalize_text(
        run_state.get("prompt418_commit_tag_plan_tag_name"),
        default="",
    ).strip()
    plan_valid = _prompt419_commit_tag_plan_valid(
        run_state=run_state,
        commit_message=commit_message,
        tag_name=tag_name,
    )
    state.update(
        {
            "prompt419_approve_commit_tag_boundary_status": "ready",
            "prompt419_approve_commit_tag_boundary_ready": True,
            "prompt419_approve_commit_tag_boundary_blocked_reason": "",
            "prompt419_approve_commit_tag_boundary_blocked_reasons": [],
            "prompt419_selected_prompt_id": "prompt402",
            "prompt419_approve_candidate": True,
            "prompt419_approve_reason": (
                "selected_prompt_execution_returncode_success"
            ),
            "prompt419_commit_tag_status": "not_run",
            "prompt419_commit_tag_blocked_reason": (
                "commit_tag_not_requested_or_not_allowed"
            ),
            "prompt419_commit_message": commit_message,
            "prompt419_tag_name": tag_name,
            "prompt419_commit_tag_receipt_path": receipt_relative_path,
            "prompt419_success_loop_packet_mode": "commit_tag_not_performed",
            "prompt419_success_loop_packet_selected_prompt_id": "prompt402",
            "prompt419_success_loop_packet_commit_tag_status": "not_run",
            "prompt419_next_cycle_plan_ready": True,
            "prompt419_next_cycle_plan_mode": (
                "success_only_bounded_next_cycle_plan"
            ),
            "prompt419_next_action": (
                "request_prompt419_approve_commit_tag_execution"
            ),
        }
    )

    if not plan_valid:
        state.update(
            {
                "prompt419_approve_commit_tag_boundary_status": "blocked",
                "prompt419_approve_commit_tag_boundary_ready": False,
                "prompt419_approve_commit_tag_boundary_blocked_reason": (
                    "invalid_commit_tag_plan"
                ),
                "prompt419_approve_commit_tag_boundary_blocked_reasons": [
                    "invalid_commit_tag_plan"
                ],
                "prompt419_commit_tag_status": "blocked",
                "prompt419_commit_tag_blocked_reason": "invalid_commit_tag_plan",
                "prompt419_commit_tag_performed": False,
                "prompt419_success_loop_packet_ready": False,
                "prompt419_success_loop_packet_mode": "blocked",
                "prompt419_success_loop_packet_commit_tag_status": "blocked",
                "prompt419_next_action": "review_prompt418_commit_tag_plan",
            }
        )
        return state

    if not (commit_tag_requested and allow_git_mutation and repo_path is not None):
        return state

    repo_root = Path(repo_path)
    commands: list[list[str]] = [
        ["git", "status", "--short"],
        ["git", "add", "automation/orchestration/planned_execution_runner.py"],
        ["git", "commit", "-m", commit_message],
        ["git", "tag", tag_name],
        ["git", "tag", "--points-at", "HEAD"],
    ]
    command_results: list[dict[str, Any]] = []
    execution_exception = ""
    state.update(
        {
            "prompt419_git_mutation_allowed": True,
            "prompt419_commit_tag_allowed": True,
            "prompt419_commit_tag_attempted": True,
            "prompt419_commit_tag_blocked_reason": "",
        }
    )
    try:
        for command in commands:
            if command == ["git", "tag", tag_name]:
                commit_returncode = state.get("prompt419_commit_returncode")
                if commit_returncode != 0:
                    break
            result = _prompt419_run_git_command(
                command=command,
                cwd=str(repo_root),
                timeout=30,
                git_runner=git_runner,
                commit_message=commit_message,
                tag_name=tag_name,
            )
            command_results.append(result)
            if command[:3] == ["git", "commit", "-m"]:
                state["prompt419_commit_returncode"] = result.get("returncode")
                state["prompt419_commit_performed"] = (
                    result.get("returncode") == 0
                )
            elif command == ["git", "tag", tag_name]:
                state["prompt419_tag_returncode"] = result.get("returncode")
                state["prompt419_tag_performed"] = result.get("returncode") == 0
            if command[:3] == ["git", "commit", "-m"] and result.get(
                "returncode"
            ) != 0:
                break
            if command == ["git", "tag", tag_name] and result.get(
                "returncode"
            ) != 0:
                break
            if command in (
                ["git", "status", "--short"],
                ["git", "add", "automation/orchestration/planned_execution_runner.py"],
            ) and result.get("returncode") != 0:
                break
    except Exception as exc:  # noqa: BLE001 - serialized into guarded receipt.
        execution_exception = str(exc)
        state.update(
            {
                "prompt419_commit_tag_status": "execution_error",
                "prompt419_commit_tag_performed": False,
                "prompt419_success_loop_packet_ready": False,
                "prompt419_success_loop_packet_mode": "blocked",
                "prompt419_success_loop_packet_commit_tag_status": (
                    "execution_error"
                ),
                "prompt419_next_action": "review_prompt419_commit_tag_failure",
            }
        )
    else:
        commit_performed = state.get("prompt419_commit_performed") is True
        tag_performed = state.get("prompt419_tag_performed") is True
        commit_tag_performed = commit_performed and tag_performed
        state.update(
            {
                "prompt419_commit_tag_performed": commit_tag_performed,
                "prompt419_commit_tag_status": (
                    "performed" if commit_tag_performed else "failed"
                ),
                "prompt419_approve_commit_tag_boundary_status": (
                    "performed" if commit_tag_performed else "ready"
                ),
                "prompt419_success_loop_packet_ready": commit_tag_performed,
                "prompt419_success_loop_packet_mode": (
                    "commit_tag_performed_success_loop_ready"
                    if commit_tag_performed
                    else "commit_tag_not_performed"
                ),
                "prompt419_success_loop_packet_commit_tag_status": (
                    "performed" if commit_tag_performed else "failed"
                ),
                "prompt419_next_action": (
                    "prepare_prompt420_success_only_next_cycle_loop"
                    if commit_tag_performed
                    else "review_prompt419_commit_tag_failure"
                ),
            }
        )

    receipt_status = _normalize_text(
        state.get("prompt419_commit_tag_status"),
        default="execution_error",
    )
    receipt_payload: dict[str, Any] = {
        "schema_version": _PROMPT419_SCHEMA_VERSION,
        "prompt_id": "prompt419",
        "status": receipt_status,
        "selected_prompt_id": "prompt402",
        "commit_message": commit_message,
        "tag_name": tag_name,
        "commit_tag_requested": True,
        "git_mutation_allowed": True,
        "commit_tag_allowed": True,
        "commit_tag_attempted": True,
        "commit_tag_performed": state.get("prompt419_commit_tag_performed")
        is True,
        "commit_performed": state.get("prompt419_commit_performed") is True,
        "tag_performed": state.get("prompt419_tag_performed") is True,
        "commands": commands,
        "command_results": command_results,
        "push_allowed": False,
        "pr_allowed": False,
        "merge_allowed": False,
        "rollback_allowed": False,
        "next_cycle_started": False,
    }
    if execution_exception:
        receipt_payload["execution_exception"] = execution_exception
    state["prompt419_commit_tag_receipt_ready"] = True
    state["prompt419_commit_tag_receipt_written"] = (
        _prompt419_write_commit_tag_receipt(
            repo_root=repo_root,
            receipt=receipt_payload,
        )
    )
    return state

def _build_prompt420_success_only_next_cycle_loop_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
    start_next_cycle_requested: bool = False,
    allow_next_cycle: bool = False,
    max_success_cycles: int = 2,
    current_success_cycle: int | None = None,
) -> dict[str, Any]:
    run_state = (
        dict(run_state_payload)
        if isinstance(run_state_payload, Mapping)
        else {}
    )
    normalized_max_success_cycles = _prompt420_normalize_cycle_value(
        max_success_cycles,
        field_name="max_success_cycles",
        minimum=1,
    )
    if current_success_cycle is None:
        derived_current_success_cycle = run_state.get(
            "prompt420_success_cycle_current",
            0,
        )
    else:
        derived_current_success_cycle = current_success_cycle
    normalized_current_success_cycle = _prompt420_normalize_cycle_value(
        derived_current_success_cycle,
        field_name="current_success_cycle",
        minimum=0,
    )
    next_success_cycle = normalized_current_success_cycle + 1
    remaining_success_cycles = max(
        normalized_max_success_cycles - normalized_current_success_cycle,
        0,
    )
    prompt419_ready = _prompt420_prompt419_success_loop_packet_ready(run_state)

    state: dict[str, Any] = {
        "prompt420_schema_version": _PROMPT420_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt420",
        "prompt420_success_only_next_cycle_loop_enabled": True,
        "prompt420_success_only_next_cycle_loop_status": "blocked",
        "prompt420_success_only_next_cycle_loop_ready": False,
        "prompt420_success_only_next_cycle_loop_blocked_reason": (
            "prompt419_success_loop_packet_not_ready"
        ),
        "prompt420_success_only_next_cycle_loop_blocked_reasons": [
            "prompt419_success_loop_packet_not_ready"
        ],
        "prompt420_success_only_next_cycle_loop_source": (
            "prompt419_success_loop_packet"
        ),
        "prompt420_selected_prompt_id": "",
        "prompt420_previous_cycle_completed": False,
        "prompt420_previous_cycle_commit_tag_performed": False,
        "prompt420_success_cycle_current": 0,
        "prompt420_success_cycle_next": 0,
        "prompt420_success_cycle_max": normalized_max_success_cycles,
        "prompt420_success_cycle_remaining": normalized_max_success_cycles,
        "prompt420_bounded_loop_ready": False,
        "prompt420_bounded_loop_continue_allowed": False,
        "prompt420_bounded_loop_started": False,
        "prompt420_bounded_loop_stop_required": False,
        "prompt420_next_prompt_selection_ready": False,
        "prompt420_next_prompt_selection_requested": bool(
            start_next_cycle_requested
        ),
        "prompt420_next_prompt_selection_allowed": False,
        "prompt420_next_prompt_selection_started": False,
        "prompt420_next_prompt_selection_target_prompt": "prompt402",
        "prompt420_next_prompt_selection_mode": "blocked",
        "prompt420_next_prompt_selection_reason": (
            "prompt419_success_loop_packet_not_ready"
        ),
        "prompt420_success_only_autonomous_loop_ready": False,
        "prompt420_success_only_autonomous_loop_completed": False,
        "prompt420_success_only_autonomous_loop_scope": "success_only",
        "prompt420_full_autonomous_loop_ready": False,
        "prompt420_full_autonomous_loop_blocked_reason": (
            "prompt419_success_loop_packet_not_ready"
        ),
        "prompt420_targeted_fix_required": False,
        "prompt420_targeted_fix_integrated": False,
        "prompt420_retry_required": False,
        "prompt420_stop_required": False,
        "prompt420_selected_prompt_execution_allowed": False,
        "prompt420_codex_invocation_allowed": False,
        "prompt420_git_mutation_allowed": False,
        "prompt420_commit_tag_allowed": False,
        "prompt420_push_allowed": False,
        "prompt420_pr_allowed": False,
        "prompt420_merge_allowed": False,
        "prompt420_rollback_allowed": False,
        "prompt420_next_action": (
            "review_prompt419_approve_commit_tag_and_success_loop_boundary"
        ),
    }

    if not prompt419_ready:
        return state

    state.update(
        {
            "prompt420_success_only_next_cycle_loop_status": "ready",
            "prompt420_success_only_next_cycle_loop_ready": True,
            "prompt420_success_only_next_cycle_loop_blocked_reason": "",
            "prompt420_success_only_next_cycle_loop_blocked_reasons": [],
            "prompt420_selected_prompt_id": "prompt402",
            "prompt420_previous_cycle_completed": True,
            "prompt420_previous_cycle_commit_tag_performed": True,
            "prompt420_success_cycle_current": normalized_current_success_cycle,
            "prompt420_success_cycle_next": next_success_cycle,
            "prompt420_success_cycle_max": normalized_max_success_cycles,
            "prompt420_success_cycle_remaining": remaining_success_cycles,
            "prompt420_bounded_loop_ready": True,
            "prompt420_next_prompt_selection_ready": True,
            "prompt420_next_prompt_selection_mode": (
                "success_only_return_to_prompt_selection"
            ),
            "prompt420_next_prompt_selection_reason": (
                "previous_cycle_success_commit_tag_performed"
            ),
            "prompt420_success_only_autonomous_loop_ready": True,
            "prompt420_success_only_autonomous_loop_completed": True,
            "prompt420_full_autonomous_loop_blocked_reason": (
                "targeted_fix_route_not_integrated"
            ),
            "prompt420_next_action": (
                "request_prompt420_success_only_next_cycle_start"
            ),
        }
    )

    if next_success_cycle > normalized_max_success_cycles:
        state.update(
            {
                "prompt420_success_only_next_cycle_loop_status": "stopped",
                "prompt420_bounded_loop_continue_allowed": False,
                "prompt420_bounded_loop_started": False,
                "prompt420_bounded_loop_stop_required": True,
                "prompt420_next_prompt_selection_ready": False,
                "prompt420_next_prompt_selection_allowed": False,
                "prompt420_next_prompt_selection_started": False,
                "prompt420_stop_required": True,
                "prompt420_next_action": (
                    "stop_success_only_loop_max_cycles_reached"
                ),
            }
        )
        return state

    if start_next_cycle_requested and allow_next_cycle:
        state.update(
            {
                "prompt420_success_only_next_cycle_loop_status": "started",
                "prompt420_bounded_loop_continue_allowed": True,
                "prompt420_bounded_loop_started": True,
                "prompt420_bounded_loop_stop_required": False,
                "prompt420_next_prompt_selection_requested": True,
                "prompt420_next_prompt_selection_allowed": True,
                "prompt420_next_prompt_selection_started": True,
                "prompt420_next_action": (
                    "return_to_prompt402_next_prompt_selection"
                ),
            }
        )

    return state

def _build_prompt421_targeted_fix_route_and_materialization_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
    materialize_requested: bool = False,
    allow_materialize: bool = False,
    repo_path: str | Path | None = None,
) -> dict[str, Any]:
    run_state = (
        dict(run_state_payload)
        if isinstance(run_state_payload, Mapping)
        else {}
    )
    prompt_relative_path = (
        "current_prompt_verify_results/prompt421/targeted_fix_prompt.md"
    )
    receipt_relative_path = (
        "current_prompt_verify_results/prompt421/"
        "targeted_fix_materialization_receipt.json"
    )
    materialize_allowed = (
        bool(materialize_requested) and bool(allow_materialize) and repo_path is not None
    )
    safety_invariants: dict[str, Any] = {
        "prompt421_selected_prompt_execution_allowed": False,
        "prompt421_codex_invocation_allowed": False,
        "prompt421_git_mutation_allowed": False,
        "prompt421_commit_tag_allowed": False,
        "prompt421_push_allowed": False,
        "prompt421_pr_allowed": False,
        "prompt421_merge_allowed": False,
        "prompt421_rollback_allowed": False,
        "prompt421_next_cycle_started": False,
    }
    state: dict[str, Any] = {
        "prompt421_schema_version": _PROMPT421_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt421",
        "prompt421_targeted_fix_route_enabled": True,
        "prompt421_targeted_fix_route_status": "blocked",
        "prompt421_targeted_fix_route_ready": False,
        "prompt421_targeted_fix_route_blocked_reason": (
            "prompt418_targeted_fix_route_not_ready"
        ),
        "prompt421_targeted_fix_route_blocked_reasons": [
            "prompt418_targeted_fix_route_not_ready"
        ],
        "prompt421_targeted_fix_route_source": "prompt418_failure_route",
        "prompt421_selected_prompt_id": "",
        "prompt421_failure_classification": "blocked",
        "prompt421_failure_route_reason": "",
        "prompt421_execution_returncode": None,
        "prompt421_execution_returncode_classification": "not_run",
        "prompt421_execution_status": "blocked",
        "prompt421_result_json_path": "",
        "prompt421_stdout_path": "",
        "prompt421_stderr_path": "",
        "prompt421_targeted_fix_required": False,
        "prompt421_retry_required": False,
        "prompt421_stop_required": False,
        "prompt421_targeted_fix_prompt_ready": False,
        "prompt421_targeted_fix_prompt_text": "",
        "prompt421_targeted_fix_prompt_path": "",
        "prompt421_targeted_fix_materialize_requested": bool(
            materialize_requested
        ),
        "prompt421_targeted_fix_materialize_allowed": False,
        "prompt421_targeted_fix_prompt_written": False,
        "prompt421_targeted_fix_prompt_exists": False,
        "prompt421_targeted_fix_receipt_path": "",
        "prompt421_targeted_fix_receipt_written": False,
        "prompt421_targeted_fix_execution_packet_ready": False,
        "prompt421_targeted_fix_execution_packet_target_prompt": "prompt422",
        "prompt421_targeted_fix_execution_packet_mode": "blocked",
        "prompt421_targeted_fix_execution_packet_prompt_path": "",
        **safety_invariants,
        "prompt421_next_action": "review_prompt418_execution_result_review",
    }

    if not _prompt421_prompt418_targeted_fix_route_ready(run_state):
        return state

    selected_prompt_id = _normalize_text(
        run_state.get("prompt418_selected_prompt_id"),
        default="",
    ) or "prompt402"
    failure_classification = _normalize_text(
        run_state.get("prompt418_execution_review_classification"),
        default="",
    )
    failure_route_reason = _normalize_text(
        run_state.get("prompt418_failure_route_reason"),
        default="",
    )
    execution_returncode = run_state.get("prompt418_execution_returncode")
    execution_returncode_classification = _normalize_text(
        run_state.get("prompt418_execution_returncode_classification"),
        default="",
    )
    execution_status = _normalize_text(
        run_state.get("prompt418_execution_status"),
        default="",
    )
    result_json_path = _normalize_text(
        run_state.get("prompt418_result_json_path"),
        default="",
    )
    stdout_path = _normalize_text(
        run_state.get("prompt418_stdout_path"),
        default="",
    )
    stderr_path = _normalize_text(
        run_state.get("prompt418_stderr_path"),
        default="",
    )
    prompt_text = _prompt421_build_targeted_fix_prompt_text(
        selected_prompt_id=selected_prompt_id,
        failure_classification=failure_classification,
        failure_route_reason=failure_route_reason,
        execution_returncode=execution_returncode,
        execution_returncode_classification=execution_returncode_classification,
        execution_status=execution_status,
        result_json_path=result_json_path,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
    )
    state.update(
        {
            "prompt421_targeted_fix_route_status": "ready",
            "prompt421_targeted_fix_route_ready": True,
            "prompt421_targeted_fix_route_blocked_reason": "",
            "prompt421_targeted_fix_route_blocked_reasons": [],
            "prompt421_selected_prompt_id": selected_prompt_id,
            "prompt421_failure_classification": failure_classification,
            "prompt421_failure_route_reason": failure_route_reason,
            "prompt421_execution_returncode": execution_returncode,
            "prompt421_execution_returncode_classification": (
                execution_returncode_classification
            ),
            "prompt421_execution_status": execution_status,
            "prompt421_result_json_path": result_json_path,
            "prompt421_stdout_path": stdout_path,
            "prompt421_stderr_path": stderr_path,
            "prompt421_targeted_fix_required": True,
            "prompt421_retry_required": True,
            "prompt421_targeted_fix_prompt_ready": True,
            "prompt421_targeted_fix_prompt_text": prompt_text,
            "prompt421_targeted_fix_prompt_path": prompt_relative_path,
            "prompt421_targeted_fix_receipt_path": receipt_relative_path,
            "prompt421_targeted_fix_execution_packet_mode": (
                "targeted_fix_prompt_not_materialized"
            ),
            "prompt421_targeted_fix_execution_packet_prompt_path": (
                prompt_relative_path
            ),
            "prompt421_next_action": (
                "request_prompt421_targeted_fix_prompt_materialization"
            ),
        }
    )

    if not materialize_allowed:
        return state

    if not (
        _prompt421_relative_path_valid(prompt_relative_path)
        and _prompt421_relative_path_valid(receipt_relative_path)
        and prompt_relative_path.startswith(
            "current_prompt_verify_results/prompt421/"
        )
        and receipt_relative_path.startswith(
            "current_prompt_verify_results/prompt421/"
        )
    ):
        state.update(
            {
                "prompt421_targeted_fix_route_status": "blocked",
                "prompt421_targeted_fix_route_ready": False,
                "prompt421_targeted_fix_route_blocked_reason": (
                    "invalid_targeted_fix_prompt_path"
                ),
                "prompt421_targeted_fix_route_blocked_reasons": [
                    "invalid_targeted_fix_prompt_path"
                ],
                "prompt421_targeted_fix_execution_packet_ready": False,
                "prompt421_targeted_fix_execution_packet_mode": "blocked",
                "prompt421_next_action": (
                    "request_prompt421_targeted_fix_prompt_materialization"
                ),
            }
        )
        return state

    repo_root = Path(repo_path)
    prompt_path = repo_root / prompt_relative_path
    receipt_path = repo_root / receipt_relative_path
    receipt_payload: dict[str, Any] = {
        "schema_version": _PROMPT421_SCHEMA_VERSION,
        "prompt_id": "prompt421",
        "status": "materialized",
        "selected_prompt_id": selected_prompt_id,
        "failure_classification": failure_classification,
        "materialize_requested": True,
        "materialize_allowed": True,
        "prompt_path": prompt_relative_path,
        "prompt_written": True,
        "receipt_written": True,
        "target_prompt": "prompt422",
        "codex_invocation_allowed": False,
        "git_mutation_allowed": False,
        "commit_tag_allowed": False,
    }
    try:
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(prompt_text, encoding="utf-8")
        _write_json(receipt_path, receipt_payload)
    except Exception:  # noqa: BLE001 - surfaced as deterministic route status.
        state.update(
            {
                "prompt421_targeted_fix_route_status": "materialization_error",
                "prompt421_targeted_fix_route_ready": False,
                "prompt421_targeted_fix_route_blocked_reason": (
                    "targeted_fix_prompt_materialization_error"
                ),
                "prompt421_targeted_fix_route_blocked_reasons": [
                    "targeted_fix_prompt_materialization_error"
                ],
                "prompt421_targeted_fix_materialize_allowed": True,
                "prompt421_targeted_fix_prompt_written": False,
                "prompt421_targeted_fix_prompt_exists": False,
                "prompt421_targeted_fix_receipt_written": False,
                "prompt421_targeted_fix_execution_packet_ready": False,
                "prompt421_targeted_fix_execution_packet_mode": "blocked",
                "prompt421_next_action": (
                    "request_prompt421_targeted_fix_prompt_materialization"
                ),
            }
        )
        return state

    state.update(
        {
            "prompt421_targeted_fix_route_status": "materialized",
            "prompt421_targeted_fix_route_ready": True,
            "prompt421_targeted_fix_materialize_allowed": True,
            "prompt421_targeted_fix_prompt_written": True,
            "prompt421_targeted_fix_prompt_exists": True,
            "prompt421_targeted_fix_receipt_written": True,
            "prompt421_targeted_fix_execution_packet_ready": True,
            "prompt421_targeted_fix_execution_packet_mode": (
                "targeted_fix_prompt_materialized_no_execute"
            ),
            "prompt421_next_action": (
                "prepare_prompt422_targeted_fix_codex_execution"
            ),
        }
    )
    return state

def _build_prompt422_targeted_fix_codex_execution_adapter_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
    execute_requested: bool = False,
    allow_execute: bool = False,
    repo_path: str | Path | None = None,
    codex_command: Sequence[str] | None = None,
    timeout_seconds: int = 600,
    transport_runner: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    run_state = (
        dict(run_state_payload)
        if isinstance(run_state_payload, Mapping)
        else {}
    )
    normalized_timeout_seconds = _prompt422_normalize_timeout_seconds(
        timeout_seconds
    )
    try:
        normalized_command = _prompt422_normalize_command(codex_command)
    except ValueError:
        normalized_command = []
    stdout_relative_path = (
        "current_prompt_verify_results/prompt422/targeted_fix_stdout.txt"
    )
    stderr_relative_path = (
        "current_prompt_verify_results/prompt422/targeted_fix_stderr.txt"
    )
    result_json_relative_path = (
        "current_prompt_verify_results/prompt422/"
        "targeted_fix_execution_result.json"
    )
    safety_invariants: dict[str, Any] = {
        "prompt422_git_mutation_allowed": False,
        "prompt422_commit_tag_allowed": False,
        "prompt422_push_allowed": False,
        "prompt422_pr_allowed": False,
        "prompt422_merge_allowed": False,
        "prompt422_rollback_allowed": False,
        "prompt422_next_cycle_started": False,
    }
    state: dict[str, Any] = {
        "prompt422_schema_version": _PROMPT422_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt422",
        "prompt422_targeted_fix_codex_execution_adapter_enabled": True,
        "prompt422_targeted_fix_codex_execution_adapter_status": "blocked",
        "prompt422_targeted_fix_codex_execution_adapter_ready": False,
        "prompt422_targeted_fix_codex_execution_adapter_blocked_reason": (
            "prompt421_targeted_fix_execution_packet_not_ready"
        ),
        "prompt422_targeted_fix_codex_execution_adapter_blocked_reasons": [
            "prompt421_targeted_fix_execution_packet_not_ready"
        ],
        "prompt422_targeted_fix_codex_execution_adapter_source": (
            "prompt421_targeted_fix_execution_packet"
        ),
        "prompt422_selected_prompt_id": "",
        "prompt422_targeted_fix_prompt_path": "",
        "prompt422_targeted_fix_prompt_path_valid": False,
        "prompt422_targeted_fix_prompt_file_checked": False,
        "prompt422_targeted_fix_prompt_file_read": False,
        "prompt422_targeted_fix_prompt_sha256": "",
        "prompt422_targeted_fix_prompt_size_bytes": 0,
        "prompt422_execution_mode": "blocked",
        "prompt422_execute_requested": bool(execute_requested),
        "prompt422_execution_allowed": False,
        "prompt422_execution_attempted": False,
        "prompt422_execution_performed": False,
        "prompt422_execution_status": "blocked",
        "prompt422_execution_returncode": None,
        "prompt422_execution_returncode_classification": "not_run",
        "prompt422_execution_timeout": False,
        "prompt422_execution_error": False,
        "prompt422_execution_error_message": "",
        "prompt422_command": normalized_command,
        "prompt422_command_shell": False,
        "prompt422_timeout_seconds": normalized_timeout_seconds,
        "prompt422_stdout_path": stdout_relative_path,
        "prompt422_stderr_path": stderr_relative_path,
        "prompt422_result_json_path": result_json_relative_path,
        "prompt422_stdout_written": False,
        "prompt422_stderr_written": False,
        "prompt422_result_json_written": False,
        "prompt422_capture_written": False,
        "prompt422_review_packet_ready": False,
        "prompt422_review_packet_target_prompt": "prompt423",
        "prompt422_review_packet_mode": "blocked",
        "prompt422_review_packet_prompt_id": "",
        "prompt422_approve_candidate": False,
        "prompt422_targeted_fix_required": False,
        "prompt422_retry_required": False,
        "prompt422_stop_required": False,
        "prompt422_selected_prompt_execution_allowed": False,
        "prompt422_codex_invocation_allowed": False,
        **safety_invariants,
        "prompt422_next_action": (
            "review_prompt421_targeted_fix_route_and_materialization"
        ),
    }

    if not _prompt422_prompt421_execution_packet_ready(run_state):
        return state

    prompt_relative_path = _normalize_text(
        run_state.get("prompt421_targeted_fix_execution_packet_prompt_path"),
        default="",
    )
    path_valid = _prompt422_targeted_fix_prompt_path_valid(prompt_relative_path)
    state.update(
        {
            "prompt422_targeted_fix_codex_execution_adapter_status": "ready",
            "prompt422_targeted_fix_codex_execution_adapter_ready": True,
            "prompt422_targeted_fix_codex_execution_adapter_blocked_reason": "",
            "prompt422_targeted_fix_codex_execution_adapter_blocked_reasons": [],
            "prompt422_selected_prompt_id": "prompt402",
            "prompt422_targeted_fix_prompt_path": prompt_relative_path,
            "prompt422_targeted_fix_prompt_path_valid": path_valid,
            "prompt422_execution_mode": "planned_no_execute",
            "prompt422_execution_status": "not_run",
            "prompt422_review_packet_mode": "targeted_fix_execution_not_run",
            "prompt422_review_packet_prompt_id": "prompt402",
            "prompt422_targeted_fix_required": True,
            "prompt422_retry_required": True,
            "prompt422_stop_required": False,
            "prompt422_next_action": (
                "request_prompt422_targeted_fix_codex_execution"
            ),
        }
    )

    def _block_ready_state(reason: str) -> dict[str, Any]:
        state.update(
            {
                "prompt422_targeted_fix_codex_execution_adapter_status": (
                    "blocked"
                ),
                "prompt422_targeted_fix_codex_execution_adapter_ready": False,
                "prompt422_targeted_fix_codex_execution_adapter_blocked_reason": (
                    reason
                ),
                "prompt422_targeted_fix_codex_execution_adapter_blocked_reasons": [
                    reason
                ],
                "prompt422_execution_mode": "blocked",
                "prompt422_execution_allowed": False,
                "prompt422_execution_attempted": False,
                "prompt422_execution_performed": False,
                "prompt422_execution_status": "blocked",
                "prompt422_execution_returncode": None,
                "prompt422_execution_returncode_classification": "not_run",
                "prompt422_execution_timeout": False,
                "prompt422_execution_error": False,
                "prompt422_execution_error_message": "",
                "prompt422_review_packet_ready": False,
                "prompt422_review_packet_mode": "blocked",
                "prompt422_codex_invocation_allowed": False,
                **safety_invariants,
                "prompt422_next_action": (
                    "review_prompt421_targeted_fix_route_and_materialization"
                ),
            }
        )
        return state

    if not path_valid:
        return _block_ready_state("invalid_targeted_fix_prompt_path")

    if not normalized_command:
        return _block_ready_state("invalid_codex_command")

    if not (bool(execute_requested) and bool(allow_execute)):
        return state

    if repo_path is None:
        return _block_ready_state("targeted_fix_prompt_file_missing")

    repo_root = Path(repo_path)
    prompt_path = repo_root / prompt_relative_path
    stdout_path = repo_root / stdout_relative_path
    stderr_path = repo_root / stderr_relative_path
    result_json_path = repo_root / result_json_relative_path
    state.update(
        {
            "prompt422_targeted_fix_prompt_file_checked": True,
            "prompt422_execution_allowed": True,
            "prompt422_codex_invocation_allowed": True,
        }
    )
    if prompt_path.is_symlink():
        return _block_ready_state("targeted_fix_prompt_file_symlink")
    if not prompt_path.exists():
        return _block_ready_state("targeted_fix_prompt_file_missing")

    execution_attempted = True
    execution_performed = True
    stdout_text = ""
    stderr_text = ""
    execution_status = "execution_error"
    returncode: int | None = None
    returncode_classification = "execution_error"
    execution_timeout = False
    execution_error = True
    execution_error_message = ""
    prompt_text = ""
    prompt_sha256 = ""
    prompt_size_bytes = 0

    try:
        prompt_text = prompt_path.read_text(encoding="utf-8")
        encoded_prompt_text = prompt_text.encode("utf-8")
        prompt_sha256 = hashlib.sha256(encoded_prompt_text).hexdigest()
        prompt_size_bytes = len(encoded_prompt_text)
        state.update(
            {
                "prompt422_targeted_fix_prompt_file_read": True,
                "prompt422_targeted_fix_prompt_sha256": prompt_sha256,
                "prompt422_targeted_fix_prompt_size_bytes": prompt_size_bytes,
            }
        )
        if transport_runner is not None:
            completed = transport_runner(
                command=normalized_command,
                input=prompt_text,
                timeout=normalized_timeout_seconds,
                cwd=repo_root,
            )
        else:
            completed = subprocess.run(
                normalized_command,
                shell=False,
                capture_output=True,
                text=True,
                check=False,
                input=prompt_text,
                cwd=repo_root,
                timeout=normalized_timeout_seconds,
            )
        if isinstance(completed, Mapping):
            stdout_text = str(completed.get("stdout", ""))
            stderr_text = str(completed.get("stderr", ""))
            raw_returncode = completed.get("returncode")
        else:
            stdout_text = str(getattr(completed, "stdout", ""))
            stderr_text = str(getattr(completed, "stderr", ""))
            raw_returncode = getattr(completed, "returncode", None)
        returncode = (
            raw_returncode
            if isinstance(raw_returncode, int) and not isinstance(raw_returncode, bool)
            else None
        )
        execution_status = "completed"
        returncode_classification = "success" if returncode == 0 else "failed"
        execution_timeout = False
        execution_error = False
        execution_error_message = ""
    except (subprocess.TimeoutExpired, TimeoutError) as exc:
        stdout_text = str(getattr(exc, "stdout", "") or "")
        stderr_text = str(getattr(exc, "stderr", "") or "")
        execution_status = "timeout"
        returncode = None
        returncode_classification = "timeout"
        execution_timeout = True
        execution_error = False
        execution_error_message = ""
    except Exception as exc:  # noqa: BLE001 - captured for Prompt423 review.
        execution_status = "execution_error"
        returncode = None
        returncode_classification = "execution_error"
        execution_timeout = False
        execution_error = True
        execution_error_message = str(exc)

    stdout_size_bytes = len(stdout_text.encode("utf-8"))
    stderr_size_bytes = len(stderr_text.encode("utf-8"))
    result_payload = _prompt422_result_json_payload(
        targeted_fix_prompt_path=prompt_relative_path,
        targeted_fix_prompt_sha256=prompt_sha256,
        targeted_fix_prompt_size_bytes=prompt_size_bytes,
        command=normalized_command,
        timeout_seconds=normalized_timeout_seconds,
        execution_requested=True,
        execution_allowed=True,
        execution_attempted=execution_attempted,
        execution_performed=execution_performed,
        execution_status=execution_status,
        returncode=returncode,
        returncode_classification=returncode_classification,
        execution_timeout=execution_timeout,
        execution_error=execution_error,
        execution_error_message=execution_error_message,
        stdout_path=stdout_relative_path,
        stderr_path=stderr_relative_path,
        result_json_path=result_json_relative_path,
        stdout_size_bytes=stdout_size_bytes,
        stderr_size_bytes=stderr_size_bytes,
        codex_invocation_allowed=True,
    )
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stdout_path.write_text(stdout_text, encoding="utf-8")
    stderr_path.write_text(stderr_text, encoding="utf-8")
    _write_json(result_json_path, result_payload)
    state.update(
        {
            "prompt422_targeted_fix_codex_execution_adapter_status": "executed",
            "prompt422_targeted_fix_codex_execution_adapter_ready": True,
            "prompt422_targeted_fix_codex_execution_adapter_blocked_reason": (
                "targeted_fix_codex_execution_error"
                if execution_error
                else ""
            ),
            "prompt422_targeted_fix_codex_execution_adapter_blocked_reasons": (
                ["targeted_fix_codex_execution_error"] if execution_error else []
            ),
            "prompt422_execution_mode": "targeted_fix_execution_captured",
            "prompt422_execution_allowed": True,
            "prompt422_execution_attempted": execution_attempted,
            "prompt422_execution_performed": execution_performed,
            "prompt422_execution_status": execution_status,
            "prompt422_execution_returncode": returncode,
            "prompt422_execution_returncode_classification": (
                returncode_classification
            ),
            "prompt422_execution_timeout": execution_timeout,
            "prompt422_execution_error": execution_error,
            "prompt422_execution_error_message": execution_error_message,
            "prompt422_stdout_written": True,
            "prompt422_stderr_written": True,
            "prompt422_result_json_written": True,
            "prompt422_capture_written": True,
            "prompt422_review_packet_ready": True,
            "prompt422_review_packet_mode": (
                "targeted_fix_execution_result_captured"
            ),
            "prompt422_review_packet_prompt_id": "prompt402",
            "prompt422_selected_prompt_execution_allowed": False,
            "prompt422_codex_invocation_allowed": True,
            **safety_invariants,
            "prompt422_next_action": (
                "prepare_prompt423_targeted_fix_result_review"
            ),
        }
    )
    return state

def _build_prompt423_targeted_fix_result_review_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
    targeted_fix_attempt_current: int | None = None,
    targeted_fix_attempt_max: int = 2,
) -> dict[str, Any]:
    run_state = (
        dict(run_state_payload)
        if isinstance(run_state_payload, Mapping)
        else {}
    )
    attempt_current_source = (
        run_state.get("prompt423_targeted_fix_attempt_current")
        if targeted_fix_attempt_current is None
        else targeted_fix_attempt_current
    )
    attempt_current = _prompt423_normalize_attempt(attempt_current_source, 1)
    attempt_max = _prompt423_normalize_attempt(targeted_fix_attempt_max, 2)
    attempt_next = attempt_current + 1
    prompt_path = "current_prompt_verify_results/prompt421/targeted_fix_prompt.md"
    result_json_path = (
        "current_prompt_verify_results/prompt422/"
        "targeted_fix_execution_result.json"
    )
    stdout_path = "current_prompt_verify_results/prompt422/targeted_fix_stdout.txt"
    stderr_path = "current_prompt_verify_results/prompt422/targeted_fix_stderr.txt"
    safety_invariants: dict[str, Any] = {
        "prompt423_selected_prompt_execution_allowed": False,
        "prompt423_codex_invocation_allowed": False,
        "prompt423_git_mutation_allowed": False,
        "prompt423_commit_tag_allowed": False,
        "prompt423_push_allowed": False,
        "prompt423_pr_allowed": False,
        "prompt423_merge_allowed": False,
        "prompt423_rollback_allowed": False,
        "prompt423_next_cycle_started": False,
    }
    state: dict[str, Any] = {
        "prompt423_schema_version": _PROMPT423_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt423",
        "prompt423_targeted_fix_result_review_enabled": True,
        "prompt423_targeted_fix_result_review_status": "blocked",
        "prompt423_targeted_fix_result_review_ready": False,
        "prompt423_targeted_fix_result_review_blocked_reason": (
            "prompt422_targeted_fix_execution_result_not_ready"
        ),
        "prompt423_targeted_fix_result_review_blocked_reasons": [
            "prompt422_targeted_fix_execution_result_not_ready"
        ],
        "prompt423_targeted_fix_result_review_source": (
            "prompt422_targeted_fix_execution_result"
        ),
        "prompt423_selected_prompt_id": "",
        "prompt423_targeted_fix_execution_result_available": False,
        "prompt423_targeted_fix_execution_success": False,
        "prompt423_targeted_fix_execution_failed": False,
        "prompt423_targeted_fix_execution_timeout": False,
        "prompt423_targeted_fix_execution_error": False,
        "prompt423_targeted_fix_execution_status": "blocked",
        "prompt423_targeted_fix_execution_returncode": None,
        "prompt423_targeted_fix_execution_returncode_classification": "not_run",
        "prompt423_targeted_fix_prompt_path": "",
        "prompt423_targeted_fix_result_json_path": "",
        "prompt423_targeted_fix_stdout_path": "",
        "prompt423_targeted_fix_stderr_path": "",
        "prompt423_targeted_fix_attempt_current": attempt_current,
        "prompt423_targeted_fix_attempt_max": attempt_max,
        "prompt423_targeted_fix_attempt_next": attempt_next,
        "prompt423_targeted_fix_retry_allowed": False,
        "prompt423_retry_required": False,
        "prompt423_stop_required": False,
        "prompt423_approve_candidate": False,
        "prompt423_targeted_fix_required": False,
        "prompt423_commit_tag_plan_ready": False,
        "prompt423_commit_tag_plan_target_prompt": "",
        "prompt423_commit_tag_plan_mode": "",
        "prompt423_commit_tag_plan_selected_prompt_id": "",
        "prompt423_commit_tag_plan_commit_message": "",
        "prompt423_commit_tag_plan_tag_name": "",
        "prompt423_commit_tag_plan_allowed": False,
        "prompt423_success_handoff_ready": False,
        "prompt423_success_handoff_target_prompt": "",
        "prompt423_success_handoff_mode": "",
        "prompt423_success_handoff_next_cycle_target_prompt": "",
        "prompt423_failure_route_ready": False,
        "prompt423_failure_route_reason": "",
        "prompt423_failure_route_target_prompt": "",
        "prompt423_retry_route_ready": False,
        "prompt423_retry_route_target_prompt": "",
        "prompt423_retry_route_mode": "",
        "prompt423_retry_route_attempt_next": attempt_next,
        **safety_invariants,
        "prompt423_next_action": (
            "review_prompt422_targeted_fix_codex_execution_adapter"
        ),
    }

    if not _prompt423_prompt422_review_packet_ready(run_state):
        return state

    classification = _normalize_text(
        run_state.get("prompt422_execution_returncode_classification"),
        default="",
    )
    execution_status = _normalize_text(
        run_state.get("prompt422_execution_status"),
        default="",
    )
    returncode = run_state.get("prompt422_execution_returncode")
    execution_failed = classification == "failed"
    execution_timeout = classification == "timeout"
    execution_error = classification == "execution_error"
    shared_ready_state: dict[str, Any] = {
        "prompt423_targeted_fix_result_review_ready": True,
        "prompt423_targeted_fix_result_review_blocked_reason": "",
        "prompt423_targeted_fix_result_review_blocked_reasons": [],
        "prompt423_selected_prompt_id": "prompt402",
        "prompt423_targeted_fix_execution_result_available": True,
        "prompt423_targeted_fix_execution_success": classification == "success",
        "prompt423_targeted_fix_execution_failed": execution_failed,
        "prompt423_targeted_fix_execution_timeout": execution_timeout,
        "prompt423_targeted_fix_execution_error": execution_error,
        "prompt423_targeted_fix_execution_status": execution_status,
        "prompt423_targeted_fix_execution_returncode": returncode,
        "prompt423_targeted_fix_execution_returncode_classification": classification,
        "prompt423_targeted_fix_prompt_path": prompt_path,
        "prompt423_targeted_fix_result_json_path": result_json_path,
        "prompt423_targeted_fix_stdout_path": stdout_path,
        "prompt423_targeted_fix_stderr_path": stderr_path,
        **safety_invariants,
    }

    if classification == "success":
        state.update(
            {
                **shared_ready_state,
                "prompt423_targeted_fix_result_review_status": "approved",
                "prompt423_targeted_fix_retry_allowed": False,
                "prompt423_retry_required": False,
                "prompt423_stop_required": False,
                "prompt423_approve_candidate": True,
                "prompt423_targeted_fix_required": False,
                "prompt423_commit_tag_plan_ready": True,
                "prompt423_commit_tag_plan_target_prompt": "prompt419",
                "prompt423_commit_tag_plan_mode": (
                    "targeted_fix_success_guarded_commit_tag_plan"
                ),
                "prompt423_commit_tag_plan_selected_prompt_id": "prompt402",
                "prompt423_commit_tag_plan_commit_message": (
                    "Prompt402 apply targeted fix execution result"
                ),
                "prompt423_commit_tag_plan_tag_name": (
                    "prompt402-targeted-fix-execution-result"
                ),
                "prompt423_commit_tag_plan_allowed": False,
                "prompt423_success_handoff_ready": True,
                "prompt423_success_handoff_target_prompt": "prompt419",
                "prompt423_success_handoff_mode": (
                    "targeted_fix_success_commit_tag_boundary"
                ),
                "prompt423_success_handoff_next_cycle_target_prompt": "prompt420",
                "prompt423_failure_route_ready": False,
                "prompt423_failure_route_reason": "",
                "prompt423_failure_route_target_prompt": "",
                "prompt423_retry_route_ready": False,
                "prompt423_retry_route_target_prompt": "",
                "prompt423_retry_route_mode": "",
                "prompt423_next_action": (
                    "prepare_prompt419_approve_commit_tag_for_targeted_fix_success"
                ),
            }
        )
        return state

    retry_allowed = attempt_current < attempt_max
    failure_route_reason = {
        "failed": "targeted_fix_execution_failed",
        "timeout": "targeted_fix_execution_timeout",
        "execution_error": "targeted_fix_execution_error",
    }.get(classification, "")

    if retry_allowed:
        state.update(
            {
                **shared_ready_state,
                "prompt423_targeted_fix_result_review_status": "retry",
                "prompt423_targeted_fix_retry_allowed": True,
                "prompt423_retry_required": True,
                "prompt423_stop_required": False,
                "prompt423_approve_candidate": False,
                "prompt423_targeted_fix_required": True,
                "prompt423_commit_tag_plan_ready": False,
                "prompt423_success_handoff_ready": False,
                "prompt423_failure_route_ready": True,
                "prompt423_failure_route_reason": failure_route_reason,
                "prompt423_failure_route_target_prompt": "prompt421",
                "prompt423_retry_route_ready": True,
                "prompt423_retry_route_target_prompt": "prompt421",
                "prompt423_retry_route_mode": "bounded_targeted_fix_retry",
                "prompt423_retry_route_attempt_next": attempt_next,
                "prompt423_next_action": "prepare_prompt421_targeted_fix_retry",
            }
        )
        return state

    state.update(
        {
            **shared_ready_state,
            "prompt423_targeted_fix_result_review_status": "stopped",
            "prompt423_targeted_fix_retry_allowed": False,
            "prompt423_retry_required": False,
            "prompt423_stop_required": True,
            "prompt423_approve_candidate": False,
            "prompt423_targeted_fix_required": False,
            "prompt423_commit_tag_plan_ready": False,
            "prompt423_success_handoff_ready": False,
            "prompt423_failure_route_ready": True,
            "prompt423_failure_route_reason": "targeted_fix_retry_limit_reached",
            "prompt423_failure_route_target_prompt": "",
            "prompt423_retry_route_ready": False,
            "prompt423_retry_route_target_prompt": "",
            "prompt423_retry_route_mode": "",
            "prompt423_retry_route_attempt_next": attempt_next,
            "prompt423_next_action": "stop_targeted_fix_retry_limit_reached",
        }
    )
    return state

def _build_prompt424_bounded_full_autonomous_loop_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
    loop_start_requested: bool = False,
    allow_loop_progress: bool = False,
    current_cycle: int | None = None,
    max_cycles: int = 2,
) -> dict[str, Any]:
    run_state = (
        dict(run_state_payload)
        if isinstance(run_state_payload, Mapping)
        else {}
    )
    current_cycle_source = (
        run_state.get("prompt424_current_cycle", 0)
        if current_cycle is None
        else current_cycle
    )
    normalized_current_cycle = _prompt424_normalize_cycle_value(
        current_cycle_source,
        minimum=0,
        default=0,
    )
    normalized_max_cycles = _prompt424_normalize_cycle_value(
        max_cycles,
        minimum=1,
        default=2,
    )
    next_cycle_index = normalized_current_cycle + 1
    loop_capacity_available = normalized_current_cycle < normalized_max_cycles
    selected_prompt_id = _normalize_text(
        run_state.get("prompt423_selected_prompt_id"),
        default="",
    ) or _normalize_text(
        run_state.get("prompt422_selected_prompt_id"),
        default="",
    )
    safety_invariants: dict[str, Any] = {
        "prompt424_selected_prompt_execution_allowed": False,
        "prompt424_codex_invocation_allowed": False,
        "prompt424_prompt_materialization_allowed": False,
        "prompt424_targeted_fix_execution_allowed": False,
        "prompt424_git_mutation_allowed": False,
        "prompt424_commit_tag_allowed": False,
        "prompt424_push_allowed": False,
        "prompt424_pr_allowed": False,
        "prompt424_merge_allowed": False,
        "prompt424_rollback_allowed": False,
        "prompt424_next_cycle_started": False,
        "prompt424_unbounded_loop_allowed": False,
    }
    state: dict[str, Any] = {
        "prompt424_schema_version": _PROMPT424_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt424",
        "prompt424_bounded_full_autonomous_loop_enabled": True,
        "prompt424_bounded_full_autonomous_loop_status": "blocked",
        "prompt424_bounded_full_autonomous_loop_ready": False,
        "prompt424_bounded_full_autonomous_loop_blocked_reason": (
            "no_ready_prompt420_or_prompt423_route"
        ),
        "prompt424_bounded_full_autonomous_loop_blocked_reasons": [
            "no_ready_prompt420_or_prompt423_route"
        ],
        "prompt424_current_cycle": normalized_current_cycle,
        "prompt424_max_cycles": normalized_max_cycles,
        "prompt424_next_cycle_index": next_cycle_index,
        "prompt424_loop_start_requested": bool(loop_start_requested),
        "prompt424_loop_progress_allowed": bool(allow_loop_progress),
        "prompt424_loop_capacity_available": loop_capacity_available,
        "prompt424_loop_progress_performed": False,
        "prompt424_route": "blocked",
        "prompt424_route_source": "",
        "prompt424_success_route_ready": False,
        "prompt424_targeted_fix_route_ready": False,
        "prompt424_retry_route_ready": False,
        "prompt424_retry_route_target_prompt": "",
        "prompt424_retry_route_mode": "",
        "prompt424_retry_route_attempt_next": None,
        "prompt424_stop_route_ready": False,
        "prompt424_stop_reason": "",
        "prompt424_commit_tag_handoff_ready": False,
        "prompt424_approve_commit_tag_handoff_target_prompt": "",
        "prompt424_approve_commit_tag_handoff_mode": "",
        "prompt424_approve_commit_tag_handoff_selected_prompt_id": "",
        "prompt424_approve_commit_tag_handoff_commit_message": "",
        "prompt424_approve_commit_tag_handoff_tag_name": "",
        "prompt424_next_cycle_handoff_ready": False,
        "prompt424_next_cycle_handoff_target_prompt": "",
        "prompt424_next_cycle_handoff_mode": "",
        "prompt424_selected_prompt_id": selected_prompt_id,
        **safety_invariants,
        "prompt424_next_action": (
            "review_prompt420_success_or_prompt423_targeted_fix_route"
        ),
    }

    if not loop_capacity_available:
        state.update(
            {
                "prompt424_bounded_full_autonomous_loop_status": "stopped",
                "prompt424_bounded_full_autonomous_loop_ready": True,
                "prompt424_bounded_full_autonomous_loop_blocked_reason": "",
                "prompt424_bounded_full_autonomous_loop_blocked_reasons": [],
                "prompt424_route": "cycle_limit_stop",
                "prompt424_route_source": "prompt424",
                "prompt424_stop_route_ready": True,
                "prompt424_stop_reason": (
                    "bounded_full_autonomous_loop_cycle_limit_reached"
                ),
                "prompt424_next_action": (
                    "stop_bounded_full_autonomous_loop_cycle_limit_reached"
                ),
            }
        )
        return state

    prompt420_success_ready = (
        run_state.get("prompt420_success_only_next_cycle_loop_status")
        in {"ready", "next_cycle_ready"}
        and run_state.get("prompt420_success_handoff_ready") is True
        and (
            run_state.get("prompt420_next_cycle_allowed", False) is False
            or run_state.get("prompt420_next_cycle_started", False) is False
        )
        and run_state.get("prompt420_next_action")
        in {
            "request_next_cycle_start",
            "next_cycle_start_blocked_until_explicit_request",
            "bounded_success_cycle_ready",
        }
    )
    if prompt420_success_ready:
        state.update(
            {
                "prompt424_bounded_full_autonomous_loop_status": "success_ready",
                "prompt424_bounded_full_autonomous_loop_ready": True,
                "prompt424_bounded_full_autonomous_loop_blocked_reason": "",
                "prompt424_bounded_full_autonomous_loop_blocked_reasons": [],
                "prompt424_route": "success_next_cycle",
                "prompt424_route_source": "prompt420",
                "prompt424_success_route_ready": True,
                "prompt424_targeted_fix_route_ready": False,
                "prompt424_retry_route_ready": False,
                "prompt424_stop_route_ready": False,
                "prompt424_commit_tag_handoff_ready": False,
                "prompt424_next_cycle_handoff_ready": True,
                "prompt424_next_cycle_handoff_target_prompt": "prompt420",
                "prompt424_next_cycle_handoff_mode": (
                    "success_only_next_cycle_loop"
                ),
                "prompt424_approve_commit_tag_handoff_target_prompt": "",
                "prompt424_next_action": (
                    "ready_for_bounded_success_next_cycle_handoff"
                ),
            }
        )
        return state

    prompt423_success_ready = (
        run_state.get("prompt423_targeted_fix_result_review_status")
        == "approved"
        and run_state.get("prompt423_targeted_fix_result_review_ready") is True
        and run_state.get("prompt423_approve_candidate") is True
        and run_state.get("prompt423_commit_tag_plan_ready") is True
        and run_state.get("prompt423_commit_tag_plan_target_prompt")
        == "prompt419"
        and run_state.get("prompt423_success_handoff_ready") is True
        and run_state.get("prompt423_success_handoff_target_prompt")
        == "prompt419"
        and run_state.get("prompt423_success_handoff_next_cycle_target_prompt")
        == "prompt420"
        and run_state.get("prompt423_retry_required") is False
        and run_state.get("prompt423_stop_required") is False
        and run_state.get("prompt423_codex_invocation_allowed") is False
        and run_state.get("prompt423_git_mutation_allowed") is False
        and run_state.get("prompt423_commit_tag_allowed") is False
        and run_state.get("prompt423_next_cycle_started") is False
    )
    if prompt423_success_ready:
        state.update(
            {
                "prompt424_bounded_full_autonomous_loop_status": (
                    "targeted_fix_success_ready"
                ),
                "prompt424_bounded_full_autonomous_loop_ready": True,
                "prompt424_bounded_full_autonomous_loop_blocked_reason": "",
                "prompt424_bounded_full_autonomous_loop_blocked_reasons": [],
                "prompt424_route": "targeted_fix_success_commit_tag",
                "prompt424_route_source": "prompt423",
                "prompt424_success_route_ready": True,
                "prompt424_targeted_fix_route_ready": True,
                "prompt424_retry_route_ready": False,
                "prompt424_stop_route_ready": False,
                "prompt424_commit_tag_handoff_ready": True,
                "prompt424_approve_commit_tag_handoff_target_prompt": (
                    "prompt419"
                ),
                "prompt424_approve_commit_tag_handoff_mode": (
                    "targeted_fix_success_commit_tag_boundary"
                ),
                "prompt424_approve_commit_tag_handoff_selected_prompt_id": (
                    "prompt402"
                ),
                "prompt424_approve_commit_tag_handoff_commit_message": (
                    "Prompt402 apply targeted fix execution result"
                ),
                "prompt424_approve_commit_tag_handoff_tag_name": (
                    "prompt402-targeted-fix-execution-result"
                ),
                "prompt424_next_cycle_handoff_ready": True,
                "prompt424_next_cycle_handoff_target_prompt": "prompt420",
                "prompt424_next_cycle_handoff_mode": (
                    "post_targeted_fix_success_next_cycle"
                ),
                "prompt424_next_action": (
                    "prepare_prompt419_commit_tag_for_targeted_fix_success_then_"
                    "prompt420_next_cycle"
                ),
            }
        )
        return state

    prompt423_retry_ready = (
        run_state.get("prompt423_targeted_fix_result_review_status") == "retry"
        and run_state.get("prompt423_targeted_fix_result_review_ready") is True
        and run_state.get("prompt423_approve_candidate") is False
        and run_state.get("prompt423_targeted_fix_required") is True
        and run_state.get("prompt423_retry_required") is True
        and run_state.get("prompt423_stop_required") is False
        and run_state.get("prompt423_retry_route_ready") is True
        and run_state.get("prompt423_retry_route_target_prompt") == "prompt421"
        and run_state.get("prompt423_retry_route_mode")
        == "bounded_targeted_fix_retry"
        and run_state.get("prompt423_codex_invocation_allowed") is False
        and run_state.get("prompt423_git_mutation_allowed") is False
        and run_state.get("prompt423_commit_tag_allowed") is False
        and run_state.get("prompt423_next_cycle_started") is False
    )
    if prompt423_retry_ready:
        retry_attempt_next = run_state.get("prompt423_retry_route_attempt_next")
        if retry_attempt_next is None:
            retry_attempt_next = run_state.get(
                "prompt423_targeted_fix_attempt_next"
            )
        state.update(
            {
                "prompt424_bounded_full_autonomous_loop_status": (
                    "targeted_fix_retry_ready"
                ),
                "prompt424_bounded_full_autonomous_loop_ready": True,
                "prompt424_bounded_full_autonomous_loop_blocked_reason": "",
                "prompt424_bounded_full_autonomous_loop_blocked_reasons": [],
                "prompt424_route": "targeted_fix_retry",
                "prompt424_route_source": "prompt423",
                "prompt424_success_route_ready": False,
                "prompt424_targeted_fix_route_ready": True,
                "prompt424_retry_route_ready": True,
                "prompt424_retry_route_target_prompt": "prompt421",
                "prompt424_retry_route_mode": "bounded_targeted_fix_retry",
                "prompt424_retry_route_attempt_next": retry_attempt_next,
                "prompt424_stop_route_ready": False,
                "prompt424_commit_tag_handoff_ready": False,
                "prompt424_next_cycle_handoff_ready": False,
                "prompt424_next_action": (
                    "prepare_prompt421_bounded_targeted_fix_retry"
                ),
            }
        )
        return state

    prompt423_stop_ready = (
        run_state.get("prompt423_targeted_fix_result_review_status")
        == "stopped"
        and run_state.get("prompt423_targeted_fix_result_review_ready") is True
        and run_state.get("prompt423_approve_candidate") is False
        and run_state.get("prompt423_retry_required") is False
        and run_state.get("prompt423_stop_required") is True
        and run_state.get("prompt423_failure_route_ready") is True
        and run_state.get("prompt423_failure_route_reason")
        == "targeted_fix_retry_limit_reached"
        and run_state.get("prompt423_codex_invocation_allowed") is False
        and run_state.get("prompt423_git_mutation_allowed") is False
        and run_state.get("prompt423_commit_tag_allowed") is False
        and run_state.get("prompt423_next_cycle_started") is False
    )
    if prompt423_stop_ready:
        state.update(
            {
                "prompt424_bounded_full_autonomous_loop_status": "stopped",
                "prompt424_bounded_full_autonomous_loop_ready": True,
                "prompt424_bounded_full_autonomous_loop_blocked_reason": "",
                "prompt424_bounded_full_autonomous_loop_blocked_reasons": [],
                "prompt424_route": "targeted_fix_stop",
                "prompt424_route_source": "prompt423",
                "prompt424_success_route_ready": False,
                "prompt424_targeted_fix_route_ready": True,
                "prompt424_retry_route_ready": False,
                "prompt424_stop_route_ready": True,
                "prompt424_stop_reason": "targeted_fix_retry_limit_reached",
                "prompt424_commit_tag_handoff_ready": False,
                "prompt424_next_cycle_handoff_ready": False,
                "prompt424_next_action": "stop_targeted_fix_retry_limit_reached",
            }
        )
        return state

    return state

def _build_prompt425_local_autonomous_loop_invocation_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
    invocation_requested: bool = False,
    allow_invocation_plan: bool = False,
    current_cycle: int | None = None,
    max_cycles: int = 2,
) -> dict[str, Any]:
    run_state = (
        dict(run_state_payload)
        if isinstance(run_state_payload, Mapping)
        else {}
    )
    current_cycle_source = (
        run_state.get("prompt424_current_cycle", 0)
        if current_cycle is None
        else current_cycle
    )
    normalized_current_cycle = _prompt424_normalize_cycle_value(
        current_cycle_source,
        minimum=0,
        default=0,
    )
    normalized_max_cycles = _prompt424_normalize_cycle_value(
        max_cycles,
        minimum=1,
        default=2,
    )
    prompt424_route = _normalize_text(
        run_state.get("prompt424_route"),
        default="",
    )
    prompt424_selected_prompt_id = _normalize_text(
        run_state.get("prompt424_selected_prompt_id"),
        default="",
    )
    selected_prompt_id = prompt424_selected_prompt_id
    if not selected_prompt_id and prompt424_route.startswith("targeted_fix"):
        selected_prompt_id = "prompt402"

    state: dict[str, Any] = {
        "prompt425_local_autonomous_loop_invocation_enabled": True,
        "prompt425_schema_version": _PROMPT425_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt425",
        "prompt425_invocation_requested": bool(invocation_requested),
        "prompt425_invocation_plan_allowed": bool(allow_invocation_plan),
        "prompt425_invocation_performed": False,
        "prompt425_current_cycle": normalized_current_cycle,
        "prompt425_max_cycles": normalized_max_cycles,
        "prompt425_next_cycle_index": normalized_current_cycle + 1,
        "prompt425_selected_prompt_id": selected_prompt_id,
        "prompt425_codex_invocation_allowed": False,
        "prompt425_git_mutation_allowed": False,
        "prompt425_commit_tag_allowed": False,
        "prompt425_push_allowed": False,
        "prompt425_pr_allowed": False,
        "prompt425_merge_allowed": False,
        "prompt425_rollback_allowed": False,
        "prompt425_next_cycle_started": False,
        "prompt425_unbounded_loop_allowed": False,
        "prompt425_daemon_mode_allowed": False,
        "prompt425_local_autonomous_loop_invocation_status": "blocked",
        "prompt425_local_autonomous_loop_invocation_ready": False,
        "prompt425_local_autonomous_loop_invocation_blocked_reason": (
            "prompt424_bounded_full_autonomous_loop_not_ready"
        ),
        "prompt425_local_autonomous_loop_invocation_blocked_reasons": [
            "prompt424_bounded_full_autonomous_loop_not_ready"
        ],
        "prompt425_invocation_mode": "blocked",
        "prompt425_invocation_plan_ready": False,
        "prompt425_invocation_step": "",
        "prompt425_invocation_target_prompt": "",
        "prompt425_invocation_reason": "prompt424_not_ready",
        "prompt425_invocation_order": [],
        "prompt425_expected_next_surface": "",
        "prompt425_requires_codex_execution": False,
        "prompt425_requires_prompt_materialization": False,
        "prompt425_requires_targeted_fix_execution": False,
        "prompt425_requires_commit_tag": False,
        "prompt425_requires_next_cycle": False,
        "prompt425_stop_required": False,
        "prompt425_next_action": (
            "review_prompt424_bounded_full_autonomous_loop_integration"
        ),
    }

    prompt424_ready = (
        run_state.get("prompt424_bounded_full_autonomous_loop_enabled") is True
        and run_state.get("prompt424_bounded_full_autonomous_loop_ready") is True
        and prompt424_route
        in {
            "success_next_cycle",
            "targeted_fix_success_commit_tag",
            "targeted_fix_retry",
            "targeted_fix_stop",
            "cycle_limit_stop",
        }
        and run_state.get("prompt424_codex_invocation_allowed") is False
        and run_state.get("prompt424_git_mutation_allowed") is False
        and run_state.get("prompt424_commit_tag_allowed") is False
        and run_state.get("prompt424_push_allowed") is False
        and run_state.get("prompt424_pr_allowed") is False
        and run_state.get("prompt424_merge_allowed") is False
        and run_state.get("prompt424_rollback_allowed") is False
        and run_state.get("prompt424_next_cycle_started") is False
        and run_state.get("prompt424_unbounded_loop_allowed") is False
    )
    if not prompt424_ready:
        return state

    if not invocation_requested or not allow_invocation_plan:
        state.update(
            {
                "prompt425_local_autonomous_loop_invocation_status": "ready",
                "prompt425_local_autonomous_loop_invocation_ready": True,
                "prompt425_local_autonomous_loop_invocation_blocked_reason": "",
                "prompt425_local_autonomous_loop_invocation_blocked_reasons": [],
                "prompt425_invocation_mode": "planned_no_invocation",
                "prompt425_invocation_plan_ready": False,
                "prompt425_invocation_step": "",
                "prompt425_invocation_target_prompt": "",
                "prompt425_invocation_reason": (
                    "invocation_not_requested_or_not_allowed"
                ),
                "prompt425_next_action": (
                    "request_prompt425_local_autonomous_loop_invocation_plan"
                ),
            }
        )
        return state

    if prompt424_route == "success_next_cycle":
        state.update(
            {
                "prompt425_local_autonomous_loop_invocation_status": "planned",
                "prompt425_local_autonomous_loop_invocation_ready": True,
                "prompt425_local_autonomous_loop_invocation_blocked_reason": "",
                "prompt425_local_autonomous_loop_invocation_blocked_reasons": [],
                "prompt425_invocation_mode": "one_step_plan",
                "prompt425_invocation_plan_ready": True,
                "prompt425_invocation_step": "start_next_success_cycle",
                "prompt425_invocation_target_prompt": "prompt420",
                "prompt425_invocation_reason": (
                    "prompt424_success_next_cycle_route_ready"
                ),
                "prompt425_invocation_order": ["prompt420"],
                "prompt425_expected_next_surface": (
                    "prompt420_success_only_next_cycle_loop"
                ),
                "prompt425_requires_next_cycle": True,
                "prompt425_stop_required": False,
                "prompt425_next_action": (
                    "invoke_prompt420_success_next_cycle_boundary"
                ),
            }
        )
        return state

    if prompt424_route == "targeted_fix_success_commit_tag":
        state.update(
            {
                "prompt425_local_autonomous_loop_invocation_status": "planned",
                "prompt425_local_autonomous_loop_invocation_ready": True,
                "prompt425_local_autonomous_loop_invocation_blocked_reason": "",
                "prompt425_local_autonomous_loop_invocation_blocked_reasons": [],
                "prompt425_invocation_mode": "one_step_plan",
                "prompt425_invocation_plan_ready": True,
                "prompt425_invocation_step": "approve_commit_tag_then_next_cycle",
                "prompt425_invocation_target_prompt": "prompt419",
                "prompt425_invocation_reason": (
                    "prompt424_targeted_fix_success_commit_tag_route_ready"
                ),
                "prompt425_invocation_order": ["prompt419", "prompt420"],
                "prompt425_expected_next_surface": (
                    "prompt419_approve_commit_tag_boundary_then_"
                    "prompt420_next_cycle"
                ),
                "prompt425_requires_commit_tag": True,
                "prompt425_requires_next_cycle": True,
                "prompt425_stop_required": False,
                "prompt425_next_action": (
                    "invoke_prompt419_commit_tag_boundary_then_"
                    "prompt420_next_cycle"
                ),
            }
        )
        return state

    if prompt424_route == "targeted_fix_retry":
        state.update(
            {
                "prompt425_local_autonomous_loop_invocation_status": "planned",
                "prompt425_local_autonomous_loop_invocation_ready": True,
                "prompt425_local_autonomous_loop_invocation_blocked_reason": "",
                "prompt425_local_autonomous_loop_invocation_blocked_reasons": [],
                "prompt425_invocation_mode": "one_step_plan",
                "prompt425_invocation_plan_ready": True,
                "prompt425_invocation_step": "retry_targeted_fix",
                "prompt425_invocation_target_prompt": "prompt421",
                "prompt425_invocation_reason": (
                    "prompt424_targeted_fix_retry_route_ready"
                ),
                "prompt425_invocation_order": [
                    "prompt421",
                    "prompt422",
                    "prompt423",
                    "prompt424",
                ],
                "prompt425_expected_next_surface": (
                    "prompt421_targeted_fix_materialization_then_"
                    "prompt424_review"
                ),
                "prompt425_requires_codex_execution": True,
                "prompt425_requires_prompt_materialization": True,
                "prompt425_requires_targeted_fix_execution": True,
                "prompt425_requires_commit_tag": False,
                "prompt425_requires_next_cycle": False,
                "prompt425_stop_required": False,
                "prompt425_next_action": (
                    "invoke_prompt421_targeted_fix_retry_boundary"
                ),
            }
        )
        return state

    if prompt424_route == "targeted_fix_stop":
        state.update(
            {
                "prompt425_local_autonomous_loop_invocation_status": "stopped",
                "prompt425_local_autonomous_loop_invocation_ready": True,
                "prompt425_local_autonomous_loop_invocation_blocked_reason": "",
                "prompt425_local_autonomous_loop_invocation_blocked_reasons": [],
                "prompt425_invocation_mode": "stop",
                "prompt425_invocation_plan_ready": False,
                "prompt425_invocation_step": "stop",
                "prompt425_invocation_target_prompt": "",
                "prompt425_invocation_reason": (
                    "prompt424_targeted_fix_stop_route_ready"
                ),
                "prompt425_invocation_order": [],
                "prompt425_expected_next_surface": "",
                "prompt425_requires_codex_execution": False,
                "prompt425_requires_prompt_materialization": False,
                "prompt425_requires_targeted_fix_execution": False,
                "prompt425_requires_commit_tag": False,
                "prompt425_requires_next_cycle": False,
                "prompt425_stop_required": True,
                "prompt425_next_action": (
                    "stop_targeted_fix_retry_limit_reached"
                ),
            }
        )
        return state

    if prompt424_route == "cycle_limit_stop":
        state.update(
            {
                "prompt425_local_autonomous_loop_invocation_status": "stopped",
                "prompt425_local_autonomous_loop_invocation_ready": True,
                "prompt425_local_autonomous_loop_invocation_blocked_reason": "",
                "prompt425_local_autonomous_loop_invocation_blocked_reasons": [],
                "prompt425_invocation_mode": "stop",
                "prompt425_invocation_plan_ready": False,
                "prompt425_invocation_step": "stop",
                "prompt425_invocation_target_prompt": "",
                "prompt425_invocation_reason": (
                    "prompt424_cycle_limit_stop_route_ready"
                ),
                "prompt425_invocation_order": [],
                "prompt425_expected_next_surface": "",
                "prompt425_requires_codex_execution": False,
                "prompt425_requires_prompt_materialization": False,
                "prompt425_requires_targeted_fix_execution": False,
                "prompt425_requires_commit_tag": False,
                "prompt425_requires_next_cycle": False,
                "prompt425_stop_required": True,
                "prompt425_next_action": (
                    "stop_bounded_full_autonomous_loop_cycle_limit_reached"
                ),
            }
        )
        return state

    return state

def _build_prompt426_bounded_runner_step_executor_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
    execute_requested: bool = False,
    allow_step_execution: bool = False,
    current_cycle: int | None = None,
    max_cycles: int = 2,
    step_runner: Callable[..., Mapping[str, Any] | None] | None = None,
) -> dict[str, Any]:
    run_state = (
        dict(run_state_payload)
        if isinstance(run_state_payload, Mapping)
        else {}
    )
    current_cycle_source = (
        run_state.get("prompt425_current_cycle", 0)
        if current_cycle is None
        else current_cycle
    )
    normalized_current_cycle = _prompt424_normalize_cycle_value(
        current_cycle_source,
        minimum=0,
        default=0,
    )
    normalized_max_cycles = _prompt424_normalize_cycle_value(
        max_cycles,
        minimum=1,
        default=2,
    )
    invocation_step = _normalize_text(
        run_state.get("prompt425_invocation_step"),
        default="",
    )
    invocation_target_prompt = _normalize_text(
        run_state.get("prompt425_invocation_target_prompt"),
        default="",
    )
    invocation_order = _normalize_string_list(
        run_state.get("prompt425_invocation_order"),
        sort_items=False,
    )
    expected_next_surface = _normalize_text(
        run_state.get("prompt425_expected_next_surface"),
        default="",
    )
    prompt425_status = _normalize_text(
        run_state.get("prompt425_local_autonomous_loop_invocation_status"),
        default="",
    )
    prompt425_stop_required = bool(run_state.get("prompt425_stop_required"))

    state: dict[str, Any] = {
        "prompt426_bounded_runner_step_executor_enabled": True,
        "prompt426_schema_version": _PROMPT426_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt426",
        "prompt426_current_cycle": normalized_current_cycle,
        "prompt426_max_cycles": normalized_max_cycles,
        "prompt426_next_cycle_index": normalized_current_cycle + 1,
        "prompt426_execute_requested": bool(execute_requested),
        "prompt426_step_execution_allowed": bool(allow_step_execution),
        "prompt426_invocation_step": invocation_step,
        "prompt426_invocation_target_prompt": invocation_target_prompt,
        "prompt426_invocation_order": invocation_order,
        "prompt426_expected_next_surface": expected_next_surface,
        "prompt426_requires_codex_execution": bool(
            run_state.get("prompt425_requires_codex_execution", False)
        ),
        "prompt426_requires_prompt_materialization": bool(
            run_state.get("prompt425_requires_prompt_materialization", False)
        ),
        "prompt426_requires_targeted_fix_execution": bool(
            run_state.get("prompt425_requires_targeted_fix_execution", False)
        ),
        "prompt426_requires_commit_tag": bool(
            run_state.get("prompt425_requires_commit_tag", False)
        ),
        "prompt426_requires_next_cycle": bool(
            run_state.get("prompt425_requires_next_cycle", False)
        ),
        "prompt426_codex_invocation_allowed": False,
        "prompt426_git_mutation_allowed": False,
        "prompt426_commit_tag_allowed": False,
        "prompt426_push_allowed": False,
        "prompt426_pr_allowed": False,
        "prompt426_merge_allowed": False,
        "prompt426_rollback_allowed": False,
        "prompt426_next_cycle_started": False,
        "prompt426_unbounded_loop_allowed": False,
        "prompt426_daemon_mode_allowed": False,
        "prompt426_bounded_runner_step_executor_status": "blocked",
        "prompt426_bounded_runner_step_executor_ready": False,
        "prompt426_bounded_runner_step_executor_blocked_reason": (
            "prompt425_invocation_plan_not_ready"
        ),
        "prompt426_bounded_runner_step_executor_blocked_reasons": [
            "prompt425_invocation_plan_not_ready"
        ],
        "prompt426_step_execution_mode": "blocked",
        "prompt426_step_execution_ready": False,
        "prompt426_step_execution_attempted": False,
        "prompt426_step_execution_performed": False,
        "prompt426_step_execution_status": "blocked",
        "prompt426_step_execution_result_available": False,
        "prompt426_step_execution_result_payload": {},
        "prompt426_step_execution_error": False,
        "prompt426_step_execution_error_message": "",
        "prompt426_stop_required": False,
        "prompt426_next_action": (
            "review_prompt425_local_autonomous_loop_invocation"
        ),
    }

    if prompt425_status == "stopped" or prompt425_stop_required:
        state.update(
            {
                "prompt426_bounded_runner_step_executor_status": "stopped",
                "prompt426_bounded_runner_step_executor_ready": True,
                "prompt426_bounded_runner_step_executor_blocked_reason": "",
                "prompt426_bounded_runner_step_executor_blocked_reasons": [],
                "prompt426_step_execution_mode": "stop",
                "prompt426_step_execution_ready": False,
                "prompt426_step_execution_attempted": False,
                "prompt426_step_execution_performed": False,
                "prompt426_step_execution_status": "not_run",
                "prompt426_step_execution_result_available": False,
                "prompt426_step_execution_result_payload": {},
                "prompt426_step_execution_error": False,
                "prompt426_step_execution_error_message": "",
                "prompt426_stop_required": True,
                "prompt426_next_action": "stop_local_autonomous_loop",
            }
        )
        return state

    prompt425_executable_plan_ready = (
        run_state.get("prompt425_local_autonomous_loop_invocation_enabled") is True
        and run_state.get("prompt425_local_autonomous_loop_invocation_ready") is True
        and run_state.get("prompt425_invocation_plan_ready") is True
        and run_state.get("prompt425_invocation_mode") == "one_step_plan"
        and invocation_step
        in {
            "start_next_success_cycle",
            "approve_commit_tag_then_next_cycle",
            "retry_targeted_fix",
        }
        and invocation_target_prompt in {"prompt420", "prompt419", "prompt421"}
        and run_state.get("prompt425_codex_invocation_allowed") is False
        and run_state.get("prompt425_git_mutation_allowed") is False
        and run_state.get("prompt425_commit_tag_allowed") is False
        and run_state.get("prompt425_push_allowed") is False
        and run_state.get("prompt425_pr_allowed") is False
        and run_state.get("prompt425_merge_allowed") is False
        and run_state.get("prompt425_rollback_allowed") is False
        and run_state.get("prompt425_next_cycle_started") is False
        and run_state.get("prompt425_unbounded_loop_allowed") is False
        and run_state.get("prompt425_daemon_mode_allowed") is False
    )
    if not prompt425_executable_plan_ready:
        return state

    if not execute_requested or not allow_step_execution:
        state.update(
            {
                "prompt426_bounded_runner_step_executor_status": "ready",
                "prompt426_bounded_runner_step_executor_ready": True,
                "prompt426_bounded_runner_step_executor_blocked_reason": "",
                "prompt426_bounded_runner_step_executor_blocked_reasons": [],
                "prompt426_step_execution_mode": "planned_no_execute",
                "prompt426_step_execution_ready": True,
                "prompt426_step_execution_attempted": False,
                "prompt426_step_execution_performed": False,
                "prompt426_step_execution_status": "not_run",
                "prompt426_step_execution_result_available": False,
                "prompt426_step_execution_result_payload": {},
                "prompt426_step_execution_error": False,
                "prompt426_step_execution_error_message": "",
                "prompt426_stop_required": False,
                "prompt426_next_action": (
                    "request_prompt426_bounded_runner_step_execution"
                ),
            }
        )
        return state

    if step_runner is None:
        state.update(
            {
                "prompt426_bounded_runner_step_executor_status": "blocked",
                "prompt426_bounded_runner_step_executor_ready": False,
                "prompt426_bounded_runner_step_executor_blocked_reason": (
                    "step_runner_missing"
                ),
                "prompt426_bounded_runner_step_executor_blocked_reasons": [
                    "step_runner_missing"
                ],
                "prompt426_step_execution_mode": "blocked",
                "prompt426_step_execution_ready": False,
                "prompt426_step_execution_attempted": False,
                "prompt426_step_execution_performed": False,
                "prompt426_step_execution_status": "blocked",
                "prompt426_step_execution_result_available": False,
                "prompt426_step_execution_result_payload": {},
                "prompt426_step_execution_error": False,
                "prompt426_step_execution_error_message": "",
                "prompt426_stop_required": False,
                "prompt426_next_action": "provide_prompt426_step_runner",
            }
        )
        return state

    try:
        step_result = step_runner(
            invocation_step=invocation_step,
            invocation_target_prompt=invocation_target_prompt,
            invocation_order=invocation_order,
            current_cycle=normalized_current_cycle,
            max_cycles=normalized_max_cycles,
            run_state_payload=run_state_payload,
        )
        result_payload = dict(step_result) if isinstance(step_result, Mapping) else {}
        execution_status = _normalize_text(
            result_payload.get("status"),
            default="completed",
        )
        state.update(
            {
                "prompt426_bounded_runner_step_executor_status": "executed",
                "prompt426_bounded_runner_step_executor_ready": True,
                "prompt426_bounded_runner_step_executor_blocked_reason": "",
                "prompt426_bounded_runner_step_executor_blocked_reasons": [],
                "prompt426_step_execution_mode": "bounded_step_runner",
                "prompt426_step_execution_ready": True,
                "prompt426_step_execution_attempted": True,
                "prompt426_step_execution_performed": True,
                "prompt426_step_execution_status": execution_status,
                "prompt426_step_execution_result_available": True,
                "prompt426_step_execution_result_payload": result_payload,
                "prompt426_step_execution_error": False,
                "prompt426_step_execution_error_message": "",
                "prompt426_stop_required": False,
                "prompt426_next_action": (
                    "review_prompt426_step_execution_result"
                ),
            }
        )
        return state
    except Exception as exc:
        state.update(
            {
                "prompt426_bounded_runner_step_executor_status": (
                    "execution_error"
                ),
                "prompt426_bounded_runner_step_executor_ready": True,
                "prompt426_bounded_runner_step_executor_blocked_reason": "",
                "prompt426_bounded_runner_step_executor_blocked_reasons": [],
                "prompt426_step_execution_mode": "bounded_step_runner",
                "prompt426_step_execution_ready": True,
                "prompt426_step_execution_attempted": True,
                "prompt426_step_execution_performed": True,
                "prompt426_step_execution_status": "execution_error",
                "prompt426_step_execution_result_available": False,
                "prompt426_step_execution_result_payload": {},
                "prompt426_step_execution_error": True,
                "prompt426_step_execution_error_message": str(exc),
                "prompt426_stop_required": False,
                "prompt426_next_action": (
                    "review_prompt426_step_execution_error"
                ),
            }
        )
        return state

def _build_prompt427_bounded_multi_cycle_loop_runner_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
    loop_requested: bool = False,
    allow_bounded_loop: bool = False,
    current_cycle: int | None = None,
    max_cycles: int = 2,
    step_executor: Callable[..., Mapping[str, Any] | None] | None = None,
) -> dict[str, Any]:
    run_state = (
        dict(run_state_payload)
        if isinstance(run_state_payload, Mapping)
        else {}
    )
    normalized_current_cycle = _prompt427_int_like(current_cycle)
    if normalized_current_cycle is None:
        normalized_current_cycle = _prompt427_int_like(
            run_state.get("prompt426_current_cycle")
            or run_state.get("prompt425_current_cycle")
            or 0
        )
    if normalized_current_cycle is None:
        normalized_current_cycle = 0
    normalized_current_cycle = max(normalized_current_cycle, 0)

    normalized_max_cycles = _prompt427_int_like(max_cycles)
    if normalized_max_cycles is None or normalized_max_cycles < 1:
        normalized_max_cycles = 2

    def _base_state() -> dict[str, Any]:
        return {
            "prompt427_bounded_multi_cycle_loop_runner_enabled": True,
            "prompt427_schema_version": _PROMPT427_SCHEMA_VERSION,
            "local_only": True,
            "source_prompt": "prompt427",
            "prompt427_bounded_multi_cycle_loop_runner_ready": False,
            "prompt427_bounded_multi_cycle_loop_runner_status": "blocked",
            "prompt427_bounded_multi_cycle_loop_runner_blocked_reason": "",
            "prompt427_loop_requested": bool(loop_requested),
            "prompt427_allow_bounded_loop": bool(allow_bounded_loop),
            "prompt427_current_cycle": normalized_current_cycle,
            "prompt427_max_cycles": normalized_max_cycles,
            "prompt427_cycle_limit_reached": (
                normalized_current_cycle >= normalized_max_cycles
            ),
            "prompt427_cycle_execution_attempted": False,
            "prompt427_cycle_execution_performed": False,
            "prompt427_cycle_execution_count": 0,
            "prompt427_cycle_results": [],
            "prompt427_final_cycle_status": "",
            "prompt427_stop_required": False,
            "prompt427_stop_reason": "",
            "prompt427_execution_error": False,
            "prompt427_execution_error_message": "",
            "prompt427_codex_invocation_allowed": False,
            "prompt427_git_mutation_allowed": False,
            "prompt427_commit_tag_allowed": False,
            "prompt427_push_allowed": False,
            "prompt427_pr_allowed": False,
            "prompt427_merge_allowed": False,
            "prompt427_rollback_allowed": False,
            "prompt427_unbounded_loop_allowed": False,
            "prompt427_daemon_mode_allowed": False,
            "prompt427_next_action": "",
        }

    state = _base_state()

    if not loop_requested:
        state.update(
            {
                "prompt427_bounded_multi_cycle_loop_runner_ready": True,
                "prompt427_bounded_multi_cycle_loop_runner_status": "ready",
                "prompt427_next_action": (
                    "request_prompt427_bounded_loop_execution"
                ),
            }
        )
        return state

    if not allow_bounded_loop:
        state.update(
            {
                "prompt427_bounded_multi_cycle_loop_runner_ready": False,
                "prompt427_bounded_multi_cycle_loop_runner_status": "blocked",
                "prompt427_bounded_multi_cycle_loop_runner_blocked_reason": (
                    "bounded_loop_execution_not_allowed"
                ),
                "prompt427_cycle_limit_reached": False,
                "prompt427_next_action": (
                    "allow_prompt427_bounded_loop_execution"
                ),
            }
        )
        return state

    if normalized_current_cycle >= normalized_max_cycles:
        state.update(
            {
                "prompt427_bounded_multi_cycle_loop_runner_ready": True,
                "prompt427_bounded_multi_cycle_loop_runner_status": "stopped",
                "prompt427_cycle_limit_reached": True,
                "prompt427_final_cycle_status": "cycle_limit_stop",
                "prompt427_stop_required": True,
                "prompt427_stop_reason": (
                    "bounded_multi_cycle_loop_cycle_limit_reached"
                ),
                "prompt427_next_action": "stop_bounded_multi_cycle_loop",
            }
        )
        return state

    if not callable(step_executor):
        state.update(
            {
                "prompt427_bounded_multi_cycle_loop_runner_ready": False,
                "prompt427_bounded_multi_cycle_loop_runner_status": "blocked",
                "prompt427_bounded_multi_cycle_loop_runner_blocked_reason": (
                    "step_executor_missing"
                ),
                "prompt427_cycle_limit_reached": False,
                "prompt427_next_action": "provide_prompt427_step_executor",
            }
        )
        return state

    cycle_results: list[dict[str, Any]] = []
    previous_cycle_result: dict[str, Any] | None = None
    current = normalized_current_cycle

    def _finalize_cycle_state(
        *,
        status: str,
        ready: bool,
        stop_required: bool,
        stop_reason: str,
        final_cycle_status: str,
        next_action: str,
        execution_error: bool = False,
        execution_error_message: str = "",
    ) -> dict[str, Any]:
        state.update(
            {
                "prompt427_bounded_multi_cycle_loop_runner_ready": ready,
                "prompt427_bounded_multi_cycle_loop_runner_status": status,
                "prompt427_bounded_multi_cycle_loop_runner_blocked_reason": "",
                "prompt427_current_cycle": current,
                "prompt427_cycle_limit_reached": current >= normalized_max_cycles,
                "prompt427_cycle_execution_attempted": True,
                "prompt427_cycle_execution_performed": len(cycle_results) > 0,
                "prompt427_cycle_execution_count": len(cycle_results),
                "prompt427_cycle_results": cycle_results,
                "prompt427_final_cycle_status": final_cycle_status,
                "prompt427_stop_required": stop_required,
                "prompt427_stop_reason": stop_reason,
                "prompt427_execution_error": execution_error,
                "prompt427_execution_error_message": execution_error_message,
                "prompt427_next_action": next_action,
            }
        )
        return state

    for cycle_index in range(normalized_max_cycles - normalized_current_cycle):
        try:
            raw_result = step_executor(
                cycle_index=cycle_index,
                current_cycle=current,
                max_cycles=normalized_max_cycles,
                run_state_payload=run_state_payload,
                previous_cycle_result=previous_cycle_result,
            )
        except Exception as exc:
            current += 1
            return _finalize_cycle_state(
                status="execution_error",
                ready=False,
                stop_required=True,
                stop_reason="step_executor_exception",
                final_cycle_status="execution_error",
                next_action="review_prompt427_step_executor_error",
                execution_error=True,
                execution_error_message=str(exc),
            )

        result = dict(raw_result) if isinstance(raw_result, Mapping) else {}
        cycle_results.append(result)
        previous_cycle_result = result
        current += 1

        result_blocked = (
            result.get("prompt426_bounded_runner_step_executor_status")
            == "blocked"
            or result.get("prompt427_bounded_multi_cycle_loop_runner_status")
            == "blocked"
            or result.get("status") == "blocked"
        )
        if result_blocked:
            return _finalize_cycle_state(
                status="blocked",
                ready=False,
                stop_required=True,
                stop_reason="cycle_result_blocked",
                final_cycle_status="blocked",
                next_action="review_prompt427_blocked_cycle_result",
            )

        result_execution_error = (
            result.get("prompt426_bounded_runner_step_executor_status")
            == "execution_error"
            or result.get("prompt426_step_execution_status")
            == "execution_error"
            or result.get("prompt426_step_execution_error") is True
            or result.get("status") == "execution_error"
        )
        if result_execution_error:
            return _finalize_cycle_state(
                status="execution_error",
                ready=False,
                stop_required=True,
                stop_reason="cycle_result_execution_error",
                final_cycle_status="execution_error",
                next_action="review_prompt427_execution_error_cycle_result",
                execution_error=True,
            )

        result_stop = (
            result.get("prompt426_stop_required") is True
            or result.get("prompt427_stop_required") is True
            or result.get("stop_required") is True
            or result.get("prompt426_bounded_runner_step_executor_status")
            == "stopped"
            or result.get("status") == "stopped"
        )
        if result_stop:
            return _finalize_cycle_state(
                status="stopped",
                ready=True,
                stop_required=True,
                stop_reason="cycle_result_stop_required",
                final_cycle_status="stopped",
                next_action="stop_bounded_multi_cycle_loop",
            )

        if current >= normalized_max_cycles:
            return _finalize_cycle_state(
                status="cycle_limit_stop",
                ready=True,
                stop_required=True,
                stop_reason="bounded_multi_cycle_loop_cycle_limit_reached",
                final_cycle_status="cycle_limit_stop",
                next_action="review_prompt427_bounded_loop_results",
            )

    return _finalize_cycle_state(
        status="cycle_limit_stop",
        ready=True,
        stop_required=True,
        stop_reason="bounded_multi_cycle_loop_cycle_limit_reached",
        final_cycle_status="cycle_limit_stop",
        next_action="review_prompt427_bounded_loop_results",
    )

def _build_prompt428_bounded_runtime_command_artifact_contract_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
    runtime_contract_requested: bool = False,
    allow_runtime_contract: bool = False,
    artifacts_dir: str | None = None,
    out_dir: str | None = None,
    job_id: str | None = None,
    max_cycles: int = 2,
    transport_mode: str = "dry-run",
) -> dict[str, Any]:
    _ = run_state_payload
    normalized_artifacts_dir = _normalize_text(
        artifacts_dir,
        default="/tmp/codex-local-runner-decision/one_cycle_controller",
    )
    normalized_out_dir = _normalize_text(
        out_dir,
        default="/tmp/codex-local-runner-checks/"
        "prompt428_bounded_runtime_contract_out",
    )
    normalized_job_id = _normalize_text(
        job_id,
        default="prompt428-bounded-runtime-contract",
    )
    normalized_max_cycles = _prompt427_int_like(max_cycles)
    if normalized_max_cycles is None or normalized_max_cycles < 1:
        normalized_max_cycles = 2
    normalized_transport_mode = _normalize_text(
        transport_mode,
        default="dry-run",
    )
    expected_artifacts_by_role = {
        "runtime_summary": "prompt428_bounded_runtime_summary.json",
        "runtime_receipt": "prompt428_bounded_runtime_receipt.json",
        "cycle_results": "prompt428_bounded_cycle_results.json",
        "failure_stop": "prompt428_failure_stop_contract.json",
        "final_state": "prompt428_final_state.json",
    }
    expected_artifacts = [
        expected_artifacts_by_role["runtime_summary"],
        expected_artifacts_by_role["runtime_receipt"],
        expected_artifacts_by_role["cycle_results"],
        expected_artifacts_by_role["failure_stop"],
        expected_artifacts_by_role["final_state"],
    ]
    failure_stop_conditions = [
        "py_compile_failed",
        "changed_file_guard_failed",
        "prompt425_invocation_plan_blocked",
        "prompt426_step_execution_error",
        "prompt426_step_execution_blocked",
        "prompt427_loop_blocked",
        "prompt427_loop_execution_error",
        "prompt427_cycle_limit_reached",
        "prompt427_stop_required",
        "runtime_command_returncode_nonzero",
        "unexpected_tracked_changes",
        "unexpected_untracked_files",
    ]
    commit_tag_review_requirements = [
        "runtime_command_completed",
        "expected_artifacts_produced",
        "failure_stop_artifact_reviewed",
        "no_unexpected_tracked_or_untracked_files",
        "py_compile_passes",
        "changed_file_guard_satisfied",
    ]

    state: dict[str, Any] = {
        "prompt428_bounded_runtime_command_artifact_contract_enabled": True,
        "prompt428_schema_version": _PROMPT428_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt428",
        "prompt428_bounded_runtime_command_artifact_contract_ready": False,
        "prompt428_bounded_runtime_command_artifact_contract_status": "blocked",
        "prompt428_bounded_runtime_command_artifact_contract_blocked_reason": "",
        "prompt428_runtime_contract_requested": bool(runtime_contract_requested),
        "prompt428_allow_runtime_contract": bool(allow_runtime_contract),
        "prompt428_transport_mode": normalized_transport_mode,
        "prompt428_max_cycles": normalized_max_cycles,
        "prompt428_required_runtime_inputs": [
            "artifacts_dir",
            "out_dir",
            "job_id",
            "transport_mode",
        ],
        "prompt428_command_plan_ready": False,
        "prompt428_runtime_command_argv": [],
        "prompt428_artifact_contract_ready": False,
        "prompt428_expected_artifacts_dir": normalized_artifacts_dir,
        "prompt428_expected_out_dir": normalized_out_dir,
        "prompt428_expected_job_id": normalized_job_id,
        "prompt428_expected_runtime_summary_artifact": (
            expected_artifacts_by_role["runtime_summary"]
        ),
        "prompt428_expected_runtime_receipt_artifact": (
            expected_artifacts_by_role["runtime_receipt"]
        ),
        "prompt428_expected_cycle_results_artifact": (
            expected_artifacts_by_role["cycle_results"]
        ),
        "prompt428_expected_failure_stop_artifact": (
            expected_artifacts_by_role["failure_stop"]
        ),
        "prompt428_expected_final_state_artifact": (
            expected_artifacts_by_role["final_state"]
        ),
        "prompt428_expected_artifacts": expected_artifacts,
        "prompt428_failure_stop_contract_ready": False,
        "prompt428_failure_stop_conditions": failure_stop_conditions,
        "prompt428_review_required_before_commit_tag": True,
        "prompt428_commit_tag_review_requirements": (
            commit_tag_review_requirements
        ),
        "prompt428_commit_tag_handoff_ready": False,
        "prompt428_commit_tag_allowed": False,
        "prompt428_commit_tag_performed": False,
        "prompt428_codex_invocation_allowed": False,
        "prompt428_git_mutation_allowed": False,
        "prompt428_push_allowed": False,
        "prompt428_pr_allowed": False,
        "prompt428_merge_allowed": False,
        "prompt428_rollback_allowed": False,
        "prompt428_unbounded_loop_allowed": False,
        "prompt428_daemon_mode_allowed": False,
        "prompt428_runtime_command_executed": False,
        "prompt428_next_action": "",
    }

    if not runtime_contract_requested:
        state.update(
            {
                "prompt428_bounded_runtime_command_artifact_contract_ready": True,
                "prompt428_bounded_runtime_command_artifact_contract_status": (
                    "ready"
                ),
                "prompt428_next_action": (
                    "request_prompt428_runtime_contract"
                ),
            }
        )
        return state

    if not allow_runtime_contract:
        state.update(
            {
                "prompt428_bounded_runtime_command_artifact_contract_ready": False,
                "prompt428_bounded_runtime_command_artifact_contract_status": (
                    "blocked"
                ),
                "prompt428_bounded_runtime_command_artifact_contract_blocked_reason": (
                    "runtime_contract_not_allowed"
                ),
                "prompt428_next_action": "allow_prompt428_runtime_contract",
            }
        )
        return state

    if normalized_transport_mode not in {"dry-run", "live"}:
        state.update(
            {
                "prompt428_bounded_runtime_command_artifact_contract_ready": False,
                "prompt428_bounded_runtime_command_artifact_contract_status": (
                    "blocked"
                ),
                "prompt428_bounded_runtime_command_artifact_contract_blocked_reason": (
                    "invalid_transport_mode"
                ),
                "prompt428_next_action": (
                    "select_supported_prompt428_transport_mode"
                ),
            }
        )
        return state

    command_argv = [
        "python",
        "scripts/run_planned_execution.py",
        "--artifacts-dir",
        normalized_artifacts_dir,
        "--out-dir",
        normalized_out_dir,
        "--job-id",
        normalized_job_id,
        "--transport-mode",
        normalized_transport_mode,
        "--json",
    ]
    if normalized_transport_mode == "live":
        command_argv.extend(
            [
                "--enable-live-transport",
                "--live-timeout-seconds",
                "120",
            ]
        )

    state.update(
        {
            "prompt428_bounded_runtime_command_artifact_contract_ready": True,
            "prompt428_bounded_runtime_command_artifact_contract_status": (
                "contract_ready"
            ),
            "prompt428_command_plan_ready": True,
            "prompt428_runtime_command_argv": command_argv,
            "prompt428_artifact_contract_ready": True,
            "prompt428_failure_stop_contract_ready": True,
            "prompt428_commit_tag_handoff_ready": True,
            "prompt428_next_action": (
                "run_prompt428_runtime_command_and_review_artifacts"
            ),
        }
    )
    return state

def _build_prompt429_bounded_runtime_launch_readiness_gate_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
    launch_requested: bool = False,
    allow_runtime_launch: bool = False,
) -> dict[str, Any]:
    payload = (
        run_state_payload if isinstance(run_state_payload, Mapping) else {}
    )
    command_argv = payload.get("prompt428_runtime_command_argv")
    expected_artifacts = payload.get("prompt428_expected_artifacts")
    failure_stop_conditions = payload.get(
        "prompt428_failure_stop_conditions"
    )
    command_argv_ready = (
        isinstance(command_argv, list) and len(command_argv) > 0
    )
    expected_artifacts_ready = (
        isinstance(expected_artifacts, list) and len(expected_artifacts) > 0
    )
    failure_stop_contract_ready = (
        payload.get("prompt428_failure_stop_contract_ready") is True
        and isinstance(failure_stop_conditions, list)
        and len(failure_stop_conditions) > 0
    )
    prompt428_contract_ready = (
        payload.get(
            "prompt428_bounded_runtime_command_artifact_contract_ready"
        )
        is True
        and payload.get(
            "prompt428_bounded_runtime_command_artifact_contract_status"
        )
        == "contract_ready"
        and payload.get("prompt428_command_plan_ready") is True
        and payload.get("prompt428_artifact_contract_ready") is True
        and payload.get("prompt428_failure_stop_contract_ready") is True
    )
    runtime_command_already_executed = (
        payload.get("prompt428_runtime_command_executed") is True
    )
    launch_packet = {
        "command_argv": (
            list(command_argv)
            if isinstance(command_argv, list)
            else command_argv
        ),
        "expected_artifacts": (
            list(expected_artifacts)
            if isinstance(expected_artifacts, list)
            else expected_artifacts
        ),
        "failure_stop_conditions": (
            list(failure_stop_conditions)
            if isinstance(failure_stop_conditions, list)
            else failure_stop_conditions
        ),
        "review_required_before_commit_tag": payload.get(
            "prompt428_review_required_before_commit_tag"
        ),
        "expected_artifacts_dir": payload.get(
            "prompt428_expected_artifacts_dir"
        ),
        "expected_out_dir": payload.get("prompt428_expected_out_dir"),
        "expected_job_id": payload.get("prompt428_expected_job_id"),
        "transport_mode": payload.get("prompt428_transport_mode"),
        "launch_execution_policy": "external_only",
        "launch_execution_performed": False,
    }

    status = "blocked"
    ready = False
    blocked_reason = ""
    launch_packet_ready = False
    launch_allowed = False
    next_action = "review_prompt428_runtime_contract"

    if not launch_requested:
        status = "ready"
        ready = True
        next_action = "request_prompt429_runtime_launch"
    elif not allow_runtime_launch:
        blocked_reason = "runtime_launch_not_allowed"
        next_action = "allow_prompt429_runtime_launch"
    elif runtime_command_already_executed:
        blocked_reason = "runtime_command_already_executed"
        next_action = "review_existing_runtime_execution_result"
    elif not prompt428_contract_ready:
        blocked_reason = "prompt428_runtime_contract_not_ready"
        next_action = "review_prompt428_runtime_contract"
    elif not command_argv_ready:
        blocked_reason = "runtime_command_argv_not_ready"
        next_action = "fix_prompt428_runtime_command_argv"
    elif not expected_artifacts_ready:
        blocked_reason = "expected_artifacts_not_ready"
        next_action = "fix_prompt428_expected_artifacts"
    elif not failure_stop_contract_ready:
        blocked_reason = "failure_stop_contract_not_ready"
        next_action = "fix_prompt428_failure_stop_contract"
    else:
        status = "launch_packet_ready"
        ready = True
        launch_packet_ready = True
        launch_allowed = True
        next_action = "execute_prompt429_runtime_launch_packet_externally"

    return {
        "prompt429_bounded_runtime_launch_readiness_gate_enabled": True,
        "prompt429_schema_version": _PROMPT429_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt429",
        "prompt429_bounded_runtime_launch_readiness_gate_ready": ready,
        "prompt429_bounded_runtime_launch_readiness_gate_status": status,
        "prompt429_bounded_runtime_launch_readiness_gate_blocked_reason": (
            blocked_reason
        ),
        "prompt429_launch_requested": bool(launch_requested),
        "prompt429_allow_runtime_launch": bool(allow_runtime_launch),
        "prompt429_prompt428_contract_ready": prompt428_contract_ready,
        "prompt429_command_argv_ready": command_argv_ready,
        "prompt429_expected_artifacts_ready": expected_artifacts_ready,
        "prompt429_failure_stop_contract_ready": failure_stop_contract_ready,
        "prompt429_runtime_command_already_executed": (
            runtime_command_already_executed
        ),
        "prompt429_launch_packet_ready": launch_packet_ready,
        "prompt429_launch_allowed": launch_allowed,
        "prompt429_launch_performed": False,
        "prompt429_runtime_launch_packet": launch_packet,
        "prompt429_codex_invocation_allowed": False,
        "prompt429_git_mutation_allowed": False,
        "prompt429_commit_tag_allowed": False,
        "prompt429_push_allowed": False,
        "prompt429_pr_allowed": False,
        "prompt429_merge_allowed": False,
        "prompt429_rollback_allowed": False,
        "prompt429_unbounded_loop_allowed": False,
        "prompt429_daemon_mode_allowed": False,
        "prompt429_runtime_command_executed": False,
        "prompt429_next_action": next_action,
    }

def _build_prompt437_runtime_command_artifact_wiring_state(
    *,
    allow_runtime_command_artifact: bool = False,
    runtime_command_artifact_path: str | Path | None = None,
    runtime_command_json: str | None = None,
) -> dict[str, Any]:
    artifact_path_text = _normalize_text(runtime_command_artifact_path, default="")
    inline_json_text = _normalize_text(runtime_command_json, default="")
    inline_json_provided = bool(inline_json_text)
    artifact_provided = bool(artifact_path_text)
    request_provided = artifact_provided or inline_json_provided
    source = "none"
    loaded = False
    valid = False
    blocked_reason = ""
    validation_status = "not_requested"
    next_action = "provide_prompt437_runtime_command_request"
    normalized_request: dict[str, Any] = {}
    raw_explicit_allow_present = False
    raw_explicit_allow_source = ""
    raw_explicit_allow_keys_present: list[str] = []
    raw_prompt474_explicit_targeted_fix_allow_present = False
    raw_prompt474_allow_bounded_targeted_fix_execution = False
    raw_prompt474_allow_codex_invocation = False
    raw_prompt474_runtime_execution_requested = False
    raw_prompt478_explicit_two_cycle_live_allow_present = False
    raw_prompt478_allow_two_cycle_live_execution = False
    raw_prompt478_allow_cycle_0_codex_invocation = False
    raw_prompt478_allow_cycle_1_codex_invocation = False
    raw_prompt478_runtime_execution_requested = False
    raw_prompt479_config_payload: dict[str, Any] = {}
    raw_prompt481_config_payload: dict[str, Any] = {}
    raw_prompt481_allow_repeated_cycle_smoke = False
    raw_prompt481_allow_cycle_0_codex_invocation = False
    raw_prompt481_allow_cycle_1_codex_invocation = False
    raw_prompt481_allow_cycle_2_codex_invocation = False
    raw_prompt481_runtime_execution_requested = False
    raw_prompt483_config_payload: dict[str, Any] = {}

    if request_provided and not allow_runtime_command_artifact:
        validation_status = "blocked"
        blocked_reason = "runtime_command_artifact_not_allowed"
        next_action = "allow_prompt437_runtime_command_artifact"
    elif request_provided:
        source = "inline_json" if inline_json_provided else "artifact"
        try:
            raw_payload = (
                json.loads(inline_json_text)
                if inline_json_provided
                else json.loads(Path(artifact_path_text).read_text(encoding="utf-8"))
            )
            if not isinstance(raw_payload, Mapping):
                validation_status = "invalid"
                blocked_reason = "invalid_runtime_command_request"
                next_action = "fix_prompt437_runtime_command_request"
            else:
                loaded = True
                raw_prompt479_config_payload = {
                    key: raw_payload.get(key)
                    for key in (
                        "prompt479_max_runtime_seconds",
                        "prompt479_max_cycles",
                        "prompt479_max_invocations",
                        "max_runtime_seconds",
                        "max_cycles",
                        "max_invocations",
                    )
                    if key in raw_payload
                }
                raw_prompt481_config_payload = {
                    key: raw_payload.get(key)
                    for key in (
                        "prompt481_requested_cycle_count",
                        "prompt481_max_cycles",
                        "prompt481_max_invocations",
                        "prompt481_max_runtime_seconds",
                    )
                    if key in raw_payload
                }
                raw_prompt483_config_payload = {
                    key: raw_payload.get(key)
                    for key in (
                        "prompt483_role_catalog_path",
                        "prompt483_selected_role_id",
                        "prompt_role_catalog_path",
                        "prompt_role_id",
                        "selected_role_id",
                    )
                    if key in raw_payload
                }
                (
                    raw_explicit_allow_present,
                    raw_explicit_allow_source,
                    raw_explicit_allow_keys_present,
                ) = _extract_explicit_commit_tag_allow_metadata_from_mapping(
                    raw_payload
                )
                raw_prompt474_explicit_targeted_fix_allow_present = (
                    raw_payload.get(
                        "prompt474_explicit_targeted_fix_allow_present"
                    )
                    is True
                )
                raw_prompt474_allow_bounded_targeted_fix_execution = (
                    raw_payload.get(
                        "prompt474_allow_bounded_targeted_fix_execution"
                    )
                    is True
                )
                raw_prompt474_allow_codex_invocation = (
                    raw_payload.get("prompt474_allow_codex_invocation") is True
                    or raw_payload.get("allow_codex_invocation") is True
                )
                raw_prompt474_runtime_execution_requested = (
                    raw_payload.get("prompt474_runtime_execution_requested") is True
                    or raw_payload.get("request_codex_invocation") is True
                )
                raw_prompt478_explicit_two_cycle_live_allow_present = (
                    raw_payload.get(
                        "prompt478_explicit_two_cycle_live_allow_present"
                    )
                    is True
                )
                raw_prompt478_allow_two_cycle_live_execution = (
                    raw_payload.get("prompt478_allow_two_cycle_live_execution")
                    is True
                )
                raw_prompt478_allow_cycle_0_codex_invocation = (
                    raw_payload.get("prompt478_allow_cycle_0_codex_invocation")
                    is True
                )
                raw_prompt478_allow_cycle_1_codex_invocation = (
                    raw_payload.get("prompt478_allow_cycle_1_codex_invocation")
                    is True
                )
                raw_prompt478_runtime_execution_requested = (
                    raw_payload.get("prompt478_runtime_execution_requested") is True
                )
                raw_prompt481_allow_repeated_cycle_smoke = (
                    raw_payload.get("prompt481_allow_repeated_cycle_smoke") is True
                )
                raw_prompt481_allow_cycle_0_codex_invocation = (
                    raw_payload.get("prompt481_allow_cycle_0_codex_invocation")
                    is True
                )
                raw_prompt481_allow_cycle_1_codex_invocation = (
                    raw_payload.get("prompt481_allow_cycle_1_codex_invocation")
                    is True
                )
                raw_prompt481_allow_cycle_2_codex_invocation = (
                    raw_payload.get("prompt481_allow_cycle_2_codex_invocation")
                    is True
                )
                raw_prompt481_runtime_execution_requested = (
                    raw_payload.get("prompt481_runtime_execution_requested") is True
                )
                normalized_request, validation_error = (
                    _normalize_prompt437_runtime_command_request(raw_payload)
                )
                if validation_error:
                    validation_status = "invalid"
                    blocked_reason = "invalid_runtime_command_request"
                    next_action = "fix_prompt437_runtime_command_request"
                else:
                    valid = True
                    validation_status = "valid"
                    next_action = "prompt437_runtime_command_request_ready"
        except json.JSONDecodeError:
            validation_status = "error"
            blocked_reason = "runtime_command_json_parse_error"
            next_action = "fix_prompt437_runtime_command_request"
        except OSError:
            validation_status = "error"
            blocked_reason = "runtime_command_artifact_read_error"
            next_action = "fix_prompt437_runtime_command_request"

    (
        normalized_explicit_allow_present,
        normalized_explicit_allow_source,
        normalized_explicit_allow_keys_present,
    ) = _extract_explicit_commit_tag_allow_metadata_from_mapping(
        normalized_request
    )
    explicit_allow_missing_reason = ""
    if raw_explicit_allow_present and not normalized_explicit_allow_present:
        explicit_allow_missing_reason = (
            "runtime_command_json_explicit_allow_not_exposed"
        )

    return {
        "prompt437_runtime_command_artifact_wiring_enabled": True,
        "prompt437_schema_version": _PROMPT437_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt437",
        "prompt437_allow_runtime_command_artifact": bool(
            allow_runtime_command_artifact
        ),
        "prompt437_runtime_command_artifact_path": artifact_path_text,
        "prompt437_runtime_command_json_provided": inline_json_provided,
        "prompt437_runtime_command_request_loaded": loaded,
        "prompt437_runtime_command_request_valid": valid,
        "prompt437_runtime_command_request_source": source,
        "prompt437_runtime_command_argv": list(
            normalized_request.get("command_argv", [])
        )
        if isinstance(normalized_request.get("command_argv"), list)
        else [],
        "prompt437_runtime_command_request_id": _normalize_text(
            normalized_request.get("request_id"),
            default="",
        ),
        "prompt437_runtime_command_validation_status": validation_status,
        "prompt437_blocked_reason": blocked_reason,
        "prompt437_next_action": next_action,
        "prompt437_runtime_command_request": normalized_request if valid else {},
        "prompt474_explicit_targeted_fix_allow_present": (
            raw_prompt474_explicit_targeted_fix_allow_present
        ),
        "prompt474_allow_bounded_targeted_fix_execution": (
            raw_prompt474_allow_bounded_targeted_fix_execution
        ),
        "prompt474_allow_codex_invocation": raw_prompt474_allow_codex_invocation,
        "prompt474_runtime_execution_requested": (
            raw_prompt474_runtime_execution_requested
        ),
        "prompt478_explicit_two_cycle_live_allow_present": (
            raw_prompt478_explicit_two_cycle_live_allow_present
        ),
        "prompt478_allow_two_cycle_live_execution": (
            raw_prompt478_allow_two_cycle_live_execution
        ),
        "prompt478_allow_cycle_0_codex_invocation": (
            raw_prompt478_allow_cycle_0_codex_invocation
        ),
        "prompt478_allow_cycle_1_codex_invocation": (
            raw_prompt478_allow_cycle_1_codex_invocation
        ),
        "prompt478_runtime_execution_requested": (
            raw_prompt478_runtime_execution_requested
        ),
        **raw_prompt479_config_payload,
        **raw_prompt481_config_payload,
        **raw_prompt483_config_payload,
        "prompt481_allow_repeated_cycle_smoke": (
            raw_prompt481_allow_repeated_cycle_smoke
        ),
        "prompt481_allow_cycle_0_codex_invocation": (
            raw_prompt481_allow_cycle_0_codex_invocation
        ),
        "prompt481_allow_cycle_1_codex_invocation": (
            raw_prompt481_allow_cycle_1_codex_invocation
        ),
        "prompt481_allow_cycle_2_codex_invocation": (
            raw_prompt481_allow_cycle_2_codex_invocation
        ),
        "prompt481_runtime_execution_requested": (
            raw_prompt481_runtime_execution_requested
        ),
        "prompt456_runtime_command_explicit_commit_tag_allow_present": (
            normalized_explicit_allow_present if valid else False
        ),
        "prompt456_runtime_command_explicit_commit_tag_allow_source": (
            f"prompt437_runtime_command_request.{normalized_explicit_allow_source}"
            if valid and normalized_explicit_allow_source
            else ""
        ),
        "prompt456_runtime_command_explicit_commit_tag_allow_keys_present": (
            list(normalized_explicit_allow_keys_present) if valid else []
        ),
        "prompt456_explicit_commit_tag_allow_source_missing_reason": (
            explicit_allow_missing_reason
        ),
        "prompt437_codex_direct_invocation_allowed": False,
        "prompt437_subprocess_direct_execution_allowed": False,
        "prompt437_git_direct_mutation_allowed": False,
        "prompt437_commit_tag_direct_execution_allowed": False,
        "prompt437_push_allowed": False,
        "prompt437_pr_allowed": False,
        "prompt437_merge_allowed": False,
        "prompt437_rollback_allowed": False,
        "prompt437_unbounded_loop_allowed": False,
        "prompt437_daemon_mode_allowed": False,
    }

def _build_prompt430_dry_run_runtime_command_runner() -> Callable[..., dict[str, Any]]:
    def _command_runner(
        *,
        command_argv: Sequence[str],
        launch_packet: Mapping[str, Any],
        run_state_payload: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        runtime_request = (
            launch_packet.get("runtime_command_request")
            if isinstance(launch_packet, Mapping)
            else {}
        )
        expected_returncode = (
            runtime_request.get("dry_run_expected_returncode")
            if isinstance(runtime_request, Mapping)
            else None
        )
        returncode = (
            expected_returncode
            if isinstance(expected_returncode, int)
            and not isinstance(expected_returncode, bool)
            else None
        )
        request_id = (
            _normalize_text(runtime_request.get("request_id"), default="")
            if isinstance(runtime_request, Mapping)
            else ""
        )
        return {
            "returncode": returncode,
            "stdout": "",
            "stderr": "dry_run_runtime_command_not_executed",
            "stdout_path": "",
            "stderr_path": "",
            "receipt_path": "",
            "dry_run": True,
            "execution_performed": False,
            "command_argv": list(command_argv),
            "request_id": request_id,
            "adapter": "prompt430_dry_run_runtime_command_runner",
            "runtime_command_request": (
                dict(runtime_request)
                if isinstance(runtime_request, Mapping)
                else {}
            ),
            "run_state_id": _normalize_text(
                (run_state_payload or {}).get("run_id")
                if isinstance(run_state_payload, Mapping)
                else "",
                default="",
            ),
        }

    return _command_runner

def _build_prompt440_live_safe_runtime_command_runner_state(
    *,
    transport_mode: str,
    live_transport_enabled: bool,
    prompt437_state: Mapping[str, Any],
    request_runtime_execution: bool,
    allow_runtime_execution: bool,
) -> tuple[dict[str, Any], Callable[..., dict[str, Any]] | None]:
    normalized_transport_mode = _normalize_text(transport_mode, default="dry-run")
    command_argv = prompt437_state.get("prompt437_runtime_command_argv")
    copied_command_argv = list(command_argv) if isinstance(command_argv, list) else []
    prompt437_request_valid = (
        prompt437_state.get("prompt437_runtime_command_request_valid") is True
    )
    live_enabled = normalized_transport_mode == "live" and bool(live_transport_enabled)
    allowlisted = _prompt440_live_command_allowlisted(copied_command_argv)

    state: dict[str, Any] = {
        "prompt440_live_safe_runtime_execution_enabled": live_enabled,
        "prompt440_schema_version": _PROMPT440_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt440",
        "prompt440_transport_mode": normalized_transport_mode,
        "prompt440_live_transport_enabled": bool(live_transport_enabled),
        "prompt440_prompt437_request_valid": prompt437_request_valid,
        "prompt440_prompt436_runtime_execution_requested": bool(
            request_runtime_execution
        ),
        "prompt440_prompt436_runtime_execution_allowed": bool(
            allow_runtime_execution
        ),
        "prompt440_runtime_command_argv": copied_command_argv,
        "prompt440_live_command_allowlisted": False,
        "prompt440_live_command_execution_attempted": False,
        "prompt440_live_command_execution_performed": False,
        "prompt440_live_command_returncode": None,
        "prompt440_live_command_returncode_classification": "unknown",
        "prompt440_live_command_stdout_path": "",
        "prompt440_live_command_stderr_path": "",
        "prompt440_live_command_result_materialized": False,
        "prompt440_blocked_reason": "",
        "prompt440_next_action": "",
        "prompt440_git_direct_mutation_allowed": False,
        "prompt440_commit_tag_direct_execution_allowed": False,
        "prompt440_push_allowed": False,
        "prompt440_pr_allowed": False,
        "prompt440_merge_allowed": False,
        "prompt440_rollback_allowed": False,
        "prompt440_unbounded_loop_allowed": False,
        "prompt440_daemon_mode_allowed": False,
    }

    if not live_enabled:
        state["prompt440_next_action"] = (
            "prompt440_live_safe_runtime_result_ready"
            if normalized_transport_mode != "live"
            else "enable_live_transport"
        )
        return state, None
    if not prompt437_request_valid:
        state.update(
            {
                "prompt440_blocked_reason": "prompt437_runtime_command_request_not_valid",
                "prompt440_next_action": (
                    "provide_prompt437_runtime_command_request"
                ),
            }
        )
        return state, None
    if not request_runtime_execution:
        state.update(
            {
                "prompt440_blocked_reason": "prompt436_runtime_execution_not_requested",
                "prompt440_next_action": "request_prompt436_runtime_execution",
            }
        )
        return state, None
    if not allow_runtime_execution:
        state.update(
            {
                "prompt440_blocked_reason": "prompt436_runtime_execution_not_allowed",
                "prompt440_next_action": "allow_prompt436_runtime_execution",
            }
        )
        return state, None
    state["prompt440_live_command_allowlisted"] = allowlisted
    if not allowlisted:
        state.update(
            {
                "prompt440_blocked_reason": "prompt440_live_command_not_allowlisted",
                "prompt440_next_action": "allow_prompt440_live_safe_command",
            }
        )
        return state, None

    def _command_runner(
        *,
        command_argv: Sequence[str],
        launch_packet: Mapping[str, Any],
        run_state_payload: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        runtime_request = (
            launch_packet.get("runtime_command_request")
            if isinstance(launch_packet, Mapping)
            else {}
        )
        if not isinstance(runtime_request, Mapping):
            runtime_request = {}
        timeout_seconds = _prompt440_normalize_timeout_seconds(
            runtime_request.get("timeout_seconds")
        )
        cwd = runtime_request.get("cwd")
        subprocess_cwd = cwd if isinstance(cwd, str) and cwd else None
        env_payload = runtime_request.get("env")
        subprocess_env = None
        if isinstance(env_payload, Mapping):
            subprocess_env = {
                **os.environ,
                **{
                    key: value
                    for key, value in env_payload.items()
                    if isinstance(key, str) and isinstance(value, str)
                },
            }
        result_payload: dict[str, Any] = {
            "stdout_path": "",
            "stderr_path": "",
            "receipt_path": "",
            "dry_run": False,
            "execution_performed": False,
            "command_argv": list(command_argv),
            "request_id": _normalize_text(
                runtime_request.get("request_id"),
                default="",
            ),
            "adapter": "prompt440_live_safe_bounded_command_runner",
            "runtime_command_request": dict(runtime_request),
            "timeout_seconds": timeout_seconds,
            "run_state_id": _normalize_text(
                (run_state_payload or {}).get("run_id")
                if isinstance(run_state_payload, Mapping)
                else "",
                default="",
            ),
            "prompt440_live_command_allowlisted": True,
            "prompt440_live_command_execution_attempted": True,
        }
        try:
            completed = subprocess.run(
                list(command_argv),
                shell=False,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                cwd=subprocess_cwd,
                env=subprocess_env,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout if isinstance(exc.stdout, str) else ""
            stderr = exc.stderr if isinstance(exc.stderr, str) else ""
            result_payload.update(
                {
                    "returncode": None,
                    "returncode_classification": "timeout",
                    "stdout": stdout,
                    "stderr": stderr,
                    "execution_performed": True,
                    "timeout": True,
                    "prompt440_live_command_execution_performed": True,
                    "prompt440_live_command_returncode": None,
                    "prompt440_live_command_returncode_classification": "timeout",
                    "prompt440_live_command_result_materialized": True,
                    "prompt440_blocked_reason": "prompt440_live_command_timeout",
                    "prompt440_next_action": (
                        "prompt440_live_safe_runtime_result_ready"
                    ),
                }
            )
            return result_payload

        classification = "success" if completed.returncode == 0 else "failed"
        result_payload.update(
            {
                "returncode": completed.returncode,
                "returncode_classification": classification,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
                "execution_performed": True,
                "prompt440_live_command_execution_performed": True,
                "prompt440_live_command_returncode": completed.returncode,
                "prompt440_live_command_returncode_classification": classification,
                "prompt440_live_command_result_materialized": True,
                "prompt440_next_action": (
                    "prompt440_live_safe_runtime_result_ready"
                ),
            }
        )
        return result_payload

    state.update(
        {
            "prompt440_live_command_allowlisted": True,
            "prompt440_next_action": "review_prompt440_live_command_result",
        }
    )
    return state, _command_runner

def _build_prompt441_bounded_codex_invocation_state(
    *,
    transport_mode: str,
    live_transport_enabled: bool,
    prompt437_state: Mapping[str, Any],
    request_runtime_execution: bool,
    allow_runtime_execution: bool,
) -> tuple[dict[str, Any], Callable[..., dict[str, Any]] | None]:
    normalized_transport_mode = _normalize_text(transport_mode, default="dry-run")
    prompt437_request_valid = (
        prompt437_state.get("prompt437_runtime_command_request_valid") is True
    )
    runtime_request = prompt437_state.get("prompt437_runtime_command_request")
    if not isinstance(runtime_request, Mapping):
        runtime_request = {}
    command_argv = prompt437_state.get("prompt437_runtime_command_argv")
    copied_command_argv = list(command_argv) if isinstance(command_argv, list) else []
    requested = runtime_request.get("request_codex_invocation") is True
    allowed = runtime_request.get("allow_codex_invocation") is True
    prompt_artifact_path_text = _normalize_text(
        runtime_request.get("codex_prompt_artifact_path"),
        default="",
    )
    prompt_artifact_exists = False
    prompt_artifact_path: Path | None = None
    if prompt_artifact_path_text:
        prompt_artifact_path = Path(prompt_artifact_path_text)
        prompt_artifact_exists = prompt_artifact_path.exists() and prompt_artifact_path.is_file()
    command_allowlisted = _prompt441_codex_command_allowlisted(copied_command_argv)

    state: dict[str, Any] = {
        "prompt441_schema_version": _PROMPT441_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt441",
        "prompt441_bounded_codex_invocation_status": "blocked",
        "prompt441_codex_invocation_requested": requested,
        "prompt441_codex_invocation_allowed": allowed,
        "prompt441_codex_prompt_artifact_path": prompt_artifact_path_text,
        "prompt441_codex_prompt_artifact_exists": prompt_artifact_exists,
        "prompt441_codex_command_argv": copied_command_argv,
        "prompt441_codex_command_allowlisted": command_allowlisted,
        "prompt441_codex_execution_attempted": False,
        "prompt441_codex_execution_performed": False,
        "prompt441_codex_returncode": None,
        "prompt441_codex_returncode_classification": "unknown",
        "prompt441_codex_stdout_path": "",
        "prompt441_codex_stderr_path": "",
        "prompt441_codex_result_materialized": False,
        "prompt441_blocked_reason": "",
        "prompt441_next_action": "",
        "prompt441_git_mutation_performed": False,
        "prompt441_remote_mutation_performed": False,
        "prompt441_commit_tag_performed": False,
    }

    live_enabled = normalized_transport_mode == "live" and bool(live_transport_enabled)
    if not requested:
        state.update(
            {
                "prompt441_bounded_codex_invocation_status": "not_requested",
                "prompt441_blocked_reason": "prompt441_codex_invocation_not_requested",
                "prompt441_next_action": "request_prompt441_codex_invocation",
            }
        )
        return state, None
    if not allowed:
        state.update(
            {
                "prompt441_blocked_reason": "prompt441_codex_invocation_not_allowed",
                "prompt441_next_action": "allow_prompt441_codex_invocation",
            }
        )
        return state, None
    if not live_enabled:
        state.update(
            {
                "prompt441_blocked_reason": "prompt441_live_transport_not_enabled",
                "prompt441_next_action": "enable_live_transport",
            }
        )
        return state, None
    if not request_runtime_execution:
        state.update(
            {
                "prompt441_blocked_reason": "prompt441_runtime_execution_not_requested",
                "prompt441_next_action": "request_prompt436_runtime_execution",
            }
        )
        return state, None
    if not allow_runtime_execution:
        state.update(
            {
                "prompt441_blocked_reason": "prompt441_runtime_execution_not_allowed",
                "prompt441_next_action": "allow_prompt436_runtime_execution",
            }
        )
        return state, None
    if not prompt437_request_valid:
        state.update(
            {
                "prompt441_blocked_reason": "prompt437_runtime_command_request_not_valid",
                "prompt441_next_action": "provide_prompt437_runtime_command_request",
            }
        )
        return state, None
    if not command_allowlisted:
        state.update(
            {
                "prompt441_blocked_reason": "prompt441_codex_command_not_allowlisted",
                "prompt441_codex_execution_attempted": False,
                "prompt441_codex_execution_performed": False,
                "prompt441_codex_result_materialized": False,
                "prompt441_next_action": "use_prompt441_codex_exec_dash_command",
            }
        )
        return state, None
    if not prompt_artifact_path_text:
        state.update(
            {
                "prompt441_blocked_reason": "prompt441_prompt_artifact_path_missing",
                "prompt441_next_action": "provide_prompt441_prompt_artifact_path",
            }
        )
        return state, None
    if prompt_artifact_path is None or not prompt_artifact_exists:
        state.update(
            {
                "prompt441_blocked_reason": "prompt441_prompt_artifact_not_found",
                "prompt441_next_action": "provide_existing_prompt441_prompt_artifact",
            }
        )
        return state, None

    def _command_runner(
        *,
        command_argv: Sequence[str],
        launch_packet: Mapping[str, Any],
        run_state_payload: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        runtime_request_for_runner = (
            launch_packet.get("runtime_command_request")
            if isinstance(launch_packet, Mapping)
            else {}
        )
        if not isinstance(runtime_request_for_runner, Mapping):
            runtime_request_for_runner = {}
        timeout_seconds = _prompt440_normalize_timeout_seconds(
            runtime_request_for_runner.get("timeout_seconds")
        )
        payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
        out_dir_text = _normalize_text(payload.get("prompt428_expected_out_dir"), default="")
        job_id_text = _normalize_text(payload.get("run_id"), default="")
        if not job_id_text:
            job_id_text = _normalize_text(payload.get("prompt428_expected_job_id"), default="")
        output_root = Path(out_dir_text) if out_dir_text else Path(".")
        result_dir = output_root / job_id_text if job_id_text else output_root
        stdout_path = result_dir / "prompt441_codex_stdout.txt"
        stderr_path = result_dir / "prompt441_codex_stderr.txt"
        receipt_path = result_dir / "prompt441_codex_result.json"

        result_payload: dict[str, Any] = {
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
            "receipt_path": str(receipt_path),
            "dry_run": False,
            "execution_performed": False,
            "command_argv": list(command_argv),
            "request_id": _normalize_text(
                runtime_request_for_runner.get("request_id"),
                default="",
            ),
            "adapter": "prompt441_bounded_codex_invocation_adapter",
            "runtime_command_request": dict(runtime_request_for_runner),
            "timeout_seconds": timeout_seconds,
            "run_state_id": job_id_text,
            "prompt441_codex_invocation_requested": True,
            "prompt441_codex_invocation_allowed": True,
            "prompt441_codex_prompt_artifact_path": prompt_artifact_path_text,
            "prompt441_codex_prompt_artifact_exists": True,
            "prompt441_codex_command_argv": list(_PROMPT441_CODEX_COMMAND_ARGV),
            "prompt441_codex_command_allowlisted": True,
            "prompt441_codex_execution_attempted": True,
            "prompt441_codex_execution_performed": False,
            "prompt441_git_mutation_performed": False,
            "prompt441_remote_mutation_performed": False,
            "prompt441_commit_tag_performed": False,
        }
        prompt_text = prompt_artifact_path.read_text(encoding="utf-8")
        try:
            completed = subprocess.run(
                list(_PROMPT441_CODEX_COMMAND_ARGV),
                input=prompt_text,
                capture_output=True,
                text=True,
                shell=False,
                timeout=timeout_seconds,
                check=False,
            )
            classification = "success" if completed.returncode == 0 else "failed"
            stdout = completed.stdout
            stderr = completed.stderr
            result_payload.update(
                {
                    "returncode": completed.returncode,
                    "returncode_classification": classification,
                    "stdout": stdout,
                    "stderr": stderr,
                    "execution_performed": True,
                    "prompt441_bounded_codex_invocation_status": "executed",
                    "prompt441_codex_execution_performed": True,
                    "prompt441_codex_returncode": completed.returncode,
                    "prompt441_codex_returncode_classification": classification,
                    "prompt441_codex_stdout_path": str(stdout_path),
                    "prompt441_codex_stderr_path": str(stderr_path),
                    "prompt441_codex_result_materialized": True,
                    "prompt441_next_action": "prompt441_codex_result_ready",
                }
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout if isinstance(exc.stdout, str) else ""
            stderr = exc.stderr if isinstance(exc.stderr, str) else ""
            result_payload.update(
                {
                    "returncode": None,
                    "returncode_classification": "timeout",
                    "stdout": stdout,
                    "stderr": stderr,
                    "execution_performed": True,
                    "timeout": True,
                    "prompt441_bounded_codex_invocation_status": "timeout",
                    "prompt441_codex_execution_performed": True,
                    "prompt441_codex_returncode": None,
                    "prompt441_codex_returncode_classification": "timeout",
                    "prompt441_codex_stdout_path": str(stdout_path),
                    "prompt441_codex_stderr_path": str(stderr_path),
                    "prompt441_codex_result_materialized": True,
                    "prompt441_blocked_reason": "prompt441_codex_execution_timeout",
                    "prompt441_next_action": "prompt441_codex_result_ready",
                }
            )

        stdout_path.parent.mkdir(parents=True, exist_ok=True)
        stdout_path.write_text(_normalize_text(result_payload.get("stdout"), default=""), encoding="utf-8")
        stderr_path.write_text(_normalize_text(result_payload.get("stderr"), default=""), encoding="utf-8")
        _write_json(receipt_path, result_payload)
        return result_payload

    state.update(
        {
            "prompt441_bounded_codex_invocation_status": "ready",
            "prompt441_next_action": "review_prompt441_codex_result",
        }
    )
    return state, _command_runner

def _build_prompt442_codex_post_execution_review_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
    execution_repo_path: str,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    allowed_changed_files = sorted(
        {
            "automation/orchestration/planned_execution_runner.py",
            "scripts/run_planned_execution.py",
        }
    )
    prompt441_result_available = (
        payload.get("prompt441_codex_result_materialized") is True
    )
    prompt441_returncode = _as_optional_int(
        payload.get("prompt441_codex_returncode")
    )
    prompt441_returncode_classification = _normalize_text(
        payload.get("prompt441_codex_returncode_classification"),
        default="unknown",
    )

    state: dict[str, Any] = {
        "prompt442_schema_version": _PROMPT442_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt442",
        "prompt442_codex_post_execution_review_enabled": True,
        "prompt442_prompt441_result_available": prompt441_result_available,
        "prompt442_prompt441_returncode": prompt441_returncode,
        "prompt442_prompt441_returncode_classification": (
            prompt441_returncode_classification
        ),
        "prompt442_git_status_short": [],
        "prompt442_tracked_changed_files": [],
        "prompt442_staged_changed_files": [],
        "prompt442_untracked_files": [],
        "prompt442_allowed_changed_files": allowed_changed_files,
        "prompt442_unexpected_changed_files": [],
        "prompt442_unexpected_untracked_files": [],
        "prompt442_post_codex_diff_empty": False,
        "prompt442_post_codex_changes_present": False,
        "prompt442_post_codex_change_safety_status": "not_reviewed",
        "prompt442_codex_post_execution_route": "not_requested",
        "prompt442_review_status": "not_requested",
        "prompt442_blocked_reason": "",
        "prompt442_next_action": "",
        "prompt442_git_mutation_allowed": False,
        "prompt442_commit_tag_allowed": False,
        "prompt442_push_allowed": False,
        "prompt442_pr_allowed": False,
        "prompt442_merge_allowed": False,
        "prompt442_rollback_allowed": False,
        "prompt442_auto_stage_allowed": False,
        "prompt442_auto_revert_allowed": False,
    }

    if not prompt441_result_available:
        state.update(
            {
                "prompt442_codex_post_execution_route": (
                    "codex_result_not_available"
                ),
                "prompt442_review_status": "blocked",
                "prompt442_blocked_reason": (
                    "prompt441_codex_result_not_available"
                ),
                "prompt442_next_action": "run_prompt441_codex_invocation",
            }
        )
        return state

    repo_path = _normalize_text(execution_repo_path, default="")

    def _run_prompt442_git(args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", repo_path, *args],
            text=True,
            capture_output=True,
            shell=False,
            timeout=10,
            check=False,
        )

    try:
        if not repo_path:
            raise RuntimeError("execution_repo_path_missing")
        status_result = _run_prompt442_git(["status", "--short"])
        tracked_result = _run_prompt442_git(["diff", "--name-only"])
        staged_result = _run_prompt442_git(["diff", "--cached", "--name-only"])
        untracked_result = _run_prompt442_git(
            ["ls-files", "--others", "--exclude-standard"]
        )
    except (OSError, RuntimeError, subprocess.TimeoutExpired):
        state.update(
            {
                "prompt442_post_codex_change_safety_status": (
                    "git_inspection_error"
                ),
                "prompt442_codex_post_execution_route": (
                    "codex_git_inspection_error_stop"
                ),
                "prompt442_review_status": "stop",
                "prompt442_blocked_reason": "prompt442_git_inspection_error",
                "prompt442_next_action": (
                    "stop_for_prompt442_git_inspection_error"
                ),
            }
        )
        return state

    git_results = (status_result, tracked_result, staged_result, untracked_result)
    if any(result.returncode != 0 for result in git_results):
        state.update(
            {
                "prompt442_git_status_short": (
                    status_result.stdout or ""
                ).splitlines(),
                "prompt442_post_codex_change_safety_status": (
                    "git_inspection_error"
                ),
                "prompt442_codex_post_execution_route": (
                    "codex_git_inspection_error_stop"
                ),
                "prompt442_review_status": "stop",
                "prompt442_blocked_reason": "prompt442_git_inspection_error",
                "prompt442_next_action": (
                    "stop_for_prompt442_git_inspection_error"
                ),
            }
        )
        return state

    tracked_changed_files = sorted(
        line.strip()
        for line in (tracked_result.stdout or "").splitlines()
        if line.strip()
    )
    staged_changed_files = sorted(
        line.strip()
        for line in (staged_result.stdout or "").splitlines()
        if line.strip()
    )
    untracked_files = sorted(
        line.strip()
        for line in (untracked_result.stdout or "").splitlines()
        if line.strip()
    )
    status_short = [
        line.rstrip()
        for line in (status_result.stdout or "").splitlines()
        if line.strip()
    ]
    allowed_set = set(allowed_changed_files)
    unexpected_changed_files = sorted(
        {
            *[path for path in tracked_changed_files if path not in allowed_set],
            *staged_changed_files,
        }
    )
    unexpected_untracked_files = sorted(untracked_files)
    changes_present = bool(
        tracked_changed_files or staged_changed_files or untracked_files
    )
    diff_empty = not changes_present

    if diff_empty:
        safety_status = "clean_no_changes"
    elif unexpected_untracked_files:
        safety_status = "unexpected_untracked"
    elif unexpected_changed_files:
        safety_status = "unexpected_changes"
    else:
        safety_status = "allowed_changes"

    state.update(
        {
            "prompt442_git_status_short": status_short,
            "prompt442_tracked_changed_files": tracked_changed_files,
            "prompt442_staged_changed_files": staged_changed_files,
            "prompt442_untracked_files": untracked_files,
            "prompt442_unexpected_changed_files": unexpected_changed_files,
            "prompt442_unexpected_untracked_files": unexpected_untracked_files,
            "prompt442_post_codex_diff_empty": diff_empty,
            "prompt442_post_codex_changes_present": changes_present,
            "prompt442_post_codex_change_safety_status": safety_status,
        }
    )

    if unexpected_changed_files or unexpected_untracked_files:
        state.update(
            {
                "prompt442_codex_post_execution_route": (
                    "codex_unsafe_changes_stop"
                ),
                "prompt442_review_status": "stop",
                "prompt442_blocked_reason": (
                    "prompt442_unexpected_post_codex_changes"
                ),
                "prompt442_next_action": (
                    "stop_for_prompt442_unexpected_changes"
                ),
            }
        )
        return state

    success = (
        prompt441_returncode == 0
        or prompt441_returncode_classification == "success"
    )
    failed = (
        (prompt441_returncode is not None and prompt441_returncode != 0)
        or prompt441_returncode_classification in {
            "failed",
            "timeout",
            "execution_error",
            "nonzero",
            "nonzero_exit",
            "execution_failed",
        }
    )
    if success and diff_empty:
        state.update(
            {
                "prompt442_codex_post_execution_route": (
                    "codex_success_no_changes"
                ),
                "prompt442_review_status": "reviewed",
                "prompt442_next_action": "review_codex_no_changes",
            }
        )
    elif success:
        state.update(
            {
                "prompt442_codex_post_execution_route": (
                    "codex_success_with_allowed_changes"
                ),
                "prompt442_review_status": "reviewed",
                "prompt442_next_action": (
                    "prepare_prompt443_success_diff_route"
                ),
            }
        )
    elif failed and diff_empty:
        state.update(
            {
                "prompt442_codex_post_execution_route": (
                    "codex_failed_no_changes"
                ),
                "prompt442_review_status": "reviewed",
                "prompt442_next_action": (
                    "prepare_prompt443_targeted_fix_route"
                ),
            }
        )
    else:
        state.update(
            {
                "prompt442_codex_post_execution_route": (
                    "codex_failed_with_changes"
                ),
                "prompt442_review_status": "reviewed",
                "prompt442_next_action": (
                    "prepare_prompt443_targeted_fix_route"
                ),
            }
        )
    return state

def _build_prompt443_success_diff_handoff_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    prompt442_review_status = _normalize_text(
        payload.get("prompt442_review_status"),
        default="",
    )
    prompt442_route = _normalize_text(
        payload.get("prompt442_codex_post_execution_route"),
        default="",
    )
    prompt442_change_safety_status = _normalize_text(
        payload.get("prompt442_post_codex_change_safety_status"),
        default="",
    )
    prompt442_changes_present = bool(
        payload.get("prompt442_post_codex_changes_present", False)
    )
    prompt442_diff_empty = bool(
        payload.get("prompt442_post_codex_diff_empty", False)
    )
    allowed_changed_files = _normalize_string_list(
        payload.get("prompt442_allowed_changed_files"),
        sort_items=True,
    )
    unexpected_changed_files = _normalize_string_list(
        payload.get("prompt442_unexpected_changed_files"),
        sort_items=True,
    )
    unexpected_untracked_files = _normalize_string_list(
        payload.get("prompt442_unexpected_untracked_files"),
        sort_items=True,
    )

    state: dict[str, Any] = {
        "prompt443_schema_version": _PROMPT443_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt443",
        "prompt443_success_diff_handoff_status": "blocked",
        "prompt443_prompt442_review_status": prompt442_review_status,
        "prompt443_prompt442_route": prompt442_route,
        "prompt443_prompt442_change_safety_status": (
            prompt442_change_safety_status
        ),
        "prompt443_prompt442_changes_present": prompt442_changes_present,
        "prompt443_prompt442_diff_empty": prompt442_diff_empty,
        "prompt443_allowed_changed_files": allowed_changed_files,
        "prompt443_unexpected_changed_files": unexpected_changed_files,
        "prompt443_unexpected_untracked_files": unexpected_untracked_files,
        "prompt443_diff_summary_available": False,
        "prompt443_diff_summary_source": "",
        "prompt443_approve_commit_tag_candidate": False,
        "prompt443_commit_message_candidate": "",
        "prompt443_tag_name_candidate": "",
        "prompt443_review_required": True,
        "prompt443_commit_tag_allowed": False,
        "prompt443_git_mutation_allowed": False,
        "prompt443_remote_mutation_allowed": False,
        "prompt443_codex_invocation_allowed": False,
        "prompt443_blocked_reason": (
            "prompt443_missing_prompt442_route"
            if not prompt442_route
            else f"prompt443_unsupported_prompt442_route_{prompt442_route}"
        ),
        "prompt443_next_action": "prepare_targeted_fix_or_manual_review",
    }

    ready_candidate = (
        prompt442_route == "codex_success_with_allowed_changes"
        and prompt442_change_safety_status == "allowed_changes"
        and prompt442_changes_present is True
        and prompt442_diff_empty is False
        and unexpected_changed_files == []
        and unexpected_untracked_files == []
        and bool(allowed_changed_files)
    )
    if ready_candidate:
        state.update(
            {
                "prompt443_success_diff_handoff_status": "ready",
                "prompt443_diff_summary_available": True,
                "prompt443_diff_summary_source": (
                    "prompt442_allowed_changed_files"
                ),
                "prompt443_approve_commit_tag_candidate": True,
                "prompt443_commit_message_candidate": (
                    "Prompt443 approve Codex success diff candidate"
                ),
                "prompt443_tag_name_candidate": (
                    "prompt443-success-diff-approve-candidate"
                ),
                "prompt443_review_required": True,
                "prompt443_blocked_reason": "",
                "prompt443_next_action": (
                    "prepare_prompt444_or_prompt445_approve_commit_tag_gate"
                ),
            }
        )
    elif prompt442_route == "codex_success_no_changes":
        state.update(
            {
                "prompt443_success_diff_handoff_status": "not_applicable",
                "prompt443_approve_commit_tag_candidate": False,
                "prompt443_review_required": False,
                "prompt443_blocked_reason": (
                    "prompt443_no_success_diff_to_handoff"
                ),
                "prompt443_next_action": "review_codex_no_changes",
            }
        )
    elif prompt442_route == "codex_unsafe_changes_stop":
        state.update(
            {
                "prompt443_success_diff_handoff_status": "blocked",
                "prompt443_approve_commit_tag_candidate": False,
                "prompt443_review_required": True,
                "prompt443_blocked_reason": (
                    "prompt443_prompt442_unsafe_changes"
                ),
                "prompt443_next_action": (
                    "stop_for_prompt442_unexpected_changes"
                ),
            }
        )

    return state

def _build_prompt444_targeted_fix_reentry_packet_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    prompt442_route = _normalize_text(
        payload.get("prompt442_codex_post_execution_route"),
        default="",
    )
    prompt442_review_status = _normalize_text(
        payload.get("prompt442_review_status"),
        default="",
    )
    prompt442_change_safety_status = _normalize_text(
        payload.get("prompt442_post_codex_change_safety_status"),
        default="",
    )
    prompt443_status = _normalize_text(
        payload.get("prompt443_success_diff_handoff_status"),
        default="",
    )
    retry_count = _prompt444_retry_value(
        payload,
        "prompt444_retry_count",
        0,
    )
    retry_limit = _prompt444_retry_value(
        payload,
        "prompt444_retry_limit",
        1,
    )
    retry_allowed = retry_count < retry_limit
    planned_artifact_path = _prompt444_targeted_fix_prompt_artifact_path(payload)
    prompt441_result_materialized = (
        payload.get("prompt441_codex_result_materialized") is True
    )
    prompt442_result_available = (
        payload.get("prompt442_prompt441_result_available") is True
    )
    runtime_result_available = (
        prompt441_result_materialized or prompt442_result_available
    )

    state: dict[str, Any] = {
        "prompt444_schema_version": _PROMPT444_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt444",
        "prompt444_targeted_fix_reentry_status": "blocked",
        "prompt444_prompt442_route": prompt442_route,
        "prompt444_prompt442_review_status": prompt442_review_status,
        "prompt444_prompt442_change_safety_status": (
            prompt442_change_safety_status
        ),
        "prompt444_prompt442_changes_present": bool(
            payload.get("prompt442_post_codex_changes_present", False)
        ),
        "prompt444_prompt442_diff_empty": bool(
            payload.get("prompt442_post_codex_diff_empty", False)
        ),
        "prompt444_prompt443_status": prompt443_status,
        "prompt444_prompt443_approve_commit_tag_candidate": bool(
            payload.get("prompt443_approve_commit_tag_candidate", False)
        ),
        "prompt444_failure_classification": "unsupported_or_missing_route",
        "prompt444_failure_reason": (
            f"unsupported_prompt442_route_{prompt442_route}"
            if prompt442_route
            else "missing_prompt442_route"
        ),
        "prompt444_prompt441_returncode": _as_optional_int(
            payload.get("prompt441_codex_returncode")
        ),
        "prompt444_prompt441_returncode_classification": _normalize_text(
            payload.get("prompt441_codex_returncode_classification"),
            default="unknown",
        ),
        "prompt444_runtime_result_available": runtime_result_available,
        "prompt444_stdout_summary_available": (
            _prompt444_summary_metadata_available(
                payload,
                (
                    "prompt441_codex_stdout_path",
                    "prompt430_runtime_execution_stdout_path",
                    "prompt431_runtime_execution_stdout_path",
                    "stdout_path",
                    "stdout_summary",
                    "stdout",
                ),
            )
        ),
        "prompt444_stderr_summary_available": (
            _prompt444_summary_metadata_available(
                payload,
                (
                    "prompt441_codex_stderr_path",
                    "prompt430_runtime_execution_stderr_path",
                    "prompt431_runtime_execution_stderr_path",
                    "stderr_path",
                    "stderr_summary",
                    "stderr",
                ),
            )
        ),
        "prompt444_retryable": False,
        "prompt444_retry_count": retry_count,
        "prompt444_retry_limit": retry_limit,
        "prompt444_retry_allowed": False,
        "prompt444_retry_count_increment_planned": False,
        "prompt444_retry_count_increment_allowed": False,
        "prompt444_targeted_fix_prompt_required": False,
        "prompt444_targeted_fix_prompt_artifact_planned": False,
        "prompt444_targeted_fix_prompt_artifact_path": "",
        "prompt444_targeted_fix_prompt_inputs_available": False,
        "prompt444_targeted_fix_reentry_candidate": False,
        "prompt444_targeted_fix_materialization_required": False,
        "prompt444_targeted_fix_reentry_execution_required": False,
        "prompt444_codex_reentry_allowed": False,
        "prompt444_git_mutation_allowed": False,
        "prompt444_remote_mutation_allowed": False,
        "prompt444_commit_tag_allowed": False,
        "prompt444_file_creation_allowed": False,
        "prompt444_blocked_reason": (
            f"prompt444_unsupported_prompt442_route_{prompt442_route}"
            if prompt442_route
            else "prompt444_missing_prompt442_route"
        ),
        "prompt444_next_action": "manual_review_prompt444_route",
    }

    if (
        state["prompt444_prompt443_approve_commit_tag_candidate"] is True
        and prompt443_status == "ready"
    ):
        state.update(
            {
                "prompt444_targeted_fix_reentry_status": "not_applicable",
                "prompt444_failure_classification": (
                    "success_candidate_available"
                ),
                "prompt444_failure_reason": "",
                "prompt444_blocked_reason": "",
                "prompt444_next_action": (
                    "prepare_prompt445_approve_commit_tag_execution_gate"
                ),
            }
        )
        return state

    targeted_fix_routes = {
        "codex_success_no_changes": (
            "success_no_changes",
            "prompt442_codex_success_no_changes",
        ),
        "codex_failed_with_changes": (
            "failed_with_changes",
            "prompt442_codex_failed_with_changes",
        ),
        "codex_failed_no_changes": (
            "failed_no_changes",
            "prompt442_codex_failed_no_changes",
        ),
    }
    if prompt442_route in targeted_fix_routes:
        failure_classification, failure_reason = targeted_fix_routes[prompt442_route]
        state.update(
            {
                "prompt444_targeted_fix_reentry_status": (
                    "ready" if retry_allowed else "blocked"
                ),
                "prompt444_failure_classification": failure_classification,
                "prompt444_failure_reason": failure_reason,
                "prompt444_retryable": True,
                "prompt444_retry_allowed": retry_allowed,
                "prompt444_retry_count_increment_planned": retry_allowed,
                "prompt444_targeted_fix_prompt_required": retry_allowed,
                "prompt444_targeted_fix_prompt_artifact_planned": retry_allowed,
                "prompt444_targeted_fix_prompt_artifact_path": (
                    planned_artifact_path if retry_allowed else ""
                ),
                "prompt444_targeted_fix_prompt_inputs_available": retry_allowed,
                "prompt444_targeted_fix_reentry_candidate": retry_allowed,
                "prompt444_targeted_fix_materialization_required": retry_allowed,
                "prompt444_targeted_fix_reentry_execution_required": retry_allowed,
                "prompt444_blocked_reason": (
                    "" if retry_allowed else "prompt444_retry_limit_reached"
                ),
                "prompt444_next_action": (
                    "prepare_prompt445_targeted_fix_prompt_materialization"
                    if retry_allowed
                    else "manual_review_retry_limit_reached"
                ),
            }
        )
        return state

    if prompt442_route == "codex_unsafe_changes_stop":
        state.update(
            {
                "prompt444_targeted_fix_reentry_status": "blocked",
                "prompt444_failure_classification": "unsafe_changes",
                "prompt444_failure_reason": "prompt442_unsafe_changes_stop",
                "prompt444_blocked_reason": (
                    "prompt444_unsafe_changes_require_manual_review"
                ),
                "prompt444_next_action": (
                    "stop_for_prompt442_unexpected_changes"
                ),
            }
        )
        return state

    if prompt442_route in {
        "",
        "codex_result_not_available",
        "codex_git_inspection_error_stop",
    }:
        observed_route = prompt442_route or "missing_prompt442_route"
        state.update(
            {
                "prompt444_failure_reason": observed_route,
                "prompt444_blocked_reason": (
                    f"prompt444_{observed_route}"
                ),
            }
        )
    return state

def _build_prompt445_targeted_fix_prompt_materialization_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    prompt444_status = _normalize_text(
        payload.get("prompt444_targeted_fix_reentry_status"),
        default="",
    )
    failure_classification = _normalize_text(
        payload.get("prompt444_failure_classification"),
        default="",
    )
    failure_reason = _normalize_text(
        payload.get("prompt444_failure_reason"),
        default="",
    )
    retry_count = _prompt444_retry_value(payload, "prompt444_retry_count", 0)
    retry_limit = _prompt444_retry_value(payload, "prompt444_retry_limit", 1)
    retry_allowed = payload.get("prompt444_retry_allowed") is True
    artifact_path = _normalize_text(
        payload.get("prompt444_targeted_fix_prompt_artifact_path"),
        default="",
    )
    prompt444_inputs_available = (
        payload.get("prompt444_targeted_fix_prompt_inputs_available") is True
    )
    next_retry_count = retry_count + 1

    state: dict[str, Any] = {
        "prompt445_schema_version": _PROMPT445_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt445",
        "prompt445_targeted_fix_materialization_status": "blocked",
        "prompt445_prompt444_status": prompt444_status,
        "prompt445_prompt444_failure_classification": failure_classification,
        "prompt445_prompt444_failure_reason": failure_reason,
        "prompt445_prompt444_retry_allowed": retry_allowed,
        "prompt445_prompt444_retry_count": retry_count,
        "prompt445_prompt444_retry_limit": retry_limit,
        "prompt445_prompt444_artifact_path": artifact_path,
        "prompt445_prompt444_inputs_available": prompt444_inputs_available,
        "prompt445_materialization_required": False,
        "prompt445_materialization_allowed": False,
        "prompt445_materialization_performed": False,
        "prompt445_targeted_fix_prompt_artifact_path": artifact_path,
        "prompt445_targeted_fix_prompt_artifact_planned": False,
        "prompt445_targeted_fix_prompt_artifact_materialized": False,
        "prompt445_targeted_fix_prompt_content_ready": False,
        "prompt445_targeted_fix_prompt_content_summary": (
            _prompt445_prompt_content_summary(
                failure_classification=failure_classification,
                failure_reason=failure_reason,
                retry_count=retry_count,
                retry_limit=retry_limit,
                next_action="manual_review_prompt445_route",
            )
        ),
        "prompt445_targeted_fix_prompt_inputs_summary": (
            _prompt445_prompt_inputs_summary(
                payload,
                prompt444_status=prompt444_status,
                failure_classification=failure_classification,
                failure_reason=failure_reason,
                retry_count=retry_count,
                retry_limit=retry_limit,
            )
        ),
        "prompt445_targeted_fix_prompt_instruction_profile": "",
        "prompt445_retry_count_increment_required": False,
        "prompt445_retry_count_increment_allowed": False,
        "prompt445_retry_count_increment_performed": False,
        "prompt445_next_retry_count": next_retry_count,
        "prompt445_codex_reentry_request_ready": False,
        "prompt445_codex_reentry_allowed": False,
        "prompt445_git_mutation_allowed": False,
        "prompt445_remote_mutation_allowed": False,
        "prompt445_commit_tag_allowed": False,
        "prompt445_file_creation_allowed": False,
        "prompt445_blocked_reason": (
            f"prompt445_unsupported_prompt444_state_{prompt444_status}"
            if prompt444_status
            else "prompt445_missing_prompt444_state"
        ),
        "prompt445_next_action": "manual_review_prompt445_route",
    }

    ready_materialization_request = (
        prompt444_status == "ready"
        and retry_allowed is True
        and payload.get("prompt444_targeted_fix_prompt_required") is True
        and payload.get("prompt444_targeted_fix_prompt_artifact_planned") is True
        and prompt444_inputs_available is True
        and payload.get("prompt444_targeted_fix_reentry_candidate") is True
        and payload.get("prompt444_targeted_fix_materialization_required") is True
    )
    if ready_materialization_request:
        next_action = "prepare_prompt446_targeted_fix_codex_reentry_execution"
        state.update(
            {
                "prompt445_targeted_fix_materialization_status": "ready",
                "prompt445_materialization_required": True,
                "prompt445_targeted_fix_prompt_artifact_planned": True,
                "prompt445_targeted_fix_prompt_content_ready": True,
                "prompt445_targeted_fix_prompt_content_summary": (
                    _prompt445_prompt_content_summary(
                        failure_classification=failure_classification,
                        failure_reason=failure_reason,
                        retry_count=retry_count,
                        retry_limit=retry_limit,
                        next_action=next_action,
                    )
                ),
                "prompt445_targeted_fix_prompt_instruction_profile": (
                    "bounded_targeted_fix_no_tests_no_git_mutation"
                ),
                "prompt445_retry_count_increment_required": True,
                "prompt445_next_retry_count": next_retry_count,
                "prompt445_codex_reentry_request_ready": True,
                "prompt445_blocked_reason": "",
                "prompt445_next_action": next_action,
            }
        )
        return state

    if (
        prompt444_status == "not_applicable"
        and failure_classification == "success_candidate_available"
    ):
        next_action = "prepare_prompt447_approve_commit_tag_execution_gate"
        state.update(
            {
                "prompt445_targeted_fix_materialization_status": (
                    "not_applicable"
                ),
                "prompt445_next_retry_count": retry_count,
                "prompt445_blocked_reason": "",
                "prompt445_next_action": next_action,
                "prompt445_targeted_fix_prompt_content_summary": (
                    _prompt445_prompt_content_summary(
                        failure_classification=failure_classification,
                        failure_reason=failure_reason,
                        retry_count=retry_count,
                        retry_limit=retry_limit,
                        next_action=next_action,
                    )
                ),
            }
        )
        return state

    if (
        prompt444_status == "blocked"
        and payload.get("prompt444_blocked_reason")
        == "prompt444_retry_limit_reached"
    ):
        next_action = "manual_review_retry_limit_reached"
        state.update(
            {
                "prompt445_targeted_fix_materialization_status": "blocked",
                "prompt445_next_retry_count": retry_count,
                "prompt445_blocked_reason": "prompt445_retry_limit_reached",
                "prompt445_next_action": next_action,
                "prompt445_targeted_fix_prompt_content_summary": (
                    _prompt445_prompt_content_summary(
                        failure_classification=failure_classification,
                        failure_reason=failure_reason,
                        retry_count=retry_count,
                        retry_limit=retry_limit,
                        next_action=next_action,
                    )
                ),
            }
        )
        return state

    if (
        failure_classification == "unsafe_changes"
        or payload.get("prompt444_next_action")
        == "stop_for_prompt442_unexpected_changes"
    ):
        next_action = "stop_for_prompt442_unexpected_changes"
        state.update(
            {
                "prompt445_targeted_fix_materialization_status": "blocked",
                "prompt445_next_retry_count": retry_count,
                "prompt445_blocked_reason": (
                    "prompt445_unsafe_changes_require_manual_review"
                ),
                "prompt445_next_action": next_action,
                "prompt445_targeted_fix_prompt_content_summary": (
                    _prompt445_prompt_content_summary(
                        failure_classification=failure_classification,
                        failure_reason=failure_reason,
                        retry_count=retry_count,
                        retry_limit=retry_limit,
                        next_action=next_action,
                    )
                ),
            }
        )
        return state

    return state

def _build_prompt446_targeted_fix_reentry_request_packet_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    prompt445_status = _normalize_text(
        payload.get("prompt445_targeted_fix_materialization_status"),
        default="",
    )
    prompt445_next_action = _normalize_text(
        payload.get("prompt445_next_action"),
        default="",
    )
    failure_classification = _normalize_text(
        payload.get("prompt445_prompt444_failure_classification"),
        default="",
    )
    failure_reason = _normalize_text(
        payload.get("prompt445_prompt444_failure_reason"),
        default="",
    )
    artifact_path = _normalize_text(
        payload.get("prompt445_targeted_fix_prompt_artifact_path"),
        default="",
    )
    content_ready = (
        payload.get("prompt445_targeted_fix_prompt_content_ready") is True
    )
    reentry_request_ready = (
        payload.get("prompt445_codex_reentry_request_ready") is True
    )
    current_retry_count = _prompt446_retry_value(
        payload,
        "prompt445_prompt444_retry_count",
        0,
    )
    prompt445_next_retry_count = _as_optional_int(
        payload.get("prompt445_next_retry_count")
    )
    next_retry_count = (
        prompt445_next_retry_count
        if prompt445_next_retry_count is not None
        and prompt445_next_retry_count >= 0
        else current_retry_count + 1
    )
    retry_limit = _prompt446_retry_value(
        payload,
        "prompt445_prompt444_retry_limit",
        1,
    )
    instruction_profile = _normalize_text(
        payload.get("prompt445_targeted_fix_prompt_instruction_profile"),
        default="",
    )
    if not instruction_profile:
        instruction_profile = "bounded_targeted_fix_no_tests_no_git_mutation"
    command_argv = ["codex", "exec", "-"]
    request_id = "prompt446-targeted-fix-reentry"

    state: dict[str, Any] = {
        "prompt446_schema_version": _PROMPT446_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt446",
        "prompt446_targeted_fix_request_packet_status": "blocked",
        "prompt446_prompt445_status": prompt445_status,
        "prompt446_prompt445_next_action": prompt445_next_action,
        "prompt446_prompt445_failure_classification": failure_classification,
        "prompt446_prompt445_failure_reason": failure_reason,
        "prompt446_prompt445_artifact_path": artifact_path,
        "prompt446_prompt445_content_ready": content_ready,
        "prompt446_prompt445_reentry_request_ready": reentry_request_ready,
        "prompt446_prompt445_next_retry_count": next_retry_count,
        "prompt446_materialization_request_required": False,
        "prompt446_materialization_request_ready": False,
        "prompt446_materialization_allowed": False,
        "prompt446_materialization_attempted": False,
        "prompt446_materialization_performed": False,
        "prompt446_targeted_fix_prompt_artifact_path": artifact_path,
        "prompt446_targeted_fix_prompt_artifact_path_available": bool(
            artifact_path
        ),
        "prompt446_targeted_fix_prompt_artifact_content_ready": False,
        "prompt446_targeted_fix_prompt_artifact_materialized": False,
        "prompt446_targeted_fix_prompt_instruction_profile": (
            instruction_profile
        ),
        "prompt446_targeted_fix_prompt_body_available": False,
        "prompt446_targeted_fix_prompt_body_summary": "",
        "prompt446_targeted_fix_prompt_body_preview": "",
        "prompt446_codex_reentry_request_required": False,
        "prompt446_codex_reentry_request_ready": False,
        "prompt446_codex_reentry_runtime_command_ready": False,
        "prompt446_codex_reentry_command_argv": [],
        "prompt446_codex_reentry_prompt_artifact_path": artifact_path,
        "prompt446_codex_reentry_request_id": "",
        "prompt446_codex_reentry_transport_mode": "",
        "prompt446_codex_reentry_runtime_command_json_ready": False,
        "prompt446_codex_reentry_runtime_command_request": {},
        "prompt446_request_codex_invocation": False,
        "prompt446_allow_codex_invocation": False,
        "prompt446_retry_count_increment_required": False,
        "prompt446_retry_count_increment_allowed": False,
        "prompt446_retry_count_increment_attempted": False,
        "prompt446_retry_count_increment_performed": False,
        "prompt446_current_retry_count": current_retry_count,
        "prompt446_next_retry_count": next_retry_count,
        "prompt446_retry_limit": retry_limit,
        "prompt446_file_creation_allowed": False,
        "prompt446_codex_reentry_allowed": False,
        "prompt446_codex_reentry_attempted": False,
        "prompt446_codex_reentry_performed": False,
        "prompt446_git_mutation_allowed": False,
        "prompt446_remote_mutation_allowed": False,
        "prompt446_commit_tag_allowed": False,
        "prompt446_blocked_reason": (
            f"prompt446_unsupported_prompt445_state_{prompt445_status}"
            if prompt445_status
            else "prompt446_missing_prompt445_state"
        ),
        "prompt446_next_action": "manual_review_prompt446_route",
    }

    ready_packet = (
        prompt445_status == "ready"
        and payload.get("prompt445_materialization_required") is True
        and content_ready is True
        and reentry_request_ready is True
        and prompt445_next_action
        == "prepare_prompt446_targeted_fix_codex_reentry_execution"
    )
    if ready_packet:
        prompt442_route = _normalize_text(
            payload.get("prompt444_prompt442_route")
            or payload.get("prompt442_codex_post_execution_route"),
            default="",
        )
        prompt442_safety_status = _normalize_text(
            payload.get("prompt444_prompt442_change_safety_status")
            or payload.get("prompt442_post_codex_change_safety_status"),
            default="",
        )
        state.update(
            {
                "prompt446_targeted_fix_request_packet_status": "ready",
                "prompt446_materialization_request_required": True,
                "prompt446_materialization_request_ready": True,
                "prompt446_targeted_fix_prompt_artifact_content_ready": True,
                "prompt446_targeted_fix_prompt_body_available": True,
                "prompt446_targeted_fix_prompt_body_summary": (
                    _prompt446_prompt_body_summary(
                        failure_classification=failure_classification,
                        failure_reason=failure_reason,
                        prompt442_route=prompt442_route,
                        prompt442_safety_status=prompt442_safety_status,
                        current_retry_count=current_retry_count,
                        next_retry_count=next_retry_count,
                        retry_limit=retry_limit,
                    )
                ),
                "prompt446_targeted_fix_prompt_body_preview": (
                    _prompt446_prompt_body_preview(
                        failure_classification=failure_classification,
                        failure_reason=failure_reason,
                        prompt442_route=prompt442_route,
                        prompt442_safety_status=prompt442_safety_status,
                        stdout_summary_available=bool(
                            payload.get("prompt444_stdout_summary_available")
                        ),
                        stderr_summary_available=bool(
                            payload.get("prompt444_stderr_summary_available")
                        ),
                        current_retry_count=current_retry_count,
                        next_retry_count=next_retry_count,
                        retry_limit=retry_limit,
                    )
                ),
                "prompt446_codex_reentry_request_required": True,
                "prompt446_codex_reentry_request_ready": True,
                "prompt446_codex_reentry_runtime_command_ready": True,
                "prompt446_codex_reentry_command_argv": command_argv,
                "prompt446_codex_reentry_request_id": request_id,
                "prompt446_codex_reentry_transport_mode": "live",
                "prompt446_codex_reentry_runtime_command_json_ready": True,
                "prompt446_codex_reentry_runtime_command_request": {
                    "command_argv": command_argv,
                    "request_id": request_id,
                    "codex_prompt_artifact_path": artifact_path,
                    "request_codex_invocation": True,
                    "allow_codex_invocation": False,
                    "transport_mode": "live",
                },
                "prompt446_request_codex_invocation": True,
                "prompt446_retry_count_increment_required": True,
                "prompt446_blocked_reason": "",
                "prompt446_next_action": (
                    "prepare_prompt447_targeted_fix_materialization_and_codex_reentry_gate"
                ),
            }
        )
        return state

    if (
        prompt445_status == "not_applicable"
        and prompt445_next_action
        == "prepare_prompt447_approve_commit_tag_execution_gate"
    ):
        state.update(
            {
                "prompt446_targeted_fix_request_packet_status": (
                    "not_applicable"
                ),
                "prompt446_blocked_reason": "",
                "prompt446_next_action": (
                    "prepare_prompt447_approve_commit_tag_execution_gate"
                ),
            }
        )
        return state

    if (
        prompt445_status == "blocked"
        and prompt445_next_action == "manual_review_retry_limit_reached"
    ):
        state.update(
            {
                "prompt446_targeted_fix_request_packet_status": "blocked",
                "prompt446_blocked_reason": "prompt446_retry_limit_reached",
                "prompt446_next_action": "manual_review_retry_limit_reached",
            }
        )
        return state

    if prompt445_next_action == "stop_for_prompt442_unexpected_changes":
        state.update(
            {
                "prompt446_targeted_fix_request_packet_status": "blocked",
                "prompt446_blocked_reason": (
                    "prompt446_unsafe_changes_require_manual_review"
                ),
                "prompt446_next_action": (
                    "stop_for_prompt442_unexpected_changes"
                ),
            }
        )
        return state

    state["prompt446_blocked_reason"] = (
        f"prompt446_unsupported_prompt445_state_{prompt445_status}_"
        f"next_action_{prompt445_next_action}"
        if prompt445_status or prompt445_next_action
        else "prompt446_missing_prompt445_state"
    )
    return state

def _build_prompt447_targeted_fix_execution_gate_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    prompt446_status = _normalize_text(
        payload.get("prompt446_targeted_fix_request_packet_status"),
        default="",
    )
    prompt446_next_action = _normalize_text(
        payload.get("prompt446_next_action"),
        default="",
    )
    artifact_path = _normalize_text(
        payload.get("prompt446_targeted_fix_prompt_artifact_path"),
        default="",
    )
    body_available = (
        payload.get("prompt446_targeted_fix_prompt_body_available") is True
    )
    body_preview_available = bool(
        _normalize_text(
            payload.get("prompt446_targeted_fix_prompt_body_preview"),
            default="",
        )
    )
    runtime_command_ready = (
        payload.get("prompt446_codex_reentry_runtime_command_ready") is True
    )
    runtime_command_json_ready = (
        payload.get("prompt446_codex_reentry_runtime_command_json_ready") is True
    )
    command_argv = _normalize_string_list(
        payload.get("prompt446_codex_reentry_command_argv")
    )
    request_id = _normalize_text(
        payload.get("prompt446_codex_reentry_request_id"),
        default="",
    )
    transport_mode = _normalize_text(
        payload.get("prompt446_codex_reentry_transport_mode"),
        default="",
    )
    current_retry_count = _prompt447_retry_value(
        payload,
        "prompt446_current_retry_count",
        0,
    )
    next_retry_count = _prompt447_retry_value(
        payload,
        "prompt446_next_retry_count",
        current_retry_count + 1,
    )
    retry_limit = _prompt447_retry_value(
        payload,
        "prompt446_retry_limit",
        1,
    )
    materialization_requested = _prompt447_any_explicit_flag(
        payload,
        (
            "request_prompt447_materialization",
            "allow_prompt447_materialization",
            "prompt447_materialization_allowed_input",
        ),
    )
    materialization_allowed = _prompt447_any_explicit_flag(
        payload,
        (
            "allow_prompt447_materialization",
            "prompt447_materialization_allowed_input",
        ),
    )
    codex_reentry_requested = _prompt447_any_explicit_flag(
        payload,
        (
            "request_prompt447_codex_reentry",
            "allow_prompt447_codex_reentry",
            "prompt447_codex_reentry_allowed_input",
        ),
    )
    codex_reentry_allowed = _prompt447_any_explicit_flag(
        payload,
        (
            "allow_prompt447_codex_reentry",
            "prompt447_codex_reentry_allowed_input",
        ),
    )
    retry_increment_requested = _prompt447_any_explicit_flag(
        payload,
        (
            "allow_prompt447_retry_increment",
            "prompt447_retry_increment_allowed_input",
        ),
    )
    retry_increment_allowed = _prompt447_any_explicit_flag(
        payload,
        (
            "allow_prompt447_retry_increment",
            "prompt447_retry_increment_allowed_input",
        ),
    )
    codex_prompt_artifact_path = _normalize_text(
        payload.get("prompt446_codex_reentry_prompt_artifact_path"),
        default=artifact_path,
    )
    runtime_command_json = _prompt447_runtime_command_json(
        command_argv=command_argv,
        request_id=request_id,
        artifact_path=codex_prompt_artifact_path or artifact_path,
        allow_codex_invocation=False,
        transport_mode=transport_mode,
    )
    state: dict[str, Any] = {
        "prompt447_schema_version": _PROMPT447_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt447",
        "prompt447_targeted_fix_execution_gate_status": "blocked",
        "prompt447_prompt446_status": prompt446_status,
        "prompt447_prompt446_next_action": prompt446_next_action,
        "prompt447_prompt446_artifact_path": artifact_path,
        "prompt447_prompt446_body_available": body_available,
        "prompt447_prompt446_body_preview_available": body_preview_available,
        "prompt447_prompt446_runtime_command_ready": runtime_command_ready,
        "prompt447_prompt446_runtime_command_json_ready": (
            runtime_command_json_ready
        ),
        "prompt447_prompt446_command_argv": command_argv,
        "prompt447_prompt446_request_id": request_id,
        "prompt447_prompt446_transport_mode": transport_mode,
        "prompt447_prompt446_current_retry_count": current_retry_count,
        "prompt447_prompt446_next_retry_count": next_retry_count,
        "prompt447_prompt446_retry_limit": retry_limit,
        "prompt447_materialization_requested": materialization_requested,
        "prompt447_materialization_explicitly_allowed": (
            materialization_allowed
        ),
        "prompt447_codex_reentry_requested": codex_reentry_requested,
        "prompt447_codex_reentry_explicitly_allowed": codex_reentry_allowed,
        "prompt447_retry_increment_requested": retry_increment_requested,
        "prompt447_retry_increment_explicitly_allowed": (
            retry_increment_allowed
        ),
        "prompt447_materialization_required": False,
        "prompt447_materialization_allowed": False,
        "prompt447_materialization_attempted": False,
        "prompt447_materialization_performed": False,
        "prompt447_materialization_blocked_reason": "",
        "prompt447_targeted_fix_prompt_artifact_path": artifact_path,
        "prompt447_targeted_fix_prompt_body_available": body_available,
        "prompt447_targeted_fix_prompt_body_preview_available": (
            body_preview_available
        ),
        "prompt447_targeted_fix_prompt_artifact_materialized": False,
        "prompt447_targeted_fix_prompt_artifact_materialization_result": (
            "not_performed"
        ),
        "prompt447_codex_reentry_required": False,
        "prompt447_codex_reentry_allowed": False,
        "prompt447_codex_reentry_attempted": False,
        "prompt447_codex_reentry_performed": False,
        "prompt447_codex_reentry_blocked_reason": "",
        "prompt447_codex_reentry_runtime_command_ready": runtime_command_ready,
        "prompt447_codex_reentry_runtime_command_json_ready": (
            runtime_command_json_ready
        ),
        "prompt447_codex_reentry_command_argv": command_argv,
        "prompt447_codex_reentry_prompt_artifact_path": (
            codex_prompt_artifact_path
        ),
        "prompt447_codex_reentry_request_id": request_id,
        "prompt447_codex_reentry_transport_mode": transport_mode,
        "prompt447_runtime_command_json": runtime_command_json,
        "prompt447_runtime_command_json_ready": runtime_command_json_ready,
        "prompt447_retry_count_increment_required": False,
        "prompt447_retry_count_increment_allowed": False,
        "prompt447_retry_count_increment_attempted": False,
        "prompt447_retry_count_increment_performed": False,
        "prompt447_current_retry_count": current_retry_count,
        "prompt447_next_retry_count": next_retry_count,
        "prompt447_retry_limit": retry_limit,
        "prompt447_git_mutation_allowed": False,
        "prompt447_remote_mutation_allowed": False,
        "prompt447_commit_tag_allowed": False,
        "prompt447_tests_allowed": False,
        "prompt447_blocked_reason": (
            f"prompt447_unsupported_prompt446_state_{prompt446_status}"
            if prompt446_status
            else "prompt447_missing_prompt446_state"
        ),
        "prompt447_next_action": "manual_review_prompt447_route",
    }

    ready_packet = (
        prompt446_status == "ready"
        and payload.get("prompt446_materialization_request_ready") is True
        and body_available is True
        and payload.get("prompt446_codex_reentry_request_ready") is True
        and runtime_command_ready is True
        and runtime_command_json_ready is True
        and prompt446_next_action
        == "prepare_prompt447_targeted_fix_materialization_and_codex_reentry_gate"
    )
    if ready_packet:
        state.update(
            {
                "prompt447_materialization_required": True,
                "prompt447_materialization_allowed": materialization_allowed,
                "prompt447_codex_reentry_required": True,
                "prompt447_codex_reentry_allowed": codex_reentry_allowed,
                "prompt447_retry_count_increment_required": True,
                "prompt447_retry_count_increment_allowed": (
                    retry_increment_allowed and codex_reentry_allowed
                ),
                "prompt447_runtime_command_json_ready": True,
                "prompt447_codex_reentry_runtime_command_json_ready": True,
            }
        )
        if not materialization_allowed:
            state.update(
                {
                    "prompt447_materialization_blocked_reason": (
                        "prompt447_materialization_not_explicitly_allowed"
                    ),
                    "prompt447_codex_reentry_blocked_reason": (
                        "prompt447_codex_reentry_not_explicitly_allowed"
                    ),
                    "prompt447_blocked_reason": (
                        "prompt447_execution_not_explicitly_allowed"
                    ),
                    "prompt447_next_action": (
                        "request_explicit_prompt447_execution_allow"
                    ),
                }
            )
            return state

        prompt_body = _prompt447_targeted_fix_prompt_body(
            failure_classification=_normalize_text(
                payload.get("prompt446_prompt445_failure_classification"),
                default="",
            ),
            failure_reason=_normalize_text(
                payload.get("prompt446_prompt445_failure_reason"),
                default="",
            ),
            prompt442_route=_normalize_text(
                payload.get("prompt444_prompt442_route")
                or payload.get("prompt442_codex_post_execution_route"),
                default="",
            ),
            prompt442_safety_status=_normalize_text(
                payload.get("prompt444_prompt442_change_safety_status")
                or payload.get("prompt442_post_codex_change_safety_status"),
                default="",
            ),
            current_retry_count=current_retry_count,
            next_retry_count=next_retry_count,
            retry_limit=retry_limit,
        )
        materialized, materialization_result = (
            _prompt447_materialize_prompt_artifact(
                artifact_path=artifact_path,
                prompt_body=prompt_body,
            )
        )
        state.update(
            {
                "prompt447_materialization_attempted": True,
                "prompt447_materialization_performed": materialized,
                "prompt447_targeted_fix_prompt_artifact_materialized": (
                    materialized
                ),
                "prompt447_targeted_fix_prompt_artifact_materialization_result": (
                    materialization_result
                ),
            }
        )
        if not materialized:
            state.update(
                {
                    "prompt447_targeted_fix_execution_gate_status": "blocked",
                    "prompt447_materialization_blocked_reason": (
                        materialization_result
                    ),
                    "prompt447_codex_reentry_allowed": False,
                    "prompt447_codex_reentry_blocked_reason": (
                        "prompt447_materialization_failed"
                    ),
                    "prompt447_blocked_reason": materialization_result,
                    "prompt447_next_action": "manual_review_prompt447_route",
                }
            )
            return state

        runtime_command_json = _prompt447_runtime_command_json(
            command_argv=command_argv,
            request_id=request_id,
            artifact_path=artifact_path,
            allow_codex_invocation=codex_reentry_allowed,
            transport_mode=transport_mode,
        )
        state.update(
            {
                "prompt447_runtime_command_json": runtime_command_json,
                "prompt447_codex_reentry_prompt_artifact_path": artifact_path,
            }
        )
        if not codex_reentry_allowed:
            state.update(
                {
                    "prompt447_targeted_fix_execution_gate_status": (
                        "materialized"
                    ),
                    "prompt447_codex_reentry_blocked_reason": (
                        "prompt447_codex_reentry_not_explicitly_allowed"
                    ),
                    "prompt447_blocked_reason": "",
                    "prompt447_next_action": (
                        "request_explicit_prompt447_codex_reentry_allow"
                    ),
                }
            )
            return state

        state.update(
            {
                "prompt447_targeted_fix_execution_gate_status": "prepared",
                "prompt447_codex_reentry_attempted": False,
                "prompt447_codex_reentry_performed": False,
                "prompt447_blocked_reason": "",
                "prompt447_next_action": (
                    "prepare_runtime_command_execution_from_prompt447_packet"
                ),
            }
        )
        return state

    if (
        prompt446_status == "not_applicable"
        and prompt446_next_action
        == "prepare_prompt447_approve_commit_tag_execution_gate"
    ):
        state.update(
            {
                "prompt447_targeted_fix_execution_gate_status": (
                    "not_applicable"
                ),
                "prompt447_materialization_required": False,
                "prompt447_codex_reentry_required": False,
                "prompt447_retry_count_increment_required": False,
                "prompt447_blocked_reason": "",
                "prompt447_next_action": (
                    "prepare_prompt448_approve_commit_tag_execution_gate"
                ),
            }
        )
        return state

    if (
        prompt446_status == "blocked"
        and (
            payload.get("prompt446_blocked_reason")
            == "prompt446_retry_limit_reached"
            or prompt446_next_action == "manual_review_retry_limit_reached"
        )
    ):
        state.update(
            {
                "prompt447_targeted_fix_execution_gate_status": "blocked",
                "prompt447_blocked_reason": "prompt447_retry_limit_reached",
                "prompt447_next_action": "manual_review_retry_limit_reached",
            }
        )
        return state

    if (
        prompt446_next_action == "stop_for_prompt442_unexpected_changes"
        or payload.get("prompt446_blocked_reason")
        == "prompt446_unsafe_changes_require_manual_review"
    ):
        state.update(
            {
                "prompt447_targeted_fix_execution_gate_status": "blocked",
                "prompt447_blocked_reason": (
                    "prompt447_unsafe_changes_require_manual_review"
                ),
                "prompt447_next_action": (
                    "stop_for_prompt442_unexpected_changes"
                ),
            }
        )
        return state

    state["prompt447_blocked_reason"] = (
        f"prompt447_unsupported_prompt446_state_{prompt446_status}_"
        f"next_action_{prompt446_next_action}"
        if prompt446_status or prompt446_next_action
        else "prompt447_missing_prompt446_state"
    )
    return state

def _build_prompt448_targeted_fix_execution_allow_candidate_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    prompt447_status = _normalize_text(
        payload.get("prompt447_targeted_fix_execution_gate_status"),
        default="",
    )
    prompt447_next_action = _normalize_text(
        payload.get("prompt447_next_action"),
        default="",
    )
    prompt447_blocked_reason = _normalize_text(
        payload.get("prompt447_blocked_reason"),
        default="",
    )
    artifact_path = _normalize_text(
        payload.get("prompt447_targeted_fix_prompt_artifact_path"),
        default="",
    )
    body_available = (
        payload.get("prompt447_targeted_fix_prompt_body_available") is True
    )
    command_argv = _normalize_string_list(
        payload.get("prompt447_codex_reentry_command_argv")
    )
    request_id = _normalize_text(
        payload.get("prompt447_codex_reentry_request_id"),
        default="",
    )
    transport_mode = _normalize_text(
        payload.get("prompt447_codex_reentry_transport_mode"),
        default="",
    )
    current_retry_count = _prompt448_retry_value(
        payload,
        "prompt447_current_retry_count",
        0,
    )
    next_retry_count = _prompt448_retry_value(
        payload,
        "prompt447_next_retry_count",
        current_retry_count + 1,
    )
    retry_limit = _prompt448_retry_value(
        payload,
        "prompt447_retry_limit",
        1,
    )
    prompt447_runtime_command_json = _prompt448_runtime_command_json(
        payload.get("prompt447_runtime_command_json")
    )
    runtime_command_json_ready = (
        payload.get("prompt447_runtime_command_json_ready") is True
    )
    materialization_required = (
        payload.get("prompt447_materialization_required") is True
    )
    codex_reentry_required = (
        payload.get("prompt447_codex_reentry_required") is True
    )
    retry_count_increment_required = (
        payload.get("prompt447_retry_count_increment_required") is True
    )
    prompt_artifact_path_available = bool(artifact_path)
    runtime_command_packet_available = (
        runtime_command_json_ready and bool(prompt447_runtime_command_json)
    )
    retry_budget_available = retry_limit >= 0 and current_retry_count >= 0
    retry_budget_not_exceeded = (
        retry_budget_available and current_retry_count < retry_limit
    )
    prompt447_invariants_safe = (
        payload.get("prompt447_git_mutation_allowed") is False
        and payload.get("prompt447_remote_mutation_allowed") is False
        and payload.get("prompt447_commit_tag_allowed") is False
        and payload.get("prompt447_tests_allowed") is False
    )
    prompt447_invariants_unsafe = (
        payload.get("prompt447_git_mutation_allowed") is True
        or payload.get("prompt447_remote_mutation_allowed") is True
        or payload.get("prompt447_commit_tag_allowed") is True
        or payload.get("prompt447_tests_allowed") is True
    )

    state: dict[str, Any] = {
        "prompt448_schema_version": _PROMPT448_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt448",
        "prompt448_targeted_fix_execution_allow_candidate_status": (
            "blocked"
        ),
        "prompt448_prompt447_status": prompt447_status,
        "prompt448_prompt447_next_action": prompt447_next_action,
        "prompt448_prompt447_blocked_reason": prompt447_blocked_reason,
        "prompt448_prompt447_materialization_required": (
            materialization_required
        ),
        "prompt448_prompt447_codex_reentry_required": codex_reentry_required,
        "prompt448_prompt447_retry_count_increment_required": (
            retry_count_increment_required
        ),
        "prompt448_prompt447_runtime_command_json_ready": (
            runtime_command_json_ready
        ),
        "prompt448_prompt447_runtime_command_json": (
            prompt447_runtime_command_json
        ),
        "prompt448_prompt447_artifact_path": artifact_path,
        "prompt448_prompt447_body_available": body_available,
        "prompt448_prompt447_command_argv": command_argv,
        "prompt448_prompt447_request_id": request_id,
        "prompt448_prompt447_transport_mode": transport_mode,
        "prompt448_prompt447_current_retry_count": current_retry_count,
        "prompt448_prompt447_next_retry_count": next_retry_count,
        "prompt448_prompt447_retry_limit": retry_limit,
        "prompt448_allow_candidate_inputs_available": False,
        "prompt448_allow_candidate_safety_status": (
            "unsupported_or_missing_prompt447_state"
        ),
        "prompt448_allow_candidate_blocked_reason": "",
        "prompt448_prompt_artifact_path_available": (
            prompt_artifact_path_available
        ),
        "prompt448_prompt_body_available": body_available,
        "prompt448_runtime_command_packet_available": (
            runtime_command_packet_available
        ),
        "prompt448_retry_budget_available": retry_budget_available,
        "prompt448_retry_budget_not_exceeded": retry_budget_not_exceeded,
        "prompt448_materialization_allow_candidate": False,
        "prompt448_codex_reentry_allow_candidate": False,
        "prompt448_retry_increment_allow_candidate": False,
        "prompt448_combined_execution_allow_candidate": False,
        "prompt448_materialization_allowed": False,
        "prompt448_materialization_attempted": False,
        "prompt448_materialization_performed": False,
        "prompt448_codex_reentry_allowed": False,
        "prompt448_codex_reentry_attempted": False,
        "prompt448_codex_reentry_performed": False,
        "prompt448_retry_count_increment_allowed": False,
        "prompt448_retry_count_increment_attempted": False,
        "prompt448_retry_count_increment_performed": False,
        "prompt448_runtime_command_json": prompt447_runtime_command_json,
        "prompt448_runtime_command_json_ready": False,
        "prompt448_runtime_command_json_allow_codex_invocation": False,
        "prompt448_runtime_command_json_request_codex_invocation": False,
        "prompt448_runtime_command_handoff_ready": False,
        "prompt448_runtime_command_handoff_next_action": "",
        "prompt448_reentry_result_review_required": False,
        "prompt448_reentry_result_route_to_prompt442_required": False,
        "prompt448_reentry_result_next_action": "",
        "prompt448_git_mutation_allowed": False,
        "prompt448_remote_mutation_allowed": False,
        "prompt448_commit_tag_allowed": False,
        "prompt448_tests_allowed": False,
        "prompt448_file_creation_allowed": False,
        "prompt448_blocked_reason": (
            f"prompt448_unsupported_prompt447_state_{prompt447_status}"
            if prompt447_status
            else "prompt448_missing_prompt447_state"
        ),
        "prompt448_next_action": "manual_review_prompt448_route",
    }

    if (
        prompt447_status == "not_applicable"
        and prompt447_next_action
        == "prepare_prompt448_approve_commit_tag_execution_gate"
    ):
        state.update(
            {
                "prompt448_targeted_fix_execution_allow_candidate_status": (
                    "not_applicable"
                ),
                "prompt448_allow_candidate_inputs_available": False,
                "prompt448_allow_candidate_safety_status": (
                    "success_candidate_available"
                ),
                "prompt448_allow_candidate_blocked_reason": "",
                "prompt448_blocked_reason": "",
                "prompt448_next_action": (
                    "prepare_prompt449_approve_commit_tag_execution_gate"
                ),
            }
        )
        return state

    if (
        prompt447_next_action == "stop_for_prompt442_unexpected_changes"
        or prompt447_blocked_reason
        == "prompt447_unsafe_changes_require_manual_review"
        or prompt447_invariants_unsafe
    ):
        return _prompt448_mark_blocked_no_candidates(
            state,
            safety_status="unsafe_changes",
            blocked_reason="prompt448_unsafe_changes_require_manual_review",
            next_action="stop_for_prompt442_unexpected_changes",
        )

    expected_blocked_gate = (
        prompt447_status == "blocked"
        and prompt447_blocked_reason
        == "prompt447_execution_not_explicitly_allowed"
        and prompt447_next_action
        == "request_explicit_prompt447_execution_allow"
        and materialization_required
        and codex_reentry_required
        and retry_count_increment_required
        and prompt447_invariants_safe
    )
    if expected_blocked_gate:
        state["prompt448_allow_candidate_inputs_available"] = True
        if not prompt_artifact_path_available:
            return _prompt448_mark_blocked_no_candidates(
                state,
                safety_status="missing_targeted_fix_prompt_artifact_path",
                blocked_reason=(
                    "prompt448_missing_targeted_fix_prompt_artifact_path"
                ),
                next_action=(
                    "manual_review_prompt448_missing_artifact_path"
                ),
            )
        if not body_available:
            return _prompt448_mark_blocked_no_candidates(
                state,
                safety_status="unsupported_or_missing_prompt447_state",
                blocked_reason=(
                    "prompt448_missing_targeted_fix_prompt_body"
                ),
                next_action="manual_review_prompt448_route",
            )
        if not runtime_command_packet_available:
            return _prompt448_mark_blocked_no_candidates(
                state,
                safety_status="missing_runtime_command_packet",
                blocked_reason="prompt448_missing_runtime_command_packet",
                next_action=(
                    "manual_review_prompt448_runtime_command_packet"
                ),
            )
        if not retry_budget_not_exceeded:
            return _prompt448_mark_blocked_no_candidates(
                state,
                safety_status="retry_limit_reached",
                blocked_reason="prompt448_retry_limit_reached",
                next_action="manual_review_retry_limit_reached",
            )

        runtime_command_json = dict(prompt447_runtime_command_json)
        runtime_command_json["request_codex_invocation"] = True
        runtime_command_json["allow_codex_invocation"] = False
        state.update(
            {
                "prompt448_targeted_fix_execution_allow_candidate_status": (
                    "ready"
                ),
                "prompt448_allow_candidate_inputs_available": True,
                "prompt448_allow_candidate_safety_status": (
                    "safe_to_prepare_execution_allow_candidate"
                ),
                "prompt448_allow_candidate_blocked_reason": "",
                "prompt448_prompt_artifact_path_available": True,
                "prompt448_prompt_body_available": True,
                "prompt448_runtime_command_packet_available": True,
                "prompt448_retry_budget_available": True,
                "prompt448_retry_budget_not_exceeded": True,
                "prompt448_materialization_allow_candidate": True,
                "prompt448_codex_reentry_allow_candidate": True,
                "prompt448_retry_increment_allow_candidate": True,
                "prompt448_combined_execution_allow_candidate": True,
                "prompt448_runtime_command_json": runtime_command_json,
                "prompt448_runtime_command_json_ready": True,
                "prompt448_runtime_command_json_allow_codex_invocation": (
                    False
                ),
                "prompt448_runtime_command_json_request_codex_invocation": (
                    True
                ),
                "prompt448_runtime_command_handoff_ready": True,
                "prompt448_runtime_command_handoff_next_action": (
                    "prepare_prompt449_explicit_targeted_fix_execution"
                ),
                "prompt448_blocked_reason": "",
                "prompt448_next_action": (
                    "prepare_prompt449_explicit_targeted_fix_execution"
                ),
            }
        )
        return state

    state["prompt448_blocked_reason"] = (
        f"prompt448_unsupported_prompt447_state_{prompt447_status}_"
        f"next_action_{prompt447_next_action}"
        if prompt447_status or prompt447_next_action
        else "prompt448_missing_prompt447_state"
    )
    state["prompt448_allow_candidate_blocked_reason"] = state[
        "prompt448_blocked_reason"
    ]
    return state

def _build_prompt449_explicit_targeted_fix_execution_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    prompt448_status = _normalize_text(
        payload.get("prompt448_targeted_fix_execution_allow_candidate_status"),
        default="",
    )
    prompt448_next_action = _normalize_text(
        payload.get("prompt448_next_action"),
        default="",
    )
    prompt448_safety_status = _normalize_text(
        payload.get("prompt448_allow_candidate_safety_status"),
        default="",
    )
    prompt448_runtime_command_json = (
        dict(payload.get("prompt448_runtime_command_json"))
        if isinstance(payload.get("prompt448_runtime_command_json"), Mapping)
        else {}
    )
    artifact_path = _normalize_text(
        payload.get("prompt448_prompt447_artifact_path")
        or prompt448_runtime_command_json.get("codex_prompt_artifact_path"),
        default="",
    )
    artifact_path_available = (
        payload.get("prompt448_prompt_artifact_path_available") is True
    )
    prompt_body_available = (
        payload.get("prompt448_prompt_body_available") is True
    )
    runtime_command_handoff_ready = (
        payload.get("prompt448_runtime_command_handoff_ready") is True
    )
    runtime_command_json_ready = (
        payload.get("prompt448_runtime_command_json_ready") is True
    )
    current_retry_count = _prompt449_retry_value(
        payload,
        "prompt448_prompt447_current_retry_count",
        0,
    )
    next_retry_count = _prompt449_retry_value(
        payload,
        "prompt448_prompt447_next_retry_count",
        current_retry_count + 1,
    )
    retry_limit = _prompt449_retry_value(
        payload,
        "prompt448_prompt447_retry_limit",
        1,
    )
    runtime_command_json = _prompt449_runtime_command_json(
        artifact_path=artifact_path,
    )
    state: dict[str, Any] = {
        "prompt449_schema_version": _PROMPT449_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt449",
        "prompt449_explicit_targeted_fix_execution_status": "blocked",
        "prompt449_prompt448_status": prompt448_status,
        "prompt449_prompt448_next_action": prompt448_next_action,
        "prompt449_prompt448_safety_status": prompt448_safety_status,
        "prompt449_prompt448_artifact_path_available": (
            artifact_path_available
        ),
        "prompt449_prompt448_prompt_body_available": prompt_body_available,
        "prompt449_prompt448_runtime_command_handoff_ready": (
            runtime_command_handoff_ready
        ),
        "prompt449_prompt448_runtime_command_json_ready": (
            runtime_command_json_ready
        ),
        "prompt449_prompt448_runtime_command_json": (
            prompt448_runtime_command_json
        ),
        "prompt449_prompt448_materialization_allow_candidate": (
            payload.get("prompt448_materialization_allow_candidate") is True
        ),
        "prompt449_prompt448_codex_reentry_allow_candidate": (
            payload.get("prompt448_codex_reentry_allow_candidate") is True
        ),
        "prompt449_prompt448_retry_increment_allow_candidate": (
            payload.get("prompt448_retry_increment_allow_candidate") is True
        ),
        "prompt449_prompt448_combined_execution_allow_candidate": (
            payload.get("prompt448_combined_execution_allow_candidate") is True
        ),
        "prompt449_materialization_required": False,
        "prompt449_materialization_allowed": False,
        "prompt449_materialization_attempted": False,
        "prompt449_materialization_performed": False,
        "prompt449_materialization_blocked_reason": "",
        "prompt449_targeted_fix_prompt_artifact_path": artifact_path,
        "prompt449_targeted_fix_prompt_body_available": False,
        "prompt449_targeted_fix_prompt_artifact_materialized": False,
        "prompt449_targeted_fix_prompt_artifact_materialization_result": (
            "not_performed"
        ),
        "prompt449_codex_reentry_required": False,
        "prompt449_codex_reentry_allowed": False,
        "prompt449_codex_reentry_attempted": False,
        "prompt449_codex_reentry_performed": False,
        "prompt449_codex_reentry_blocked_reason": "",
        "prompt449_codex_reentry_runtime_command_ready": False,
        "prompt449_codex_reentry_runtime_command_json_ready": False,
        "prompt449_codex_reentry_command_argv": [],
        "prompt449_codex_reentry_prompt_artifact_path": artifact_path,
        "prompt449_codex_reentry_request_id": "",
        "prompt449_codex_reentry_transport_mode": "",
        "prompt449_runtime_command_json": {},
        "prompt449_runtime_command_json_ready": False,
        "prompt449_runtime_command_json_allow_codex_invocation": False,
        "prompt449_runtime_command_json_request_codex_invocation": False,
        "prompt449_retry_count_increment_required": False,
        "prompt449_retry_count_increment_allowed": False,
        "prompt449_retry_count_increment_attempted": False,
        "prompt449_retry_count_increment_performed": False,
        "prompt449_current_retry_count": current_retry_count,
        "prompt449_next_retry_count": next_retry_count,
        "prompt449_retry_limit": retry_limit,
        "prompt449_reentry_result_available": False,
        "prompt449_reentry_result_review_required": False,
        "prompt449_reentry_result_route_to_prompt442_required": False,
        "prompt449_reentry_result_review_packet_ready": False,
        "prompt449_reentry_prompt442_review_handoff_ready": False,
        "prompt449_reentry_prompt442_review_handoff_source": "",
        "prompt449_reentry_review_next_action": "",
        "prompt449_git_mutation_allowed": False,
        "prompt449_remote_mutation_allowed": False,
        "prompt449_commit_tag_allowed": False,
        "prompt449_tests_allowed": False,
        "prompt449_file_creation_allowed": False,
        "prompt449_blocked_reason": (
            f"prompt449_unsupported_prompt448_state_{prompt448_status}"
            if prompt448_status
            else "prompt449_missing_prompt448_state"
        ),
        "prompt449_next_action": "manual_review_prompt449_route",
    }

    if (
        prompt448_status == "not_applicable"
        and prompt448_next_action
        == "prepare_prompt449_approve_commit_tag_execution_gate"
    ):
        state.update(
            {
                "prompt449_explicit_targeted_fix_execution_status": (
                    "not_applicable"
                ),
                "prompt449_blocked_reason": "",
                "prompt449_next_action": (
                    "prepare_prompt450_approve_commit_tag_execution_gate"
                ),
            }
        )
        return state

    if (
        prompt448_next_action == "stop_for_prompt442_unexpected_changes"
        or payload.get("prompt448_blocked_reason")
        == "prompt448_unsafe_changes_require_manual_review"
        or payload.get("prompt448_git_mutation_allowed") is True
        or payload.get("prompt448_remote_mutation_allowed") is True
        or payload.get("prompt448_commit_tag_allowed") is True
        or payload.get("prompt448_tests_allowed") is True
        or payload.get("prompt448_file_creation_allowed") is True
    ):
        return _prompt449_mark_blocked(
            state,
            blocked_reason="prompt449_unsafe_changes_require_manual_review",
            next_action="stop_for_prompt442_unexpected_changes",
        )

    if (
        payload.get("prompt448_blocked_reason")
        == "prompt448_retry_limit_reached"
        or prompt448_next_action == "manual_review_retry_limit_reached"
        or payload.get("prompt448_retry_budget_not_exceeded") is False
    ):
        return _prompt449_mark_blocked(
            state,
            blocked_reason="prompt449_retry_limit_reached",
            next_action="manual_review_retry_limit_reached",
        )

    ready_execution_path = (
        prompt448_status == "ready"
        and prompt448_next_action
        == "prepare_prompt449_explicit_targeted_fix_execution"
        and payload.get("prompt448_materialization_allow_candidate") is True
        and payload.get("prompt448_codex_reentry_allow_candidate") is True
        and payload.get("prompt448_retry_increment_allow_candidate") is True
        and payload.get("prompt448_combined_execution_allow_candidate") is True
        and runtime_command_handoff_ready
        and runtime_command_json_ready
        and payload.get("prompt448_runtime_command_json_request_codex_invocation")
        is True
        and payload.get("prompt448_runtime_command_json_allow_codex_invocation")
        is False
        and artifact_path_available
        and prompt_body_available
        and payload.get("prompt448_retry_budget_not_exceeded") is True
        and payload.get("prompt448_git_mutation_allowed") is False
        and payload.get("prompt448_remote_mutation_allowed") is False
        and payload.get("prompt448_commit_tag_allowed") is False
        and payload.get("prompt448_tests_allowed") is False
        and payload.get("prompt448_file_creation_allowed") is False
    )
    if not ready_execution_path:
        if prompt448_status == "ready" and not artifact_path_available:
            return _prompt449_mark_blocked(
                state,
                blocked_reason=(
                    "prompt449_missing_targeted_fix_prompt_artifact_path"
                ),
                next_action="manual_review_prompt449_missing_artifact_path",
            )
        if prompt448_status == "ready" and not runtime_command_json_ready:
            return _prompt449_mark_blocked(
                state,
                blocked_reason="prompt449_missing_runtime_command_packet",
                next_action="manual_review_prompt449_runtime_command_packet",
            )
        state["prompt449_blocked_reason"] = (
            f"prompt449_unsupported_prompt448_state_{prompt448_status}_"
            f"next_action_{prompt448_next_action}"
            if prompt448_status or prompt448_next_action
            else "prompt449_missing_prompt448_state"
        )
        return state

    if not artifact_path:
        return _prompt449_mark_blocked(
            state,
            blocked_reason="prompt449_missing_targeted_fix_prompt_artifact_path",
            next_action="manual_review_prompt449_missing_artifact_path",
        )
    if not prompt448_runtime_command_json:
        return _prompt449_mark_blocked(
            state,
            blocked_reason="prompt449_missing_runtime_command_packet",
            next_action="manual_review_prompt449_runtime_command_packet",
        )

    prompt_body = _prompt449_targeted_fix_prompt_body(
        failure_classification=_normalize_text(
            payload.get("prompt444_failure_classification")
            or payload.get("prompt446_prompt445_failure_classification"),
            default="",
        ),
        failure_reason=_normalize_text(
            payload.get("prompt444_failure_reason")
            or payload.get("prompt446_prompt445_failure_reason"),
            default="",
        ),
        prompt442_route=_normalize_text(
            payload.get("prompt444_prompt442_route")
            or payload.get("prompt442_codex_post_execution_route"),
            default="",
        ),
        prompt442_safety_status=_normalize_text(
            payload.get("prompt444_prompt442_change_safety_status")
            or payload.get("prompt442_post_codex_change_safety_status"),
            default="",
        ),
        current_retry_count=current_retry_count,
        next_retry_count=next_retry_count,
        retry_limit=retry_limit,
    )
    materialized, materialization_result = (
        _prompt449_materialize_prompt_artifact(
            artifact_path=artifact_path,
            prompt_body=prompt_body,
        )
    )
    state.update(
        {
            "prompt449_explicit_targeted_fix_execution_status": (
                "ready" if materialized else "blocked"
            ),
            "prompt449_materialization_required": True,
            "prompt449_materialization_allowed": True,
            "prompt449_materialization_attempted": True,
            "prompt449_materialization_performed": materialized,
            "prompt449_materialization_blocked_reason": (
                "" if materialized else materialization_result
            ),
            "prompt449_targeted_fix_prompt_body_available": True,
            "prompt449_targeted_fix_prompt_artifact_materialized": (
                materialized
            ),
            "prompt449_targeted_fix_prompt_artifact_materialization_result": (
                materialization_result
            ),
            "prompt449_file_creation_allowed": True,
        }
    )
    if not materialized:
        state.update(
            {
                "prompt449_blocked_reason": materialization_result,
                "prompt449_next_action": "manual_review_prompt449_route",
            }
        )
        return state

    state.update(
        {
            "prompt449_explicit_targeted_fix_execution_status": "prepared",
            "prompt449_codex_reentry_required": True,
            "prompt449_codex_reentry_allowed": True,
            "prompt449_codex_reentry_attempted": False,
            "prompt449_codex_reentry_performed": False,
            "prompt449_codex_reentry_runtime_command_ready": True,
            "prompt449_codex_reentry_runtime_command_json_ready": True,
            "prompt449_codex_reentry_command_argv": ["codex", "exec", "-"],
            "prompt449_codex_reentry_prompt_artifact_path": artifact_path,
            "prompt449_codex_reentry_request_id": (
                "prompt449-targeted-fix-reentry"
            ),
            "prompt449_codex_reentry_transport_mode": "live",
            "prompt449_runtime_command_json": runtime_command_json,
            "prompt449_runtime_command_json_ready": True,
            "prompt449_runtime_command_json_allow_codex_invocation": True,
            "prompt449_runtime_command_json_request_codex_invocation": True,
            "prompt449_retry_count_increment_required": True,
            "prompt449_retry_count_increment_allowed": True,
            "prompt449_retry_count_increment_attempted": False,
            "prompt449_retry_count_increment_performed": False,
            "prompt449_blocked_reason": "",
            "prompt449_next_action": "execute_prompt449_runtime_command_packet",
        }
    )
    return state

def _build_prompt430_bounded_runtime_execution_adapter_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
    execution_requested: bool = False,
    allow_runtime_execution: bool = False,
    command_runner: Callable[..., Any] | None = None,
    runtime_command_request: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = (
        run_state_payload if isinstance(run_state_payload, Mapping) else {}
    )
    injected_runtime_command_request = (
        dict(runtime_command_request)
        if isinstance(runtime_command_request, Mapping)
        else {}
    )
    launch_packet = payload.get("prompt429_runtime_launch_packet")
    launch_packet_copy = dict(launch_packet) if isinstance(launch_packet, Mapping) else {}
    if injected_runtime_command_request:
        launch_packet_copy = {
            **launch_packet_copy,
            "command_argv": list(
                injected_runtime_command_request.get("command_argv", [])
            ),
            "cwd": injected_runtime_command_request.get("cwd"),
            "env": dict(injected_runtime_command_request.get("env", {}))
            if isinstance(injected_runtime_command_request.get("env"), Mapping)
            else {},
            "timeout_seconds": injected_runtime_command_request.get(
                "timeout_seconds"
            ),
            "runtime_command_request": dict(injected_runtime_command_request),
            "runtime_command_request_source": "prompt437",
            "launch_execution_policy": "external_only",
            "launch_execution_performed": False,
        }
    command_argv = launch_packet_copy.get("command_argv")
    command_argv_ready = isinstance(command_argv, list) and len(command_argv) > 0
    copied_command_argv = list(command_argv) if isinstance(command_argv, list) else []
    injected_launch_packet_ready = bool(
        injected_runtime_command_request and command_argv_ready
    )
    prompt429_launch_packet_ready = (
        injected_launch_packet_ready
        or (
            payload.get("prompt429_bounded_runtime_launch_readiness_gate_ready")
            is True
            and payload.get("prompt429_bounded_runtime_launch_readiness_gate_status")
            == "launch_packet_ready"
            and payload.get("prompt429_launch_packet_ready") is True
            and payload.get("prompt429_launch_allowed") is True
            and payload.get("prompt429_launch_performed") is False
            and isinstance(launch_packet, Mapping)
            and launch_packet.get("launch_execution_policy") == "external_only"
            and launch_packet.get("launch_execution_performed") is False
        )
    )
    command_runner_ready = callable(command_runner)

    state: dict[str, Any] = {
        "prompt430_bounded_runtime_execution_adapter_enabled": True,
        "prompt430_schema_version": _PROMPT430_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt430",
        "prompt430_bounded_runtime_execution_adapter_ready": False,
        "prompt430_bounded_runtime_execution_adapter_status": "blocked",
        "prompt430_bounded_runtime_execution_adapter_blocked_reason": "",
        "prompt430_execution_requested": bool(execution_requested),
        "prompt430_allow_runtime_execution": bool(allow_runtime_execution),
        "prompt430_prompt429_launch_packet_ready": prompt429_launch_packet_ready,
        "prompt430_runtime_command_argv_ready": command_argv_ready,
        "prompt430_command_runner_ready": command_runner_ready,
        "prompt430_execution_ready": False,
        "prompt430_execution_attempted": False,
        "prompt430_execution_performed": False,
        "prompt430_execution_result_available": False,
        "prompt430_runtime_command_argv": copied_command_argv,
        "prompt430_runtime_launch_packet": launch_packet_copy,
        "prompt430_runtime_execution_returncode": None,
        "prompt430_runtime_execution_returncode_classification": "unknown",
        "prompt430_runtime_execution_stdout": None,
        "prompt430_runtime_execution_stderr": None,
        "prompt430_runtime_execution_stdout_path": None,
        "prompt430_runtime_execution_stderr_path": None,
        "prompt430_runtime_execution_receipt_path": None,
        "prompt430_runtime_execution_result_payload": {},
        "prompt430_runtime_execution_success": False,
        "prompt430_runtime_execution_failed": False,
        "prompt430_runtime_execution_unknown": False,
        "prompt430_execution_error": False,
        "prompt430_execution_error_message": "",
        "prompt430_success_path_ready": False,
        "prompt430_failure_review_required": False,
        "prompt430_next_cycle_continuation_candidate": False,
        "prompt430_targeted_fix_candidate": False,
        "prompt430_commit_tag_candidate": False,
        "prompt430_commit_tag_performed": False,
        "prompt430_codex_direct_invocation_allowed": False,
        "prompt430_subprocess_direct_execution_allowed": False,
        "prompt430_git_mutation_allowed": False,
        "prompt430_commit_tag_allowed": False,
        "prompt430_push_allowed": False,
        "prompt430_pr_allowed": False,
        "prompt430_merge_allowed": False,
        "prompt430_rollback_allowed": False,
        "prompt430_unbounded_loop_allowed": False,
        "prompt430_daemon_mode_allowed": False,
        "prompt430_next_action": "",
    }

    if not execution_requested:
        state.update(
            {
                "prompt430_bounded_runtime_execution_adapter_ready": True,
                "prompt430_bounded_runtime_execution_adapter_status": "ready",
                "prompt430_next_action": (
                    "request_prompt430_runtime_execution"
                ),
            }
        )
        return state

    if not allow_runtime_execution:
        state.update(
            {
                "prompt430_bounded_runtime_execution_adapter_status": "blocked",
                "prompt430_bounded_runtime_execution_adapter_blocked_reason": (
                    "runtime_execution_not_allowed"
                ),
                "prompt430_next_action": (
                    "allow_prompt430_runtime_execution"
                ),
            }
        )
        return state

    if not prompt429_launch_packet_ready:
        state.update(
            {
                "prompt430_bounded_runtime_execution_adapter_status": "blocked",
                "prompt430_bounded_runtime_execution_adapter_blocked_reason": (
                    "prompt429_launch_packet_not_ready"
                ),
                "prompt430_next_action": (
                    "review_prompt429_runtime_launch_packet"
                ),
            }
        )
        return state

    if not command_argv_ready:
        state.update(
            {
                "prompt430_bounded_runtime_execution_adapter_status": "blocked",
                "prompt430_bounded_runtime_execution_adapter_blocked_reason": (
                    "runtime_command_argv_not_ready"
                ),
                "prompt430_next_action": (
                    "fix_prompt429_runtime_command_argv"
                ),
            }
        )
        return state

    if not command_runner_ready:
        state.update(
            {
                "prompt430_bounded_runtime_execution_adapter_status": "blocked",
                "prompt430_bounded_runtime_execution_adapter_blocked_reason": (
                    "command_runner_missing"
                ),
                "prompt430_next_action": "provide_prompt430_command_runner",
            }
        )
        return state

    state["prompt430_execution_ready"] = True
    state["prompt430_execution_attempted"] = True
    try:
        result = command_runner(
            command_argv=list(copied_command_argv),
            launch_packet=dict(launch_packet_copy),
            run_state_payload=run_state_payload,
        )
    except Exception as exc:  # pragma: no cover - caller injected boundary.
        state.update(
            {
                "prompt430_bounded_runtime_execution_adapter_ready": False,
                "prompt430_bounded_runtime_execution_adapter_status": (
                    "execution_error"
                ),
                "prompt430_execution_performed": False,
                "prompt430_execution_result_available": False,
                "prompt430_execution_error": True,
                "prompt430_execution_error_message": str(exc),
                "prompt430_runtime_execution_returncode": None,
                "prompt430_runtime_execution_returncode_classification": (
                    "execution_error"
                ),
                "prompt430_failure_review_required": True,
                "prompt430_next_action": (
                    "review_prompt430_runtime_execution_error"
                ),
            }
        )
        return state

    if not isinstance(result, Mapping):
        state.update(
            {
                "prompt430_bounded_runtime_execution_adapter_ready": False,
                "prompt430_bounded_runtime_execution_adapter_status": (
                    "execution_error"
                ),
                "prompt430_execution_performed": False,
                "prompt430_execution_result_available": False,
                "prompt430_execution_error": True,
                "prompt430_execution_error_message": (
                    "command_runner_result_not_mapping"
                ),
                "prompt430_runtime_execution_returncode": None,
                "prompt430_runtime_execution_returncode_classification": (
                    "execution_error"
                ),
                "prompt430_failure_review_required": True,
                "prompt430_next_action": (
                    "review_prompt430_runtime_execution_error"
                ),
            }
        )
        return state

    result_payload = dict(result)
    returncode = result_payload.get("returncode")
    if returncode == 0:
        returncode_classification = "success"
    elif returncode is None:
        returncode_classification = _normalize_text(
            result_payload.get("returncode_classification"),
            default="unknown",
        )
        if returncode_classification == "timeout":
            returncode_classification = "failed"
    else:
        returncode_classification = "failed"
    execution_success = returncode == 0
    execution_failed = (
        (returncode is not None and returncode != 0)
        or returncode_classification == "failed"
    )
    execution_unknown = returncode is None and not execution_failed

    state.update(
        {
            "prompt430_bounded_runtime_execution_adapter_ready": True,
            "prompt430_bounded_runtime_execution_adapter_status": "executed",
            "prompt430_execution_performed": True,
            "prompt430_execution_result_available": True,
            "prompt430_runtime_execution_returncode": returncode,
            "prompt430_runtime_execution_returncode_classification": (
                returncode_classification
            ),
            "prompt430_runtime_execution_stdout": result_payload.get("stdout"),
            "prompt430_runtime_execution_stderr": result_payload.get("stderr"),
            "prompt430_runtime_execution_stdout_path": (
                result_payload.get("stdout_path")
            ),
            "prompt430_runtime_execution_stderr_path": (
                result_payload.get("stderr_path")
            ),
            "prompt430_runtime_execution_receipt_path": (
                result_payload.get("receipt_path")
            ),
            "prompt430_runtime_execution_result_payload": result_payload,
            "prompt430_runtime_execution_success": execution_success,
            "prompt430_runtime_execution_failed": execution_failed,
            "prompt430_runtime_execution_unknown": execution_unknown,
            "prompt430_success_path_ready": execution_success,
            "prompt430_failure_review_required": (
                execution_unknown or execution_failed
            ),
            "prompt430_next_cycle_continuation_candidate": execution_success,
            "prompt430_targeted_fix_candidate": execution_failed,
            "prompt430_next_action": (
                "review_prompt430_runtime_execution_result"
            ),
        }
    )
    return state

def _build_prompt438_runtime_result_classification_wiring_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    adapter_status = _normalize_text(
        payload.get("prompt430_bounded_runtime_execution_adapter_status"),
        default="",
    )
    result_payload_candidate = payload.get(
        "prompt430_runtime_execution_result_payload"
    )
    if not isinstance(result_payload_candidate, Mapping):
        result_payload_candidate = payload.get("prompt430_result_payload")
    result_payload = (
        dict(result_payload_candidate)
        if isinstance(result_payload_candidate, Mapping)
        else {}
    )
    result_available = (
        payload.get("prompt430_execution_result_available") is True
        or result_payload != {}
    )

    returncode = payload.get("prompt430_runtime_execution_returncode")
    if returncode is None:
        returncode = payload.get("prompt430_returncode")
    if returncode is None:
        returncode = result_payload.get("returncode")
    parsed_returncode = _as_optional_int(returncode)
    runtime_command_request = result_payload.get("runtime_command_request")
    if (
        parsed_returncode is None
        and result_available
        and adapter_status == "executed"
        and result_payload.get("dry_run") is True
        and isinstance(runtime_command_request, Mapping)
        and "dry_run_expected_returncode" not in runtime_command_request
    ):
        parsed_returncode = 0

    returncode_classification = _normalize_text(
        payload.get("prompt430_runtime_execution_returncode_classification"),
        default="",
    )
    if not returncode_classification:
        returncode_classification = _normalize_text(
            payload.get("prompt430_returncode_classification"),
            default="",
        )
    if not returncode_classification:
        returncode_classification = _normalize_text(
            result_payload.get("returncode_classification"),
            default="",
        )
    if returncode_classification == "unknown" and parsed_returncode is not None:
        returncode_classification = ""

    status = "not_requested"
    normalized_outcome = "none"
    selected_route = "not_requested"
    blocked_reason = ""
    next_action = "classify_prompt430_runtime_result"

    success_classifications = {"success", "zero", "completed_success"}
    failure_classifications = {"failed", "nonzero", "execution_failed"}

    if not result_available:
        status = "blocked"
        selected_route = "blocked"
        blocked_reason = "prompt430_execution_result_not_ready"
        next_action = "review_prompt430_execution_result"
    elif (
        parsed_returncode == 0
        or returncode_classification in success_classifications
    ):
        status = "classified"
        normalized_outcome = "success"
        selected_route = "success_approve_commit_tag_then_next_cycle"
        next_action = "route_prompt431_runtime_success"
        if returncode_classification not in success_classifications:
            returncode_classification = "success"
        if parsed_returncode is None:
            parsed_returncode = 0
    elif (
        (parsed_returncode is not None and parsed_returncode != 0)
        or returncode_classification in failure_classifications
    ):
        status = "classified"
        normalized_outcome = "failed"
        selected_route = "prepare_targeted_fix"
        next_action = "route_prompt431_runtime_failure"
        if returncode_classification not in failure_classifications:
            returncode_classification = "failed"
    else:
        status = "unknown"
        normalized_outcome = "unknown"
        selected_route = "blocked"
        blocked_reason = "runtime_result_classification_unknown"
        next_action = "fix_prompt438_runtime_result_classification"
        if not returncode_classification:
            returncode_classification = "unknown"

    return {
        "prompt438_runtime_result_classification_wiring_enabled": True,
        "prompt438_schema_version": _PROMPT438_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt438",
        "prompt438_prompt430_result_available": result_available,
        "prompt438_prompt430_adapter_status": adapter_status,
        "prompt438_prompt430_returncode": parsed_returncode,
        "prompt438_prompt430_returncode_classification": (
            returncode_classification
        ),
        "prompt438_runtime_result_classification_status": status,
        "prompt438_normalized_runtime_outcome": normalized_outcome,
        "prompt438_selected_prompt431_route": selected_route,
        "prompt438_blocked_reason": blocked_reason,
        "prompt438_next_action": next_action,
        "prompt438_codex_direct_invocation_allowed": False,
        "prompt438_subprocess_direct_execution_allowed": False,
        "prompt438_git_direct_mutation_allowed": False,
        "prompt438_commit_tag_direct_execution_allowed": False,
        "prompt438_push_allowed": False,
        "prompt438_pr_allowed": False,
        "prompt438_merge_allowed": False,
        "prompt438_rollback_allowed": False,
        "prompt438_unbounded_loop_allowed": False,
        "prompt438_daemon_mode_allowed": False,
    }

def _build_prompt431_runtime_execution_result_review_route_decision_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
    review_requested: bool = False,
    allow_route_decision: bool = False,
    current_cycle: Any = None,
    max_cycles: Any = 2,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}

    parsed_current_cycle = _as_optional_int(current_cycle)
    if parsed_current_cycle is None:
        for key in (
            "prompt431_current_cycle",
            "prompt430_current_cycle",
            "prompt427_current_cycle",
        ):
            parsed_current_cycle = _as_optional_int(payload.get(key))
            if parsed_current_cycle is not None:
                break
    effective_current_cycle = parsed_current_cycle if parsed_current_cycle is not None else 0

    parsed_max_cycles = _as_optional_int(max_cycles)
    effective_max_cycles = (
        parsed_max_cycles if parsed_max_cycles is not None and parsed_max_cycles > 0 else 2
    )
    cycle_capacity_available = effective_current_cycle < effective_max_cycles

    prompt430_status = _normalize_text(
        payload.get("prompt430_bounded_runtime_execution_adapter_status"),
        default="",
    )
    returncode = payload.get("prompt430_runtime_execution_returncode")
    returncode_classification = _normalize_text(
        payload.get("prompt430_runtime_execution_returncode_classification"),
        default="",
    )
    prompt438_status = _normalize_text(
        payload.get("prompt438_runtime_result_classification_status"),
        default="",
    )
    prompt438_outcome = _normalize_text(
        payload.get("prompt438_normalized_runtime_outcome"),
        default="",
    )
    prompt438_route = _normalize_text(
        payload.get("prompt438_selected_prompt431_route"),
        default="",
    )
    prompt438_returncode = payload.get("prompt438_prompt430_returncode")
    prompt438_returncode_classification = _normalize_text(
        payload.get("prompt438_prompt430_returncode_classification"),
        default="",
    )
    prompt438_classified = prompt438_status == "classified"
    if prompt438_classified:
        returncode = prompt438_returncode
        returncode_classification = prompt438_returncode_classification
    prompt430_execution_error = payload.get("prompt430_execution_error") is True
    prompt430_executed_result_ready = (
        prompt430_status == "executed"
        and (
            payload.get("prompt430_execution_result_available") is True
            or payload.get("prompt430_execution_performed") is True
        )
    )
    prompt430_error_result_ready = (
        prompt430_status == "execution_error"
        or prompt430_execution_error
        or returncode_classification == "execution_error"
    )
    prompt438_result_ready = (
        payload.get("prompt438_prompt430_result_available") is True
    )
    prompt430_result_ready = (
        prompt430_executed_result_ready
        or prompt430_error_result_ready
        or prompt438_result_ready
    )

    status = "blocked"
    ready = False
    blocked_reason = ""
    route_decision_ready = False
    selected_route = "blocked"
    route_source = ""
    approve_candidate = False
    commit_tag_handoff_candidate = False
    targeted_fix_candidate = False
    targeted_fix_handoff_candidate = False
    next_cycle_continuation_candidate = False
    failure_review_required = False
    stop_required = False
    stop_reason = ""
    next_action = "review_prompt430_runtime_execution_adapter"

    if not review_requested:
        status = "ready"
        ready = True
        selected_route = "not_requested"
        next_action = "request_prompt431_runtime_result_review"
    elif not allow_route_decision:
        blocked_reason = "route_decision_not_allowed"
        next_action = "allow_prompt431_route_decision"
    elif not prompt430_result_ready:
        blocked_reason = "prompt430_runtime_execution_result_not_ready"
        next_action = "review_prompt430_runtime_execution_adapter"
    elif prompt430_error_result_ready:
        status = "execution_error"
        blocked_reason = "runtime_execution_error"
        selected_route = "runtime_execution_error_stop"
        failure_review_required = True
        stop_required = True
        stop_reason = "runtime_execution_error"
        next_action = "review_prompt430_runtime_execution_error"
    elif prompt438_classified and prompt438_outcome == "success":
        status = "success_route_ready"
        ready = True
        route_decision_ready = True
        selected_route = (
            prompt438_route
            if prompt438_route
            and not prompt438_route.startswith("blocked")
            else "success_approve_commit_tag_then_next_cycle"
        )
        route_source = "prompt438"
        approve_candidate = True
        commit_tag_handoff_candidate = True
        next_cycle_continuation_candidate = cycle_capacity_available
        stop_required = not cycle_capacity_available
        stop_reason = (
            "bounded_runtime_cycle_limit_reached"
            if not cycle_capacity_available
            else ""
        )
        next_action = "prepare_prompt432_success_approve_commit_tag_handoff"
    elif prompt438_classified and prompt438_outcome == "failed":
        status = "targeted_fix_route_ready"
        ready = True
        route_decision_ready = True
        selected_route = (
            prompt438_route
            if prompt438_route
            and not prompt438_route.startswith("blocked")
            else "prepare_targeted_fix"
        )
        route_source = "prompt438"
        targeted_fix_candidate = True
        targeted_fix_handoff_candidate = True
        next_action = "prepare_prompt432_targeted_fix_handoff"
    elif prompt438_status == "unknown":
        blocked_reason = "runtime_result_classification_unknown"
        selected_route = "blocked"
        failure_review_required = True
        stop_required = True
        stop_reason = "runtime_result_classification_unknown"
        next_action = "fix_prompt438_runtime_result_classification"
    elif (
        prompt430_status == "executed"
        and payload.get("prompt430_execution_result_available") is True
        and returncode == 0
        and returncode_classification == "success"
        and payload.get("prompt430_runtime_execution_success") is True
        and payload.get("prompt430_success_path_ready") is True
    ):
        status = "success_route_ready"
        ready = True
        route_decision_ready = True
        selected_route = "success_approve_commit_tag_then_next_cycle"
        route_source = "prompt430"
        approve_candidate = True
        commit_tag_handoff_candidate = True
        next_cycle_continuation_candidate = cycle_capacity_available
        stop_required = not cycle_capacity_available
        stop_reason = (
            "bounded_runtime_cycle_limit_reached"
            if not cycle_capacity_available
            else ""
        )
        next_action = "prepare_prompt432_success_approve_commit_tag_handoff"
    elif (
        (returncode is not None and returncode != 0)
        or returncode_classification == "failed"
        or payload.get("prompt430_runtime_execution_failed") is True
        or payload.get("prompt430_targeted_fix_candidate") is True
    ):
        status = "targeted_fix_route_ready"
        ready = True
        route_decision_ready = True
        selected_route = "prepare_targeted_fix"
        route_source = "prompt430"
        targeted_fix_candidate = True
        targeted_fix_handoff_candidate = True
        next_action = "prepare_prompt432_targeted_fix_handoff"
    elif (
        returncode is None
        or returncode_classification == "unknown"
        or payload.get("prompt430_runtime_execution_unknown") is True
    ):
        blocked_reason = "runtime_execution_returncode_unknown"
        selected_route = "blocked_unknown_runtime_result"
        failure_review_required = True
        stop_required = True
        stop_reason = "runtime_execution_returncode_unknown"
        next_action = "review_prompt430_unknown_runtime_result"
    else:
        blocked_reason = "unclassified_runtime_execution_result"
        selected_route = "blocked_unclassified_runtime_result"
        failure_review_required = True
        stop_required = True
        stop_reason = "unclassified_runtime_execution_result"
        next_action = "review_prompt430_unclassified_runtime_result"

    return {
        "prompt431_runtime_execution_result_review_route_decision_enabled": True,
        "prompt431_schema_version": _PROMPT431_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt431",
        "prompt431_runtime_execution_result_review_route_decision_ready": ready,
        "prompt431_runtime_execution_result_review_route_decision_status": status,
        "prompt431_runtime_execution_result_review_route_decision_blocked_reason": (
            blocked_reason
        ),
        "prompt431_review_requested": bool(review_requested),
        "prompt431_allow_route_decision": bool(allow_route_decision),
        "prompt431_current_cycle": effective_current_cycle,
        "prompt431_max_cycles": effective_max_cycles,
        "prompt431_cycle_capacity_available": cycle_capacity_available,
        "prompt431_prompt430_result_ready": prompt430_result_ready,
        "prompt431_route_decision_ready": route_decision_ready,
        "prompt431_selected_route": selected_route,
        "prompt431_route_source": route_source,
        "prompt431_runtime_returncode": returncode,
        "prompt431_runtime_returncode_classification": returncode_classification,
        "prompt431_approve_candidate": approve_candidate,
        "prompt431_commit_tag_handoff_candidate": commit_tag_handoff_candidate,
        "prompt431_targeted_fix_candidate": targeted_fix_candidate,
        "prompt431_targeted_fix_handoff_candidate": targeted_fix_handoff_candidate,
        "prompt431_next_cycle_continuation_candidate": (
            next_cycle_continuation_candidate
        ),
        "prompt431_failure_review_required": failure_review_required,
        "prompt431_stop_required": stop_required,
        "prompt431_stop_reason": stop_reason,
        "prompt431_runtime_execution_receipt_path": payload.get(
            "prompt430_runtime_execution_receipt_path"
        ),
        "prompt431_runtime_execution_stdout_path": payload.get(
            "prompt430_runtime_execution_stdout_path"
        ),
        "prompt431_runtime_execution_stderr_path": payload.get(
            "prompt430_runtime_execution_stderr_path"
        ),
        "prompt431_runtime_execution_result_payload": payload.get(
            "prompt430_runtime_execution_result_payload"
        ),
        "prompt431_next_action": next_action,
        "prompt431_codex_invocation_allowed": False,
        "prompt431_git_mutation_allowed": False,
        "prompt431_commit_tag_allowed": False,
        "prompt431_commit_tag_performed": False,
        "prompt431_push_allowed": False,
        "prompt431_pr_allowed": False,
        "prompt431_merge_allowed": False,
        "prompt431_rollback_allowed": False,
        "prompt431_unbounded_loop_allowed": False,
        "prompt431_daemon_mode_allowed": False,
        "prompt431_next_cycle_started": False,
        "prompt431_targeted_fix_generated": False,
        "prompt431_targeted_fix_executed": False,
    }

def _build_prompt432_route_decision_handoff_packet_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
    handoff_requested: bool = False,
    allow_handoff_packet: bool = False,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}

    prompt431_route_decision_ready = (
        payload.get("prompt431_route_decision_ready") is True
    )
    selected_route = _normalize_text(
        payload.get("prompt431_selected_route"),
        default="",
    )
    prompt431_status = _normalize_text(
        payload.get(
            "prompt431_runtime_execution_result_review_route_decision_status"
        ),
        default="",
    )
    prompt431_blocked_reason = _normalize_text(
        payload.get(
            "prompt431_runtime_execution_result_review_route_decision_blocked_reason"
        ),
        default="",
    )
    current_cycle = payload.get("prompt431_current_cycle")
    max_cycles = payload.get("prompt431_max_cycles")
    cycle_capacity_available = payload.get("prompt431_cycle_capacity_available")
    runtime_returncode = payload.get("prompt431_runtime_returncode")
    runtime_returncode_classification = _normalize_text(
        payload.get("prompt431_runtime_returncode_classification"),
        default="",
    )
    next_cycle_continuation_candidate = (
        payload.get("prompt431_next_cycle_continuation_candidate") is True
    )
    failure_review_required = (
        payload.get("prompt431_failure_review_required") is True
    )
    stop_required = payload.get("prompt431_stop_required") is True
    stop_reason = _normalize_text(
        payload.get("prompt431_stop_reason"),
        default="",
    )
    runtime_execution_receipt_path = payload.get(
        "prompt431_runtime_execution_receipt_path"
    )
    runtime_execution_stdout_path = payload.get(
        "prompt431_runtime_execution_stdout_path"
    )
    runtime_execution_stderr_path = payload.get(
        "prompt431_runtime_execution_stderr_path"
    )
    runtime_execution_result_payload = payload.get(
        "prompt431_runtime_execution_result_payload"
    )

    status = "blocked"
    ready = False
    blocked_reason = ""
    handoff_packet_ready = False
    selected_handoff = "blocked"
    approve_commit_tag_handoff_ready = False
    targeted_fix_handoff_ready = False
    stop_handoff_ready = False
    approve_commit_tag_handoff_packet: dict[str, Any] = {}
    targeted_fix_handoff_packet: dict[str, Any] = {}
    stop_handoff_packet: dict[str, Any] = {}
    cycle_closure_after_commit_tag = False
    next_action = "review_prompt431_route_decision"

    success_handoff_route = (
        prompt431_route_decision_ready
        and selected_route == "success_approve_commit_tag_then_next_cycle"
        and payload.get("prompt431_approve_candidate") is True
        and payload.get("prompt431_commit_tag_handoff_candidate") is True
        and runtime_returncode == 0
        and runtime_returncode_classification == "success"
    )
    targeted_fix_handoff_route = (
        prompt431_route_decision_ready
        and selected_route == "prepare_targeted_fix"
        and payload.get("prompt431_targeted_fix_candidate") is True
        and payload.get("prompt431_targeted_fix_handoff_candidate") is True
        and (
            (runtime_returncode is not None and runtime_returncode != 0)
            or runtime_returncode_classification == "failed"
        )
    )
    stop_handoff_route = (
        stop_required
        or failure_review_required
        or selected_route.startswith("blocked")
        or prompt431_status in {"blocked", "execution_error"}
    )

    if not handoff_requested:
        status = "ready"
        ready = True
        selected_handoff = "not_requested"
        next_action = "request_prompt432_route_decision_handoff"
    elif not allow_handoff_packet:
        blocked_reason = "handoff_packet_not_allowed"
        next_action = "allow_prompt432_handoff_packet"
    elif success_handoff_route:
        status = "success_handoff_ready"
        ready = True
        handoff_packet_ready = True
        selected_handoff = "approve_commit_tag_handoff"
        approve_commit_tag_handoff_ready = True
        cycle_closure_after_commit_tag = (
            stop_required
            and stop_reason == "bounded_runtime_cycle_limit_reached"
        )
        if cycle_closure_after_commit_tag:
            next_cycle_continuation_candidate = False
            next_action = "prepare_prompt433_approve_commit_tag_execution_then_stop"
        else:
            next_action = "prepare_prompt433_approve_commit_tag_execution"
        approve_commit_tag_handoff_packet = {
            "handoff_type": "approve_commit_tag",
            "source_prompt": "prompt431",
            "selected_route": selected_route,
            "current_cycle": current_cycle,
            "max_cycles": max_cycles,
            "cycle_capacity_available": cycle_capacity_available,
            "next_cycle_continuation_candidate": (
                next_cycle_continuation_candidate
            ),
            "cycle_closure_after_commit_tag": cycle_closure_after_commit_tag,
            "runtime_returncode": runtime_returncode,
            "runtime_returncode_classification": (
                runtime_returncode_classification
            ),
            "runtime_execution_receipt_path": runtime_execution_receipt_path,
            "runtime_execution_stdout_path": runtime_execution_stdout_path,
            "runtime_execution_stderr_path": runtime_execution_stderr_path,
            "runtime_execution_result_payload": runtime_execution_result_payload,
            "commit_tag_execution_policy": "prompt433_only",
            "commit_tag_execution_performed": False,
            "next_cycle_started": False,
        }
    elif targeted_fix_handoff_route:
        status = "targeted_fix_handoff_ready"
        ready = True
        handoff_packet_ready = True
        selected_handoff = "targeted_fix_handoff"
        targeted_fix_handoff_ready = True
        next_action = "prepare_prompt433_targeted_fix_generation_execution"
        targeted_fix_handoff_packet = {
            "handoff_type": "targeted_fix",
            "source_prompt": "prompt431",
            "selected_route": selected_route,
            "current_cycle": current_cycle,
            "max_cycles": max_cycles,
            "runtime_returncode": runtime_returncode,
            "runtime_returncode_classification": (
                runtime_returncode_classification
            ),
            "runtime_execution_receipt_path": runtime_execution_receipt_path,
            "runtime_execution_stdout_path": runtime_execution_stdout_path,
            "runtime_execution_stderr_path": runtime_execution_stderr_path,
            "runtime_execution_result_payload": runtime_execution_result_payload,
            "targeted_fix_generation_policy": "prompt433_only",
            "targeted_fix_execution_policy": "prompt433_only",
            "targeted_fix_generated": False,
            "targeted_fix_executed": False,
            "commit_tag_execution_performed": False,
            "next_cycle_started": False,
        }
    elif stop_handoff_route:
        status = "stop_handoff_ready"
        ready = True
        handoff_packet_ready = True
        selected_handoff = "stop_handoff"
        stop_handoff_ready = True
        next_action = "review_prompt432_stop_handoff"
        stop_handoff_packet = {
            "handoff_type": "stop",
            "source_prompt": "prompt431",
            "selected_route": selected_route,
            "status": prompt431_status,
            "blocked_reason": prompt431_blocked_reason,
            "current_cycle": current_cycle,
            "max_cycles": max_cycles,
            "runtime_returncode": runtime_returncode,
            "runtime_returncode_classification": (
                runtime_returncode_classification
            ),
            "failure_review_required": failure_review_required,
            "stop_required": stop_required,
            "stop_reason": stop_reason,
            "runtime_execution_receipt_path": runtime_execution_receipt_path,
            "runtime_execution_stdout_path": runtime_execution_stdout_path,
            "runtime_execution_stderr_path": runtime_execution_stderr_path,
            "runtime_execution_result_payload": runtime_execution_result_payload,
            "next_cycle_started": False,
            "commit_tag_execution_performed": False,
            "targeted_fix_generated": False,
            "targeted_fix_executed": False,
        }
    elif not prompt431_route_decision_ready:
        blocked_reason = "prompt431_route_decision_not_ready"
        next_action = "review_prompt431_route_decision"
    else:
        blocked_reason = "unclassified_prompt431_route_decision"
        selected_handoff = "blocked_unclassified_route"
        next_action = "review_prompt431_unclassified_route_decision"

    return {
        "prompt432_route_decision_handoff_packet_enabled": True,
        "prompt432_schema_version": _PROMPT432_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt432",
        "prompt432_route_decision_handoff_packet_ready": ready,
        "prompt432_route_decision_handoff_packet_status": status,
        "prompt432_route_decision_handoff_packet_blocked_reason": blocked_reason,
        "prompt432_handoff_requested": bool(handoff_requested),
        "prompt432_allow_handoff_packet": bool(allow_handoff_packet),
        "prompt432_prompt431_route_decision_ready": (
            prompt431_route_decision_ready
        ),
        "prompt432_handoff_packet_ready": handoff_packet_ready,
        "prompt432_selected_handoff": selected_handoff,
        "prompt432_approve_commit_tag_handoff_ready": (
            approve_commit_tag_handoff_ready
        ),
        "prompt432_targeted_fix_handoff_ready": targeted_fix_handoff_ready,
        "prompt432_stop_handoff_ready": stop_handoff_ready,
        "prompt432_approve_commit_tag_handoff_packet": (
            approve_commit_tag_handoff_packet
        ),
        "prompt432_targeted_fix_handoff_packet": targeted_fix_handoff_packet,
        "prompt432_stop_handoff_packet": stop_handoff_packet,
        "prompt432_current_cycle": current_cycle,
        "prompt432_max_cycles": max_cycles,
        "prompt432_cycle_capacity_available": cycle_capacity_available,
        "prompt432_runtime_returncode": runtime_returncode,
        "prompt432_runtime_returncode_classification": (
            runtime_returncode_classification
        ),
        "prompt432_next_cycle_continuation_candidate": (
            next_cycle_continuation_candidate
        ),
        "prompt432_cycle_closure_after_commit_tag": (
            cycle_closure_after_commit_tag
        ),
        "prompt432_failure_review_required": failure_review_required,
        "prompt432_stop_required": stop_required,
        "prompt432_stop_reason": stop_reason,
        "prompt432_next_action": next_action,
        "prompt432_codex_invocation_allowed": False,
        "prompt432_subprocess_execution_allowed": False,
        "prompt432_git_mutation_allowed": False,
        "prompt432_commit_tag_allowed": False,
        "prompt432_commit_tag_performed": False,
        "prompt432_push_allowed": False,
        "prompt432_pr_allowed": False,
        "prompt432_merge_allowed": False,
        "prompt432_rollback_allowed": False,
        "prompt432_unbounded_loop_allowed": False,
        "prompt432_daemon_mode_allowed": False,
        "prompt432_next_cycle_started": False,
        "prompt432_targeted_fix_generated": False,
        "prompt432_targeted_fix_executed": False,
    }

def _build_prompt439_handoff_execution_result_materialization_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
    dry_run: bool = True,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    selected_handoff = _normalize_text(
        payload.get("prompt432_selected_handoff"),
        default="",
    )
    execution_requested = bool(payload.get("prompt433_execution_requested"))
    execution_allowed = bool(payload.get("prompt433_allow_handoff_execution"))
    handoff_available = (
        payload.get("prompt432_route_decision_handoff_packet_ready") is True
        and payload.get("prompt432_handoff_packet_ready") is True
        and selected_handoff
        and selected_handoff not in {"blocked", "not_requested"}
    )

    result_type = "none"
    status = "blocked"
    blocked_reason = ""
    next_action = "review_prompt432_handoff_packet"
    materialized = False
    result_payload: dict[str, Any] = {}

    def _existing_text(*keys: str) -> str:
        for key in keys:
            value = _normalize_text(payload.get(key), default="")
            if value:
                return value
        return ""

    if selected_handoff == "approve_commit_tag_handoff":
        result_type = "approve_commit_tag"
    elif selected_handoff == "targeted_fix_handoff":
        result_type = "targeted_fix"
    elif selected_handoff == "stop_handoff":
        result_type = "stop"
    elif (
        selected_handoff
        and selected_handoff not in {"blocked", "not_requested"}
    ):
        result_type = "unknown"

    if not execution_requested:
        status = "not_requested"
        blocked_reason = ""
        next_action = "request_prompt433_handoff_execution"
    elif not execution_allowed:
        status = "blocked"
        blocked_reason = "handoff_execution_not_allowed"
        next_action = "allow_prompt433_handoff_execution"
    elif not handoff_available:
        status = "blocked"
        blocked_reason = "prompt432_handoff_packet_not_ready"
        next_action = "review_prompt432_handoff_packet"
    elif not dry_run:
        status = "blocked"
        blocked_reason = "prompt439_materialization_requires_dry_run"
        next_action = "review_prompt432_handoff_packet"
    elif result_type == "approve_commit_tag":
        handoff_packet = payload.get(
            "prompt432_approve_commit_tag_handoff_packet"
        )
        if isinstance(handoff_packet, Mapping):
            materialized = True
            status = "materialized"
            next_action = "prompt439_handoff_execution_result_ready"
            result_payload = {
                "result_type": "approve_commit_tag",
                "execution_status": "completed/materialized",
                "commit_tag_performed": False,
                "git_mutation_performed": False,
                "remote_mutation_performed": False,
                "dry_run_metadata_only": True,
                "commit_sha": _existing_text(
                    "prompt433_commit_sha",
                    "prompt434_commit_sha",
                    "prompt385_previous_cycle_commit",
                    "previous_cycle_commit_hash",
                ),
                "tag_name": _existing_text(
                    "prompt433_tag_name",
                    "prompt434_tag_name",
                    "prompt424_approve_commit_tag_handoff_tag_name",
                    "prompt385_previous_cycle_tag_name",
                    "cycle_tag_name",
                ),
                "receipt_path": _existing_text(
                    "prompt433_commit_tag_receipt_path",
                    "prompt434_commit_tag_receipt_path",
                ),
                "handoff_packet": dict(handoff_packet),
                "prompt439_next_action": (
                    "materialize_prompt433_approve_commit_tag_result"
                ),
            }
        else:
            status = "blocked"
            blocked_reason = "prompt432_handoff_packet_not_ready"
            next_action = "review_prompt432_handoff_packet"
    elif result_type == "targeted_fix":
        handoff_packet = payload.get("prompt432_targeted_fix_handoff_packet")
        if isinstance(handoff_packet, Mapping):
            materialized = True
            status = "materialized"
            next_action = "prompt439_handoff_execution_result_ready"
            targeted_fix_performed = (
                payload.get("prompt433_targeted_fix_executed") is True
                or payload.get("prompt432_targeted_fix_executed") is True
            )
            result_payload = {
                "result_type": "targeted_fix",
                "execution_status": "completed/materialized",
                "targeted_fix_performed": targeted_fix_performed,
                "codex_invocation_performed": False,
                "git_mutation_performed": False,
                "dry_run_metadata_only": True,
                "returncode": payload.get("prompt432_runtime_returncode"),
                "handoff_packet": dict(handoff_packet),
                "prompt439_next_action": (
                    "materialize_prompt433_targeted_fix_result"
                ),
            }
        else:
            status = "blocked"
            blocked_reason = "prompt432_handoff_packet_not_ready"
            next_action = "review_prompt432_handoff_packet"
    elif result_type == "stop":
        handoff_packet = payload.get("prompt432_stop_handoff_packet")
        if isinstance(handoff_packet, Mapping):
            materialized = True
            status = "materialized"
            next_action = "prompt439_handoff_execution_result_ready"
            result_payload = {
                "result_type": "stop",
                "execution_status": "completed/materialized",
                "stop_recorded": True,
                "dry_run_metadata_only": True,
                "handoff_packet": dict(handoff_packet),
                "prompt439_next_action": (
                    "materialize_prompt433_stop_result"
                ),
            }
        else:
            status = "blocked"
            blocked_reason = "prompt432_handoff_packet_not_ready"
            next_action = "review_prompt432_handoff_packet"
    else:
        status = "unsupported"
        blocked_reason = "unsupported_prompt432_handoff_type"
        next_action = "fix_prompt439_unsupported_handoff_type"

    return {
        "prompt439_handoff_execution_result_materialization_enabled": True,
        "prompt439_schema_version": _PROMPT439_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt439",
        "prompt439_prompt432_handoff_available": bool(handoff_available),
        "prompt439_prompt432_selected_handoff": selected_handoff,
        "prompt439_prompt433_execution_requested": execution_requested,
        "prompt439_prompt433_execution_allowed": execution_allowed,
        "prompt439_handoff_execution_result_materialized": materialized,
        "prompt439_handoff_execution_result_type": result_type,
        "prompt439_handoff_execution_result_status": status,
        "prompt439_blocked_reason": blocked_reason,
        "prompt439_next_action": next_action,
        "prompt439_handoff_execution_result_payload": result_payload,
        "prompt439_codex_direct_invocation_allowed": False,
        "prompt439_subprocess_direct_execution_allowed": False,
        "prompt439_git_direct_mutation_allowed": False,
        "prompt439_commit_tag_direct_execution_allowed": False,
        "prompt439_push_allowed": False,
        "prompt439_pr_allowed": False,
        "prompt439_merge_allowed": False,
        "prompt439_rollback_allowed": False,
        "prompt439_unbounded_loop_allowed": False,
        "prompt439_daemon_mode_allowed": False,
    }

def _build_prompt433_bounded_handoff_execution_adapter_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
    execution_requested: bool = False,
    allow_handoff_execution: bool = False,
    commit_tag_runner: Callable[..., Any] | None = None,
    targeted_fix_runner: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}

    prompt432_handoff_packet_ready = (
        payload.get("prompt432_route_decision_handoff_packet_ready") is True
        and payload.get("prompt432_handoff_packet_ready") is True
    )
    selected_handoff = _normalize_text(
        payload.get("prompt432_selected_handoff"),
        default="",
    )
    current_cycle = payload.get("prompt432_current_cycle")
    max_cycles = payload.get("prompt432_max_cycles")
    cycle_capacity_available = payload.get("prompt432_cycle_capacity_available")
    next_cycle_continuation_candidate = (
        payload.get("prompt432_next_cycle_continuation_candidate") is True
    )
    cycle_closure_after_commit_tag = (
        payload.get("prompt432_cycle_closure_after_commit_tag") is True
    )
    stop_required = payload.get("prompt432_stop_required") is True
    stop_reason = _normalize_text(
        payload.get("prompt432_stop_reason"),
        default="",
    )

    state: dict[str, Any] = {
        "prompt433_bounded_handoff_execution_adapter_enabled": True,
        "prompt433_schema_version": _PROMPT433_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt433",
        "prompt433_bounded_handoff_execution_adapter_ready": False,
        "prompt433_bounded_handoff_execution_adapter_status": "blocked",
        "prompt433_bounded_handoff_execution_adapter_blocked_reason": "",
        "prompt433_execution_requested": bool(execution_requested),
        "prompt433_allow_handoff_execution": bool(allow_handoff_execution),
        "prompt433_prompt432_handoff_packet_ready": prompt432_handoff_packet_ready,
        "prompt433_selected_execution": "blocked",
        "prompt433_execution_ready": False,
        "prompt433_execution_attempted": False,
        "prompt433_execution_performed": False,
        "prompt433_execution_result_available": False,
        "prompt433_execution_error": False,
        "prompt433_execution_error_message": "",
        "prompt433_current_cycle": current_cycle,
        "prompt433_max_cycles": max_cycles,
        "prompt433_cycle_capacity_available": cycle_capacity_available,
        "prompt433_next_cycle_continuation_candidate": (
            next_cycle_continuation_candidate
        ),
        "prompt433_cycle_closure_after_commit_tag": (
            cycle_closure_after_commit_tag
        ),
        "prompt433_stop_required": stop_required,
        "prompt433_stop_reason": stop_reason,
        "prompt433_approve_commit_tag_execution_attempted": False,
        "prompt433_approve_commit_tag_execution_performed": False,
        "prompt433_approve_commit_tag_execution_success": False,
        "prompt433_approve_commit_tag_execution_failed": False,
        "prompt433_commit_sha": None,
        "prompt433_tag_name": None,
        "prompt433_commit_tag_receipt_path": None,
        "prompt433_commit_tag_result_payload": {},
        "prompt433_targeted_fix_generation_attempted": False,
        "prompt433_targeted_fix_generated": False,
        "prompt433_targeted_fix_execution_attempted": False,
        "prompt433_targeted_fix_executed": False,
        "prompt433_targeted_fix_returncode": None,
        "prompt433_targeted_fix_success": False,
        "prompt433_targeted_fix_failed": False,
        "prompt433_targeted_fix_unknown": False,
        "prompt433_targeted_fix_prompt_path": None,
        "prompt433_targeted_fix_receipt_path": None,
        "prompt433_targeted_fix_result_payload": {},
        "prompt433_stop_recorded": False,
        "prompt433_stop_handoff_packet": {},
        "prompt433_next_action": "review_prompt432_handoff_packet",
        "prompt433_codex_direct_invocation_allowed": False,
        "prompt433_subprocess_direct_execution_allowed": False,
        "prompt433_git_direct_mutation_allowed": False,
        "prompt433_push_allowed": False,
        "prompt433_pr_allowed": False,
        "prompt433_merge_allowed": False,
        "prompt433_rollback_allowed": False,
        "prompt433_unbounded_loop_allowed": False,
        "prompt433_daemon_mode_allowed": False,
        "prompt433_next_cycle_started": False,
        "prompt433_commit_tag_runner_used": False,
        "prompt433_targeted_fix_runner_used": False,
    }

    if not execution_requested:
        state.update(
            {
                "prompt433_bounded_handoff_execution_adapter_ready": True,
                "prompt433_bounded_handoff_execution_adapter_status": "ready",
                "prompt433_selected_execution": "not_requested",
                "prompt433_next_action": (
                    "request_prompt433_handoff_execution"
                ),
            }
        )
        return state

    if not allow_handoff_execution:
        state.update(
            {
                "prompt433_bounded_handoff_execution_adapter_blocked_reason": (
                    "handoff_execution_not_allowed"
                ),
                "prompt433_selected_execution": "blocked",
                "prompt433_next_action": "allow_prompt433_handoff_execution",
            }
        )
        return state

    if not prompt432_handoff_packet_ready:
        state.update(
            {
                "prompt433_bounded_handoff_execution_adapter_blocked_reason": (
                    "prompt432_handoff_packet_not_ready"
                ),
                "prompt433_selected_execution": "blocked",
                "prompt433_next_action": "review_prompt432_handoff_packet",
            }
        )
        return state

    approve_packet = payload.get("prompt432_approve_commit_tag_handoff_packet")
    targeted_fix_packet = payload.get("prompt432_targeted_fix_handoff_packet")
    stop_packet = payload.get("prompt432_stop_handoff_packet")

    approve_route = (
        selected_handoff == "approve_commit_tag_handoff"
        and payload.get("prompt432_approve_commit_tag_handoff_ready") is True
        and isinstance(approve_packet, dict)
        and approve_packet.get("handoff_type") == "approve_commit_tag"
    )
    targeted_fix_route = (
        selected_handoff == "targeted_fix_handoff"
        and payload.get("prompt432_targeted_fix_handoff_ready") is True
        and isinstance(targeted_fix_packet, dict)
        and targeted_fix_packet.get("handoff_type") == "targeted_fix"
    )
    stop_route = (
        selected_handoff == "stop_handoff"
        and payload.get("prompt432_stop_handoff_ready") is True
        and isinstance(stop_packet, dict)
        and stop_packet.get("handoff_type") == "stop"
    )
    prompt439_result_materialized = (
        payload.get("prompt439_handoff_execution_result_materialized") is True
    )
    prompt439_result_type = _normalize_text(
        payload.get("prompt439_handoff_execution_result_type"),
        default="",
    )
    prompt439_result_payload = payload.get(
        "prompt439_handoff_execution_result_payload"
    )
    if not isinstance(prompt439_result_payload, Mapping):
        prompt439_result_payload = {}

    if approve_route:
        state.update(
            {
                "prompt433_selected_execution": "approve_commit_tag",
                "prompt433_execution_ready": True,
            }
        )
        if (
            prompt439_result_materialized
            and prompt439_result_type == "approve_commit_tag"
            and not callable(commit_tag_runner)
        ):
            result_payload = dict(prompt439_result_payload)
            effective_next_cycle_candidate = next_cycle_continuation_candidate
            if cycle_closure_after_commit_tag:
                effective_next_cycle_candidate = False
            if cycle_closure_after_commit_tag:
                next_action = "prepare_prompt434_cycle_closure_stop"
            elif effective_next_cycle_candidate:
                next_action = "prepare_prompt434_next_cycle_continuation"
            else:
                next_action = "complete_prompt434_commit_tag_success_closure"
            state.update(
                {
                    "prompt433_bounded_handoff_execution_adapter_ready": True,
                    "prompt433_bounded_handoff_execution_adapter_status": (
                        "approve_commit_tag_executed"
                    ),
                    "prompt433_execution_performed": False,
                    "prompt433_execution_result_available": True,
                    "prompt433_next_cycle_continuation_candidate": (
                        effective_next_cycle_candidate
                    ),
                    "prompt433_approve_commit_tag_execution_performed": False,
                    "prompt433_approve_commit_tag_execution_success": True,
                    "prompt433_approve_commit_tag_execution_failed": False,
                    "prompt433_commit_sha": _normalize_text(
                        result_payload.get("commit_sha"),
                        default="",
                    ),
                    "prompt433_tag_name": _normalize_text(
                        result_payload.get("tag_name"),
                        default="",
                    ),
                    "prompt433_commit_tag_receipt_path": _normalize_text(
                        result_payload.get("receipt_path"),
                        default="",
                    ),
                    "prompt433_commit_tag_result_payload": result_payload,
                    "prompt433_next_action": next_action,
                }
            )
            return state
        if not callable(commit_tag_runner):
            state.update(
                {
                    "prompt433_bounded_handoff_execution_adapter_blocked_reason": (
                        "commit_tag_runner_missing"
                    ),
                    "prompt433_next_action": "provide_prompt433_commit_tag_runner",
                }
            )
            return state

        approve_packet_copy = dict(approve_packet)
        state["prompt433_execution_attempted"] = True
        state["prompt433_approve_commit_tag_execution_attempted"] = True
        state["prompt433_commit_tag_runner_used"] = True
        try:
            runner_result = commit_tag_runner(
                handoff_packet=approve_packet_copy,
                run_state_payload=run_state_payload,
            )
        except Exception as exc:  # noqa: BLE001 - normalize injected runner failures.
            state.update(
                {
                    "prompt433_bounded_handoff_execution_adapter_status": (
                        "execution_error"
                    ),
                    "prompt433_bounded_handoff_execution_adapter_blocked_reason": (
                        "commit_tag_runner_exception"
                    ),
                    "prompt433_execution_error": True,
                    "prompt433_execution_error_message": str(exc),
                    "prompt433_next_action": (
                        "review_prompt433_handoff_execution_error"
                    ),
                }
            )
            return state

        if not isinstance(runner_result, dict):
            state.update(
                {
                    "prompt433_bounded_handoff_execution_adapter_status": (
                        "execution_error"
                    ),
                    "prompt433_bounded_handoff_execution_adapter_blocked_reason": (
                        "commit_tag_runner_result_not_mapping"
                    ),
                    "prompt433_execution_error": True,
                    "prompt433_next_action": (
                        "review_prompt433_handoff_execution_error"
                    ),
                }
            )
            return state

        allowed_keys = (
            "status",
            "commit_sha",
            "tag_name",
            "returncode",
            "stdout",
            "stderr",
            "receipt_path",
            "performed",
            "error_message",
        )
        result_payload = {
            key: runner_result.get(key)
            for key in allowed_keys
            if key in runner_result
        }
        returncode = runner_result.get("returncode")
        performed = (
            runner_result.get("performed") is True or returncode == 0
        )
        approve_success = (
            runner_result.get("performed") is True
            and (returncode == 0 or returncode is None)
        )
        approve_failed = (
            (returncode is not None and returncode != 0)
            or runner_result.get("performed") is False
        )
        effective_next_cycle_candidate = next_cycle_continuation_candidate
        if cycle_closure_after_commit_tag:
            effective_next_cycle_candidate = False

        if (
            approve_success
            and not cycle_closure_after_commit_tag
            and effective_next_cycle_candidate
        ):
            next_action = "prepare_prompt434_next_cycle_continuation"
        elif approve_success and cycle_closure_after_commit_tag:
            next_action = "prepare_prompt434_cycle_closure_stop"
        else:
            next_action = "review_prompt433_approve_commit_tag_failure"

        state.update(
            {
                "prompt433_bounded_handoff_execution_adapter_ready": True,
                "prompt433_bounded_handoff_execution_adapter_status": (
                    "approve_commit_tag_executed"
                ),
                "prompt433_execution_performed": performed,
                "prompt433_execution_result_available": True,
                "prompt433_next_cycle_continuation_candidate": (
                    effective_next_cycle_candidate
                ),
                "prompt433_approve_commit_tag_execution_performed": performed,
                "prompt433_approve_commit_tag_execution_success": (
                    approve_success
                ),
                "prompt433_approve_commit_tag_execution_failed": (
                    approve_failed
                ),
                "prompt433_commit_sha": runner_result.get("commit_sha"),
                "prompt433_tag_name": runner_result.get("tag_name"),
                "prompt433_commit_tag_receipt_path": runner_result.get(
                    "receipt_path"
                ),
                "prompt433_commit_tag_result_payload": (
                    dict(runner_result) if approve_success else result_payload
                ),
                "prompt433_next_action": next_action,
            }
        )
        return state

    if targeted_fix_route:
        state.update(
            {
                "prompt433_selected_execution": "targeted_fix",
                "prompt433_execution_ready": True,
            }
        )
        if (
            prompt439_result_materialized
            and prompt439_result_type == "targeted_fix"
            and not callable(targeted_fix_runner)
        ):
            result_payload = dict(prompt439_result_payload)
            returncode = result_payload.get("returncode")
            targeted_fix_executed = (
                result_payload.get("targeted_fix_performed") is True
            )
            targeted_fix_success = targeted_fix_executed and returncode == 0
            targeted_fix_failed = (
                returncode is not None
                and returncode != 0
            )
            targeted_fix_unknown = (
                not targeted_fix_success
                and not targeted_fix_failed
            )
            if targeted_fix_success:
                next_action = "prepare_prompt434_targeted_fix_success_review"
            elif targeted_fix_failed:
                next_action = "prepare_prompt434_targeted_fix_failure_stop"
            else:
                next_action = "review_prompt433_targeted_fix_unknown_result"
            state.update(
                {
                    "prompt433_bounded_handoff_execution_adapter_ready": True,
                    "prompt433_bounded_handoff_execution_adapter_status": (
                        "targeted_fix_executed"
                    ),
                    "prompt433_execution_performed": False,
                    "prompt433_execution_result_available": True,
                    "prompt433_targeted_fix_generated": False,
                    "prompt433_targeted_fix_executed": targeted_fix_executed,
                    "prompt433_targeted_fix_returncode": returncode,
                    "prompt433_targeted_fix_success": targeted_fix_success,
                    "prompt433_targeted_fix_failed": targeted_fix_failed,
                    "prompt433_targeted_fix_unknown": targeted_fix_unknown,
                    "prompt433_targeted_fix_prompt_path": "",
                    "prompt433_targeted_fix_receipt_path": "",
                    "prompt433_targeted_fix_result_payload": result_payload,
                    "prompt433_next_action": next_action,
                }
            )
            return state
        if not callable(targeted_fix_runner):
            state.update(
                {
                    "prompt433_bounded_handoff_execution_adapter_blocked_reason": (
                        "targeted_fix_runner_missing"
                    ),
                    "prompt433_next_action": (
                        "provide_prompt433_targeted_fix_runner"
                    ),
                }
            )
            return state

        state["prompt433_execution_attempted"] = True
        state["prompt433_targeted_fix_generation_attempted"] = True
        state["prompt433_targeted_fix_execution_attempted"] = True
        state["prompt433_targeted_fix_runner_used"] = True
        try:
            runner_result = targeted_fix_runner(
                handoff_packet=dict(targeted_fix_packet),
                run_state_payload=run_state_payload,
            )
        except Exception as exc:  # noqa: BLE001 - normalize injected runner failures.
            state.update(
                {
                    "prompt433_bounded_handoff_execution_adapter_status": (
                        "execution_error"
                    ),
                    "prompt433_bounded_handoff_execution_adapter_blocked_reason": (
                        "targeted_fix_runner_exception"
                    ),
                    "prompt433_execution_error": True,
                    "prompt433_execution_error_message": str(exc),
                    "prompt433_next_action": (
                        "review_prompt433_handoff_execution_error"
                    ),
                }
            )
            return state

        if not isinstance(runner_result, dict):
            state.update(
                {
                    "prompt433_bounded_handoff_execution_adapter_status": (
                        "execution_error"
                    ),
                    "prompt433_bounded_handoff_execution_adapter_blocked_reason": (
                        "targeted_fix_runner_result_not_mapping"
                    ),
                    "prompt433_execution_error": True,
                    "prompt433_next_action": (
                        "review_prompt433_handoff_execution_error"
                    ),
                }
            )
            return state

        allowed_keys = (
            "status",
            "generated",
            "executed",
            "returncode",
            "stdout",
            "stderr",
            "prompt_path",
            "receipt_path",
            "result_payload",
            "error_message",
        )
        filtered_result = {
            key: runner_result.get(key)
            for key in allowed_keys
            if key in runner_result
        }
        returncode = runner_result.get("returncode")
        executed = runner_result.get("executed") is True
        targeted_fix_success = executed and returncode == 0
        targeted_fix_failed = returncode is not None and returncode != 0
        targeted_fix_unknown = returncode is None
        if targeted_fix_success:
            next_action = "prepare_prompt434_targeted_fix_success_review"
        elif targeted_fix_failed:
            next_action = "prepare_prompt434_targeted_fix_failure_stop"
        else:
            next_action = "review_prompt433_targeted_fix_unknown_result"

        state.update(
            {
                "prompt433_bounded_handoff_execution_adapter_ready": True,
                "prompt433_bounded_handoff_execution_adapter_status": (
                    "targeted_fix_executed"
                ),
                "prompt433_execution_performed": (
                    executed or returncode is not None
                ),
                "prompt433_execution_result_available": True,
                "prompt433_targeted_fix_generated": (
                    runner_result.get("generated") is True
                ),
                "prompt433_targeted_fix_executed": executed,
                "prompt433_targeted_fix_returncode": returncode,
                "prompt433_targeted_fix_success": targeted_fix_success,
                "prompt433_targeted_fix_failed": targeted_fix_failed,
                "prompt433_targeted_fix_unknown": targeted_fix_unknown,
                "prompt433_targeted_fix_prompt_path": runner_result.get(
                    "prompt_path"
                ),
                "prompt433_targeted_fix_receipt_path": runner_result.get(
                    "receipt_path"
                ),
                "prompt433_targeted_fix_result_payload": runner_result.get(
                    "result_payload",
                    filtered_result,
                ),
                "prompt433_next_action": next_action,
            }
        )
        return state

    if stop_route:
        stop_packet_copy = dict(stop_packet)
        effective_stop_reason = stop_reason or _normalize_text(
            stop_packet_copy.get("stop_reason"),
            default="",
        )
        state.update(
            {
                "prompt433_bounded_handoff_execution_adapter_ready": True,
                "prompt433_bounded_handoff_execution_adapter_status": (
                    "stop_handoff_recorded"
                ),
                "prompt433_selected_execution": "stop",
                "prompt433_execution_ready": True,
                "prompt433_execution_result_available": True,
                "prompt433_stop_recorded": True,
                "prompt433_stop_required": True,
                "prompt433_stop_reason": effective_stop_reason,
                "prompt433_stop_handoff_packet": stop_packet_copy,
                "prompt433_next_action": "prepare_prompt434_stop_closure",
            }
        )
        return state

    state.update(
        {
            "prompt433_bounded_handoff_execution_adapter_blocked_reason": (
                "unclassified_prompt432_handoff"
            ),
            "prompt433_selected_execution": "blocked_unclassified_handoff",
            "prompt433_next_action": "review_prompt432_unclassified_handoff",
        }
    )
    return state

def _build_prompt435_bounded_cycle_runner_adapter(
    *,
    transport_mode: str,
    repo_path: str | Path | None,
    artifacts_dir: str | Path,
    out_dir: str | Path,
    job_id: str,
    live_transport_enabled: bool = False,
) -> Callable[..., dict[str, Any]]:
    normalized_transport_mode = _normalize_text(transport_mode, default="dry-run")
    normalized_repo_path = _normalize_text(repo_path, default="")
    normalized_artifacts_dir = _normalize_text(artifacts_dir, default="")
    normalized_out_dir = _normalize_text(out_dir, default="")
    normalized_job_id = _normalize_text(job_id, default="planned-execution")

    def _cycle_runner(
        *,
        next_cycle_number: Any,
        current_cycle: Any,
        max_cycles: Any,
        previous_commit_sha: Any,
        previous_tag_name: Any,
        previous_commit_tag_receipt_path: Any,
        run_state_payload: Any,
    ) -> dict[str, Any]:
        next_job_id = f"{normalized_job_id}-cycle-{next_cycle_number}"
        next_command_argv = [
            sys.executable or "python",
            "scripts/run_planned_execution.py",
            "--artifacts-dir",
            normalized_artifacts_dir,
            "--out-dir",
            normalized_out_dir,
            "--job-id",
            next_job_id,
            "--transport-mode",
            normalized_transport_mode,
        ]
        if normalized_repo_path:
            next_command_argv.extend(["--repo-path", normalized_repo_path])
        if normalized_transport_mode == "live" and bool(live_transport_enabled):
            next_command_argv.append("--enable-live-transport")
        next_command_argv.append("--json")

        live_transport_flag_omitted = (
            normalized_transport_mode == "live" and not bool(live_transport_enabled)
        )
        return {
            "status": "completed",
            "next_prompt_id": "prompt_unknown",
            "next_prompt_path": "",
            "next_prompt_text": "",
            "next_command_argv": next_command_argv,
            "next_run_state_path": "",
            "next_manifest_path": "",
            "next_artifacts_dir": normalized_artifacts_dir,
            "next_out_dir": normalized_out_dir,
            "next_job_id": next_job_id,
            "returncode": 0,
            "receipt_path": "",
            "result_payload": {
                "prompt435_cycle_runner_adapter": "metadata_only",
                "next_cycle_number": next_cycle_number,
                "current_cycle": current_cycle,
                "max_cycles": max_cycles,
                "previous_commit_sha": previous_commit_sha,
                "previous_tag_name": previous_tag_name,
                "previous_commit_tag_receipt_path": (
                    previous_commit_tag_receipt_path
                ),
                "transport_mode": normalized_transport_mode,
                "repo_path": normalized_repo_path,
                "live_transport_enabled": bool(live_transport_enabled),
                "enable_live_transport_flag_omitted": live_transport_flag_omitted,
                "run_state_payload_received": isinstance(
                    run_state_payload,
                    Mapping,
                ),
            },
        }

    return _cycle_runner

def _build_prompt435_runtime_activation_wiring_state(
    *,
    request_autonomous_closure: bool = False,
    allow_autonomous_closure: bool = False,
    allow_next_cycle: bool = False,
    enable_bounded_cycle_runner: bool = False,
    autonomous_current_cycle: Any = None,
    autonomous_max_cycles: Any = 2,
) -> dict[str, Any]:
    request_closure = bool(request_autonomous_closure)
    allow_closure = bool(allow_autonomous_closure)
    allow_cycle = bool(allow_next_cycle)
    runner_connected = bool(enable_bounded_cycle_runner)
    if not request_closure:
        next_action = "request_prompt434_autonomous_self_run_closure"
    elif not allow_closure:
        next_action = "allow_prompt434_autonomous_closure"
    elif allow_cycle and not runner_connected:
        next_action = "enable_prompt435_bounded_cycle_runner"
    else:
        next_action = "activate_prompt434_autonomous_closure"

    return {
        "prompt435_runtime_activation_wiring_enabled": True,
        "prompt435_schema_version": _PROMPT435_SCHEMA_VERSION,
        "prompt435_request_autonomous_closure": request_closure,
        "prompt435_allow_autonomous_closure": allow_closure,
        "prompt435_allow_next_cycle": allow_cycle,
        "prompt435_enable_bounded_cycle_runner": runner_connected,
        "prompt435_autonomous_current_cycle": autonomous_current_cycle,
        "prompt435_autonomous_max_cycles": autonomous_max_cycles,
        "prompt435_cycle_runner_connected": runner_connected,
        "prompt435_cycle_runner_mode": "metadata_only" if runner_connected else "",
        "prompt435_next_action": next_action,
        "prompt435_codex_direct_invocation_allowed": False,
        "prompt435_subprocess_direct_execution_allowed": False,
        "prompt435_git_direct_mutation_allowed": False,
        "prompt435_commit_tag_direct_execution_allowed": False,
        "prompt435_push_allowed": False,
        "prompt435_pr_allowed": False,
        "prompt435_merge_allowed": False,
        "prompt435_rollback_allowed": False,
        "prompt435_unbounded_loop_allowed": False,
        "prompt435_daemon_mode_allowed": False,
    }

def _build_prompt436_runtime_chain_activation_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}

    request_runtime_execution = bool(
        payload.get("prompt436_request_runtime_execution")
    )
    allow_runtime_execution = bool(
        payload.get("prompt436_allow_runtime_execution")
    )
    request_runtime_result_review = bool(
        payload.get("prompt436_request_runtime_result_review")
    )
    request_route_handoff = bool(
        payload.get("prompt436_request_route_handoff")
    )
    request_handoff_execution = bool(
        payload.get("prompt436_request_handoff_execution")
    )
    allow_handoff_execution = bool(
        payload.get("prompt436_allow_handoff_execution")
    )
    request_autonomous_closure = bool(
        payload.get("prompt435_request_autonomous_closure")
    )

    prompt436_requested = any(
        (
            request_runtime_execution,
            request_runtime_result_review,
            request_route_handoff,
            request_handoff_execution,
        )
    )

    def _adapter_activation_status(
        *,
        requested: bool,
        status: str,
        ready: bool = False,
        completed_statuses: set[str] | None = None,
        failed_statuses: set[str] | None = None,
    ) -> str:
        if not requested:
            return "not_requested"
        normalized_status = _normalize_text(status, default="")
        if normalized_status in (failed_statuses or set()):
            return "failed"
        if normalized_status in (completed_statuses or set()):
            return "completed"
        if normalized_status == "blocked":
            return "blocked"
        if ready:
            return "ready"
        return "blocked"

    prompt430_status = _adapter_activation_status(
        requested=request_runtime_execution,
        status=_normalize_text(
            payload.get("prompt430_bounded_runtime_execution_adapter_status"),
            default="",
        ),
        ready=payload.get("prompt430_execution_ready") is True,
        completed_statuses={"executed"},
        failed_statuses={"execution_error"},
    )
    if (
        request_runtime_execution
        and allow_runtime_execution
        and prompt430_status == "blocked"
    ):
        prompt430_blocker = _normalize_text(
            payload.get(
                "prompt430_bounded_runtime_execution_adapter_blocked_reason"
            ),
            default="",
        )
        if prompt430_blocker in {
            "prompt429_launch_packet_not_ready",
            "runtime_command_argv_not_ready",
            "command_runner_missing",
        }:
            prompt430_status = "ready"

    prompt431_status = _adapter_activation_status(
        requested=request_runtime_result_review,
        status=_normalize_text(
            payload.get(
                "prompt431_runtime_execution_result_review_route_decision_status"
            ),
            default="",
        ),
        ready=payload.get("prompt431_route_decision_ready") is True,
        completed_statuses={
            "success_route_ready",
            "targeted_fix_route_ready",
        },
        failed_statuses={"execution_error"},
    )
    prompt432_status = _adapter_activation_status(
        requested=request_route_handoff,
        status=_normalize_text(
            payload.get("prompt432_route_decision_handoff_packet_status"),
            default="",
        ),
        ready=payload.get("prompt432_handoff_packet_ready") is True,
        completed_statuses={
            "success_handoff_ready",
            "targeted_fix_handoff_ready",
            "stop_handoff_ready",
        },
    )
    prompt433_status = _adapter_activation_status(
        requested=request_handoff_execution,
        status=_normalize_text(
            payload.get("prompt433_bounded_handoff_execution_adapter_status"),
            default="",
        ),
        ready=payload.get("prompt433_execution_ready") is True,
        completed_statuses={
            "approve_commit_tag_executed",
            "targeted_fix_executed",
            "stop_handoff_recorded",
        },
        failed_statuses={"execution_error"},
    )
    prompt434_status = _adapter_activation_status(
        requested=request_autonomous_closure,
        status=_normalize_text(
            payload.get(
                "prompt434_bounded_complete_autonomous_self_run_closure_status"
            ),
            default="",
        ),
        ready=payload.get("prompt434_closure_ready") is True,
        completed_statuses={
            "cycle_closure_ready",
            "next_cycle_started",
            "targeted_fix_success_rejoin_ready",
            "targeted_fix_failure_stop",
            "targeted_fix_unknown_stop",
            "stop_closure_ready",
        },
        failed_statuses={"execution_error", "next_cycle_start_failed"},
    )

    chain_status = "not_requested"
    blocked_reason = ""
    next_action = "request_prompt436_runtime_chain_activation"

    if prompt436_requested:
        stage_results = (
            prompt430_status,
            prompt431_status,
            prompt432_status,
            prompt433_status,
            prompt434_status,
        )
        if "failed" in stage_results:
            chain_status = "failed"
            if prompt430_status == "failed":
                blocked_reason = "prompt430_runtime_execution_failed"
                next_action = "review_prompt430_execution_result"
            elif prompt431_status == "failed":
                blocked_reason = "prompt431_route_decision_failed"
                next_action = "review_prompt431_route_decision"
            elif prompt432_status == "failed":
                blocked_reason = "prompt432_handoff_packet_failed"
                next_action = "review_prompt432_handoff_packet"
            elif prompt433_status == "failed":
                blocked_reason = "prompt433_handoff_execution_failed"
                next_action = "review_prompt434_closure_result"
            else:
                blocked_reason = "prompt434_closure_failed"
                next_action = "review_prompt434_closure_result"
        elif request_runtime_execution and not allow_runtime_execution:
            chain_status = "blocked"
            blocked_reason = "runtime_execution_not_allowed"
            next_action = "allow_prompt430_runtime_execution"
        elif (
            request_runtime_result_review
            and payload.get("prompt431_prompt430_result_ready") is not True
        ):
            chain_status = "blocked"
            prompt431_status = "blocked"
            blocked_reason = "prompt430_execution_result_not_ready"
            next_action = "review_prompt430_execution_result"
        elif (
            request_route_handoff
            and payload.get("prompt432_prompt431_route_decision_ready")
            is not True
        ):
            chain_status = "blocked"
            prompt432_status = "blocked"
            blocked_reason = "prompt431_route_decision_not_ready"
            next_action = "review_prompt431_route_decision"
        elif request_handoff_execution and not allow_handoff_execution:
            chain_status = "blocked"
            prompt433_status = "blocked"
            blocked_reason = "handoff_execution_not_allowed"
            next_action = "allow_prompt433_handoff_execution"
        elif (
            request_handoff_execution
            and payload.get("prompt433_prompt432_handoff_packet_ready")
            is not True
        ):
            chain_status = "blocked"
            prompt433_status = "blocked"
            blocked_reason = "prompt432_handoff_packet_not_ready"
            next_action = "review_prompt432_handoff_packet"
        elif request_autonomous_closure and prompt434_status == "blocked":
            chain_status = "blocked"
            blocked_reason = _normalize_text(
                payload.get(
                    "prompt434_bounded_complete_autonomous_self_run_closure_blocked_reason"
                ),
                default="prompt434_closure_blocked",
            )
            next_action = "review_prompt434_closure_result"
        elif request_autonomous_closure and prompt434_status != "completed":
            chain_status = "ready"
            next_action = "activate_prompt434_autonomous_self_run_closure"
        elif request_autonomous_closure:
            chain_status = "completed"
            next_action = "prompt436_runtime_chain_activation_completed"
        else:
            chain_status = "ready"
            next_action = "prompt436_runtime_chain_activation_completed"

    return {
        "prompt436_runtime_chain_activation_enabled": True,
        "prompt436_schema_version": _PROMPT436_SCHEMA_VERSION,
        "prompt436_request_runtime_execution": request_runtime_execution,
        "prompt436_allow_runtime_execution": allow_runtime_execution,
        "prompt436_request_runtime_result_review": (
            request_runtime_result_review
        ),
        "prompt436_request_route_handoff": request_route_handoff,
        "prompt436_request_handoff_execution": request_handoff_execution,
        "prompt436_allow_handoff_execution": allow_handoff_execution,
        "prompt436_prompt430_activation_status": prompt430_status,
        "prompt436_prompt431_activation_status": prompt431_status,
        "prompt436_prompt432_activation_status": prompt432_status,
        "prompt436_prompt433_activation_status": prompt433_status,
        "prompt436_prompt434_activation_status": prompt434_status,
        "prompt436_chain_activation_status": chain_status,
        "prompt436_blocked_reason": blocked_reason,
        "prompt436_next_action": next_action,
        "prompt436_codex_direct_invocation_allowed": False,
        "prompt436_subprocess_direct_execution_allowed": False,
        "prompt436_git_direct_mutation_allowed": False,
        "prompt436_commit_tag_direct_execution_allowed": False,
        "prompt436_push_allowed": False,
        "prompt436_pr_allowed": False,
        "prompt436_merge_allowed": False,
        "prompt436_rollback_allowed": False,
        "prompt436_unbounded_loop_allowed": False,
        "prompt436_daemon_mode_allowed": False,
    }

def _build_prompt434_bounded_complete_autonomous_self_run_closure_state(
    *,
    run_state_payload: Mapping[str, Any] | None,
    closure_requested: bool = False,
    allow_autonomous_closure: bool = False,
    allow_next_cycle: bool = False,
    current_cycle: Any = None,
    max_cycles: Any = 2,
    cycle_runner: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}

    def _copy_cycle_payload(value: Any) -> Any:
        if isinstance(value, Mapping):
            return {
                key: _copy_cycle_payload(item)
                for key, item in value.items()
                if isinstance(key, str)
            }
        if isinstance(value, list):
            return [_copy_cycle_payload(item) for item in value]
        if isinstance(value, tuple):
            return [_copy_cycle_payload(item) for item in value]
        return value

    def _int_like_or_none(value: Any) -> int | None:
        if isinstance(value, bool):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    effective_current_cycle = _int_like_or_none(current_cycle)
    if effective_current_cycle is None:
        for cycle_candidate in (
            payload.get("prompt434_current_cycle"),
            payload.get("prompt433_current_cycle"),
            0,
        ):
            effective_current_cycle = _int_like_or_none(cycle_candidate)
            if effective_current_cycle is not None:
                break
    if effective_current_cycle is None:
        effective_current_cycle = 0

    normalized_max_cycles = _int_like_or_none(max_cycles)
    if normalized_max_cycles is None or normalized_max_cycles <= 0:
        for max_cycle_candidate in (
            payload.get("prompt434_max_cycles"),
            payload.get("prompt433_max_cycles"),
            2,
        ):
            normalized_max_cycles = _int_like_or_none(max_cycle_candidate)
            if (
                normalized_max_cycles is not None
                and normalized_max_cycles > 0
            ):
                break
    if normalized_max_cycles is None or normalized_max_cycles <= 0:
        normalized_max_cycles = 2

    next_cycle_number = effective_current_cycle + 1
    cycle_capacity_available = next_cycle_number < normalized_max_cycles
    cycle_limit_reached = not cycle_capacity_available
    prompt433_status = _normalize_text(
        payload.get("prompt433_bounded_handoff_execution_adapter_status"),
        default="",
    )
    prompt433_result_ready = (
        payload.get("prompt433_execution_result_available") is True
        or payload.get("prompt433_stop_recorded") is True
        or payload.get("prompt433_execution_error") is True
        or prompt433_status == "execution_error"
    )
    selected_execution = _normalize_text(
        payload.get("prompt433_selected_execution"),
        default="",
    )
    stop_handoff_packet = payload.get("prompt433_stop_handoff_packet")
    stop_handoff_reason = ""
    if isinstance(stop_handoff_packet, Mapping):
        stop_handoff_reason = _normalize_text(
            stop_handoff_packet.get("stop_reason"),
            default="",
        )

    state: dict[str, Any] = {
        "prompt434_bounded_complete_autonomous_self_run_closure_enabled": True,
        "prompt434_schema_version": _PROMPT434_SCHEMA_VERSION,
        "local_only": True,
        "source_prompt": "prompt434",
        "prompt434_bounded_complete_autonomous_self_run_closure_ready": False,
        "prompt434_bounded_complete_autonomous_self_run_closure_status": (
            "blocked"
        ),
        "prompt434_bounded_complete_autonomous_self_run_closure_blocked_reason": (
            ""
        ),
        "prompt434_closure_requested": bool(closure_requested),
        "prompt434_allow_autonomous_closure": bool(allow_autonomous_closure),
        "prompt434_allow_next_cycle": bool(allow_next_cycle),
        "prompt434_prompt433_result_ready": prompt433_result_ready,
        "prompt434_closure_ready": False,
        "prompt434_selected_closure": "blocked",
        "prompt434_current_cycle": effective_current_cycle,
        "prompt434_next_cycle_number": next_cycle_number,
        "prompt434_max_cycles": normalized_max_cycles,
        "prompt434_cycle_capacity_available": cycle_capacity_available,
        "prompt434_cycle_limit_reached": cycle_limit_reached,
        "prompt434_complete_autonomous_self_run_candidate": False,
        "prompt434_autonomous_cycle_complete": False,
        "prompt434_next_cycle_start_attempted": False,
        "prompt434_next_cycle_started": False,
        "prompt434_cycle_runner_used": False,
        "prompt434_next_prompt_selected": False,
        "prompt434_next_prompt_generated": False,
        "prompt434_next_command_ready": False,
        "prompt434_next_prompt_id": None,
        "prompt434_next_prompt_path": None,
        "prompt434_next_prompt_text": None,
        "prompt434_next_command_argv": None,
        "prompt434_next_run_state_path": None,
        "prompt434_next_manifest_path": None,
        "prompt434_next_artifacts_dir": None,
        "prompt434_next_out_dir": None,
        "prompt434_next_job_id": None,
        "prompt434_next_cycle_returncode": None,
        "prompt434_next_cycle_receipt_path": None,
        "prompt434_next_cycle_result_payload": {},
        "prompt434_commit_sha": payload.get("prompt433_commit_sha"),
        "prompt434_tag_name": payload.get("prompt433_tag_name"),
        "prompt434_commit_tag_receipt_path": payload.get(
            "prompt433_commit_tag_receipt_path"
        ),
        "prompt434_commit_tag_success": (
            payload.get("prompt433_approve_commit_tag_execution_success")
            is True
        ),
        "prompt434_targeted_fix_success_rejoin_candidate": False,
        "prompt434_targeted_fix_rejoin_packet": {},
        "prompt434_targeted_fix_returncode": payload.get(
            "prompt433_targeted_fix_returncode"
        ),
        "prompt434_targeted_fix_prompt_path": payload.get(
            "prompt433_targeted_fix_prompt_path"
        ),
        "prompt434_targeted_fix_receipt_path": payload.get(
            "prompt433_targeted_fix_receipt_path"
        ),
        "prompt434_targeted_fix_result_payload": _copy_cycle_payload(
            payload.get("prompt433_targeted_fix_result_payload", {})
        ),
        "prompt434_stop_required": False,
        "prompt434_stop_reason": "",
        "prompt434_execution_error": False,
        "prompt434_execution_error_message": "",
        "prompt434_next_action": "review_prompt433_handoff_execution_adapter",
        "prompt434_codex_direct_invocation_allowed": False,
        "prompt434_subprocess_direct_execution_allowed": False,
        "prompt434_git_direct_mutation_allowed": False,
        "prompt434_commit_tag_direct_execution_allowed": False,
        "prompt434_push_allowed": False,
        "prompt434_pr_allowed": False,
        "prompt434_merge_allowed": False,
        "prompt434_rollback_allowed": False,
        "prompt434_unbounded_loop_allowed": False,
        "prompt434_daemon_mode_allowed": False,
    }

    def _update_surface(
        *,
        status: str,
        ready: bool,
        blocked_reason: str,
        closure_ready: bool,
        selected_closure: str,
        complete_candidate: bool,
        cycle_complete: bool,
        next_action: str,
        stop_required: bool | None = None,
        stop_reason: str | None = None,
        execution_error: bool | None = None,
        execution_error_message: str | None = None,
    ) -> None:
        state.update(
            {
                "prompt434_bounded_complete_autonomous_self_run_closure_status": (
                    status
                ),
                "prompt434_bounded_complete_autonomous_self_run_closure_ready": (
                    ready
                ),
                "prompt434_bounded_complete_autonomous_self_run_closure_blocked_reason": (
                    blocked_reason
                ),
                "prompt434_closure_ready": closure_ready,
                "prompt434_selected_closure": selected_closure,
                "prompt434_complete_autonomous_self_run_candidate": (
                    complete_candidate
                ),
                "prompt434_autonomous_cycle_complete": cycle_complete,
                "prompt434_next_action": next_action,
            }
        )
        if stop_required is not None:
            state["prompt434_stop_required"] = stop_required
        if stop_reason is not None:
            state["prompt434_stop_reason"] = stop_reason
        if execution_error is not None:
            state["prompt434_execution_error"] = execution_error
        if execution_error_message is not None:
            state["prompt434_execution_error_message"] = (
                execution_error_message
            )

    if not closure_requested:
        _update_surface(
            status="ready",
            ready=True,
            blocked_reason="",
            closure_ready=False,
            selected_closure="not_requested",
            complete_candidate=False,
            cycle_complete=False,
            next_action="request_prompt434_autonomous_self_run_closure",
        )
        return state

    if not allow_autonomous_closure:
        _update_surface(
            status="blocked",
            ready=False,
            blocked_reason="autonomous_closure_not_allowed",
            closure_ready=False,
            selected_closure="blocked",
            complete_candidate=False,
            cycle_complete=False,
            next_action="allow_prompt434_autonomous_closure",
        )
        return state

    if not prompt433_result_ready:
        _update_surface(
            status="blocked",
            ready=False,
            blocked_reason="prompt433_handoff_execution_result_not_ready",
            closure_ready=False,
            selected_closure="blocked",
            complete_candidate=False,
            cycle_complete=False,
            next_action="review_prompt433_handoff_execution_adapter",
        )
        return state

    if (
        payload.get("prompt433_execution_error") is True
        or prompt433_status == "execution_error"
    ):
        _update_surface(
            status="execution_error",
            ready=False,
            blocked_reason="prompt433_execution_error",
            closure_ready=False,
            selected_closure="prompt433_execution_error_stop",
            complete_candidate=False,
            cycle_complete=False,
            stop_required=True,
            stop_reason="prompt433_execution_error",
            execution_error=True,
            execution_error_message=_normalize_text(
                payload.get("prompt433_execution_error_message"),
                default="",
            ),
            next_action="review_prompt433_handoff_execution_error",
        )
        return state

    approve_success = (
        selected_execution == "approve_commit_tag"
        and payload.get("prompt433_approve_commit_tag_execution_success")
        is True
    )
    if approve_success and (
        payload.get("prompt433_cycle_closure_after_commit_tag") is True
    ):
        _update_surface(
            status="cycle_closure_ready",
            ready=True,
            blocked_reason="",
            closure_ready=True,
            selected_closure="commit_tag_success_then_stop",
            complete_candidate=True,
            cycle_complete=True,
            stop_required=True,
            stop_reason="cycle_closure_after_commit_tag",
            next_action="complete_prompt434_commit_tag_success_closure",
        )
        return state

    next_cycle_candidate = (
        payload.get("prompt433_next_cycle_continuation_candidate") is True
    )
    if (
        approve_success
        and next_cycle_candidate
        and payload.get("prompt433_cycle_closure_after_commit_tag") is False
    ):
        if not allow_next_cycle:
            _update_surface(
                status="cycle_closure_ready",
                ready=True,
                blocked_reason="",
                closure_ready=True,
                selected_closure="next_cycle_not_allowed_stop",
                complete_candidate=True,
                cycle_complete=True,
                stop_required=True,
                stop_reason="next_cycle_not_allowed",
                next_action="complete_prompt434_next_cycle_not_allowed_stop",
            )
            return state

        if not cycle_capacity_available:
            _update_surface(
                status="cycle_closure_ready",
                ready=True,
                blocked_reason="",
                closure_ready=True,
                selected_closure="bounded_cycle_limit_stop",
                complete_candidate=True,
                cycle_complete=True,
                stop_required=True,
                stop_reason="bounded_cycle_limit_reached",
                next_action="complete_prompt434_bounded_cycle_limit_stop",
            )
            return state

        if not callable(cycle_runner):
            _update_surface(
                status="blocked",
                ready=False,
                blocked_reason="cycle_runner_missing",
                closure_ready=False,
                selected_closure="next_cycle_runner_missing",
                complete_candidate=True,
                cycle_complete=False,
                stop_required=True,
                stop_reason="cycle_runner_missing",
                next_action="provide_prompt434_cycle_runner",
            )
            return state

        state["prompt434_next_cycle_start_attempted"] = True
        state["prompt434_cycle_runner_used"] = True
        try:
            runner_result = cycle_runner(
                next_cycle_number=next_cycle_number,
                current_cycle=effective_current_cycle,
                max_cycles=normalized_max_cycles,
                previous_commit_sha=_copy_cycle_payload(
                    payload.get("prompt433_commit_sha")
                ),
                previous_tag_name=_copy_cycle_payload(
                    payload.get("prompt433_tag_name")
                ),
                previous_commit_tag_receipt_path=_copy_cycle_payload(
                    payload.get("prompt433_commit_tag_receipt_path")
                ),
                run_state_payload=_copy_cycle_payload(payload),
            )
        except Exception as exc:  # noqa: BLE001 - normalize injected runner failures.
            _update_surface(
                status="execution_error",
                ready=False,
                blocked_reason="cycle_runner_exception",
                closure_ready=False,
                selected_closure="next_cycle_execution",
                complete_candidate=True,
                cycle_complete=False,
                stop_required=True,
                stop_reason="cycle_runner_exception",
                execution_error=True,
                execution_error_message=f"cycle_runner_exception: {exc}",
                next_action="review_prompt434_cycle_runner_error",
            )
            return state

        if not isinstance(runner_result, dict):
            _update_surface(
                status="execution_error",
                ready=False,
                blocked_reason="cycle_runner_result_not_mapping",
                closure_ready=False,
                selected_closure="next_cycle_execution",
                complete_candidate=True,
                cycle_complete=False,
                stop_required=True,
                stop_reason="cycle_runner_result_not_mapping",
                execution_error=True,
                execution_error_message="cycle_runner_result_not_mapping",
                next_action="review_prompt434_cycle_runner_error",
            )
            return state

        allowed_result_keys = (
            "status",
            "next_prompt_id",
            "next_prompt_path",
            "next_prompt_text",
            "next_command_argv",
            "next_run_state_path",
            "next_manifest_path",
            "next_artifacts_dir",
            "next_out_dir",
            "next_job_id",
            "returncode",
            "stdout",
            "stderr",
            "receipt_path",
            "result_payload",
            "error_message",
        )
        filtered_result = {
            key: _copy_cycle_payload(runner_result.get(key))
            for key in allowed_result_keys
            if key in runner_result
        }
        next_cycle_returncode = runner_result.get("returncode")
        runner_status = _normalize_text(
            runner_result.get("status"),
            default="",
        )
        next_cycle_started = (
            runner_status != "failed"
            and (
                next_cycle_returncode is None
                or next_cycle_returncode == 0
            )
        )
        next_command_argv = runner_result.get("next_command_argv")
        state.update(
            {
                "prompt434_next_cycle_started": next_cycle_started,
                "prompt434_next_prompt_selected": bool(
                    runner_result.get("next_prompt_id")
                    or runner_result.get("next_prompt_path")
                ),
                "prompt434_next_prompt_generated": bool(
                    runner_result.get("next_prompt_path")
                    or runner_result.get("next_prompt_text")
                ),
                "prompt434_next_command_ready": (
                    isinstance(next_command_argv, list)
                    and bool(next_command_argv)
                ),
                "prompt434_next_prompt_id": _copy_cycle_payload(
                    runner_result.get("next_prompt_id")
                ),
                "prompt434_next_prompt_path": _copy_cycle_payload(
                    runner_result.get("next_prompt_path")
                ),
                "prompt434_next_prompt_text": _copy_cycle_payload(
                    runner_result.get("next_prompt_text")
                ),
                "prompt434_next_command_argv": _copy_cycle_payload(
                    next_command_argv
                ),
                "prompt434_next_run_state_path": _copy_cycle_payload(
                    runner_result.get("next_run_state_path")
                ),
                "prompt434_next_manifest_path": _copy_cycle_payload(
                    runner_result.get("next_manifest_path")
                ),
                "prompt434_next_artifacts_dir": _copy_cycle_payload(
                    runner_result.get("next_artifacts_dir")
                ),
                "prompt434_next_out_dir": _copy_cycle_payload(
                    runner_result.get("next_out_dir")
                ),
                "prompt434_next_job_id": _copy_cycle_payload(
                    runner_result.get("next_job_id")
                ),
                "prompt434_next_cycle_returncode": _copy_cycle_payload(
                    next_cycle_returncode
                ),
                "prompt434_next_cycle_receipt_path": _copy_cycle_payload(
                    runner_result.get("receipt_path")
                ),
                "prompt434_next_cycle_result_payload": (
                    _copy_cycle_payload(runner_result.get("result_payload"))
                    if "result_payload" in runner_result
                    else filtered_result
                ),
            }
        )
        if next_cycle_started:
            _update_surface(
                status="next_cycle_started",
                ready=True,
                blocked_reason="",
                closure_ready=True,
                selected_closure="next_cycle_continuation",
                complete_candidate=True,
                cycle_complete=True,
                stop_required=False,
                stop_reason="",
                next_action="continue_prompt434_bounded_autonomous_self_run",
            )
            return state

        _update_surface(
            status="next_cycle_start_failed",
            ready=False,
            blocked_reason="next_cycle_start_failed",
            closure_ready=False,
            selected_closure="next_cycle_continuation_failed",
            complete_candidate=True,
            cycle_complete=False,
            stop_required=True,
            stop_reason="next_cycle_start_failed",
            next_action="review_prompt434_next_cycle_start_failure",
        )
        return state

    if selected_execution == "approve_commit_tag" and (
        payload.get("prompt433_approve_commit_tag_execution_failed") is True
        or payload.get("prompt433_approve_commit_tag_execution_success")
        is not True
    ):
        _update_surface(
            status="blocked",
            ready=False,
            blocked_reason="commit_tag_execution_failed",
            closure_ready=False,
            selected_closure="commit_tag_failure_stop",
            complete_candidate=False,
            cycle_complete=False,
            stop_required=True,
            stop_reason="commit_tag_execution_failed",
            next_action="review_prompt433_approve_commit_tag_failure",
        )
        return state

    targeted_fix_returncode = payload.get("prompt433_targeted_fix_returncode")
    if (
        selected_execution == "targeted_fix"
        and payload.get("prompt433_targeted_fix_success") is True
        and payload.get("prompt433_targeted_fix_executed") is True
        and targeted_fix_returncode == 0
    ):
        rejoin_packet = {
            "rejoin_type": "targeted_fix_success",
            "source_prompt": "prompt433",
            "current_cycle": effective_current_cycle,
            "max_cycles": normalized_max_cycles,
            "targeted_fix_returncode": targeted_fix_returncode,
            "targeted_fix_prompt_path": payload.get(
                "prompt433_targeted_fix_prompt_path"
            ),
            "targeted_fix_receipt_path": payload.get(
                "prompt433_targeted_fix_receipt_path"
            ),
            "targeted_fix_result_payload": _copy_cycle_payload(
                payload.get("prompt433_targeted_fix_result_payload", {})
            ),
            "next_required_stage": (
                "runtime_result_review_after_targeted_fix"
            ),
            "approve_route_candidate": True,
            "commit_tag_execution_performed": False,
            "next_cycle_started": False,
        }
        state.update(
            {
                "prompt434_targeted_fix_success_rejoin_candidate": True,
                "prompt434_targeted_fix_rejoin_packet": rejoin_packet,
            }
        )
        _update_surface(
            status="targeted_fix_success_rejoin_ready",
            ready=True,
            blocked_reason="",
            closure_ready=True,
            selected_closure="targeted_fix_success_rejoin_review",
            complete_candidate=True,
            cycle_complete=False,
            stop_required=False,
            stop_reason="",
            next_action=(
                "prepare_prompt434_targeted_fix_success_rejoin_approve_route"
            ),
        )
        return state

    if selected_execution == "targeted_fix" and (
        payload.get("prompt433_targeted_fix_failed") is True
        or (
            targeted_fix_returncode is not None
            and targeted_fix_returncode != 0
        )
    ):
        _update_surface(
            status="targeted_fix_failure_stop",
            ready=True,
            blocked_reason="",
            closure_ready=True,
            selected_closure="targeted_fix_failure_stop",
            complete_candidate=True,
            cycle_complete=True,
            stop_required=True,
            stop_reason="targeted_fix_failed",
            next_action="complete_prompt434_targeted_fix_failure_stop",
        )
        return state

    if selected_execution == "targeted_fix" and (
        payload.get("prompt433_targeted_fix_unknown") is True
        or targeted_fix_returncode is None
    ):
        _update_surface(
            status="targeted_fix_unknown_stop",
            ready=True,
            blocked_reason="",
            closure_ready=True,
            selected_closure="targeted_fix_unknown_stop",
            complete_candidate=True,
            cycle_complete=True,
            stop_required=True,
            stop_reason="targeted_fix_unknown",
            next_action="complete_prompt434_targeted_fix_unknown_stop",
        )
        return state

    if (
        selected_execution == "stop"
        and payload.get("prompt433_stop_recorded") is True
    ):
        _update_surface(
            status="stop_closure_ready",
            ready=True,
            blocked_reason="",
            closure_ready=True,
            selected_closure="stop_closure",
            complete_candidate=True,
            cycle_complete=True,
            stop_required=True,
            stop_reason=(
                _normalize_text(payload.get("prompt433_stop_reason"), default="")
                or stop_handoff_reason
            ),
            next_action="complete_prompt434_stop_closure",
        )
        return state

    _update_surface(
        status="blocked",
        ready=False,
        blocked_reason="unclassified_prompt433_result",
        closure_ready=False,
        selected_closure="blocked_unclassified_prompt433_result",
        complete_candidate=False,
        cycle_complete=False,
        stop_required=True,
        stop_reason="unclassified_prompt433_result",
        next_action="review_prompt433_unclassified_result",
    )
    return state


__all__ = [
    "_build_prompt400_relaxed_next_cycle_handoff_bridge_state",
    "_build_prompt401_next_prompt_selection_state",
    "_build_prompt402_generated_prompt_surface_state",
    "_build_prompt403_selected_prompt_dry_run_handoff_state",
    "_build_prompt404_selected_prompt_handoff_review_state",
    "_build_prompt405_selected_prompt_execution_plan_state",
    "_build_prompt406_bounded_loop_observation_state",
    "_build_prompt407_relaxed_loop_completion_receipt_state",
    "_build_prompt408_strict_reenable_plan_state",
    "_build_prompt409_strict_reenable_gate_restoration_packet_state",
    "_build_prompt410_strict_route_restore_state",
    "_build_prompt411_physical_prompt_materialization_plan_state",
    "_build_prompt412_physical_prompt_materialization_boundary_state",
    "_build_prompt413_selected_prompt_execution_adapter_boundary_state",
    "_build_prompt414_execution_result_review_boundary_state",
    "_build_prompt415_guarded_execution_enable_plan_state",
    "_build_prompt416_physical_prompt_materialization_write_state",
    "_build_prompt417_selected_prompt_codex_execution_adapter_state",
    "_build_prompt418_execution_result_review_and_success_route_state",
    "_build_prompt419_approve_commit_tag_and_success_loop_boundary_state",
    "_build_prompt420_success_only_next_cycle_loop_state",
    "_build_prompt421_targeted_fix_route_and_materialization_state",
    "_build_prompt422_targeted_fix_codex_execution_adapter_state",
    "_build_prompt423_targeted_fix_result_review_state",
    "_build_prompt424_bounded_full_autonomous_loop_state",
    "_build_prompt425_local_autonomous_loop_invocation_state",
    "_build_prompt426_bounded_runner_step_executor_state",
    "_build_prompt427_bounded_multi_cycle_loop_runner_state",
    "_build_prompt428_bounded_runtime_command_artifact_contract_state",
    "_build_prompt429_bounded_runtime_launch_readiness_gate_state",
    "_build_prompt430_bounded_runtime_execution_adapter_state",
    "_build_prompt430_dry_run_runtime_command_runner",
    "_build_prompt431_runtime_execution_result_review_route_decision_state",
    "_build_prompt432_route_decision_handoff_packet_state",
    "_build_prompt433_bounded_handoff_execution_adapter_state",
    "_build_prompt434_bounded_complete_autonomous_self_run_closure_state",
    "_build_prompt435_bounded_cycle_runner_adapter",
    "_build_prompt435_runtime_activation_wiring_state",
    "_build_prompt436_runtime_chain_activation_state",
    "_build_prompt437_runtime_command_artifact_wiring_state",
    "_build_prompt438_runtime_result_classification_wiring_state",
    "_build_prompt439_handoff_execution_result_materialization_state",
    "_build_prompt440_live_safe_runtime_command_runner_state",
    "_build_prompt441_bounded_codex_invocation_state",
    "_build_prompt442_codex_post_execution_review_state",
    "_build_prompt443_success_diff_handoff_state",
    "_build_prompt444_targeted_fix_reentry_packet_state",
    "_build_prompt445_targeted_fix_prompt_materialization_state",
    "_build_prompt446_targeted_fix_reentry_request_packet_state",
    "_build_prompt447_targeted_fix_execution_gate_state",
    "_build_prompt448_targeted_fix_execution_allow_candidate_state",
    "_build_prompt449_explicit_targeted_fix_execution_state",
]
