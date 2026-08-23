"""Durable launch claims for verified R6-B2 successor-ready state."""

from __future__ import annotations

import fcntl
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from automation.orchestration.repository_multi_cycle_replan_state import (
    ReplanPersistenceError,
    ReplanPersistenceResult,
    _canonical_json,
    _digest,
    _fsync_directory,
    _verify_successor,
    load_verified_accepted_replan,
    load_verified_campaign_state,
)


SCHEMA_VERSION = "1"
_SHA256 = re.compile(r"[0-9a-f]{64}")
_COMMIT_SHA = re.compile(r"[0-9a-f]{40}")
_CLAIM_FIELDS = {
    "schema_version",
    "repository_id",
    "campaign_id",
    "replan_attempt_number",
    "launch_id",
    "accepted_head_sha",
    "successor_queue_path",
    "successor_queue_sha256",
    "state",
    "created_at",
}


class ReplanLaunchClaimError(ValueError):
    def __init__(self, reason_code: str) -> None:
        self.reason_code = reason_code
        super().__init__(reason_code)


@dataclass(frozen=True)
class ReplanLaunchClaimInput:
    persistence_result: ReplanPersistenceResult
    repository_id: str
    accepted_head_sha: str


@dataclass(frozen=True)
class ReplanLaunchClaimResult:
    status: str
    reason_code: str
    repository_id: str | None
    campaign_id: str | None
    replan_attempt_number: int | None
    launch_id: str | None
    claim_path: Path | None
    successor_queue_path: Path | None
    successor_queue_sha256: str | None
    accepted_head_sha: str | None


@dataclass(frozen=True)
class _VerifiedAuthority:
    attempt_directory: Path
    repository_id: str
    campaign_id: str
    replan_attempt_number: int
    accepted_head_sha: str
    successor_queue_path: Path
    successor_queue_sha256: str
    launch_id: str


def _blocked(reason_code: str) -> ReplanLaunchClaimResult:
    return ReplanLaunchClaimResult(
        "blocked", reason_code, None, None, None, None, None, None, None, None
    )


def _launch_id(
    repository_id: str,
    campaign_id: str,
    replan_attempt_number: int,
    successor_queue_sha256: str,
    accepted_head_sha: str,
) -> str:
    return _digest(
        _canonical_json(
            {
                "accepted_head_sha": accepted_head_sha,
                "campaign_id": campaign_id,
                "replan_attempt_number": replan_attempt_number,
                "repository_id": repository_id,
                "successor_queue_sha256": successor_queue_sha256,
            }
        )
    )


def _verify_authority(value: ReplanLaunchClaimInput) -> _VerifiedAuthority:
    persisted = value.persistence_result
    if persisted.status != "successor_ready":
        raise ReplanLaunchClaimError("replan.launch.not_successor_ready")
    if any(
        item is None
        for item in (
            persisted.attempt_directory,
            persisted.accepted_replan_path,
            persisted.successor_queue_path,
            persisted.successor_queue_sha256,
            persisted.campaign_path,
            persisted.campaign_id,
        )
    ):
        raise ReplanLaunchClaimError("replan.launch.authority_invalid")
    attempt = Path(persisted.attempt_directory)
    accepted = load_verified_accepted_replan(attempt)
    campaign = load_verified_campaign_state(attempt)
    successor = Path(persisted.successor_queue_path)
    _verify_successor(successor, accepted)
    expected_successor = attempt / "successor_queue.json"
    if (
        campaign.get("state") != "successor_ready"
        or campaign.get("decision") != "replace_failed_task"
        or accepted.get("decision") != "replace_failed_task"
        or accepted.get("repository_id") != value.repository_id
        or campaign.get("repository_id") != value.repository_id
        or accepted.get("campaign_id") != persisted.campaign_id
        or campaign.get("campaign_id") != persisted.campaign_id
        or accepted.get("replan_attempt_number") != persisted.replan_attempt_number
        or campaign.get("current_attempt_number") != persisted.replan_attempt_number
        or accepted.get("accepted_head_sha") != value.accepted_head_sha
        or campaign.get("accepted_head_sha") != value.accepted_head_sha
        or accepted.get("successor_queue_sha256") != persisted.successor_queue_sha256
        or campaign.get("successor_queue_sha256") != persisted.successor_queue_sha256
        or campaign.get("successor_queue_path") != "successor_queue.json"
        or successor != expected_successor
        or Path(persisted.accepted_replan_path) != attempt / "accepted_replan.json"
        or Path(persisted.campaign_path) != attempt / "campaign.json"
        or not _SHA256.fullmatch(persisted.successor_queue_sha256 or "")
        or not _COMMIT_SHA.fullmatch(value.accepted_head_sha)
    ):
        raise ReplanLaunchClaimError("replan.launch.authority_conflict")
    launch_id = _launch_id(
        value.repository_id,
        persisted.campaign_id,
        persisted.replan_attempt_number,
        persisted.successor_queue_sha256,
        value.accepted_head_sha,
    )
    return _VerifiedAuthority(
        attempt,
        value.repository_id,
        persisted.campaign_id,
        persisted.replan_attempt_number,
        value.accepted_head_sha,
        successor,
        persisted.successor_queue_sha256,
        launch_id,
    )


