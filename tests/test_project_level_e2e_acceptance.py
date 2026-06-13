"""Prompt651: deterministic offline project-level E2E acceptance.

Proves the full offline chain end to end (no live Codex / daemon):

  ProjectIntent + descriptors
    -> generate_project_task_plan
    -> populate_queue_from_plan (explicit /tmp queue dir)
    -> [simulated task results]
    -> evaluate_project_completion
    -> run_project_loop final status

and confirms the materialized queue files are daemon-consumable
(task_spec.validate_task_spec accepts them with a real repo_path).
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from automation.orchestration.planned_runner.project_completion_gate import (
    evaluate_project_completion,
)
from automation.orchestration.planned_runner.project_loop_controller import (
    NEXT_FINISH,
    NEXT_FIX,
    NEXT_WAIT,
    run_project_loop,
)
from automation.orchestration.planned_runner.project_queue_population import (
    populate_queue_from_plan,
)
from automation.orchestration.planned_runner.project_task_generator import (
    generate_project_task_plan,
)
from automation.orchestration.planned_runner.task_spec import validate_task_spec


def _intent() -> dict:
    return {
        "project_id": "proj-e2e",
        "project_name": "E2E project",
        "goal": "Add two helper functions with an ordering dependency",
        "repo_target": "/tmp/e2e_repo",
        "allowed_task_kinds": ["add_function"],
        "safety_limits": {"max_tasks": 3, "max_cycles_per_task": 1, "max_total_seconds": 600},
    }


def _descriptors() -> list[dict]:
    return [
        {"target_file": "pkg/a.py", "function_name": "fa", "expression": "a + b"},
        {"target_file": "pkg/b.py", "function_name": "fb", "expression": "a + b", "depends_on": [0]},
    ]


class ProjectLevelE2EAcceptanceTests(unittest.TestCase):
    def test_full_offline_chain_step_by_step(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = Path(raw) / "repo"
            repo.mkdir()
            queue = Path(raw) / "queue"

            # 1. intent + descriptors -> plan
            gen = generate_project_task_plan(_intent(), _descriptors(), generated_at="2026-06-14T00:00:00Z")
            self.assertEqual(gen["status"], "success", msg=gen["errors"])
            plan = gen["plan"]
            self.assertEqual(len(plan["tasks"]), 2)

            # 2. plan -> queue files (explicit dir), daemon-consumable
            pop = populate_queue_from_plan(plan, queue.as_posix(), repo_path_override=repo.as_posix())
            self.assertEqual(pop["status"], "success", msg=pop["errors"])
            self.assertEqual(pop["task_count"], 2)
            pending = sorted((queue / "pending").glob("*.json"))
            self.assertEqual(len(pending), 2)
            # topological order: fa (dependency) before fb
            specs = [json.loads(p.read_text()) for p in pending]
            self.assertEqual([s["function_name"] for s in specs], ["fa", "fb"])
            for spec in specs:
                _, errors = validate_task_spec(spec)
                self.assertEqual(errors, [], msg=f"daemon would reject spec: {errors}")

            # 3. simulated results -> completion gate transitions
            ids = [t["task_id"] for t in plan["tasks"]]
            self.assertEqual(evaluate_project_completion(plan, {})["status"], "in_progress")
            self.assertEqual(
                evaluate_project_completion(plan, {ids[0]: "done"})["status"], "in_progress"
            )
            done_all = {ids[0]: "done", ids[1]: "done"}
            final = evaluate_project_completion(plan, done_all)
            self.assertEqual(final["status"], "complete")
            self.assertTrue(final["complete"])

    def test_controller_e2e_in_progress_then_complete(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            queue = Path(raw) / "queue"
            # no results -> queue materialized, awaiting execution
            s0 = run_project_loop(_intent(), _descriptors(), queue.as_posix())
            self.assertEqual(s0["status"], "in_progress")
            self.assertEqual(s0["next_step"], NEXT_WAIT)
            self.assertEqual(len(s0["written_files"]), 2)

            # successive simulated rounds -> complete
            snaps = [{"proj-e2e-t000": "done"}, {"proj-e2e-t000": "done", "proj-e2e-t001": "done"}]
            with tempfile.TemporaryDirectory(dir="/tmp") as raw2:
                s = run_project_loop(_intent(), _descriptors(), (Path(raw2) / "q").as_posix(),
                                     result_snapshots=snaps, max_cycles=3)
            self.assertEqual(s["status"], "complete")
            self.assertEqual(s["next_step"], NEXT_FINISH)
            self.assertEqual(s["cycles_run"], 2)

    def test_controller_e2e_failure_routes_to_fix(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            s = run_project_loop(
                _intent(), _descriptors(), (Path(raw) / "q").as_posix(),
                result_snapshots=[{"proj-e2e-t000": "done", "proj-e2e-t001": "failed"}],
            )
            self.assertEqual(s["status"], "failed")
            self.assertEqual(s["next_step"], NEXT_FIX)

    def test_full_chain_deterministic(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as r1, tempfile.TemporaryDirectory(dir="/tmp") as r2:
            done = {"proj-e2e-t000": "done", "proj-e2e-t001": "done"}
            a = run_project_loop(_intent(), _descriptors(), (Path(r1) / "q").as_posix(), result_snapshots=[done])
            b = run_project_loop(_intent(), _descriptors(), (Path(r2) / "q").as_posix(), result_snapshots=[done])
            for key in ("status", "next_step", "cycles_run", "plan_task_count", "per_cycle", "final_completion"):
                self.assertEqual(a[key], b[key])

    def test_no_side_effects_outside_tmp(self):
        before = set(Path(".").iterdir())
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            run_project_loop(_intent(), _descriptors(), (Path(raw) / "q").as_posix(),
                             result_snapshots=[{"proj-e2e-t000": "done", "proj-e2e-t001": "done"}])
        self.assertEqual(before, set(Path(".").iterdir()))


if __name__ == "__main__":
    unittest.main()
