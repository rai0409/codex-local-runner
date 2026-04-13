from __future__ import annotations

import argparse
from datetime import datetime
from datetime import timezone
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from orchestrator.ledger import DEFAULT_LEDGER_DB_PATH  # noqa: E402
from orchestrator.operator_schedules import OPERATOR_SCHEDULES_PATH  # noqa: E402
from orchestrator.operator_summary_delivery import DEFAULT_NOTIFICATION_LOG_PATH  # noqa: E402
from orchestrator.operator_summary_delivery import DEFAULT_WINDOW_STATE_PATH  # noqa: E402
from orchestrator.operator_summary_delivery import run_scheduled_operator_summary_delivery  # noqa: E402


def _parse_now_utc(value: str | None) -> datetime | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--now-utc must be an ISO8601 datetime") from exc
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("--now-utc must include timezone offset")
    return parsed.astimezone(timezone.utc)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run scheduled operator-summary delivery")
    parser.add_argument("--db-path", default=DEFAULT_LEDGER_DB_PATH)
    parser.add_argument("--schedule-path", default=OPERATOR_SCHEDULES_PATH)
    parser.add_argument("--window-state-path", default=DEFAULT_WINDOW_STATE_PATH)
    parser.add_argument("--notification-log-path", default=DEFAULT_NOTIFICATION_LOG_PATH)
    parser.add_argument("--now-utc", type=_parse_now_utc)
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def _format_human(report: dict[str, object]) -> str:
    lines = [
        f"now_utc: {report.get('now_utc')}",
        f"due_count: {report.get('due_count')}",
        f"delivery_count: {report.get('delivery_count')}",
    ]
    deliveries = report.get("deliveries")
    if isinstance(deliveries, list):
        if not deliveries:
            lines.append("deliveries: none")
        else:
            lines.append("deliveries:")
            for item in deliveries:
                if isinstance(item, dict):
                    lines.append(
                        "- schedule_id={schedule_id} status={status} job_id={job_id} reason={reason}".format(
                            schedule_id=item.get("schedule_id"),
                            status=item.get("status"),
                            job_id=item.get("job_id"),
                            reason=item.get("reason"),
                        )
                    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    report = run_scheduled_operator_summary_delivery(
        now_utc=args.now_utc,
        db_path=str(args.db_path),
        schedule_path=str(args.schedule_path),
        window_state_path=str(args.window_state_path),
        notification_log_path=str(args.notification_log_path),
    )

    if args.as_json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    else:
        print(_format_human(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
