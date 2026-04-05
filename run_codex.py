from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


def run_codex(task: dict, prompt: str, work_root: str = "tasks/runs") -> dict:
    codex_path = shutil.which("codex")
    cmd = ["codex", "exec", "--skip-git-repo-check", prompt]
    repo_path_raw = str(task.get("repo_path", "")).strip()
    repo_path = Path(repo_path_raw).expanduser() if repo_path_raw else None
    cwd = str(repo_path) if repo_path else ""
    timeout_seconds = 600

    if codex_path is None:
        return {
            "success": False,
            "return_code": None,
            "run_dir": "",
            "stdout_path": "",
            "stderr_path": "",
            "task_path": "",
            "prompt_path": "",
            "meta_path": "",
            "error": "Codex CLI is not available in PATH. Install it and ensure `codex` is runnable.",
            "timed_out": False,
        }

    if not repo_path_raw:
        return {
            "success": False,
            "return_code": None,
            "run_dir": "",
            "stdout_path": "",
            "stderr_path": "",
            "task_path": "",
            "prompt_path": "",
            "meta_path": "",
            "error": "repo_path is required.",
            "timed_out": False,
        }
    if not repo_path.exists():
        return {
            "success": False,
            "return_code": None,
            "run_dir": "",
            "stdout_path": "",
            "stderr_path": "",
            "task_path": "",
            "prompt_path": "",
            "meta_path": "",
            "error": f"repo_path does not exist: {repo_path}",
            "timed_out": False,
        }
    if not repo_path.is_dir():
        return {
            "success": False,
            "return_code": None,
            "run_dir": "",
            "stdout_path": "",
            "stderr_path": "",
            "task_path": "",
            "prompt_path": "",
            "meta_path": "",
            "error": f"repo_path is not a directory: {repo_path}",
            "timed_out": False,
        }

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
        stdout_text = completed.stdout or ""
        stderr_text = completed.stderr or ""
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout_text = exc.stdout or ""
        timeout_message = f"Codex timed out after {timeout_seconds} seconds."
        if exc.stderr:
            stderr_text = f"{exc.stderr}\n{timeout_message}"
        else:
            stderr_text = timeout_message
    except Exception as exc:
        stderr_text = f"Failed to run Codex CLI ({type(exc).__name__}): {exc}"
    finished_at = datetime.now().isoformat(timespec="seconds")

    success = return_code == 0
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

    return {
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
    }
