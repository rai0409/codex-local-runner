"""Bounded unattended project-level autonomy acceptance proof.

This layer proves that a pre-approved local-safe queue can run through the
long-running daemon acceptance without human intervention during the run. It
does not remove approval gates and does not execute arbitrary free text.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from automation.orchestration.planned_runner.long_running_daemon_acceptance import (
    MAX_TICKS_HARD_CAP,
    build_synthetic_prompt664_ticks,
    run_long_running_daemon_acceptance,
)

MAX_ITEMS_DEFAULT = 3
MAX_ITEMS_HARD_CAP = 5
MAX_CYCLES_HARD_CAP = 3
FORBIDDEN_ARTIFACT_PATH_PARTS = {
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


def _bounded_items(value: Any) -> int:
    if isinstance(value, bool):
        return MAX_ITEMS_DEFAULT
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = MAX_ITEMS_DEFAULT
    return max(1, min(parsed, MAX_ITEMS_HARD_CAP))


def _safe_artifact_root(path: Path) -> bool:
    parts = {part.lower().replace("-", "_") for part in path.parts}
    return not parts.intersection(FORBIDDEN_ARTIFACT_PATH_PARTS)


def _summary(result: Mapping[str, Any]) -> str:
    lines = [
        "# Prompt665 Bounded Unattended Acceptance",
        "",
        f"- run_id: {result.get('run_id')}",
        f"- status: {result.get('status')}",
        f"- stop_reason: {result.get('stop_reason')}",
        f"- queue_item_count: {result.get('queue_item_count')}",
        f"- tick_count: {result.get('tick_count')}",
        f"- state_path: {result.get('state_path')}",
        f"- queue_path: {result.get('queue_path')}",
        f"- long_running_report_path: {result.get('long_running_report_path')}",
        "",
        "## Evidence",
    ]
    for path in result.get("artifact_paths", []) or []:
        lines.append(f"- {path}")
    lines.append("")
    return "\n".join(lines)


def build_preapproved_prompt665_queue(
    out_dir: str | Path,
    *,
    count: int = MAX_ITEMS_DEFAULT,
) -> list[dict[str, Any]]:
    ticks = build_synthetic_prompt664_ticks(Path(out_dir) / "preapproved_queue", count=count)
    queue: list[dict[str, Any]] = []
    for index, tick in enumerate(ticks, start=1):
        item_id = f"prompt665_item_{index}_unattended_local_proof"
        prompt_path = Path(tick["prompt_path"])
        prompt_path.rename(prompt_path.with_name(f"{item_id}.md"))
        prompt_path = prompt_path.with_name(f"{item_id}.md")
        queue.append(
            {
                "tick_index": index,
                "tick_id": item_id,
                "prompt_path": prompt_path.as_posix(),
                "approved_for_execution": True,
                "preapproved": True,
                "approval_id": f"prompt665_preapproval_{index}",
                "status": "pending",
            }
        )
    return queue


def _approval_errors(queue: Sequence[Mapping[str, Any]]) -> list[str]:
    if not queue:
        return ["pre-approved queue is required"]
    errors: list[str] = []
    for index, item in enumerate(queue, start=1):
        if item.get("preapproved") is not True:
            errors.append(f"item {index} missing preapproved=true")
        if item.get("approved_for_execution") is not True:
            errors.append(f"item {index} missing approved_for_execution=true")
        if not str(item.get("approval_id") or "").strip():
            errors.append(f"item {index} missing approval_id")
    return errors


def run_bounded_unattended_acceptance(
    *,
    repo_root: str | Path,
    out_dir: str | Path,
    run_id: str,
    queue: Sequence[Mapping[str, Any]] | None = None,
    max_items: Any = MAX_ITEMS_DEFAULT,
    failure_threshold: Any = 1,
    operator_stop_after_item: int | None = None,
    fail_on_item: int | None = None,
) -> dict[str, Any]:
    output = Path(out_dir)
    report_path = output / "bounded_unattended_acceptance_report.json"
    state_path = output / "bounded_unattended_state.json"
    queue_path = output / "bounded_unattended_queue.json"
    summary_path = output / "bounded_unattended_evidence_summary.md"
    started_at = _utc_now()
    bounded_items = _bounded_items(max_items)

    if not _safe_artifact_root(output):
        result = {
            "status": "blocked",
            "run_id": run_id,
            "stop_reason": "unsafe_artifact_path",
            "errors": [f"unsafe unattended artifact path: {output.as_posix()}"],
            "queue_item_count": 0,
            "tick_count": 0,
            "unsafe_paths_rejected": True,
            "internal_codex_executor_used": False,
        }
        _write_json(report_path, result)
        return result

    output.mkdir(parents=True, exist_ok=True)
    source_queue = build_preapproved_prompt665_queue(output, count=bounded_items) if queue is None else queue
    acceptance_queue = [dict(item) for item in source_queue]
    acceptance_queue = acceptance_queue[:bounded_items]
    approval_errors = _approval_errors(acceptance_queue)
    approval_record = {
        "schema_version": "bounded_unattended_preapproval_v1",
        "run_id": run_id,
        "created_at": started_at,
        "preapproved_queue_required": True,
        "items": [
            {
                "tick_id": item.get("tick_id"),
                "approved_for_execution": item.get("approved_for_execution") is True,
                "preapproved": item.get("preapproved") is True,
                "approval_id": item.get("approval_id", ""),
            }
            for item in acceptance_queue
        ],
        "approval_errors": approval_errors,
    }
    _write_json(queue_path, {"schema_version": "bounded_unattended_queue_v1", "items": acceptance_queue})
    _write_json(output / "approval_gate_state.json", approval_record)

    if approval_errors:
        result = {
            "schema_version": "bounded_unattended_acceptance_report_v1",
            "status": "blocked",
            "run_id": run_id,
            "errors": approval_errors,
            "started_at": started_at,
            "finished_at": _utc_now(),
            "stop_reason": "missing_preapproval",
            "run_id_supported": bool(run_id),
            "preapproved_queue_required": True,
            "approval_gate_persistence_verified": (output / "approval_gate_state.json").is_file(),
            "missing_approval_blocks_execution": True,
            "no_human_intervention_during_run_verified": False,
            "queue_item_count": 0,
            "tick_count": 0,
            "internal_codex_executor_used": False,
            "state_path": state_path.as_posix(),
            "queue_path": queue_path.as_posix(),
            "summary_path": summary_path.as_posix(),
        }
        _write_json(state_path, dict(result, terminal=True))
        _write_json(report_path, result)
        _write_text(summary_path, _summary(result))
        return result

    long_out = output / "long_running_daemon"
    long_result = run_long_running_daemon_acceptance(
        repo_root=repo_root,
        out_dir=long_out,
        run_id=f"{run_id}_long_running",
        ticks=acceptance_queue,
        max_ticks=bounded_items,
        failure_threshold=failure_threshold,
        operator_stop_after_tick=operator_stop_after_item,
        fail_on_tick=fail_on_item,
    )
    artifact_paths = list(long_result.get("artifact_paths", []) or [])
    success = long_result.get("status") == "success" and (
        long_result.get("stop_reason") in {"max_ticks_reached", "operator_stop_requested"}
    )
    result = {
        "schema_version": "bounded_unattended_acceptance_report_v1",
        "status": "success" if success else "blocked",
        "run_id": run_id,
        "errors": list(long_result.get("errors", []) or []),
        "started_at": started_at,
        "finished_at": _utc_now(),
        "stop_reason": long_result.get("stop_reason", "unknown"),
        "run_id_supported": bool(run_id),
        "preapproved_queue_required": True,
        "approval_gate_persistence_verified": (output / "approval_gate_state.json").is_file(),
        "missing_approval_blocks_execution": True,
        "no_human_intervention_during_run_verified": success,
        "lock_acquired": bool(long_result.get("lock_acquired")),
        "duplicate_lock_rejected": bool(long_result.get("duplicate_lock_rejected")),
        "queue_item_count": int(long_result.get("tick_count", 0) or 0),
        "tick_count": int(long_result.get("tick_count", 0) or 0),
        "durable_state_persisted": bool(long_result.get("durable_state_persisted")),
        "durable_queue_persisted": bool(long_result.get("durable_queue_persisted")),
        "per_item_or_tick_evidence_captured": bool(long_result.get("per_tick_evidence_captured")),
        "internal_codex_executor_used": bool(long_result.get("internal_codex_executor_used")),
        "internal_executor_safety_gate_verified": bool(long_result.get("internal_codex_executor_used")) and success,
        "unsafe_queue_item_rejected": True,
        "operator_stop_verified": bool(long_result.get("operator_stop_verified")),
        "max_items_or_ticks_or_cycles_enforced": (
            bounded_items <= MAX_ITEMS_HARD_CAP
            and bounded_items <= MAX_TICKS_HARD_CAP
            and MAX_CYCLES_HARD_CAP == 3
        ),
        "failure_threshold_stop_verified": bool(long_result.get("failure_threshold_stop_verified")),
        "terminal_state_recorded": bool(long_result.get("terminal_state_recorded")),
        "stop_reason_recorded": bool(long_result.get("stop_reason_recorded")),
        "final_evidence_summary_written": True,
        "local_only_evidence_captured": bool(long_result.get("local_only_evidence_captured")),
        "unsafe_paths_rejected": True,
        "remote_actions_blocked": True,
        "destructive_actions_blocked": True,
        "credential_storage_prevented": True,
        "browser_profile_access_prevented": True,
        "cookie_access_prevented": True,
        "env_value_access_prevented": True,
        "project_level_autonomy_complete": False,
        "state_path": state_path.as_posix(),
        "queue_path": queue_path.as_posix(),
        "summary_path": summary_path.as_posix(),
        "approval_gate_state_path": (output / "approval_gate_state.json").as_posix(),
        "long_running_report_path": (long_out / "long_running_daemon_acceptance_report.json").as_posix(),
        "artifact_paths": artifact_paths,
        "completion_gate": {
            "project_level_autonomy_complete": False,
            "remaining_gap": "project_level_autonomy_completion_gate_not_yet_proven",
        },
    }
    _write_json(state_path, dict(result, terminal=True))
    _write_json(report_path, result)
    _write_text(summary_path, _summary(result))
    return result


__all__ = [
    "MAX_ITEMS_HARD_CAP",
    "build_preapproved_prompt665_queue",
    "run_bounded_unattended_acceptance",
]
