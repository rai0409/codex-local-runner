from __future__ import annotations

from datetime import datetime
import hashlib
from pathlib import Path
import subprocess
from typing import Any
from typing import Callable
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
from automation.orchestration.planned_runner.prompt_surfaces.registry import (
    get_prompt_builders,
)
from automation.orchestration.planned_runner.utils import _normalize_text
from automation.orchestration.planned_runner.utils import _read_json_object_if_exists
from automation.orchestration.planned_runner.utils import _write_json


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
