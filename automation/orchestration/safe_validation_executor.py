"""Safe, declarative validation-command execution for validated Profiles.

Calling this module does not itself grant authorization; callers must establish
authorization before invoking the executor.
"""
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from datetime import datetime, timezone
import signal
import subprocess
import threading
import time
from typing import Any, Mapping

from automation.orchestration.repository_profile import RepositoryProfile
from automation.orchestration.repository_profile import RepositoryProfileValidationError
from automation.orchestration.repository_profile import ValidationCommand
from automation.orchestration.repository_profile import validate_repository_profile

SAFE_VALIDATION_EXECUTOR_SCHEMA_VERSION = 1
DEFAULT_MAX_OUTPUT_BYTES = 65536
MAX_OUTPUT_BYTES = 1048576
DEFAULT_TERMINATION_GRACE_SECONDS = 2.0
MAX_TERMINATION_GRACE_SECONDS = 30.0
VALIDATION_COMMAND_STATUSES = ("passed", "failed", "timed_out", "spawn_failed", "skipped")
VALIDATION_EXECUTION_STATUSES = ("passed", "partial", "failed")

_FIXED_ENVIRONMENT = {
    "GIT_TERMINAL_PROMPT": "0",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "PYTHONUNBUFFERED": "1",
    "PYTHONDONTWRITEBYTECODE": "1",
}


class SafeValidationExecutorError(ValueError):
    """A stable executor failure that never includes command output or secrets."""

    def __init__(self, reason_code: str, message: str, detail_reason_code: str | None = None) -> None:
        self.reason_code = reason_code
        self.detail_reason_code = detail_reason_code
        super().__init__(f"{reason_code}: {message}")


@dataclass(frozen=True)
class ValidationCommandResult:
    command_id: str
    kind: str
    argv: tuple[str, ...]
    cwd: str
    required: bool
    stop_on_failure: bool
    status: str
    return_code: int | None
    reason_code: str
    started_at: str | None
    finished_at: str | None
    duration_seconds: float
    stdout: str
    stderr: str
    stdout_truncated: bool
    stderr_truncated: bool


@dataclass(frozen=True)
class ValidationExecutionResult:
    schema_version: int
    profile_id: str
    repository_root: str
    status: str
    started_at: str
    finished_at: str
    duration_seconds: float
    command_results: tuple[ValidationCommandResult, ...]
    required_failure_ids: tuple[str, ...]
    optional_failure_ids: tuple[str, ...]
    stopped_early: bool
    stop_reason_code: str | None


def _error(reason_code: str, message: str, detail_reason_code: str | None = None) -> SafeValidationExecutorError:
    return SafeValidationExecutorError(reason_code, message, detail_reason_code)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _validated_options(
    ambient_environment: Mapping[str, str] | None,
    max_output_bytes: int,
    termination_grace_seconds: float,
) -> tuple[Mapping[str, str], int, float]:
    if isinstance(max_output_bytes, bool) or not isinstance(max_output_bytes, int) or not 1 <= max_output_bytes <= MAX_OUTPUT_BYTES:
        raise _error("safe_validation.max_output_bytes.invalid", "must be an integer within the supported range")
    if (
        isinstance(termination_grace_seconds, bool)
        or not isinstance(termination_grace_seconds, (int, float))
        or not math.isfinite(float(termination_grace_seconds))
        or not 0 < float(termination_grace_seconds) <= MAX_TERMINATION_GRACE_SECONDS
    ):
        raise _error("safe_validation.termination_grace_seconds.invalid", "must be a finite positive number within the supported range")
    source: Mapping[str, str] = os.environ if ambient_environment is None else ambient_environment
    if not isinstance(source, Mapping) or any(not isinstance(key, str) or not isinstance(value, str) for key, value in source.items()):
        raise _error("safe_validation.ambient_environment.invalid", "must be a string-to-string mapping")
    return source, max_output_bytes, float(termination_grace_seconds)


def _safe_environment(profile: RepositoryProfile, source: Mapping[str, str]) -> dict[str, str]:
    environment = {
        key: source[key]
        for key in profile.environment_allowlist
        if key in source
    }
    environment.update(_FIXED_ENVIRONMENT)
    return environment


class _StreamCapture:
    def __init__(self, stream: Any, limit: int) -> None:
        self._stream = stream
        self._limit = limit
        self.data = bytearray()
        self.truncated = False
        self.error: BaseException | None = None

    def drain(self) -> None:
        try:
            while True:
                chunk = self._stream.read(65536)
                if not chunk:
                    break
                remaining = self._limit - len(self.data)
                if remaining > 0:
                    self.data.extend(chunk[:remaining])
                if len(chunk) > max(remaining, 0):
                    self.truncated = True
        except BaseException as exc:  # reader errors are converted to a command result
            self.error = exc

    def text(self) -> str:
        return bytes(self.data).decode("utf-8", errors="replace")


