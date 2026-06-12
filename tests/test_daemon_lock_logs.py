from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
import tempfile
import unittest

from automation.orchestration.planned_runner.daemon_lock import (
    acquire_lock,
    is_pid_alive,
    release_lock,
)
from automation.orchestration.planned_runner.daemon_logs import append_log, read_log_events


def _dead_pid() -> int:
    proc = subprocess.Popen(["sleep", "0"])
    proc.wait()
    return proc.pid


class DaemonLockTests(unittest.TestCase):
    def test_acquire_and_release(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            lock_path = Path(tmp_dir) / "daemon.lock"
            result = acquire_lock(lock_path)
            self.assertTrue(result["acquired"])
            self.assertTrue(lock_path.exists())
            self.assertTrue(release_lock(lock_path))
            self.assertFalse(lock_path.exists())

    def test_second_acquire_by_live_pid_refused(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            lock_path = Path(tmp_dir) / "daemon.lock"
            acquire_lock(lock_path, pid=os.getpid())
            other = acquire_lock(lock_path, pid=os.getpid() + 1) if False else None
            # simulate a different process trying while our (live) pid holds it
            contender = acquire_lock(lock_path, pid=999999991)
            self.assertFalse(contender["acquired"])
            self.assertEqual(contender["reason"], "lock_held_by_running_process")
            self.assertEqual(contender["existing_pid"], os.getpid())

    def test_stale_lock_from_dead_pid_is_recovered(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            lock_path = Path(tmp_dir) / "daemon.lock"
            dead = _dead_pid()
            self.assertFalse(is_pid_alive(dead))
            lock_path.write_text(json.dumps({"pid": dead}), encoding="utf-8")
            result = acquire_lock(lock_path)
            self.assertTrue(result["acquired"])
            self.assertTrue(result["stale_recovered"])

    def test_release_refuses_foreign_lock(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            lock_path = Path(tmp_dir) / "daemon.lock"
            lock_path.write_text(json.dumps({"pid": os.getpid() + 12345}), encoding="utf-8")
            self.assertFalse(release_lock(lock_path))
            self.assertTrue(lock_path.exists())


class DaemonLogsTests(unittest.TestCase):
    def test_append_and_read_events(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = Path(tmp_dir) / "daemon_log.jsonl"
            append_log(log_path, "daemon_started", {"pid": 1})
            append_log(log_path, "task_finished", {"task": "x.json", "status": "success"})
            events = read_log_events(log_path)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["event"], "daemon_started")
        self.assertEqual(events[1]["task"], "x.json")
        self.assertIn("ts", events[0])


if __name__ == "__main__":
    unittest.main()
