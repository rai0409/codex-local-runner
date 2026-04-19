from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import tempfile
from typing import Any
from typing import Mapping

from automation.github.write_idempotency import normalize_final_classification

_SCHEMA_VERSION = "v1"
_LOCK_SUFFIX = ".lock"

try:  # pragma: no cover - platform dependent
    import fcntl  # type: ignore
except Exception:  # pragma: no cover - platform dependent
    fcntl = None  # type: ignore


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _as_non_negative_int(value: Any, *, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return max(0, value)
    if isinstance(value, str):
        text = value.strip()
        if text and text.lstrip("-").isdigit():
            return max(0, int(text))
    return default


def _is_mapping(value: Any) -> bool:
    return isinstance(value, Mapping)


def _empty_action_store(write_action: str) -> dict[str, Any]:
    return {
        "schema_version": _SCHEMA_VERSION,
        "write_action": _normalize_text(write_action, default="unknown_action"),
        "records_by_key": {},
        "updated_at": "",
    }


def _serialize_store(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)


class FileWriteReceiptStore:
    def __init__(self, root_dir: str | Path) -> None:
        self.root_dir = Path(root_dir)

    def _action_path(self, write_action: str) -> Path:
        normalized = _normalize_text(write_action, default="unknown_action")
        return self.root_dir / f"{normalized}.json"

    def _lock_path(self, write_action: str) -> Path:
        return self._action_path(write_action).with_suffix(f".json{_LOCK_SUFFIX}")

    @contextmanager
    def _action_lock(self, write_action: str):
        self.root_dir.mkdir(parents=True, exist_ok=True)
        lock_path = self._lock_path(write_action)
        with lock_path.open("a+b") as lock_file:
            if fcntl is not None:  # pragma: no branch
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                if fcntl is not None:  # pragma: no branch
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def _read_action_payload(self, write_action: str) -> dict[str, Any]:
        path = self._action_path(write_action)
        if not path.exists():
            return _empty_action_store(write_action)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"corrupted write receipt file: {path}") from exc
        except OSError as exc:
            raise ValueError(f"unreadable write receipt file: {path}") from exc
        if not _is_mapping(payload):
            raise ValueError(f"invalid write receipt structure at {path}")
        records = payload.get("records_by_key")
        if records is not None and not _is_mapping(records):
            raise ValueError(f"invalid records_by_key in write receipt file: {path}")
        return dict(payload)

    def _atomic_write_action_payload(self, write_action: str, payload: Mapping[str, Any]) -> None:
        path = self._action_path(write_action)
        self.root_dir.mkdir(parents=True, exist_ok=True)
        serialized = _serialize_store(payload)
        fd, temp_path = tempfile.mkstemp(
            dir=str(path.parent),
            prefix=f".{path.name}.",
            suffix=".tmp",
        )
        temp_file = Path(temp_path)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(serialized)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(str(temp_file), str(path))
            if hasattr(os, "O_DIRECTORY"):
                dir_fd = os.open(str(path.parent), os.O_DIRECTORY)
                try:
                    os.fsync(dir_fd)
                finally:
                    os.close(dir_fd)
        finally:
            if temp_file.exists():
                temp_file.unlink(missing_ok=True)

    def load_action(self, write_action: str) -> dict[str, Any]:
        payload = self._read_action_payload(write_action)
        records = payload.get("records_by_key")
        if not _is_mapping(records):
            records = {}
        normalized_records: dict[str, Any] = {}
        for key, value in records.items():
            idempotency_key = _normalize_text(key, default="")
            if not idempotency_key or not _is_mapping(value):
                continue
            record = dict(value)
            record["idempotency_key"] = idempotency_key
            record["job_id"] = _normalize_text(record.get("job_id"), default="")
            record["write_action"] = _normalize_text(record.get("write_action"), default=write_action)
            record["final_classification"] = normalize_final_classification(record.get("final_classification"))
            record["attempt_count"] = _as_non_negative_int(record.get("attempt_count"), default=0)
            target_identifiers = record.get("target_identifiers")
            record["target_identifiers"] = dict(target_identifiers) if _is_mapping(target_identifiers) else {}
            request_snapshot = record.get("request_snapshot")
            record["request_snapshot"] = dict(request_snapshot) if _is_mapping(request_snapshot) else {}
            response_summary = record.get("response_summary")
            record["response_summary"] = dict(response_summary) if _is_mapping(response_summary) else {}
            preconditions = record.get("precondition_snapshot")
            record["precondition_snapshot"] = dict(preconditions) if _is_mapping(preconditions) else {}
            observed = record.get("observed_github_facts")
            record["observed_github_facts"] = dict(observed) if _is_mapping(observed) else {}
            normalized_records[idempotency_key] = record
        return {
            "schema_version": _SCHEMA_VERSION,
            "write_action": _normalize_text(payload.get("write_action"), default=write_action),
            "records_by_key": normalized_records,
            "updated_at": _normalize_text(payload.get("updated_at"), default=""),
        }

    def list_records(self, write_action: str) -> list[dict[str, Any]]:
        store = self.load_action(write_action)
        records = store.get("records_by_key")
        if not _is_mapping(records):
            return []
        return [
            dict(record)
            for _, record in sorted(
                records.items(),
                key=lambda item: (
                    _normalize_text(item[1].get("created_at"), default=""),
                    _normalize_text(item[0], default=""),
                ),
            )
            if _is_mapping(record)
        ]

    def get_record(self, write_action: str, idempotency_key: str) -> dict[str, Any] | None:
        normalized_key = _normalize_text(idempotency_key, default="")
        if not normalized_key:
            return None
        store = self.load_action(write_action)
        records = store.get("records_by_key")
        if not _is_mapping(records):
            return None
        record = records.get(normalized_key)
        if not _is_mapping(record):
            return None
        return dict(record)

    def persist_record(
        self,
        *,
        write_action: str,
        idempotency_key: str,
        payload: Mapping[str, Any],
        updated_at: str,
    ) -> dict[str, Any]:
        normalized_key = _normalize_text(idempotency_key, default="")
        normalized_action = _normalize_text(write_action, default="")
        if not normalized_key:
            raise ValueError("idempotency_key is required")
        if not normalized_action:
            raise ValueError("write_action is required")
        if not _is_mapping(payload):
            raise ValueError("payload must be a mapping")

        with self._action_lock(normalized_action):
            store = self.load_action(normalized_action)
            records = store.get("records_by_key")
            if not _is_mapping(records):
                records = {}

            existing = records.get(normalized_key) if _is_mapping(records.get(normalized_key)) else {}
            attempt_count = _as_non_negative_int(existing.get("attempt_count"), default=0) + 1
            created_at = _normalize_text(existing.get("created_at"), default=_normalize_text(updated_at, default=""))

            merged_record = dict(payload)
            merged_record["idempotency_key"] = normalized_key
            merged_record["write_action"] = normalized_action
            merged_record["job_id"] = _normalize_text(merged_record.get("job_id"), default="")
            merged_record["attempt_count"] = attempt_count
            merged_record["created_at"] = created_at
            merged_record["updated_at"] = _normalize_text(updated_at, default="")
            merged_record["final_classification"] = normalize_final_classification(
                merged_record.get("final_classification")
            )
            target_identifiers = merged_record.get("target_identifiers")
            merged_record["target_identifiers"] = dict(target_identifiers) if _is_mapping(target_identifiers) else {}
            request_snapshot = merged_record.get("request_snapshot")
            merged_record["request_snapshot"] = dict(request_snapshot) if _is_mapping(request_snapshot) else {}
            response_summary = merged_record.get("response_summary")
            merged_record["response_summary"] = dict(response_summary) if _is_mapping(response_summary) else {}
            preconditions = merged_record.get("precondition_snapshot")
            merged_record["precondition_snapshot"] = dict(preconditions) if _is_mapping(preconditions) else {}
            observed = merged_record.get("observed_github_facts")
            merged_record["observed_github_facts"] = dict(observed) if _is_mapping(observed) else {}
            records[normalized_key] = merged_record

            store["records_by_key"] = records
            store["updated_at"] = _normalize_text(updated_at, default="")
            self._atomic_write_action_payload(normalized_action, store)
            return dict(merged_record)
