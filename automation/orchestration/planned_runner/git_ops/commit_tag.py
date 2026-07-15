from __future__ import annotations
from automation.orchestration.planned_runner.constants import *

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
from automation.orchestration.planned_runner.summaries.final_payload import (
    _with_execution_gate_surface,
)

def _build_approve_commit_tag_boundary_state(
    *,
    execution_repo_path: str,
    bounded_cycle_decision_path: Path,
    bounded_cycle_receipt_path: Path,
    terminal_summary_path: Path,
    cycle_closure_result_path: Path,
    command_file_path: Path,
) -> dict[str, Any]:
    tracked_file = _APPROVE_COMMIT_TAG_EXECUTION_TRACKED_FILE
    proposed_commit_message = _APPROVE_COMMIT_TAG_EXECUTION_COMMIT_MESSAGE
    proposed_tag = _APPROVE_COMMIT_TAG_EXECUTION_TAG_NAME
    command_path_text = str(command_file_path)

    def _read_json(path: Path) -> dict[str, Any]:
        try:
            payload = _read_json_object_if_exists(path)
        except (OSError, json.JSONDecodeError, ValueError):
            payload = None
        return dict(payload) if isinstance(payload, Mapping) else {}

    bounded_cycle_decision = _read_json(bounded_cycle_decision_path)
    terminal_summary = _read_json(terminal_summary_path)
    _ = _read_json(bounded_cycle_receipt_path)
    _ = _read_json(cycle_closure_result_path)

    activation_via_bounded_cycle = (
        _normalize_text(bounded_cycle_decision.get("status"), default="") == "completed"
        and _normalize_text(bounded_cycle_decision.get("decision"), default="") == "stop_completed"
        and bool(bounded_cycle_decision.get("bounded_cycle_complete", False))
        and bool(bounded_cycle_decision.get("safe_to_stop", False))
        and _normalize_text(bounded_cycle_decision.get("next_action"), default="") == "none"
    )
    activation_via_terminal_summary = (
        _normalize_text(terminal_summary.get("status"), default="") == "completed"
        and _normalize_text(terminal_summary.get("terminal_status"), default="") == "completed"
        and bool(terminal_summary.get("cycle_closed", False))
        and bool(terminal_summary.get("safe_to_commit_prompt_changes", False))
        and bool(terminal_summary.get("safe_to_stop", False))
        and _normalize_text(terminal_summary.get("final_next_action"), default="") == "none"
    )
    activation_condition_met = activation_via_bounded_cycle or activation_via_terminal_summary
    source = "targeted_fix_post_reentry_bounded_cycle_or_terminal_summary"
    if activation_via_bounded_cycle:
        source = "targeted_fix_post_reentry_bounded_cycle_decision"
    elif activation_via_terminal_summary:
        source = "targeted_fix_post_reentry_terminal_summary"

    base_state: dict[str, Any] = {
        "status": "blocked",
        "boundary_status": "blocked",
        "blocked_reason": "bounded_cycle_not_completed",
        "source": source,
        "bounded_cycle_decision_path": str(bounded_cycle_decision_path),
        "bounded_cycle_receipt_path": str(bounded_cycle_receipt_path),
        "terminal_summary_path": str(terminal_summary_path),
        "activation_condition_met": activation_condition_met,
        "plan_ready": False,
        "tracked_files_allowed": False,
        "changed_tracked_files": [],
        "unexpected_tracked_files": [],
        "explicit_add_paths": [],
        "proposed_commit_message": proposed_commit_message,
        "proposed_tag": proposed_tag,
        "command_file_path": command_path_text,
        "commit_allowed": False,
        "tag_allowed": False,
        "execution_allowed": False,
        "execution_performed": False,
        "next_action": "complete_bounded_cycle_before_commit",
        "summary": "Bounded cycle is not completed for approve commit/tag planning.",
    }
    if not activation_condition_met:
        return base_state

    normalized_repo_path = _normalize_text(
        execution_repo_path,
        default=_APPROVE_COMMIT_TAG_EXECUTION_REPO_PATH,
    )
    status_short = subprocess.run(
        ["git", "status", "--short", "--untracked-files=no"],
        text=True,
        capture_output=True,
        check=False,
        cwd=normalized_repo_path,
        shell=False,
    )
    diff_names = subprocess.run(
        ["git", "diff", "--name-only"],
        text=True,
        capture_output=True,
        check=False,
        cwd=normalized_repo_path,
        shell=False,
    )
    if status_short.returncode != 0 or diff_names.returncode != 0:
        return {
            **base_state,
            "blocked_reason": "git_metadata_collection_failed",
            "next_action": "review_git_metadata_failure",
            "summary": "Git metadata collection failed for approve commit/tag boundary.",
        }

    changed_from_status: list[str] = []
    for line in (status_short.stdout or "").splitlines():
        if not line.strip():
            continue
        path_text = line[3:].strip() if len(line) >= 4 else ""
        if " -> " in path_text:
            path_text = path_text.split(" -> ", 1)[1].strip()
        if path_text:
            changed_from_status.append(path_text)

    changed_from_diff = [
        line.strip() for line in (diff_names.stdout or "").splitlines() if line.strip()
    ]
    changed_tracked_files = sorted(set(changed_from_status + changed_from_diff))
    allowed_paths = {tracked_file}
    unexpected_tracked_files = sorted(
        path for path in changed_tracked_files if path not in allowed_paths
    )

    if not changed_tracked_files:
        return {
            **base_state,
            "blocked_reason": "no_tracked_changes_to_commit",
            "changed_tracked_files": [],
            "unexpected_tracked_files": [],
            "next_action": "none",
            "summary": "No tracked changes are available for commit/tag planning.",
        }
    if unexpected_tracked_files:
        return {
            **base_state,
            "blocked_reason": "unexpected_tracked_files_present",
            "changed_tracked_files": changed_tracked_files,
            "unexpected_tracked_files": unexpected_tracked_files,
            "next_action": "review_unexpected_tracked_files",
            "summary": "Unexpected tracked files are present for commit/tag planning.",
        }

    if changed_tracked_files != [tracked_file]:
        return {
            **base_state,
            "blocked_reason": "unexpected_tracked_files_present",
            "changed_tracked_files": changed_tracked_files,
            "unexpected_tracked_files": changed_tracked_files,
            "next_action": "review_unexpected_tracked_files",
            "summary": "Tracked file set does not match allowlist for commit/tag planning.",
        }

    return {
        **base_state,
        "status": "ready",
        "boundary_status": "ready",
        "blocked_reason": "none",
        "plan_ready": True,
        "tracked_files_allowed": True,
        "changed_tracked_files": [tracked_file],
        "unexpected_tracked_files": [],
        "explicit_add_paths": [tracked_file],
        "next_action": "run_prompt321_approve_commit_tag_execution_gate",
        "summary": "Approve commit/tag boundary is ready; execution remains disabled until Prompt321.",
    }

