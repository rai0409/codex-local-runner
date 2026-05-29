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
    _BOUNDED_LOCAL_LOOP_CONTROL_KEYS,
    _BOUNDED_LOCAL_LOOP_LOCAL_LOOP_STATE_KEYS,
    _CHATGPT_DIFF_REVIEW_REQUEST_CONTROL_KEYS,
    _CODEX_GATE_CONNECTOR_ENABLEMENT_KEYS,
    _CODEX_LIVE_NETWORK_STOP_SURFACE_KEYS,
    _LOCAL_CODEX_EXECUTION_READINESS_SURFACE_KEYS,
    _MULTI_CYCLE_CONTROLLER_SURFACE_KEYS,
    _NEXT_DEV_SLICE_SURFACE_KEYS,
    _NEXT_LOCAL_CODEX_PROMPT_SURFACE_KEYS,
    _ONE_CYCLE_CONTROLLER_ENABLEMENT_KEYS,
    _ONE_CYCLE_CONTROLLER_SURFACE_KEYS,
    _PROMPT360_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT361_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT362_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT363_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT364_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT369_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT370_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT371_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT372_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT373_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT374_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT375_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT376_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT377_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT378_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT383_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT384_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT385_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT386_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT387_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT388_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT389_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT390_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT398_COMMITTED_PROMPT379_RESULT_SURFACE_KEYS,
    _PROMPT399_RELAXED_OBSERVATION_SURFACE_KEYS,
    _PROMPT400_RELAXED_HANDOFF_SURFACE_KEYS,
    _PROMPT401_NEXT_PROMPT_SELECTION_SURFACE_KEYS,
    _PROMPT402_GENERATED_PROMPT_SURFACE_KEYS,
    _PROMPT403_SELECTED_PROMPT_DRY_RUN_HANDOFF_KEYS,
    _PROMPT404_SELECTED_PROMPT_HANDOFF_REVIEW_KEYS,
    _PROMPT405_SELECTED_PROMPT_EXECUTION_PLAN_KEYS,
    _PROMPT406_BOUNDED_LOOP_OBSERVATION_KEYS,
    _PROMPT407_RELAXED_LOOP_COMPLETION_RECEIPT_KEYS,
    _PROMPT408_STRICT_REENABLE_PLAN_KEYS,
    _PROMPT409_STRICT_REENABLE_GATE_RESTORATION_PACKET_KEYS,
    _PROMPT410_STRICT_ROUTE_RESTORE_KEYS,
    _PROMPT411_PHYSICAL_PROMPT_MATERIALIZATION_PLAN_KEYS,
    _PROMPT412_PHYSICAL_PROMPT_MATERIALIZATION_BOUNDARY_KEYS,
    _PROMPT413_SELECTED_PROMPT_EXECUTION_ADAPTER_BOUNDARY_KEYS,
    _PROMPT414_EXECUTION_RESULT_REVIEW_BOUNDARY_KEYS,
    _PROMPT415_GUARDED_EXECUTION_ENABLE_PLAN_KEYS,
    _PROMPT416_PHYSICAL_PROMPT_MATERIALIZATION_WRITE_KEYS,
    _PROMPT417_SELECTED_PROMPT_CODEX_EXECUTION_ADAPTER_KEYS,
    _PROMPT418_EXECUTION_RESULT_REVIEW_AND_SUCCESS_ROUTE_KEYS,
    _PROMPT419_APPROVE_COMMIT_TAG_AND_SUCCESS_LOOP_KEYS,
    _PROMPT420_SUCCESS_ONLY_NEXT_CYCLE_LOOP_KEYS,
    _PROMPT421_TARGETED_FIX_ROUTE_AND_MATERIALIZATION_KEYS,
    _PROMPT422_TARGETED_FIX_CODEX_EXECUTION_ADAPTER_KEYS,
    _PROMPT423_TARGETED_FIX_RESULT_REVIEW_KEYS,
    _PROMPT424_BOUNDED_FULL_AUTONOMOUS_LOOP_KEYS,
    _PROMPT425_LOCAL_AUTONOMOUS_LOOP_INVOCATION_KEYS,
    _PROMPT426_BOUNDED_RUNNER_STEP_EXECUTOR_KEYS,
    _PROMPT427_BOUNDED_MULTI_CYCLE_LOOP_RUNNER_KEYS,
    _PROMPT428_BOUNDED_RUNTIME_COMMAND_ARTIFACT_CONTRACT_KEYS,
    _PROMPT429_BOUNDED_RUNTIME_LAUNCH_READINESS_GATE_KEYS,
    _PROMPT430_BOUNDED_RUNTIME_EXECUTION_ADAPTER_KEYS,
    _PROMPT431_RUNTIME_EXECUTION_RESULT_REVIEW_ROUTE_DECISION_KEYS,
    _PROMPT432_ROUTE_DECISION_HANDOFF_PACKET_KEYS,
    _PROMPT433_BOUNDED_HANDOFF_EXECUTION_ADAPTER_KEYS,
    _PROMPT434_BOUNDED_COMPLETE_AUTONOMOUS_SELF_RUN_CLOSURE_KEYS,
    _PROMPT435_RUNTIME_ACTIVATION_WIRING_KEYS,
    _PROMPT436_RUNTIME_CHAIN_ACTIVATION_KEYS,
    _PROMPT437_RUNTIME_COMMAND_ARTIFACT_WIRING_KEYS,
    _PROMPT438_RUNTIME_RESULT_CLASSIFICATION_WIRING_KEYS,
    _PROMPT439_HANDOFF_EXECUTION_RESULT_MATERIALIZATION_KEYS,
    _PROMPT441_BOUNDED_CODEX_INVOCATION_KEYS,
    _PROMPT442_CODEX_POST_EXECUTION_REVIEW_KEYS,
    _PROMPT443_SUCCESS_DIFF_HANDOFF_KEYS,
    _PROMPT444_TARGETED_FIX_REENTRY_PACKET_KEYS,
    _PROMPT445_TARGETED_FIX_PROMPT_MATERIALIZATION_KEYS,
    _PROMPT446_TARGETED_FIX_REENTRY_REQUEST_PACKET_KEYS,
    _PROMPT447_TARGETED_FIX_EXECUTION_GATE_KEYS,
    _PROMPT448_TARGETED_FIX_EXECUTION_ALLOW_CANDIDATE_KEYS,
    _PROMPT449_EXPLICIT_TARGETED_FIX_EXECUTION_KEYS,
    _PROMPT450_PROMPT449_RUNTIME_PACKET_EXECUTION_KEYS,
    _PROMPT451_MINIMAL_AUTONOMOUS_COMPLETION_KEYS,
    _PROMPT452_PROMPT451_RUNTIME_EXECUTED_REVIEW_CLOSURE_KEYS,
    _PROMPT453_COMMIT_TAG_READY_EXPLICIT_ALLOW_PACKET_KEYS,
    _PROMPT454_PROMPT452_RUNTIME_EVIDENCE_REPAIR_KEYS,
    _PROMPT455_EXPLICIT_COMMIT_TAG_ALLOW_BRIDGE_KEYS,
    _PROMPT456_COMPRESSED_BOUNDED_COMMIT_TAG_EXECUTION_GATE_KEYS,
    _PROMPT457_COMMIT_TAG_EXECUTION_OBSERVATION_CLEAN_RERUN_CLOSURE_KEYS,
    _PROMPT458_MINIMAL_AUTONOMOUS_COMPLETION_CLOSURE_KEYS,
    _PROMPT459_BOUNDED_LOCAL_COMMIT_TAG_PACKET_EXECUTOR_KEYS,
    _PROMPT460_EXISTING_COMMIT_TAG_EXECUTOR_CONNECTOR_KEYS,
    _PROMPT461_POST_COMMIT_CLEAN_OBSERVED_COMPLETION_CLOSURE_KEYS,
    _PROMPT462_COMPLETED_NEXT_CYCLE_SMOKE_REGRESSION_GUARD_KEYS,
    _PROMPT463_ONE_CYCLE_NEXT_PROMPT_SELECTION_SMOKE_KEYS,
    _PROMPT464_ONE_CYCLE_NEXT_PROMPT_MATERIALIZATION_SMOKE_KEYS,
    _PROMPT465_BOUNDED_ONE_CYCLE_EXECUTION_SMOKE_KEYS,
    _PROMPT466_EXECUTION_RESULT_REVIEW_ROUTE_DECISION_KEYS,
    _PROMPT467_NO_HUMAN_NEXT_CYCLE_CONTINUATION_KEYS,
    _PROMPT468_FULL_NO_HUMAN_LOOP_REGRESSION_RERUN_KEYS,
    _PROMPT469_CHANGED_DIFF_ROUTE_GUARD_KEYS,
    _PROMPT470_BOUNDED_TARGETED_FIX_EXECUTION_KEYS,
    _PROMPT471_COMMIT_TAG_CANDIDATE_EXECUTION_GATE_KEYS,
    _PROMPT472_POST_COMMIT_CLEAN_RERUN_NEXT_CYCLE_KEYS,
    _PROMPT473_CHANGED_DIFF_TARGETED_FIX_BOUNDARY_KEYS,
    _PROMPT474_BOUNDED_TARGETED_FIX_EXECUTION_KEYS,
    _PROMPT475_COMMIT_TAG_EVIDENCE_HANDOFF_GATE_KEYS,
    _PROMPT476_TARGETED_FIX_SUCCESS_LOOP_KEYS,
    _PROMPT477_TWO_CYCLE_READINESS_KEYS,
    _PROMPT478_TWO_CYCLE_LIVE_EXECUTION_KEYS,
    _PROMPT479_DAEMON_LITE_BOUNDARY_KEYS,
    _PROMPT480_WORKSPACE_SAFETY_STOP_KEYS,
    _PROMPT481_DAEMON_LITE_REPEATED_CYCLE_KEYS,
    _PROMPT482_THREE_CYCLE_USABILITY_CONFIRMATION_KEYS,
    _PROMPT483_ROLE_CATALOG_READER_HANDOFF_KEYS,
    _PROMPT484B_ROLE_SELECTION_LAYER_KEYS,
    _PROMPT484C_SELECTED_ROLE_PROMPT_GENERATION_REQUEST_KEYS,
    _PROMPT484_DAEMON_LITE_10_CYCLE_NO_ALLOW_BOUNDARY_KEYS,
    _collect_one_cycle_controller_enablement_overrides_from_retry_context,
)

