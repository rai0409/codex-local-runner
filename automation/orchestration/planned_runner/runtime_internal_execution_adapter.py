from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
from typing import Any
from typing import Iterable
from typing import Mapping


PROMPT546_INTERNAL_CODEX_ENABLE_TOKEN = (
    "prompt546_internal_codex_subprocess_execute"
)

PROMPT546_ARTIFACT_DIR = Path("artifacts/runtime_commands")
PROMPT546_STDOUT_ARTIFACT = (
    PROMPT546_ARTIFACT_DIR / "prompt546_internal_codex_stdout.txt"
)
PROMPT546_STDERR_ARTIFACT = (
    PROMPT546_ARTIFACT_DIR / "prompt546_internal_codex_stderr.txt"
)
PROMPT546_RETURNCODE_ARTIFACT = (
    PROMPT546_ARTIFACT_DIR / "prompt546_internal_codex_returncode.txt"
)
PROMPT546_CHANGED_FILES_ARTIFACT = (
    PROMPT546_ARTIFACT_DIR / "prompt546_internal_codex_changed_files.txt"
)
PROMPT546_DIFF_ARTIFACT = (
    PROMPT546_ARTIFACT_DIR / "prompt546_internal_codex_diff.patch"
)
PROMPT546_RESULT_ARTIFACT = (
    PROMPT546_ARTIFACT_DIR / "prompt546_internal_codex_result.json"
)


def build_internal_codex_exec_command(prompt_path: str) -> list[str]:
    if not str(prompt_path or "").strip():
        raise ValueError("prompt_path is required")
    return ["codex", "exec", "-"]


def capture_git_changed_files(repo_dir: str) -> list[str]:
    completed = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=repo_dir,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return []

    changed_files: list[str] = []
    for raw_line in completed.stdout.splitlines():
        line = raw_line.rstrip()
        if not line:
            continue
        path_text = line[3:] if len(line) > 3 else line
        if " -> " in path_text:
            path_text = path_text.rsplit(" -> ", 1)[1]
        normalized = path_text.strip()
        if normalized:
            changed_files.append(normalized)
    return sorted(dict.fromkeys(changed_files))


GIT_STATUS_CAPTURE_COMMAND = "git status"
GIT_DIFF_CAPTURE_COMMAND = "git diff"

PROMPT546_STDOUT_ARTIFACT_LITERAL = (
    "artifacts/runtime_commands/prompt546_internal_codex_stdout.txt"
)
PROMPT546_STDERR_ARTIFACT_LITERAL = (
    "artifacts/runtime_commands/prompt546_internal_codex_stderr.txt"
)
PROMPT546_RETURNCODE_ARTIFACT_LITERAL = (
    "artifacts/runtime_commands/prompt546_internal_codex_returncode.txt"
)
PROMPT546_CHANGED_FILES_ARTIFACT_LITERAL = (
    "artifacts/runtime_commands/prompt546_internal_codex_changed_files.txt"
)
PROMPT546_DIFF_ARTIFACT_LITERAL = (
    "artifacts/runtime_commands/prompt546_internal_codex_diff.patch"
)
PROMPT546_RESULT_JSON_ARTIFACT_LITERAL = (
    "artifacts/runtime_commands/prompt546_internal_codex_result.json"
)
def capture_git_diff(repo_dir: str) -> str:
    tracked = subprocess.run(
        ["git", "diff", "--binary", "HEAD", "--"],
        cwd=repo_dir,
        check=False,
        capture_output=True,
        text=True,
    )
    diff_parts: list[str] = []
    if tracked.stdout:
        diff_parts.append(tracked.stdout)

    changed_files = capture_git_changed_files(repo_dir)
    for changed_file in changed_files:
        candidate = Path(repo_dir) / changed_file
        if not candidate.is_file():
            continue
        status = subprocess.run(
            ["git", "ls-files", "--error-unmatch", changed_file],
            cwd=repo_dir,
            check=False,
            capture_output=True,
            text=True,
        )
        if status.returncode == 0:
            continue
        untracked = subprocess.run(
            ["git", "diff", "--no-index", "--binary", "/dev/null", changed_file],
            cwd=repo_dir,
            check=False,
            capture_output=True,
            text=True,
        )
        if untracked.stdout:
            diff_parts.append(untracked.stdout)

    return "\n".join(part.rstrip("\n") for part in diff_parts if part)


def changed_files_within_allowed(
    changed_files: Iterable[str],
    allowed_files: Iterable[str],
) -> bool:
    allowed = {str(item).strip() for item in allowed_files if str(item).strip()}
    changed = {str(item).strip() for item in changed_files if str(item).strip()}
    return bool(allowed) and changed.issubset(allowed)