def _build_approve_commit_tag_plan_state(
    *,
    boundary_state: Mapping[str, Any] | None,
    command_file_path: Path,
) -> dict[str, Any]:
    boundary = dict(boundary_state) if isinstance(boundary_state, Mapping) else {}
    boundary_status = _normalize_text(boundary.get("boundary_status"), default="blocked")
    blocked_reason = _normalize_text(boundary.get("blocked_reason"), default="bounded_cycle_not_completed")
    ready = boundary_status == "ready" and bool(boundary.get("plan_ready", False))

    status = "blocked"
    plan_status = "blocked"
    next_action = _normalize_text(boundary.get("next_action"), default="none")
    summary = "Approve commit/tag plan is blocked."
    if ready:
        status = "ready"
        plan_status = "ready"
        blocked_reason = "none"
        next_action = "run_prompt321_approve_commit_tag_execution_gate"
        summary = "Approve commit/tag plan is ready; execution remains disabled until Prompt321."

    return {
        "status": status,
        "plan_status": plan_status,
        "blocked_reason": blocked_reason,
        "source": "approve_commit_tag_boundary",
        "commit_message": _normalize_text(
            boundary.get("proposed_commit_message"),
            default=_APPROVE_COMMIT_TAG_EXECUTION_COMMIT_MESSAGE,
        ),
        "tag_name": _normalize_text(
            boundary.get("proposed_tag"),
            default=_APPROVE_COMMIT_TAG_EXECUTION_TAG_NAME,
        ),
        "explicit_add_paths": _normalize_string_list(boundary.get("explicit_add_paths")),
        "command_file_path": str(command_file_path),
        "execution_required_by": "Prompt321",
        "execution_performed": False,
        "next_action": next_action,
        "summary": summary,
    }

def _write_approve_commit_tag_commands_if_safe(
    *,
    boundary_state: Mapping[str, Any] | None,
    command_file_path: Path,
) -> bool:
    boundary = dict(boundary_state) if isinstance(boundary_state, Mapping) else {}
    changed_paths = _normalize_string_list(boundary.get("changed_tracked_files"))
    unexpected_paths = _normalize_string_list(boundary.get("unexpected_tracked_files"))
    should_write = (
        _normalize_text(boundary.get("boundary_status"), default="blocked") == "ready"
        and bool(boundary.get("plan_ready", False))
        and bool(boundary.get("tracked_files_allowed", False))
        and changed_paths == [_APPROVE_COMMIT_TAG_EXECUTION_TRACKED_FILE]
        and not unexpected_paths
    )
    if not should_write:
        try:
            command_file_path.unlink(missing_ok=True)
        except OSError:
            pass
        return False

    commands_text = "\n".join(
        [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            "",
            "cd /home/rai/codex-local-runner",
            "",
            "git add automation/orchestration/planned_execution_runner.py",
            f'git commit -m "{_APPROVE_COMMIT_TAG_EXECUTION_COMMIT_MESSAGE}"',
            f"git tag {_APPROVE_COMMIT_TAG_EXECUTION_TAG_NAME}",
            "",
            "git status --short --untracked-files=no",
        ]
    ).rstrip() + "\n"
    try:
        command_file_path.parent.mkdir(parents=True, exist_ok=True)
        command_file_path.write_text(commands_text, encoding="utf-8")
    except OSError:
        return False
    return True

