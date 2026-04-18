from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Mapping

_AUDIT_SCHEMA_VERSION = "v1"
_AUDIT_FILENAME = "run_audit.json"


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return False


def _as_optional_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text and text.lstrip("-").isdigit():
            return int(text)
    return None


def _iso_now(now: Callable[[], datetime]) -> str:
    return now().isoformat(timespec="seconds")


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def _normalize_record(raw: Mapping[str, Any], *, now: Callable[[], datetime]) -> dict[str, Any]:
    return {
        "job_id": _normalize_text(raw.get("job_id"), default=""),
        "run_id": _normalize_text(raw.get("run_id"), default="") or None,
        "scheduler_action_taken": _normalize_text(raw.get("scheduler_action_taken"), default="unspecified"),
        "execution_attempted": _as_bool(raw.get("execution_attempted")),
        "retry_attempted": _as_bool(raw.get("retry_attempted")),
        "routed_action": _normalize_text(raw.get("routed_action"), default="") or None,
        "routing_reason": _normalize_text(raw.get("routing_reason"), default=""),
        "retry_class": _normalize_text(raw.get("retry_class"), default="") or None,
        "retry_budget_remaining": _as_optional_int(raw.get("retry_budget_remaining")),
        "whether_human_required": _as_bool(raw.get("whether_human_required")),
        "outcome_status": _normalize_text(raw.get("outcome_status"), default="unknown"),
        "pause_state": _normalize_text(raw.get("pause_state"), default="") or None,
        "pause_reason": _normalize_text(raw.get("pause_reason"), default="") or None,
        "next_eligible_at": _normalize_text(raw.get("next_eligible_at"), default="") or None,
        "recorded_at": _normalize_text(raw.get("recorded_at"), default=_iso_now(now)),
    }


class RunAuditLogger:
    def __init__(self, *, now: Callable[[], datetime] = datetime.now) -> None:
        self._now = now

    def append(self, run_root: str | Path, record: Mapping[str, Any]) -> dict[str, Any]:
        root = Path(run_root)
        root.mkdir(parents=True, exist_ok=True)
        audit_path = root / _AUDIT_FILENAME
        if audit_path.exists():
            payload = _read_json_object(audit_path)
        else:
            payload = {}

        records = payload.get("records")
        normalized_records = list(records) if isinstance(records, list) else []
        normalized_records.append(_normalize_record(record, now=self._now))

        normalized_payload = {
            "schema_version": _AUDIT_SCHEMA_VERSION,
            "job_id": _normalize_text(record.get("job_id"), default=_normalize_text(payload.get("job_id"), default="")),
            "records": normalized_records,
        }
        audit_path.write_text(
            json.dumps(normalized_payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return normalized_payload
