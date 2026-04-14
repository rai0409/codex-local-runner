from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from orchestrator.ledger import DEFAULT_LEDGER_DB_PATH  # noqa: E402
from orchestrator.ledger import get_job_by_id  # noqa: E402
from scripts.operator_review_decision import DEFAULT_REVIEW_DECISION_LOG_PATH  # noqa: E402


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect read-only operator decision history with optional policy recommendation context."
    )
    parser.add_argument("--decision-log-path", default=DEFAULT_REVIEW_DECISION_LOG_PATH)
    parser.add_argument("--db-path", default=DEFAULT_LEDGER_DB_PATH)
    parser.add_argument("--job-id")
    parser.add_argument("--decision", choices=("keep", "rollback", "retry", "escalate"))
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--include-recommendation", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def _read_json_object(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _load_decision_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    for line in lines:
        text = line.strip()
        if not text:
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _normalize_decision_effect(record: Mapping[str, Any]) -> str | None:
    raw = record.get("decision_effect")
    if raw is None:
        return None
    text = str(raw).strip()
    return text or None


def _execution_meaning(record: Mapping[str, Any]) -> str:
    decision = str(record.get("decision", "")).strip().lower()
    decision_effect = _normalize_decision_effect(record) or ""

    if decision_effect.startswith("bookkeeping_only_"):
        return "bookkeeping_only_non_executing"
    if decision == "rollback":
        return "rollback_path_requested"
    if decision in {"retry", "escalate", "keep"}:
        return "bookkeeping_only_non_executing"
    return "unknown"


def _reason_summary(record: Mapping[str, Any]) -> str | None:
    for key in ("decision_error", "rollback_execution_error"):
        value = record.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _derive_machine_review_payload_path(job_row: Mapping[str, Any]) -> Path | None:
    result_path = job_row.get("result_path")
    job_id = str(job_row.get("job_id", "")).strip()
    if not isinstance(result_path, str) or not result_path.strip() or not job_id:
        return None
    return Path(result_path).resolve().parent / f"{job_id}_machine_review_payload.json"


def _read_current_policy_recommendation(
    *,
    job_id: str | None,
    db_path: str,
    cache: dict[str, dict[str, Any] | None],
) -> dict[str, Any] | None:
    if not job_id:
        return None
    if job_id in cache:
        return cache[job_id]

    row = get_job_by_id(job_id, db_path=db_path)
    if row is None:
        cache[job_id] = None
        return None
    payload_path = _derive_machine_review_payload_path(row)
    if payload_path is None:
        cache[job_id] = None
        return None
    machine_payload = _read_json_object(payload_path)
    if machine_payload is None:
        cache[job_id] = None
        return None
    recommendation = {
        "recommended_action": machine_payload.get("recommended_action"),
        "policy_version": machine_payload.get("policy_version"),
        "policy_reasons": machine_payload.get("policy_reasons"),
        "requires_human_review": machine_payload.get("requires_human_review"),
    }
    cache[job_id] = recommendation
    return recommendation


def _build_history(
    *,
    decision_log_path: str,
    db_path: str,
    job_id: str | None,
    decision: str | None,
    limit: int,
    include_recommendation: bool,
) -> dict[str, Any]:
    rows = _load_decision_rows(Path(decision_log_path))
    filtered: list[dict[str, Any]] = []
    normalized_job_id = str(job_id).strip() if job_id else None
    normalized_decision = str(decision).strip().lower() if decision else None
    recommendation_cache: dict[str, dict[str, Any] | None] = {}

    for row in reversed(rows):
        row_job_id = str(row.get("job_id", "")).strip() or None
        row_decision = str(row.get("decision", "")).strip().lower() or None
        if normalized_job_id is not None and row_job_id != normalized_job_id:
            continue
        if normalized_decision is not None and row_decision != normalized_decision:
            continue

        item = {
            "decided_at": row.get("decided_at"),
            "job_id": row_job_id,
            "decision": row_decision,
            "decision_status": row.get("decision_status"),
            "decision_effect": _normalize_decision_effect(row),
            "execution_meaning": _execution_meaning(row),
            "rollback_execution_status": row.get("rollback_execution_status"),
            "reason_summary": _reason_summary(row),
            "rollback_trace_id": row.get("rollback_trace_id"),
        }
        if include_recommendation:
            item["current_policy_recommendation"] = _read_current_policy_recommendation(
                job_id=row_job_id,
                db_path=db_path,
                cache=recommendation_cache,
            )
        filtered.append(item)
        if len(filtered) >= max(0, limit):
            break

    return {
        "decision_log_path": str(decision_log_path),
        "count": len(filtered),
        "decisions": filtered,
    }


def _format_human(report: Mapping[str, Any]) -> str:
    lines = [
        f"decision_log_path: {report.get('decision_log_path')}",
        f"count: {report.get('count')}",
    ]
    decisions = report.get("decisions")
    if not isinstance(decisions, list) or not decisions:
        lines.append("decisions: none")
        return "\n".join(lines)

    lines.append("decisions:")
    for item in decisions:
        if not isinstance(item, Mapping):
            continue
        lines.append(
            "- decided_at={decided_at} job_id={job_id} decision={decision} "
            "decision_status={decision_status} decision_effect={decision_effect} "
            "execution_meaning={execution_meaning} rollback_execution_status={rollback_execution_status} "
            "reason_summary={reason_summary}".format(
                decided_at=item.get("decided_at"),
                job_id=item.get("job_id"),
                decision=item.get("decision"),
                decision_status=item.get("decision_status"),
                decision_effect=item.get("decision_effect"),
                execution_meaning=item.get("execution_meaning"),
                rollback_execution_status=item.get("rollback_execution_status"),
                reason_summary=item.get("reason_summary"),
            )
        )
        recommendation = item.get("current_policy_recommendation")
        if isinstance(recommendation, Mapping):
            lines.append(
                "  current_policy_recommendation: action={action} policy_version={policy_version} "
                "requires_human_review={requires_human_review}".format(
                    action=recommendation.get("recommended_action"),
                    policy_version=recommendation.get("policy_version"),
                    requires_human_review=recommendation.get("requires_human_review"),
                )
            )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    report = _build_history(
        decision_log_path=str(args.decision_log_path),
        db_path=str(args.db_path),
        job_id=(str(args.job_id).strip() if args.job_id else None),
        decision=(str(args.decision).strip() if args.decision else None),
        limit=int(args.limit),
        include_recommendation=bool(args.include_recommendation),
    )
    if args.as_json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    else:
        print(_format_human(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
