from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def append_log(log_path: str | Path, event: str, payload: Mapping[str, Any] | None = None) -> None:
    """Append one JSONL event line to the daemon log."""
    log_file = Path(log_path)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    record = {"ts": _utc_now(), "event": str(event)}
    if payload:
        record.update(dict(payload))
    with log_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def read_log_events(log_path: str | Path) -> list[dict[str, Any]]:
    log_file = Path(log_path)
    if not log_file.is_file():
        return []
    events: list[dict[str, Any]] = []
    for line in log_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            events.append(payload)
    return events


__all__ = ["append_log", "read_log_events"]
