from __future__ import annotations

import json
import hashlib
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Callable, Literal, NotRequired, TypedDict


RunCodexStatus = Literal["completed", "failed", "timed_out", "not_started"]

DEFAULT_CODEX_EXECUTION_TIMEOUT_SECONDS = 3600
MAX_CODEX_EXECUTION_TIMEOUT_SECONDS = 18000
DEFAULT_VALIDATION_TIMEOUT_SECONDS = 3600
DEFAULT_COMPLETION_EVALUATOR_TIMEOUT_SECONDS = 3600
MAX_COMPLETION_EVALUATOR_TIMEOUT_SECONDS = 7200
DEFAULT_COMPLETION_REWORK_TIMEOUT_SECONDS = 7200


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
) -> RunCodexResult:
    try:
        timeout_seconds = validate_codex_execution_timeout_seconds(timeout_seconds)
    except ValueError as exc:
        return _empty_result(str(exc))
    codex_path = which("codex")
    cmd = ["codex", "exec", "--skip-git-repo-check", prompt]
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
        prompt_path.write_text(prompt, encoding="utf-8")

    return_code = None
    stdout_text = ""
    stderr_text = ""
    timed_out = False
    started_at = now().isoformat(timespec="seconds")

    try:
        completed = run_subprocess(
            cmd,
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
    if not persist_prompt:
        stdout_text = _sanitize_prompt_from_stream(stdout_text, prompt)
        stderr_text = _sanitize_prompt_from_stream(stderr_text, prompt)
    stdout_path.write_text(stdout_text, encoding="utf-8")
    stderr_path.write_text(stderr_text, encoding="utf-8")

    meta = {
        "timestamp": timestamp,
        "repo_path": cwd,
        "run_dir": str(run_dir),
        "started_at": started_at,
        "finished_at": finished_at,
        "command": cmd if persist_prompt else [*cmd[:-1], "[prompt redacted]"],
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
