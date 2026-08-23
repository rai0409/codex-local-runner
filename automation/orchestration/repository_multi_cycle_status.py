"""Read-only observation for repository multi-cycle execution evidence."""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Callable


DEFAULT_SUPERVISOR_STATE_ROOT = "~/.local/state/codex-local-runner/repository-multi-cycle-supervisor"
DEFAULT_CYCLE_OUTPUT_ROOT = "~/.local/state/codex-local-runner/repository-multi-cycle-runs"
_JSON = re.compile(r"^checkpoint-(\d{6})\.json$")
_SHA = re.compile(r"^checkpoint-(\d{6})\.sha256$")
_TERMINAL_STATUSES = {"completed", "blocked", "failed"}
_LIFECYCLE_STATUSES = {"initialized", "active_task", "accepted_task", "finalizing"}


class RepositoryMultiCycleStatusError(ValueError):
    """Raised only for invalid persisted evidence during observation."""


def _state_directory(repository_id: str, state_root: Path) -> Path:
    return state_root / hashlib.sha256(repository_id.encode("utf-8")).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RepositoryMultiCycleStatusError("observation.evidence_invalid") from exc
    if not isinstance(value, dict):
        raise RepositoryMultiCycleStatusError("observation.evidence_invalid")
    return value


def read_verified_terminal_receipt(directory: str | Path, repository_id: str, queue_sha256: str) -> dict[str, Any] | None:
    """Return a verified terminal receipt, or ``None`` when no receipt exists.

    This function reads only.  It intentionally has no recovery path: a receipt
    with a sidecar is authoritative only when every invariant verifies.
    """
    directory = Path(directory)
    receipt, sidecar = directory / "receipt.json", directory / "receipt.sha256"
    if not receipt.exists() and not sidecar.exists():
        return None
    try:
        payload = receipt.read_bytes()
        value = json.loads(payload)
        if not isinstance(value, dict):
            raise RepositoryMultiCycleStatusError("observation.receipt_invariant")
        # Historical receipts for another repository/queue do not participate in
        # this observation, even if their own sidecar has aged badly.
        if value.get("repository_id") != repository_id or value.get("queue_spec_sha256") != queue_sha256:
            return None
        expected = f"{hashlib.sha256(payload).hexdigest()}  receipt.json\n"
        if sidecar.read_text(encoding="utf-8") != expected:
            raise RepositoryMultiCycleStatusError("observation.receipt_hash_mismatch")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RepositoryMultiCycleStatusError("observation.receipt_invalid") from exc
    if value.get("schema_version") != "1" or value.get("cycle_run_id") != directory.name:
        raise RepositoryMultiCycleStatusError("observation.receipt_invariant")
    if value.get("status") not in _TERMINAL_STATUSES or not isinstance(value.get("task_count"), int) or not isinstance(value.get("completed_count"), int):
        raise RepositoryMultiCycleStatusError("observation.receipt_invariant")
    if not 0 <= value["completed_count"] <= value["task_count"] or not isinstance(value.get("executed_task_results"), list):
        raise RepositoryMultiCycleStatusError("observation.receipt_invariant")
    if not isinstance(value.get("source_anchor_sha"), str) or not isinstance(value.get("final_accepted_head_sha"), str):
        raise RepositoryMultiCycleStatusError("observation.receipt_invariant")
    return value


def _read_latest_checkpoint_read_only(directory: Path) -> dict[str, Any] | None:
    """Validate the immutable checkpoint history without orphan recovery."""
    root = directory / "state"
    if not root.exists():
        return None
    inventory: dict[int, dict[str, Path]] = {}
    try:
        entries = list(root.iterdir())
    except OSError as exc:
        raise RepositoryMultiCycleStatusError("observation.checkpoint_invalid") from exc
    for item in entries:
        match, kind = _JSON.match(item.name), "json"
        if match is None:
            match, kind = _SHA.match(item.name), "sha"
        if match is not None:
            inventory.setdefault(int(match.group(1)), {})[kind] = item
    if not inventory:
        return None
    sequences = sorted(inventory)
    if sequences != list(range(len(sequences))):
        raise RepositoryMultiCycleStatusError("observation.checkpoint_sequence_invalid")
    values: dict[int, dict[str, Any]] = {}
    for sequence in sequences:
        pair = inventory[sequence]
        if set(pair) != {"json", "sha"}:
            raise RepositoryMultiCycleStatusError("observation.checkpoint_incomplete")
        try:
            payload = pair["json"].read_bytes()
            value = json.loads(payload)
            expected = f"{hashlib.sha256(payload).hexdigest()}  {pair['json'].name}\n"
            actual = pair["sha"].read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RepositoryMultiCycleStatusError("observation.checkpoint_invalid") from exc
        if actual != expected:
            raise RepositoryMultiCycleStatusError("observation.checkpoint_hash_mismatch")
        if not isinstance(value, dict) or value.get("schema_version") != "1" or value.get("checkpoint_sequence") != sequence:
            raise RepositoryMultiCycleStatusError("observation.checkpoint_invariant")
        values[sequence] = value
    return values[max(values)]


