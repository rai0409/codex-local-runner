from __future__ import annotations

from pathlib import Path
import json
import subprocess
from typing import Any, Mapping


DEFAULT_COMMIT_TAG_ENABLE_TOKEN = "ENABLE_LOCAL_COMMIT_TAG_EXECUTION"
SANDBOX_COMMIT_TAG_ENABLE_TOKEN = "ENABLE_SANDBOX_COMMIT_TAG_EXECUTION"
_MAIN_REPO_ROOT = Path(__file__).resolve().parents[3]
_SANDBOX_ROOT_PREFIXES = ("/tmp/",)


def _git_status_changed_files(repo: Path) -> tuple[list[str], str]:
    completed = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return [], _normalize_text(completed.stderr, default="git_status_failed")
    files: list[str] = []
    for line in completed.stdout.splitlines():
        if not line.strip():
            continue
        path_text = line[3:].strip()
        if " -> " in path_text:
            path_text = path_text.split(" -> ", 1)[1].strip()
        path_text = path_text.replace("\\", "/").lstrip("./")
        if path_text:
            files.append(path_text)
    return sorted(set(files)), ""


def _tag_exists(repo: Path, tag_name: str) -> bool:
    completed = subprocess.run(
        ["git", "tag", "-l", tag_name],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    return bool(completed.stdout.strip())


def execute_sandbox_commit_tag(
    *,
    repo_path: str | Path,
    allowed_files: list[str] | tuple[str, ...],
    artifact_dir: str | Path,
    task_id: str = "",
    commit_message: str = "",
    tag_name: str = "",
    forbidden_paths: list[str] | tuple[str, ...] | None = None,
    enabled: bool = False,
    explicit_enable_token: str = "",
    required_enable_token: str = SANDBOX_COMMIT_TAG_ENABLE_TOKEN,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    """Gated commit+tag that can only ever execute inside a /tmp sandbox repo.

    Policy (all must hold before any git mutation):
    - explicit enable token matches,
    - repo resolves under /tmp and is not (inside) the main repo,
    - every changed file is in allowed_files and changes are non-empty,
    - no forbidden path exists in the repo,
    - the tag does not already exist.
    """
    artifact_root = Path(artifact_dir)
    result_path = artifact_root / "sandbox_commit_tag_result.json"
    repo = Path(repo_path).resolve()
    task_slug = _normalize_text(task_id, default="sandbox-task")
    message = _normalize_text(commit_message, default=f"sandbox auto commit: {task_slug}")
    tag = _normalize_text(tag_name, default=f"sandbox-{task_slug}")
    allowed = _normalize_string_list(allowed_files)
    forbidden = _normalize_string_list(forbidden_paths or [])

    result: dict[str, Any] = {
        "status": "blocked",
        "executed": False,
        "blocked_reason": "none",
        "next_action": "manual_review_required",
        "repo_path": repo.as_posix(),
        "sandbox_only": True,
        "explicit_enable_required": True,
        "allowed_files": allowed,
        "forbidden_paths": forbidden,
        "changed_files": [],
        "commit_message": message,
        "tag_name": tag,
        "commit_sha": "",
        "commit_performed": False,
        "tag_performed": False,
        "remote_operations_allowed": False,
        "result_path": result_path.as_posix(),
    }

    def _finish(reason: str) -> dict[str, Any]:
        result["blocked_reason"] = reason
        artifact_root.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return result

    if not (enabled and explicit_enable_token == required_enable_token):
        return _finish("explicit_enable_required")
    repo_text = repo.as_posix()
    if not any(repo_text.startswith(prefix) for prefix in _SANDBOX_ROOT_PREFIXES):
        return _finish("repo_not_sandbox")
    main_root = _MAIN_REPO_ROOT.resolve()
    if repo == main_root or main_root in repo.parents or repo in main_root.parents:
        return _finish("repo_is_main_repo")
    if not (repo / ".git").exists():
        return _finish("repo_not_git")
    if not allowed:
        return _finish("missing_allowed_files")

    all_changed, status_error = _git_status_changed_files(repo)
    # Python bytecode caches are generated artifacts (e.g. by verify commands),
    # never source changes: they are ignored by policy and never committed.
    ignored_generated = [
        path for path in all_changed
        if "__pycache__" in path.split("/") or path.rstrip("/").endswith("__pycache__") or path.endswith(".pyc")
    ]
    changed_files = [path for path in all_changed if path not in ignored_generated]
    result["changed_files"] = changed_files
    result["ignored_generated_paths"] = ignored_generated
    if status_error:
        return _finish("git_status_failed")
    if not changed_files:
        return _finish("no_changes_to_commit")
    outside = [path for path in changed_files if path not in allowed]
    if outside:
        result["changes_outside_allowed_files"] = outside
        return _finish("changes_outside_allowed_files")
    present_forbidden = [path for path in forbidden if (repo / path).exists()]
    if present_forbidden:
        result["forbidden_paths_present"] = present_forbidden
        return _finish("forbidden_path_present")
    if _tag_exists(repo, tag):
        return _finish("tag_already_exists")

    commands = [
        ["git", "add", "--", *changed_files],
        [
            "git",
            "-c", "user.email=sandbox-runner@local",
            "-c", "user.name=sandbox-runner",
            "commit", "-m", message,
        ],
        ["git", "tag", tag],
    ]
    for command in commands:
        completed = subprocess.run(
            command,
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
            timeout=max(1, int(timeout_seconds)),
        )
        if completed.returncode != 0:
            result["failed_command"] = command
            result["failed_stderr"] = (completed.stderr or "")[-2000:]
            return _finish("commit_tag_command_failed")
    result["executed"] = True
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    result.update(
        {
            "status": "success",
            "next_action": "success_handoff",
            "commit_sha": sha,
            "commit_performed": True,
            "tag_performed": True,
        }
    )
    return _finish("none")


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple, set)):
        return []
    items: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = _normalize_text(item).replace("\\", "/").lstrip("./")
        if text and text not in seen:
            seen.add(text)
            items.append(text)
    return items


