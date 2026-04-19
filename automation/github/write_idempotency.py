from __future__ import annotations

from hashlib import sha256
import json
from typing import Any
from typing import Mapping
from typing import Sequence

DEDUPE_FIRST_ATTEMPT = "first_attempt"
DEDUPE_ALREADY_APPLIED = "already_applied"
DEDUPE_REPLAY_SAME_INTENT = "replay_same_intent"
DEDUPE_CONFLICTING_PRIOR_INTENT = "conflicting_prior_intent"
DEDUPE_PRECONDITION_CHANGED = "precondition_changed"
DEDUPE_UNKNOWN_NEEDS_HUMAN = "unknown_needs_human"

DEDUPE_STATUSES = {
    DEDUPE_FIRST_ATTEMPT,
    DEDUPE_ALREADY_APPLIED,
    DEDUPE_REPLAY_SAME_INTENT,
    DEDUPE_CONFLICTING_PRIOR_INTENT,
    DEDUPE_PRECONDITION_CHANGED,
    DEDUPE_UNKNOWN_NEEDS_HUMAN,
}

FINAL_CLASSIFICATIONS = {
    "applied",
    "already_applied",
    "no_op",
    "conflict",
    "precondition_changed",
    "needs_human",
    "auth_failure",
    "api_failure",
    "unsupported",
    "failed",
}


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _normalize_for_hash(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            _normalize_text(key, default=""): _normalize_for_hash(item)
            for key, item in sorted(value.items(), key=lambda item: _normalize_text(item[0], default=""))
            if _normalize_text(key, default="")
        }
    if isinstance(value, (list, tuple)):
        return [_normalize_for_hash(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return _normalize_text(value, default="")


def stable_intent_fingerprint(intent_payload: Mapping[str, Any]) -> str:
    normalized = _normalize_for_hash(intent_payload if isinstance(intent_payload, Mapping) else {})
    serialized = json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(serialized.encode("utf-8")).hexdigest()


def stable_idempotency_key(
    *,
    job_id: str,
    write_action: str,
    target_identifiers: Mapping[str, Any],
    intent_fingerprint: str,
) -> str:
    payload = {
        "job_id": _normalize_text(job_id, default=""),
        "write_action": _normalize_text(write_action, default=""),
        "target_identifiers": _normalize_for_hash(target_identifiers),
        "intent_fingerprint": _normalize_text(intent_fingerprint, default=""),
    }
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(serialized.encode("utf-8")).hexdigest()


def normalize_final_classification(value: Any) -> str:
    normalized = _normalize_text(value, default="failed")
    if normalized in FINAL_CLASSIFICATIONS:
        return normalized
    return "failed"


def _is_mapping(value: Any) -> bool:
    return isinstance(value, Mapping)


def _record_matches_key(record: Mapping[str, Any], *, idempotency_key: str) -> bool:
    return _normalize_text(record.get("idempotency_key"), default="") == idempotency_key


def evaluate_write_dedupe_status(
    *,
    job_id: str,
    write_action: str,
    target_identifiers: Mapping[str, Any],
    intent_payload: Mapping[str, Any],
    prior_records: Sequence[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    intent_fingerprint = stable_intent_fingerprint(intent_payload)
    idempotency_key = stable_idempotency_key(
        job_id=job_id,
        write_action=write_action,
        target_identifiers=target_identifiers,
        intent_fingerprint=intent_fingerprint,
    )

    records = [record for record in (prior_records or []) if _is_mapping(record)]
    if not records:
        return {
            "dedupe_status": DEDUPE_FIRST_ATTEMPT,
            "idempotency_key": idempotency_key,
            "intent_fingerprint": intent_fingerprint,
            "matched_record": None,
            "conflicting_record": None,
        }

    same_key_record = next(
        (record for record in records if _record_matches_key(record, idempotency_key=idempotency_key)),
        None,
    )
    if same_key_record is not None:
        prior_classification = normalize_final_classification(same_key_record.get("final_classification"))
        if prior_classification in {"applied", "already_applied", "no_op"}:
            dedupe_status = DEDUPE_REPLAY_SAME_INTENT
        elif prior_classification == "precondition_changed":
            dedupe_status = DEDUPE_PRECONDITION_CHANGED
        elif prior_classification == "conflict":
            dedupe_status = DEDUPE_CONFLICTING_PRIOR_INTENT
        elif prior_classification == "needs_human":
            dedupe_status = DEDUPE_UNKNOWN_NEEDS_HUMAN
        else:
            dedupe_status = DEDUPE_FIRST_ATTEMPT
        return {
            "dedupe_status": dedupe_status,
            "idempotency_key": idempotency_key,
            "intent_fingerprint": intent_fingerprint,
            "matched_record": dict(same_key_record),
            "conflicting_record": None,
        }

    normalized_target = _normalize_for_hash(target_identifiers)
    conflicting_record = next(
        (
            record
            for record in records
            if _normalize_text(record.get("job_id"), default="") == _normalize_text(job_id, default="")
            and _normalize_text(record.get("write_action"), default="")
            == _normalize_text(write_action, default="")
            and _normalize_for_hash(record.get("target_identifiers") if _is_mapping(record.get("target_identifiers")) else {})
            != normalized_target
            and normalize_final_classification(record.get("final_classification"))
            in {"applied", "already_applied", "no_op"}
        ),
        None,
    )
    if conflicting_record is not None:
        return {
            "dedupe_status": DEDUPE_CONFLICTING_PRIOR_INTENT,
            "idempotency_key": idempotency_key,
            "intent_fingerprint": intent_fingerprint,
            "matched_record": None,
            "conflicting_record": dict(conflicting_record),
        }

    return {
        "dedupe_status": DEDUPE_FIRST_ATTEMPT,
        "idempotency_key": idempotency_key,
        "intent_fingerprint": intent_fingerprint,
        "matched_record": None,
        "conflicting_record": None,
    }
