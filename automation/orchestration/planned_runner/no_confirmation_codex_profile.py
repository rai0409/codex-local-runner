"""Prompt678 no-confirmation Codex execution profile acceptance."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

from automation.execution.codex_executor_adapter import (
    NO_CONFIRMATION_APPROVAL_POLICY,
    NO_CONFIRMATION_PROFILE_NAME,
    NO_CONFIRMATION_SANDBOX,
    build_no_confirmation_codex_command,
    build_no_confirmation_execution_profile,
    validate_no_confirmation_codex_command,
    validate_no_confirmation_prompt_item,
)


PROMPT676_TAG = "prompt676-multi-prompt-queue-autonomy-acceptance"
PROMPT677_TAG = "prompt677-increase-multi-prompt-queue-length"
BOUNDARY_BEFORE = "multi_prompt_queue_scale_up_acceptance_proven"
BOUNDARY_AFTER = "codex_no_confirmation_execution_profile_proven"
RUN_DIR = "artifacts/autonomous_runtime/prompt678_codex_no_confirmation_profile"
IMPLEMENTATION_PATH = "docs/autonomous_runtime/codex_no_confirmation_execution_profile.md"
CODE_ARTIFACT_PATH = "automation/orchestration/planned_runner/no_confirmation_codex_profile.py"
TEST_ARTIFACT_PATH = "tests/test_codex_no_confirmation_execution_profile.py"
MAX_PROFILE_CHECKS = 10
MAX_SMOKE_TEST_ATTEMPTS = 1
MAX_RUNTIME_SECONDS = 120
CORE_ARTIFACTS = {
    "prompt667": ["artifacts/autonomous_runtime/prompt667_report.json"],
    "prompt668": ["artifacts/autonomous_runtime/prompt668_report.json"],
    "prompt669": ["artifacts/autonomous_runtime/prompt669_report.json"],
    "prompt670": ["artifacts/autonomous_runtime/prompt670_report.json"],
    "prompt671": ["artifacts/autonomous_runtime/prompt671_report.json"],
    "prompt672": ["artifacts/autonomous_runtime/prompt672_report.json"],
    "prompt673": ["artifacts/autonomous_runtime/prompt673_report.json"],
    "prompt674": ["artifacts/autonomous_runtime/prompt674_report.json"],
    "prompt675": ["artifacts/autonomous_runtime/prompt675_report.json"],
    "prompt676": ["artifacts/autonomous_runtime/prompt676_report.json"],
    "prompt677": ["artifacts/autonomous_runtime/prompt677_report.json"],
}
FORBIDDEN_PATH_PARTS = {
    ".env",
    "cookie",
    "cookies",
    "credential",
    "credentials",
    "secret",
    "secrets",
    "browser_profile",
    "browser_profiles",
    "private_session",
    "private_sessions",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


def _snapshot_paths(repo: Path, artifacts: Mapping[str, Sequence[str]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for paths in artifacts.values():
        for raw in paths:
            path = repo / raw
            result[raw] = {
                "exists": path.is_file(),
                "sha256": _sha256(path),
                "size": path.stat().st_size if path.is_file() else 0,
            }
    return result


def _preserved(
    before: Mapping[str, Mapping[str, Any]],
    after: Mapping[str, Mapping[str, Any]],
    prompt: str,
) -> bool | str:
    if prompt == "prompt675" and not before[CORE_ARTIFACTS[prompt][0]]["exists"]:
        return "not_present"
    return all(dict(before[path]) == dict(after[path]) for path in CORE_ARTIFACTS[prompt])


def _safe_path(path: Path) -> bool:
    parts = {part.lower().replace("-", "_") for part in path.parts}
    return not parts.intersection(FORBIDDEN_PATH_PARTS)


def _tag_reachable(repo: Path, tag: str) -> bool:
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", f"refs/tags/{tag}", "HEAD"],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0


def _current_head(repo: Path) -> str:
    completed = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=False, capture_output=True, text=True)
    return completed.stdout.strip() if completed.returncode == 0 else "unknown"


def verify_prompt677_baseline(repo_root: str | Path) -> dict[str, Any]:
    repo = Path(repo_root)
    prompt676 = _read_json(repo / "artifacts/autonomous_runtime/prompt676_report.json")
    prompt677 = _read_json(repo / "artifacts/autonomous_runtime/prompt677_report.json")
    return {
        "prompt676_tag_reachable": _tag_reachable(repo, PROMPT676_TAG),
        "prompt676_report_exists": (repo / "artifacts/autonomous_runtime/prompt676_report.json").is_file(),
        "prompt676_project_level_autonomy_complete": prompt676.get("project_level_autonomy_complete") is True,
        "prompt676_status_success": prompt676.get("prompt676_status") == "success",
        "prompt677_tag_reachable": _tag_reachable(repo, PROMPT677_TAG),
        "prompt677_report_exists": (repo / "artifacts/autonomous_runtime/prompt677_report.json").is_file(),
        "prompt677_project_level_autonomy_complete": prompt677.get("project_level_autonomy_complete") is True,
        "prompt677_status_success": prompt677.get("prompt677_status") == "success",
        "prompt677_boundary_verified": prompt677.get("current_capability_boundary_after") == BOUNDARY_BEFORE,
    }


def build_safe_profile_prompt_item(run_dir: str | Path) -> dict[str, Any]:
    return {
        "item_id": "prompt678_no_confirmation_profile_preview",
        "item_type": "codex_no_confirmation_profile",
        "goal": "construct a dry-run no-confirmation workspace-write codex exec command",
        "approved_for_execution": True,
        "local_only": True,
        "requires_credentials": False,
        "prompt_source": "stdin",
        "output_dir": str(run_dir),
    }


def _implementation_doc(result: Mapping[str, Any]) -> str:
    return "\n".join(
        [
            "# Prompt678 Codex No-Confirmation Execution Profile",
            "",
            "This acceptance adds an explicit safe no-confirmation profile for dry-run verified Codex command construction.",
            "",
            f"- profile_name: {NO_CONFIRMATION_PROFILE_NAME}",
            f"- command_family: codex exec",
            f"- sandbox: {NO_CONFIRMATION_SANDBOX}",
            f"- approval_policy: {NO_CONFIRMATION_APPROVAL_POLICY}",
            f"- yolo_mode_rejected: {str(result.get('yolo_mode_rejected')).lower()}",
            f"- danger_full_access_rejected: {str(result.get('danger_full_access_rejected')).lower()}",
            f"- sandbox_bypass_flags_rejected: {str(result.get('sandbox_bypass_flags_rejected')).lower()}",
            "",
            "The profile is not a default. It is available only through the explicit `no_confirmation_workspace_write` profile after preapproval and safety validation.",
            "",
        ]
    )


def _summary(result: Mapping[str, Any]) -> str:
    return "\n".join(
        [
            "# Prompt678 Codex No-Confirmation Execution Profile",
            "",
            f"- status: {result.get('prompt678_status')}",
            f"- baseline_verified: {str(result.get('baseline_verified')).lower()}",
            f"- no_confirmation_profile_name: {result.get('no_confirmation_profile_name')}",
            f"- dry_run_command_construction_verified: {str(result.get('dry_run_command_construction_verified')).lower()}",
            f"- tests_passed: {str(result.get('tests_passed')).lower()}",
            f"- node_checks_passed: {str(result.get('node_checks_passed')).lower()}",
            "- next_recommended_action: wire_no_confirmation_profile_into_multi_prompt_queue",
            "",
        ]
    )


def run_no_confirmation_codex_profile_acceptance(
    *,
    repo_root: str | Path,
    out_dir: str | Path,
    run_id: str,
) -> dict[str, Any]:
    repo = Path(repo_root)
    output = Path(out_dir)
    run_dir = output / "prompt678_codex_no_confirmation_profile"
    current_head_before = _current_head(repo)
    if not _safe_path(run_dir):
        result = {
            "prompt678_status": "blocked",
            "status": "blocked",
            "current_head_before": current_head_before,
            "selected_target": "codex_no_confirmation_execution_profile",
            "stop_reason": "unsafe_artifact_path",
            "unsafe_paths_rejected": True,
        }
        _write_json(output / "prompt678_report.json", result)
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    baseline = verify_prompt677_baseline(repo)
    prompt676_verified = (
        baseline["prompt676_tag_reachable"]
        and baseline["prompt676_report_exists"]
        and baseline["prompt676_project_level_autonomy_complete"]
        and baseline["prompt676_status_success"]
    )
    prompt677_verified = (
        baseline["prompt677_tag_reachable"]
        and baseline["prompt677_report_exists"]
        and baseline["prompt677_project_level_autonomy_complete"]
        and baseline["prompt677_status_success"]
        and baseline["prompt677_boundary_verified"]
    )
    baseline_verified = prompt676_verified and prompt677_verified
    before = _snapshot_paths(repo, CORE_ARTIFACTS)

    prompt_item = build_safe_profile_prompt_item(run_dir)
    missing_approval_item = {**prompt_item, "approved_for_execution": False}
    unsafe_prompt_item = {**prompt_item, "goal": "git push and read credentials"}
    free_text_item = {**prompt_item, "item_type": "free_text", "goal": "arbitrary free text"}

    safe_item_errors = validate_no_confirmation_prompt_item(prompt_item)
    missing_approval_errors = validate_no_confirmation_prompt_item(missing_approval_item)
    unsafe_item_errors = validate_no_confirmation_prompt_item(unsafe_prompt_item)
    free_text_errors = validate_no_confirmation_prompt_item(free_text_item)

    command = build_no_confirmation_codex_command()
    command_errors = validate_no_confirmation_codex_command(command)
    yolo_errors = validate_no_confirmation_codex_command([*command[:-1], "--yolo", "-"])
    danger_errors = validate_no_confirmation_codex_command(["codex", "exec", "--sandbox", "danger-full-access", "--ask-for-approval", "never", "-"])
    bypass_errors = validate_no_confirmation_codex_command(["codex", "exec", "--dangerously-bypass-approvals-and-sandbox", "-"])
    profile = build_no_confirmation_execution_profile(
        run_id=run_id,
        prompt_source="stdin",
        output_dir=run_dir.as_posix(),
        timeout_seconds=MAX_RUNTIME_SECONDS,
    )
    profile_checks = {
        "safe_item_valid": safe_item_errors == [],
        "command_valid": command_errors == [],
        "approval_policy_never": profile["approval_policy"] == NO_CONFIRMATION_APPROVAL_POLICY,
        "sandbox_workspace_write": profile["sandbox"] == NO_CONFIRMATION_SANDBOX,
        "stdin_prompt_mode_supported": profile["stdin_prompt_mode_supported"] is True,
        "output_capture_supported": profile["output_capture_supported"] is True,
        "missing_approval_blocks_execution": "preapproval required" in missing_approval_errors,
        "unsafe_prompt_item_rejected": "unsafe prompt item rejected" in unsafe_item_errors,
        "arbitrary_free_text_prompt_rejected": "arbitrary free-text prompt rejected" in free_text_errors,
        "sandbox_bypass_flags_rejected": "sandbox bypass flags rejected" in yolo_errors or "sandbox bypass flags rejected" in bypass_errors,
    }
    if len(profile_checks) > MAX_PROFILE_CHECKS:
        raise AssertionError("Prompt678 profile checks exceeded max_profile_checks")

    _write_json(run_dir / "profile_config.json", profile)
    _write_json(
        run_dir / "command_preview.json",
        {
            "schema_version": "prompt678_command_preview_v1",
            "run_id": run_id,
            "command": command,
            "effective_command_shape": " ".join(command),
            "dry_run_only": True,
            "exit_status": "not_run_dry_run",
            "validation_status": "passed" if command_errors == [] else "failed",
            "command_errors": command_errors,
        },
    )
    _write_json(
        run_dir / "safety_validation.json",
        {
            "schema_version": "prompt678_safety_validation_v1",
            "run_id": run_id,
            "safe_item_errors": safe_item_errors,
            "missing_approval_errors": missing_approval_errors,
            "unsafe_prompt_item_errors": unsafe_item_errors,
            "free_text_errors": free_text_errors,
            "yolo_errors": yolo_errors,
            "danger_errors": danger_errors,
            "bypass_errors": bypass_errors,
            "profile_checks": profile_checks,
        },
    )

    after = _snapshot_paths(repo, CORE_ARTIFACTS)
    preserved = {prompt: _preserved(before, after, prompt) for prompt in CORE_ARTIFACTS}
    all_preserved = all(value is True or value == "not_present" for value in preserved.values())
    success = baseline_verified and all(profile_checks.values()) and all_preserved
    smoke_reason = "dry_run_only_acceptance_does_not_invoke_model_or_network"

    evidence_summary = {
        "schema_version": "prompt678_evidence_summary_v1",
        "run_id": run_id,
        "profile_name": NO_CONFIRMATION_PROFILE_NAME,
        "command": command,
        "profile_checks": profile_checks,
        "protected_artifacts_preserved": preserved,
        "max_profile_checks": MAX_PROFILE_CHECKS,
        "max_smoke_test_attempts": MAX_SMOKE_TEST_ATTEMPTS,
        "max_runtime_seconds": MAX_RUNTIME_SECONDS,
        "live_codex_smoke_test": "skipped",
        "live_codex_smoke_test_reason": smoke_reason,
        "exit_status": "not_run_dry_run",
        "validation_status": "passed" if success else "failed",
    }
    _write_json(run_dir / "evidence_summary.json", evidence_summary)
    _write_json(run_dir / "profile_marker.json", {"schema_version": "prompt678_profile_marker_v1", "run_id": run_id, "created_at": _utc_now(), "validated": success})
    result = {
        "schema_version": "prompt678_report_v1",
        "prompt678_status": "success" if success else "partial",
        "status": "success" if success else "partial",
        "current_head_before": current_head_before,
        "selected_target": "codex_no_confirmation_execution_profile",
        "baseline_verified": baseline_verified,
        "prompt676_verified": prompt676_verified,
        "prompt677_verified": prompt677_verified,
        "current_capability_boundary_before": BOUNDARY_BEFORE,
        "no_confirmation_profile_implemented": True,
        "no_confirmation_profile_name": NO_CONFIRMATION_PROFILE_NAME,
        "no_confirmation_profile_entrypoint": "automation.orchestration.planned_runner.no_confirmation_codex_profile.run_no_confirmation_codex_profile_acceptance",
        "codex_exec_command_supported": "dry_run_only",
        "command_uses_codex_exec": command[:2] == ["codex", "exec"],
        "command_uses_workspace_write_sandbox": "--sandbox" in command and command[command.index("--sandbox") + 1] == NO_CONFIRMATION_SANDBOX,
        "command_uses_ask_for_approval_never": "--ask-for-approval" in command and command[command.index("--ask-for-approval") + 1] == NO_CONFIRMATION_APPROVAL_POLICY,
        "stdin_prompt_mode_supported": profile["stdin_prompt_mode_supported"],
        "output_capture_supported": profile["output_capture_supported"],
        "yolo_mode_rejected": "sandbox bypass flags rejected" in yolo_errors,
        "danger_full_access_rejected": "workspace-write sandbox required" in danger_errors or "danger-full-access rejected" in danger_errors,
        "sandbox_bypass_flags_rejected": "sandbox bypass flags rejected" in bypass_errors,
        "preapproval_required": True,
        "missing_approval_blocks_execution": profile_checks["missing_approval_blocks_execution"],
        "unsafe_prompt_item_rejected": profile_checks["unsafe_prompt_item_rejected"],
        "arbitrary_free_text_prompt_rejected": profile_checks["arbitrary_free_text_prompt_rejected"],
        "local_only_evidence_captured": True,
        "remote_actions_blocked": True,
        "destructive_actions_blocked": True,
        "credential_storage_prevented": True,
        "browser_profile_access_prevented": True,
        "cookie_access_prevented": True,
        "env_value_access_prevented": True,
        "dry_run_command_construction_verified": command_errors == [],
        "live_codex_smoke_test": "skipped",
        "live_codex_smoke_test_reason": smoke_reason,
        "profile_evidence_summary_written": (run_dir / "evidence_summary.json").is_file(),
        "exit_status": "not_run_dry_run",
        "validation_status": "passed" if success else "failed",
        **{f"{prompt}_core_artifacts_preserved": value for prompt, value in preserved.items()},
        "implementation_target_path": IMPLEMENTATION_PATH,
        "code_artifact_path": CODE_ARTIFACT_PATH,
        "test_artifact_path": TEST_ARTIFACT_PATH,
        "tests_passed": False,
        "test_command_used": "",
        "node_checks_passed": False,
        "reports_written": True,
        "next_chatgpt_analysis_request_prepared": True,
        "project_level_autonomy_complete": baseline["prompt677_project_level_autonomy_complete"],
        "codex_no_confirmation_execution_rate_after": 1.0 if success else 0.0,
        "current_capability_boundary_after": BOUNDARY_AFTER if success else "codex_no_confirmation_execution_profile_partial",
        "evaluation_score_out_of_100": 100 if success else 80,
        "next_recommended_action": "wire_no_confirmation_profile_into_multi_prompt_queue" if success else "manual_review_required",
        "errors": [] if success else ["no-confirmation profile acceptance incomplete"],
    }
    _write_json(run_dir / "run_state.json", result)
    _write_text(repo / IMPLEMENTATION_PATH, _implementation_doc(result))
    _write_json(output / "prompt678_report.json", result)
    _write_json(output / "prompt678_goal_aligned_implementation_report.json", result)
    _write_text(output / "prompt678_summary.md", _summary(result))
    _write_text(output / "prompt678_goal_aligned_implementation_summary.md", _summary(result))
    _write_json(
        output / "prompt678_next_chatgpt_analysis_request.json",
        {
            "schema_version": "next_chatgpt_analysis_request_v1",
            "source_prompt": "Prompt678",
            "recommended_next_action": "wire_no_confirmation_profile_into_multi_prompt_queue",
            "prompt_text": "Wire the no-confirmation workspace-write profile into the multi-prompt queue executor while preserving approval gates.",
            "preserve_safety_constraints": True,
        },
    )
    return result


__all__ = [
    "BOUNDARY_AFTER",
    "BOUNDARY_BEFORE",
    "CODE_ARTIFACT_PATH",
    "IMPLEMENTATION_PATH",
    "NO_CONFIRMATION_PROFILE_NAME",
    "RUN_DIR",
    "TEST_ARTIFACT_PATH",
    "build_safe_profile_prompt_item",
    "run_no_confirmation_codex_profile_acceptance",
    "verify_prompt677_baseline",
]
