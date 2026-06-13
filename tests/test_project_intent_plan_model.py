"""Prompt645: tests for the Project Intent / Project Task Plan data-model layer.

Pure, offline model tests — no execution, no daemon queue, no Codex, no network.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from automation.orchestration.planned_runner.project_intent import (
    DAEMON_MAX_CYCLES_CAP,
    DAEMON_MAX_JOBS_CAP,
    DAEMON_MAX_SECONDS_TOTAL_CAP,
    project_intent_from_json,
    project_intent_to_json,
    validate_project_intent,
)
from automation.orchestration.planned_runner.project_plan import (
    planned_task_to_task_spec,
    project_plan_from_json,
    project_plan_to_json,
    validate_project_task_plan,
)
from automation.orchestration.planned_runner.task_spec import validate_task_spec


def _valid_intent() -> dict:
    return {
        "project_id": "proj-alpha",
        "project_name": "Alpha",
        "goal": "Add helper functions across modules",
        "success_criteria": ["all tasks done", "tests pass"],
        "constraints": ["sandbox only"],
        "allowed_task_kinds": ["add_function"],
        "safety_limits": {"max_tasks": 3, "max_cycles_per_task": 1, "max_total_seconds": 600},
        "human_approval_policy": {"require_human_approval": True, "approval_required_for": ["push", "merge"]},
        "repo_target": "/tmp/some_repo",
        "source": "manual",
    }


def _task(task_id: str, depends_on=None) -> dict:
    return {
        "task_id": task_id,
        "kind": "add_function",
        "task_spec_payload": {
            "repo_path": "/tmp/placeholder",
            "target_file": "pkg/mod.py",
            "function_name": "fn_" + task_id.replace("-", "_"),
            "expression": "a + b",
            "verify_commands": [["python", "-m", "py_compile", "pkg/mod.py"]],
        },
        "depends_on": depends_on or [],
        "order": 0,
        "status": "planned",
    }


def _valid_plan() -> dict:
    return {
        "intent": _valid_intent(),
        "tasks": [_task("t1"), _task("t2", depends_on=["t1"])],
        "completion_criteria": "all tasks done",
        "generated_at": "2026-06-14T00:00:00Z",
        "source": "manual",
    }


class ProjectIntentModelTests(unittest.TestCase):
    def test_valid_intent_validates(self):
        intent, errors = validate_project_intent(_valid_intent())
        self.assertEqual(errors, [])
        self.assertEqual(intent["project_id"], "proj-alpha")
        self.assertEqual(intent["allowed_task_kinds"], ["add_function"])

    def test_invalid_intent_fails_safely(self):
        intent, errors = validate_project_intent({"project_id": "Bad ID", "project_name": ""})
        self.assertTrue(errors)
        self.assertTrue(any("project_id" in e for e in errors))
        self.assertTrue(any("goal" in e for e in errors))

    def test_non_object_intent_returns_error_not_raise(self):
        intent, errors = validate_project_intent("nope")  # type: ignore[arg-type]
        self.assertEqual(intent, {})
        self.assertTrue(errors)

    def test_unknown_allowed_task_kind_rejected(self):
        payload = _valid_intent()
        payload["allowed_task_kinds"] = ["add_function", "delete_everything"]
        _, errors = validate_project_intent(payload)
        self.assertTrue(any("unsupported" in e for e in errors))

    def test_safety_limits_bounded_by_daemon_caps(self):
        payload = _valid_intent()
        payload["safety_limits"] = {
            "max_tasks": DAEMON_MAX_JOBS_CAP + 1,
            "max_cycles_per_task": DAEMON_MAX_CYCLES_CAP + 5,
            "max_total_seconds": DAEMON_MAX_SECONDS_TOTAL_CAP + 1,
        }
        _, errors = validate_project_intent(payload)
        self.assertTrue(any("max_tasks" in e and "cap" in e for e in errors))
        self.assertTrue(any("max_cycles_per_task" in e and "cap" in e for e in errors))
        self.assertTrue(any("max_total_seconds" in e and "cap" in e for e in errors))

    def test_intent_round_trip(self):
        intent, errors = validate_project_intent(_valid_intent())
        self.assertEqual(errors, [])
        reloaded, reload_errors = project_intent_from_json(project_intent_to_json(intent))
        self.assertEqual(reload_errors, [])
        self.assertEqual(reloaded, intent)


class ProjectTaskPlanModelTests(unittest.TestCase):
    def test_valid_plan_validates(self):
        plan, errors = validate_project_task_plan(_valid_plan())
        self.assertEqual(errors, [])
        self.assertEqual(len(plan["tasks"]), 2)
        self.assertEqual(plan["tasks"][1]["depends_on"], ["t1"])

    def test_kind_not_in_allowed_rejected(self):
        payload = _valid_plan()
        payload["tasks"][0]["kind"] = "refactor"  # not in allowed_task_kinds
        _, errors = validate_project_task_plan(payload)
        self.assertTrue(any("not in intent.allowed_task_kinds" in e for e in errors))

    def test_duplicate_task_ids_rejected(self):
        payload = _valid_plan()
        payload["tasks"] = [_task("dup"), _task("dup")]
        _, errors = validate_project_task_plan(payload)
        self.assertTrue(any("duplicate task_id" in e for e in errors))

    def test_dangling_dependency_rejected(self):
        payload = _valid_plan()
        payload["tasks"] = [_task("t1", depends_on=["ghost"])]
        _, errors = validate_project_task_plan(payload)
        self.assertTrue(any("dangling depends_on" in e for e in errors))

    def test_dependency_cycle_rejected(self):
        payload = _valid_plan()
        payload["tasks"] = [_task("a", depends_on=["b"]), _task("b", depends_on=["a"])]
        _, errors = validate_project_task_plan(payload)
        self.assertTrue(any("cycle" in e for e in errors))

    def test_valid_dag_accepted(self):
        payload = _valid_plan()
        payload["tasks"] = [_task("a"), _task("b", depends_on=["a"]), _task("c", depends_on=["a", "b"])]
        _, errors = validate_project_task_plan(payload)
        self.assertEqual(errors, [])

    def test_max_tasks_bound_enforced(self):
        payload = _valid_plan()
        payload["intent"]["safety_limits"]["max_tasks"] = 1
        payload["tasks"] = [_task("t1"), _task("t2")]
        _, errors = validate_project_task_plan(payload)
        self.assertTrue(any("exceeds intent safety_limits.max_tasks" in e for e in errors))

    def test_task_requires_payload_or_ref(self):
        payload = _valid_plan()
        payload["tasks"] = [{"task_id": "t1", "kind": "add_function", "depends_on": [], "status": "planned"}]
        _, errors = validate_project_task_plan(payload)
        self.assertTrue(any("task_spec_payload or generated_task_spec_ref" in e for e in errors))

    def test_plan_round_trip(self):
        plan, errors = validate_project_task_plan(_valid_plan())
        self.assertEqual(errors, [])
        reloaded, reload_errors = project_plan_from_json(project_plan_to_json(plan))
        self.assertEqual(reload_errors, [])
        self.assertEqual(reloaded, plan)

    def test_planned_task_to_task_spec_is_backward_compatible(self):
        plan, errors = validate_project_task_plan(_valid_plan())
        self.assertEqual(errors, [])
        with tempfile.TemporaryDirectory(dir="/tmp") as repo:
            # supply a concrete existing repo_path via overrides (model time does not require it)
            spec = planned_task_to_task_spec(plan["tasks"][0], overrides={"repo_path": repo})
            normalized, spec_errors = validate_task_spec(spec)
            self.assertEqual(spec_errors, [], msg=f"spec rejected: {spec_errors}")
            self.assertEqual(normalized["task_id"], "t1")
            self.assertEqual(normalized["kind"], "add_function")

    def test_no_execution_side_effects(self):
        # Validating a plan must not create any queue dirs or files in cwd.
        before = set(Path(".").iterdir())
        validate_project_task_plan(_valid_plan())
        plan, _ = validate_project_task_plan(_valid_plan())
        planned_task_to_task_spec(plan["tasks"][0])
        after = set(Path(".").iterdir())
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
