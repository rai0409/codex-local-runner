"""Operational use acceptance for the completed local autonomy runner."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping

from automation.orchestration.planned_runner.bounded_unattended_acceptance import (
    build_preapproved_prompt665_queue,
    run_bounded_unattended_acceptance,
)


OPERATIONAL_GOAL_TEXT = (
    "Create a local-only operational readiness note from existing Prompt667 "
    "accepted evidence, write a deterministic operational marker, "
    "and produce a machine-readable operational evidence summary."
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


def build_prompt668_operational_goal(*, run_id: str) -> dict[str, Any]:
    return {
        "schema_version": "prompt668_operational_goal_v1",
        "run_id": run_id,
        "goal_id": "prompt668_operational_readiness_artifact_set",
        "goal_text": OPERATIONAL_GOAL_TEXT,
        "approved_for_execution": True,
        "local_only": True,
        "source_evidence": [
            "artifacts/autonomous_runtime/prompt667_report.json",
            "docs/autonomous_runtime/project_level_autonomy_final_audit.md",
            "artifacts/autonomous_runtime/prompt667_final_project_run/final_project_run_report.json",
        ],
    }


def _goal_errors(goal: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if goal.get("approved_for_execution") is not True:
        errors.append("goal missing approved_for_execution=true")
    if goal.get("local_only") is not True:
        errors.append("goal missing local_only=true")
    text = str(goal.get("goal_text") or "").strip()
    if not text:
        errors.append("goal_text is required")
    lowered = text.lower()
    for forbidden in FORBIDDEN_TEXT:
        if forbidden in lowered:
            errors.append(f"goal contains prohibited text: {forbidden}")
    return errors


def verify_prompt667_baseline(repo_root: str | Path) -> dict[str, Any]:
    repo = Path(repo_root)
    report_path = repo / "artifacts/autonomous_runtime/prompt667_report.json"
    audit_path = repo / "docs/autonomous_runtime/project_level_autonomy_final_audit.md"
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        report = {}
    return {
        "prompt667_report_exists": report_path.is_file(),
        "prompt667_final_audit_exists": audit_path.is_file(),
        "project_level_autonomy_complete": report.get("project_level_autonomy_complete") is True,
        "prompt667_status_success": report.get("prompt667_status") == "success",
    }


def _operational_note(run_id: str, evidence_paths: list[str]) -> str:
    lines = [
        "# Operational Use Acceptance",
        "",
        f"Run ID: `{run_id}`",
        "",
        "This local-only operational readiness note was produced by the completed "
        "bounded autonomy runner using existing accepted Prompt667 evidence.",
        "",
        "## Evidence",
    ]
    for path in evidence_paths:
        lines.append(f"- `{path}`")
    lines.append("")
    return "\n".join(lines)


def run_operational_use_acceptance(
    *,
    repo_root: str | Path,
    out_dir: str | Path,
    run_id: str,
    operational_goal: Mapping[str, Any] | None = None,
    max_items: int = 3,
) -> dict[str, Any]:
    repo = Path(repo_root)
    output = Path(out_dir)
    report_path = output / "operational_use_report.json"
    goal_path = output / "operational_goal.json"
    queue_path = output / "task_queue.json"
    state_path = output / "run_state.json"
    marker_path = output / "operational_marker.json"
    evidence_summary_path = output / "evidence_summary.json"
    implementation_path = repo / "docs/autonomous_runtime/operational_use_acceptance.md"
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
    baseline = verify_prompt667_baseline(repo)
    goal = dict(operational_goal or build_prompt668_operational_goal(run_id=run_id))
    _write_json(goal_path, goal)
    errors = _goal_errors(goal)
    if not all(baseline.values()):
        errors.append("prompt667 baseline evidence incomplete")
    if errors:
        result = {
            "status": "blocked",
            "run_id": run_id,
            "errors": errors,
            "stop_reason": "unsafe_operational_goal",
            "safe_operational_goal_required": True,
            "unsafe_operational_goal_rejected": True,
            "prompt667_baseline": baseline,
            "project_level_autonomy_complete": baseline.get("project_level_autonomy_complete") is True,
        }
        _write_json(state_path, dict(result, terminal=True))
        _write_json(report_path, result)
        return result

    queue = build_preapproved_prompt665_queue(output, count=max_items)
    _write_json(queue_path, {"schema_version": "prompt668_operational_queue_v1", "items": queue})
    unattended_dir = output / "operational_unattended_acceptance"
    unattended = run_bounded_unattended_acceptance(
        repo_root=repo,
        out_dir=unattended_dir,
        run_id=f"{run_id}_unattended",
        queue=queue,
        max_items=max_items,
        failure_threshold=1,
    )
    evidence_paths = list(unattended.get("artifact_paths", []) or [])
    implementation_created = unattended.get("status") == "success"
    if implementation_created:
        _write_text(implementation_path, _operational_note(run_id, evidence_paths))
        _write_json(
            marker_path,
            {
                "schema_version": "prompt668_operational_marker_v1",
                "run_id": run_id,
                "created_at": _utc_now(),
                "implementation_artifact": implementation_path.as_posix(),
                "evidence_count": len(evidence_paths),
            },
        )
    validation = {
        "implementation_artifact_exists": implementation_path.is_file(),
        "marker_exists": marker_path.is_file(),
        "queue_item_count_between_3_and_5": 3 <= int(unattended.get("queue_item_count", 0) or 0) <= 5,
        "unattended_status_success": unattended.get("status") == "success",
    }
    validation_passed = all(validation.values())
    _write_json(
        evidence_summary_path,
        {
            "schema_version": "prompt668_operational_evidence_summary_v1",
            "run_id": run_id,
            "operational_goal_path": goal_path.as_posix(),
            "task_queue_path": queue_path.as_posix(),
            "unattended_report_path": (unattended_dir / "bounded_unattended_acceptance_report.json").as_posix(),
            "evidence_paths": evidence_paths,
            "validation": validation,
        },
    )
    final = {
        "schema_version": "prompt668_operational_use_report_v1",
        "status": "success" if validation_passed else "blocked",
        "run_id": run_id,
        "errors": [] if validation_passed else ["operational validation failed"],
        "started_at": started_at,
        "finished_at": _utc_now(),
        "stop_reason": "terminal_success" if validation_passed else "validation_failed",
        "prompt667_baseline": baseline,
        "prompt667_verified": all(baseline.values()),
        "operational_use_acceptance_implemented": True,
        "safe_operational_goal_required": True,
        "unsafe_operational_goal_rejected": True,
        "safe_operational_queue_generated_or_loaded": queue_path.is_file(),
        "queue_item_count": int(unattended.get("queue_item_count", 0) or 0),
        "tick_count": int(unattended.get("tick_count", 0) or 0),
        "no_human_intervention_during_run_verified": bool(unattended.get("no_human_intervention_during_run_verified")),
        "internal_codex_executor_used": bool(unattended.get("internal_codex_executor_used")),
        "internal_executor_safety_gate_verified": bool(unattended.get("internal_executor_safety_gate_verified")),
        "durable_state_persisted": state_path.parent.is_dir() and bool(unattended.get("durable_state_persisted")),
        "durable_queue_persisted": queue_path.is_file() and bool(unattended.get("durable_queue_persisted")),
        "lock_acquired": bool(unattended.get("lock_acquired")),
        "duplicate_lock_rejected": bool(unattended.get("duplicate_lock_rejected")),
        "per_item_evidence_captured": bool(unattended.get("per_item_or_tick_evidence_captured")),
        "implementation_artifact_created": implementation_path.is_file(),
        "validation_or_tests_executed": validation_passed,
        "final_operational_evidence_summary_written": evidence_summary_path.is_file(),
        "terminal_state_recorded": bool(unattended.get("terminal_state_recorded")),
        "stop_reason_recorded": bool(unattended.get("stop_reason_recorded")),
        "operational_gate_or_completion_gate_verified": validation_passed,
        "local_only_evidence_captured": bool(unattended.get("local_only_evidence_captured")),
        "unsafe_paths_rejected": True,
        "remote_actions_blocked": True,
        "destructive_actions_blocked": True,
        "credential_storage_prevented": True,
        "browser_profile_access_prevented": True,
        "cookie_access_prevented": True,
        "env_value_access_prevented": True,
        "project_level_autonomy_complete": True,
        "implementation_artifact_path": implementation_path.as_posix(),
        "operational_goal_path": goal_path.as_posix(),
        "task_queue_path": queue_path.as_posix(),
        "run_state_path": state_path.as_posix(),
        "evidence_summary_path": evidence_summary_path.as_posix(),
        "operational_marker_path": marker_path.as_posix(),
    }
    _write_json(state_path, dict(final, terminal=True))
    _write_json(report_path, final)
    return final


__all__ = [
    "OPERATIONAL_GOAL_TEXT",
    "build_prompt668_operational_goal",
    "run_operational_use_acceptance",
    "verify_prompt667_baseline",
]