def _merge_bounded_local_loop_controls_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    policy_snapshot: Mapping[str, Any] | None,
    retry_context: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    policy_payload = dict(policy_snapshot) if isinstance(policy_snapshot, Mapping) else {}
    retry_payload = dict(retry_context) if isinstance(retry_context, Mapping) else {}

    for key in _BOUNDED_LOCAL_LOOP_CONTROL_KEYS:
        if key in policy_payload and policy_payload.get(key) is not None:
            merged[key] = policy_payload.get(key)
    for key in _BOUNDED_LOCAL_LOOP_CONTROL_KEYS:
        if key in retry_payload and retry_payload.get(key) is not None:
            merged[key] = retry_payload.get(key)
    return merged

def _merge_codex_live_network_stop_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    policy_snapshot: Mapping[str, Any] | None,
    retry_context: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    policy_payload = dict(policy_snapshot) if isinstance(policy_snapshot, Mapping) else {}
    retry_payload = dict(retry_context) if isinstance(retry_context, Mapping) else {}

    for key in _CODEX_LIVE_NETWORK_STOP_SURFACE_KEYS:
        if key in policy_payload and policy_payload.get(key) is not None:
            merged[key] = policy_payload.get(key)
    for key in _CODEX_LIVE_NETWORK_STOP_SURFACE_KEYS:
        if key in retry_payload and retry_payload.get(key) is not None:
            merged[key] = retry_payload.get(key)
    return merged

def _merge_codex_gate_connector_enablement_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    policy_snapshot: Mapping[str, Any] | None,
    retry_context: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    policy_payload = dict(policy_snapshot) if isinstance(policy_snapshot, Mapping) else {}
    retry_payload = dict(retry_context) if isinstance(retry_context, Mapping) else {}

    for key in _CODEX_GATE_CONNECTOR_ENABLEMENT_KEYS:
        if key in policy_payload and policy_payload.get(key) is not None:
            merged[key] = policy_payload.get(key)
    for key in _CODEX_GATE_CONNECTOR_ENABLEMENT_KEYS:
        if key in retry_payload and retry_payload.get(key) is not None:
            merged[key] = retry_payload.get(key)
    return merged

def _merge_chatgpt_diff_review_request_controls_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    policy_snapshot: Mapping[str, Any] | None,
    retry_context: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    policy_payload = dict(policy_snapshot) if isinstance(policy_snapshot, Mapping) else {}
    retry_payload = dict(retry_context) if isinstance(retry_context, Mapping) else {}

    for key in _CHATGPT_DIFF_REVIEW_REQUEST_CONTROL_KEYS:
        if key in policy_payload and policy_payload.get(key) is not None:
            merged[key] = policy_payload.get(key)
    for key in _CHATGPT_DIFF_REVIEW_REQUEST_CONTROL_KEYS:
        if key in retry_payload and retry_payload.get(key) is not None:
            merged[key] = retry_payload.get(key)
    return merged

def _merge_one_cycle_controller_enablement_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    policy_snapshot: Mapping[str, Any] | None,
    retry_context: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    policy_payload = dict(policy_snapshot) if isinstance(policy_snapshot, Mapping) else {}
    retry_overrides = _collect_one_cycle_controller_enablement_overrides_from_retry_context(
        retry_context
    )

    for key in _ONE_CYCLE_CONTROLLER_ENABLEMENT_KEYS:
        if key in policy_payload and policy_payload.get(key) is not None:
            merged[key] = policy_payload.get(key)
    for key in _ONE_CYCLE_CONTROLLER_ENABLEMENT_KEYS:
        if key in retry_overrides and retry_overrides.get(key) is not None:
            merged[key] = retry_overrides.get(key)
    return merged

def _merge_bounded_local_loop_local_loop_state_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    policy_snapshot: Mapping[str, Any] | None,
    retry_context: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    policy_payload = dict(policy_snapshot) if isinstance(policy_snapshot, Mapping) else {}
    retry_payload = dict(retry_context) if isinstance(retry_context, Mapping) else {}

    for key in _BOUNDED_LOCAL_LOOP_LOCAL_LOOP_STATE_KEYS:
        if key in policy_payload and policy_payload.get(key) is not None:
            merged[key] = policy_payload.get(key)
    for key in _BOUNDED_LOCAL_LOOP_LOCAL_LOOP_STATE_KEYS:
        if key in retry_payload and retry_payload.get(key) is not None:
            merged[key] = retry_payload.get(key)
    return merged

def _merge_next_dev_slice_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    next_dev_slice_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    surface = dict(next_dev_slice_state) if isinstance(next_dev_slice_state, Mapping) else {}
    for key in _NEXT_DEV_SLICE_SURFACE_KEYS:
        if key in surface and surface.get(key) is not None:
            merged[key] = surface.get(key)
    return merged

def _merge_next_local_codex_prompt_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    next_local_codex_prompt_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    surface = (
        dict(next_local_codex_prompt_state)
        if isinstance(next_local_codex_prompt_state, Mapping)
        else {}
    )
    for key in _NEXT_LOCAL_CODEX_PROMPT_SURFACE_KEYS:
        if key in surface and surface.get(key) is not None:
            merged[key] = surface.get(key)
    return merged

