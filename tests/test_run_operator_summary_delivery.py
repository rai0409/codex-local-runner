from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from orchestrator.ledger import record_job_evaluation


class RunOperatorSummaryDeliveryCliTests(unittest.TestCase):
    def _repo_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def _script_path(self) -> Path:
        return self._repo_root() / "scripts" / "run_operator_summary_delivery.py"

    def _run(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self._script_path()), *args],
            capture_output=True,
            text=True,
            cwd=self._repo_root(),
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
                "      method: placeholder_operator_summary\n"
                "    decision:\n"
                "      mode: human_review_required\n"
            ),
            encoding="utf-8",
        )

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


if __name__ == "__main__":
    unittest.main()
