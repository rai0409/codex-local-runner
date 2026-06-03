from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping

from automation.control.next_action_controller import evaluate_next_action_from_run_dir
from automation.control.retry_context_store import FileRetryContextStore
from automation.execution.codex_executor_adapter import CodexExecutorAdapter
from automation.orchestration.objective_contract import build_objective_contract_surface
from automation.orchestration.objective_contract import build_objective_run_state_summary_surface
from automation.orchestration.planned_runner.runtime_output_wiring import reconnect_runtime_output_generation
from automation.orchestration.planned_runner.transports import DryRunCodexExecutionTransport
from automation.orchestration.planned_runner.utils import _as_non_negative_int, _iso_now
from automation.orchestration.planned_runner.utils import _normalize_string_list, _normalize_text
from automation.orchestration.planned_runner.utils import _read_json_object_if_exists, _write_json
from automation.planning.prompt_compiler import compile_prompt_units
from automation.planning.prompt_compiler import load_planning_artifacts

_UNIT_STATE_PROMPT_READY = "prompt_ready"
_UNIT_STATE_EXECUTION_READY = "execution_ready"
_UNIT_STATE_EXECUTION_COMPLETED = "execution_completed"
_UNIT_STATE_REVIEWED = "reviewed"


def _normalize_contract_payload(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _unit_is_failure(*, execution_status: str, dry_run: bool) -> bool:
    if execution_status in {"failed", "timed_out"}:
        return True
    if execution_status in {"running", "not_started"}:
        return not dry_run
    return False


def _validate_pr_unit_order(units: list[dict[str, Any]], *, pr_plan: Mapping[str, Any]) -> None:
    raw_prs = pr_plan.get("prs")
    if not isinstance(raw_prs, list):
        return
    expected = [
        _normalize_text(item.get("pr_id"))
        for item in raw_prs
        if isinstance(item, Mapping) and _normalize_text(item.get("pr_id"))
    ]
    actual = [_normalize_text(unit.get("pr_id")) for unit in units]
    if expected and actual[: len(expected)] != expected[: len(actual)]:
        raise ValueError("compiled pr unit order does not match pr_plan order")


def _extract_contract_handoff(
    *,
    pr_id: str,
    bounded_step_contract: Mapping[str, Any],
    prompt_contract: Mapping[str, Any],
) -> dict[str, Any]:
    bounded_progression = bounded_step_contract.get("progression_metadata")
    if not isinstance(bounded_progression, Mapping):
        bounded_progression = {}
    prompt_progression = prompt_contract.get("progression_metadata")
    if not isinstance(prompt_progression, Mapping):
        prompt_progression = {}
    task_scope = prompt_contract.get("task_scope")
    if not isinstance(task_scope, Mapping):
        task_scope = {}
    return {
        "bounded_step": {
            "schema_version": _normalize_text(bounded_step_contract.get("schema_version")),
            "planned_step_id": _normalize_text(
                bounded_progression.get("planned_step_id"),
                default=_normalize_text(bounded_step_contract.get("step_id"), default=pr_id),
            ),
            "tier_category": _normalize_text(
                bounded_progression.get("tier_category")
                or bounded_step_contract.get("tier_category")
            ),
            "depends_on": _normalize_string_list(
                bounded_progression.get("depends_on") or bounded_step_contract.get("depends_on")
            ),
            "strict_scope_files": _normalize_string_list(
                bounded_progression.get("strict_scope_files")
                or bounded_step_contract.get("scope_in"),
                sort_items=True,
            ),
            "forbidden_files": _normalize_string_list(
                bounded_progression.get("forbidden_files")
                or bounded_step_contract.get("scope_out"),
                sort_items=True,
            ),
            "validation_expectations": _normalize_string_list(
                bounded_step_contract.get("validation_expectations")
            ),
            "boundedness_status": _normalize_text(
                (bounded_step_contract.get("boundedness") or {}).get("status")
                if isinstance(bounded_step_contract.get("boundedness"), Mapping)
                else "",
                default="unknown",
            ),
        },
        "pr_implementation_prompt": {
            "schema_version": _normalize_text(prompt_contract.get("schema_version")),
            "source_step_id": _normalize_text(
                prompt_progression.get("planned_step_id"),
                default=_normalize_text(prompt_contract.get("source_step_id"), default=pr_id),
            ),
            "tier_category": _normalize_text(
                prompt_progression.get("tier_category") or task_scope.get("tier_category")
            ),
            "depends_on": _normalize_string_list(prompt_progression.get("depends_on")),
            "strict_scope_files": _normalize_string_list(
                prompt_progression.get("strict_scope_files") or task_scope.get("scope_in"),
                sort_items=True,
            ),
            "forbidden_files": _normalize_string_list(
                prompt_progression.get("forbidden_files") or task_scope.get("scope_out"),
                sort_items=True,
            ),
            "required_tests": _normalize_string_list(prompt_contract.get("required_tests")),
            "requires_explicit_validation": bool(
                prompt_progression.get("requires_explicit_validation", False)
            ),
        },
    }


def _new_unit_progression_payload(
    *,
    pr_id: str,
    now: Callable[[], datetime],
    contract_handoff: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "v1",
        "pr_id": pr_id,
        "current_state": "planned",
        "checkpoints": [
            {
                "state": "planned",
                "at": _iso_now(now),
                "reason": "unit_registered_from_compiled_plan",
            }
        ],
        "contract_handoff": dict(contract_handoff),
    }


def _append_progression_checkpoint(
    payload: dict[str, Any],
    *,
    state: str,
    now: Callable[[], datetime],
    reason: str,
    metadata: Mapping[str, Any] | None = None,
    update_current_state: bool = True,
) -> None:
    checkpoints = payload.get("checkpoints")
    if not isinstance(checkpoints, list):
        checkpoints = []
        payload["checkpoints"] = checkpoints
    entry: dict[str, Any] = {"state": state, "at": _iso_now(now), "reason": reason}
    if isinstance(metadata, Mapping) and metadata:
        entry["metadata"] = dict(metadata)
    checkpoints.append(entry)
    if update_current_state:
        payload["current_state"] = state


def _build_lifecycle_signals(
    *,
    bounded_step_contract: Mapping[str, Any],
    prompt_contract: Mapping[str, Any],
    strict_scope_files: list[str],
    normalized_result: Mapping[str, Any],
) -> dict[str, bool]:
    execution = normalized_result.get("execution")
    execution = dict(execution) if isinstance(execution, Mapping) else {}
    verify = execution.get("verify")
    verify = dict(verify) if isinstance(verify, Mapping) else {}
    changed_files = _normalize_string_list(normalized_result.get("changed_files"), sort_items=True)
    scope_violation = bool(strict_scope_files) and any(
        path not in set(strict_scope_files) for path in changed_files
    )
    execution_status = _normalize_text(execution.get("status"))
    verify_status = _normalize_text(verify.get("status"))
    return {
        "execution_succeeded": execution_status == "completed" and verify_status == "passed",
        "execution_failed": execution_status in {"failed", "timed_out"},
        "validation_failed": verify_status == "failed",
        "scope_violation_detected": scope_violation,
        "contract_missing": not bool(bounded_step_contract) or not bool(prompt_contract),
    }


def _build_simple_decision(
    *,
    kind: str,
    unit_id: str,
    decision_payload: Mapping[str, Any],
    signals: Mapping[str, bool],
) -> dict[str, Any]:
    next_action = _normalize_text(decision_payload.get("next_action"))
    manual_required = bool(decision_payload.get("whether_human_required", False))
    blocked = bool(signals.get("contract_missing") or signals.get("scope_violation_detected"))
    if kind == "rollback":
        decision = "required" if next_action == "rollback_required" else "not_required"
    elif kind == "checkpoint":
        if next_action == "rollback_required":
            decision = "rollback_evaluation_ready"
        elif manual_required or next_action == "escalate_to_human":
            decision = "manual_review_required"
        elif blocked:
            decision = "pause"
        else:
            decision = "continue"
    else:
        decision = "blocked" if blocked or manual_required else "allowed"
    return {
        "schema_version": "v1",
        "unit_id": unit_id,
        "decision_kind": kind,
        "decision": decision,
        "rule_id": f"{kind}_{decision}",
        "reason": _normalize_text(decision_payload.get("reason"), default=next_action),
        "manual_intervention_required": manual_required,
        "global_stop_recommended": next_action in {"escalate_to_human", "rollback_required"},
        "checkpoint_stage": "post_execution_review" if kind == "checkpoint" else "",
    }


def _resolve_review_terminal_state(decision_payload: Mapping[str, Any]) -> str:
    next_action = _normalize_text(decision_payload.get("next_action"))
    result_acceptance = _normalize_text(decision_payload.get("result_acceptance"))
    if next_action in {"escalate_to_human", "rollback_required"}:
        return "escalated"
    if result_acceptance == "accept_current_result" and next_action in {
        "proceed_to_pr",
        "proceed_to_merge",
    }:
        return "advanced"
    return _UNIT_STATE_REVIEWED


def _build_run_state_payload(
    *,
    run_id: str,
    run_status: str,
    next_action: str,
    reason: str,
    total_units_planned: int,
    manifest_units: list[Mapping[str, Any]],
) -> dict[str, Any]:
    units_processed = len(manifest_units)
    units_failed = sum(
        1 for unit in manifest_units if _normalize_text(unit.get("status")) == "failed"
    )
    units_completed = sum(
        1 for unit in manifest_units if _normalize_text(unit.get("status")) == "recorded"
    )
    manual_required = any(
        bool(unit.get("checkpoint_summary", {}).get("manual_intervention_required"))
        for unit in manifest_units
        if isinstance(unit.get("checkpoint_summary"), Mapping)
    )
    global_stop = next_action in {"escalate_to_human", "rollback_required"}
    continue_allowed = (
        run_status != "failed"
        and not manual_required
        and not global_stop
        and next_action in {"proceed_to_pr", "proceed_to_merge"}
    )
    return {
        "schema_version": "v1",
        "run_id": run_id,
        "state": "paused" if not continue_allowed else "commit_ready",
        "orchestration_state": (
            "run_ready_to_continue" if continue_allowed else "checkpoint_evaluation_in_progress"
        ),
        "summary": reason or f"next_action={next_action}",
        "units_total": max(0, total_units_planned),
        "units_completed": units_completed,
        "units_blocked": 0,
        "units_failed": units_failed,
        "units_pending": max(0, total_units_planned - units_processed),
        "global_stop": global_stop,
        "global_stop_reason": reason if global_stop else "",
        "continue_allowed": continue_allowed,
        "run_paused": not continue_allowed,
        "manual_intervention_required": manual_required,
        "rollback_evaluation_pending": next_action == "rollback_required",
        "global_stop_recommended": global_stop,
        "next_run_action": "continue_run" if continue_allowed else "pause_run",
        "unit_blocked": False,
        "latest_unit_id": _normalize_text(manifest_units[-1].get("pr_id")) if manifest_units else "",
        "allowed_transitions": [],
        "orchestration_allowed_transitions": [],
    }


def _merge_retry_context_inputs(
    *,
    persisted: Mapping[str, Any] | None,
    explicit: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    merged: dict[str, Any] = {}
    if isinstance(persisted, Mapping):
        merged.update(persisted)
    if isinstance(explicit, Mapping):
        merged.update(explicit)
    return merged or None


class PlannedExecutionRunner:
    """Small compatibility entry point for planned execution orchestration."""

    adapter: CodexExecutorAdapter
    github_read_backend: Any | None = None
    github_write_backend: Any | None = None
    now: Callable[[], datetime]

    def __init__(self, *, adapter: CodexExecutorAdapter | None = None) -> None:
        self.adapter = adapter or CodexExecutorAdapter(
            transport=DryRunCodexExecutionTransport()
        )
        self.now = datetime.now

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
        verify_reason = _normalize_text(raw_verify.get("reason"), default="")
        if not verify_reason:
            verify_reason = "validation_not_run_dry_run" if dry_run else "validation_not_run"

        status_error = _normalize_text(
            status_response.get("error") or launch_response.get("error"),
            default="",
        )
        failure_type = _normalize_text(
            status_response.get("failure_type") or launch_response.get("failure_type"),
            default="",
        )
        failure_message = _normalize_text(
            status_response.get("failure_message")
            or launch_response.get("failure_message"),
            default="",
        )
        if status in {"failed", "timed_out"}:
            failure_type = failure_type or "execution_failure"
            failure_message = failure_message or status_error or f"execution_status={status}"
        elif status in {"not_started", "running"} and not dry_run:
            failure_type = failure_type or "missing_signal"
            failure_message = failure_message or f"execution_status={status}"
        elif verify_status == "failed":
            failure_type = failure_type or "evaluation_failure"
            failure_message = failure_message or verify_reason or "validation_failed"

        raw_cost = status_response.get("cost")
        if not isinstance(raw_cost, Mapping):
            raw_cost = artifact_response.get("cost")
        if not isinstance(raw_cost, Mapping):
            raw_cost = {}

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
            "verify": {
                "status": verify_status,
                "commands": verify_commands,
                "reason": verify_reason,
            },
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
            "failure_type": failure_type or None,
            "failure_message": failure_message or None,
            "error": status_error,
            "cost": {
                "tokens_input": _as_non_negative_int(raw_cost.get("tokens_input"), default=0),
                "tokens_output": _as_non_negative_int(raw_cost.get("tokens_output"), default=0),
            },
        }

    def _write_unit_artifacts(
        self,
        *,
        unit: Mapping[str, Any],
        unit_dir: Path,
        job_id: str,
        dry_run: bool,
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, bool]]:
        pr_id = _normalize_text(unit.get("pr_id"))
        unit_dir.mkdir(parents=True, exist_ok=True)

        compiled_prompt_path = unit_dir / "compiled_prompt.md"
        compiled_prompt_path.write_text(
            _normalize_text(unit.get("codex_task_prompt_md"), default=""),
            encoding="utf-8",
        )
        bounded_step_contract_path = unit_dir / "bounded_step_contract.json"
        bounded_step_contract = _normalize_contract_payload(unit.get("bounded_step_contract"))
        _write_json(bounded_step_contract_path, bounded_step_contract)
        prompt_contract_path = unit_dir / "pr_implementation_prompt_contract.json"
        prompt_contract = _normalize_contract_payload(
            unit.get("pr_implementation_prompt_contract")
        )
        _write_json(prompt_contract_path, prompt_contract)

        contract_handoff = _extract_contract_handoff(
            pr_id=pr_id,
            bounded_step_contract=bounded_step_contract,
            prompt_contract=prompt_contract,
        )
        step_handoff = dict(contract_handoff.get("bounded_step") or {})
        prompt_handoff = dict(contract_handoff.get("pr_implementation_prompt") or {})

        progression_path = unit_dir / "unit_progression.json"
        progression = _new_unit_progression_payload(
            pr_id=pr_id,
            now=self.now,
            contract_handoff=contract_handoff,
        )
        _append_progression_checkpoint(
            progression,
            state=_UNIT_STATE_PROMPT_READY,
            now=self.now,
            reason="prompt_and_contract_artifacts_persisted",
            metadata={
                "compiled_prompt_path": str(compiled_prompt_path),
                "bounded_step_contract_path": str(bounded_step_contract_path),
                "pr_implementation_prompt_contract_path": str(prompt_contract_path),
            },
        )
        _write_json(progression_path, progression)

        launch_response = self.adapter.launch_job(
            job_id=job_id,
            pr_id=pr_id,
            prompt_path=str(compiled_prompt_path),
            work_dir=str(unit_dir),
            metadata={
                "dry_run": dry_run,
                "planned_step_id": _normalize_text(
                    step_handoff.get("planned_step_id"),
                    default=pr_id,
                ),
                "source_step_id": _normalize_text(
                    prompt_handoff.get("source_step_id"),
                    default=pr_id,
                ),
                "tier_category": _normalize_text(
                    step_handoff.get("tier_category")
                    or prompt_handoff.get("tier_category"),
                    default="",
                ),
                "depends_on": _normalize_string_list(
                    step_handoff.get("depends_on") or prompt_handoff.get("depends_on")
                ),
                "strict_scope_files": _normalize_string_list(
                    step_handoff.get("strict_scope_files")
                    or prompt_handoff.get("strict_scope_files"),
                    sort_items=True,
                ),
                "forbidden_files": _normalize_string_list(
                    step_handoff.get("forbidden_files")
                    or prompt_handoff.get("forbidden_files"),
                    sort_items=True,
                ),
                "validation_commands": _normalize_string_list(
                    step_handoff.get("validation_expectations")
                    or prompt_handoff.get("required_tests")
                ),
                "boundedness_status": _normalize_text(
                    step_handoff.get("boundedness_status"),
                    default="unknown",
                ),
                "requires_explicit_validation": bool(
                    prompt_handoff.get("requires_explicit_validation", False)
                ),
            },
        )
        run_id = _normalize_text(launch_response.get("run_id"), default="")
        _append_progression_checkpoint(
            progression,
            state=_UNIT_STATE_EXECUTION_READY,
            now=self.now,
            reason="execution_launch_attempted",
            metadata={"run_id": run_id, "launch_succeeded": bool(run_id)},
        )
        _write_json(progression_path, progression)

        status_response = (
            self.adapter.poll_status(run_id=run_id)
            if run_id
            else {"status": "failed", "error": "missing_run_id"}
        )
        artifact_response = (
            self.adapter.collect_artifacts(run_id=run_id)
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
            job_id=job_id,
            pr_unit=unit,
            raw_result=raw_result,
            raw_artifacts=artifact_response,
        )
        result_path = unit_dir / "result.json"
        _write_json(result_path, normalized_result)

        execution = dict(normalized_result.get("execution") or {})
        execution_status = _normalize_text(execution.get("status"), default="failed").lower()
        unit_failed = _unit_is_failure(execution_status=execution_status, dry_run=dry_run)
        receipt_status = "failed" if unit_failed else "recorded"
        _append_progression_checkpoint(
            progression,
            state=_UNIT_STATE_EXECUTION_COMPLETED,
            now=self.now,
            reason="execution_result_persisted",
            metadata={
                "execution_status": execution_status,
                "result_path": str(result_path),
            },
        )
        _append_progression_checkpoint(
            progression,
            state="decision_ready",
            now=self.now,
            reason="execution_and_contract_signals_ready_for_decision",
        )

        lifecycle_signals = _build_lifecycle_signals(
            bounded_step_contract=bounded_step_contract,
            prompt_contract=prompt_contract,
            strict_scope_files=_normalize_string_list(
                step_handoff.get("strict_scope_files")
                or prompt_handoff.get("strict_scope_files"),
                sort_items=True,
            ),
            normalized_result=normalized_result,
        )
        _write_json(progression_path, progression)

        receipt_path = unit_dir / "execution_receipt.json"
        receipt = {
            "job_id": job_id,
            "pr_id": pr_id,
            "status": receipt_status,
            "dry_run": dry_run,
            "run_id": run_id,
            "execution_status": execution_status,
            "compiled_prompt_path": str(compiled_prompt_path),
            "bounded_step_contract_path": str(bounded_step_contract_path),
            "pr_implementation_prompt_contract_path": str(prompt_contract_path),
            "result_path": str(result_path),
            "stdout_path": _normalize_text(execution.get("stdout_path"), default=""),
            "stderr_path": _normalize_text(execution.get("stderr_path"), default=""),
            "contract_handoff": contract_handoff,
            "unit_progression_path": str(progression_path),
            "unit_progression_state": _normalize_text(
                progression.get("current_state"),
                default=_UNIT_STATE_EXECUTION_COMPLETED,
            ),
            "started_at": _iso_now(self.now),
            "finished_at": _iso_now(self.now),
        }
        _write_json(receipt_path, receipt)

        manifest_unit = {
            "pr_id": pr_id,
            "compiled_prompt_path": str(compiled_prompt_path),
            "bounded_step_contract_path": str(bounded_step_contract_path),
            "pr_implementation_prompt_contract_path": str(prompt_contract_path),
            "result_path": str(result_path),
            "receipt_path": str(receipt_path),
            "status": receipt_status,
            "unit_progression_path": str(progression_path),
            "unit_progression_state": _normalize_text(
                progression.get("current_state"),
                default=_UNIT_STATE_EXECUTION_COMPLETED,
            ),
            "contract_handoff_summary": {
                "planned_step_id": _normalize_text(
                    step_handoff.get("planned_step_id"),
                    default=pr_id,
                ),
                "source_step_id": _normalize_text(
                    prompt_handoff.get("source_step_id"),
                    default=pr_id,
                ),
                "tier_category": _normalize_text(
                    step_handoff.get("tier_category")
                    or prompt_handoff.get("tier_category"),
                    default="",
                ),
                "boundedness_status": _normalize_text(
                    step_handoff.get("boundedness_status"),
                    default="",
                ),
            },
            "checkpoint_decision_path": str(unit_dir / "checkpoint_decision.json"),
            "commit_decision_path": str(unit_dir / "commit_decision.json"),
            "merge_decision_path": str(unit_dir / "merge_decision.json"),
            "rollback_decision_path": str(unit_dir / "rollback_decision.json"),
            "commit_execution_path": str(unit_dir / "commit_execution.json"),
            "push_execution_path": str(unit_dir / "push_execution.json"),
            "pr_execution_path": str(unit_dir / "pr_execution.json"),
            "merge_execution_path": str(unit_dir / "merge_execution.json"),
            "rollback_execution_path": str(unit_dir / "rollback_execution.json"),
        }
        return manifest_unit, progression, lifecycle_signals

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
        execution_repo_path: str | Path | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        artifacts_root = Path(artifacts_input_dir)
        output_root = Path(output_dir)
        execution_repo = _normalize_text(execution_repo_path, default="")

        artifacts = load_planning_artifacts(artifacts_root)

        units = compile_prompt_units(artifacts)
        if not units:
            raise ValueError("no pr units found in planning artifacts")
        pr_plan = artifacts.get("pr_plan", {})
        _validate_pr_unit_order(units, pr_plan=pr_plan if isinstance(pr_plan, Mapping) else {})

        project_brief = dict(artifacts.get("project_brief") or {})
        repo_facts = dict(artifacts.get("repo_facts") or {})
        policy_payload = dict(policy_snapshot) if isinstance(policy_snapshot, Mapping) else {}
        resolved_job_id = _normalize_text(
            job_id,
            default=_normalize_text(
                project_brief.get("project_id"),
                default="planned-execution",
            ),
        )
        retry_context_store = FileRetryContextStore(output_root / "retry_context_store.json")
        effective_retry_context = _merge_retry_context_inputs(
            persisted=retry_context_store.get(resolved_job_id),
            explicit=retry_context,
        )

        run_root = output_root / resolved_job_id
        run_root.mkdir(parents=True, exist_ok=True)
        started_at = _iso_now(self.now)
        finished_at = started_at
        run_status = "dry_run_completed" if dry_run else "completed"
        manifest_units: list[dict[str, Any]] = []
        progressions: dict[str, dict[str, Any]] = {}
        signal_registry: dict[str, dict[str, bool]] = {}

        for unit in units:
            pr_id = _normalize_text(unit.get("pr_id"))
            manifest_unit, progression, lifecycle_signals = self._write_unit_artifacts(
                unit=unit,
                unit_dir=run_root / pr_id,
                job_id=resolved_job_id,
                dry_run=dry_run,
            )
            manifest_units.append(manifest_unit)
            progressions[pr_id] = progression
            signal_registry[pr_id] = lifecycle_signals
            if manifest_unit["status"] == "failed":
                run_status = "failed"
                if stop_on_failure:
                    break
            finished_at = _iso_now(self.now)

        if run_status != "failed":
            run_status = "dry_run_completed" if dry_run else "completed"

        manifest: dict[str, Any] = {
            "job_id": resolved_job_id,
            "run_status": run_status,
            "artifact_input_dir": str(artifacts_root),
            "started_at": started_at,
            "finished_at": finished_at,
            "dry_run": dry_run,
            "stop_on_failure": stop_on_failure,
            "artifact_ownership": {
                "bounded_step_contract": "bounded_step_contract.json",
                "pr_implementation_prompt_contract": "pr_implementation_prompt_contract.json",
                "execution_result": "result.json",
                "unit_progression": "unit_progression.json",
                "checkpoint_decision": "checkpoint_decision.json",
                "commit_decision": "commit_decision.json",
                "merge_decision": "merge_decision.json",
                "rollback_decision": "rollback_decision.json",
                "commit_execution": "commit_execution.json",
                "push_execution": "push_execution.json",
                "pr_execution": "pr_execution.json",
                "merge_execution": "merge_execution.json",
                "rollback_execution": "rollback_execution.json",
                "run_state": "run_state.json",
                "objective_contract": "objective_contract.json",
            },
            "pr_units": manifest_units,
        }

        objective_contract_path = run_root / "objective_contract.json"
        objective_contract_payload = build_objective_contract_surface(
            run_id=resolved_job_id,
            artifacts=artifacts,
            units=units,
            policy_snapshot=policy_snapshot,
            execution_repo_path=execution_repo or None,
            artifact_ownership=manifest["artifact_ownership"],
        )
        _write_json(objective_contract_path, objective_contract_payload)
        manifest["objective_contract_summary"] = build_objective_run_state_summary_surface(
            objective_contract_payload
        )
        manifest["objective_contract_path"] = str(objective_contract_path)

        manifest_path = run_root / "manifest.json"
        _write_json(manifest_path, manifest)
        decision_path = run_root / "next_action.json"
        try:
            decision = evaluate_next_action_from_run_dir(
                run_root,
                retry_context=effective_retry_context,
                policy_snapshot=policy_snapshot,
                pr_plan=pr_plan if isinstance(pr_plan, Mapping) else None,
            )
        except Exception as exc:
            decision = {
                "next_action": "escalate_to_human",
                "reason": f"controller_evaluation_failed: {str(exc).strip()}",
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
        review_terminal_state = _resolve_review_terminal_state(decision_payload)

        for entry in manifest_units:
            pr_id = _normalize_text(entry.get("pr_id"), default="")
            lifecycle_signals = dict(signal_registry.get(pr_id) or {})
            lifecycle_signals["review_passed"] = (
                _normalize_text(decision_payload.get("result_acceptance"), default="")
                == "accept_current_result"
            )
            lifecycle_signals["review_failed"] = not lifecycle_signals["review_passed"]
            lifecycle_signals["manual_review_required"] = bool(
                decision_payload.get("whether_human_required", False)
            )
            lifecycle_signals["global_stop_required"] = _normalize_text(
                decision_payload.get("next_action"),
                default="",
            ) in {"escalate_to_human", "rollback_required"}

            rollback_decision = _build_simple_decision(
                kind="rollback",
                unit_id=pr_id,
                decision_payload=decision_payload,
                signals=lifecycle_signals,
            )
            lifecycle_signals["rollback_required"] = (
                rollback_decision.get("decision") == "required"
            )
            commit_decision = _build_simple_decision(
                kind="commit",
                unit_id=pr_id,
                decision_payload=decision_payload,
                signals=lifecycle_signals,
            )
            lifecycle_signals["commit_allowed"] = commit_decision.get("decision") == "allowed"
            merge_decision = _build_simple_decision(
                kind="merge",
                unit_id=pr_id,
                decision_payload=decision_payload,
                signals=lifecycle_signals,
            )
            lifecycle_signals["merge_allowed"] = merge_decision.get("decision") == "allowed"
            checkpoint_decision = _build_simple_decision(
                kind="checkpoint",
                unit_id=pr_id,
                decision_payload=decision_payload,
                signals=lifecycle_signals,
            )

            for path_key, payload in (
                ("checkpoint_decision_path", checkpoint_decision),
                ("commit_decision_path", commit_decision),
                ("merge_decision_path", merge_decision),
                ("rollback_decision_path", rollback_decision),
            ):
                _write_json(Path(_normalize_text(entry.get(path_key), default="")), payload)

            progression = dict(progressions.get(pr_id) or {})
            progression_path = Path(_normalize_text(entry.get("unit_progression_path")))
            if progression and progression_path:
                _append_progression_checkpoint(
                    progression,
                    state=_UNIT_STATE_REVIEWED,
                    now=self.now,
                    reason="review_progression_outcome_evaluated",
                    metadata={
                        "next_action": _normalize_text(
                            decision_payload.get("next_action"),
                            default="",
                        ),
                        "result_acceptance": _normalize_text(
                            decision_payload.get("result_acceptance"),
                            default="",
                        ),
                    },
                )
                if review_terminal_state != _UNIT_STATE_REVIEWED:
                    _append_progression_checkpoint(
                        progression,
                        state=review_terminal_state,
                        now=self.now,
                        reason="review_terminal_state_resolved",
                    )
                _write_json(progression_path, progression)
                entry["unit_progression_state"] = _normalize_text(
                    progression.get("current_state"),
                    default=review_terminal_state,
                )

            entry["decision_summary"] = {
                "checkpoint_decision": _normalize_text(
                    checkpoint_decision.get("decision"),
                    default="unknown",
                ),
                "commit_decision": _normalize_text(
                    commit_decision.get("decision"),
                    default="unknown",
                ),
                "merge_decision": _normalize_text(
                    merge_decision.get("decision"),
                    default="unknown",
                ),
                "rollback_decision": _normalize_text(
                    rollback_decision.get("decision"),
                    default="unknown",
                ),
            }
            entry["checkpoint_summary"] = {
                "checkpoint_stage": _normalize_text(
                    checkpoint_decision.get("checkpoint_stage"),
                    default="",
                ),
                "decision": _normalize_text(
                    checkpoint_decision.get("decision"),
                    default="unknown",
                ),
                "rule_id": _normalize_text(checkpoint_decision.get("rule_id"), default=""),
                "manual_intervention_required": bool(
                    checkpoint_decision.get("manual_intervention_required", False)
                ),
                "global_stop_recommended": bool(
                    checkpoint_decision.get("global_stop_recommended", False)
                ),
            }

        run_state_path = run_root / "run_state.json"
        run_state_payload = _build_run_state_payload(
            run_id=resolved_job_id,
            run_status=run_status,
            next_action=_normalize_text(decision_payload.get("next_action"), default=""),
            reason=_normalize_text(decision_payload.get("reason"), default=""),
            total_units_planned=len(units),
            manifest_units=manifest_units,
        )
        run_state_payload["github_read_evidence_present"] = isinstance(github_read_evidence, Mapping)
        run_state_payload, manifest = reconnect_runtime_output_generation(
            run_root=run_root,
            run_state_payload=run_state_payload,
            manifest_payload=manifest,
            execution_repo_path=execution_repo,
            job_id=resolved_job_id,
            dry_run=dry_run,
            now=self.now,
            prompt373_live_execution_requested=bool(kwargs.get("prompt373_live_execution_requested", False)),
            prompt373_live_execution_confirmed=bool(kwargs.get("prompt373_live_execution_confirmed", False)),
            prompt378_generated_prompt_path=_normalize_text(kwargs.get("prompt378_generated_prompt_path"), default=""),
            prompt379_codex_execution_requested=bool(kwargs.get("prompt379_codex_execution_requested", False)),
            prompt379_codex_execution_confirmed=bool(kwargs.get("prompt379_codex_execution_confirmed", False)),
            prompt389_bounded_repeated_success_path_loop_enabled=bool(
                kwargs.get("prompt389_bounded_repeated_success_path_loop_enabled", False)
            ),
            prompt389_max_cycles=kwargs.get("prompt389_max_cycles"),
            prompt546_internal_codex_subprocess_enabled=bool(
                kwargs.get("prompt546_internal_codex_subprocess_enabled", False)
            ),
            prompt546_internal_codex_enable_token=_normalize_text(
                kwargs.get("prompt546_internal_codex_enable_token"),
                default="",
            ),
            prompt546_internal_codex_prompt_path=_normalize_text(
                kwargs.get("prompt546_internal_codex_prompt_path"),
                default="",
            ),
            prompt546_internal_codex_timeout_seconds=kwargs.get(
                "prompt546_internal_codex_timeout_seconds",
                600,
            ),
            prompt546_internal_codex_allowed_files=kwargs.get(
                "prompt546_internal_codex_allowed_files"
            ),
            prompt547_internal_codex_subprocess_enabled=bool(
                kwargs.get("prompt547_internal_codex_subprocess_enabled", False)
            ),
            prompt547_internal_codex_enable_token=_normalize_text(
                kwargs.get("prompt547_internal_codex_enable_token"),
                default="",
            ),
            prompt547_internal_codex_prompt_path=_normalize_text(
                kwargs.get("prompt547_internal_codex_prompt_path"),
                default="",
            ),
            prompt547_internal_codex_timeout_seconds=kwargs.get(
                "prompt547_internal_codex_timeout_seconds",
                600,
            ),
            prompt547_internal_codex_allowed_files=kwargs.get(
                "prompt547_internal_codex_allowed_files"
            ),
        )
        _write_json(run_state_path, run_state_payload)

        manifest.update(
            {
                "decision_summary": decision_payload,
                "next_action_path": str(decision_path),
                "run_state_path": str(run_state_path),
                "manifest_path": str(manifest_path),
                "run_state_summary": _read_json_object_if_exists(run_state_path) or {},
                "repository": _normalize_text(
                    policy_payload.get("repository"),
                    default=_normalize_text(
                        project_brief.get("target_repo"),
                        default=_normalize_text(repo_facts.get("repo"), default=""),
                    ),
                ),
            }
        )
        _write_json(manifest_path, manifest)
        return manifest


__all__ = ["PlannedExecutionRunner", "DryRunCodexExecutionTransport"]
