from __future__ import annotations

import importlib.util
import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from automation.orchestration.repository_resolved_single_task_controller import RepositorySingleTaskRunResult


def _module():
    path = Path(__file__).resolve().parents[1] / "scripts/run_repository_single_task.py"
    spec = importlib.util.spec_from_file_location("single_task_cli", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _result(status: str) -> RepositorySingleTaskRunResult:
    return RepositorySingleTaskRunResult("1", "run", status, "single_task.test", None, "repo", "task", "/tmp/source", "main", "a" * 40, "a" * 40, "profile", "b" * 64, "/tmp/worktree", status == "blocked", "codex-task/repo/task", "c" * 40, "a" * 40, ("file.py",), "codex_cli", "completed", "passed", "validation_passed", False, "not_attempted", "/tmp/receipt", "/tmp/receipt.sha256", "start", "finish")


class RepositorySingleTaskCliTests(unittest.TestCase):
    def test_help_and_public_options_only(self):
        cli = _module()
        help_text = cli._parser().format_help()
        self.assertIn("--repository-id", help_text)
        self.assertIn("--task-spec", help_text)
        for forbidden in ("--repo-path", "--repository-profile", "--validation-command", "--push", "--pr", "--merge", "--tag", "--release", "--max-cycles"):
            self.assertNotIn(forbidden, help_text)
        option_names = {option for action in cli._parser()._actions for option in action.option_strings}
        self.assertEqual(option_names - {"-h", "--help"}, {"--repository-id", "--task-spec"})

    def test_missing_and_forbidden_options_are_parser_errors(self):
        cli = _module()
        for argv in (("--task-spec", "task.json"), ("--repository-id", "repo"), ("--repository-id", "repo", "--task-spec", "task.json", "--push")):
            with self.subTest(argv=argv), self.assertRaises(SystemExit) as raised:
                cli.main(list(argv))
            self.assertEqual(raised.exception.code, 2)

    def test_status_exit_codes_markers_and_compact_redaction(self):
        cli = _module()
        for status, code, marker in (("completed", 0, "READY_FOR_PUSH_REVIEW"), ("blocked", 2, "BLOCKED_REPOSITORY_SINGLE_TASK"), ("failed", 1, "FAILED_REPOSITORY_SINGLE_TASK")):
            with self.subTest(status=status), mock.patch.object(cli, "run_repository_single_task", return_value=_result(status)) as controller:
                output = io.StringIO()
                with redirect_stdout(output):
                    actual = cli.main(["--repository-id", "repo", "--task-spec", "task.json"])
                self.assertEqual(actual, code)
                controller.assert_called_once_with(repository_id="repo", task_spec_path="task.json")
                lines = output.getvalue().splitlines()
                self.assertEqual(lines[-1], marker)
                self.assertEqual({line.split("=", 1)[0] for line in lines[:-1]}, {"status", "reason_code", "receipt_path", "repository_id", "task_id", "task_branch", "commit_sha", "worktree_preserved"})
                self.assertNotIn("PROMPT_SECRET_MARKER_8B71", output.getvalue())

    def test_controller_exception_is_redacted(self):
        cli = _module()
        output = io.StringIO()
        with mock.patch.object(cli, "run_repository_single_task", side_effect=ValueError("TOKEN_SECRET_MARKER_52AF ENV_SECRET_MARKER_91D4")), redirect_stdout(output):
            self.assertEqual(cli.main(["--repository-id", "repo", "--task-spec", "task.json"]), 1)
        self.assertIn("FAILED_REPOSITORY_SINGLE_TASK", output.getvalue())
        self.assertNotIn("TOKEN_SECRET_MARKER_52AF", output.getvalue())
        self.assertNotIn("ENV_SECRET_MARKER_91D4", output.getvalue())
