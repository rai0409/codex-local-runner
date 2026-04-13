from __future__ import annotations

import json
import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from adapters.chatgpt_tasks import ChatgptTasksAdapter
from adapters.codex_cli import _build_review_handoff_summary
from adapters.codex_cli import _build_reviewer_handoff
from adapters.codex_cli import CodexCliAdapter
from adapters.codex_cli import _derive_result_interpretation
from adapters.codex_cli import _derive_review_recommendation
from adapters.local_llm import LocalLlmAdapter
from orchestrator import main as orchestrator_main


class CodexCliExecutionTests(unittest.TestCase):
    def _assert_review_handoff_summary_consistency(self, result: dict) -> None:
        summary = result["review_handoff_summary"]
        self.assertEqual(
            set(summary.keys()),
            {
                "final_status",
                "final_verify_status",
                "final_verify_reason",
                "retry_attempted",
                "retry_outcome",
                "result_interpretation",
                "review_recommendation",
            },
        )
        self.assertEqual(summary["final_status"], result["status"])
        self.assertEqual(summary["final_verify_status"], result["verify"]["status"])
        self.assertEqual(summary["final_verify_reason"], result["verify"]["reason"])
        self.assertEqual(summary["retry_attempted"], result["retry"]["attempted"])
        self.assertEqual(summary["retry_outcome"], result["retry"]["outcome"])
        self.assertEqual(summary["result_interpretation"], result["result_interpretation"])
        self.assertEqual(summary["review_recommendation"], result["review_recommendation"])

    def _assert_reviewer_handoff_consistency(self, result: dict) -> None:
        handoff = result["reviewer_handoff"]
        self.assertEqual(set(handoff.keys()), {"summary", "execution", "validation"})
        summary = handoff["summary"]
        self.assertEqual(
            set(summary.keys()),
            {
                "final_status",
                "final_verify_status",
                "final_verify_reason",
                "retry_attempted",
                "retry_outcome",
                "result_interpretation",
                "review_recommendation",
            },
        )
        self.assertEqual(summary, result["review_handoff_summary"])
        self.assertEqual(summary["final_status"], result["status"])
        self.assertEqual(summary["final_verify_status"], result["verify"]["status"])
        self.assertEqual(summary["final_verify_reason"], result["verify"]["reason"])
        self.assertEqual(summary["retry_attempted"], result["retry"]["attempted"])
        self.assertEqual(summary["retry_outcome"], result["retry"]["outcome"])
        self.assertEqual(summary["result_interpretation"], result["result_interpretation"])
        self.assertEqual(summary["review_recommendation"], result["review_recommendation"])

        execution = handoff["execution"]
        self.assertEqual(set(execution.keys()), {"status", "attempt_count", "return_code"})
        self.assertEqual(execution["status"], result["status"])
        self.assertEqual(execution["attempt_count"], result["attempt_count"])
        self.assertEqual(execution["return_code"], result["return_code"])

        validation = handoff["validation"]
        self.assertEqual(validation["verify_status"], result["verify"]["status"])
        self.assertEqual(validation["verify_reason"], result["verify"]["reason"])
        if "summary" in result["verify"]:
            self.assertEqual(set(validation.keys()), {"verify_status", "verify_reason", "summary"})
            self.assertEqual(validation["summary"], result["verify"]["summary"])
        else:
            self.assertEqual(set(validation.keys()), {"verify_status", "verify_reason"})

        self.assertNotIn("diff", handoff)
        self.assertNotIn("tests", handoff)

    def test_codex_cli_execute_completed(self) -> None:
        adapter = CodexCliAdapter()
        with tempfile.TemporaryDirectory() as repo_dir, tempfile.TemporaryDirectory() as work_dir:
            execution_dir = Path(work_dir) / "execution_runs" / "20260101_000000"
            with mock.patch(
                "adapters.codex_cli.prepare_git_worktree",
                return_value={
                    "source_repo_path": repo_dir,
                    "worktree_path": "/prepared/worktree",
                    "branch_name": "codex-run/20260101_000000",
                    "created": True,
                    "cleanup_needed": True,
                    "error": "",
                },
            ):
                with mock.patch(
                    "adapters.codex_cli.cleanup_git_worktree",
                    return_value={
                        "worktree_path": "/prepared/worktree",
                        "branch_name": "codex-run/20260101_000000",
                        "cleaned": True,
                        "error": "",
                    },
                ):
                    with mock.patch(
                        "adapters.codex_cli.run_codex",
                        return_value={
                            "status": "completed",
                            "success": True,
                            "return_code": 0,
                            "started_at": "2026-01-01T00:00:00",
                            "finished_at": "2026-01-01T00:00:01",
                            "artifacts": [
                                {"name": "stdout", "path": str(execution_dir / "stdout.txt")},
                                {"name": "stderr", "path": str(execution_dir / "stderr.txt")},
                                {"name": "meta", "path": str(execution_dir / "meta.json")},
                            ],
                            "stdout_path": str(execution_dir / "stdout.txt"),
                            "stderr_path": str(execution_dir / "stderr.txt"),
                            "meta_path": str(execution_dir / "meta.json"),
                            "error": "",
                        },
                    ) as run_codex_mock:
                        result = adapter.execute(
                            {
                                "prompt": "test prompt",
                                "repo_path": repo_dir,
                                "work_dir": work_dir,
                                "timeout_seconds": 30,
                            }
                        )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["started_at"], "2026-01-01T00:00:00")
        self.assertEqual(result["finished_at"], "2026-01-01T00:00:01")
        self.assertIsNone(result["error"])
        self.assertEqual(len(result["artifacts"]), 3)
        run_codex_mock.assert_called_once()
        self.assertEqual(result["attempt_count"], 1)
        self.assertEqual(
            result["retry"],
            {"attempted": False, "trigger": "not_applicable", "outcome": "not_attempted"},
        )
        self.assertEqual(result["verify"]["status"], "not_run")
        self.assertEqual(result["result_interpretation"], "completed_verified_passed")
        self.assertEqual(result["review_recommendation"], "no_review_needed")
        self._assert_review_handoff_summary_consistency(result)
        self._assert_reviewer_handoff_consistency(result)

    def test_codex_cli_execute_failure_is_reported(self) -> None:
        adapter = CodexCliAdapter()
        with tempfile.TemporaryDirectory() as repo_dir, tempfile.TemporaryDirectory() as work_dir:
            with mock.patch(
                "adapters.codex_cli.prepare_git_worktree",
                return_value={
                    "source_repo_path": repo_dir,
                    "worktree_path": "/prepared/worktree",
                    "branch_name": "codex-run/20260101_000000",
                    "created": True,
                    "cleanup_needed": True,
                    "error": "",
                },
            ):
                with mock.patch(
                    "adapters.codex_cli.cleanup_git_worktree",
                    return_value={
                        "worktree_path": "/prepared/worktree",
                        "branch_name": "codex-run/20260101_000000",
                        "cleaned": True,
                        "error": "",
                    },
                ):
                    with mock.patch("adapters.codex_cli.run_validation_commands") as verify_mock:
                        with mock.patch(
                            "adapters.codex_cli.run_codex",
                            return_value={
                                "status": "failed",
                                "success": False,
                                "return_code": 2,
                                "started_at": "2026-01-01T00:00:00",
                                "finished_at": "2026-01-01T00:00:01",
                                "artifacts": [
                                    {
                                        "name": "stderr",
                                        "path": str(Path(work_dir) / "execution_runs" / "stderr.txt"),
                                    }
                                ],
                                "stdout_path": str(Path(work_dir) / "execution_runs" / "stdout.txt"),
                                "stderr_path": str(Path(work_dir) / "execution_runs" / "stderr.txt"),
                                "meta_path": str(Path(work_dir) / "execution_runs" / "meta.json"),
                                "error": "execution failed",
                            },
                        ) as run_codex_mock:
                            result = adapter.execute(
                                {
                                    "prompt": "test prompt",
                                    "repo_path": repo_dir,
                                    "work_dir": work_dir,
                                    "timeout_seconds": 30,
                                }
                            )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["started_at"], "2026-01-01T00:00:00")
        self.assertEqual(result["finished_at"], "2026-01-01T00:00:01")
        self.assertIn("execution failed", result["error"])
        run_codex_mock.assert_called_once()
        verify_mock.assert_not_called()
        self.assertEqual(result["verify"]["status"], "not_run")
        self.assertEqual(
            set(result["verify"].keys()),
            {"status", "success", "commands", "error", "reason"},
        )
        self.assertNotIn("command_results", result["verify"])
        self.assertNotIn("summary", result["verify"])
        self.assertEqual(result["attempt_count"], 1)
        self.assertEqual(
            result["retry"],
            {"attempted": False, "trigger": "not_applicable", "outcome": "not_attempted"},
        )
        self.assertEqual(result["result_interpretation"], "execution_not_completed")
        self.assertEqual(result["review_recommendation"], "review_recommended")
        self._assert_review_handoff_summary_consistency(result)
        self._assert_reviewer_handoff_consistency(result)

    def test_codex_cli_execute_uses_prepared_worktree_path(self) -> None:
        adapter = CodexCliAdapter()
        with tempfile.TemporaryDirectory() as work_dir:
            with mock.patch(
                "adapters.codex_cli.prepare_git_worktree",
                return_value={
                    "source_repo_path": "/source/repo",
                    "worktree_path": "/prepared/worktree",
                    "branch_name": "codex-run/20260101_000000",
                    "created": True,
                    "cleanup_needed": True,
                    "error": "",
                },
            ) as prepare_mock:
                with mock.patch(
                    "adapters.codex_cli.cleanup_git_worktree",
                    return_value={
                        "worktree_path": "/prepared/worktree",
                        "branch_name": "codex-run/20260101_000000",
                        "cleaned": True,
                        "error": "",
                    },
                ) as cleanup_mock:
                    with mock.patch(
                        "adapters.codex_cli.run_validation_commands",
                        return_value={
                            "status": "passed",
                            "success": True,
                            "commands": [
                                {
                                    "command": "echo verify",
                                    "return_code": 0,
                                    "stdout": "ok\n",
                                    "stderr": "",
                                    "success": True,
                                }
                            ],
                            "command_results": [
                                {
                                    "command": "echo verify",
                                    "status": "passed",
                                    "return_code": 0,
                                    "stdout": "ok\n",
                                    "stderr": "",
                                }
                            ],
                            "error": "",
                            "summary": {"total": 1, "passed": 1, "failed": 0},
                            "reason": "validation_passed",
                        },
                    ) as verify_mock:
                        with mock.patch(
                            "adapters.codex_cli.run_codex",
                            return_value={
                                "status": "completed",
                                "success": True,
                                "return_code": 0,
                                "started_at": "2026-01-01T00:00:00",
                                "finished_at": "2026-01-01T00:00:01",
                                "artifacts": [],
                                "stdout_path": "",
                                "stderr_path": "",
                                "meta_path": "",
                                "error": "",
                            },
                        ) as run_codex_mock:
                            result = adapter.execute(
                                {
                                    "prompt": "test prompt",
                                    "repo_path": "/source/repo",
                                    "work_dir": work_dir,
                                    "validation_commands": ["echo verify"],
                                }
                            )

        prepare_mock.assert_called_once_with(
            source_repo_path="/source/repo",
            worktree_parent=str(Path(work_dir) / "worktrees"),
        )
        run_codex_mock.assert_called_once_with(
            task={"repo_path": "/prepared/worktree"},
            prompt="test prompt",
            work_root=str(Path(work_dir) / "execution_runs"),
        )
        cleanup_mock.assert_called_once_with(
            source_repo_path="/source/repo",
            worktree_path="/prepared/worktree",
            branch_name="codex-run/20260101_000000",
        )
        verify_mock.assert_called_once_with(
            validation_commands=["echo verify"],
            cwd="/prepared/worktree",
        )
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["verify"]["status"], "passed")
        self.assertEqual(result["verify"]["summary"], {"total": 1, "passed": 1, "failed": 0})
        self.assertEqual(result["verify"]["command_results"][0]["status"], "passed")
        self.assertEqual(result["verify"]["reason"], "validation_passed")
        self.assertEqual(result["attempt_count"], 1)
        self.assertEqual(
            result["retry"],
            {"attempted": False, "trigger": "not_applicable", "outcome": "not_attempted"},
        )
        self.assertEqual(result["result_interpretation"], "completed_verified_passed")
        self.assertEqual(result["review_recommendation"], "no_review_needed")
        self._assert_review_handoff_summary_consistency(result)
        self._assert_reviewer_handoff_consistency(result)

    def test_codex_cli_execute_fails_when_worktree_preparation_fails(self) -> None:
        adapter = CodexCliAdapter()
        with tempfile.TemporaryDirectory() as work_dir:
            with mock.patch(
                "adapters.codex_cli.prepare_git_worktree",
                return_value={
                    "source_repo_path": "/source/repo",
                    "worktree_path": "",
                    "branch_name": "",
                    "created": False,
                    "cleanup_needed": False,
                    "error": "source repo path is not a git working tree: not a git repository",
                },
            ):
                with mock.patch("adapters.codex_cli.run_validation_commands") as verify_mock:
                    with mock.patch("adapters.codex_cli.run_codex") as run_codex_mock:
                        result = adapter.execute(
                            {
                                "prompt": "test prompt",
                                "repo_path": "/source/repo",
                                "work_dir": work_dir,
                            }
                        )

        run_codex_mock.assert_not_called()
        verify_mock.assert_not_called()
        self.assertEqual(result["status"], "failed")
        self.assertIn("not a git working tree", result["error"])
        self.assertEqual(result["verify"]["status"], "not_run")
        self.assertEqual(result["verify"]["reason"], "validation_not_run_execution_status_failed")
        self.assertNotIn("command_results", result["verify"])
        self.assertNotIn("summary", result["verify"])
        self.assertEqual(result["attempt_count"], 1)
        self.assertEqual(
            result["retry"],
            {"attempted": False, "trigger": "not_applicable", "outcome": "not_attempted"},
        )
        self.assertEqual(result["result_interpretation"], "execution_not_completed")
        self.assertEqual(result["review_recommendation"], "review_recommended")
        self._assert_review_handoff_summary_consistency(result)
        self._assert_reviewer_handoff_consistency(result)

    def test_codex_cli_execute_timed_out_sets_verify_not_run(self) -> None:
        adapter = CodexCliAdapter()
        with tempfile.TemporaryDirectory() as repo_dir, tempfile.TemporaryDirectory() as work_dir:
            with mock.patch(
                "adapters.codex_cli.prepare_git_worktree",
                return_value={
                    "source_repo_path": repo_dir,
                    "worktree_path": "/prepared/worktree",
                    "branch_name": "codex-run/20260101_000000",
                    "created": True,
                    "cleanup_needed": True,
                    "error": "",
                },
            ):
                with mock.patch(
                    "adapters.codex_cli.cleanup_git_worktree",
                    return_value={
                        "worktree_path": "/prepared/worktree",
                        "branch_name": "codex-run/20260101_000000",
                        "cleaned": True,
                        "error": "",
                    },
                ):
                    with mock.patch("adapters.codex_cli.run_validation_commands") as verify_mock:
                        with mock.patch(
                            "adapters.codex_cli.run_codex",
                            return_value={
                                "status": "timed_out",
                                "success": False,
                                "return_code": None,
                                "started_at": "2026-01-01T00:00:00",
                                "finished_at": "2026-01-01T00:10:00",
                                "artifacts": [],
                                "stdout_path": "",
                                "stderr_path": "",
                                "meta_path": "",
                                "error": "timed out",
                            },
                        ) as run_codex_mock:
                            result = adapter.execute(
                                {
                                    "prompt": "test prompt",
                                    "repo_path": repo_dir,
                                    "work_dir": work_dir,
                                    "validation_commands": ["echo verify"],
                                }
                            )

        verify_mock.assert_not_called()
        run_codex_mock.assert_called_once()
        self.assertEqual(result["status"], "timed_out")
        self.assertEqual(result["verify"]["status"], "not_run")
        self.assertEqual(result["verify"]["reason"], "validation_not_run_execution_status_timed_out")
        self.assertNotIn("command_results", result["verify"])
        self.assertNotIn("summary", result["verify"])
        self.assertEqual(result["attempt_count"], 1)
        self.assertEqual(
            result["retry"],
            {"attempted": False, "trigger": "not_applicable", "outcome": "not_attempted"},
        )
        self.assertEqual(result["result_interpretation"], "execution_not_completed")
        self.assertEqual(result["review_recommendation"], "review_recommended")
        self._assert_review_handoff_summary_consistency(result)
        self._assert_reviewer_handoff_consistency(result)

    def test_codex_cli_retries_once_when_verify_failed_and_second_attempt_passes(self) -> None:
        adapter = CodexCliAdapter()
        with tempfile.TemporaryDirectory() as repo_dir, tempfile.TemporaryDirectory() as work_dir:
            with mock.patch(
                "adapters.codex_cli.prepare_git_worktree",
                return_value={
                    "source_repo_path": repo_dir,
                    "worktree_path": "/prepared/worktree",
                    "branch_name": "codex-run/20260101_000000",
                    "created": True,
                    "cleanup_needed": True,
                    "error": "",
                },
            ):
                with mock.patch(
                    "adapters.codex_cli.cleanup_git_worktree",
                    return_value={
                        "worktree_path": "/prepared/worktree",
                        "branch_name": "codex-run/20260101_000000",
                        "cleaned": True,
                        "error": "",
                    },
                ):
                    with mock.patch(
                        "adapters.codex_cli.run_codex",
                        side_effect=[
                            {
                                "status": "completed",
                                "success": True,
                                "return_code": 0,
                                "started_at": "2026-01-01T00:00:00",
                                "finished_at": "2026-01-01T00:00:01",
                                "artifacts": [],
                                "stdout_path": "",
                                "stderr_path": "",
                                "meta_path": "",
                                "error": "",
                            },
                            {
                                "status": "completed",
                                "success": True,
                                "return_code": 0,
                                "started_at": "2026-01-01T00:00:02",
                                "finished_at": "2026-01-01T00:00:03",
                                "artifacts": [],
                                "stdout_path": "",
                                "stderr_path": "",
                                "meta_path": "",
                                "error": "",
                            },
                        ],
                    ) as run_codex_mock:
                        with mock.patch(
                            "adapters.codex_cli.run_validation_commands",
                            side_effect=[
                                {
                                    "status": "failed",
                                    "success": False,
                                    "commands": [
                                        {
                                            "command": "echo verify",
                                            "return_code": 1,
                                            "stdout": "",
                                            "stderr": "first failure",
                                            "success": False,
                                        }
                                    ],
                                    "command_results": [
                                        {
                                            "command": "echo verify",
                                            "status": "failed",
                                            "return_code": 1,
                                            "stdout": "",
                                            "stderr": "first failure",
                                        }
                                    ],
                                    "error": "first failure",
                                    "summary": {"total": 1, "passed": 0, "failed": 1},
                                    "reason": "validation_failed",
                                },
                                {
                                    "status": "passed",
                                    "success": True,
                                    "commands": [
                                        {
                                            "command": "echo verify",
                                            "return_code": 0,
                                            "stdout": "ok\n",
                                            "stderr": "",
                                            "success": True,
                                        }
                                    ],
                                    "command_results": [
                                        {
                                            "command": "echo verify",
                                            "status": "passed",
                                            "return_code": 0,
                                            "stdout": "ok\n",
                                            "stderr": "",
                                        }
                                    ],
                                    "error": "",
                                    "summary": {"total": 1, "passed": 1, "failed": 0},
                                    "reason": "validation_passed",
                                },
                            ],
                        ) as verify_mock:
                            result = adapter.execute(
                                {
                                    "prompt": "test prompt",
                                    "repo_path": repo_dir,
                                    "work_dir": work_dir,
                                    "validation_commands": ["echo verify"],
                                }
                            )

        self.assertEqual(run_codex_mock.call_count, 2)
        self.assertEqual(verify_mock.call_count, 2)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["started_at"], "2026-01-01T00:00:02")
        self.assertEqual(result["finished_at"], "2026-01-01T00:00:03")
        self.assertEqual(result["verify"]["status"], "passed")
        self.assertEqual(result["verify"]["reason"], "validation_passed")
        self.assertEqual(result["verify"]["error"], "")
        self.assertIn("commands", result["verify"])
        self.assertIn("command_results", result["verify"])
        self.assertIn("summary", result["verify"])
        self.assertEqual(result["verify"]["summary"], {"total": 1, "passed": 1, "failed": 0})
        self.assertEqual(len(result["verify"]["command_results"]), result["verify"]["summary"]["total"])
        self.assertEqual(len(result["verify"]["command_results"]), 1)
        self.assertEqual(result["verify"]["command_results"][0]["status"], "passed")
        self.assertEqual(result["attempt_count"], 2)
        self.assertEqual(
            result["retry"],
            {"attempted": True, "trigger": "verify_failed", "outcome": "retry_succeeded"},
        )
        self.assertEqual(result["result_interpretation"], "completed_verified_passed_after_retry")
        self.assertEqual(result["review_recommendation"], "review_recommended")
        self._assert_review_handoff_summary_consistency(result)
        self._assert_reviewer_handoff_consistency(result)

    def test_codex_cli_retry_outcome_failed_when_second_attempt_verify_fails(self) -> None:
        adapter = CodexCliAdapter()
        with tempfile.TemporaryDirectory() as repo_dir, tempfile.TemporaryDirectory() as work_dir:
            with mock.patch(
                "adapters.codex_cli.prepare_git_worktree",
                return_value={
                    "source_repo_path": repo_dir,
                    "worktree_path": "/prepared/worktree",
                    "branch_name": "codex-run/20260101_000000",
                    "created": True,
                    "cleanup_needed": True,
                    "error": "",
                },
            ):
                with mock.patch(
                    "adapters.codex_cli.cleanup_git_worktree",
                    return_value={
                        "worktree_path": "/prepared/worktree",
                        "branch_name": "codex-run/20260101_000000",
                        "cleaned": True,
                        "error": "",
                    },
                ):
                    with mock.patch(
                        "adapters.codex_cli.run_codex",
                        side_effect=[
                            {
                                "status": "completed",
                                "success": True,
                                "return_code": 0,
                                "started_at": "2026-01-01T00:00:00",
                                "finished_at": "2026-01-01T00:00:01",
                                "artifacts": [],
                                "stdout_path": "",
                                "stderr_path": "",
                                "meta_path": "",
                                "error": "",
                            },
                            {
                                "status": "completed",
                                "success": True,
                                "return_code": 0,
                                "started_at": "2026-01-01T00:00:02",
                                "finished_at": "2026-01-01T00:00:03",
                                "artifacts": [],
                                "stdout_path": "",
                                "stderr_path": "",
                                "meta_path": "",
                                "error": "",
                            },
                        ],
                    ):
                        with mock.patch(
                            "adapters.codex_cli.run_validation_commands",
                            side_effect=[
                                {
                                    "status": "failed",
                                    "success": False,
                                    "commands": [
                                        {
                                            "command": "echo verify",
                                            "return_code": 1,
                                            "stdout": "",
                                            "stderr": "first failure",
                                            "success": False,
                                        }
                                    ],
                                    "command_results": [
                                        {
                                            "command": "echo verify",
                                            "status": "failed",
                                            "return_code": 1,
                                            "stdout": "",
                                            "stderr": "first failure",
                                        }
                                    ],
                                    "error": "first failure",
                                    "summary": {"total": 1, "passed": 0, "failed": 1},
                                    "reason": "validation_failed",
                                },
                                {
                                    "status": "failed",
                                    "success": False,
                                    "commands": [
                                        {
                                            "command": "echo verify",
                                            "return_code": 1,
                                            "stdout": "",
                                            "stderr": "second failure",
                                            "success": False,
                                        }
                                    ],
                                    "command_results": [
                                        {
                                            "command": "echo verify",
                                            "status": "failed",
                                            "return_code": 1,
                                            "stdout": "",
                                            "stderr": "second failure",
                                        }
                                    ],
                                    "error": "second failure",
                                    "summary": {"total": 1, "passed": 0, "failed": 1},
                                    "reason": "validation_failed",
                                },
                            ],
                        ):
                            result = adapter.execute(
                                {
                                    "prompt": "test prompt",
                                    "repo_path": repo_dir,
                                    "work_dir": work_dir,
                                    "validation_commands": ["echo verify"],
                                }
                            )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["verify"]["status"], "failed")
        self.assertEqual(result["verify"]["reason"], "validation_failed")
        self.assertEqual(result["verify"]["error"], "second failure")
        self.assertIn("commands", result["verify"])
        self.assertIn("command_results", result["verify"])
        self.assertIn("summary", result["verify"])
        self.assertEqual(result["verify"]["summary"], {"total": 1, "passed": 0, "failed": 1})
        self.assertEqual(len(result["verify"]["command_results"]), result["verify"]["summary"]["total"])
        self.assertEqual(len(result["verify"]["command_results"]), 1)
        self.assertEqual(result["verify"]["command_results"][0]["status"], "failed")
        self.assertEqual(result["attempt_count"], 2)
        self.assertEqual(
            result["retry"],
            {"attempted": True, "trigger": "verify_failed", "outcome": "retry_failed"},
        )
        self.assertEqual(result["result_interpretation"], "completed_verified_failed_after_retry")
        self.assertEqual(result["review_recommendation"], "review_recommended_after_retry_failure")
        self._assert_review_handoff_summary_consistency(result)
        self._assert_reviewer_handoff_consistency(result)

    def test_result_interpretation_completed_verify_failed_without_retry(self) -> None:
        interpretation = _derive_result_interpretation(
            execution_status="completed",
            verify_result={"status": "failed"},
            retry={"attempted": False, "trigger": "not_applicable", "outcome": "not_attempted"},
        )

        self.assertEqual(interpretation, "completed_verified_failed")
        self.assertEqual(_derive_review_recommendation(interpretation), "review_recommended")

    def test_review_handoff_summary_completed_verify_failed_without_retry(self) -> None:
        summary = _build_review_handoff_summary(
            final_status="completed",
            final_verify_status="failed",
            final_verify_reason="validation_failed",
            retry_attempted=False,
            retry_outcome="not_attempted",
            result_interpretation="completed_verified_failed",
            review_recommendation="review_recommended",
        )

        self.assertEqual(
            summary,
            {
                "final_status": "completed",
                "final_verify_status": "failed",
                "final_verify_reason": "validation_failed",
                "retry_attempted": False,
                "retry_outcome": "not_attempted",
                "result_interpretation": "completed_verified_failed",
                "review_recommendation": "review_recommended",
            },
        )

    def test_review_handoff_summary_is_direct_scalar_mirror_without_coercion(self) -> None:
        interpretation_marker = object()
        summary = _build_review_handoff_summary(
            final_status=123,  # type: ignore[arg-type]
            final_verify_status=456,  # type: ignore[arg-type]
            final_verify_reason=None,  # type: ignore[arg-type]
            retry_attempted="yes",  # type: ignore[arg-type]
            retry_outcome=789,  # type: ignore[arg-type]
            result_interpretation=interpretation_marker,  # type: ignore[arg-type]
            review_recommendation=[],
        )

        self.assertEqual(summary["final_status"], 123)
        self.assertEqual(summary["final_verify_status"], 456)
        self.assertIsNone(summary["final_verify_reason"])
        self.assertEqual(summary["retry_attempted"], "yes")
        self.assertEqual(summary["retry_outcome"], 789)
        self.assertIs(summary["result_interpretation"], interpretation_marker)
        self.assertEqual(summary["review_recommendation"], [])

    def test_reviewer_handoff_completed_verify_failed_without_retry(self) -> None:
        summary = _build_review_handoff_summary(
            final_status="completed",
            final_verify_status="failed",
            final_verify_reason="validation_failed",
            retry_attempted=False,
            retry_outcome="not_attempted",
            result_interpretation="completed_verified_failed",
            review_recommendation="review_recommended",
        )
        handoff = _build_reviewer_handoff(
            review_handoff_summary=summary,
            final_status="completed",
            attempt_count=1,
            return_code=1,
            verify_result={"status": "failed", "reason": "validation_failed"},
        )

        self.assertEqual(
            handoff,
            {
                "summary": summary,
                "execution": {"status": "completed", "attempt_count": 1, "return_code": 1},
                "validation": {"verify_status": "failed", "verify_reason": "validation_failed"},
            },
        )

    def test_stub_adapters_do_not_execute(self) -> None:
        with self.assertRaises(NotImplementedError):
            ChatgptTasksAdapter().execute({})
        with self.assertRaises(NotImplementedError):
            LocalLlmAdapter().execute({})