def _pid_exists(pid: Any) -> bool:
    return isinstance(pid, int) and pid > 0 and (Path("/proc") / str(pid)).exists()


def _empty_status(repository_id: str, queue_sha256: str) -> dict[str, Any]:
    return {"repository_id": repository_id, "queue_sha256": queue_sha256, "state": "idle", "cycle_run_id": None,
            "supervisor_pid": None, "supervisor_alive": False, "worker_pid": None, "worker_alive": False,
            "task_count": None, "completed_count": None, "current_task_index": None, "current_task_id": None,
            "phase": None, "last_activity_at": None, "terminal_status": None, "reason_code": None,
            "source_anchor_sha": None, "final_accepted_head_sha": None, "action_required": False,
            "authoritative_source": "none"}


def inspect_repository_multi_cycle_status(repository_id: str, queue_spec_path: str | os.PathLike[str], *, state_root: str | os.PathLike[str] = DEFAULT_SUPERVISOR_STATE_ROOT, cycle_output_root: str | os.PathLike[str] = DEFAULT_CYCLE_OUTPUT_ROOT, pid_exists: Callable[[Any], bool] = _pid_exists) -> dict[str, Any]:
    """Return a stable observation derived solely from persisted evidence.

    Authority is terminal receipt, checkpoint, live process metadata, then the
    supervisor status fallback.  This never calls execution or recovery APIs.
    """
    queue = Path(queue_spec_path).expanduser()
    try:
        queue_sha256 = hashlib.sha256(queue.read_bytes()).hexdigest()
    except OSError:
        result = _empty_status(repository_id, "")
        result.update(state="blocked_observation", reason_code="observation.queue_unavailable", action_required=True, authoritative_source="queue")
        return result
    result = _empty_status(repository_id, queue_sha256)
    state_root_path, cycle_root = Path(state_root).expanduser(), Path(cycle_output_root).expanduser()
    status_path = _state_directory(repository_id, state_root_path) / "status.json"
    status: dict[str, Any] = {}
    status_error: str | None = None
    if status_path.exists():
        try:
            candidate = _read_json(status_path)
            if candidate.get("repository_id") == repository_id:
                status = candidate
        except RepositoryMultiCycleStatusError:
            status_error = "observation.status_invalid"
    terminals: list[tuple[Path, dict[str, Any]]] = []
    checkpoints: list[tuple[Path, dict[str, Any]]] = []
    try:
        directories = sorted((item for item in cycle_root.iterdir() if item.is_dir() and item.name.startswith("cycle-")), key=lambda item: item.name) if cycle_root.exists() else []
        for directory in directories:
            terminal = read_verified_terminal_receipt(directory, repository_id, queue_sha256)
            if terminal is not None:
                terminals.append((directory, terminal)); continue
            checkpoint = _read_latest_checkpoint_read_only(directory)
            if checkpoint is not None and checkpoint.get("cycle_run_id") == directory.name and checkpoint.get("repository_id") == repository_id and checkpoint.get("queue_spec_sha256") == queue_sha256:
                if checkpoint.get("lifecycle_status") not in _LIFECYCLE_STATUSES:
                    raise RepositoryMultiCycleStatusError("observation.checkpoint_invariant")
                checkpoints.append((directory, checkpoint))
    except RepositoryMultiCycleStatusError as exc:
        return {**result, "state": "blocked_observation", "reason_code": str(exc), "action_required": True, "authoritative_source": "verified_evidence"}
    wanted_cycle = status.get("cycle_run_id")
    terminal_for_status = next(((directory, receipt) for directory, receipt in terminals if directory.name == wanted_cycle), None)
    checkpoint_for_status = next(((directory, checkpoint) for directory, checkpoint in checkpoints if directory.name == wanted_cycle), None)
    if terminal_for_status is not None:
        selected_terminal, selected_checkpoint = terminal_for_status, None
    elif checkpoint_for_status is not None:
        # A newer, explicitly recorded active cycle must not be hidden by an
        # older terminal receipt for the same queue revision.
        selected_terminal, selected_checkpoint = None, checkpoint_for_status
    else:
        latest = max([*( (directory.name, "terminal", directory, value) for directory, value in terminals ), *( (directory.name, "checkpoint", directory, value) for directory, value in checkpoints )], default=None)
        selected_terminal = (latest[2], latest[3]) if latest is not None and latest[1] == "terminal" else None
        selected_checkpoint = (latest[2], latest[3]) if latest is not None and latest[1] == "checkpoint" else None
    if selected_terminal is not None:
        directory, receipt = selected_terminal
        terminal_status = receipt["status"]
        return {**result, "state": "terminal", "cycle_run_id": directory.name, "supervisor_pid": status.get("supervisor_pid"), "supervisor_alive": pid_exists(status.get("supervisor_pid")), "worker_pid": status.get("worker_pid"), "worker_alive": False, "task_count": receipt["task_count"], "completed_count": receipt["completed_count"], "last_activity_at": receipt.get("finished_at") or receipt.get("updated_at"), "terminal_status": terminal_status, "reason_code": receipt.get("reason_code"), "source_anchor_sha": receipt["source_anchor_sha"], "final_accepted_head_sha": receipt["final_accepted_head_sha"], "action_required": terminal_status != "completed", "authoritative_source": "verified_terminal_receipt"}
    supervisor_pid, worker_pid = status.get("supervisor_pid"), status.get("worker_pid")
    supervisor_alive, worker_alive = pid_exists(supervisor_pid), pid_exists(worker_pid)
    if selected_checkpoint is not None:
        directory, checkpoint = selected_checkpoint
        active = checkpoint.get("active_task") if isinstance(checkpoint.get("active_task"), dict) else {}
        active_now = status.get("state") == "worker_active" and worker_alive
        return {**result, "state": "worker_active" if active_now else "interrupted_or_stale", "cycle_run_id": directory.name, "supervisor_pid": supervisor_pid, "supervisor_alive": supervisor_alive, "worker_pid": worker_pid, "worker_alive": worker_alive, "task_count": checkpoint.get("task_count"), "completed_count": checkpoint.get("completed_count"), "current_task_index": active.get("task_index"), "current_task_id": active.get("task_id"), "phase": checkpoint.get("lifecycle_status"), "last_activity_at": checkpoint.get("updated_at") or status.get("last_heartbeat_at") or status.get("updated_at"), "reason_code": None if active_now else "observation.nonterminal_without_live_worker", "source_anchor_sha": checkpoint.get("source_anchor_sha"), "final_accepted_head_sha": checkpoint.get("accepted_head_sha"), "action_required": not active_now, "authoritative_source": "verified_checkpoint"}
    if status_error is not None:
        return {**result, "state": "blocked_observation", "reason_code": status_error, "action_required": True, "authoritative_source": "status.json"}
    if status.get("state") == "worker_active":
        return {**result, "state": "worker_active" if worker_alive else "interrupted_or_stale", "cycle_run_id": wanted_cycle, "supervisor_pid": supervisor_pid, "supervisor_alive": supervisor_alive, "worker_pid": worker_pid, "worker_alive": worker_alive, "last_activity_at": status.get("last_heartbeat_at") or status.get("updated_at"), "reason_code": None if worker_alive else "observation.worker_not_alive", "action_required": not worker_alive, "authoritative_source": "status.json"}
    return {**result, "supervisor_pid": supervisor_pid, "supervisor_alive": supervisor_alive, "worker_pid": worker_pid, "worker_alive": worker_alive, "last_activity_at": status.get("last_heartbeat_at") or status.get("updated_at"), "authoritative_source": "status.json" if status else "none"}


__all__ = ["DEFAULT_CYCLE_OUTPUT_ROOT", "DEFAULT_SUPERVISOR_STATE_ROOT", "RepositoryMultiCycleStatusError", "inspect_repository_multi_cycle_status", "read_verified_terminal_receipt"]
