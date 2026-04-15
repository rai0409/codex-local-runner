from __future__ import annotations

import argparse
from datetime import datetime
from datetime import timezone
from html import escape
import json
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from orchestrator.ledger import DEFAULT_LEDGER_DB_PATH  # noqa: E402
from orchestrator.ledger import get_job_by_id  # noqa: E402
from orchestrator.ledger import get_latest_job  # noqa: E402
from orchestrator.ledger import get_rollback_execution_by_job_id  # noqa: E402
from orchestrator.ledger import get_rollback_trace_by_job_id  # noqa: E402
from orchestrator.ledger import record_machine_review_payload_path  # noqa: E402
from automation.review.recovery_policy import POLICY_VERSION  # noqa: E402
from automation.review.recovery_policy import evaluate_recovery_policy  # noqa: E402


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build operator summary artifacts for a recorded job")
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument("--job-id")
    selector.add_argument("--latest", action="store_true")
    parser.add_argument("--db-path", default=DEFAULT_LEDGER_DB_PATH)
    parser.add_argument("--out-dir")
    return parser


def _as_optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes"}:
            return True
        if normalized in {"0", "false", "no"}:
            return False
    return None


def _read_json(path_value: Any) -> dict[str, Any] | None:
    if not isinstance(path_value, str) or not path_value.strip():
        return None
    path = Path(path_value)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _derive_validation_status(result_payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(result_payload, dict):
        return {"verify_status": None, "verify_reason": None}

    execution = result_payload.get("execution")
    if not isinstance(execution, dict):
        return {"verify_status": None, "verify_reason": None}

    verify = execution.get("verify")
    if isinstance(verify, dict):
        return {
            "verify_status": verify.get("status"),
            "verify_reason": verify.get("reason"),
        }

    return {"verify_status": None, "verify_reason": None}


def _derive_output_dir(row: dict[str, Any], *, out_dir_arg: str | None) -> Path:
    if out_dir_arg:
        return Path(out_dir_arg)

    result_path = row.get("result_path")
    if isinstance(result_path, str) and result_path.strip():
        return Path(result_path).resolve().parent

    return Path.cwd()


def _build_summary(row: dict[str, Any], *, db_path: str) -> dict[str, Any]:
    result_payload = _read_json(row.get("result_path"))
    rollback_trace = get_rollback_trace_by_job_id(str(row.get("job_id", "")), db_path=db_path)
    rollback_execution = get_rollback_execution_by_job_id(str(row.get("job_id", "")), db_path=db_path)

    validation = _derive_validation_status(result_payload)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "repo": row.get("repo"),
        "job_id": row.get("job_id"),
        "accepted_status": row.get("accepted_status"),
        "declared_category": row.get("declared_category"),
        "observed_category": row.get("observed_category"),
        "validation": validation,
        "merge": {
            "merge_eligible": _as_optional_bool(row.get("merge_eligible")),
            "merge_gate_passed": _as_optional_bool(row.get("merge_gate_passed")),
        },
        "rollback": {
            "trace_recorded": rollback_trace is not None,
            "rollback_trace_id": rollback_trace.get("rollback_trace_id") if rollback_trace else None,
            "rollback_eligible": (
                _as_optional_bool(rollback_trace.get("rollback_eligible"))
                if rollback_trace
                else None
            ),
            "rollback_execution_recorded": rollback_execution is not None,
            "rollback_execution_status": (
                rollback_execution.get("execution_status") if rollback_execution else None
            ),
        },
        "paths": {
            "request": row.get("request_path"),
            "result": row.get("result_path"),
            "rubric": row.get("rubric_path"),
            "merge_gate": row.get("merge_gate_path"),
            "classification": row.get("classification_path"),
        },
    }


