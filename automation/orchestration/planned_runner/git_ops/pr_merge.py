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
from automation.orchestration.artifact_index import build_contract_artifact_index
from automation.orchestration.approval_transport import build_approval_transport_surface
from automation.orchestration.completion_contract import build_completion_contract_surface
from automation.orchestration.completion_contract import build_completion_run_state_summary_surface
from automation.orchestration.execution_authorization_gate import (
    build_execution_authorization_gate_run_state_summary_surface,
)
from automation.orchestration.execution_authorization_gate import build_execution_authorization_gate_surface
from automation.orchestration.execution_result_contract import (
    build_execution_result_contract_run_state_summary_surface,
)
from automation.orchestration.execution_result_contract import build_execution_result_contract_surface
from automation.orchestration.verification_closure_contract import (
    build_verification_closure_contract_surface,
)
from automation.orchestration.verification_closure_contract import (
    build_verification_closure_run_state_summary_surface,
)
from automation.orchestration.retry_reentry_loop_contract import (
    build_retry_reentry_loop_contract_surface,
)
from automation.orchestration.retry_reentry_loop_contract import (
    build_retry_reentry_loop_run_state_summary_surface,
)
from automation.orchestration.endgame_closure_contract import (
    build_endgame_closure_contract_surface,
)
from automation.orchestration.endgame_closure_contract import (
    build_endgame_closure_run_state_summary_surface,
)
from automation.orchestration.loop_hardening_contract import (
    build_loop_hardening_contract_surface,
)
from automation.orchestration.loop_hardening_contract import (
    build_loop_hardening_run_state_summary_surface,
)
from automation.orchestration.lane_stabilization_contract import (
    build_lane_stabilization_contract_surface,
)
from automation.orchestration.lane_stabilization_contract import (
    build_lane_stabilization_run_state_summary_surface,
)
from automation.orchestration.observability_rollup import (
    build_failure_bucket_rollup_summary_surface,
)
from automation.orchestration.observability_rollup import (
    build_failure_bucket_rollup_surface,
)
from automation.orchestration.observability_rollup import (
    build_fleet_run_rollup_summary_surface,
)
from automation.orchestration.observability_rollup import (
    build_fleet_run_rollup_surface,
)
from automation.orchestration.observability_rollup import (
    build_observability_rollup_contract_summary_surface,
)
from automation.orchestration.observability_rollup import (
    build_observability_rollup_contract_surface,
)
from automation.orchestration.observability_rollup import (
    build_observability_rollup_run_state_summary_surface,
)
from automation.orchestration.failure_bucketing_hardening import (
    build_failure_bucketing_hardening_run_state_summary_surface,
)
from automation.orchestration.failure_bucketing_hardening import (
    build_failure_bucketing_hardening_summary_surface,
)
from automation.orchestration.failure_bucketing_hardening import (
    build_failure_bucketing_hardening_contract_surface,
)
from automation.orchestration.artifact_retention import (
    build_artifact_retention_contract_surface,
)
from automation.orchestration.artifact_retention import (
    build_artifact_retention_run_state_summary_surface,
)
from automation.orchestration.artifact_retention import (
    build_artifact_retention_summary_surface,
)
from automation.orchestration.artifact_retention import (
    build_retention_manifest_summary_surface,
)
from automation.orchestration.artifact_retention import (
    build_retention_manifest_surface,
)
from automation.orchestration.fleet_safety_control import (
    build_fleet_safety_control_contract_surface,
)
from automation.orchestration.fleet_safety_control import (
    build_fleet_safety_control_run_state_summary_surface,
)
from automation.orchestration.fleet_safety_control import (
    build_fleet_safety_control_summary_surface,
)
from automation.orchestration.approval_email_delivery import (
    build_approval_email_delivery_contract_surface,
)
from automation.orchestration.approval_email_delivery import (
    build_approval_email_delivery_run_state_summary_surface,
)
from automation.orchestration.approval_email_delivery import (
    build_approval_email_delivery_summary_surface,
)
from automation.orchestration.approval_runtime_policy import (
    build_approval_runtime_rules_contract_surface,
)
from automation.orchestration.approval_runtime_policy import (
    build_approval_runtime_rules_run_state_summary_surface,
)
from automation.orchestration.approval_runtime_policy import (
    build_approval_runtime_rules_summary_surface,
)
from automation.orchestration.approval_delivery_adapter import (
    build_approval_delivery_handoff_contract_surface,
)
from automation.orchestration.approval_delivery_adapter import (
    build_approval_delivery_handoff_run_state_summary_surface,
)
from automation.orchestration.approval_delivery_adapter import (
    build_approval_delivery_handoff_summary_surface,
)
from automation.orchestration.approval_response_ingest import (
    build_approved_restart_contract_surface,
)
from automation.orchestration.approval_response_ingest import (
    build_approved_restart_run_state_summary_surface,
)
from automation.orchestration.approval_response_ingest import (
    build_approved_restart_summary_surface,
)
from automation.orchestration.approval_response_ingest import (
    build_approval_response_contract_surface,
)
from automation.orchestration.approval_response_ingest import (
    build_approval_response_run_state_summary_surface,
)
from automation.orchestration.approval_response_ingest import (
    build_approval_response_summary_surface,
)
from automation.orchestration.approval_safety import (
    build_approval_safety_contract_surface,
)
from automation.orchestration.approval_safety import (
    build_approval_safety_run_state_summary_surface,
)
from automation.orchestration.approval_safety import (
    build_approval_safety_summary_surface,
)
from automation.orchestration.bounded_execution_bridge import (
    build_bounded_execution_bridge_run_state_summary_surface,
)
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

