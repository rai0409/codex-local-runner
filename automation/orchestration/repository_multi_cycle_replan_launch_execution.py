"""Crash-conservative execution transactions for durable replan launch claims."""

from __future__ import annotations

import fcntl
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from automation.orchestration.repository_multi_cycle_replan_launch import (
    ReplanLaunchClaimError,
    ReplanLaunchClaimInput,
    ReplanLaunchClaimResult,
    load_verified_replan_launch_claim,
)
from automation.orchestration.repository_multi_cycle_replan_state import (
    ReplanPersistenceError,
    _atomic_write,
    _canonical_json,
    _digest,
)


SCHEMA_VERSION = "1"
_SHA256 = re.compile(r"[0-9a-f]{64}")
_CYCLE_RUN_ID = re.compile(r"cycle-[0-9]{20}")
_FIELDS = {
    "schema_version",
    "repository_id",
    "campaign_id",
    "replan_attempt_number",
    "launch_id",
    "launch_attempt_id",
    "accepted_head_sha",
    "successor_queue_path",
    "successor_queue_sha256",
    "state",
    "started_at",
    "launched_at",
    "worker_pid",
    "cycle_run_id",
    "uncertain_reason_code",
}


class ReplanLaunchExecutionError(ValueError):
    def __init__(self, reason_code: str) -> None:
        self.reason_code = reason_code
        super().__init__(reason_code)


@dataclass(frozen=True)
class ReplanLaunchExecutionInput:
    claim_input: ReplanLaunchClaimInput
    claim_result: ReplanLaunchClaimResult


@dataclass(frozen=True)
class WorkerLaunchRequest:
    repository_id: str
    campaign_id: str
    replan_attempt_number: int
    launch_id: str
    launch_attempt_id: str
    accepted_head_sha: str
    successor_queue_path: Path
    successor_queue_sha256: str


@dataclass(frozen=True)
class WorkerLaunchResult:
    status: str
    worker_pid: int | None = None
    cycle_run_id: str | None = None


@dataclass(frozen=True)
class ReplanLaunchExecutionResult:
    status: str
    reason_code: str
    launch_id: str | None
    launch_attempt_id: str | None
    execution_path: Path | None
    successor_queue_path: Path | None
    successor_queue_sha256: str | None
    worker_pid: int | None
    cycle_run_id: str | None
    launcher_call_count: int


WorkerLauncher = Callable[[WorkerLaunchRequest], WorkerLaunchResult]


def _blocked(reason_code: str) -> ReplanLaunchExecutionResult:
    return ReplanLaunchExecutionResult(
        "blocked", reason_code, None, None, None, None, None, None, None, 0
    )


def _launch_attempt_id(launch_id: str) -> str:
    return _digest(_canonical_json({"launch_id": launch_id}))


def _verified_claim(value: ReplanLaunchExecutionInput) -> ReplanLaunchClaimResult:
    supplied = value.claim_result
    verified = load_verified_replan_launch_claim(value.claim_input)
    if (
        supplied.status != "launch_pending"
        or supplied.repository_id != verified.repository_id
        or supplied.campaign_id != verified.campaign_id
        or supplied.replan_attempt_number != verified.replan_attempt_number
        or supplied.launch_id != verified.launch_id
        or supplied.claim_path != verified.claim_path
        or supplied.accepted_head_sha != verified.accepted_head_sha
        or supplied.successor_queue_path != verified.successor_queue_path
        or supplied.successor_queue_sha256 != verified.successor_queue_sha256
    ):
        raise ReplanLaunchExecutionError("replan.launch.execution.claim_conflict")
    return verified


def _base_record(claim: ReplanLaunchClaimResult, started_at: str) -> dict[str, Any]:
    assert claim.launch_id is not None
    assert claim.repository_id is not None
    assert claim.campaign_id is not None
    assert claim.replan_attempt_number is not None
    assert claim.accepted_head_sha is not None
    assert claim.successor_queue_sha256 is not None
    return {
        "schema_version": SCHEMA_VERSION,
        "repository_id": claim.repository_id,
        "campaign_id": claim.campaign_id,
        "replan_attempt_number": claim.replan_attempt_number,
        "launch_id": claim.launch_id,
        "launch_attempt_id": _launch_attempt_id(claim.launch_id),
        "accepted_head_sha": claim.accepted_head_sha,
        "successor_queue_path": "successor_queue.json",
        "successor_queue_sha256": claim.successor_queue_sha256,
        "state": "launching",
        "started_at": started_at,
        "launched_at": None,
        "worker_pid": None,
        "cycle_run_id": None,
        "uncertain_reason_code": None,
    }


