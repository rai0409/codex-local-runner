from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from automation.orchestration.planned_runner.bounded_unattended_acceptance import (
    build_preapproved_prompt665_queue,
    run_bounded_unattended_acceptance,
)


class BoundedUnattendedAcceptanceTests(unittest.TestCase):
    def _run(self, tmp: Path, queue=None, **kwargs):
        return run_bounded_unattended_acceptance(
            repo_root=tmp,
            out_dir=tmp / "unattended",
            run_id=kwargs.pop("run_id", "prompt665-test-run"),
            queue=queue,
            **kwargs,
        )

    def test_unattended_run_starts_with_run_id_and_three_items(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            result = self._run(Path(raw))
        self.assertEqual(result["status"], "success", msg=result["errors"])
        self.assertEqual(result["run_id"], "prompt665-test-run")
        self.assertEqual(result["queue_item_count"], 3)
        self.assertEqual(result["tick_count"], 3)
        self.assertTrue(result["no_human_intervention_during_run_verified"])

    def test_preapproved_local_safe_queue_is_required(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            tmp = Path(raw)
            result = self._run(tmp, queue=[])
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["stop_reason"], "missing_preapproval")
        self.assertTrue(result["preapproved_queue_required"])

    def test_missing_approval_blocks_unattended_execution(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            tmp = Path(raw)
            queue = build_preapproved_prompt665_queue(tmp / "unattended")
            queue[0]["approved_for_execution"] = False
            result = self._run(tmp, queue=queue)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["stop_reason"], "missing_preapproval")
        self.assertTrue(result["missing_approval_blocks_execution"])
        self.assertFalse(result["internal_codex_executor_used"])

    def test_approval_gate_persistence_is_auditable(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            result = self._run(Path(raw))
            approval = json.loads(Path(result["approval_gate_state_path"]).read_text(encoding="utf-8"))
        self.assertTrue(result["approval_gate_persistence_verified"])
        self.assertEqual(len(approval["items"]), 3)
        self.assertEqual(approval["approval_errors"], [])

    def test_lock_acquisition_and_duplicate_lock_rejection(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            tmp = Path(raw)
            ok = self._run(tmp)
            lock_path = Path(tmp) / "unattended" / "long_running_daemon" / "long_running_daemon.lock"
            proc = subprocess.Popen(["sleep", "5"])
            try:
                lock_path.parent.mkdir(parents=True, exist_ok=True)
                lock_path.write_text(json.dumps({"pid": proc.pid}), encoding="utf-8")
                blocked = self._run(tmp, run_id="prompt665-lock-blocked")
            finally:
                proc.terminate()
                proc.wait()
        self.assertTrue(ok["lock_acquired"])
        self.assertEqual(blocked["status"], "blocked")
        self.assertEqual(blocked["stop_reason"], "duplicate_active_lock")
        self.assertTrue(blocked["duplicate_lock_rejected"])

    def test_durable_state_queue_and_evidence(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            result = self._run(Path(raw))
            state = json.loads(Path(result["state_path"]).read_text(encoding="utf-8"))
            queue = json.loads(Path(result["queue_path"]).read_text(encoding="utf-8"))
            self.assertTrue(result["durable_state_persisted"])
            self.assertTrue(result["durable_queue_persisted"])
            self.assertTrue(result["per_item_or_tick_evidence_captured"])
            self.assertTrue(state["terminal"])
            self.assertEqual(len(queue["items"]), 3)
            for path in result["artifact_paths"]:
                self.assertTrue(Path(path).is_file())

    def test_internal_executor_invoked_through_approved_gate(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            result = self._run(Path(raw))
        self.assertTrue(result["internal_codex_executor_used"])
        self.assertTrue(result["internal_executor_safety_gate_verified"])

    def test_operator_stop_file_handling(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            result = self._run(Path(raw), operator_stop_after_item=1)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["stop_reason"], "operator_stop_requested")
        self.assertTrue(result["operator_stop_verified"])
        self.assertEqual(result["queue_item_count"], 1)

    def test_max_items_stop(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            tmp = Path(raw)
            queue = build_preapproved_prompt665_queue(tmp / "unattended", count=5)
            result = self._run(tmp, queue=queue, max_items=3)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["queue_item_count"], 3)
        self.assertTrue(result["max_items_or_ticks_or_cycles_enforced"])

    def test_failure_threshold_stop(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            result = self._run(Path(raw), fail_on_item=1, failure_threshold=1)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["stop_reason"], "failure_threshold_reached")
        self.assertTrue(result["failure_threshold_stop_verified"])

    def test_terminal_state_stop_reason_and_summary(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            result = self._run(Path(raw))
            summary = Path(result["summary_path"]).read_text(encoding="utf-8")
        self.assertTrue(result["terminal_state_recorded"])
        self.assertTrue(result["stop_reason_recorded"])
        self.assertTrue(result["final_evidence_summary_written"])
        self.assertIn("Prompt665 Bounded Unattended Acceptance", summary)

    def test_unsafe_path_rejection(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            result = run_bounded_unattended_acceptance(
                repo_root=raw,
                out_dir=Path(raw) / "private_sessions" / "unattended",
                run_id="unsafe-path",
            )
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["stop_reason"], "unsafe_artifact_path")
        self.assertTrue(result["unsafe_paths_rejected"])

    def test_unsafe_queue_item_rejection_and_prohibitions(self):
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
                queue = build_preapproved_prompt665_queue(tmp / "unattended")
                Path(queue[0]["prompt_path"]).write_text(text, encoding="utf-8")
                result = self._run(tmp, queue=queue)
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["stop_reason"], "safety_gate_failed")
            self.assertFalse(result["internal_codex_executor_used"])


if __name__ == "__main__":
    unittest.main()