from automation.orchestration.planned_runner.approved_restart.payload_merge import (
    _merge_bounded_local_loop_controls_into_approved_restart_payload,
    _merge_bounded_local_loop_local_loop_state_into_approved_restart_payload,
    _merge_chatgpt_diff_review_request_controls_into_approved_restart_payload,
    _merge_codex_gate_connector_enablement_into_approved_restart_payload,
    _merge_codex_live_network_stop_surface_into_approved_restart_payload,
    _merge_local_codex_execution_readiness_surface_into_approved_restart_payload,
    _merge_multi_cycle_controller_surface_into_approved_restart_payload,
    _merge_next_dev_slice_surface_into_approved_restart_payload,
    _merge_next_local_codex_prompt_surface_into_approved_restart_payload,
    _merge_one_cycle_controller_enablement_into_approved_restart_payload,
    _merge_one_cycle_controller_surface_into_approved_restart_payload,
    _merge_prompt360_surface_into_approved_restart_payload,
    _merge_prompt361_surface_into_approved_restart_payload,
    _merge_prompt362_surface_into_approved_restart_payload,
    _merge_prompt363_surface_into_approved_restart_payload,
    _merge_prompt364_surface_into_approved_restart_payload,
    _merge_prompt369_surface_into_approved_restart_payload,
    _merge_prompt370_surface_into_approved_restart_payload,
    _merge_prompt371_surface_into_approved_restart_payload,
    _merge_prompt372_surface_into_approved_restart_payload,
    _merge_prompt373_surface_into_approved_restart_payload,
    _merge_prompt374_surface_into_approved_restart_payload,
    _merge_prompt375_surface_into_approved_restart_payload,
    _merge_prompt376_surface_into_approved_restart_payload,
    _merge_prompt377_surface_into_approved_restart_payload,
    _merge_prompt378_surface_into_approved_restart_payload,
    _merge_prompt383_surface_into_approved_restart_payload,
    _merge_prompt384_surface_into_approved_restart_payload,
    _merge_prompt385_surface_into_approved_restart_payload,
    _merge_prompt386_surface_into_approved_restart_payload,
    _merge_prompt387_surface_into_approved_restart_payload,
    _merge_prompt388_surface_into_approved_restart_payload,
    _merge_prompt389_surface_into_approved_restart_payload,
    _merge_prompt390_surface_into_approved_restart_payload,
    _merge_prompt398_surface_into_approved_restart_payload,
    _merge_prompt399_surface_into_approved_restart_payload,
    _merge_prompt400_surface_into_approved_restart_payload,
    _merge_prompt401_surface_into_approved_restart_payload,
    _merge_prompt402_surface_into_approved_restart_payload,
    _merge_prompt403_surface_into_approved_restart_payload,
    _merge_prompt404_surface_into_approved_restart_payload,
    _merge_prompt405_surface_into_approved_restart_payload,
    _merge_prompt406_surface_into_approved_restart_payload,
    _merge_prompt407_surface_into_approved_restart_payload,
    _merge_prompt408_surface_into_approved_restart_payload,
    _merge_prompt409_surface_into_approved_restart_payload,
    _merge_prompt410_surface_into_approved_restart_payload,
    _merge_prompt411_surface_into_approved_restart_payload,
    _merge_prompt412_surface_into_approved_restart_payload,
    _merge_prompt413_surface_into_approved_restart_payload,
    _merge_prompt414_surface_into_approved_restart_payload,
    _merge_prompt415_surface_into_approved_restart_payload,
    _merge_prompt416_surface_into_approved_restart_payload,
    _merge_prompt417_surface_into_approved_restart_payload,
    _merge_prompt418_surface_into_approved_restart_payload,
    _merge_prompt419_surface_into_approved_restart_payload,
    _merge_prompt420_surface_into_approved_restart_payload,
    _merge_prompt421_surface_into_approved_restart_payload,
    _merge_prompt422_surface_into_approved_restart_payload,
    _merge_prompt423_surface_into_approved_restart_payload,
    _merge_prompt424_surface_into_approved_restart_payload,
    _merge_prompt425_surface_into_approved_restart_payload,
    _merge_prompt426_surface_into_approved_restart_payload,
    _merge_prompt427_surface_into_approved_restart_payload,
    _merge_prompt428_surface_into_approved_restart_payload,
    _merge_prompt429_surface_into_approved_restart_payload,
    _merge_prompt430_surface_into_approved_restart_payload,
    _merge_prompt431_surface_into_approved_restart_payload,
    _merge_prompt432_surface_into_approved_restart_payload,
    _merge_prompt433_surface_into_approved_restart_payload,
    _merge_prompt434_surface_into_approved_restart_payload,
    _merge_prompt435_surface_into_approved_restart_payload,
    _merge_prompt436_surface_into_approved_restart_payload,
    _merge_prompt437_surface_into_approved_restart_payload,
    _merge_prompt438_surface_into_approved_restart_payload,
    _merge_prompt439_surface_into_approved_restart_payload,
    _merge_prompt441_surface_into_approved_restart_payload,
    _merge_prompt442_surface_into_approved_restart_payload,
    _merge_prompt443_surface_into_approved_restart_payload,
    _merge_prompt444_surface_into_approved_restart_payload,
    _merge_prompt445_surface_into_approved_restart_payload,
    _merge_prompt446_surface_into_approved_restart_payload,
    _merge_prompt447_surface_into_approved_restart_payload,
    _merge_prompt448_surface_into_approved_restart_payload,
    _merge_prompt449_surface_into_approved_restart_payload,
    _merge_prompt450_surface_into_approved_restart_payload,
    _merge_prompt451_surface_into_approved_restart_payload,
    _merge_prompt452_surface_into_approved_restart_payload,
    _merge_prompt453_surface_into_approved_restart_payload,
    _merge_prompt454_surface_into_approved_restart_payload,
    _merge_prompt455_surface_into_approved_restart_payload,
    _merge_prompt456_surface_into_approved_restart_payload,
    _merge_prompt457_surface_into_approved_restart_payload,
    _merge_prompt458_surface_into_approved_restart_payload,
    _merge_prompt459_surface_into_approved_restart_payload,
    _merge_prompt460_surface_into_approved_restart_payload,
    _merge_prompt461_surface_into_approved_restart_payload,
    _merge_prompt462_surface_into_approved_restart_payload,
    _merge_prompt463_surface_into_approved_restart_payload,
    _merge_prompt464_surface_into_approved_restart_payload,
    _merge_prompt465_surface_into_approved_restart_payload,
    _merge_prompt466_surface_into_approved_restart_payload,
    _merge_prompt467_surface_into_approved_restart_payload,
    _merge_prompt468_surface_into_approved_restart_payload,
    _merge_prompt469_surface_into_approved_restart_payload,
    _merge_prompt470_surface_into_approved_restart_payload,
    _merge_prompt471_surface_into_approved_restart_payload,
    _merge_prompt472_surface_into_approved_restart_payload,
    _merge_prompt473_surface_into_approved_restart_payload,
    _merge_prompt474_surface_into_approved_restart_payload,
    _merge_prompt475_surface_into_approved_restart_payload,
    _merge_prompt476_surface_into_approved_restart_payload,
    _merge_prompt477_surface_into_approved_restart_payload,
    _merge_prompt478_surface_into_approved_restart_payload,
    _merge_prompt479_surface_into_approved_restart_payload,
    _merge_prompt480_surface_into_approved_restart_payload,
    _merge_prompt481_surface_into_approved_restart_payload,
    _merge_prompt482_surface_into_approved_restart_payload,
    _merge_prompt483_surface_into_approved_restart_payload,
    _merge_prompt484_surface_into_approved_restart_payload,
    _merge_prompt484b_surface_into_approved_restart_payload,
    _merge_prompt484c_surface_into_approved_restart_payload,
)
from automation.orchestration.planned_runner.project_browser.constants import (
    _PROJECT_BROWSER_ASSIMILATED_DECISIONS,
    _PROJECT_BROWSER_ASSIMILATED_RISK_LEVELS,
    _PROJECT_BROWSER_ASSIMILATION_RUNTIME_POSTURES,
    _PROJECT_BROWSER_AUTONOMOUS_ACTION_DUPLICATE_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_ACTION_FINGERPRINT_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_ACTION_IDENTITY_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_ACTION_KINDS,
    _PROJECT_BROWSER_AUTONOMOUS_ACTION_RECEIPT_KINDS,
    _PROJECT_BROWSER_AUTONOMOUS_ACTION_RECEIPT_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_CONTINUATION_BLOCK_REASONS,
    _PROJECT_BROWSER_AUTONOMOUS_CONTINUATION_GATE_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_CONTINUATION_NEXT_ACTIONS,
    _PROJECT_BROWSER_AUTONOMOUS_CONTROLLER_ACTIONS,
    _PROJECT_BROWSER_AUTONOMOUS_CONTROLLER_ACTION_SOURCES,
    _PROJECT_BROWSER_AUTONOMOUS_CONTROLLER_RECEIPT_KINDS,
    _PROJECT_BROWSER_AUTONOMOUS_CONTROLLER_RECEIPT_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_CONTROLLER_RUNTIME_POSTURES,
    _PROJECT_BROWSER_AUTONOMOUS_CONTROLLER_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_CONTROLLER_STOP_REASONS,
    _PROJECT_BROWSER_AUTONOMOUS_DEV_ASSIMILATION_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_DEV_NEXT_ACTIONS,
    _PROJECT_BROWSER_AUTONOMOUS_DEV_OUTCOMES,
    _PROJECT_BROWSER_AUTONOMOUS_DEV_RUNTIME_POSTURES,
    _PROJECT_BROWSER_AUTONOMOUS_DEV_STOP_REASONS,
    _PROJECT_BROWSER_AUTONOMOUS_DRAFT_RUNTIME_POSTURES,
    _PROJECT_BROWSER_AUTONOMOUS_DUPLICATE_POLICY_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_DUPLICATE_REASONS,
    _PROJECT_BROWSER_AUTONOMOUS_EXECUTION_BRIDGE_REASONS,
    _PROJECT_BROWSER_AUTONOMOUS_EXECUTION_BRIDGE_RUNTIME_POSTURES,
    _PROJECT_BROWSER_AUTONOMOUS_EXECUTION_BRIDGE_SOURCE_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_EXECUTION_BRIDGE_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_EXECUTION_PERMISSIONS,
    _PROJECT_BROWSER_AUTONOMOUS_GATE_RUNTIME_POSTURES,
    _PROJECT_BROWSER_AUTONOMOUS_LEDGER_RUNTIME_POSTURES,
    _PROJECT_BROWSER_AUTONOMOUS_MANUAL_OVERRIDE_REASONS,
    _PROJECT_BROWSER_AUTONOMOUS_MANUAL_OVERRIDE_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_MD_UPDATE_BLOCK_REASONS,
    _PROJECT_BROWSER_AUTONOMOUS_MD_UPDATE_COMMAND_DRAFT_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_MD_UPDATE_DRAFT_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_MD_UPDATE_KINDS,
    _PROJECT_BROWSER_AUTONOMOUS_NEXT_PROMPT_BLOCK_REASONS,
    _PROJECT_BROWSER_AUTONOMOUS_NEXT_PROMPT_DRAFT_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_NEXT_PROMPT_KINDS,
    _PROJECT_BROWSER_AUTONOMOUS_NEXT_PROMPT_SCOPES,
    _PROJECT_BROWSER_AUTONOMOUS_NEXT_PROMPT_SOURCES,
    _PROJECT_BROWSER_AUTONOMOUS_RETRY_BUDGET_POSTURES,
    _PROJECT_BROWSER_AUTONOMOUS_RUN_LEDGER_ENTRY_KINDS,
    _PROJECT_BROWSER_AUTONOMOUS_RUN_LEDGER_ENTRY_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_RUN_LEDGER_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_SAFETY_RUNTIME_POSTURES,
    _PROJECT_BROWSER_AUTONOMOUS_SAFETY_SWITCH_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_SAFE_STOP_REASONS,
    _PROJECT_BROWSER_AUTONOMOUS_SAFE_STOP_STATUSES,
    _PROJECT_BROWSER_CHATGPT_PAGE_STATUSES,
    _PROJECT_BROWSER_CHAT_ROTATION_NEAR_THRESHOLD,
    _PROJECT_BROWSER_CHAT_ROTATION_TARGET,
    _PROJECT_BROWSER_CHAT_TURN_POSTURES,
    _PROJECT_BROWSER_COMMAND_BLOCK_REASONS,
    _PROJECT_BROWSER_COMMAND_PRECONDITION_VALUES,
    _PROJECT_BROWSER_COMMAND_QUEUE_MODES,
    _PROJECT_BROWSER_COMMAND_QUEUE_STATUSES,
    _PROJECT_BROWSER_COMMAND_RECEIPT_KINDS,
    _PROJECT_BROWSER_COMMAND_RECEIPT_RESULTS,
    _PROJECT_BROWSER_COMMAND_RECEIPT_STATUSES,
    _PROJECT_BROWSER_COMMAND_RUNTIME_POSTURES,
    _PROJECT_BROWSER_COMMAND_SOURCES,
    _PROJECT_BROWSER_COMMAND_TYPES,
    _PROJECT_BROWSER_CONTEXT_STATUSES,
    _PROJECT_BROWSER_CONTINUATION_THRESHOLD,
    _PROJECT_BROWSER_DECISIONS,
    _PROJECT_BROWSER_DOM_PROBE_BLOCK_REASONS,
    _PROJECT_BROWSER_DOM_READINESS_STATUSES,
    _PROJECT_BROWSER_EXECUTION_BLOCK_REASONS,
    _PROJECT_BROWSER_EXECUTION_HANDOFF_KINDS,
    _PROJECT_BROWSER_EXECUTION_HANDOFF_STATUSES,
    _PROJECT_BROWSER_EXECUTION_PREREQUISITE_VALUES,
    _PROJECT_BROWSER_EXECUTION_RECEIPT_PARSE_KINDS,
    _PROJECT_BROWSER_EXECUTION_RECEIPT_PARSE_STATUSES,
    _PROJECT_BROWSER_EXECUTION_RESULT_STATUSES,
    _PROJECT_BROWSER_EXECUTION_RUNTIME_POSTURES,
    _PROJECT_BROWSER_EXECUTOR_BLOCK_REASONS,
    _PROJECT_BROWSER_EXECUTOR_CAPABILITY_POSTURES,
    _PROJECT_BROWSER_EXECUTOR_CONTRACT_VERSION,
    _PROJECT_BROWSER_EXECUTOR_INTERFACE_CONTRACT_VERSION,
    _PROJECT_BROWSER_EXECUTOR_INTERFACE_STATUSES,
    _PROJECT_BROWSER_EXECUTOR_MODES,
    _PROJECT_BROWSER_EXECUTOR_RECEIPT_KINDS,
    _PROJECT_BROWSER_EXECUTOR_RECEIPT_STATUSES,
    _PROJECT_BROWSER_HANDOFF_COMPILE_STATUSES,
    _PROJECT_BROWSER_HANDOFF_PAYLOAD_POSTURES,
    _PROJECT_BROWSER_HANDOFF_RUNTIME_POSTURES,
    _PROJECT_BROWSER_HANDOFF_SECTION_NAMES,
    _PROJECT_BROWSER_HANDOFF_SUMMARY_POSTURES,
    _PROJECT_BROWSER_HANDOFF_TRIGGERS,
    _PROJECT_BROWSER_JSON_REQUIRED_FIELDS,
    _PROJECT_BROWSER_LAUNCH_BLOCK_REASONS,
    _PROJECT_BROWSER_LAUNCH_PREFLIGHT_MODES,
    _PROJECT_BROWSER_LAUNCH_PREFLIGHT_STATUSES,
    _PROJECT_BROWSER_LAUNCH_RECEIPT_KINDS,
    _PROJECT_BROWSER_LAUNCH_RECEIPT_KINDS_RUNTIME,
    _PROJECT_BROWSER_LAUNCH_RECEIPT_STATUSES,
    _PROJECT_BROWSER_LAUNCH_RECEIPT_STATUSES_RUNTIME,
    _PROJECT_BROWSER_LAUNCH_RUNTIME_POSTURES,
    _PROJECT_BROWSER_LAUNCH_STATUSES,
    _PROJECT_BROWSER_LOGIN_INTERRUPTION_STATUSES,
    _PROJECT_BROWSER_LOGIN_PREFLIGHT_POSTURES,
    _PROJECT_BROWSER_NEXT_ACTION_POSTURES,
    _PROJECT_BROWSER_ONE_COMMAND_EXECUTOR_RESULTS,
    _PROJECT_BROWSER_ONE_COMMAND_EXECUTOR_STATUSES,
    _PROJECT_BROWSER_ONE_COMMAND_RECEIPT_KINDS,
    _PROJECT_BROWSER_ONE_COMMAND_RECEIPT_STATUSES,
    _PROJECT_BROWSER_ONE_COMMAND_RUNTIME_POSTURES,
    _PROJECT_BROWSER_ONE_COMMAND_STOP_REASONS,
    _PROJECT_BROWSER_PAGE_OPEN_STATUSES,
    _PROJECT_BROWSER_PLAYWRIGHT_BOUNDARY_STATUSES,
    _PROJECT_BROWSER_PLAYWRIGHT_IMPORT_POSTURES,
    _PROJECT_BROWSER_PROMPT_CONTEXT_LEVELS,
    _PROJECT_BROWSER_PROMPT_FILL_BLOCK_REASONS,
    _PROJECT_BROWSER_PROMPT_FILL_RECEIPT_KINDS,
    _PROJECT_BROWSER_PROMPT_FILL_RECEIPT_STATUSES,
    _PROJECT_BROWSER_PROMPT_FILL_RUNTIME_POSTURES,
    _PROJECT_BROWSER_PROMPT_FILL_SOURCE_STATUSES,
    _PROJECT_BROWSER_PROMPT_FILL_STATUSES,
    _PROJECT_BROWSER_PROMPT_FILL_TARGET_STATUSES,
    _PROJECT_BROWSER_PROMPT_PAYLOAD_STATUSES,
    _PROJECT_BROWSER_PROMPT_PAYLOAD_STYLES,
    _PROJECT_BROWSER_PROMPT_RUNTIME_POSTURES,
    _PROJECT_BROWSER_PROMPT_SECTION_NAMES,
    _PROJECT_BROWSER_PROMPT_SEND_BLOCK_REASONS,
    _PROJECT_BROWSER_PROMPT_SEND_RECEIPT_KINDS,
    _PROJECT_BROWSER_PROMPT_SEND_RECEIPT_STATUSES,
    _PROJECT_BROWSER_PROMPT_SEND_RUNTIME_POSTURES,
    _PROJECT_BROWSER_PROMPT_SEND_STATUSES,
    _PROJECT_BROWSER_PROMPT_SEND_TARGET_STATUSES,
    _PROJECT_BROWSER_PROMPT_TOKEN_POSTURES,
    _PROJECT_BROWSER_PROOF_POSTURES,
    _PROJECT_BROWSER_REASON_CODES,
    _PROJECT_BROWSER_REASON_ORDER,
    _PROJECT_BROWSER_RECOVERY_ACTIONS,
    _PROJECT_BROWSER_RECOVERY_BLOCK_REASONS,
    _PROJECT_BROWSER_RECOVERY_REASONS,
    _PROJECT_BROWSER_RECOVERY_RECEIPT_KINDS,
    _PROJECT_BROWSER_RECOVERY_RECEIPT_STATUSES,
    _PROJECT_BROWSER_RECOVERY_RUNTIME_POSTURES,
    _PROJECT_BROWSER_RECOVERY_STATUSES,
    _PROJECT_BROWSER_RESPONSE_ASSIMILATION_STATUSES,
    _PROJECT_BROWSER_RESPONSE_JSON_DECISION_STATUSES,
    _PROJECT_BROWSER_RESPONSE_JSON_PARSE_STATUSES,
    _PROJECT_BROWSER_RESPONSE_JSON_SCHEMA_STATUSES,
    _PROJECT_BROWSER_RESPONSE_PARSE_BLOCK_REASONS,
    _PROJECT_BROWSER_RESPONSE_PARSE_RUNTIME_POSTURES,
    _PROJECT_BROWSER_RESPONSE_READ_RECEIPT_KINDS,
    _PROJECT_BROWSER_RESPONSE_READ_RECEIPT_STATUSES,
    _PROJECT_BROWSER_RESPONSE_READ_STATUSES,
    _PROJECT_BROWSER_RESPONSE_RUNTIME_POSTURES,
    _PROJECT_BROWSER_RESPONSE_STATUSES,
    _PROJECT_BROWSER_RESPONSE_TEXT_STATUSES,
    _PROJECT_BROWSER_RESPONSE_WAIT_BLOCK_REASONS,
    _PROJECT_BROWSER_RESPONSE_WAIT_STATUSES,
    _PROJECT_BROWSER_RETRY_LIMIT,
    _PROJECT_BROWSER_RISK_LEVELS,
    _PROJECT_BROWSER_RUNTIME_BLOCK_REASONS,
    _PROJECT_BROWSER_SAME_PROMPT_RETRY_POLICIES,
    _PROJECT_BROWSER_SAME_PROMPT_RETRY_REASONS,
    _PROJECT_BROWSER_SCORE_POSTURES,
    _PROJECT_BROWSER_SELECTOR_PROBE_RECEIPT_KINDS,
    _PROJECT_BROWSER_SELECTOR_PROBE_RECEIPT_STATUSES,
    _PROJECT_BROWSER_SELECTOR_PROBE_STATUSES,
    _PROJECT_BROWSER_SELECTOR_REQUIRED_PROBE_TARGETS,
    _PROJECT_BROWSER_SELECTOR_RESOLVER_STATUSES,
    _PROJECT_BROWSER_SELECTOR_RUNTIME_POSTURES,
    _PROJECT_BROWSER_SELECTOR_TARGETS,
    _PROJECT_BROWSER_SELECTOR_TARGET_STATUSES,
    _PROJECT_BROWSER_SESSION_CONFIG_STATUSES,
    _PROJECT_BROWSER_SESSION_MODES,
    _PROJECT_BROWSER_TASK_ENVELOPE_STATUSES,
    _PROJECT_BROWSER_TASK_SCHEMA_REF,
    _PROJECT_BROWSER_TASK_STATUSES,
    _PROJECT_BROWSER_TASK_TYPES,
    _PROJECT_BROWSER_UI_FAILURE_STATUSES,
    _PROJECT_BROWSER_UI_HANDOFF_DEPENDENCY_POSTURES,
    _PROJECT_BROWSER_UI_READINESS_STATUSES,
    _PROJECT_BROWSER_UI_RECOVERY_ACTIONS,
    _PROJECT_BROWSER_UI_RECOVERY_CANDIDATES,
    _PROJECT_BROWSER_UI_RECOVERY_DECISION_STATUSES,
    _PROJECT_BROWSER_UI_RECOVERY_REASONS,
    _PROJECT_BROWSER_UI_RECOVERY_RUNTIME_POSTURES,
    _PROJECT_BROWSER_UI_RETRY_COUNT_POSTURES,
)
from automation.orchestration.planned_runner.utils import (
    _APPROVAL_SKIP_GATE_STATUSES,
    _APPROVE_COMMIT_TAG_ARTIFACT_RECONCILIATION_RECEIPT_PATH,
    _APPROVE_COMMIT_TAG_EXECUTION_COMMIT_MESSAGE,
    _APPROVE_COMMIT_TAG_EXECUTION_RECEIPT_PATH,
    _APPROVE_COMMIT_TAG_EXECUTION_REPO_PATH,
    _APPROVE_COMMIT_TAG_EXECUTION_TAG_NAME,
    _APPROVE_COMMIT_TAG_STALE_COMMIT_MESSAGE,
    _APPROVE_COMMIT_TAG_STALE_IDENTITY,
    _APPROVE_COMMIT_TAG_STALE_TAG_NAME,
    _AUTONOMY_BROWSER_ORCHESTRATOR_SPEC_REF,
    _BOUNDED_LOCAL_AUTONOMOUS_LOOP_DEFAULT_CURRENT_CYCLE_COUNT,
    _BOUNDED_LOCAL_AUTONOMOUS_LOOP_DEFAULT_MAX_CYCLE_COUNT,
    _BOUNDED_LOCAL_AUTONOMOUS_LOOP_EXPECTED_HEAD_TAG,
    _BOUNDED_LOCAL_LOOP_CONTROL_KEYS,
    _BOUNDED_LOCAL_LOOP_LOCAL_LOOP_STATE_KEYS,
    _CHATGPT_DIFF_REVIEW_REQUEST_CONTROL_KEYS,
    _CODEX_GATE_CONNECTOR_ENABLEMENT_KEYS,
    _CODEX_LIVE_NETWORK_STOP_SURFACE_KEYS,
    _EXPLICIT_COMMIT_TAG_ALLOW_KEYS,
    _IMPLEMENTATION_PROMPT_STATUSES,
    _LOCAL_AUTONOMOUS_CONTINUATION_DECISION_PATH,
    _LOCAL_AUTONOMOUS_CONTINUATION_DECISION_SCHEMA_VERSION,
    _LOCAL_AUTONOMOUS_CONTINUATION_RECEIPT_PATH,
    _LOCAL_AUTONOMOUS_CONTINUATION_RECEIPT_SCHEMA_VERSION,
    _LOCAL_AUTONOMOUS_CONTINUATION_STATE_PATH,
    _LOCAL_AUTONOMOUS_CONTINUATION_STATE_SCHEMA_VERSION,
    _LOCAL_AUTONOMOUS_CYCLE_V2_CURRENT_CYCLE,
    _LOCAL_AUTONOMOUS_CYCLE_V2_DECISION_PATH,
    _LOCAL_AUTONOMOUS_CYCLE_V2_MAX_CYCLES,
    _LOCAL_AUTONOMOUS_CYCLE_V2_RECEIPT_PATH,
    _LOCAL_AUTONOMOUS_CYCLE_V2_SCHEMA_VERSION,
    _LOCAL_AUTONOMOUS_CYCLE_V2_STATE_PATH,
    _LOCAL_AUTONOMOUS_LOOP_COMPLETION_SUMMARY_PATH,
    _LOCAL_AUTONOMOUS_LOOP_COMPLETION_SUMMARY_SCHEMA_VERSION,
    _LOCAL_AUTONOMOUS_NEXT_CYCLE_SELECTION_PATH,
    _LOCAL_AUTONOMOUS_NEXT_CYCLE_SELECTION_SCHEMA_VERSION,
    _LOCAL_BOUNDED_APPROVE_COMMIT_TAG_COMMIT_MESSAGE,
    _LOCAL_BOUNDED_APPROVE_COMMIT_TAG_EXECUTION_RECEIPT_PATH,
    _LOCAL_BOUNDED_APPROVE_COMMIT_TAG_EXECUTION_RECEIPT_SCHEMA_VERSION,
    _LOCAL_BOUNDED_APPROVE_COMMIT_TAG_EXECUTION_RESULT_PATH,
    _LOCAL_BOUNDED_APPROVE_COMMIT_TAG_EXECUTION_RESULT_SCHEMA_VERSION,
    _LOCAL_BOUNDED_APPROVE_COMMIT_TAG_GATE_STATE_PATH,
    _LOCAL_BOUNDED_APPROVE_COMMIT_TAG_GATE_STATE_SCHEMA_VERSION,
    _LOCAL_BOUNDED_APPROVE_COMMIT_TAG_PLAN_PATH,
    _LOCAL_BOUNDED_APPROVE_COMMIT_TAG_PLAN_SCHEMA_VERSION,
    _LOCAL_BOUNDED_APPROVE_COMMIT_TAG_STDIO_MAX_CHARS,
    _LOCAL_BOUNDED_APPROVE_COMMIT_TAG_TAG_NAME,
    _LOCAL_CODEX_EXECUTION_READINESS_BANNED_PROMPT_FRAGMENTS,
    _LOCAL_CODEX_EXECUTION_READINESS_DISALLOW_CONTEXT_FRAGMENTS,
    _LOCAL_CODEX_EXECUTION_READINESS_SURFACE_KEYS,
    _LOCAL_CODEX_EXEC_PLAN_COMMAND,
    _LOCAL_CODEX_ONE_SHOT_EXECUTION_COMMAND,
    _LOCAL_CODEX_ONE_SHOT_EXECUTION_HANDOFF_PATH,
    _LOCAL_CODEX_ONE_SHOT_EXECUTION_OUTPUT_MAX_CHARS,
    _LOCAL_CODEX_ONE_SHOT_EXECUTION_RECEIPT_PATH,
    _LOCAL_CODEX_ONE_SHOT_EXECUTION_RECEIPT_V2_PATH,
    _LOCAL_CODEX_ONE_SHOT_EXECUTION_RESULT_PATH,
    _LOCAL_CODEX_ONE_SHOT_EXECUTION_SCHEMA_VERSION,
    _LOCAL_CODEX_ONE_SHOT_EXECUTION_STDERR_PATH,
    _LOCAL_CODEX_ONE_SHOT_EXECUTION_STDOUT_PATH,
    _LOCAL_CODEX_ONE_SHOT_HANDOFF_SCHEMA_VERSION,
    _LOCAL_CODEX_ONE_SHOT_PROMPT_PATH,
    _LOCAL_CONTRACT_FIX_CYCLE_COORDINATION_DECISION_PATH,
    _LOCAL_CONTRACT_FIX_CYCLE_COORDINATION_DECISION_SCHEMA_VERSION,
    _LOCAL_CONTRACT_FIX_CYCLE_COORDINATION_RECEIPT_PATH,
    _LOCAL_CONTRACT_FIX_CYCLE_COORDINATION_RECEIPT_SCHEMA_VERSION,
    _LOCAL_CONTRACT_FIX_CYCLE_COORDINATION_STATE_PATH,
    _LOCAL_CONTRACT_FIX_CYCLE_COORDINATION_STATE_SCHEMA_VERSION,
    _LOCAL_CONTRACT_FIX_CYCLE_EXECUTION_HANDOFF_PATH,
    _LOCAL_CONTRACT_FIX_CYCLE_EXECUTION_HANDOFF_SCHEMA_VERSION,
    _LOCAL_DAEMON_LITE_WRAPPER_DECISION_PATH,
    _LOCAL_DAEMON_LITE_WRAPPER_DECISION_SCHEMA_VERSION,
    _LOCAL_DAEMON_LITE_WRAPPER_PLAN_PATH,
    _LOCAL_DAEMON_LITE_WRAPPER_PLAN_SCHEMA_VERSION,
    _LOCAL_DAEMON_LITE_WRAPPER_RECEIPT_PATH,
    _LOCAL_DAEMON_LITE_WRAPPER_RECEIPT_SCHEMA_VERSION,
    _LOCAL_DAEMON_LITE_WRAPPER_STATE_PATH,
    _LOCAL_DAEMON_LITE_WRAPPER_STATE_SCHEMA_VERSION,
    _LOCAL_END_TO_END_CONTROLLER_EXPECTED_BRANCH,
    _LOCAL_END_TO_END_CONTROLLER_EXPECTED_HEAD_TAG,
    _LOCAL_END_TO_END_DRY_RUN_EXPECTED_HEAD_TAG,
    _LOCAL_END_TO_END_ONE_SHOT_EXPECTED_HEAD_TAG,
    _LOCAL_END_TO_END_ONE_SHOT_STEP_SELECTION_PATH,
    _LOCAL_NEXT_CYCLE_REENTRY_DECISION_PATH,
    _LOCAL_NEXT_CYCLE_REENTRY_DECISION_SCHEMA_VERSION,
    _LOCAL_ONLY_AUTONOMOUS_LOOP_CLOSURE_DECISION_PATH,
    _LOCAL_ONLY_AUTONOMOUS_LOOP_CLOSURE_RECEIPT_PATH,
    _LOCAL_ONLY_AUTONOMOUS_LOOP_CLOSURE_STATE_PATH,
    _LOCAL_POST_CODEX_DIFF_CAPTURE_PATH,
    _LOCAL_POST_CODEX_DIFF_CAPTURE_RECEIPT_PATH,
    _LOCAL_POST_CODEX_DIFF_CAPTURE_SCHEMA_VERSION,
    _LOCAL_POST_CODEX_EXECUTION_OUTCOME_PATH,
    _LOCAL_POST_CODEX_EXECUTION_OUTCOME_SCHEMA_VERSION,
    _LOCAL_POST_CODEX_ROUTE_DECISION_PATH,
    _LOCAL_POST_CODEX_ROUTE_DECISION_SCHEMA_VERSION,
    _LOCAL_POST_COMMIT_CYCLE_CLOSURE_DECISION_PATH,
    _LOCAL_POST_COMMIT_CYCLE_CLOSURE_DECISION_SCHEMA_VERSION,
    _LOCAL_POST_COMMIT_CYCLE_CLOSURE_RECEIPT_PATH,
    _LOCAL_POST_COMMIT_CYCLE_CLOSURE_RECEIPT_SCHEMA_VERSION,
    _LOCAL_POST_COMMIT_CYCLE_CLOSURE_STATE_PATH,
    _LOCAL_POST_COMMIT_CYCLE_CLOSURE_STATE_SCHEMA_VERSION,
    _LOCAL_POST_TARGETED_CONTRACT_FIX_DIFF_CAPTURE_PATH,
    _LOCAL_POST_TARGETED_CONTRACT_FIX_DIFF_CAPTURE_SCHEMA_VERSION,
    _LOCAL_POST_TARGETED_CONTRACT_FIX_EXECUTION_OUTCOME_PATH,
    _LOCAL_POST_TARGETED_CONTRACT_FIX_EXECUTION_OUTCOME_SCHEMA_VERSION,
    _LOCAL_POST_TARGETED_CONTRACT_FIX_REVIEW_RECEIPT_PATH,
    _LOCAL_POST_TARGETED_CONTRACT_FIX_REVIEW_RECEIPT_SCHEMA_VERSION,
    _LOCAL_POST_TARGETED_CONTRACT_FIX_ROUTE_DECISION_PATH,
    _LOCAL_POST_TARGETED_CONTRACT_FIX_ROUTE_DECISION_SCHEMA_VERSION,
    _LOCAL_POST_TARGETED_CONTRACT_FIX_STDIO_MAX_CHARS,
    _LOCAL_TARGETED_CONTRACT_FIX_EXECUTION_COMMAND,
    _LOCAL_TARGETED_CONTRACT_FIX_EXECUTION_RECEIPT_PATH,
    _LOCAL_TARGETED_CONTRACT_FIX_EXECUTION_RECEIPT_SCHEMA_VERSION,
    _LOCAL_TARGETED_CONTRACT_FIX_EXECUTION_RESULT_PATH,
    _LOCAL_TARGETED_CONTRACT_FIX_EXECUTION_RESULT_SCHEMA_VERSION,
    _LOCAL_TARGETED_CONTRACT_FIX_EXECUTION_STATE_PATH,
    _LOCAL_TARGETED_CONTRACT_FIX_EXECUTION_STATE_SCHEMA_VERSION,
    _LOCAL_TARGETED_CONTRACT_FIX_EXECUTION_STDERR_PATH,
    _LOCAL_TARGETED_CONTRACT_FIX_EXECUTION_STDOUT_PATH,
    _LOCAL_TARGETED_CONTRACT_FIX_EXECUTION_TIMEOUT_SECONDS,
    _LOCAL_TARGETED_CONTRACT_FIX_PROMPT_PATH,
    _LOCAL_TARGETED_CONTRACT_FIX_PROMPT_PLAN_PATH,
    _LOCAL_TARGETED_CONTRACT_FIX_PROMPT_PLAN_SCHEMA_VERSION,
    _LOCAL_TARGETED_CONTRACT_FIX_PROMPT_RECEIPT_PATH,
    _LOCAL_TARGETED_CONTRACT_FIX_PROMPT_RECEIPT_SCHEMA_VERSION,
    _LOCAL_TARGETED_CONTRACT_FIX_ROUTE_INTAKE_PATH,
    _LOCAL_TARGETED_CONTRACT_FIX_ROUTE_INTAKE_SCHEMA_VERSION,
    _LONG_RUNNING_STABILITY_STATUSES,
    _MULTI_CYCLE_CONTROLLER_SURFACE_KEYS,
    _NEXT_DEV_SLICE_SURFACE_KEYS,
    _NEXT_LOCAL_CODEX_PROMPT_SURFACE_KEYS,
    _ONE_CYCLE_CONTROLLER_ENABLEMENT_KEYS,
    _ONE_CYCLE_CONTROLLER_EXEC_PLAN_APPROVAL_POLICY_ALLOWED_FRAGMENTS,
    _ONE_CYCLE_CONTROLLER_EXEC_PLAN_BANNED_FRAGMENTS,
    _ONE_CYCLE_CONTROLLER_EXEC_PLAN_REQUIRED_FRAGMENTS,
    _ONE_CYCLE_CONTROLLER_SURFACE_KEYS,
    _PROJECT_APPROVAL_REPLY_REQUIRED_POSTURES,
    _PROJECT_EXTERNAL_BOUNDARY_POSTURES,
    _PROJECT_EXTERNAL_BOUNDARY_STATUSES,
    _PROJECT_EXTERNAL_DEPENDENCY_POSTURES,
    _PROJECT_PR_QUEUE_STATUSES,
    _PROMPT360_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT361_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT362_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT363_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT364_ALLOWED_IMPLEMENTATION_FILES,
    _PROMPT364_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT364_EXPECTED_HEAD_TAG_NAME,
    _PROMPT364_EXPECTED_TAG_NAME,
    _PROMPT364_IMPLEMENTATION_IN_PROGRESS_HEAD_TAG_NAME,
    _PROMPT364_LEGACY_HEAD_TAG_NAME,
    _PROMPT364_PREVIOUS_EXPECTED_TAG_NAME,
    _PROMPT365_DRY_RUN_BLOCKED_NEXT_ACTION,
    _PROMPT365_DRY_RUN_BLOCKED_REASON,
    _PROMPT365_DRY_RUN_MUTATION_DETECTED_NEXT_ACTION,
    _PROMPT365_DRY_RUN_MUTATION_DETECTED_REASON,
    _PROMPT366_ALLOWED_HEAD_TAG_NAMES,
    _PROMPT366_EXPECTED_HEAD_TAG_NAME,
    _PROMPT366_IMPLEMENTATION_FIX1_HEAD_TAG_NAME,
    _PROMPT366_PREVIOUS_SOURCE_TAG_NAME,
    _PROMPT366_SCHEMA_VERSION,
    _PROMPT367_IMPLEMENTATION_COMMIT_MESSAGE,
    _PROMPT367_IMPLEMENTATION_TAG_NAME,
    _PROMPT367_IMPLEMENTATION_TRACKED_FILES,
    _PROMPT367_SCHEMA_VERSION,
    _PROMPT368_DEFAULT_SELECTED_PROMPT_CONTRACT_FILENAME,
    _PROMPT368_IMPLEMENTATION_TAG_NAME,
    _PROMPT368_IMPLEMENTATION_TRACKED_FILES,
    _PROMPT368_SCHEMA_VERSION,
    _PROMPT369_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT369_SCHEMA_VERSION,
    _PROMPT370_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT370_SCHEMA_VERSION,
    _PROMPT371_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT371_SCHEMA_VERSION,
    _PROMPT372_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT372_SCHEMA_VERSION,
    _PROMPT373_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT373_SCHEMA_VERSION,
    _PROMPT374_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT375_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT376_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT377_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT378_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT379_SCHEMA_VERSION,
    _PROMPT380_SCHEMA_VERSION,
    _PROMPT381_SCHEMA_VERSION,
    _PROMPT382_COMMIT_MESSAGE,
    _PROMPT382_SCHEMA_VERSION,
    _PROMPT382_TAG_NAME,
    _PROMPT383_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT383_SCHEMA_VERSION,
    _PROMPT384_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT384_SCHEMA_VERSION,
    _PROMPT385_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT385_GENERATED_PROMPT_EXPECTED_FLAG,
    _PROMPT385_GENERATED_PROMPT_EXPECTED_PATH_FIELD,
    _PROMPT385_GENERATED_PROMPT_INTAKE_METHOD,
    _PROMPT385_NEXT_PROMPT_GENERATION_OWNER,
    _PROMPT385_SCHEMA_VERSION,
    _PROMPT386_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT386_MAX_CYCLES_ALLOWED,
    _PROMPT386_ORDERED_LOOP_STAGES,
    _PROMPT386_REQUIRED_NEXT_PROMPT,
    _PROMPT386_REQUIRED_NEXT_PROMPT_GOAL,
    _PROMPT386_REQUIRED_NEXT_PROMPT_ID,
    _PROMPT386_SCHEMA_VERSION,
    _PROMPT387_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT387_EXPLICIT_ENABLE_FLAG,
    _PROMPT387_GENERATED_PROMPT_PATH_FIELD,
    _PROMPT387_MAX_CYCLES_ALLOWED,
    _PROMPT387_ORDERED_LOOP_STAGES,
    _PROMPT387_REQUIRED_NEXT_PROMPT,
    _PROMPT387_REQUIRED_NEXT_PROMPT_GOAL,
    _PROMPT387_REQUIRED_NEXT_PROMPT_ID,
    _PROMPT387_SCHEMA_VERSION,
    _PROMPT388_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT388_GENERATED_PROMPT_PATH_FIELD,
    _PROMPT388_MAX_CYCLES_ALLOWED,
    _PROMPT388_ORDERED_LOOP_STAGES,
    _PROMPT388_REQUIRED_NEXT_PROMPT,
    _PROMPT388_REQUIRED_NEXT_PROMPT_GOAL,
    _PROMPT388_REQUIRED_NEXT_PROMPT_ID,
    _PROMPT388_SCHEMA_VERSION,
    _PROMPT389_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT389_DEFAULT_MAX_CYCLES,
    _PROMPT389_EXPLICIT_ENABLE_FLAG,
    _PROMPT389_GENERATED_PROMPT_PATH_FIELD,
    _PROMPT389_ORDERED_LOOP_STAGES,
    _PROMPT389_SAFE_UPPER_BOUND_MAX_CYCLES,
    _PROMPT389_SCHEMA_VERSION,
    _PROMPT390_APPROVED_RESTART_SURFACE_KEYS,
    _PROMPT390_SCHEMA_VERSION,
    _PROMPT397C_PRE_PROMPT379_MUTATION_SUPPRESSION_REASON,
    _PROMPT397C_SUPPRESSION_SCOPE,
    _PROMPT398_COMMITTED_PROMPT379_EXPECTED_HEAD_SUBJECT_FRAGMENT,
    _PROMPT398_COMMITTED_PROMPT379_EXPECTED_TAG,
    _PROMPT398_COMMITTED_PROMPT379_RESULT_SURFACE_KEYS,
    _PROMPT398_SCHEMA_VERSION,
    _PROMPT399_RELAXED_OBSERVATION_SURFACE_KEYS,
    _PROMPT399_SCHEMA_VERSION,
    _PROMPT400_RELAXED_HANDOFF_SURFACE_KEYS,
    _PROMPT400_SCHEMA_VERSION,
    _PROMPT401_NEXT_PROMPT_SELECTION_SURFACE_KEYS,
    _PROMPT401_SCHEMA_VERSION,
    _PROMPT402_GENERATED_PROMPT_SURFACE_KEYS,
    _PROMPT402_SCHEMA_VERSION,
    _PROMPT403_SCHEMA_VERSION,
    _PROMPT403_SELECTED_PROMPT_DRY_RUN_HANDOFF_KEYS,
    _PROMPT404_SCHEMA_VERSION,
    _PROMPT404_SELECTED_PROMPT_HANDOFF_REVIEW_KEYS,
    _PROMPT405_SCHEMA_VERSION,
    _PROMPT405_SELECTED_PROMPT_EXECUTION_PLAN_KEYS,
    _PROMPT406_BOUNDED_LOOP_OBSERVATION_KEYS,
    _PROMPT406_SCHEMA_VERSION,
    _PROMPT407_RELAXED_LOOP_COMPLETION_RECEIPT_KEYS,
    _PROMPT407_SCHEMA_VERSION,
    _PROMPT408_SCHEMA_VERSION,
    _PROMPT408_STRICT_REENABLE_PLAN_KEYS,
    _PROMPT409_SCHEMA_VERSION,
    _PROMPT409_STRICT_REENABLE_GATE_RESTORATION_PACKET_KEYS,
    _PROMPT410_SCHEMA_VERSION,
    _PROMPT410_STRICT_ROUTE_RESTORE_KEYS,
    _PROMPT411_PHYSICAL_PROMPT_MATERIALIZATION_PLAN_KEYS,
    _PROMPT411_SCHEMA_VERSION,
    _PROMPT412_PHYSICAL_PROMPT_MATERIALIZATION_BOUNDARY_KEYS,
    _PROMPT412_SCHEMA_VERSION,
    _PROMPT413_SCHEMA_VERSION,
    _PROMPT413_SELECTED_PROMPT_EXECUTION_ADAPTER_BOUNDARY_KEYS,
    _PROMPT414_EXECUTION_RESULT_REVIEW_BOUNDARY_KEYS,
    _PROMPT414_SCHEMA_VERSION,
    _PROMPT415_GUARDED_EXECUTION_ENABLE_PLAN_KEYS,
    _PROMPT415_SCHEMA_VERSION,
    _PROMPT416_PHYSICAL_PROMPT_MATERIALIZATION_WRITE_KEYS,
    _PROMPT416_SCHEMA_VERSION,
    _PROMPT417_SCHEMA_VERSION,
    _PROMPT417_SELECTED_PROMPT_CODEX_EXECUTION_ADAPTER_KEYS,
    _PROMPT418_EXECUTION_RESULT_REVIEW_AND_SUCCESS_ROUTE_KEYS,
    _PROMPT418_SCHEMA_VERSION,
    _PROMPT419_APPROVE_COMMIT_TAG_AND_SUCCESS_LOOP_KEYS,
    _PROMPT419_SCHEMA_VERSION,
    _PROMPT420_SCHEMA_VERSION,
    _PROMPT420_SUCCESS_ONLY_NEXT_CYCLE_LOOP_KEYS,
    _PROMPT421_SCHEMA_VERSION,
    _PROMPT421_TARGETED_FIX_ROUTE_AND_MATERIALIZATION_KEYS,
    _PROMPT422_SCHEMA_VERSION,
    _PROMPT422_TARGETED_FIX_CODEX_EXECUTION_ADAPTER_KEYS,
    _PROMPT423_SCHEMA_VERSION,
    _PROMPT423_TARGETED_FIX_RESULT_REVIEW_KEYS,
    _PROMPT424_BOUNDED_FULL_AUTONOMOUS_LOOP_KEYS,
    _PROMPT424_SCHEMA_VERSION,
    _PROMPT425_LOCAL_AUTONOMOUS_LOOP_INVOCATION_KEYS,
    _PROMPT425_SCHEMA_VERSION,
    _PROMPT426_BOUNDED_RUNNER_STEP_EXECUTOR_KEYS,
    _PROMPT426_SCHEMA_VERSION,
    _PROMPT427_BOUNDED_MULTI_CYCLE_LOOP_RUNNER_KEYS,
    _PROMPT427_SCHEMA_VERSION,
    _PROMPT428_BOUNDED_RUNTIME_COMMAND_ARTIFACT_CONTRACT_KEYS,
    _PROMPT428_SCHEMA_VERSION,
    _PROMPT429_BOUNDED_RUNTIME_LAUNCH_READINESS_GATE_KEYS,
    _PROMPT429_SCHEMA_VERSION,
    _PROMPT430_BOUNDED_RUNTIME_EXECUTION_ADAPTER_KEYS,
    _PROMPT430_SCHEMA_VERSION,
    _PROMPT431_RUNTIME_EXECUTION_RESULT_REVIEW_ROUTE_DECISION_KEYS,
    _PROMPT431_SCHEMA_VERSION,
    _PROMPT432_ROUTE_DECISION_HANDOFF_PACKET_KEYS,
    _PROMPT432_SCHEMA_VERSION,
    _PROMPT433_BOUNDED_HANDOFF_EXECUTION_ADAPTER_KEYS,
    _PROMPT433_SCHEMA_VERSION,
    _PROMPT434_BOUNDED_COMPLETE_AUTONOMOUS_SELF_RUN_CLOSURE_KEYS,
    _PROMPT434_SCHEMA_VERSION,
    _PROMPT435_RUNTIME_ACTIVATION_WIRING_KEYS,
    _PROMPT435_SCHEMA_VERSION,
    _PROMPT436_RUNTIME_CHAIN_ACTIVATION_KEYS,
    _PROMPT436_SCHEMA_VERSION,
    _PROMPT437_RUNTIME_COMMAND_ARTIFACT_WIRING_KEYS,
    _PROMPT437_SCHEMA_VERSION,
    _PROMPT438_RUNTIME_RESULT_CLASSIFICATION_WIRING_KEYS,
    _PROMPT438_SCHEMA_VERSION,
    _PROMPT439_HANDOFF_EXECUTION_RESULT_MATERIALIZATION_KEYS,
    _PROMPT439_SCHEMA_VERSION,
    _PROMPT440_SCHEMA_VERSION,
    _PROMPT441_BOUNDED_CODEX_INVOCATION_KEYS,
    _PROMPT441_CODEX_COMMAND_ARGV,
    _PROMPT441_SCHEMA_VERSION,
    _PROMPT442_CODEX_POST_EXECUTION_REVIEW_KEYS,
    _PROMPT442_SCHEMA_VERSION,
    _PROMPT443_SCHEMA_VERSION,
    _PROMPT443_SUCCESS_DIFF_HANDOFF_KEYS,
    _PROMPT444_SCHEMA_VERSION,
    _PROMPT444_TARGETED_FIX_REENTRY_PACKET_KEYS,
    _PROMPT445_SCHEMA_VERSION,
    _PROMPT445_TARGETED_FIX_PROMPT_MATERIALIZATION_KEYS,
    _PROMPT446_SCHEMA_VERSION,
    _PROMPT446_TARGETED_FIX_REENTRY_REQUEST_PACKET_KEYS,
    _PROMPT447_SCHEMA_VERSION,
    _PROMPT447_TARGETED_FIX_EXECUTION_GATE_KEYS,
    _PROMPT448_SCHEMA_VERSION,
    _PROMPT448_TARGETED_FIX_EXECUTION_ALLOW_CANDIDATE_KEYS,
    _PROMPT449_EXPLICIT_TARGETED_FIX_EXECUTION_KEYS,
    _PROMPT449_SCHEMA_VERSION,
    _PROMPT450_PROMPT449_RUNTIME_PACKET_EXECUTION_KEYS,
    _PROMPT450_SCHEMA_VERSION,
    _PROMPT451_MINIMAL_AUTONOMOUS_COMPLETION_KEYS,
    _PROMPT451_SCHEMA_VERSION,
    _PROMPT452_BLOCKED_RETURNCODE_CLASSIFICATIONS,
    _PROMPT452_PROMPT451_RUNTIME_EXECUTED_REVIEW_CLOSURE_KEYS,
    _PROMPT452_SCHEMA_VERSION,
    _PROMPT452_SUCCESS_RETURNCODE_CLASSIFICATIONS,
    _PROMPT453_COMMIT_TAG_READY_EXPLICIT_ALLOW_PACKET_KEYS,
    _PROMPT453_SCHEMA_VERSION,
    _PROMPT454_APPLICABLE_PROMPT452_BLOCKED_REASONS,
    _PROMPT454_PLACEHOLDER_RETURNCODE_CLASSIFICATIONS,
    _PROMPT454_PROMPT452_RUNTIME_EVIDENCE_REPAIR_KEYS,
    _PROMPT454_SCHEMA_VERSION,
    _PROMPT455_EXPLICIT_COMMIT_TAG_ALLOW_BRIDGE_KEYS,
    _PROMPT455_SCHEMA_VERSION,
    _PROMPT456_COMPRESSED_BOUNDED_COMMIT_TAG_EXECUTION_GATE_KEYS,
    _PROMPT456_SCHEMA_VERSION,
    _PROMPT457_COMMIT_TAG_EXECUTION_OBSERVATION_CLEAN_RERUN_CLOSURE_KEYS,
    _PROMPT457_SCHEMA_VERSION,
    _PROMPT458_MINIMAL_AUTONOMOUS_COMPLETION_CLOSURE_KEYS,
    _PROMPT458_SCHEMA_VERSION,
    _PROMPT459_BOUNDED_LOCAL_COMMIT_TAG_PACKET_EXECUTOR_KEYS,
    _PROMPT459_SCHEMA_VERSION,
    _PROMPT460_EXISTING_COMMIT_TAG_EXECUTOR_CONNECTOR_KEYS,
    _PROMPT460_SCHEMA_VERSION,
    _PROMPT461_POST_COMMIT_CLEAN_OBSERVED_COMPLETION_CLOSURE_KEYS,
    _PROMPT461_SCHEMA_VERSION,
    _PROMPT462_COMPLETED_NEXT_CYCLE_SMOKE_REGRESSION_GUARD_KEYS,
    _PROMPT462_SCHEMA_VERSION,
    _PROMPT463_ONE_CYCLE_NEXT_PROMPT_SELECTION_SMOKE_KEYS,
    _PROMPT463_SCHEMA_VERSION,
    _PROMPT464_ONE_CYCLE_NEXT_PROMPT_MATERIALIZATION_SMOKE_KEYS,
    _PROMPT464_SCHEMA_VERSION,
    _PROMPT465_BOUNDED_ONE_CYCLE_EXECUTION_SMOKE_KEYS,
    _PROMPT465_SCHEMA_VERSION,
    _PROMPT466_EXECUTION_RESULT_REVIEW_ROUTE_DECISION_KEYS,
    _PROMPT466_SCHEMA_VERSION,
    _PROMPT467_NO_HUMAN_NEXT_CYCLE_CONTINUATION_KEYS,
    _PROMPT467_SCHEMA_VERSION,
    _PROMPT468_FULL_NO_HUMAN_LOOP_REGRESSION_RERUN_KEYS,
    _PROMPT468_SCHEMA_VERSION,
    _PROMPT469_CHANGED_DIFF_ROUTE_GUARD_KEYS,
    _PROMPT469_SCHEMA_VERSION,
    _PROMPT470_BOUNDED_TARGETED_FIX_EXECUTION_KEYS,
    _PROMPT470_SCHEMA_VERSION,
    _PROMPT471_COMMIT_MESSAGE,
    _PROMPT471_COMMIT_TAG_CANDIDATE_EXECUTION_GATE_KEYS,
    _PROMPT471_SCHEMA_VERSION,
    _PROMPT471_TAG_NAME,
    _PROMPT472_COMMIT_MESSAGE,
    _PROMPT472_NEXT_ACTION,
    _PROMPT472_NEXT_PROMPT_ID,
    _PROMPT472_POST_COMMIT_CLEAN_RERUN_NEXT_CYCLE_KEYS,
    _PROMPT472_SCHEMA_VERSION,
    _PROMPT472_TAG_NAME,
    _PROMPT472_VALID_FINAL_HEAD_SUBJECTS,
    _PROMPT472_VALID_FINAL_TAG_NAMES,
    _PROMPT473_ALLOWED_TRACKED_FILES,
    _PROMPT473_CHANGED_DIFF_TARGETED_FIX_BOUNDARY_KEYS,
    _PROMPT473_NEXT_ACTION,
    _PROMPT473_SCHEMA_VERSION,
    _PROMPT474_ALLOWED_TRACKED_FILES,
    _PROMPT474_BOUNDED_TARGETED_FIX_EXECUTION_KEYS,
    _PROMPT474_PROMPT473_TAG_NAME,
    _PROMPT474_SCHEMA_VERSION,
    _PROMPT475_ALLOWED_TRACKED_FILES,
    _PROMPT475_COMMIT_TAG_EVIDENCE_HANDOFF_GATE_KEYS,
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
    _PROMPT476_TARGETED_FIX_SUCCESS_LOOP_KEYS,
    _PROMPT476_VALID_FINAL_HEAD_SUBJECTS,
    _PROMPT476_VALID_FINAL_TAG_NAMES,
    _PROMPT477_ALLOWED_TRACKED_FILES,
    _PROMPT477_BLOCKED_NEXT_ACTION,
    _PROMPT477_CYCLE_IDS,
    _PROMPT477_MAX_CYCLE_COUNT,
    _PROMPT477_NEXT_ACTION,
    _PROMPT477_REQUESTED_CYCLE_COUNT,
    _PROMPT477_SCHEMA_VERSION,
    _PROMPT477_TWO_CYCLE_READINESS_KEYS,
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
    _PROMPT478_TWO_CYCLE_LIVE_EXECUTION_KEYS,
    _PROMPT478_VALID_FINAL_HEAD_SUBJECTS,
    _PROMPT478_VALID_FINAL_TAG_NAMES,
    _PROMPT478_VALID_PROMPT477_HEAD_SUBJECTS,
    _PROMPT478_VALID_PROMPT477_TAG_NAME,
    _PROMPT479_ALLOWED_TRACKED_FILES,
    _PROMPT479_BLOCKED_NEXT_ACTION,
    _PROMPT479_DAEMON_LITE_BOUNDARY_KEYS,
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
    _PROMPT480_WORKSPACE_SAFETY_STOP_KEYS,
    _PROMPT481_ALLOWED_TRACKED_FILES,
    _PROMPT481_BLOCKED_NEXT_ACTION,
    _PROMPT481_CYCLE_IDS,
    _PROMPT481_DAEMON_LITE_REPEATED_CYCLE_KEYS,
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
    _PROMPT482_THREE_CYCLE_USABILITY_CONFIRMATION_KEYS,
    _PROMPT483_ALLOWED_TRACKED_FILES,
    _PROMPT483_BLOCKED_NEXT_ACTION,
    _PROMPT483_DEFAULT_ROLE_CATALOG_PATH,
    _PROMPT483_DEFAULT_SELECTED_ROLE_ID,
    _PROMPT483_ROLE_CATALOG_READER_HANDOFF_KEYS,
    _PROMPT483_SCHEMA_VERSION,
    _PROMPT483_SUCCESS_NEXT_ACTION,
    _PROMPT484B_BLOCKED_NEXT_ACTION,
    _PROMPT484B_DEFAULT_SELECTED_ROLE_ID,
    _PROMPT484B_ROLE_SELECTION_LAYER_KEYS,
    _PROMPT484B_SCHEMA_VERSION,
    _PROMPT484B_SUCCESS_NEXT_ACTION,
    _PROMPT484C_BLOCKED_NEXT_ACTION,
    _PROMPT484C_SCHEMA_VERSION,
    _PROMPT484C_SELECTED_ROLE_PROMPT_GENERATION_REQUEST_KEYS,
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
    _PROMPT484_DAEMON_LITE_10_CYCLE_NO_ALLOW_BOUNDARY_KEYS,
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
    _REMOTE_READINESS_EXPECTED_BRANCH,
    _REMOTE_READINESS_EXPECTED_HEAD_TAG,
    _SELECTED_STEP_EXECUTION_ADAPTER_EXPECTED_HEAD_TAG,
    _SELECTED_STEP_EXECUTION_RESULT_ROUTE_CAPTURE_PATH,
    _SELECTED_STEP_EXECUTION_RESULT_ROUTE_DECISION_PATH,
    _SELECTED_STEP_EXECUTION_RESULT_ROUTE_RECEIPT_PATH,
    _SELECTED_STEP_LIVE_EXECUTION_EXPECTED_HEAD_TAG,
    _SELECTED_STEP_LIVE_EXECUTION_GATE_PATH,
    _SELECTED_STEP_LIVE_EXECUTION_RECEIPT_PATH,
    _SELECTED_STEP_LIVE_EXECUTION_RESULT_PATH,
    _TARGETED_FIX_POST_REENTRY_BOUNDED_CYCLE_DECISION_PATH,
    _TARGETED_FIX_POST_REENTRY_BOUNDED_CYCLE_DEFAULT_CURRENT_CYCLE_COUNT,
    _TARGETED_FIX_POST_REENTRY_BOUNDED_CYCLE_DEFAULT_MAX_CYCLE_COUNT,
    _TARGETED_FIX_POST_REENTRY_BOUNDED_CYCLE_RECEIPT_PATH,
    _TARGETED_FIX_POST_REENTRY_BOUNDED_CYCLE_STATE_PATH,
    _TARGETED_FIX_POST_REENTRY_CODEX_REENTRY_EXECUTION_RECEIPT_PATH,
    _TARGETED_FIX_POST_REENTRY_CODEX_REENTRY_EXECUTION_STDERR_PATH,
    _TARGETED_FIX_POST_REENTRY_CODEX_REENTRY_EXECUTION_STDOUT_PATH,
    _TARGETED_FIX_POST_REENTRY_CYCLE_CLOSURE_RESULT_PATH,
    _TARGETED_FIX_POST_REENTRY_DIFF_CAPTURE_PATH,
    _TARGETED_FIX_POST_REENTRY_DIFF_NAME_STATUS_PATH,
    _TARGETED_FIX_POST_REENTRY_DIFF_PATCH_PATH,
    _TARGETED_FIX_POST_REENTRY_DIFF_STAT_PATH,
    _TARGETED_FIX_POST_REENTRY_NEXT_STEP_HANDOFF_PATH,
    _TARGETED_FIX_POST_REENTRY_PROMPT_EMISSION_FORBIDDEN_FRAGMENTS,
    _TARGETED_FIX_POST_REENTRY_PROMPT_EMISSION_PATH,
    _TARGETED_FIX_POST_REENTRY_PROMPT_EMISSION_RECEIPT_PATH,
    _TARGETED_FIX_POST_REENTRY_REVIEW_ASSIMILATION_PATH,
    _TARGETED_FIX_POST_REENTRY_REVIEW_HANDOFF_PATH,
    _TARGETED_FIX_POST_REENTRY_REVIEW_RESPONSE_PATH,
    _TARGETED_FIX_POST_REENTRY_ROUTE_DECISION_PATH,
    _TARGETED_FIX_POST_REENTRY_ROUTE_EXECUTOR_BOUNDARY_PATH,
    _TARGETED_FIX_POST_REENTRY_TERMINAL_SUMMARY_PATH,
    _TARGETED_FIX_REENTRY_EXECUTION_COMMAND,
    _TARGETED_FIX_REENTRY_EXECUTION_PROMPT_PATH,
    _TARGETED_FIX_REENTRY_EXECUTION_RECEIPT_PATH,
    _TARGETED_FIX_REENTRY_EXECUTION_STDERR_PATH,
    _TARGETED_FIX_REENTRY_EXECUTION_STDOUT_PATH,
    _as_int,
    _as_non_negative_int,
    _as_optional_int,
    _build_bounded_local_autonomous_loop_decision_state,
    _build_bounded_local_autonomous_loop_receipt_state,
    _build_bounded_local_autonomous_loop_state,
    _build_concrete_prompt298_goal_from_next_dev_slice,
    _build_default_multi_cycle_history_payload,
    _build_dry_run_local_codex_one_shot_execution_result_state,
    _build_dry_run_selected_step_live_execution_gate_state,
    _build_dry_run_selected_step_live_execution_operation_state,
    _build_local_autonomous_continuation_artifacts,
    _build_local_autonomous_cycle_v2_decision,
    _build_local_autonomous_cycle_v2_receipt,
    _build_local_autonomous_cycle_v2_state,
    _build_local_bounded_approve_commit_tag_execution_artifacts,
    _build_local_codex_one_shot_execution_handoff_state,
    _build_local_codex_one_shot_execution_receipt,
    _build_local_codex_one_shot_execution_receipt_v2,
    _build_local_codex_one_shot_execution_result_state,
    _build_local_codex_one_shot_prompt_markdown,
    _build_local_contract_fix_cycle_coordination_artifacts,
    _build_local_daemon_lite_wrapper_artifacts,
    _build_local_end_to_end_controller_component_matrix_state,
    _build_local_end_to_end_controller_gap_report_state,
    _build_local_end_to_end_controller_readiness_boundary_state,
    _build_local_end_to_end_dry_run_plan_state,
    _build_local_end_to_end_dry_run_receipt_state,
    _build_local_end_to_end_dry_run_step_matrix_state,
    _build_local_end_to_end_one_shot_execution_gate_state,
    _build_local_end_to_end_one_shot_execution_receipt_state,
    _build_local_end_to_end_one_shot_step_selection_state,
    _build_local_only_autonomous_loop_closure_decision,
    _build_local_only_autonomous_loop_closure_receipt,
    _build_local_only_autonomous_loop_closure_state,
    _build_local_post_commit_cycle_closure_artifacts,
    _build_local_post_targeted_contract_fix_review_artifacts,
    _build_local_targeted_contract_fix_execution_artifacts,
    _build_local_targeted_contract_fix_prompt_artifacts,
    _build_one_cycle_post_execution_handoff,
    _build_one_cycle_review_handoff_decision_state,
    _build_remote_readiness_boundary_state,
    _build_remote_readiness_plan_state,
    _build_review_response_assimilation_state,
    _build_review_route_decision_state,
    _build_selected_step_execution_adapter_state,
    _build_selected_step_execution_plan_state,
    _build_selected_step_execution_receipt_state,
    _build_selected_step_execution_result_route_capture_state,
    _build_selected_step_execution_result_route_decision_state,
    _build_selected_step_execution_result_route_receipt_state,
    _build_selected_step_live_execution_gate_state,
    _build_selected_step_live_execution_receipt_state,
    _build_selected_step_live_execution_result_state,
    _build_targeted_fix_post_reentry_bounded_cycle_decision_state,
    _build_targeted_fix_post_reentry_bounded_cycle_receipt_state,
    _build_targeted_fix_post_reentry_bounded_cycle_state,
    _build_targeted_fix_post_reentry_cycle_closure_result_state,
    _build_targeted_fix_post_reentry_next_step_handoff_state,
    _build_targeted_fix_post_reentry_prompt_emission_state,
    _build_targeted_fix_post_reentry_review_assimilation_state,
    _build_targeted_fix_post_reentry_review_handoff_state,
    _build_targeted_fix_post_reentry_route_decision_state,
    _build_targeted_fix_post_reentry_route_executor_boundary_state,
    _build_targeted_fix_post_reentry_terminal_summary_state,
    _build_targeted_fix_prompt_boundary_state,
    _build_targeted_fix_reentry_execution_gate_state,
    _capture_targeted_fix_post_reentry_diff_state,
    _classify_project_browser_autonomous_duplicate_status,
    _collect_changed_tracked_files,
    _collect_local_codex_execution_readiness_banned_prompt_fragments,
    _collect_one_cycle_controller_enablement_overrides_from_retry_context,
    _collect_project_browser_selector_candidates_for_target,
    _collect_prompt357_local_git_diff_changed_files,
    _derive_bounded_n2_reason_taxonomy,
    _evaluate_one_cycle_controller_exec_plan_safety,
    _extract_explicit_commit_tag_allow_metadata_from_mapping,
    _first_true_reason,
    _is_abstract_or_self_referential_next_dev_slice_goal,
    _is_one_cycle_controller_local_artifacts_dir,
    _is_project_browser_login_interruption_url,
    _iso_now,
    _line_has_local_codex_execution_readiness_disallow_context,
    _line_is_local_codex_execution_readiness_disallow_heading,
    _load_prompt357_previous_success_candidates_from_reference_payload,
    _maybe_reconcile_stale_prompt334_post_codex_artifacts,
    _normalize_contract_payload,
    _normalize_project_browser_reason_codes,
    _normalize_prompt437_runtime_command_request,
    _normalize_selector_candidates,
    _normalize_string_list,
    _normalize_text,
    _overlay_bounded_local_loop_local_loop_state_for_coordinator,
    _parse_git_status_path,
    _parse_project_browser_structured_response,
    _planning_artifact_bundle_has_complete_objective,
    _planning_artifact_bundle_is_incomplete_prompt167_smoke_placeholder,
    _planning_artifact_bundle_is_prompt167_smoke_placeholder,
    _probe_playwright_import_posture,
    _prompt357_as_boolish,
    _prompt357_current_runtime_evidence_is_ready,
    _prompt357_read_bool,
    _prompt357_read_list,
    _prompt357_read_text,
    _prompt358_candidate_artifact_timestamp,
    _prompt358_find_latest_valid_prior_artifact,
    _prompt358_required_bool_match,
    _prompt358_required_text_match,
    _prompt358_valid_prior_prompt355_payload,
    _prompt358_valid_prior_prompt356_payload,
    _prompt358_valid_prior_prompt357_payload,
    _prompt397c_generated_prompt_can_be_strict_valid,
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
    _prompt419_command_allowed,
    _prompt419_commit_message_valid,
    _prompt419_commit_tag_plan_valid,
    _prompt419_normalize_git_runner_result,
    _prompt419_run_git_command,
    _prompt419_success_approval_ready,
    _prompt419_tag_name_valid,
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
    _prompt447_read_bool,
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
    _prompt452_source_family,
    _prompt452_source_kind,
    _prompt453_explicit_commit_tag_allow_present,
    _prompt453_safe_deferred_next_action,
    _prompt454_first_known_string_list,
    _prompt454_first_returncode,
    _prompt454_first_returncode_classification,
    _prompt454_safe_deferred_next_action,
    _prompt454_source_family,
    _prompt454_source_kind,
    _prompt455_explicit_commit_tag_allow_source,
    _prompt455_known_string_list,
    _prompt455_safe_deferred_next_action,
    _prompt456_explicit_commit_tag_allow_source,
    _prompt456_first_known_string_list,
    _prompt456_runtime_command_explicit_commit_tag_allow_metadata,
    _prompt456_tag_uniqueness_state,
    _prompt457_first_present,
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
    _prompt473_bool_from_any_existing,
    _prompt473_historical_prompt472_repo_evidence_ready,
    _prompt473_prompt472_evidence_bridge,
    _prompt474_bool_from_any_existing,
    _prompt474_historical_prompt473_repo_evidence_ready,
    _prompt474_prompt473_evidence_bridge,
    _prompt474_targeted_fix_prompt_body,
    _prompt475_prompt474_current_fields_evidence_ready,
    _prompt475_prompt474_evidence_bridge,
    _prompt475_prompt474_explicit_flags_evidence_ready,
    _prompt475_prompt474_historical_repo_evidence_ready,
    _prompt475_prompt474_tag_in_lineage,
    _prompt476_prompt475_current_fields_evidence_ready,
    _prompt476_prompt475_evidence_bridge,
    _prompt476_prompt475_explicit_flags_evidence_ready,
    _prompt476_prompt475_historical_repo_evidence_ready,
    _prompt476_prompt475_tag_in_lineage,
    _prompt477_prompt476_current_fields_evidence_ready,
    _prompt477_prompt476_evidence_bridge,
    _prompt477_prompt476_explicit_flags_evidence_ready,
    _prompt477_prompt476_historical_repo_evidence_ready,
    _prompt477_tag_in_lineage,
    _prompt478_bool_from_allow_surfaces,
    _prompt478_cycle_prompt_body,
    _prompt478_empty_cycle_state,
    _prompt478_final_repo_state_evidence_ready,
    _prompt478_ordered_union,
    _prompt478_prompt477_current_fields_evidence_ready,
    _prompt478_prompt477_evidence_bridge,
    _prompt478_prompt477_explicit_flags_evidence_ready,
    _prompt478_prompt477_historical_repo_evidence_ready,
    _prompt478_run_cycle,
    _prompt478_runtime_allow_surfaces,
    _prompt479_prompt478_current_fields_evidence_ready,
    _prompt479_prompt478_evidence_bridge,
    _prompt479_prompt478_explicit_flags_evidence_ready,
    _prompt479_prompt478_historical_repo_evidence_ready,
    _prompt479_surface_int,
    _prompt480_manual_stop_requested,
    _prompt480_prompt479_current_fields_evidence_ready,
    _prompt480_prompt479_evidence_bridge,
    _prompt480_prompt479_explicit_flags_evidence_ready,
    _prompt480_prompt479_historical_repo_evidence_ready,
    _prompt481_cycle_prompt_body,
    _prompt481_empty_cycle_state,
    _prompt481_manual_stop_requested,
    _prompt481_prompt480_current_fields_evidence_ready,
    _prompt481_prompt480_evidence_bridge,
    _prompt481_prompt480_explicit_flags_evidence_ready,
    _prompt481_prompt480_historical_repo_evidence_ready,
    _prompt481_run_cycle,
    _prompt482_prompt481_current_fields_evidence_ready,
    _prompt482_prompt481_evidence_bridge,
    _prompt482_prompt481_explicit_flags_evidence_ready,
    _prompt482_prompt481_historical_repo_evidence_ready,
    _prompt482_prompt481_post_commit_no_allow_evidence_ready,
    _prompt483_extract_selected_role_text,
    _prompt483_first_text_from_payloads,
    _prompt483_prompt482_current_fields_evidence_ready,
    _prompt483_prompt482_evidence_bridge,
    _prompt483_prompt482_explicit_flags_evidence_ready,
    _prompt483_prompt482_historical_repo_evidence_ready,
    _prompt483_resolve_repo_relative_path,
    _prompt483_untracked_files,
    _prompt491a_bounded_role_summary,
    _prompt491a_canonical_tokens_ready,
    _prompt491a_materialized_prompt378_markdown,
    _prompt492_extract_role_paths,
    _prompt492_infer_allowed_files,
    _prompt492_infer_forbidden_files,
    _prompt492_infer_validation_commands,
    _prompt492_role_text_section_lines,
    _read_json_object_if_exists,
    _read_multi_cycle_history,
    _read_planning_artifact_bundle,
    _reconcile_approve_commit_tag_artifacts,
    _record_one_cycle_result_into_multi_cycle_history,
    _refresh_one_cycle_controller_runtime_planning_artifacts,
    _replace_one_cycle_controller_prompt167_placeholder_bundle,
    _resolve_current_branch,
    _resolve_project_browser_chatgpt_url,
    _resolve_project_browser_prepared_prompt_text,
    _resolve_prompt357_previous_success_fallback,
    _resolve_prompt358_recovered_local_continuation_evidence,
    _run_git,
    _run_selected_step_read_current_state_if_allowed,
    _run_targeted_fix_post_reentry_codex_reentry_execution_if_enabled,
    _run_targeted_fix_reentry_execution_if_enabled,
    _serialize_required_signals,
    _write_json,
    _write_multi_cycle_history,
    _write_targeted_fix_post_reentry_prompt_if_allowed,
)
from automation.orchestration.planned_runner.state.run_state import (
    _is_remote_github_blocker_reason,
    _is_remote_github_missing_or_ambiguous_reason,
    _run_state_execution_blockers,
)
from automation.orchestration.planned_runner.summaries.final_payload import (
    _with_execution_gate_surface,
)

