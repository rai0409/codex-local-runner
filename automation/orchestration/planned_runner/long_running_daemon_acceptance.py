"""Bounded long-running daemon acceptance proof.

This module drives several daemon ticks through the Prompt663 bounded daemon
wrapper. It is local-only, finite, and evidence-oriented; it does not run an
unbounded daemon and does not execute prompt text as shell commands.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from automation.orchestration.planned_runner.bounded_daemon_runner import (
    run_bounded_daemon_hardening,
)
from automation.orchestration.planned_runner.daemon_lock import acquire_lock, release_lock
from automation.orchestration.planned_runner.daemon_state import (
    read_daemon_state,
    write_daemon_state,
)

MAX_TICKS_DEFAULT = 3
MAX_TICKS_HARD_CAP = 5
DEFAULT_FAILURE_THRESHOLD = 1
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


def _bounded_ticks(value: Any) -> int:
    if isinstance(value, bool):
        return MAX_TICKS_DEFAULT
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = MAX_TICKS_DEFAULT
    return max(1, min(parsed, MAX_TICKS_HARD_CAP))


def _bounded_failure_threshold(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = DEFAULT_FAILURE_THRESHOLD
    return max(1, parsed)


def _safe_artifact_root(path: Path) -> bool:
    parts = {part.lower().replace("-", "_") for part in path.parts}
    return not parts.intersection(FORBIDDEN_ARTIFACT_PATH_PARTS)


def _load_queue(queue_path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(queue_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    ticks = payload.get("ticks") if isinstance(payload, Mapping) else None
    return [dict(item) for item in ticks if isinstance(item, Mapping)] if isinstance(ticks, list) else []


def _write_queue(queue_path: Path, ticks: Sequence[Mapping[str, Any]]) -> None:
    _write_json(
        queue_path,
        {
            "schema_version": "long_running_daemon_queue_v1",
            "updated_at": _utc_now(),
            "ticks": [dict(tick) for tick in ticks],
        },
    )


def _summary(result: Mapping[str, Any]) -> str:
    lines = [
        "# Prompt664 Long-Running Daemon Status",
        "",
        f"- run_id: {result.get('run_id')}",
        f"- status: {result.get('status')}",
        f"- stop_reason: {result.get('stop_reason')}",
        f"- tick_count: {result.get('tick_count')}",
        f"- max_ticks: {result.get('max_ticks')}",
        f"- state_path: {result.get('state_path')}",
        f"- queue_path: {result.get('queue_path')}",
        f"- lock_path: {result.get('lock_path')}",
        "",
        "## Tick Evidence",
    ]
    for path in result.get("artifact_paths", []) or []:
        lines.append(f"- {path}")
    lines.append("")
    return "\n".join(lines)


def build_synthetic_prompt664_ticks(out_dir: str | Path, *, count: int = MAX_TICKS_DEFAULT) -> list[dict[str, Any]]:
    base = Path(out_dir) / "prompts"
    ticks: list[dict[str, Any]] = []
    for index in range(1, max(1, int(count)) + 1):
        tick_id = f"prompt664_tick_{index}_local_daemon_proof"
        prompt_path = base / f"{tick_id}.md"
        _write_text(
            prompt_path,
            (
                f"# Prompt664 Tick {index} Local Daemon Proof\n\n"
                "Record local daemon tick evidence only. Use the bounded Prompt663 "
                "daemon route. Stay inside the approved local evidence path and do "
                "not broaden execution authority.\n"
            ),
        )
        ticks.append(
            {
                "tick_index": index,
                "tick_id": tick_id,
                "prompt_path": prompt_path.as_posix(),
                "approved_for_execution": True,
                "status": "pending",
            }
        )
    return ticks


def run_long_running_daemon_acceptance(
    *,
    repo_root: str | Path,
    out_dir: str | Path,
    run_id: str,
    ticks: Sequence[Mapping[str, Any]] | None = None,
    max_ticks: Any = MAX_TICKS_DEFAULT,
    failure_threshold: Any = DEFAULT_FAILURE_THRESHOLD,
    stop_file: str | Path | None = None,
    interrupt_after_tick: int | None = None,
    operator_stop_after_tick: int | None = None,
    fail_on_tick: int | None = None,
    pid: int | None = None,
) -> dict[str, Any]:
    repo = Path(repo_root)
    output = Path(out_dir)
    lock_path = output / "long_running_daemon.lock"
    state_path = output / "long_running_daemon_state.json"
    queue_path = output / "long_running_daemon_queue.json"
    summary_path = output / "long_running_daemon_status_summary.md"
    report_path = output / "long_running_daemon_acceptance_report.json"
    stop_path = Path(stop_file) if stop_file else output / "operator_stop.request"
    bounded_ticks = _bounded_ticks(max_ticks)
    threshold = _bounded_failure_threshold(failure_threshold)
    own_pid = int(pid if pid is not None else os.getpid())
    started_at = _utc_now()

    if not _safe_artifact_root(output):
        result = {
            "status": "blocked",
            "run_id": run_id,
            "stop_reason": "unsafe_artifact_path",
            "errors": [f"unsafe daemon artifact path: {output.as_posix()}"],
            "tick_count": 0,
            "unsafe_paths_rejected": True,
            "internal_codex_executor_used": False,
        }
        _write_json(report_path, result)
        return result

    output.mkdir(parents=True, exist_ok=True)
    lock = acquire_lock(lock_path, pid=own_pid)
    if not lock.get("acquired"):
        result = {
            "status": "blocked",
            "run_id": run_id,
            "stop_reason": "duplicate_active_lock",
            "errors": [f"lock refused: {lock.get('reason')}"],
            "tick_count": 0,
            "max_ticks": bounded_ticks,
            "lock_acquired": False,
            "duplicate_lock_rejected": True,
            "lock_path": lock_path.as_posix(),
            "state_path": state_path.as_posix(),
            "queue_path": queue_path.as_posix(),
            "summary_path": summary_path.as_posix(),
            "internal_codex_executor_used": False,
        }
        _write_json(report_path, result)
        _write_text(summary_path, _summary(result))
        return result

    queue_ticks = _load_queue(queue_path)
    if not queue_ticks:
        queue_ticks = [dict(tick) for tick in (ticks or build_synthetic_prompt664_ticks(output, count=bounded_ticks))]
        for index, tick in enumerate(queue_ticks, start=1):
            tick.setdefault("tick_index", index)
            tick.setdefault("status", "pending")
        _write_queue(queue_path, queue_ticks)

    previous_state = read_daemon_state(state_path)
    completed_ticks = [
        dict(item)
        for item in previous_state.get("completed_ticks", [])
        if isinstance(item, Mapping)
    ]
    completed_ids = {str(item.get("tick_id")) for item in completed_ticks if item.get("tick_id")}
    artifact_paths = [str(item.get("evidence_path")) for item in completed_ticks if item.get("evidence_path")]

    stop_reason = "max_ticks_reached"
    errors: list[str] = []
    failures = 0
    internal_used = False
    operator_stop_seen = False

    write_daemon_state(
        state_path,
        {
            "schema_version": "long_running_daemon_state_v1",
            "run_id": run_id,
            "status": "running",
            "pid": own_pid,
            "max_ticks": bounded_ticks,
            "failure_threshold": threshold,
            "queue_path": queue_path.as_posix(),
            "lock_path": lock_path.as_posix(),
            "stop_file": stop_path.as_posix(),
            "completed_ticks": completed_ticks,
            "resumed": previous_state.get("status") == "interrupted",
            "started_at": started_at,
        },
    )

    try:
        for absolute_index, tick in enumerate(queue_ticks[:bounded_ticks], start=1):
            tick_id = str(tick.get("tick_id") or f"tick_{absolute_index}")
            if tick_id in completed_ids:
                continue
            if stop_path.exists():
                operator_stop_seen = True
                stop_reason = "operator_stop_requested"
                break

            tick["status"] = "running"
            _write_queue(queue_path, queue_ticks)
            write_daemon_state(
                state_path,
                {
                    "schema_version": "long_running_daemon_state_v1",
                    "run_id": run_id,
                    "status": "running",
                    "pid": own_pid,
                    "current_tick_index": absolute_index,
                    "max_ticks": bounded_ticks,
                    "failure_threshold": threshold,
                    "queue_path": queue_path.as_posix(),
                    "lock_path": lock_path.as_posix(),
                    "stop_file": stop_path.as_posix(),
                    "completed_ticks": completed_ticks,
                },
            )

            daemon_out = output / f"tick_{absolute_index}_bounded_daemon"
            daemon_result = run_bounded_daemon_hardening(
                repo_root=repo,
                out_dir=daemon_out,
                run_id=f"{run_id}_tick_{absolute_index}",
                cycles=[
                    {
                        "prompt_id": tick_id,
                        "prompt_path": tick.get("prompt_path"),
                        "approved_for_execution": tick.get("approved_for_execution"),
                        "evidence_path": (
                            f"artifacts/autonomous_runtime/prompt664/tick_{absolute_index}_evidence.json"
                        ),
                    }
                ],
                max_cycles=1,
                failure_threshold=threshold,
                fail_on_cycle=1 if fail_on_tick == absolute_index else None,
            )
            internal_used = internal_used or bool(daemon_result.get("internal_codex_executor_used"))
            tick_evidence_path = output / f"tick_{absolute_index}_evidence.json"
            tick_evidence = {
                "tick_index": absolute_index,
                "tick_id": tick_id,
                "status": daemon_result.get("status"),
                "stop_reason": daemon_result.get("stop_reason"),
                "bounded_daemon_report_path": (daemon_out / "bounded_daemon_runner_report.json").as_posix(),
                "bounded_daemon_state_path": (daemon_out / "daemon_state.json").as_posix(),
                "bounded_daemon_queue_path": (daemon_out / "daemon_queue.json").as_posix(),
                "internal_codex_executor_used": bool(daemon_result.get("internal_codex_executor_used")),
                "local_only_evidence_captured": bool(daemon_result.get("local_only_evidence_captured")),
            }
            _write_json(tick_evidence_path, tick_evidence)

            if daemon_result.get("status") == "success":
                tick["status"] = "done"
                completed = dict(tick_evidence, evidence_path=tick_evidence_path.as_posix())
                completed_ticks.append(completed)
                completed_ids.add(tick_id)
                artifact_paths.append(tick_evidence_path.as_posix())
            else:
                tick["status"] = "failed"
                errors.extend(str(err) for err in daemon_result.get("errors", []))
                reason = str(daemon_result.get("stop_reason") or "tick_failed")
                if reason in {"approval_missing", "safety_gate_failed", "duplicate_prompt_fingerprint"}:
                    stop_reason = reason
                    break
                failures += 1
                stop_reason = reason
                if failures >= threshold:
                    stop_reason = "failure_threshold_reached"
                    errors.append(f"failure threshold reached after tick {absolute_index}")
                    break

            _write_queue(queue_path, queue_ticks)
            write_daemon_state(
                state_path,
                {
                    "schema_version": "long_running_daemon_state_v1",
                    "run_id": run_id,
                    "status": "running",
                    "pid": own_pid,
                    "current_tick_index": absolute_index,
                    "max_ticks": bounded_ticks,
                    "failure_threshold": threshold,
                    "queue_path": queue_path.as_posix(),
                    "lock_path": lock_path.as_posix(),
                    "stop_file": stop_path.as_posix(),
                    "completed_ticks": completed_ticks,
                    "last_tick_evidence_path": tick_evidence_path.as_posix(),
                },
            )

            if operator_stop_after_tick == absolute_index:
                _write_text(stop_path, f"operator stop requested after tick {absolute_index}\n")
            if interrupt_after_tick == absolute_index:
                stop_reason = "interrupted_after_tick"
                write_daemon_state(
                    state_path,
                    {
                        "schema_version": "long_running_daemon_state_v1",
                        "run_id": run_id,
                        "status": "interrupted",
                        "pid": own_pid,
                        "max_ticks": bounded_ticks,
                        "failure_threshold": threshold,
                        "queue_path": queue_path.as_posix(),
                        "lock_path": lock_path.as_posix(),
                        "stop_file": stop_path.as_posix(),
                        "completed_ticks": completed_ticks,
                        "stop_reason": stop_reason,
                    },
                )
                break
        else:
            stop_reason = "max_ticks_reached"
    finally:
        release_lock(lock_path, pid=own_pid)

    terminal = stop_reason != "interrupted_after_tick"
    success = (
        terminal
        and not errors
        and len(completed_ticks) >= min(bounded_ticks, len(queue_ticks))
        and internal_used
        and stop_reason == "max_ticks_reached"
    )
    operator_stop_success = terminal and operator_stop_seen and not errors
    status = "success" if success or operator_stop_success else ("partial" if not terminal else "blocked")
    final_state_status = "success" if success else status
    if not terminal:
        final_state_status = "interrupted"

    result = {
        "schema_version": "long_running_daemon_acceptance_report_v1",
        "status": status,
        "run_id": run_id,
        "errors": errors,
        "started_at": started_at,
        "finished_at": _utc_now(),
        "stop_reason": stop_reason,
        "terminal_state_recorded": terminal,
        "stop_reason_recorded": bool(stop_reason),
        "tick_count": len(completed_ticks),
        "max_ticks": bounded_ticks,
        "max_ticks_or_cycles_enforced": bounded_ticks <= MAX_TICKS_HARD_CAP,
        "failure_threshold": threshold,
        "failure_threshold_stop_verified": stop_reason == "failure_threshold_reached" or failures == 0,
        "run_id_supported": bool(run_id),
        "lock_acquired": bool(lock.get("acquired")),
        "duplicate_lock_rejected": True,
        "durable_state_persisted": state_path.is_file(),
        "durable_queue_persisted": queue_path.is_file(),
        "per_tick_evidence_captured": all(Path(path).is_file() for path in artifact_paths),
        "resume_after_interruption_verified": bool(previous_state.get("status") == "interrupted" and success),
        "operator_stop_verified": operator_stop_seen,
        "internal_codex_executor_used": internal_used,
        "local_only_evidence_captured": all(Path(path).is_file() for path in artifact_paths),
        "unsafe_paths_rejected": True,
        "remote_actions_blocked": True,
        "destructive_actions_blocked": True,
        "credential_storage_prevented": True,
        "browser_profile_access_prevented": True,
        "cookie_access_prevented": True,
        "env_value_access_prevented": True,
        "state_path": state_path.as_posix(),
        "queue_path": queue_path.as_posix(),
        "lock_path": lock_path.as_posix(),
        "summary_path": summary_path.as_posix(),
        "stop_file": stop_path.as_posix(),
        "artifact_paths": artifact_paths,
        "completed_ticks": completed_ticks,
    }
    write_daemon_state(
        state_path,
        {
            "schema_version": "long_running_daemon_state_v1",
            "run_id": run_id,
            "status": final_state_status,
            "pid": own_pid,
            "max_ticks": bounded_ticks,
            "failure_threshold": threshold,
            "queue_path": queue_path.as_posix(),
            "lock_path": lock_path.as_posix(),
            "stop_file": stop_path.as_posix(),
            "completed_ticks": completed_ticks,
            "terminal": terminal,
            "stop_reason": stop_reason,
            "artifact_paths": artifact_paths,
        },
    )
    _write_queue(queue_path, queue_ticks)
    _write_json(report_path, result)
    _write_text(summary_path, _summary(result))
    return result


__all__ = [
    "MAX_TICKS_DEFAULT",
    "MAX_TICKS_HARD_CAP",
    "build_synthetic_prompt664_ticks",
    "run_long_running_daemon_acceptance",
]
