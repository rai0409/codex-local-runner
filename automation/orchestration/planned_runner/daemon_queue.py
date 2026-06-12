from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Mapping

QUEUE_SUBDIRS = ("pending", "running", "done", "failed")


def ensure_queue_dirs(queue_dir: str | Path) -> dict[str, str]:
    root = Path(queue_dir)
    paths: dict[str, str] = {"root": root.as_posix()}
    for name in QUEUE_SUBDIRS:
        sub = root / name
        sub.mkdir(parents=True, exist_ok=True)
        paths[name] = sub.as_posix()
    return paths


def enqueue_task(queue_dir: str | Path, spec: Mapping[str, Any]) -> Path:
    """Write a task spec into pending/. The spec must carry a task_id."""
    paths = ensure_queue_dirs(queue_dir)
    task_id = str(spec.get("task_id") or "").strip()
    if not task_id:
        raise ValueError("task spec must include task_id")
    target = Path(paths["pending"]) / f"{task_id}.json"
    target.write_text(
        json.dumps(dict(spec), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return target


def claim_next_task(queue_dir: str | Path) -> Path | None:
    """Move the oldest pending task to running/ and return its new path."""
    paths = ensure_queue_dirs(queue_dir)
    pending = sorted(Path(paths["pending"]).glob("*.json"))
    if not pending:
        return None
    source = pending[0]
    target = Path(paths["running"]) / source.name
    shutil.move(source.as_posix(), target.as_posix())
    return target


def complete_task(queue_dir: str | Path, running_path: str | Path, *, success: bool) -> Path:
    """Move a running task to done/ or failed/."""
    paths = ensure_queue_dirs(queue_dir)
    source = Path(running_path)
    bucket = "done" if success else "failed"
    target = Path(paths[bucket]) / source.name
    shutil.move(source.as_posix(), target.as_posix())
    return target


def list_tasks(queue_dir: str | Path) -> dict[str, list[str]]:
    paths = ensure_queue_dirs(queue_dir)
    return {
        name: sorted(p.name for p in Path(paths[name]).glob("*.json"))
        for name in QUEUE_SUBDIRS
    }


__all__ = [
    "QUEUE_SUBDIRS",
    "claim_next_task",
    "complete_task",
    "ensure_queue_dirs",
    "enqueue_task",
    "list_tasks",
]