def _validate_pr_unit_order(units: list[dict[str, Any]], *, pr_plan: Mapping[str, Any]) -> None:
    planned_units = pr_plan.get("prs") if isinstance(pr_plan.get("prs"), list) else []

    planned_order: list[str] = []
    for pr in planned_units:
        if not isinstance(pr, Mapping):
            continue
        pr_id = _normalize_text(pr.get("pr_id"))
        if pr_id:
            planned_order.append(pr_id)

    compiled_order = [_normalize_text(unit.get("pr_id")) for unit in units if _normalize_text(unit.get("pr_id"))]

    if compiled_order != planned_order:
        raise ValueError("compiled prompt units are not aligned with pr_plan.prs ordering")

    seen: set[str] = set()
    for unit in units:
        pr_id = _normalize_text(unit.get("pr_id"))
        if not pr_id:
            raise ValueError("pr_unit.pr_id must be non-empty")
        if pr_id in seen:
            raise ValueError(f"duplicate pr_id in compiled units: {pr_id}")
        dependencies = _normalize_string_list(unit.get("depends_on"))
        for dependency in dependencies:
            if dependency not in seen:
                raise ValueError(
                    f"dependency order violation for {pr_id}: depends_on={dependency} not yet processed"
                )
        seen.add(pr_id)

