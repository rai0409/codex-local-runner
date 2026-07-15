"""Prompt656: tests for the add_file task kind (validation + planner + chain safety)."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from automation.orchestration.planned_runner.task_spec import (
    ADD_FILE_MAX_CONTENT_BYTES,
    SUPPORTED_TASK_KINDS,
    validate_task_spec,
)
from automation.orchestration.planned_runner.task_planner import (
    build_task_effect_spec,
    build_task_prompt,
    plan_task,
)
from automation.orchestration.planned_runner.project_completion_gate import (
    evaluate_project_completion,
)
from automation.orchestration.planned_runner.project_plan import (
    planned_task_to_task_spec,
)
from automation.orchestration.planned_runner.project_task_generator import (
    generate_project_task_plan,
)


def _add_file_spec(tmp_repo, **over):
    spec = {
        "task_id": "p656-add-file",
        "kind": "add_file",
        "repo_path": tmp_repo,
        "target_file": "src/new_module.py",
        "content": "def hello():\n    return 1\n",
        "allow_overwrite": False,
        "create_parent_dirs": True,
    }
    spec.update(over)
    return spec


class AddFileValidationTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(dir="/tmp")
        self.repo = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def test_add_file_is_supported_kind(self):
        self.assertIn("add_file", SUPPORTED_TASK_KINDS)
        self.assertIn("add_function", SUPPORTED_TASK_KINDS)

    def test_valid_add_file_passes(self):
        spec, errors = validate_task_spec(_add_file_spec(self.repo))
        self.assertEqual(errors, [])
        self.assertEqual(spec["kind"], "add_file")
        self.assertEqual(spec["content"], "def hello():\n    return 1\n")
        self.assertFalse(spec["allow_overwrite"])
        self.assertTrue(spec["create_parent_dirs"])

    def test_absolute_target_rejected(self):
        _, errors = validate_task_spec(_add_file_spec(self.repo, target_file="/etc/evil.py"))
        self.assertTrue(any("target_file" in e for e in errors))

    def test_traversal_target_rejected(self):
        _, errors = validate_task_spec(_add_file_spec(self.repo, target_file="../../etc/evil.py"))
        self.assertTrue(any("target_file" in e for e in errors))

    def test_dotenv_rejected(self):
        for name in (".env", ".env.local", "config/.env.production"):
            _, errors = validate_task_spec(_add_file_spec(self.repo, target_file=name))
            self.assertTrue(any("secret" in e for e in errors), msg=name)

    def test_secret_like_paths_rejected(self):
        for name in ("my_secret.txt", "auth_token.json", "db_credential.yaml", ".ssh/id_rsa", "keys/id_ed25519"):
            _, errors = validate_task_spec(_add_file_spec(self.repo, target_file=name))
            self.assertTrue(any("secret" in e for e in errors), msg=name)

    def test_empty_content_rejected(self):
        _, errors = validate_task_spec(_add_file_spec(self.repo, content=""))
        self.assertTrue(any("content is required" in e for e in errors))

    def test_non_string_content_rejected(self):
        _, errors = validate_task_spec(_add_file_spec(self.repo, content={"x": 1}))
        self.assertTrue(any("content is required" in e for e in errors))

    def test_binary_content_rejected(self):
        _, errors = validate_task_spec(_add_file_spec(self.repo, content="abc\x00def"))
        self.assertTrue(any("binary" in e or "NUL" in e for e in errors))

    def test_oversized_content_rejected(self):
        big = "a" * (ADD_FILE_MAX_CONTENT_BYTES + 1)
        _, errors = validate_task_spec(_add_file_spec(self.repo, content=big))
        self.assertTrue(any("max size" in e for e in errors))

    def test_overwrite_protection_default_false(self):
        spec, _ = validate_task_spec(_add_file_spec(self.repo))
        self.assertFalse(spec["allow_overwrite"])
        prompt = build_task_prompt(spec)
        self.assertIn("must be a new file", prompt)  # no-overwrite instruction present

    def test_create_parent_dirs_explicit(self):
        spec_off, _ = validate_task_spec(_add_file_spec(self.repo, create_parent_dirs=False))
        self.assertFalse(spec_off["create_parent_dirs"])
        self.assertIn("Do not create directories", build_task_prompt(spec_off))
        spec_on, _ = validate_task_spec(_add_file_spec(self.repo, create_parent_dirs=True))
        self.assertIn("Create any parent directories", build_task_prompt(spec_on))

    def test_repo_path_must_be_dir(self):
        _, errors = validate_task_spec(_add_file_spec("/no/such/dir"))
        self.assertTrue(any("repo_path" in e for e in errors))


class AddFilePlannerTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(dir="/tmp")
        self.repo = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def test_effect_spec_requires_content_and_target(self):
        spec, errors = validate_task_spec(_add_file_spec(self.repo))
        self.assertEqual(errors, [])
        eff = build_task_effect_spec(spec)
        self.assertEqual(eff["expected_modified_files"], ["src/new_module.py"])
        self.assertIn("src/new_module.py", eff["required_text"])
        self.assertEqual(eff["required_text"]["src/new_module.py"], ["def hello():\n    return 1"])
        self.assertFalse(eff["allow_extra_files"])

    def test_plan_task_accepts_add_file(self):
        spec, _ = validate_task_spec(_add_file_spec(self.repo))
        with tempfile.TemporaryDirectory(dir="/tmp") as work:
            plan = plan_task(spec, work)
            self.assertEqual(plan["status"], "success")
            self.assertTrue(Path(plan["generated_prompt_path"]).is_file())
            self.assertTrue(Path(plan["effect_spec_path"]).is_file())

    def test_plan_task_rejects_unknown_kind(self):
        spec = _add_file_spec(self.repo)
        spec["kind"] = "delete_everything"
        with tempfile.TemporaryDirectory(dir="/tmp") as work:
            plan = plan_task(spec, work)
            self.assertEqual(plan["status"], "blocked")


class AddFileChainTests(unittest.TestCase):
    def _intent(self):
        return {
            "project_id": "p656-proj",
            "project_name": "add_file project",
            "goal": "add a file",
            "repo_target": "/tmp/p656_repo",
            "allowed_task_kinds": ["add_file"],
            "safety_limits": {"max_tasks": 2},
        }

    def test_generator_produces_valid_add_file_plan(self):
        descs = [{"kind": "add_file", "target_file": "src/a.py", "content": "x = 1\n"}]
        result = generate_project_task_plan(self._intent(), descs)
        self.assertEqual(result["status"], "success", msg=result["errors"])
        task = result["plan"]["tasks"][0]
        self.assertEqual(task["kind"], "add_file")
        # generated queue spec for add_file remains valid against task_spec
        with tempfile.TemporaryDirectory(dir="/tmp") as repo:
            spec = planned_task_to_task_spec(task, overrides={"repo_path": repo})
            normalized, errors = validate_task_spec(spec)
            self.assertEqual(errors, [], msg=errors)
            self.assertEqual(normalized["kind"], "add_file")
            self.assertEqual(normalized["content"], "x = 1\n")

    def test_generator_missing_content_blocked(self):
        descs = [{"kind": "add_file", "target_file": "src/a.py"}]  # no content
        result = generate_project_task_plan(self._intent(), descs)
        self.assertEqual(result["status"], "blocked")
        self.assertTrue(any("add_file" in e for e in result["errors"]))

    def test_completion_gate_does_not_mark_failed_add_file_complete(self):
        descs = [{"kind": "add_file", "target_file": "src/a.py", "content": "x = 1\n"}]
        plan = generate_project_task_plan(self._intent(), descs)["plan"]
        tid = plan["tasks"][0]["task_id"]
        verdict = evaluate_project_completion(plan, {tid: "failed"})
        self.assertEqual(verdict["status"], "failed")
        self.assertFalse(verdict["complete"])

    def test_no_side_effects(self):
        before = set(Path(".").iterdir())
        descs = [{"kind": "add_file", "target_file": "src/a.py", "content": "x = 1\n"}]
        generate_project_task_plan(self._intent(), descs)
        self.assertEqual(before, set(Path(".").iterdir()))


if __name__ == "__main__":
    unittest.main()
