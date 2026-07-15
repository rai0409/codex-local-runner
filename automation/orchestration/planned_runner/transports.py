from __future__ import annotations

from pathlib import Path
from typing import Any
from typing import Mapping

from automation.execution.codex_executor_adapter import CodexExecutionTransport
from automation.orchestration.planned_runner.utils import _normalize_text


class DryRunCodexExecutionTransport(CodexExecutionTransport):
    def __init__(self, *, status_by_pr_id: Mapping[str, str] | None = None) -> None:
        self._status_by_pr_id = dict(status_by_pr_id or {})
        self._runs: dict[str, dict[str, Any]] = {}

    def launch_job(
        self,
        *,
        job_id: str,
        pr_id: str,
        prompt_path: str,
        work_dir: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        run_id = f"{job_id}:{pr_id}:dry-run"
        status = _normalize_text(self._status_by_pr_id.get(pr_id), default="not_started").lower()
        if status not in {"not_started", "failed", "completed", "timed_out", "running"}:
            status = "not_started"

        record = {
            "run_id": run_id,
            "job_id": job_id,
            "pr_id": pr_id,
            "status": status,
            "prompt_path": prompt_path,
            "work_dir": work_dir,
            "metadata": dict(metadata or {}),
        }
        self._runs[run_id] = record
        return {
            "run_id": run_id,
            "status": status,
            "dry_run": True,
        }

    def poll_status(self, *, run_id: str) -> Mapping[str, Any]:
        run = self._runs.get(run_id)
        if run is None:
            return {
                "run_id": run_id,
                "status": "failed",
                "error": "unknown_run_id",
            }
        return {
            "run_id": run_id,
            "status": run["status"],
            "dry_run": True,
        }

    def collect_artifacts(self, *, run_id: str) -> Mapping[str, Any]:
        run = self._runs.get(run_id)
        if run is None:
            return {
                "run_id": run_id,
                "stdout_path": "",
                "stderr_path": "",
                "artifacts": [],
            }
        work_dir = Path(str(run["work_dir"]))
        return {
            "run_id": run_id,
            "stdout_path": str(work_dir / "stdout.txt"),
            "stderr_path": str(work_dir / "stderr.txt"),
            "artifacts": [],
            "dry_run": True,
        }


__all__ = ["DryRunCodexExecutionTransport"]