def _merge_local_codex_execution_readiness_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    local_codex_execution_readiness_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    surface = (
        dict(local_codex_execution_readiness_state)
        if isinstance(local_codex_execution_readiness_state, Mapping)
        else {}
    )
    for key in _LOCAL_CODEX_EXECUTION_READINESS_SURFACE_KEYS:
        if key in surface and surface.get(key) is not None:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt360_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt360_gate_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    surface = dict(prompt360_gate_state) if isinstance(prompt360_gate_state, Mapping) else {}
    for key in _PROMPT360_APPROVED_RESTART_SURFACE_KEYS:
        if key in surface and surface.get(key) is not None:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt361_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt361_diff_capture_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    surface = (
        dict(prompt361_diff_capture_state)
        if isinstance(prompt361_diff_capture_state, Mapping)
        else {}
    )
    for key in _PROMPT361_APPROVED_RESTART_SURFACE_KEYS:
        if key in surface and surface.get(key) is not None:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt362_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt362_review_route_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    surface = (
        dict(prompt362_review_route_state)
        if isinstance(prompt362_review_route_state, Mapping)
        else {}
    )
    for key in _PROMPT362_APPROVED_RESTART_SURFACE_KEYS:
        if key in surface and surface.get(key) is not None:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt363_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt363_approve_commit_tag_boundary_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    surface = (
        dict(prompt363_approve_commit_tag_boundary_state)
        if isinstance(prompt363_approve_commit_tag_boundary_state, Mapping)
        else {}
    )
    for key in _PROMPT363_APPROVED_RESTART_SURFACE_KEYS:
        if key in surface and surface.get(key) is not None:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt364_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt364_post_commit_tag_verification_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    surface = (
        dict(prompt364_post_commit_tag_verification_state)
        if isinstance(prompt364_post_commit_tag_verification_state, Mapping)
        else {}
    )
    for key in _PROMPT364_APPROVED_RESTART_SURFACE_KEYS:
        if key in surface and surface.get(key) is not None:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt369_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt369_targeted_fix_route_integration_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    surface = (
        dict(prompt369_targeted_fix_route_integration_state)
        if isinstance(prompt369_targeted_fix_route_integration_state, Mapping)
        else {}
    )
    for key in _PROMPT369_APPROVED_RESTART_SURFACE_KEYS:
        if key in surface and surface.get(key) is not None:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt370_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt370_integrated_autonomous_cycle_runner_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    surface = (
        dict(prompt370_integrated_autonomous_cycle_runner_state)
        if isinstance(prompt370_integrated_autonomous_cycle_runner_state, Mapping)
        else {}
    )
    for key in _PROMPT370_APPROVED_RESTART_SURFACE_KEYS:
        if key in surface and surface.get(key) is not None:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt371_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt371_bounded_one_cycle_execution_wiring_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    surface = (
        dict(prompt371_bounded_one_cycle_execution_wiring_state)
        if isinstance(prompt371_bounded_one_cycle_execution_wiring_state, Mapping)
        else {}
    )
    for key in _PROMPT371_APPROVED_RESTART_SURFACE_KEYS:
        if key in surface and surface.get(key) is not None:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt372_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt372_selected_step_execution_gate_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    surface = (
        dict(prompt372_selected_step_execution_gate_state)
        if isinstance(prompt372_selected_step_execution_gate_state, Mapping)
        else {}
    )
    for key in _PROMPT372_APPROVED_RESTART_SURFACE_KEYS:
        if key in surface and surface.get(key) is not None:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt373_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt373_selected_step_live_codex_execution_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    surface = (
        dict(prompt373_selected_step_live_codex_execution_state)
        if isinstance(prompt373_selected_step_live_codex_execution_state, Mapping)
        else {}
    )
    for key in _PROMPT373_APPROVED_RESTART_SURFACE_KEYS:
        if key in surface and surface.get(key) is not None:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt374_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt374_post_execution_diff_capture_handoff_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    surface = (
        dict(prompt374_post_execution_diff_capture_handoff_state)
        if isinstance(prompt374_post_execution_diff_capture_handoff_state, Mapping)
        else {}
    )
    for key in _PROMPT374_APPROVED_RESTART_SURFACE_KEYS:
        if key in surface and surface.get(key) is not None:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt375_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt375_no_diff_review_route_decision_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    surface = (
        dict(prompt375_no_diff_review_route_decision_state)
        if isinstance(prompt375_no_diff_review_route_decision_state, Mapping)
        else {}
    )
    for key in _PROMPT375_APPROVED_RESTART_SURFACE_KEYS:
        if key in surface and surface.get(key) is not None:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt376_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt376_no_diff_cycle_continuation_handoff_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    surface = (
        dict(prompt376_no_diff_cycle_continuation_handoff_state)
        if isinstance(prompt376_no_diff_cycle_continuation_handoff_state, Mapping)
        else {}
    )
    for key in _PROMPT376_APPROVED_RESTART_SURFACE_KEYS:
        if key in surface and surface.get(key) is not None:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt377_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt377_chatgpt_prompt_generation_request_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    surface = (
        dict(prompt377_chatgpt_prompt_generation_request_state)
        if isinstance(prompt377_chatgpt_prompt_generation_request_state, Mapping)
        else {}
    )
    for key in _PROMPT377_APPROVED_RESTART_SURFACE_KEYS:
        if key in surface and surface.get(key) is not None:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt378_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt378_chatgpt_generated_prompt_intake_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    surface = (
        dict(prompt378_chatgpt_generated_prompt_intake_state)
        if isinstance(prompt378_chatgpt_generated_prompt_intake_state, Mapping)
        else {}
    )
    for key in _PROMPT378_APPROVED_RESTART_SURFACE_KEYS:
        if key in surface and surface.get(key) is not None:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt383_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt383_explicit_approve_commit_tag_execution_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    surface = (
        dict(prompt383_explicit_approve_commit_tag_execution_state)
        if isinstance(prompt383_explicit_approve_commit_tag_execution_state, Mapping)
        else {}
    )
    for key in _PROMPT383_APPROVED_RESTART_SURFACE_KEYS:
        if key in surface and surface.get(key) is not None:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt384_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt384_commit_tag_reconciliation_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    surface = (
        dict(prompt384_commit_tag_reconciliation_state)
        if isinstance(prompt384_commit_tag_reconciliation_state, Mapping)
        else {}
    )
    for key in _PROMPT384_APPROVED_RESTART_SURFACE_KEYS:
        if key in surface and surface.get(key) is not None:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt385_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt385_success_path_next_cycle_handoff_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    surface = (
        dict(prompt385_success_path_next_cycle_handoff_state)
        if isinstance(prompt385_success_path_next_cycle_handoff_state, Mapping)
        else {}
    )
    for key in _PROMPT385_APPROVED_RESTART_SURFACE_KEYS:
        if key in surface and surface.get(key) is not None:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt398_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt398_committed_prompt379_result_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    surface = (
        dict(prompt398_committed_prompt379_result_state)
        if isinstance(prompt398_committed_prompt379_result_state, Mapping)
        else {}
    )
    for key in _PROMPT398_COMMITTED_PROMPT379_RESULT_SURFACE_KEYS:
        if key in surface and surface.get(key) is not None:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt399_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt399_relaxed_observation_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    surface = (
        dict(prompt399_relaxed_observation_state)
        if isinstance(prompt399_relaxed_observation_state, Mapping)
        else {}
    )
    for key in _PROMPT399_RELAXED_OBSERVATION_SURFACE_KEYS:
        if key in surface and surface.get(key) is not None:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt400_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt400_relaxed_handoff_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    surface = (
        dict(prompt400_relaxed_handoff_state)
        if isinstance(prompt400_relaxed_handoff_state, Mapping)
        else {}
    )
    for key in _PROMPT400_RELAXED_HANDOFF_SURFACE_KEYS:
        if key in surface and surface.get(key) is not None:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt401_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt401_next_prompt_selection_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    surface = (
        dict(prompt401_next_prompt_selection_state)
        if isinstance(prompt401_next_prompt_selection_state, Mapping)
        else {}
    )
    for key in _PROMPT401_NEXT_PROMPT_SELECTION_SURFACE_KEYS:
        if key in surface and surface.get(key) is not None:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt402_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt402_generated_prompt_surface_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    surface = (
        dict(prompt402_generated_prompt_surface_state)
        if isinstance(prompt402_generated_prompt_surface_state, Mapping)
        else {}
    )
    for key in _PROMPT402_GENERATED_PROMPT_SURFACE_KEYS:
        if key in surface and surface.get(key) is not None:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt403_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt403_selected_prompt_dry_run_handoff_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    surface = (
        dict(prompt403_selected_prompt_dry_run_handoff_state)
        if isinstance(prompt403_selected_prompt_dry_run_handoff_state, Mapping)
        else {}
    )
    for key in _PROMPT403_SELECTED_PROMPT_DRY_RUN_HANDOFF_KEYS:
        if key in surface and surface.get(key) is not None:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt404_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt404_selected_prompt_handoff_review_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    surface = (
        dict(prompt404_selected_prompt_handoff_review_state)
        if isinstance(prompt404_selected_prompt_handoff_review_state, Mapping)
        else {}
    )
    for key in _PROMPT404_SELECTED_PROMPT_HANDOFF_REVIEW_KEYS:
        if key in surface and surface.get(key) is not None:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt405_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt405_selected_prompt_execution_plan_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    surface = (
        dict(prompt405_selected_prompt_execution_plan_state)
        if isinstance(prompt405_selected_prompt_execution_plan_state, Mapping)
        else {}
    )
    for key in _PROMPT405_SELECTED_PROMPT_EXECUTION_PLAN_KEYS:
        if key in surface and surface.get(key) is not None:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt406_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt406_bounded_loop_observation_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    surface = (
        dict(prompt406_bounded_loop_observation_state)
        if isinstance(prompt406_bounded_loop_observation_state, Mapping)
        else {}
    )
    for key in _PROMPT406_BOUNDED_LOOP_OBSERVATION_KEYS:
        if key in surface and surface.get(key) is not None:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt407_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt407_relaxed_loop_completion_receipt_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    surface = (
        dict(prompt407_relaxed_loop_completion_receipt_state)
        if isinstance(prompt407_relaxed_loop_completion_receipt_state, Mapping)
        else {}
    )
    for key in _PROMPT407_RELAXED_LOOP_COMPLETION_RECEIPT_KEYS:
        if key in surface and surface.get(key) is not None:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt408_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt408_strict_reenable_plan_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    surface = (
        dict(prompt408_strict_reenable_plan_state)
        if isinstance(prompt408_strict_reenable_plan_state, Mapping)
        else {}
    )
    for key in _PROMPT408_STRICT_REENABLE_PLAN_KEYS:
        if key in surface and surface.get(key) is not None:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt409_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt409_strict_reenable_gate_restoration_packet_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt409_strict_reenable_gate_restoration_packet_state)
        if isinstance(prompt409_strict_reenable_gate_restoration_packet_state, Mapping)
        else {}
    )
    for key in _PROMPT409_STRICT_REENABLE_GATE_RESTORATION_PACKET_KEYS:
        if key in surface and surface.get(key) is not None:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt410_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt410_strict_route_restore_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt410_strict_route_restore_state)
        if isinstance(prompt410_strict_route_restore_state, Mapping)
        else {}
    )
    for key in _PROMPT410_STRICT_ROUTE_RESTORE_KEYS:
        if key in surface and surface.get(key) is not None:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt411_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt411_physical_prompt_materialization_plan_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt411_physical_prompt_materialization_plan_state)
        if isinstance(prompt411_physical_prompt_materialization_plan_state, Mapping)
        else {}
    )
    for key in _PROMPT411_PHYSICAL_PROMPT_MATERIALIZATION_PLAN_KEYS:
        if key in surface and surface.get(key) is not None:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt412_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt412_physical_prompt_materialization_boundary_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt412_physical_prompt_materialization_boundary_state)
        if isinstance(prompt412_physical_prompt_materialization_boundary_state, Mapping)
        else {}
    )
    for key in _PROMPT412_PHYSICAL_PROMPT_MATERIALIZATION_BOUNDARY_KEYS:
        if key in surface and surface.get(key) is not None:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt413_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt413_selected_prompt_execution_adapter_boundary_state: Mapping[str, Any]
    | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt413_selected_prompt_execution_adapter_boundary_state)
        if isinstance(
            prompt413_selected_prompt_execution_adapter_boundary_state,
            Mapping,
        )
        else {}
    )
    for key in _PROMPT413_SELECTED_PROMPT_EXECUTION_ADAPTER_BOUNDARY_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt414_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt414_execution_result_review_boundary_state: Mapping[str, Any]
    | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt414_execution_result_review_boundary_state)
        if isinstance(
            prompt414_execution_result_review_boundary_state,
            Mapping,
        )
        else {}
    )
    for key in _PROMPT414_EXECUTION_RESULT_REVIEW_BOUNDARY_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt415_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt415_guarded_execution_enable_plan_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt415_guarded_execution_enable_plan_state)
        if isinstance(prompt415_guarded_execution_enable_plan_state, Mapping)
        else {}
    )
    for key in _PROMPT415_GUARDED_EXECUTION_ENABLE_PLAN_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt416_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt416_physical_prompt_materialization_write_state: Mapping[str, Any]
    | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt416_physical_prompt_materialization_write_state)
        if isinstance(
            prompt416_physical_prompt_materialization_write_state,
            Mapping,
        )
        else {}
    )
    for key in _PROMPT416_PHYSICAL_PROMPT_MATERIALIZATION_WRITE_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt417_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt417_selected_prompt_codex_execution_adapter_state: Mapping[str, Any]
    | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt417_selected_prompt_codex_execution_adapter_state)
        if isinstance(
            prompt417_selected_prompt_codex_execution_adapter_state,
            Mapping,
        )
        else {}
    )
    for key in _PROMPT417_SELECTED_PROMPT_CODEX_EXECUTION_ADAPTER_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt418_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt418_execution_result_review_and_success_route_state: Mapping[str, Any]
    | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt418_execution_result_review_and_success_route_state)
        if isinstance(
            prompt418_execution_result_review_and_success_route_state,
            Mapping,
        )
        else {}
    )
    for key in _PROMPT418_EXECUTION_RESULT_REVIEW_AND_SUCCESS_ROUTE_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt419_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt419_approve_commit_tag_and_success_loop_boundary_state: Mapping[
        str, Any
    ]
    | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt419_approve_commit_tag_and_success_loop_boundary_state)
        if isinstance(
            prompt419_approve_commit_tag_and_success_loop_boundary_state,
            Mapping,
        )
        else {}
    )
    for key in _PROMPT419_APPROVE_COMMIT_TAG_AND_SUCCESS_LOOP_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt420_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt420_success_only_next_cycle_loop_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt420_success_only_next_cycle_loop_state)
        if isinstance(prompt420_success_only_next_cycle_loop_state, Mapping)
        else {}
    )
    for key in _PROMPT420_SUCCESS_ONLY_NEXT_CYCLE_LOOP_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt421_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt421_targeted_fix_route_and_materialization_state: Mapping[str, Any]
    | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt421_targeted_fix_route_and_materialization_state)
        if isinstance(
            prompt421_targeted_fix_route_and_materialization_state,
            Mapping,
        )
        else {}
    )
    for key in _PROMPT421_TARGETED_FIX_ROUTE_AND_MATERIALIZATION_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt422_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt422_targeted_fix_codex_execution_adapter_state: Mapping[str, Any]
    | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt422_targeted_fix_codex_execution_adapter_state)
        if isinstance(
            prompt422_targeted_fix_codex_execution_adapter_state,
            Mapping,
        )
        else {}
    )
    for key in _PROMPT422_TARGETED_FIX_CODEX_EXECUTION_ADAPTER_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt423_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt423_targeted_fix_result_review_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt423_targeted_fix_result_review_state)
        if isinstance(prompt423_targeted_fix_result_review_state, Mapping)
        else {}
    )
    for key in _PROMPT423_TARGETED_FIX_RESULT_REVIEW_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt424_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt424_bounded_full_autonomous_loop_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt424_bounded_full_autonomous_loop_state)
        if isinstance(prompt424_bounded_full_autonomous_loop_state, Mapping)
        else {}
    )
    for key in _PROMPT424_BOUNDED_FULL_AUTONOMOUS_LOOP_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt425_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt425_local_autonomous_loop_invocation_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt425_local_autonomous_loop_invocation_state)
        if isinstance(prompt425_local_autonomous_loop_invocation_state, Mapping)
        else {}
    )
    for key in _PROMPT425_LOCAL_AUTONOMOUS_LOOP_INVOCATION_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt426_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt426_bounded_runner_step_executor_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt426_bounded_runner_step_executor_state)
        if isinstance(prompt426_bounded_runner_step_executor_state, Mapping)
        else {}
    )
    for key in _PROMPT426_BOUNDED_RUNNER_STEP_EXECUTOR_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt427_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt427_bounded_multi_cycle_loop_runner_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt427_bounded_multi_cycle_loop_runner_state)
        if isinstance(prompt427_bounded_multi_cycle_loop_runner_state, Mapping)
        else {}
    )
    for key in _PROMPT427_BOUNDED_MULTI_CYCLE_LOOP_RUNNER_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt428_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt428_bounded_runtime_command_artifact_contract_state: (
        Mapping[str, Any] | None
    ),
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt428_bounded_runtime_command_artifact_contract_state)
        if isinstance(
            prompt428_bounded_runtime_command_artifact_contract_state,
            Mapping,
        )
        else {}
    )
    for key in _PROMPT428_BOUNDED_RUNTIME_COMMAND_ARTIFACT_CONTRACT_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt429_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt429_bounded_runtime_launch_readiness_gate_state: (
        Mapping[str, Any] | None
    ),
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt429_bounded_runtime_launch_readiness_gate_state)
        if isinstance(
            prompt429_bounded_runtime_launch_readiness_gate_state,
            Mapping,
        )
        else {}
    )
    for key in _PROMPT429_BOUNDED_RUNTIME_LAUNCH_READINESS_GATE_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt430_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt430_bounded_runtime_execution_adapter_state: (
        Mapping[str, Any] | None
    ),
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt430_bounded_runtime_execution_adapter_state)
        if isinstance(
            prompt430_bounded_runtime_execution_adapter_state,
            Mapping,
        )
        else {}
    )
    for key in _PROMPT430_BOUNDED_RUNTIME_EXECUTION_ADAPTER_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt431_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt431_runtime_execution_result_review_route_decision_state: (
        Mapping[str, Any] | None
    ),
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt431_runtime_execution_result_review_route_decision_state)
        if isinstance(
            prompt431_runtime_execution_result_review_route_decision_state,
            Mapping,
        )
        else {}
    )
    for key in _PROMPT431_RUNTIME_EXECUTION_RESULT_REVIEW_ROUTE_DECISION_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt432_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt432_route_decision_handoff_packet_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt432_route_decision_handoff_packet_state)
        if isinstance(prompt432_route_decision_handoff_packet_state, Mapping)
        else {}
    )
    for key in _PROMPT432_ROUTE_DECISION_HANDOFF_PACKET_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt433_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt433_bounded_handoff_execution_adapter_state: (
        Mapping[str, Any] | None
    ),
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt433_bounded_handoff_execution_adapter_state)
        if isinstance(
            prompt433_bounded_handoff_execution_adapter_state,
            Mapping,
        )
        else {}
    )
    for key in _PROMPT433_BOUNDED_HANDOFF_EXECUTION_ADAPTER_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt439_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt439_handoff_execution_result_materialization_state: (
        Mapping[str, Any] | None
    ),
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt439_handoff_execution_result_materialization_state)
        if isinstance(
            prompt439_handoff_execution_result_materialization_state,
            Mapping,
        )
        else {}
    )
    for key in _PROMPT439_HANDOFF_EXECUTION_RESULT_MATERIALIZATION_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt434_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt434_bounded_complete_autonomous_self_run_closure_state: (
        Mapping[str, Any] | None
    ),
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt434_bounded_complete_autonomous_self_run_closure_state)
        if isinstance(
            prompt434_bounded_complete_autonomous_self_run_closure_state,
            Mapping,
        )
        else {}
    )
    for key in _PROMPT434_BOUNDED_COMPLETE_AUTONOMOUS_SELF_RUN_CLOSURE_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt435_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt435_runtime_activation_wiring_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt435_runtime_activation_wiring_state)
        if isinstance(prompt435_runtime_activation_wiring_state, Mapping)
        else {}
    )
    for key in _PROMPT435_RUNTIME_ACTIVATION_WIRING_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt436_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt436_runtime_chain_activation_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt436_runtime_chain_activation_state)
        if isinstance(prompt436_runtime_chain_activation_state, Mapping)
        else {}
    )
    for key in _PROMPT436_RUNTIME_CHAIN_ACTIVATION_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt437_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt437_runtime_command_artifact_wiring_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt437_runtime_command_artifact_wiring_state)
        if isinstance(prompt437_runtime_command_artifact_wiring_state, Mapping)
        else {}
    )
    for key in _PROMPT437_RUNTIME_COMMAND_ARTIFACT_WIRING_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt438_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt438_runtime_result_classification_wiring_state: (
        Mapping[str, Any] | None
    ),
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt438_runtime_result_classification_wiring_state)
        if isinstance(prompt438_runtime_result_classification_wiring_state, Mapping)
        else {}
    )
    for key in _PROMPT438_RUNTIME_RESULT_CLASSIFICATION_WIRING_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt441_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt441_bounded_codex_invocation_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt441_bounded_codex_invocation_state)
        if isinstance(prompt441_bounded_codex_invocation_state, Mapping)
        else {}
    )
    for key in _PROMPT441_BOUNDED_CODEX_INVOCATION_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt442_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt442_codex_post_execution_review_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt442_codex_post_execution_review_state)
        if isinstance(prompt442_codex_post_execution_review_state, Mapping)
        else {}
    )
    for key in _PROMPT442_CODEX_POST_EXECUTION_REVIEW_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt443_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt443_success_diff_handoff_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt443_success_diff_handoff_state)
        if isinstance(prompt443_success_diff_handoff_state, Mapping)
        else {}
    )
    for key in _PROMPT443_SUCCESS_DIFF_HANDOFF_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt444_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt444_targeted_fix_reentry_packet_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt444_targeted_fix_reentry_packet_state)
        if isinstance(prompt444_targeted_fix_reentry_packet_state, Mapping)
        else {}
    )
    for key in _PROMPT444_TARGETED_FIX_REENTRY_PACKET_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt445_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt445_targeted_fix_prompt_materialization_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt445_targeted_fix_prompt_materialization_state)
        if isinstance(prompt445_targeted_fix_prompt_materialization_state, Mapping)
        else {}
    )
    for key in _PROMPT445_TARGETED_FIX_PROMPT_MATERIALIZATION_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt446_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt446_targeted_fix_reentry_request_packet_state: (
        Mapping[str, Any] | None
    ),
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt446_targeted_fix_reentry_request_packet_state)
        if isinstance(
            prompt446_targeted_fix_reentry_request_packet_state,
            Mapping,
        )
        else {}
    )
    for key in _PROMPT446_TARGETED_FIX_REENTRY_REQUEST_PACKET_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt447_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt447_targeted_fix_execution_gate_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt447_targeted_fix_execution_gate_state)
        if isinstance(prompt447_targeted_fix_execution_gate_state, Mapping)
        else {}
    )
    for key in _PROMPT447_TARGETED_FIX_EXECUTION_GATE_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt448_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt448_targeted_fix_execution_allow_candidate_state: (
        Mapping[str, Any] | None
    ),
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt448_targeted_fix_execution_allow_candidate_state)
        if isinstance(
            prompt448_targeted_fix_execution_allow_candidate_state,
            Mapping,
        )
        else {}
    )
    for key in _PROMPT448_TARGETED_FIX_EXECUTION_ALLOW_CANDIDATE_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt449_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt449_explicit_targeted_fix_execution_state: (
        Mapping[str, Any] | None
    ),
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt449_explicit_targeted_fix_execution_state)
        if isinstance(
            prompt449_explicit_targeted_fix_execution_state,
            Mapping,
        )
        else {}
    )
    for key in _PROMPT449_EXPLICIT_TARGETED_FIX_EXECUTION_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt450_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt450_prompt449_runtime_packet_execution_state: (
        Mapping[str, Any] | None
    ),
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt450_prompt449_runtime_packet_execution_state)
        if isinstance(
            prompt450_prompt449_runtime_packet_execution_state,
            Mapping,
        )
        else {}
    )
    for key in _PROMPT450_PROMPT449_RUNTIME_PACKET_EXECUTION_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt451_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt451_minimal_autonomous_completion_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt451_minimal_autonomous_completion_state)
        if isinstance(prompt451_minimal_autonomous_completion_state, Mapping)
        else {}
    )
    for key in _PROMPT451_MINIMAL_AUTONOMOUS_COMPLETION_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt452_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt452_prompt451_runtime_executed_review_closure_state: (
        Mapping[str, Any] | None
    ),
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt452_prompt451_runtime_executed_review_closure_state)
        if isinstance(
            prompt452_prompt451_runtime_executed_review_closure_state,
            Mapping,
        )
        else {}
    )
    for key in _PROMPT452_PROMPT451_RUNTIME_EXECUTED_REVIEW_CLOSURE_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt453_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt453_commit_tag_ready_explicit_allow_packet_state: (
        Mapping[str, Any] | None
    ),
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt453_commit_tag_ready_explicit_allow_packet_state)
        if isinstance(
            prompt453_commit_tag_ready_explicit_allow_packet_state,
            Mapping,
        )
        else {}
    )
    for key in _PROMPT453_COMMIT_TAG_READY_EXPLICIT_ALLOW_PACKET_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt454_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt454_prompt452_runtime_evidence_repair_state: (
        Mapping[str, Any] | None
    ),
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt454_prompt452_runtime_evidence_repair_state)
        if isinstance(
            prompt454_prompt452_runtime_evidence_repair_state,
            Mapping,
        )
        else {}
    )
    for key in _PROMPT454_PROMPT452_RUNTIME_EVIDENCE_REPAIR_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt455_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt455_explicit_commit_tag_allow_bridge_state: (
        Mapping[str, Any] | None
    ),
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt455_explicit_commit_tag_allow_bridge_state)
        if isinstance(
            prompt455_explicit_commit_tag_allow_bridge_state,
            Mapping,
        )
        else {}
    )
    for key in _PROMPT455_EXPLICIT_COMMIT_TAG_ALLOW_BRIDGE_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt456_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt456_compressed_bounded_commit_tag_execution_gate_state: (
        Mapping[str, Any] | None
    ),
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt456_compressed_bounded_commit_tag_execution_gate_state)
        if isinstance(
            prompt456_compressed_bounded_commit_tag_execution_gate_state,
            Mapping,
        )
        else {}
    )
    for key in _PROMPT456_COMPRESSED_BOUNDED_COMMIT_TAG_EXECUTION_GATE_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt457_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt457_commit_tag_execution_observation_clean_rerun_closure_state: (
        Mapping[str, Any] | None
    ),
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt457_commit_tag_execution_observation_clean_rerun_closure_state)
        if isinstance(
            prompt457_commit_tag_execution_observation_clean_rerun_closure_state,
            Mapping,
        )
        else {}
    )
    for key in _PROMPT457_COMMIT_TAG_EXECUTION_OBSERVATION_CLEAN_RERUN_CLOSURE_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt458_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt458_minimal_autonomous_completion_closure_state: (
        Mapping[str, Any] | None
    ),
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt458_minimal_autonomous_completion_closure_state)
        if isinstance(
            prompt458_minimal_autonomous_completion_closure_state,
            Mapping,
        )
        else {}
    )
    for key in _PROMPT458_MINIMAL_AUTONOMOUS_COMPLETION_CLOSURE_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt459_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt459_bounded_local_commit_tag_packet_executor_state: (
        Mapping[str, Any] | None
    ),
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt459_bounded_local_commit_tag_packet_executor_state)
        if isinstance(
            prompt459_bounded_local_commit_tag_packet_executor_state,
            Mapping,
        )
        else {}
    )
    for key in _PROMPT459_BOUNDED_LOCAL_COMMIT_TAG_PACKET_EXECUTOR_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt460_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt460_existing_commit_tag_executor_connector_state: (
        Mapping[str, Any] | None
    ),
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt460_existing_commit_tag_executor_connector_state)
        if isinstance(
            prompt460_existing_commit_tag_executor_connector_state,
            Mapping,
        )
        else {}
    )
    for key in _PROMPT460_EXISTING_COMMIT_TAG_EXECUTOR_CONNECTOR_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt461_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt461_post_commit_clean_observed_completion_closure_state: (
        Mapping[str, Any] | None
    ),
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt461_post_commit_clean_observed_completion_closure_state)
        if isinstance(
            prompt461_post_commit_clean_observed_completion_closure_state,
            Mapping,
        )
        else {}
    )
    for key in _PROMPT461_POST_COMMIT_CLEAN_OBSERVED_COMPLETION_CLOSURE_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt462_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt462_completed_next_cycle_smoke_regression_guard_state: (
        Mapping[str, Any] | None
    ),
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt462_completed_next_cycle_smoke_regression_guard_state)
        if isinstance(
            prompt462_completed_next_cycle_smoke_regression_guard_state,
            Mapping,
        )
        else {}
    )
    for key in _PROMPT462_COMPLETED_NEXT_CYCLE_SMOKE_REGRESSION_GUARD_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt463_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt463_one_cycle_next_prompt_selection_smoke_state: (
        Mapping[str, Any] | None
    ),
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt463_one_cycle_next_prompt_selection_smoke_state)
        if isinstance(
            prompt463_one_cycle_next_prompt_selection_smoke_state,
            Mapping,
        )
        else {}
    )
    for key in _PROMPT463_ONE_CYCLE_NEXT_PROMPT_SELECTION_SMOKE_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt464_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt464_one_cycle_next_prompt_materialization_smoke_state: (
        Mapping[str, Any] | None
    ),
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt464_one_cycle_next_prompt_materialization_smoke_state)
        if isinstance(
            prompt464_one_cycle_next_prompt_materialization_smoke_state,
            Mapping,
        )
        else {}
    )
    for key in _PROMPT464_ONE_CYCLE_NEXT_PROMPT_MATERIALIZATION_SMOKE_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt465_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt465_bounded_one_cycle_execution_smoke_state: (
        Mapping[str, Any] | None
    ),
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt465_bounded_one_cycle_execution_smoke_state)
        if isinstance(
            prompt465_bounded_one_cycle_execution_smoke_state,
            Mapping,
        )
        else {}
    )
    for key in _PROMPT465_BOUNDED_ONE_CYCLE_EXECUTION_SMOKE_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt466_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt466_execution_result_review_route_decision_state: (
        Mapping[str, Any] | None
    ),
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt466_execution_result_review_route_decision_state)
        if isinstance(
            prompt466_execution_result_review_route_decision_state,
            Mapping,
        )
        else {}
    )
    for key in _PROMPT466_EXECUTION_RESULT_REVIEW_ROUTE_DECISION_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt467_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt467_no_human_next_cycle_continuation_state: (
        Mapping[str, Any] | None
    ),
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt467_no_human_next_cycle_continuation_state)
        if isinstance(
            prompt467_no_human_next_cycle_continuation_state,
            Mapping,
        )
        else {}
    )
    for key in _PROMPT467_NO_HUMAN_NEXT_CYCLE_CONTINUATION_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt468_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt468_full_no_human_loop_regression_rerun_state: (
        Mapping[str, Any] | None
    ),
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt468_full_no_human_loop_regression_rerun_state)
        if isinstance(
            prompt468_full_no_human_loop_regression_rerun_state,
            Mapping,
        )
        else {}
    )
    for key in _PROMPT468_FULL_NO_HUMAN_LOOP_REGRESSION_RERUN_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt469_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt469_changed_diff_route_guard_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt469_changed_diff_route_guard_state)
        if isinstance(prompt469_changed_diff_route_guard_state, Mapping)
        else {}
    )
    for key in _PROMPT469_CHANGED_DIFF_ROUTE_GUARD_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt470_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt470_bounded_targeted_fix_execution_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt470_bounded_targeted_fix_execution_state)
        if isinstance(prompt470_bounded_targeted_fix_execution_state, Mapping)
        else {}
    )
    for key in _PROMPT470_BOUNDED_TARGETED_FIX_EXECUTION_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt471_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt471_commit_tag_candidate_execution_gate_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt471_commit_tag_candidate_execution_gate_state)
        if isinstance(prompt471_commit_tag_candidate_execution_gate_state, Mapping)
        else {}
    )
    for key in _PROMPT471_COMMIT_TAG_CANDIDATE_EXECUTION_GATE_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt472_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt472_post_commit_clean_rerun_next_cycle_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt472_post_commit_clean_rerun_next_cycle_state)
        if isinstance(prompt472_post_commit_clean_rerun_next_cycle_state, Mapping)
        else {}
    )
    for key in _PROMPT472_POST_COMMIT_CLEAN_RERUN_NEXT_CYCLE_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt473_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt473_changed_diff_targeted_fix_boundary_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt473_changed_diff_targeted_fix_boundary_state)
        if isinstance(prompt473_changed_diff_targeted_fix_boundary_state, Mapping)
        else {}
    )
    for key in _PROMPT473_CHANGED_DIFF_TARGETED_FIX_BOUNDARY_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt474_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt474_bounded_targeted_fix_execution_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt474_bounded_targeted_fix_execution_state)
        if isinstance(prompt474_bounded_targeted_fix_execution_state, Mapping)
        else {}
    )
    for key in _PROMPT474_BOUNDED_TARGETED_FIX_EXECUTION_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt475_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt475_commit_tag_evidence_handoff_gate_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt475_commit_tag_evidence_handoff_gate_state)
        if isinstance(prompt475_commit_tag_evidence_handoff_gate_state, Mapping)
        else {}
    )
    for key in _PROMPT475_COMMIT_TAG_EVIDENCE_HANDOFF_GATE_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt476_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt476_targeted_fix_success_loop_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt476_targeted_fix_success_loop_state)
        if isinstance(prompt476_targeted_fix_success_loop_state, Mapping)
        else {}
    )
    for key in _PROMPT476_TARGETED_FIX_SUCCESS_LOOP_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt477_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt477_two_cycle_readiness_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt477_two_cycle_readiness_state)
        if isinstance(prompt477_two_cycle_readiness_state, Mapping)
        else {}
    )
    for key in _PROMPT477_TWO_CYCLE_READINESS_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt478_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt478_two_cycle_live_execution_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt478_two_cycle_live_execution_state)
        if isinstance(prompt478_two_cycle_live_execution_state, Mapping)
        else {}
    )
    for key in _PROMPT478_TWO_CYCLE_LIVE_EXECUTION_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt479_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt479_daemon_lite_boundary_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt479_daemon_lite_boundary_state)
        if isinstance(prompt479_daemon_lite_boundary_state, Mapping)
        else {}
    )
    for key in _PROMPT479_DAEMON_LITE_BOUNDARY_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt480_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt480_workspace_safety_stop_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt480_workspace_safety_stop_state)
        if isinstance(prompt480_workspace_safety_stop_state, Mapping)
        else {}
    )
    for key in _PROMPT480_WORKSPACE_SAFETY_STOP_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt481_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt481_daemon_lite_repeated_cycle_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt481_daemon_lite_repeated_cycle_state)
        if isinstance(prompt481_daemon_lite_repeated_cycle_state, Mapping)
        else {}
    )
    for key in _PROMPT481_DAEMON_LITE_REPEATED_CYCLE_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt482_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt482_three_cycle_usability_confirmation_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt482_three_cycle_usability_confirmation_state)
        if isinstance(prompt482_three_cycle_usability_confirmation_state, Mapping)
        else {}
    )
    for key in _PROMPT482_THREE_CYCLE_USABILITY_CONFIRMATION_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt483_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt483_role_catalog_reader_handoff_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt483_role_catalog_reader_handoff_state)
        if isinstance(prompt483_role_catalog_reader_handoff_state, Mapping)
        else {}
    )
    for key in _PROMPT483_ROLE_CATALOG_READER_HANDOFF_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt484_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt484_daemon_lite_10_cycle_no_allow_boundary_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt484_daemon_lite_10_cycle_no_allow_boundary_state)
        if isinstance(prompt484_daemon_lite_10_cycle_no_allow_boundary_state, Mapping)
        else {}
    )
    for key in _PROMPT484_DAEMON_LITE_10_CYCLE_NO_ALLOW_BOUNDARY_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt484b_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt484b_role_selection_layer_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt484b_role_selection_layer_state)
        if isinstance(prompt484b_role_selection_layer_state, Mapping)
        else {}
    )
    for key in _PROMPT484B_ROLE_SELECTION_LAYER_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt484c_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt484c_selected_role_prompt_generation_request_state: (
        Mapping[str, Any] | None
    ),
) -> dict[str, Any]:
    merged = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    surface = (
        dict(prompt484c_selected_role_prompt_generation_request_state)
        if isinstance(
            prompt484c_selected_role_prompt_generation_request_state,
            Mapping,
        )
        else {}
    )
    for key in _PROMPT484C_SELECTED_ROLE_PROMPT_GENERATION_REQUEST_KEYS:
        if key in surface:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt386_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt386_success_path_bounded_loop_controller_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    surface = (
        dict(prompt386_success_path_bounded_loop_controller_state)
        if isinstance(prompt386_success_path_bounded_loop_controller_state, Mapping)
        else {}
    )
    for key in _PROMPT386_APPROVED_RESTART_SURFACE_KEYS:
        if key in surface and surface.get(key) is not None:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt387_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt387_success_path_loop_dispatch_bridge_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    surface = (
        dict(prompt387_success_path_loop_dispatch_bridge_state)
        if isinstance(prompt387_success_path_loop_dispatch_bridge_state, Mapping)
        else {}
    )
    for key in _PROMPT387_APPROVED_RESTART_SURFACE_KEYS:
        if key in surface and surface.get(key) is not None:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt388_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt388_local_success_path_autonomous_loop_completion_gate_state: (
        Mapping[str, Any] | None
    ),
) -> dict[str, Any]:
    merged = dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    surface = (
        dict(prompt388_local_success_path_autonomous_loop_completion_gate_state)
        if isinstance(
            prompt388_local_success_path_autonomous_loop_completion_gate_state,
            Mapping,
        )
        else {}
    )
    for key in _PROMPT388_APPROVED_RESTART_SURFACE_KEYS:
        if key in surface and surface.get(key) is not None:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt389_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt389_explicit_bounded_repeated_success_path_loop_execution_state: (
        Mapping[str, Any] | None
    ),
) -> dict[str, Any]:
    merged = dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    surface = (
        dict(prompt389_explicit_bounded_repeated_success_path_loop_execution_state)
        if isinstance(
            prompt389_explicit_bounded_repeated_success_path_loop_execution_state,
            Mapping,
        )
        else {}
    )
    for key in _PROMPT389_APPROVED_RESTART_SURFACE_KEYS:
        if key in surface and surface.get(key) is not None:
            merged[key] = surface.get(key)
    return merged

