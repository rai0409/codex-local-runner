from __future__ import annotations

import subprocess
from typing import Literal
from typing import TypedDict


ValidationStatus = Literal["passed", "failed", "not_run"]


class ValidationCommandResult(TypedDict):
    command: str
    return_code: int
    stdout: str
    stderr: str
    success: bool


class ValidationObservedCommandResult(TypedDict):
    command: str
    status: str
    return_code: int
    stdout: str
    stderr: str


class ValidationSummary(TypedDict):
    total: int
    passed: int
    failed: int


class ValidationResult(TypedDict, total=False):
    status: ValidationStatus
    success: bool
    commands: list[ValidationCommandResult]
    command_results: list[ValidationObservedCommandResult]
    error: str
    summary: ValidationSummary
    reason: str


def run_validation_commands(validation_commands: list[str], cwd: str) -> ValidationResult:
    if not validation_commands:
        return {
            "status": "not_run",
            "success": True,
            "commands": [],
            "error": "",
            "reason": "validation_not_run_execution_status_unknown",
        }

    command_results: list[ValidationCommandResult] = []
    observed_command_results: list[ValidationObservedCommandResult] = []
    for command in validation_commands:
        completed = subprocess.run(
            command,
            shell=True,
            text=True,
            capture_output=True,
            cwd=cwd,
        )
        command_status = "passed" if completed.returncode == 0 else "failed"
        command_results.append(
            {
                "command": command,
                "return_code": completed.returncode,
                "stdout": completed.stdout if completed.stdout is not None else "",
                "stderr": completed.stderr if completed.stderr is not None else "",
                "success": completed.returncode == 0,
            }
        )
        observed_command_results.append(
            {
                "command": command,
                "status": command_status,
                "return_code": completed.returncode,
                "stdout": completed.stdout if completed.stdout is not None else "",
                "stderr": completed.stderr if completed.stderr is not None else "",
            }
        )

    passed_count = sum(1 for item in observed_command_results if item["status"] == "passed")
    failed_count = sum(1 for item in command_results if not item["success"])
    summary: ValidationSummary = {
        "total": len(observed_command_results),
        "passed": passed_count,
        "failed": failed_count,
    }
    if failed_count > 0:
        return {
            "status": "failed",
            "success": False,
            "commands": command_results,
            "command_results": observed_command_results,
            "error": f"{failed_count} validation command(s) failed.",
            "summary": summary,
            "reason": "validation_failed",
        }

    return {
        "status": "passed",
        "success": True,
        "commands": command_results,
        "command_results": observed_command_results,
        "error": "",
        "summary": summary,
        "reason": "validation_passed",
    }
