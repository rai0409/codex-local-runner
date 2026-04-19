from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Mapping

STATE_PENDING = "pending"
STATE_RUNNABLE = "runnable"
STATE_PAUSED = "paused"
STATE_RETRY_SCHEDULED = "retry_scheduled"
STATE_ESCALATED = "escalated"
STATE_COMPLETED = "completed"
STATE_FAILED_TERMINAL = "failed_terminal"

JOB_STATES = {
    STATE_PENDING,
    STATE_RUNNABLE,
    STATE_PAUSED,
    STATE_RETRY_SCHEDULED,
    STATE_ESCALATED,
    STATE_COMPLETED,
    STATE_FAILED_TERMINAL,
}

_REGISTRY_SCHEMA_VERSION = "v1"


def _iso_now(now: Callable[[], datetime]) -> str:
    return now().isoformat(timespec="seconds")


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


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


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return False


def _empty_registry() -> dict[str, Any]:
    return {
        "schema_version": _REGISTRY_SCHEMA_VERSION,
        "jobs": {},
    }


def _normalize_state(value: Any, *, default: str = STATE_PENDING) -> str:
    state = _normalize_text(value, default=default).lower()
    if state not in JOB_STATES:
        return default
    return state


def _normalize_record(
    raw: Mapping[str, Any],
    *,
    now: Callable[[], datetime],
    existing_created_at: str | None = None,
) -> dict[str, Any]:
    created_at = existing_created_at or _normalize_text(raw.get("created_at"), default=_iso_now(now))
    return {
        "job_id": _normalize_text(raw.get("job_id"), default=""),
        "repo_or_workspace": _normalize_text(raw.get("repo_or_workspace"), default="") or None,
        "current_state": _normalize_state(raw.get("current_state"), default=STATE_PENDING),
        "created_at": created_at,
        "updated_at": _normalize_text(raw.get("updated_at"), default=_iso_now(now)),
        "run_root": _normalize_text(raw.get("run_root"), default="") or None,
        "artifact_root": _normalize_text(raw.get("artifact_root"), default="") or None,
        "next_eligible_at": _normalize_text(raw.get("next_eligible_at"), default="") or None,
        "retry_class": _normalize_text(raw.get("retry_class"), default="") or None,
        "retry_budget_remaining": _as_optional_int(raw.get("retry_budget_remaining")),
        "whether_human_required": _as_bool(raw.get("whether_human_required")),
        "terminal_status": _normalize_text(raw.get("terminal_status"), default="") or None,
    }


class FileJobRegistry:
    def __init__(self, path: str | Path, *, now: Callable[[], datetime] = datetime.now) -> None:
        self.path = Path(path)
        self._now = now

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return _empty_registry()
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            return _empty_registry()
        jobs_raw = payload.get("jobs")
        if not isinstance(jobs_raw, Mapping):
            return _empty_registry()
        normalized_jobs: dict[str, Any] = {}
        for key, value in sorted(jobs_raw.items(), key=lambda item: str(item[0])):
            job_id = _normalize_text(key, default="")
            if not job_id or not isinstance(value, Mapping):
                continue
            normalized = _normalize_record(value, now=self._now)
            if not normalized["job_id"]:
                normalized["job_id"] = job_id
            if normalized["job_id"] != job_id:
                normalized["job_id"] = job_id
            normalized_jobs[job_id] = normalized
        return {"schema_version": _REGISTRY_SCHEMA_VERSION, "jobs": normalized_jobs}

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
        jobs = self.load().get("jobs")
        if not isinstance(jobs, Mapping):
            return None
        record = jobs.get(normalized_job_id)
        if not isinstance(record, Mapping):
            return None
        return dict(record)

    def list(self, *, current_state: str | None = None) -> list[dict[str, Any]]:
        jobs = self.load().get("jobs")
        if not isinstance(jobs, Mapping):
            return []
        records = [dict(record) for record in jobs.values() if isinstance(record, Mapping)]
        if current_state is not None:
            target = _normalize_state(current_state, default="")
            records = [record for record in records if _normalize_state(record.get("current_state"), default="") == target]
        return sorted(records, key=lambda record: _normalize_text(record.get("job_id"), default=""))

    def upsert(self, record: Mapping[str, Any]) -> dict[str, Any]:
        raw_job_id = _normalize_text(record.get("job_id"), default="")
        if not raw_job_id:
            raise ValueError("job_id is required")
        current = self.load()
        jobs = current.get("jobs")
        if not isinstance(jobs, dict):
            jobs = {}
            current["jobs"] = jobs
        existing = jobs.get(raw_job_id)
        existing_created_at = (
            _normalize_text(existing.get("created_at"), default="")
            if isinstance(existing, Mapping)
            else ""
        ) or None
        normalized = _normalize_record(record, now=self._now, existing_created_at=existing_created_at)
        normalized["job_id"] = raw_job_id
        jobs[raw_job_id] = normalized
        self._write(current)
        return normalized

    def ensure(
        self,
        *,
        job_id: str,
        artifact_root: str | Path | None = None,
        run_root: str | Path | None = None,
        repo_or_workspace: str | None = None,
        current_state: str = STATE_PENDING,
    ) -> dict[str, Any]:
        existing = self.get(job_id)
        base = dict(existing or {})
        base["job_id"] = _normalize_text(job_id, default="")
        base["artifact_root"] = str(artifact_root) if artifact_root is not None else base.get("artifact_root")
        base["run_root"] = str(run_root) if run_root is not None else base.get("run_root")
        base["repo_or_workspace"] = repo_or_workspace or base.get("repo_or_workspace")
        base["current_state"] = base.get("current_state") or current_state
        base["updated_at"] = _iso_now(self._now)
        return self.upsert(base)

