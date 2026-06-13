"""Prompt646: tests for the deterministic project task generator.

Pure, offline tests — no execution, no daemon queue, no Codex, no network.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from automation.orchestration.planned_runner.project_plan import (
    planned_task_to_task_spec,
    validate_project_task_plan,
)
from automation.orchestration.planned_runner.project_task_generator import (
    generate_project_task_plan,
)
from automation.orchestration.planned_runner.task_spec import validate_task_spec


def _intent(max_tasks: int = 3, allowed=None) -> dict:
    return {
        "project_id": "proj-alpha",
        "project_name": "Alpha",
        "goal": "Add helper functions",
        "repo_target": "/tmp/placeholder_repo",
        "allowed_task_kinds": allowed or ["add_function"],
        "safety_limits": {"max_tasks": max_tasks, "max_cycles_per_task": 1, "max_total_seconds": 600},
        "source": "manual",
    }


def _descriptors() -> list[dict]:
    return [
        {"target_file": "pkg/a.py", "function_name": "fa", "expression": "a + b"},
        {"target_file": "pkg/b.py", "function_name": "fb", "expression": "a + b", "depends_on": [0]},
    ]


class ProjectTaskGeneratorTests(unittest.TestCase):
    def test_valid_intent_generates_valid_plan(self):
        result = generate_project_task_plan(_intent(), _descriptors(), generated_at="2026-06-14T00:00:00Z")
        self.assertEqual(result["status"], "success", msg=result["errors"])
        self.assertEqual(result["errors"], [])
        # generated plan passes the Prompt645 validator with no errors
        _, plan_errors = validate_project_task_plan(result["plan"])
        self.assertEqual(plan_errors, [])
        self.assertEqual(len(result["plan"]["tasks"]), 2)
        self.assertEqual(result["plan"]["source"], "generated")

    def test_deterministic_ids_order_and_deps(self):
        ids = [t["task_id"] for t in generate_project_task_plan(_intent(), _descriptors())["plan"]["tasks"]]
        self.assertEqual(ids, ["proj-alpha-t000", "proj-alpha-t001"])
        plan = generate_project_task_plan(_intent(), _descriptors())["plan"]
        self.assertEqual(plan["tasks"][1]["depends_on"], ["proj-alpha-t000"])
        self.assertEqual([t["order"] for t in plan["tasks"]], [0, 1])

    def test_deterministic_output_repeatable(self):
        a = generate_project_task_plan(_intent(), _descriptors(), generated_at="2026-06-14T00:00:00Z")
        b = generate_project_task_plan(_intent(), _descriptors(), generated_at="2026-06-14T00:00:00Z")
        self.assertEqual(a, b)

    def test_allowed_task_kinds_enforced(self):
        descs = [{"kind": "refactor", "target_file": "pkg/a.py", "function_name": "fa", "expression": "a + b"}]
        result = generate_project_task_plan(_intent(allowed=["add_function"]), descs)
        self.assertEqual(result["status"], "blocked")
        self.assertTrue(any("not in intent.allowed_task_kinds" in e for e in result["errors"]))

    def test_max_tasks_bound_enforced(self):
        descs = _descriptors() + [{"target_file": "pkg/c.py", "function_name": "fc", "expression": "a + b"}]
        result = generate_project_task_plan(_intent(max_tasks=2), descs)
        self.assertEqual(result["status"], "blocked")
        self.assertTrue(any("exceeds safety_limits.max_tasks" in e for e in result["errors"]))

    def test_invalid_intent_fails_safely(self):
        result = generate_project_task_plan({"project_id": "Bad ID"}, _descriptors())
        self.assertEqual(result["status"], "blocked")
        self.assertTrue(result["errors"])
        self.assertEqual(result["plan"], {})

    def test_empty_descriptors_blocked(self):
        result = generate_project_task_plan(_intent(), [])
        self.assertEqual(result["status"], "blocked")
        self.assertTrue(any("non-empty" in e for e in result["errors"]))

    def test_missing_add_function_fields_blocked(self):
        descs = [{"target_file": "pkg/a.py"}]  # missing function_name + expression
        result = generate_project_task_plan(_intent(), descs)
        self.assertEqual(result["status"], "blocked")
        self.assertTrue(any("missing required add_function fields" in e for e in result["errors"]))

    def test_unresolved_dependency_blocked(self):
        descs = [{"target_file": "pkg/a.py", "function_name": "fa", "expression": "a + b", "depends_on": ["ghost"]}]
        result = generate_project_task_plan(_intent(), descs)
        self.assertEqual(result["status"], "blocked")
        self.assertTrue(any("unresolved depends_on" in e for e in result["errors"]))

    def test_valid_dag_accepted(self):
        descs = [
            {"target_file": "pkg/a.py", "function_name": "fa", "expression": "a + b"},
            {"target_file": "pkg/b.py", "function_name": "fb", "expression": "a + b", "depends_on": [0]},
            {"target_file": "pkg/c.py", "function_name": "fc", "expression": "a + b", "depends_on": [0, 1]},
        ]
        result = generate_project_task_plan(_intent(max_tasks=3), descs)
        self.assertEqual(result["status"], "success", msg=result["errors"])

    def test_backward_compatible_task_spec_conversion(self):
        result = generate_project_task_plan(_intent(), _descriptors())
        self.assertEqual(result["status"], "success", msg=result["errors"])
        with tempfile.TemporaryDirectory(dir="/tmp") as repo:
            spec = planned_task_to_task_spec(result["plan"]["tasks"][0], overrides={"repo_path": repo})
            normalized, spec_errors = validate_task_spec(spec)
            self.assertEqual(spec_errors, [], msg=f"spec rejected: {spec_errors}")
            self.assertEqual(normalized["function_name"], "fa")

    def test_no_execution_side_effects(self):
        before = set(Path(".").iterdir())
        generate_project_task_plan(_intent(), _descriptors())
        generate_project_task_plan(_intent(), _descriptors(), generated_at="2026-06-14T00:00:00Z")
        after = set(Path(".").iterdir())
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
