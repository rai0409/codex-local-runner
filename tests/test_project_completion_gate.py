"""Prompt648: tests for the offline project completion gate."""
from __future__ import annotations

import unittest

from automation.orchestration.planned_runner.project_completion_gate import (
    evaluate_project_completion,
)
from automation.orchestration.planned_runner.project_task_generator import (
    generate_project_task_plan,
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


def _plan() -> dict:
    descs = [
        {"target_file": "pkg/a.py", "function_name": "fa", "expression": "a + b"},
        {"target_file": "pkg/b.py", "function_name": "fb", "expression": "a + b", "depends_on": [0]},
    ]
    r = generate_project_task_plan(_intent(), descs)
    assert r["status"] == "success", r["errors"]
    return r["plan"]


class ProjectCompletionGateTests(unittest.TestCase):
    def test_all_done_is_complete(self):
        v = evaluate_project_completion(_plan(), {"proj-alpha-t000": "done", "proj-alpha-t001": "done"})
        self.assertEqual(v["status"], "complete")
        self.assertTrue(v["complete"])
        self.assertEqual(v["counts"]["done"], 2)

    def test_failed_required_is_failed_not_complete(self):
        v = evaluate_project_completion(_plan(), {"proj-alpha-t000": "done", "proj-alpha-t001": "failed"})
        self.assertEqual(v["status"], "failed")
        self.assertFalse(v["complete"])

    def test_blocked_required_is_blocked_not_complete(self):
        v = evaluate_project_completion(_plan(), {"proj-alpha-t000": "done", "proj-alpha-t001": "blocked"})
        self.assertEqual(v["status"], "blocked")
        self.assertFalse(v["complete"])

    def test_pending_is_in_progress(self):
        v = evaluate_project_completion(_plan(), {"proj-alpha-t000": "done"})  # t001 falls back to planned
        self.assertEqual(v["status"], "in_progress")
        self.assertFalse(v["complete"])
        self.assertEqual(v["counts"]["pending"], 1)

    def test_unknown_status_is_in_progress_not_complete(self):
        v = evaluate_project_completion(_plan(), {"proj-alpha-t000": "done", "proj-alpha-t001": "weird"})
        self.assertEqual(v["status"], "in_progress")
        self.assertFalse(v["complete"])
        self.assertEqual(v["counts"]["unknown"], 1)

    def test_failed_non_required_does_not_fail_project(self):
        v = evaluate_project_completion(
            _plan(),
            {"proj-alpha-t000": "done", "proj-alpha-t001": "failed"},
            required_task_ids=["proj-alpha-t000"],
        )
        # t001 failed but is NOT required -> project complete on the required set
        self.assertEqual(v["status"], "complete")
        self.assertTrue(v["complete"])

    def test_invalid_plan_safe(self):
        v = evaluate_project_completion({"tasks": []}, {})
        self.assertEqual(v["status"], "invalid")
        self.assertFalse(v["complete"])
        self.assertTrue(v["errors"])

    def test_fallback_to_plan_status(self):
        # no task_results -> all tasks fall back to plan status "planned" -> pending -> in_progress
        v = evaluate_project_completion(_plan())
        self.assertEqual(v["status"], "in_progress")
        self.assertEqual(v["counts"]["pending"], 2)

    def test_deterministic(self):
        a = evaluate_project_completion(_plan(), {"proj-alpha-t000": "done", "proj-alpha-t001": "done"})
        b = evaluate_project_completion(_plan(), {"proj-alpha-t000": "done", "proj-alpha-t001": "done"})
        self.assertEqual(a, b)

    def test_unsupported_criteria_recorded(self):
        v = evaluate_project_completion(
            _plan(), {"proj-alpha-t000": "done", "proj-alpha-t001": "done"},
            completion_criteria=["all_tasks_done", "bogus_criterion"],
        )
        self.assertTrue(any("unsupported completion_criteria" in e for e in v["errors"]))
        self.assertEqual(v["status"], "complete")  # still complete on the valid criterion


if __name__ == "__main__":
    unittest.main()
