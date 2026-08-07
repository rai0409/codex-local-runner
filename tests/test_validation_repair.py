from __future__ import annotations

import ast
import unittest
from pathlib import Path

from automation.orchestration.validation_repair import MAX_REPAIR_PROMPT_CHARS
from automation.orchestration.validation_repair import MAX_REPAIR_STREAM_CHARS
from automation.orchestration.validation_repair import build_repair_prompt
from automation.orchestration.validation_repair import extract_actionable_failure


class ValidationRepairTests(unittest.TestCase):
    def _failure(self):
        return extract_actionable_failure({"command_results": [
            {"command_id": "skip", "kind": "focused", "status": "skipped", "return_code": None, "reason_code": "skip", "stdout": "", "stderr": ""},
            {"command_id": "pass", "kind": "focused", "status": "passed", "return_code": 0, "reason_code": "pass", "stdout": "", "stderr": ""},
            {"command_id": "first", "kind": "compile", "status": "failed", "return_code": 1, "reason_code": "compile.failed", "stdout": "a" * 5000, "stderr": "b" * 5000},
            {"command_id": "later", "kind": "full", "status": "timed_out", "return_code": None, "reason_code": "timeout", "stdout": "", "stderr": ""},
        ]})

    def test_selects_first_actionable_in_original_order_and_bounds_tails(self):
        failure = self._failure()
        self.assertEqual(failure["command_id"], "first")
        self.assertEqual(len(failure["stdout_tail"]), MAX_REPAIR_STREAM_CHARS)
        self.assertEqual(len(failure["stderr_tail"]), MAX_REPAIR_STREAM_CHARS)

    def test_skipped_and_successful_commands_are_not_selected(self):
        self.assertIsNone(extract_actionable_failure({"command_results": [
            {"command_id": "a", "kind": "x", "status": "skipped", "return_code": None, "reason_code": "x", "stdout": "", "stderr": ""},
            {"command_id": "b", "kind": "x", "status": "passed", "return_code": 0, "reason_code": "x", "stdout": "", "stderr": ""},
        ]}))

    def test_prompt_is_bounded_deterministic_and_includes_scope_and_safety(self):
        failure = self._failure()
        prompt = build_repair_prompt("original objective " * 2000, 1, failure, ("src/a.py", "tests/test_a.py"))
        self.assertLessEqual(len(prompt), MAX_REPAIR_PROMPT_CHARS)
        self.assertIn("src/a.py", prompt)
        self.assertIn("command_id: first", prompt)
        self.assertIn("Do not stage files", prompt)
        self.assertIn("Do not weaken validation", prompt)
        self.assertEqual(prompt, build_repair_prompt("original objective " * 2000, 1, failure, ("src/a.py", "tests/test_a.py")))

    def test_prompt_accepts_actionable_failure_with_nonzero_return_code(self):
        failure = {
            "command_id": "focused", "kind": "focused", "status": "failed",
            "return_code": 1, "reason_code": "safe_validation.command.failed",
            "stdout_tail": "focused output", "stderr_tail": "focused error",
        }

        prompt = build_repair_prompt("fix the focused validation failure", 1, failure)

        self.assertIn("command_id: focused", prompt)
        self.assertIn("return_code: 1", prompt)
        self.assertIn("reason_code: safe_validation.command.failed", prompt)

    def test_helpers_are_pure(self):
        module = __import__("automation.orchestration.validation_repair", fromlist=["*"])
        source = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
        forbidden = {"subprocess", "os", "git", "run_codex", "execute_repository_validation"}
        self.assertFalse({node.id for node in ast.walk(source) if isinstance(node, ast.Name)} & forbidden)
