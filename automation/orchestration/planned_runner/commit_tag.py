from __future__ import annotations

from pathlib import Path
import json
import subprocess
from typing import Any, Mapping


DEFAULT_COMMIT_TAG_ENABLE_TOKEN = "ENABLE_LOCAL_COMMIT_TAG_EXECUTION"


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
