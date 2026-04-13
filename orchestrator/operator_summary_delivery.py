from __future__ import annotations

import json
import os
from datetime import datetime
from datetime import timezone
from pathlib import Path
import subprocess
import sys
from typing import Any
from typing import Mapping
from urllib.error import HTTPError
from urllib.error import URLError
from urllib.request import Request
from urllib.request import urlopen
from zoneinfo import ZoneInfo

from orchestrator.ledger import DEFAULT_LEDGER_DB_PATH
from orchestrator.ledger import list_recorded_jobs
from orchestrator.operator_schedules import OPERATOR_SCHEDULES_PATH
from orchestrator.operator_schedules import get_due_operator_schedules
from orchestrator.operator_schedules import load_operator_schedules

DEFAULT_WINDOW_STATE_PATH = "state/operator_summary_windows.json"
DEFAULT_NOTIFICATION_LOG_PATH = "state/operator_summary_notifications.jsonl"
WEBHOOK_URL_ENV_VAR = "OPERATOR_SUMMARY_WEBHOOK_URL"


class JsonlNotifier:
    def __init__(self, *, log_path: str | Path) -> None:
        self._log_path = Path(log_path)

    def notify(self, payload: Mapping[str, Any]) -> None:
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        with self._log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(dict(payload), ensure_ascii=False, sort_keys=True))
            handle.write("\n")


class WebhookNotifier:
    def __init__(self, *, webhook_url: str, timeout_seconds: float = 10.0) -> None:
        normalized = str(webhook_url).strip()
        if not normalized:
            raise ValueError(
                f"delivery.method=webhook_operator_summary requires {WEBHOOK_URL_ENV_VAR}"
            )
        self._webhook_url = normalized
        self._timeout_seconds = timeout_seconds

    def notify(self, payload: Mapping[str, Any]) -> None:
        body = json.dumps(dict(payload), ensure_ascii=False, sort_keys=True).encode("utf-8")
        request = Request(
            self._webhook_url,
            data=body,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:  # noqa: S310
                status_code = getattr(response, "status", None) or response.getcode()
        except HTTPError as exc:
            raise RuntimeError(f"webhook delivery failed with HTTP {exc.code}") from exc
        except URLError as exc:
            raise RuntimeError(f"webhook delivery connection failed: {exc.reason}") from exc
        if status_code < 200 or status_code >= 300:
            raise RuntimeError(f"webhook delivery failed with HTTP {status_code}")


def _parse_now_utc(now_utc: datetime | None = None) -> datetime:
    candidate = now_utc or datetime.now(timezone.utc)
    if candidate.tzinfo is None:
        raise ValueError("now_utc must be timezone-aware")
    return candidate


def _load_window_state(path: str | Path) -> dict[str, Any]:
    state_path = Path(path)
    if not state_path.exists():
        return {"sent_windows": {}}
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"sent_windows": {}}
    if not isinstance(payload, dict):
        return {"sent_windows": {}}
    sent_windows = payload.get("sent_windows")
    if not isinstance(sent_windows, dict):
        sent_windows = {}
    return {"sent_windows": sent_windows}


