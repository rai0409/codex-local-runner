from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from automation.orchestration.planned_runner.daemon_queue import ensure_queue_dirs, list_tasks
from automation.orchestration.planned_runner.daemon_state import (
    read_daemon_state,
    recover_interrupted_tasks,
    write_daemon_state,
)


def _put_running_task(queue_dir: Path, task_id: str, recovery_attempts: int = 0) -> Path:
    paths = ensure_queue_dirs(queue_dir)
    spec = {"task_id": task_id, "kind": "add_function"}
    if recovery_attempts:
        spec["_recovery_attempts"] = recovery_attempts
    path = Path(paths["running"]) / f"{task_id}.json"
    path.write_text(json.dumps(spec), encoding="utf-8")
    return path


class DaemonStateTests(unittest.TestCase):
    def test_state_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_path = Path(tmp_dir) / "daemon_state.json"
            write_daemon_state(state_path, {"status": "running", "pid": 42})
            state = read_daemon_state(state_path)
        self.assertEqual(state["status"], "running")
        self.assertEqual(state["pid"], 42)
        self.assertIn("updated_at", state)

    def test_interrupted_task_is_requeued_with_attempt_count(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            queue_dir = Path(tmp_dir)
            _put_running_task(queue_dir, "interrupted-task")
            result = recover_interrupted_tasks(queue_dir)
            tasks = list_tasks(queue_dir)
            requeued_spec = json.loads(
                (queue_dir / "pending" / "interrupted-task.json").read_text(encoding="utf-8")
            )
        self.assertEqual(result["recovered_count"], 1)
        self.assertEqual(tasks["pending"], ["interrupted-task.json"])
        self.assertEqual(tasks["running"], [])
        self.assertEqual(requeued_spec["_recovery_attempts"], 1)
        self.assertIn("_last_interruption_at", requeued_spec)

    def test_recovery_exhaustion_moves_to_failed(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            queue_dir = Path(tmp_dir)
            _put_running_task(queue_dir, "doomed-task", recovery_attempts=1)
            result = recover_interrupted_tasks(queue_dir, max_recovery_attempts=1)
            tasks = list_tasks(queue_dir)
            failed_spec = json.loads(
                (queue_dir / "failed" / "doomed-task.json").read_text(encoding="utf-8")
            )
        self.assertEqual(result["exhausted_count"], 1)
        self.assertEqual(tasks["failed"], ["doomed-task.json"])
        self.assertEqual(tasks["pending"], [])
        self.assertTrue(failed_spec["_recovery_exhausted"])

    def test_recovery_noop_on_empty_queue(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = recover_interrupted_tasks(tmp_dir)
        self.assertEqual(result["recovered_count"], 0)
        self.assertEqual(result["exhausted_count"], 0)


if __name__ == "__main__":
    unittest.main()
