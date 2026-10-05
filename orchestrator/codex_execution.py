from __future__ import annotations

import json
import hashlib
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Literal, NotRequired, TypedDict

from automation.execution.codex_executor_adapter import build_no_confirmation_codex_command
from automation.execution.codex_executor_adapter import build_no_confirmation_execution_prompt


RunCodexStatus = Literal["completed", "failed", "timed_out", "not_started"]

DEFAULT_CODEX_EXECUTION_TIMEOUT_SECONDS = 3600
MAX_CODEX_EXECUTION_TIMEOUT_SECONDS = 18000
DEFAULT_VALIDATION_TIMEOUT_SECONDS = 3600
DEFAULT_COMPLETION_EVALUATOR_TIMEOUT_SECONDS = 3600
MAX_COMPLETION_EVALUATOR_TIMEOUT_SECONDS = 7200
DEFAULT_COMPLETION_REWORK_TIMEOUT_SECONDS = 7200
_OBSERVED_USAGE_FIELDS = (
    "input_tokens",
    "cached_input_tokens",
    "cache_write_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
)


def validate_codex_execution_timeout_seconds(value: object) -> int:
    """Return one bounded Codex timeout or reject malformed configuration."""
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= MAX_CODEX_EXECUTION_TIMEOUT_SECONDS:
        raise ValueError("codex_execution.timeout.invalid")
    return value