def build_commit_tag_execution_gate(
    *,
    repo_path: str | Path,
    commit_message: str = "",
    tag_name: str = "",
    changed_files: list[str] | tuple[str, ...] | None = None,
    artifact_dir: str | Path = "artifacts/runtime_commands/commit_tag",
    enabled: bool = False,
    explicit_enable_token: str = "",
    required_enable_token: str = DEFAULT_COMMIT_TAG_ENABLE_TOKEN,
) -> dict[str, Any]:
    artifact_root = Path(artifact_dir)
    stdout_path = artifact_root / "commit_tag_stdout.txt"
    stderr_path = artifact_root / "commit_tag_stderr.txt"
    result_path = artifact_root / "commit_tag_result.json"
    enabled_now = bool(enabled and explicit_enable_token == required_enable_token)
    blocked_reason = "none" if enabled_now else "explicit_enable_required"
    if enabled_now and not _normalize_text(commit_message):
        blocked_reason = "missing_commit_message"
    if enabled_now and not _normalize_text(tag_name):
        blocked_reason = "missing_tag_name"
    return {
        "status": "ready" if enabled_now and blocked_reason == "none" else "blocked",
        "next_action": "execute_local_commit_tag" if enabled_now and blocked_reason == "none" else "manual_review_required",
        "blocked_reason": blocked_reason,
        "runtime_posture": "local_only_commit_tag_gate" if enabled_now else "dry_run_disabled",
        "artifact_paths": [artifact_root.as_posix()],
        "enabled": enabled_now,
        "explicit_enable_required": True,
        "executed": False,
        "command": "git add -- <files> && git commit -m <message> && git tag <tag>",
        "argv": [],
        "stdout_path": stdout_path.as_posix(),
        "stderr_path": stderr_path.as_posix(),
        "result_path": result_path.as_posix(),
        "repo_path": str(repo_path),
        "commit_message": _normalize_text(commit_message),
        "tag_name": _normalize_text(tag_name),
        "changed_files": _normalize_string_list(changed_files or []),
        "remote_operations_allowed": False,
    }


def execute_bounded_commit_tag(
    *,
    repo_path: str | Path,
    commit_message: str,
    tag_name: str,
    changed_files: list[str] | tuple[str, ...],
    artifact_dir: str | Path = "artifacts/runtime_commands/commit_tag",
    enabled: bool = False,
    explicit_enable_token: str = "",
    required_enable_token: str = DEFAULT_COMMIT_TAG_ENABLE_TOKEN,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    gate = build_commit_tag_execution_gate(
        repo_path=repo_path,
        commit_message=commit_message,
        tag_name=tag_name,
        changed_files=list(changed_files),
        artifact_dir=artifact_dir,
        enabled=enabled,
        explicit_enable_token=explicit_enable_token,
        required_enable_token=required_enable_token,
    )
    artifact_root = Path(artifact_dir)
    stdout_path = Path(gate["stdout_path"])
    stderr_path = Path(gate["stderr_path"])
    result_path = Path(gate["result_path"])
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stdout_path.write_text("", encoding="utf-8")
    stderr_path.write_text("", encoding="utf-8")
    result = dict(gate)
    if gate["status"] != "ready":
        result["next_action"] = "manual_review_required"
        result_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return result

    repo = Path(repo_path)
    argv = [
        ["git", "add", "--", *_normalize_string_list(changed_files)],
        ["git", "commit", "-m", _normalize_text(commit_message)],
        ["git", "tag", _normalize_text(tag_name)],
    ]
    result.update({"argv": argv, "executed": True})
    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []
    for command in argv:
        completed = subprocess.run(
            command,
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
            timeout=max(1, int(timeout_seconds)),
        )
        stdout_chunks.append(completed.stdout or "")
        stderr_chunks.append(completed.stderr or "")
        if completed.returncode != 0:
            result.update(
                {
                    "status": "failed",
                    "next_action": "targeted_fix_required",
                    "blocked_reason": "commit_tag_command_failed",
                    "returncode": completed.returncode,
                    "failed_command": command,
                }
            )
            break
    else:
        result.update(
            {
                "status": "success",
                "next_action": "success_handoff",
                "blocked_reason": "none",
                "returncode": 0,
            }
        )
    stdout_path.write_text("".join(stdout_chunks), encoding="utf-8")
    stderr_path.write_text("".join(stderr_chunks), encoding="utf-8")
    result["artifact_paths"] = [artifact_root.as_posix()]
    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result