def _build_remote_delivery_surface(
    *,
    execution_type: str,
    status: str,
    blocking_reasons: list[str],
    command_summary: Mapping[str, Any],
    existing_payload: Mapping[str, Any],
) -> dict[str, Any]:
    normalized_execution_type = _normalize_text(execution_type, default="")
    normalized_status = _normalize_text(status, default="")
    normalized_blockers = _serialize_required_signals(blocking_reasons)
    remote_github_blocked_reasons = _serialize_required_signals(
        [reason for reason in normalized_blockers if _is_remote_github_blocker_reason(reason)]
    )
    remote_github_blocked = normalized_status == "blocked" and bool(remote_github_blocked_reasons)
    remote_github_missing_or_ambiguous = any(
        _is_remote_github_missing_or_ambiguous_reason(reason)
        for reason in remote_github_blocked_reasons
    )
    remote_github_status = (
        "blocked"
        if remote_github_blocked
        else "allowed"
        if normalized_status in {"succeeded", "failed"}
        else "unknown"
    )

    surface: dict[str, Any] = {
        "remote_github_status": remote_github_status,
        "remote_github_blocked": remote_github_blocked,
        "remote_github_blocked_reason": (
            remote_github_blocked_reasons[0] if remote_github_blocked_reasons else ""
        ),
        "remote_github_blocked_reasons": remote_github_blocked_reasons,
        "remote_github_missing_or_ambiguous": remote_github_missing_or_ambiguous,
    }

    if normalized_execution_type == _PUSH_EXECUTION_TYPE:
        remote_state_status = (
            "ready"
            if normalized_status == "succeeded"
            else "blocked"
            if remote_github_blocked
            else "unknown"
        )
        if "remote_non_fast_forward_risk" in remote_github_blocked_reasons:
            remote_state_status = "non_fast_forward_risk"
        elif "remote_branch_diverged" in remote_github_blocked_reasons:
            remote_state_status = "diverged"
        elif remote_github_missing_or_ambiguous:
            remote_state_status = "ambiguous"

        upstream_tracking_status = _normalize_text(
            existing_payload.get("upstream_tracking_status"),
            default="",
        )
        if not upstream_tracking_status:
            if "upstream_tracking_unresolved" in remote_github_blocked_reasons:
                upstream_tracking_status = "unresolved"
            elif "upstream_ref_ambiguous" in remote_github_blocked_reasons:
                upstream_tracking_status = "ambiguous"
            elif any(
                reason in remote_github_blocked_reasons
                for reason in {"remote_non_fast_forward_risk", "remote_branch_diverged"}
            ):
                upstream_tracking_status = "tracked"
            elif normalized_status in {"succeeded", "failed"}:
                upstream_tracking_status = "tracked"
            else:
                upstream_tracking_status = "unknown"

        remote_divergence_status = _normalize_text(
            existing_payload.get("remote_divergence_status"),
            default="",
        )
        if not remote_divergence_status:
            if "remote_non_fast_forward_risk" in remote_github_blocked_reasons:
                remote_divergence_status = "non_fast_forward_risk"
            elif "remote_branch_diverged" in remote_github_blocked_reasons:
                remote_divergence_status = "diverged"
            elif normalized_status in {"succeeded", "failed"}:
                remote_divergence_status = "none"
            else:
                remote_divergence_status = "unknown"

        surface.update(
            {
                "remote_state_status": remote_state_status,
                "remote_state_blocked": remote_github_blocked,
                "remote_state_blocked_reason": (
                    remote_github_blocked_reasons[0] if remote_github_blocked_reasons else ""
                ),
                "remote_state_missing_or_ambiguous": remote_github_missing_or_ambiguous,
                "upstream_tracking_status": upstream_tracking_status,
                "remote_divergence_status": remote_divergence_status,
                "remote_branch_status": (
                    "known"
                    if _normalize_text(existing_payload.get("head_branch"), default="")
                    else "unknown"
                ),
                "github_state_status": "not_applicable",
                "github_state_unavailable": False,
            }
        )
        return surface

    if normalized_execution_type == _PR_EXECUTION_TYPE:
        existing_pr_status = _normalize_text(existing_payload.get("existing_pr_status"), default="")
        if not existing_pr_status:
            if "existing_open_pr_detected" in remote_github_blocked_reasons:
                existing_pr_status = "existing_open"
            elif "existing_pr_identity_ambiguous" in remote_github_blocked_reasons or (
                "existing_pr_lookup_ambiguous" in remote_github_blocked_reasons
            ):
                existing_pr_status = "ambiguous"
            elif normalized_status == "succeeded":
                existing_pr_status = "none"
            else:
                existing_pr_status = "unknown"

        pr_creation_state_status = _normalize_text(
            existing_payload.get("pr_creation_state_status"),
            default="",
        )
        if not pr_creation_state_status:
            if normalized_status == "succeeded":
                pr_creation_state_status = "created"
            elif existing_pr_status == "existing_open":
                pr_creation_state_status = "blocked_existing_pr"
            elif remote_github_missing_or_ambiguous:
                pr_creation_state_status = "blocked_remote_ambiguous"
            elif remote_github_blocked:
                pr_creation_state_status = "blocked_remote"
            elif normalized_status == "failed":
                pr_creation_state_status = "failed"
            else:
                pr_creation_state_status = "unknown"

        lookup_status = _normalize_text(command_summary.get("open_pr_lookup_status"), default="")
        github_state_status = (
            lookup_status
            or _normalize_text(existing_payload.get("github_state_status"), default="")
            or "unknown"
        )
        github_state_unavailable = github_state_status in {
            "unavailable",
            "api_failure",
            "auth_failure",
            "not_found",
            "unsupported_query",
        }

        surface.update(
            {
                "existing_pr_status": existing_pr_status,
                "pr_creation_state_status": pr_creation_state_status,
                "pr_duplication_risk": (
                    "detected" if existing_pr_status == "existing_open" else "none" if normalized_status == "succeeded" else "unknown"
                ),
                "remote_state_status": "blocked" if remote_github_blocked else "ready" if normalized_status == "succeeded" else "unknown",
                "remote_state_blocked": remote_github_blocked,
                "remote_state_blocked_reason": (
                    remote_github_blocked_reasons[0] if remote_github_blocked_reasons else ""
                ),
                "remote_state_missing_or_ambiguous": remote_github_missing_or_ambiguous,
                "github_state_status": github_state_status,
                "github_state_unavailable": github_state_unavailable,
            }
        )
        return surface

    if normalized_execution_type == _MERGE_EXECUTION_TYPE:
        mergeability_status = _normalize_text(existing_payload.get("mergeability_status"), default="")
        if not mergeability_status:
            if "mergeability_unknown" in remote_github_blocked_reasons:
                mergeability_status = "unknown"
            elif "mergeability_not_ready" in remote_github_blocked_reasons:
                mergeability_status = "not_ready"
            elif normalized_status == "succeeded":
                mergeability_status = "clean"
            else:
                mergeability_status = "unknown"

        required_checks_status = _normalize_text(
            existing_payload.get("required_checks_status"),
            default="",
        )
        if not required_checks_status:
            if "required_checks_unsatisfied" in remote_github_blocked_reasons:
                required_checks_status = "unsatisfied"
            elif normalized_status == "succeeded":
                required_checks_status = "passing"
            else:
                required_checks_status = "unknown"

        review_state_status = _normalize_text(existing_payload.get("review_state_status"), default="")
        if not review_state_status:
            review_state_status = (
                "unsatisfied"
                if "review_requirements_unsatisfied" in remote_github_blocked_reasons
                else "unknown"
            )

        branch_protection_status = _normalize_text(
            existing_payload.get("branch_protection_status"),
            default="",
        )
        if not branch_protection_status:
            branch_protection_status = (
                "unsatisfied"
                if "branch_protection_unsatisfied" in remote_github_blocked_reasons
                else "unknown"
            )

        merge_requirements_status = _normalize_text(
            existing_payload.get("merge_requirements_status"),
            default="",
        )
        if not merge_requirements_status:
            if any(
                reason in remote_github_blocked_reasons
                for reason in {
                    "required_checks_unsatisfied",
                    "review_requirements_unsatisfied",
                    "branch_protection_unsatisfied",
                }
            ):
                merge_requirements_status = "unsatisfied"
            elif normalized_status == "succeeded":
                merge_requirements_status = "satisfied"
            else:
                merge_requirements_status = "unknown"

        status_summary_status = _normalize_text(
            command_summary.get("pr_status_summary_status"),
            default="",
        )
        github_state_status = (
            status_summary_status
            or _normalize_text(command_summary.get("merge_status"), default="")
            or _normalize_text(existing_payload.get("github_state_status"), default="")
            or "unknown"
        )
        github_state_unavailable = status_summary_status in {
            "unavailable",
            "api_failure",
            "auth_failure",
            "not_found",
            "unsupported_query",
            "empty",
        }

        surface.update(
            {
                "mergeability_status": mergeability_status,
                "merge_requirements_status": merge_requirements_status,
                "required_checks_status": required_checks_status,
                "review_state_status": review_state_status,
                "branch_protection_status": branch_protection_status,
                "remote_state_status": "blocked" if remote_github_blocked else "ready" if normalized_status == "succeeded" else "unknown",
                "remote_state_blocked": remote_github_blocked,
                "remote_state_blocked_reason": (
                    remote_github_blocked_reasons[0] if remote_github_blocked_reasons else ""
                ),
                "remote_state_missing_or_ambiguous": remote_github_missing_or_ambiguous,
                "github_state_status": github_state_status,
                "github_state_unavailable": github_state_unavailable,
            }
        )
        return surface

    return surface

def _default_delivery_execution_payload(
    *,
    schema_version: str,
    execution_type: str,
    unit_id: str,
    now: Callable[[], datetime],
) -> dict[str, Any]:
    return {
        "schema_version": schema_version,
        "unit_id": unit_id,
        "execution_type": execution_type,
        "status": "blocked",
        "summary": f"{execution_type} blocked",
        "started_at": "",
        "finished_at": _iso_now(now),
        "branch_name": "",
        "remote_name": "",
        "base_branch": "",
        "head_branch": "",
        "pr_number": None,
        "pr_url": "",
        "merge_commit_sha": "",
        "command_summary": {},
        "failure_reason": f"{execution_type}_not_attempted",
        "manual_intervention_required": False,
        "blocking_reasons": [],
        "attempted": False,
        "execution_allowed": False,
        "execution_authority_status": "unknown",
        "validation_status": "unknown",
        "execution_gate_status": "unknown",
        "authority_blocked_reasons": [],
        "validation_blocked_reasons": [],
        "authority_blocked_reason": "",
        "validation_blocked_reason": "",
        "missing_prerequisites": [],
        "missing_required_refs": [],
        "unsafe_repo_state": [],
        "remote_pr_ambiguity": [],
        "manual_approval_required": False,
    }

def _build_delivery_execution_blocked_payload(
    *,
    schema_version: str,
    execution_type: str,
    unit_id: str,
    now: Callable[[], datetime],
    summary: str,
    failure_reason: str,
    blocking_reasons: list[str],
    manual_intervention_required: bool = False,
    command_summary: Mapping[str, Any] | None = None,
    branch_name: str = "",
    remote_name: str = "",
    base_branch: str = "",
    head_branch: str = "",
    pr_number: int | None = None,
    pr_url: str = "",
) -> dict[str, Any]:
    payload = _default_delivery_execution_payload(
        schema_version=schema_version,
        execution_type=execution_type,
        unit_id=unit_id,
        now=now,
    )
    payload["summary"] = summary
    payload["failure_reason"] = failure_reason
    payload["blocking_reasons"] = _serialize_required_signals(list(blocking_reasons))
    payload["manual_intervention_required"] = manual_intervention_required
    payload["command_summary"] = dict(command_summary) if isinstance(command_summary, Mapping) else {}
    payload["branch_name"] = _normalize_text(branch_name, default="")
    payload["remote_name"] = _normalize_text(remote_name, default="")
    payload["base_branch"] = _normalize_text(base_branch, default="")
    payload["head_branch"] = _normalize_text(head_branch, default="")
    payload["pr_number"] = _as_optional_int(pr_number)
    payload["pr_url"] = _normalize_text(pr_url, default="")
    return _with_execution_gate_surface(payload)

def _resolve_open_pr_lookup(
    *,
    read_backend: Any,
    repository: str,
    head_branch: str,
    base_branch: str,
) -> tuple[str, dict[str, Any]]:
    if read_backend is None:
        return "unavailable", {}
    finder = getattr(read_backend, "find_open_pr", None)
    if not callable(finder):
        return "unavailable", {}
    try:
        payload = finder(repository, head_branch=head_branch, base_branch=base_branch)
    except Exception:
        return "api_failure", {}
    if not isinstance(payload, Mapping):
        return "api_failure", {}
    status = _normalize_text(payload.get("status"), default="")
    if not status:
        return "api_failure", dict(payload)
    data = dict(payload.get("data")) if isinstance(payload.get("data"), Mapping) else {}
    return status, data

def _build_pr_title_and_body(
    *,
    job_id: str,
    unit_id: str,
    commit_sha: str,
) -> tuple[str, str]:
    title = f"[{job_id}:{unit_id}] bounded execution slice"
    body = (
        "Automated bounded PR creation from planned execution runner.\n"
        f"- job_id: {job_id}\n"
        f"- unit_id: {unit_id}\n"
        f"- commit_sha: {commit_sha or '(unknown)'}"
    )
    return title, body

def _resolve_git_remotes(repo_path: str, *, command_summary: dict[str, Any]) -> list[str]:
    remotes_result = _run_git(repo_path, ["remote"])
    command_summary["remote_list_rc"] = remotes_result.returncode
    if remotes_result.returncode != 0:
        return []
    remotes = _normalize_string_list((remotes_result.stdout or "").splitlines(), sort_items=False)
    return remotes

