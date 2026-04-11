from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from adapters.chatgpt_tasks import ChatgptTasksAdapter
from adapters.codex_cli import CodexCliAdapter
from adapters.local_llm import LocalLlmAdapter
from orchestrator import main as orchestrator_main


class CodexCliExecutionTests(unittest.TestCase):
    def test_codex_cli_execute_completed(self) -> None:
        adapter = CodexCliAdapter()
        with tempfile.TemporaryDirectory() as repo_dir, tempfile.TemporaryDirectory() as work_dir:
            execution_dir = Path(work_dir) / "execution_runs" / "20260101_000000"
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
            ):
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

    def test_codex_cli_execute_failure_is_reported(self) -> None:
        adapter = CodexCliAdapter()
        with tempfile.TemporaryDirectory() as repo_dir, tempfile.TemporaryDirectory() as work_dir:
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
            ):
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

    def test_stub_adapters_do_not_execute(self) -> None:
        with self.assertRaises(NotImplementedError):
            ChatgptTasksAdapter().execute({})
        with self.assertRaises(NotImplementedError):
            LocalLlmAdapter().execute({})


class OrchestratorExecutionSemanticsTests(unittest.TestCase):
    def _read_single_result(self, output_root: str) -> dict:
        output_dirs = list(Path(output_root).iterdir())
        self.assertEqual(len(output_dirs), 1)
        return json.loads((output_dirs[0] / "result.json").read_text(encoding="utf-8"))

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

        self.assertEqual(rc, 0)
        self.assertEqual(result["status"], "accepted")
        self.assertEqual(result["execution"]["status"], "failed")

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

        self.assertEqual(rc, 1)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["execution"]["status"], "not_started")


if __name__ == "__main__":
    unittest.main()
