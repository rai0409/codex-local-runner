from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def is_pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def acquire_lock(lock_path: str | Path, *, pid: int | None = None) -> dict[str, Any]:
    """Acquire a pidfile lock. A lock held by a dead pid is treated as stale and replaced."""
    lock_file = Path(lock_path)
    own_pid = int(pid if pid is not None else os.getpid())
    stale_recovered = False
    if lock_file.exists():
        try:
            existing = json.loads(lock_file.read_text(encoding="utf-8"))
            existing_pid = int(existing.get("pid", -1))
        except (OSError, json.JSONDecodeError, ValueError):
            existing_pid = -1
        if existing_pid != own_pid and is_pid_alive(existing_pid):
            return {
                "acquired": False,
                "reason": "lock_held_by_running_process",
                "existing_pid": existing_pid,
                "stale_recovered": False,
                "lock_path": lock_file.as_posix(),
            }
        stale_recovered = True
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    lock_file.write_text(
        json.dumps({"pid": own_pid, "acquired_at": _utc_now()}, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "acquired": True,
        "reason": "stale_lock_recovered" if stale_recovered else "acquired",
        "existing_pid": None,
        "stale_recovered": stale_recovered,
        "lock_path": lock_file.as_posix(),
    }


def release_lock(lock_path: str | Path, *, pid: int | None = None) -> bool:
    """Release the lock if owned by pid (default: current process)."""
    lock_file = Path(lock_path)
    own_pid = int(pid if pid is not None else os.getpid())
    if not lock_file.exists():
        return False
    try:
        existing = json.loads(lock_file.read_text(encoding="utf-8"))
        if int(existing.get("pid", -1)) != own_pid:
            return False
    except (OSError, json.JSONDecodeError, ValueError):
        pass
    lock_file.unlink(missing_ok=True)
    return True


__all__ = ["acquire_lock", "is_pid_alive", "release_lock"]
