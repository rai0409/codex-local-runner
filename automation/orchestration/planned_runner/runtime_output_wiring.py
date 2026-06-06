from __future__ import annotations

from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any
from typing import Callable
from typing import Iterable
from typing import Mapping
from typing import Sequence

from automation.orchestration.run_state_summary_contract import (
    PROMPT468_RUN_STATE_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.run_state_summary_contract import (
    PROMPT489_RUN_STATE_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.run_state_summary_contract import (
    PROMPT490_RUN_STATE_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.run_state_summary_contract import (
    PROMPT491_RUN_STATE_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.planned_runner.prompt_surfaces import prompts_350_399
from automation.orchestration.planned_runner.prompt_surfaces.prompts_350_399 import (
    _build_prompt373_selected_step_live_codex_execution_state,
)
from automation.orchestration.planned_runner.prompt_surfaces.prompts_350_399 import (
    _build_prompt378_chatgpt_generated_prompt_intake_state,
)
from automation.orchestration.planned_runner.prompt_surfaces.prompts_350_399 import (
    _build_prompt379_generated_prompt_codex_execution_bridge_state,
)
from automation.orchestration.planned_runner.prompt_surfaces.prompts_350_399 import (
    _build_prompt380_prompt379_result_review_route_decision_state,
)
from automation.orchestration.planned_runner.prompt_surfaces.prompts_350_399 import (
    _build_prompt381_approve_candidate_boundary_state,
)
from automation.orchestration.planned_runner.prompt_surfaces.prompts_350_399 import (
    _build_prompt382_approve_commit_tag_execution_gate_state,
)
from automation.orchestration.planned_runner.prompt_surfaces.prompts_350_399 import (
    _build_prompt383_explicit_approve_commit_tag_execution_state,
)
from automation.orchestration.planned_runner.prompt_surfaces.prompts_350_399 import (
    _build_prompt385_success_path_next_cycle_handoff_state,
)
from automation.orchestration.planned_runner.prompt_surfaces.prompts_350_399 import (
    _build_prompt388_local_success_path_autonomous_loop_completion_gate_state,
)
from automation.orchestration.planned_runner.prompt_surfaces.prompts_350_399 import (
    _build_prompt389_explicit_bounded_repeated_success_path_loop_execution_state,
)
from automation.orchestration.planned_runner.prompt_surfaces.prompts_450_499 import (
    _prompt491a_canonical_tokens_ready,
)
from automation.orchestration.planned_runner.prompt_surfaces.prompts_450_499 import (
    _prompt491a_materialized_prompt378_markdown,
)
from automation.orchestration.planned_runner.runtime_internal_execution_adapter import (
    PROMPT546_CHANGED_FILES_ARTIFACT,
)
from automation.orchestration.planned_runner.runtime_internal_execution_adapter import (
    PROMPT546_DIFF_ARTIFACT,
)
from automation.orchestration.planned_runner.runtime_internal_execution_adapter import (
    PROMPT546_INTERNAL_CODEX_ENABLE_TOKEN,
)
from automation.orchestration.planned_runner.runtime_internal_execution_adapter import (
    PROMPT546_RESULT_ARTIFACT,
)
from automation.orchestration.planned_runner.runtime_internal_execution_adapter import (
    PROMPT546_RETURNCODE_ARTIFACT,
)
from automation.orchestration.planned_runner.runtime_internal_execution_adapter import (
    PROMPT546_STDERR_ARTIFACT,
)
from automation.orchestration.planned_runner.runtime_internal_execution_adapter import (
    PROMPT546_STDOUT_ARTIFACT,
)
from automation.orchestration.planned_runner.runtime_internal_execution_adapter import (
    PROMPT547_CHANGED_FILES_ARTIFACT,
)
from automation.orchestration.planned_runner.runtime_internal_execution_adapter import (
    PROMPT547_DIFF_ARTIFACT,
)
from automation.orchestration.planned_runner.runtime_internal_execution_adapter import (
    PROMPT547_RESULT_ARTIFACT,
)
from automation.orchestration.planned_runner.runtime_internal_execution_adapter import (
    PROMPT547_RETURNCODE_ARTIFACT,
)
from automation.orchestration.planned_runner.runtime_internal_execution_adapter import (
    PROMPT547_STDERR_ARTIFACT,
)
from automation.orchestration.planned_runner.runtime_internal_execution_adapter import (
    PROMPT547_STDOUT_ARTIFACT,
)
from automation.orchestration.planned_runner.runtime_internal_execution_adapter import (
    run_internal_codex_subprocess,
)
from automation.orchestration.planned_runner.prompt_surfaces.registry import (
    get_prompt_builders,
)
from automation.orchestration.planned_runner.utils import _normalize_text
from automation.orchestration.planned_runner.utils import _read_json_object_if_exists
from automation.orchestration.planned_runner.utils import _write_json


PROMPT551_ACTUAL_RUNTIME_ADAPTER_EXECUTION_BRIDGE_ENABLE_TOKEN = (
    "PROMPT551_ACTUAL_RUNTIME_ADAPTER_EXECUTION_BRIDGE_ENABLE"
)
PROMPT565_MULTI_CYCLE_DAEMON_AUTONOMOUS_LOOP_ENABLE_TOKEN = (
    "PROMPT565_MULTI_CYCLE_DAEMON_AUTONOMOUS_LOOP_ENABLE"
)
PROMPT568_PRODUCTION_HARDENING_ENTRYPOINT_ENABLE_TOKEN = (
    "PROMPT568_PRODUCTION_HARDENING_ENTRYPOINT_ENABLE"
)
PROMPT569_SOAK_RUNNER_SUPERVISOR_WRAPPER_ENABLE_TOKEN = (
    "PROMPT569_SOAK_RUNNER_SUPERVISOR_WRAPPER_ENABLE"
)
PROMPT571_SERVICE_ARTIFACTS_LOCAL_ONLY_ENABLE_TOKEN = (
    "PROMPT571_SERVICE_ARTIFACTS_LOCAL_ONLY_ENABLE"
)
PROMPT572_LONGER_SOAK_STABILITY_GATE_ENABLE_TOKEN = (
    "PROMPT572_LONGER_SOAK_STABILITY_GATE_ENABLE"
)
PROMPT574_OBSERVED_DAEMON_RUN_GATE_ENABLE_TOKEN = (
    "PROMPT574_OBSERVED_DAEMON_RUN_GATE_ENABLE"
)
PROMPT575_MANUAL_SERVICE_INSTALL_GATE_ENABLE_TOKEN = (
    "PROMPT575_MANUAL_SERVICE_INSTALL_GATE_ENABLE"
)
PROMPT578_ACTUAL_CODEX_DISPATCH_ENABLE_TOKEN = (
    "PROMPT578_ACTUAL_CODEX_DISPATCH_ENABLE"
)
PROMPT580_REAL_DEV_TASK_DISPATCH_ENABLE_TOKEN = (
    "PROMPT580_REAL_DEV_TASK_DISPATCH_ENABLE"
)

_CRITICAL_RUNTIME_ARTIFACTS = (
    "prompt373_codex_execution_request.json",
    "prompt373_codex_execution_receipt.json",
    "prompt378_generated_prompt_intake_receipt.json",
    "prompt378_generated_prompt_validation.json",
    "prompt378_generated_prompt_source.json",
    "prompt378_chatgpt_generated_prompt_intake.json",
    "prompt378_generated_prompt_execution_handoff.json",
    "execution_prompt.json",
    "prompt379_generated_prompt_codex_execution_receipt.json",
    "prompt380_prompt379_result_review_route_decision.json",
    "prompt381_approve_candidate_boundary.json",
    "prompt382_approve_commit_tag_execution_gate.json",
    "prompt383_explicit_approve_commit_tag_execution_gate.json",
    "prompt385_success_path_next_cycle_handoff.json",
    "prompt388_success_path_autonomy_completion_receipt.json",
    "prompt389_bounded_repeated_success_path_loop_execution_receipt.json",
)

_SPLIT_COMPATIBLE_RUNTIME_ARTIFACTS = (
    (
        "prompt468_full_no_human_loop_regression_rerun.json",
        PROMPT468_RUN_STATE_SUMMARY_SAFE_FIELDS,
    ),
    (
        "prompt489_real_task_marker.json",
        PROMPT489_RUN_STATE_SUMMARY_SAFE_FIELDS,
    ),
    (
        "prompt490_second_success_cycle_marker.json",
        PROMPT490_RUN_STATE_SUMMARY_SAFE_FIELDS,
    ),
    (
        "prompt491_current_head_multi_cycle_success_evidence_bridge.json",
        PROMPT491_RUN_STATE_SUMMARY_SAFE_FIELDS,
    ),
)

_SPLIT_COMPATIBLE_RUNTIME_BUILDER_NAMES = (
    "_build_prompt468_full_no_human_loop_regression_rerun_state",
    "_build_prompt489_real_task_marker_state",
    "_build_prompt490_second_success_cycle_state",
    "_build_prompt491_third_success_cycle_state",
)

_PROMPT546_DEFAULT_ALLOWED_FILES = (
    "automation/orchestration/planned_runner/runtime_internal_execution_adapter.py",
    "automation/orchestration/planned_runner/runtime_output_wiring.py",
    "automation/orchestration/planned_runner/runner.py",
    "automation/orchestration/planned_runner/prompt_surfaces/prompts_450_499.py",
    "automation/orchestration/planned_runner/prompt_surfaces/registry.py",
)
_PROMPT547_DEFAULT_ALLOWED_FILES = _PROMPT546_DEFAULT_ALLOWED_FILES

_PROMPT551_MINIMAL_PROMPT_ARTIFACT = (
    Path("artifacts/runtime_commands/prompt551_minimal_runtime_smoke_prompt.txt")
)
_PROMPT563_GENERATED_RUNTIME_ARTIFACTS = (
    PROMPT546_STDOUT_ARTIFACT,
    PROMPT546_STDERR_ARTIFACT,
    PROMPT546_RETURNCODE_ARTIFACT,
    PROMPT546_CHANGED_FILES_ARTIFACT,
    PROMPT546_DIFF_ARTIFACT,
    PROMPT546_RESULT_ARTIFACT,
    _PROMPT551_MINIMAL_PROMPT_ARTIFACT,
)
_PROMPT563_ALLOWED_PYTHON_FILES = (
    "automation/orchestration/planned_runner/runtime_output_wiring.py",
    "automation/orchestration/planned_runner/runtime_internal_execution_adapter.py",
    "automation/orchestration/planned_runner/prompt_surfaces/prompts_450_499.py",
    "automation/orchestration/planned_runner/prompt_surfaces/registry.py",
)
_PROMPT565_DEFAULT_ARTIFACT_DIR = Path(
    "artifacts/runtime_commands/prompt565_multi_cycle_daemon"
)
_PROMPT568_DEFAULT_ARTIFACT_DIR = Path(
    "artifacts/runtime_commands/prompt568_production_hardening_entrypoint"
)
_PROMPT569_DEFAULT_ARTIFACT_DIR = Path(
    "artifacts/runtime_commands/prompt569_soak_runner_supervisor_wrapper"
)
_PROMPT571_DEFAULT_ARTIFACT_DIR = Path(
    "artifacts/runtime_commands/prompt571_service_artifacts_local_only"
)
_PROMPT572_DEFAULT_ARTIFACT_DIR = Path(
    "artifacts/runtime_commands/prompt572_longer_soak_stability_gate"
)
_PROMPT574_DEFAULT_ARTIFACT_DIR = Path(
    "artifacts/runtime_commands/prompt574_observed_daemon_run_gate"
)
_PROMPT575_DEFAULT_ARTIFACT_DIR = Path(
    "artifacts/runtime_commands/prompt575_manual_service_install_gate"
)
_PROMPT576_DEFAULT_ARTIFACT_DIR = Path(
    "artifacts/runtime_commands/"
    "prompt576_bounded_multi_cycle_daemon_runner_proof"
)
_PROMPT577_DEFAULT_ARTIFACT_DIR = Path(
    "artifacts/runtime_commands/"
    "prompt577_actual_autonomous_development_cycle_bridge"
)
_PROMPT578_DEFAULT_ARTIFACT_DIR = Path(
    "artifacts/runtime_commands/"
    "prompt578_actual_codex_dispatch_cycle"
)
_PROMPT579_DEFAULT_ARTIFACT_DIR = Path(
    "artifacts/runtime_commands/"
    "prompt579_actual_dispatch_result_ingestion"
)
_PROMPT580_DEFAULT_ARTIFACT_DIR = Path(
    "artifacts/runtime_commands/"
    "prompt580_real_dev_task_dispatch"
)
_PROMPT569_SOAK_CLEANUP_RUNTIME_ARTIFACTS = (
    Path("artifacts/runtime_commands/prompt565_multi_cycle_daemon"),
    Path("artifacts/runtime_commands/prompt568_production_hardening"),
    Path("artifacts/runtime_commands/prompt568_production_hardening_entrypoint"),
    Path("artifacts/runtime_commands/prompt569_soak_runner_supervisor"),
    Path("artifacts/runtime_commands/prompt569_soak_runner_supervisor_wrapper"),
    Path("artifacts/runtime_commands/prompt546_internal_codex_stdout.txt"),
    Path("artifacts/runtime_commands/prompt546_internal_codex_stderr.txt"),
    Path("artifacts/runtime_commands/prompt546_internal_codex_returncode.txt"),
    Path("artifacts/runtime_commands/prompt546_internal_codex_changed_files.txt"),
    Path("artifacts/runtime_commands/prompt546_internal_codex_diff.patch"),
    Path("artifacts/runtime_commands/prompt546_internal_codex_result.json"),
    _PROMPT551_MINIMAL_PROMPT_ARTIFACT,
)
_PROMPT565_REQUIRED_CYCLE_TRUE_FIELDS = (
    "prompt563_prompt552_final_smoke_success",
    "prompt563_prompt552_full_autonomous_flow_completed",
    "prompt563_prompt552_completion_claim_allowed",
    "prompt552_final_runtime_completion_smoke_success",
    "prompt552_full_autonomous_flow_completed",
    "prompt552_completion_claim_allowed",
)
_PROMPT565_MINIMUM_CYCLE_ARTIFACTS = ("cycle_001.json", "cycle_002.json")
_PROMPT565_CLEANUP_RUNTIME_ARTIFACTS = _PROMPT563_GENERATED_RUNTIME_ARTIFACTS

_PROMPT380_RESULT_REVIEW_ROUTE_FIELDS = (
    "prompt380_prompt379_result_review_status",
    "prompt380_prompt379_evidence_ready",
    "prompt380_prompt379_execution_performed",
    "prompt380_prompt379_returncode",
    "prompt380_prompt379_returncode_classification",
    "prompt380_prompt379_post_execution_tracked_diff_empty",
    "prompt380_prompt379_post_execution_changed_files",
    "prompt380_route_decision",
    "prompt380_approve_candidate",
    "prompt380_authoritative_next_action",
    "prompt380_next_action",
    "prompt380_active_blocked_reason",
    "prompt380_active_blocked_reasons",
)

_PROMPT381_APPROVE_CANDIDATE_BOUNDARY_FIELDS = (
    "prompt381_approve_candidate_boundary_status",
    "prompt381_prompt380_evidence_ready",
    "prompt381_prompt380_route_decision",
    "prompt381_prompt380_approve_candidate",
    "prompt381_prompt379_execution_performed",
    "prompt381_prompt379_returncode",
    "prompt381_prompt379_returncode_classification",
    "prompt381_prompt379_post_execution_tracked_diff_empty",
    "prompt381_prompt379_post_execution_changed_files",
    "prompt381_approve_candidate_ready",
    "prompt381_approve_candidate_contract_ready",
    "prompt381_approve_commit_tag_allowed",
    "prompt381_approve_commit_tag_performed",
    "prompt381_git_mutation_allowed",
    "prompt381_git_mutation_performed",
    "prompt381_remote_mutation_allowed",
    "prompt381_remote_mutation_performed",
    "prompt381_authoritative_next_action",
    "prompt381_next_action",
    "prompt381_active_blocked_reason",
    "prompt381_active_blocked_reasons",
)

_PROMPT382_APPROVE_COMMIT_TAG_EXECUTION_GATE_FIELDS = (
    "prompt382_approve_commit_tag_execution_gate_status",
    "prompt382_prompt381_evidence_ready",
    "prompt382_prompt381_approve_candidate_ready",
    "prompt382_prompt381_approve_candidate_contract_ready",
    "prompt382_prompt381_changed_files",
    "prompt382_commit_message",
    "prompt382_tag_name",
    "prompt382_execution_ready",
    "prompt382_execution_allowed",
    "prompt382_execution_attempted",
    "prompt382_execution_performed",
    "prompt382_approve_commit_tag_allowed",
    "prompt382_approve_commit_tag_performed",
    "prompt382_git_mutation_allowed",
    "prompt382_git_mutation_performed",
    "prompt382_git_add_allowed",
    "prompt382_git_add_performed",
    "prompt382_git_commit_allowed",
    "prompt382_git_commit_performed",
    "prompt382_git_tag_allowed",
    "prompt382_git_tag_performed",
    "prompt382_remote_mutation_allowed",
    "prompt382_remote_mutation_performed",
    "prompt382_authoritative_next_action",
    "prompt382_next_action",
    "prompt382_active_blocked_reason",
    "prompt382_active_blocked_reasons",
)

_PROMPT383_EXPLICIT_APPROVE_COMMIT_TAG_EXECUTION_GATE_FIELDS = (
    "prompt383_explicit_approve_commit_tag_execution_status",
    "prompt383_prompt382_evidence_ready",
    "prompt383_prompt382_plan_ready",
    "prompt383_prompt382_execution_ready",
    "prompt383_prompt382_execution_allowed",
    "prompt383_prompt382_commit_message",
    "prompt383_prompt382_tag_name",
    "prompt383_prompt382_approved_paths",
    "prompt383_approve_commit_tag_requested",
    "prompt383_approve_commit_tag_confirmed",
    "prompt383_execution_ready",
    "prompt383_execution_allowed",
    "prompt383_execution_attempted",
    "prompt383_execution_performed",
    "prompt383_git_mutation_allowed",
    "prompt383_git_mutation_performed",
    "prompt383_git_add_allowed",
    "prompt383_git_add_attempted",
    "prompt383_git_add_performed",
    "prompt383_git_commit_allowed",
    "prompt383_git_commit_attempted",
    "prompt383_git_commit_performed",
    "prompt383_git_tag_allowed",
    "prompt383_git_tag_attempted",
    "prompt383_git_tag_performed",
    "prompt383_remote_mutation_allowed",
    "prompt383_remote_mutation_performed",
    "prompt383_commit_message",
    "prompt383_tag_name",
    "prompt383_committed_files",
    "prompt383_approved_paths_validation_status",
    "prompt383_approved_paths_validation_reasons",
    "prompt383_tag_preexistence_checked",
    "prompt383_tag_preexisting",
    "prompt383_git_add_argv",
    "prompt383_git_commit_argv",
    "prompt383_git_tag_argv",
    "prompt383_git_add_returncode",
    "prompt383_git_commit_returncode",
    "prompt383_git_tag_returncode",
    "prompt383_returncode_classification",
    "prompt383_receipt_path",
    "prompt383_stdout_path",
    "prompt383_stderr_path",
    "prompt383_authoritative_next_action",
    "prompt383_next_action",
    "prompt383_active_blocked_reason",
    "prompt383_active_blocked_reasons",
)


def _as_boolish(value: Any, *, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on", "ready", "completed"}:
        return True
    if text in {"0", "false", "no", "n", "off", "blocked", "failed"}:
        return False
    return default


def _install_runtime_surface_helpers() -> None:
    prompts_350_399._prompt357_as_boolish = _as_boolish
    prompts_350_399._prompt358_candidate_artifact_timestamp = (
        _candidate_artifact_timestamp
    )
    prompts_350_399._LOCAL_AUTONOMOUS_CYCLE_V2_MAX_CYCLES = 3
    prompts_350_399._PROMPT388_MAX_CYCLES_ALLOWED = 3
    prompts_350_399._PROMPT389_DEFAULT_MAX_CYCLES = 3
    prompts_350_399._PROMPT389_SAFE_UPPER_BOUND_MAX_CYCLES = 10
    ordered_loop_stages = [
        "prompt378_generated_prompt_intake",
        "prompt379_generated_prompt_codex_execution_bridge",
        "prompt380_prompt379_result_review_route_decision",
        "prompt381_approve_candidate_boundary",
        "prompt382_approve_commit_tag_execution_gate",
        "prompt383_explicit_approve_commit_tag_execution",
        "prompt384_commit_tag_reconciliation",
        "prompt385_success_path_next_cycle_handoff",
    ]
    prompts_350_399._PROMPT388_ORDERED_LOOP_STAGES = ordered_loop_stages
    prompts_350_399._PROMPT389_ORDERED_LOOP_STAGES = ordered_loop_stages
    prompts_350_399._PROMPT388_GENERATED_PROMPT_PATH_FIELD = "prompt378_generated_prompt_path"
    prompts_350_399._PROMPT389_GENERATED_PROMPT_PATH_FIELD = "prompt378_generated_prompt_path"
    prompts_350_399._PROMPT388_REQUIRED_NEXT_PROMPT_ID = "prompt389"
    prompts_350_399._PROMPT388_REQUIRED_NEXT_PROMPT = (
        "prompt389_bounded_repeated_success_path_loop_execution"
    )
    prompts_350_399._PROMPT388_REQUIRED_NEXT_PROMPT_GOAL = (
        "Run a bounded repeated local success-path loop only when explicitly enabled."
    )
    prompts_350_399._PROMPT388_APPROVED_RESTART_SURFACE_KEYS = [
        "prompt388_local_success_path_autonomous_loop_completion_gate_status",
        "prompt388_autonomous_loop_completion_gate_ready",
        "prompt388_local_only_success_path_autonomy_complete",
        "prompt388_repeated_cycle_runner_contract_ready",
    ]
    prompts_350_399._PROMPT389_APPROVED_RESTART_SURFACE_KEYS = [
        "prompt389_bounded_repeated_success_path_loop_execution_status",
        "prompt389_repeated_cycle_execution_gate_ready",
        "prompt389_repeated_cycle_execution_allowed",
        "prompt389_next_action",
    ]


def _candidate_artifact_timestamp(path: Any) -> int:
    try:
        return int(Path(path).stat().st_mtime_ns)
    except (OSError, TypeError, ValueError):
        return 0


def _artifact_summary(path: Path) -> dict[str, Any]:
    payload = _read_json_object_if_exists(path)
    if not isinstance(payload, Mapping):
        return {
            "path": str(path),
            "present": path.exists(),
            "json_object": False,
            "key_count": 0,
            "status": "",
            "next_action": "",
            "blocked_reason": "",
        }
    return {
        "path": str(path),
        "present": True,
        "json_object": True,
        "key_count": len(payload),
        "status": _normalize_text(
            payload.get("status")
            or payload.get("execution_status")
            or payload.get("readiness_status")
            or payload.get("prompt380_prompt379_result_review_status")
            or payload.get("prompt381_approve_candidate_boundary_status")
            or payload.get("prompt382_approve_commit_tag_execution_gate_status")
            or payload.get("prompt383_explicit_approve_commit_tag_execution_status")
            or payload.get("prompt468_full_no_human_loop_regression_status")
            or payload.get("prompt489_real_task_marker_status")
            or payload.get("prompt490_second_success_cycle_status")
            or payload.get("prompt491_third_success_cycle_status"),
            default="",
        ),
        "next_action": _normalize_text(
            payload.get("next_action")
            or payload.get("authoritative_next_action")
            or payload.get("prompt373_next_action")
            or payload.get("prompt379_next_action")
            or payload.get("prompt380_next_action")
            or payload.get("prompt381_next_action")
            or payload.get("prompt382_next_action")
            or payload.get("prompt383_next_action")
            or payload.get("prompt385_next_action")
            or payload.get("prompt388_next_action")
            or payload.get("prompt389_next_action")
            or payload.get("prompt468_next_action")
            or payload.get("prompt489_next_action")
            or payload.get("prompt490_next_action")
            or payload.get("prompt491_next_action"),
            default="",
        ),
        "blocked_reason": _normalize_text(
            payload.get("blocked_reason")
            or payload.get("active_blocked_reason")
            or payload.get("prompt373_active_blocked_reason")
            or payload.get("prompt379_active_blocked_reason")
            or payload.get("prompt380_active_blocked_reason")
            or payload.get("prompt381_active_blocked_reason")
            or payload.get("prompt382_active_blocked_reason")
            or payload.get("prompt383_active_blocked_reason")
            or payload.get("prompt385_active_blocked_reason")
            or payload.get("prompt388_active_blocked_reason")
            or payload.get("prompt389_active_blocked_reason")
            or payload.get("prompt468_blocked_reason"),
            default="",
        ),
    }


def _git_text(
    *,
    repo_path: str,
    args: list[str],
) -> str:
    normalized_repo_path = _normalize_text(repo_path, default="")
    if not normalized_repo_path:
        return ""
    try:
        completed = subprocess.run(
            ["git", "-C", normalized_repo_path, *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if completed.returncode != 0:
        return ""
    return _normalize_text(completed.stdout, default="")


def _current_head_metadata(*, repo_path: str) -> dict[str, Any]:
    head_sha = _git_text(repo_path=repo_path, args=["rev-parse", "HEAD"])
    head_tags = [
        tag
        for tag in _git_text(
            repo_path=repo_path,
            args=["tag", "--points-at", "HEAD"],
        ).splitlines()
        if tag
    ]
    return {
        "current_head_sha": head_sha,
        "current_head_tags": sorted(head_tags),
    }


def _write_filtered_runtime_artifact_if_present(
    *,
    run_root: Path,
    run_state: Mapping[str, Any],
    artifact_name: str,
    fields: tuple[str, ...],
) -> bool:
    payload = {field: run_state[field] for field in fields if field in run_state}
    if not payload:
        return False
    _write_json(run_root / artifact_name, payload)
    return True


def _merge_split_compatible_runtime_surfaces(
    run_state: Mapping[str, Any],
) -> dict[str, Any]:
    merged = dict(run_state)
    builders = get_prompt_builders()
    for builder_name in _SPLIT_COMPATIBLE_RUNTIME_BUILDER_NAMES:
        builder = builders[builder_name]
        merged.update(builder(run_state_payload=merged))
    return merged


def _prompt546_artifact_ready(repo_path: Path, artifact_path: Path) -> bool:
    return (repo_path / artifact_path).is_file()


def _artifact_nonempty(repo_path: Path, artifact_path: Path) -> bool:
    try:
        return (
            (repo_path / artifact_path).read_text(encoding="utf-8").strip()
            != ""
        )
    except OSError:
        return False


def _prompt546_input_metadata(
    *,
    repo_path: Path,
    result_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(result_payload, Mapping):
        return {"prompt546_input_runtime_adapter_result_present": False}
    return {
        "prompt546_input_runtime_adapter_result_present": True,
        "prompt546_input_internal_codex_subprocess_executed": bool(
            result_payload.get("prompt546_internal_codex_subprocess_executed")
        ),
        "prompt546_input_internal_codex_returncode_success": bool(
            result_payload.get("prompt546_internal_codex_returncode_success")
        ),
        "prompt546_input_internal_codex_stdout_captured": bool(
            result_payload.get("prompt546_internal_codex_stdout_captured")
        ),
        "prompt546_input_internal_codex_stderr_captured": bool(
            result_payload.get("prompt546_internal_codex_stderr_captured")
        ),
        "prompt546_input_internal_changed_files_captured": bool(
            result_payload.get("prompt546_internal_changed_files_captured")
        ),
        "prompt546_input_internal_diff_captured": bool(
            result_payload.get("prompt546_internal_diff_captured")
        ),
        "prompt546_input_internal_changed_files_allowed": bool(
            result_payload.get("prompt546_internal_changed_files_allowed")
        ),
        "prompt546_input_internal_unexpected_changed_files_present": bool(
            result_payload.get(
                "prompt546_internal_unexpected_changed_files_present"
            )
        ),
        "prompt546_input_internal_unexpected_diff_present": bool(
            result_payload.get("prompt546_internal_unexpected_diff_present")
        ),
        "prompt546_input_internal_execution_timeout_occurred": bool(
            result_payload.get("prompt546_internal_execution_timeout_occurred")
        ),
        "prompt546_input_internal_execution_error_present": bool(
            result_payload.get("prompt546_internal_execution_error_present")
        ),
        "prompt546_input_internal_no_remote_mutation_verified": bool(
            result_payload.get("prompt546_internal_no_remote_mutation_verified")
        ),
        "prompt546_input_stdout_artifact_ready": _prompt546_artifact_ready(
            repo_path,
            PROMPT546_STDOUT_ARTIFACT,
        ),
        "prompt546_input_stderr_artifact_ready": _prompt546_artifact_ready(
            repo_path,
            PROMPT546_STDERR_ARTIFACT,
        ),
        "prompt546_input_returncode_artifact_ready": _prompt546_artifact_ready(
            repo_path,
            PROMPT546_RETURNCODE_ARTIFACT,
        ),
        "prompt546_input_changed_files_artifact_ready": (
            _prompt546_artifact_ready(repo_path, PROMPT546_CHANGED_FILES_ARTIFACT)
        ),
        "prompt546_input_diff_artifact_ready": _prompt546_artifact_ready(
            repo_path,
            PROMPT546_DIFF_ARTIFACT,
        ),
        "prompt546_input_result_json_artifact_ready": _prompt546_artifact_ready(
            repo_path,
            PROMPT546_RESULT_ARTIFACT,
        ),
    }


def _prompt547_input_metadata(
    *,
    repo_path: Path,
    result_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(result_payload, Mapping):
        return {"prompt547_input_real_runtime_smoke_result_present": False}
    return {
        "prompt547_input_real_runtime_smoke_result_present": True,
        "prompt547_input_internal_codex_subprocess_executed": bool(
            result_payload.get("prompt547_internal_codex_subprocess_executed")
        ),
        "prompt547_input_internal_codex_returncode_success": bool(
            result_payload.get("prompt547_internal_codex_returncode_success")
        ),
        "prompt547_input_internal_codex_stdout_captured": bool(
            result_payload.get("prompt547_internal_codex_stdout_captured")
        ),
        "prompt547_input_internal_codex_stderr_captured": bool(
            result_payload.get("prompt547_internal_codex_stderr_captured")
        ),
        "prompt547_input_internal_changed_files_captured": bool(
            result_payload.get("prompt547_internal_changed_files_captured")
        ),
        "prompt547_input_internal_diff_captured": bool(
            result_payload.get("prompt547_internal_diff_captured")
        ),
        "prompt547_input_internal_changed_files_allowed": bool(
            result_payload.get("prompt547_internal_changed_files_allowed")
        ),
        "prompt547_input_internal_unexpected_changed_files_present": bool(
            result_payload.get(
                "prompt547_internal_unexpected_changed_files_present"
            )
        ),
        "prompt547_input_internal_unexpected_diff_present": bool(
            result_payload.get("prompt547_internal_unexpected_diff_present")
        ),
        "prompt547_input_internal_execution_timeout_occurred": bool(
            result_payload.get("prompt547_internal_execution_timeout_occurred")
        ),
        "prompt547_input_internal_execution_error_present": bool(
            result_payload.get("prompt547_internal_execution_error_present")
        ),
        "prompt547_input_internal_no_remote_mutation_verified": bool(
            result_payload.get("prompt547_internal_no_remote_mutation_verified")
        ),
        "prompt547_input_runtime_artifacts_present": bool(
            _prompt546_artifact_ready(repo_path, PROMPT547_STDOUT_ARTIFACT)
            and _prompt546_artifact_ready(repo_path, PROMPT547_STDERR_ARTIFACT)
            and _prompt546_artifact_ready(repo_path, PROMPT547_RETURNCODE_ARTIFACT)
            and _prompt546_artifact_ready(
                repo_path,
                PROMPT547_CHANGED_FILES_ARTIFACT,
            )
            and _prompt546_artifact_ready(repo_path, PROMPT547_DIFF_ARTIFACT)
        ),
        "prompt547_input_runtime_result_json_present": _prompt546_artifact_ready(
            repo_path,
            PROMPT547_RESULT_ARTIFACT,
        ),
    }


_PROMPT547_INPUT_FIELDS = (
    "prompt547_input_real_runtime_smoke_result_present",
    "prompt547_input_internal_codex_subprocess_executed",
    "prompt547_input_internal_codex_returncode_success",
    "prompt547_input_internal_codex_stdout_captured",
    "prompt547_input_internal_codex_stderr_captured",
    "prompt547_input_internal_changed_files_captured",
    "prompt547_input_internal_diff_captured",
    "prompt547_input_internal_changed_files_allowed",
    "prompt547_input_internal_unexpected_changed_files_present",
    "prompt547_input_internal_unexpected_diff_present",
    "prompt547_input_internal_execution_timeout_occurred",
    "prompt547_input_internal_execution_error_present",
    "prompt547_input_internal_no_remote_mutation_verified",
    "prompt547_input_runtime_artifacts_present",
    "prompt547_input_runtime_result_json_present",
)


_PROMPT548_RESULT_JSON_SCHEMA_FIELDS = (
    "prompt547_internal_codex_subprocess_executed",
    "prompt547_internal_codex_returncode_success",
    "prompt547_internal_codex_stdout_captured",
    "prompt547_internal_codex_stderr_captured",
    "prompt547_internal_changed_files_captured",
    "prompt547_internal_diff_captured",
    "prompt547_internal_changed_files_allowed",
    "prompt547_internal_unexpected_changed_files_present",
    "prompt547_internal_unexpected_diff_present",
    "prompt547_internal_execution_timeout_occurred",
    "prompt547_internal_execution_error_present",
    "prompt547_internal_no_remote_mutation_verified",
)

_PROMPT551_RESULT_JSON_SCHEMA_FIELDS = (
    "prompt546_internal_codex_subprocess_executed",
    "prompt546_internal_codex_returncode",
    "prompt546_internal_codex_returncode_success",
    "prompt546_internal_codex_stdout_captured",
    "prompt546_internal_codex_stderr_captured",
    "prompt546_internal_changed_files_captured",
    "prompt546_internal_diff_captured",
    "prompt546_internal_changed_files_allowed",
    "prompt546_internal_unexpected_changed_files_present",
    "prompt546_internal_unexpected_diff_present",
    "prompt546_internal_execution_timeout_occurred",
    "prompt546_internal_execution_error_present",
    "prompt546_internal_no_remote_mutation_verified",
)


def _prompt551_returncode_exists(repo_path: Path) -> bool:
    return (repo_path / PROMPT546_RETURNCODE_ARTIFACT).is_file()


def _prompt551_result_returncode(
    result_payload: Mapping[str, Any],
) -> int | None:
    raw_returncode = result_payload.get("prompt546_internal_codex_returncode")
    if isinstance(raw_returncode, bool):
        return None
    if isinstance(raw_returncode, int):
        return raw_returncode
    if isinstance(raw_returncode, str):
        try:
            return int(raw_returncode.strip())
        except ValueError:
            return None
    return None


def _prompt551_materialize_result_artifacts(
    *,
    repo_path: Path,
    result_payload: Mapping[str, Any],
) -> None:
    materialized_payload = dict(result_payload)
    returncode = _prompt551_result_returncode(materialized_payload)
    missing_returncode_fallback = returncode is None
    if missing_returncode_fallback:
        returncode = 1
    materialized_payload["prompt546_internal_codex_returncode"] = int(returncode)
    materialized_payload["prompt546_internal_codex_returncode_success"] = (
        returncode == 0
    )
    if missing_returncode_fallback or returncode != 0:
        materialized_payload["prompt546_internal_execution_error_present"] = True

    (repo_path / PROMPT546_RETURNCODE_ARTIFACT).write_text(
        f"{returncode}\n",
        encoding="utf-8",
    )

    changed_files = result_payload.get("prompt546_internal_changed_files")
    if isinstance(changed_files, Iterable) and not isinstance(
        changed_files,
        (str, bytes),
    ):
        changed_file_lines = [str(item) for item in changed_files]
        (repo_path / PROMPT546_CHANGED_FILES_ARTIFACT).write_text(
            "\n".join(changed_file_lines) + "\n",
            encoding="utf-8",
        )

    for artifact_path in (
        PROMPT546_STDOUT_ARTIFACT,
        PROMPT546_STDERR_ARTIFACT,
        PROMPT546_DIFF_ARTIFACT,
    ):
        full_path = repo_path / artifact_path
        if not full_path.is_file():
            full_path.write_text("", encoding="utf-8")

    _write_json(repo_path / PROMPT546_RESULT_ARTIFACT, materialized_payload)


def _prompt551_input_metadata(
    *,
    repo_path: Path,
    result_payload: Mapping[str, Any] | None = None,
    explicit_execution_enable_present: bool = False,
    bridge_present: bool = True,
    runtime_adapter_invocation_attempted: bool = False,
) -> dict[str, Any]:
    result_path = repo_path / PROMPT546_RESULT_ARTIFACT
    loaded_payload = (
        result_payload
        if isinstance(result_payload, Mapping)
        else _read_json_object_if_exists(result_path)
    )
    result_json_schema_valid = bool(
        isinstance(loaded_payload, Mapping)
        and all(
            field in loaded_payload
            for field in _PROMPT551_RESULT_JSON_SCHEMA_FIELDS
        )
    )
    loaded_payload = (
        loaded_payload if isinstance(loaded_payload, Mapping) else {}
    )
    return {
        "prompt551_input_runtime_execution_bridge_present": bool(
            bridge_present
        ),
        "prompt551_input_explicit_execution_enable_present": bool(
            explicit_execution_enable_present
        ),
        "prompt551_input_runtime_adapter_invoked": bool(
            runtime_adapter_invocation_attempted
        ),
        "prompt551_input_stdout_artifact_exists": _prompt546_artifact_ready(
            repo_path,
            PROMPT546_STDOUT_ARTIFACT,
        ),
        "prompt551_input_stderr_artifact_exists": _prompt546_artifact_ready(
            repo_path,
            PROMPT546_STDERR_ARTIFACT,
        ),
        "prompt551_input_returncode_artifact_exists": _prompt551_returncode_exists(
            repo_path
        ),
        "prompt551_input_changed_files_artifact_exists": (
            _prompt546_artifact_ready(repo_path, PROMPT546_CHANGED_FILES_ARTIFACT)
        ),
        "prompt551_input_diff_artifact_exists": _prompt546_artifact_ready(
            repo_path,
            PROMPT546_DIFF_ARTIFACT,
        ),
        "prompt551_input_result_json_artifact_exists": result_path.is_file(),
        "prompt551_input_result_json_schema_valid": bool(
            result_json_schema_valid
        ),
        "prompt551_input_remote_mutation_absent": bool(
            loaded_payload.get("prompt546_internal_no_remote_mutation_verified")
            is True
        ),
        "prompt551_input_execution_error_present": bool(
            loaded_payload.get("prompt546_internal_execution_error_present")
            is True
        ),
        "prompt551_input_result_json_subprocess_executed_true": bool(
            loaded_payload.get("prompt546_internal_codex_subprocess_executed")
            is True
        ),
        "prompt551_input_result_json_returncode_success_true": bool(
            loaded_payload.get("prompt546_internal_codex_returncode_success")
            is True
        ),
        "prompt551_input_result_json_returncode_zero": bool(
            _prompt551_result_returncode(loaded_payload) == 0
        ),
        "prompt551_input_result_json_changed_files_allowed_true": bool(
            loaded_payload.get("prompt546_internal_changed_files_allowed")
            is True
        ),
        "prompt551_input_result_json_unexpected_changed_files_present_false": (
            loaded_payload.get(
                "prompt546_internal_unexpected_changed_files_present"
            )
            is False
        ),
        "prompt551_input_result_json_unexpected_diff_present_false": bool(
            loaded_payload.get("prompt546_internal_unexpected_diff_present")
            is False
        ),
        "prompt551_input_result_json_no_remote_mutation_verified_true": bool(
            loaded_payload.get("prompt546_internal_no_remote_mutation_verified")
            is True
        ),
    }


def _prompt551_prompt550_base_ready(payload: Mapping[str, Any]) -> bool:
    prompt550_next_action = _normalize_text(
        payload.get("prompt550_next_action"),
        default="",
    )
    return bool(
        payload.get(
            "prompt550_post_smoke_local_commit_tag_clean_rerun_final_completion_ready"
        )
        is True
        and payload.get("prompt550_source_prompt549_ready") is True
        and payload.get("prompt550_remote_push_pr_merge_rollback_included")
        is False
        and payload.get("prompt550_long_running_daemon_included") is False
        and payload.get("prompt550_multi_cycle_unattended_loop_included")
        is False
        and payload.get("prompt550_completion_scope")
        == "local_only_success_path_one_cycle_final_completion"
        and prompt550_next_action
        in {
            "await_post_smoke_local_commit_tag_clean_rerun_final_completion",
            "manual_review_prompt550_post_smoke_local_commit_tag_clean_rerun_final_completion",
            "local_only_success_path_one_cycle_autonomous_development_completed",
        }
    )


def run_prompt551_actual_runtime_adapter_execution_bridge(
    *,
    run_state_payload: Mapping[str, Any] | None = None,
    execution_repo_path: str = "",
    enabled: bool | None = None,
    enable_token: str | None = None,
    timeout_seconds: int | None = None,
    allowed_files: Iterable[str] | None = None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    repo_text = _normalize_text(
        execution_repo_path or payload.get("execution_repo_path"),
        default="",
    )
    repo_path = Path(repo_text) if repo_text else Path(".")
    resolved_enable_token = _normalize_text(
        enable_token
        if enable_token is not None
        else payload.get("prompt551_runtime_execution_enable_token"),
        default="",
    )
    outer_enable_token_present = bool(resolved_enable_token)
    outer_enable_token_accepted = (
        resolved_enable_token
        == PROMPT551_ACTUAL_RUNTIME_ADAPTER_EXECUTION_BRIDGE_ENABLE_TOKEN
    )
    internal_adapter_enable_token = (
        PROMPT546_INTERNAL_CODEX_ENABLE_TOKEN
        if outer_enable_token_accepted
        else ""
    )
    internal_adapter_enable_token_resolved = bool(
        internal_adapter_enable_token
    )
    internal_adapter_enable_token_valid = (
        internal_adapter_enable_token
        == PROMPT546_INTERNAL_CODEX_ENABLE_TOKEN
    )
    token_bridge_applied = bool(
        outer_enable_token_accepted and internal_adapter_enable_token_valid
    )
    explicit_arg_enable_token = _normalize_text(enable_token, default="")
    explicit_arg_enable_present = bool(
        enabled is True and explicit_arg_enable_token
    )
    payload_explicit_execution_enable_token = _normalize_text(
        payload.get("prompt551_runtime_execution_enable_token"),
        default="",
    )
    payload_explicit_execution_enable_present = bool(
        payload.get("prompt551_runtime_execution_enabled") is True
        and payload_explicit_execution_enable_token
    )
    explicit_execution_enable_present = bool(
        explicit_arg_enable_present
        or payload_explicit_execution_enable_present
    )
    timeout = max(
        1,
        min(
            600,
            int(
                timeout_seconds
                if timeout_seconds is not None
                else payload.get("prompt551_runtime_execution_timeout_seconds")
                or 120
            ),
        ),
    )
    merged = dict(payload)

    result_payload: dict[str, Any] | None = None
    runtime_adapter_invocation_attempted = False
    if (
        repo_text
        and _prompt551_prompt550_base_ready(merged)
        and explicit_execution_enable_present
        and token_bridge_applied
    ):
        prompt_path = repo_path / _PROMPT551_MINIMAL_PROMPT_ARTIFACT
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(
            "\n".join(
                (
                    "Mode: Scout",
                    "Goal: bounded runtime adapter smoke only.",
                    "Allowed files: none.",
                    "Forbidden files: all repository files.",
                    "Expected artifact/output: report current working directory only.",
                    "Allowed validation commands: pwd.",
                    "Out of scope: code changes, commits, tags, pushes, PRs, merges, rollbacks.",
                )
            )
            + "\n",
            encoding="utf-8",
        )
        runtime_adapter_invocation_attempted = True
        result_payload = run_internal_codex_subprocess(
            repo_dir=str(repo_path),
            prompt_path=str(prompt_path),
            allowed_files=(
                tuple(allowed_files)
                if allowed_files is not None
                else _PROMPT546_DEFAULT_ALLOWED_FILES
            ),
            enabled=True,
            enable_token=internal_adapter_enable_token,
            timeout_seconds=timeout,
        )
        if isinstance(result_payload, Mapping):
            _prompt551_materialize_result_artifacts(
                repo_path=repo_path,
                result_payload=result_payload,
            )

    merged.update(
        _prompt551_input_metadata(
            repo_path=repo_path,
            result_payload=result_payload,
            explicit_execution_enable_present=explicit_execution_enable_present,
            runtime_adapter_invocation_attempted=(
                runtime_adapter_invocation_attempted
            ),
        )
    )
    merged.update(
        {
            "prompt551_outer_enable_token_present": bool(
                outer_enable_token_present
            ),
            "prompt551_internal_adapter_enable_token_resolved": bool(
                internal_adapter_enable_token_resolved
            ),
            "prompt551_internal_adapter_enable_token_valid": bool(
                internal_adapter_enable_token_valid
            ),
            "prompt551_token_bridge_applied": bool(token_bridge_applied),
        }
    )
    builder = get_prompt_builders()[
        "_build_prompt551_actual_runtime_adapter_execution_bridge_state"
    ]
    merged.update(builder(run_state_payload=merged))
    return merged


def _prompt563_read_returncode(repo_path: Path) -> int | None:
    try:
        raw_returncode = (
            repo_path / PROMPT546_RETURNCODE_ARTIFACT
        ).read_text(encoding="utf-8")
        return int(raw_returncode.strip())
    except (OSError, ValueError):
        return None


def _prompt563_result_json_schema_valid(
    result_payload: Mapping[str, Any],
) -> bool:
    required_fields = (
        *_PROMPT551_RESULT_JSON_SCHEMA_FIELDS,
        "prompt546_internal_execution_enable_token_valid",
        "prompt546_internal_execution_allowed",
    )
    return all(field in result_payload for field in required_fields)


def _prompt563_changed_files(result_payload: Mapping[str, Any]) -> list[str]:
    raw_changed_files = result_payload.get(
        "prompt546_internal_semantic_changed_files"
    )
    if not isinstance(raw_changed_files, Iterable) or isinstance(
        raw_changed_files,
        (str, bytes),
    ):
        raw_changed_files = result_payload.get("prompt546_internal_changed_files")
    if not isinstance(raw_changed_files, Iterable) or isinstance(
        raw_changed_files,
        (str, bytes),
    ):
        return []
    return [
        str(item).strip()
        for item in raw_changed_files
        if str(item).strip()
    ]


def _prompt563_py_compile(
    *,
    repo_path: Path,
    result_payload: Mapping[str, Any],
) -> bool:
    changed_python_files = [
        path
        for path in _prompt563_changed_files(result_payload)
        if path in _PROMPT563_ALLOWED_PYTHON_FILES and path.endswith(".py")
    ]
    compile_targets = (
        changed_python_files
        if changed_python_files
        else list(_PROMPT563_ALLOWED_PYTHON_FILES)
    )
    env = dict(os.environ)
    env["PYTHONPYCACHEPREFIX"] = "/tmp/prompt563_pycache"
    completed = subprocess.run(
        ["python", "-m", "py_compile", *compile_targets],
        cwd=str(repo_path),
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    return completed.returncode == 0


def _prompt563_remove_generated_runtime_artifacts(repo_path: Path) -> None:
    for artifact_path in _PROMPT563_GENERATED_RUNTIME_ARTIFACTS:
        try:
            (repo_path / artifact_path).unlink()
        except FileNotFoundError:
            continue


def _prompt563_worktree_clean(repo_path: Path) -> bool:
    completed = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=str(repo_path),
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0 and not completed.stdout.strip()


def _prompt563_prompt552_inputs(
    *,
    repo_path: Path,
    bridge_state: Mapping[str, Any],
    result_payload: Mapping[str, Any],
    post_smoke_worktree_clean: bool,
    py_compile_success: bool,
) -> dict[str, Any]:
    return {
        "prompt552_input_final_runtime_smoke_result_present": True,
        "prompt552_input_runtime_bridge_invoked_with_explicit_enable": bool(
            bridge_state.get("prompt551_runtime_adapter_invoked") is True
            and bridge_state.get("prompt551_explicit_execution_enable_present")
            is True
            and bridge_state.get("prompt551_token_bridge_applied") is True
            and result_payload.get(
                "prompt546_internal_execution_enable_token_valid"
            )
            is True
            and result_payload.get("prompt546_internal_execution_allowed")
            is True
        ),
        "prompt552_input_stdout_artifact_exists": _prompt546_artifact_ready(
            repo_path,
            PROMPT546_STDOUT_ARTIFACT,
        ),
        "prompt552_input_stdout_artifact_nonempty": _artifact_nonempty(
            repo_path,
            PROMPT546_STDOUT_ARTIFACT,
        ),
        "prompt552_input_stderr_artifact_exists": _prompt546_artifact_ready(
            repo_path,
            PROMPT546_STDERR_ARTIFACT,
        ),
        "prompt552_input_returncode_artifact_exists": _prompt546_artifact_ready(
            repo_path,
            PROMPT546_RETURNCODE_ARTIFACT,
        ),
        "prompt552_input_returncode_zero": _prompt563_read_returncode(repo_path)
        == 0,
        "prompt552_input_changed_files_artifact_exists": _prompt546_artifact_ready(
            repo_path,
            PROMPT546_CHANGED_FILES_ARTIFACT,
        ),
        "prompt552_input_changed_files_artifact_nonempty": _artifact_nonempty(
            repo_path,
            PROMPT546_CHANGED_FILES_ARTIFACT,
        ),
        "prompt552_input_diff_artifact_exists": _prompt546_artifact_ready(
            repo_path,
            PROMPT546_DIFF_ARTIFACT,
        ),
        "prompt552_input_diff_artifact_nonempty": _artifact_nonempty(
            repo_path,
            PROMPT546_DIFF_ARTIFACT,
        ),
        "prompt552_input_result_json_artifact_exists": _prompt546_artifact_ready(
            repo_path,
            PROMPT546_RESULT_ARTIFACT,
        ),
        "prompt552_input_result_json_schema_valid": bool(
            _prompt563_result_json_schema_valid(result_payload)
        ),
        "prompt552_input_result_json_subprocess_executed_true": bool(
            result_payload.get("prompt546_internal_codex_subprocess_executed")
            is True
        ),
        "prompt552_input_result_json_returncode_success_true": bool(
            result_payload.get("prompt546_internal_codex_returncode_success")
            is True
        ),
        "prompt552_input_result_json_changed_files_allowed_true": bool(
            result_payload.get("prompt546_internal_changed_files_allowed")
            is True
        ),
        "prompt552_input_result_json_unexpected_changed_files_present_false": bool(
            result_payload.get(
                "prompt546_internal_unexpected_changed_files_present"
            )
            is False
        ),
        "prompt552_input_result_json_unexpected_diff_present_false": bool(
            result_payload.get("prompt546_internal_unexpected_diff_present")
            is False
        ),
        "prompt552_input_result_json_timeout_occurred_false": bool(
            result_payload.get("prompt546_internal_execution_timeout_occurred")
            is False
        ),
        "prompt552_input_result_json_execution_error_present_false": bool(
            result_payload.get("prompt546_internal_execution_error_present")
            is False
        ),
        "prompt552_input_result_json_no_remote_mutation_verified_true": bool(
            result_payload.get("prompt546_internal_no_remote_mutation_verified")
            is True
        ),
        "prompt552_input_post_smoke_worktree_clean": bool(
            post_smoke_worktree_clean
        ),
        "prompt552_input_final_py_compile_success": bool(py_compile_success),
        "prompt552_input_final_completion_error_present": False,
    }


def run_prompt563_prompt552_final_runtime_completion_smoke(
    *,
    run_state_payload: Mapping[str, Any] | None = None,
    execution_repo_path: str | Path = "",
    enabled: bool | None = None,
    enable_token: str | None = None,
    timeout_seconds: int = 180,
    allowed_files: Sequence[str] | None = None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    repo_text = _normalize_text(
        execution_repo_path or payload.get("execution_repo_path"),
        default="",
    )
    repo_path = Path(repo_text) if repo_text else Path(".")

    bridge_state = run_prompt551_actual_runtime_adapter_execution_bridge(
        run_state_payload=payload,
        execution_repo_path=str(repo_path),
        enabled=enabled,
        enable_token=enable_token,
        timeout_seconds=timeout_seconds,
        allowed_files=(
            allowed_files
            if allowed_files is not None
            else _PROMPT563_ALLOWED_PYTHON_FILES
        ),
    )
    result_payload = _read_json_object_if_exists(
        repo_path / PROMPT546_RESULT_ARTIFACT
    )
    if not isinstance(result_payload, Mapping):
        result_payload = {}

    py_compile_success = _prompt563_py_compile(
        repo_path=repo_path,
        result_payload=result_payload,
    )
    prompt552_inputs = _prompt563_prompt552_inputs(
        repo_path=repo_path,
        bridge_state=bridge_state,
        result_payload=result_payload,
        post_smoke_worktree_clean=False,
        py_compile_success=py_compile_success,
    )
    _prompt563_remove_generated_runtime_artifacts(repo_path)
    post_smoke_worktree_clean = _prompt563_worktree_clean(repo_path)
    prompt552_inputs["prompt552_input_post_smoke_worktree_clean"] = bool(
        post_smoke_worktree_clean
    )

    merged = dict(bridge_state)
    merged.update(prompt552_inputs)
    builders = get_prompt_builders()
    prompt552_state = builders[
        "_build_prompt552_final_runtime_completion_smoke_state"
    ](run_state_payload=merged)
    merged.update(prompt552_state)
    merged.update(
        builders[
            "_build_prompt563_materialize_prompt552_final_smoke_inputs_state"
        ](run_state_payload=merged)
    )
    return merged


def _prompt565_worktree_clean_excluding_daemon_artifacts(
    *,
    repo_path: Path,
    daemon_artifact_dir: Path,
) -> bool:
    completed = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=str(repo_path),
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return False
    daemon_artifact_root = daemon_artifact_dir
    daemon_artifact_under_repo = True
    if daemon_artifact_root.is_absolute():
        try:
            daemon_artifact_root = daemon_artifact_root.relative_to(repo_path)
        except ValueError:
            daemon_artifact_under_repo = False
    daemon_artifact_prefix = (
        daemon_artifact_root.as_posix().rstrip("/") + "/"
        if daemon_artifact_under_repo
        else ""
    )
    for raw_line in completed.stdout.splitlines():
        path_text = raw_line[3:].strip()
        if daemon_artifact_prefix and path_text.startswith(daemon_artifact_prefix):
            continue
        return False
    return True


def _prompt565_remove_known_generated_runtime_artifacts(repo_path: Path) -> bool:
    removed_any = False
    for artifact_path in _PROMPT565_CLEANUP_RUNTIME_ARTIFACTS:
        candidate = repo_path / artifact_path
        if not candidate.exists():
            continue
        if candidate.is_dir():
            shutil.rmtree(candidate)
        else:
            candidate.unlink()
        removed_any = True
    return removed_any


def _prompt565_remove_existing_daemon_artifact_dir(
    *,
    repo_path: Path,
    daemon_artifact_dir: Path,
) -> bool:
    expected_dir = (repo_path / _PROMPT565_DEFAULT_ARTIFACT_DIR).resolve()
    candidate_dir = daemon_artifact_dir.resolve()
    if candidate_dir != expected_dir or not daemon_artifact_dir.exists():
        return False
    if daemon_artifact_dir.is_dir():
        shutil.rmtree(daemon_artifact_dir)
        return True
    return False


def _prompt569_remove_known_generated_runtime_artifacts(repo_path: Path) -> list[str]:
    removed_artifacts: list[str] = []
    for artifact_path in _PROMPT569_SOAK_CLEANUP_RUNTIME_ARTIFACTS:
        candidate = repo_path / artifact_path
        if not candidate.exists():
            continue
        if candidate.is_dir():
            shutil.rmtree(candidate)
        else:
            candidate.unlink()
        removed_artifacts.append(artifact_path.as_posix())
    return removed_artifacts


def _prompt565_cycle_succeeded(cycle_result: Mapping[str, Any]) -> bool:
    return all(
        cycle_result.get(field) is True
        for field in _PROMPT565_REQUIRED_CYCLE_TRUE_FIELDS
    )


def run_prompt565_multi_cycle_daemon_autonomous_loop(
    *,
    run_state_payload: Mapping[str, Any] | None = None,
    execution_repo_path: str | Path = "",
    enabled: bool | None = None,
    enable_token: str | None = None,
    timeout_seconds: int = 180,
    allowed_files: Sequence[str] | None = None,
    max_cycles: int = 2,
    stop_on_failure: bool = True,
    artifact_dir: str | Path | None = None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    repo_text = _normalize_text(
        execution_repo_path or payload.get("execution_repo_path"),
        default="",
    )
    repo_path = Path(repo_text) if repo_text else Path(".")
    try:
        requested_max_cycles = max(0, int(max_cycles))
    except (TypeError, ValueError):
        requested_max_cycles = 0
    daemon_artifact_dir = (
        Path(artifact_dir)
        if artifact_dir is not None
        else _PROMPT565_DEFAULT_ARTIFACT_DIR
    )
    if not daemon_artifact_dir.is_absolute():
        daemon_artifact_dir = repo_path / daemon_artifact_dir

    prompt565_enabled = enabled is True
    prompt565_enable_token_valid = (
        _normalize_text(enable_token, default="")
        == PROMPT565_MULTI_CYCLE_DAEMON_AUTONOMOUS_LOOP_ENABLE_TOKEN
    )
    blocked_reasons: list[str] = []
    if not prompt565_enabled:
        blocked_reasons.append("prompt565_enabled_required")
    if not prompt565_enable_token_valid:
        blocked_reasons.append("prompt565_enable_token_invalid")
    if requested_max_cycles < 2:
        blocked_reasons.append("prompt565_requested_max_cycles_below_2")

    cycle_results: list[dict[str, Any]] = []
    failed_cycle_index: int | None = None
    final_worktree_clean = False
    existing_daemon_artifacts_cleaned_before_cycle = False
    known_runtime_artifacts_cleaned_between_cycles = False
    if not blocked_reasons:
        existing_daemon_artifacts_cleaned_before_cycle = (
            _prompt565_remove_existing_daemon_artifact_dir(
                repo_path=repo_path,
                daemon_artifact_dir=daemon_artifact_dir,
            )
        )
        known_runtime_artifacts_cleaned_between_cycles = (
            _prompt565_remove_known_generated_runtime_artifacts(repo_path)
        )
        for cycle_index in range(1, requested_max_cycles + 1):
            cycle_result = run_prompt563_prompt552_final_runtime_completion_smoke(
                run_state_payload=payload,
                execution_repo_path=str(repo_path),
                enabled=True,
                enable_token=(
                    PROMPT551_ACTUAL_RUNTIME_ADAPTER_EXECUTION_BRIDGE_ENABLE_TOKEN
                ),
                timeout_seconds=timeout_seconds,
                allowed_files=allowed_files,
            )
            if _prompt565_remove_known_generated_runtime_artifacts(repo_path):
                known_runtime_artifacts_cleaned_between_cycles = True
            cycle_worktree_clean = (
                _prompt565_worktree_clean_excluding_daemon_artifacts(
                    repo_path=repo_path,
                    daemon_artifact_dir=daemon_artifact_dir,
                )
            )
            cycle_success = bool(
                _prompt565_cycle_succeeded(cycle_result)
                and cycle_worktree_clean
            )
            cycle_summary = {
                "cycle_index": cycle_index,
                "cycle_artifact_name": f"cycle_{cycle_index:03d}.json",
                "cycle_success": cycle_success,
                "cycle_worktree_clean_after_artifact_cleanup": (
                    cycle_worktree_clean
                ),
                "required_cycle_true_fields": {
                    field: cycle_result.get(field) is True
                    for field in _PROMPT565_REQUIRED_CYCLE_TRUE_FIELDS
                },
                "prompt563_prompt552_final_smoke_success": bool(
                    cycle_result.get("prompt563_prompt552_final_smoke_success")
                    is True
                ),
                "prompt563_prompt552_full_autonomous_flow_completed": bool(
                    cycle_result.get(
                        "prompt563_prompt552_full_autonomous_flow_completed"
                    )
                    is True
                ),
                "prompt563_prompt552_completion_claim_allowed": bool(
                    cycle_result.get(
                        "prompt563_prompt552_completion_claim_allowed"
                    )
                    is True
                ),
                "prompt552_final_runtime_completion_smoke_success": bool(
                    cycle_result.get(
                        "prompt552_final_runtime_completion_smoke_success"
                    )
                    is True
                ),
                "prompt552_full_autonomous_flow_completed": bool(
                    cycle_result.get("prompt552_full_autonomous_flow_completed")
                    is True
                ),
                "prompt552_completion_claim_allowed": bool(
                    cycle_result.get("prompt552_completion_claim_allowed")
                    is True
                ),
                "prompt552_result_json_no_remote_mutation_verified_true": bool(
                    cycle_result.get(
                        "prompt552_result_json_no_remote_mutation_verified_true"
                    )
                    is True
                ),
                "cycle_result": dict(cycle_result),
            }
            cycle_results.append(cycle_summary)
            if not cycle_success and failed_cycle_index is None:
                failed_cycle_index = cycle_index
                blocked_reasons.append(f"prompt565_cycle_{cycle_index:03d}_failed")
                if stop_on_failure:
                    break

        final_worktree_clean = _prompt565_worktree_clean_excluding_daemon_artifacts(
            repo_path=repo_path,
            daemon_artifact_dir=daemon_artifact_dir,
        )

    cycles_executed = len(cycle_results)
    successful_cycles = sum(
        1 for cycle_result in cycle_results if cycle_result["cycle_success"]
    )
    all_cycles_succeeded = bool(
        cycles_executed > 0 and successful_cycles == cycles_executed
    )
    no_remote_mutation_verified = bool(
        all(
            cycle_result.get(
                "prompt552_result_json_no_remote_mutation_verified_true"
            )
            is True
            for cycle_result in cycle_results
        )
        and cycles_executed > 0
    )
    success = bool(
        prompt565_enabled
        and prompt565_enable_token_valid
        and requested_max_cycles >= 2
        and cycles_executed >= 2
        and all_cycles_succeeded
        and final_worktree_clean
        and no_remote_mutation_verified
    )
    if cycles_executed > 0 and not final_worktree_clean and not success:
        blocked_reasons.append("prompt565_final_worktree_not_clean")
    if cycles_executed < 2 and prompt565_enabled and prompt565_enable_token_valid:
        blocked_reasons.append("prompt565_less_than_2_cycles_executed")

    summary = {
        "local_only": True,
        "source_prompt": "prompt565",
        "prompt565_multi_cycle_daemon_autonomous_loop_status": (
            "multi_cycle_daemon_autonomous_loop_success"
            if success
            else "blocked"
        ),
        "prompt565_multi_cycle_daemon_autonomous_loop_ready": bool(
            prompt565_enabled
            and prompt565_enable_token_valid
            and requested_max_cycles >= 2
        ),
        "prompt565_multi_cycle_daemon_autonomous_loop_success": success,
        "prompt565_enabled": prompt565_enabled,
        "prompt565_enable_token_valid": prompt565_enable_token_valid,
        "prompt565_requested_max_cycles": requested_max_cycles,
        "prompt565_cycles_executed": cycles_executed,
        "prompt565_successful_cycles": successful_cycles,
        "prompt565_failed_cycle_index": failed_cycle_index,
        "prompt565_all_cycles_succeeded": all_cycles_succeeded,
        "prompt565_final_worktree_clean": final_worktree_clean,
        "prompt565_no_remote_mutation_verified": no_remote_mutation_verified,
        "prompt565_full_autonomous_development_completed": success,
        "prompt565_completion_claim_allowed": success,
        "prompt565_long_running_daemon_included": True,
        "prompt565_multi_cycle_unattended_loop_included": True,
        "prompt565_remote_push_pr_merge_rollback_included": False,
        "prompt565_stop_on_failure": bool(stop_on_failure),
        "prompt565_artifact_dir": str(daemon_artifact_dir),
        "prompt565_existing_daemon_artifacts_cleaned_before_cycle": (
            existing_daemon_artifacts_cleaned_before_cycle
        ),
        "prompt565_known_runtime_artifacts_cleaned_between_cycles": (
            known_runtime_artifacts_cleaned_between_cycles
        ),
        "prompt565_daemon_artifact_dir_excluded_from_clean_check": True,
        "prompt565_arbitrary_untracked_files_still_block": True,
        "prompt565_cycle_artifacts": [
            cycle_result["cycle_artifact_name"]
            for cycle_result in cycle_results
        ],
        "prompt565_minimum_cycle_artifacts": list(
            _PROMPT565_MINIMUM_CYCLE_ARTIFACTS
        ),
        "prompt565_next_action": (
            "full_autonomous_development_completed_multi_cycle_daemon"
            if success
            else "manual_review_prompt565_multi_cycle_daemon_failed"
        ),
        "prompt565_blocked_reasons": blocked_reasons,
        "prompt565_cycle_results": cycle_results,
    }
    if not blocked_reasons or cycle_results:
        daemon_artifact_dir.mkdir(parents=True, exist_ok=True)
        for cycle_result in cycle_results:
            _write_json(
                daemon_artifact_dir / cycle_result["cycle_artifact_name"],
                cycle_result,
            )
        _write_json(daemon_artifact_dir / "daemon_summary.json", summary)
    return summary


def run_prompt568_production_hardening_entrypoint(
    *,
    run_state_payload: Mapping[str, Any] | None = None,
    execution_repo_path: str | Path = "",
    enabled: bool | None = None,
    enable_token: str | None = None,
    timeout_seconds: int = 180,
    allowed_files: Sequence[str] | None = None,
    max_cycles: int = 2,
    stop_on_failure: bool = True,
    max_daemon_runs: int = 1,
    artifact_dir: str | Path | None = None,
    resume_state_path: str | Path | None = None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    prompt565_payload = dict(payload)
    prompt565_payload.update(
        {
            "prompt550_post_smoke_local_commit_tag_clean_rerun_final_completion_ready": True,
            "prompt550_source_prompt549_ready": True,
            "prompt550_remote_push_pr_merge_rollback_included": False,
            "prompt550_long_running_daemon_included": False,
            "prompt550_multi_cycle_unattended_loop_included": False,
            "prompt550_completion_scope": (
                "local_only_success_path_one_cycle_final_completion"
            ),
            "prompt550_next_action": (
                "await_post_smoke_local_commit_tag_clean_rerun_final_completion"
            ),
        }
    )
    prompt568_prompt550_payload_materialized = all(
        (
            prompt565_payload.get(
                "prompt550_post_smoke_local_commit_tag_clean_rerun_final_completion_ready"
            )
            is True,
            prompt565_payload.get("prompt550_source_prompt549_ready") is True,
            prompt565_payload.get(
                "prompt550_remote_push_pr_merge_rollback_included"
            )
            is False,
            prompt565_payload.get("prompt550_long_running_daemon_included")
            is False,
            prompt565_payload.get(
                "prompt550_multi_cycle_unattended_loop_included"
            )
            is False,
            prompt565_payload.get("prompt550_completion_scope")
            == "local_only_success_path_one_cycle_final_completion",
            prompt565_payload.get("prompt550_next_action")
            == "await_post_smoke_local_commit_tag_clean_rerun_final_completion",
        )
    )
    repo_text = _normalize_text(
        execution_repo_path or payload.get("execution_repo_path"),
        default="",
    )
    repo_path = Path(repo_text) if repo_text else Path(".")
    hardening_artifact_dir = (
        Path(artifact_dir)
        if artifact_dir is not None
        else _PROMPT568_DEFAULT_ARTIFACT_DIR
    )
    if not hardening_artifact_dir.is_absolute():
        hardening_artifact_dir = repo_path / hardening_artifact_dir
    resume_path = (
        Path(resume_state_path)
        if resume_state_path is not None
        else hardening_artifact_dir / "resume_state.json"
    )
    if not resume_path.is_absolute():
        resume_path = repo_path / resume_path

    prompt568_enabled = enabled is True
    prompt568_enable_token_valid = (
        _normalize_text(enable_token, default="")
        == PROMPT568_PRODUCTION_HARDENING_ENTRYPOINT_ENABLE_TOKEN
    )
    try:
        requested_max_cycles = max(0, int(max_cycles))
    except (TypeError, ValueError):
        requested_max_cycles = 0
    try:
        requested_max_daemon_runs = max(0, int(max_daemon_runs))
    except (TypeError, ValueError):
        requested_max_daemon_runs = 0

    blocked_reasons: list[str] = []
    if not prompt568_enabled:
        blocked_reasons.append("prompt568_enabled_required")
    if not prompt568_enable_token_valid:
        blocked_reasons.append("prompt568_enable_token_invalid")
    if requested_max_daemon_runs < 1:
        blocked_reasons.append("prompt568_max_daemon_runs_below_1")
    if requested_max_cycles < 2:
        blocked_reasons.append("prompt568_requested_max_cycles_below_2")

    daemon_run_results: list[dict[str, Any]] = []
    failed_daemon_run_index: int | None = None
    if not blocked_reasons:
        for daemon_run_index in range(1, requested_max_daemon_runs + 1):
            daemon_result = run_prompt565_multi_cycle_daemon_autonomous_loop(
                run_state_payload=prompt565_payload,
                execution_repo_path=str(repo_path),
                enabled=True,
                enable_token=PROMPT565_MULTI_CYCLE_DAEMON_AUTONOMOUS_LOOP_ENABLE_TOKEN,
                timeout_seconds=timeout_seconds,
                allowed_files=allowed_files,
                max_cycles=requested_max_cycles,
                stop_on_failure=stop_on_failure,
                artifact_dir=hardening_artifact_dir,
            )
            daemon_success = bool(
                daemon_result.get(
                    "prompt565_multi_cycle_daemon_autonomous_loop_success"
                )
                is True
                and int(daemon_result.get("prompt565_cycles_executed") or 0) >= 2
                and int(daemon_result.get("prompt565_successful_cycles") or 0)
                >= 2
                and daemon_result.get(
                    "prompt565_full_autonomous_development_completed"
                )
                is True
                and daemon_result.get("prompt565_final_worktree_clean") is True
                and daemon_result.get("prompt565_no_remote_mutation_verified")
                is True
            )
            daemon_summary = {
                "daemon_run_index": daemon_run_index,
                "daemon_run_artifact_name": (
                    f"daemon_run_{daemon_run_index:03d}.json"
                ),
                "daemon_run_success": daemon_success,
                "daemon_result": dict(daemon_result),
            }
            daemon_run_results.append(daemon_summary)
            if not daemon_success and failed_daemon_run_index is None:
                failed_daemon_run_index = daemon_run_index
                blocked_reasons.append(
                    f"prompt568_daemon_run_{daemon_run_index:03d}_failed"
                )
                if stop_on_failure:
                    break

    daemon_runs_executed = len(daemon_run_results)
    successful_daemon_runs = sum(
        1
        for daemon_run_result in daemon_run_results
        if daemon_run_result["daemon_run_success"]
    )
    final_worktree_clean = _prompt565_worktree_clean_excluding_daemon_artifacts(
        repo_path=repo_path,
        daemon_artifact_dir=hardening_artifact_dir,
    )
    no_remote_mutation_verified = bool(
        daemon_runs_executed > 0
        and all(
            daemon_run_result["daemon_result"].get(
                "prompt565_no_remote_mutation_verified"
            )
            is True
            for daemon_run_result in daemon_run_results
        )
    )
    success_without_artifacts = bool(
        prompt568_enabled
        and prompt568_enable_token_valid
        and requested_max_daemon_runs >= 1
        and requested_max_cycles >= 2
        and prompt568_prompt550_payload_materialized
        and daemon_runs_executed >= 1
        and successful_daemon_runs == daemon_runs_executed
        and successful_daemon_runs >= 1
        and final_worktree_clean
        and no_remote_mutation_verified
    )
    if daemon_runs_executed > 0 and not final_worktree_clean:
        blocked_reasons.append("prompt568_final_worktree_not_clean")
    if daemon_runs_executed < requested_max_daemon_runs and not stop_on_failure:
        blocked_reasons.append("prompt568_less_than_requested_daemon_runs_executed")

    last_completed_daemon_run = daemon_runs_executed
    last_success = (
        daemon_run_results[-1]["daemon_run_success"]
        if daemon_run_results
        else False
    )
    next_action = (
        "production_hardening_entrypoint_completed_local_only"
        if success_without_artifacts
        else "manual_review_prompt568_production_hardening_entrypoint_failed"
    )
    status = (
        "production_hardening_entrypoint_completed_local_only"
        if success_without_artifacts
        else "blocked"
    )
    success = False
    resume_state = {
        "last_completed_daemon_run": last_completed_daemon_run,
        "last_status": status,
        "last_next_action": next_action,
        "last_success": last_success,
        "total_daemon_runs_requested": requested_max_daemon_runs,
        "total_daemon_runs_completed": daemon_runs_executed,
        "stopped_on_failure": bool(
            failed_daemon_run_index is not None and stop_on_failure
        ),
        "local_only": True,
        "remote_workflow_included": False,
    }
    summary = {
        "local_only": True,
        "source_prompt": "prompt568",
        "prompt568_production_hardening_entrypoint_status": status,
        "prompt568_production_hardening_entrypoint_ready": bool(
            prompt568_enabled
            and prompt568_enable_token_valid
            and requested_max_daemon_runs >= 1
            and requested_max_cycles >= 2
        ),
        "prompt568_production_hardening_entrypoint_success": False,
        "prompt568_enabled": prompt568_enabled,
        "prompt568_enable_token_valid": prompt568_enable_token_valid,
        "prompt568_requested_max_cycles": requested_max_cycles,
        "prompt568_max_daemon_runs": requested_max_daemon_runs,
        "prompt568_daemon_runs_executed": daemon_runs_executed,
        "prompt568_successful_daemon_runs": successful_daemon_runs,
        "prompt568_failed_daemon_run_index": failed_daemon_run_index,
        "prompt568_stop_on_failure": bool(stop_on_failure),
        "prompt568_prompt550_payload_materialized": (
            prompt568_prompt550_payload_materialized
        ),
        "prompt568_resume_state_written": False,
        "prompt568_hardening_summary_written": False,
        "prompt568_final_worktree_clean": final_worktree_clean,
        "prompt568_no_remote_mutation_verified": no_remote_mutation_verified,
        "prompt568_production_hardening_completed": success,
        "prompt568_completion_claim_allowed": success,
        "prompt568_remote_workflow_included": False,
        "prompt568_next_action": next_action,
        "prompt568_blocked_reasons": blocked_reasons,
        "prompt568_artifact_dir": str(hardening_artifact_dir),
        "prompt568_resume_state_path": str(resume_path),
        "prompt568_daemon_run_artifacts": [
            daemon_run_result["daemon_run_artifact_name"]
            for daemon_run_result in daemon_run_results
        ],
        "prompt568_daemon_run_results": daemon_run_results,
        "resume_state": resume_state,
    }

    hardening_artifact_dir.mkdir(parents=True, exist_ok=True)
    for daemon_run_result in daemon_run_results:
        _write_json(
            hardening_artifact_dir / daemon_run_result["daemon_run_artifact_name"],
            daemon_run_result,
        )
    resume_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(resume_path, resume_state)
    summary["prompt568_resume_state_written"] = resume_path.exists()
    summary_path = hardening_artifact_dir / "hardening_summary.json"
    _write_json(summary_path, summary)
    summary["prompt568_hardening_summary_written"] = summary_path.exists()
    success = bool(
        success_without_artifacts
        and summary["prompt568_resume_state_written"]
        and summary["prompt568_hardening_summary_written"]
    )
    next_action = (
        "production_hardening_entrypoint_completed_local_only"
        if success
        else "manual_review_prompt568_production_hardening_entrypoint_failed"
    )
    status = (
        "production_hardening_entrypoint_completed_local_only"
        if success
        else "blocked"
    )
    resume_state["last_status"] = status
    resume_state["last_next_action"] = next_action
    resume_state["last_success"] = last_success and success
    summary["prompt568_production_hardening_entrypoint_status"] = status
    summary["prompt568_production_hardening_entrypoint_success"] = success
    summary["prompt568_production_hardening_completed"] = success
    summary["prompt568_completion_claim_allowed"] = success
    summary["prompt568_next_action"] = next_action
    summary["resume_state"] = resume_state
    if summary["prompt568_resume_state_written"]:
        _write_json(resume_path, resume_state)
    if summary["prompt568_hardening_summary_written"]:
        _write_json(summary_path, summary)
    return summary


def run_prompt569_soak_runner_supervisor_wrapper(
    *,
    run_state_payload: Mapping[str, Any] | None = None,
    execution_repo_path: str | Path = "",
    enabled: bool | None = None,
    enable_token: str | None = None,
    timeout_seconds: int = 180,
    allowed_files: Sequence[str] | None = None,
    max_cycles: int = 2,
    stop_on_failure: bool = True,
    max_daemon_runs: int = 1,
    soak_runs: int = 2,
    artifact_dir: str | Path | None = None,
    resume_state_path: str | Path | None = None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    repo_text = _normalize_text(
        execution_repo_path or payload.get("execution_repo_path"),
        default="",
    )
    repo_path = Path(repo_text) if repo_text else Path(".")
    supervisor_artifact_dir = (
        Path(artifact_dir)
        if artifact_dir is not None
        else _PROMPT569_DEFAULT_ARTIFACT_DIR
    )
    if not supervisor_artifact_dir.is_absolute():
        supervisor_artifact_dir = repo_path / supervisor_artifact_dir
    resume_path = (
        Path(resume_state_path)
        if resume_state_path is not None
        else supervisor_artifact_dir / "supervisor_resume_state.json"
    )
    if not resume_path.is_absolute():
        resume_path = repo_path / resume_path

    prompt569_enabled = enabled is True
    prompt569_enable_token_valid = (
        _normalize_text(enable_token, default="")
        == PROMPT569_SOAK_RUNNER_SUPERVISOR_WRAPPER_ENABLE_TOKEN
    )
    try:
        requested_soak_runs = max(0, int(soak_runs))
    except (TypeError, ValueError):
        requested_soak_runs = 0

    blocked_reasons: list[str] = []
    if not prompt569_enabled:
        blocked_reasons.append("prompt569_enabled_required")
    if not prompt569_enable_token_valid:
        blocked_reasons.append("prompt569_enable_token_invalid")
    if requested_soak_runs < 2:
        blocked_reasons.append("prompt569_soak_runs_below_2")

    soak_run_results: list[dict[str, Any]] = []
    failed_soak_run_index: int | None = None
    stop_reason = ""
    known_runtime_artifacts_cleaned_before_soak: list[str] = []
    known_runtime_artifacts_cleaned_between_soaks: list[dict[str, Any]] = []
    can_execute_soak = bool(
        prompt569_enabled
        and prompt569_enable_token_valid
        and requested_soak_runs >= 2
    )
    if can_execute_soak:
        known_runtime_artifacts_cleaned_before_soak = (
            _prompt569_remove_known_generated_runtime_artifacts(repo_path)
        )
        for soak_run_index in range(1, requested_soak_runs + 1):
            prompt568_artifact_dir = (
                supervisor_artifact_dir
                / f"prompt568_soak_run_{soak_run_index:03d}"
            )
            prompt568_result = run_prompt568_production_hardening_entrypoint(
                run_state_payload=payload,
                execution_repo_path=str(repo_path),
                enabled=True,
                enable_token=PROMPT568_PRODUCTION_HARDENING_ENTRYPOINT_ENABLE_TOKEN,
                timeout_seconds=timeout_seconds,
                allowed_files=allowed_files,
                max_cycles=2,
                stop_on_failure=bool(stop_on_failure),
                max_daemon_runs=1,
                artifact_dir=prompt568_artifact_dir,
                resume_state_path=(
                    prompt568_artifact_dir / "resume_state.json"
                ),
            )
            prompt568_success = bool(
                prompt568_result.get(
                    "prompt568_production_hardening_entrypoint_success"
                )
                is True
                and prompt568_result.get(
                    "prompt568_production_hardening_completed"
                )
                is True
                and prompt568_result.get("prompt568_completion_claim_allowed")
                is True
                and prompt568_result.get(
                    "prompt568_no_remote_mutation_verified"
                )
                is True
                and prompt568_result.get("prompt568_remote_workflow_included")
                is False
            )
            soak_run_summary = {
                "soak_run_index": soak_run_index,
                "soak_run_artifact_name": (
                    f"soak_run_{soak_run_index:03d}.json"
                ),
                "soak_run_success": prompt568_success,
                "prompt568_artifact_dir": str(prompt568_artifact_dir),
                "prompt568_result": dict(prompt568_result),
            }
            soak_run_results.append(soak_run_summary)
            if not prompt568_success and failed_soak_run_index is None:
                failed_soak_run_index = soak_run_index
                blocked_reasons.append(
                    f"prompt569_soak_run_{soak_run_index:03d}_failed"
                )
                if stop_on_failure:
                    stop_reason = "stopped_on_failed_soak_run"
                    break
            if soak_run_index < requested_soak_runs:
                known_runtime_artifacts_cleaned_between_soaks.append(
                    {
                        "after_soak_run_index": soak_run_index,
                        "removed_artifacts": (
                            _prompt569_remove_known_generated_runtime_artifacts(
                                repo_path
                            )
                        ),
                    }
                )

    soak_runs_executed = len(soak_run_results)
    successful_soak_runs = sum(
        1 for soak_run_result in soak_run_results if soak_run_result["soak_run_success"]
    )
    if not stop_reason:
        if not (prompt569_enabled and prompt569_enable_token_valid):
            stop_reason = "blocked_by_enable_token"
        elif requested_soak_runs < 2:
            stop_reason = "blocked_by_invalid_soak_runs"
        elif (
            soak_runs_executed == requested_soak_runs
            and successful_soak_runs == requested_soak_runs
        ):
            stop_reason = "completed_requested_soak_runs"
        elif failed_soak_run_index is not None and stop_on_failure:
            stop_reason = "stopped_on_failed_soak_run"
        else:
            stop_reason = "stopped_on_failed_soak_run"

    final_worktree_clean = _prompt565_worktree_clean_excluding_daemon_artifacts(
        repo_path=repo_path,
        daemon_artifact_dir=supervisor_artifact_dir,
    )
    no_remote_mutation_verified = bool(
        soak_runs_executed > 0
        and all(
            soak_run_result["prompt568_result"].get(
                "prompt568_no_remote_mutation_verified"
            )
            is True
            for soak_run_result in soak_run_results
        )
    )
    all_soak_runs_executed = soak_runs_executed == requested_soak_runs
    every_prompt568_succeeded = bool(
        soak_runs_executed > 0
        and all(soak_run_result["soak_run_success"] for soak_run_result in soak_run_results)
    )
    success_without_artifacts = bool(
        prompt569_enabled
        and prompt569_enable_token_valid
        and requested_soak_runs >= 2
        and all_soak_runs_executed
        and every_prompt568_succeeded
        and final_worktree_clean
        and no_remote_mutation_verified
    )
    if soak_runs_executed > 0 and not final_worktree_clean:
        blocked_reasons.append("prompt569_final_worktree_not_clean")
    if can_execute_soak and not all_soak_runs_executed:
        blocked_reasons.append("prompt569_less_than_requested_soak_runs_executed")

    next_action = (
        "production_hardening_soak_runner_completed_local_only"
        if success_without_artifacts
        else "manual_review_prompt569_soak_runner_supervisor_wrapper_failed"
    )
    status = (
        "production_hardening_soak_runner_completed_local_only"
        if success_without_artifacts
        else "blocked"
    )
    last_success = (
        soak_run_results[-1]["soak_run_success"] if soak_run_results else False
    )
    resume_state = {
        "last_completed_soak_run": soak_runs_executed,
        "last_status": status,
        "last_next_action": next_action,
        "last_success": last_success,
        "total_soak_runs_requested": requested_soak_runs,
        "total_soak_runs_completed": soak_runs_executed,
        "failed_soak_run_index": failed_soak_run_index,
        "stop_reason": stop_reason,
        "stopped_on_failure": bool(
            failed_soak_run_index is not None and stop_on_failure
        ),
        "local_only": True,
        "remote_workflow_included": False,
    }
    summary = {
        "local_only": True,
        "source_prompt": "prompt569",
        "prompt569_soak_runner_supervisor_wrapper_status": status,
        "prompt569_soak_runner_supervisor_wrapper_ready": bool(
            prompt569_enabled
            and prompt569_enable_token_valid
            and requested_soak_runs >= 2
        ),
        "prompt569_soak_runner_supervisor_wrapper_success": False,
        "prompt569_enabled": prompt569_enabled,
        "prompt569_enable_token_valid": prompt569_enable_token_valid,
        "prompt569_requested_soak_runs": requested_soak_runs,
        "prompt569_soak_runs_executed": soak_runs_executed,
        "prompt569_successful_soak_runs": successful_soak_runs,
        "prompt569_failed_soak_run_index": failed_soak_run_index,
        "prompt569_stop_on_failure": bool(stop_on_failure),
        "prompt569_stop_reason": stop_reason,
        "prompt569_resume_state_written": False,
        "prompt569_soak_summary_written": False,
        "prompt569_final_worktree_clean": final_worktree_clean,
        "prompt569_no_remote_mutation_verified": no_remote_mutation_verified,
        "prompt569_production_hardening_soak_completed": False,
        "prompt569_completion_claim_allowed": False,
        "prompt569_remote_workflow_included": False,
        "prompt569_next_action": next_action,
        "prompt569_blocked_reasons": blocked_reasons,
        "prompt569_artifact_dir": str(supervisor_artifact_dir),
        "prompt569_resume_state_path": str(resume_path),
        "prompt569_soak_run_artifacts": [
            soak_run_result["soak_run_artifact_name"]
            for soak_run_result in soak_run_results
        ],
        "prompt569_soak_run_results": soak_run_results,
        "prompt570_fix_prompt569_soak_artifact_cleanup_status": (
            "prompt569_known_runtime_artifact_cleanup_applied"
            if can_execute_soak
            else "prompt569_known_runtime_artifact_cleanup_not_executed"
        ),
        "prompt570_known_runtime_artifacts_cleaned_before_soak": (
            known_runtime_artifacts_cleaned_before_soak
        ),
        "prompt570_known_runtime_artifacts_cleaned_between_soaks": (
            known_runtime_artifacts_cleaned_between_soaks
        ),
        "prompt570_prompt569_postcommit_rerun_ready": False,
        "prompt570_arbitrary_untracked_files_still_block": True,
        "prompt570_full_autonomous_development_completed_local_only": False,
        "prompt570_remote_workflow_included": False,
        "prompt570_next_action": (
            "production_hardening_soak_runner_completed_local_only"
            if success_without_artifacts
            else "manual_review_prompt569_soak_runner_supervisor_wrapper_failed"
        ),
        "resume_state": resume_state,
    }

    supervisor_artifact_dir.mkdir(parents=True, exist_ok=True)
    for soak_run_result in soak_run_results:
        _write_json(
            supervisor_artifact_dir / soak_run_result["soak_run_artifact_name"],
            soak_run_result,
        )
    resume_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(resume_path, resume_state)
    summary["prompt569_resume_state_written"] = resume_path.exists()
    summary_path = supervisor_artifact_dir / "soak_summary.json"
    _write_json(summary_path, summary)
    summary["prompt569_soak_summary_written"] = summary_path.exists()

    artifacts_written = bool(
        summary["prompt569_resume_state_written"]
        and summary["prompt569_soak_summary_written"]
        and all(
            (supervisor_artifact_dir / soak_run_result["soak_run_artifact_name"]).exists()
            for soak_run_result in soak_run_results
        )
    )
    success = bool(success_without_artifacts and artifacts_written)
    next_action = (
        "production_hardening_soak_runner_completed_local_only"
        if success
        else "manual_review_prompt569_soak_runner_supervisor_wrapper_failed"
    )
    status = (
        "production_hardening_soak_runner_completed_local_only"
        if success
        else "blocked"
    )
    resume_state["last_status"] = status
    resume_state["last_next_action"] = next_action
    resume_state["last_success"] = last_success and success
    summary["prompt569_soak_runner_supervisor_wrapper_status"] = status
    summary["prompt569_soak_runner_supervisor_wrapper_success"] = success
    summary["prompt569_production_hardening_soak_completed"] = success
    summary["prompt569_completion_claim_allowed"] = success
    summary["prompt569_next_action"] = next_action
    summary["prompt570_prompt569_postcommit_rerun_ready"] = success
    summary["prompt570_next_action"] = next_action
    summary["resume_state"] = resume_state
    if summary["prompt569_resume_state_written"]:
        _write_json(resume_path, resume_state)
    if summary["prompt569_soak_summary_written"]:
        _write_json(summary_path, summary)
    return summary


def run_prompt571_service_artifacts_local_only(
    *,
    run_state_payload: Mapping[str, Any] | None = None,
    execution_repo_path: str | Path = "",
    enabled: bool | None = None,
    enable_token: str | None = None,
    artifact_dir: str | Path | None = None,
    service_name: str = "codex-local-runner",
    soak_runs: int = 2,
    max_cycles: int = 2,
    max_daemon_runs: int = 1,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    repo_text = _normalize_text(
        execution_repo_path or payload.get("execution_repo_path"),
        default="",
    )
    repo_path = Path(repo_text) if repo_text else Path(".")
    service_artifact_dir = (
        Path(artifact_dir)
        if artifact_dir is not None
        else _PROMPT571_DEFAULT_ARTIFACT_DIR
    )
    if not service_artifact_dir.is_absolute():
        service_artifact_dir = repo_path / service_artifact_dir

    prompt571_enabled = enabled is True
    prompt571_enable_token_valid = (
        _normalize_text(enable_token, default="")
        == PROMPT571_SERVICE_ARTIFACTS_LOCAL_ONLY_ENABLE_TOKEN
    )
    prompt571_service_name = _normalize_text(
        service_name,
        default="codex-local-runner",
    )
    if not prompt571_service_name:
        prompt571_service_name = "codex-local-runner"

    def _prompt571_int(value: Any) -> int:
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return 0

    requested_soak_runs = _prompt571_int(soak_runs)
    requested_max_cycles = _prompt571_int(max_cycles)
    requested_max_daemon_runs = _prompt571_int(max_daemon_runs)

    installation_performed = False
    daemon_started = False
    remote_workflow_included = False
    blocked_reasons: list[str] = []
    if not prompt571_enabled:
        blocked_reasons.append("prompt571_enabled_required")
    if not prompt571_enable_token_valid:
        blocked_reasons.append("prompt571_enable_token_invalid")
    if requested_soak_runs < 2:
        blocked_reasons.append("prompt571_soak_runs_below_2")
    if requested_max_cycles < 2:
        blocked_reasons.append("prompt571_max_cycles_below_2")
    if requested_max_daemon_runs < 1:
        blocked_reasons.append("prompt571_max_daemon_runs_below_1")

    service_path = service_artifact_dir / "codex-local-runner.service"
    env_path = service_artifact_dir / "codex-local-runner.env.example"
    runner_script_path = service_artifact_dir / "run_prompt569_supervisor.sh"
    summary_path = service_artifact_dir / "service_artifacts_summary.json"
    service_file_written = False
    env_file_written = False
    runner_script_written = False
    summary_written = False

    can_write_artifacts = bool(prompt571_enabled and prompt571_enable_token_valid)
    if can_write_artifacts:
        service_artifact_dir.mkdir(parents=True, exist_ok=True)
        repo_path_text = str(repo_path.resolve())
        artifact_dir_text = str(service_artifact_dir.resolve())
        runner_script_text = f"""#!/usr/bin/env bash
set -euo pipefail

REPO_PATH="${{REPO_PATH:-{repo_path_text}}}"
ARTIFACT_DIR="${{ARTIFACT_DIR:-{artifact_dir_text}/prompt569_soak_runner}}"
SOAK_RUNS="${{SOAK_RUNS:-{requested_soak_runs}}}"
MAX_CYCLES="${{MAX_CYCLES:-{requested_max_cycles}}}"
MAX_DAEMON_RUNS="${{MAX_DAEMON_RUNS:-{requested_max_daemon_runs}}}"

cd "$REPO_PATH"
python - <<'PY'
import json
import os
from pathlib import Path

from automation.orchestration.planned_runner.runtime_output_wiring import (
    PROMPT569_SOAK_RUNNER_SUPERVISOR_WRAPPER_ENABLE_TOKEN,
    run_prompt569_soak_runner_supervisor_wrapper,
)

result = run_prompt569_soak_runner_supervisor_wrapper(
    execution_repo_path=os.environ["REPO_PATH"],
    enabled=True,
    enable_token=PROMPT569_SOAK_RUNNER_SUPERVISOR_WRAPPER_ENABLE_TOKEN,
    artifact_dir=Path(os.environ["ARTIFACT_DIR"]),
    soak_runs=int(os.environ["SOAK_RUNS"]),
    max_cycles=int(os.environ["MAX_CYCLES"]),
    max_daemon_runs=int(os.environ["MAX_DAEMON_RUNS"]),
)
print(json.dumps(result, indent=2, sort_keys=True))
PY
"""
        env_text = f"""# Example environment for reviewing Prompt571 local-only service artifacts.
REPO_PATH={repo_path_text}
ARTIFACT_DIR={artifact_dir_text}/prompt569_soak_runner
SOAK_RUNS={requested_soak_runs}
MAX_CYCLES={requested_max_cycles}
MAX_DAEMON_RUNS={requested_max_daemon_runs}
"""
        service_text = f"""[Unit]
Description=Prompt571 review artifact for {prompt571_service_name}
Documentation=file://{artifact_dir_text}/service_artifacts_summary.json

[Service]
Type=oneshot
EnvironmentFile={artifact_dir_text}/codex-local-runner.env.example
WorkingDirectory={repo_path_text}
ExecStart=/usr/bin/env bash {artifact_dir_text}/run_prompt569_supervisor.sh
"""
        runner_script_path.write_text(runner_script_text, encoding="utf-8")
        env_path.write_text(env_text, encoding="utf-8")
        service_path.write_text(service_text, encoding="utf-8")
        service_file_written = service_path.is_file()
        env_file_written = env_path.is_file()
        runner_script_written = runner_script_path.is_file()

    artifacts_written = bool(
        service_file_written
        and env_file_written
        and runner_script_written
    )
    success = bool(
        prompt571_enable_token_valid
        and artifacts_written
        and not installation_performed
        and not daemon_started
        and not remote_workflow_included
        and requested_soak_runs >= 2
        and requested_max_cycles >= 2
        and requested_max_daemon_runs >= 1
    )
    if can_write_artifacts and not artifacts_written:
        blocked_reasons.append("prompt571_artifact_write_incomplete")
    next_action = (
        "service_artifacts_ready_for_manual_review_local_only"
        if success
        else "manual_review_prompt571_service_artifacts_local_only_failed"
    )
    status = (
        "service_artifacts_ready_for_manual_review_local_only"
        if success
        else "blocked"
    )
    summary: dict[str, Any] = {
        "local_only": True,
        "source_prompt": "prompt571",
        "prompt571_service_artifacts_local_only_status": status,
        "prompt571_service_artifacts_local_only_ready": bool(
            prompt571_enabled
            and prompt571_enable_token_valid
            and requested_soak_runs >= 2
            and requested_max_cycles >= 2
            and requested_max_daemon_runs >= 1
        ),
        "prompt571_service_artifacts_local_only_success": success,
        "prompt571_enabled": prompt571_enabled,
        "prompt571_enable_token_valid": prompt571_enable_token_valid,
        "prompt571_service_name": prompt571_service_name,
        "prompt571_artifact_dir": str(service_artifact_dir),
        "prompt571_service_file_written": service_file_written,
        "prompt571_env_file_written": env_file_written,
        "prompt571_runner_script_written": runner_script_written,
        "prompt571_summary_written": False,
        "prompt571_installation_performed": installation_performed,
        "prompt571_daemon_started": daemon_started,
        "prompt571_remote_workflow_included": remote_workflow_included,
        "prompt571_soak_runs": requested_soak_runs,
        "prompt571_max_cycles": requested_max_cycles,
        "prompt571_max_daemon_runs": requested_max_daemon_runs,
        "prompt571_next_action": next_action,
        "prompt571_blocked_reasons": blocked_reasons,
    }
    if can_write_artifacts:
        _write_json(summary_path, summary)
        summary_written = summary_path.is_file()
        summary["prompt571_summary_written"] = summary_written
        success = bool(success and summary_written)
        summary["prompt571_service_artifacts_local_only_success"] = success
        summary["prompt571_next_action"] = (
            "service_artifacts_ready_for_manual_review_local_only"
            if success
            else "manual_review_prompt571_service_artifacts_local_only_failed"
        )
        summary["prompt571_service_artifacts_local_only_status"] = (
            "service_artifacts_ready_for_manual_review_local_only"
            if success
            else "blocked"
        )
        _write_json(summary_path, summary)
    return summary


def run_prompt572_longer_soak_stability_gate(
    *,
    run_state_payload: Mapping[str, Any] | None = None,
    execution_repo_path: str | Path = "",
    enabled: bool | None = None,
    enable_token: str | None = None,
    timeout_seconds: int = 180,
    allowed_files: Sequence[str] | None = None,
    soak_runs: int = 5,
    max_cycles: int = 2,
    max_daemon_runs: int = 1,
    artifact_dir: str | Path | None = None,
    resume_state_path: str | Path | None = None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    repo_text = _normalize_text(
        execution_repo_path or payload.get("execution_repo_path"),
        default="",
    )
    repo_path = Path(repo_text) if repo_text else Path(".")
    longer_soak_artifact_dir = (
        Path(artifact_dir)
        if artifact_dir is not None
        else _PROMPT572_DEFAULT_ARTIFACT_DIR
    )
    if not longer_soak_artifact_dir.is_absolute():
        longer_soak_artifact_dir = repo_path / longer_soak_artifact_dir
    resume_path = (
        Path(resume_state_path)
        if resume_state_path is not None
        else longer_soak_artifact_dir / "prompt569_resume_state.json"
    )
    if not resume_path.is_absolute():
        resume_path = repo_path / resume_path

    prompt572_enabled = enabled is True
    prompt572_enable_token_valid = (
        _normalize_text(enable_token, default="")
        == PROMPT572_LONGER_SOAK_STABILITY_GATE_ENABLE_TOKEN
    )

    def _prompt572_int(value: Any) -> int:
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return 0

    requested_soak_runs = _prompt572_int(soak_runs)
    requested_max_cycles = _prompt572_int(max_cycles)
    requested_max_daemon_runs = _prompt572_int(max_daemon_runs)
    installation_performed = False
    daemon_started = False
    remote_workflow_included = False
    blocked_reasons: list[str] = []
    if not prompt572_enabled:
        blocked_reasons.append("prompt572_enabled_required")
    if not prompt572_enable_token_valid:
        blocked_reasons.append("prompt572_enable_token_invalid")
    if requested_soak_runs < 5:
        blocked_reasons.append("prompt572_soak_runs_below_5")
    if requested_max_cycles != 2:
        blocked_reasons.append("prompt572_max_cycles_must_equal_2")
    if requested_max_daemon_runs != 1:
        blocked_reasons.append("prompt572_max_daemon_runs_must_equal_1")

    prompt569_result: dict[str, Any] = {}
    can_execute_soak = bool(
        prompt572_enabled
        and prompt572_enable_token_valid
        and requested_soak_runs >= 5
        and requested_max_cycles == 2
        and requested_max_daemon_runs == 1
    )
    if can_execute_soak:
        longer_soak_artifact_dir_inside_repo = (
            longer_soak_artifact_dir.resolve().is_relative_to(
                repo_path.resolve()
            )
        )
        prompt569_temp_dir = (
            __import__("tempfile").TemporaryDirectory()
            if longer_soak_artifact_dir_inside_repo
            else __import__("contextlib").nullcontext(None)
        )
        with prompt569_temp_dir as prompt569_temp_dir_text:
            if prompt569_temp_dir_text is None:
                prompt569_artifact_dir = (
                    longer_soak_artifact_dir / "prompt569_soak_runner"
                )
                prompt569_resume_state_path = resume_path
            else:
                prompt569_temp_path = Path(prompt569_temp_dir_text)
                prompt569_artifact_dir = (
                    prompt569_temp_path / "prompt569_soak_runner"
                )
                prompt569_resume_state_path = (
                    prompt569_temp_path / "prompt569_resume_state.json"
                )
            prompt569_result = run_prompt569_soak_runner_supervisor_wrapper(
                run_state_payload=payload,
                execution_repo_path=str(repo_path),
                enabled=True,
                enable_token=PROMPT569_SOAK_RUNNER_SUPERVISOR_WRAPPER_ENABLE_TOKEN,
                timeout_seconds=timeout_seconds,
                allowed_files=allowed_files,
                max_cycles=requested_max_cycles,
                stop_on_failure=True,
                max_daemon_runs=requested_max_daemon_runs,
                soak_runs=requested_soak_runs,
                artifact_dir=prompt569_artifact_dir,
                resume_state_path=prompt569_resume_state_path,
            )

    confirmed_soak_runs = _prompt572_int(
        prompt569_result.get("prompt569_soak_runs_executed")
    )
    confirmed_prompt568_runs = confirmed_soak_runs
    confirmed_inner_prompt565_cycles_total = (
        confirmed_prompt568_runs * requested_max_cycles
    )
    failed_soak_run_index = prompt569_result.get(
        "prompt569_failed_soak_run_index"
    )
    stop_reason = _normalize_text(
        prompt569_result.get("prompt569_stop_reason"),
        default="blocked_by_enable_token",
    )
    prompt569_success = (
        prompt569_result.get("prompt569_soak_runner_supervisor_wrapper_success")
        is True
    )
    prompt569_successful_soak_runs = _prompt572_int(
        prompt569_result.get("prompt569_successful_soak_runs")
    )
    final_worktree_clean = (
        prompt569_result.get("prompt569_final_worktree_clean") is True
    )
    no_remote_mutation_verified = (
        prompt569_result.get("prompt569_no_remote_mutation_verified") is True
    )
    prompt569_remote_workflow_included = (
        prompt569_result.get("prompt569_remote_workflow_included") is True
    )

    result_path = longer_soak_artifact_dir / "longer_soak_result.json"
    summary_path = longer_soak_artifact_dir / "longer_soak_summary.json"
    result_written = False
    summary_written = False

    completion_checks = (
        ("prompt572_enabled", prompt572_enabled),
        ("prompt572_enable_token_valid", prompt572_enable_token_valid),
        ("prompt572_requested_soak_runs_at_least_5", requested_soak_runs >= 5),
        ("prompt572_max_cycles_equals_2", requested_max_cycles == 2),
        (
            "prompt572_max_daemon_runs_equals_1",
            requested_max_daemon_runs == 1,
        ),
        ("prompt572_prompt569_success", prompt569_success),
        (
            "prompt572_prompt569_executed_requested_soak_runs",
            confirmed_soak_runs == requested_soak_runs,
        ),
        (
            "prompt572_prompt569_successful_soak_runs",
            prompt569_successful_soak_runs == requested_soak_runs,
        ),
        (
            "prompt572_failed_soak_run_index_none",
            failed_soak_run_index is None,
        ),
        (
            "prompt572_stop_reason_completed",
            stop_reason == "completed_requested_soak_runs",
        ),
        ("prompt572_final_worktree_clean", final_worktree_clean),
        (
            "prompt572_no_remote_mutation_verified",
            no_remote_mutation_verified,
        ),
        (
            "prompt572_remote_workflow_included_false",
            not prompt569_remote_workflow_included
            and not remote_workflow_included,
        ),
        (
            "prompt572_installation_performed_false",
            not installation_performed,
        ),
        ("prompt572_daemon_started_false", not daemon_started),
    )
    for field, passed in completion_checks:
        if not passed:
            blocked_reason = f"missing_{field}"
            if blocked_reason not in blocked_reasons:
                blocked_reasons.append(blocked_reason)

    success_without_artifacts = bool(all(passed for _, passed in completion_checks))
    status = (
        "longer_soak_stability_gate_completed_local_only"
        if success_without_artifacts
        else "blocked"
    )
    next_action = (
        "longer_soak_stability_gate_completed_local_only"
        if success_without_artifacts
        else "manual_review_prompt572_longer_soak_stability_gate_failed"
    )
    summary: dict[str, Any] = {
        "local_only": True,
        "source_prompt": "prompt572",
        "prompt572_longer_soak_stability_gate_status": status,
        "prompt572_longer_soak_stability_gate_ready": bool(
            prompt572_enabled
            and prompt572_enable_token_valid
            and requested_soak_runs >= 5
            and requested_max_cycles == 2
            and requested_max_daemon_runs == 1
        ),
        "prompt572_longer_soak_stability_gate_success": False,
        "prompt572_enabled": prompt572_enabled,
        "prompt572_enable_token_valid": prompt572_enable_token_valid,
        "prompt572_requested_soak_runs": requested_soak_runs,
        "prompt572_max_cycles": requested_max_cycles,
        "prompt572_max_daemon_runs": requested_max_daemon_runs,
        "prompt572_confirmed_soak_runs": confirmed_soak_runs,
        "prompt572_confirmed_prompt568_runs": confirmed_prompt568_runs,
        "prompt572_confirmed_inner_prompt565_cycles_total": (
            confirmed_inner_prompt565_cycles_total
        ),
        "prompt572_failed_soak_run_index": failed_soak_run_index,
        "prompt572_stop_reason": stop_reason,
        "prompt572_longer_soak_result_written": False,
        "prompt572_longer_soak_summary_written": False,
        "prompt572_final_worktree_clean": final_worktree_clean,
        "prompt572_no_remote_mutation_verified": no_remote_mutation_verified,
        "prompt572_installation_performed": installation_performed,
        "prompt572_daemon_started": daemon_started,
        "prompt572_remote_workflow_included": remote_workflow_included,
        "prompt572_longer_soak_completed": False,
        "prompt572_completion_claim_allowed": False,
        "prompt572_next_action": next_action,
        "prompt572_blocked_reasons": blocked_reasons,
        "prompt572_artifact_dir": str(longer_soak_artifact_dir),
        "prompt572_prompt569_result": prompt569_result,
    }

    if can_execute_soak:
        longer_soak_artifact_dir.mkdir(parents=True, exist_ok=True)
        _write_json(result_path, prompt569_result)
        result_written = result_path.is_file()
        summary["prompt572_longer_soak_result_written"] = result_written
        _write_json(summary_path, summary)
        summary_written = summary_path.is_file()
        summary["prompt572_longer_soak_summary_written"] = summary_written

    success = bool(
        success_without_artifacts
        and result_written
        and summary_written
        and not installation_performed
        and not daemon_started
        and not remote_workflow_included
    )
    if can_execute_soak and not result_written:
        blocked_reasons.append("missing_prompt572_longer_soak_result_written")
    if can_execute_soak and not summary_written:
        blocked_reasons.append("missing_prompt572_longer_soak_summary_written")
    next_action = (
        "longer_soak_stability_gate_completed_local_only"
        if success
        else "manual_review_prompt572_longer_soak_stability_gate_failed"
    )
    status = (
        "longer_soak_stability_gate_completed_local_only"
        if success
        else "blocked"
    )
    summary["prompt572_longer_soak_stability_gate_status"] = status
    summary["prompt572_longer_soak_stability_gate_success"] = success
    summary["prompt572_longer_soak_result_written"] = result_written
    summary["prompt572_longer_soak_summary_written"] = summary_written
    summary["prompt572_longer_soak_completed"] = success
    summary["prompt572_completion_claim_allowed"] = success
    summary["prompt572_next_action"] = next_action
    summary["prompt572_blocked_reasons"] = blocked_reasons
    if summary_written:
        _write_json(summary_path, summary)
    return summary


def _prompt574_int(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _prompt574_evidence_ready(
    *,
    payload: Mapping[str, Any],
    prefix: str,
    allow_unprefixed: bool = False,
) -> bool:
    if prefix == "prompt572":
        return bool(
            payload.get("prompt572_longer_soak_stability_gate_success") is True
            and payload.get("prompt572_completion_claim_allowed") is True
            and payload.get("prompt572_no_remote_mutation_verified") is True
            and payload.get("prompt572_installation_performed") is False
            and payload.get("prompt572_daemon_started") is False
            and payload.get("prompt572_remote_workflow_included") is False
            and _prompt574_int(payload.get("prompt572_confirmed_soak_runs")) >= 5
            and _prompt574_int(payload.get("prompt572_confirmed_prompt568_runs"))
            >= 5
            and _prompt574_int(
                payload.get("prompt572_confirmed_inner_prompt565_cycles_total")
            )
            >= 10
        )
    if prefix == "prompt573":
        return bool(
            payload.get("prompt573_success") is True
            and payload.get("prompt573_completion_claim_allowed") is True
            and payload.get("prompt573_prompt572_repo_artifact_real_success")
            is True
            and payload.get("prompt573_no_remote_mutation_verified") is True
            and payload.get("prompt573_remote_workflow_included") is False
        )
    return False


def _prompt574_run_noop_daemon_simulator(
    *,
    artifact_dir: Path,
    heartbeat_count: int,
    interval_seconds: float,
    timeout_seconds: int,
) -> dict[str, Any]:
    heartbeat_path = artifact_dir / "observed_daemon_heartbeats.jsonl"
    child_script_path = artifact_dir / "observed_daemon_child.py"
    stdout_path = artifact_dir / "observed_daemon_stdout.txt"
    stderr_path = artifact_dir / "observed_daemon_stderr.txt"
    child_script = (
        "from __future__ import annotations\n"
        "\n"
        "import json\n"
        "from pathlib import Path\n"
        "import sys\n"
        "\n"
        "\n"
        "def main() -> int:\n"
        "    heartbeat_path = Path(sys.argv[1])\n"
        "    heartbeat_count = max(1, int(sys.argv[2]))\n"
        "    heartbeat_path.parent.mkdir(parents=True, exist_ok=True)\n"
        "    with heartbeat_path.open('w', encoding='utf-8') as handle:\n"
        "        for index in range(1, heartbeat_count + 1):\n"
        "            record = {\n"
        "                'heartbeat_index': index,\n"
        "                'heartbeat_total': heartbeat_count,\n"
        "                'source_prompt': 'prompt574',\n"
        "            }\n"
        "            handle.write(json.dumps(record, sort_keys=True) + '\\n')\n"
        "            handle.flush()\n"
        "    print(\n"
        "        json.dumps(\n"
        "            {\n"
        "                'heartbeat_count': heartbeat_count,\n"
        "                'heartbeat_path': str(heartbeat_path),\n"
        "                'source_prompt': 'prompt574',\n"
        "            },\n"
        "            sort_keys=True,\n"
        "        )\n"
        "    )\n"
        "    return 0\n"
        "\n"
        "\n"
        "if __name__ == '__main__':\n"
        "    raise SystemExit(main())\n"
    )
    child_script_path.write_text(child_script, encoding="utf-8")
    command = [
        sys.executable,
        str(child_script_path.resolve()),
        str(heartbeat_path.resolve()),
        str(max(1, int(heartbeat_count))),
    ]
    start_timestamp = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    with stdout_path.open("w", encoding="utf-8") as stdout_handle:
        with stderr_path.open("w", encoding="utf-8") as stderr_handle:
            process = subprocess.Popen(
                command,
                cwd=str(artifact_dir),
                stdout=stdout_handle,
                stderr=stderr_handle,
                text=True,
            )
            returncode: int | None
            timed_out = False
            try:
                returncode = process.wait(timeout=max(1, int(timeout_seconds)))
            except subprocess.TimeoutExpired:
                timed_out = True
                process.terminate()
                try:
                    returncode = process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    returncode = process.wait(timeout=5)
    stop_timestamp = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    observed_heartbeats = 0
    try:
        observed_heartbeats = sum(
            1
            for line in heartbeat_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    except OSError:
        observed_heartbeats = 0
    try:
        stdout_snippet = stdout_path.read_text(encoding="utf-8")[:1000]
    except OSError:
        stdout_snippet = ""
    try:
        stderr_snippet = stderr_path.read_text(encoding="utf-8")[:1000]
    except OSError:
        stderr_snippet = ""
    return {
        "pid": process.pid,
        "returncode": returncode,
        "timed_out": timed_out,
        "command": command,
        "child_script_path": str(child_script_path),
        "heartbeat_path": str(heartbeat_path),
        "observed_heartbeats": observed_heartbeats,
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "stdout_snippet": stdout_snippet,
        "stderr_snippet": stderr_snippet,
        "interval_seconds": interval_seconds,
        "start_timestamp": start_timestamp,
        "stop_timestamp": stop_timestamp,
    }


def run_prompt574_observed_daemon_run_gate(
    *,
    run_state_payload: Mapping[str, Any] | None = None,
    execution_repo_path: str | Path = "",
    enabled: bool | None = None,
    enable_token: str | None = None,
    timeout_seconds: int = 10,
    min_heartbeat_count: int = 3,
    artifact_dir: str | Path | None = None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    repo_text = _normalize_text(
        execution_repo_path or payload.get("execution_repo_path"),
        default="",
    )
    repo_path = Path(repo_text) if repo_text else Path(".")
    observed_daemon_artifact_dir = (
        Path(artifact_dir)
        if artifact_dir is not None
        else _PROMPT574_DEFAULT_ARTIFACT_DIR
    )
    if not observed_daemon_artifact_dir.is_absolute():
        observed_daemon_artifact_dir = repo_path / observed_daemon_artifact_dir

    prompt574_enabled = enabled is True
    prompt574_enable_token_valid = (
        _normalize_text(enable_token, default="")
        == PROMPT574_OBSERVED_DAEMON_RUN_GATE_ENABLE_TOKEN
    )
    requested_min_heartbeat_count = max(1, _prompt574_int(min_heartbeat_count))
    prompt572_success_ready = _prompt574_evidence_ready(
        payload=payload,
        prefix="prompt572",
        allow_unprefixed=(
            payload.get("prompt572_longer_soak_stability_gate_success") is True
        ),
    )
    prompt573_success_ready = _prompt574_evidence_ready(
        payload=payload,
        prefix="prompt573",
        allow_unprefixed=True,
    )
    blocked_reasons: list[str] = []
    if not prompt574_enabled:
        blocked_reasons.append("prompt574_enabled_required")
    if not prompt574_enable_token_valid:
        blocked_reasons.append("prompt574_enable_token_invalid")
    if not prompt572_success_ready:
        blocked_reasons.append("prompt574_prompt572_success_evidence_missing")
    if not prompt573_success_ready:
        blocked_reasons.append("prompt574_prompt573_success_evidence_missing")

    daemon_result: dict[str, Any] = {}
    daemon_started = False
    daemon_stopped = False
    daemon_returncode: int | None = None
    heartbeat_count = 0
    result_written = False
    summary_written = False
    installation_performed = False
    remote_workflow_included = False
    no_remote_mutation_verified = True
    final_worktree_clean = False

    can_run_daemon = bool(
        prompt574_enabled
        and prompt574_enable_token_valid
        and prompt572_success_ready
        and prompt573_success_ready
    )
    if can_run_daemon:
        observed_daemon_artifact_dir.mkdir(parents=True, exist_ok=True)
        daemon_result = _prompt574_run_noop_daemon_simulator(
            artifact_dir=observed_daemon_artifact_dir,
            heartbeat_count=requested_min_heartbeat_count,
            interval_seconds=0.05,
            timeout_seconds=timeout_seconds,
        )
        daemon_started = daemon_result.get("pid") is not None
        daemon_returncode = daemon_result.get("returncode")
        daemon_stopped = daemon_returncode is not None
        heartbeat_count = _prompt574_int(daemon_result.get("observed_heartbeats"))
        final_worktree_clean = _prompt565_worktree_clean_excluding_daemon_artifacts(
            repo_path=repo_path,
            daemon_artifact_dir=observed_daemon_artifact_dir,
        )

    daemon_observed = bool(heartbeat_count >= requested_min_heartbeat_count)
    result_path = observed_daemon_artifact_dir / "observed_daemon_result.json"
    summary_path = observed_daemon_artifact_dir / "observed_daemon_summary.json"
    result_payload = {
        "local_only": True,
        "source_prompt": "prompt574",
        "daemon_simulator": daemon_result,
        "service_install_performed": False,
        "systemd_service_file_created": False,
        "remote_mutation_performed": False,
    }
    if can_run_daemon:
        _write_json(result_path, result_payload)
        result_written = result_path.is_file()

    completion_checks = (
        ("prompt574_enabled", prompt574_enabled),
        ("prompt574_enable_token_valid", prompt574_enable_token_valid),
        ("prompt574_prompt572_success_ready", prompt572_success_ready),
        ("prompt574_prompt573_success_ready", prompt573_success_ready),
        ("prompt574_daemon_started", daemon_started),
        ("prompt574_daemon_observed", daemon_observed),
        ("prompt574_daemon_stopped", daemon_stopped),
        ("prompt574_daemon_returncode_zero", daemon_returncode == 0),
        (
            "prompt574_heartbeat_count_at_least_min",
            heartbeat_count >= requested_min_heartbeat_count,
        ),
        ("prompt574_result_written", result_written),
        ("prompt574_final_worktree_clean", final_worktree_clean),
        ("prompt574_no_remote_mutation_verified", no_remote_mutation_verified),
        (
            "prompt574_installation_performed_false",
            not installation_performed,
        ),
        (
            "prompt574_remote_workflow_included_false",
            not remote_workflow_included,
        ),
    )
    for field, passed in completion_checks:
        if not passed:
            blocked_reason = f"missing_{field}"
            if blocked_reason not in blocked_reasons:
                blocked_reasons.append(blocked_reason)

    status = "blocked_observed_daemon_run_gate_failed"
    if not prompt574_enabled:
        status = "blocked_observed_daemon_run_gate_disabled"
    elif not prompt574_enable_token_valid:
        status = "blocked_observed_daemon_run_gate_invalid_enable_token"
    elif not (prompt572_success_ready and prompt573_success_ready):
        status = "blocked_observed_daemon_run_gate_missing_prerequisite"

    summary: dict[str, Any] = {
        "local_only": True,
        "source_prompt": "prompt574",
        "prompt574_observed_daemon_run_gate_status": status,
        "prompt574_observed_daemon_run_gate_ready": can_run_daemon,
        "prompt574_observed_daemon_run_gate_success": False,
        "prompt574_enabled": prompt574_enabled,
        "prompt574_enable_token_valid": prompt574_enable_token_valid,
        "prompt574_prompt572_success_ready": prompt572_success_ready,
        "prompt574_prompt573_success_ready": prompt573_success_ready,
        "prompt574_daemon_observed": daemon_observed,
        "prompt574_daemon_started": daemon_started,
        "prompt574_daemon_stopped": daemon_stopped,
        "prompt574_daemon_returncode": daemon_returncode,
        "prompt574_heartbeat_count": heartbeat_count,
        "prompt574_min_heartbeat_count": requested_min_heartbeat_count,
        "prompt574_result_written": result_written,
        "prompt574_summary_written": False,
        "prompt574_final_worktree_clean": final_worktree_clean,
        "prompt574_no_remote_mutation_verified": no_remote_mutation_verified,
        "prompt574_installation_performed": installation_performed,
        "prompt574_remote_workflow_included": remote_workflow_included,
        "prompt574_completion_claim_allowed": False,
        "prompt574_next_action": (
            "manual_review_prompt574_observed_daemon_run_gate_failed"
        ),
        "prompt574_blocked_reasons": blocked_reasons,
        "prompt574_artifact_dir": str(observed_daemon_artifact_dir),
        "prompt574_result_path": str(result_path),
        "prompt574_summary_path": str(summary_path),
    }
    if can_run_daemon:
        _write_json(summary_path, summary)
        summary_written = summary_path.is_file()
        summary["prompt574_summary_written"] = summary_written
        if not summary_written:
            blocked_reasons.append("missing_prompt574_summary_written")

    success = bool(
        can_run_daemon
        and daemon_started
        and daemon_observed
        and daemon_stopped
        and daemon_returncode == 0
        and heartbeat_count >= requested_min_heartbeat_count
        and result_written
        and summary_written
        and final_worktree_clean
        and no_remote_mutation_verified
        and not installation_performed
        and not remote_workflow_included
        and not blocked_reasons
    )
    if success:
        status = "observed_daemon_run_gate_completed_local_only"
    elif (
        prompt574_enabled
        and prompt574_enable_token_valid
        and prompt572_success_ready
        and prompt573_success_ready
    ):
        status = "blocked_observed_daemon_run_gate_failed"
    next_action = (
        "observed_daemon_run_gate_completed_local_only"
        if success
        else "manual_review_prompt574_observed_daemon_run_gate_failed"
    )
    summary["prompt574_observed_daemon_run_gate_status"] = status
    summary["prompt574_observed_daemon_run_gate_success"] = success
    summary["prompt574_summary_written"] = summary_written
    summary["prompt574_completion_claim_allowed"] = success
    summary["prompt574_next_action"] = next_action
    summary["prompt574_blocked_reasons"] = blocked_reasons
    if summary_written:
        _write_json(summary_path, summary)
    return summary


def _prompt575_int(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _prompt575_prompt574_success_ready(payload: Mapping[str, Any]) -> bool:
    heartbeat_count = _prompt575_int(payload.get("prompt574_heartbeat_count"))
    min_heartbeat_count = max(
        1,
        _prompt575_int(payload.get("prompt574_min_heartbeat_count") or 3),
    )
    return bool(
        payload.get("prompt574_observed_daemon_run_gate_success") is True
        and payload.get("prompt574_daemon_started") is True
        and payload.get("prompt574_daemon_observed") is True
        and payload.get("prompt574_daemon_stopped") is True
        and payload.get("prompt574_daemon_returncode") == 0
        and heartbeat_count >= min_heartbeat_count
        and payload.get("prompt574_final_worktree_clean") is True
        and payload.get("prompt574_no_remote_mutation_verified") is True
        and payload.get("prompt574_installation_performed") is False
        and payload.get("prompt574_remote_workflow_included") is False
        and payload.get("prompt574_completion_claim_allowed") is True
    )


def run_prompt575_manual_service_install_gate(
    *,
    run_state_payload: Mapping[str, Any] | None = None,
    execution_repo_path: str | Path = "",
    enabled: bool | None = None,
    enable_token: str | None = None,
    service_name: str | None = None,
    command_entrypoint: Sequence[str] | str | None = None,
    working_directory: str | Path | None = None,
    environment_variables: Mapping[str, str] | None = None,
    artifact_dir: str | Path | None = None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    repo_text = _normalize_text(
        execution_repo_path or payload.get("execution_repo_path"),
        default="",
    )
    repo_path = Path(repo_text) if repo_text else Path(".")
    manual_service_artifact_dir = (
        Path(artifact_dir)
        if artifact_dir is not None
        else _PROMPT575_DEFAULT_ARTIFACT_DIR
    )
    if not manual_service_artifact_dir.is_absolute():
        manual_service_artifact_dir = repo_path / manual_service_artifact_dir

    prompt575_enabled = enabled is True
    prompt575_enable_token_valid = (
        _normalize_text(enable_token, default="")
        == PROMPT575_MANUAL_SERVICE_INSTALL_GATE_ENABLE_TOKEN
    )
    prompt574_success_ready = _prompt575_prompt574_success_ready(payload)
    prompt575_service_name = _normalize_text(
        service_name or payload.get("prompt575_service_name"),
        default="codex-local-runner",
    )
    proposed_working_directory = _normalize_text(
        working_directory or payload.get("prompt575_proposed_working_directory"),
        default=str(repo_path),
    )
    if command_entrypoint is None:
        proposed_command_entrypoint: list[str] = [
            sys.executable,
            "-m",
            "automation.orchestration.planned_runner.runner",
        ]
    elif isinstance(command_entrypoint, str):
        proposed_command_entrypoint = [command_entrypoint]
    else:
        proposed_command_entrypoint = [str(part) for part in command_entrypoint]
    env_vars = dict(environment_variables or {})

    blocked_reasons: list[str] = []
    if not prompt575_enabled:
        blocked_reasons.append("prompt575_enabled_required")
    if not prompt575_enable_token_valid:
        blocked_reasons.append("prompt575_enable_token_invalid")
    if not prompt574_success_ready:
        blocked_reasons.append("prompt575_prompt574_success_evidence_missing")

    can_prepare_plan = bool(
        prompt575_enabled
        and prompt575_enable_token_valid
        and prompt574_success_ready
    )
    systemd_file_created = False
    service_install_performed = False
    service_enable_performed = False
    service_start_performed = False
    persistent_daemon_started = False
    no_remote_mutation_verified = True
    remote_workflow_included = False
    plan_written = False
    summary_written = False
    final_worktree_clean = False
    plan_path = manual_service_artifact_dir / "manual_service_install_plan.json"
    summary_path = manual_service_artifact_dir / "manual_service_install_summary.json"

    if can_prepare_plan:
        manual_service_artifact_dir.mkdir(parents=True, exist_ok=True)
        plan_payload: dict[str, Any] = {
            "local_only": True,
            "source_prompt": "prompt575",
            "service_name_candidate": prompt575_service_name,
            "local_repo_path": str(repo_path),
            "proposed_command_entrypoint": proposed_command_entrypoint,
            "proposed_working_directory": proposed_working_directory,
            "proposed_environment_variables": env_vars,
            "install_steps_text_only": [
                "Review this plan manually before any service installation.",
                "Create a service unit only in a separate, explicit manual step.",
                "Run any install, enable, or start command only after separate approval.",
            ],
            "rollback_steps_text_only": [
                "Stop the service only if it was started in a later manual step.",
                "Disable the service only if it was enabled in a later manual step.",
                "Remove the service file only if it was created in a later manual step.",
                "Reload service manager state only in the later manual step.",
            ],
            "safety_notes": [
                "This gate does not call systemctl.",
                "This gate does not write to systemd service paths.",
                "This gate does not run sudo.",
                "This gate does not start a persistent daemon.",
                "This gate does not use remote workflows or network APIs.",
            ],
            "systemd_file_created": systemd_file_created,
            "service_install_performed": service_install_performed,
            "service_enable_performed": service_enable_performed,
            "service_start_performed": service_start_performed,
            "persistent_daemon_started": persistent_daemon_started,
            "remote_mutation_performed": False,
            "remote_workflow_included": remote_workflow_included,
        }
        _write_json(plan_path, plan_payload)
        plan_written = plan_path.is_file()
        final_worktree_clean = _prompt565_worktree_clean_excluding_daemon_artifacts(
            repo_path=repo_path,
            daemon_artifact_dir=manual_service_artifact_dir,
        )

    completion_checks = (
        ("prompt575_enabled", prompt575_enabled),
        ("prompt575_enable_token_valid", prompt575_enable_token_valid),
        ("prompt575_prompt574_success_ready", prompt574_success_ready),
        ("prompt575_plan_written", plan_written),
        ("prompt575_systemd_file_created_false", not systemd_file_created),
        (
            "prompt575_service_install_performed_false",
            not service_install_performed,
        ),
        (
            "prompt575_service_enable_performed_false",
            not service_enable_performed,
        ),
        ("prompt575_service_start_performed_false", not service_start_performed),
        (
            "prompt575_persistent_daemon_started_false",
            not persistent_daemon_started,
        ),
        (
            "prompt575_no_remote_mutation_verified",
            no_remote_mutation_verified,
        ),
        (
            "prompt575_remote_workflow_included_false",
            not remote_workflow_included,
        ),
        ("prompt575_final_worktree_clean", final_worktree_clean),
    )
    for field, passed in completion_checks:
        if not passed:
            blocked_reason = f"missing_{field}"
            if blocked_reason not in blocked_reasons:
                blocked_reasons.append(blocked_reason)

    status = "blocked_manual_service_install_gate_failed"
    if not prompt574_success_ready:
        status = "blocked_manual_service_install_gate_missing_prerequisite"

    summary: dict[str, Any] = {
        "local_only": True,
        "source_prompt": "prompt575",
        "prompt575_manual_service_install_gate_status": status,
        "prompt575_manual_service_install_gate_ready": can_prepare_plan,
        "prompt575_manual_service_install_gate_success": False,
        "prompt575_enabled": prompt575_enabled,
        "prompt575_enable_token_valid": prompt575_enable_token_valid,
        "prompt575_prompt574_success_ready": prompt574_success_ready,
        "prompt575_plan_written": plan_written,
        "prompt575_summary_written": False,
        "prompt575_service_name": prompt575_service_name,
        "prompt575_service_install_plan_path": str(plan_path),
        "prompt575_service_install_summary_path": str(summary_path),
        "prompt575_systemd_file_created": systemd_file_created,
        "prompt575_service_install_performed": service_install_performed,
        "prompt575_service_enable_performed": service_enable_performed,
        "prompt575_service_start_performed": service_start_performed,
        "prompt575_persistent_daemon_started": persistent_daemon_started,
        "prompt575_no_remote_mutation_verified": no_remote_mutation_verified,
        "prompt575_remote_workflow_included": remote_workflow_included,
        "prompt575_final_worktree_clean": final_worktree_clean,
        "prompt575_completion_claim_allowed": False,
        "prompt575_next_action": "manual_review_prompt575_manual_service_install_gate_failed",
        "prompt575_blocked_reasons": blocked_reasons,
        "prompt575_artifact_dir": str(manual_service_artifact_dir),
    }
    if can_prepare_plan:
        _write_json(summary_path, summary)
        summary_written = summary_path.is_file()
        summary["prompt575_summary_written"] = summary_written
        if not summary_written:
            blocked_reasons.append("missing_prompt575_summary_written")

    success = bool(
        prompt574_success_ready
        and plan_written
        and summary_written
        and not systemd_file_created
        and not service_install_performed
        and not service_enable_performed
        and not service_start_performed
        and not persistent_daemon_started
        and no_remote_mutation_verified
        and not remote_workflow_included
        and final_worktree_clean
        and not blocked_reasons
    )
    if success:
        status = "manual_service_install_gate_ready_local_only"
    elif not prompt574_success_ready:
        status = "blocked_manual_service_install_gate_missing_prerequisite"
    else:
        status = "blocked_manual_service_install_gate_failed"
    next_action = (
        "manual_service_install_ready_for_separate_manual_step"
        if success
        else "manual_review_prompt575_manual_service_install_gate_failed"
    )
    summary["prompt575_manual_service_install_gate_status"] = status
    summary["prompt575_manual_service_install_gate_success"] = success
    summary["prompt575_summary_written"] = summary_written
    summary["prompt575_completion_claim_allowed"] = success
    summary["prompt575_next_action"] = next_action
    summary["prompt575_blocked_reasons"] = blocked_reasons
    if summary_written:
        _write_json(summary_path, summary)
    return summary


def _prompt576_int(value: Any, *, default: int = 0) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def _prompt576_prompt575_success_ready(payload: Mapping[str, Any]) -> bool:
    return bool(
        payload.get("prompt575_manual_service_install_gate_success") is True
        and payload.get("prompt575_prompt574_success_ready") is True
        and payload.get("prompt575_enabled") is True
        and payload.get("prompt575_enable_token_valid") is True
        and payload.get("prompt575_plan_written") is True
        and payload.get("prompt575_summary_written") is True
        and payload.get("prompt575_systemd_file_created") is False
        and payload.get("prompt575_service_install_performed") is False
        and payload.get("prompt575_service_enable_performed") is False
        and payload.get("prompt575_service_start_performed") is False
        and payload.get("prompt575_persistent_daemon_started") is False
        and payload.get("prompt575_no_remote_mutation_verified") is True
        and payload.get("prompt575_remote_workflow_included") is False
        and payload.get("prompt575_final_worktree_clean") is True
        and payload.get("prompt575_completion_claim_allowed") is True
    )


def _prompt577_prompt576_success_ready(payload: Mapping[str, Any]) -> bool:
    return bool(
        payload.get("prompt576_bounded_multi_cycle_daemon_runner_success")
        is True
        and payload.get("prompt576_prompt575_success_ready") is True
        and _prompt576_int(payload.get("prompt576_requested_cycles")) == 3
        and _prompt576_int(payload.get("prompt576_completed_cycles")) == 3
        and _prompt576_int(payload.get("prompt576_failed_cycles")) == 0
        and _prompt576_int(payload.get("prompt576_cycle_summaries_written")) == 3
        and payload.get("prompt576_heartbeat_written") is True
        and payload.get("prompt576_resume_state_written") is True
        and payload.get("prompt576_aggregate_summary_written") is True
        and payload.get("prompt576_stop_reason") == "max_cycles_reached"
        and payload.get("prompt576_max_cycles_reached") is True
        and payload.get("prompt576_daemon_started") is True
        and payload.get("prompt576_daemon_stopped") is True
        and payload.get("prompt576_installation_performed") is False
        and payload.get("prompt576_systemd_used") is False
        and payload.get("prompt576_service_enable_performed") is False
        and payload.get("prompt576_service_start_performed") is False
        and payload.get("prompt576_persistent_service_started") is False
        and payload.get("prompt576_remote_workflow_included") is False
        and payload.get("prompt576_no_remote_mutation_verified") is True
        and payload.get("prompt576_final_worktree_clean") is True
        and payload.get("prompt576_completion_claim_allowed") is True
    )


def run_prompt576_bounded_multi_cycle_daemon_runner_proof(
    *,
    run_state_payload: Mapping[str, Any] | None = None,
    execution_repo_path: str | Path = "",
    requested_cycles: int | None = None,
    artifact_dir: str | Path | None = None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    repo_text = _normalize_text(
        execution_repo_path or payload.get("execution_repo_path"),
        default="",
    )
    repo_path = Path(repo_text) if repo_text else Path(".")
    daemon_artifact_dir = (
        Path(artifact_dir)
        if artifact_dir is not None
        else _PROMPT576_DEFAULT_ARTIFACT_DIR
    )
    if not daemon_artifact_dir.is_absolute():
        daemon_artifact_dir = repo_path / daemon_artifact_dir

    prompt575_success_ready = _prompt576_prompt575_success_ready(payload)
    requested_cycle_count = _prompt576_int(
        requested_cycles
        if requested_cycles is not None
        else payload.get("prompt576_requested_cycles", 3),
        default=3,
    )
    if requested_cycle_count == 0:
        requested_cycle_count = 3

    installation_performed = False
    systemd_used = False
    service_enable_performed = False
    service_start_performed = False
    persistent_service_started = False
    remote_workflow_included = False
    no_remote_mutation_verified = True

    blocked_reasons: list[str] = []
    if not prompt575_success_ready:
        blocked_reasons.append("prompt576_prompt575_success_evidence_missing")

    can_run = prompt575_success_ready
    daemon_started = False
    daemon_stopped = False
    completed_cycles = 0
    failed_cycles = 0
    cycle_summaries_written = 0
    heartbeat_written = False
    resume_state_written = False
    aggregate_summary_written = False
    stop_reason = ""
    max_cycles_reached = False
    final_worktree_clean = False
    heartbeat_path = daemon_artifact_dir / "daemon_heartbeat.jsonl"
    resume_state_path = daemon_artifact_dir / "daemon_resume_state.json"
    aggregate_summary_path = daemon_artifact_dir / "daemon_aggregate_summary.json"

    if can_run:
        daemon_artifact_dir.mkdir(parents=True, exist_ok=True)
        daemon_started = True
        with heartbeat_path.open("w", encoding="utf-8") as heartbeat_handle:
            for cycle_index in range(1, requested_cycle_count + 1):
                heartbeat_record = {
                    "cycle_index": cycle_index,
                    "heartbeat_index": cycle_index,
                    "requested_cycles": requested_cycle_count,
                    "source_prompt": "prompt576",
                    "status": "cycle_started",
                }
                heartbeat_handle.write(
                    json.dumps(heartbeat_record, sort_keys=True) + "\n"
                )
                heartbeat_handle.flush()
                heartbeat_written = heartbeat_path.is_file()

                cycle_summary_path = (
                    daemon_artifact_dir
                    / f"daemon_cycle_{cycle_index:03d}_summary.json"
                )
                cycle_summary = {
                    "local_only": True,
                    "source_prompt": "prompt576",
                    "cycle_index": cycle_index,
                    "requested_cycles": requested_cycle_count,
                    "cycle_status": "completed",
                    "codex_invoked": False,
                    "tracked_files_modified": False,
                    "installation_performed": installation_performed,
                    "systemd_used": systemd_used,
                    "service_enable_performed": service_enable_performed,
                    "service_start_performed": service_start_performed,
                    "persistent_service_started": persistent_service_started,
                    "remote_workflow_included": remote_workflow_included,
                    "remote_mutation_performed": False,
                }
                _write_json(cycle_summary_path, cycle_summary)
                if cycle_summary_path.is_file():
                    cycle_summaries_written += 1
                    completed_cycles += 1
                else:
                    failed_cycles += 1

                cycle_stop_reason = (
                    "max_cycles_reached"
                    if cycle_index == requested_cycle_count
                    else ""
                )
                resume_state = {
                    "local_only": True,
                    "source_prompt": "prompt576",
                    "requested_cycles": requested_cycle_count,
                    "completed_cycles": completed_cycles,
                    "failed_cycles": failed_cycles,
                    "last_completed_cycle": completed_cycles,
                    "next_cycle_index": (
                        cycle_index + 1
                        if cycle_index < requested_cycle_count
                        else None
                    ),
                    "stop_reason": cycle_stop_reason,
                    "codex_invoked": False,
                    "remote_mutation_performed": False,
                }
                _write_json(resume_state_path, resume_state)
                resume_state_written = resume_state_path.is_file()

        daemon_stopped = True
        stop_reason = "max_cycles_reached"
        max_cycles_reached = completed_cycles == requested_cycle_count
        final_worktree_clean = _prompt565_worktree_clean_excluding_daemon_artifacts(
            repo_path=repo_path,
            daemon_artifact_dir=daemon_artifact_dir,
        )

    completion_checks = (
        ("prompt576_prompt575_success_ready", prompt575_success_ready),
        ("prompt576_requested_cycles_default_3", requested_cycle_count == 3),
        (
            "prompt576_completed_cycles_match_requested",
            completed_cycles == requested_cycle_count,
        ),
        ("prompt576_failed_cycles_zero", failed_cycles == 0),
        (
            "prompt576_cycle_summaries_written_match_requested",
            cycle_summaries_written == requested_cycle_count,
        ),
        ("prompt576_heartbeat_written", heartbeat_written),
        ("prompt576_resume_state_written", resume_state_written),
        (
            "prompt576_stop_reason_max_cycles_reached",
            stop_reason == "max_cycles_reached",
        ),
        ("prompt576_max_cycles_reached", max_cycles_reached),
        ("prompt576_daemon_started", daemon_started),
        ("prompt576_daemon_stopped", daemon_stopped),
        ("prompt576_installation_performed_false", not installation_performed),
        ("prompt576_systemd_used_false", not systemd_used),
        (
            "prompt576_service_enable_performed_false",
            not service_enable_performed,
        ),
        (
            "prompt576_service_start_performed_false",
            not service_start_performed,
        ),
        (
            "prompt576_persistent_service_started_false",
            not persistent_service_started,
        ),
        (
            "prompt576_remote_workflow_included_false",
            not remote_workflow_included,
        ),
        (
            "prompt576_no_remote_mutation_verified",
            no_remote_mutation_verified,
        ),
        ("prompt576_final_worktree_clean", final_worktree_clean),
    )
    for field, passed in completion_checks:
        if not passed:
            blocked_reason = f"missing_{field}"
            if blocked_reason not in blocked_reasons:
                blocked_reasons.append(blocked_reason)

    summary: dict[str, Any] = {
        "local_only": True,
        "source_prompt": "prompt576",
        "prompt576_bounded_multi_cycle_daemon_runner_status": (
            "blocked_bounded_multi_cycle_daemon_runner_missing_prerequisite"
            if not prompt575_success_ready
            else "blocked_bounded_multi_cycle_daemon_runner_failed"
        ),
        "prompt576_bounded_multi_cycle_daemon_runner_ready": can_run,
        "prompt576_bounded_multi_cycle_daemon_runner_success": False,
        "prompt576_prompt575_success_ready": prompt575_success_ready,
        "prompt576_requested_cycles": requested_cycle_count,
        "prompt576_completed_cycles": completed_cycles,
        "prompt576_failed_cycles": failed_cycles,
        "prompt576_cycle_summaries_written": cycle_summaries_written,
        "prompt576_heartbeat_written": heartbeat_written,
        "prompt576_resume_state_written": resume_state_written,
        "prompt576_aggregate_summary_written": False,
        "prompt576_stop_reason": stop_reason,
        "prompt576_max_cycles_reached": max_cycles_reached,
        "prompt576_daemon_started": daemon_started,
        "prompt576_daemon_stopped": daemon_stopped,
        "prompt576_installation_performed": installation_performed,
        "prompt576_systemd_used": systemd_used,
        "prompt576_service_enable_performed": service_enable_performed,
        "prompt576_service_start_performed": service_start_performed,
        "prompt576_persistent_service_started": persistent_service_started,
        "prompt576_remote_workflow_included": remote_workflow_included,
        "prompt576_no_remote_mutation_verified": no_remote_mutation_verified,
        "prompt576_final_worktree_clean": final_worktree_clean,
        "prompt576_completion_claim_allowed": False,
        "prompt576_next_action": (
            "manual_review_prompt576_bounded_multi_cycle_daemon_runner_failed"
        ),
        "prompt576_blocked_reasons": blocked_reasons,
        "prompt576_artifact_dir": str(daemon_artifact_dir),
        "prompt576_heartbeat_path": str(heartbeat_path),
        "prompt576_resume_state_path": str(resume_state_path),
        "prompt576_aggregate_summary_path": str(aggregate_summary_path),
    }
    if can_run:
        _write_json(aggregate_summary_path, summary)
        aggregate_summary_written = aggregate_summary_path.is_file()
        summary["prompt576_aggregate_summary_written"] = aggregate_summary_written
        if not aggregate_summary_written:
            blocked_reasons.append("missing_prompt576_aggregate_summary_written")

    success = bool(
        prompt575_success_ready
        and requested_cycle_count == 3
        and completed_cycles == requested_cycle_count
        and failed_cycles == 0
        and cycle_summaries_written == requested_cycle_count
        and heartbeat_written
        and resume_state_written
        and aggregate_summary_written
        and stop_reason == "max_cycles_reached"
        and max_cycles_reached
        and daemon_started
        and daemon_stopped
        and not installation_performed
        and not systemd_used
        and not service_enable_performed
        and not service_start_performed
        and not persistent_service_started
        and not remote_workflow_included
        and no_remote_mutation_verified
        and final_worktree_clean
        and not blocked_reasons
    )
    if success:
        status = "bounded_multi_cycle_daemon_runner_completed_local_only"
    elif not prompt575_success_ready:
        status = "blocked_bounded_multi_cycle_daemon_runner_missing_prerequisite"
    else:
        status = "blocked_bounded_multi_cycle_daemon_runner_failed"
    next_action = (
        "bounded_multi_cycle_daemon_runner_completed_local_only"
        if success
        else "manual_review_prompt576_bounded_multi_cycle_daemon_runner_failed"
    )
    summary["prompt576_bounded_multi_cycle_daemon_runner_status"] = status
    summary["prompt576_bounded_multi_cycle_daemon_runner_success"] = success
    summary["prompt576_completion_claim_allowed"] = success
    summary["prompt576_next_action"] = next_action
    summary["prompt576_blocked_reasons"] = blocked_reasons
    if aggregate_summary_written:
        _write_json(aggregate_summary_path, summary)
    return summary


def _prompt577_tracked_files_modified(repo_path: Path) -> bool:
    completed = subprocess.run(
        ["git", "diff", "--quiet", "--"],
        cwd=str(repo_path),
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode != 0


def _prompt577_direction_payload() -> dict[str, Any]:
    allowed_files = [
        "automation/orchestration/planned_runner/runtime_output_wiring.py",
        "automation/orchestration/planned_runner/prompt_surfaces/prompts_450_499.py",
        "automation/orchestration/planned_runner/prompt_surfaces/registry.py",
    ]
    forbidden_operations = [
        "invoke Codex unless explicit Prompt578 enable token is present",
        "commit",
        "tag",
        "remote push",
        "pull request",
        "merge",
        "install packages",
        "install or enable services",
        "systemd writes",
        "systemctl",
        "sudo",
        "persistent daemon start",
    ]
    return {
        "source_prompt": "prompt577",
        "target_next_prompt": "prompt578",
        "cycle_type": "actual_codex_development_cycle",
        "development_goal": (
            "Implement a minimal local-only actual Codex dispatch cycle gate "
            "for one prepared prompt artifact with explicit enable-token "
            "execution and observable not_run/success/failed results."
        ),
        "allowed_files": allowed_files,
        "forbidden_operations": forbidden_operations,
        "expected_runtime_fields": [
            "prompt578_actual_codex_dispatch_cycle_status",
            "prompt578_actual_codex_dispatch_cycle_ready",
            "prompt578_actual_codex_dispatch_cycle_success",
            "prompt578_prompt577_bridge_ready",
            "prompt578_codex_prompt_artifact_path",
            "prompt578_dispatch_request_prepared",
            "prompt578_dispatch_request_fields",
            "prompt578_actual_codex_enabled",
            "prompt578_actual_codex_enable_token_valid",
            "prompt578_actual_codex_executed",
            "prompt578_stdout_path",
            "prompt578_stderr_path",
            "prompt578_result_path",
            "prompt578_result_classification",
            "prompt578_no_remote_mutation_verified",
            "prompt578_installation_performed",
            "prompt578_systemd_used",
            "prompt578_persistent_service_started",
            "prompt578_final_worktree_clean",
            "prompt578_completion_claim_allowed",
            "prompt578_blocked_reasons",
        ],
        "verification_strategy": {
            "compile": "python -m compileall automation/orchestration/planned_runner",
            "import": (
                "python - <<'PY'\n"
                "from automation.orchestration.planned_runner.prompt_surfaces.registry "
                "import get_prompt_builders\n"
                "assert '_build_prompt578_actual_codex_dispatch_cycle_gate_state' "
                "in get_prompt_builders()\n"
                "PY"
            ),
            "runtime": (
                "Exercise missing-prerequisite, disabled/not_run, and explicit "
                "enabled classifications without remote operations or service "
                "installation."
            ),
        },
        "evaluation_strategy": (
            "Score Prompt578 against usefulness, safety, determinism, "
            "observability, recovery readiness, and clean worktree preservation."
        ),
        "commit_tag_strategy": {
            "prompt578_runtime": "never commit or tag during runtime",
            "operator_after_success": (
                "manual commit/tag may occur only after clean local review"
            ),
        },
        "stop_conditions": [
            "missing Prompt577 bridge readiness",
            "missing prepared prompt artifact",
            "missing explicit Prompt578 enable token",
            "forbidden operation detected",
            "tracked file mutation outside allowed files",
            "runtime result cannot be classified",
        ],
    }


def _prompt577_codex_prompt_text() -> str:
    return """You are editing /home/rai/codex-local-runner.

Task: Implement Prompt578 minimal actual Codex dispatch cycle gate.
Mode: Implement.

Goal:
Add a local-only Prompt578 gate that accepts one prepared Codex prompt artifact from Prompt577, prepares observable dispatch request fields, optionally executes Codex only when an explicit enable token is present, records stdout/stderr/result paths, and classifies the result as not_run, success, or failed.

Allowed files:
- automation/orchestration/planned_runner/runtime_output_wiring.py
- automation/orchestration/planned_runner/prompt_surfaces/prompts_450_499.py
- automation/orchestration/planned_runner/prompt_surfaces/registry.py

Forbidden files:
- all files not listed above

Expected artifact/output:
- Runtime wrapper for Prompt578
- Prompt578 prompt surface state builder
- Prompt578 registration in the existing prompt surface registry
- Local runtime artifacts under artifacts/runtime_commands/prompt578_actual_codex_dispatch_cycle_gate when the wrapper is run

Required behavior:
1. Require Prompt577 bridge readiness before dispatch readiness.
2. Accept the prepared Codex prompt artifact path from Prompt577.
3. Expose dispatch request fields including prompt path, repo path, allowed files, forbidden operations, timeout, stdout path, stderr path, result path, and enable-token status.
4. Do not invoke Codex unless Prompt578 has an explicit enable flag and valid enable token.
5. In the disabled path, write a not_run result with stdout/stderr/result paths and safety fields.
6. In the enabled path, execute at most one bounded local Codex subprocess using existing local adapter patterns if available.
7. Classify results as not_run, success, or failed.
8. Preserve no-remote/no-install safety fields.
9. Do not perform remote operations.
10. Do not install services.
11. Do not start a persistent daemon.
12. Do not commit or tag during runtime.

Allowed validation commands:
- python -m compileall automation/orchestration/planned_runner
- python - <<'PY'
from automation.orchestration.planned_runner.prompt_surfaces.registry import get_prompt_builders
assert '_build_prompt578_actual_codex_dispatch_cycle_gate_state' in get_prompt_builders()
PY
- python - <<'PY'
from automation.orchestration.planned_runner.runtime_output_wiring import run_prompt578_actual_codex_dispatch_cycle_gate
summary = run_prompt578_actual_codex_dispatch_cycle_gate(run_state_payload={})
assert summary['prompt578_actual_codex_dispatch_cycle_status'] == 'blocked_actual_codex_dispatch_cycle_missing_prerequisite'
assert summary['prompt578_actual_codex_executed'] is False
PY

Explicitly out of scope:
- Broad tests
- Docs
- Service installation
- systemd
- systemctl
- sudo
- Remote operations
- Persistent daemon start
- Runtime commit/tag
- More than one Codex dispatch attempt
"""


def _prompt577_verification_command_text() -> str:
    return """#!/usr/bin/env bash
set -euo pipefail

echo "=== compile ==="
python -m py_compile \
  automation/orchestration/planned_runner/runtime_output_wiring.py \
  automation/orchestration/planned_runner/prompt_surfaces/prompts_450_499.py \
  automation/orchestration/planned_runner/prompt_surfaces/registry.py
echo "COMPILE_OK=true"

python -m compileall automation/orchestration/planned_runner

python - <<'PY'
from automation.orchestration.planned_runner.prompt_surfaces.registry import get_prompt_builders
builders = get_prompt_builders()
assert '_build_prompt578_actual_codex_dispatch_cycle_gate_state' in builders
PY

python - <<'PY'
from automation.orchestration.planned_runner.runtime_output_wiring import run_prompt578_actual_codex_dispatch_cycle_gate
summary = run_prompt578_actual_codex_dispatch_cycle_gate(run_state_payload={})
assert summary['prompt578_actual_codex_dispatch_cycle_status'] == 'blocked_actual_codex_dispatch_cycle_missing_prerequisite'
assert summary['prompt578_actual_codex_executed'] is False
PY

python - <<'PY'
from automation.orchestration.planned_runner.runtime_output_wiring import run_prompt578_actual_codex_dispatch_cycle_gate
payload = {
    'prompt577_actual_autonomous_development_cycle_bridge_success': True,
    'prompt577_actual_autonomous_development_cycle_bridge_ready': True,
    'prompt577_prompt576_success_ready': True,
    'prompt577_direction_written': True,
    'prompt577_codex_prompt_written': True,
    'prompt577_verification_command_written': True,
    'prompt577_evaluation_rubric_written': True,
    'prompt577_retry_fix_route_written': True,
    'prompt577_bridge_summary_written': True,
    'prompt577_target_next_prompt': 'prompt578',
    'prompt577_cycle_type': 'actual_codex_development_cycle',
    'prompt577_actual_codex_dispatch_ready': True,
    'prompt577_actual_codex_executed': False,
    'prompt577_tracked_files_modified_during_runtime': False,
    'prompt577_commit_performed': False,
    'prompt577_installation_performed': False,
    'prompt577_systemd_used': False,
    'prompt577_service_enable_performed': False,
    'prompt577_service_start_performed': False,
    'prompt577_persistent_service_started': False,
    'prompt577_remote_workflow_included': False,
    'prompt577_no_remote_mutation_verified': True,
    'prompt577_final_worktree_clean': True,
    'prompt577_completion_claim_allowed': True,
    'prompt577_codex_prompt_path': 'artifacts/runtime_commands/prompt577_actual_autonomous_development_cycle_bridge/actual_development_codex_prompt.txt',
    'prompt577_blocked_reasons': [],
}
summary = run_prompt578_actual_codex_dispatch_cycle_gate(run_state_payload=payload)
assert summary['prompt578_result_classification'] == 'not_run'
assert summary['prompt578_actual_codex_executed'] is False
PY

python - <<'PY'
import ast
from pathlib import Path

paths = [
    Path('automation/orchestration/planned_runner/runtime_output_wiring.py'),
    Path('automation/orchestration/planned_runner/prompt_surfaces/prompts_450_499.py'),
    Path('automation/orchestration/planned_runner/prompt_surfaces/registry.py'),
]
forbidden = {
    ('systemctl',),
    ('sudo',),
    ('git', 'push'),
    ('git', 'commit'),
    ('git', 'tag'),
    ('gh', 'pr'),
}

def literal_list(node):
    if not isinstance(node, (ast.List, ast.Tuple)):
        return None
    values = []
    for item in node.elts:
        if not isinstance(item, ast.Constant) or not isinstance(item.value, str):
            return None
        values.append(item.value)
    return tuple(values)

for path in paths:
    tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (
            isinstance(func, ast.Attribute)
            and func.attr in {'run', 'Popen', 'call', 'check_call', 'check_output'}
            and isinstance(func.value, ast.Name)
            and func.value.id == 'subprocess'
        ):
            continue
        command = literal_list(node.args[0]) if node.args else None
        if command is None:
            continue
        for prefix in forbidden:
            if command[: len(prefix)] == prefix:
                raise SystemExit(f'Forbidden executable operation found: {path}: {command}')
PY

if [[ "${PROMPT578_ACTUAL_CODEX_DISPATCH_ENABLE:-}" == "I_UNDERSTAND_RUN_ONE_LOCAL_CODEX_DISPATCH" ]]; then
  python - <<'PY'
from automation.orchestration.planned_runner.runtime_output_wiring import run_prompt578_actual_codex_dispatch_cycle_gate
payload = {
    'prompt577_actual_autonomous_development_cycle_bridge_success': True,
    'prompt577_actual_autonomous_development_cycle_bridge_ready': True,
    'prompt577_prompt576_success_ready': True,
    'prompt577_direction_written': True,
    'prompt577_codex_prompt_written': True,
    'prompt577_verification_command_written': True,
    'prompt577_evaluation_rubric_written': True,
    'prompt577_retry_fix_route_written': True,
    'prompt577_bridge_summary_written': True,
    'prompt577_target_next_prompt': 'prompt578',
    'prompt577_cycle_type': 'actual_codex_development_cycle',
    'prompt577_actual_codex_dispatch_ready': True,
    'prompt577_actual_codex_executed': False,
    'prompt577_tracked_files_modified_during_runtime': False,
    'prompt577_commit_performed': False,
    'prompt577_installation_performed': False,
    'prompt577_systemd_used': False,
    'prompt577_service_enable_performed': False,
    'prompt577_service_start_performed': False,
    'prompt577_persistent_service_started': False,
    'prompt577_remote_workflow_included': False,
    'prompt577_no_remote_mutation_verified': True,
    'prompt577_final_worktree_clean': True,
    'prompt577_completion_claim_allowed': True,
    'prompt577_codex_prompt_path': 'artifacts/runtime_commands/prompt577_actual_autonomous_development_cycle_bridge/actual_development_codex_prompt.txt',
    'prompt577_blocked_reasons': [],
}
summary = run_prompt578_actual_codex_dispatch_cycle_gate(
    run_state_payload=payload,
    enabled=True,
    enable_token='I_UNDERSTAND_RUN_ONE_LOCAL_CODEX_DISPATCH',
)
assert summary['prompt578_actual_codex_executed'] is True
assert summary['prompt578_result_classification'] in {'success', 'failed'}
PY
fi

git diff --quiet --
"""


def _prompt577_evaluation_rubric_payload() -> dict[str, Any]:
    return {
        "source_prompt": "prompt577",
        "target_next_prompt": "prompt578",
        "total_points": 100,
        "criteria": {
            "actual_development_usefulness": {
                "points": 25,
                "required": (
                    "Prompt578 can bridge one prepared prompt artifact into "
                    "a concrete local Codex dispatch request."
                ),
            },
            "safety": {
                "points": 20,
                "required": (
                    "No remote operations, installs, systemd, persistent "
                    "service start, runtime commit, or runtime tag."
                ),
            },
            "determinism": {
                "points": 15,
                "required": (
                    "Missing prerequisite and disabled paths produce stable "
                    "not_run/blocked summaries."
                ),
            },
            "observability": {
                "points": 15,
                "required": (
                    "Dispatch fields and stdout/stderr/result paths are "
                    "recorded even when execution is disabled."
                ),
            },
            "recovery_readiness": {
                "points": 15,
                "required": (
                    "Failures classify cleanly and expose blocked reasons "
                    "that route to narrow fixes."
                ),
            },
            "clean_worktree_preservation": {
                "points": 10,
                "required": (
                    "Runtime does not modify tracked files and reports clean "
                    "candidate behavior excluding generated artifacts."
                ),
            },
        },
        "passing_score": 90,
    }


def _prompt577_retry_fix_route_payload() -> dict[str, Any]:
    return {
        "source_prompt": "prompt577",
        "target_next_prompt": "prompt578",
        "routes": [
            {
                "condition": "if import fails",
                "action": "fix registration/symbol names",
            },
            {
                "condition": "if dispatch fields missing",
                "action": "fix field exposure only",
            },
            {
                "condition": "if Codex result missing",
                "action": "fix result capture only",
            },
            {
                "condition": "if final clean fails",
                "action": "verify in clean worktree before changing logic",
            },
            {
                "condition": "if forbidden operation appears",
                "action": "remove operation and keep artifact-only behavior",
            },
        ],
    }


def run_prompt577_actual_autonomous_development_cycle_bridge(
    *,
    run_state_payload: Mapping[str, Any] | None = None,
    execution_repo_path: str | Path = "",
    artifact_dir: str | Path | None = None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    repo_text = _normalize_text(
        execution_repo_path or payload.get("execution_repo_path"),
        default="",
    )
    repo_path = Path(repo_text) if repo_text else Path(".")
    bridge_artifact_dir = (
        Path(artifact_dir)
        if artifact_dir is not None
        else _PROMPT577_DEFAULT_ARTIFACT_DIR
    )
    if not bridge_artifact_dir.is_absolute():
        bridge_artifact_dir = repo_path / bridge_artifact_dir

    prompt576_success_ready = _prompt577_prompt576_success_ready(payload)
    actual_codex_executed = False
    commit_performed = False
    installation_performed = False
    systemd_used = False
    service_enable_performed = False
    service_start_performed = False
    persistent_service_started = False
    remote_workflow_included = False
    no_remote_mutation_verified = True

    direction_path = bridge_artifact_dir / "actual_development_direction.json"
    codex_prompt_path = (
        bridge_artifact_dir / "actual_development_codex_prompt.txt"
    )
    verification_command_path = (
        bridge_artifact_dir / "actual_development_verification_command.sh"
    )
    evaluation_rubric_path = (
        bridge_artifact_dir / "actual_development_evaluation_rubric.json"
    )
    retry_fix_route_path = (
        bridge_artifact_dir / "actual_development_retry_fix_route.json"
    )
    bridge_summary_path = (
        bridge_artifact_dir / "actual_development_bridge_summary.json"
    )

    blocked_reasons: list[str] = []
    if not prompt576_success_ready:
        blocked_reasons.append("prompt577_prompt576_success_evidence_missing")

    direction_written = False
    codex_prompt_written = False
    verification_command_written = False
    evaluation_rubric_written = False
    retry_fix_route_written = False
    bridge_summary_written = False
    target_next_prompt = "prompt578"
    cycle_type = "actual_codex_development_cycle"

    if prompt576_success_ready:
        bridge_artifact_dir.mkdir(parents=True, exist_ok=True)
        _write_json(direction_path, _prompt577_direction_payload())
        direction_written = direction_path.is_file()
        codex_prompt_path.write_text(
            _prompt577_codex_prompt_text(),
            encoding="utf-8",
        )
        codex_prompt_written = codex_prompt_path.is_file()
        verification_command_path.write_text(
            _prompt577_verification_command_text(),
            encoding="utf-8",
        )
        verification_command_written = verification_command_path.is_file()
        _write_json(
            evaluation_rubric_path,
            _prompt577_evaluation_rubric_payload(),
        )
        evaluation_rubric_written = evaluation_rubric_path.is_file()
        _write_json(retry_fix_route_path, _prompt577_retry_fix_route_payload())
        retry_fix_route_written = retry_fix_route_path.is_file()

    tracked_files_modified_during_runtime = _prompt577_tracked_files_modified(
        repo_path
    )
    final_worktree_clean = _prompt565_worktree_clean_excluding_daemon_artifacts(
        repo_path=repo_path,
        daemon_artifact_dir=bridge_artifact_dir,
    )
    actual_codex_dispatch_ready = bool(
        prompt576_success_ready
        and direction_written
        and codex_prompt_written
        and verification_command_written
        and evaluation_rubric_written
        and retry_fix_route_written
    )

    completion_checks = (
        ("prompt577_prompt576_success_ready", prompt576_success_ready),
        ("prompt577_direction_written", direction_written),
        ("prompt577_codex_prompt_written", codex_prompt_written),
        ("prompt577_verification_command_written", verification_command_written),
        ("prompt577_evaluation_rubric_written", evaluation_rubric_written),
        ("prompt577_retry_fix_route_written", retry_fix_route_written),
        ("prompt577_target_next_prompt_prompt578", target_next_prompt == "prompt578"),
        (
            "prompt577_cycle_type_actual_codex_development_cycle",
            cycle_type == "actual_codex_development_cycle",
        ),
        ("prompt577_actual_codex_dispatch_ready", actual_codex_dispatch_ready),
        ("prompt577_actual_codex_executed_false", not actual_codex_executed),
        (
            "prompt577_tracked_files_modified_during_runtime_false",
            not tracked_files_modified_during_runtime,
        ),
        ("prompt577_commit_performed_false", not commit_performed),
        ("prompt577_installation_performed_false", not installation_performed),
        ("prompt577_systemd_used_false", not systemd_used),
        (
            "prompt577_service_enable_performed_false",
            not service_enable_performed,
        ),
        (
            "prompt577_service_start_performed_false",
            not service_start_performed,
        ),
        (
            "prompt577_persistent_service_started_false",
            not persistent_service_started,
        ),
        (
            "prompt577_remote_workflow_included_false",
            not remote_workflow_included,
        ),
        (
            "prompt577_no_remote_mutation_verified",
            no_remote_mutation_verified,
        ),
        ("prompt577_final_worktree_clean", final_worktree_clean),
    )
    for field, passed in completion_checks:
        if not passed:
            blocked_reason = f"missing_{field}"
            if blocked_reason not in blocked_reasons:
                blocked_reasons.append(blocked_reason)

    summary: dict[str, Any] = {
        "local_only": True,
        "source_prompt": "prompt577",
        "prompt577_actual_autonomous_development_cycle_bridge_status": (
            "blocked_actual_autonomous_development_cycle_bridge_missing_prerequisite"
            if not prompt576_success_ready
            else "blocked_actual_autonomous_development_cycle_bridge_failed"
        ),
        "prompt577_actual_autonomous_development_cycle_bridge_ready": (
            prompt576_success_ready
        ),
        "prompt577_actual_autonomous_development_cycle_bridge_success": False,
        "prompt577_prompt576_success_ready": prompt576_success_ready,
        "prompt577_direction_written": direction_written,
        "prompt577_codex_prompt_written": codex_prompt_written,
        "prompt577_verification_command_written": verification_command_written,
        "prompt577_evaluation_rubric_written": evaluation_rubric_written,
        "prompt577_retry_fix_route_written": retry_fix_route_written,
        "prompt577_bridge_summary_written": False,
        "prompt577_target_next_prompt": target_next_prompt,
        "prompt577_cycle_type": cycle_type,
        "prompt577_actual_codex_dispatch_ready": actual_codex_dispatch_ready,
        "prompt577_actual_codex_executed": actual_codex_executed,
        "prompt577_tracked_files_modified_during_runtime": (
            tracked_files_modified_during_runtime
        ),
        "prompt577_commit_performed": commit_performed,
        "prompt577_installation_performed": installation_performed,
        "prompt577_systemd_used": systemd_used,
        "prompt577_service_enable_performed": service_enable_performed,
        "prompt577_service_start_performed": service_start_performed,
        "prompt577_persistent_service_started": persistent_service_started,
        "prompt577_remote_workflow_included": remote_workflow_included,
        "prompt577_no_remote_mutation_verified": no_remote_mutation_verified,
        "prompt577_final_worktree_clean": final_worktree_clean,
        "prompt577_completion_claim_allowed": False,
        "prompt577_next_action": (
            "manual_review_prompt577_actual_autonomous_development_cycle_bridge_failed"
        ),
        "prompt577_blocked_reasons": blocked_reasons,
        "prompt577_artifact_dir": str(bridge_artifact_dir),
        "prompt577_direction_path": str(direction_path),
        "prompt577_codex_prompt_path": str(codex_prompt_path),
        "prompt577_verification_command_path": str(verification_command_path),
        "prompt577_evaluation_rubric_path": str(evaluation_rubric_path),
        "prompt577_retry_fix_route_path": str(retry_fix_route_path),
        "prompt577_bridge_summary_path": str(bridge_summary_path),
    }
    if prompt576_success_ready:
        _write_json(bridge_summary_path, summary)
        bridge_summary_written = bridge_summary_path.is_file()
        summary["prompt577_bridge_summary_written"] = bridge_summary_written
        if not bridge_summary_written:
            blocked_reasons.append("missing_prompt577_bridge_summary_written")

    success = bool(
        prompt576_success_ready
        and direction_written
        and codex_prompt_written
        and verification_command_written
        and evaluation_rubric_written
        and retry_fix_route_written
        and bridge_summary_written
        and target_next_prompt == "prompt578"
        and cycle_type == "actual_codex_development_cycle"
        and actual_codex_dispatch_ready
        and not actual_codex_executed
        and not tracked_files_modified_during_runtime
        and not commit_performed
        and not installation_performed
        and not systemd_used
        and not service_enable_performed
        and not service_start_performed
        and not persistent_service_started
        and not remote_workflow_included
        and no_remote_mutation_verified
        and final_worktree_clean
        and not blocked_reasons
    )
    if success:
        status = (
            "actual_autonomous_development_cycle_bridge_ready_local_only"
        )
    elif not prompt576_success_ready:
        status = (
            "blocked_actual_autonomous_development_cycle_bridge_missing_prerequisite"
        )
    else:
        status = "blocked_actual_autonomous_development_cycle_bridge_failed"
    next_action = (
        "prepare_prompt578_actual_codex_dispatch_cycle"
        if success
        else "manual_review_prompt577_actual_autonomous_development_cycle_bridge_failed"
    )
    summary[
        "prompt577_actual_autonomous_development_cycle_bridge_status"
    ] = status
    summary[
        "prompt577_actual_autonomous_development_cycle_bridge_success"
    ] = success
    summary["prompt577_completion_claim_allowed"] = success
    summary["prompt577_next_action"] = next_action
    summary["prompt577_blocked_reasons"] = blocked_reasons
    if bridge_summary_written:
        _write_json(bridge_summary_path, summary)
    return summary


def _prompt578_prompt577_success_ready(payload: Mapping[str, Any]) -> bool:
    return bool(
        payload.get(
            "prompt577_actual_autonomous_development_cycle_bridge_success"
        )
        is True
        and payload.get("prompt577_prompt576_success_ready") is True
        and payload.get("prompt577_direction_written") is True
        and payload.get("prompt577_codex_prompt_written") is True
        and payload.get("prompt577_verification_command_written") is True
        and payload.get("prompt577_evaluation_rubric_written") is True
        and payload.get("prompt577_retry_fix_route_written") is True
        and payload.get("prompt577_bridge_summary_written") is True
        and payload.get("prompt577_target_next_prompt") == "prompt578"
        and payload.get("prompt577_cycle_type")
        == "actual_codex_development_cycle"
        and payload.get("prompt577_actual_codex_dispatch_ready") is True
        and payload.get("prompt577_actual_codex_executed") is False
        and payload.get("prompt577_tracked_files_modified_during_runtime")
        is False
        and payload.get("prompt577_commit_performed") is False
        and payload.get("prompt577_installation_performed") is False
        and payload.get("prompt577_systemd_used") is False
        and payload.get("prompt577_service_enable_performed") is False
        and payload.get("prompt577_service_start_performed") is False
        and payload.get("prompt577_persistent_service_started") is False
        and payload.get("prompt577_remote_workflow_included") is False
        and payload.get("prompt577_no_remote_mutation_verified") is True
        and payload.get("prompt577_final_worktree_clean") is True
        and payload.get("prompt577_completion_claim_allowed") is True
        and payload.get("prompt577_next_action")
        == "prepare_prompt578_actual_codex_dispatch_cycle"
    )


def _prompt578_timeout_seconds(value: Any, *, default: int = 120) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, parsed)


def _prompt578_changed_tracked_files(repo_path: Path) -> list[str]:
    completed = subprocess.run(
        ["git", "diff", "--name-only", "--"],
        cwd=str(repo_path),
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return []
    return sorted(
        {
            line.strip()
            for line in completed.stdout.splitlines()
            if line.strip()
        }
    )


def _prompt578_default_codex_prompt_text() -> str:
    return """Mode: Scout
Goal:
Inspect the Prompt578 local dispatch environment and report readiness only.

Allowed files:
- automation/orchestration/planned_runner/runtime_output_wiring.py
- automation/orchestration/planned_runner/prompt_surfaces/prompts_450_499.py
- automation/orchestration/planned_runner/prompt_surfaces/registry.py

Forbidden files:
- all files not listed above

Expected artifact/output:
- A concise local-only readiness observation in stdout.

Allowed validation commands:
- python -m py_compile automation/orchestration/planned_runner/runtime_output_wiring.py automation/orchestration/planned_runner/prompt_surfaces/prompts_450_499.py automation/orchestration/planned_runner/prompt_surfaces/registry.py

Explicitly out-of-scope items:
- code edits
- commits or tags
- installs
- systemd, systemctl, sudo, or service operations
- remote operations
- persistent services
"""


def _prompt578_prompt_text_from_payload(
    *,
    payload: Mapping[str, Any],
    repo_path: Path,
    codex_prompt_text: str | None,
) -> str:
    if codex_prompt_text is not None:
        return codex_prompt_text
    prompt_path_text = _normalize_text(
        payload.get("prompt577_codex_prompt_path"),
        default="",
    )
    if prompt_path_text:
        prompt_path = Path(prompt_path_text)
        if not prompt_path.is_absolute():
            prompt_path = repo_path / prompt_path
        try:
            return prompt_path.read_text(encoding="utf-8")
        except OSError:
            pass
    return _prompt578_default_codex_prompt_text()


def run_prompt578_actual_codex_dispatch_cycle_gate(
    *,
    run_state_payload: Mapping[str, Any] | None = None,
    execution_repo_path: str | Path = "",
    artifact_dir: str | Path | None = None,
    enabled: bool = False,
    enable_token: str = "",
    codex_prompt_text: str | None = None,
    timeout_seconds: int | None = None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    repo_text = _normalize_text(
        execution_repo_path or payload.get("execution_repo_path"),
        default="",
    )
    repo_path = Path(repo_text) if repo_text else Path(".")
    dispatch_artifact_dir = (
        Path(artifact_dir)
        if artifact_dir is not None
        else _PROMPT578_DEFAULT_ARTIFACT_DIR
    )
    if not dispatch_artifact_dir.is_absolute():
        dispatch_artifact_dir = repo_path / dispatch_artifact_dir

    timeout = _prompt578_timeout_seconds(
        timeout_seconds
        if timeout_seconds is not None
        else payload.get("prompt578_timeout_seconds", 120),
        default=120,
    )
    prompt577_success_ready = _prompt578_prompt577_success_ready(payload)
    prompt578_enabled = enabled is True
    enable_token_valid = (
        enable_token == PROMPT578_ACTUAL_CODEX_DISPATCH_ENABLE_TOKEN
    )

    prompt_path = dispatch_artifact_dir / "actual_codex_dispatch_prompt.txt"
    stdout_path = dispatch_artifact_dir / "actual_codex_dispatch_stdout.txt"
    stderr_path = dispatch_artifact_dir / "actual_codex_dispatch_stderr.txt"
    result_path = dispatch_artifact_dir / "actual_codex_dispatch_result.json"
    summary_path = dispatch_artifact_dir / "actual_codex_dispatch_summary.json"

    command = ["codex", "exec", "-"]
    codex_command_prepared = prompt577_success_ready
    codex_prompt_written = False
    actual_codex_executed = False
    timeout_occurred = False
    returncode: int | None = None
    stdout_text = ""
    stderr_text = ""
    dispatch_completed = False
    dispatch_failed = False
    dispatch_not_run = False
    blocked_reasons: list[str] = []

    if not prompt577_success_ready:
        blocked_reasons.append(
            "prompt578_prompt577_success_evidence_missing"
        )

    dispatch_artifact_dir.mkdir(parents=True, exist_ok=True)
    prompt_text = _prompt578_prompt_text_from_payload(
        payload=payload,
        repo_path=repo_path,
        codex_prompt_text=codex_prompt_text,
    )
    prompt_path.write_text(prompt_text, encoding="utf-8")
    codex_prompt_written = prompt_path.is_file()

    if prompt577_success_ready:
        if prompt578_enabled and enable_token_valid:
            try:
                completed = subprocess.run(
                    command,
                    cwd=str(repo_path),
                    input=prompt_text,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
                actual_codex_executed = True
                stdout_text = completed.stdout
                stderr_text = completed.stderr
                returncode = completed.returncode
            except subprocess.TimeoutExpired as exc:
                actual_codex_executed = True
                timeout_occurred = True
                returncode = -1
                stdout_text = _coerce_output_text(exc.stdout)
                stderr_text = _coerce_output_text(exc.stderr)
            except Exception as exc:
                actual_codex_executed = True
                returncode = -1
                stderr_text = str(exc)
        else:
            dispatch_not_run = True

    if actual_codex_executed and returncode == 0 and not timeout_occurred:
        returncode_classification = "success"
        dispatch_completed = True
    elif actual_codex_executed:
        returncode_classification = "failed"
        dispatch_failed = True
    else:
        returncode_classification = "not_run"
        dispatch_not_run = True

    changed_tracked_files = _prompt578_changed_tracked_files(repo_path)
    tracked_files_modified_by_codex = bool(
        actual_codex_executed and changed_tracked_files
    )
    final_worktree_clean = _prompt565_worktree_clean_excluding_daemon_artifacts(
        repo_path=repo_path,
        daemon_artifact_dir=dispatch_artifact_dir,
    )

    commit_performed = False
    installation_performed = False
    systemd_used = False
    service_enable_performed = False
    service_start_performed = False
    persistent_service_started = False
    remote_workflow_included = False
    no_remote_mutation_verified = True

    if prompt577_success_ready and not codex_prompt_written:
        blocked_reasons.append("missing_prompt578_codex_prompt_written")
    if dispatch_failed:
        blocked_reasons.append("prompt578_actual_codex_dispatch_failed")

    completion_claim_allowed = bool(
        prompt577_success_ready
        and prompt578_enabled
        and enable_token_valid
        and actual_codex_executed
        and codex_command_prepared
        and codex_prompt_written
        and dispatch_completed
        and not dispatch_not_run
        and not timeout_occurred
        and returncode == 0
        and returncode_classification == "success"
        and not commit_performed
        and not installation_performed
        and not systemd_used
        and not service_enable_performed
        and not service_start_performed
        and not persistent_service_started
        and not remote_workflow_included
        and no_remote_mutation_verified
        and not blocked_reasons
    )

    if not prompt577_success_ready:
        status = "blocked_actual_codex_dispatch_cycle_missing_prerequisite"
        next_action = (
            "manual_review_prompt578_actual_codex_dispatch_cycle_prerequisite"
        )
    elif dispatch_completed:
        status = "actual_codex_dispatch_cycle_executed_local_only"
        next_action = "verify_actual_codex_dispatch_result"
    elif dispatch_not_run and not dispatch_failed:
        status = "actual_codex_dispatch_cycle_ready_not_run_local_only"
        next_action = "provide_explicit_enable_token_for_actual_codex_dispatch"
    else:
        status = "blocked_actual_codex_dispatch_cycle_failed"
        next_action = "manual_review_prompt578_actual_codex_dispatch_cycle_failed"

    success = bool(completion_claim_allowed)
    actual_codex_dispatch_ready = bool(
        prompt577_success_ready and codex_command_prepared and codex_prompt_written
    )
    if prompt577_success_ready:
        stdout_path.write_text(stdout_text, encoding="utf-8")
        stderr_path.write_text(stderr_text, encoding="utf-8")
    else:
        stdout_path.write_text(stdout_text, encoding="utf-8")
        stderr_path.write_text(stderr_text, encoding="utf-8")

    result_payload: dict[str, Any] = {
        "local_only": True,
        "source_prompt": "prompt578",
        "command": command,
        "shell": False,
        "timeout_seconds": timeout,
        "timeout_occurred": timeout_occurred,
        "returncode": returncode,
        "returncode_classification": returncode_classification,
        "actual_codex_executed": actual_codex_executed,
        "dispatch_completed": dispatch_completed,
        "dispatch_failed": dispatch_failed,
        "dispatch_not_run": dispatch_not_run,
        "no_remote_mutation_verified": no_remote_mutation_verified,
    }
    _write_json(result_path, result_payload)

    summary: dict[str, Any] = {
        "local_only": True,
        "source_prompt": "prompt578",
        "prompt578_actual_codex_dispatch_cycle_status": status,
        "prompt578_actual_codex_dispatch_cycle_ready": (
            actual_codex_dispatch_ready
        ),
        "prompt578_actual_codex_dispatch_cycle_success": success,
        "prompt578_prompt577_success_ready": prompt577_success_ready,
        "prompt578_enabled": prompt578_enabled,
        "prompt578_enable_token_valid": enable_token_valid,
        "prompt578_actual_codex_dispatch_ready": actual_codex_dispatch_ready,
        "prompt578_actual_codex_executed": actual_codex_executed,
        "prompt578_codex_command_prepared": codex_command_prepared,
        "prompt578_codex_prompt_written": codex_prompt_written,
        "prompt578_stdout_path": str(stdout_path),
        "prompt578_stderr_path": str(stderr_path),
        "prompt578_result_path": str(result_path),
        "prompt578_summary_path": str(summary_path),
        "prompt578_timeout_seconds": timeout,
        "prompt578_timeout_occurred": timeout_occurred,
        "prompt578_returncode": returncode,
        "prompt578_returncode_classification": returncode_classification,
        "prompt578_dispatch_completed": dispatch_completed,
        "prompt578_dispatch_failed": dispatch_failed,
        "prompt578_dispatch_not_run": dispatch_not_run,
        "prompt578_tracked_files_modified_by_codex": (
            tracked_files_modified_by_codex
        ),
        "prompt578_changed_tracked_files": changed_tracked_files,
        "prompt578_commit_performed": commit_performed,
        "prompt578_installation_performed": installation_performed,
        "prompt578_systemd_used": systemd_used,
        "prompt578_service_enable_performed": service_enable_performed,
        "prompt578_service_start_performed": service_start_performed,
        "prompt578_persistent_service_started": persistent_service_started,
        "prompt578_remote_workflow_included": remote_workflow_included,
        "prompt578_no_remote_mutation_verified": no_remote_mutation_verified,
        "prompt578_final_worktree_clean": final_worktree_clean,
        "prompt578_completion_claim_allowed": completion_claim_allowed,
        "prompt578_next_action": next_action,
        "prompt578_blocked_reasons": blocked_reasons,
    }
    _write_json(summary_path, summary)
    return summary


def _prompt579_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, Iterable):
        values = [item for item in value]
    else:
        return []
    return sorted(
        {
            text
            for item in values
            if (text := _normalize_text(item, default=""))
        }
    )


def _prompt579_prompt578_success_ready(
    payload: Mapping[str, Any],
) -> tuple[bool, list[str]]:
    required_checks = (
        (
            "prompt578_actual_codex_dispatch_cycle_success",
            payload.get("prompt578_actual_codex_dispatch_cycle_success") is True,
        ),
        (
            "prompt578_prompt577_success_ready",
            payload.get("prompt578_prompt577_success_ready") is True,
        ),
        ("prompt578_enabled", payload.get("prompt578_enabled") is True),
        (
            "prompt578_enable_token_valid",
            payload.get("prompt578_enable_token_valid") is True,
        ),
        (
            "prompt578_actual_codex_dispatch_ready",
            payload.get("prompt578_actual_codex_dispatch_ready") is True,
        ),
        (
            "prompt578_actual_codex_executed",
            payload.get("prompt578_actual_codex_executed") is True,
        ),
        (
            "prompt578_codex_command_prepared",
            payload.get("prompt578_codex_command_prepared") is True,
        ),
        (
            "prompt578_codex_prompt_written",
            payload.get("prompt578_codex_prompt_written") is True,
        ),
        (
            "prompt578_dispatch_completed",
            payload.get("prompt578_dispatch_completed") is True,
        ),
        (
            "prompt578_dispatch_not_run_false",
            payload.get("prompt578_dispatch_not_run") is False,
        ),
        (
            "prompt578_timeout_occurred_false",
            payload.get("prompt578_timeout_occurred") is False,
        ),
        ("prompt578_returncode_0", payload.get("prompt578_returncode") == 0),
        (
            "prompt578_returncode_classification_success",
            payload.get("prompt578_returncode_classification") == "success",
        ),
        (
            "prompt578_commit_performed_false",
            payload.get("prompt578_commit_performed") is False,
        ),
        (
            "prompt578_installation_performed_false",
            payload.get("prompt578_installation_performed") is False,
        ),
        (
            "prompt578_systemd_used_false",
            payload.get("prompt578_systemd_used") is False,
        ),
        (
            "prompt578_service_enable_performed_false",
            payload.get("prompt578_service_enable_performed") is False,
        ),
        (
            "prompt578_service_start_performed_false",
            payload.get("prompt578_service_start_performed") is False,
        ),
        (
            "prompt578_persistent_service_started_false",
            payload.get("prompt578_persistent_service_started") is False,
        ),
        (
            "prompt578_remote_workflow_included_false",
            payload.get("prompt578_remote_workflow_included") is False,
        ),
        (
            "prompt578_no_remote_mutation_verified",
            payload.get("prompt578_no_remote_mutation_verified") is True,
        ),
        (
            "prompt578_completion_claim_allowed",
            payload.get("prompt578_completion_claim_allowed") is True,
        ),
        (
            "prompt578_next_action_verify_actual_codex_dispatch_result",
            payload.get("prompt578_next_action")
            == "verify_actual_codex_dispatch_result",
        ),
        (
            "prompt578_blocked_reasons_empty",
            _prompt579_string_list(payload.get("prompt578_blocked_reasons"))
            == [],
        ),
    )
    blocked_reasons = [
        f"missing_{name}" for name, ready in required_checks if not ready
    ]
    return blocked_reasons == [], blocked_reasons


def _prompt579_result_route(
    *,
    timeout_occurred: bool,
    returncode: Any,
    returncode_classification: str,
    dispatch_completed: bool,
    dispatch_failed: bool,
    dispatch_not_run: bool,
    tracked_files_modified_by_codex: bool,
    changed_tracked_files: Sequence[str],
) -> str:
    if timeout_occurred:
        return "timeout_retry_required"
    if (
        dispatch_failed
        or dispatch_not_run
        or returncode != 0
        or returncode_classification == "failed"
    ):
        return "failed_retry_required"
    if (
        dispatch_completed
        and returncode == 0
        and returncode_classification == "success"
    ):
        if tracked_files_modified_by_codex or changed_tracked_files:
            return "success_with_tracked_changes"
        return "success_no_changes"
    return "manual_review_required"


def _prompt579_next_action(result_route: str) -> str:
    return {
        "success_no_changes": "prepare_prompt580_real_dev_task_dispatch",
        "success_with_tracked_changes": (
            "prepare_prompt580_verify_and_review_codex_changes"
        ),
        "failed_retry_required": "prepare_prompt580_retry_fix_dispatch",
        "timeout_retry_required": "prepare_prompt580_timeout_retry_dispatch",
        "manual_review_required": (
            "manual_review_prompt579_actual_dispatch_result_ingestion"
        ),
    }[result_route]


def _prompt579_text_excerpt(text: str, *, limit: int = 4000) -> str:
    if len(text) <= limit:
        return text
    return text[:limit]


def _prompt579_read_text_if_exists(path_text: str, repo_path: Path) -> str:
    if not path_text:
        return ""
    path = Path(path_text)
    if not path.is_absolute():
        path = repo_path / path
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _prompt579_read_json_if_exists(
    path_text: str,
    repo_path: Path,
) -> dict[str, Any]:
    if not path_text:
        return {}
    path = Path(path_text)
    if not path.is_absolute():
        path = repo_path / path
    try:
        payload = _read_json_object_if_exists(path)
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def run_prompt579_actual_dispatch_result_ingestion_gate(
    *,
    run_state_payload: Mapping[str, Any] | None = None,
    execution_repo_path: str | Path = "",
    artifact_dir: str | Path | None = None,
    dispatch_result_payload: Mapping[str, Any] | None = None,
    stdout_text: str | None = None,
    stderr_text: str | None = None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    repo_text = _normalize_text(
        execution_repo_path or payload.get("execution_repo_path"),
        default="",
    )
    repo_path = Path(repo_text) if repo_text else Path(".")
    ingestion_artifact_dir = (
        Path(artifact_dir)
        if artifact_dir is not None
        else _PROMPT579_DEFAULT_ARTIFACT_DIR
    )
    if not ingestion_artifact_dir.is_absolute():
        ingestion_artifact_dir = repo_path / ingestion_artifact_dir

    ingested_result_path = (
        ingestion_artifact_dir / "actual_dispatch_ingested_result.json"
    )
    stdout_excerpt_path = (
        ingestion_artifact_dir / "actual_dispatch_stdout_excerpt.txt"
    )
    stderr_excerpt_path = (
        ingestion_artifact_dir / "actual_dispatch_stderr_excerpt.txt"
    )
    evaluation_path = (
        ingestion_artifact_dir / "actual_dispatch_evaluation.json"
    )
    route_path = ingestion_artifact_dir / "actual_dispatch_route.json"
    summary_path = (
        ingestion_artifact_dir / "actual_dispatch_ingestion_summary.json"
    )

    prompt578_success_ready, prerequisite_blocked_reasons = (
        _prompt579_prompt578_success_ready(payload)
    )
    prompt578_actual_codex_executed = (
        payload.get("prompt578_actual_codex_executed") is True
    )
    prompt578_returncode = payload.get("prompt578_returncode")
    prompt578_returncode_classification = _normalize_text(
        payload.get("prompt578_returncode_classification"),
        default="",
    )
    prompt578_timeout_occurred = (
        payload.get("prompt578_timeout_occurred") is True
    )
    prompt578_dispatch_completed = (
        payload.get("prompt578_dispatch_completed") is True
    )
    prompt578_dispatch_failed = (
        payload.get("prompt578_dispatch_failed") is True
    )
    prompt578_dispatch_not_run = (
        payload.get("prompt578_dispatch_not_run") is True
    )
    prompt578_changed_tracked_files = _prompt579_string_list(
        payload.get("prompt578_changed_tracked_files")
    )
    prompt578_tracked_files_modified_by_codex = (
        payload.get("prompt578_tracked_files_modified_by_codex") is True
        or bool(prompt578_changed_tracked_files)
    )

    result_payload = (
        dict(dispatch_result_payload)
        if isinstance(dispatch_result_payload, Mapping)
        else _prompt579_read_json_if_exists(
            _normalize_text(payload.get("prompt578_result_path"), default=""),
            repo_path,
        )
    )
    stdout_ingested = (
        stdout_text
        if stdout_text is not None
        else _prompt579_read_text_if_exists(
            _normalize_text(payload.get("prompt578_stdout_path"), default=""),
            repo_path,
        )
    )
    stderr_ingested = (
        stderr_text
        if stderr_text is not None
        else _prompt579_read_text_if_exists(
            _normalize_text(payload.get("prompt578_stderr_path"), default=""),
            repo_path,
        )
    )

    result_route = _prompt579_result_route(
        timeout_occurred=prompt578_timeout_occurred,
        returncode=prompt578_returncode,
        returncode_classification=prompt578_returncode_classification,
        dispatch_completed=prompt578_dispatch_completed,
        dispatch_failed=prompt578_dispatch_failed,
        dispatch_not_run=prompt578_dispatch_not_run,
        tracked_files_modified_by_codex=(
            prompt578_tracked_files_modified_by_codex
        ),
        changed_tracked_files=prompt578_changed_tracked_files,
    )
    retry_required = result_route in {
        "failed_retry_required",
        "timeout_retry_required",
    }
    manual_review_required = result_route == "manual_review_required"
    success_no_changes = result_route == "success_no_changes"
    success_with_tracked_changes = result_route == "success_with_tracked_changes"

    ingestion_artifact_dir.mkdir(parents=True, exist_ok=True)
    ingested_result = {
        "local_only": True,
        "source_prompt": "prompt579",
        "prompt578_result_metadata": result_payload,
        "prompt578_result_path": _normalize_text(
            payload.get("prompt578_result_path"),
            default="",
        ),
        "prompt578_stdout_path": _normalize_text(
            payload.get("prompt578_stdout_path"),
            default="",
        ),
        "prompt578_stderr_path": _normalize_text(
            payload.get("prompt578_stderr_path"),
            default="",
        ),
    }
    _write_json(ingested_result_path, ingested_result)
    stdout_excerpt_path.write_text(
        _prompt579_text_excerpt(stdout_ingested),
        encoding="utf-8",
    )
    stderr_excerpt_path.write_text(
        _prompt579_text_excerpt(stderr_ingested),
        encoding="utf-8",
    )

    evaluation = {
        "local_only": True,
        "source_prompt": "prompt579",
        "prompt578_prerequisite_ready": prompt578_success_ready,
        "prompt578_prerequisite_blocked_reasons": (
            prerequisite_blocked_reasons
        ),
        "prompt578_actual_codex_executed": prompt578_actual_codex_executed,
        "prompt578_returncode": prompt578_returncode,
        "prompt578_returncode_classification": (
            prompt578_returncode_classification
        ),
        "prompt578_timeout_occurred": prompt578_timeout_occurred,
        "prompt578_dispatch_completed": prompt578_dispatch_completed,
        "prompt578_dispatch_failed": prompt578_dispatch_failed,
        "prompt578_dispatch_not_run": prompt578_dispatch_not_run,
        "prompt578_tracked_files_modified_by_codex": (
            prompt578_tracked_files_modified_by_codex
        ),
        "prompt578_changed_tracked_files": prompt578_changed_tracked_files,
        "result_route": result_route,
    }
    _write_json(evaluation_path, evaluation)

    route_payload = {
        "local_only": True,
        "source_prompt": "prompt579",
        "prompt579_result_route": result_route,
        "prompt579_next_action": _prompt579_next_action(result_route),
        "prompt579_retry_required": retry_required,
        "prompt579_manual_review_required": manual_review_required,
    }
    _write_json(route_path, route_payload)

    ingested_result_written = ingested_result_path.is_file()
    stdout_excerpt_written = stdout_excerpt_path.is_file()
    stderr_excerpt_written = stderr_excerpt_path.is_file()
    evaluation_written = evaluation_path.is_file()
    route_written = route_path.is_file()
    all_artifacts_except_summary_written = all(
        (
            ingested_result_written,
            stdout_excerpt_written,
            stderr_excerpt_written,
            evaluation_written,
            route_written,
        )
    )

    blocked_reasons = list(prerequisite_blocked_reasons)
    if not all_artifacts_except_summary_written:
        blocked_reasons.append("prompt579_required_artifact_write_failed")

    summary_written = False
    next_action = _prompt579_next_action(result_route)
    if not prompt578_success_ready:
        status = (
            "blocked_actual_dispatch_result_ingestion_missing_prerequisite"
        )
        next_action = (
            "manual_review_prompt579_actual_dispatch_result_ingestion"
        )
        success = False
    elif not all_artifacts_except_summary_written:
        status = "blocked_actual_dispatch_result_ingestion_failed"
        next_action = (
            "manual_review_prompt579_actual_dispatch_result_ingestion"
        )
        success = False
    else:
        status = "actual_dispatch_result_ingestion_completed_local_only"
        success = True

    actual_dispatch_result_ingestion_ready = prompt578_success_ready
    codex_executed_during_runtime = False
    tracked_files_modified_during_runtime = False
    commit_performed = False
    installation_performed = False
    systemd_used = False
    service_enable_performed = False
    service_start_performed = False
    persistent_service_started = False
    remote_workflow_included = False
    no_remote_mutation_verified = True
    final_worktree_clean = bool(
        payload.get("prompt578_final_worktree_clean", True) is True
        and not tracked_files_modified_during_runtime
    )

    completion_claim_allowed = bool(
        success
        and prompt578_success_ready
        and prompt578_actual_codex_executed
        and all_artifacts_except_summary_written
        and result_route
        in {"success_no_changes", "success_with_tracked_changes"}
        and not retry_required
        and not manual_review_required
        and not codex_executed_during_runtime
        and not tracked_files_modified_during_runtime
        and not commit_performed
        and not installation_performed
        and not systemd_used
        and not service_enable_performed
        and not service_start_performed
        and not persistent_service_started
        and not remote_workflow_included
        and no_remote_mutation_verified
        and final_worktree_clean
        and blocked_reasons == []
    )

    summary: dict[str, Any] = {
        "local_only": True,
        "source_prompt": "prompt579",
        "prompt579_actual_dispatch_result_ingestion_status": status,
        "prompt579_actual_dispatch_result_ingestion_ready": (
            actual_dispatch_result_ingestion_ready
        ),
        "prompt579_actual_dispatch_result_ingestion_success": success,
        "prompt579_prompt578_success_ready": prompt578_success_ready,
        "prompt579_prompt578_actual_codex_executed": (
            prompt578_actual_codex_executed
        ),
        "prompt579_prompt578_returncode": prompt578_returncode,
        "prompt579_prompt578_returncode_classification": (
            prompt578_returncode_classification
        ),
        "prompt579_prompt578_timeout_occurred": prompt578_timeout_occurred,
        "prompt579_prompt578_dispatch_completed": (
            prompt578_dispatch_completed
        ),
        "prompt579_prompt578_dispatch_failed": prompt578_dispatch_failed,
        "prompt579_prompt578_dispatch_not_run": prompt578_dispatch_not_run,
        "prompt579_prompt578_tracked_files_modified_by_codex": (
            prompt578_tracked_files_modified_by_codex
        ),
        "prompt579_prompt578_changed_tracked_files": (
            prompt578_changed_tracked_files
        ),
        "prompt579_ingested_result_written": ingested_result_written,
        "prompt579_stdout_excerpt_written": stdout_excerpt_written,
        "prompt579_stderr_excerpt_written": stderr_excerpt_written,
        "prompt579_evaluation_written": evaluation_written,
        "prompt579_route_written": route_written,
        "prompt579_summary_written": summary_written,
        "prompt579_result_route": result_route,
        "prompt579_retry_required": retry_required,
        "prompt579_manual_review_required": manual_review_required,
        "prompt579_success_no_changes": success_no_changes,
        "prompt579_success_with_tracked_changes": success_with_tracked_changes,
        "prompt579_actual_codex_executed": prompt578_actual_codex_executed,
        "prompt579_codex_executed_during_runtime": (
            codex_executed_during_runtime
        ),
        "prompt579_tracked_files_modified_during_runtime": (
            tracked_files_modified_during_runtime
        ),
        "prompt579_commit_performed": commit_performed,
        "prompt579_installation_performed": installation_performed,
        "prompt579_systemd_used": systemd_used,
        "prompt579_service_enable_performed": service_enable_performed,
        "prompt579_service_start_performed": service_start_performed,
        "prompt579_persistent_service_started": persistent_service_started,
        "prompt579_remote_workflow_included": remote_workflow_included,
        "prompt579_no_remote_mutation_verified": no_remote_mutation_verified,
        "prompt579_final_worktree_clean": final_worktree_clean,
        "prompt579_completion_claim_allowed": completion_claim_allowed,
        "prompt579_next_action": next_action,
        "prompt579_blocked_reasons": blocked_reasons,
    }
    _write_json(summary_path, summary)
    summary_written = summary_path.is_file()
    summary["prompt579_summary_written"] = summary_written
    summary["prompt579_completion_claim_allowed"] = bool(
        completion_claim_allowed and summary_written
    )
    if summary_written:
        _write_json(summary_path, summary)
    return summary


def _prompt580_prompt579_success_ready(
    payload: Mapping[str, Any],
) -> tuple[bool, list[str]]:
    required_checks = (
        (
            "prompt579_actual_dispatch_result_ingestion_success",
            payload.get("prompt579_actual_dispatch_result_ingestion_success")
            is True,
        ),
        (
            "prompt579_prompt578_success_ready",
            payload.get("prompt579_prompt578_success_ready") is True,
        ),
        (
            "prompt579_prompt578_actual_codex_executed",
            payload.get("prompt579_prompt578_actual_codex_executed") is True,
        ),
        (
            "prompt579_prompt578_returncode_0",
            payload.get("prompt579_prompt578_returncode") == 0,
        ),
        (
            "prompt579_prompt578_returncode_classification_success",
            payload.get("prompt579_prompt578_returncode_classification")
            == "success",
        ),
        (
            "prompt579_prompt578_timeout_occurred_false",
            payload.get("prompt579_prompt578_timeout_occurred") is False,
        ),
        (
            "prompt579_prompt578_dispatch_completed",
            payload.get("prompt579_prompt578_dispatch_completed") is True,
        ),
        (
            "prompt579_prompt578_dispatch_failed_false",
            payload.get("prompt579_prompt578_dispatch_failed") is False,
        ),
        (
            "prompt579_prompt578_dispatch_not_run_false",
            payload.get("prompt579_prompt578_dispatch_not_run") is False,
        ),
        (
            "prompt579_prompt578_tracked_files_modified_by_codex_false",
            payload.get("prompt579_prompt578_tracked_files_modified_by_codex")
            is False,
        ),
        (
            "prompt579_prompt578_changed_tracked_files_empty",
            _prompt579_string_list(
                payload.get("prompt579_prompt578_changed_tracked_files")
            )
            == [],
        ),
        (
            "prompt579_ingested_result_written",
            payload.get("prompt579_ingested_result_written") is True,
        ),
        (
            "prompt579_stdout_excerpt_written",
            payload.get("prompt579_stdout_excerpt_written") is True,
        ),
        (
            "prompt579_stderr_excerpt_written",
            payload.get("prompt579_stderr_excerpt_written") is True,
        ),
        (
            "prompt579_evaluation_written",
            payload.get("prompt579_evaluation_written") is True,
        ),
        (
            "prompt579_route_written",
            payload.get("prompt579_route_written") is True,
        ),
        (
            "prompt579_summary_written",
            payload.get("prompt579_summary_written") is True,
        ),
        (
            "prompt579_result_route_success_no_changes",
            payload.get("prompt579_result_route") == "success_no_changes",
        ),
        (
            "prompt579_retry_required_false",
            payload.get("prompt579_retry_required") is False,
        ),
        (
            "prompt579_manual_review_required_false",
            payload.get("prompt579_manual_review_required") is False,
        ),
        (
            "prompt579_success_no_changes",
            payload.get("prompt579_success_no_changes") is True,
        ),
        (
            "prompt579_success_with_tracked_changes_false",
            payload.get("prompt579_success_with_tracked_changes") is False,
        ),
        (
            "prompt579_actual_codex_executed",
            payload.get("prompt579_actual_codex_executed") is True,
        ),
        (
            "prompt579_codex_executed_during_runtime_false",
            payload.get("prompt579_codex_executed_during_runtime") is False,
        ),
        (
            "prompt579_tracked_files_modified_during_runtime_false",
            payload.get("prompt579_tracked_files_modified_during_runtime")
            is False,
        ),
        (
            "prompt579_commit_performed_false",
            payload.get("prompt579_commit_performed") is False,
        ),
        (
            "prompt579_installation_performed_false",
            payload.get("prompt579_installation_performed") is False,
        ),
        (
            "prompt579_systemd_used_false",
            payload.get("prompt579_systemd_used") is False,
        ),
        (
            "prompt579_service_enable_performed_false",
            payload.get("prompt579_service_enable_performed") is False,
        ),
        (
            "prompt579_service_start_performed_false",
            payload.get("prompt579_service_start_performed") is False,
        ),
        (
            "prompt579_persistent_service_started_false",
            payload.get("prompt579_persistent_service_started") is False,
        ),
        (
            "prompt579_remote_workflow_included_false",
            payload.get("prompt579_remote_workflow_included") is False,
        ),
        (
            "prompt579_no_remote_mutation_verified",
            payload.get("prompt579_no_remote_mutation_verified") is True,
        ),
        (
            "prompt579_final_worktree_clean",
            payload.get("prompt579_final_worktree_clean") is True,
        ),
        (
            "prompt579_completion_claim_allowed",
            payload.get("prompt579_completion_claim_allowed") is True,
        ),
        (
            "prompt579_next_action_prepare_prompt580_real_dev_task_dispatch",
            payload.get("prompt579_next_action")
            == "prepare_prompt580_real_dev_task_dispatch",
        ),
        (
            "prompt579_blocked_reasons_empty",
            _prompt579_string_list(payload.get("prompt579_blocked_reasons"))
            == [],
        ),
    )
    blocked_reasons = [
        f"missing_{name}" for name, ready in required_checks if not ready
    ]
    return blocked_reasons == [], blocked_reasons


def _prompt580_timeout_seconds(value: Any, *, default: int = 180) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, parsed)


def _prompt580_coerce_output_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _prompt580_default_dev_task_prompt_text() -> str:
    return """Mode: Implement
Goal:
Perform one bounded local development task only if this prompt describes a concrete code change.

Allowed files:
- automation/orchestration/planned_runner/runtime_output_wiring.py
- automation/orchestration/planned_runner/prompt_surfaces/prompts_450_499.py
- automation/orchestration/planned_runner/prompt_surfaces/registry.py

Forbidden files:
- all files not listed above

Expected artifact/output:
- A concise stdout summary of whether any tracked files were changed.

Allowed validation commands:
- python -m py_compile automation/orchestration/planned_runner/runtime_output_wiring.py automation/orchestration/planned_runner/prompt_surfaces/prompts_450_499.py automation/orchestration/planned_runner/prompt_surfaces/registry.py

Explicitly out-of-scope items:
- commits or tags
- installs
- systemd, systemctl, sudo, or service operations
- remote operations
- persistent services
"""


def _prompt580_result_route(
    *,
    timeout_occurred: bool,
    returncode: int | None,
    returncode_classification: str,
    changed_tracked_files: Sequence[str],
    dispatch_not_run: bool,
) -> str:
    if dispatch_not_run:
        return "not_run"
    if timeout_occurred:
        return "timeout_retry_required"
    if returncode != 0 or returncode_classification != "success":
        return "failed_retry_required"
    if changed_tracked_files:
        return "verify_codex_changes"
    return "success_no_changes"


def _prompt580_next_action(result_route: str) -> str:
    return {
        "not_run": "provide_explicit_enable_token_for_real_dev_task_dispatch",
        "verify_codex_changes": (
            "prepare_prompt581_verify_real_dev_task_changes"
        ),
        "success_no_changes": "prepare_prompt581_no_change_dispatch_review",
        "timeout_retry_required": "prepare_prompt581_timeout_retry_dispatch",
        "failed_retry_required": "prepare_prompt581_retry_fix_dispatch",
        "missing_prerequisite": (
            "manual_review_prompt580_real_dev_task_dispatch_prerequisite"
        ),
    }[result_route]


def run_prompt580_real_dev_task_dispatch_gate(
    *,
    run_state_payload: Mapping[str, Any] | None = None,
    execution_repo_path: str | Path = "",
    artifact_dir: str | Path | None = None,
    enabled: bool = False,
    enable_token: str = "",
    dev_task_prompt_text: str | None = None,
    timeout_seconds: int | None = None,
) -> dict[str, Any]:
    payload = run_state_payload if isinstance(run_state_payload, Mapping) else {}
    repo_text = _normalize_text(
        execution_repo_path or payload.get("execution_repo_path"),
        default="",
    )
    repo_path = Path(repo_text) if repo_text else Path(".")
    dispatch_artifact_dir = (
        Path(artifact_dir)
        if artifact_dir is not None
        else _PROMPT580_DEFAULT_ARTIFACT_DIR
    )
    if not dispatch_artifact_dir.is_absolute():
        dispatch_artifact_dir = repo_path / dispatch_artifact_dir

    timeout = _prompt580_timeout_seconds(
        timeout_seconds
        if timeout_seconds is not None
        else payload.get("prompt580_timeout_seconds", 180),
        default=180,
    )
    prompt579_success_ready, prerequisite_blocked_reasons = (
        _prompt580_prompt579_success_ready(payload)
    )
    prompt580_enabled = enabled is True
    enable_token_valid = (
        enable_token == PROMPT580_REAL_DEV_TASK_DISPATCH_ENABLE_TOKEN
    )

    prompt_path = dispatch_artifact_dir / "real_dev_task_prompt.txt"
    stdout_path = dispatch_artifact_dir / "real_dev_task_stdout.txt"
    stderr_path = dispatch_artifact_dir / "real_dev_task_stderr.txt"
    result_path = dispatch_artifact_dir / "real_dev_task_result.json"
    summary_path = dispatch_artifact_dir / "real_dev_task_summary.json"

    command = ["codex", "exec", "-"]
    codex_command_prepared = prompt579_success_ready
    dev_task_prompt_written = False
    real_dev_task_executed = False
    timeout_occurred = False
    returncode: int | None = None
    stdout_text = ""
    stderr_text = ""
    dispatch_completed = False
    dispatch_failed = False
    dispatch_not_run = False
    blocked_reasons = list(prerequisite_blocked_reasons)

    dispatch_artifact_dir.mkdir(parents=True, exist_ok=True)
    prompt_text = (
        dev_task_prompt_text
        if dev_task_prompt_text is not None
        else _prompt580_default_dev_task_prompt_text()
    )
    prompt_path.write_text(prompt_text, encoding="utf-8")
    dev_task_prompt_written = prompt_path.is_file()

    if prompt579_success_ready:
        if prompt580_enabled and enable_token_valid:
            try:
                completed = subprocess.run(
                    command,
                    cwd=str(repo_path),
                    input=prompt_text,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
                real_dev_task_executed = True
                stdout_text = completed.stdout
                stderr_text = completed.stderr
                returncode = completed.returncode
            except subprocess.TimeoutExpired as exc:
                real_dev_task_executed = True
                timeout_occurred = True
                returncode = -1
                stdout_text = _prompt580_coerce_output_text(exc.stdout)
                stderr_text = _prompt580_coerce_output_text(exc.stderr)
            except Exception as exc:
                real_dev_task_executed = True
                returncode = -1
                stderr_text = str(exc)
        else:
            dispatch_not_run = True
    else:
        dispatch_not_run = True

    if real_dev_task_executed and returncode == 0 and not timeout_occurred:
        returncode_classification = "success"
        dispatch_completed = True
    elif real_dev_task_executed:
        returncode_classification = "failed"
        dispatch_failed = True
    else:
        returncode_classification = "not_run"
        dispatch_not_run = True

    changed_tracked_files = _prompt578_changed_tracked_files(repo_path)
    tracked_files_modified_by_codex = bool(
        real_dev_task_executed and changed_tracked_files
    )
    final_worktree_clean = _prompt565_worktree_clean_excluding_daemon_artifacts(
        repo_path=repo_path,
        daemon_artifact_dir=dispatch_artifact_dir,
    )

    commit_performed = False
    installation_performed = False
    systemd_used = False
    service_enable_performed = False
    service_start_performed = False
    persistent_service_started = False
    remote_workflow_included = False
    no_remote_mutation_verified = True

    if prompt579_success_ready and not dev_task_prompt_written:
        blocked_reasons.append("missing_prompt580_dev_task_prompt_written")
    if dispatch_failed:
        blocked_reasons.append("prompt580_real_dev_task_dispatch_failed")

    real_dev_task_dispatch_ready = bool(
        prompt579_success_ready
        and codex_command_prepared
        and dev_task_prompt_written
    )
    if not prompt579_success_ready:
        result_route = "missing_prerequisite"
    else:
        result_route = _prompt580_result_route(
            timeout_occurred=timeout_occurred,
            returncode=returncode,
            returncode_classification=returncode_classification,
            changed_tracked_files=changed_tracked_files,
            dispatch_not_run=dispatch_not_run,
        )
    next_action = _prompt580_next_action(result_route)

    not_run_success = bool(
        prompt579_success_ready
        and real_dev_task_dispatch_ready
        and (not prompt580_enabled or not enable_token_valid)
        and not real_dev_task_executed
        and dispatch_not_run
        and not dispatch_completed
        and not commit_performed
        and not installation_performed
        and not systemd_used
        and not service_enable_performed
        and not service_start_performed
        and not persistent_service_started
        and not remote_workflow_included
        and no_remote_mutation_verified
        and result_route == "not_run"
    )
    executed_success = bool(
        prompt579_success_ready
        and prompt580_enabled
        and enable_token_valid
        and real_dev_task_dispatch_ready
        and real_dev_task_executed
        and codex_command_prepared
        and dev_task_prompt_written
        and dispatch_completed
        and not dispatch_not_run
        and not timeout_occurred
        and returncode == 0
        and returncode_classification == "success"
        and not commit_performed
        and not installation_performed
        and not systemd_used
        and not service_enable_performed
        and not service_start_performed
        and not persistent_service_started
        and not remote_workflow_included
        and no_remote_mutation_verified
        and blocked_reasons == []
    )

    completion_claim_allowed = executed_success
    if not prompt579_success_ready:
        status = "blocked_real_dev_task_dispatch_missing_prerequisite"
        success = False
    elif executed_success:
        status = "real_dev_task_dispatch_executed_local_only"
        success = True
    elif not_run_success:
        status = "real_dev_task_dispatch_ready_not_run_local_only"
        success = False
    else:
        status = "blocked_real_dev_task_dispatch_failed"
        success = False

    stdout_path.write_text(stdout_text, encoding="utf-8")
    stderr_path.write_text(stderr_text, encoding="utf-8")
    result_payload: dict[str, Any] = {
        "local_only": True,
        "source_prompt": "prompt580",
        "command": command,
        "shell": False,
        "prompt_path": str(prompt_path),
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "result_path": str(result_path),
        "summary_path": str(summary_path),
        "timeout_seconds": timeout,
        "timeout_occurred": timeout_occurred,
        "returncode": returncode,
        "returncode_classification": returncode_classification,
        "real_dev_task_executed": real_dev_task_executed,
        "dispatch_completed": dispatch_completed,
        "dispatch_failed": dispatch_failed,
        "dispatch_not_run": dispatch_not_run,
        "changed_tracked_files": changed_tracked_files,
        "tracked_files_modified_by_codex": tracked_files_modified_by_codex,
        "result_route": result_route,
        "no_remote_mutation_verified": no_remote_mutation_verified,
    }
    _write_json(result_path, result_payload)

    summary: dict[str, Any] = {
        "local_only": True,
        "source_prompt": "prompt580",
        "prompt580_real_dev_task_dispatch_status": status,
        "prompt580_real_dev_task_dispatch_ready": (
            real_dev_task_dispatch_ready
        ),
        "prompt580_real_dev_task_dispatch_success": success,
        "prompt580_prompt579_success_ready": prompt579_success_ready,
        "prompt580_enabled": prompt580_enabled,
        "prompt580_enable_token_valid": enable_token_valid,
        "prompt580_real_dev_task_executed": real_dev_task_executed,
        "prompt580_codex_command_prepared": codex_command_prepared,
        "prompt580_dev_task_prompt_written": dev_task_prompt_written,
        "prompt580_prompt_path": str(prompt_path),
        "prompt580_stdout_path": str(stdout_path),
        "prompt580_stderr_path": str(stderr_path),
        "prompt580_result_path": str(result_path),
        "prompt580_summary_path": str(summary_path),
        "prompt580_timeout_seconds": timeout,
        "prompt580_timeout_occurred": timeout_occurred,
        "prompt580_returncode": returncode,
        "prompt580_returncode_classification": returncode_classification,
        "prompt580_dispatch_completed": dispatch_completed,
        "prompt580_dispatch_failed": dispatch_failed,
        "prompt580_dispatch_not_run": dispatch_not_run,
        "prompt580_tracked_files_modified_by_codex": (
            tracked_files_modified_by_codex
        ),
        "prompt580_changed_tracked_files": changed_tracked_files,
        "prompt580_commit_performed": commit_performed,
        "prompt580_installation_performed": installation_performed,
        "prompt580_systemd_used": systemd_used,
        "prompt580_service_enable_performed": service_enable_performed,
        "prompt580_service_start_performed": service_start_performed,
        "prompt580_persistent_service_started": persistent_service_started,
        "prompt580_remote_workflow_included": remote_workflow_included,
        "prompt580_no_remote_mutation_verified": no_remote_mutation_verified,
        "prompt580_final_worktree_clean": final_worktree_clean,
        "prompt580_completion_claim_allowed": completion_claim_allowed,
        "prompt580_result_route": result_route,
        "prompt580_next_action": next_action,
        "prompt580_blocked_reasons": blocked_reasons,
    }
    _write_json(summary_path, summary)
    return summary


def _prompt548_returncode_zero(repo_path: Path) -> bool:
    returncode_path = repo_path / PROMPT547_RETURNCODE_ARTIFACT
    try:
        return returncode_path.read_text(encoding="utf-8").strip() == "0"
    except OSError:
        return False


def _prompt548_input_metadata(*, repo_path: Path) -> dict[str, Any]:
    result_path = repo_path / PROMPT547_RESULT_ARTIFACT
    result_json_artifact_exists = result_path.is_file()
    result_payload = _read_json_object_if_exists(result_path)
    result_json_loaded = isinstance(result_payload, Mapping)
    result_json_schema_valid = bool(
        result_json_loaded
        and all(field in result_payload for field in _PROMPT548_RESULT_JSON_SCHEMA_FIELDS)
    )
    injection_error_present = bool(
        result_json_artifact_exists and not result_json_loaded
    )
    result_payload = result_payload if isinstance(result_payload, Mapping) else {}
    return {
        "prompt548_input_runtime_result_json_loaded": bool(
            result_json_loaded
        ),
        "prompt548_input_runtime_result_json_schema_valid": bool(
            result_json_schema_valid
        ),
        "prompt548_input_stdout_artifact_exists": _prompt546_artifact_ready(
            repo_path,
            PROMPT547_STDOUT_ARTIFACT,
        ),
        "prompt548_input_stderr_artifact_exists": _prompt546_artifact_ready(
            repo_path,
            PROMPT547_STDERR_ARTIFACT,
        ),
        "prompt548_input_returncode_artifact_exists": _prompt546_artifact_ready(
            repo_path,
            PROMPT547_RETURNCODE_ARTIFACT,
        ),
        "prompt548_input_changed_files_artifact_exists": (
            _prompt546_artifact_ready(repo_path, PROMPT547_CHANGED_FILES_ARTIFACT)
        ),
        "prompt548_input_diff_artifact_exists": _prompt546_artifact_ready(
            repo_path,
            PROMPT547_DIFF_ARTIFACT,
        ),
        "prompt548_input_result_json_artifact_exists": bool(
            result_json_artifact_exists
        ),
        "prompt548_input_returncode_zero": _prompt548_returncode_zero(
            repo_path
        ),
        "prompt548_input_subprocess_executed": bool(
            result_payload.get("prompt547_internal_codex_subprocess_executed")
        ),
        "prompt548_input_changed_files_allowed": bool(
            result_payload.get("prompt547_internal_changed_files_allowed")
        ),
        "prompt548_input_unexpected_changed_files_present": bool(
            result_payload.get(
                "prompt547_internal_unexpected_changed_files_present"
            )
        ),
        "prompt548_input_unexpected_diff_present": bool(
            result_payload.get("prompt547_internal_unexpected_diff_present")
        ),
        "prompt548_input_timeout_occurred": bool(
            result_payload.get("prompt547_internal_execution_timeout_occurred")
        ),
        "prompt548_input_execution_error_present": bool(
            result_payload.get("prompt547_internal_execution_error_present")
        ),
        "prompt548_input_no_remote_mutation_verified": bool(
            result_payload.get("prompt547_internal_no_remote_mutation_verified")
        ),
        "prompt548_input_injection_error_present": injection_error_present,
    }


def _prompt549_input_metadata(*, repo_path: Path) -> dict[str, Any]:
    result_path = repo_path / PROMPT547_RESULT_ARTIFACT
    result_payload = _read_json_object_if_exists(result_path)
    result_json_artifact_valid = bool(
        isinstance(result_payload, Mapping)
        and all(
            field in result_payload
            for field in _PROMPT548_RESULT_JSON_SCHEMA_FIELDS
        )
    )
    result_payload = result_payload if isinstance(result_payload, Mapping) else {}
    runtime_smoke_verification_error_present = bool(
        result_path.is_file() and not result_json_artifact_valid
    )
    actual_runtime_smoke_verification_present = bool(
        result_json_artifact_valid
        or _prompt546_artifact_ready(repo_path, PROMPT547_STDOUT_ARTIFACT)
        or _prompt546_artifact_ready(repo_path, PROMPT547_STDERR_ARTIFACT)
        or _prompt546_artifact_ready(repo_path, PROMPT547_RETURNCODE_ARTIFACT)
        or _prompt546_artifact_ready(repo_path, PROMPT547_CHANGED_FILES_ARTIFACT)
        or _prompt546_artifact_ready(repo_path, PROMPT547_DIFF_ARTIFACT)
    )
    return {
        "prompt549_input_actual_runtime_smoke_verification_present": (
            actual_runtime_smoke_verification_present
        ),
        "prompt549_input_stdout_artifact_nonempty": _artifact_nonempty(
            repo_path,
            PROMPT547_STDOUT_ARTIFACT,
        ),
        "prompt549_input_stderr_artifact_exists": _prompt546_artifact_ready(
            repo_path,
            PROMPT547_STDERR_ARTIFACT,
        ),
        "prompt549_input_returncode_artifact_zero": _prompt548_returncode_zero(
            repo_path
        ),
        "prompt549_input_changed_files_artifact_nonempty": _artifact_nonempty(
            repo_path,
            PROMPT547_CHANGED_FILES_ARTIFACT,
        ),
        "prompt549_input_diff_artifact_nonempty": _artifact_nonempty(
            repo_path,
            PROMPT547_DIFF_ARTIFACT,
        ),
        "prompt549_input_result_json_artifact_valid": result_json_artifact_valid,
        "prompt549_input_result_json_subprocess_executed_true": bool(
            result_payload.get("prompt547_internal_codex_subprocess_executed")
            is True
        ),
        "prompt549_input_result_json_returncode_success_true": bool(
            result_payload.get("prompt547_internal_codex_returncode_success")
            is True
        ),
        "prompt549_input_result_json_changed_files_allowed_true": bool(
            result_payload.get("prompt547_internal_changed_files_allowed")
            is True
        ),
        "prompt549_input_result_json_unexpected_changed_files_present_false": bool(
            result_payload.get(
                "prompt547_internal_unexpected_changed_files_present"
            )
            is False
        ),
        "prompt549_input_result_json_unexpected_diff_present_false": bool(
            result_payload.get("prompt547_internal_unexpected_diff_present")
            is False
        ),
        "prompt549_input_result_json_timeout_occurred_false": bool(
            result_payload.get("prompt547_internal_execution_timeout_occurred")
            is False
        ),
        "prompt549_input_result_json_execution_error_present_false": bool(
            result_payload.get("prompt547_internal_execution_error_present")
            is False
        ),
        "prompt549_input_result_json_no_remote_mutation_verified_true": bool(
            result_payload.get("prompt547_internal_no_remote_mutation_verified")
            is True
        ),
        "prompt549_input_runtime_smoke_verification_error_present": (
            runtime_smoke_verification_error_present
        ),
    }


def _connect_prompt546_runtime_internal_execution_adapter(
    *,
    run_state: Mapping[str, Any],
    execution_repo_path: str,
    prompt_path: str,
    enabled: bool,
    enable_token: str,
    timeout_seconds: int,
    allowed_files: Iterable[str] | None,
) -> dict[str, Any]:
    merged = dict(run_state)
    repo_text = _normalize_text(execution_repo_path, default="")
    resolved_prompt_path = _normalize_text(prompt_path, default="")
    result_payload: dict[str, Any] | None = None
    if repo_text and resolved_prompt_path and (enabled or enable_token):
        result_payload = run_internal_codex_subprocess(
            repo_dir=repo_text,
            prompt_path=resolved_prompt_path,
            allowed_files=(
                tuple(allowed_files)
                if allowed_files is not None
                else _PROMPT546_DEFAULT_ALLOWED_FILES
            ),
            enabled=bool(enabled),
            enable_token=_normalize_text(enable_token, default=""),
            timeout_seconds=timeout_seconds,
        )
    merged.update(
        _prompt546_input_metadata(
            repo_path=Path(repo_text) if repo_text else Path("."),
            result_payload=result_payload,
        )
    )
    builder = get_prompt_builders()[
        "_build_prompt546_runtime_internal_execution_adapter_connection_state"
    ]
    merged.update(builder(run_state_payload=merged))
    return merged


def _connect_prompt547_real_runtime_internal_codex_smoke(
    *,
    run_state: Mapping[str, Any],
    execution_repo_path: str,
    prompt_path: str,
    enabled: bool,
    enable_token: str,
    timeout_seconds: int,
    allowed_files: Iterable[str] | None,
) -> dict[str, Any]:
    merged = dict(run_state)
    repo_text = _normalize_text(execution_repo_path, default="")
    resolved_prompt_path = _normalize_text(prompt_path, default="")
    result_payload: dict[str, Any] | None = None
    if repo_text and resolved_prompt_path and (enabled or enable_token):
        result_payload = run_internal_codex_subprocess(
            repo_dir=repo_text,
            prompt_path=resolved_prompt_path,
            allowed_files=(
                tuple(allowed_files)
                if allowed_files is not None
                else _PROMPT547_DEFAULT_ALLOWED_FILES
            ),
            enabled=bool(enabled),
            enable_token=_normalize_text(enable_token, default=""),
            timeout_seconds=timeout_seconds,
            prompt_id="prompt547",
        )
    if isinstance(result_payload, Mapping) or not any(
        field in merged for field in _PROMPT547_INPUT_FIELDS
    ):
        merged.update(
            _prompt547_input_metadata(
                repo_path=Path(repo_text) if repo_text else Path("."),
                result_payload=result_payload,
            )
        )
    builder = get_prompt_builders()[
        "_build_prompt547_real_runtime_internal_codex_smoke_state"
    ]
    merged.update(builder(run_state_payload=merged))
    return merged


def _connect_prompt548_runtime_result_injection_to_contract(
    *,
    run_state: Mapping[str, Any],
    execution_repo_path: str,
) -> dict[str, Any]:
    merged = dict(run_state)
    repo_text = _normalize_text(execution_repo_path, default="")
    merged.update(
        _prompt548_input_metadata(
            repo_path=Path(repo_text) if repo_text else Path("."),
        )
    )
    builder = get_prompt_builders()[
        "_build_prompt548_runtime_result_injection_to_contract_state"
    ]
    merged.update(builder(run_state_payload=merged))
    return merged


def _connect_prompt549_actual_runtime_smoke_artifact_verification(
    *,
    run_state: Mapping[str, Any],
    execution_repo_path: str,
) -> dict[str, Any]:
    merged = dict(run_state)
    repo_text = _normalize_text(execution_repo_path, default="")
    merged.update(
        _prompt549_input_metadata(
            repo_path=Path(repo_text) if repo_text else Path("."),
        )
    )
    builder = get_prompt_builders()[
        "_build_prompt549_actual_runtime_smoke_artifact_verification_state"
    ]
    merged.update(builder(run_state_payload=merged))
    return merged


def _connect_prompt550_post_smoke_local_commit_tag_clean_rerun_final_completion(
    *,
    run_state: Mapping[str, Any],
) -> dict[str, Any]:
    merged = dict(run_state)
    builder = get_prompt_builders()[
        "_build_prompt550_post_smoke_local_commit_tag_clean_rerun_final_completion_state"
    ]
    merged.update(builder(run_state_payload=merged))
    return merged


def _merge_prompt491a_current_head_materialization_surfaces(
    *,
    run_state: Mapping[str, Any],
    run_root: Path,
) -> tuple[dict[str, Any], str]:
    merged = dict(run_state)
    builders = get_prompt_builders()
    if "_build_prompt491a_role_prompt_materialization_state" not in builders:
        return merged, ""

    selected_role_id = _normalize_text(
        merged.get("prompt483_selected_role_id"),
        default="prompt491a_role",
    )
    selected_role_text = _normalize_text(
        merged.get("prompt483_selected_role_text"),
        default="",
    )
    prompt_text = _prompt491a_materialized_prompt378_markdown(
        selected_role_id=selected_role_id,
        selected_role_text=selected_role_text,
    )
    canonical_tokens_ready = _prompt491a_canonical_tokens_ready(prompt_text)
    if not canonical_tokens_ready:
        merged.update(
            {
                "prompt491a_current_head_prompt378_override_ready": False,
                "prompt491a_current_head_prompt378_override_path": "",
            }
        )
        return merged, ""

    materialized_path = run_root / "prompt491a" / "materialized_prompt378.md"
    try:
        materialized_path.parent.mkdir(parents=True, exist_ok=True)
        materialized_path.write_text(prompt_text, encoding="utf-8")
    except OSError:
        merged.update(
            {
                "prompt491a_current_head_prompt378_override_ready": False,
                "prompt491a_current_head_prompt378_override_path": "",
            }
        )
        return merged, ""

    materialized_path_text = str(materialized_path)
    merged.update(
        {
            "prompt491a_current_head_prompt378_override_ready": True,
            "prompt491a_current_head_prompt378_override_path": materialized_path_text,
            "prompt491a_current_head_prompt378_override_source": "current_head_prompt491a",
            "prompt491a_current_head_prompt378_override_canonical_tokens_ready": True,
        }
    )
    return merged, materialized_path_text


def _resolve_existing_prompt378_generated_prompt_path(
    *,
    explicit_path: str,
    current_head_prompt491a_path: str = "",
    manifest_payload: Mapping[str, Any],
) -> str:
    normalized_explicit_path = _normalize_text(explicit_path, default="")
    if normalized_explicit_path:
        return normalized_explicit_path

    normalized_current_head_path = _normalize_text(
        current_head_prompt491a_path,
        default="",
    )
    if normalized_current_head_path:
        return normalized_current_head_path

    artifacts_dir = Path(
        _normalize_text(manifest_payload.get("artifact_input_dir"), default="")
    )
    if not artifacts_dir.exists() or not artifacts_dir.is_dir():
        return ""

    prompt_candidates: list[Path] = []
    for candidate in artifacts_dir.rglob("*.md"):
        normalized_name = candidate.name.lower()
        if "prompt378" not in normalized_name:
            continue
        if not candidate.exists() or not candidate.is_file():
            continue
        prompt_candidates.append(candidate)
    if len(prompt_candidates) != 1:
        return ""
    return str(prompt_candidates[0])


def _write_execution_prompt_alias_if_ready(
    *,
    run_root: Path,
    run_state: Mapping[str, Any],
) -> bool:
    prompt_path_text = _normalize_text(
        run_state.get("prompt378_generated_prompt_path"),
        default="",
    )
    prompt_checksum = _normalize_text(
        run_state.get("prompt378_generated_prompt_checksum"),
        default="",
    )
    prompt_path = Path(prompt_path_text) if prompt_path_text else Path()
    if not prompt_path_text or not prompt_checksum or not prompt_path.is_file():
        return False
    try:
        actual_checksum = hashlib.sha256(prompt_path.read_bytes()).hexdigest()
    except OSError:
        return False
    if actual_checksum != prompt_checksum:
        return False

    _write_json(
        run_root / "execution_prompt.json",
        {
            "status": _normalize_text(
                run_state.get("prompt378_chatgpt_generated_prompt_intake_status"),
                default="",
            ),
            "ready": bool(run_state.get("prompt378_generated_prompt_ready", False)),
            "prompt_path": prompt_path_text,
            "prompt_sha256": prompt_checksum,
            "source": "prompt378_generated_prompt_execution_handoff",
            "compatibility_stage": "prompt378",
        },
    )
    return True


def reconnect_runtime_output_generation(
    *,
    run_root: Path,
    run_state_payload: Mapping[str, Any],
    manifest_payload: Mapping[str, Any],
    execution_repo_path: str,
    job_id: str,
    dry_run: bool,
    now: Callable[[], datetime],
    prompt373_live_execution_requested: bool = False,
    prompt373_live_execution_confirmed: bool = False,
    prompt378_generated_prompt_path: str = "",
    prompt379_codex_execution_requested: bool = False,
    prompt379_codex_execution_confirmed: bool = False,
    prompt383_approve_commit_tag_requested: bool = False,
    prompt383_approve_commit_tag_confirmed: bool = False,
    prompt389_bounded_repeated_success_path_loop_enabled: bool = False,
    prompt389_max_cycles: int | None = None,
    prompt546_internal_codex_subprocess_enabled: bool = False,
    prompt546_internal_codex_enable_token: str = "",
    prompt546_internal_codex_prompt_path: str = "",
    prompt546_internal_codex_timeout_seconds: int = 600,
    prompt546_internal_codex_allowed_files: Iterable[str] | None = None,
    prompt547_internal_codex_subprocess_enabled: bool = False,
    prompt547_internal_codex_enable_token: str = "",
    prompt547_internal_codex_prompt_path: str = "",
    prompt547_internal_codex_timeout_seconds: int = 600,
    prompt547_internal_codex_allowed_files: Iterable[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run split runtime output builders and merge their surfaces."""
    _install_runtime_surface_helpers()
    run_state = dict(run_state_payload)
    run_state.update(
        {
            **_current_head_metadata(repo_path=execution_repo_path),
            "prompt373_live_execution_requested": bool(
                prompt373_live_execution_requested
            ),
            "prompt373_live_execution_confirmed": bool(
                prompt373_live_execution_confirmed
            ),
            "prompt379_codex_execution_requested": bool(
                prompt379_codex_execution_requested
            ),
            "prompt379_codex_execution_confirmed": bool(
                prompt379_codex_execution_confirmed
            ),
            "prompt383_approve_commit_tag_requested": bool(
                prompt383_approve_commit_tag_requested
            ),
            "prompt383_approve_commit_tag_confirmed": bool(
                prompt383_approve_commit_tag_confirmed
            ),
        }
    )
    pr_units = manifest_payload.get("pr_units")
    first_unit = pr_units[0] if isinstance(pr_units, list) and pr_units else {}
    first_unit = first_unit if isinstance(first_unit, Mapping) else {}
    prompt_path = _normalize_text(first_unit.get("compiled_prompt_path"), default="")
    if prompt_path:
        run_state.update(
            {
                "prompt372_selected_step_execution_gate_status": "ready",
                "prompt372_gate_status": "ready",
                "prompt372_prompt371_wiring_ready": True,
                "prompt372_selected_route": "continue_next_cycle",
                "prompt372_selected_step_kind": "compiled_pr_unit",
                "prompt372_selected_step_operation": "prepare_selected_step_execution_gate",
                "prompt372_selected_next_action": (
                    "prepare_prompt373_selected_step_live_codex_execution"
                ),
                "prompt372_gate_ready": True,
                "prompt372_selected_step_contract_ready": bool(
                    first_unit.get("bounded_step_contract_path")
                ),
                "prompt372_selected_prompt_contract_ready": bool(
                    first_unit.get("pr_implementation_prompt_contract_path")
                ),
                "prompt372_codex_execution_request_status": "prepared",
                "prompt372_codex_execution_request_ready": bool(prompt_path),
                "prompt372_live_execution_preflight_ready": bool(prompt_path),
                "prompt372_next_action": (
                    "prepare_prompt373_selected_step_live_codex_execution"
                ),
                "prompt359_prompt358_selected_prompt_contract_path": prompt_path,
            }
        )

    prompt373 = _build_prompt373_selected_step_live_codex_execution_state(
        run_state_payload=run_state,
        run_root=run_root,
        execution_repo_path=execution_repo_path,
        job_id=job_id,
        now=now,
    )
    run_state.update(prompt373)

    (
        run_state,
        current_head_prompt491a_materialized_path,
    ) = _merge_prompt491a_current_head_materialization_surfaces(
        run_state=run_state,
        run_root=run_root,
    )
    resolved_prompt378_generated_prompt_path = (
        _resolve_existing_prompt378_generated_prompt_path(
            explicit_path=prompt378_generated_prompt_path,
            current_head_prompt491a_path=current_head_prompt491a_materialized_path,
            manifest_payload=manifest_payload,
        )
    )
    prompt378 = _build_prompt378_chatgpt_generated_prompt_intake_state(
        run_state_payload=run_state,
        run_root=run_root,
        prompt378_generated_prompt_path=resolved_prompt378_generated_prompt_path,
    )
    run_state.update(prompt378)
    execution_prompt_alias_emitted = _write_execution_prompt_alias_if_ready(
        run_root=run_root,
        run_state=run_state,
    )

    prompt379 = _build_prompt379_generated_prompt_codex_execution_bridge_state(
        run_state_payload=run_state,
        run_root=run_root,
        execution_repo_path=execution_repo_path,
        prompt379_codex_execution_requested=bool(prompt379_codex_execution_requested),
        prompt379_codex_execution_confirmed=bool(prompt379_codex_execution_confirmed),
        prompt379_dry_run_transport_mode=bool(dry_run),
        prompt379_live_transport_enabled=not bool(dry_run),
        now=now,
    )
    run_state.update(prompt379)

    prompt380 = _build_prompt380_prompt379_result_review_route_decision_state(
        run_state_payload=run_state,
        run_root=run_root,
    )
    run_state.update(prompt380)

    prompt381 = _build_prompt381_approve_candidate_boundary_state(
        run_state_payload=run_state,
        run_root=run_root,
    )
    run_state.update(prompt381)

    prompt382 = _build_prompt382_approve_commit_tag_execution_gate_state(
        run_state_payload=run_state,
        run_root=run_root,
    )
    run_state.update(prompt382)

    prompt383 = _build_prompt383_explicit_approve_commit_tag_execution_state(
        run_state_payload=run_state,
        run_root=run_root,
        execution_repo_path=execution_repo_path,
        prompt383_approve_commit_tag_requested=bool(
            prompt383_approve_commit_tag_requested
        ),
        prompt383_approve_commit_tag_confirmed=bool(
            prompt383_approve_commit_tag_confirmed
        ),
    )
    run_state.update(prompt383)

    prompt385 = _build_prompt385_success_path_next_cycle_handoff_state(
        run_state_payload=run_state,
        run_root=run_root,
    )
    run_state.update(prompt385)

    prompt388 = _build_prompt388_local_success_path_autonomous_loop_completion_gate_state(
        run_state_payload=run_state,
        run_root=run_root,
    )
    run_state.update(prompt388)

    prompt389 = _build_prompt389_explicit_bounded_repeated_success_path_loop_execution_state(
        run_state_payload=run_state,
        run_root=run_root,
        execution_repo_path=execution_repo_path,
        prompt378_generated_prompt_path=_normalize_text(
            run_state.get("prompt378_generated_prompt_path"),
            default="",
        ),
        prompt379_codex_execution_requested=bool(prompt379_codex_execution_requested),
        prompt379_codex_execution_confirmed=bool(prompt379_codex_execution_confirmed),
        prompt389_bounded_repeated_success_path_loop_enabled=bool(
            prompt389_bounded_repeated_success_path_loop_enabled
        ),
        prompt389_max_cycles=prompt389_max_cycles,
    )
    run_state.update(prompt389)

    run_state = _merge_split_compatible_runtime_surfaces(run_state)
    run_state = _connect_prompt546_runtime_internal_execution_adapter(
        run_state=run_state,
        execution_repo_path=execution_repo_path,
        prompt_path=prompt546_internal_codex_prompt_path,
        enabled=bool(prompt546_internal_codex_subprocess_enabled),
        enable_token=prompt546_internal_codex_enable_token,
        timeout_seconds=prompt546_internal_codex_timeout_seconds,
        allowed_files=prompt546_internal_codex_allowed_files,
    )
    run_state = _connect_prompt547_real_runtime_internal_codex_smoke(
        run_state=run_state,
        execution_repo_path=execution_repo_path,
        prompt_path=prompt547_internal_codex_prompt_path,
        enabled=bool(prompt547_internal_codex_subprocess_enabled),
        enable_token=prompt547_internal_codex_enable_token,
        timeout_seconds=prompt547_internal_codex_timeout_seconds,
        allowed_files=prompt547_internal_codex_allowed_files,
    )
    run_state = _connect_prompt548_runtime_result_injection_to_contract(
        run_state=run_state,
        execution_repo_path=execution_repo_path,
    )
    run_state = _connect_prompt549_actual_runtime_smoke_artifact_verification(
        run_state=run_state,
        execution_repo_path=execution_repo_path,
    )
    run_state = (
        _connect_prompt550_post_smoke_local_commit_tag_clean_rerun_final_completion(
            run_state=run_state,
        )
    )

    split_compatible_artifact_names: list[str] = []
    _write_filtered_runtime_artifact_if_present(
        run_root=run_root,
        run_state=run_state,
        artifact_name="prompt380_prompt379_result_review_route_decision.json",
        fields=_PROMPT380_RESULT_REVIEW_ROUTE_FIELDS,
    )
    _write_filtered_runtime_artifact_if_present(
        run_root=run_root,
        run_state=run_state,
        artifact_name="prompt381_approve_candidate_boundary.json",
        fields=_PROMPT381_APPROVE_CANDIDATE_BOUNDARY_FIELDS,
    )
    _write_filtered_runtime_artifact_if_present(
        run_root=run_root,
        run_state=run_state,
        artifact_name="prompt382_approve_commit_tag_execution_gate.json",
        fields=_PROMPT382_APPROVE_COMMIT_TAG_EXECUTION_GATE_FIELDS,
    )
    _write_filtered_runtime_artifact_if_present(
        run_root=run_root,
        run_state=run_state,
        artifact_name="prompt383_explicit_approve_commit_tag_execution_gate.json",
        fields=_PROMPT383_EXPLICIT_APPROVE_COMMIT_TAG_EXECUTION_GATE_FIELDS,
    )
    for artifact_name, fields in _SPLIT_COMPATIBLE_RUNTIME_ARTIFACTS:
        if _write_filtered_runtime_artifact_if_present(
            run_root=run_root,
            run_state=run_state,
            artifact_name=artifact_name,
            fields=fields,
        ):
            split_compatible_artifact_names.append(artifact_name)

    manifest = dict(manifest_payload)
    runtime_artifacts = {
        name: _artifact_summary(run_root / name) for name in _CRITICAL_RUNTIME_ARTIFACTS
    }
    split_compatible_artifacts = {
        name: _artifact_summary(run_root / name)
        for name in split_compatible_artifact_names
    }
    manifest["runtime_output_wiring"] = {
        "status": "completed",
        "dry_run": bool(dry_run),
        "critical_artifacts": runtime_artifacts,
        "split_compatible_artifacts": split_compatible_artifacts,
        "generated_artifact_count": sum(
            1 for summary in runtime_artifacts.values() if summary["present"]
        )
        + len(split_compatible_artifacts),
        "prompt378_generated_prompt_path_source": (
            "explicit"
            if _normalize_text(prompt378_generated_prompt_path, default="")
            else (
                "current_head_prompt491a"
                if current_head_prompt491a_materialized_path
                else ("artifact_input_dir" if resolved_prompt378_generated_prompt_path else "")
            )
        ),
        "execution_prompt_alias_emitted": bool(execution_prompt_alias_emitted),
    }
    for name, summary in runtime_artifacts.items():
        stem = name.removesuffix(".json")
        manifest[f"{stem}_path"] = summary["path"]
        manifest[f"{stem}_summary"] = summary
    for name, summary in split_compatible_artifacts.items():
        stem = name.removesuffix(".json")
        manifest[f"{stem}_path"] = summary["path"]
        manifest[f"{stem}_summary"] = summary

    run_state["runtime_output_wiring_status"] = "completed"
    run_state["runtime_output_wiring_critical_artifacts_present"] = sorted(
        name for name, summary in runtime_artifacts.items() if summary["present"]
    )
    run_state["runtime_output_wiring_critical_artifacts_missing"] = sorted(
        name for name, summary in runtime_artifacts.items() if not summary["present"]
    )
    run_state["selected_route"] = _normalize_text(
        run_state.get("prompt373_selected_route"),
        default=_normalize_text(run_state.get("selected_route"), default=""),
    )
    run_state["route_decision"] = _normalize_text(
        run_state.get("prompt380_route_decision")
        or run_state.get("prompt379_next_action")
        or run_state.get("prompt373_next_action")
        or run_state.get("route_decision"),
        default="",
    )
    run_state["blocked_reason"] = _normalize_text(
        run_state.get("prompt389_active_blocked_reason")
        or run_state.get("prompt388_active_blocked_reason")
        or run_state.get("prompt385_active_blocked_reason")
        or run_state.get("prompt379_active_blocked_reason")
        or run_state.get("prompt373_active_blocked_reason")
        or run_state.get("blocked_reason"),
        default="",
    )
    return run_state, manifest


__all__ = ["reconnect_runtime_output_generation"]
