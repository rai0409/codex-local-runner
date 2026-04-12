from __future__ import annotations

import json
import importlib.util
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
        self.assertEqual(set(result["persistence"].keys()), {"evaluation_artifacts", "ledger"})
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
            {"evaluation_artifacts": "skipped", "ledger": "skipped"},
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
        self.assertEqual(set(result_payload["persistence"].keys()), {"evaluation_artifacts", "ledger"})

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
            {"evaluation_artifacts": "written", "ledger": "written"},
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
            {"evaluation_artifacts": "failed", "ledger": "written"},
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
            {"evaluation_artifacts": "written", "ledger": "failed"},
        )


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
