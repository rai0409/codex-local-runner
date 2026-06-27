from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from automation.orchestration.planned_runner.long_running_daemon_acceptance import (
    build_synthetic_prompt664_ticks,
    run_long_running_daemon_acceptance,
)


class LongRunningDaemonAcceptanceTests(unittest.TestCase):
    def _run(self, tmp: Path, ticks=None, **kwargs):
        return run_long_running_daemon_acceptance(
            repo_root=tmp,
            out_dir=tmp / "long_daemon",
            run_id=kwargs.pop("run_id", "prompt664-test-run"),
            ticks=ticks,
            **kwargs,
        )

    def test_long_running_daemon_starts_with_run_id_and_three_ticks(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            result = self._run(Path(raw))
            state = json.loads(Path(result["state_path"]).read_text(encoding="utf-8"))
            queue = json.loads(Path(result["queue_path"]).read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "success", msg=result["errors"])
        self.assertEqual(result["run_id"], "prompt664-test-run")
        self.assertEqual(result["tick_count"], 3)
        self.assertEqual(result["stop_reason"], "max_ticks_reached")
        self.assertEqual(state["status"], "success")
        self.assertEqual([tick["status"] for tick in queue["ticks"]], ["done", "done", "done"])

    def test_lock_acquisition_and_release(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            result = self._run(Path(raw))
            lock_path = Path(result["lock_path"])
        self.assertTrue(result["lock_acquired"])
        self.assertFalse(lock_path.exists())

    def test_duplicate_lock_rejection(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            tmp = Path(raw)
            out = tmp / "long_daemon"
            out.mkdir()
            proc = subprocess.Popen(["sleep", "5"])
            try:
                (out / "long_running_daemon.lock").write_text(
                    json.dumps({"pid": proc.pid}), encoding="utf-8"
                )
                result = self._run(tmp)
            finally:
                proc.terminate()
                proc.wait()
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["stop_reason"], "duplicate_active_lock")
        self.assertFalse(result["internal_codex_executor_used"])

    def test_durable_state_and_queue_persist_across_ticks(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            result = self._run(Path(raw))
            state = json.loads(Path(result["state_path"]).read_text(encoding="utf-8"))
            queue = json.loads(Path(result["queue_path"]).read_text(encoding="utf-8"))
        self.assertTrue(result["durable_state_persisted"])
        self.assertTrue(result["durable_queue_persisted"])
        self.assertEqual(len(state["completed_ticks"]), 3)
        self.assertEqual(len(queue["ticks"]), 3)

    def test_per_tick_evidence_creation(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            result = self._run(Path(raw))
            for path in result["artifact_paths"]:
                self.assertTrue(Path(path).is_file())
        self.assertTrue(result["per_tick_evidence_captured"])

    def test_resume_from_interrupted_state(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            tmp = Path(raw)
            interrupted = self._run(tmp, interrupt_after_tick=1)
            resumed = self._run(tmp)
        self.assertEqual(interrupted["status"], "partial")
        self.assertEqual(interrupted["stop_reason"], "interrupted_after_tick")
        self.assertEqual(resumed["status"], "success", msg=resumed["errors"])
        self.assertTrue(resumed["resume_after_interruption_verified"])
        self.assertEqual(resumed["tick_count"], 3)

    def test_operator_stop_file_handling(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            result = self._run(Path(raw), operator_stop_after_tick=1)
        self.assertEqual(result["status"], "success", msg=result["errors"])
        self.assertEqual(result["stop_reason"], "operator_stop_requested")
        self.assertTrue(result["operator_stop_verified"])
        self.assertEqual(result["tick_count"], 1)

    def test_max_ticks_stop(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            tmp = Path(raw)
            ticks = build_synthetic_prompt664_ticks(tmp / "long_daemon", count=5)
            result = self._run(tmp, ticks=ticks, max_ticks=3)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["tick_count"], 3)
        self.assertTrue(result["max_ticks_or_cycles_enforced"])

    def test_failure_threshold_stop(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            result = self._run(Path(raw), fail_on_tick=1, failure_threshold=1)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["stop_reason"], "failure_threshold_reached")
        self.assertTrue(result["failure_threshold_stop_verified"])

    def test_terminal_state_and_stop_reason_recorded(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            result = self._run(Path(raw))
            state = json.loads(Path(result["state_path"]).read_text(encoding="utf-8"))
        self.assertTrue(result["terminal_state_recorded"])
        self.assertTrue(result["stop_reason_recorded"])
        self.assertTrue(state["terminal"])
        self.assertEqual(state["stop_reason"], "max_ticks_reached")

    def test_unsafe_path_rejection(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            result = run_long_running_daemon_acceptance(
                repo_root=raw,
                out_dir=Path(raw) / "cookies" / "long_daemon",
                run_id="unsafe-path",
            )
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["stop_reason"], "unsafe_artifact_path")
        self.assertTrue(result["unsafe_paths_rejected"])

    def test_remote_destructive_and_secret_text_prohibitions(self):
        samples = [
            ("remote", "git push origin main\n"),
            ("destructive", "rm -rf /tmp/example\n"),
            ("credential", "read credential material\n"),
            ("cookie", "read cookie jar\n"),
            ("browser_profile", "read browser profile\n"),
            ("env", "read .env values\n"),
            ("private_session", "read private session files\n"),
        ]
        for name, text in samples:
            with self.subTest(name=name), tempfile.TemporaryDirectory(dir="/tmp") as raw:
                tmp = Path(raw)
                ticks = build_synthetic_prompt664_ticks(tmp / "long_daemon", count=3)
                Path(ticks[0]["prompt_path"]).write_text(text, encoding="utf-8")
                result = self._run(tmp, ticks=ticks)
            self.assertEqual(result["status"], "blocked")
            self.assertFalse(result["internal_codex_executor_used"])
            self.assertEqual(result["stop_reason"], "safety_gate_failed")


if __name__ == "__main__":
    unittest.main()
