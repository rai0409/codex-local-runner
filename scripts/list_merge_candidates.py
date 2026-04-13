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
from orchestrator.ledger import list_recorded_jobs  # noqa: E402
from orchestrator.policy_loader import load_merge_gate_policy  # noqa: E402


def _positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--latest must be a positive integer") from exc
    if number <= 0:
        raise argparse.ArgumentTypeError("--latest must be a positive integer")
    return number


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="List visible safe auto-merge candidates")
    parser.add_argument("--latest", type=_positive_int)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--db-path", default=DEFAULT_LEDGER_DB_PATH)
    return parser


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        return normalized in {"1", "true", "yes"}
    return False


def _candidate_from_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "job_id": row.get("job_id"),
        "repo": row.get("repo"),
        "observed_category": row.get("observed_category"),
        "merge_gate_passed": _as_bool(row.get("merge_gate_passed")),
        "created_at": row.get("created_at"),
    }


def _filter_candidates(
    rows: tuple[dict[str, Any], ...],
    *,
    safe_categories: set[str],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for row in rows:
        if str(row.get("accepted_status", "")).strip() != "accepted":
            continue
        if not _as_bool(row.get("merge_gate_passed")):
            continue
        observed_category = str(row.get("observed_category", "")).strip()
        if observed_category not in safe_categories:
            continue
        candidates.append(_candidate_from_row(row))
    return candidates


def _format_human(candidates: list[dict[str, Any]]) -> str:
    if not candidates:
        return "No merge candidates found."
    lines: list[str] = []
    for candidate in candidates:
        lines.append(
            "job_id={job_id} observed_category={observed_category} "
            "merge_gate_passed={merge_gate_passed} repo={repo} created_at={created_at}".format(
                job_id=candidate.get("job_id"),
                observed_category=candidate.get("observed_category"),
                merge_gate_passed=str(candidate.get("merge_gate_passed")).lower(),
                repo=candidate.get("repo"),
                created_at=candidate.get("created_at"),
            )
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    policy = load_merge_gate_policy()
    safe_categories = {str(item).strip() for item in policy.get("auto_merge_categories", ()) if str(item).strip()}

    rows = list_recorded_jobs(db_path=args.db_path)
    candidates = _filter_candidates(rows, safe_categories=safe_categories)
    if args.latest is not None:
        candidates = candidates[: args.latest]

    payload = {"candidates": candidates}
    if args.as_json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        print(_format_human(candidates))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
