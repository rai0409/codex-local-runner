from __future__ import annotations
from pathlib import Path
from typing import Any
from typing import Mapping
from automation.orchestration.planned_runner.utils import (
    _normalize_text,
    _read_json_object_if_exists,
)

def _collect_execution_result_contract_records(
    manifest_units: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for entry in manifest_units:
        result_path_text = _normalize_text(entry.get("result_path"), default="")
        receipt_path_text = _normalize_text(entry.get("receipt_path"), default="")

        result_path = Path(result_path_text) if result_path_text else None
        receipt_path = Path(receipt_path_text) if receipt_path_text else None

        result_exists = bool(result_path and result_path.exists())
        receipt_exists = bool(receipt_path and receipt_path.exists())
        result_payload = _read_json_object_if_exists(result_path) if result_path else None
        receipt_payload = _read_json_object_if_exists(receipt_path) if receipt_path else None

        records.append(
            {
                "pr_id": _normalize_text(entry.get("pr_id"), default=""),
                "result_path": str(result_path) if result_path else "",
                "result_exists": result_exists,
                "result_malformed": bool(result_exists and not isinstance(result_payload, Mapping)),
                "result_payload": dict(result_payload) if isinstance(result_payload, Mapping) else None,
                "receipt_path": str(receipt_path) if receipt_path else "",
                "receipt_exists": receipt_exists,
                "receipt_malformed": bool(receipt_exists and not isinstance(receipt_payload, Mapping)),
                "receipt_payload": dict(receipt_payload) if isinstance(receipt_payload, Mapping) else None,
            }
        )
    return records


__all__ = [
    "_collect_execution_result_contract_records",
]