def _merge_prompt390_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prompt390_prompt389_next_action_reconciliation_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    surface = (
        dict(prompt390_prompt389_next_action_reconciliation_state)
        if isinstance(prompt390_prompt389_next_action_reconciliation_state, Mapping)
        else {}
    )
    for key in _PROMPT390_APPROVED_RESTART_SURFACE_KEYS:
        if key in surface and surface.get(key) is not None:
            merged[key] = surface.get(key)
    return merged

def _merge_one_cycle_controller_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    one_cycle_controller_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    surface = (
        dict(one_cycle_controller_state)
        if isinstance(one_cycle_controller_state, Mapping)
        else {}
    )
    for key in _ONE_CYCLE_CONTROLLER_SURFACE_KEYS:
        if key in surface and surface.get(key) is not None:
            merged[key] = surface.get(key)
    return merged

def _merge_multi_cycle_controller_surface_into_approved_restart_payload(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    multi_cycle_controller_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    surface = (
        dict(multi_cycle_controller_state)
        if isinstance(multi_cycle_controller_state, Mapping)
        else {}
    )
    for key in _MULTI_CYCLE_CONTROLLER_SURFACE_KEYS:
        if key in surface and surface.get(key) is not None:
            merged[key] = surface.get(key)
    return merged


__all__ = [
    "_merge_bounded_local_loop_controls_into_approved_restart_payload",
    "_merge_bounded_local_loop_local_loop_state_into_approved_restart_payload",
    "_merge_chatgpt_diff_review_request_controls_into_approved_restart_payload",
    "_merge_codex_gate_connector_enablement_into_approved_restart_payload",
    "_merge_codex_live_network_stop_surface_into_approved_restart_payload",
    "_merge_local_codex_execution_readiness_surface_into_approved_restart_payload",
    "_merge_multi_cycle_controller_surface_into_approved_restart_payload",
    "_merge_next_dev_slice_surface_into_approved_restart_payload",
    "_merge_next_local_codex_prompt_surface_into_approved_restart_payload",
    "_merge_one_cycle_controller_enablement_into_approved_restart_payload",
    "_merge_one_cycle_controller_surface_into_approved_restart_payload",
    "_merge_prompt360_surface_into_approved_restart_payload",
    "_merge_prompt361_surface_into_approved_restart_payload",
    "_merge_prompt362_surface_into_approved_restart_payload",
    "_merge_prompt363_surface_into_approved_restart_payload",
    "_merge_prompt364_surface_into_approved_restart_payload",
    "_merge_prompt369_surface_into_approved_restart_payload",
    "_merge_prompt370_surface_into_approved_restart_payload",
    "_merge_prompt371_surface_into_approved_restart_payload",
    "_merge_prompt372_surface_into_approved_restart_payload",
    "_merge_prompt373_surface_into_approved_restart_payload",
    "_merge_prompt374_surface_into_approved_restart_payload",
    "_merge_prompt375_surface_into_approved_restart_payload",
    "_merge_prompt376_surface_into_approved_restart_payload",
    "_merge_prompt377_surface_into_approved_restart_payload",
    "_merge_prompt378_surface_into_approved_restart_payload",
    "_merge_prompt383_surface_into_approved_restart_payload",
    "_merge_prompt384_surface_into_approved_restart_payload",
    "_merge_prompt385_surface_into_approved_restart_payload",
    "_merge_prompt386_surface_into_approved_restart_payload",
    "_merge_prompt387_surface_into_approved_restart_payload",
    "_merge_prompt388_surface_into_approved_restart_payload",
    "_merge_prompt389_surface_into_approved_restart_payload",
    "_merge_prompt390_surface_into_approved_restart_payload",
    "_merge_prompt398_surface_into_approved_restart_payload",
    "_merge_prompt399_surface_into_approved_restart_payload",
    "_merge_prompt400_surface_into_approved_restart_payload",
    "_merge_prompt401_surface_into_approved_restart_payload",
    "_merge_prompt402_surface_into_approved_restart_payload",
    "_merge_prompt403_surface_into_approved_restart_payload",
    "_merge_prompt404_surface_into_approved_restart_payload",
    "_merge_prompt405_surface_into_approved_restart_payload",
    "_merge_prompt406_surface_into_approved_restart_payload",
    "_merge_prompt407_surface_into_approved_restart_payload",
    "_merge_prompt408_surface_into_approved_restart_payload",
    "_merge_prompt409_surface_into_approved_restart_payload",
    "_merge_prompt410_surface_into_approved_restart_payload",
    "_merge_prompt411_surface_into_approved_restart_payload",
    "_merge_prompt412_surface_into_approved_restart_payload",
    "_merge_prompt413_surface_into_approved_restart_payload",
    "_merge_prompt414_surface_into_approved_restart_payload",
    "_merge_prompt415_surface_into_approved_restart_payload",
    "_merge_prompt416_surface_into_approved_restart_payload",
    "_merge_prompt417_surface_into_approved_restart_payload",
    "_merge_prompt418_surface_into_approved_restart_payload",
    "_merge_prompt419_surface_into_approved_restart_payload",
    "_merge_prompt420_surface_into_approved_restart_payload",
    "_merge_prompt421_surface_into_approved_restart_payload",
    "_merge_prompt422_surface_into_approved_restart_payload",
    "_merge_prompt423_surface_into_approved_restart_payload",
    "_merge_prompt424_surface_into_approved_restart_payload",
    "_merge_prompt425_surface_into_approved_restart_payload",
    "_merge_prompt426_surface_into_approved_restart_payload",
    "_merge_prompt427_surface_into_approved_restart_payload",
    "_merge_prompt428_surface_into_approved_restart_payload",
    "_merge_prompt429_surface_into_approved_restart_payload",
    "_merge_prompt430_surface_into_approved_restart_payload",
    "_merge_prompt431_surface_into_approved_restart_payload",
    "_merge_prompt432_surface_into_approved_restart_payload",
    "_merge_prompt433_surface_into_approved_restart_payload",
    "_merge_prompt434_surface_into_approved_restart_payload",
    "_merge_prompt435_surface_into_approved_restart_payload",
    "_merge_prompt436_surface_into_approved_restart_payload",
    "_merge_prompt437_surface_into_approved_restart_payload",
    "_merge_prompt438_surface_into_approved_restart_payload",
    "_merge_prompt439_surface_into_approved_restart_payload",
    "_merge_prompt441_surface_into_approved_restart_payload",
    "_merge_prompt442_surface_into_approved_restart_payload",
    "_merge_prompt443_surface_into_approved_restart_payload",
    "_merge_prompt444_surface_into_approved_restart_payload",
    "_merge_prompt445_surface_into_approved_restart_payload",
    "_merge_prompt446_surface_into_approved_restart_payload",
    "_merge_prompt447_surface_into_approved_restart_payload",
    "_merge_prompt448_surface_into_approved_restart_payload",
    "_merge_prompt449_surface_into_approved_restart_payload",
    "_merge_prompt450_surface_into_approved_restart_payload",
    "_merge_prompt451_surface_into_approved_restart_payload",
    "_merge_prompt452_surface_into_approved_restart_payload",
    "_merge_prompt453_surface_into_approved_restart_payload",
    "_merge_prompt454_surface_into_approved_restart_payload",
    "_merge_prompt455_surface_into_approved_restart_payload",
    "_merge_prompt456_surface_into_approved_restart_payload",
    "_merge_prompt457_surface_into_approved_restart_payload",
    "_merge_prompt458_surface_into_approved_restart_payload",
    "_merge_prompt459_surface_into_approved_restart_payload",
    "_merge_prompt460_surface_into_approved_restart_payload",
    "_merge_prompt461_surface_into_approved_restart_payload",
    "_merge_prompt462_surface_into_approved_restart_payload",
    "_merge_prompt463_surface_into_approved_restart_payload",
    "_merge_prompt464_surface_into_approved_restart_payload",
    "_merge_prompt465_surface_into_approved_restart_payload",
    "_merge_prompt466_surface_into_approved_restart_payload",
    "_merge_prompt467_surface_into_approved_restart_payload",
    "_merge_prompt468_surface_into_approved_restart_payload",
    "_merge_prompt469_surface_into_approved_restart_payload",
    "_merge_prompt470_surface_into_approved_restart_payload",
    "_merge_prompt471_surface_into_approved_restart_payload",
    "_merge_prompt472_surface_into_approved_restart_payload",
    "_merge_prompt473_surface_into_approved_restart_payload",
    "_merge_prompt474_surface_into_approved_restart_payload",
    "_merge_prompt475_surface_into_approved_restart_payload",
    "_merge_prompt476_surface_into_approved_restart_payload",
    "_merge_prompt477_surface_into_approved_restart_payload",
    "_merge_prompt478_surface_into_approved_restart_payload",
    "_merge_prompt479_surface_into_approved_restart_payload",
    "_merge_prompt480_surface_into_approved_restart_payload",
    "_merge_prompt481_surface_into_approved_restart_payload",
    "_merge_prompt482_surface_into_approved_restart_payload",
    "_merge_prompt483_surface_into_approved_restart_payload",
    "_merge_prompt484_surface_into_approved_restart_payload",
    "_merge_prompt484b_surface_into_approved_restart_payload",
    "_merge_prompt484c_surface_into_approved_restart_payload",
]
