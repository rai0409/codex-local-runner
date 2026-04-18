from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Mapping

from automation.control.action_handoff import build_action_handoff_payload
from automation.control.next_action_controller import evaluate_next_action_from_run_dir
from automation.control.retry_context_store import FileRetryContextStore
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


def _merge_retry_context_inputs(
    *,
    persisted: Mapping[str, Any] | None,
    explicit: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    has_persisted = isinstance(persisted, Mapping)
    has_explicit = isinstance(explicit, Mapping)
    if not has_persisted and not has_explicit:
        return None
    merged: dict[str, Any] = {}
    if has_persisted:
        merged.update(dict(persisted or {}))
    if has_explicit:
        merged.update(dict(explicit or {}))
    return merged


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
        raw_verify = status_response.get("verify")
        if not isinstance(raw_verify, Mapping):
            raw_verify = artifact_response.get("verify")
        if not isinstance(raw_verify, Mapping):
            raw_verify = {}

        verify_status = _normalize_text(raw_verify.get("status"), default="").lower()
        if verify_status not in {"passed", "failed", "not_run"}:
            verify_status = "not_run"
        verify_commands = _normalize_string_list(raw_verify.get("commands"))
        if not verify_commands:
            verify_commands = _normalize_string_list(unit.get("validation_commands"))
        normalized_verify_reason = _normalize_text(raw_verify.get("reason"), default="")
        if not normalized_verify_reason:
            normalized_verify_reason = verify_reason
        verify_payload: dict[str, Any] = {
            "status": verify_status,
            "commands": verify_commands,
            "reason": normalized_verify_reason,
        }
        command_results = raw_verify.get("command_results")
        if isinstance(command_results, list):
            verify_payload["command_results"] = command_results

        failure_type: str | None = None
        failure_message: str | None = None
        status_error = _normalize_text(
            status_response.get("error") or launch_response.get("error"),
            default="",
        )
        status_failure_type = _normalize_text(
            status_response.get("failure_type") or launch_response.get("failure_type"),
            default="",
        )
        status_failure_message = _normalize_text(
            status_response.get("failure_message") or launch_response.get("failure_message"),
            default="",
        )
        if status in {"failed", "timed_out"}:
            failure_type = status_failure_type or "execution_failure"
            failure_message = status_failure_message or status_error or f"execution_status={status}"
        elif status in {"not_started", "running"}:
            failure_type = status_failure_type or "missing_signal"
            failure_message = (
                status_failure_message
                or ("dry_run_execution_not_performed" if dry_run else f"execution_status={status}")
            )
        elif verify_status == "failed":
            failure_type = status_failure_type or "evaluation_failure"
            failure_message = status_failure_message or normalized_verify_reason or "validation_failed"
        elif verify_status == "not_run":
            failure_type = status_failure_type or "missing_signal"
            failure_message = status_failure_message or normalized_verify_reason or "validation_not_run"

        raw_cost = status_response.get("cost") if isinstance(status_response.get("cost"), Mapping) else {}
        if not raw_cost:
            raw_cost = artifact_response.get("cost") if isinstance(artifact_response.get("cost"), Mapping) else {}
        return {
            "status": status,
            "attempt_count": _as_non_negative_int(
                status_response.get("attempt_count") or launch_response.get("attempt_count"),
                default=0 if dry_run else 1,
            ),
            "started_at": _normalize_text(
                status_response.get("started_at") or launch_response.get("started_at"),
                default=_iso_now(self.now),
            ),
            "finished_at": _normalize_text(
                status_response.get("finished_at") or launch_response.get("finished_at"),
                default=_iso_now(self.now),
            ),
            "stdout_path": _normalize_text(
                status_response.get("stdout_path") or artifact_response.get("stdout_path"),
                default="",
            ),
            "stderr_path": _normalize_text(
                status_response.get("stderr_path") or artifact_response.get("stderr_path"),
                default="",
            ),
            "verify": verify_payload,
            "changed_files": _normalize_string_list(
                status_response.get("changed_files") or artifact_response.get("changed_files"),
                sort_items=True,
            ),
            "additions": _as_non_negative_int(
                status_response.get("additions") or artifact_response.get("additions"),
                default=0,
            ),
            "deletions": _as_non_negative_int(
                status_response.get("deletions") or artifact_response.get("deletions"),
                default=0,
            ),
            "generated_patch_summary": _normalize_text(
                status_response.get("generated_patch_summary")
                or artifact_response.get("generated_patch_summary"),
                default="",
            ),
            "failure_type": failure_type,
            "failure_message": failure_message,
            "error": status_error,
            "cost": {
                "tokens_input": _as_non_negative_int(raw_cost.get("tokens_input"), default=0),
                "tokens_output": _as_non_negative_int(raw_cost.get("tokens_output"), default=0),
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
        retry_context: Mapping[str, Any] | None = None,
        policy_snapshot: Mapping[str, Any] | None = None,
        github_read_evidence: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
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
        retry_context_store_path = output_root / "retry_context_store.json"
        retry_context_store = FileRetryContextStore(retry_context_store_path)
        persisted_retry_context = retry_context_store.get(resolved_job_id)
        effective_retry_context = _merge_retry_context_inputs(
            persisted=persisted_retry_context,
            explicit=retry_context,
        )

        run_root = output_root / resolved_job_id
        run_root.mkdir(parents=True, exist_ok=True)

        started_at = _iso_now(self.now)
        finished_at = started_at
        run_status = "dry_run_completed" if dry_run else "completed"
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
                        "validation_commands": _normalize_string_list(unit.get("validation_commands")),
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
            run_status = "dry_run_completed" if dry_run else "completed"

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
        decision_path = run_root / "next_action.json"
        decision_error = ""
        try:
            decision = evaluate_next_action_from_run_dir(
                run_root,
                retry_context=effective_retry_context,
                policy_snapshot=policy_snapshot,
                pr_plan=artifacts.get("pr_plan"),
            )
        except Exception as exc:
            # Keep deterministic run-level decision handling even when the controller cannot evaluate.
            decision_error = str(exc).strip() or "next_action_evaluation_failed"
            decision = {
                "next_action": "escalate_to_human",
                "reason": f"controller_evaluation_failed: {decision_error}",
                "retry_budget_remaining": 0,
                "whether_human_required": True,
                "updated_retry_context": {
                    "prior_attempt_count": 0,
                    "prior_retry_class": None,
                    "missing_signal_count": 0,
                    "retry_budget_remaining": 0,
                },
            }

        decision_payload = {
            **decision,
            "evaluated_at": _iso_now(self.now),
            "job_id": resolved_job_id,
        }
        _write_json(decision_path, decision_payload)

        handoff_path = run_root / "action_handoff.json"
        handoff_error = ""
        retry_context_store_error = ""
        try:
            handoff_payload = build_action_handoff_payload(
                job_id=resolved_job_id,
                decision_payload=decision_payload,
                now=self.now,
                external_evidence=github_read_evidence,
            )
        except Exception as exc:
            handoff_error = str(exc).strip() or "action_handoff_generation_failed"
            handoff_payload = {
                "handoff_schema_version": "v1",
                "job_id": resolved_job_id,
                "next_action": _normalize_text(decision_payload.get("next_action"), default=""),
                "reason": f"action_handoff_generation_failed: {handoff_error}",
                "whether_human_required": True,
                "retry_budget_remaining": _as_non_negative_int(
                    decision_payload.get("retry_budget_remaining"),
                    default=0,
                ),
                "updated_retry_context": (
                    dict(decision_payload.get("updated_retry_context"))
                    if isinstance(decision_payload.get("updated_retry_context"), Mapping)
                    else {
                        "prior_attempt_count": 0,
                        "prior_retry_class": None,
                        "missing_signal_count": 0,
                        "retry_budget_remaining": 0,
                    }
                ),
                "action_consumable": False,
                "unsupported_reason": "action_handoff_generation_failed",
                "retry_class": None,
                "evidence_summary": {
                    "provided": bool(github_read_evidence),
                    "items_total": 0,
                    "items": [],
                    "status_counts": {
                        "success": 0,
                        "empty": 0,
                        "not_found": 0,
                        "auth_failure": 0,
                        "api_failure": 0,
                        "unsupported_query": 0,
                    },
                },
                "evidence_constraints": [],
                "handoff_created_at": _iso_now(self.now),
            }
        _write_json(handoff_path, handoff_payload)

        try:
            retry_context_to_store = (
                dict(handoff_payload.get("updated_retry_context"))
                if isinstance(handoff_payload.get("updated_retry_context"), Mapping)
                else {
                    "prior_attempt_count": 0,
                    "prior_retry_class": None,
                    "missing_signal_count": 0,
                    "retry_budget_remaining": 0,
                }
            )
            retry_context_store.set(
                job_id=resolved_job_id,
                retry_context=retry_context_to_store,
                updated_at=_normalize_text(handoff_payload.get("handoff_created_at"), default=_iso_now(self.now)),
            )
        except Exception as exc:
            retry_context_store_error = str(exc).strip() or "retry_context_store_update_failed"

        manifest["decision_summary"] = {
            "next_action": _normalize_text(decision_payload.get("next_action"), default=""),
            "whether_human_required": bool(decision_payload.get("whether_human_required", False)),
            "decision_path": str(decision_path),
            "evaluated_at": _normalize_text(decision_payload.get("evaluated_at"), default=""),
        }
        if decision_error:
            manifest["decision_summary"]["decision_error"] = decision_error

        manifest["handoff_summary"] = {
            "next_action": _normalize_text(handoff_payload.get("next_action"), default=""),
            "action_consumable": bool(handoff_payload.get("action_consumable", False)),
            "unsupported_reason": _normalize_text(handoff_payload.get("unsupported_reason"), default=""),
            "handoff_path": str(handoff_path),
            "handoff_created_at": _normalize_text(handoff_payload.get("handoff_created_at"), default=""),
            "evidence_constraints_count": len(
                handoff_payload.get("evidence_constraints")
                if isinstance(handoff_payload.get("evidence_constraints"), list)
                else []
            ),
        }
        if handoff_error:
            manifest["handoff_summary"]["handoff_error"] = handoff_error
        if retry_context_store_error:
            manifest["handoff_summary"]["retry_context_store_error"] = retry_context_store_error

        manifest["manifest_path"] = str(manifest_path)
        manifest["next_action_path"] = str(decision_path)
        manifest["action_handoff_path"] = str(handoff_path)
        manifest["retry_context_store_path"] = str(retry_context_store_path)
        _write_json(manifest_path, manifest)
        return manifest
