from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from automation.orchestration.planned_runner.task_planner import plan_task
from automation.orchestration.planned_runner.task_spec import load_task_spec, validate_task_spec


def _valid_spec(repo_path: str) -> dict:
    return {
        "task_id": "calc-subtract-1",
        "kind": "add_function",
        "repo_path": repo_path,
        "target_file": "calculator.py",
        "function_name": "subtract",
        "expression": "a - b",
        "description": "add subtract",
        "expected_unmodified_files": ["test_calculator.py"],
        "verify_commands": [["python", "-c", "from calculator import subtract; assert subtract(7,4)==3"]],
    }


class TaskSpecTests(unittest.TestCase):
    def test_valid_spec_passes(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            spec, errors = validate_task_spec(_valid_spec(tmp_dir))
        self.assertEqual(errors, [])
        self.assertEqual(spec["task_id"], "calc-subtract-1")
        self.assertEqual(spec["verify_commands"][0][0], "python")

    def test_invalid_specs_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = _valid_spec(tmp_dir)
            cases = [
                ({**base, "task_id": "Bad Id!"}, "task_id"),
                ({**base, "kind": "refactor_world"}, "kind"),
                ({**base, "repo_path": tmp_dir + "/missing"}, "repo_path"),
                ({**base, "target_file": "../escape.py"}, "target_file"),
                ({**base, "function_name": "not valid"}, "function_name"),
                ({**base, "expression": ""}, "expression"),
            ]
            for payload, needle in cases:
                _, errors = validate_task_spec(payload)
                self.assertTrue(
                    any(needle in error for error in errors),
                    msg=f"expected error mentioning {needle}: {errors}",
                )

    def test_load_task_spec_from_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            spec_path = Path(tmp_dir) / "task.json"
            spec_path.write_text(json.dumps(_valid_spec(tmp_dir)), encoding="utf-8")
            spec, errors = load_task_spec(spec_path)
        self.assertEqual(errors, [])
        self.assertEqual(spec["function_name"], "subtract")


class TaskPlannerTests(unittest.TestCase):
    def test_plan_produces_prompt_spec_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            spec, errors = validate_task_spec(_valid_spec(tmp_dir))
            self.assertEqual(errors, [])
            plan = plan_task(spec, Path(tmp_dir) / "plan")
            prompt_text = Path(plan["generated_prompt_path"]).read_text(encoding="utf-8")
            effect_spec = json.loads(Path(plan["effect_spec_path"]).read_text(encoding="utf-8"))
            manifest = json.loads(Path(plan["manifest_path"]).read_text(encoding="utf-8"))
        self.assertEqual(plan["status"], "success")
        self.assertFalse(plan["codex_invoked"])
        self.assertIn(f"You are operating only inside {tmp_dir}", prompt_text)
        self.assertIn("Add a function named subtract(a, b) that returns a - b.", prompt_text)
        self.assertIn("Do not modify test_calculator.py.", prompt_text)
        self.assertEqual(effect_spec["repo_path"], tmp_dir)
        self.assertEqual(effect_spec["expected_modified_files"], ["calculator.py"])
        self.assertIn("def subtract(a, b):", effect_spec["required_text"]["calculator.py"])
        self.assertEqual(len(manifest["cycles"]), 1)
        self.assertEqual(manifest["cycles"][0]["effect_spec_path"], plan["effect_spec_path"])

    def test_plan_blocks_unsupported_kind(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            plan = plan_task({"kind": "mystery", "task_id": "x"}, tmp_dir)
        self.assertEqual(plan["status"], "blocked")


if __name__ == "__main__":
    unittest.main()
