from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Mapping

from orchestrator.codex_execution import execute_codex_cli
from verify.runner import run_validation_commands


def _iso_now(now: Callable[[], datetime]) -> str:
    return now().isoformat(timespec="seconds")


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _normalize_string_list(value: Any, *, sort_items: bool = False) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = str(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    if sort_items:
        return sorted(out)
    return out


def _normalize_status(value: Any) -> str:
    text = _normalize_text(value, default="failed").lower()
    allowed = {"completed", "failed", "timed_out", "not_started", "running"}
    if text not in allowed:
        return "failed"
    return text


def _normalize_verify_status(value: Any) -> str:
    text = _normalize_text(value, default="not_run").lower()
    if text not in {"passed", "failed", "not_run"}:
        return "not_run"
    return text


def _as_non_negative_int(value: Any, *, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return max(0, value)
    if isinstance(value, str):
        text = value.strip()
        if text and text.isdigit():
            return int(text)
    return default


def _derive_failure_type(*, status: str, verify_status: str) -> str | None:
    if status == "not_started":
        return "transport_submission_failure"
    if status == "timed_out":
        return "transport_timeout"
    if status == "failed":
        return "execution_failure"
    if status == "completed" and verify_status == "failed":
        return "evaluation_failure"
    if status == "completed" and verify_status == "not_run":
        return "missing_signal"
    return None


def _derive_failure_message(
    *,
    status: str,
    verify_status: str,
    execution_error: str,
    verify_reason: str,
) -> str | None:
    if execution_error:
        return execution_error
    if status == "not_started":
        return "transport submission did not start"
    if status == "timed_out":
        return "execution timed out"
    if status == "failed":
        return "execution failed"
    if status == "completed" and verify_status == "failed":
        return verify_reason or "verification failed"
    if status == "completed" and verify_status == "not_run":
        return verify_reason or "verification not run"
    return None


@dataclass
class CodexLiveExecutionTransport:
    repo_path: str
    timeout_seconds: int = 600
    execute_fn: Callable[..., Mapping[str, Any]] = execute_codex_cli
    verify_fn: Callable[[list[str], str], Mapping[str, Any]] = run_validation_commands
    now: Callable[[], datetime] = datetime.now
    _runs: dict[str, dict[str, Any]] = field(default_factory=dict)

    def _build_verify(
        self,
        *,
        execution_status: str,
        validation_commands: list[str],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if execution_status != "completed":
            verify = {
                "status": "not_run",
                "commands": validation_commands,
                "reason": f"validation_not_run_execution_status_{execution_status}",
            }
            return verify, {}

        if not validation_commands:
            verify = {
                "status": "not_run",
                "commands": [],
                "reason": "validation_not_run_no_validation_commands",
            }
            return verify, {}

        try:
            verify_raw = dict(self.verify_fn(validation_commands, self.repo_path))
        except Exception as exc:
            verify = {
                "status": "failed",
                "commands": validation_commands,
                "reason": "validation_runner_exception",
                "error": f"{type(exc).__name__}: {exc}",
            }
            return verify, {}

        verify_status = _normalize_verify_status(verify_raw.get("status"))
        verify_reason = _normalize_text(verify_raw.get("reason"), default="")
        if not verify_reason:
            if verify_status == "passed":
                verify_reason = "validation_passed"
            elif verify_status == "failed":
                verify_reason = "validation_failed"
            else:
                verify_reason = "validation_not_run"

        verify: dict[str, Any] = {
            "status": verify_status,
            "commands": validation_commands,
            "reason": verify_reason,
        }
        if _normalize_text(verify_raw.get("error"), default=""):
            verify["error"] = _normalize_text(verify_raw.get("error"), default="")

        command_results = verify_raw.get("command_results")
        if isinstance(command_results, list):
            verify["command_results"] = command_results

        return verify, verify_raw

    def launch_job(
        self,
        *,
        job_id: str,
        pr_id: str,
        prompt_path: str,
        work_dir: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        run_id = f"{job_id}:{pr_id}:live"
        metadata_map = dict(metadata or {})
        validation_commands = _normalize_string_list(metadata_map.get("validation_commands"))

        prompt_file = Path(prompt_path)
        if not prompt_file.exists():
            run_payload = {
                "run_id": run_id,
                "status": "not_started",
                "attempt_count": 0,
                "started_at": _iso_now(self.now),
                "finished_at": _iso_now(self.now),
                "stdout_path": "",
                "stderr_path": "",
                "verify": {
                    "status": "not_run",
                    "commands": validation_commands,
                    "reason": "validation_not_run_execution_status_not_started",
                },
                "changed_files": [],
                "additions": 0,
                "deletions": 0,
                "generated_patch_summary": "",
                "failure_type": "transport_submission_failure",
                "failure_message": f"compiled prompt not found: {prompt_file}",
                "error": f"compiled prompt not found: {prompt_file}",
                "cost": {"tokens_input": 0, "tokens_output": 0},
                "artifacts": [],
                "raw_transport": {"execution": {}, "verify": {}},
            }
            self._runs[run_id] = run_payload
            return {"run_id": run_id, "status": "not_started", "dry_run": False}

        prompt_text = prompt_file.read_text(encoding="utf-8")
        execution_result: dict[str, Any]
        try:
            execution_result = dict(
                self.execute_fn(
                    task={
                        "job_id": job_id,
                        "pr_id": pr_id,
                        "repo_path": self.repo_path,
                    },
                    prompt=prompt_text,
                    work_root=str(Path(work_dir) / "execution_runs"),
                    timeout_seconds=self.timeout_seconds,
                )
            )
        except Exception as exc:
            execution_result = {
                "status": "not_started",
                "started_at": _iso_now(self.now),
                "finished_at": _iso_now(self.now),
                "stdout_path": "",
                "stderr_path": "",
                "artifacts": [],
                "error": f"live transport submission exception ({type(exc).__name__}): {exc}",
            }

        status = _normalize_status(execution_result.get("status"))
        verify, verify_raw = self._build_verify(
            execution_status=status,
            validation_commands=validation_commands,
        )
        verify_status = _normalize_verify_status(verify.get("status"))

        execution_error = _normalize_text(execution_result.get("error"), default="")
        failure_type = _derive_failure_type(status=status, verify_status=verify_status)
        failure_message = _derive_failure_message(
            status=status,
            verify_status=verify_status,
            execution_error=execution_error,
            verify_reason=_normalize_text(verify.get("reason"), default=""),
        )

        run_payload = {
            "run_id": run_id,
            "status": status,
            "attempt_count": 0 if status == "not_started" else 1,
            "started_at": _normalize_text(
                execution_result.get("started_at"),
                default=_iso_now(self.now),
            ),
            "finished_at": _normalize_text(
                execution_result.get("finished_at"),
                default=_iso_now(self.now),
            ),
            "stdout_path": _normalize_text(execution_result.get("stdout_path"), default=""),
            "stderr_path": _normalize_text(execution_result.get("stderr_path"), default=""),
            "verify": verify,
            "changed_files": _normalize_string_list(execution_result.get("changed_files"), sort_items=True),
            "additions": _as_non_negative_int(execution_result.get("additions"), default=0),
            "deletions": _as_non_negative_int(execution_result.get("deletions"), default=0),
            "generated_patch_summary": _normalize_text(execution_result.get("generated_patch_summary"), default=""),
            "failure_type": failure_type,
            "failure_message": failure_message,
            "error": execution_error,
            "cost": {
                "tokens_input": _as_non_negative_int(
                    execution_result.get("tokens_input"),
                    default=0,
                ),
                "tokens_output": _as_non_negative_int(
                    execution_result.get("tokens_output"),
                    default=0,
                ),
            },
            "artifacts": execution_result.get("artifacts") if isinstance(execution_result.get("artifacts"), list) else [],
            "raw_transport": {
                "execution": execution_result,
                "verify": verify_raw,
            },
        }

        self._runs[run_id] = run_payload
        return {
            "run_id": run_id,
            "status": status,
            "dry_run": False,
        }

    def poll_status(self, *, run_id: str) -> Mapping[str, Any]:
        run = self._runs.get(run_id)
        if run is None:
            return {
                "run_id": run_id,
                "status": "not_started",
                "error": "unknown_run_id",
                "failure_type": "transport_submission_failure",
                "failure_message": "unknown_run_id",
            }
        payload = dict(run)
        payload["dry_run"] = False
        return payload

    def collect_artifacts(self, *, run_id: str) -> Mapping[str, Any]:
        run = self._runs.get(run_id)
        if run is None:
            return {
                "run_id": run_id,
                "stdout_path": "",
                "stderr_path": "",
                "artifacts": [],
                "raw_transport": {},
            }
        return {
            "run_id": run_id,
            "stdout_path": _normalize_text(run.get("stdout_path"), default=""),
            "stderr_path": _normalize_text(run.get("stderr_path"), default=""),
            "artifacts": run.get("artifacts") if isinstance(run.get("artifacts"), list) else [],
            "verify": run.get("verify") if isinstance(run.get("verify"), Mapping) else {},
            "raw_transport": run.get("raw_transport") if isinstance(run.get("raw_transport"), Mapping) else {},
            "dry_run": False,
        }
