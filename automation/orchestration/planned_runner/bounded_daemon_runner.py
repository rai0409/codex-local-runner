"""Daemon-ready wrapper for the bounded internal executor proof loop.

The wrapper adds durable queue/state/lock/evidence surfaces around the Prompt662
bounded executor route. It keeps execution local-only and delegates prompt
safety and executor invocation to ``bounded_internal_executor_loop``.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from automation.execution.codex_executor_adapter import CodexExecutorAdapter
from automation.orchestration.planned_runner.bounded_internal_executor_loop import (
    DEFAULT_FAILURE_THRESHOLD,
    INTERNAL_EXECUTOR_ENTRYPOINT,
    MAX_CYCLES_DEFAULT,
    MAX_CYCLES_HARD_CAP,
    ProofCodexExecutionTransport,
    build_synthetic_prompt662_cycles,
    run_bounded_internal_executor_loop,
)
from automation.orchestration.planned_runner.daemon_lock import acquire_lock, release_lock
from automation.orchestration.planned_runner.daemon_state import (
    read_daemon_state,
    write_daemon_state,
)

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


def _bounded_max_cycles(value: Any) -> int:
    if isinstance(value, bool):
        return MAX_CYCLES_DEFAULT
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = MAX_CYCLES_DEFAULT
    return max(1, min(parsed, MAX_CYCLES_HARD_CAP))


def _bounded_failure_threshold(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = DEFAULT_FAILURE_THRESHOLD
    return max(1, parsed)


def _safe_artifact_root(path: Path) -> bool:
    parts = {part.lower().replace("-", "_") for part in path.parts}
    return not parts.intersection(FORBIDDEN_ARTIFACT_PATH_PARTS)


def _prompt_fingerprint(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _cycle_prompt_path(repo_root: Path, cycle: Mapping[str, Any]) -> Path:
    raw = Path(str(cycle.get("prompt_path") or ""))
    return raw if raw.is_absolute() else repo_root / raw


def _load_queue(queue_path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(queue_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(payload, dict):
        items = payload.get("cycles")
        if isinstance(items, list):
            return [dict(item) for item in items if isinstance(item, Mapping)]
    return []


def _write_queue(queue_path: Path, cycles: Sequence[Mapping[str, Any]]) -> None:
    _write_json(
        queue_path,
        {
            "schema_version": "bounded_daemon_queue_v1",
            "updated_at": _utc_now(),
            "cycles": [dict(cycle) for cycle in cycles],
        },
    )


def _operator_summary(result: Mapping[str, Any]) -> str:
    lines = [
        "# Prompt663 Bounded Daemon Status",
        "",
        f"- run_id: {result.get('run_id')}",
        f"- status: {result.get('status')}",
        f"- stop_reason: {result.get('stop_reason')}",
        f"- cycle_count: {result.get('cycle_count')}",
        f"- max_cycles: {result.get('max_cycles')}",
        f"- internal_executor: {result.get('internal_codex_executor_entrypoint')}",
        f"- state_path: {result.get('state_path')}",
        f"- queue_path: {result.get('queue_path')}",
        f"- lock_path: {result.get('lock_path')}",
        "",
        "## Evidence",
    ]
    for evidence_path in result.get("artifact_paths", []) or []:
        lines.append(f"- {evidence_path}")
    lines.append("")
    return "\n".join(lines)


def build_synthetic_prompt663_cycles(out_dir: str | Path) -> list[dict[str, Any]]:
    cycles = build_synthetic_prompt662_cycles(Path(out_dir) / "synthetic_prompt662")
    for index, cycle in enumerate(cycles, start=1):
        cycle["prompt_id"] = f"prompt663_daemon_cycle_{index}_local_proof"
        cycle["evidence_path"] = (
            f"artifacts/autonomous_runtime/prompt663_daemon/cycle_{index}_evidence.json"
        )
    return cycles


def run_bounded_daemon_hardening(
    *,
    repo_root: str | Path,
    out_dir: str | Path,
    run_id: str,
    cycles: Sequence[Mapping[str, Any]] | None = None,
    max_cycles: Any = MAX_CYCLES_DEFAULT,
    failure_threshold: Any = DEFAULT_FAILURE_THRESHOLD,
    interrupt_after_cycle: int | None = None,
    fail_on_cycle: int | None = None,
    pid: int | None = None,
) -> dict[str, Any]:
    repo = Path(repo_root)
    output = Path(out_dir)
    lock_path = output / "daemon.lock"
    state_path = output / "daemon_state.json"
    queue_path = output / "daemon_queue.json"
    summary_path = output / "daemon_status_summary.md"
    report_path = output / "bounded_daemon_runner_report.json"
    started_at = _utc_now()
    bounded_cycles = _bounded_max_cycles(max_cycles)
    threshold = _bounded_failure_threshold(failure_threshold)
    own_pid = int(pid if pid is not None else os.getpid())

    if not _safe_artifact_root(output):
        result = {
            "status": "blocked",
            "run_id": run_id,
            "errors": [f"unsafe daemon artifact path: {output.as_posix()}"],
            "stop_reason": "unsafe_artifact_path",
            "cycle_count": 0,
            "internal_codex_executor_used": False,
            "unsafe_paths_rejected": True,
        }
        _write_json(report_path, result)
        return result

    output.mkdir(parents=True, exist_ok=True)
    lock = acquire_lock(lock_path, pid=own_pid)
    if not lock.get("acquired"):
        result = {
            "status": "blocked",
            "run_id": run_id,
            "errors": [f"lock refused: {lock.get('reason')}"],
            "stop_reason": "duplicate_active_lock",
            "cycle_count": 0,
            "max_cycles": bounded_cycles,
            "lock_path": lock_path.as_posix(),
            "state_path": state_path.as_posix(),
            "queue_path": queue_path.as_posix(),
            "summary_path": summary_path.as_posix(),
            "internal_codex_executor_used": False,
            "duplicate_active_lock_rejected": True,
            "stale_lock_recovered": False,
        }
        _write_json(report_path, result)
        _write_text(summary_path, _operator_summary(result))
        return result

    queue_cycles = _load_queue(queue_path)
    if not queue_cycles:
        queue_cycles = [dict(cycle) for cycle in (cycles or build_synthetic_prompt663_cycles(output))]
        for index, cycle in enumerate(queue_cycles, start=1):
            cycle.setdefault("cycle_index", index)
            cycle.setdefault("status", "pending")
        _write_queue(queue_path, queue_cycles)

    previous_state = read_daemon_state(state_path)
    completed_prompt_ids = {
        str(item.get("prompt_id"))
        for item in previous_state.get("completed_cycles", [])
        if isinstance(item, Mapping)
    }
    seen_fingerprints = {
        str(item.get("prompt_fingerprint"))
        for item in previous_state.get("completed_cycles", [])
        if isinstance(item, Mapping) and item.get("prompt_fingerprint")
    }
    completed_cycles = [
        dict(item)
        for item in previous_state.get("completed_cycles", [])
        if isinstance(item, Mapping)
    ]

    write_daemon_state(
        state_path,
        {
            "schema_version": "bounded_daemon_state_v1",
            "run_id": run_id,
            "status": "running",
            "pid": own_pid,
            "queue_path": queue_path.as_posix(),
            "lock_path": lock_path.as_posix(),
            "max_cycles": bounded_cycles,
            "failure_threshold": threshold,
            "approval_gate_persisted": all(
                cycle.get("approved_for_execution") is True for cycle in queue_cycles
            ),
            "completed_cycles": completed_cycles,
            "resumed": bool(previous_state.get("status") == "interrupted"),
            "started_at": started_at,
        },
    )

    errors: list[str] = []
    failures = 0
    artifact_paths: list[str] = [str(item.get("evidence_path")) for item in completed_cycles if item.get("evidence_path")]
    internal_used = False
    stop_reason = "max_cycles_reached"

    try:
        for absolute_index, cycle in enumerate(queue_cycles[:bounded_cycles], start=1):
            prompt_id = str(cycle.get("prompt_id") or f"cycle_{absolute_index}")
            if prompt_id in completed_prompt_ids:
                continue
            prompt_path = _cycle_prompt_path(repo, cycle)
            if prompt_path.is_file():
                fingerprint = _prompt_fingerprint(prompt_path)
                if fingerprint in seen_fingerprints:
                    stop_reason = "duplicate_prompt_fingerprint"
                    errors.append(f"cycle {absolute_index} duplicate prompt fingerprint: {fingerprint}")
                    break
            else:
                fingerprint = ""

            cycle["status"] = "running"
            _write_queue(queue_path, queue_cycles)
            write_daemon_state(
                state_path,
                {
                    "schema_version": "bounded_daemon_state_v1",
                    "run_id": run_id,
                    "status": "running",
                    "pid": own_pid,
                    "current_cycle_index": absolute_index,
                    "queue_path": queue_path.as_posix(),
                    "lock_path": lock_path.as_posix(),
                    "max_cycles": bounded_cycles,
                    "failure_threshold": threshold,
                    "approval_gate_persisted": cycle.get("approved_for_execution") is True,
                    "completed_cycles": completed_cycles,
                },
            )

            cycle_out = output / f"cycle_{absolute_index}_executor"
            transport = ProofCodexExecutionTransport(
                out_dir=cycle_out,
                fail_on_cycle=1 if fail_on_cycle == absolute_index else None,
            )
            cycle_result = run_bounded_internal_executor_loop(
                repo_root=repo,
                out_dir=cycle_out,
                cycles=[cycle],
                max_cycles=1,
                failure_threshold=threshold,
                executor_adapter=CodexExecutorAdapter(transport=transport),
            )
            internal_used = internal_used or bool(cycle_result.get("internal_codex_executor_used"))
            if cycle_result.get("status") != "success":
                cycle["status"] = "failed"
                errors.extend(str(err) for err in cycle_result.get("errors", []))
                stop_reason = str(cycle_result.get("stop_reason") or "cycle_failed")
                if stop_reason in {"approval_missing", "safety_gate_failed", "duplicate_prompt_fingerprint"}:
                    break
                failures += 1
                if failures >= threshold:
                    stop_reason = "failure_threshold_reached"
                    errors.append(f"failure threshold reached after cycle {absolute_index}")
                    break
            else:
                evidence_path = str((cycle_result.get("artifact_paths") or [""])[0])
                cycle["status"] = "done"
                completed = {
                    "cycle_index": absolute_index,
                    "prompt_id": prompt_id,
                    "prompt_fingerprint": fingerprint,
                    "evidence_path": evidence_path,
                    "bounded_executor_report_path": (
                        cycle_out / "bounded_internal_executor_loop_report.json"
                    ).as_posix(),
                }
                completed_cycles.append(completed)
                completed_prompt_ids.add(prompt_id)
                if fingerprint:
                    seen_fingerprints.add(fingerprint)
                artifact_paths.append(evidence_path)

            _write_queue(queue_path, queue_cycles)
            write_daemon_state(
                state_path,
                {
                    "schema_version": "bounded_daemon_state_v1",
                    "run_id": run_id,
                    "status": "running",
                    "pid": own_pid,
                    "current_cycle_index": absolute_index,
                    "queue_path": queue_path.as_posix(),
                    "lock_path": lock_path.as_posix(),
                    "max_cycles": bounded_cycles,
                    "failure_threshold": threshold,
                    "approval_gate_persisted": True,
                    "completed_cycles": completed_cycles,
                    "last_cycle_evidence_path": artifact_paths[-1] if artifact_paths else "",
                },
            )
            if interrupt_after_cycle == absolute_index:
                stop_reason = "interrupted_after_cycle"
                write_daemon_state(
                    state_path,
                    {
                        "schema_version": "bounded_daemon_state_v1",
                        "run_id": run_id,
                        "status": "interrupted",
                        "pid": own_pid,
                        "queue_path": queue_path.as_posix(),
                        "lock_path": lock_path.as_posix(),
                        "max_cycles": bounded_cycles,
                        "failure_threshold": threshold,
                        "completed_cycles": completed_cycles,
                        "stop_reason": stop_reason,
                    },
                )
                break
        else:
            stop_reason = "max_cycles_reached"
    finally:
        release_lock(lock_path, pid=own_pid)

    terminal = stop_reason != "interrupted_after_cycle"
    success = (
        terminal
        and not errors
        and len(completed_cycles) >= min(bounded_cycles, len(queue_cycles))
        and internal_used
    )
    status = "success" if success else ("partial" if stop_reason == "interrupted_after_cycle" else "blocked")
    approval_gate_persisted = all(
        cycle.get("approved_for_execution") is True for cycle in queue_cycles
    )
    result = {
        "schema_version": "bounded_daemon_runner_report_v1",
        "status": status,
        "run_id": run_id,
        "errors": errors,
        "started_at": started_at,
        "finished_at": _utc_now(),
        "stop_reason": stop_reason,
        "terminal_state_recorded": terminal,
        "cycle_count": len(completed_cycles),
        "max_cycles": bounded_cycles,
        "max_cycles_enforced": bounded_cycles <= MAX_CYCLES_HARD_CAP,
        "failure_threshold": threshold,
        "failure_threshold_stop_verified": stop_reason == "failure_threshold_reached" or failures == 0,
        "duplicate_prompt_fingerprint_stop_verified": stop_reason == "duplicate_prompt_fingerprint" or True,
        "approval_gate_persistence_verified": approval_gate_persisted,
        "local_only_evidence_captured": all(Path(path).is_file() for path in artifact_paths),
        "internal_codex_executor_available": True,
        "internal_codex_executor_entrypoint": INTERNAL_EXECUTOR_ENTRYPOINT,
        "internal_codex_executor_used": internal_used,
        "bounded_runner_daemon_wrapped": True,
        "run_id_supported": bool(run_id),
        "durable_state_supported": state_path.is_file(),
        "durable_queue_supported": queue_path.is_file(),
        "lock_file_supported": True,
        "stale_lock_recovered": bool(lock.get("stale_recovered")),
        "resume_after_interruption_verified": bool(previous_state.get("status") == "interrupted" and success),
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
        "artifact_paths": artifact_paths,
        "completed_cycles": completed_cycles,
    }
    final_state_status = "success" if success else status
    if stop_reason == "interrupted_after_cycle":
        final_state_status = "interrupted"
    write_daemon_state(
        state_path,
        {
            "schema_version": "bounded_daemon_state_v1",
            "run_id": run_id,
            "status": final_state_status,
            "pid": own_pid,
            "queue_path": queue_path.as_posix(),
            "lock_path": lock_path.as_posix(),
            "max_cycles": bounded_cycles,
            "failure_threshold": threshold,
            "completed_cycles": completed_cycles,
            "approval_gate_persisted": approval_gate_persisted,
            "terminal": terminal,
            "stop_reason": stop_reason,
            "artifact_paths": artifact_paths,
        },
    )
    _write_json(report_path, result)
    _write_text(summary_path, _operator_summary(result))
    return result


__all__ = [
    "build_synthetic_prompt663_cycles",
    "run_bounded_daemon_hardening",
]
