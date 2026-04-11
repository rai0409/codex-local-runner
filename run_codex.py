from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Literal, TypedDict


RunCodexStatus = Literal["completed", "failed", "timed_out", "not_started"]


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


def _to_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


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


def run_codex(task: dict, prompt: str, work_root: str = "tasks/runs") -> RunCodexResult:
    codex_path = shutil.which("codex")
    cmd = ["codex", "exec", "--skip-git-repo-check", prompt]
    repo_path_raw = str(task.get("repo_path", "")).strip()
    repo_path = Path(repo_path_raw).expanduser() if repo_path_raw else None
    cwd = str(repo_path) if repo_path else ""
    timeout_seconds = 600

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

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
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
    prompt_path.write_text(prompt, encoding="utf-8")

    return_code = None
    stdout_text = ""
    stderr_text = ""
    timed_out = False
    started_at = datetime.now().isoformat(timespec="seconds")

    try:
        completed = subprocess.run(
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
    finished_at = datetime.now().isoformat(timespec="seconds")

    success = return_code == 0
    status: RunCodexStatus
    if timed_out:
        status = "timed_out"
    elif success:
        status = "completed"
    else:
        status = "failed"

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
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    artifacts: list[RunCodexArtifact] = [
        {"name": "task", "path": str(task_path)},
        {"name": "prompt", "path": str(prompt_path)},
        {"name": "stdout", "path": str(stdout_path)},
        {"name": "stderr", "path": str(stderr_path)},
        {"name": "meta", "path": str(meta_path)},
    ]

    return {
        "status": status,
        "success": success,
        "return_code": return_code,
        "run_dir": str(run_dir),
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "task_path": str(task_path),
        "prompt_path": str(prompt_path),
        "meta_path": str(meta_path),
        "error": stderr_text if (return_code is None or return_code != 0) else "",
        "timed_out": timed_out,
        "started_at": started_at,
        "finished_at": finished_at,
        "artifacts": artifacts,
    }
