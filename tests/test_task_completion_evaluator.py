from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from automation.orchestration.task_completion_evaluator import (
    MAX_EVALUATOR_OUTPUT_BYTES,
    TASK_COMPLETION_EVALUATION_BEGIN,
    TASK_COMPLETION_EVALUATION_END,
    TaskCompletionEvaluation,
    build_task_completion_evaluator_prompt,
    build_task_completion_rework_prompt,
    execute_task_completion_evaluator,
    parse_task_completion_evaluation_output,
)


def envelope(payload: str) -> str:
    return f"{TASK_COMPLETION_EVALUATION_BEGIN}\n{payload}\n{TASK_COMPLETION_EVALUATION_END}"


class TaskCompletionEvaluatorTests(unittest.TestCase):
    def test_valid_statuses_parse(self):
        for status in ("completed", "needs_rework", "blocked"):
            result = parse_task_completion_evaluation_output(envelope(
                '{"status":"%s","reason_code":"task.code","satisfied_criteria":["a"],"unsatisfied_criteria":[],"evidence_refs":["git:diff"]}' % status
            ))
            self.assertEqual(result.status, status)

    def test_malformed_values_fail_closed(self):
        cases = ["", "{}", envelope("not-json"), envelope('{"status":"other"}'),
                 envelope('{"status":"completed","reason_code":"x","satisfied_criteria":"bad","unsatisfied_criteria":[],"evidence_refs":[]}'),
                 envelope('{"status":"completed","reason_code":"x","satisfied_criteria":[""],"unsatisfied_criteria":[],"evidence_refs":[]}'),
                 envelope('{"status":"completed","reason_code":"x","satisfied_criteria":[],"unsatisfied_criteria":[],"evidence_refs":[]}') + "x",
                 envelope('{"status":"completed","reason_code":"x","satisfied_criteria":[],"unsatisfied_criteria":[],"evidence_refs":[]}') + "\n" + envelope('{"status":"completed","reason_code":"x","satisfied_criteria":[],"unsatisfied_criteria":[],"evidence_refs":[]}'),
                 "x" * (MAX_EVALUATOR_OUTPUT_BYTES + 1)]
        for value in cases:
            with self.subTest(value=value[:20]):
                self.assertEqual(parse_task_completion_evaluation_output(value).status, "blocked")

    def test_prompts_include_objective_evidence_and_rework_safety(self):
        prompt = build_task_completion_evaluator_prompt(
            original_task="DISTINCTIVE_ORIGINAL_TASK", allowed_changed_paths=("a.py",), changed_paths=("a.py",),
            repository_state={"head_sha": "a" * 40}, diff_evidence="diff --git", validation_evidence={"status": "passed"}, artifact_evidence={},
        )
        self.assertIn("DISTINCTIVE_ORIGINAL_TASK", prompt)
        self.assertIn("implementation stdout/stderr", prompt)
        self.assertIn("review recommendations", prompt)
        rework = build_task_completion_rework_prompt(original_task="task", allowed_changed_paths=("a.py",), evaluation=TaskCompletionEvaluation("needs_rework", "task.missing", (), ("missing behavior",), ("git:diff",)))
        for text in ("missing behavior", "git:diff", "a.py", "Do not stage, commit", "Do not weaken"):
            self.assertIn(text, rework)

    def test_execution_uses_nonpersisted_prompt_and_no_runner_prompt_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            captured = {}
            def runner(**kwargs):
                captured.update(kwargs)
                out = root / "stdout.txt"
                out.write_text(envelope('{"status":"completed","reason_code":"task.ok","satisfied_criteria":["done"],"unsatisfied_criteria":[],"evidence_refs":["git:diff"]}'), encoding="utf-8")
                return {"status": "completed", "stdout_path": str(out)}
            result = execute_task_completion_evaluator(worktree_path=str(root), run_root=str(root / "runs"), prompt="DISTINCTIVE_ORIGINAL_TASK", runner=runner)
            self.assertEqual(result.status, "completed")
            self.assertFalse(captured["persist_prompt"])

