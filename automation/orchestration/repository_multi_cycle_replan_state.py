"""Durable, checksummed state for accepted in-memory REPLAN outcomes."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from automation.orchestration.repository_multi_cycle_replan_runtime import (
    ReplanPlannerResult,
)
from automation.orchestration.repository_multi_cycle_task_spec import (
    load_repository_multi_cycle_task_spec,
    validate_repository_multi_cycle_task_spec,
)


SCHEMA_VERSION = "1"
DEFAULT_STATE_ROOT = (
    Path.home() / ".local/state/codex-local-runner/repository-multi-cycle-replans"
)
_SHA256 = re.compile(r"[0-9a-f]{64}")
_COMMIT_SHA = re.compile(r"[0-9a-f]{40}")


class ReplanPersistenceError(ValueError):
    def __init__(self, reason_code: str) -> None:
        self.reason_code = reason_code
        super().__init__(reason_code)


@dataclass(frozen=True)
class ReplanPersistenceInput:
    repository_id: str
    root_queue_spec_sha256: str
    predecessor_queue_spec_sha256: str
    predecessor_cycle_run_id: str
    failed_task_id: str
    failed_task_index: int
    accepted_head_sha: str
    reason_code: str
    detail_reason_code: str | None
    runtime_result: ReplanPlannerResult


@dataclass(frozen=True)
class ReplanPersistenceResult:
    status: str
    reason_code: str
    campaign_id: str | None
    attempt_directory: Path | None
    accepted_replan_path: Path | None
    successor_queue_path: Path | None
    successor_queue_sha256: str | None
    campaign_path: Path | None
    replan_attempt_number: int
    replacement_task_id: str | None


def _canonical_json(value: dict[str, Any]) -> bytes:
    return json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _fsync_directory(directory: Path) -> None:
    try:
        descriptor = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    except OSError:
        return
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_write(path: Path, payload: bytes) -> None:
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        if temporary.exists():
            temporary.unlink()


def _sidecar_payload(path: Path, payload: bytes) -> bytes:
    return f"{_digest(payload)}  {path.name}\n".encode("ascii")


def _write_new_pair(path: Path, payload: bytes) -> None:
    sidecar = path.with_suffix(".sha256")
    if path.exists() or sidecar.exists():
        raise ReplanPersistenceError("replan.persistence.artifact_conflict")
    _atomic_write(path, payload)
    _atomic_write(sidecar, _sidecar_payload(path, payload))


def _load_verified_pair(path: Path, reason_prefix: str) -> tuple[bytes, Any]:
    sidecar = path.with_suffix(".sha256")
    if not path.is_file() or not sidecar.is_file():
        raise ReplanPersistenceError(f"{reason_prefix}.incomplete")
    try:
        payload = path.read_bytes()
        sidecar_text = sidecar.read_text(encoding="ascii")
    except (OSError, UnicodeDecodeError) as exc:
        raise ReplanPersistenceError(f"{reason_prefix}.invalid") from exc
    match = re.fullmatch(r"([0-9a-f]{64})  " + re.escape(path.name) + r"\n", sidecar_text)
    if match is None:
        raise ReplanPersistenceError(f"{reason_prefix}.sidecar_invalid")
    if match.group(1) != _digest(payload):
        raise ReplanPersistenceError(f"{reason_prefix}.hash_mismatch")
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReplanPersistenceError(f"{reason_prefix}.json_invalid") from exc
    return payload, value


def _require_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_accepted(value: Any) -> dict[str, Any]:
    fields = {
        "schema_version",
        "repository_id",
        "campaign_id",
        "root_queue_spec_sha256",
        "predecessor_queue_spec_sha256",
        "predecessor_cycle_run_id",
        "failed_task_id",
        "failed_task_index",
        "replan_attempt_number",
        "reason_code",
        "detail_reason_code",
        "accepted_head_sha",
        "decision",
        "replacement_task_id",
        "planner_call_count",
        "successor_queue_sha256",
        "successor_queue_serialized_content",
        "created_at",
    }
    if not isinstance(value, dict) or set(value) != fields:
        raise ReplanPersistenceError("replan.persistence.accepted.invariant")
    text_fields = (
        "repository_id",
        "campaign_id",
        "predecessor_cycle_run_id",
        "failed_task_id",
        "reason_code",
        "created_at",
    )
    if value.get("schema_version") != SCHEMA_VERSION or not all(
        _require_text(value.get(field)) for field in text_fields
    ):
        raise ReplanPersistenceError("replan.persistence.accepted.invariant")
    if not _SHA256.fullmatch(value.get("campaign_id", "")) or not all(
        _SHA256.fullmatch(value.get(field, ""))
        for field in ("root_queue_spec_sha256", "predecessor_queue_spec_sha256")
    ):
        raise ReplanPersistenceError("replan.persistence.accepted.invariant")
    if not _COMMIT_SHA.fullmatch(value.get("accepted_head_sha", "")):
        raise ReplanPersistenceError("replan.persistence.accepted.invariant")
    if (
        not isinstance(value.get("failed_task_index"), int)
        or isinstance(value.get("failed_task_index"), bool)
        or value["failed_task_index"] < 0
        or not isinstance(value.get("replan_attempt_number"), int)
        or isinstance(value.get("replan_attempt_number"), bool)
        or not 1 <= value["replan_attempt_number"] <= 999
        or value.get("planner_call_count") not in (1, 2)
        or (value.get("detail_reason_code") is not None and not _require_text(value["detail_reason_code"]))
    ):
        raise ReplanPersistenceError("replan.persistence.accepted.invariant")
    decision = value.get("decision")
    if decision == "replace_failed_task":
        if (
            not _require_text(value.get("replacement_task_id"))
            or not isinstance(value.get("successor_queue_serialized_content"), str)
            or not _SHA256.fullmatch(value.get("successor_queue_sha256", ""))
            or _digest(value["successor_queue_serialized_content"].encode("utf-8"))
            != value["successor_queue_sha256"]
        ):
            raise ReplanPersistenceError("replan.persistence.accepted.invariant")
        try:
            validate_repository_multi_cycle_task_spec(
                json.loads(value["successor_queue_serialized_content"])
            )
        except (json.JSONDecodeError, ValueError) as exc:
            raise ReplanPersistenceError(
                "replan.persistence.accepted.invariant"
            ) from exc
    elif decision == "stop":
        if any(
            value.get(field) is not None
            for field in (
                "replacement_task_id",
                "successor_queue_sha256",
                "successor_queue_serialized_content",
            )
        ):
            raise ReplanPersistenceError("replan.persistence.accepted.invariant")
    else:
        raise ReplanPersistenceError("replan.persistence.accepted.invariant")
    return value


def load_verified_accepted_replan(attempt_directory: str | Path) -> dict[str, Any]:
    _, value = _load_verified_pair(
        Path(attempt_directory) / "accepted_replan.json",
        "replan.persistence.accepted",
    )
    return _validate_accepted(value)


def _campaign_id(repository_id: str, root_queue_sha256: str) -> str:
    return _digest(
        _canonical_json(
            {"repository_id": repository_id, "root_queue_spec_sha256": root_queue_sha256}
        )
    )


def _expected_accepted(
    value: ReplanPersistenceInput, campaign_id: str, created_at: str
) -> dict[str, Any]:
    runtime = value.runtime_result
    decision = "replace_failed_task" if runtime.status == "successor_ready" else "stop"
    return {
        "schema_version": SCHEMA_VERSION,
        "repository_id": value.repository_id,
        "campaign_id": campaign_id,
        "root_queue_spec_sha256": value.root_queue_spec_sha256,
        "predecessor_queue_spec_sha256": value.predecessor_queue_spec_sha256,
        "predecessor_cycle_run_id": value.predecessor_cycle_run_id,
        "failed_task_id": value.failed_task_id,
        "failed_task_index": value.failed_task_index,
        "replan_attempt_number": runtime.replan_attempt_number,
        "reason_code": value.reason_code,
        "detail_reason_code": value.detail_reason_code,
        "accepted_head_sha": value.accepted_head_sha,
        "decision": decision,
        "replacement_task_id": runtime.replacement_task_id,
        "planner_call_count": runtime.planner_call_count,
        "successor_queue_sha256": runtime.successor_queue_sha256,
        "successor_queue_serialized_content": runtime.serialized_successor_queue,
        "created_at": created_at,
    }


def _validate_input(value: ReplanPersistenceInput) -> None:
    runtime = value.runtime_result
    if runtime.status not in {"successor_ready", "stop", "blocked"}:
        raise ReplanPersistenceError("replan.persistence.runtime_status_invalid")
    if not _require_text(value.repository_id) or not all(
        _require_text(item)
        for item in (value.predecessor_cycle_run_id, value.failed_task_id, value.reason_code)
    ):
        raise ReplanPersistenceError("replan.persistence.input_invalid")
    if not all(
        _SHA256.fullmatch(item)
        for item in (value.root_queue_spec_sha256, value.predecessor_queue_spec_sha256)
    ) or not _COMMIT_SHA.fullmatch(value.accepted_head_sha):
        raise ReplanPersistenceError("replan.persistence.input_invalid")
    if (
        not isinstance(value.failed_task_index, int)
        or isinstance(value.failed_task_index, bool)
        or value.failed_task_index < 0
        or not isinstance(runtime.replan_attempt_number, int)
        or isinstance(runtime.replan_attempt_number, bool)
        or not 1 <= runtime.replan_attempt_number <= 999
    ):
        raise ReplanPersistenceError("replan.persistence.input_invalid")
    if runtime.status == "successor_ready":
        if (
            runtime.successor_queue is None
            or not _require_text(runtime.replacement_task_id)
            or not isinstance(runtime.serialized_successor_queue, str)
            or not _SHA256.fullmatch(runtime.successor_queue_sha256 or "")
            or _digest(runtime.serialized_successor_queue.encode("utf-8"))
            != runtime.successor_queue_sha256
        ):
            raise ReplanPersistenceError("replan.persistence.runtime_result_invalid")
        try:
            parsed = json.loads(runtime.serialized_successor_queue)
        except json.JSONDecodeError as exc:
            raise ReplanPersistenceError("replan.persistence.runtime_result_invalid") from exc
        # Validate the exact serialized protocol without creating authoritative bytes.
        if validate_repository_multi_cycle_task_spec(parsed) != runtime.successor_queue:
            raise ReplanPersistenceError("replan.persistence.runtime_result_invalid")
    elif runtime.status == "stop" and any(
        item is not None
        for item in (
            runtime.replacement_task_id,
            runtime.successor_queue,
            runtime.serialized_successor_queue,
            runtime.successor_queue_sha256,
        )
    ):
        raise ReplanPersistenceError("replan.persistence.runtime_result_invalid")


def _verify_successor(path: Path, accepted: dict[str, Any]) -> None:
    payload, _ = _load_verified_pair(path, "replan.persistence.successor")
    if _digest(payload) != accepted["successor_queue_sha256"]:
        raise ReplanPersistenceError("replan.persistence.successor.authority_conflict")
    try:
        load_repository_multi_cycle_task_spec(path)
    except ValueError as exc:
        raise ReplanPersistenceError("replan.persistence.successor.queue_invalid") from exc


def _campaign(accepted: dict[str, Any]) -> dict[str, Any]:
    replacement = accepted["decision"] == "replace_failed_task"
    return {
        "schema_version": SCHEMA_VERSION,
        "repository_id": accepted["repository_id"],
        "campaign_id": accepted["campaign_id"],
        "root_queue_spec_sha256": accepted["root_queue_spec_sha256"],
        "current_queue_spec_sha256": accepted["successor_queue_sha256"] if replacement else None,
        "replan_attempt_count": accepted["replan_attempt_number"],
        "current_attempt_number": accepted["replan_attempt_number"],
        "predecessor_cycle_run_id": accepted["predecessor_cycle_run_id"],
        "failed_task_id": accepted["failed_task_id"],
        "accepted_head_sha": accepted["accepted_head_sha"],
        "decision": accepted["decision"],
        "successor_queue_path": "successor_queue.json" if replacement else None,
        "successor_queue_sha256": accepted["successor_queue_sha256"] if replacement else None,
        "state": "successor_ready" if replacement else "stopped",
        "updated_at": accepted["created_at"],
    }


def _validate_campaign(value: Any, accepted: dict[str, Any]) -> dict[str, Any]:
    expected = _campaign(accepted)
    if not isinstance(value, dict) or value != expected:
        raise ReplanPersistenceError("replan.persistence.campaign.authority_conflict")
    return value


def load_verified_campaign_state(attempt_directory: str | Path) -> dict[str, Any]:
    attempt = Path(attempt_directory)
    accepted = load_verified_accepted_replan(attempt)
    _, value = _load_verified_pair(
        attempt / "campaign.json", "replan.persistence.campaign"
    )
    return _validate_campaign(value, accepted)


def persist_replan_result(
    value: ReplanPersistenceInput,
    *,
    state_root: str | Path = DEFAULT_STATE_ROOT,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> ReplanPersistenceResult:
    """Persist accepted R6-B1 authority and recover its derived artifacts."""

    runtime = value.runtime_result
    if runtime.status == "blocked":
        return ReplanPersistenceResult(
            "blocked", runtime.reason_code, None, None, None, None, None, None,
            runtime.replan_attempt_number, None,
        )
    try:
        _validate_input(value)
        campaign_id = _campaign_id(value.repository_id, value.root_queue_spec_sha256)
        repository_namespace = _digest(value.repository_id.encode("utf-8"))
        attempt = (
            Path(state_root)
            / repository_namespace
            / campaign_id
            / f"attempt-{runtime.replan_attempt_number:03d}"
        )
        attempt.mkdir(parents=True, exist_ok=True)
        _fsync_directory(attempt.parent)
        accepted_path = attempt / "accepted_replan.json"
        if accepted_path.exists() or accepted_path.with_suffix(".sha256").exists():
            accepted = load_verified_accepted_replan(attempt)
            expected = _expected_accepted(value, campaign_id, accepted["created_at"])
            if accepted != expected:
                raise ReplanPersistenceError("replan.persistence.accepted.caller_conflict")
        else:
            created_at = now().astimezone(timezone.utc).isoformat()
            accepted = _expected_accepted(value, campaign_id, created_at)
            _validate_accepted(accepted)
            _write_new_pair(accepted_path, _canonical_json(accepted))
            accepted = load_verified_accepted_replan(attempt)

        successor_path: Path | None = None
        if accepted["decision"] == "replace_failed_task":
            successor_path = attempt / "successor_queue.json"
            successor_sidecar = successor_path.with_suffix(".sha256")
            if successor_path.exists() or successor_sidecar.exists():
                _verify_successor(successor_path, accepted)
            else:
                queue_payload = accepted["successor_queue_serialized_content"].encode("utf-8")
                if _digest(queue_payload) != accepted["successor_queue_sha256"]:
                    raise ReplanPersistenceError("replan.persistence.successor.authority_conflict")
                _write_new_pair(successor_path, queue_payload)
                _verify_successor(successor_path, accepted)

        campaign_path = attempt / "campaign.json"
        campaign_sidecar = campaign_path.with_suffix(".sha256")
        if campaign_path.exists() or campaign_sidecar.exists():
            load_verified_campaign_state(attempt)
        else:
            _write_new_pair(campaign_path, _canonical_json(_campaign(accepted)))
            load_verified_campaign_state(attempt)
        return ReplanPersistenceResult(
            "successor_ready" if successor_path else "stopped",
            "replan.persistence.ready" if successor_path else "replan.persistence.stopped",
            campaign_id,
            attempt,
            accepted_path,
            successor_path,
            accepted["successor_queue_sha256"],
            campaign_path,
            accepted["replan_attempt_number"],
            accepted["replacement_task_id"],
        )
    except ReplanPersistenceError as exc:
        return ReplanPersistenceResult(
            "blocked", exc.reason_code, None, None, None, None, None, None,
            runtime.replan_attempt_number, None,
        )


__all__ = [
    "DEFAULT_STATE_ROOT",
    "ReplanPersistenceError",
    "ReplanPersistenceInput",
    "ReplanPersistenceResult",
    "load_verified_accepted_replan",
    "load_verified_campaign_state",
    "persist_replan_result",
]
