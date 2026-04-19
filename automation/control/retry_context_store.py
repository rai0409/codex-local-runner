from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from typing import Mapping

from automation.control.retry_context import normalize_retry_context

_STORE_SCHEMA_VERSION = "v1"


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _is_mapping(value: Any) -> bool:
    return isinstance(value, Mapping)


def _empty_store() -> dict[str, Any]:
    return {
        "schema_version": _STORE_SCHEMA_VERSION,
        "contexts": {},
    }


class FileRetryContextStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return _empty_store()
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if not _is_mapping(payload):
            return _empty_store()
        contexts = payload.get("contexts")
        if not _is_mapping(contexts):
            return _empty_store()
        normalized: dict[str, Any] = _empty_store()
        normalized_contexts: dict[str, Any] = {}
        for key, value in contexts.items():
            job_id = _normalize_text(key, default="")
            if not job_id or not _is_mapping(value):
                continue
            retry_context_payload = (
                value.get("retry_context")
                if _is_mapping(value.get("retry_context"))
                else value
            )
            normalized_contexts[job_id] = {
                "retry_context": normalize_retry_context(
                    retry_context_payload if _is_mapping(retry_context_payload) else None
                ),
                "updated_at": _normalize_text(
                    value.get("updated_at"),
                    default=_normalize_text(value.get("handoff_created_at"), default=""),
                ),
            }
        normalized["contexts"] = normalized_contexts
        return normalized

    def get(self, job_id: str) -> dict[str, Any] | None:
        record = self.get_record(job_id)
        if not _is_mapping(record):
            return None
        retry_context = record.get("retry_context")
        if not _is_mapping(retry_context):
            return None
        return dict(retry_context)

    def get_record(self, job_id: str) -> dict[str, Any] | None:
        normalized_job_id = _normalize_text(job_id, default="")
        if not normalized_job_id:
            return None
        store = self.load()
        contexts = store.get("contexts")
        if not _is_mapping(contexts):
            return None
        record = contexts.get(normalized_job_id)
        if not _is_mapping(record):
            return None
        retry_context = record.get("retry_context")
        return {
            "retry_context": (
                normalize_retry_context(retry_context if _is_mapping(retry_context) else None)
            ),
            "updated_at": _normalize_text(record.get("updated_at"), default=""),
        }

    def set(
        self,
        *,
        job_id: str,
        retry_context: Mapping[str, Any],
        updated_at: str,
    ) -> dict[str, Any]:
        normalized_job_id = _normalize_text(job_id, default="")
        if not normalized_job_id:
            raise ValueError("job_id is required to persist retry context")

        store = self.load()
        contexts = store.get("contexts")
        if not _is_mapping(contexts):
            contexts = {}
            store["contexts"] = contexts

        normalized_context = normalize_retry_context(retry_context)
        contexts[normalized_job_id] = {
            "retry_context": normalized_context,
            "updated_at": _normalize_text(updated_at, default=""),
        }

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(store, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return normalized_context