def _has_conflict_status_lines(status_lines: list[str]) -> bool:
    return any(
        line[:2].strip() == "U" or line[:2] in {"DD", "AU", "UD", "UA", "DU", "AA", "UU"}
        for line in status_lines
    )

def _execute_bounded_push(
    *,
    unit_id: str,
    repo_path: str,
    remote_name: str,
    configured_head_branch: str,
    base_branch: str,
    run_state_payload: Mapping[str, Any],
    commit_execution_payload: Mapping[str, Any],
    dry_run: bool,
    now: Callable[[], datetime],
) -> dict[str, Any]:
    command_summary: dict[str, Any] = {}
    branch_name = ""
    head_branch = _normalize_text(configured_head_branch, default="")
    blockers = _run_state_execution_blockers(run_state_payload)

    commit_status = _normalize_text(commit_execution_payload.get("status"), default="")
    commit_sha = _normalize_text(commit_execution_payload.get("commit_sha"), default="")
    if commit_status != "succeeded":
        blockers.append("commit_execution_not_succeeded")
    if not commit_sha:
        blockers.append("commit_execution_commit_sha_missing")
    if dry_run:
        blockers.append("dry_run_mode")
    if not _normalize_text(repo_path, default=""):
        blockers.append("execution_repo_path_missing")

    if blockers:
        return _build_delivery_execution_blocked_payload(
            schema_version=_PUSH_EXECUTION_SCHEMA_VERSION,
            execution_type=_PUSH_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
            summary="push execution blocked by prerequisites or run-level guardrails",
            failure_reason="push_execution_blocked_by_preconditions",
            blocking_reasons=blockers,
            base_branch=base_branch,
            head_branch=head_branch,
            remote_name=remote_name,
        )

    repo_dir = Path(repo_path)
    if not repo_dir.exists() or not repo_dir.is_dir():
        return _build_delivery_execution_blocked_payload(
            schema_version=_PUSH_EXECUTION_SCHEMA_VERSION,
            execution_type=_PUSH_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
            summary="push execution blocked because execution repo path is invalid",
            failure_reason="execution_repo_not_directory",
            blocking_reasons=["execution_repo_not_directory"],
            base_branch=base_branch,
            head_branch=head_branch,
            remote_name=remote_name,
        )

    worktree_result = _run_git(repo_path, ["rev-parse", "--is-inside-work-tree"])
    command_summary["rev_parse_worktree_rc"] = worktree_result.returncode
    if worktree_result.returncode != 0:
        return _build_delivery_execution_blocked_payload(
            schema_version=_PUSH_EXECUTION_SCHEMA_VERSION,
            execution_type=_PUSH_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
            summary="push execution blocked because repo is not a git worktree",
            failure_reason="repo_not_git_worktree",
            blocking_reasons=["repo_not_git_worktree"],
            command_summary=command_summary,
            base_branch=base_branch,
            head_branch=head_branch,
            remote_name=remote_name,
        )

    branch_name = _resolve_current_branch(repo_path, command_summary=command_summary)
    if not branch_name:
        return _build_delivery_execution_blocked_payload(
            schema_version=_PUSH_EXECUTION_SCHEMA_VERSION,
            execution_type=_PUSH_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
            summary="push execution blocked because current branch is missing or detached",
            failure_reason="current_branch_unresolved",
            blocking_reasons=["current_branch_unresolved"],
            command_summary=command_summary,
            base_branch=base_branch,
            head_branch=head_branch,
            remote_name=remote_name,
            branch_name=branch_name,
        )
    if not head_branch:
        head_branch = branch_name

    remotes = _resolve_git_remotes(repo_path, command_summary=command_summary)
    if not remotes:
        return _build_delivery_execution_blocked_payload(
            schema_version=_PUSH_EXECUTION_SCHEMA_VERSION,
            execution_type=_PUSH_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
            summary="push execution blocked because no git remote was configured",
            failure_reason="git_remote_missing",
            blocking_reasons=["git_remote_missing"],
            command_summary=command_summary,
            base_branch=base_branch,
            head_branch=head_branch,
            remote_name=remote_name,
            branch_name=branch_name,
        )

    resolved_remote = _normalize_text(remote_name, default="origin")
    if resolved_remote not in set(remotes):
        return _build_delivery_execution_blocked_payload(
            schema_version=_PUSH_EXECUTION_SCHEMA_VERSION,
            execution_type=_PUSH_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
            summary="push execution blocked because configured remote was not found",
            failure_reason="configured_remote_missing",
            blocking_reasons=["configured_remote_missing"],
            command_summary=command_summary,
            base_branch=base_branch,
            head_branch=head_branch,
            remote_name=resolved_remote,
            branch_name=branch_name,
        )

    status_result = _run_git(repo_path, ["status", "--porcelain"])
    command_summary["status_rc"] = status_result.returncode
    if status_result.returncode != 0:
        return _build_delivery_execution_blocked_payload(
            schema_version=_PUSH_EXECUTION_SCHEMA_VERSION,
            execution_type=_PUSH_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
            summary="push execution blocked because git status failed",
            failure_reason="git_status_failed",
            blocking_reasons=["git_status_failed"],
            manual_intervention_required=True,
            command_summary=command_summary,
            base_branch=base_branch,
            head_branch=head_branch,
            remote_name=resolved_remote,
            branch_name=branch_name,
        )
    status_lines = [line.rstrip("\n") for line in (status_result.stdout or "").splitlines() if line.strip()]
    if _has_conflict_status_lines(status_lines):
        return _build_delivery_execution_blocked_payload(
            schema_version=_PUSH_EXECUTION_SCHEMA_VERSION,
            execution_type=_PUSH_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
            summary="push execution blocked because merge conflicts were detected",
            failure_reason="working_tree_conflicts_present",
            blocking_reasons=["working_tree_conflicts_present"],
            manual_intervention_required=True,
            command_summary=command_summary,
            base_branch=base_branch,
            head_branch=head_branch,
            remote_name=resolved_remote,
            branch_name=branch_name,
        )

    upstream_result = _run_git(repo_path, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
    command_summary["upstream_ref_rc"] = upstream_result.returncode
    if upstream_result.returncode != 0:
        return _build_delivery_execution_blocked_payload(
            schema_version=_PUSH_EXECUTION_SCHEMA_VERSION,
            execution_type=_PUSH_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
            summary="push execution blocked because upstream tracking was unresolved",
            failure_reason="upstream_tracking_unresolved",
            blocking_reasons=["upstream_tracking_unresolved"],
            manual_intervention_required=True,
            command_summary=command_summary,
            base_branch=base_branch,
            head_branch=head_branch,
            remote_name=resolved_remote,
            branch_name=branch_name,
        )

    upstream_ref = _normalize_text(upstream_result.stdout, default="")
    command_summary["upstream_ref"] = upstream_ref
    if "/" not in upstream_ref:
        return _build_delivery_execution_blocked_payload(
            schema_version=_PUSH_EXECUTION_SCHEMA_VERSION,
            execution_type=_PUSH_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
            summary="push execution blocked because upstream ref was ambiguous",
            failure_reason="upstream_ref_ambiguous",
            blocking_reasons=["upstream_ref_ambiguous"],
            manual_intervention_required=True,
            command_summary=command_summary,
            base_branch=base_branch,
            head_branch=head_branch,
            remote_name=resolved_remote,
            branch_name=branch_name,
        )

    upstream_remote, _, upstream_branch = upstream_ref.partition("/")
    command_summary["upstream_remote"] = upstream_remote
    command_summary["upstream_branch"] = upstream_branch
    if not upstream_remote or not upstream_branch:
        return _build_delivery_execution_blocked_payload(
            schema_version=_PUSH_EXECUTION_SCHEMA_VERSION,
            execution_type=_PUSH_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
            summary="push execution blocked because upstream remote/branch truth was ambiguous",
            failure_reason="upstream_ref_ambiguous",
            blocking_reasons=["upstream_ref_ambiguous"],
            manual_intervention_required=True,
            command_summary=command_summary,
            base_branch=base_branch,
            head_branch=head_branch,
            remote_name=resolved_remote,
            branch_name=branch_name,
        )
    if upstream_remote != resolved_remote:
        return _build_delivery_execution_blocked_payload(
            schema_version=_PUSH_EXECUTION_SCHEMA_VERSION,
            execution_type=_PUSH_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
            summary="push execution blocked because configured remote conflicted with tracked upstream remote",
            failure_reason="upstream_remote_ambiguous",
            blocking_reasons=["upstream_remote_ambiguous"],
            manual_intervention_required=True,
            command_summary=command_summary,
            base_branch=base_branch,
            head_branch=head_branch,
            remote_name=resolved_remote,
            branch_name=branch_name,
        )

    divergence_result = _run_git(repo_path, ["rev-list", "--left-right", "--count", "HEAD...@{u}"])
    command_summary["remote_divergence_rc"] = divergence_result.returncode
    if divergence_result.returncode != 0:
        return _build_delivery_execution_blocked_payload(
            schema_version=_PUSH_EXECUTION_SCHEMA_VERSION,
            execution_type=_PUSH_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
            summary="push execution blocked because remote divergence truth was unavailable",
            failure_reason="remote_divergence_status_unavailable",
            blocking_reasons=["remote_divergence_status_unavailable"],
            manual_intervention_required=True,
            command_summary=command_summary,
            base_branch=base_branch,
            head_branch=head_branch,
            remote_name=resolved_remote,
            branch_name=branch_name,
        )

    divergence_fields = _normalize_text(divergence_result.stdout, default="").split()
    ahead_count = _as_non_negative_int(divergence_fields[0], default=0) if len(divergence_fields) >= 1 else 0
    behind_count = _as_non_negative_int(divergence_fields[1], default=0) if len(divergence_fields) >= 2 else 0
    command_summary["remote_ahead_count"] = ahead_count
    command_summary["remote_behind_count"] = behind_count
    if behind_count > 0 and ahead_count > 0:
        return _build_delivery_execution_blocked_payload(
            schema_version=_PUSH_EXECUTION_SCHEMA_VERSION,
            execution_type=_PUSH_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
            summary="push execution blocked because local and remote branches diverged",
            failure_reason="remote_branch_diverged",
            blocking_reasons=["remote_branch_diverged"],
            manual_intervention_required=True,
            command_summary=command_summary,
            base_branch=base_branch,
            head_branch=head_branch,
            remote_name=resolved_remote,
            branch_name=branch_name,
        )
    if behind_count > 0:
        return _build_delivery_execution_blocked_payload(
            schema_version=_PUSH_EXECUTION_SCHEMA_VERSION,
            execution_type=_PUSH_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
            summary="push execution blocked because non-fast-forward risk was detected",
            failure_reason="remote_non_fast_forward_risk",
            blocking_reasons=["remote_non_fast_forward_risk"],
            manual_intervention_required=True,
            command_summary=command_summary,
            base_branch=base_branch,
            head_branch=head_branch,
            remote_name=resolved_remote,
            branch_name=branch_name,
        )

    started_at = _iso_now(now)
    push_result = _run_git(repo_path, ["push", resolved_remote, f"HEAD:{head_branch}"])
    command_summary["git_push_rc"] = push_result.returncode
    if push_result.returncode != 0:
        push_text = (
            _normalize_text(push_result.stderr, default="")
            + "\n"
            + _normalize_text(push_result.stdout, default="")
        ).lower()
        if any(
            marker in push_text
            for marker in (
                "non-fast-forward",
                "fetch first",
                "rejected",
                "tip of your current branch is behind",
            )
        ):
            return _build_delivery_execution_blocked_payload(
                schema_version=_PUSH_EXECUTION_SCHEMA_VERSION,
                execution_type=_PUSH_EXECUTION_TYPE,
                unit_id=unit_id,
                now=now,
                summary="push execution blocked because non-fast-forward risk was detected during push",
                failure_reason="remote_non_fast_forward_risk",
                blocking_reasons=["remote_non_fast_forward_risk"],
                manual_intervention_required=True,
                command_summary=command_summary,
                base_branch=base_branch,
                head_branch=head_branch,
                remote_name=resolved_remote,
                branch_name=branch_name,
            )
        return {
            **_default_delivery_execution_payload(
                schema_version=_PUSH_EXECUTION_SCHEMA_VERSION,
                execution_type=_PUSH_EXECUTION_TYPE,
                unit_id=unit_id,
                now=now,
            ),
            "status": "failed",
            "summary": "push execution failed during git push",
            "started_at": started_at,
            "finished_at": _iso_now(now),
            "branch_name": branch_name,
            "remote_name": resolved_remote,
            "base_branch": base_branch,
            "head_branch": head_branch,
            "command_summary": command_summary,
            "failure_reason": "git_push_failed",
            "manual_intervention_required": True,
            "blocking_reasons": ["git_push_failed"],
            "attempted": True,
            "remote_state_status": "unknown",
            "upstream_tracking_status": "tracked",
            "remote_divergence_status": "unknown",
            "remote_branch_status": "known",
        }

    return {
        **_default_delivery_execution_payload(
            schema_version=_PUSH_EXECUTION_SCHEMA_VERSION,
            execution_type=_PUSH_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
        ),
        "status": "succeeded",
        "summary": "push execution succeeded under bounded readiness and run-state conditions",
        "started_at": started_at,
        "finished_at": _iso_now(now),
        "branch_name": branch_name,
        "remote_name": resolved_remote,
        "base_branch": base_branch,
        "head_branch": head_branch,
        "failure_reason": "",
        "blocking_reasons": [],
        "attempted": True,
        "remote_state_status": "ready",
        "upstream_tracking_status": "tracked",
        "remote_divergence_status": "none",
        "remote_branch_status": "known",
    }

def _execute_bounded_pr_creation(
    *,
    unit_id: str,
    job_id: str,
    repository: str,
    base_branch: str,
    run_state_payload: Mapping[str, Any],
    merge_decision_payload: Mapping[str, Any],
    commit_execution_payload: Mapping[str, Any],
    push_execution_payload: Mapping[str, Any],
    read_backend: Any,
    write_backend: Any,
    now: Callable[[], datetime],
) -> dict[str, Any]:
    command_summary: dict[str, Any] = {}
    branch_name = _normalize_text(push_execution_payload.get("branch_name"), default="")
    remote_name = _normalize_text(push_execution_payload.get("remote_name"), default="")
    head_branch = _normalize_text(push_execution_payload.get("head_branch"), default=branch_name)
    pr_number: int | None = None
    pr_url = ""

    blockers = _run_state_execution_blockers(run_state_payload)
    if _normalize_text(commit_execution_payload.get("status"), default="") != "succeeded":
        blockers.append("commit_execution_not_succeeded")
    if _normalize_text(push_execution_payload.get("status"), default="") != "succeeded":
        blockers.append("push_execution_not_succeeded")
    if bool(merge_decision_payload.get("manual_intervention_required", False)):
        blockers.append("merge_manual_intervention_required")
    if not repository:
        blockers.append("repository_missing")
    if not base_branch:
        blockers.append("base_branch_missing")
    if not head_branch:
        blockers.append("head_branch_missing")
    if read_backend is None:
        blockers.append("github_read_backend_unavailable")
    if write_backend is None:
        blockers.append("github_write_backend_unavailable")

    unresolved = _normalize_string_list(merge_decision_payload.get("unresolved_blockers"))
    unexpected_unresolved = [item for item in unresolved if item != "merge_not_requested"]
    if unexpected_unresolved:
        blockers.append("merge_unresolved_blockers_present")

    if blockers:
        return _build_delivery_execution_blocked_payload(
            schema_version=_PR_EXECUTION_SCHEMA_VERSION,
            execution_type=_PR_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
            summary="PR creation blocked by prerequisites or ambiguous state",
            failure_reason="pr_creation_blocked_by_preconditions",
            blocking_reasons=blockers,
            base_branch=base_branch,
            head_branch=head_branch,
            remote_name=remote_name,
            branch_name=branch_name,
        )

    lookup_status, lookup_data = _resolve_open_pr_lookup(
        read_backend=read_backend,
        repository=repository,
        head_branch=head_branch,
        base_branch=base_branch,
    )
    command_summary["open_pr_lookup_status"] = lookup_status
    if lookup_status not in {"success", "empty"}:
        return _build_delivery_execution_blocked_payload(
            schema_version=_PR_EXECUTION_SCHEMA_VERSION,
            execution_type=_PR_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
            summary="PR creation blocked because open PR state could not be resolved conservatively",
            failure_reason=f"open_pr_lookup_{lookup_status}",
            blocking_reasons=[f"open_pr_lookup_{lookup_status}"],
            manual_intervention_required=True,
            command_summary=command_summary,
            base_branch=base_branch,
            head_branch=head_branch,
            remote_name=remote_name,
            branch_name=branch_name,
        )

    matched = bool(lookup_data.get("matched", False))
    match_count = _as_non_negative_int(lookup_data.get("match_count"), default=0)
    command_summary["open_pr_match_count"] = match_count
    matched_pr = dict(lookup_data.get("pr")) if isinstance(lookup_data.get("pr"), Mapping) else {}
    if matched and match_count > 1:
        return _build_delivery_execution_blocked_payload(
            schema_version=_PR_EXECUTION_SCHEMA_VERSION,
            execution_type=_PR_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
            summary="PR creation blocked because existing PR lookup returned ambiguous multiple matches",
            failure_reason="existing_pr_lookup_ambiguous",
            blocking_reasons=["existing_pr_lookup_ambiguous"],
            manual_intervention_required=True,
            command_summary=command_summary,
            base_branch=base_branch,
            head_branch=head_branch,
            remote_name=remote_name,
            branch_name=branch_name,
        )
    if matched:
        pr_number = _as_optional_int(matched_pr.get("number"))
        pr_url = _normalize_text(matched_pr.get("html_url"), default="")
        if pr_number is None or pr_number <= 0:
            return _build_delivery_execution_blocked_payload(
                schema_version=_PR_EXECUTION_SCHEMA_VERSION,
                execution_type=_PR_EXECUTION_TYPE,
                unit_id=unit_id,
                now=now,
                summary="PR creation blocked because existing PR identity was ambiguous",
                failure_reason="existing_pr_identity_ambiguous",
                blocking_reasons=["existing_pr_identity_ambiguous"],
                manual_intervention_required=True,
                command_summary=command_summary,
                base_branch=base_branch,
                head_branch=head_branch,
                remote_name=remote_name,
                branch_name=branch_name,
                pr_number=pr_number,
                pr_url=pr_url,
            )
        return _build_delivery_execution_blocked_payload(
            schema_version=_PR_EXECUTION_SCHEMA_VERSION,
            execution_type=_PR_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
            summary="PR creation blocked because an existing open PR already matches head/base",
            failure_reason="existing_open_pr_detected",
            blocking_reasons=["existing_open_pr_detected"],
            manual_intervention_required=True,
            command_summary=command_summary,
            base_branch=base_branch,
            head_branch=head_branch,
            remote_name=remote_name,
            branch_name=branch_name,
            pr_number=pr_number,
            pr_url=pr_url,
        )

    creator = getattr(write_backend, "create_draft_pr", None)
    if not callable(creator):
        return _build_delivery_execution_blocked_payload(
            schema_version=_PR_EXECUTION_SCHEMA_VERSION,
            execution_type=_PR_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
            summary="PR creation blocked because write backend does not support draft PR creation",
            failure_reason="pr_creation_capability_missing",
            blocking_reasons=["pr_creation_capability_missing"],
            manual_intervention_required=True,
            command_summary=command_summary,
            base_branch=base_branch,
            head_branch=head_branch,
            remote_name=remote_name,
            branch_name=branch_name,
        )

    commit_sha = _normalize_text(commit_execution_payload.get("commit_sha"), default="")
    title, body = _build_pr_title_and_body(job_id=job_id, unit_id=unit_id, commit_sha=commit_sha)
    started_at = _iso_now(now)
    try:
        create_result = creator(
            repo=repository,
            title=title,
            body=body,
            head_branch=head_branch,
            base_branch=base_branch,
        )
    except Exception:
        create_result = {"status": "api_failure", "data": {}, "error": {"message": "create_pr_exception"}}
    result_map = dict(create_result) if isinstance(create_result, Mapping) else {}
    status = _normalize_text(result_map.get("status"), default="api_failure")
    command_summary["create_pr_status"] = status

    if status != "success":
        return {
            **_default_delivery_execution_payload(
                schema_version=_PR_EXECUTION_SCHEMA_VERSION,
                execution_type=_PR_EXECUTION_TYPE,
                unit_id=unit_id,
                now=now,
            ),
            "status": "failed",
            "summary": "PR creation failed during backend write operation",
            "started_at": started_at,
            "finished_at": _iso_now(now),
            "branch_name": branch_name,
            "remote_name": remote_name,
            "base_branch": base_branch,
            "head_branch": head_branch,
            "command_summary": command_summary,
            "failure_reason": f"pr_creation_failed:{status}",
            "manual_intervention_required": True,
            "blocking_reasons": [f"pr_creation_failed:{status}"],
            "attempted": True,
            "pr_creation_state_status": "failed",
            "existing_pr_status": "none",
        }

    data = dict(result_map.get("data")) if isinstance(result_map.get("data"), Mapping) else {}
    pr_data = dict(data.get("pr")) if isinstance(data.get("pr"), Mapping) else {}
    pr_number = _as_optional_int(pr_data.get("number"))
    pr_url = _normalize_text(pr_data.get("html_url"), default="")
    if pr_number is None or pr_number <= 0:
        return {
            **_default_delivery_execution_payload(
                schema_version=_PR_EXECUTION_SCHEMA_VERSION,
                execution_type=_PR_EXECUTION_TYPE,
                unit_id=unit_id,
                now=now,
            ),
            "status": "failed",
            "summary": "PR creation failed because backend response missed PR identity",
            "started_at": started_at,
            "finished_at": _iso_now(now),
            "branch_name": branch_name,
            "remote_name": remote_name,
            "base_branch": base_branch,
            "head_branch": head_branch,
            "command_summary": command_summary,
            "failure_reason": "pr_creation_identity_missing",
            "manual_intervention_required": True,
            "blocking_reasons": ["pr_creation_identity_missing"],
            "attempted": True,
            "pr_creation_state_status": "failed",
            "existing_pr_status": "none",
        }

    return {
        **_default_delivery_execution_payload(
            schema_version=_PR_EXECUTION_SCHEMA_VERSION,
            execution_type=_PR_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
        ),
        "status": "succeeded",
        "summary": "PR creation succeeded under bounded readiness and run-state conditions",
        "started_at": started_at,
        "finished_at": _iso_now(now),
        "branch_name": branch_name,
        "remote_name": remote_name,
        "base_branch": base_branch,
        "head_branch": head_branch,
        "pr_number": pr_number,
        "pr_url": pr_url,
        "command_summary": command_summary,
        "failure_reason": "",
        "manual_intervention_required": False,
        "blocking_reasons": [],
        "attempted": True,
        "existing_pr_status": "none",
        "pr_creation_state_status": "created",
    }

def _execute_bounded_merge(
    *,
    unit_id: str,
    repository: str,
    run_state_payload: Mapping[str, Any],
    merge_decision_payload: Mapping[str, Any],
    commit_execution_payload: Mapping[str, Any],
    push_execution_payload: Mapping[str, Any],
    pr_execution_payload: Mapping[str, Any],
    read_backend: Any,
    write_backend: Any,
    now: Callable[[], datetime],
) -> dict[str, Any]:
    command_summary: dict[str, Any] = {}
    branch_name = _normalize_text(push_execution_payload.get("branch_name"), default="")
    remote_name = _normalize_text(push_execution_payload.get("remote_name"), default="")
    base_branch = _normalize_text(pr_execution_payload.get("base_branch"), default="")
    head_branch = _normalize_text(pr_execution_payload.get("head_branch"), default=branch_name)
    pr_number = _as_optional_int(pr_execution_payload.get("pr_number"))

    blockers = _run_state_execution_blockers(run_state_payload)
    if _normalize_text(merge_decision_payload.get("readiness_status"), default="") != "ready":
        blockers.append("merge_readiness_not_ready")
    if not bool(merge_decision_payload.get("automation_eligible", False)):
        blockers.append("merge_automation_not_eligible")
    if bool(merge_decision_payload.get("manual_intervention_required", False)):
        blockers.append("merge_manual_intervention_required")
    if _normalize_string_list(merge_decision_payload.get("unresolved_blockers")):
        blockers.append("merge_unresolved_blockers_present")
    if not bool(merge_decision_payload.get("prerequisites_satisfied", False)):
        blockers.append("merge_prerequisites_unsatisfied")
    if _normalize_text(commit_execution_payload.get("status"), default="") != "succeeded":
        blockers.append("commit_execution_not_succeeded")
    commit_sha = _normalize_text(commit_execution_payload.get("commit_sha"), default="")
    if not commit_sha:
        blockers.append("commit_execution_commit_sha_missing")
    if _normalize_text(push_execution_payload.get("status"), default="") != "succeeded":
        blockers.append("push_execution_not_succeeded")
    if _normalize_text(pr_execution_payload.get("status"), default="") != "succeeded":
        blockers.append("pr_creation_not_succeeded")
    if pr_number is None or pr_number <= 0:
        blockers.append("pr_number_missing_or_invalid")
    if not repository:
        blockers.append("repository_missing")
    if read_backend is None:
        blockers.append("github_pr_status_summary_unavailable")
    if write_backend is None:
        blockers.append("github_write_backend_unavailable")

    pr_status_summary_data: dict[str, Any] = {}
    if read_backend is not None and pr_number is not None and pr_number > 0:
        status_getter = getattr(read_backend, "get_pr_status_summary", None)
        if not callable(status_getter):
            blockers.append("github_pr_status_summary_unavailable")
        else:
            try:
                status_summary_payload = status_getter(
                    repository,
                    pr_number=pr_number,
                )
            except Exception:
                status_summary_payload = {"status": "api_failure", "data": {}}
            status_summary_map = (
                dict(status_summary_payload)
                if isinstance(status_summary_payload, Mapping)
                else {"status": "api_failure", "data": {}}
            )
            status_summary_status = _normalize_text(status_summary_map.get("status"), default="api_failure")
            command_summary["pr_status_summary_status"] = status_summary_status
            pr_status_summary_data = (
                dict(status_summary_map.get("data"))
                if isinstance(status_summary_map.get("data"), Mapping)
                else {}
            )
            if status_summary_status != "success":
                blockers.append(f"merge_pr_status_summary_{status_summary_status}")
            else:
                pr_state = _normalize_text(pr_status_summary_data.get("pr_state"), default="")
                if pr_state and pr_state != "open":
                    blockers.append("merge_pr_not_open")
                mergeable_state = _normalize_text(pr_status_summary_data.get("mergeable_state"), default="")
                if not mergeable_state:
                    blockers.append("mergeability_unknown")
                elif mergeable_state not in {"clean"}:
                    blockers.append("mergeability_not_ready")
                checks_state = _normalize_text(pr_status_summary_data.get("checks_state"), default="")
                if checks_state != "passing":
                    blockers.append("required_checks_unsatisfied")
                review_state_status = _normalize_text(
                    pr_status_summary_data.get("review_state_status"),
                    default="",
                )
                if review_state_status in {"unsatisfied", "required", "changes_requested"}:
                    blockers.append("review_requirements_unsatisfied")
                branch_protection_status = _normalize_text(
                    pr_status_summary_data.get("branch_protection_status"),
                    default="",
                )
                if branch_protection_status in {"unsatisfied", "blocked", "required"}:
                    blockers.append("branch_protection_unsatisfied")
                command_summary["mergeable_state"] = mergeable_state
                command_summary["checks_state"] = checks_state
                if review_state_status:
                    command_summary["review_state_status"] = review_state_status
                if branch_protection_status:
                    command_summary["branch_protection_status"] = branch_protection_status

    if blockers:
        return _build_delivery_execution_blocked_payload(
            schema_version=_MERGE_EXECUTION_SCHEMA_VERSION,
            execution_type=_MERGE_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
            summary="merge execution blocked by readiness or run-level preconditions",
            failure_reason="merge_execution_blocked_by_preconditions",
            blocking_reasons=blockers,
            base_branch=base_branch,
            head_branch=head_branch,
            remote_name=remote_name,
            branch_name=branch_name,
            pr_number=pr_number,
            pr_url=_normalize_text(pr_execution_payload.get("pr_url"), default=""),
        )

    merger = getattr(write_backend, "merge_pull_request", None)
    if not callable(merger):
        return _build_delivery_execution_blocked_payload(
            schema_version=_MERGE_EXECUTION_SCHEMA_VERSION,
            execution_type=_MERGE_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
            summary="merge execution blocked because write backend does not support merge",
            failure_reason="merge_execution_capability_missing",
            blocking_reasons=["merge_execution_capability_missing"],
            manual_intervention_required=True,
            command_summary=command_summary,
            base_branch=base_branch,
            head_branch=head_branch,
            remote_name=remote_name,
            branch_name=branch_name,
            pr_number=pr_number,
            pr_url=_normalize_text(pr_execution_payload.get("pr_url"), default=""),
        )

    started_at = _iso_now(now)
    try:
        merge_result = merger(
            repo=repository,
            pr_number=pr_number,
            expected_head_sha=commit_sha,
        )
    except Exception:
        merge_result = {"status": "api_failure", "data": {}, "error": {"message": "merge_exception"}}

    result_map = dict(merge_result) if isinstance(merge_result, Mapping) else {}
    status = _normalize_text(result_map.get("status"), default="api_failure")
    command_summary["merge_status"] = status
    if status != "success":
        return {
            **_default_delivery_execution_payload(
                schema_version=_MERGE_EXECUTION_SCHEMA_VERSION,
                execution_type=_MERGE_EXECUTION_TYPE,
                unit_id=unit_id,
                now=now,
            ),
            "status": "failed",
            "summary": "merge execution failed during backend merge operation",
            "started_at": started_at,
            "finished_at": _iso_now(now),
            "branch_name": branch_name,
            "remote_name": remote_name,
            "base_branch": base_branch,
            "head_branch": head_branch,
            "pr_number": pr_number,
            "pr_url": _normalize_text(pr_execution_payload.get("pr_url"), default=""),
            "command_summary": command_summary,
            "failure_reason": f"merge_execution_failed:{status}",
            "manual_intervention_required": True,
            "blocking_reasons": [f"merge_execution_failed:{status}"],
            "attempted": True,
            "mergeability_status": _normalize_text(
                pr_status_summary_data.get("mergeable_state"),
                default="unknown",
            ),
            "required_checks_status": _normalize_text(
                pr_status_summary_data.get("checks_state"),
                default="unknown",
            ),
            "review_state_status": _normalize_text(
                pr_status_summary_data.get("review_state_status"),
                default="unknown",
            ),
            "branch_protection_status": _normalize_text(
                pr_status_summary_data.get("branch_protection_status"),
                default="unknown",
            ),
            "merge_requirements_status": "unknown",
        }

    data = dict(result_map.get("data")) if isinstance(result_map.get("data"), Mapping) else {}
    merge_commit_sha = _normalize_text(data.get("merge_commit_sha"), default="")
    if not merge_commit_sha:
        return {
            **_default_delivery_execution_payload(
                schema_version=_MERGE_EXECUTION_SCHEMA_VERSION,
                execution_type=_MERGE_EXECUTION_TYPE,
                unit_id=unit_id,
                now=now,
            ),
            "status": "failed",
            "summary": "merge execution failed because backend response missed merge commit sha",
            "started_at": started_at,
            "finished_at": _iso_now(now),
            "branch_name": branch_name,
            "remote_name": remote_name,
            "base_branch": base_branch,
            "head_branch": head_branch,
            "pr_number": pr_number,
            "pr_url": _normalize_text(pr_execution_payload.get("pr_url"), default=""),
            "command_summary": command_summary,
            "failure_reason": "merge_commit_sha_missing",
            "manual_intervention_required": True,
            "blocking_reasons": ["merge_commit_sha_missing"],
            "attempted": True,
            "mergeability_status": _normalize_text(
                pr_status_summary_data.get("mergeable_state"),
                default="unknown",
            ),
            "required_checks_status": _normalize_text(
                pr_status_summary_data.get("checks_state"),
                default="unknown",
            ),
            "review_state_status": _normalize_text(
                pr_status_summary_data.get("review_state_status"),
                default="unknown",
            ),
            "branch_protection_status": _normalize_text(
                pr_status_summary_data.get("branch_protection_status"),
                default="unknown",
            ),
            "merge_requirements_status": "unknown",
        }

    return {
        **_default_delivery_execution_payload(
            schema_version=_MERGE_EXECUTION_SCHEMA_VERSION,
            execution_type=_MERGE_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
        ),
        "status": "succeeded",
        "summary": "merge execution succeeded under bounded readiness and run-state conditions",
        "started_at": started_at,
        "finished_at": _iso_now(now),
        "branch_name": branch_name,
        "remote_name": remote_name,
        "base_branch": base_branch,
        "head_branch": head_branch,
        "pr_number": pr_number,
        "pr_url": _normalize_text(pr_execution_payload.get("pr_url"), default=""),
        "merge_commit_sha": merge_commit_sha,
        "command_summary": command_summary,
        "failure_reason": "",
        "manual_intervention_required": False,
        "blocking_reasons": [],
        "attempted": True,
        "mergeability_status": _normalize_text(
            pr_status_summary_data.get("mergeable_state"),
            default="clean",
        ),
        "required_checks_status": _normalize_text(
            pr_status_summary_data.get("checks_state"),
            default="passing",
        ),
        "review_state_status": _normalize_text(
            pr_status_summary_data.get("review_state_status"),
            default="unknown",
        ),
        "branch_protection_status": _normalize_text(
            pr_status_summary_data.get("branch_protection_status"),
            default="unknown",
        ),
        "merge_requirements_status": "satisfied",
    }

def _merge_prompt360_surface_into_approved_restart_execution_contract(
    *,
    approved_restart_execution_contract_payload: Mapping[str, Any] | None,
    prompt360_gate_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = (
        dict(approved_restart_execution_contract_payload)
        if isinstance(approved_restart_execution_contract_payload, Mapping)
        else {}
    )
    prompt360 = dict(prompt360_gate_payload) if isinstance(prompt360_gate_payload, Mapping) else {}
    for key in _PROMPT360_APPROVED_RESTART_SURFACE_KEYS:
        if key in prompt360 and prompt360.get(key) is not None:
            payload[key] = prompt360.get(key)
    supporting_refs = _serialize_required_signals(
        [
            *(
                payload.get("supporting_compact_truth_refs")
                if isinstance(payload.get("supporting_compact_truth_refs"), list)
                else []
            ),
            "approved_restart_execution_contract.prompt360_gate_status"
            if _normalize_text(prompt360.get("prompt360_gate_status"), default="")
            else "",
            "approved_restart_execution_contract.prompt360_next_action"
            if _normalize_text(prompt360.get("prompt360_next_action"), default="")
            else "",
            "approved_restart_execution_contract.prompt360_safe_live_helper_found"
            if bool(prompt360.get("prompt360_safe_live_helper_found", False))
            else "",
            "approved_restart_execution_contract.prompt360_bounded_prompt_source_path"
            if _normalize_text(
                prompt360.get("prompt360_bounded_prompt_source_path"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt360_execution_receipt_path"
            if _normalize_text(
                prompt360.get("prompt360_execution_receipt_path"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt360_recovered_prompt359_evidence_used"
            if bool(prompt360.get("prompt360_recovered_prompt359_evidence_used", False))
            else "",
            "approved_restart_execution_contract.prompt360_recovered_prompt359_source"
            if _normalize_text(
                prompt360.get("prompt360_recovered_prompt359_source"),
                default="",
            )
            else "",
        ]
    )
    payload["supporting_compact_truth_refs"] = supporting_refs
    return payload

def _merge_prompt361_surface_into_approved_restart_execution_contract(
    *,
    approved_restart_execution_contract_payload: Mapping[str, Any] | None,
    prompt361_diff_capture_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = (
        dict(approved_restart_execution_contract_payload)
        if isinstance(approved_restart_execution_contract_payload, Mapping)
        else {}
    )
    prompt361 = (
        dict(prompt361_diff_capture_payload)
        if isinstance(prompt361_diff_capture_payload, Mapping)
        else {}
    )
    for key in _PROMPT361_APPROVED_RESTART_SURFACE_KEYS:
        if key in prompt361 and prompt361.get(key) is not None:
            payload[key] = prompt361.get(key)
    supporting_refs = _serialize_required_signals(
        [
            *(
                payload.get("supporting_compact_truth_refs")
                if isinstance(payload.get("supporting_compact_truth_refs"), list)
                else []
            ),
            "approved_restart_execution_contract.prompt361_diff_capture_status"
            if _normalize_text(prompt361.get("prompt361_diff_capture_status"), default="")
            else "",
            "approved_restart_execution_contract.prompt361_next_action"
            if _normalize_text(prompt361.get("prompt361_next_action"), default="")
            else "",
            "approved_restart_execution_contract.prompt361_patch_path"
            if _normalize_text(prompt361.get("prompt361_patch_path"), default="")
            else "",
            "approved_restart_execution_contract.prompt361_diff_report_path"
            if _normalize_text(
                prompt361.get("prompt361_diff_report_path"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt361_review_handoff_ready"
            if bool(prompt361.get("prompt361_review_handoff_ready", False))
            else "",
            "approved_restart_execution_contract.prompt361_recovered_prompt360_evidence_used"
            if bool(prompt361.get("prompt361_recovered_prompt360_evidence_used", False))
            else "",
            "approved_restart_execution_contract.prompt361_prompt360_source_path"
            if _normalize_text(
                prompt361.get("prompt361_prompt360_source_path"),
                default="",
            )
            else "",
        ]
    )
    payload["supporting_compact_truth_refs"] = supporting_refs
    return payload

def _merge_prompt362_surface_into_approved_restart_execution_contract(
    *,
    approved_restart_execution_contract_payload: Mapping[str, Any] | None,
    prompt362_review_route_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = (
        dict(approved_restart_execution_contract_payload)
        if isinstance(approved_restart_execution_contract_payload, Mapping)
        else {}
    )
    prompt362 = (
        dict(prompt362_review_route_payload)
        if isinstance(prompt362_review_route_payload, Mapping)
        else {}
    )
    for key in _PROMPT362_APPROVED_RESTART_SURFACE_KEYS:
        if key in prompt362 and prompt362.get(key) is not None:
            payload[key] = prompt362.get(key)
    supporting_refs = _serialize_required_signals(
        [
            *(
                payload.get("supporting_compact_truth_refs")
                if isinstance(payload.get("supporting_compact_truth_refs"), list)
                else []
            ),
            "approved_restart_execution_contract.prompt362_review_status"
            if _normalize_text(prompt362.get("prompt362_review_status"), default="")
            else "",
            "approved_restart_execution_contract.prompt362_route_decision"
            if _normalize_text(prompt362.get("prompt362_route_decision"), default="")
            else "",
            "approved_restart_execution_contract.prompt362_next_action"
            if _normalize_text(prompt362.get("prompt362_next_action"), default="")
            else "",
            "approved_restart_execution_contract.prompt362_prompt361_source_path"
            if _normalize_text(
                prompt362.get("prompt362_prompt361_source_path"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt362_recovered_prompt361_evidence_used"
            if bool(prompt362.get("prompt362_recovered_prompt361_evidence_used", False))
            else "",
            "approved_restart_execution_contract.prompt362_requires_targeted_fix"
            if bool(prompt362.get("prompt362_requires_targeted_fix", False))
            else "",
            "approved_restart_execution_contract.prompt362_approve_commit_tag_ready"
            if bool(prompt362.get("prompt362_approve_commit_tag_ready", False))
            else "",
            "approved_restart_execution_contract.prompt362_no_change_review_ready"
            if bool(prompt362.get("prompt362_no_change_review_ready", False))
            else "",
        ]
    )
    payload["supporting_compact_truth_refs"] = supporting_refs
    return payload

def _merge_prompt374_surface_into_approved_restart_execution_contract(
    *,
    approved_restart_execution_contract_payload: Mapping[str, Any] | None,
    prompt374_post_execution_diff_capture_handoff_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = (
        dict(approved_restart_execution_contract_payload)
        if isinstance(approved_restart_execution_contract_payload, Mapping)
        else {}
    )
    prompt374 = (
        dict(prompt374_post_execution_diff_capture_handoff_payload)
        if isinstance(prompt374_post_execution_diff_capture_handoff_payload, Mapping)
        else {}
    )
    for key in _PROMPT374_APPROVED_RESTART_SURFACE_KEYS:
        if key in prompt374 and prompt374.get(key) is not None:
            payload[key] = prompt374.get(key)
    supporting_refs = _serialize_required_signals(
        [
            *(
                payload.get("supporting_compact_truth_refs")
                if isinstance(payload.get("supporting_compact_truth_refs"), list)
                else []
            ),
            "approved_restart_execution_contract.prompt374_post_execution_diff_capture_status"
            if _normalize_text(
                prompt374.get("prompt374_post_execution_diff_capture_status"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt374_prompt373_execution_evidence_ready"
            if bool(
                prompt374.get(
                    "prompt374_prompt373_execution_evidence_ready",
                    False,
                )
            )
            else "",
            "approved_restart_execution_contract.prompt374_tracked_diff_capture_ready"
            if bool(
                prompt374.get("prompt374_tracked_diff_capture_ready", False)
            )
            else "",
            "approved_restart_execution_contract.prompt374_post_execution_diff_classification"
            if _normalize_text(
                prompt374.get("prompt374_post_execution_diff_classification"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt374_review_route"
            if _normalize_text(prompt374.get("prompt374_review_route"), default="")
            else "",
            "approved_restart_execution_contract.prompt374_review_route_handoff_ready"
            if bool(prompt374.get("prompt374_review_route_handoff_ready", False))
            else "",
            "approved_restart_execution_contract.prompt374_next_action"
            if _normalize_text(prompt374.get("prompt374_next_action"), default="")
            else "",
        ]
    )
    payload["supporting_compact_truth_refs"] = supporting_refs
    return payload

def _merge_prompt375_surface_into_approved_restart_execution_contract(
    *,
    approved_restart_execution_contract_payload: Mapping[str, Any] | None,
    prompt375_no_diff_review_route_decision_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = (
        dict(approved_restart_execution_contract_payload)
        if isinstance(approved_restart_execution_contract_payload, Mapping)
        else {}
    )
    prompt375 = (
        dict(prompt375_no_diff_review_route_decision_payload)
        if isinstance(prompt375_no_diff_review_route_decision_payload, Mapping)
        else {}
    )
    for key in _PROMPT375_APPROVED_RESTART_SURFACE_KEYS:
        if key in prompt375 and prompt375.get(key) is not None:
            payload[key] = prompt375.get(key)
    supporting_refs = _serialize_required_signals(
        [
            *(
                payload.get("supporting_compact_truth_refs")
                if isinstance(payload.get("supporting_compact_truth_refs"), list)
                else []
            ),
            "approved_restart_execution_contract.prompt375_no_diff_review_route_decision_status"
            if _normalize_text(
                prompt375.get("prompt375_no_diff_review_route_decision_status"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt375_prompt374_evidence_ready"
            if bool(prompt375.get("prompt375_prompt374_evidence_ready", False))
            else "",
            "approved_restart_execution_contract.prompt375_no_diff_confirmed"
            if bool(prompt375.get("prompt375_no_diff_confirmed", False))
            else "",
            "approved_restart_execution_contract.prompt375_review_decision"
            if _normalize_text(prompt375.get("prompt375_review_decision"), default="")
            else "",
            "approved_restart_execution_contract.prompt375_cycle_continuation_allowed"
            if bool(prompt375.get("prompt375_cycle_continuation_allowed", False))
            else "",
            "approved_restart_execution_contract.prompt375_cycle_continuation_handoff_ready"
            if bool(
                prompt375.get("prompt375_cycle_continuation_handoff_ready", False)
            )
            else "",
            "approved_restart_execution_contract.prompt375_next_action"
            if _normalize_text(prompt375.get("prompt375_next_action"), default="")
            else "",
        ]
    )
    payload["supporting_compact_truth_refs"] = supporting_refs
    return payload

def _merge_prompt376_surface_into_approved_restart_execution_contract(
    *,
    approved_restart_execution_contract_payload: Mapping[str, Any] | None,
    prompt376_no_diff_cycle_continuation_handoff_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = (
        dict(approved_restart_execution_contract_payload)
        if isinstance(approved_restart_execution_contract_payload, Mapping)
        else {}
    )
    prompt376 = (
        dict(prompt376_no_diff_cycle_continuation_handoff_payload)
        if isinstance(prompt376_no_diff_cycle_continuation_handoff_payload, Mapping)
        else {}
    )
    for key in _PROMPT376_APPROVED_RESTART_SURFACE_KEYS:
        if key in prompt376 and prompt376.get(key) is not None:
            payload[key] = prompt376.get(key)
    supporting_refs = _serialize_required_signals(
        [
            *(
                payload.get("supporting_compact_truth_refs")
                if isinstance(payload.get("supporting_compact_truth_refs"), list)
                else []
            ),
            "approved_restart_execution_contract.prompt376_no_diff_cycle_continuation_status"
            if _normalize_text(
                prompt376.get("prompt376_no_diff_cycle_continuation_status"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt376_prompt375_evidence_ready"
            if bool(prompt376.get("prompt376_prompt375_evidence_ready", False))
            else "",
            "approved_restart_execution_contract.prompt376_no_diff_continuation_confirmed"
            if bool(prompt376.get("prompt376_no_diff_continuation_confirmed", False))
            else "",
            "approved_restart_execution_contract.prompt376_next_cycle_allowed"
            if bool(prompt376.get("prompt376_next_cycle_allowed", False))
            else "",
            "approved_restart_execution_contract.prompt376_next_cycle_contract_ready"
            if bool(prompt376.get("prompt376_next_cycle_contract_ready", False))
            else "",
            "approved_restart_execution_contract.prompt376_chatgpt_prompt_generation_request_allowed"
            if bool(
                prompt376.get(
                    "prompt376_chatgpt_prompt_generation_request_allowed",
                    False,
                )
            )
            else "",
            "approved_restart_execution_contract.prompt376_cycle_limit_reached"
            if bool(prompt376.get("prompt376_cycle_limit_reached", False))
            else "",
            "approved_restart_execution_contract.prompt376_next_action"
            if _normalize_text(prompt376.get("prompt376_next_action"), default="")
            else "",
        ]
    )
    payload["supporting_compact_truth_refs"] = supporting_refs
    return payload

def _merge_prompt377_surface_into_approved_restart_execution_contract(
    *,
    approved_restart_execution_contract_payload: Mapping[str, Any] | None,
    prompt377_chatgpt_prompt_generation_request_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = (
        dict(approved_restart_execution_contract_payload)
        if isinstance(approved_restart_execution_contract_payload, Mapping)
        else {}
    )
    prompt377 = (
        dict(prompt377_chatgpt_prompt_generation_request_payload)
        if isinstance(prompt377_chatgpt_prompt_generation_request_payload, Mapping)
        else {}
    )
    for key in _PROMPT377_APPROVED_RESTART_SURFACE_KEYS:
        if key in prompt377 and prompt377.get(key) is not None:
            payload[key] = prompt377.get(key)
    supporting_refs = _serialize_required_signals(
        [
            *(
                payload.get("supporting_compact_truth_refs")
                if isinstance(payload.get("supporting_compact_truth_refs"), list)
                else []
            ),
            "approved_restart_execution_contract.prompt377_chatgpt_prompt_generation_request_status"
            if _normalize_text(
                prompt377.get("prompt377_chatgpt_prompt_generation_request_status"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt377_prompt376_evidence_ready"
            if bool(prompt377.get("prompt377_prompt376_evidence_ready", False))
            else "",
            "approved_restart_execution_contract.prompt377_chatgpt_prompt_generation_request_ready"
            if bool(
                prompt377.get(
                    "prompt377_chatgpt_prompt_generation_request_ready",
                    False,
                )
            )
            else "",
            "approved_restart_execution_contract.prompt377_generated_prompt_intake_contract_ready"
            if bool(
                prompt377.get(
                    "prompt377_generated_prompt_intake_contract_ready",
                    False,
                )
            )
            else "",
            "approved_restart_execution_contract.prompt377_generated_prompt_validation_contract_ready"
            if bool(
                prompt377.get(
                    "prompt377_generated_prompt_validation_contract_ready",
                    False,
                )
            )
            else "",
            "approved_restart_execution_contract.prompt377_next_action"
            if _normalize_text(prompt377.get("prompt377_next_action"), default="")
            else "",
        ]
    )
    payload["supporting_compact_truth_refs"] = supporting_refs
    return payload

def _merge_prompt378_surface_into_approved_restart_execution_contract(
    *,
    approved_restart_execution_contract_payload: Mapping[str, Any] | None,
    prompt378_chatgpt_generated_prompt_intake_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = (
        dict(approved_restart_execution_contract_payload)
        if isinstance(approved_restart_execution_contract_payload, Mapping)
        else {}
    )
    prompt378 = (
        dict(prompt378_chatgpt_generated_prompt_intake_payload)
        if isinstance(prompt378_chatgpt_generated_prompt_intake_payload, Mapping)
        else {}
    )
    for key in _PROMPT378_APPROVED_RESTART_SURFACE_KEYS:
        if key in prompt378 and prompt378.get(key) is not None:
            payload[key] = prompt378.get(key)
    supporting_refs = _serialize_required_signals(
        [
            *(
                payload.get("supporting_compact_truth_refs")
                if isinstance(payload.get("supporting_compact_truth_refs"), list)
                else []
            ),
            "approved_restart_execution_contract.prompt378_chatgpt_generated_prompt_intake_status"
            if _normalize_text(
                prompt378.get("prompt378_chatgpt_generated_prompt_intake_status"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt378_prompt377_evidence_ready"
            if bool(prompt378.get("prompt378_prompt377_evidence_ready", False))
            else "",
            "approved_restart_execution_contract.prompt378_generated_prompt_supplied"
            if bool(prompt378.get("prompt378_generated_prompt_supplied", False))
            else "",
            "approved_restart_execution_contract.prompt378_generated_prompt_ready"
            if bool(prompt378.get("prompt378_generated_prompt_ready", False))
            else "",
            "approved_restart_execution_contract.prompt378_generated_prompt_execution_handoff_ready"
            if bool(
                prompt378.get("prompt378_generated_prompt_execution_handoff_ready", False)
            )
            else "",
            "approved_restart_execution_contract.prompt378_next_action"
            if _normalize_text(prompt378.get("prompt378_next_action"), default="")
            else "",
        ]
    )
    payload["supporting_compact_truth_refs"] = supporting_refs
    return payload

def _merge_prompt383_surface_into_approved_restart_execution_contract(
    *,
    approved_restart_execution_contract_payload: Mapping[str, Any] | None,
    prompt383_explicit_approve_commit_tag_execution_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = (
        dict(approved_restart_execution_contract_payload)
        if isinstance(approved_restart_execution_contract_payload, Mapping)
        else {}
    )
    prompt383 = (
        dict(prompt383_explicit_approve_commit_tag_execution_payload)
        if isinstance(prompt383_explicit_approve_commit_tag_execution_payload, Mapping)
        else {}
    )
    for key in _PROMPT383_APPROVED_RESTART_SURFACE_KEYS:
        if key in prompt383 and prompt383.get(key) is not None:
            payload[key] = prompt383.get(key)
    supporting_refs = _serialize_required_signals(
        [
            *(
                payload.get("supporting_compact_truth_refs")
                if isinstance(payload.get("supporting_compact_truth_refs"), list)
                else []
            ),
            "approved_restart_execution_contract.prompt383_explicit_approve_commit_tag_execution_status"
            if _normalize_text(
                prompt383.get("prompt383_explicit_approve_commit_tag_execution_status"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt383_prompt382_evidence_ready"
            if bool(prompt383.get("prompt383_prompt382_evidence_ready", False))
            else "",
            "approved_restart_execution_contract.prompt383_prompt382_plan_ready"
            if bool(prompt383.get("prompt383_prompt382_plan_ready", False))
            else "",
            "approved_restart_execution_contract.prompt383_prompt382_execution_ready"
            if bool(prompt383.get("prompt383_prompt382_execution_ready", False))
            else "",
            "approved_restart_execution_contract.prompt383_execution_ready"
            if bool(prompt383.get("prompt383_execution_ready", False))
            else "",
            "approved_restart_execution_contract.prompt383_execution_allowed"
            if bool(prompt383.get("prompt383_execution_allowed", False))
            else "",
            "approved_restart_execution_contract.prompt383_execution_attempted"
            if bool(prompt383.get("prompt383_execution_attempted", False))
            else "",
            "approved_restart_execution_contract.prompt383_execution_performed"
            if bool(prompt383.get("prompt383_execution_performed", False))
            else "",
            "approved_restart_execution_contract.prompt383_git_tag_performed"
            if bool(prompt383.get("prompt383_git_tag_performed", False))
            else "",
            "approved_restart_execution_contract.prompt383_remote_mutation_performed"
            if bool(prompt383.get("prompt383_remote_mutation_performed", False))
            else "",
            "approved_restart_execution_contract.prompt383_next_action"
            if _normalize_text(prompt383.get("prompt383_next_action"), default="")
            else "",
        ]
    )
    payload["supporting_compact_truth_refs"] = supporting_refs
    return payload

def _merge_prompt384_surface_into_approved_restart_execution_contract(
    *,
    approved_restart_execution_contract_payload: Mapping[str, Any] | None,
    prompt384_commit_tag_reconciliation_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = (
        dict(approved_restart_execution_contract_payload)
        if isinstance(approved_restart_execution_contract_payload, Mapping)
        else {}
    )
    prompt384 = (
        dict(prompt384_commit_tag_reconciliation_payload)
        if isinstance(prompt384_commit_tag_reconciliation_payload, Mapping)
        else {}
    )
    for key in _PROMPT384_APPROVED_RESTART_SURFACE_KEYS:
        if key in prompt384 and prompt384.get(key) is not None:
            payload[key] = prompt384.get(key)
    supporting_refs = _serialize_required_signals(
        [
            *(
                payload.get("supporting_compact_truth_refs")
                if isinstance(payload.get("supporting_compact_truth_refs"), list)
                else []
            ),
            "approved_restart_execution_contract.prompt384_commit_tag_reconciliation_status"
            if _normalize_text(
                prompt384.get("prompt384_commit_tag_reconciliation_status"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt384_prompt383_evidence_ready"
            if bool(prompt384.get("prompt384_prompt383_evidence_ready", False))
            else "",
            "approved_restart_execution_contract.prompt384_reconciliation_attempted"
            if bool(prompt384.get("prompt384_reconciliation_attempted", False))
            else "",
            "approved_restart_execution_contract.prompt384_reconciliation_performed"
            if bool(prompt384.get("prompt384_reconciliation_performed", False))
            else "",
            "approved_restart_execution_contract.prompt384_tag_points_at_head"
            if bool(prompt384.get("prompt384_tag_points_at_head", False))
            else "",
            "approved_restart_execution_contract.prompt384_worktree_tracked_clean"
            if bool(prompt384.get("prompt384_worktree_tracked_clean", False))
            else "",
            "approved_restart_execution_contract.prompt384_index_clean"
            if bool(prompt384.get("prompt384_index_clean", False))
            else "",
            "approved_restart_execution_contract.prompt384_committed_files_match_prompt383"
            if bool(
                prompt384.get("prompt384_committed_files_match_prompt383", False)
            )
            else "",
            "approved_restart_execution_contract.prompt384_success_cycle_closed"
            if bool(prompt384.get("prompt384_success_cycle_closed", False))
            else "",
            "approved_restart_execution_contract.prompt384_next_action"
            if _normalize_text(prompt384.get("prompt384_next_action"), default="")
            else "",
        ]
    )
    payload["supporting_compact_truth_refs"] = supporting_refs
    return payload

def _merge_prompt385_surface_into_approved_restart_execution_contract(
    *,
    approved_restart_execution_contract_payload: Mapping[str, Any] | None,
    prompt385_success_path_next_cycle_handoff_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = (
        dict(approved_restart_execution_contract_payload)
        if isinstance(approved_restart_execution_contract_payload, Mapping)
        else {}
    )
    prompt385 = (
        dict(prompt385_success_path_next_cycle_handoff_payload)
        if isinstance(prompt385_success_path_next_cycle_handoff_payload, Mapping)
        else {}
    )
    for key in _PROMPT385_APPROVED_RESTART_SURFACE_KEYS:
        if key in prompt385 and prompt385.get(key) is not None:
            payload[key] = prompt385.get(key)
    supporting_refs = _serialize_required_signals(
        [
            *(
                payload.get("supporting_compact_truth_refs")
                if isinstance(payload.get("supporting_compact_truth_refs"), list)
                else []
            ),
            "approved_restart_execution_contract.prompt385_success_path_next_cycle_handoff_status"
            if _normalize_text(
                prompt385.get("prompt385_success_path_next_cycle_handoff_status"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt385_prompt384_evidence_ready"
            if bool(prompt385.get("prompt385_prompt384_evidence_ready", False))
            else "",
            "approved_restart_execution_contract.prompt385_prompt384_success_cycle_closure_ready"
            if bool(
                prompt385.get(
                    "prompt385_prompt384_success_cycle_closure_ready",
                    False,
                )
            )
            else "",
            "approved_restart_execution_contract.prompt385_prompt384_success_cycle_closed"
            if bool(prompt385.get("prompt385_prompt384_success_cycle_closed", False))
            else "",
            "approved_restart_execution_contract.prompt385_next_cycle_handoff_ready"
            if bool(prompt385.get("prompt385_next_cycle_handoff_ready", False))
            else "",
            "approved_restart_execution_contract.prompt385_next_cycle_contract_ready"
            if bool(prompt385.get("prompt385_next_cycle_contract_ready", False))
            else "",
            "approved_restart_execution_contract.prompt385_next_prompt_generation_request_ready"
            if bool(
                prompt385.get(
                    "prompt385_next_prompt_generation_request_ready",
                    False,
                )
            )
            else "",
            "approved_restart_execution_contract.prompt385_generated_prompt_intake_expected"
            if bool(
                prompt385.get("prompt385_generated_prompt_intake_expected", False)
            )
            else "",
            "approved_restart_execution_contract.prompt385_next_action"
            if _normalize_text(prompt385.get("prompt385_next_action"), default="")
            else "",
        ]
    )
    payload["supporting_compact_truth_refs"] = supporting_refs
    return payload

def _merge_prompt386_surface_into_approved_restart_execution_contract(
    *,
    approved_restart_execution_contract_payload: Mapping[str, Any] | None,
    prompt386_success_path_bounded_loop_controller_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = (
        dict(approved_restart_execution_contract_payload)
        if isinstance(approved_restart_execution_contract_payload, Mapping)
        else {}
    )
    prompt386 = (
        dict(prompt386_success_path_bounded_loop_controller_payload)
        if isinstance(prompt386_success_path_bounded_loop_controller_payload, Mapping)
        else {}
    )
    for key in _PROMPT386_APPROVED_RESTART_SURFACE_KEYS:
        if key in prompt386 and prompt386.get(key) is not None:
            payload[key] = prompt386.get(key)
    supporting_refs = _serialize_required_signals(
        [
            *(
                payload.get("supporting_compact_truth_refs")
                if isinstance(payload.get("supporting_compact_truth_refs"), list)
                else []
            ),
            "approved_restart_execution_contract.prompt386_success_path_bounded_loop_controller_status"
            if _normalize_text(
                prompt386.get(
                    "prompt386_success_path_bounded_loop_controller_status"
                ),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt386_prompt385_evidence_ready"
            if bool(prompt386.get("prompt386_prompt385_evidence_ready", False))
            else "",
            "approved_restart_execution_contract.prompt386_prompt385_next_cycle_handoff_ready"
            if bool(
                prompt386.get("prompt386_prompt385_next_cycle_handoff_ready", False)
            )
            else "",
            "approved_restart_execution_contract.prompt386_prompt385_next_prompt_generation_request_ready"
            if bool(
                prompt386.get(
                    "prompt386_prompt385_next_prompt_generation_request_ready",
                    False,
                )
            )
            else "",
            "approved_restart_execution_contract.prompt386_prompt385_generated_prompt_intake_expected"
            if bool(
                prompt386.get(
                    "prompt386_prompt385_generated_prompt_intake_expected",
                    False,
                )
            )
            else "",
            "approved_restart_execution_contract.prompt386_loop_controller_ready"
            if bool(prompt386.get("prompt386_loop_controller_ready", False))
            else "",
            "approved_restart_execution_contract.prompt386_loop_plan_ready"
            if bool(prompt386.get("prompt386_loop_plan_ready", False))
            else "",
            "approved_restart_execution_contract.prompt386_loop_readiness_ready"
            if bool(prompt386.get("prompt386_loop_readiness_ready", False))
            else "",
            "approved_restart_execution_contract.prompt386_required_next_prompt_id"
            if _normalize_text(
                prompt386.get("prompt386_required_next_prompt_id"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt386_next_action"
            if _normalize_text(prompt386.get("prompt386_next_action"), default="")
            else "",
        ]
    )
    payload["supporting_compact_truth_refs"] = supporting_refs
    return payload

def _merge_prompt387_surface_into_approved_restart_execution_contract(
    *,
    approved_restart_execution_contract_payload: Mapping[str, Any] | None,
    prompt387_success_path_loop_dispatch_bridge_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = (
        dict(approved_restart_execution_contract_payload)
        if isinstance(approved_restart_execution_contract_payload, Mapping)
        else {}
    )
    prompt387 = (
        dict(prompt387_success_path_loop_dispatch_bridge_payload)
        if isinstance(prompt387_success_path_loop_dispatch_bridge_payload, Mapping)
        else {}
    )
    for key in _PROMPT387_APPROVED_RESTART_SURFACE_KEYS:
        if key in prompt387 and prompt387.get(key) is not None:
            payload[key] = prompt387.get(key)
    supporting_refs = _serialize_required_signals(
        [
            *(
                payload.get("supporting_compact_truth_refs")
                if isinstance(payload.get("supporting_compact_truth_refs"), list)
                else []
            ),
            "approved_restart_execution_contract.prompt387_success_path_loop_dispatch_bridge_status"
            if _normalize_text(
                prompt387.get("prompt387_success_path_loop_dispatch_bridge_status"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt387_prompt386_evidence_ready"
            if bool(prompt387.get("prompt387_prompt386_evidence_ready", False))
            else "",
            "approved_restart_execution_contract.prompt387_dispatch_bridge_ready"
            if bool(prompt387.get("prompt387_dispatch_bridge_ready", False))
            else "",
            "approved_restart_execution_contract.prompt387_dispatch_plan_ready"
            if bool(prompt387.get("prompt387_dispatch_plan_ready", False))
            else "",
            "approved_restart_execution_contract.prompt387_execution_wiring_ready"
            if bool(prompt387.get("prompt387_execution_wiring_ready", False))
            else "",
            "approved_restart_execution_contract.prompt387_required_next_prompt_id"
            if _normalize_text(
                prompt387.get("prompt387_required_next_prompt_id"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt387_next_action"
            if _normalize_text(prompt387.get("prompt387_next_action"), default="")
            else "",
        ]
    )
    payload["supporting_compact_truth_refs"] = supporting_refs
    return payload

def _merge_prompt388_surface_into_approved_restart_execution_contract(
    *,
    approved_restart_execution_contract_payload: Mapping[str, Any] | None,
    prompt388_local_success_path_autonomous_loop_completion_gate_payload: (
        Mapping[str, Any] | None
    ),
) -> dict[str, Any]:
    payload = (
        dict(approved_restart_execution_contract_payload)
        if isinstance(approved_restart_execution_contract_payload, Mapping)
        else {}
    )
    prompt388 = (
        dict(prompt388_local_success_path_autonomous_loop_completion_gate_payload)
        if isinstance(
            prompt388_local_success_path_autonomous_loop_completion_gate_payload,
            Mapping,
        )
        else {}
    )
    for key in _PROMPT388_APPROVED_RESTART_SURFACE_KEYS:
        if key in prompt388 and prompt388.get(key) is not None:
            payload[key] = prompt388.get(key)
    supporting_refs = _serialize_required_signals(
        [
            *(
                payload.get("supporting_compact_truth_refs")
                if isinstance(payload.get("supporting_compact_truth_refs"), list)
                else []
            ),
            "approved_restart_execution_contract.prompt388_local_success_path_autonomous_loop_completion_gate_status"
            if _normalize_text(
                prompt388.get(
                    "prompt388_local_success_path_autonomous_loop_completion_gate_status"
                ),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt388_prompt387_evidence_ready"
            if bool(prompt388.get("prompt388_prompt387_evidence_ready", False))
            else "",
            "approved_restart_execution_contract.prompt388_autonomous_loop_completion_gate_ready"
            if bool(
                prompt388.get(
                    "prompt388_autonomous_loop_completion_gate_ready",
                    False,
                )
            )
            else "",
            "approved_restart_execution_contract.prompt388_local_only_success_path_autonomy_complete"
            if bool(
                prompt388.get(
                    "prompt388_local_only_success_path_autonomy_complete",
                    False,
                )
            )
            else "",
            "approved_restart_execution_contract.prompt388_repeated_cycle_runner_contract_ready"
            if bool(
                prompt388.get(
                    "prompt388_repeated_cycle_runner_contract_ready",
                    False,
                )
            )
            else "",
            "approved_restart_execution_contract.prompt388_required_next_prompt_id"
            if _normalize_text(
                prompt388.get("prompt388_required_next_prompt_id"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt388_next_action"
            if _normalize_text(prompt388.get("prompt388_next_action"), default="")
            else "",
        ]
    )
    payload["supporting_compact_truth_refs"] = supporting_refs
    return payload

def _merge_prompt389_surface_into_approved_restart_execution_contract(
    *,
    approved_restart_execution_contract_payload: Mapping[str, Any] | None,
    prompt389_explicit_bounded_repeated_success_path_loop_execution_payload: (
        Mapping[str, Any] | None
    ),
) -> dict[str, Any]:
    payload = (
        dict(approved_restart_execution_contract_payload)
        if isinstance(approved_restart_execution_contract_payload, Mapping)
        else {}
    )
    prompt389 = (
        dict(prompt389_explicit_bounded_repeated_success_path_loop_execution_payload)
        if isinstance(
            prompt389_explicit_bounded_repeated_success_path_loop_execution_payload,
            Mapping,
        )
        else {}
    )
    for key in _PROMPT389_APPROVED_RESTART_SURFACE_KEYS:
        if key in prompt389 and prompt389.get(key) is not None:
            payload[key] = prompt389.get(key)
    supporting_refs = _serialize_required_signals(
        [
            *(
                payload.get("supporting_compact_truth_refs")
                if isinstance(payload.get("supporting_compact_truth_refs"), list)
                else []
            ),
            "approved_restart_execution_contract.prompt389_explicit_bounded_repeated_success_path_loop_execution_gate_status"
            if _normalize_text(
                prompt389.get(
                    "prompt389_explicit_bounded_repeated_success_path_loop_execution_gate_status"
                ),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt389_prompt388_evidence_ready"
            if bool(prompt389.get("prompt389_prompt388_evidence_ready", False))
            else "",
            "approved_restart_execution_contract.prompt389_prompt388_completion_gate_ready"
            if bool(prompt389.get("prompt389_prompt388_completion_gate_ready", False))
            else "",
            "approved_restart_execution_contract.prompt389_repeated_cycle_execution_allowed"
            if bool(prompt389.get("prompt389_repeated_cycle_execution_allowed", False))
            else "",
            "approved_restart_execution_contract.prompt389_next_action"
            if _normalize_text(prompt389.get("prompt389_next_action"), default="")
            else "",
        ]
    )
    payload["supporting_compact_truth_refs"] = supporting_refs
    return payload

def _merge_prompt390_surface_into_approved_restart_execution_contract(
    *,
    approved_restart_execution_contract_payload: Mapping[str, Any] | None,
    prompt390_prompt389_next_action_reconciliation_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = (
        dict(approved_restart_execution_contract_payload)
        if isinstance(approved_restart_execution_contract_payload, Mapping)
        else {}
    )
    prompt390 = (
        dict(prompt390_prompt389_next_action_reconciliation_payload)
        if isinstance(prompt390_prompt389_next_action_reconciliation_payload, Mapping)
        else {}
    )
    for key in _PROMPT390_APPROVED_RESTART_SURFACE_KEYS:
        if key in prompt390 and prompt390.get(key) is not None:
            payload[key] = prompt390.get(key)
    supporting_refs = _serialize_required_signals(
        [
            *(
                payload.get("supporting_compact_truth_refs")
                if isinstance(payload.get("supporting_compact_truth_refs"), list)
                else []
            ),
            "approved_restart_execution_contract.prompt390_prompt389_next_action_reconciliation_status"
            if _normalize_text(
                prompt390.get("prompt390_prompt389_next_action_reconciliation_status"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt390_prompt389_evidence_ready"
            if bool(prompt390.get("prompt390_prompt389_evidence_ready", False))
            else "",
            "approved_restart_execution_contract.prompt390_enabled_run_readiness_status"
            if _normalize_text(
                prompt390.get("prompt390_enabled_run_readiness_status"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt390_enabled_run_ready"
            if bool(prompt390.get("prompt390_enabled_run_ready", False))
            else "",
            "approved_restart_execution_contract.prompt390_prompt389_next_action_canonical"
            if _normalize_text(
                prompt390.get("prompt390_prompt389_next_action_canonical"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt390_next_action"
            if _normalize_text(prompt390.get("prompt390_next_action"), default="")
            else "",
        ]
    )
    payload["supporting_compact_truth_refs"] = supporting_refs
    return payload

def _merge_prompt363_surface_into_approved_restart_execution_contract(
    *,
    approved_restart_execution_contract_payload: Mapping[str, Any] | None,
    prompt363_approve_commit_tag_boundary_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = (
        dict(approved_restart_execution_contract_payload)
        if isinstance(approved_restart_execution_contract_payload, Mapping)
        else {}
    )
    prompt363 = (
        dict(prompt363_approve_commit_tag_boundary_payload)
        if isinstance(prompt363_approve_commit_tag_boundary_payload, Mapping)
        else {}
    )
    for key in _PROMPT363_APPROVED_RESTART_SURFACE_KEYS:
        if key in prompt363 and prompt363.get(key) is not None:
            payload[key] = prompt363.get(key)
    supporting_refs = _serialize_required_signals(
        [
            *(
                payload.get("supporting_compact_truth_refs")
                if isinstance(payload.get("supporting_compact_truth_refs"), list)
                else []
            ),
            "approved_restart_execution_contract.prompt363_boundary_status"
            if _normalize_text(prompt363.get("prompt363_boundary_status"), default="")
            else "",
            "approved_restart_execution_contract.prompt363_prompt362_source_path"
            if _normalize_text(
                prompt363.get("prompt363_prompt362_source_path"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt363_recovered_prompt362_evidence_used"
            if bool(prompt363.get("prompt363_recovered_prompt362_evidence_used", False))
            else "",
            "approved_restart_execution_contract.prompt363_approve_commit_tag_plan_ready"
            if bool(prompt363.get("prompt363_approve_commit_tag_plan_ready", False))
            else "",
            "approved_restart_execution_contract.prompt363_commit_tag_execution_allowed"
            if bool(prompt363.get("prompt363_commit_tag_execution_allowed", False))
            else "",
            "approved_restart_execution_contract.prompt363_next_action"
            if _normalize_text(prompt363.get("prompt363_next_action"), default="")
            else "",
            "approved_restart_execution_contract.prompt363_plan_path"
            if _normalize_text(prompt363.get("prompt363_plan_path"), default="")
            else "",
            "approved_restart_execution_contract.prompt363_commands_path"
            if _normalize_text(prompt363.get("prompt363_commands_path"), default="")
            else "",
        ]
    )
    payload["supporting_compact_truth_refs"] = supporting_refs
    return payload

def _merge_prompt364_surface_into_approved_restart_execution_contract(
    *,
    approved_restart_execution_contract_payload: Mapping[str, Any] | None,
    prompt364_post_commit_tag_verification_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = (
        dict(approved_restart_execution_contract_payload)
        if isinstance(approved_restart_execution_contract_payload, Mapping)
        else {}
    )
    prompt364 = (
        dict(prompt364_post_commit_tag_verification_payload)
        if isinstance(prompt364_post_commit_tag_verification_payload, Mapping)
        else {}
    )
    for key in _PROMPT364_APPROVED_RESTART_SURFACE_KEYS:
        if key in prompt364 and prompt364.get(key) is not None:
            payload[key] = prompt364.get(key)
    supporting_refs = _serialize_required_signals(
        [
            *(
                payload.get("supporting_compact_truth_refs")
                if isinstance(payload.get("supporting_compact_truth_refs"), list)
                else []
            ),
            "approved_restart_execution_contract.prompt364_verification_status"
            if _normalize_text(prompt364.get("prompt364_verification_status"), default="")
            else "",
            "approved_restart_execution_contract.prompt364_commit_tag_verified"
            if bool(prompt364.get("prompt364_commit_tag_verified", False))
            else "",
            "approved_restart_execution_contract.prompt364_head_short_sha"
            if _normalize_text(prompt364.get("prompt364_head_short_sha"), default="")
            else "",
            "approved_restart_execution_contract.prompt364_head_tag_verified"
            if bool(prompt364.get("prompt364_head_tag_verified", False))
            else "",
            "approved_restart_execution_contract.prompt364_next_cycle_handoff_ready"
            if bool(prompt364.get("prompt364_next_cycle_handoff_ready", False))
            else "",
            "approved_restart_execution_contract.prompt364_next_action"
            if _normalize_text(prompt364.get("prompt364_next_action"), default="")
            else "",
        ]
    )
    payload["supporting_compact_truth_refs"] = supporting_refs
    return payload

def _merge_prompt369_surface_into_approved_restart_execution_contract(
    *,
    approved_restart_execution_contract_payload: Mapping[str, Any] | None,
    prompt369_targeted_fix_route_integration_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = (
        dict(approved_restart_execution_contract_payload)
        if isinstance(approved_restart_execution_contract_payload, Mapping)
        else {}
    )
    prompt369 = (
        dict(prompt369_targeted_fix_route_integration_payload)
        if isinstance(prompt369_targeted_fix_route_integration_payload, Mapping)
        else {}
    )
    for key in _PROMPT369_APPROVED_RESTART_SURFACE_KEYS:
        if key in prompt369 and prompt369.get(key) is not None:
            payload[key] = prompt369.get(key)
    supporting_refs = _serialize_required_signals(
        [
            *(
                payload.get("supporting_compact_truth_refs")
                if isinstance(payload.get("supporting_compact_truth_refs"), list)
                else []
            ),
            "approved_restart_execution_contract.prompt369_targeted_fix_route_integration_status"
            if _normalize_text(
                prompt369.get("prompt369_targeted_fix_route_integration_status"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt369_prompt368_resume_ready"
            if bool(prompt369.get("prompt369_prompt368_resume_ready", False))
            else "",
            "approved_restart_execution_contract.prompt369_targeted_fix_route_integrated"
            if bool(prompt369.get("prompt369_targeted_fix_route_integrated", False))
            else "",
            "approved_restart_execution_contract.prompt369_targeted_fix_required"
            if bool(prompt369.get("prompt369_targeted_fix_required", False))
            else "",
            "approved_restart_execution_contract.prompt369_targeted_fix_reentry_contract_ready"
            if bool(
                prompt369.get(
                    "prompt369_targeted_fix_reentry_contract_ready",
                    False,
                )
            )
            else "",
            "approved_restart_execution_contract.prompt369_targeted_fix_route_integration_path"
            if _normalize_text(
                prompt369.get("prompt369_targeted_fix_route_integration_path"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt369_targeted_fix_reentry_contract_path"
            if _normalize_text(
                prompt369.get("prompt369_targeted_fix_reentry_contract_path"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt369_targeted_fix_route_receipt_path"
            if _normalize_text(
                prompt369.get("prompt369_targeted_fix_route_receipt_path"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt369_next_action"
            if _normalize_text(prompt369.get("prompt369_next_action"), default="")
            else "",
        ]
    )
    payload["supporting_compact_truth_refs"] = supporting_refs
    return payload

def _merge_prompt370_surface_into_approved_restart_execution_contract(
    *,
    approved_restart_execution_contract_payload: Mapping[str, Any] | None,
    prompt370_integrated_autonomous_cycle_runner_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = (
        dict(approved_restart_execution_contract_payload)
        if isinstance(approved_restart_execution_contract_payload, Mapping)
        else {}
    )
    prompt370 = (
        dict(prompt370_integrated_autonomous_cycle_runner_payload)
        if isinstance(prompt370_integrated_autonomous_cycle_runner_payload, Mapping)
        else {}
    )
    for key in _PROMPT370_APPROVED_RESTART_SURFACE_KEYS:
        if key in prompt370 and prompt370.get(key) is not None:
            payload[key] = prompt370.get(key)
    supporting_refs = _serialize_required_signals(
        [
            *(
                payload.get("supporting_compact_truth_refs")
                if isinstance(payload.get("supporting_compact_truth_refs"), list)
                else []
            ),
            "approved_restart_execution_contract.prompt370_integrated_autonomous_cycle_runner_status"
            if _normalize_text(
                prompt370.get("prompt370_integrated_autonomous_cycle_runner_status"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt370_prompt368_resume_ready"
            if bool(prompt370.get("prompt370_prompt368_resume_ready", False))
            else "",
            "approved_restart_execution_contract.prompt370_prompt369_route_ready"
            if bool(prompt370.get("prompt370_prompt369_route_ready", False))
            else "",
            "approved_restart_execution_contract.prompt370_dispatch_status"
            if _normalize_text(prompt370.get("prompt370_dispatch_status"), default="")
            else "",
            "approved_restart_execution_contract.prompt370_selected_route"
            if _normalize_text(prompt370.get("prompt370_selected_route"), default="")
            else "",
            "approved_restart_execution_contract.prompt370_selected_next_action"
            if _normalize_text(
                prompt370.get("prompt370_selected_next_action"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt370_next_action_dispatch_plan_path"
            if _normalize_text(
                prompt370.get("prompt370_next_action_dispatch_plan_path"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt370_dispatch_receipt_path"
            if _normalize_text(
                prompt370.get("prompt370_dispatch_receipt_path"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt370_next_action"
            if _normalize_text(prompt370.get("prompt370_next_action"), default="")
            else "",
        ]
    )
    payload["supporting_compact_truth_refs"] = supporting_refs
    return payload

def _merge_prompt371_surface_into_approved_restart_execution_contract(
    *,
    approved_restart_execution_contract_payload: Mapping[str, Any] | None,
    prompt371_bounded_one_cycle_execution_wiring_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = (
        dict(approved_restart_execution_contract_payload)
        if isinstance(approved_restart_execution_contract_payload, Mapping)
        else {}
    )
    prompt371 = (
        dict(prompt371_bounded_one_cycle_execution_wiring_payload)
        if isinstance(prompt371_bounded_one_cycle_execution_wiring_payload, Mapping)
        else {}
    )
    for key in _PROMPT371_APPROVED_RESTART_SURFACE_KEYS:
        if key in prompt371 and prompt371.get(key) is not None:
            payload[key] = prompt371.get(key)
    supporting_refs = _serialize_required_signals(
        [
            *(
                payload.get("supporting_compact_truth_refs")
                if isinstance(payload.get("supporting_compact_truth_refs"), list)
                else []
            ),
            "approved_restart_execution_contract.prompt371_bounded_one_cycle_execution_wiring_status"
            if _normalize_text(
                prompt371.get("prompt371_bounded_one_cycle_execution_wiring_status"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt371_prompt370_dispatch_ready"
            if bool(prompt371.get("prompt371_prompt370_dispatch_ready", False))
            else "",
            "approved_restart_execution_contract.prompt371_selected_route"
            if _normalize_text(prompt371.get("prompt371_selected_route"), default="")
            else "",
            "approved_restart_execution_contract.prompt371_selected_step_kind"
            if _normalize_text(
                prompt371.get("prompt371_selected_step_kind"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt371_selected_step_operation"
            if _normalize_text(
                prompt371.get("prompt371_selected_step_operation"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt371_selected_prompt_contract_id"
            if _normalize_text(
                prompt371.get("prompt371_selected_prompt_contract_id"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt371_selected_next_action"
            if _normalize_text(
                prompt371.get("prompt371_selected_next_action"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt371_one_cycle_plan_ready"
            if bool(prompt371.get("prompt371_one_cycle_plan_ready", False))
            else "",
            "approved_restart_execution_contract.prompt371_execution_gate_ready"
            if bool(prompt371.get("prompt371_execution_gate_ready", False))
            else "",
            "approved_restart_execution_contract.prompt371_one_cycle_execution_plan_path"
            if _normalize_text(
                prompt371.get("prompt371_one_cycle_execution_plan_path"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt371_selected_step_contract_path"
            if _normalize_text(
                prompt371.get("prompt371_selected_step_contract_path"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt371_execution_gate_readiness_path"
            if _normalize_text(
                prompt371.get("prompt371_execution_gate_readiness_path"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt371_wiring_receipt_path"
            if _normalize_text(
                prompt371.get("prompt371_wiring_receipt_path"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt371_next_action"
            if _normalize_text(prompt371.get("prompt371_next_action"), default="")
            else "",
        ]
    )
    payload["supporting_compact_truth_refs"] = supporting_refs
    return payload

def _merge_prompt372_surface_into_approved_restart_execution_contract(
    *,
    approved_restart_execution_contract_payload: Mapping[str, Any] | None,
    prompt372_selected_step_execution_gate_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = (
        dict(approved_restart_execution_contract_payload)
        if isinstance(approved_restart_execution_contract_payload, Mapping)
        else {}
    )
    prompt372 = (
        dict(prompt372_selected_step_execution_gate_payload)
        if isinstance(prompt372_selected_step_execution_gate_payload, Mapping)
        else {}
    )
    for key in _PROMPT372_APPROVED_RESTART_SURFACE_KEYS:
        if key in prompt372 and prompt372.get(key) is not None:
            payload[key] = prompt372.get(key)
    supporting_refs = _serialize_required_signals(
        [
            *(
                payload.get("supporting_compact_truth_refs")
                if isinstance(payload.get("supporting_compact_truth_refs"), list)
                else []
            ),
            "approved_restart_execution_contract.prompt372_selected_step_execution_gate_status"
            if _normalize_text(
                prompt372.get("prompt372_selected_step_execution_gate_status"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt372_gate_status"
            if _normalize_text(
                prompt372.get("prompt372_gate_status"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt372_prompt371_source_path"
            if _normalize_text(
                prompt372.get("prompt372_prompt371_source_path"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt372_prompt371_selected_step_contract_path"
            if _normalize_text(
                prompt372.get("prompt372_prompt371_selected_step_contract_path"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt372_prompt371_execution_gate_readiness_path"
            if _normalize_text(
                prompt372.get("prompt372_prompt371_execution_gate_readiness_path"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt372_prompt371_wiring_ready"
            if bool(prompt372.get("prompt372_prompt371_wiring_ready", False))
            else "",
            "approved_restart_execution_contract.prompt372_selected_route"
            if _normalize_text(prompt372.get("prompt372_selected_route"), default="")
            else "",
            "approved_restart_execution_contract.prompt372_selected_step_kind"
            if _normalize_text(
                prompt372.get("prompt372_selected_step_kind"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt372_selected_step_operation"
            if _normalize_text(
                prompt372.get("prompt372_selected_step_operation"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt372_selected_next_action"
            if _normalize_text(
                prompt372.get("prompt372_selected_next_action"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt372_gate_ready"
            if bool(prompt372.get("prompt372_gate_ready", False))
            else "",
            "approved_restart_execution_contract.prompt372_codex_execution_request_status"
            if _normalize_text(
                prompt372.get("prompt372_codex_execution_request_status"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt372_codex_execution_request_ready"
            if bool(
                prompt372.get("prompt372_codex_execution_request_ready", False)
            )
            else "",
            "approved_restart_execution_contract.prompt372_live_execution_preflight_ready"
            if bool(
                prompt372.get("prompt372_live_execution_preflight_ready", False)
            )
            else "",
            "approved_restart_execution_contract.prompt372_selected_step_execution_gate_path"
            if _normalize_text(
                prompt372.get("prompt372_selected_step_execution_gate_path"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt372_codex_execution_request_contract_path"
            if _normalize_text(
                prompt372.get("prompt372_codex_execution_request_contract_path"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt372_live_execution_preflight_receipt_path"
            if _normalize_text(
                prompt372.get("prompt372_live_execution_preflight_receipt_path"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt372_gate_receipt_path"
            if _normalize_text(
                prompt372.get("prompt372_gate_receipt_path"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt372_next_action"
            if _normalize_text(prompt372.get("prompt372_next_action"), default="")
            else "",
        ]
    )
    payload["supporting_compact_truth_refs"] = supporting_refs
    return payload

def _merge_prompt373_surface_into_approved_restart_execution_contract(
    *,
    approved_restart_execution_contract_payload: Mapping[str, Any] | None,
    prompt373_selected_step_live_codex_execution_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = (
        dict(approved_restart_execution_contract_payload)
        if isinstance(approved_restart_execution_contract_payload, Mapping)
        else {}
    )
    prompt373 = (
        dict(prompt373_selected_step_live_codex_execution_payload)
        if isinstance(prompt373_selected_step_live_codex_execution_payload, Mapping)
        else {}
    )
    for key in _PROMPT373_APPROVED_RESTART_SURFACE_KEYS:
        if key in prompt373 and prompt373.get(key) is not None:
            payload[key] = prompt373.get(key)
    supporting_refs = _serialize_required_signals(
        [
            *(
                payload.get("supporting_compact_truth_refs")
                if isinstance(payload.get("supporting_compact_truth_refs"), list)
                else []
            ),
            "approved_restart_execution_contract.prompt373_selected_step_live_codex_execution_status"
            if _normalize_text(
                prompt373.get("prompt373_selected_step_live_codex_execution_status"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt373_execution_status"
            if _normalize_text(
                prompt373.get("prompt373_execution_status"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt373_prompt372_preflight_ready"
            if bool(prompt373.get("prompt373_prompt372_preflight_ready", False))
            else "",
            "approved_restart_execution_contract.prompt373_live_execution_gate_ready"
            if bool(prompt373.get("prompt373_live_execution_gate_ready", False))
            else "",
            "approved_restart_execution_contract.prompt373_selected_route"
            if _normalize_text(
                prompt373.get("prompt373_selected_route"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt373_selected_step_kind"
            if _normalize_text(
                prompt373.get("prompt373_selected_step_kind"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt373_selected_step_operation"
            if _normalize_text(
                prompt373.get("prompt373_selected_step_operation"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt373_codex_execution_request_path"
            if _normalize_text(
                prompt373.get("prompt373_codex_execution_request_path"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt373_codex_execution_receipt_path"
            if _normalize_text(
                prompt373.get("prompt373_codex_execution_receipt_path"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt373_post_execution_diff_capture_handoff_path"
            if _normalize_text(
                prompt373.get("prompt373_post_execution_diff_capture_handoff_path"),
                default="",
            )
            else "",
            "approved_restart_execution_contract.prompt373_next_action"
            if _normalize_text(prompt373.get("prompt373_next_action"), default="")
            else "",
        ]
    )
    payload["supporting_compact_truth_refs"] = supporting_refs
    return payload

def _approval_delivery_noop_adapter(
    handoff_payload: Mapping[str, Any],
) -> Mapping[str, Any]:
    _ = handoff_payload
    return {
        "delivery_attempted": False,
        "delivery_outcome": "not_attempted",
        "delivery_metadata": {"adapter": "deferred_to_handoff_contract"},
    }

def _normalize_project_pr_slicing_reason_codes(
    reason_codes: list[str],
) -> list[str]:
    normalized = _serialize_required_signals(
        [
            reason
            for reason in reason_codes
            if reason in _PROJECT_PR_SLICING_REASON_CODES
        ]
    )
    ordered = [
        reason
        for reason in _PROJECT_PR_SLICING_REASON_ORDER
        if reason in normalized
    ]
    return ordered if ordered else ["pr_slices_insufficient_truth"]

def _build_project_pr_slices(
    roadmap_items: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if not roadmap_items:
        return []

    item_id_to_slice_id: dict[str, str] = {}
    slices: list[dict[str, Any]] = []
    for index, item in enumerate(roadmap_items, start=1):
        topic_theme = _normalize_text(item.get("topic_theme"), default="unknown")
        item_id = _normalize_text(item.get("roadmap_item_id"), default="")
        slice_id = f"slice_{index:02d}_{topic_theme}"
        item_id_to_slice_id[item_id] = slice_id
        slices.append(
            {
                "slice_id": slice_id,
                "order": index,
                "priority": _as_non_negative_int(item.get("priority"), default=index),
                "topic_theme": topic_theme,
                "roadmap_item_id": item_id,
                "bounded_scope_class": _normalize_text(
                    item.get("bounded_scope_class"),
                    default="unknown",
                ),
                "planning_source_status": _normalize_text(
                    item.get("planning_source_status"),
                    default="planning_summary_available",
                ),
                "blocked": bool(item.get("blocked", False)),
                "blocked_reason": _normalize_text(
                    item.get("blocked_reason"),
                    default="none",
                ),
                "one_pr_size_decision": "single_theme_single_pr",
                "insufficient_reason": _normalize_text(
                    item.get("insufficient_reason"),
                    default="",
                ),
                "prerequisite_slice_ids": [],
            }
        )
    for item, slice_entry in zip(roadmap_items, slices):
        prerequisite_ids = [
            item_id_to_slice_id[prereq_id]
            for prereq_id in item.get("prerequisite_item_ids", [])
            if prereq_id in item_id_to_slice_id
        ]
        slice_entry["prerequisite_slice_ids"] = prerequisite_ids
    return slices

def _normalize_project_pr_queue_reason_codes(
    reason_codes: list[str],
) -> list[str]:
    normalized = _serialize_required_signals(
        [
            reason
            for reason in reason_codes
            if reason in _PROJECT_PR_QUEUE_REASON_CODES
        ]
    )
    ordered = [
        reason
        for reason in _PROJECT_PR_QUEUE_REASON_ORDER
        if reason in normalized
    ]
    return ordered if ordered else ["queue_state_insufficient_truth"]

def _build_project_pr_queue_state(
    *,
    project_pr_slicing_status: str,
    project_pr_slices: list[Mapping[str, Any]],
    implementation_prompt_payload: Mapping[str, Any],
    prior_processed_slice_ids: list[str],
) -> dict[str, Any]:
    queue_status = "insufficient_truth"
    queue_reason = "queue_state_insufficient_truth"
    queue_items: list[dict[str, Any]] = []
    selected_item: dict[str, Any] = {}
    handoff_prepared = False
    handoff_payload: dict[str, Any] = {}
    processed_before = _serialize_required_signals(prior_processed_slice_ids)
    processed_set = set(processed_before)

    if project_pr_slicing_status == "available":
        ordered_slices = sorted(
            project_pr_slices,
            key=lambda item: (
                _as_non_negative_int(item.get("order"), default=0),
                _normalize_text(item.get("slice_id"), default=""),
            ),
        )
        for item in ordered_slices:
            slice_id = _normalize_text(item.get("slice_id"), default="")
            blocked = bool(item.get("blocked", False))
            processed = bool(slice_id and slice_id in processed_set)
            runnable = bool(slice_id and not blocked and not processed)
            blocked_reason = _normalize_text(item.get("blocked_reason"), default="")
            if processed and not blocked_reason:
                blocked_reason = "already_prepared"
            queue_items.append(
                {
                    "slice_id": slice_id,
                    "roadmap_item_id": _normalize_text(item.get("roadmap_item_id"), default=""),
                    "order": _as_non_negative_int(item.get("order"), default=0),
                    "blocked": blocked,
                    "processed": processed,
                    "runnable": runnable,
                    "blocked_reason": blocked_reason,
                }
            )

        if not queue_items:
            queue_status = "empty"
            queue_reason = "queue_empty"
        else:
            runnable_items = [item for item in queue_items if bool(item.get("runnable", False))]
            if not runnable_items:
                if any(bool(item.get("processed", False)) for item in queue_items):
                    queue_status = "empty"
                    queue_reason = "queue_empty"
                else:
                    queue_status = "blocked"
                    queue_reason = "queue_item_blocked"
                    selected_item = dict(queue_items[0])
            else:
                selected_item = dict(runnable_items[0])
                prompt_available = bool(implementation_prompt_payload.get("prompt_available", False))
                prompt_slice_id = _normalize_text(
                    implementation_prompt_payload.get("slice_id"),
                    default="",
                )
                selected_slice_id = _normalize_text(selected_item.get("slice_id"), default="")
                if prompt_available and prompt_slice_id == selected_slice_id:
                    queue_status = "prepared"
                    queue_reason = "queue_item_prepared"
                    handoff_prepared = True
                    handoff_payload = {
                        "slice_id": selected_slice_id,
                        "roadmap_item_id": _normalize_text(
                            selected_item.get("roadmap_item_id"),
                            default="",
                        ),
                        "order": _as_non_negative_int(
                            selected_item.get("order"),
                            default=0,
                        ),
                        "implementation_prompt_payload": dict(implementation_prompt_payload),
                    }
                else:
                    queue_status = "blocked"
                    queue_reason = "prompt_unavailable_for_selected_slice"

    queue_reason_codes = _normalize_project_pr_queue_reason_codes([queue_reason])
    selected_slice_id = _normalize_text(selected_item.get("slice_id"), default="")
    processed_after = processed_before
    if handoff_prepared and selected_slice_id:
        processed_after = _serialize_required_signals([*processed_before, selected_slice_id])
    runnable_count = sum(1 for item in queue_items if bool(item.get("runnable", False)))
    blocked_count = sum(
        1
        for item in queue_items
        if bool(item.get("blocked", False)) or bool(item.get("processed", False))
    )
    return {
        "queue_status": (
            queue_status if queue_status in _PROJECT_PR_QUEUE_STATUSES else "insufficient_truth"
        ),
        "queue_reason": queue_reason_codes[0],
        "queue_reason_codes": queue_reason_codes,
        "queue_item_count": len(queue_items),
        "queue_runnable_count": runnable_count,
        "queue_blocked_count": blocked_count,
        "queue_selected_slice_id": selected_slice_id,
        "queue_selected_roadmap_item_id": _normalize_text(
            selected_item.get("roadmap_item_id"),
            default="",
        ),
        "queue_selected_blocked": bool(selected_item.get("blocked", False)),
        "queue_handoff_prepared": bool(handoff_prepared),
        "queue_handoff_payload": handoff_payload,
        "queue_items": queue_items,
        "queue_processed_slice_ids_before": processed_before,
        "queue_processed_slice_ids_after": processed_after,
    }