def _expected_claim(authority: _VerifiedAuthority, created_at: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "repository_id": authority.repository_id,
        "campaign_id": authority.campaign_id,
        "replan_attempt_number": authority.replan_attempt_number,
        "launch_id": authority.launch_id,
        "accepted_head_sha": authority.accepted_head_sha,
        "successor_queue_path": "successor_queue.json",
        "successor_queue_sha256": authority.successor_queue_sha256,
        "state": "launch_pending",
        "created_at": created_at,
    }


def _validate_claim(value: Any, authority: _VerifiedAuthority) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or set(value) != _CLAIM_FIELDS
        or value.get("schema_version") != SCHEMA_VERSION
        or value.get("state") != "launch_pending"
        or not isinstance(value.get("created_at"), str)
        or not value["created_at"]
        or value != _expected_claim(authority, value["created_at"])
    ):
        raise ReplanLaunchClaimError("replan.launch.claim_invariant")
    return value


def _sidecar_payload(path: Path, payload: bytes) -> bytes:
    return f"{_digest(payload)}  {path.name}\n".encode("ascii")


def _write_exclusive(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    _fsync_directory(path.parent)


def _load_claim(authority: _VerifiedAuthority) -> tuple[Path, dict[str, Any]]:
    path = authority.attempt_directory / "launch_claim.json"
    sidecar = path.with_suffix(".sha256")
    if not path.is_file() or not sidecar.is_file():
        raise ReplanLaunchClaimError("replan.launch.claim_incomplete")
    try:
        payload = path.read_bytes()
        sidecar_text = sidecar.read_text(encoding="ascii")
    except (OSError, UnicodeDecodeError) as exc:
        raise ReplanLaunchClaimError("replan.launch.claim_invalid") from exc
    match = re.fullmatch(
        r"([0-9a-f]{64})  " + re.escape(path.name) + r"\n", sidecar_text
    )
    if match is None:
        raise ReplanLaunchClaimError("replan.launch.claim_sidecar_invalid")
    if match.group(1) != _digest(payload):
        raise ReplanLaunchClaimError("replan.launch.claim_hash_mismatch")
    try:
        claim = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReplanLaunchClaimError("replan.launch.claim_json_invalid") from exc
    return path, _validate_claim(claim, authority)


def _result(authority: _VerifiedAuthority, claim_path: Path) -> ReplanLaunchClaimResult:
    return ReplanLaunchClaimResult(
        "launch_pending",
        "replan.launch.pending",
        authority.repository_id,
        authority.campaign_id,
        authority.replan_attempt_number,
        authority.launch_id,
        claim_path,
        authority.successor_queue_path,
        authority.successor_queue_sha256,
        authority.accepted_head_sha,
    )


def load_verified_replan_launch_claim(
    value: ReplanLaunchClaimInput,
) -> ReplanLaunchClaimResult:
    """Load a claim after re-verifying its complete R6-B2 authority chain."""

    authority = _verify_authority(value)
    path, _ = _load_claim(authority)
    return _result(authority, path)


def acquire_replan_launch_claim(
    value: ReplanLaunchClaimInput,
    *,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> ReplanLaunchClaimResult:
    """Acquire or reuse one durable launch-pending claim without launching work."""

    try:
        authority = _verify_authority(value)
        lock_descriptor = os.open(authority.attempt_directory, os.O_RDONLY)
        try:
            fcntl.flock(lock_descriptor, fcntl.LOCK_EX)
            claim_path = authority.attempt_directory / "launch_claim.json"
            sidecar_path = claim_path.with_suffix(".sha256")
            if claim_path.exists() or sidecar_path.exists():
                claim_path, _ = _load_claim(authority)
            else:
                created_at = now().astimezone(timezone.utc).isoformat()
                payload = _canonical_json(_expected_claim(authority, created_at))
                _write_exclusive(claim_path, payload)
                _write_exclusive(sidecar_path, _sidecar_payload(claim_path, payload))
                claim_path, _ = _load_claim(authority)
        finally:
            os.close(lock_descriptor)
        return _result(authority, claim_path)
    except (OSError, ReplanPersistenceError, ReplanLaunchClaimError) as exc:
        reason = (
            exc.reason_code
            if isinstance(exc, ReplanLaunchClaimError)
            else "replan.launch.authority_invalid"
        )
        return _blocked(reason)


__all__ = [
    "ReplanLaunchClaimError",
    "ReplanLaunchClaimInput",
    "ReplanLaunchClaimResult",
    "acquire_replan_launch_claim",
    "load_verified_replan_launch_claim",
]
