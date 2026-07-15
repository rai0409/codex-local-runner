"""Prompt649: tests for the bounded offline project loop controller."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from automation.orchestration.planned_runner.project_loop_controller import (
    MAX_PROJECT_LOOP_CYCLES,
    NEXT_FINISH,
    NEXT_FIX,
    NEXT_WAIT,
    run_project_loop,
)


def _intent(max_tasks: int = 3) -> dict:
    return {
        "project_id": "proj-alpha",
        "project_name": "Alpha",
        "goal": "Add helpers",
        "repo_target": "/tmp/r",
        "allowed_task_kinds": ["add_function"],
        "safety_limits": {"max_tasks": max_tasks},
    }


def _descs() -> list[dict]:
    return [
        {"target_file": "pkg/a.py", "function_name": "fa", "expression": "a + b"},
        {"target_file": "pkg/b.py", "function_name": "fb", "expression": "a + b", "depends_on": [0]},
    ]


_DONE = {"proj-alpha-t000": "done", "proj-alpha-t001": "done"}
_FAIL = {"proj-alpha-t000": "done", "proj-alpha-t001": "failed"}


class ProjectLoopControllerTests(unittest.TestCase):
    def test_no_results_generates_populates_in_progress(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            q = Path(raw) / "queue"
            s = run_project_loop(_intent(), _descs(), q.as_posix())
            self.assertEqual(s["status"], "in_progress")
            self.assertEqual(s["next_step"], NEXT_WAIT)
            self.assertEqual(s["plan_task_count"], 2)
            self.assertEqual(len(s["written_files"]), 2)
            self.assertTrue((q / "pending").is_dir())
            self.assertEqual(s["cycles_run"], 1)

    def test_all_done_snapshot_completes(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            s = run_project_loop(_intent(), _descs(), (Path(raw) / "q").as_posix(), result_snapshots=[_DONE])
            self.assertEqual(s["status"], "complete")
            self.assertEqual(s["next_step"], NEXT_FINISH)
            self.assertTrue(s["final_completion"]["complete"])

    def test_failed_snapshot_routes_to_fix(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            s = run_project_loop(_intent(), _descs(), (Path(raw) / "q").as_posix(), result_snapshots=[_FAIL])
            self.assertEqual(s["status"], "failed")
            self.assertEqual(s["next_step"], NEXT_FIX)

    def test_iterates_until_done_across_snapshots(self):
        # round 0: only t000 done -> in_progress; round 1: both done -> complete
        snaps = [{"proj-alpha-t000": "done"}, _DONE]
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            s = run_project_loop(_intent(), _descs(), (Path(raw) / "q").as_posix(), result_snapshots=snaps, max_cycles=3)
            self.assertEqual(s["status"], "complete")
            self.assertEqual(s["cycles_run"], 2)
            self.assertEqual(s["next_step"], NEXT_FINISH)

    def test_bounded_by_max_cycles(self):
        snaps = [{}, {}, {}, {}, {}]  # always in_progress
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            s = run_project_loop(_intent(), _descs(), (Path(raw) / "q").as_posix(), result_snapshots=snaps, max_cycles=2)
            self.assertEqual(s["status"], "in_progress")
            self.assertEqual(s["cycles_run"], 2)  # capped at max_cycles

    def test_max_cycles_hard_cap(self):
        snaps = [{} for _ in range(MAX_PROJECT_LOOP_CYCLES + 5)]
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            s = run_project_loop(_intent(), _descs(), (Path(raw) / "q").as_posix(), result_snapshots=snaps, max_cycles=999)
            self.assertLessEqual(s["cycles_run"], MAX_PROJECT_LOOP_CYCLES)

    def test_invalid_intent_blocked_no_queue(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            q = Path(raw) / "queue"
            s = run_project_loop({"project_id": "BAD"}, _descs(), q.as_posix())
            self.assertEqual(s["status"], "blocked")
            self.assertTrue(s["errors"])
            self.assertEqual(s["written_files"], [])

    def test_missing_output_dir_blocked(self):
        s = run_project_loop(_intent(), _descs(), None)
        self.assertEqual(s["status"], "blocked")
        self.assertTrue(s["errors"])

    def test_deterministic(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as r1, tempfile.TemporaryDirectory(dir="/tmp") as r2:
            a = run_project_loop(_intent(), _descs(), (Path(r1) / "q").as_posix(), result_snapshots=[_DONE])
            b = run_project_loop(_intent(), _descs(), (Path(r2) / "q").as_posix(), result_snapshots=[_DONE])
            # compare everything except the tmp-specific paths
            for key in ("status", "next_step", "cycles_run", "plan_task_count", "per_cycle", "final_completion"):
                self.assertEqual(a[key], b[key])

    def test_no_side_effects_outside_explicit_dir(self):
        before = set(Path(".").iterdir())
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            run_project_loop(_intent(), _descs(), (Path(raw) / "q").as_posix(), result_snapshots=[_DONE])
        self.assertEqual(before, set(Path(".").iterdir()))


if __name__ == "__main__":
    unittest.main()
