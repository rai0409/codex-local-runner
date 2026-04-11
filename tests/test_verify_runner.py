from __future__ import annotations

import subprocess
import unittest
from unittest import mock

from verify.runner import run_validation_commands


class ValidationRunnerTests(unittest.TestCase):
    def test_no_validation_commands_returns_not_run(self) -> None:
        with mock.patch("verify.runner.subprocess.run") as run_mock:
            result = run_validation_commands(validation_commands=[], cwd="/tmp/repo")

        run_mock.assert_not_called()
        self.assertEqual(
            result,
            {
                "status": "not_run",
                "success": True,
                "commands": [],
                "error": "",
                "summary": "validation not run: no validation commands provided.",
                "reason": "no_validation_commands",
            },
        )
        self.assertNotIn("command_results", result)

    def test_one_successful_validation_command_returns_passed(self) -> None:
        with mock.patch(
            "verify.runner.subprocess.run",
            return_value=subprocess.CompletedProcess(
                args="echo ok",
                returncode=0,
                stdout="ok\n",
                stderr="",
            ),
        ) as run_mock:
            result = run_validation_commands(validation_commands=["echo ok"], cwd="/prepared/worktree")

        run_mock.assert_called_once_with(
            "echo ok",
            shell=True,
            text=True,
            capture_output=True,
            cwd="/prepared/worktree",
        )
        self.assertEqual(result["status"], "passed")
        self.assertTrue(result["success"])
        self.assertEqual(result["error"], "")
        self.assertEqual(result["summary"], {"total": 1, "passed": 1, "failed": 0})
        self.assertEqual(result["reason"], "")
        self.assertEqual(len(result["commands"]), 1)
        self.assertEqual(
            set(result["commands"][0].keys()),
            {"command", "return_code", "stdout", "stderr", "success"},
        )
        self.assertEqual(len(result["command_results"]), 1)
        self.assertEqual(
            set(result["command_results"][0].keys()),
            {"command", "status", "return_code", "stdout", "stderr"},
        )
        self.assertEqual(result["command_results"][0]["status"], "passed")
        self.assertEqual(result["commands"][0]["command"], "echo ok")
        self.assertEqual(result["commands"][0]["return_code"], 0)
        self.assertEqual(result["commands"][0]["stdout"], "ok\n")
        self.assertEqual(result["commands"][0]["stderr"], "")
        self.assertTrue(result["commands"][0]["success"])

    def test_one_failing_validation_command_returns_failed(self) -> None:
        with mock.patch(
            "verify.runner.subprocess.run",
            return_value=subprocess.CompletedProcess(
                args="false",
                returncode=1,
                stdout="",
                stderr="failed",
            ),
        ):
            result = run_validation_commands(validation_commands=["false"], cwd="/prepared/worktree")

        self.assertEqual(result["status"], "failed")
        self.assertFalse(result["success"])
        self.assertEqual(result["commands"][0]["command"], "false")
        self.assertEqual(result["commands"][0]["return_code"], 1)
        self.assertEqual(result["commands"][0]["stdout"], "")
        self.assertEqual(result["commands"][0]["stderr"], "failed")
        self.assertFalse(result["commands"][0]["success"])
        self.assertEqual(result["error"], "1 validation command(s) failed.")
        self.assertEqual(result["summary"], {"total": 1, "passed": 0, "failed": 1})
        self.assertEqual(result["reason"], "")
        self.assertEqual(result["command_results"][0]["status"], "failed")

    def test_validation_commands_continue_in_order(self) -> None:
        with mock.patch(
            "verify.runner.subprocess.run",
            side_effect=[
                subprocess.CompletedProcess(
                    args="cmd1",
                    returncode=1,
                    stdout="",
                    stderr="err1",
                ),
                subprocess.CompletedProcess(
                    args="cmd2",
                    returncode=0,
                    stdout="ok2",
                    stderr="",
                ),
            ],
        ) as run_mock:
            result = run_validation_commands(
                validation_commands=["cmd1", "cmd2"],
                cwd="/prepared/worktree",
            )

        self.assertEqual(run_mock.call_count, 2)
        self.assertEqual(result["status"], "failed")
        self.assertFalse(result["success"])
        self.assertEqual([item["command"] for item in result["command_results"]], ["cmd1", "cmd2"])
        self.assertEqual(result["summary"], {"total": 2, "passed": 1, "failed": 1})
        self.assertEqual(
            set(result.keys()),
            {"status", "success", "commands", "command_results", "error", "summary", "reason"},
        )


if __name__ == "__main__":
    unittest.main()