def _validate_record(value: Any, claim: ReplanLaunchClaimResult) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != _FIELDS:
        raise ReplanLaunchExecutionError("replan.launch.execution.invariant")
    expected = _base_record(claim, value.get("started_at"))
    identity_fields = _FIELDS - {
        "state", "launched_at", "worker_pid", "cycle_run_id", "uncertain_reason_code"
    }
    if (
        not isinstance(value.get("started_at"), str)
        or not value["started_at"]
        or any(value.get(field) != expected[field] for field in identity_fields)
    ):
        raise ReplanLaunchExecutionError("replan.launch.execution.identity_conflict")
    state = value.get("state")
    worker_pid = value.get("worker_pid")
    cycle_run_id = value.get("cycle_run_id")
    if worker_pid is not None and (
        not isinstance(worker_pid, int) or isinstance(worker_pid, bool) or worker_pid <= 0
    ):
        raise ReplanLaunchExecutionError("replan.launch.execution.invariant")
    if cycle_run_id is not None and (
        not isinstance(cycle_run_id, str) or not _CYCLE_RUN_ID.fullmatch(cycle_run_id)
    ):
        raise ReplanLaunchExecutionError("replan.launch.execution.invariant")
    if state == "launching":
        if any(
            value.get(field) is not None
            for field in ("launched_at", "worker_pid", "cycle_run_id", "uncertain_reason_code")
        ):
            raise ReplanLaunchExecutionError("replan.launch.execution.invariant")
    elif state == "launched":
        if (
            not isinstance(value.get("launched_at"), str)
            or not value["launched_at"]
            or value.get("uncertain_reason_code") is not None
        ):
            raise ReplanLaunchExecutionError("replan.launch.execution.invariant")
    elif state == "launch_uncertain":
        if (
            value.get("launched_at") is not None
            or value.get("worker_pid") is not None
            or value.get("cycle_run_id") is not None
            or value.get("uncertain_reason_code") != "replan.launch.execution_uncertain"
        ):
            raise ReplanLaunchExecutionError("replan.launch.execution.invariant")
    else:
        raise ReplanLaunchExecutionError("replan.launch.execution.invariant")
    return value


def _sidecar_payload(path: Path, payload: bytes) -> bytes:
    return f"{_digest(payload)}  {path.name}\n".encode("ascii")


def _write_record(path: Path, value: dict[str, Any]) -> None:
    payload = _canonical_json(value)
    _atomic_write(path, payload)
    _atomic_write(path.with_suffix(".sha256"), _sidecar_payload(path, payload))


def _load_record(path: Path, claim: ReplanLaunchClaimResult) -> dict[str, Any]:
    sidecar = path.with_suffix(".sha256")
    if not path.is_file() or not sidecar.is_file():
        raise ReplanLaunchExecutionError("replan.launch.execution.incomplete")
    try:
        payload = path.read_bytes()
        sidecar_text = sidecar.read_text(encoding="ascii")
    except (OSError, UnicodeDecodeError) as exc:
        raise ReplanLaunchExecutionError("replan.launch.execution.invalid") from exc
    match = re.fullmatch(
        r"([0-9a-f]{64})  " + re.escape(path.name) + r"\n", sidecar_text
    )
    if match is None:
        raise ReplanLaunchExecutionError("replan.launch.execution.sidecar_invalid")
    if match.group(1) != _digest(payload):
        raise ReplanLaunchExecutionError("replan.launch.execution.hash_mismatch")
    try:
        record = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReplanLaunchExecutionError("replan.launch.execution.json_invalid") from exc
    return _validate_record(record, claim)


def _result(
    record: dict[str, Any],
    claim: ReplanLaunchClaimResult,
    path: Path,
    launcher_calls: int,
    *,
    reason_code: str | None = None,
) -> ReplanLaunchExecutionResult:
    state = record["state"]
    status = "launched" if state == "launched" else "launch_uncertain"
    reason = reason_code or (
        "replan.launch.execution_launched"
        if status == "launched"
        else record.get("uncertain_reason_code") or "replan.launch.execution_unreconciled"
    )
    return ReplanLaunchExecutionResult(
        status,
        reason,
        record["launch_id"],
        record["launch_attempt_id"],
        path,
        claim.successor_queue_path,
        claim.successor_queue_sha256,
        record.get("worker_pid"),
        record.get("cycle_run_id"),
        launcher_calls,
    )


