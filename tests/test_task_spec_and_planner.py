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


def _bounded_implementation_spec(repo_path: str, **overrides) -> dict:
    spec = {
        "task_id": "universe-loader-1",
        "kind": "bounded_implementation",
        "repo_path": repo_path,
        "allowed_files": ["src/universe.py", "tests/test_universe.py"],
        "goal": "Add a validated universe CSV loader.",
        "required_behavior": ["Reject missing ticker columns.", "Reject blank tickers."],
        "prohibited_behavior": ["Do not access the network."],
        "required_text": {
            "src/universe.py": ["def load_universe"],
            "tests/test_universe.py": ["def test_blank_ticker"],
        },
        "verify_commands": [["python", "-m", "pytest", "-q", "tests/test_universe.py"]],
    }
    spec.update(overrides)
    return spec


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

    def test_bounded_implementation_accepts_one_to_three_allowed_files(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            for allowed_files in (
                ["src/universe.py"],
                ["src/universe.py", "tests/test_universe.py"],
                ["src/universe.py", "tests/test_universe.py", "tests/test_api.py"],
            ):
                required_text = {
                    path: ["required marker"] for path in allowed_files
                }
                spec, errors = validate_task_spec(
                    _bounded_implementation_spec(
                        tmp_dir,
                        allowed_files=allowed_files,
                        required_text=required_text,
                    )
                )
                self.assertEqual(errors, [], msg=errors)
                self.assertEqual(spec["allowed_files"], allowed_files)

    def test_legacy_target_file_normalizes_to_single_allowed_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            spec, errors = validate_task_spec(_valid_spec(tmp_dir))
        self.assertEqual(errors, [])
        self.assertEqual(spec["allowed_files"], ["calculator.py"])

    def test_bounded_implementation_rejects_invalid_allowed_file_scopes(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            cases = (
                [],
                ["a.py", "b.py", "c.py", "d.py"],
                ["/tmp/a.py"],
                ["../a.py"],
                ["src/"],
                ["src/*.py"],
                ["a.py", "a.py"],
            )
            for allowed_files in cases:
                _, errors = validate_task_spec(
                    _bounded_implementation_spec(tmp_dir, allowed_files=allowed_files)
                )
                self.assertTrue(errors, msg=f"scope unexpectedly accepted: {allowed_files}")


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

    def test_bounded_implementation_plan_transmits_scope_to_prompt_and_effect_gate(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            spec, errors = validate_task_spec(_bounded_implementation_spec(tmp_dir))
            self.assertEqual(errors, [])
            plan = plan_task(spec, Path(tmp_dir) / "plan")
            prompt_text = Path(plan["generated_prompt_path"]).read_text(encoding="utf-8")
            effect_spec = json.loads(Path(plan["effect_spec_path"]).read_text(encoding="utf-8"))
        self.assertIn("- src/universe.py", prompt_text)
        self.assertIn("- tests/test_universe.py", prompt_text)
        self.assertEqual(effect_spec["allowed_files"], spec["allowed_files"])
        self.assertEqual(effect_spec["expected_modified_files"], spec["allowed_files"])


if __name__ == "__main__":
    unittest.main()