def validate_timeout_seconds(value: object, *, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
        raise ValueError("codex_execution.timeout.invalid")
    return value


def timeout_retry_seconds(initial_timeout_seconds: int) -> int | None:
    initial = validate_codex_execution_timeout_seconds(initial_timeout_seconds)
    retry = min(max(initial * 2, initial + 1800), MAX_CODEX_EXECUTION_TIMEOUT_SECONDS)
    return retry if retry > initial else None


class RunCodexArtifact(TypedDict):
    name: str
    path: str


class RunCodexResult(TypedDict):
    status: RunCodexStatus
    success: bool
    return_code: int | None
    run_dir: str
    stdout_path: str
    stderr_path: str
    task_path: str
    prompt_path: str
    meta_path: str
    error: str
    timed_out: bool
    started_at: str | None
    finished_at: str | None
    artifacts: list[RunCodexArtifact]
    transient_stdout: NotRequired[str]


def _to_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _sanitize_prompt_from_stream(stream: str, prompt: str) -> str:
    """Remove the prompt and distinctive prompt lines from persisted output."""
    sanitized = stream.replace(prompt, "[prompt redacted]")
    markers = sorted(
        {line for line in prompt.splitlines() if len(line.strip()) >= 8},
        key=len,
        reverse=True,
    )
    for marker in markers:
        sanitized = sanitized.replace(marker, "[prompt content redacted]")
    return sanitized


def _jsonl_line_content_and_ending(line: str) -> tuple[str, str]:
    if line.endswith("\r\n"):
        return line[:-2], "\r\n"
    if line.endswith("\n") or line.endswith("\r"):
        return line[:-1], line[-1]
    return line, ""


def _parse_jsonl_events(stdout: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Summarize a JSONL event stream and retain valid objects in line order."""
    event_count = 0
    invalid_line_count = 0
    event_types: set[str] = set()
    events: list[dict[str, Any]] = []
    for raw_line in stdout.splitlines(keepends=True):
        line, _ = _jsonl_line_content_and_ending(raw_line)
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except (RecursionError, TypeError, ValueError):
            invalid_line_count += 1
            continue
        if not isinstance(event, dict):
            invalid_line_count += 1
            continue
        event_count += 1
        events.append(event)
        event_type = event.get("type")
        if isinstance(event_type, str) and (event_type := event_type.strip()):
            event_types.add(event_type)
    if event_count and invalid_line_count:
        parse_status = "partial"
    elif event_count:
        parse_status = "parsed"
    elif invalid_line_count:
        parse_status = "invalid"
    else:
        parse_status = "empty"
    return (
        {
            "enabled": True,
            "parse_status": parse_status,
            "event_count": event_count,
            "invalid_line_count": invalid_line_count,
            "event_types": sorted(event_types),
        },
        events,
    )


def _extract_usage_observations(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Record only recognized numeric usage observations from turn completions."""
    observations: list[dict[str, int]] = []
    invalid_event_count = 0

    for event in events:
        if event.get("type") != "turn.completed" or "usage" not in event:
            continue

        usage = event["usage"]
        if not isinstance(usage, dict):
            invalid_event_count += 1
            continue

        observation: dict[str, int] = {}
        invalid_observation = False
        for field in _OBSERVED_USAGE_FIELDS:
            if field not in usage:
                continue
            value = usage[field]
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                invalid_observation = True
                break
            observation[field] = value

        if invalid_observation or not observation:
            invalid_event_count += 1
            continue
        observations.append(observation)

    if invalid_event_count:
        status = "invalid"
    elif observations:
        status = "observed"
    else:
        status = "absent"

    return {
        "status": status,
        "event_count": len(observations),
        "invalid_event_count": invalid_event_count,
        "events": observations,
    }


def _sanitize_json_event_value(value: Any, prompt: str) -> Any:
    if isinstance(value, str):
        return _sanitize_prompt_from_stream(value, prompt)
    if isinstance(value, list):
        return [_sanitize_json_event_value(item, prompt) for item in value]
    if isinstance(value, dict):
        return {
            key: _sanitize_json_event_value(item, prompt)
            for key, item in value.items()
        }
    return value


def _sanitize_jsonl_stdout(stdout: str, prompt: str) -> str:
    """Preserve JSONL order while sanitizing every valid event recursively."""
    sanitized_lines: list[str] = []
    for raw_line in stdout.splitlines(keepends=True):
        line, ending = _jsonl_line_content_and_ending(raw_line)
        if not line.strip():
            sanitized_lines.append(raw_line)
            continue
        try:
            event = json.loads(line)
        except (TypeError, ValueError, json.JSONDecodeError):
            sanitized_lines.append(_sanitize_prompt_from_stream(raw_line, prompt))
            continue
        if not isinstance(event, dict):
            sanitized_lines.append(_sanitize_prompt_from_stream(raw_line, prompt))
            continue
        sanitized_lines.append(
            json.dumps(
                _sanitize_json_event_value(event, prompt),
                ensure_ascii=False,
            )
            + ending
        )
    return "".join(sanitized_lines)


def _empty_result(error: str) -> RunCodexResult:
    return {
        "status": "not_started",
        "success": False,
        "return_code": None,
        "run_dir": "",
        "stdout_path": "",
        "stderr_path": "",
        "task_path": "",
        "prompt_path": "",
        "meta_path": "",
        "error": error,
        "timed_out": False,
        "started_at": None,
        "finished_at": None,
        "artifacts": [],
    }


def execute_codex_cli(
    task: dict,
    prompt: str,
    work_root: str = "tasks/runs",
    *,
    timeout_seconds: int = DEFAULT_CODEX_EXECUTION_TIMEOUT_SECONDS,
    which: Callable[[str], str | None] = shutil.which,
    run_subprocess: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    now: Callable[[], datetime] = datetime.now,
    persist_prompt: bool = True,
    return_transient_stdout: bool = False,
    model: str | None = None,
    model_reasoning_effort: str | None = None,
    emit_json: bool = False,
) -> RunCodexResult:
    try:
        timeout_seconds = validate_codex_execution_timeout_seconds(timeout_seconds)
    except ValueError as exc:
        return _empty_result(str(exc))
    codex_path = which("codex")
    try:
        cmd = build_no_confirmation_codex_command(
            skip_git_repo_check=True,
            model=model,
            model_reasoning_effort=model_reasoning_effort,
        )
    except ValueError as exc:
        return _empty_result(str(exc))
    effective_prompt = build_no_confirmation_execution_prompt(prompt)
    if emit_json:
        cmd.insert(-1, "--json")
    repo_path_raw = str(task.get("repo_path", "")).strip()
    repo_path = Path(repo_path_raw).expanduser() if repo_path_raw else None
    cwd = str(repo_path) if repo_path else ""

    if codex_path is None:
        return _empty_result(
            "Codex CLI is not available in PATH. Install it and ensure `codex` is runnable."
        )

    if not repo_path_raw:
        return _empty_result("repo_path is required.")
    if not repo_path.exists():
        return _empty_result(f"repo_path does not exist: {repo_path}")
    if not repo_path.is_dir():
        return _empty_result(f"repo_path is not a directory: {repo_path}")

    timestamp = now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path(work_root) / timestamp
    suffix = 1
    while run_dir.exists():
        run_dir = Path(work_root) / f"{timestamp}_{suffix}"
        suffix += 1
    run_dir.mkdir(parents=True, exist_ok=False)

    task_path = run_dir / "task.json"
    prompt_path = run_dir / "prompt.txt"
    stdout_path = run_dir / "stdout.txt"
    stderr_path = run_dir / "stderr.txt"
    meta_path = run_dir / "meta.json"

    task_path.write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")
    if persist_prompt:
        prompt_path.write_text(effective_prompt, encoding="utf-8")

    return_code = None
    stdout_text = ""
    stderr_text = ""
    timed_out = False
    started_at = now().isoformat(timespec="seconds")

    try:
        completed = run_subprocess(
            cmd,
            input=effective_prompt,
            text=True,
            capture_output=True,
            cwd=cwd,
            timeout=timeout_seconds,
        )
        return_code = completed.returncode
        stdout_text = _to_text(completed.stdout)
        stderr_text = _to_text(completed.stderr)
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        timeout_stdout = exc.stdout if exc.stdout is not None else exc.output
        stdout_text = _to_text(timeout_stdout)
        timeout_message = f"Codex timed out after {timeout_seconds} seconds."
        timeout_stderr = _to_text(exc.stderr)
        if timeout_stderr:
            stderr_text = f"{timeout_stderr}\n{timeout_message}"
        else:
            stderr_text = timeout_message
    except Exception as exc:
        stderr_text = f"Failed to run Codex CLI ({type(exc).__name__}): {exc}"
    finished_at = now().isoformat(timespec="seconds")

    success = return_code == 0
    status: RunCodexStatus
    if timed_out:
        status = "timed_out"
    elif success:
        status = "completed"
    else:
        status = "failed"

    transient_stdout = stdout_text
    json_events: dict[str, Any] | None = None
    if emit_json:
        if not persist_prompt:
            stdout_text = _sanitize_jsonl_stdout(stdout_text, effective_prompt)
            stderr_text = _sanitize_prompt_from_stream(stderr_text, effective_prompt)
        json_events, parsed_events = _parse_jsonl_events(stdout_text)
        json_events["usage"] = _extract_usage_observations(parsed_events)
    elif not persist_prompt:
        stdout_text = _sanitize_prompt_from_stream(stdout_text, effective_prompt)
        stderr_text = _sanitize_prompt_from_stream(stderr_text, effective_prompt)
    stdout_path.write_text(stdout_text, encoding="utf-8")
    stderr_path.write_text(stderr_text, encoding="utf-8")

    meta = {
        "timestamp": timestamp,
        "repo_path": cwd,
        "run_dir": str(run_dir),
        "started_at": started_at,
        "finished_at": finished_at,
        "command": cmd,
        "cwd": cwd,
        "codex_path": codex_path,
        "success": success,
        "return_code": return_code,
        "timed_out": timed_out,
        "timeout_seconds": timeout_seconds,
    }
    if not persist_prompt:
        meta["prompt_sha256"] = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        meta["prompt_bytes"] = len(prompt.encode("utf-8"))
    if json_events is not None:
        meta["json_events"] = json_events
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    artifacts: list[RunCodexArtifact] = [
        {"name": "task", "path": str(task_path)},
        {"name": "stdout", "path": str(stdout_path)},
        {"name": "stderr", "path": str(stderr_path)},
        {"name": "meta", "path": str(meta_path)},
    ]
    if persist_prompt:
        artifacts.insert(1, {"name": "prompt", "path": str(prompt_path)})

    result: RunCodexResult = {
        "status": status,
        "success": success,
        "return_code": return_code,
        "run_dir": str(run_dir),
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "task_path": str(task_path),
        "prompt_path": str(prompt_path) if persist_prompt else "",
        "meta_path": str(meta_path),
        "error": stderr_text if (return_code is None or return_code != 0) else "",
        "timed_out": timed_out,
        "started_at": started_at,
        "finished_at": finished_at,
        "artifacts": artifacts,
    }
    if return_transient_stdout:
        result["transient_stdout"] = transient_stdout
    return result
