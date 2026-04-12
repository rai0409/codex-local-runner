from __future__ import annotations

import argparse
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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect a recorded orchestration job")
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument("--job-id")
    selector.add_argument("--latest", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--db-path", default=DEFAULT_LEDGER_DB_PATH)
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


def _read_fail_reasons(path_value: Any) -> list[str]:
    if not isinstance(path_value, str) or not path_value.strip():
        return []
    path = Path(path_value)
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    raw = payload.get("fail_reasons")
    if not isinstance(raw, (list, tuple)):
        return []
    return [str(item) for item in raw]


def _build_output(row: dict[str, Any]) -> dict[str, Any]:
    rubric_path = row.get("rubric_path")
    merge_gate_path = row.get("merge_gate_path")
    return {
        "job_id": row.get("job_id"),
        "repo": row.get("repo"),
        "task_type": row.get("task_type"),
        "provider": row.get("provider"),
        "accepted_status": row.get("accepted_status"),
        "declared_category": row.get("declared_category"),
        "observed_category": row.get("observed_category"),
        "merge_eligible": _as_optional_bool(row.get("merge_eligible")),
        "merge_gate_passed": _as_optional_bool(row.get("merge_gate_passed")),
        "created_at": row.get("created_at"),
        "paths": {
            "request": row.get("request_path"),
            "result": row.get("result_path"),
            "rubric": rubric_path,
            "merge_gate": merge_gate_path,
        },
        "fail_reasons": {
            "rubric": _read_fail_reasons(rubric_path),
            "merge_gate": _read_fail_reasons(merge_gate_path),
        },
    }


def _fmt(value: Any) -> str:
    if value is None:
        return "<missing>"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _format_human(output: dict[str, Any]) -> str:
    lines = [
        f"job_id: {_fmt(output.get('job_id'))}",
        f"repo: {_fmt(output.get('repo'))}",
        f"task_type: {_fmt(output.get('task_type'))}",
        f"provider: {_fmt(output.get('provider'))}",
        f"accepted_status: {_fmt(output.get('accepted_status'))}",
        f"declared_category: {_fmt(output.get('declared_category'))}",
        f"observed_category: {_fmt(output.get('observed_category'))}",
        f"merge_eligible: {_fmt(output.get('merge_eligible'))}",
        f"merge_gate_passed: {_fmt(output.get('merge_gate_passed'))}",
        f"created_at: {_fmt(output.get('created_at'))}",
        f"request_path: {_fmt(output['paths'].get('request'))}",
        f"result_path: {_fmt(output['paths'].get('result'))}",
        f"rubric_path: {_fmt(output['paths'].get('rubric'))}",
        f"merge_gate_path: {_fmt(output['paths'].get('merge_gate'))}",
        "rubric_fail_reasons: "
        + (", ".join(output["fail_reasons"]["rubric"]) if output["fail_reasons"]["rubric"] else "none"),
        "merge_gate_fail_reasons: "
        + (
            ", ".join(output["fail_reasons"]["merge_gate"])
            if output["fail_reasons"]["merge_gate"]
            else "none"
        ),
    ]
    return "\n".join(lines)


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

    output = _build_output(row)
    if args.as_json:
        print(json.dumps(output, ensure_ascii=False, sort_keys=True))
    else:
        print(_format_human(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