def _build_approve_commit_tag_execution_gate_state(
    *,
    execution_enabled: bool,
    execution_confirmed: bool,
    dry_run: bool,
    review_route_status: str,
    review_route_decision: str,
    review_route_should_prepare_commit: bool,
    approve_commit_tag_boundary_status: str,
    approve_commit_tag_boundary_decision: str,
    approve_commit_tag_boundary_commit_message: str,
    approve_commit_tag_boundary_tag_name: str,
    approve_commit_tag_boundary_commands_path: str,
    approve_commit_tag_boundary_metadata_path: str,
    approve_commit_tag_boundary_should_execute_commit: bool,
    approve_commit_tag_boundary_should_execute_tag: bool,
    approve_commit_tag_boundary_ready: bool,
    receipt_path: str,
) -> dict[str, Any]:
    execution_commit_message = _normalize_text(
        approve_commit_tag_boundary_commit_message,
        default="",
    )
    execution_tag_name = _normalize_text(
        approve_commit_tag_boundary_tag_name,
        default="",
    )
    state: dict[str, Any] = {
        "execution_enabled": bool(execution_enabled),
        "execution_confirmed": bool(execution_confirmed),
        "execution_gate_status": "execution_not_enabled",
        "execution_status": "not_executed",
        "execution_attempted": False,
        "execution_exit_code": 0,
        "execution_blocked_reason": "execution_not_enabled",
        "execution_commit_message": execution_commit_message,
        "execution_tag_name": execution_tag_name,
        "execution_receipt_path": _normalize_text(
            receipt_path,
            default=_APPROVE_COMMIT_TAG_EXECUTION_RECEIPT_PATH,
        ),
        "execution_should_commit": False,
        "execution_should_tag": False,
    }
    if not execution_enabled or not execution_confirmed:
        return state
    if dry_run:
        state.update(
            {
                "execution_gate_status": "dry_run_suppressed",
                "execution_status": "dry_run_suppressed",
                "execution_attempted": False,
                "execution_exit_code": 0,
                "execution_blocked_reason": "dry_run_execution_suppressed",
                "execution_should_commit": False,
                "execution_should_tag": False,
            }
        )
        return state
    if review_route_decision != "approve":
        state.update(
            {
                "execution_gate_status": "boundary_not_ready",
                "execution_status": "blocked",
                "execution_attempted": False,
                "execution_exit_code": 0,
                "execution_blocked_reason": "route_not_approve",
                "execution_should_commit": False,
                "execution_should_tag": False,
            }
        )
        return state
    boundary_ready = (
        review_route_status == "route_ready"
        and bool(review_route_should_prepare_commit)
        and approve_commit_tag_boundary_status == "boundary_ready"
        and approve_commit_tag_boundary_decision == "approve"
        and bool(approve_commit_tag_boundary_ready)
    )
    if not boundary_ready:
        state.update(
            {
                "execution_gate_status": "boundary_not_ready",
                "execution_status": "blocked",
                "execution_attempted": False,
                "execution_exit_code": 0,
                "execution_blocked_reason": "boundary_not_ready",
                "execution_should_commit": False,
                "execution_should_tag": False,
            }
        )
        return state
    deterministic_surface_valid = (
        execution_commit_message == _APPROVE_COMMIT_TAG_EXECUTION_COMMIT_MESSAGE
        and execution_tag_name == _APPROVE_COMMIT_TAG_EXECUTION_TAG_NAME
        and _normalize_text(
            approve_commit_tag_boundary_commands_path,
            default="",
        )
        == _APPROVE_COMMIT_TAG_BOUNDARY_COMMANDS_PATH
        and _normalize_text(
            approve_commit_tag_boundary_metadata_path,
            default="",
        )
        == _APPROVE_COMMIT_TAG_BOUNDARY_METADATA_PATH
        and (not bool(approve_commit_tag_boundary_should_execute_commit))
        and (not bool(approve_commit_tag_boundary_should_execute_tag))
    )
    if not deterministic_surface_valid:
        state.update(
            {
                "execution_gate_status": "preflight_blocked",
                "execution_status": "blocked",
                "execution_attempted": False,
                "execution_exit_code": 0,
                "execution_blocked_reason": "boundary_metadata_invalid",
                "execution_should_commit": False,
                "execution_should_tag": False,
            }
        )
        return state
    state.update(
        {
            "execution_gate_status": "ready_for_execution",
            "execution_status": "not_executed",
            "execution_attempted": False,
            "execution_exit_code": 0,
            "execution_blocked_reason": "none",
            "execution_commit_message": _APPROVE_COMMIT_TAG_EXECUTION_COMMIT_MESSAGE,
            "execution_tag_name": _APPROVE_COMMIT_TAG_EXECUTION_TAG_NAME,
            "execution_should_commit": False,
            "execution_should_tag": False,
        }
    )
    return state

