from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from automation.orchestration.planned_runner.daemon_queue import ensure_queue_dirs

DAEMON_STATE_FILENAME = "daemon_state.json"
MAX_RECOVERY_ATTEMPTS_DEFAULT = 1


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_daemon_state(state_path: str | Path, payload: Mapping[str, Any]) -> Path:
    state_file = Path(state_path)
    state_file.parent.mkdir(parents=True, exist_ok=True)
    record = dict(payload)
    record["updated_at"] = _utc_now()
    state_file.write_text(
        json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return state_file


def read_daemon_state(state_path: str | Path) -> dict[str, Any]:
    try:
        payload = json.loads(Path(state_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def recover_interrupted_tasks(
    queue_dir: str | Path,
    *,
    max_recovery_attempts: int = MAX_RECOVERY_ATTEMPTS_DEFAULT,
) -> dict[str, Any]:
    """Handle tasks left in running/ by an interrupted daemon.

    Each interrupted task is requeued to pending/ with an incremented
    `_recovery_attempts` counter; tasks exceeding max_recovery_attempts are
    moved to failed/ with an `_recovery_exhausted` marker instead of looping.
    """
    paths = ensure_queue_dirs(queue_dir)
    requeued: list[str] = []
    exhausted: list[str] = []
    for running_path in sorted(Path(paths["running"]).glob("*.json")):
        try:
            spec = json.loads(running_path.read_text(encoding="utf-8"))
            if not isinstance(spec, dict):
                spec = {}
        except (OSError, json.JSONDecodeError):
            spec = {}
        attempts = int(spec.get("_recovery_attempts", 0) or 0) + 1
        spec["_recovery_attempts"] = attempts
        spec["_last_interruption_at"] = _utc_now()
        if attempts > max(0, int(max_recovery_attempts)):
            spec["_recovery_exhausted"] = True
            target = Path(paths["failed"]) / running_path.name
            target.write_text(
                json.dumps(spec, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            running_path.unlink()
            exhausted.append(running_path.name)
        else:
            target = Path(paths["pending"]) / running_path.name
            target.write_text(
                json.dumps(spec, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            running_path.unlink()
            requeued.append(running_path.name)
    return {
        "requeued": requeued,
        "recovery_exhausted": exhausted,
        "recovered_count": len(requeued),
        "exhausted_count": len(exhausted),
    }


__all__ = [
    "DAEMON_STATE_FILENAME",
    "MAX_RECOVERY_ATTEMPTS_DEFAULT",
    "read_daemon_state",
    "recover_interrupted_tasks",
    "write_daemon_state",
]
