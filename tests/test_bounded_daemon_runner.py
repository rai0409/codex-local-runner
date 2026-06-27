from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from automation.orchestration.planned_runner.bounded_daemon_runner import (
    build_synthetic_prompt663_cycles,
    run_bounded_daemon_hardening,
)


class BoundedDaemonRunnerTests(unittest.TestCase):
    def _run(self, tmp: Path, cycles=None, **kwargs):
        out = tmp / "daemon"
        return run_bounded_daemon_hardening(
            repo_root=tmp,
            out_dir=out,
            run_id=kwargs.pop("run_id", "prompt663-test-run"),
            cycles=cycles,
            **kwargs,
        )

    def test_successful_bounded_two_cycle_daemon_proof(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            result = self._run(Path(raw))
            state = json.loads(Path(result["state_path"]).read_text(encoding="utf-8"))
            queue = json.loads(Path(result["queue_path"]).read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "success", msg=result["errors"])
        self.assertTrue(result["bounded_runner_daemon_wrapped"])
        self.assertTrue(result["internal_codex_executor_used"])
        self.assertEqual(result["cycle_count"], 2)
        self.assertEqual(result["stop_reason"], "max_cycles_reached")
        self.assertEqual(state["status"], "success")
        self.assertEqual([c["status"] for c in queue["cycles"]], ["done", "done"])
        self.assertTrue(result["local_only_evidence_captured"])

    def test_lock_acquisition_and_release(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            result = self._run(Path(raw))
            lock_path = Path(result["lock_path"])
        self.assertEqual(result["status"], "success")
        self.assertFalse(lock_path.exists())
        self.assertTrue(result["lock_file_supported"])

    def test_duplicate_active_lock_rejection(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            tmp = Path(raw)
            out = tmp / "daemon"
            out.mkdir()
            proc = subprocess.Popen(["sleep", "5"])
            try:
                (out / "daemon.lock").write_text(json.dumps({"pid": proc.pid}), encoding="utf-8")
                result = self._run(tmp)
            finally:
                proc.terminate()
                proc.wait()
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["stop_reason"], "duplicate_active_lock")
        self.assertFalse(result["internal_codex_executor_used"])

    def test_stale_lock_handling(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            tmp = Path(raw)
            out = tmp / "daemon"
            out.mkdir()
            (out / "daemon.lock").write_text(json.dumps({"pid": 999999991}), encoding="utf-8")
            result = self._run(tmp)
        self.assertEqual(result["status"], "success")
        self.assertTrue(result["stale_lock_recovered"])

    def test_durable_state_creation_and_terminal_state(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            result = self._run(Path(raw))
            state_path = Path(result["state_path"])
            summary_path = Path(result["summary_path"])
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertTrue(result["durable_state_supported"])
            self.assertTrue(summary_path.is_file())
            self.assertTrue(state["terminal"])
            self.assertEqual(state["stop_reason"], "max_cycles_reached")

    def test_resume_from_interrupted_state(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            tmp = Path(raw)
            interrupted = self._run(tmp, interrupt_after_cycle=1)
            resumed = self._run(tmp)
        self.assertEqual(interrupted["status"], "partial")
        self.assertEqual(interrupted["stop_reason"], "interrupted_after_cycle")
        self.assertEqual(resumed["status"], "success", msg=resumed["errors"])
        self.assertTrue(resumed["resume_after_interruption_verified"])
        self.assertEqual(resumed["cycle_count"], 2)

    def test_max_cycles_stop(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            tmp = Path(raw)
            out = tmp / "daemon"
            cycles = build_synthetic_prompt663_cycles(out)
            third = out / "third.md"
            third.parent.mkdir(parents=True, exist_ok=True)
            third.write_text("third local proof\n", encoding="utf-8")
            cycles.append(
                {
                    "prompt_id": "prompt663_daemon_cycle_3_local_proof",
                    "prompt_path": third.as_posix(),
                    "approved_for_execution": True,
                    "evidence_path": "artifacts/autonomous_runtime/prompt663_daemon/cycle_3.json",
                }
            )
            result = self._run(tmp, cycles=cycles, max_cycles=2)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["cycle_count"], 2)
        self.assertTrue(result["max_cycles_enforced"])

    def test_failure_threshold_stop(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            result = self._run(Path(raw), fail_on_cycle=1, failure_threshold=1)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["stop_reason"], "failure_threshold_reached")
        self.assertTrue(result["failure_threshold_stop_verified"])

    def test_duplicate_prompt_fingerprint_stop(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            tmp = Path(raw)
            cycles = build_synthetic_prompt663_cycles(tmp / "daemon")
            cycles[1]["prompt_path"] = cycles[0]["prompt_path"]
            result = self._run(tmp, cycles=cycles)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["stop_reason"], "duplicate_prompt_fingerprint")
        self.assertEqual(result["cycle_count"], 1)

    def test_approval_gate_persistence_and_missing_approval_blocks(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            tmp = Path(raw)
            cycles = build_synthetic_prompt663_cycles(tmp / "daemon")
            cycles[0]["approved_for_execution"] = False
            result = self._run(tmp, cycles=cycles)
            state = json.loads(Path(result["state_path"]).read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["stop_reason"], "approval_missing")
        self.assertFalse(result["internal_codex_executor_used"])
        self.assertFalse(state["approval_gate_persisted"])

    def test_unsafe_path_rejection(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            result = run_bounded_daemon_hardening(
                repo_root=raw,
                out_dir=Path(raw) / ".env" / "daemon",
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
                cycles = build_synthetic_prompt663_cycles(tmp / "daemon")
                Path(cycles[0]["prompt_path"]).write_text(text, encoding="utf-8")
                result = self._run(tmp, cycles=cycles)
            self.assertEqual(result["status"], "blocked")
            self.assertFalse(result["internal_codex_executor_used"])
            self.assertEqual(result["stop_reason"], "safety_gate_failed")

    def test_evidence_summary_creation(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            result = self._run(Path(raw))
            summary = Path(result["summary_path"]).read_text(encoding="utf-8")
        self.assertIn("Prompt663 Bounded Daemon Status", summary)
        self.assertIn("max_cycles_reached", summary)
        self.assertTrue(result["local_only_evidence_captured"])


if __name__ == "__main__":
    unittest.main()
