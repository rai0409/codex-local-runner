from __future__ import annotations

from datetime import datetime
from datetime import timedelta
import json
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Mapping

_LEASE_SCHEMA_VERSION = "v1"


def _iso_now(now: Callable[[], datetime]) -> str:
    return now().isoformat(timespec="seconds")


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _as_non_negative_int(value: Any, *, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return max(0, value)
    if isinstance(value, str):
        text = value.strip()
        if text and text.isdigit():
            return int(text)
    return default


def _parse_iso_datetime(value: Any) -> datetime | None:
    text = _normalize_text(value, default="")
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _empty_leases() -> dict[str, Any]:
    return {"schema_version": _LEASE_SCHEMA_VERSION, "leases": {}}


def _is_active_lease(record: Mapping[str, Any], *, now: Callable[[], datetime]) -> bool:
    expires_at = _parse_iso_datetime(record.get("expires_at"))
    if expires_at is None:
        return False
    return now() < expires_at


class FileJobLease:
    def __init__(self, path: str | Path, *, now: Callable[[], datetime] = datetime.now) -> None:
        self.path = Path(path)
        self._now = now

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return _empty_leases()
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            return _empty_leases()
        leases = payload.get("leases")
        if not isinstance(leases, Mapping):
            return _empty_leases()
        normalized_leases: dict[str, Any] = {}
        for key, value in sorted(leases.items(), key=lambda item: str(item[0])):
            job_id = _normalize_text(key, default="")
            if not job_id or not isinstance(value, Mapping):
                continue
            holder = _normalize_text(value.get("holder"), default="")
            if not holder:
                continue
            normalized_leases[job_id] = {
                "job_id": job_id,
                "holder": holder,
                "acquired_at": _normalize_text(value.get("acquired_at"), default=""),
                "updated_at": _normalize_text(value.get("updated_at"), default=""),
                "expires_at": _normalize_text(value.get("expires_at"), default=""),
            }
        return {"schema_version": _LEASE_SCHEMA_VERSION, "leases": normalized_leases}

    def _write(self, payload: Mapping[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def get(self, job_id: str) -> dict[str, Any] | None:
        normalized_job_id = _normalize_text(job_id, default="")
        if not normalized_job_id:
            return None
        leases = self.load().get("leases")
        if not isinstance(leases, Mapping):
            return None
        record = leases.get(normalized_job_id)
        if not isinstance(record, Mapping):
            return None
        return dict(record)

    def claim(self, *, job_id: str, holder: str, lease_seconds: int) -> tuple[bool, dict[str, Any] | None]:
        normalized_job_id = _normalize_text(job_id, default="")
        normalized_holder = _normalize_text(holder, default="")
        duration = _as_non_negative_int(lease_seconds, default=0)
        if not normalized_job_id:
            raise ValueError("job_id is required for lease claim")
        if not normalized_holder:
            raise ValueError("holder is required for lease claim")
        if duration <= 0:
            raise ValueError("lease_seconds must be positive")

        payload = self.load()
        leases = payload.get("leases")
        if not isinstance(leases, dict):
            leases = {}
            payload["leases"] = leases

        current = leases.get(normalized_job_id)
        if isinstance(current, Mapping):
            if _is_active_lease(current, now=self._now) and _normalize_text(current.get("holder"), default="") != normalized_holder:
                return False, dict(current)

        now_value = self._now()
        new_record = {
            "job_id": normalized_job_id,
            "holder": normalized_holder,
            "acquired_at": _normalize_text(
                current.get("acquired_at"),
                default=_iso_now(self._now),
            )
            if isinstance(current, Mapping) and _normalize_text(current.get("holder"), default="") == normalized_holder
            else now_value.isoformat(timespec="seconds"),
            "updated_at": now_value.isoformat(timespec="seconds"),
            "expires_at": (now_value + timedelta(seconds=duration)).isoformat(timespec="seconds"),
        }
        leases[normalized_job_id] = new_record
        self._write(payload)
        return True, new_record

    def renew(self, *, job_id: str, holder: str, lease_seconds: int) -> tuple[bool, dict[str, Any] | None]:
        normalized_job_id = _normalize_text(job_id, default="")
        normalized_holder = _normalize_text(holder, default="")
        duration = _as_non_negative_int(lease_seconds, default=0)
        if not normalized_job_id or not normalized_holder or duration <= 0:
            return False, None

        payload = self.load()
        leases = payload.get("leases")
        if not isinstance(leases, dict):
            return False, None
        current = leases.get(normalized_job_id)
        if not isinstance(current, Mapping):
            return False, None
        if _normalize_text(current.get("holder"), default="") != normalized_holder:
            return False, dict(current)
        if not _is_active_lease(current, now=self._now):
            return False, dict(current)

        now_value = self._now()
        renewed = {
            **dict(current),
            "updated_at": now_value.isoformat(timespec="seconds"),
            "expires_at": (now_value + timedelta(seconds=duration)).isoformat(timespec="seconds"),
        }
        leases[normalized_job_id] = renewed
        self._write(payload)
        return True, renewed

    def release(self, *, job_id: str, holder: str | None = None) -> bool:
        normalized_job_id = _normalize_text(job_id, default="")
        if not normalized_job_id:
            return False

        payload = self.load()
        leases = payload.get("leases")
        if not isinstance(leases, dict):
            return False
        current = leases.get(normalized_job_id)
        if not isinstance(current, Mapping):
            return False

        normalized_holder = _normalize_text(holder, default="") if holder is not None else ""
        if normalized_holder and _normalize_text(current.get("holder"), default="") != normalized_holder:
            return False

        del leases[normalized_job_id]
        self._write(payload)
        return True

    def is_claimed(self, *, job_id: str) -> bool:
        current = self.get(job_id)
        if not isinstance(current, Mapping):
            return False
        return _is_active_lease(current, now=self._now)

