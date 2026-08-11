"""Immutable, crash-consistent checkpoint pairs for multi-cycle recovery."""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

CHECKPOINT_SCHEMA_VERSION = "1"
_JSON = re.compile(r"^checkpoint-(\d{6})\.json$")
_SHA = re.compile(r"^checkpoint-(\d{6})\.sha256$")


class RepositoryMultiCycleStateError(ValueError):
    def __init__(self, reason_code: str):
        self.reason_code = reason_code
        super().__init__(reason_code)


def _fsync_directory(directory: Path) -> None:
    descriptor = os.open(directory, os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write(path: Path, data: bytes) -> None:
    fd, name = tempfile.mkstemp(prefix=".checkpoint-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        if temporary.exists():
            temporary.unlink()


def _inventory(root: Path) -> dict[int, dict[str, Path]]:
    inventory: dict[int, dict[str, Path]] = {}
    if not root.exists():
        return inventory
    for item in root.iterdir():
        match = _JSON.match(item.name)
        kind = "json"
        if match is None:
            match = _SHA.match(item.name)
            kind = "sha"
        if match is not None:
            inventory.setdefault(int(match.group(1)), {})[kind] = item
    return inventory


def _validate_topology(inventory: dict[int, dict[str, Path]]) -> None:
    sequences = sorted(inventory)
    if sequences != list(range(len(sequences))):
        raise RepositoryMultiCycleStateError("multi_cycle.resume.checkpoint_sequence_invalid")


def _validate_pair(sequence: int, pair: dict[str, Path]) -> dict[str, Any]:
    if set(pair) != {"json", "sha"}:
        raise RepositoryMultiCycleStateError("multi_cycle.resume.checkpoint_incomplete")
    path, sidecar = pair["json"], pair["sha"]
    try:
        payload = path.read_bytes()
        value = json.loads(payload)
        actual = sidecar.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RepositoryMultiCycleStateError("multi_cycle.resume.checkpoint_invalid") from exc
    expected = f"{hashlib.sha256(payload).hexdigest()}  {path.name}\n"
    if actual != expected:
        raise RepositoryMultiCycleStateError("multi_cycle.resume.checkpoint_hash_mismatch")
    if not isinstance(value, dict) or value.get("schema_version") != CHECKPOINT_SCHEMA_VERSION or value.get("checkpoint_sequence") != sequence:
        raise RepositoryMultiCycleStateError("multi_cycle.resume.checkpoint_invariant")
    return value


def _validate_history(inventory: dict[int, dict[str, Path]], *, allow_latest_incomplete: bool) -> tuple[dict[int, dict[str, Any]], int | None]:
    _validate_topology(inventory)
    values: dict[int, dict[str, Any]] = {}
    incomplete: int | None = None
    for sequence in sorted(inventory):
        pair = inventory[sequence]
        if set(pair) == {"json", "sha"}:
            values[sequence] = _validate_pair(sequence, pair)
            continue
        if not allow_latest_incomplete or sequence != max(inventory) or len(values) != sequence:
            raise RepositoryMultiCycleStateError("multi_cycle.resume.checkpoint_sequence_invalid")
        incomplete = sequence
    return values, incomplete


def _cleanup_orphan(root: Path, pair: dict[str, Path]) -> None:
    try:
        for path in pair.values():
            path.unlink()
        _fsync_directory(root)
    except OSError as exc:
        raise RepositoryMultiCycleStateError("multi_cycle.resume.checkpoint_recovery_failed") from exc


def write_checkpoint(directory: str | Path, value: dict[str, Any]) -> Path:
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    inventory = _inventory(root)
    try:
        values, incomplete = _validate_history(inventory, allow_latest_incomplete=False)
    except RepositoryMultiCycleStateError as exc:
        raise RepositoryMultiCycleStateError("multi_cycle.state.history_invalid") from exc
    if incomplete is not None:  # defensive: disallowed above
        raise RepositoryMultiCycleStateError("multi_cycle.state.history_invalid")
    sequence = len(values)
    path = root / f"checkpoint-{sequence:06d}.json"
    sidecar = root / f"checkpoint-{sequence:06d}.sha256"
    if path.exists() or sidecar.exists():
        raise RepositoryMultiCycleStateError("multi_cycle.state.sequence_exists")
    snapshot = dict(value)
    snapshot.update({"schema_version": CHECKPOINT_SCHEMA_VERSION, "checkpoint_sequence": sequence})
    payload = json.dumps(snapshot, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    _write(path, payload)
    _write(sidecar, f"{hashlib.sha256(payload).hexdigest()}  {path.name}\n".encode("utf-8"))
    return path


def load_latest_checkpoint(directory: str | Path) -> tuple[dict[str, Any], bool]:
    root = Path(directory)
    inventory = _inventory(root)
    if not inventory:
        raise RepositoryMultiCycleStateError("multi_cycle.resume.checkpoint_missing")
    values, incomplete = _validate_history(inventory, allow_latest_incomplete=True)
    if incomplete is None:
        return values[max(values)], False
    if not values:
        raise RepositoryMultiCycleStateError("multi_cycle.resume.checkpoint_incomplete")
    _cleanup_orphan(root, inventory[incomplete])
    return values[max(values)], True
