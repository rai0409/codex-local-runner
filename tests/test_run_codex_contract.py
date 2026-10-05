from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from run_codex import run_codex


class _CapturingSubprocess:
    def __init__(self) -> None:
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout=kwargs["input"], stderr=kwargs["input"])


class RunCodexContractTests(unittest.TestCase):
    def test_production_path_uses_no_confirmation_stdin_contract(self) -> None:
        prompt = "PROMPT_SECRET_MARKER_7A19"
        with tempfile.TemporaryDirectory() as repo_dir, tempfile.TemporaryDirectory() as work_root:
            runner = _CapturingSubprocess()
            with mock.patch("run_codex.shutil.which", return_value="/usr/bin/codex"), mock.patch(
                "run_codex.subprocess.run", side_effect=runner
            ):
                result = run_codex(task={"repo_path": repo_dir}, prompt=prompt, work_root=work_root, persist_prompt=False)
            args, kwargs = runner.calls[0]
            command = args[0]
            self.assertEqual(result["status"], "completed")
            self.assertNotIn(prompt, command)
            self.assertEqual(command[command.index("--sandbox") + 1], "workspace-write")
            self.assertEqual(command[command.index("--config") + 1], 'approval_policy="never"')
            self.assertEqual(command[-1], "-")
            self.assertNotIn("--approve-for-me", command)
            self.assertNotIn("--yolo", command)
            self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", command)
            self.assertNotIn("danger-full-access", command)
            self.assertIn(prompt, kwargs["input"])
            self.assertTrue(kwargs["text"])
            self.assertTrue(kwargs["capture_output"])
            self.assertEqual(kwargs["cwd"], repo_dir)
            self.assertEqual(kwargs["timeout"], 3600)
            self.assertEqual(result["prompt_path"], "")
            self.assertNotIn(prompt, Path(result["meta_path"]).read_text(encoding="utf-8"))
            self.assertNotIn(prompt, Path(result["stdout_path"]).read_text(encoding="utf-8"))
            self.assertNotIn(prompt, Path(result["stderr_path"]).read_text(encoding="utf-8"))
    def test_not_started_when_codex_is_missing(self) -> None:
        with mock.patch("run_codex.shutil.which", return_value=None):
            result = run_codex(task={"repo_path": "."}, prompt="test")

        self.assertEqual(result["status"], "not_started")
        self.assertFalse(result["success"])
        self.assertIsNone(result["return_code"])
        self.assertFalse(result["timed_out"])
        self.assertIsNone(result["started_at"])
        self.assertIsNone(result["finished_at"])
        self.assertEqual(result["artifacts"], [])

    def test_completed_contract_contains_timestamps_and_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as repo_dir, tempfile.TemporaryDirectory() as work_root:
            with mock.patch("run_codex.shutil.which", return_value="/usr/bin/codex"):
                with mock.patch(
                    "run_codex.subprocess.run",
                    return_value=subprocess.CompletedProcess(
                        args=["codex", "exec"],
                        returncode=0,
                        stdout="ok",
                        stderr="",
                    ),
                ):
                    result = run_codex(
                        task={"repo_path": repo_dir},
                        prompt="test prompt",
                        work_root=work_root,
                    )

            self.assertEqual(result["status"], "completed")
            self.assertTrue(result["success"])
            self.assertIsNotNone(result["started_at"])
            self.assertIsNotNone(result["finished_at"])
            self.assertEqual(len(result["artifacts"]), 5)
            names = {item["name"] for item in result["artifacts"]}
            self.assertEqual(names, {"task", "prompt", "stdout", "stderr", "meta"})
            for item in result["artifacts"]:
                self.assertTrue(Path(item["path"]).exists())

    def test_default_timeout_is_3600_seconds(self) -> None:
        with tempfile.TemporaryDirectory() as repo_dir, tempfile.TemporaryDirectory() as work_root:
            with mock.patch("run_codex.shutil.which", return_value="/usr/bin/codex"), mock.patch(
                "run_codex.subprocess.run",
                return_value=subprocess.CompletedProcess(args=["codex", "exec"], returncode=0, stdout="", stderr=""),
            ) as execute:
                run_codex(task={"repo_path": repo_dir}, prompt="test", work_root=work_root)
        self.assertEqual(execute.call_args.kwargs["timeout"], 3600)

    def test_model_profile_values_are_explicitly_forwarded(self) -> None:
        with mock.patch("run_codex.execute_codex_cli", return_value={}) as execute:
            result = run_codex(
                task={
                    "repo_path": ".",
                    "model": "must-not-be-read",
                    "model_reasoning_effort": "must-not-be-read",
                },
                prompt="test",
                model="gpt-5.6",
                model_reasoning_effort="high",
            )
        self.assertEqual(result, {})
        self.assertEqual(execute.call_args.kwargs["model"], "gpt-5.6")
        self.assertEqual(execute.call_args.kwargs["model_reasoning_effort"], "high")
        self.assertEqual(execute.call_args.kwargs["timeout_seconds"], 3600)

    def test_emit_json_is_explicitly_forwarded(self) -> None:
        with mock.patch("run_codex.execute_codex_cli", return_value={}) as execute:
            result = run_codex(
                task={"repo_path": ".", "emit_json": False},
                prompt="test",
                emit_json=True,
            )
        self.assertEqual(result, {})
        self.assertTrue(execute.call_args.kwargs["emit_json"])

    def test_task_timeout_is_bounded_and_invalid_values_do_not_execute(self) -> None:
        with tempfile.TemporaryDirectory() as repo_dir, tempfile.TemporaryDirectory() as work_root:
            with mock.patch("run_codex.shutil.which", return_value="/usr/bin/codex"), mock.patch(
                "run_codex.subprocess.run",
                return_value=subprocess.CompletedProcess(args=["codex", "exec"], returncode=0, stdout="", stderr=""),
            ) as execute:
                result = run_codex(task={"repo_path": repo_dir, "execution_timeout_seconds": 1200}, prompt="test", work_root=work_root)
                self.assertEqual(result["status"], "completed")
                self.assertEqual(execute.call_args.kwargs["timeout"], 1200)
                accepted = run_codex(task={"repo_path": repo_dir, "execution_timeout_seconds": 18000}, prompt="test", work_root=work_root)
                self.assertEqual(accepted["status"], "completed")
                self.assertEqual(execute.call_args.kwargs["timeout"], 18000)
                for invalid in (True, 1.5, "900", 0, -1, 18001):
                    failed = run_codex(task={"repo_path": repo_dir, "execution_timeout_seconds": invalid}, prompt="test", work_root=work_root)
                    self.assertEqual(failed["status"], "not_started")
                    self.assertEqual(failed["error"], "codex_execution.timeout.invalid")
        self.assertEqual(execute.call_count, 2)

    def test_timed_out_status_is_explicit(self) -> None:
        timeout_exc = subprocess.TimeoutExpired(
            cmd=["codex", "exec"], timeout=600, output="partial", stderr="stream"
        )
        with tempfile.TemporaryDirectory() as repo_dir, tempfile.TemporaryDirectory() as work_root:
            with mock.patch("run_codex.shutil.which", return_value="/usr/bin/codex"):
                with mock.patch("run_codex.subprocess.run", side_effect=timeout_exc):
                    result = run_codex(
                        task={"repo_path": repo_dir},
                        prompt="test prompt",
                        work_root=work_root,
                    )

        self.assertEqual(result["status"], "timed_out")
        self.assertFalse(result["success"])
        self.assertTrue(result["timed_out"])
        self.assertIsNone(result["return_code"])
        self.assertIn("timed out", result["error"])

    def test_timed_out_bytes_output_is_normalized_to_string(self) -> None:
        timeout_exc = subprocess.TimeoutExpired(
            cmd=["codex", "exec"],
            timeout=600,
            output=b"\xffpartial",
            stderr=b"\xfeerror",
        )
        with tempfile.TemporaryDirectory() as repo_dir, tempfile.TemporaryDirectory() as work_root:
            with mock.patch("run_codex.shutil.which", return_value="/usr/bin/codex"):
                with mock.patch("run_codex.subprocess.run", side_effect=timeout_exc):
                    result = run_codex(
                        task={"repo_path": repo_dir},
                        prompt="test prompt",
                        work_root=work_root,
                    )

            stdout_text = Path(result["stdout_path"]).read_text(encoding="utf-8")
            stderr_text = Path(result["stderr_path"]).read_text(encoding="utf-8")

        self.assertEqual(result["status"], "timed_out")
        self.assertIsInstance(result["error"], str)
        self.assertIn("timed out", result["error"])
        self.assertIsInstance(stdout_text, str)
        self.assertIsInstance(stderr_text, str)
        self.assertIn("partial", stdout_text)
        self.assertIn("error", stderr_text)


if __name__ == "__main__":
    unittest.main()
