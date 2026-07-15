"""Prompt647: tests for deterministic ProjectTaskPlan -> daemon queue population.

Pure, offline tests — no daemon run, no Codex, no network, no git; only tmpdirs.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from automation.orchestration.planned_runner.project_queue_population import (
    populate_queue_from_plan,
)
from automation.orchestration.planned_runner.project_task_generator import (
    generate_project_task_plan,
)
from automation.orchestration.planned_runner.task_spec import validate_task_spec


def _intent(max_tasks: int = 3) -> dict:
    return {
        "project_id": "proj-alpha",
        "project_name": "Alpha",
        "goal": "Add helper functions",
        "repo_target": "/tmp/placeholder_repo",
        "allowed_task_kinds": ["add_function"],
        "safety_limits": {"max_tasks": max_tasks, "max_cycles_per_task": 1, "max_total_seconds": 600},
    }


def _descriptors_with_deps() -> list[dict]:
    return [
        {"target_file": "pkg/a.py", "function_name": "fa", "expression": "a + b"},
        {"target_file": "pkg/b.py", "function_name": "fb", "expression": "a + b", "depends_on": [0]},
    ]


def _plan(descriptors=None, max_tasks=3) -> dict:
    descriptors = descriptors or _descriptors_with_deps()
    result = generate_project_task_plan(_intent(max_tasks), descriptors)
    assert result["status"] == "success", result["errors"]
    return result["plan"]


def _pending_files(queue_dir: Path) -> list[str]:
    return sorted(p.name for p in (queue_dir / "pending").glob("*.json"))


class ProjectQueuePopulationTests(unittest.TestCase):
    def test_valid_plan_populates_pending_files(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            q = Path(raw) / "queue"
            result = populate_queue_from_plan(_plan(), q)
            self.assertEqual(result["status"], "success", msg=result["errors"])
            self.assertEqual(result["task_count"], 2)
            self.assertEqual(len(result["written_files"]), 2)
            self.assertEqual(_pending_files(q), ["000-proj-alpha-t000.json", "001-proj-alpha-t001.json"])

    def test_written_specs_pass_task_spec_validation(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            q = Path(raw) / "queue"
            repo = Path(raw) / "repo"
            repo.mkdir()
            # repo_path_override makes repo_path an existing dir so validate_task_spec passes
            result = populate_queue_from_plan(_plan(), q, repo_path_override=repo.as_posix())
            self.assertEqual(result["status"], "success", msg=result["errors"])
            for path in result["written_files"]:
                spec = json.loads(Path(path).read_text(encoding="utf-8"))
                normalized, errors = validate_task_spec(spec)
                self.assertEqual(errors, [], msg=f"{path}: {errors}")
                self.assertEqual(normalized["repo_path"], repo.as_posix())

    def test_invalid_plan_fails_safely_no_files(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            q = Path(raw) / "queue"
            result = populate_queue_from_plan({"tasks": []}, q)  # missing intent + empty tasks
            self.assertEqual(result["status"], "blocked")
            self.assertTrue(result["errors"])
            self.assertEqual(result["written_files"], [])
            # nothing written
            self.assertFalse((q / "pending").exists() and any((q / "pending").iterdir()))

    def test_explicit_output_dir_required(self):
        for bad in (None, "", "   "):
            result = populate_queue_from_plan(_plan(), bad)
            self.assertEqual(result["status"], "blocked")
            self.assertTrue(any("output_queue_dir is required" in e for e in result["errors"]))
            self.assertEqual(result["written_files"], [])

    def test_deterministic_filenames_content_and_order(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw1, tempfile.TemporaryDirectory(dir="/tmp") as raw2:
            q1 = Path(raw1) / "queue"
            q2 = Path(raw2) / "queue"
            r1 = populate_queue_from_plan(_plan(), q1)
            r2 = populate_queue_from_plan(_plan(), q2)
            self.assertEqual(_pending_files(q1), _pending_files(q2))
            for name in _pending_files(q1):
                c1 = (q1 / "pending" / name).read_text(encoding="utf-8")
                c2 = (q2 / "pending" / name).read_text(encoding="utf-8")
                self.assertEqual(c1, c2, msg=f"content differs for {name}")

    def test_topological_order_respects_dependencies(self):
        # b depends on a, but list a after b -> topo order must still place a's file first
        descs = [
            {"name": "b", "target_file": "pkg/b.py", "function_name": "fb", "expression": "a + b", "depends_on": ["a"]},
            {"name": "a", "target_file": "pkg/a.py", "function_name": "fa", "expression": "a + b"},
        ]
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            q = Path(raw) / "queue"
            result = populate_queue_from_plan(_plan(descs), q)
            self.assertEqual(result["status"], "success", msg=result["errors"])
            files = _pending_files(q)
            # files sort by topological-order prefix; dependency 'a' (fa) must come first
            specs = [json.loads((q / "pending" / f).read_text()) for f in files]
            self.assertEqual(specs[0]["function_name"], "fa")
            self.assertEqual(specs[1]["function_name"], "fb")

    def test_dependency_warning_emitted(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            q = Path(raw) / "queue"
            result = populate_queue_from_plan(_plan(), q)  # has depends_on
            self.assertTrue(any("queue processing order only" in w for w in result["warnings"]))

    def test_no_dependency_warning_when_no_deps(self):
        descs = [{"target_file": "pkg/a.py", "function_name": "fa", "expression": "a + b"}]
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            q = Path(raw) / "queue"
            result = populate_queue_from_plan(_plan(descs), q)
            self.assertEqual(result["status"], "success", msg=result["errors"])
            self.assertEqual(result["warnings"], [])

    def test_create_dirs_false_requires_existing_pending(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            q = Path(raw) / "queue"  # not created
            result = populate_queue_from_plan(_plan(), q, create_dirs=False)
            self.assertEqual(result["status"], "blocked")
            self.assertTrue(any("does not exist" in e for e in result["errors"]))

    def test_no_side_effects_outside_explicit_dir(self):
        before = set(Path(".").iterdir())
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            populate_queue_from_plan(_plan(), Path(raw) / "queue")
        after = set(Path(".").iterdir())
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
