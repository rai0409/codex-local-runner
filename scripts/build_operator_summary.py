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
    if isinstance(execution, dict):
        verify = execution.get("verify")
        if isinstance(verify, dict):
            return {
                "verify_status": verify.get("status"),
                "verify_reason": verify.get("reason"),
            }

    reviewer_handoff = result_payload.get("reviewer_handoff")
    if isinstance(reviewer_handoff, dict):
        validation = reviewer_handoff.get("validation")
        if isinstance(validation, dict):
            return {
                "verify_status": validation.get("verify_status"),
                "verify_reason": validation.get("verify_reason"),
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

    json_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    html_path.write_text(_to_html(summary), encoding="utf-8")

    print(f"summary_json_path={json_path}")
    print(f"summary_html_path={html_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
