from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from run_codex import run_codex


class RunCodexContractTests(unittest.TestCase):
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
