from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from automation.orchestration.planned_runner.daemon_queue import (
    claim_next_task,
    complete_task,
    ensure_queue_dirs,
    enqueue_task,
    list_tasks,
)


class DaemonQueueTests(unittest.TestCase):
    def test_queue_lifecycle_pending_running_done(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            ensure_queue_dirs(tmp_dir)
            enqueue_task(tmp_dir, {"task_id": "a-task", "kind": "add_function"})
            enqueue_task(tmp_dir, {"task_id": "b-task", "kind": "add_function"})
            self.assertEqual(list_tasks(tmp_dir)["pending"], ["a-task.json", "b-task.json"])

            claimed = claim_next_task(tmp_dir)
            self.assertEqual(claimed.name, "a-task.json")
            self.assertIn("running", claimed.as_posix())
            self.assertEqual(list_tasks(tmp_dir)["pending"], ["b-task.json"])
            self.assertEqual(list_tasks(tmp_dir)["running"], ["a-task.json"])

            done_path = complete_task(tmp_dir, claimed, success=True)
            self.assertIn("done", done_path.as_posix())
            self.assertEqual(list_tasks(tmp_dir)["done"], ["a-task.json"])
            self.assertEqual(list_tasks(tmp_dir)["running"], [])

    def test_failed_tasks_go_to_failed(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            enqueue_task(tmp_dir, {"task_id": "bad-task"})
            claimed = claim_next_task(tmp_dir)
            complete_task(tmp_dir, claimed, success=False)
            self.assertEqual(list_tasks(tmp_dir)["failed"], ["bad-task.json"])

    def test_claim_returns_none_when_empty(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            self.assertIsNone(claim_next_task(tmp_dir))

    def test_enqueue_requires_task_id(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            with self.assertRaises(ValueError):
                enqueue_task(tmp_dir, {"kind": "add_function"})


if __name__ == "__main__":
    unittest.main()