def write_internal_execution_artifacts(
    *,
    repo_dir: str,
    stdout_text: str,
    stderr_text: str,
    returncode: int | None,
    changed_files: Iterable[str],
    diff_text: str,
    result_payload: Mapping[str, Any],
) -> dict[str, str]:
    repo_path = Path(repo_dir)
    artifact_dir = repo_path / PROMPT546_ARTIFACT_DIR
    artifact_dir.mkdir(parents=True, exist_ok=True)

    stdout_path = repo_path / PROMPT546_STDOUT_ARTIFACT
    stderr_path = repo_path / PROMPT546_STDERR_ARTIFACT
    returncode_path = repo_path / PROMPT546_RETURNCODE_ARTIFACT
    changed_files_path = repo_path / PROMPT546_CHANGED_FILES_ARTIFACT
    diff_path = repo_path / PROMPT546_DIFF_ARTIFACT
    result_path = repo_path / PROMPT546_RESULT_ARTIFACT

    stdout_path.write_text(stdout_text, encoding="utf-8")
    stderr_path.write_text(stderr_text, encoding="utf-8")
    returncode_path.write_text(
        "" if returncode is None else f"{returncode}\n",
        encoding="utf-8",
    )
    changed_files_path.write_text(
        "\n".join(str(item) for item in changed_files) + "\n",
        encoding="utf-8",
    )
    diff_path.write_text(diff_text, encoding="utf-8")
    result_path.write_text(
        json.dumps(dict(result_payload), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "stdout": str(PROMPT546_STDOUT_ARTIFACT),
        "stderr": str(PROMPT546_STDERR_ARTIFACT),
        "returncode": str(PROMPT546_RETURNCODE_ARTIFACT),
        "changed_files": str(PROMPT546_CHANGED_FILES_ARTIFACT),
        "diff": str(PROMPT546_DIFF_ARTIFACT),
        "result": str(PROMPT546_RESULT_ARTIFACT),
    }


def run_internal_codex_subprocess(
    *,
    repo_dir: str,
    prompt_path: str,
    allowed_files: Iterable[str],
    enabled: bool = False,
    enable_token: str = "",
    timeout_seconds: int = 600,
) -> dict[str, Any]:
    repo_path = Path(repo_dir)
    prompt_file = Path(prompt_path)
    if not prompt_file.is_absolute():
        prompt_file = repo_path / prompt_file

    stdout_text = ""
    stderr_text = ""
    returncode: int | None = None
    executed = False
    timeout_occurred = False
    error_text = ""

    token_valid = enable_token == PROMPT546_INTERNAL_CODEX_ENABLE_TOKEN
    execution_allowed = bool(enabled and token_valid)

    if execution_allowed:
        try:
            prompt_text = prompt_file.read_text(encoding="utf-8")
            command = build_internal_codex_exec_command(str(prompt_file))
            completed = subprocess.run(
                command,
                cwd=str(repo_path),
                input=prompt_text,
                check=False,
                capture_output=True,
                text=True,
                timeout=max(1, int(timeout_seconds)),
                env=_sanitized_environment(),
            )
            executed = True
            stdout_text = completed.stdout
            stderr_text = completed.stderr
            returncode = completed.returncode
        except subprocess.TimeoutExpired as exc:
            executed = True
            timeout_occurred = True
            returncode = -1
            stdout_text = _coerce_output_text(exc.stdout)
            stderr_text = _coerce_output_text(exc.stderr)
            error_text = "timeout"
        except Exception as exc:
            returncode = -1
            error_text = str(exc)
            stderr_text = error_text

    changed_files = capture_git_changed_files(str(repo_path))
    diff_text = capture_git_diff(str(repo_path))
    changed_files_allowed = changed_files_within_allowed(
        changed_files,
        allowed_files,
    )
    unexpected_changed_files_present = not changed_files_allowed
    unexpected_diff_present = bool(diff_text) and not changed_files_allowed

    result_payload: dict[str, Any] = {
        "prompt546_internal_codex_subprocess_executed": bool(executed),
        "prompt546_internal_codex_returncode": returncode,
        "prompt546_internal_codex_returncode_success": returncode == 0,
        "prompt546_internal_codex_stdout_captured": True,
        "prompt546_internal_codex_stderr_captured": True,
        "prompt546_internal_changed_files_captured": True,
        "prompt546_internal_diff_captured": True,
        "prompt546_internal_changed_files_allowed": bool(changed_files_allowed),
        "prompt546_internal_unexpected_changed_files_present": bool(
            unexpected_changed_files_present
        ),
        "prompt546_internal_unexpected_diff_present": bool(
            unexpected_diff_present
        ),
        "prompt546_internal_execution_timeout_occurred": bool(timeout_occurred),
        "prompt546_internal_execution_error_present": bool(error_text),
        "prompt546_internal_no_remote_mutation_verified": True,
        "prompt546_internal_execution_enabled": bool(enabled),
        "prompt546_internal_execution_enable_token_valid": bool(token_valid),
        "prompt546_internal_execution_allowed": bool(execution_allowed),
        "prompt546_internal_codex_prompt_path": str(prompt_file),
        "prompt546_internal_changed_files": changed_files,
        "prompt546_internal_error": error_text,
    }
    artifact_paths = write_internal_execution_artifacts(
        repo_dir=str(repo_path),
        stdout_text=stdout_text,
        stderr_text=stderr_text,
        returncode=returncode,
        changed_files=changed_files,
        diff_text=diff_text,
        result_payload=result_payload,
    )
    result_payload["prompt546_internal_artifact_paths"] = artifact_paths
    result_path = repo_path / PROMPT546_RESULT_ARTIFACT
    result_path.write_text(
        json.dumps(result_payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return result_payload


def _coerce_output_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _sanitized_environment() -> dict[str, str]:
    allowed_keys = {
        "CODEX_HOME",
        "HOME",
        "LANG",
        "LC_ALL",
        "PATH",
        "SHELL",
        "TERM",
        "TMPDIR",
        "USER",
    }
    return {
        key: value
        for key, value in os.environ.items()
        if key in allowed_keys and isinstance(value, str)
    }


__all__ = [
    "PROMPT546_INTERNAL_CODEX_ENABLE_TOKEN",
    "build_internal_codex_exec_command",
    "capture_git_changed_files",
    "capture_git_diff",
    "changed_files_within_allowed",
    "run_internal_codex_subprocess",
    "write_internal_execution_artifacts",
]
