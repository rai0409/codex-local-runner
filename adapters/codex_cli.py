from __future__ import annotations

from pathlib import Path
from typing import Any

from adapters.base import ProviderAdapter
from run_codex import run_codex
from verify.runner import run_validation_commands
from workspace.worktree import cleanup_git_worktree
from workspace.worktree import prepare_git_worktree


def _verify_not_run(reason: str, summary: str) -> dict[str, Any]:
    return {
        "status": "not_run",
        "success": True,
        "commands": [],
        "error": "",
        "summary": summary,
        "reason": reason,
    }


class CodexCliAdapter(ProviderAdapter):
    def __init__(self) -> None:
        super().__init__(name="codex_cli")

    def dispatch(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("codex_cli provider execution is not implemented in Phase 1")

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        prompt = str(payload.get("prompt", "")).strip()
        work_dir = Path(str(payload.get("work_dir", ".")).strip() or ".")
        repo_path = str(Path(str(payload.get("repo_path", ".")).strip() or ".").expanduser())
        payload_validation_commands = payload.get("validation_commands", [])
        validation_commands = (
            [str(command) for command in payload_validation_commands]
            if isinstance(payload_validation_commands, list)
            else []
        )
        worktree_result = prepare_git_worktree(
            source_repo_path=repo_path,
            worktree_parent=str(work_dir / "worktrees"),
        )
        if not worktree_result["created"]:
            return {
                "adapter": self.name,
                "status": "failed",
                "started_at": None,
                "finished_at": None,
                "artifacts": [],
                "error": worktree_result["error"] or "failed to prepare git worktree",
                "return_code": None,
                "verify": _verify_not_run(
                    reason="worktree_prepare_failed",
                    summary="validation not run: worktree preparation failed.",
                ),
            }

        cleanup_error = ""
        try:
            execution_result = run_codex(
                task={"repo_path": worktree_result["worktree_path"]},
                prompt=prompt,
                work_root=str(work_dir / "execution_runs"),
            )
            execution_status = execution_result.get("status") or (
                "completed" if execution_result.get("success") else "failed"
            )
            if execution_status == "completed":
                verify_result = run_validation_commands(
                    validation_commands=validation_commands,
                    cwd=worktree_result["worktree_path"],
                )
            else:
                verify_result = _verify_not_run(
                    reason=f"execution_status_{execution_status}",
                    summary=f"validation not run: execution status is {execution_status}.",
                )
        finally:
            if worktree_result["cleanup_needed"]:
                cleanup_result = cleanup_git_worktree(
                    source_repo_path=repo_path,
                    worktree_path=worktree_result["worktree_path"],
                    branch_name=worktree_result["branch_name"],
                )
                cleanup_error = cleanup_result["error"]

        artifacts: list[str] = []
        for item in execution_result.get("artifacts", []):
            if isinstance(item, dict):
                path = str(item.get("path", "")).strip()
                if path:
                    artifacts.append(path)
        if not artifacts:
            artifacts = [
                str(execution_result.get("stdout_path", "")),
                str(execution_result.get("stderr_path", "")),
                str(execution_result.get("meta_path", "")),
            ]
            artifacts = [item for item in artifacts if item]

        execution_error = str(execution_result.get("error", "")).strip()
        if cleanup_error and execution_status != "completed":
            if execution_error:
                execution_error = f"{execution_error}\nWorktree cleanup failed: {cleanup_error}"
            else:
                execution_error = f"Worktree cleanup failed: {cleanup_error}"

        return {
            "adapter": self.name,
            "status": execution_status,
            "started_at": execution_result.get("started_at"),
            "finished_at": execution_result.get("finished_at"),
            "artifacts": artifacts,
            "error": execution_error or None,
            "return_code": execution_result.get("return_code"),
            "verify": verify_result,
        }
