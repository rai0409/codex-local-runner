from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Literal
from typing import Mapping
from typing import Protocol


class CodexExecutionTransport(Protocol):
    def launch_job(
        self,
        *,
        job_id: str,
        pr_id: str,
        prompt_path: str,
        work_dir: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        ...

    def poll_status(self, *, run_id: str) -> Mapping[str, Any]:
        ...

    def collect_artifacts(self, *, run_id: str) -> Mapping[str, Any]:
        ...


def select_execution_transport(
    *,
    mode: str,
    dry_run_transport: CodexExecutionTransport,
    live_transport: CodexExecutionTransport | None = None,
    live_transport_enabled: bool = False,
) -> tuple[CodexExecutionTransport, Literal["dry-run", "live"]]:
    normalized_mode = _normalize_text(mode, default="dry-run").lower()
    if normalized_mode in {"dry-run", "dry_run"}:
        return dry_run_transport, "dry-run"
    if normalized_mode == "live":
        if not live_transport_enabled:
            raise ValueError("live transport mode requires explicit enablement")
        if live_transport is None:
            raise ValueError("live transport mode requested but live transport is unavailable")
        return live_transport, "live"
    raise ValueError(f"unsupported transport mode: {mode}")


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


def _as_optional_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text and text.lstrip("-").isdigit():
            return int(text)
    return None


def _as_non_negative_int(value: Any, *, default: int = 0) -> int:
    maybe = _as_optional_int(value)
    if maybe is None:
        return default
    return max(0, maybe)


def _normalize_status(value: Any) -> str:
    text = _normalize_text(value, default="").lower()
    allowed = {"completed", "failed", "timed_out", "not_started", "running"}
    if text in allowed:
        return text
    return "failed"


def _normalize_verify_section(raw_result: Mapping[str, Any], *, execution_status: str) -> dict[str, Any]:
    raw_execution = raw_result.get("execution") if isinstance(raw_result.get("execution"), Mapping) else {}
    raw_verify = raw_result.get("verify")
    if not isinstance(raw_verify, Mapping):
        raw_verify = raw_execution.get("verify") if isinstance(raw_execution.get("verify"), Mapping) else {}

    raw_verify_status = _normalize_text(raw_verify.get("status"), default="").lower()
    verify_commands = _normalize_string_list(raw_verify.get("commands"))
    if not verify_commands:
        command_results = raw_verify.get("command_results")
        if isinstance(command_results, list):
            for result in command_results:
                if isinstance(result, Mapping):
                    command = _normalize_text(result.get("command"))
                    if command and command not in verify_commands:
                        verify_commands.append(command)

    if raw_verify_status in {"passed", "failed", "not_run"}:
        verify_status = raw_verify_status
        reason = _normalize_text(raw_verify.get("reason"), default="")
    else:
        verify_status = "not_run"
        if execution_status != "completed":
            reason = f"validation_not_run_execution_status_{execution_status}"
        else:
            reason = "validation_not_run_verify_data_missing"

    if not reason:
        if verify_status == "passed":
            reason = "validation_passed"
        elif verify_status == "failed":
            reason = "validation_failed"
        else:
            reason = "validation_not_run"

    return {
        "status": verify_status,
        "commands": verify_commands,
        "reason": reason,
    }


def _infer_failure_type(
    *,
    raw_failure_type: str,
    execution_status: str,
    verify_status: str,
) -> str | None:
    if raw_failure_type:
        return raw_failure_type
    if execution_status in {"failed", "timed_out"}:
        return "execution_failure"
    if execution_status in {"not_started", "running"}:
        return "missing_signal"
    if verify_status == "failed":
        return "evaluation_failure"
    if verify_status == "not_run":
        return "missing_signal"
    return None


def _infer_failure_message(
    *,
    raw_failure_message: str,
    execution_status: str,
    verify_status: str,
    verify_reason: str,
    raw_error: str,
) -> str | None:
    if raw_failure_message:
        return raw_failure_message
    if raw_error:
        return raw_error
    if execution_status in {"failed", "timed_out", "not_started", "running"}:
        return f"execution_status={execution_status}"
    if verify_status == "failed":
        return verify_reason or "verification failed"
    if verify_status == "not_run":
        return verify_reason or "verification not run"
    return None


def normalize_result_json(
    *,
    job_id: str,
    pr_unit: Mapping[str, Any],
    raw_result: Mapping[str, Any],
    raw_artifacts: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    pr_id = _normalize_text(pr_unit.get("pr_id"), default="")
    execution_payload = raw_result.get("execution") if isinstance(raw_result.get("execution"), Mapping) else {}

    execution_status = _normalize_status(raw_result.get("status") or execution_payload.get("status"))
    attempt_count = _as_non_negative_int(
        raw_result.get("attempt_count") if raw_result.get("attempt_count") is not None else execution_payload.get("attempt_count"),
        default=0 if execution_status == "not_started" else 1,
    )

    started_at = _normalize_text(raw_result.get("started_at") or execution_payload.get("started_at"), default="")
    finished_at = _normalize_text(raw_result.get("finished_at") or execution_payload.get("finished_at"), default="")

    stdout_path = _normalize_text(raw_result.get("stdout_path") or execution_payload.get("stdout_path"), default="")
    stderr_path = _normalize_text(raw_result.get("stderr_path") or execution_payload.get("stderr_path"), default="")

    verify = _normalize_verify_section(raw_result, execution_status=execution_status)

    changed_files = _normalize_string_list(raw_result.get("changed_files"), sort_items=True)
    if not changed_files:
        changed_files = _normalize_string_list(execution_payload.get("changed_files"), sort_items=True)

    additions = _as_non_negative_int(
        raw_result.get("additions") if raw_result.get("additions") is not None else execution_payload.get("additions"),
        default=0,
    )
    deletions = _as_non_negative_int(
        raw_result.get("deletions") if raw_result.get("deletions") is not None else execution_payload.get("deletions"),
        default=0,
    )

    generated_patch_summary = _normalize_text(
        raw_result.get("generated_patch_summary")
        if raw_result.get("generated_patch_summary") is not None
        else execution_payload.get("generated_patch_summary"),
        default="",
    )

    raw_error = _normalize_text(raw_result.get("error") or execution_payload.get("error"), default="")
    raw_failure_type = _normalize_text(raw_result.get("failure_type"), default="")
    raw_failure_message = _normalize_text(raw_result.get("failure_message"), default="")

    failure_type = _infer_failure_type(
        raw_failure_type=raw_failure_type,
        execution_status=execution_status,
        verify_status=verify["status"],
    )
    failure_message = _infer_failure_message(
        raw_failure_message=raw_failure_message,
        execution_status=execution_status,
        verify_status=verify["status"],
        verify_reason=verify["reason"],
        raw_error=raw_error,
    )

    if execution_status == "completed" and verify["status"] == "passed":
        failure_type = None
        failure_message = None

    raw_cost = raw_result.get("cost") if isinstance(raw_result.get("cost"), Mapping) else {}
    tokens_input = _as_non_negative_int(
        raw_cost.get("tokens_input")
        if raw_cost.get("tokens_input") is not None
        else raw_cost.get("prompt_tokens"),
        default=0,
    )
    tokens_output = _as_non_negative_int(
        raw_cost.get("tokens_output")
        if raw_cost.get("tokens_output") is not None
        else raw_cost.get("completion_tokens"),
        default=0,
    )

    normalized = {
        "job_id": _normalize_text(job_id),
        "pr_id": pr_id,
        "changed_files": changed_files,
        "execution": {
            "status": execution_status,
            "attempt_count": attempt_count,
            "started_at": started_at,
            "finished_at": finished_at,
            "stdout_path": stdout_path,
            "stderr_path": stderr_path,
            "verify": {
                "status": verify["status"],
                "commands": verify["commands"],
                "reason": verify["reason"],
            },
        },
        "additions": additions,
        "deletions": deletions,
        "generated_patch_summary": generated_patch_summary,
        "failure_type": failure_type,
        "failure_message": failure_message,
        "cost": {
            "tokens_input": tokens_input,
            "tokens_output": tokens_output,
        },
    }

    raw_bundle = {
        "result": dict(raw_result),
        "artifacts": dict(raw_artifacts or {}),
    }
    normalized["raw_execution"] = raw_bundle
    return normalized


@dataclass
class CodexExecutorAdapter:
    transport: CodexExecutionTransport

    def launch_job(
        self,
        *,
        job_id: str,
        pr_id: str,
        prompt_path: str,
        work_dir: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        return dict(
            self.transport.launch_job(
                job_id=job_id,
                pr_id=pr_id,
                prompt_path=prompt_path,
                work_dir=work_dir,
                metadata=metadata,
            )
        )

    def poll_status(self, *, run_id: str) -> dict[str, Any]:
        return dict(self.transport.poll_status(run_id=run_id))

    def collect_artifacts(self, *, run_id: str) -> dict[str, Any]:
        return dict(self.transport.collect_artifacts(run_id=run_id))

    def normalize_result(
        self,
        *,
        job_id: str,
        pr_unit: Mapping[str, Any],
        raw_result: Mapping[str, Any],
        raw_artifacts: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        return normalize_result_json(
            job_id=job_id,
            pr_unit=pr_unit,
            raw_result=raw_result,
            raw_artifacts=raw_artifacts,
        )