class OrchestratorExecutionSemanticsTests(unittest.TestCase):
    def _fake_evaluation_result(self, job_id: str) -> dict:
        return {
            "job_id": job_id,
            "classification": {
                "declared_category": "feature",
                "observed_category": "feature",
            },
            "rubric": {"merge_eligible": False},
            "merge_gate": {"passed": False},
            "assumptions": {"fallbacks_used": []},
        }

    def _candidate_evaluation_result(self, job_id: str) -> dict:
        return {
            "job_id": job_id,
            "classification": {
                "declared_category": "docs_only",
                "observed_category": "docs_only",
            },
            "rubric": {"merge_eligible": True},
            "merge_gate": {"passed": True, "auto_merge_allowed": True},
            "assumptions": {"fallbacks_used": []},
        }

    def _single_output_dir(self, output_root: str) -> Path:
        output_dirs = list(Path(output_root).iterdir())
        self.assertEqual(len(output_dirs), 1)
        return output_dirs[0]

    def _read_single_result(self, output_root: str) -> dict:
        output_dir = self._single_output_dir(output_root)
        return json.loads((output_dir / "result.json").read_text(encoding="utf-8"))

    def _read_single_request(self, output_root: str) -> dict:
        output_dir = self._single_output_dir(output_root)
        return json.loads((output_dir / "request.json").read_text(encoding="utf-8"))

    def _run_git(self, repo_dir: str, args: list[str]) -> str:
        proc = subprocess.run(
            ["git", "-C", repo_dir, *args],
            check=True,
            text=True,
            capture_output=True,
        )
        return proc.stdout.strip()

    def _git_commit(self, repo_dir: str, message: str) -> None:
        self._run_git(
            repo_dir,
            [
                "-c",
                "user.name=Test User",
                "-c",
                "user.email=test@example.com",
                "commit",
                "-m",
                message,
            ],
        )

    def _init_mergeable_repo(self, repo_dir: str) -> dict[str, str]:
        self._run_git(repo_dir, ["init"])
        self._run_git(repo_dir, ["checkout", "-b", "main"])
        (Path(repo_dir) / "README.md").write_text("base\n", encoding="utf-8")
        self._run_git(repo_dir, ["add", "README.md"])
        self._git_commit(repo_dir, "base")
        base_sha = self._run_git(repo_dir, ["rev-parse", "HEAD"])

        self._run_git(repo_dir, ["checkout", "-b", "feature"])
        (Path(repo_dir) / "feature.txt").write_text("feature\n", encoding="utf-8")
        self._run_git(repo_dir, ["add", "feature.txt"])
        self._git_commit(repo_dir, "feature")
        source_sha = self._run_git(repo_dir, ["rev-parse", "HEAD"])

        self._run_git(repo_dir, ["checkout", "main"])
        return {
            "target_ref": "refs/heads/main",
            "base_sha": base_sha,
            "source_sha": source_sha,
        }

    def _init_repo_with_merge_commit(self, repo_dir: str) -> dict[str, str]:
        identity = self._init_mergeable_repo(repo_dir)
        self._run_git(
            repo_dir,
            [
                "-c",
                "user.name=Test User",
                "-c",
                "user.email=test@example.com",
                "merge",
                "--no-ff",
                "--no-edit",
                identity["source_sha"],
            ],
        )
        post_merge_sha = self._run_git(repo_dir, ["rev-parse", "HEAD"])
        return {
            "target_ref": identity["target_ref"],
            "pre_merge_sha": identity["base_sha"],
            "post_merge_sha": post_merge_sha,
            "source_sha": identity["source_sha"],
            "base_sha": identity["base_sha"],
        }

    def test_accepted_status_is_kept_when_execution_fails(self) -> None:
        with tempfile.TemporaryDirectory() as output_root:
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "failed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": "simulated execution failure",
                },
            ):
                with mock.patch(
                    "sys.argv",
                    [
                        "main.py",
                        "--repo",
                        "codex-local-runner",
                        "--task-type",
                        "orchestration",
                        "--goal",
                        "verify semantics",
                        "--provider",
                        "codex_cli",
                        "--output-root",
                        output_root,
                    ],
                ):
                    rc = orchestrator_main.main()

            result = self._read_single_result(output_root)
            output_dir = self._single_output_dir(output_root)
            rubric = json.loads((output_dir / "rubric.json").read_text(encoding="utf-8"))
            merge_gate = json.loads((output_dir / "merge_gate.json").read_text(encoding="utf-8"))

        self.assertEqual(rc, 0)
        self.assertEqual(result["status"], "accepted")
        self.assertEqual(result["execution"]["status"], "failed")
        self.assertEqual(
            set(result["persistence"].keys()),
            {"evaluation_artifacts", "ledger", "execution_target", "merge_execution", "merge_receipt"},
        )
        self.assertIn("merge_eligible", rubric)
        self.assertIn("required_tests_declared", rubric)
        self.assertIn("passed", merge_gate)
        self.assertIn("auto_merge_allowed", merge_gate)

    def test_acceptance_failure_sets_execution_not_started(self) -> None:
        with tempfile.TemporaryDirectory() as output_root:
            with mock.patch(
                "sys.argv",
                [
                    "main.py",
                    "--repo",
                    "codex-local-runner",
                    "--task-type",
                    "orchestration",
                    "--goal",
                    "verify semantics",
                    "--provider",
                    "unknown_provider",
                    "--output-root",
                    output_root,
                ],
            ):
                rc = orchestrator_main.main()

            result = self._read_single_result(output_root)
            output_dir = self._single_output_dir(output_root)

        self.assertEqual(rc, 1)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["execution"]["status"], "not_started")
        self.assertEqual(
            result["persistence"],
            {
                "evaluation_artifacts": "skipped",
                "ledger": "skipped",
                "execution_target": "skipped",
                "merge_execution": "skipped",
                "merge_receipt": "skipped",
            },
        )
        self.assertFalse((output_dir / "rubric.json").exists())
        self.assertFalse((output_dir / "merge_gate.json").exists())

    def test_validation_commands_are_routed_to_execution_payload(self) -> None:
        with tempfile.TemporaryDirectory() as output_root:
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "completed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": None,
                    "return_code": 0,
                    "attempt_count": 1,
                    "retry": {
                        "attempted": False,
                        "trigger": "not_applicable",
                        "outcome": "not_attempted",
                    },
                    "verify": {
                        "status": "not_run",
                        "success": True,
                        "commands": [],
                        "error": "",
                        "reason": "validation_not_run_execution_status_unknown",
                    },
                    "result_interpretation": "completed_verified_passed",
                    "review_recommendation": "no_review_needed",
                    "review_handoff_summary": {
                        "final_status": "completed",
                        "final_verify_status": "not_run",
                        "final_verify_reason": "validation_not_run_execution_status_unknown",
                        "retry_attempted": False,
                        "retry_outcome": "not_attempted",
                        "result_interpretation": "completed_verified_passed",
                        "review_recommendation": "no_review_needed",
                    },
                    "reviewer_handoff": {
                        "summary": {
                            "final_status": "completed",
                            "final_verify_status": "not_run",
                            "final_verify_reason": "validation_not_run_execution_status_unknown",
                            "retry_attempted": False,
                            "retry_outcome": "not_attempted",
                            "result_interpretation": "completed_verified_passed",
                            "review_recommendation": "no_review_needed",
                        },
                        "execution": {"status": "completed", "attempt_count": 1, "return_code": 0},
                        "validation": {
                            "verify_status": "not_run",
                            "verify_reason": "validation_not_run_execution_status_unknown",
                        },
                    },
                },
            ) as execute_mock:
                with mock.patch(
                    "sys.argv",
                    [
                        "main.py",
                        "--repo",
                        "codex-local-runner",
                        "--task-type",
                        "orchestration",
                        "--goal",
                        "verify semantics",
                        "--provider",
                        "codex_cli",
                        "--output-root",
                        output_root,
                        "--validation-command",
                        "echo one",
                        "--validation-command",
                        "echo two",
                    ],
                ):
                    rc = orchestrator_main.main()

            request_payload = self._read_single_request(output_root)
            result_payload = self._read_single_result(output_root)
            output_dir = self._single_output_dir(output_root)
            rubric = json.loads((output_dir / "rubric.json").read_text(encoding="utf-8"))
            merge_gate = json.loads((output_dir / "merge_gate.json").read_text(encoding="utf-8"))

        self.assertEqual(rc, 0)
        self.assertEqual(result_payload["status"], "accepted")
        execute_mock.assert_called_once()
        self.assertEqual(
            execute_mock.call_args.args[0]["validation_commands"],
            ["echo one", "echo two"],
        )
        self.assertEqual(request_payload["validation_commands"], ["echo one", "echo two"])
        self.assertNotIn("validation_command", request_payload)
        self.assertTrue(rubric["required_tests_declared"])
        self.assertFalse(rubric["required_tests_executed"])
        self.assertFalse(rubric["required_tests_passed"])
        self.assertFalse(rubric["ci_required_checks_green"])
        self.assertFalse(rubric["rollback_metadata_recorded"])
        self.assertIn("passed", merge_gate)
        self.assertIn("auto_merge_allowed", merge_gate)
        self.assertEqual(
            result_payload["execution"]["result_interpretation"],
            "completed_verified_passed",
        )
        self.assertEqual(result_payload["execution"]["review_recommendation"], "no_review_needed")
        self.assertEqual(result_payload["execution"]["review_handoff_summary"]["final_status"], "completed")
        self.assertEqual(result_payload["execution"]["reviewer_handoff"]["execution"]["status"], "completed")
        self.assertEqual(
            set(result_payload["persistence"].keys()),
            {"evaluation_artifacts", "ledger", "execution_target", "merge_execution", "merge_receipt"},
        )

    def test_persistence_written_when_accepted_and_persistence_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as output_root:
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "completed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": None,
                },
            ):
                with mock.patch(
                    "orchestrator.main.evaluate_job_directory",
                    return_value=self._fake_evaluation_result("job-persist-ok"),
                ):
                    with mock.patch(
                        "orchestrator.main.persist_evaluation_artifacts",
                        return_value=("rubric.json", "merge_gate.json"),
                    ):
                        with mock.patch("orchestrator.main.record_job_evaluation") as record_mock:
                            with mock.patch(
                                "sys.argv",
                                [
                                    "main.py",
                                    "--repo",
                                    "codex-local-runner",
                                    "--task-type",
                                    "orchestration",
                                    "--goal",
                                    "persistence observability",
                                    "--provider",
                                    "codex_cli",
                                    "--output-root",
                                    output_root,
                                ],
                            ):
                                rc = orchestrator_main.main()

            result_payload = self._read_single_result(output_root)

        self.assertEqual(rc, 0)
        self.assertEqual(result_payload["status"], "accepted")
        self.assertEqual(
            result_payload["persistence"],
            {
                "evaluation_artifacts": "written",
                "ledger": "written",
                "execution_target": "skipped",
                "merge_execution": "skipped",
                "merge_receipt": "skipped",
            },
        )
        record_mock.assert_called_once()

    def test_persistence_evaluation_failure_remains_non_fatal(self) -> None:
        with tempfile.TemporaryDirectory() as output_root:
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "completed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": None,
                },
            ):
                with mock.patch(
                    "orchestrator.main.evaluate_job_directory",
                    return_value=self._fake_evaluation_result("job-persist-fail"),
                ):
                    with mock.patch(
                        "orchestrator.main.persist_evaluation_artifacts",
                        side_effect=RuntimeError("persist failed"),
                    ):
                        with mock.patch("orchestrator.main.record_job_evaluation"):
                            with mock.patch(
                                "sys.argv",
                                [
                                    "main.py",
                                    "--repo",
                                    "codex-local-runner",
                                    "--task-type",
                                    "orchestration",
                                    "--goal",
                                    "persistence observability",
                                    "--provider",
                                    "codex_cli",
                                    "--output-root",
                                    output_root,
                                ],
                            ):
                                rc = orchestrator_main.main()

            result_payload = self._read_single_result(output_root)

        self.assertEqual(rc, 0)
        self.assertEqual(result_payload["status"], "accepted")
        self.assertEqual(
            result_payload["persistence"],
            {
                "evaluation_artifacts": "failed",
                "ledger": "written",
                "execution_target": "skipped",
                "merge_execution": "skipped",
                "merge_receipt": "skipped",
            },
        )

    def test_accepted_flow_records_ledger_row(self) -> None:
        with tempfile.TemporaryDirectory() as output_root:
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "failed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": "simulated execution failure",
                },
            ):
                with mock.patch("orchestrator.main.record_job_evaluation") as record_mock:
                    with mock.patch(
                        "sys.argv",
                        [
                            "main.py",
                            "--repo",
                            "codex-local-runner",
                            "--task-type",
                            "orchestration",
                            "--goal",
                            "record ledger",
                            "--provider",
                            "codex_cli",
                            "--output-root",
                            output_root,
                        ],
                    ):
                        rc = orchestrator_main.main()

            result_payload = self._read_single_result(output_root)
            output_dir = self._single_output_dir(output_root)

        self.assertEqual(rc, 0)
        self.assertEqual(result_payload["status"], "accepted")
        record_mock.assert_called_once()
        kwargs = record_mock.call_args.kwargs
        self.assertEqual(kwargs["accepted_status"], "accepted")
        self.assertEqual(kwargs["request_path"], str(output_dir / "request.json"))
        self.assertEqual(kwargs["result_path"], str(output_dir / "result.json"))
        self.assertEqual(kwargs["rubric_path"], str(output_dir / "rubric.json"))
        self.assertEqual(kwargs["merge_gate_path"], str(output_dir / "merge_gate.json"))
        self.assertIsNone(kwargs["classification_path"])

    def test_acceptance_failure_skips_ledger_recording(self) -> None:
        with tempfile.TemporaryDirectory() as output_root:
            with mock.patch("orchestrator.main.record_job_evaluation") as record_mock:
                with mock.patch(
                    "sys.argv",
                    [
                        "main.py",
                        "--repo",
                        "codex-local-runner",
                        "--task-type",
                        "orchestration",
                        "--goal",
                        "record ledger",
                        "--provider",
                        "unknown_provider",
                        "--output-root",
                        output_root,
                    ],
                ):
                    rc = orchestrator_main.main()

            result = self._read_single_result(output_root)
            output_dir = self._single_output_dir(output_root)

        self.assertEqual(rc, 1)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["execution"]["status"], "not_started")
        record_mock.assert_not_called()
        self.assertFalse((output_dir / "rubric.json").exists())
        self.assertFalse((output_dir / "merge_gate.json").exists())

    def test_ledger_write_failure_does_not_flip_accepted_status(self) -> None:
        with tempfile.TemporaryDirectory() as output_root:
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "completed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": None,
                },
            ):
                with mock.patch(
                    "orchestrator.main.evaluate_job_directory",
                    return_value=self._fake_evaluation_result("job-ledger-fail"),
                ):
                    with mock.patch(
                        "orchestrator.main.persist_evaluation_artifacts",
                        return_value=("rubric.json", "merge_gate.json"),
                    ):
                        with mock.patch(
                            "orchestrator.main.record_job_evaluation",
                            side_effect=RuntimeError("ledger write failed"),
                        ):
                            with mock.patch(
                                "sys.argv",
                                [
                                    "main.py",
                                    "--repo",
                                    "codex-local-runner",
                                    "--task-type",
                                    "orchestration",
                                    "--goal",
                                    "record ledger",
                                    "--provider",
                                    "codex_cli",
                                    "--output-root",
                                    output_root,
                                ],
                            ):
                                rc = orchestrator_main.main()

            result_payload = self._read_single_result(output_root)
        self.assertEqual(rc, 0)
        self.assertEqual(result_payload["status"], "accepted")
        self.assertEqual(result_payload["execution"]["status"], "completed")
        self.assertEqual(
            result_payload["persistence"],
            {
                "evaluation_artifacts": "written",
                "ledger": "failed",
                "execution_target": "skipped",
                "merge_execution": "skipped",
                "merge_receipt": "skipped",
            },
        )

    def test_execution_target_capture_written_for_accepted_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as output_root:
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "completed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": None,
                },
            ):
                with mock.patch(
                    "orchestrator.main.evaluate_job_directory",
                    return_value=self._candidate_evaluation_result("job-candidate-written"),
                ):
                    with mock.patch(
                        "orchestrator.main.persist_evaluation_artifacts",
                        return_value=("rubric.json", "merge_gate.json"),
                    ):
                        with mock.patch("orchestrator.main.record_job_evaluation"):
                            with mock.patch("orchestrator.main.record_execution_target") as capture_mock:
                                with mock.patch(
                                    "sys.argv",
                                    [
                                        "main.py",
                                        "--repo",
                                        "codex-local-runner",
                                        "--task-type",
                                        "orchestration",
                                        "--goal",
                                        "capture execution target",
                                        "--provider",
                                        "codex_cli",
                                        "--output-root",
                                        output_root,
                                        "--target-ref",
                                        "refs/heads/main",
                                        "--source-sha",
                                        "a" * 40,
                                        "--base-sha",
                                        "b" * 40,
                                    ],
                                ):
                                    rc = orchestrator_main.main()

            result_payload = self._read_single_result(output_root)

        self.assertEqual(rc, 0)
        self.assertEqual(result_payload["status"], "accepted")
        self.assertEqual(
            result_payload["persistence"],
            {
                "evaluation_artifacts": "written",
                "ledger": "written",
                "execution_target": "written",
                "merge_execution": "skipped",
                "merge_receipt": "skipped",
            },
        )
        capture_mock.assert_called_once()
        self.assertEqual(capture_mock.call_args.kwargs["target_ref"], "refs/heads/main")
        self.assertEqual(capture_mock.call_args.kwargs["source_sha"], "a" * 40)
        self.assertEqual(capture_mock.call_args.kwargs["base_sha"], "b" * 40)

    def test_execution_target_capture_skipped_when_identity_prereqs_missing(self) -> None:
        with tempfile.TemporaryDirectory() as output_root:
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "completed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": None,
                },
            ):
                with mock.patch(
                    "orchestrator.main.evaluate_job_directory",
                    return_value=self._candidate_evaluation_result("job-candidate-skipped"),
                ):
                    with mock.patch(
                        "orchestrator.main.persist_evaluation_artifacts",
                        return_value=("rubric.json", "merge_gate.json"),
                    ):
                        with mock.patch("orchestrator.main.record_job_evaluation"):
                            with mock.patch("orchestrator.main.record_execution_target") as capture_mock:
                                with mock.patch(
                                    "sys.argv",
                                    [
                                        "main.py",
                                        "--repo",
                                        "codex-local-runner",
                                        "--task-type",
                                        "orchestration",
                                        "--goal",
                                        "capture execution target",
                                        "--provider",
                                        "codex_cli",
                                        "--output-root",
                                        output_root,
                                    ],
                                ):
                                    rc = orchestrator_main.main()

            result_payload = self._read_single_result(output_root)

        self.assertEqual(rc, 0)
        self.assertEqual(result_payload["status"], "accepted")
        self.assertEqual(
            result_payload["persistence"],
            {
                "evaluation_artifacts": "written",
                "ledger": "written",
                "execution_target": "skipped",
                "merge_execution": "skipped",
                "merge_receipt": "skipped",
            },
        )
        capture_mock.assert_not_called()

    def test_execution_target_capture_failure_remains_non_fatal(self) -> None:
        with tempfile.TemporaryDirectory() as output_root:
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "completed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": None,
                },
            ):
                with mock.patch(
                    "orchestrator.main.evaluate_job_directory",
                    return_value=self._candidate_evaluation_result("job-candidate-failed"),
                ):
                    with mock.patch(
                        "orchestrator.main.persist_evaluation_artifacts",
                        return_value=("rubric.json", "merge_gate.json"),
                    ):
                        with mock.patch("orchestrator.main.record_job_evaluation"):
                            with mock.patch(
                                "orchestrator.main.record_execution_target",
                                side_effect=RuntimeError("capture failed"),
                            ):
                                with mock.patch(
                                    "sys.argv",
                                    [
                                        "main.py",
                                        "--repo",
                                        "codex-local-runner",
                                        "--task-type",
                                        "orchestration",
                                        "--goal",
                                        "capture execution target",
                                        "--provider",
                                        "codex_cli",
                                        "--output-root",
                                        output_root,
                                        "--target-ref",
                                        "refs/heads/main",
                                        "--source-sha",
                                        "a" * 40,
                                        "--base-sha",
                                        "b" * 40,
                                    ],
                                ):
                                    rc = orchestrator_main.main()

            result_payload = self._read_single_result(output_root)

        self.assertEqual(rc, 0)
        self.assertEqual(result_payload["status"], "accepted")
        self.assertEqual(result_payload["execution"]["status"], "completed")
        self.assertEqual(
            result_payload["persistence"],
            {
                "evaluation_artifacts": "written",
                "ledger": "written",
                "execution_target": "failed",
                "merge_execution": "skipped",
                "merge_receipt": "skipped",
            },
        )

    def test_merge_receipt_written_when_attempt_signal_is_present(self) -> None:
        with tempfile.TemporaryDirectory() as output_root:
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "completed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": None,
                    "merge_attempt": {
                        "status": "failed",
                        "attempted_at": "2026-01-01T00:00:02+00:00",
                        "result_sha": None,
                        "error": "simulated conflict",
                    },
                },
            ):
                with mock.patch(
                    "orchestrator.main.evaluate_job_directory",
                    return_value=self._candidate_evaluation_result("job-merge-receipt-written"),
                ):
                    with mock.patch(
                        "orchestrator.main.persist_evaluation_artifacts",
                        return_value=("rubric.json", "merge_gate.json"),
                    ):
                        with mock.patch("orchestrator.main.record_job_evaluation"):
                            with mock.patch("orchestrator.main.record_execution_target"):
                                with mock.patch(
                                    "orchestrator.main.record_merge_attempt_receipt"
                                ) as receipt_mock:
                                    with mock.patch(
                                        "sys.argv",
                                        [
                                            "main.py",
                                            "--repo",
                                            "codex-local-runner",
                                            "--task-type",
                                            "orchestration",
                                            "--goal",
                                            "record merge receipt",
                                            "--provider",
                                            "codex_cli",
                                            "--output-root",
                                            output_root,
                                            "--target-ref",
                                            "refs/heads/main",
                                            "--source-sha",
                                            "a" * 40,
                                            "--base-sha",
                                            "b" * 40,
                                        ],
                                    ):
                                        rc = orchestrator_main.main()

            result_payload = self._read_single_result(output_root)

        self.assertEqual(rc, 0)
        self.assertEqual(result_payload["status"], "accepted")
        self.assertEqual(
            result_payload["persistence"],
            {
                "evaluation_artifacts": "written",
                "ledger": "written",
                "execution_target": "written",
                "merge_execution": "skipped",
                "merge_receipt": "written",
            },
        )
        receipt_mock.assert_called_once()
        self.assertEqual(receipt_mock.call_args.kwargs["merge_attempt_status"], "failed")
        self.assertEqual(
            receipt_mock.call_args.kwargs["merge_attempted_at"],
            "2026-01-01T00:00:02+00:00",
        )

    def test_merge_receipt_skipped_when_no_trustworthy_attempt_signal(self) -> None:
        with tempfile.TemporaryDirectory() as output_root:
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "completed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": None,
                },
            ):
                with mock.patch(
                    "orchestrator.main.evaluate_job_directory",
                    return_value=self._candidate_evaluation_result("job-merge-receipt-skipped"),
                ):
                    with mock.patch(
                        "orchestrator.main.persist_evaluation_artifacts",
                        return_value=("rubric.json", "merge_gate.json"),
                    ):
                        with mock.patch("orchestrator.main.record_job_evaluation"):
                            with mock.patch("orchestrator.main.record_execution_target"):
                                with mock.patch(
                                    "orchestrator.main.record_merge_attempt_receipt"
                                ) as receipt_mock:
                                    with mock.patch(
                                        "sys.argv",
                                        [
                                            "main.py",
                                            "--repo",
                                            "codex-local-runner",
                                            "--task-type",
                                            "orchestration",
                                            "--goal",
                                            "record merge receipt",
                                            "--provider",
                                            "codex_cli",
                                            "--output-root",
                                            output_root,
                                            "--target-ref",
                                            "refs/heads/main",
                                            "--source-sha",
                                            "a" * 40,
                                            "--base-sha",
                                            "b" * 40,
                                        ],
                                    ):
                                        rc = orchestrator_main.main()

            result_payload = self._read_single_result(output_root)

        self.assertEqual(rc, 0)
        self.assertEqual(result_payload["status"], "accepted")
        self.assertEqual(
            result_payload["persistence"],
            {
                "evaluation_artifacts": "written",
                "ledger": "written",
                "execution_target": "written",
                "merge_execution": "skipped",
                "merge_receipt": "skipped",
            },
        )
        receipt_mock.assert_not_called()

    def test_merge_receipt_skips_when_signal_present_but_linkage_identity_missing(self) -> None:
        with tempfile.TemporaryDirectory() as output_root:
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "completed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": None,
                    "merge_attempt": {
                        "status": "attempted",
                        "attempted_at": "2026-01-01T00:00:02+00:00",
                        "result_sha": None,
                        "error": None,
                    },
                },
            ):
                with mock.patch(
                    "orchestrator.main.evaluate_job_directory",
                    return_value=self._candidate_evaluation_result("job-merge-receipt-no-linkage"),
                ):
                    with mock.patch(
                        "orchestrator.main.persist_evaluation_artifacts",
                        return_value=("rubric.json", "merge_gate.json"),
                    ):
                        with mock.patch("orchestrator.main.record_job_evaluation"):
                            with mock.patch("orchestrator.main.record_execution_target") as target_mock:
                                with mock.patch(
                                    "orchestrator.main.record_merge_attempt_receipt"
                                ) as receipt_mock:
                                    with mock.patch(
                                        "sys.argv",
                                        [
                                            "main.py",
                                            "--repo",
                                            "codex-local-runner",
                                            "--task-type",
                                            "orchestration",
                                            "--goal",
                                            "record merge receipt",
                                            "--provider",
                                            "codex_cli",
                                            "--output-root",
                                            output_root,
                                        ],
                                    ):
                                        rc = orchestrator_main.main()

            result_payload = self._read_single_result(output_root)

        self.assertEqual(rc, 0)
        self.assertEqual(result_payload["status"], "accepted")
        self.assertEqual(
            result_payload["persistence"],
            {
                "evaluation_artifacts": "written",
                "ledger": "written",
                "execution_target": "skipped",
                "merge_execution": "skipped",
                "merge_receipt": "skipped",
            },
        )
        target_mock.assert_not_called()
        receipt_mock.assert_not_called()

    def test_merge_receipt_write_failure_remains_non_fatal(self) -> None:
        with tempfile.TemporaryDirectory() as output_root:
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "completed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": None,
                    "merge_attempt": {
                        "status": "failed",
                        "attempted_at": "2026-01-01T00:00:02+00:00",
                        "result_sha": None,
                        "error": "simulated conflict",
                    },
                },
            ):
                with mock.patch(
                    "orchestrator.main.evaluate_job_directory",
                    return_value=self._candidate_evaluation_result("job-merge-receipt-failed"),
                ):
                    with mock.patch(
                        "orchestrator.main.persist_evaluation_artifacts",
                        return_value=("rubric.json", "merge_gate.json"),
                    ):
                        with mock.patch("orchestrator.main.record_job_evaluation"):
                            with mock.patch("orchestrator.main.record_execution_target"):
                                with mock.patch(
                                    "orchestrator.main.record_merge_attempt_receipt",
                                    side_effect=RuntimeError("receipt write failed"),
                                ):
                                    with mock.patch(
                                        "sys.argv",
                                        [
                                            "main.py",
                                            "--repo",
                                            "codex-local-runner",
                                            "--task-type",
                                            "orchestration",
                                            "--goal",
                                            "record merge receipt",
                                            "--provider",
                                            "codex_cli",
                                            "--output-root",
                                            output_root,
                                            "--target-ref",
                                            "refs/heads/main",
                                            "--source-sha",
                                            "a" * 40,
                                            "--base-sha",
                                            "b" * 40,
                                        ],
                                    ):
                                        rc = orchestrator_main.main()

            result_payload = self._read_single_result(output_root)

        self.assertEqual(rc, 0)
        self.assertEqual(result_payload["status"], "accepted")
        self.assertEqual(result_payload["execution"]["status"], "completed")
        self.assertEqual(
            result_payload["persistence"],
            {
                "evaluation_artifacts": "written",
                "ledger": "written",
                "execution_target": "written",
                "merge_execution": "skipped",
                "merge_receipt": "failed",
            },
        )

    def test_constrained_merge_execution_succeeds_with_persisted_target_identity(self) -> None:
        with tempfile.TemporaryDirectory() as output_root, tempfile.TemporaryDirectory() as repo_dir:
            merge_identity = self._init_mergeable_repo(repo_dir)
            candidate_key = "c" * 64
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "completed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": None,
                },
            ):
                with mock.patch(
                    "orchestrator.main.evaluate_job_directory",
                    return_value=self._candidate_evaluation_result("job-merge-exec-success"),
                ):
                    with mock.patch(
                        "orchestrator.main.persist_evaluation_artifacts",
                        return_value=("rubric.json", "merge_gate.json"),
                    ):
                        with mock.patch("orchestrator.main.record_job_evaluation"):
                            with mock.patch("orchestrator.main.record_execution_target"):
                                with mock.patch(
                                    "orchestrator.main.get_execution_target_by_identity",
                                    return_value={"candidate_idempotency_key": candidate_key},
                                ):
                                    with mock.patch(
                                        "orchestrator.main.get_merge_execution_by_candidate_idempotency_key",
                                        return_value=None,
                                    ):
                                        with mock.patch(
                                            "orchestrator.main.record_merge_execution_outcome"
                                        ) as merge_state_mock:
                                            with mock.patch(
                                                "orchestrator.main.record_merge_attempt_receipt"
                                            ) as receipt_mock:
                                                with mock.patch(
                                                    "orchestrator.main.record_rollback_traceability_for_candidate",
                                                    return_value={
                                                        "rollback_trace_id": "rt-1",
                                                        "rollback_eligible": 1,
                                                        "ineligible_reason": None,
                                                    },
                                                ) as rollback_trace_mock:
                                                    with mock.patch(
                                                        "sys.argv",
                                                        [
                                                            "main.py",
                                                            "--repo",
                                                            "codex-local-runner",
                                                            "--task-type",
                                                            "orchestration",
                                                            "--goal",
                                                            "execute constrained merge",
                                                            "--provider",
                                                            "codex_cli",
                                                            "--output-root",
                                                            output_root,
                                                            "--execution-repo-path",
                                                            repo_dir,
                                                            "--target-ref",
                                                            merge_identity["target_ref"],
                                                            "--source-sha",
                                                            merge_identity["source_sha"],
                                                            "--base-sha",
                                                            merge_identity["base_sha"],
                                                            "--execute-merge",
                                                        ],
                                                    ):
                                                        rc = orchestrator_main.main()

            result_payload = self._read_single_result(output_root)
            post_sha = self._run_git(repo_dir, ["rev-parse", "HEAD"])

        merge_execution = result_payload["execution"]["merge_execution"]
        self.assertEqual(rc, 0)
        self.assertEqual(result_payload["status"], "accepted")
        self.assertEqual(merge_execution["status"], "succeeded")
        self.assertTrue(merge_execution["attempted"])
        self.assertEqual(merge_execution["candidate_idempotency_key"], candidate_key)
        self.assertEqual(merge_execution["pre_merge_sha"], merge_identity["base_sha"])
        self.assertEqual(merge_execution["post_merge_sha"], post_sha)
        self.assertEqual(merge_execution["merge_result_sha"], post_sha)
        self.assertTrue(merge_execution["rollback_trace"]["recorded"])
        self.assertTrue(merge_execution["rollback_trace"]["eligible"])
        self.assertEqual(merge_execution["rollback_trace"]["rollback_trace_id"], "rt-1")
        self.assertEqual(
            result_payload["persistence"],
            {
                "evaluation_artifacts": "written",
                "ledger": "written",
                "execution_target": "written",
                "merge_execution": "written",
                "merge_receipt": "written",
                "rollback_trace": "written",
            },
        )
        merge_state_mock.assert_called_once()
        self.assertEqual(merge_state_mock.call_args.kwargs["pre_merge_sha"], merge_identity["base_sha"])
        self.assertEqual(merge_state_mock.call_args.kwargs["post_merge_sha"], post_sha)
        receipt_mock.assert_called_once()
        self.assertEqual(receipt_mock.call_args.kwargs["merge_attempt_status"], "succeeded")
        rollback_trace_mock.assert_called_once()

    def test_constrained_merge_execution_skips_when_persisted_identity_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as output_root, tempfile.TemporaryDirectory() as repo_dir:
            merge_identity = self._init_mergeable_repo(repo_dir)
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "completed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": None,
                },
            ):
                with mock.patch(
                    "orchestrator.main.evaluate_job_directory",
                    return_value=self._candidate_evaluation_result("job-merge-exec-skip-missing"),
                ):
                    with mock.patch(
                        "orchestrator.main.persist_evaluation_artifacts",
                        return_value=("rubric.json", "merge_gate.json"),
                    ):
                        with mock.patch("orchestrator.main.record_job_evaluation"):
                            with mock.patch("orchestrator.main.record_execution_target"):
                                with mock.patch(
                                    "orchestrator.main.get_execution_target_by_identity",
                                    return_value=None,
                                ):
                                    with mock.patch(
                                        "orchestrator.main.execute_constrained_merge"
                                    ) as execute_merge_mock:
                                        with mock.patch(
                                            "sys.argv",
                                            [
                                                "main.py",
                                                "--repo",
                                                "codex-local-runner",
                                                "--task-type",
                                                "orchestration",
                                                "--goal",
                                                "execute constrained merge",
                                                "--provider",
                                                "codex_cli",
                                                "--output-root",
                                                output_root,
                                                "--execution-repo-path",
                                                repo_dir,
                                                "--target-ref",
                                                merge_identity["target_ref"],
                                                "--source-sha",
                                                merge_identity["source_sha"],
                                                "--base-sha",
                                                merge_identity["base_sha"],
                                                "--execute-merge",
                                            ],
                                        ):
                                            rc = orchestrator_main.main()

            result_payload = self._read_single_result(output_root)

        self.assertEqual(rc, 0)
        self.assertEqual(result_payload["status"], "accepted")
        self.assertEqual(result_payload["execution"]["merge_execution"]["status"], "skipped")
        self.assertEqual(
            result_payload["execution"]["merge_execution"]["error"],
            "execution_target_not_persisted_or_mismatched",
        )
        self.assertEqual(
            result_payload["persistence"],
            {
                "evaluation_artifacts": "written",
                "ledger": "written",
                "execution_target": "written",
                "merge_execution": "skipped",
                "merge_receipt": "skipped",
                "rollback_trace": "skipped",
            },
        )
        execute_merge_mock.assert_not_called()

    def test_constrained_merge_execution_is_protected_from_duplicate_success(self) -> None:
        with tempfile.TemporaryDirectory() as output_root, tempfile.TemporaryDirectory() as repo_dir:
            merge_identity = self._init_mergeable_repo(repo_dir)
            candidate_key = "c" * 64
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "completed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": None,
                },
            ):
                with mock.patch(
                    "orchestrator.main.evaluate_job_directory",
                    return_value=self._candidate_evaluation_result("job-merge-exec-idempotent"),
                ):
                    with mock.patch(
                        "orchestrator.main.persist_evaluation_artifacts",
                        return_value=("rubric.json", "merge_gate.json"),
                    ):
                        with mock.patch("orchestrator.main.record_job_evaluation"):
                            with mock.patch("orchestrator.main.record_execution_target"):
                                with mock.patch(
                                    "orchestrator.main.get_execution_target_by_identity",
                                    return_value={"candidate_idempotency_key": candidate_key},
                                ):
                                    with mock.patch(
                                        "orchestrator.main.get_merge_execution_by_candidate_idempotency_key",
                                        return_value={
                                            "execution_status": "succeeded",
                                            "executed_at": "2026-01-01T00:00:02+00:00",
                                            "pre_merge_sha": merge_identity["base_sha"],
                                            "post_merge_sha": "d" * 40,
                                            "merge_result_sha": "d" * 40,
                                        },
                                    ):
                                        with mock.patch(
                                            "orchestrator.main.execute_constrained_merge"
                                        ) as execute_merge_mock:
                                            with mock.patch(
                                                "orchestrator.main.record_merge_execution_outcome"
                                            ) as merge_state_mock:
                                                with mock.patch(
                                                    "orchestrator.main.record_merge_attempt_receipt"
                                                ) as receipt_mock:
                                                    with mock.patch(
                                                        "orchestrator.main.record_rollback_traceability_for_candidate",
                                                        return_value={
                                                            "rollback_trace_id": "rt-duplicate",
                                                            "rollback_eligible": 0,
                                                            "ineligible_reason": "merge_execution_not_succeeded",
                                                        },
                                                    ) as rollback_trace_mock:
                                                        with mock.patch(
                                                            "sys.argv",
                                                            [
                                                                "main.py",
                                                                "--repo",
                                                                "codex-local-runner",
                                                                "--task-type",
                                                                "orchestration",
                                                                "--goal",
                                                                "execute constrained merge",
                                                                "--provider",
                                                                "codex_cli",
                                                                "--output-root",
                                                                output_root,
                                                                "--execution-repo-path",
                                                                repo_dir,
                                                                "--target-ref",
                                                                merge_identity["target_ref"],
                                                                "--source-sha",
                                                                merge_identity["source_sha"],
                                                                "--base-sha",
                                                                merge_identity["base_sha"],
                                                                "--execute-merge",
                                                            ],
                                                        ):
                                                            rc = orchestrator_main.main()

            result_payload = self._read_single_result(output_root)

        self.assertEqual(rc, 0)
        self.assertEqual(result_payload["status"], "accepted")
        self.assertEqual(result_payload["execution"]["merge_execution"]["status"], "skipped")
        self.assertEqual(
            result_payload["execution"]["merge_execution"]["error"],
            "already_merged_for_candidate",
        )
        self.assertEqual(
            result_payload["persistence"],
            {
                "evaluation_artifacts": "written",
                "ledger": "written",
                "execution_target": "written",
                "merge_execution": "written",
                "merge_receipt": "written",
                "rollback_trace": "written",
            },
        )
        execute_merge_mock.assert_not_called()
        merge_state_mock.assert_called_once()
        receipt_mock.assert_called_once()
        self.assertEqual(receipt_mock.call_args.kwargs["merge_attempt_status"], "skipped")
        rollback_trace_mock.assert_called_once()
        self.assertFalse(result_payload["execution"]["merge_execution"]["rollback_trace"]["eligible"])

    def test_merge_execution_success_with_receipt_persistence_failure_is_visible(self) -> None:
        with tempfile.TemporaryDirectory() as output_root, tempfile.TemporaryDirectory() as repo_dir:
            merge_identity = self._init_mergeable_repo(repo_dir)
            candidate_key = "c" * 64
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "completed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": None,
                },
            ):
                with mock.patch(
                    "orchestrator.main.evaluate_job_directory",
                    return_value=self._candidate_evaluation_result("job-merge-exec-receipt-fail"),
                ):
                    with mock.patch(
                        "orchestrator.main.persist_evaluation_artifacts",
                        return_value=("rubric.json", "merge_gate.json"),
                    ):
                        with mock.patch("orchestrator.main.record_job_evaluation"):
                            with mock.patch("orchestrator.main.record_execution_target"):
                                with mock.patch(
                                    "orchestrator.main.get_execution_target_by_identity",
                                    return_value={"candidate_idempotency_key": candidate_key},
                                ):
                                    with mock.patch(
                                        "orchestrator.main.get_merge_execution_by_candidate_idempotency_key",
                                        return_value=None,
                                    ):
                                        with mock.patch(
                                            "orchestrator.main.record_merge_execution_outcome"
                                        ):
                                            with mock.patch(
                                                "orchestrator.main.record_merge_attempt_receipt",
                                                side_effect=RuntimeError("receipt persistence failed"),
                                            ):
                                                with mock.patch(
                                                    "orchestrator.main.record_rollback_traceability_for_candidate",
                                                    return_value={
                                                        "rollback_trace_id": "rt-receipt-failed",
                                                        "rollback_eligible": 1,
                                                        "ineligible_reason": None,
                                                    },
                                                ) as rollback_trace_mock:
                                                    with mock.patch(
                                                        "sys.argv",
                                                        [
                                                            "main.py",
                                                            "--repo",
                                                            "codex-local-runner",
                                                            "--task-type",
                                                            "orchestration",
                                                            "--goal",
                                                            "execute constrained merge",
                                                            "--provider",
                                                            "codex_cli",
                                                            "--output-root",
                                                            output_root,
                                                            "--execution-repo-path",
                                                            repo_dir,
                                                            "--target-ref",
                                                            merge_identity["target_ref"],
                                                            "--source-sha",
                                                            merge_identity["source_sha"],
                                                            "--base-sha",
                                                            merge_identity["base_sha"],
                                                            "--execute-merge",
                                                        ],
                                                    ):
                                                        rc = orchestrator_main.main()

            result_payload = self._read_single_result(output_root)

        self.assertEqual(rc, 0)
        self.assertEqual(result_payload["status"], "accepted")
        self.assertEqual(result_payload["execution"]["merge_execution"]["status"], "succeeded")
        self.assertEqual(
            result_payload["persistence"],
            {
                "evaluation_artifacts": "written",
                "ledger": "written",
                "execution_target": "written",
                "merge_execution": "written",
                "merge_receipt": "failed",
                "rollback_trace": "written",
            },
        )
        rollback_trace_mock.assert_called_once()

    def test_merge_execution_rollback_trace_persistence_failure_is_visible(self) -> None:
        with tempfile.TemporaryDirectory() as output_root, tempfile.TemporaryDirectory() as repo_dir:
            merge_identity = self._init_mergeable_repo(repo_dir)
            candidate_key = "c" * 64
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "completed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": None,
                },
            ):
                with mock.patch(
                    "orchestrator.main.evaluate_job_directory",
                    return_value=self._candidate_evaluation_result("job-merge-exec-rollback-trace-fail"),
                ):
                    with mock.patch(
                        "orchestrator.main.persist_evaluation_artifacts",
                        return_value=("rubric.json", "merge_gate.json"),
                    ):
                        with mock.patch("orchestrator.main.record_job_evaluation"):
                            with mock.patch("orchestrator.main.record_execution_target"):
                                with mock.patch(
                                    "orchestrator.main.get_execution_target_by_identity",
                                    return_value={"candidate_idempotency_key": candidate_key},
                                ):
                                    with mock.patch(
                                        "orchestrator.main.get_merge_execution_by_candidate_idempotency_key",
                                        return_value=None,
                                    ):
                                        with mock.patch(
                                            "orchestrator.main.record_merge_execution_outcome"
                                        ):
                                            with mock.patch(
                                                "orchestrator.main.record_merge_attempt_receipt",
                                                return_value="receipt-1",
                                            ):
                                                with mock.patch(
                                                    "orchestrator.main.record_rollback_traceability_for_candidate",
                                                    side_effect=RuntimeError("rollback trace write failed"),
                                                ):
                                                    with mock.patch(
                                                        "sys.argv",
                                                        [
                                                            "main.py",
                                                            "--repo",
                                                            "codex-local-runner",
                                                            "--task-type",
                                                            "orchestration",
                                                            "--goal",
                                                            "execute constrained merge",
                                                            "--provider",
                                                            "codex_cli",
                                                            "--output-root",
                                                            output_root,
                                                            "--execution-repo-path",
                                                            repo_dir,
                                                            "--target-ref",
                                                            merge_identity["target_ref"],
                                                            "--source-sha",
                                                            merge_identity["source_sha"],
                                                            "--base-sha",
                                                            merge_identity["base_sha"],
                                                            "--execute-merge",
                                                        ],
                                                    ):
                                                        rc = orchestrator_main.main()

            result_payload = self._read_single_result(output_root)

        self.assertEqual(rc, 0)
        self.assertEqual(result_payload["status"], "accepted")
        self.assertEqual(result_payload["execution"]["merge_execution"]["status"], "succeeded")
        self.assertEqual(
            result_payload["persistence"],
            {
                "evaluation_artifacts": "written",
                "ledger": "written",
                "execution_target": "written",
                "merge_execution": "written",
                "merge_receipt": "written",
                "rollback_trace": "failed",
            },
        )
        self.assertFalse(result_payload["execution"]["merge_execution"]["rollback_trace"]["recorded"])
        self.assertFalse(result_payload["execution"]["merge_execution"]["rollback_trace"]["eligible"])

    def test_constrained_rollback_execution_succeeds_with_eligible_trace(self) -> None:
        with tempfile.TemporaryDirectory() as output_root, tempfile.TemporaryDirectory() as repo_dir:
            merge_state = self._init_repo_with_merge_commit(repo_dir)
            trace_id = "trace-rollback-success"
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "completed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": None,
                },
            ):
                with mock.patch(
                    "orchestrator.main.evaluate_job_directory",
                    return_value=self._candidate_evaluation_result("job-rollback-exec-success"),
                ):
                    with mock.patch(
                        "orchestrator.main.persist_evaluation_artifacts",
                        return_value=("rubric.json", "merge_gate.json"),
                    ):
                        with mock.patch("orchestrator.main.record_job_evaluation"):
                            with mock.patch("orchestrator.main.get_rollback_trace_by_id", return_value={
                                "rollback_trace_id": trace_id,
                                "candidate_idempotency_key": "c" * 64,
                                "job_id": "job-rollback-exec-success",
                                "repo": "codex-local-runner",
                                "target_ref": merge_state["target_ref"],
                                "source_sha": merge_state["source_sha"],
                                "base_sha": merge_state["base_sha"],
                                "pre_merge_sha": merge_state["pre_merge_sha"],
                                "post_merge_sha": merge_state["post_merge_sha"],
                                "rollback_eligible": 1,
                                "ineligible_reason": None,
                            }):
                                with mock.patch(
                                    "orchestrator.main.get_rollback_execution_by_trace_id",
                                    return_value=None,
                                ):
                                    with mock.patch(
                                        "orchestrator.main.record_rollback_execution_outcome"
                                    ) as record_rollback_mock:
                                        with mock.patch(
                                            "sys.argv",
                                            [
                                                "main.py",
                                                "--repo",
                                                "codex-local-runner",
                                                "--task-type",
                                                "orchestration",
                                                "--goal",
                                                "execute constrained rollback",
                                                "--provider",
                                                "codex_cli",
                                                "--output-root",
                                                output_root,
                                                "--execution-repo-path",
                                                repo_dir,
                                                "--execute-rollback",
                                                "--rollback-trace-id",
                                                trace_id,
                                            ],
                                        ):
                                            rc = orchestrator_main.main()

            result_payload = self._read_single_result(output_root)
            head_after = self._run_git(repo_dir, ["rev-parse", "HEAD"])

        self.assertEqual(rc, 0)
        self.assertEqual(result_payload["status"], "accepted")
        rollback_execution = result_payload["execution"]["rollback_execution"]
        self.assertEqual(rollback_execution["status"], "succeeded")
        self.assertTrue(rollback_execution["attempted"])
        self.assertEqual(rollback_execution["rollback_trace_id"], trace_id)
        self.assertEqual(rollback_execution["rollback_result_sha"], head_after)
        self.assertEqual(
            result_payload["persistence"]["rollback_execution"],
            "written",
        )
        record_rollback_mock.assert_called_once()

    def test_constrained_rollback_execution_skips_when_trace_is_ineligible(self) -> None:
        with tempfile.TemporaryDirectory() as output_root, tempfile.TemporaryDirectory() as repo_dir:
            merge_state = self._init_repo_with_merge_commit(repo_dir)
            trace_id = "trace-rollback-ineligible"
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "completed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": None,
                },
            ):
                with mock.patch(
                    "orchestrator.main.evaluate_job_directory",
                    return_value=self._candidate_evaluation_result("job-rollback-exec-ineligible"),
                ):
                    with mock.patch(
                        "orchestrator.main.persist_evaluation_artifacts",
                        return_value=("rubric.json", "merge_gate.json"),
                    ):
                        with mock.patch("orchestrator.main.record_job_evaluation"):
                            with mock.patch("orchestrator.main.get_rollback_trace_by_id", return_value={
                                "rollback_trace_id": trace_id,
                                "repo": "codex-local-runner",
                                "target_ref": merge_state["target_ref"],
                                "pre_merge_sha": merge_state["pre_merge_sha"],
                                "post_merge_sha": merge_state["post_merge_sha"],
                                "rollback_eligible": 0,
                                "ineligible_reason": "merge_execution_not_succeeded",
                            }):
                                with mock.patch(
                                    "orchestrator.main.execute_constrained_rollback"
                                ) as execute_rollback_mock:
                                    with mock.patch(
                                        "orchestrator.main.record_rollback_execution_outcome"
                                    ) as record_rollback_mock:
                                        with mock.patch(
                                            "sys.argv",
                                            [
                                                "main.py",
                                                "--repo",
                                                "codex-local-runner",
                                                "--task-type",
                                                "orchestration",
                                                "--goal",
                                                "execute constrained rollback",
                                                "--provider",
                                                "codex_cli",
                                                "--output-root",
                                                output_root,
                                                "--execution-repo-path",
                                                repo_dir,
                                                "--execute-rollback",
                                                "--rollback-trace-id",
                                                trace_id,
                                            ],
                                        ):
                                            rc = orchestrator_main.main()

            result_payload = self._read_single_result(output_root)

        self.assertEqual(rc, 0)
        self.assertEqual(result_payload["execution"]["rollback_execution"]["status"], "skipped")
        self.assertEqual(
            result_payload["execution"]["rollback_execution"]["error"],
            "merge_execution_not_succeeded",
        )
        self.assertEqual(result_payload["persistence"]["rollback_execution"], "written")
        execute_rollback_mock.assert_not_called()
        record_rollback_mock.assert_called_once()

    def test_constrained_rollback_execution_skips_on_current_state_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as output_root, tempfile.TemporaryDirectory() as repo_dir:
            trace_id = "trace-rollback-mismatch"
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "completed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": None,
                },
            ):
                with mock.patch(
                    "orchestrator.main.evaluate_job_directory",
                    return_value=self._candidate_evaluation_result("job-rollback-exec-mismatch"),
                ):
                    with mock.patch(
                        "orchestrator.main.persist_evaluation_artifacts",
                        return_value=("rubric.json", "merge_gate.json"),
                    ):
                        with mock.patch("orchestrator.main.record_job_evaluation"):
                            with mock.patch("orchestrator.main.get_rollback_trace_by_id", return_value={
                                "rollback_trace_id": trace_id,
                                "candidate_idempotency_key": "c" * 64,
                                "job_id": "job-rollback-exec-mismatch",
                                "repo": "codex-local-runner",
                                "target_ref": "refs/heads/main",
                                "source_sha": "a" * 40,
                                "base_sha": "b" * 40,
                                "pre_merge_sha": "b" * 40,
                                "post_merge_sha": "c" * 40,
                                "rollback_eligible": 1,
                                "ineligible_reason": None,
                            }):
                                with mock.patch(
                                    "orchestrator.main.get_rollback_execution_by_trace_id",
                                    return_value=None,
                                ):
                                    with mock.patch(
                                        "orchestrator.main.execute_constrained_rollback",
                                        return_value={
                                            "status": "skipped",
                                            "attempted": False,
                                            "attempted_at": "2026-01-01T00:00:02+00:00",
                                            "consistency_check_passed": False,
                                            "current_head_sha": "d" * 40,
                                            "rollback_result_sha": None,
                                            "error": "current_head_mismatch_post_merge",
                                        },
                                    ) as execute_rollback_mock:
                                        with mock.patch(
                                            "orchestrator.main.record_rollback_execution_outcome"
                                        ) as record_rollback_mock:
                                            with mock.patch(
                                                "sys.argv",
                                                [
                                                    "main.py",
                                                    "--repo",
                                                    "codex-local-runner",
                                                    "--task-type",
                                                    "orchestration",
                                                    "--goal",
                                                    "execute constrained rollback",
                                                    "--provider",
                                                    "codex_cli",
                                                    "--output-root",
                                                    output_root,
                                                    "--execution-repo-path",
                                                    repo_dir,
                                                    "--execute-rollback",
                                                    "--rollback-trace-id",
                                                    trace_id,
                                                ],
                                            ):
                                                rc = orchestrator_main.main()

            result_payload = self._read_single_result(output_root)

        self.assertEqual(rc, 0)
        self.assertEqual(result_payload["execution"]["rollback_execution"]["status"], "skipped")
        self.assertEqual(
            result_payload["execution"]["rollback_execution"]["error"],
            "current_head_mismatch_post_merge",
        )
        self.assertEqual(result_payload["persistence"]["rollback_execution"], "written")
        execute_rollback_mock.assert_called_once()
        record_rollback_mock.assert_called_once()

    def test_constrained_rollback_execution_is_protected_from_duplicate_success(self) -> None:
        with tempfile.TemporaryDirectory() as output_root, tempfile.TemporaryDirectory() as repo_dir:
            trace_id = "trace-rollback-duplicate"
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "completed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": None,
                },
            ):
                with mock.patch(
                    "orchestrator.main.evaluate_job_directory",
                    return_value=self._candidate_evaluation_result("job-rollback-exec-duplicate"),
                ):
                    with mock.patch(
                        "orchestrator.main.persist_evaluation_artifacts",
                        return_value=("rubric.json", "merge_gate.json"),
                    ):
                        with mock.patch("orchestrator.main.record_job_evaluation"):
                            with mock.patch("orchestrator.main.get_rollback_trace_by_id", return_value={
                                "rollback_trace_id": trace_id,
                                "candidate_idempotency_key": "c" * 64,
                                "job_id": "job-rollback-exec-duplicate",
                                "repo": "codex-local-runner",
                                "target_ref": "refs/heads/main",
                                "source_sha": "a" * 40,
                                "base_sha": "b" * 40,
                                "pre_merge_sha": "b" * 40,
                                "post_merge_sha": "c" * 40,
                                "rollback_eligible": 1,
                                "ineligible_reason": None,
                            }):
                                with mock.patch(
                                    "orchestrator.main.get_rollback_execution_by_trace_id",
                                    return_value={
                                        "execution_status": "succeeded",
                                        "attempted_at": "2026-01-01T00:00:03+00:00",
                                        "current_head_sha": "c" * 40,
                                        "rollback_result_sha": "d" * 40,
                                        "consistency_check_passed": 1,
                                    },
                                ):
                                    with mock.patch(
                                        "orchestrator.main.execute_constrained_rollback"
                                    ) as execute_rollback_mock:
                                        with mock.patch(
                                            "orchestrator.main.record_rollback_execution_outcome"
                                        ) as record_rollback_mock:
                                            with mock.patch(
                                                "sys.argv",
                                                [
                                                    "main.py",
                                                    "--repo",
                                                    "codex-local-runner",
                                                    "--task-type",
                                                    "orchestration",
                                                    "--goal",
                                                    "execute constrained rollback",
                                                    "--provider",
                                                    "codex_cli",
                                                    "--output-root",
                                                    output_root,
                                                    "--execution-repo-path",
                                                    repo_dir,
                                                    "--execute-rollback",
                                                    "--rollback-trace-id",
                                                    trace_id,
                                                ],
                                            ):
                                                rc = orchestrator_main.main()

            result_payload = self._read_single_result(output_root)

        self.assertEqual(rc, 0)
        self.assertEqual(result_payload["execution"]["rollback_execution"]["status"], "skipped")
        self.assertEqual(
            result_payload["execution"]["rollback_execution"]["error"],
            "already_rolled_back_for_trace",
        )
        self.assertEqual(result_payload["persistence"]["rollback_execution"], "written")
        execute_rollback_mock.assert_not_called()
        record_rollback_mock.assert_called_once()

    def test_rollback_execution_persistence_failure_is_visible(self) -> None:
        with tempfile.TemporaryDirectory() as output_root, tempfile.TemporaryDirectory() as repo_dir:
            trace_id = "trace-rollback-persist-fail"
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "completed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": None,
                },
            ):
                with mock.patch(
                    "orchestrator.main.evaluate_job_directory",
                    return_value=self._candidate_evaluation_result("job-rollback-exec-persist-fail"),
                ):
                    with mock.patch(
                        "orchestrator.main.persist_evaluation_artifacts",
                        return_value=("rubric.json", "merge_gate.json"),
                    ):
                        with mock.patch("orchestrator.main.record_job_evaluation"):
                            with mock.patch("orchestrator.main.get_rollback_trace_by_id", return_value={
                                "rollback_trace_id": trace_id,
                                "candidate_idempotency_key": "c" * 64,
                                "job_id": "job-rollback-exec-persist-fail",
                                "repo": "codex-local-runner",
                                "target_ref": "refs/heads/main",
                                "source_sha": "a" * 40,
                                "base_sha": "b" * 40,
                                "pre_merge_sha": "b" * 40,
                                "post_merge_sha": "c" * 40,
                                "rollback_eligible": 1,
                                "ineligible_reason": None,
                            }):
                                with mock.patch(
                                    "orchestrator.main.get_rollback_execution_by_trace_id",
                                    return_value=None,
                                ):
                                    with mock.patch(
                                        "orchestrator.main.execute_constrained_rollback",
                                        return_value={
                                            "status": "succeeded",
                                            "attempted": True,
                                            "attempted_at": "2026-01-01T00:00:03+00:00",
                                            "consistency_check_passed": True,
                                            "current_head_sha": "c" * 40,
                                            "rollback_result_sha": "d" * 40,
                                            "error": None,
                                        },
                                    ):
                                        with mock.patch(
                                            "orchestrator.main.record_rollback_execution_outcome",
                                            side_effect=RuntimeError("rollback execution persist failed"),
                                        ):
                                            with mock.patch(
                                                "sys.argv",
                                                [
                                                    "main.py",
                                                    "--repo",
                                                    "codex-local-runner",
                                                    "--task-type",
                                                    "orchestration",
                                                    "--goal",
                                                    "execute constrained rollback",
                                                    "--provider",
                                                    "codex_cli",
                                                    "--output-root",
                                                    output_root,
                                                    "--execution-repo-path",
                                                    repo_dir,
                                                    "--execute-rollback",
                                                    "--rollback-trace-id",
                                                    trace_id,
                                                ],
                                            ):
                                                rc = orchestrator_main.main()

            result_payload = self._read_single_result(output_root)

        self.assertEqual(rc, 0)
        self.assertEqual(result_payload["execution"]["rollback_execution"]["status"], "succeeded")
        self.assertEqual(result_payload["persistence"]["rollback_execution"], "failed")