def _save_window_state(path: str | Path, state: Mapping[str, Any]) -> None:
    state_path = Path(path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(dict(state), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _window_key(schedule: Mapping[str, Any], *, now_utc: datetime) -> str:
    schedule_id = str(schedule.get("schedule_id", "")).strip()
    timezone_name = str(schedule.get("timezone", "UTC")).strip()
    local_now = now_utc.astimezone(ZoneInfo(timezone_name))
    minute_label = f"{local_now.hour:02d}:{local_now.minute:02d}"
    date_label = local_now.date().isoformat()
    return f"{schedule_id}|{date_label}|{minute_label}"


def _selector_matches(row: Mapping[str, Any], selector: Mapping[str, Any]) -> bool:
    for key, expected in selector.items():
        actual = row.get(str(key))
        if isinstance(expected, bool):
            if bool(actual) != expected:
                return False
            continue
        if str(actual).strip() != str(expected).strip():
            return False
    return True


def _select_latest_job_for_schedule(
    schedule: Mapping[str, Any],
    *,
    db_path: str,
) -> dict[str, Any] | None:
    target = schedule.get("target")
    if not isinstance(target, Mapping):
        return None
    target_repo = str(target.get("repo", "")).strip()
    if not target_repo:
        return None

    selector_raw = schedule.get("job_selector")
    selector = selector_raw if isinstance(selector_raw, Mapping) else {}

    rows = list_recorded_jobs(db_path=db_path)
    for row in rows:
        if str(row.get("repo", "")).strip() != target_repo:
            continue
        if not _selector_matches(row, selector):
            continue
        return row
    return None


def _expected_summary_paths(job_row: Mapping[str, Any]) -> tuple[Path, Path] | None:
    result_path_value = job_row.get("result_path")
    job_id = str(job_row.get("job_id", "")).strip()
    if not job_id:
        return None
    if not isinstance(result_path_value, str) or not result_path_value.strip():
        return None
    result_path = Path(result_path_value)
    base_dir = result_path.resolve().parent
    return (
        base_dir / f"{job_id}_operator_summary.json",
        base_dir / f"{job_id}_operator_summary.html",
    )


def _build_summary_for_job(*, job_id: str, db_path: str) -> tuple[Path, Path]:
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "scripts" / "build_operator_summary.py"
    proc = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--job-id",
            job_id,
            "--db-path",
            db_path,
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    if proc.returncode != 0:
        stderr = proc.stderr.strip()
        raise RuntimeError(f"summary build failed for job_id={job_id}: {stderr}")

    json_path: Path | None = None
    html_path: Path | None = None
    for line in proc.stdout.splitlines():
        if line.startswith("summary_json_path="):
            json_path = Path(line.split("=", 1)[1].strip())
        if line.startswith("summary_html_path="):
            html_path = Path(line.split("=", 1)[1].strip())
    if json_path is None or html_path is None:
        raise RuntimeError(f"summary build output missing paths for job_id={job_id}")
    return (json_path, html_path)


def _get_notifier(*, method: str, notification_log_path: str) -> JsonlNotifier | WebhookNotifier:
    normalized = str(method).strip()
    if normalized == "placeholder_operator_summary":
        return JsonlNotifier(log_path=notification_log_path)
    if normalized == "webhook_operator_summary":
        return WebhookNotifier(webhook_url=os.getenv(WEBHOOK_URL_ENV_VAR, ""))
    raise ValueError(f"unsupported delivery.method: {normalized}")


def run_scheduled_operator_summary_delivery(
    *,
    now_utc: datetime | None = None,
    db_path: str = DEFAULT_LEDGER_DB_PATH,
    schedule_path: str = OPERATOR_SCHEDULES_PATH,
    window_state_path: str = DEFAULT_WINDOW_STATE_PATH,
    notification_log_path: str = DEFAULT_NOTIFICATION_LOG_PATH,
) -> dict[str, Any]:
    now = _parse_now_utc(now_utc)
    policy = load_operator_schedules(schedule_path)
    due_schedules = get_due_operator_schedules(now_utc=now, schedule_policy=policy)
    window_state = _load_window_state(window_state_path)
    sent_windows = window_state.get("sent_windows")
    if not isinstance(sent_windows, dict):
        sent_windows = {}

    deliveries: list[dict[str, Any]] = []
    state_changed = False

    for schedule in due_schedules:
        schedule_id = str(schedule.get("schedule_id", "")).strip()
        if not schedule_id:
            continue

        key = _window_key(schedule, now_utc=now)
        if key in sent_windows:
            deliveries.append(
                {
                    "schedule_id": schedule_id,
                    "window_key": key,
                    "status": "skipped",
                    "reason": "already_sent_in_window",
                }
            )
            continue

        job_row = _select_latest_job_for_schedule(schedule, db_path=db_path)
        if job_row is None:
            deliveries.append(
                {
                    "schedule_id": schedule_id,
                    "window_key": key,
                    "status": "skipped",
                    "reason": "no_matching_recorded_job",
                }
            )
            continue

        expected_paths = _expected_summary_paths(job_row)
        if expected_paths is None:
            deliveries.append(
                {
                    "schedule_id": schedule_id,
                    "window_key": key,
                    "status": "failed",
                    "reason": "summary_paths_unresolvable",
                    "job_id": job_row.get("job_id"),
                }
            )
            continue

        json_path, html_path = expected_paths
        reused = json_path.exists() and html_path.exists()
        if not reused:
            built_json_path, built_html_path = _build_summary_for_job(
                job_id=str(job_row.get("job_id", "")).strip(),
                db_path=db_path,
            )
            json_path = built_json_path
            html_path = built_html_path

        delivery = schedule.get("delivery")
        if not isinstance(delivery, Mapping):
            deliveries.append(
                {
                    "schedule_id": schedule_id,
                    "window_key": key,
                    "status": "failed",
                    "reason": "invalid_delivery_config",
                    "job_id": job_row.get("job_id"),
                }
            )
            continue

        try:
            notifier = _get_notifier(
                method=str(delivery.get("method", "")),
                notification_log_path=notification_log_path,
            )
        except Exception as exc:
            deliveries.append(
                {
                    "schedule_id": schedule_id,
                    "window_key": key,
                    "status": "failed",
                    "reason": "notification_config_error",
                    "job_id": job_row.get("job_id"),
                    "error": str(exc),
                }
            )
            continue

        payload = {
            "schedule_id": schedule_id,
            "window_key": key,
            "decision_mode": (
                schedule.get("decision", {}).get("mode")
                if isinstance(schedule.get("decision"), Mapping)
                else None
            ),
            "repo": (
                schedule.get("target", {}).get("repo")
                if isinstance(schedule.get("target"), Mapping)
                else None
            ),
            "job_id": job_row.get("job_id"),
            "accepted_status": job_row.get("accepted_status"),
            "summary_json_path": str(json_path),
            "summary_html_path": str(html_path),
            "summary_reused": reused,
            "notified_at": now.isoformat(timespec="seconds"),
        }
        try:
            notifier.notify(payload)
        except Exception as exc:  # pragma: no cover
            deliveries.append(
                {
                    "schedule_id": schedule_id,
                    "window_key": key,
                    "status": "failed",
                    "reason": "notification_failed",
                    "job_id": job_row.get("job_id"),
                    "error": str(exc),
                }
            )
            continue

        sent_windows[key] = {
            "schedule_id": schedule_id,
            "job_id": job_row.get("job_id"),
            "notified_at": now.isoformat(timespec="seconds"),
        }
        state_changed = True
        deliveries.append(
            {
                "schedule_id": schedule_id,
                "window_key": key,
                "status": "written",
                "job_id": job_row.get("job_id"),
                "summary_reused": reused,
            }
        )

    if state_changed:
        _save_window_state(window_state_path, {"sent_windows": sent_windows})

    return {
        "now_utc": now.isoformat(timespec="seconds"),
        "due_count": len(due_schedules),
        "delivery_count": len([item for item in deliveries if item.get("status") == "written"]),
        "deliveries": deliveries,
    }
