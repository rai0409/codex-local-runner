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


class ValidationResult(TypedDict):
    status: ValidationStatus
    success: bool
    commands: list[ValidationCommandResult]
    error: str
    summary: str
    reason: str


def run_validation_commands(validation_commands: list[str], cwd: str) -> ValidationResult:
    if not validation_commands:
        return {
            "status": "not_run",
            "success": True,
            "commands": [],
            "error": "",
            "summary": "validation not run: no validation commands provided.",
            "reason": "no_validation_commands",
        }

    command_results: list[ValidationCommandResult] = []
    for command in validation_commands:
        completed = subprocess.run(
            command,
            shell=True,
            text=True,
            capture_output=True,
            cwd=cwd,
        )
        command_results.append(
            {
                "command": command,
                "return_code": completed.returncode,
                "stdout": completed.stdout if completed.stdout is not None else "",
                "stderr": completed.stderr if completed.stderr is not None else "",
                "success": completed.returncode == 0,
            }
        )

    failed_count = sum(1 for item in command_results if not item["success"])
    if failed_count > 0:
        return {
            "status": "failed",
            "success": False,
            "commands": command_results,
            "error": f"{failed_count} validation command(s) failed.",
            "summary": f"{failed_count} validation command(s) failed.",
            "reason": "",
        }

    return {
        "status": "passed",
        "success": True,
        "commands": command_results,
        "error": "",
        "summary": "all validation commands passed.",
        "reason": "",
    }