def _terminate(process: subprocess.Popen[bytes], grace_seconds: float) -> bool:
    """Terminate a timed-out process group; return whether cleanup was degraded."""
    cleanup_failed = False
    try:
        if os.name == "posix":
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            except OSError:
                process.terminate()
        else:
            process.terminate()
        try:
            process.wait(timeout=grace_seconds)
            return cleanup_failed
        except subprocess.TimeoutExpired:
            pass
        if os.name == "posix":
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except OSError:
                process.kill()
        else:
            process.kill()
        process.wait(timeout=grace_seconds)
    except (OSError, subprocess.TimeoutExpired):
        cleanup_failed = True
    return cleanup_failed


def _skipped(command: ValidationCommand) -> ValidationCommandResult:
    return ValidationCommandResult(
        command.command_id, command.kind, command.argv, command.cwd, command.required,
        command.stop_on_failure, "skipped", None,
        "safe_validation.command.skipped_after_stop", None, None, 0.0, "", "", False, False,
    )


def _run_command(
    command: ValidationCommand, environment: Mapping[str, str], max_output_bytes: int, grace_seconds: float
) -> ValidationCommandResult:
    started_at = _utc_now()
    started_monotonic = time.monotonic()
    try:
        process = subprocess.Popen(
            command.argv,
            shell=False,
            cwd=command.cwd,
            env=dict(environment),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
            close_fds=True,
            start_new_session=os.name == "posix",
        )
    except OSError:
        finished_at = _utc_now()
        return ValidationCommandResult(
            command.command_id, command.kind, command.argv, command.cwd, command.required,
            command.stop_on_failure, "spawn_failed", None,
            "safe_validation.command.spawn_failed", started_at, finished_at,
            max(0.0, time.monotonic() - started_monotonic), "", "", False, False,
        )
    assert process.stdout is not None and process.stderr is not None
    stdout = _StreamCapture(process.stdout, max_output_bytes)
    stderr = _StreamCapture(process.stderr, max_output_bytes)
    readers = [threading.Thread(target=capture.drain, daemon=True) for capture in (stdout, stderr)]
    for reader in readers:
        reader.start()
    timed_out = False
    cleanup_failed = False
    try:
        process.wait(timeout=command.timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        cleanup_failed = _terminate(process, grace_seconds)
    finally:
        if process.poll() is None:
            cleanup_failed = _terminate(process, grace_seconds) or cleanup_failed
        for reader in readers:
            reader.join()
    finished_at = _utc_now()
    duration = max(0.0, time.monotonic() - started_monotonic)
    if stdout.error is not None or stderr.error is not None:
        status, reason = "failed", "safe_validation.command.output_read_failed"
    elif timed_out:
        status = "timed_out"
        reason = "safe_validation.command.timeout_cleanup_failed" if cleanup_failed else "safe_validation.command.timed_out"
    elif process.returncode == 0:
        status, reason = "passed", "safe_validation.command.passed"
    else:
        status, reason = "failed", "safe_validation.command.failed"
    return ValidationCommandResult(
        command.command_id, command.kind, command.argv, command.cwd, command.required,
        command.stop_on_failure, status, process.returncode, reason, started_at, finished_at,
        duration, stdout.text(), stderr.text(), stdout.truncated, stderr.truncated,
    )


def execute_repository_validation(
    profile: RepositoryProfile,
    *,
    ambient_environment: Mapping[str, str] | None = None,
    max_output_bytes: int = DEFAULT_MAX_OUTPUT_BYTES,
    termination_grace_seconds: float = DEFAULT_TERMINATION_GRACE_SECONDS,
) -> ValidationExecutionResult:
    """Execute only validated Profile commands; this function grants no authorization."""
    source, output_limit, grace_seconds = _validated_options(
        ambient_environment, max_output_bytes, termination_grace_seconds
    )
    try:
        validated_profile = validate_repository_profile(profile)
    except RepositoryProfileValidationError as exc:
        raise _error("safe_validation.profile.invalid", "Profile validation failed", exc.reason_code) from exc
    environment = _safe_environment(validated_profile, source)
    started_at = _utc_now()
    started_monotonic = time.monotonic()
    results: list[ValidationCommandResult] = []
    stopped_early = False
    stop_reason: str | None = None
    for command in validated_profile.validation_commands:
        if stopped_early:
            results.append(_skipped(command))
            continue
        result = _run_command(command, environment, output_limit, grace_seconds)
        results.append(result)
        if result.status != "passed" and command.stop_on_failure:
            stopped_early = True
            stop_reason = result.reason_code
    required_failures = tuple(
        result.command_id for result in results if result.required and result.status != "passed"
    )
    optional_failures = tuple(
        result.command_id for result in results if not result.required and result.status != "passed"
    )
    status = "failed" if required_failures else "partial" if optional_failures else "passed"
    return ValidationExecutionResult(
        SAFE_VALIDATION_EXECUTOR_SCHEMA_VERSION, validated_profile.profile_id,
        validated_profile.repository_root, status, started_at, _utc_now(),
        max(0.0, time.monotonic() - started_monotonic), tuple(results),
        required_failures, optional_failures, stopped_early, stop_reason,
    )


def _validate_result(result: ValidationExecutionResult) -> None:
    if not isinstance(result, ValidationExecutionResult):
        raise _error("safe_validation.result.invalid_type", "must be a ValidationExecutionResult")
    if result.status not in VALIDATION_EXECUTION_STATUSES:
        raise _error("safe_validation.result.status.invalid", "has an invalid aggregate status")
    if not isinstance(result.duration_seconds, (int, float)) or result.duration_seconds < 0:
        raise _error("safe_validation.result.duration.invalid", "has an invalid duration")
    identifiers: set[str] = set()
    expected_required: list[str] = []
    expected_optional: list[str] = []
    skipped = False
    for command in result.command_results:
        if command.status not in VALIDATION_COMMAND_STATUSES:
            raise _error("safe_validation.result.command_status.invalid", "has an invalid command status")
        if command.command_id in identifiers:
            raise _error("safe_validation.result.command_id.duplicate", "has duplicate command IDs")
        if not isinstance(command.duration_seconds, (int, float)) or command.duration_seconds < 0:
            raise _error("safe_validation.result.duration.invalid", "has an invalid command duration")
        identifiers.add(command.command_id)
        if command.status != "passed":
            (expected_required if command.required else expected_optional).append(command.command_id)
        skipped = skipped or command.status == "skipped"
    if tuple(expected_required) != result.required_failure_ids or tuple(expected_optional) != result.optional_failure_ids:
        raise _error("safe_validation.result.failure_ids.inconsistent", "failure IDs do not match command results")
    if result.stopped_early != skipped or (result.stopped_early and result.stop_reason_code is None) or (not result.stopped_early and result.stop_reason_code is not None):
        raise _error("safe_validation.result.stop_state.inconsistent", "stop state does not match command results")


def validation_execution_result_to_mapping(result: ValidationExecutionResult) -> dict[str, Any]:
    _validate_result(result)
    return {
        "schema_version": result.schema_version,
        "profile_id": result.profile_id,
        "repository_root": result.repository_root,
        "status": result.status,
        "started_at": result.started_at,
        "finished_at": result.finished_at,
        "duration_seconds": result.duration_seconds,
        "command_results": [
            {
                "command_id": command.command_id, "kind": command.kind, "argv": list(command.argv),
                "cwd": command.cwd, "required": command.required, "stop_on_failure": command.stop_on_failure,
                "status": command.status, "return_code": command.return_code, "reason_code": command.reason_code,
                "started_at": command.started_at, "finished_at": command.finished_at,
                "duration_seconds": command.duration_seconds, "stdout": command.stdout, "stderr": command.stderr,
                "stdout_truncated": command.stdout_truncated, "stderr_truncated": command.stderr_truncated,
            }
            for command in result.command_results
        ],
        "required_failure_ids": list(result.required_failure_ids),
        "optional_failure_ids": list(result.optional_failure_ids),
        "stopped_early": result.stopped_early,
        "stop_reason_code": result.stop_reason_code,
    }


def serialize_validation_execution_result(result: ValidationExecutionResult) -> str:
    return json.dumps(
        validation_execution_result_to_mapping(result),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )


__all__ = [
    "DEFAULT_MAX_OUTPUT_BYTES",
    "DEFAULT_TERMINATION_GRACE_SECONDS",
    "MAX_OUTPUT_BYTES",
    "MAX_TERMINATION_GRACE_SECONDS",
    "SAFE_VALIDATION_EXECUTOR_SCHEMA_VERSION",
    "VALIDATION_COMMAND_STATUSES",
    "VALIDATION_EXECUTION_STATUSES",
    "SafeValidationExecutorError",
    "ValidationCommandResult",
    "ValidationExecutionResult",
    "execute_repository_validation",
    "serialize_validation_execution_result",
    "validation_execution_result_to_mapping",
]