def _validate_launcher_result(value: Any) -> WorkerLaunchResult:
    if not isinstance(value, WorkerLaunchResult) or value.status not in {
        "confirmed_started",
        "not_confirmed",
    }:
        raise ReplanLaunchExecutionError("replan.launch.execution_launcher_invalid")
    if value.status == "not_confirmed" and (
        value.worker_pid is not None or value.cycle_run_id is not None
    ):
        raise ReplanLaunchExecutionError("replan.launch.execution_launcher_invalid")
    if value.worker_pid is not None and (
        not isinstance(value.worker_pid, int)
        or isinstance(value.worker_pid, bool)
        or value.worker_pid <= 0
    ):
        raise ReplanLaunchExecutionError("replan.launch.execution_launcher_invalid")
    if value.cycle_run_id is not None and (
        not isinstance(value.cycle_run_id, str)
        or not _CYCLE_RUN_ID.fullmatch(value.cycle_run_id)
    ):
        raise ReplanLaunchExecutionError("replan.launch.execution_launcher_invalid")
    return value


def load_verified_replan_launch_execution(
    value: ReplanLaunchExecutionInput,
) -> ReplanLaunchExecutionResult:
    """Reload verified claim, successor authority, and execution evidence."""

    claim = _verified_claim(value)
    assert claim.claim_path is not None
    path = claim.claim_path.with_name("launch_execution.json")
    record = _load_record(path, claim)
    return _result(record, claim, path, 0)


def execute_replan_launch(
    value: ReplanLaunchExecutionInput,
    *,
    worker_launcher: WorkerLauncher,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> ReplanLaunchExecutionResult:
    """Execute at most one launch call behind durable, checksummed evidence."""

    try:
        claim = _verified_claim(value)
        assert claim.claim_path is not None
        assert claim.successor_queue_path is not None
        execution_path = claim.claim_path.with_name("launch_execution.json")
        lock_descriptor = os.open(claim.claim_path.parent, os.O_RDONLY)
        try:
            fcntl.flock(lock_descriptor, fcntl.LOCK_EX)
            claim = _verified_claim(value)
            if execution_path.exists() or execution_path.with_suffix(".sha256").exists():
                record = _load_record(execution_path, claim)
                if record["state"] == "launching":
                    return _result(
                        record,
                        claim,
                        execution_path,
                        0,
                        reason_code="replan.launch.execution_unreconciled",
                    )
                return _result(record, claim, execution_path, 0)

            started_at = now().astimezone(timezone.utc).isoformat()
            record = _base_record(claim, started_at)
            _write_record(execution_path, record)
            record = _load_record(execution_path, claim)
            request = WorkerLaunchRequest(
                claim.repository_id,
                claim.campaign_id,
                claim.replan_attempt_number,
                claim.launch_id,
                record["launch_attempt_id"],
                claim.accepted_head_sha,
                claim.successor_queue_path,
                claim.successor_queue_sha256,
            )
            try:
                launched = _validate_launcher_result(worker_launcher(request))
            except BaseException:
                uncertain = dict(record)
                uncertain["state"] = "launch_uncertain"
                uncertain["uncertain_reason_code"] = "replan.launch.execution_uncertain"
                _write_record(execution_path, uncertain)
                uncertain = _load_record(execution_path, claim)
                return _result(uncertain, claim, execution_path, 1)

            if launched.status == "not_confirmed":
                uncertain = dict(record)
                uncertain["state"] = "launch_uncertain"
                uncertain["uncertain_reason_code"] = "replan.launch.execution_uncertain"
                _write_record(execution_path, uncertain)
                uncertain = _load_record(execution_path, claim)
                return _result(uncertain, claim, execution_path, 1)

            completed = dict(record)
            completed["state"] = "launched"
            completed["launched_at"] = now().astimezone(timezone.utc).isoformat()
            completed["worker_pid"] = launched.worker_pid
            completed["cycle_run_id"] = launched.cycle_run_id
            _write_record(execution_path, completed)
            completed = _load_record(execution_path, claim)
            return _result(completed, claim, execution_path, 1)
        finally:
            os.close(lock_descriptor)
    except (OSError, ReplanPersistenceError, ReplanLaunchClaimError, ReplanLaunchExecutionError) as exc:
        reason = (
            exc.reason_code
            if isinstance(exc, ReplanLaunchExecutionError)
            else "replan.launch.execution_authority_invalid"
        )
        return _blocked(reason)


__all__ = [
    "ReplanLaunchExecutionError",
    "ReplanLaunchExecutionInput",
    "ReplanLaunchExecutionResult",
    "WorkerLaunchRequest",
    "WorkerLaunchResult",
    "execute_replan_launch",
    "load_verified_replan_launch_execution",
]