@unittest.skipUnless(importlib.util.find_spec("flask") is not None, "flask is not installed")
class AppWorktreeIntegrationTests(unittest.TestCase):
    def test_app_run_uses_prepared_worktree_path(self) -> None:
        import app as app_module

        app_module.app.config["TESTING"] = True
        with tempfile.TemporaryDirectory() as repo_dir, tempfile.TemporaryDirectory() as tasks_dir:
            (Path(repo_dir) / ".git").mkdir()
            latest_task_path = Path(tasks_dir) / "latest_task.json"
            latest_prompt_path = Path(tasks_dir) / "latest_prompt.txt"
            with mock.patch("app.TASKS_DIR", Path(tasks_dir)):
                with mock.patch("app.LATEST_TASK_PATH", latest_task_path):
                    with mock.patch("app.LATEST_PROMPT_PATH", latest_prompt_path):
                        with mock.patch("app.build_prompt", return_value="prompt text"):
                            with mock.patch(
                                "app.prepare_git_worktree",
                                return_value={
                                    "source_repo_path": repo_dir,
                                    "worktree_path": "/prepared/worktree",
                                    "branch_name": "codex-run/20260101_000000",
                                    "created": True,
                                    "cleanup_needed": True,
                                    "error": "",
                                },
                            ):
                                with mock.patch(
                                    "app.cleanup_git_worktree",
                                    return_value={
                                        "worktree_path": "/prepared/worktree",
                                        "branch_name": "codex-run/20260101_000000",
                                        "cleaned": True,
                                        "error": "",
                                    },
                                ):
                                    with mock.patch(
                                        "app.run_validation_commands",
                                        return_value={
                                            "status": "passed",
                                            "success": True,
                                            "commands": [
                                                {
                                                    "command": "echo verify",
                                                    "return_code": 0,
                                                    "stdout": "ok\n",
                                                    "stderr": "",
                                                    "success": True,
                                                }
                                            ],
                                            "command_results": [
                                                {
                                                    "command": "echo verify",
                                                    "status": "passed",
                                                    "return_code": 0,
                                                    "stdout": "ok\n",
                                                    "stderr": "",
                                                }
                                            ],
                                            "error": "",
                                            "summary": {"total": 1, "passed": 1, "failed": 0},
                                            "reason": "validation_passed",
                                        },
                                    ) as verify_mock:
                                        with mock.patch(
                                            "app.run_codex",
                                            return_value={
                                                "status": "completed",
                                                "success": True,
                                                "return_code": 0,
                                                "started_at": "2026-01-01T00:00:00",
                                                "finished_at": "2026-01-01T00:00:01",
                                                "artifacts": [],
                                                "error": "",
                                            },
                                        ) as run_codex_mock:
                                            client = app_module.app.test_client()
                                            response = client.post(
                                                "/run",
                                                data={
                                                    "repo_path": repo_dir,
                                                    "goal": "execute in worktree",
                                                    "allowed_files": "",
                                                    "forbidden_files": "",
                                                    "validation_commands": "echo verify",
                                                    "notes": "",
                                                },
                                            )

        self.assertEqual(response.status_code, 200)
        run_codex_mock.assert_called_once()
        run_call = run_codex_mock.call_args.kwargs
        self.assertEqual(run_call["task"]["repo_path"], "/prepared/worktree")
        verify_mock.assert_called_once_with(
            validation_commands=["echo verify"],
            cwd="/prepared/worktree",
        )


if __name__ == "__main__":
    unittest.main()