def _normalize_changed_files(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    normalized: list[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            normalized.append(text)
    return normalized


def _derive_changed_files(
    *,
    request_payload: dict[str, Any] | None,
    result_payload: dict[str, Any] | None,
    classification_payload: dict[str, Any] | None,
) -> list[str]:
    if isinstance(classification_payload, dict):
        changed = _normalize_changed_files(classification_payload.get("changed_files"))
        if changed:
            return changed

    if isinstance(request_payload, dict):
        changed = _normalize_changed_files(request_payload.get("changed_files"))
        if changed:
            return changed

    if isinstance(result_payload, dict):
        changed = _normalize_changed_files(result_payload.get("changed_files"))
        if changed:
            return changed
        execution = result_payload.get("execution")
        if isinstance(execution, dict):
            changed = _normalize_changed_files(execution.get("changed_files"))
            if changed:
                return changed
    return []


def _derive_int_signal(
    *,
    request_payload: dict[str, Any] | None,
    result_payload: dict[str, Any] | None,
    key: str,
) -> int:
    candidates: list[Any] = []
    if isinstance(result_payload, dict):
        candidates.append(result_payload.get(key))
        execution = result_payload.get("execution")
        if isinstance(execution, dict):
            candidates.append(execution.get(key))
    if isinstance(request_payload, dict):
        candidates.append(request_payload.get(key))

    for value in candidates:
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            stripped = value.strip()
            if stripped and stripped.lstrip("-").isdigit():
                return int(stripped)
    return 0


def _derive_required_tests_signals(
    *,
    request_payload: dict[str, Any] | None,
    result_payload: dict[str, Any] | None,
    rubric_payload: dict[str, Any] | None,
) -> tuple[bool, bool, bool]:
    if isinstance(rubric_payload, dict):
        declared = _as_optional_bool(rubric_payload.get("required_tests_declared"))
        executed = _as_optional_bool(rubric_payload.get("required_tests_executed"))
        passed = _as_optional_bool(rubric_payload.get("required_tests_passed"))
        if declared is not None and executed is not None and passed is not None:
            return declared, executed, passed

    declared = False
    if isinstance(request_payload, dict):
        validation_commands = request_payload.get("validation_commands")
        if isinstance(validation_commands, list):
            declared = len(validation_commands) > 0

    verify_status = ""
    if isinstance(result_payload, dict):
        execution = result_payload.get("execution")
        if isinstance(execution, dict):
            verify = execution.get("verify")
            if isinstance(verify, dict):
                verify_status = str(verify.get("status", "")).strip().lower()

    if verify_status == "passed":
        return declared, True, True
    if verify_status == "failed":
        return declared, True, False
    return declared, False, False


def _derive_prompt_contract_compliance(
    request_payload: dict[str, Any] | None,
) -> bool | None:
    if not isinstance(request_payload, dict):
        return None
    explicit = _as_optional_bool(request_payload.get("prompt_contract_compliant"))
    if explicit is not None:
        return explicit
    required = ("repo", "task_type", "goal", "provider")
    for key in required:
        value = request_payload.get(key)
        if value is None or not str(value).strip():
            return None
    validation_commands = request_payload.get("validation_commands")
    if not isinstance(validation_commands, list):
        return None
    return True


def _build_policy_facts(summary: dict[str, Any]) -> dict[str, Any]:
    paths = summary.get("paths", {})
    request_payload = _read_json(paths.get("request")) if isinstance(paths, dict) else None
    result_payload = _read_json(paths.get("result")) if isinstance(paths, dict) else None
    rubric_payload = _read_json(paths.get("rubric")) if isinstance(paths, dict) else None
    merge_gate_payload = _read_json(paths.get("merge_gate")) if isinstance(paths, dict) else None
    classification_payload = _read_json(paths.get("classification")) if isinstance(paths, dict) else None

    execution_payload = (
        result_payload.get("execution")
        if isinstance(result_payload, dict) and isinstance(result_payload.get("execution"), dict)
        else {}
    )
    verify_payload = (
        execution_payload.get("verify")
        if isinstance(execution_payload.get("verify"), dict)
        else {}
    )

    rollback = summary.get("rollback", {})
    merge = summary.get("merge", {})
    required_declared, required_executed, required_passed = _derive_required_tests_signals(
        request_payload=request_payload,
        result_payload=result_payload,
        rubric_payload=rubric_payload,
    )

    return {
        "accepted_status": summary.get("accepted_status"),
        "execution_status": execution_payload.get("status"),
        "verify_status": verify_payload.get("status"),
        "verify_reason": verify_payload.get("reason"),
        "declared_category": summary.get("declared_category"),
        "observed_category": summary.get("observed_category"),
        "changed_files": _derive_changed_files(
            request_payload=request_payload,
            result_payload=result_payload,
            classification_payload=classification_payload,
        ),
        "additions": _derive_int_signal(
            request_payload=request_payload,
            result_payload=result_payload,
            key="additions",
        ),
        "deletions": _derive_int_signal(
            request_payload=request_payload,
            result_payload=result_payload,
            key="deletions",
        ),
        "required_tests_declared": required_declared,
        "required_tests_executed": required_executed,
        "required_tests_passed": required_passed,
        "merge_eligible": (
            _as_optional_bool(rubric_payload.get("merge_eligible"))
            if isinstance(rubric_payload, dict)
            else _as_optional_bool(merge.get("merge_eligible"))
        ),
        "merge_gate_passed": (
            _as_optional_bool(merge_gate_payload.get("passed"))
            if isinstance(merge_gate_payload, dict)
            else _as_optional_bool(merge.get("merge_gate_passed"))
        ),
        "forbidden_files_untouched": (
            _as_optional_bool(rubric_payload.get("forbidden_files_untouched"))
            if isinstance(rubric_payload, dict)
            else None
        ),
        "diff_size_within_limit": (
            _as_optional_bool(rubric_payload.get("diff_size_within_limit"))
            if isinstance(rubric_payload, dict)
            else None
        ),
        "runtime_semantics_changed": (
            _as_optional_bool(rubric_payload.get("runtime_semantics_changed"))
            if isinstance(rubric_payload, dict)
            else None
        ),
        "contract_shape_changed": (
            _as_optional_bool(rubric_payload.get("contract_shape_changed"))
            if isinstance(rubric_payload, dict)
            else None
        ),
        "reviewer_fields_changed": (
            _as_optional_bool(rubric_payload.get("reviewer_fields_changed"))
            if isinstance(rubric_payload, dict)
            else None
        ),
        "rubric_fail_reasons": (
            rubric_payload.get("fail_reasons")
            if isinstance(rubric_payload, dict)
            else []
        ),
        "rubric_warnings": (
            rubric_payload.get("warnings")
            if isinstance(rubric_payload, dict)
            else []
        ),
        "merge_gate_fail_reasons": (
            merge_gate_payload.get("fail_reasons")
            if isinstance(merge_gate_payload, dict)
            else []
        ),
        "rollback_trace_recorded": (
            _as_optional_bool(rollback.get("trace_recorded")) if isinstance(rollback, dict) else None
        ),
        "rollback_eligible": (
            _as_optional_bool(rollback.get("rollback_eligible")) if isinstance(rollback, dict) else None
        ),
        "rollback_execution_status": (
            rollback.get("rollback_execution_status") if isinstance(rollback, dict) else None
        ),
        "prompt_contract_compliant": _derive_prompt_contract_compliance(request_payload),
    }


def _build_machine_review_payload(
    summary: dict[str, Any],
    *,
    summary_json_path: Path,
    summary_html_path: Path,
    machine_payload_path: Path,
) -> dict[str, Any]:
    merge = summary.get("merge")
    rollback = summary.get("rollback")
    validation = summary.get("validation")
    paths = summary.get("paths")

    merge_eligible = None
    merge_gate_passed = None
    if isinstance(merge, dict):
        merge_eligible = merge.get("merge_eligible")
        merge_gate_passed = merge.get("merge_gate_passed")

    rollback_eligible = None
    rollback_trace_recorded = None
    rollback_execution_status = None
    rollback_trace_id = None
    if isinstance(rollback, dict):
        rollback_eligible = rollback.get("rollback_eligible")
        rollback_trace_recorded = rollback.get("trace_recorded")
        rollback_execution_status = rollback.get("rollback_execution_status")
        rollback_trace_id = rollback.get("rollback_trace_id")

    verify_status = None
    verify_reason = None
    if isinstance(validation, dict):
        verify_status = validation.get("verify_status")
        verify_reason = validation.get("verify_reason")

    artifact_references: dict[str, Any] = {
        "operator_summary_json": str(summary_json_path),
        "operator_summary_html": str(summary_html_path),
        "machine_review_payload": str(machine_payload_path),
    }
    if isinstance(paths, dict):
        for key in ("request", "result", "rubric", "merge_gate", "classification"):
            artifact_references[key] = paths.get(key)

    policy_output = evaluate_recovery_policy(_build_policy_facts(summary))
    recovery_decision = str(policy_output.get("recovery_decision", "")).strip().lower()
    decision_basis = (
        [str(item) for item in policy_output.get("decision_basis", [])]
        if isinstance(policy_output.get("decision_basis"), (list, tuple))
        else []
    )
    failure_codes = (
        [str(item) for item in policy_output.get("failure_codes", [])]
        if isinstance(policy_output.get("failure_codes"), (list, tuple))
        else []
    )

    payload = {
        "schema_version": "1.1",
        "action_vocabulary": (
            "keep",
            "revise_current_state",
            "reset_and_retry",
            "escalate",
        ),
        "job_id": summary.get("job_id"),
        "repo": summary.get("repo"),
        "accepted_status": summary.get("accepted_status"),
        "merge_eligible": merge_eligible,
        "merge_gate_passed": merge_gate_passed,
        "rollback_eligible": rollback_eligible,
        "rollback_trace_id": rollback_trace_id,
        "validation": {
            "verify_status": verify_status,
            "verify_reason": verify_reason,
        },
        "guardrail_flags": {
            "rollback_trace_recorded": rollback_trace_recorded,
            "rollback_execution_status": rollback_execution_status,
        },
        "artifact_references": artifact_references,
        "policy_version": policy_output.get("policy_version", POLICY_VERSION),
        "score_total": policy_output.get("score_total"),
        "dimension_scores": policy_output.get("dimension_scores", {}),
        "failure_codes": failure_codes,
        "recovery_decision": recovery_decision,
        "decision_basis": decision_basis,
        "requires_human_review": bool(policy_output.get("requires_human_review", True)),
        "recommended_action": recovery_decision,
        "policy_reasons": failure_codes,
    }
    payload["retry_metadata"] = _build_retry_metadata(
        recovery_decision=recovery_decision,
        decision_basis=decision_basis,
    )
    return payload


def _build_retry_metadata(
    *,
    recovery_decision: Any,
    decision_basis: Any,
) -> dict[str, Any]:
    normalized_decision = str(recovery_decision or "").strip().lower()
    normalized_basis = (
        [str(reason) for reason in decision_basis]
        if isinstance(decision_basis, (list, tuple))
        else []
    )

    if normalized_decision == "reset_and_retry":
        return {
            "retry_recommended": True,
            "retry_basis": normalized_basis,
            "retry_blockers": [],
        }

    if normalized_decision in {"keep", "revise_current_state"}:
        return {
            "retry_recommended": False,
            "retry_basis": [],
            "retry_blockers": normalized_basis,
        }

    # Escalation is explicit-human-review territory.
    return {
        "retry_recommended": None,
        "retry_basis": [],
        "retry_blockers": normalized_basis,
    }


def _to_html(summary: dict[str, Any]) -> str:
    def line(label: str, value: Any) -> str:
        text = "<missing>" if value is None else str(value)
        return (
            '<div class="row">'
            f'<div class="label">{escape(label)}</div>'
            f'<div class="value">{escape(text)}</div>'
            "</div>"
        )

    rows = []
    rows.append(line("repo", summary.get("repo")))
    rows.append(line("job_id", summary.get("job_id")))
    rows.append(line("accepted_status", summary.get("accepted_status")))

    validation = summary.get("validation", {})
    if isinstance(validation, dict):
        rows.append(line("verify_status", validation.get("verify_status")))
        rows.append(line("verify_reason", validation.get("verify_reason")))

    merge = summary.get("merge", {})
    if isinstance(merge, dict):
        rows.append(line("merge_eligible", merge.get("merge_eligible")))
        rows.append(line("merge_gate_passed", merge.get("merge_gate_passed")))

    rollback = summary.get("rollback", {})
    if isinstance(rollback, dict):
        rows.append(line("rollback_trace_recorded", rollback.get("trace_recorded")))
        rows.append(line("rollback_eligible", rollback.get("rollback_eligible")))
        rows.append(line("rollback_execution_status", rollback.get("rollback_execution_status")))

    paths = summary.get("paths", {})
    if isinstance(paths, dict):
        rows.append(line("request_path", paths.get("request")))
        rows.append(line("result_path", paths.get("result")))
        rows.append(line("rubric_path", paths.get("rubric")))
        rows.append(line("merge_gate_path", paths.get("merge_gate")))
        rows.append(line("classification_path", paths.get("classification")))

    body = "\n".join(rows)
    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '  <meta charset="utf-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "  <title>Operator Summary</title>\n"
        "  <style>\n"
        "    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; "
        "margin: 0; padding: 16px; background: #f8fafc; color: #0f172a; }\n"
        "    .card { max-width: 760px; margin: 0 auto; background: #ffffff; border-radius: 12px; "
        "padding: 16px; box-shadow: 0 1px 4px rgba(15, 23, 42, 0.08); }\n"
        "    h1 { margin: 0 0 12px; font-size: 20px; }\n"
        "    .row { display: grid; grid-template-columns: 160px 1fr; gap: 8px; "
        "padding: 8px 0; border-bottom: 1px solid #e2e8f0; }\n"
        "    .row:last-child { border-bottom: 0; }\n"
        "    .label { font-weight: 600; color: #334155; }\n"
        "    .value { overflow-wrap: anywhere; }\n"
        "    @media (max-width: 640px) {\n"
        "      .row { grid-template-columns: 1fr; gap: 4px; }\n"
        "      .label { font-size: 13px; }\n"
        "      .value { font-size: 14px; }\n"
        "    }\n"
        "  </style>\n"
        "</head>\n"
        "<body>\n"
        '  <div class="card">\n'
        "    <h1>Operator Summary</h1>\n"
        f"{body}\n"
        "  </div>\n"
        "</body>\n"
        "</html>\n"
    )


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.latest:
        row = get_latest_job(db_path=args.db_path)
        if row is None:
            print("No recorded jobs found in ledger.", file=sys.stderr)
            return 1
    else:
        row = get_job_by_id(args.job_id, db_path=args.db_path)
        if row is None:
            print(f"Job not found: {args.job_id}", file=sys.stderr)
            return 1

    summary = _build_summary(row, db_path=str(args.db_path))
    output_dir = _derive_output_dir(row, out_dir_arg=args.out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    job_id = str(summary.get("job_id", "unknown-job"))
    json_path = output_dir / f"{job_id}_operator_summary.json"
    html_path = output_dir / f"{job_id}_operator_summary.html"
    machine_payload_path = output_dir / f"{job_id}_machine_review_payload.json"

    json_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    html_path.write_text(_to_html(summary), encoding="utf-8")
    machine_payload = _build_machine_review_payload(
        summary,
        summary_json_path=json_path,
        summary_html_path=html_path,
        machine_payload_path=machine_payload_path,
    )
    machine_payload_path.write_text(
        json.dumps(machine_payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    record_machine_review_payload_path(
        job_id=job_id,
        machine_review_payload_path=str(machine_payload_path.resolve()),
        db_path=args.db_path,
    )

    print(f"summary_json_path={json_path}")
    print(f"summary_html_path={html_path}")
    print(f"machine_review_payload_path={machine_payload_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
