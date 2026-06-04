from __future__ import annotations

from datetime import datetime
import hashlib
from pathlib import Path
import subprocess
from typing import Any
from typing import Callable
from typing import Iterable
from typing import Mapping

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