def _run_approve_commit_tag_execution_if_enabled(
    *,
    execution_repo_path: str,
    dry_run: bool,
    review_route_status: str,
    review_route_decision: str,
    review_route_should_prepare_commit: bool,
    approve_commit_tag_boundary_status: str,
    approve_commit_tag_boundary_decision: str,
    approve_commit_tag_boundary_commit_message: str,
    approve_commit_tag_boundary_tag_name: str,
    approve_commit_tag_boundary_commands_path: str,
    approve_commit_tag_boundary_metadata_path: str,
    approve_commit_tag_boundary_should_execute_commit: bool,
    approve_commit_tag_boundary_should_execute_tag: bool,
    approve_commit_tag_boundary_ready: bool,
    execution_enabled: bool,
    execution_confirmed: bool,
    execution_receipt_path: Path,
) -> dict[str, Any]:
    state: dict[str, Any] = {
        "execution_enabled": False,
        "execution_confirmed": False,
        "execution_gate_status": "execution_not_enabled",
        "execution_status": "not_executed",
        "execution_attempted": False,
        "execution_exit_code": 0,
        "execution_blocked_reason": "execution_not_enabled",
        "execution_commit_message": _APPROVE_COMMIT_TAG_EXECUTION_COMMIT_MESSAGE,
        "execution_tag_name": _APPROVE_COMMIT_TAG_EXECUTION_TAG_NAME,
        "execution_receipt_path": _normalize_text(
            str(execution_receipt_path),
            default=_APPROVE_COMMIT_TAG_EXECUTION_RECEIPT_PATH,
        ),
        "execution_should_commit": False,
        "execution_should_tag": False,
    }
    receipt_payload = {
        "status": state["execution_status"],
        "gate_status": state["execution_gate_status"],
        "blocked_reason": state["execution_blocked_reason"],
        "attempted": state["execution_attempted"],
        "exit_code": state["execution_exit_code"],
        "execution_enabled": state["execution_enabled"],
        "execution_confirmed": state["execution_confirmed"],
        "execution_commit_message": state["execution_commit_message"],
        "execution_tag_name": state["execution_tag_name"],
        "execution_should_commit": state["execution_should_commit"],
        "execution_should_tag": state["execution_should_tag"],
        "execution_repo_path": _normalize_text(execution_repo_path, default=""),
        "boundary_commands_path": _normalize_text(
            approve_commit_tag_boundary_commands_path,
            default="",
        ),
        "boundary_metadata_path": _normalize_text(
            approve_commit_tag_boundary_metadata_path,
            default="",
        ),
        "execution_required_by": "Prompt321",
        "execution_performed": False,
    }
    try:
        execution_receipt_path.parent.mkdir(parents=True, exist_ok=True)
        execution_receipt_path.write_text(
            json.dumps(receipt_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError:
        pass
    return state

    state = _build_approve_commit_tag_execution_gate_state(
        execution_enabled=execution_enabled,
        execution_confirmed=execution_confirmed,
        dry_run=dry_run,
        review_route_status=review_route_status,
        review_route_decision=review_route_decision,
        review_route_should_prepare_commit=review_route_should_prepare_commit,
        approve_commit_tag_boundary_status=approve_commit_tag_boundary_status,
        approve_commit_tag_boundary_decision=approve_commit_tag_boundary_decision,
        approve_commit_tag_boundary_commit_message=approve_commit_tag_boundary_commit_message,
        approve_commit_tag_boundary_tag_name=approve_commit_tag_boundary_tag_name,
        approve_commit_tag_boundary_commands_path=approve_commit_tag_boundary_commands_path,
        approve_commit_tag_boundary_metadata_path=approve_commit_tag_boundary_metadata_path,
        approve_commit_tag_boundary_should_execute_commit=(
            approve_commit_tag_boundary_should_execute_commit
        ),
        approve_commit_tag_boundary_should_execute_tag=(
            approve_commit_tag_boundary_should_execute_tag
        ),
        approve_commit_tag_boundary_ready=approve_commit_tag_boundary_ready,
        receipt_path=str(execution_receipt_path),
    )

    receipt_payload: dict[str, Any] = {
        "status": state.get("execution_status"),
        "gate_status": state.get("execution_gate_status"),
        "blocked_reason": state.get("execution_blocked_reason"),
        "attempted": bool(state.get("execution_attempted", False)),
        "exit_code": _as_int(state.get("execution_exit_code"), default=0),
        "execution_enabled": bool(state.get("execution_enabled", False)),
        "execution_confirmed": bool(state.get("execution_confirmed", False)),
        "execution_commit_message": _normalize_text(
            state.get("execution_commit_message"),
            default="",
        ),
        "execution_tag_name": _normalize_text(state.get("execution_tag_name"), default=""),
        "execution_should_commit": bool(state.get("execution_should_commit", False)),
        "execution_should_tag": bool(state.get("execution_should_tag", False)),
        "execution_repo_path": _normalize_text(execution_repo_path, default=""),
        "boundary_commands_path": _normalize_text(
            approve_commit_tag_boundary_commands_path,
            default="",
        ),
        "boundary_metadata_path": _normalize_text(
            approve_commit_tag_boundary_metadata_path,
            default="",
        ),
    }

    def _write_receipt() -> dict[str, Any]:
        receipt_payload["status"] = _normalize_text(state.get("execution_status"), default="")
        receipt_payload["gate_status"] = _normalize_text(
            state.get("execution_gate_status"),
            default="",
        )
        receipt_payload["blocked_reason"] = _normalize_text(
            state.get("execution_blocked_reason"),
            default="",
        )
        receipt_payload["attempted"] = bool(state.get("execution_attempted", False))
        receipt_payload["exit_code"] = _as_int(state.get("execution_exit_code"), default=0)
        receipt_payload["execution_should_commit"] = bool(
            state.get("execution_should_commit", False)
        )
        receipt_payload["execution_should_tag"] = bool(
            state.get("execution_should_tag", False)
        )
        try:
            execution_receipt_path.parent.mkdir(parents=True, exist_ok=True)
            execution_receipt_path.write_text(
                json.dumps(receipt_payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError:
            state.update(
                {
                    "execution_gate_status": "failed",
                    "execution_status": "failed",
                    "execution_attempted": bool(state.get("execution_attempted", False)),
                    "execution_exit_code": (
                        _as_int(state.get("execution_exit_code"), default=1) or 1
                    ),
                    "execution_blocked_reason": "receipt_write_failed",
                }
            )
        return state

    if _normalize_text(state.get("execution_gate_status"), default="") != "ready_for_execution":
        return _write_receipt()

    metadata_path = Path(approve_commit_tag_boundary_metadata_path)
    commands_path = Path(approve_commit_tag_boundary_commands_path)
    commit_message = _APPROVE_COMMIT_TAG_EXECUTION_COMMIT_MESSAGE
    tag_name = _APPROVE_COMMIT_TAG_EXECUTION_TAG_NAME
    expected_metadata = {
        "status": "boundary_ready",
        "decision": "approve",
        "reason": "approve_commit_tag_boundary_ready",
        "next_action": "prepare_approve_commit_tag_execution_gate",
        "blocked_reason": "none",
        "commit_message": commit_message,
        "tag_name": tag_name,
        "commands_path": _APPROVE_COMMIT_TAG_BOUNDARY_COMMANDS_PATH,
        "metadata_path": _APPROVE_COMMIT_TAG_BOUNDARY_METADATA_PATH,
        "should_execute_commit": False,
        "should_execute_tag": False,
    }

    if not metadata_path.exists():
        state.update(
            {
                "execution_gate_status": "preflight_blocked",
                "execution_status": "blocked",
                "execution_attempted": False,
                "execution_exit_code": 0,
                "execution_blocked_reason": "boundary_metadata_missing",
                "execution_should_commit": False,
                "execution_should_tag": False,
            }
        )
        receipt_payload["boundary_metadata_check"] = "missing"
        return _write_receipt()
    try:
        metadata_payload_raw = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        metadata_payload_raw = None
    metadata_payload = (
        dict(metadata_payload_raw) if isinstance(metadata_payload_raw, Mapping) else None
    )
    if metadata_payload is None:
        state.update(
            {
                "execution_gate_status": "preflight_blocked",
                "execution_status": "blocked",
                "execution_attempted": False,
                "execution_exit_code": 0,
                "execution_blocked_reason": "boundary_metadata_invalid",
                "execution_should_commit": False,
                "execution_should_tag": False,
            }
        )
        receipt_payload["boundary_metadata_check"] = "invalid_json_or_shape"
        return _write_receipt()
    metadata_matches = True
    for key, expected_value in expected_metadata.items():
        if metadata_payload.get(key) != expected_value:
            metadata_matches = False
            break
    if not metadata_matches:
        state.update(
            {
                "execution_gate_status": "preflight_blocked",
                "execution_status": "blocked",
                "execution_attempted": False,
                "execution_exit_code": 0,
                "execution_blocked_reason": "boundary_metadata_invalid",
                "execution_should_commit": False,
                "execution_should_tag": False,
            }
        )
        receipt_payload["boundary_metadata_check"] = "deterministic_mismatch"
        return _write_receipt()
    receipt_payload["boundary_metadata_check"] = "ok"

    if not commands_path.exists():
        state.update(
            {
                "execution_gate_status": "preflight_blocked",
                "execution_status": "blocked",
                "execution_attempted": False,
                "execution_exit_code": 0,
                "execution_blocked_reason": "command_draft_missing",
                "execution_should_commit": False,
                "execution_should_tag": False,
            }
        )
        receipt_payload["command_draft_check"] = "missing"
        return _write_receipt()
    try:
        commands_text = commands_path.read_text(encoding="utf-8")
    except OSError:
        commands_text = ""
    required_fragments = (
        f"git add {_APPROVE_COMMIT_TAG_EXECUTION_TRACKED_FILE}",
        f'git commit -m "{commit_message}"',
        f"git tag {tag_name}",
    )
    if not commands_text or any(fragment not in commands_text for fragment in required_fragments):
        state.update(
            {
                "execution_gate_status": "preflight_blocked",
                "execution_status": "blocked",
                "execution_attempted": False,
                "execution_exit_code": 0,
                "execution_blocked_reason": "command_draft_mismatch",
                "execution_should_commit": False,
                "execution_should_tag": False,
            }
        )
        receipt_payload["command_draft_check"] = "mismatch"
        return _write_receipt()
    receipt_payload["command_draft_check"] = "ok"

    normalized_repo_path = _normalize_text(execution_repo_path, default="")
    if (
        normalized_repo_path != _APPROVE_COMMIT_TAG_EXECUTION_REPO_PATH
        or str(Path.cwd()) != _APPROVE_COMMIT_TAG_EXECUTION_REPO_PATH
    ):
        state.update(
            {
                "execution_gate_status": "preflight_blocked",
                "execution_status": "blocked",
                "execution_attempted": False,
                "execution_exit_code": 0,
                "execution_blocked_reason": "manual_review_required",
                "execution_should_commit": False,
                "execution_should_tag": False,
            }
        )
        receipt_payload["preflight_check"] = "cwd_mismatch"
        return _write_receipt()

    def _run_allowed_git_command(command: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            command,
            text=True,
            capture_output=True,
            check=False,
            cwd=normalized_repo_path,
            shell=False,
        )

    status_short = _run_allowed_git_command(
        ["git", "status", "--short", "--untracked-files=no"]
    )
    if status_short.returncode != 0:
        state.update(
            {
                "execution_gate_status": "preflight_blocked",
                "execution_status": "blocked",
                "execution_attempted": False,
                "execution_exit_code": 0,
                "execution_blocked_reason": "manual_review_required",
                "execution_should_commit": False,
                "execution_should_tag": False,
            }
        )
        receipt_payload["preflight_check"] = "git_status_failed"
        receipt_payload["git_status_short_stdout"] = status_short.stdout or ""
        receipt_payload["git_status_short_stderr"] = status_short.stderr or ""
        return _write_receipt()
    receipt_payload["git_status_short_stdout"] = status_short.stdout or ""

    staged_diff = _run_allowed_git_command(["git", "diff", "--cached", "--name-only"])
    if staged_diff.returncode != 0:
        state.update(
            {
                "execution_gate_status": "preflight_blocked",
                "execution_status": "blocked",
                "execution_attempted": False,
                "execution_exit_code": 0,
                "execution_blocked_reason": "manual_review_required",
                "execution_should_commit": False,
                "execution_should_tag": False,
            }
        )
        receipt_payload["preflight_check"] = "git_diff_cached_failed"
        return _write_receipt()
    staged_paths = [
        line.strip() for line in (staged_diff.stdout or "").splitlines() if line.strip()
    ]
    receipt_payload["staged_paths"] = staged_paths
    if staged_paths:
        state.update(
            {
                "execution_gate_status": "preflight_blocked",
                "execution_status": "blocked",
                "execution_attempted": False,
                "execution_exit_code": 0,
                "execution_blocked_reason": "staged_changes_present",
                "execution_should_commit": False,
                "execution_should_tag": False,
            }
        )
        receipt_payload["preflight_check"] = "staged_changes_present"
        return _write_receipt()

    tracked_diff = _run_allowed_git_command(["git", "diff", "--name-only"])
    if tracked_diff.returncode != 0:
        state.update(
            {
                "execution_gate_status": "preflight_blocked",
                "execution_status": "blocked",
                "execution_attempted": False,
                "execution_exit_code": 0,
                "execution_blocked_reason": "manual_review_required",
                "execution_should_commit": False,
                "execution_should_tag": False,
            }
        )
        receipt_payload["preflight_check"] = "git_diff_failed"
        return _write_receipt()
    tracked_paths = [
        line.strip() for line in (tracked_diff.stdout or "").splitlines() if line.strip()
    ]
    receipt_payload["tracked_paths"] = tracked_paths
    if tracked_paths != [_APPROVE_COMMIT_TAG_EXECUTION_TRACKED_FILE]:
        state.update(
            {
                "execution_gate_status": "preflight_blocked",
                "execution_status": "blocked",
                "execution_attempted": False,
                "execution_exit_code": 0,
                "execution_blocked_reason": "unexpected_tracked_changes",
                "execution_should_commit": False,
                "execution_should_tag": False,
            }
        )
        receipt_payload["preflight_check"] = "unexpected_tracked_changes"
        return _write_receipt()

    tag_exists_check = _run_allowed_git_command(
        ["git", "rev-parse", "--verify", f"refs/tags/{tag_name}"]
    )
    if tag_exists_check.returncode == 0:
        state.update(
            {
                "execution_gate_status": "preflight_blocked",
                "execution_status": "blocked",
                "execution_attempted": False,
                "execution_exit_code": 0,
                "execution_blocked_reason": "tag_already_exists",
                "execution_should_commit": False,
                "execution_should_tag": False,
            }
        )
        receipt_payload["preflight_check"] = "tag_already_exists"
        return _write_receipt()

    state.update(
        {
            "execution_gate_status": "ready_for_execution",
            "execution_status": "not_executed",
            "execution_attempted": False,
            "execution_exit_code": 0,
            "execution_blocked_reason": "none",
            "execution_should_commit": True,
            "execution_should_tag": True,
        }
    )
    add_result = _run_allowed_git_command(
        ["git", "add", _APPROVE_COMMIT_TAG_EXECUTION_TRACKED_FILE]
    )
    state.update(
        {
            "execution_attempted": True,
            "execution_should_commit": True,
            "execution_should_tag": False,
        }
    )
    receipt_payload["git_add_exit_code"] = int(add_result.returncode)
    if add_result.returncode != 0:
        state.update(
            {
                "execution_gate_status": "failed",
                "execution_status": "failed",
                "execution_exit_code": int(add_result.returncode) or 1,
                "execution_blocked_reason": "commit_failed",
                "execution_should_tag": False,
            }
        )
        return _write_receipt()

    commit_result = _run_allowed_git_command(["git", "commit", "-m", commit_message])
    receipt_payload["git_commit_exit_code"] = int(commit_result.returncode)
    if commit_result.returncode != 0:
        state.update(
            {
                "execution_gate_status": "failed",
                "execution_status": "failed",
                "execution_attempted": True,
                "execution_exit_code": int(commit_result.returncode) or 1,
                "execution_blocked_reason": "commit_failed",
                "execution_should_commit": True,
                "execution_should_tag": False,
            }
        )
        return _write_receipt()

    tag_result = _run_allowed_git_command(["git", "tag", tag_name])
    receipt_payload["git_tag_exit_code"] = int(tag_result.returncode)
    if tag_result.returncode != 0:
        state.update(
            {
                "execution_gate_status": "failed",
                "execution_status": "failed",
                "execution_attempted": True,
                "execution_exit_code": int(tag_result.returncode) or 1,
                "execution_blocked_reason": "tag_failed",
                "execution_should_commit": True,
                "execution_should_tag": True,
            }
        )
        return _write_receipt()

    state.update(
        {
            "execution_gate_status": "executed",
            "execution_status": "completed",
            "execution_attempted": True,
            "execution_exit_code": 0,
            "execution_blocked_reason": "none",
            "execution_should_commit": True,
            "execution_should_tag": True,
        }
    )
    receipt_payload["preflight_check"] = "passed"
    receipt_payload["execution_result"] = "completed"
    return _write_receipt()

def _extract_commit_scope_from_contract(entry: Mapping[str, Any]) -> list[str]:
    bounded_contract_path_text = _normalize_text(entry.get("bounded_step_contract_path"), default="")
    if not bounded_contract_path_text:
        return []
    bounded_contract = _read_json_object_if_exists(Path(bounded_contract_path_text))
    if not isinstance(bounded_contract, Mapping):
        return []
    progression = (
        dict(bounded_contract.get("progression_metadata"))
        if isinstance(bounded_contract.get("progression_metadata"), Mapping)
        else {}
    )
    strict_scope_files = _normalize_string_list(
        progression.get("strict_scope_files") or bounded_contract.get("scope_in"),
        sort_items=True,
    )
    return strict_scope_files

def _default_commit_execution_payload(
    *,
    unit_id: str,
    now: Callable[[], datetime],
) -> dict[str, Any]:
    return {
        "schema_version": _COMMIT_EXECUTION_SCHEMA_VERSION,
        "unit_id": unit_id,
        "execution_type": _COMMIT_EXECUTION_TYPE,
        "status": "blocked",
        "summary": "commit execution blocked",
        "started_at": "",
        "finished_at": _iso_now(now),
        "commit_sha": "",
        "command_summary": {},
        "failure_reason": "commit_execution_not_attempted",
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
        "remote_github_status": "unknown",
        "remote_github_blocked": False,
        "remote_github_blocked_reason": "",
        "remote_github_blocked_reasons": [],
        "remote_github_missing_or_ambiguous": False,
        "remote_state_status": "unknown",
        "remote_state_blocked": False,
        "remote_state_blocked_reason": "",
        "remote_state_missing_or_ambiguous": False,
        "upstream_tracking_status": "unknown",
        "remote_divergence_status": "unknown",
        "remote_branch_status": "unknown",
        "existing_pr_status": "unknown",
        "pr_creation_state_status": "unknown",
        "pr_duplication_risk": "unknown",
        "mergeability_status": "unknown",
        "merge_requirements_status": "unknown",
        "required_checks_status": "unknown",
        "review_state_status": "unknown",
        "branch_protection_status": "unknown",
        "github_state_status": "unknown",
        "github_state_unavailable": False,
        "manual_approval_required": False,
    }

def _build_commit_execution_blocked_payload(
    *,
    unit_id: str,
    now: Callable[[], datetime],
    summary: str,
    failure_reason: str,
    blocking_reasons: list[str],
    manual_intervention_required: bool = False,
    command_summary: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = _default_commit_execution_payload(unit_id=unit_id, now=now)
    payload["summary"] = summary
    payload["failure_reason"] = failure_reason
    payload["blocking_reasons"] = _serialize_required_signals(list(blocking_reasons))
    payload["manual_intervention_required"] = manual_intervention_required
    payload["command_summary"] = dict(command_summary) if isinstance(command_summary, Mapping) else {}
    return _with_execution_gate_surface(payload)

def _evaluate_commit_execution_blockers(
    *,
    commit_decision: Mapping[str, Any],
    run_state_payload: Mapping[str, Any],
    changed_files: list[str],
    strict_scope_files: list[str],
    execution_repo_path: str,
    dry_run: bool,
) -> list[str]:
    blockers: list[str] = []

    readiness_status = _normalize_text(commit_decision.get("readiness_status"), default="")
    if readiness_status != "ready":
        blockers.append("commit_readiness_not_ready")
    if not bool(commit_decision.get("automation_eligible", False)):
        blockers.append("commit_automation_not_eligible")
    if bool(commit_decision.get("manual_intervention_required", False)):
        blockers.append("commit_manual_intervention_required")
    if _normalize_string_list(commit_decision.get("unresolved_blockers")):
        blockers.append("commit_unresolved_blockers_present")
    if not bool(commit_decision.get("prerequisites_satisfied", False)):
        blockers.append("commit_prerequisites_unsatisfied")

    if not bool(run_state_payload.get("continue_allowed", False)):
        blockers.append("run_continue_not_allowed")
    if bool(run_state_payload.get("run_paused", False)):
        blockers.append("run_paused")
    if bool(run_state_payload.get("manual_intervention_required", False)):
        blockers.append("run_manual_intervention_required")
    if bool(run_state_payload.get("global_stop_recommended", False)) or bool(run_state_payload.get("global_stop", False)):
        blockers.append("run_global_stop_recommended")
    if bool(run_state_payload.get("rollback_evaluation_pending", False)):
        blockers.append("run_rollback_evaluation_pending")

    if dry_run:
        blockers.append("dry_run_mode")
    if not execution_repo_path.strip():
        blockers.append("execution_repo_path_missing")
    if not changed_files:
        blockers.append("result_changed_files_missing")
    if not strict_scope_files:
        blockers.append("strict_scope_unavailable")
    elif changed_files:
        strict_scope = set(strict_scope_files)
        if any(path not in strict_scope for path in changed_files):
            blockers.append("changed_files_outside_strict_scope")

    return _serialize_required_signals(blockers)

def _execute_bounded_commit(
    *,
    unit_id: str,
    job_id: str,
    repo_path: str,
    changed_files: list[str],
    strict_scope_files: list[str],
    run_state_payload: Mapping[str, Any],
    commit_decision: Mapping[str, Any],
    dry_run: bool,
    now: Callable[[], datetime],
) -> dict[str, Any]:
    blockers = _evaluate_commit_execution_blockers(
        commit_decision=commit_decision,
        run_state_payload=run_state_payload,
        changed_files=changed_files,
        strict_scope_files=strict_scope_files,
        execution_repo_path=repo_path,
        dry_run=dry_run,
    )
    if blockers:
        return _build_commit_execution_blocked_payload(
            unit_id=unit_id,
            now=now,
            summary="commit execution blocked by readiness or run-level preconditions",
            failure_reason="commit_execution_blocked_by_preconditions",
            blocking_reasons=blockers,
        )

    repo_dir = Path(repo_path)
    if not repo_dir.exists() or not repo_dir.is_dir():
        return _build_commit_execution_blocked_payload(
            unit_id=unit_id,
            now=now,
            summary="commit execution blocked because execution repo path is invalid",
            failure_reason="execution_repo_not_directory",
            blocking_reasons=["execution_repo_not_directory"],
        )

    command_summary: dict[str, Any] = {}
    worktree_result = _run_git(repo_path, ["rev-parse", "--is-inside-work-tree"])
    command_summary["rev_parse_worktree_rc"] = worktree_result.returncode
    if worktree_result.returncode != 0:
        return _build_commit_execution_blocked_payload(
            unit_id=unit_id,
            now=now,
            summary="commit execution blocked because repo is not a git worktree",
            failure_reason="repo_not_git_worktree",
            blocking_reasons=["repo_not_git_worktree"],
            command_summary=command_summary,
        )

    status_result = _run_git(repo_path, ["status", "--porcelain"])
    command_summary["status_rc"] = status_result.returncode
    if status_result.returncode != 0:
        return _build_commit_execution_blocked_payload(
            unit_id=unit_id,
            now=now,
            summary="commit execution blocked because git status failed",
            failure_reason="git_status_failed",
            blocking_reasons=["git_status_failed"],
            manual_intervention_required=True,
            command_summary=command_summary,
        )

    status_lines = [line.rstrip("\n") for line in (status_result.stdout or "").splitlines() if line.strip()]
    command_summary["status_lines"] = len(status_lines)
    changed_files_set = set(changed_files)
    status_paths = [_parse_git_status_path(line) for line in status_lines]
    status_paths = [path for path in status_paths if path]
    if not status_paths:
        return _build_commit_execution_blocked_payload(
            unit_id=unit_id,
            now=now,
            summary="commit execution blocked because no repository changes were detected",
            failure_reason="no_repository_changes",
            blocking_reasons=["no_repository_changes"],
            command_summary=command_summary,
        )

    if any(path not in changed_files_set for path in status_paths):
        return _build_commit_execution_blocked_payload(
            unit_id=unit_id,
            now=now,
            summary="commit execution blocked because working tree contains out-of-scope changes",
            failure_reason="working_tree_contains_out_of_scope_changes",
            blocking_reasons=["working_tree_contains_out_of_scope_changes"],
            command_summary=command_summary,
        )

    if not any(path in changed_files_set for path in status_paths):
        return _build_commit_execution_blocked_payload(
            unit_id=unit_id,
            now=now,
            summary="commit execution blocked because expected changed files were not present in git status",
            failure_reason="expected_changed_files_not_present",
            blocking_reasons=["expected_changed_files_not_present"],
            command_summary=command_summary,
        )

    if any(line[:2].strip() == "U" or line[:2] in {"DD", "AU", "UD", "UA", "DU", "AA", "UU"} for line in status_lines):
        return _build_commit_execution_blocked_payload(
            unit_id=unit_id,
            now=now,
            summary="commit execution blocked because merge-conflict markers were detected in git status",
            failure_reason="working_tree_conflicts_present",
            blocking_reasons=["working_tree_conflicts_present"],
            manual_intervention_required=True,
            command_summary=command_summary,
        )

    started_at = _iso_now(now)
    add_result = _run_git(repo_path, ["add", "--", *sorted(changed_files_set)])
    command_summary["git_add_rc"] = add_result.returncode
    if add_result.returncode != 0:
        return {
            "schema_version": _COMMIT_EXECUTION_SCHEMA_VERSION,
            "unit_id": unit_id,
            "execution_type": _COMMIT_EXECUTION_TYPE,
            "status": "failed",
            "summary": "commit execution failed while staging files",
            "started_at": started_at,
            "finished_at": _iso_now(now),
            "commit_sha": "",
            "command_summary": command_summary,
            "failure_reason": "git_add_failed",
            "manual_intervention_required": True,
            "blocking_reasons": ["git_add_failed"],
            "attempted": True,
        }

    staged_diff = _run_git(repo_path, ["diff", "--cached", "--quiet"])
    command_summary["staged_diff_rc"] = staged_diff.returncode
    if staged_diff.returncode == 0:
        return _build_commit_execution_blocked_payload(
            unit_id=unit_id,
            now=now,
            summary="commit execution blocked because no staged changes were available for commit",
            failure_reason="no_staged_changes",
            blocking_reasons=["no_staged_changes"],
            command_summary=command_summary,
        )
    if staged_diff.returncode not in {0, 1}:
        return {
            "schema_version": _COMMIT_EXECUTION_SCHEMA_VERSION,
            "unit_id": unit_id,
            "execution_type": _COMMIT_EXECUTION_TYPE,
            "status": "failed",
            "summary": "commit execution failed while checking staged diff",
            "started_at": started_at,
            "finished_at": _iso_now(now),
            "commit_sha": "",
            "command_summary": command_summary,
            "failure_reason": "git_diff_cached_failed",
            "manual_intervention_required": True,
            "blocking_reasons": ["git_diff_cached_failed"],
            "attempted": True,
        }

    commit_message = f"[{job_id}:{unit_id}] bounded commit execution"
    command_summary["commit_message"] = commit_message
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
    )
    command_summary["git_commit_rc"] = commit_result.returncode
    if commit_result.returncode != 0:
        return {
            "schema_version": _COMMIT_EXECUTION_SCHEMA_VERSION,
            "unit_id": unit_id,
            "execution_type": _COMMIT_EXECUTION_TYPE,
            "status": "failed",
            "summary": "commit execution failed during git commit",
            "started_at": started_at,
            "finished_at": _iso_now(now),
            "commit_sha": "",
            "command_summary": command_summary,
            "failure_reason": "git_commit_failed",
            "manual_intervention_required": True,
            "blocking_reasons": ["git_commit_failed"],
            "attempted": True,
        }

    rev_parse_head = _run_git(repo_path, ["rev-parse", "HEAD"])
    command_summary["rev_parse_head_rc"] = rev_parse_head.returncode
    commit_sha = (rev_parse_head.stdout or "").strip() if rev_parse_head.returncode == 0 else ""
    if not commit_sha:
        return {
            "schema_version": _COMMIT_EXECUTION_SCHEMA_VERSION,
            "unit_id": unit_id,
            "execution_type": _COMMIT_EXECUTION_TYPE,
            "status": "failed",
            "summary": "commit execution failed to resolve HEAD after successful commit",
            "started_at": started_at,
            "finished_at": _iso_now(now),
            "commit_sha": "",
            "command_summary": command_summary,
            "failure_reason": "head_resolution_failed_after_commit",
            "manual_intervention_required": True,
            "blocking_reasons": ["head_resolution_failed_after_commit"],
            "attempted": True,
        }

    return {
        "schema_version": _COMMIT_EXECUTION_SCHEMA_VERSION,
        "unit_id": unit_id,
        "execution_type": _COMMIT_EXECUTION_TYPE,
        "status": "succeeded",
        "summary": "commit execution succeeded under bounded readiness and run-state conditions",
        "started_at": started_at,
        "finished_at": _iso_now(now),
        "commit_sha": commit_sha,
        "command_summary": command_summary,
        "failure_reason": "",
        "manual_intervention_required": False,
        "blocking_reasons": [],
        "attempted": True,
    }
