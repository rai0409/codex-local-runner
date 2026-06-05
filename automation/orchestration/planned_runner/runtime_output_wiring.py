from __future__ import annotations

from datetime import datetime
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
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
        prompt569_artifact_dir = longer_soak_artifact_dir / "prompt569_soak_runner"
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
            resume_state_path=resume_path,
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
