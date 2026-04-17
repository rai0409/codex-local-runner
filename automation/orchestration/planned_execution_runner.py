from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Mapping

from automation.execution.codex_executor_adapter import CodexExecutionTransport
from automation.execution.codex_executor_adapter import CodexExecutorAdapter
from automation.planning.prompt_compiler import compile_prompt_units
from automation.planning.prompt_compiler import load_planning_artifacts


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
    result: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = str(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    if sort_items:
        return sorted(result)
    return result


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _unit_is_failure(*, execution_status: str, dry_run: bool) -> bool:
    if execution_status in {"failed", "timed_out"}:
        return True
    if execution_status in {"running", "not_started"}:
        return not dry_run
    return False


def _validate_pr_unit_order(units: list[dict[str, Any]], *, pr_plan: Mapping[str, Any]) -> None:
    planned_units = pr_plan.get("prs") if isinstance(pr_plan.get("prs"), list) else []

    planned_order: list[str] = []
    for pr in planned_units:
        if not isinstance(pr, Mapping):
            continue
        pr_id = _normalize_text(pr.get("pr_id"))
        if pr_id:
            planned_order.append(pr_id)

    compiled_order = [_normalize_text(unit.get("pr_id")) for unit in units if _normalize_text(unit.get("pr_id"))]

    if compiled_order != planned_order:
        raise ValueError("compiled prompt units are not aligned with pr_plan.prs ordering")

    seen: set[str] = set()
    for unit in units:
        pr_id = _normalize_text(unit.get("pr_id"))
        if not pr_id:
            raise ValueError("pr_unit.pr_id must be non-empty")
        if pr_id in seen:
            raise ValueError(f"duplicate pr_id in compiled units: {pr_id}")
        dependencies = _normalize_string_list(unit.get("depends_on"))
        for dependency in dependencies:
            if dependency not in seen:
                raise ValueError(
                    f"dependency order violation for {pr_id}: depends_on={dependency} not yet processed"
                )
        seen.add(pr_id)


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


@dataclass
class PlannedExecutionRunner:
    adapter: CodexExecutorAdapter
    now: Callable[[], datetime] = datetime.now

    def _build_raw_result_for_unit(
        self,
        *,
        unit: Mapping[str, Any],
        launch_response: Mapping[str, Any],
        status_response: Mapping[str, Any],
        artifact_response: Mapping[str, Any],
        dry_run: bool,
    ) -> dict[str, Any]:
        status = _normalize_text(
            status_response.get("status") or launch_response.get("status"),
            default="failed",
        ).lower()
        if status not in {"completed", "failed", "timed_out", "not_started", "running"}:
            status = "failed"

        verify_reason = "validation_not_run_dry_run" if dry_run else "validation_not_run"

        failure_type: str | None = None
        failure_message: str | None = None
        if status in {"failed", "timed_out"}:
            failure_type = "execution_failure"
            failure_message = _normalize_text(status_response.get("error"), default=f"execution_status={status}")
        elif status in {"not_started", "running"}:
            failure_type = "missing_signal"
            failure_message = (
                "dry_run_execution_not_performed" if dry_run else f"execution_status={status}"
            )

        return {
            "status": status,
            "attempt_count": 0 if dry_run else 1,
            "started_at": _iso_now(self.now),
            "finished_at": _iso_now(self.now),
            "stdout_path": _normalize_text(artifact_response.get("stdout_path"), default=""),
            "stderr_path": _normalize_text(artifact_response.get("stderr_path"), default=""),
            "verify": {
                "status": "not_run",
                "commands": _normalize_string_list(unit.get("validation_commands")),
                "reason": verify_reason,
            },
            "changed_files": [],
            "additions": 0,
            "deletions": 0,
            "generated_patch_summary": "",
            "failure_type": failure_type,
            "failure_message": failure_message,
            "cost": {
                "tokens_input": 0,
                "tokens_output": 0,
            },
        }

    def run(
        self,
        *,
        artifacts_input_dir: str | Path,
        output_dir: str | Path,
        job_id: str | None = None,
        dry_run: bool = True,
        stop_on_failure: bool = True,
    ) -> dict[str, Any]:
        if not dry_run:
            raise ValueError("non-dry-run execution is not supported in this phase")

        artifacts_root = Path(artifacts_input_dir)
        output_root = Path(output_dir)

        artifacts = load_planning_artifacts(artifacts_root)
        units = compile_prompt_units(artifacts)
        if not units:
            raise ValueError("no pr units found in planning artifacts")

        pr_plan = artifacts.get("pr_plan", {})
        _validate_pr_unit_order(units, pr_plan=pr_plan)

        project_brief = artifacts.get("project_brief", {})
        resolved_job_id = _normalize_text(job_id, default=_normalize_text(project_brief.get("project_id"), default="planned-execution"))

        run_root = output_root / resolved_job_id
        run_root.mkdir(parents=True, exist_ok=True)

        started_at = _iso_now(self.now)
        finished_at = started_at
        run_status = "dry_run_completed"
        manifest_units: list[dict[str, Any]] = []

        for unit in units:
            pr_id = _normalize_text(unit.get("pr_id"))
            unit_dir = run_root / pr_id
            unit_dir.mkdir(parents=True, exist_ok=True)

            compiled_prompt_path = unit_dir / "compiled_prompt.md"
            compiled_prompt_path.write_text(
                _normalize_text(unit.get("codex_task_prompt_md"), default=""),
                encoding="utf-8",
            )

            launch_response = dict(
                self.adapter.launch_job(
                    job_id=resolved_job_id,
                    pr_id=pr_id,
                    prompt_path=str(compiled_prompt_path),
                    work_dir=str(unit_dir),
                    metadata={
                        "dry_run": dry_run,
                        "tier_category": _normalize_text(unit.get("tier_category"), default=""),
                        "depends_on": _normalize_string_list(unit.get("depends_on")),
                    },
                )
            )
            run_id = _normalize_text(launch_response.get("run_id"), default="")

            status_response = (
                dict(self.adapter.poll_status(run_id=run_id))
                if run_id
                else {"status": "failed", "error": "missing_run_id"}
            )
            artifact_response = (
                dict(self.adapter.collect_artifacts(run_id=run_id))
                if run_id
                else {"stdout_path": "", "stderr_path": "", "artifacts": []}
            )

            raw_result = self._build_raw_result_for_unit(
                unit=unit,
                launch_response=launch_response,
                status_response=status_response,
                artifact_response=artifact_response,
                dry_run=dry_run,
            )
            normalized_result = self.adapter.normalize_result(
                job_id=resolved_job_id,
                pr_unit=unit,
                raw_result=raw_result,
                raw_artifacts=artifact_response,
            )

            result_path = unit_dir / "result.json"
            _write_json(result_path, normalized_result)

            execution_status = _normalize_text(
                normalized_result.get("execution", {}).get("status"),
                default="failed",
            ).lower()
            unit_failed = _unit_is_failure(execution_status=execution_status, dry_run=dry_run)
            receipt_status = "failed" if unit_failed else "recorded"

            receipt = {
                "job_id": resolved_job_id,
                "pr_id": pr_id,
                "status": receipt_status,
                "dry_run": dry_run,
                "run_id": run_id,
                "execution_status": execution_status,
                "compiled_prompt_path": str(compiled_prompt_path),
                "result_path": str(result_path),
                "stdout_path": _normalize_text(normalized_result.get("execution", {}).get("stdout_path"), default=""),
                "stderr_path": _normalize_text(normalized_result.get("execution", {}).get("stderr_path"), default=""),
                "tier_category": _normalize_text(unit.get("tier_category"), default=""),
                "depends_on": _normalize_string_list(unit.get("depends_on")),
                "canonical_surface_notes": _normalize_string_list(unit.get("canonical_surface_notes")),
                "compatibility_notes": _normalize_string_list(unit.get("compatibility_notes")),
                "planning_warnings": _normalize_string_list(unit.get("planning_warnings")),
                "started_at": _iso_now(self.now),
                "finished_at": _iso_now(self.now),
            }
            receipt_path = unit_dir / "execution_receipt.json"
            _write_json(receipt_path, receipt)

            manifest_units.append(
                {
                    "pr_id": pr_id,
                    "compiled_prompt_path": str(compiled_prompt_path),
                    "result_path": str(result_path),
                    "receipt_path": str(receipt_path),
                    "status": receipt_status,
                }
            )

            if unit_failed:
                run_status = "failed"
                if stop_on_failure:
                    break

            finished_at = _iso_now(self.now)

        if run_status != "failed":
            run_status = "dry_run_completed"

        manifest = {
            "job_id": resolved_job_id,
            "run_status": run_status,
            "artifact_input_dir": str(artifacts_root),
            "started_at": started_at,
            "finished_at": finished_at,
            "dry_run": dry_run,
            "stop_on_failure": stop_on_failure,
            "pr_units": manifest_units,
        }

        manifest_path = run_root / "manifest.json"
        _write_json(manifest_path, manifest)
        return manifest
