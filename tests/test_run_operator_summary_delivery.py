from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from orchestrator.ledger import record_job_evaluation
from orchestrator.operator_summary_delivery import run_scheduled_operator_summary_delivery


class RunOperatorSummaryDeliveryCliTests(unittest.TestCase):
    def _repo_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def _script_path(self) -> Path:
        return self._repo_root() / "scripts" / "run_operator_summary_delivery.py"

    def _parse_iso(self, value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    def _run(self, args: list[str], *, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            [sys.executable, str(self._script_path()), *args],
            capture_output=True,
            text=True,
            cwd=self._repo_root(),
            env=env,
        )

    def _seed_job(self, *, db_path: Path, job_id: str, repo: str = "codex-local-runner") -> tuple[Path, Path]:
        request_path = db_path.parent / f"{job_id}_request.json"
        result_path = db_path.parent / f"{job_id}_result.json"
        request_path.parent.mkdir(parents=True, exist_ok=True)
        request_path.write_text(
            json.dumps({"job_id": job_id}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        result_path.write_text(
            json.dumps(
                {
                    "job_id": job_id,
                    "execution": {"verify": {"status": "passed", "reason": "all_commands_passed"}},
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        record_job_evaluation(
            db_path=db_path,
            job_id=job_id,
            repo=repo,
            task_type="orchestration",
            provider="codex_cli",
            accepted_status="accepted",
            declared_category="docs_only",
            observed_category="docs_only",
            merge_eligible=True,
            merge_gate_passed=True,
            created_at="2026-04-13T00:00:00+00:00",
            request_path=str(request_path),
            result_path=str(result_path),
            rubric_path=None,
            merge_gate_path=None,
            classification_path=None,
        )
        return request_path, result_path

    def _write_schedule(
        self,
        *,
        schedule_path: Path,
        enabled: bool = True,
        times: tuple[str, ...] = ("09:00",),
        repo: str = "codex-local-runner",
        delivery_method: str = "placeholder_operator_summary",
    ) -> None:
        times_yaml = "\n".join([f'        - "{value}"' for value in times])
        schedule_path.parent.mkdir(parents=True, exist_ok=True)
        schedule_path.write_text(
            (
                "schedules:\n"
                "  - schedule_id: daily_operator_summary\n"
                f"    enabled: {'true' if enabled else 'false'}\n"
                "    timezone: UTC\n"
                "    trigger:\n"
                "      type: daily_times\n"
                "      times:\n"
                f"{times_yaml}\n"
                "    target:\n"
                f"      repo: {repo}\n"
                "    job_selector:\n"
                "      accepted_status: accepted\n"
                "    delivery:\n"
                f"      method: {delivery_method}\n"
                "    decision:\n"
                "      mode: human_review_required\n"
            ),
            encoding="utf-8",
        )

    class _MockHttpResponse:
        def __init__(self, status: int = 200) -> None:
            self.status = status

        def __enter__(self) -> "RunOperatorSummaryDeliveryCliTests._MockHttpResponse":
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:  # type: ignore[no-untyped-def]
            return False

        def getcode(self) -> int:
            return self.status

    def test_noop_when_nothing_due(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            db_path = root / "state" / "jobs.db"
            schedule_path = root / "config" / "operator_schedules.yaml"
            window_state_path = root / "state" / "windows.json"
            notification_log_path = root / "state" / "notifications.jsonl"
            self._seed_job(db_path=db_path, job_id="job-noop")
            self._write_schedule(schedule_path=schedule_path, times=("09:00",))

            proc = self._run(
                [
                    "--db-path",
                    str(db_path),
                    "--schedule-path",
                    str(schedule_path),
                    "--window-state-path",
                    str(window_state_path),
                    "--notification-log-path",
                    str(notification_log_path),
                    "--now-utc",
                    "2026-04-13T09:01:00+00:00",
                    "--json",
                ]
            )

        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["due_count"], 0)
        self.assertEqual(payload["delivery_count"], 0)
        self.assertEqual(payload["deliveries"], [])
        self.assertFalse(notification_log_path.exists())

    def test_due_schedule_delivers_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            db_path = root / "state" / "jobs.db"
            schedule_path = root / "config" / "operator_schedules.yaml"
            window_state_path = root / "state" / "windows.json"
            notification_log_path = root / "state" / "notifications.jsonl"
            _, result_path = self._seed_job(db_path=db_path, job_id="job-due")
            self._write_schedule(schedule_path=schedule_path, times=("09:00",))

            proc = self._run(
                [
                    "--db-path",
                    str(db_path),
                    "--schedule-path",
                    str(schedule_path),
                    "--window-state-path",
                    str(window_state_path),
                    "--notification-log-path",
                    str(notification_log_path),
                    "--now-utc",
                    "2026-04-13T09:00:00+00:00",
                    "--json",
                ]
            )

            summary_json = result_path.parent / "job-due_operator_summary.json"
            summary_html = result_path.parent / "job-due_operator_summary.html"
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["due_count"], 1)
            self.assertEqual(payload["delivery_count"], 1)
            self.assertEqual(payload["deliveries"][0]["status"], "written")
            self.assertTrue(summary_json.exists())
            self.assertTrue(summary_html.exists())
            self.assertTrue(notification_log_path.exists())

    def test_disabled_schedule_is_not_delivered(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            db_path = root / "state" / "jobs.db"
            schedule_path = root / "config" / "operator_schedules.yaml"
            window_state_path = root / "state" / "windows.json"
            notification_log_path = root / "state" / "notifications.jsonl"
            self._seed_job(db_path=db_path, job_id="job-disabled")
            self._write_schedule(schedule_path=schedule_path, enabled=False, times=("09:00",))

            proc = self._run(
                [
                    "--db-path",
                    str(db_path),
                    "--schedule-path",
                    str(schedule_path),
                    "--window-state-path",
                    str(window_state_path),
                    "--notification-log-path",
                    str(notification_log_path),
                    "--now-utc",
                    "2026-04-13T09:00:00+00:00",
                    "--json",
                ]
            )

        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["due_count"], 0)
        self.assertEqual(payload["delivery_count"], 0)
        self.assertFalse(notification_log_path.exists())

    def test_multiple_daily_sends_and_duplicate_window_protection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            db_path = root / "state" / "jobs.db"
            schedule_path = root / "config" / "operator_schedules.yaml"
            window_state_path = root / "state" / "windows.json"
            notification_log_path = root / "state" / "notifications.jsonl"
            self._seed_job(db_path=db_path, job_id="job-multi")
            self._write_schedule(schedule_path=schedule_path, times=("09:00", "17:00"))

            first = self._run(
                [
                    "--db-path",
                    str(db_path),
                    "--schedule-path",
                    str(schedule_path),
                    "--window-state-path",
                    str(window_state_path),
                    "--notification-log-path",
                    str(notification_log_path),
                    "--now-utc",
                    "2026-04-13T09:00:00+00:00",
                    "--json",
                ]
            )
            duplicate = self._run(
                [
                    "--db-path",
                    str(db_path),
                    "--schedule-path",
                    str(schedule_path),
                    "--window-state-path",
                    str(window_state_path),
                    "--notification-log-path",
                    str(notification_log_path),
                    "--now-utc",
                    "2026-04-13T09:00:00+00:00",
                    "--json",
                ]
            )
            evening = self._run(
                [
                    "--db-path",
                    str(db_path),
                    "--schedule-path",
                    str(schedule_path),
                    "--window-state-path",
                    str(window_state_path),
                    "--notification-log-path",
                    str(notification_log_path),
                    "--now-utc",
                    "2026-04-13T17:00:00+00:00",
                    "--json",
                ]
            )

            lines = notification_log_path.read_text(encoding="utf-8").splitlines()

        self.assertEqual(first.returncode, 0, msg=first.stderr)
        self.assertEqual(duplicate.returncode, 0, msg=duplicate.stderr)
        self.assertEqual(evening.returncode, 0, msg=evening.stderr)

        first_payload = json.loads(first.stdout)
        duplicate_payload = json.loads(duplicate.stdout)
        evening_payload = json.loads(evening.stdout)

        self.assertEqual(first_payload["delivery_count"], 1)
        self.assertEqual(duplicate_payload["delivery_count"], 0)
        self.assertEqual(duplicate_payload["deliveries"][0]["reason"], "already_sent_in_window")
        self.assertEqual(evening_payload["delivery_count"], 1)
        self.assertEqual(len(lines), 2)

    def test_reuses_existing_summary_artifacts_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            db_path = root / "state" / "jobs.db"
            schedule_path = root / "config" / "operator_schedules.yaml"
            window_state_path = root / "state" / "windows.json"
            notification_log_path = root / "state" / "notifications.jsonl"
            _, result_path = self._seed_job(db_path=db_path, job_id="job-reuse")
            self._write_schedule(schedule_path=schedule_path, times=("09:00",))

            existing_json = result_path.parent / "job-reuse_operator_summary.json"
            existing_html = result_path.parent / "job-reuse_operator_summary.html"
            existing_json.write_text(
                json.dumps({"sentinel": "reuse"}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            existing_html.write_text("<html>reuse</html>", encoding="utf-8")

            proc = self._run(
                [
                    "--db-path",
                    str(db_path),
                    "--schedule-path",
                    str(schedule_path),
                    "--window-state-path",
                    str(window_state_path),
                    "--notification-log-path",
                    str(notification_log_path),
                    "--now-utc",
                    "2026-04-13T09:00:00+00:00",
                    "--json",
                ]
            )

            lines = notification_log_path.read_text(encoding="utf-8").splitlines()
            notification = json.loads(lines[0])
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["delivery_count"], 1)
            self.assertTrue(payload["deliveries"][0]["summary_reused"])
            self.assertEqual(json.loads(existing_json.read_text(encoding="utf-8"))["sentinel"], "reuse")
            self.assertEqual(notification["summary_reused"], True)

    def test_default_stub_path_remains_unchanged_even_when_webhook_env_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            db_path = root / "state" / "jobs.db"
            schedule_path = root / "config" / "operator_schedules.yaml"
            window_state_path = root / "state" / "windows.json"
            notification_log_path = root / "state" / "notifications.jsonl"
            self._seed_job(db_path=db_path, job_id="job-stub-default")
            self._write_schedule(schedule_path=schedule_path, times=("09:00",))
            with patch("orchestrator.operator_summary_delivery.urlopen", side_effect=AssertionError("must_not_call_webhook")):
                with patch.dict(os.environ, {"OPERATOR_SUMMARY_WEBHOOK_URL": "http://example.test/hook"}, clear=False):
                    payload = run_scheduled_operator_summary_delivery(
                        now_utc=self._parse_iso("2026-04-13T09:00:00+00:00"),
                        db_path=str(db_path),
                        schedule_path=str(schedule_path),
                        window_state_path=str(window_state_path),
                        notification_log_path=str(notification_log_path),
                    )
            self.assertEqual(payload["delivery_count"], 1)
            self.assertTrue(notification_log_path.exists())

    def test_webhook_notifier_wiring_and_narrow_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            db_path = root / "state" / "jobs.db"
            schedule_path = root / "config" / "operator_schedules.yaml"
            window_state_path = root / "state" / "windows.json"
            notification_log_path = root / "state" / "notifications.jsonl"
            self._seed_job(db_path=db_path, job_id="job-webhook")
            self._write_schedule(
                schedule_path=schedule_path,
                times=("09:00",),
                delivery_method="webhook_operator_summary",
            )
            captured: dict[str, object] = {}

            def _fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
                captured["url"] = request.full_url
                captured["timeout"] = timeout
                captured["headers"] = dict(request.header_items())
                captured["body"] = request.data.decode("utf-8")
                return self._MockHttpResponse(status=200)

            with patch("orchestrator.operator_summary_delivery.urlopen", side_effect=_fake_urlopen):
                with patch.dict(os.environ, {"OPERATOR_SUMMARY_WEBHOOK_URL": "http://example.test/hook"}, clear=False):
                    payload = run_scheduled_operator_summary_delivery(
                        now_utc=self._parse_iso("2026-04-13T09:00:00+00:00"),
                        db_path=str(db_path),
                        schedule_path=str(schedule_path),
                        window_state_path=str(window_state_path),
                        notification_log_path=str(notification_log_path),
                    )

            self.assertEqual(payload["delivery_count"], 1)
            self.assertFalse(notification_log_path.exists())
            self.assertEqual(captured["url"], "http://example.test/hook")
            self.assertIn("application/json", str(captured["headers"]).lower())
            sent = json.loads(str(captured["body"]))
            self.assertEqual(sent["schedule_id"], "daily_operator_summary")
            self.assertEqual(sent["repo"], "codex-local-runner")
            self.assertEqual(sent["job_id"], "job-webhook")
            self.assertEqual(sent["accepted_status"], "accepted")
            self.assertIn("summary_json_path", sent)
            self.assertIn("summary_html_path", sent)
            self.assertIn("summary_reused", sent)
            self.assertNotIn("execute_merge", sent)
            self.assertNotIn("execute_rollback", sent)
            self.assertNotIn("action", sent)

    def test_webhook_misconfiguration_fails_explicitly_and_narrowly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            db_path = root / "state" / "jobs.db"
            schedule_path = root / "config" / "operator_schedules.yaml"
            window_state_path = root / "state" / "windows.json"
            notification_log_path = root / "state" / "notifications.jsonl"
            self._seed_job(db_path=db_path, job_id="job-webhook-missing-config")
            self._write_schedule(
                schedule_path=schedule_path,
                times=("09:00",),
                delivery_method="webhook_operator_summary",
            )
            with patch.dict(os.environ, {"OPERATOR_SUMMARY_WEBHOOK_URL": ""}, clear=False):
                payload = run_scheduled_operator_summary_delivery(
                    now_utc=self._parse_iso("2026-04-13T09:00:00+00:00"),
                    db_path=str(db_path),
                    schedule_path=str(schedule_path),
                    window_state_path=str(window_state_path),
                    notification_log_path=str(notification_log_path),
                )

            self.assertEqual(payload["due_count"], 1)
            self.assertEqual(payload["delivery_count"], 0)
            self.assertEqual(payload["deliveries"][0]["status"], "failed")
            self.assertEqual(payload["deliveries"][0]["reason"], "notification_config_error")
            self.assertIn("requires OPERATOR_SUMMARY_WEBHOOK_URL", payload["deliveries"][0]["error"])
            self.assertFalse(window_state_path.exists())
            self.assertFalse(notification_log_path.exists())

    def test_webhook_duplicate_window_protection_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            db_path = root / "state" / "jobs.db"
            schedule_path = root / "config" / "operator_schedules.yaml"
            window_state_path = root / "state" / "windows.json"
            notification_log_path = root / "state" / "notifications.jsonl"
            self._seed_job(db_path=db_path, job_id="job-webhook-duplicate")
            self._write_schedule(
                schedule_path=schedule_path,
                times=("09:00",),
                delivery_method="webhook_operator_summary",
            )
            call_count = 0

            def _fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
                nonlocal call_count
                call_count += 1
                return self._MockHttpResponse(status=200)

            with patch("orchestrator.operator_summary_delivery.urlopen", side_effect=_fake_urlopen):
                with patch.dict(os.environ, {"OPERATOR_SUMMARY_WEBHOOK_URL": "http://example.test/hook"}, clear=False):
                    first_payload = run_scheduled_operator_summary_delivery(
                        now_utc=self._parse_iso("2026-04-13T09:00:00+00:00"),
                        db_path=str(db_path),
                        schedule_path=str(schedule_path),
                        window_state_path=str(window_state_path),
                        notification_log_path=str(notification_log_path),
                    )
                    duplicate_payload = run_scheduled_operator_summary_delivery(
                        now_utc=self._parse_iso("2026-04-13T09:00:00+00:00"),
                        db_path=str(db_path),
                        schedule_path=str(schedule_path),
                        window_state_path=str(window_state_path),
                        notification_log_path=str(notification_log_path),
                    )

            self.assertEqual(first_payload["delivery_count"], 1)
            self.assertEqual(duplicate_payload["delivery_count"], 0)
            self.assertEqual(duplicate_payload["deliveries"][0]["reason"], "already_sent_in_window")
            self.assertEqual(call_count, 1)


if __name__ == "__main__":
    unittest.main()
