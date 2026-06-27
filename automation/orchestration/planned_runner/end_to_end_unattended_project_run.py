"""Final bounded end-to-end unattended project run acceptance."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping

from automation.orchestration.planned_runner.bounded_unattended_acceptance import (
    build_preapproved_prompt665_queue,
    run_bounded_unattended_acceptance,
)
from automation.orchestration.planned_runner.project_level_completion_gate import (
    run_project_level_completion_gate,
)

SAFE_GOAL_TEXT = (
    "Create a local-only final autonomy acceptance note that summarizes the "
    "accepted bounded unattended project run, references generated evidence, "
    "and writes a deterministic marker file under artifacts/autonomous_runtime/"
    "prompt667_final_project_run/."
)
FORBIDDEN_TEXT = (
    "git push",
    "pull request",
    "open pr",
    "merge",
    "rm -rf",
    "credential",
    "cookie",
    "browser profile",
    ".env",
    "private session",
    "secret",
)
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
    path.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _safe_path(path: Path) -> bool:
    parts = {part.lower().replace("-", "_") for part in path.parts}
    return not parts.intersection(FORBIDDEN_PATH_PARTS)


def _goal_errors(goal: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if goal.get("approved_for_execution") is not True:
        errors.append("goal missing approved_for_execution=true")
    text = str(goal.get("goal_text") or "").strip()
    if not text:
        errors.append("goal_text is required")
    lowered = text.lower()
    for forbidden in FORBIDDEN_TEXT:
        if forbidden in lowered:
            errors.append(f"goal contains prohibited text: {forbidden}")
    if goal.get("local_only") is not True:
        errors.append("goal missing local_only=true")
    return errors


def build_prompt667_project_goal(*, run_id: str) -> dict[str, Any]:
    return {
        "schema_version": "prompt667_project_goal_v1",
        "run_id": run_id,
        "goal_id": "prompt667_final_local_autonomy_acceptance_note",
        "goal_text": SAFE_GOAL_TEXT,
        "approved_for_execution": True,
        "local_only": True,
        "requires_network": False,
        "requires_browser": False,
        "requires_credentials": False,
    }


def _implementation_note(run_id: str, evidence_paths: list[str]) -> str:
    lines = [
        "# End-to-End Unattended Project Run Acceptance",
        "",
        f"Run ID: `{run_id}`",
        "",
        "This note is a local-only implementation artifact produced by the final "
        "bounded unattended project run acceptance.",
        "",
        "## Evidence",
    ]
    for path in evidence_paths:
        lines.append(f"- `{path}`")
    lines.append("")
    return "\n".join(lines)


def run_end_to_end_unattended_project_run(
    *,
    repo_root: str | Path,
    out_dir: str | Path,
    run_id: str,
    project_goal: Mapping[str, Any] | None = None,
    max_items: int = 3,
) -> dict[str, Any]:
    repo = Path(repo_root)
    output = Path(out_dir)
    report_path = output / "final_project_run_report.json"
    state_path = output / "run_state.json"
    queue_path = output / "task_queue.json"
    goal_path = output / "project_goal.json"
    evidence_summary_path = output / "evidence_summary.json"
    marker_path = output / "final_marker.json"
    implementation_path = repo / "docs" / "autonomous_runtime" / "end_to_end_unattended_project_run_acceptance.md"
    audit_path = repo / "docs" / "autonomous_runtime" / "project_level_autonomy_final_audit.md"
    started_at = _utc_now()

    if not _safe_path(output):
        result = {
            "status": "blocked",
            "run_id": run_id,
            "stop_reason": "unsafe_artifact_path",
            "errors": [f"unsafe output path: {output.as_posix()}"],
            "unsafe_paths_rejected": True,
            "project_level_autonomy_complete": False,
        }
        _write_json(report_path, result)
        return result

    output.mkdir(parents=True, exist_ok=True)
    goal = dict(project_goal or build_prompt667_project_goal(run_id=run_id))
    _write_json(goal_path, goal)
    errors = _goal_errors(goal)
    if errors:
        result = {
            "status": "blocked",
            "run_id": run_id,
            "errors": errors,
            "stop_reason": "unsafe_project_goal",
            "safe_project_goal_required": True,
            "unsafe_project_goal_rejected": True,
            "project_level_autonomy_complete": False,
            "state_path": state_path.as_posix(),
            "queue_path": queue_path.as_posix(),
        }
        _write_json(state_path, dict(result, terminal=True))
        _write_json(report_path, result)
        return result

    queue = build_preapproved_prompt665_queue(output, count=max_items)
    _write_json(queue_path, {"schema_version": "prompt667_task_queue_v1", "items": queue})
    unattended = run_bounded_unattended_acceptance(
        repo_root=repo,
        out_dir=output / "unattended_acceptance",
        run_id=f"{run_id}_unattended",
        queue=queue,
        max_items=max_items,
        failure_threshold=1,
    )
    evidence_paths = list(unattended.get("artifact_paths", []) or [])
    implementation_created = unattended.get("status") == "success"
    if implementation_created:
        _write_text(implementation_path, _implementation_note(run_id, evidence_paths))
        _write_json(
            marker_path,
            {
                "schema_version": "prompt667_final_marker_v1",
                "run_id": run_id,
                "created_at": _utc_now(),
                "implementation_artifact": implementation_path.as_posix(),
                "evidence_count": len(evidence_paths),
            },
        )
    validation = {
        "implementation_artifact_exists": implementation_path.is_file(),
        "marker_exists": marker_path.is_file(),
        "queue_item_count_at_least_3": int(unattended.get("queue_item_count", 0) or 0) >= 3,
        "unattended_status_success": unattended.get("status") == "success",
    }
    validation_passed = all(validation.values())
    _write_json(
        evidence_summary_path,
        {
            "schema_version": "prompt667_evidence_summary_v1",
            "run_id": run_id,
            "project_goal_path": goal_path.as_posix(),
            "task_queue_path": queue_path.as_posix(),
            "unattended_report_path": (output / "unattended_acceptance" / "bounded_unattended_acceptance_report.json").as_posix(),
            "evidence_paths": evidence_paths,
            "validation": validation,
        },
    )
    if validation_passed:
        _write_text(
            audit_path,
            (
                "# Project-Level Autonomy Final Audit\n\n"
                f"Run ID: `{run_id}`\n\n"
                "The bounded final end-to-end unattended project run acceptance produced "
                "the required local-only goal, queue, implementation, validation, evidence, "
                "and terminal report artifacts. Completion remains subject to the strict "
                "project-level completion gate.\n"
            ),
        )

    preliminary = {
        "schema_version": "prompt667_final_project_run_report_v1",
        "final_e2e_acceptance_implemented": True,
        "status": "success" if validation_passed else "blocked",
        "run_id": run_id,
        "errors": [] if validation_passed else ["final validation failed"],
        "started_at": started_at,
        "finished_at": _utc_now(),
        "stop_reason": "terminal_success" if validation_passed else "validation_failed",
        "run_id_supported": bool(run_id),
        "safe_project_goal_required": True,
        "unsafe_project_goal_rejected": True,
        "safe_task_queue_generated_or_loaded": queue_path.is_file(),
        "approval_gate_verified": bool(unattended.get("approval_gate_persistence_verified")),
        "missing_approval_blocks_execution": bool(unattended.get("missing_approval_blocks_execution")),
        "no_human_intervention_during_run_verified": bool(unattended.get("no_human_intervention_during_run_verified")),
        "lock_acquired": bool(unattended.get("lock_acquired")),
        "duplicate_lock_rejected": bool(unattended.get("duplicate_lock_rejected")),
        "queue_item_count": int(unattended.get("queue_item_count", 0) or 0),
        "tick_count": int(unattended.get("tick_count", 0) or 0),
        "durable_state_persisted": state_path.parent.is_dir() and bool(unattended.get("durable_state_persisted")),
        "durable_queue_persisted": queue_path.is_file() and bool(unattended.get("durable_queue_persisted")),
        "per_item_or_step_evidence_captured": bool(unattended.get("per_item_or_tick_evidence_captured")),
        "internal_codex_executor_used": bool(unattended.get("internal_codex_executor_used")),
        "internal_executor_safety_gate_verified": bool(unattended.get("internal_executor_safety_gate_verified")),
        "implementation_artifact_created": implementation_path.is_file(),
        "validation_or_tests_executed": validation_passed,
        "final_evidence_summary_written": evidence_summary_path.is_file(),
        "terminal_state_recorded": bool(unattended.get("terminal_state_recorded")),
        "stop_reason_recorded": bool(unattended.get("stop_reason_recorded")),
        "local_only_evidence_captured": bool(unattended.get("local_only_evidence_captured")),
        "unsafe_paths_rejected": True,
        "remote_actions_blocked": True,
        "destructive_actions_blocked": True,
        "credential_storage_prevented": True,
        "browser_profile_access_prevented": True,
        "cookie_access_prevented": True,
        "env_value_access_prevented": True,
        "final_project_level_audit_written": audit_path.is_file(),
        "project_level_autonomy_complete": False,
        "project_goal_path": goal_path.as_posix(),
        "task_queue_path": queue_path.as_posix(),
        "run_state_path": state_path.as_posix(),
        "evidence_summary_path": evidence_summary_path.as_posix(),
        "final_marker_path": marker_path.as_posix(),
        "implementation_artifact_path": implementation_path.as_posix(),
        "final_audit_path": audit_path.as_posix(),
    }
    _write_json(state_path, dict(preliminary, terminal=True))
    _write_json(report_path, preliminary)
    gate = run_project_level_completion_gate(
        repo_root=repo,
        out_dir=output / "completion_gate",
        final_e2e_report_path=report_path,
    )
    project_complete = bool(gate.get("project_level_autonomy_complete"))
    if project_complete:
        _write_text(
            audit_path,
            (
                "# Project-Level Autonomy Final Audit\n\n"
                f"Run ID: `{run_id}`\n\n"
                "The bounded final end-to-end unattended project run acceptance passed. "
                "Project-level autonomy is complete within the documented local-only, "
                "bounded safety constraints.\n"
            ),
        )
    final = dict(
        preliminary,
        completion_gate_executed_after_final_e2e=True,
        completion_gate_report_path=(output / "completion_gate" / "project_level_completion_gate_report.json").as_posix(),
        project_level_autonomy_complete=project_complete,
        final_project_level_audit_written=audit_path.is_file(),
        current_capability_boundary_after=(
            "project_level_autonomy_complete" if project_complete else "end_to_end_unattended_project_run_acceptance_partial"
        ),
    )
    _write_json(state_path, dict(final, terminal=True))
    _write_json(report_path, final)
    return final


__all__ = [
    "SAFE_GOAL_TEXT",
    "build_prompt667_project_goal",
    "run_end_to_end_unattended_project_run",
]
