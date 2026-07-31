from __future__ import annotations

from datetime import datetime
from pathlib import Path
import inspect
import sys
from typing import Any, Callable, Mapping

from automation.control.next_action_controller import evaluate_next_action_from_run_dir
from automation.control.action_handoff import build_action_handoff_payload
from automation.control.retry_context_store import FileRetryContextStore
from automation.execution.codex_executor_adapter import CodexExecutorAdapter
from automation.orchestration.objective_contract import build_objective_contract_surface
from automation.orchestration.objective_contract import build_objective_run_state_summary_surface
from automation.orchestration.planned_runner.runtime_output_wiring import reconnect_runtime_output_generation
from automation.orchestration.planned_runner.transports import DryRunCodexExecutionTransport
from automation.orchestration.planned_runner.utils import _as_non_negative_int, _as_optional_int, _iso_now
from automation.orchestration.planned_runner.utils import _normalize_string_list, _normalize_text
from automation.orchestration.planned_runner.utils import _read_json_object_if_exists, _write_json
from automation.planning.prompt_compiler import compile_prompt_units
from automation.planning.prompt_compiler import load_planning_artifacts

_UNIT_STATE_PROMPT_READY = "prompt_ready"
_UNIT_STATE_EXECUTION_READY = "execution_ready"
_UNIT_STATE_EXECUTION_COMPLETED = "execution_completed"
_UNIT_STATE_REVIEWED = "reviewed"

_LEGACY_PATCHABLE_SYMBOLS = (
    "build_approval_email_delivery_contract_surface",
    "build_approval_response_contract_surface",
    "build_approved_restart_contract_surface",
    "build_approval_safety_contract_surface",
    "build_failure_bucketing_hardening_contract_surface",
    "build_fleet_safety_control_contract_surface",
    "build_loop_hardening_contract_surface",
    "_execute_bounded_rollback",
)


def _apply_legacy_facade_overrides() -> None:
    facade = sys.modules.get("automation.orchestration.planned_execution_runner")
    if facade is None:
        return
    for symbol in _LEGACY_PATCHABLE_SYMBOLS:
        if not hasattr(facade, symbol):
            continue
        replacement = getattr(facade, symbol)
        for module_name, module in tuple(sys.modules.items()):
            if not module_name.startswith("automation.orchestration.planned_runner."):
                continue
            # The facade wrapper imports this implementation lazily.  Replacing
            # it with the wrapper turns that lazy lookup into self-recursion.
            if module_name == "automation.orchestration.planned_runner.git_ops.rollback":
                continue
            if module is not None and hasattr(module, symbol):
                setattr(module, symbol, replacement)


def _call_contract_builder(builder: Callable[..., Mapping[str, Any]], **context: Any) -> dict[str, Any]:
    signature = inspect.signature(builder)
    accepts_kwargs = any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    )
    kwargs = context if accepts_kwargs else {
        name: value for name, value in context.items() if name in signature.parameters
    }
    if not accepts_kwargs:
        for name, parameter in signature.parameters.items():
            if (
                parameter.kind is inspect.Parameter.KEYWORD_ONLY
                and parameter.default is inspect.Parameter.empty
                and name not in kwargs
            ):
                kwargs[name] = None
    return dict(builder(**kwargs))


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
    run_state_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if kind == "checkpoint":
        from automation.orchestration.planned_runner.state.checkpoint import (
            _build_checkpoint_decision,
        )

        return _build_checkpoint_decision(
            unit_id=unit_id,
            signals=signals,
            decision_payload=decision_payload,
        )

    if kind == "commit":
        from automation.orchestration.planned_runner.decisions.commit import _build_commit_decision

        payload = _build_commit_decision(
            unit_id=unit_id,
            signals=signals,
            decision_payload=decision_payload,
        )
    elif kind == "merge":
        from automation.orchestration.planned_runner.decisions.merge import _build_merge_decision

        payload = _build_merge_decision(
            unit_id=unit_id,
            signals=signals,
            decision_payload=decision_payload,
        )
    else:
        from automation.orchestration.planned_runner.decisions.rollback import (
            _build_rollback_decision,
        )

        payload = _build_rollback_decision(
            unit_id=unit_id,
            signals=signals,
            decision_payload=decision_payload,
        )

    from automation.orchestration.planned_runner.state.run_state import _with_readiness_overlay

    return _with_readiness_overlay(
        decision_kind=kind,
        decision_payload=payload,
        signals=signals,
        run_state_payload=run_state_payload,
        commit_readiness_status=("ready" if kind == "merge" and signals.get("commit_allowed") else None),
    )


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
            "rollback_evaluation_pending"
            if next_action == "rollback_required"
            else (
                "global_stop_pending"
                if global_stop
                else (
                    "run_ready_to_continue"
                    if continue_allowed
                    else "checkpoint_evaluation_in_progress"
                )
            )
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
        "next_run_action": (
            "evaluate_rollback"
            if next_action == "rollback_required"
            else "hold_for_global_stop"
            if global_stop
            else "continue_run"
            if continue_allowed
            else "pause_run"
        ),
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

    def __init__(
        self,
        *,
        adapter: CodexExecutorAdapter | None = None,
        github_read_backend: Any | None = None,
        github_write_backend: Any | None = None,
    ) -> None:
        self.adapter = adapter or CodexExecutorAdapter(
            transport=DryRunCodexExecutionTransport()
        )
        self.github_read_backend = github_read_backend
        self.github_write_backend = github_write_backend
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
            "changed_files": _normalize_string_list(normalized_result.get("changed_files"), sort_items=True),
            "strict_scope_files": _normalize_string_list(
                step_handoff.get("strict_scope_files") or prompt_handoff.get("strict_scope_files"),
                sort_items=True,
            ),
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
        _apply_legacy_facade_overrides()
        facade = sys.modules["automation.orchestration.planned_execution_runner"]
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
                "completion_contract": "completion_contract.json",
                "approval_transport": "approval_transport.json",
                "reconcile_contract": "reconcile_contract.json",
                "repair_suggestion_contract": "repair_suggestion_contract.json",
                "repair_plan_transport": "repair_plan_transport.json",
                "repair_approval_binding": "repair_approval_binding.json",
                "execution_authorization_gate": "execution_authorization_gate.json",
                "bounded_execution_bridge": "bounded_execution_bridge.json",
                "execution_result_contract": "execution_result_contract.json",
                "verification_closure_contract": "verification_closure_contract.json",
                "retry_reentry_loop_contract": "retry_reentry_loop_contract.json",
                "approval_email_delivery_contract": "approval_email_delivery_contract.json",
                "approval_runtime_rules_contract": "approval_runtime_rules_contract.json",
                "approval_delivery_handoff_contract": "approval_delivery_handoff_contract.json",
                "approval_response_contract": "approval_response_contract.json",
                "approved_restart_contract": "approved_restart_contract.json",
                "approval_safety_contract": "approval_safety_contract.json",
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
        run_state_objective_summary = manifest["objective_contract_summary"]
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
                run_state_payload={
                    "global_stop": lifecycle_signals["global_stop_required"],
                    "global_stop_recommended": lifecycle_signals["global_stop_required"],
                },
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
                    state="checkpoint_evaluated",
                    now=self.now,
                    reason="checkpoint_decision_persisted",
                )
                _append_progression_checkpoint(
                    progression,
                    state="commit_evaluated",
                    now=self.now,
                    reason="commit_decision_persisted",
                )
                _append_progression_checkpoint(
                    progression,
                    state="merge_evaluated",
                    now=self.now,
                    reason="merge_decision_persisted",
                )
                _append_progression_checkpoint(
                    progression,
                    state="rollback_evaluated",
                    now=self.now,
                    reason="rollback_decision_persisted",
                )
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
                **{
                    f"{decision_kind}_{field}": payload.get(field)
                    for decision_kind, payload in (
                        ("commit", commit_decision),
                        ("merge", merge_decision),
                        ("rollback", rollback_decision),
                    )
                    for field in (
                        "readiness_status",
                        "readiness_next_action",
                        "automation_eligible",
                        "manual_intervention_required",
                        "unresolved_blockers",
                        "prerequisites_satisfied",
                    )
                },
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
        from automation.orchestration.planned_runner.state.run_state import (
            _augment_run_state_with_readiness,
        )

        run_state_payload = _augment_run_state_with_readiness(
            run_state_payload=run_state_payload,
            manifest_units=manifest_units,
        )
        run_state_payload.update(run_state_objective_summary)
        from automation.orchestration.planned_runner.git_ops.commit_tag import (
            _execute_bounded_commit,
        )
        from automation.orchestration.planned_runner.state.run_state import (
            _augment_run_state_with_commit_execution,
        )

        for entry in manifest_units:
            decision_summary = (
                dict(entry.get("decision_summary"))
                if isinstance(entry.get("decision_summary"), Mapping)
                else {}
            )
            commit_decision = _read_json_object_if_exists(
                Path(_normalize_text(entry.get("commit_decision_path"), default=""))
            ) or {}
            commit_execution = _execute_bounded_commit(
                unit_id=_normalize_text(entry.get("pr_id"), default=""),
                job_id=resolved_job_id,
                repo_path=execution_repo,
                changed_files=_normalize_string_list(entry.get("changed_files"), sort_items=True),
                strict_scope_files=_normalize_string_list(
                    entry.get("strict_scope_files"), sort_items=True
                ),
                run_state_payload=run_state_payload,
                commit_decision=commit_decision,
                dry_run=dry_run,
                now=self.now,
            )
            from automation.orchestration.planned_runner.summaries.final_payload import (
                _with_execution_gate_surface,
            )

            commit_execution = _with_execution_gate_surface(commit_execution)
            _write_json(
                Path(_normalize_text(entry.get("commit_execution_path"), default="")),
                commit_execution,
            )
            entry["commit_execution_summary"] = dict(commit_execution)
            decision_summary["commit_execution_status"] = _normalize_text(
                commit_execution.get("status"), default="blocked"
            )
            decision_summary["commit_execution_manual_intervention_required"] = bool(
                commit_execution.get("manual_intervention_required", False)
            )
            entry["decision_summary"] = decision_summary

            # Persist the downstream delivery/rollback receipts even when the
            # run-level guards block execution (the usual dry-run posture).
            # These are artifact-wiring records, not authorization to push,
            # create a PR, merge, or roll back.
            from automation.orchestration.planned_runner.git_ops.pr_merge import (
                _execute_bounded_merge,
                _execute_bounded_pr_creation,
                _execute_bounded_push,
            )
            from automation.orchestration.planned_runner.git_ops.rollback import (
                _build_rollback_execution_blocked_payload,
            )

            merge_decision = _read_json_object_if_exists(
                Path(_normalize_text(entry.get("merge_decision_path"), default=""))
            ) or {}
            rollback_decision = _read_json_object_if_exists(
                Path(_normalize_text(entry.get("rollback_decision_path"), default=""))
            ) or {}
            repository = _normalize_text(
                policy_payload.get("repository"),
                default=_normalize_text(
                    project_brief.get("target_repo"),
                    default=_normalize_text(repo_facts.get("repo"), default=""),
                ),
            )
            base_branch = _normalize_text(
                policy_payload.get("base_branch") or repo_facts.get("default_branch"),
                default="",
            )
            push_execution = _execute_bounded_push(
                unit_id=_normalize_text(entry.get("pr_id"), default=""),
                repo_path=execution_repo,
                remote_name="",
                configured_head_branch="",
                base_branch=base_branch,
                run_state_payload=run_state_payload,
                commit_execution_payload=commit_execution,
                dry_run=dry_run,
                now=self.now,
            )
            pr_execution = _execute_bounded_pr_creation(
                unit_id=_normalize_text(entry.get("pr_id"), default=""),
                job_id=resolved_job_id,
                repository=repository,
                base_branch=base_branch,
                run_state_payload=run_state_payload,
                merge_decision_payload=merge_decision,
                commit_execution_payload=commit_execution,
                push_execution_payload=push_execution,
                read_backend=self.github_read_backend,
                write_backend=self.github_write_backend,
                now=self.now,
            )
            push_execution = _with_execution_gate_surface(push_execution)
            pr_execution = _with_execution_gate_surface(pr_execution)
            if (
                _normalize_text(commit_execution.get("status"), default="") == "succeeded"
                and _normalize_text(push_execution.get("status"), default="") == "succeeded"
                and _normalize_text(pr_execution.get("status"), default="") == "succeeded"
                and _as_optional_int(pr_execution.get("pr_number"))
            ):
                merge_decision = {
                    **merge_decision,
                    "decision": "allowed",
                    "rule_id": "merge_allowed_after_pr_creation",
                    "summary": "merge readiness satisfied by persisted commit, push, and PR receipts",
                    "blocking_reasons": [],
                    "recommended_next_action": "proceed_to_merge",
                    "readiness_status": "ready",
                    "readiness_next_action": "prepare_merge",
                    "automation_eligible": True,
                    "manual_intervention_required": False,
                    "unresolved_blockers": [],
                    "prerequisites_satisfied": True,
                }
                _write_json(
                    Path(_normalize_text(entry.get("merge_decision_path"), default="")),
                    merge_decision,
                )
            merge_execution = _execute_bounded_merge(
                unit_id=_normalize_text(entry.get("pr_id"), default=""),
                repository=repository,
                run_state_payload=run_state_payload,
                merge_decision_payload=merge_decision,
                commit_execution_payload=commit_execution,
                push_execution_payload=push_execution,
                pr_execution_payload=pr_execution,
                read_backend=self.github_read_backend,
                write_backend=self.github_write_backend,
                now=self.now,
            )
            merge_execution = _with_execution_gate_surface(merge_execution)
            rollback_executor = facade._execute_bounded_rollback
            if (
                getattr(rollback_executor, "__module__", "")
                == "automation.orchestration.planned_execution_runner"
                and getattr(rollback_executor, "__name__", "")
                == "_execute_bounded_rollback"
            ):
                rollback_execution = _build_rollback_execution_blocked_payload(
                    unit_id=_normalize_text(entry.get("pr_id"), default=""),
                    rollback_mode="unknown",
                    summary=(
                        "rollback execution blocked; receipt persisted without "
                        "executing a rollback"
                    ),
                    failure_reason="rollback_execution_blocked_by_preconditions",
                    blocking_reasons=["artifact_wiring_only", "dry_run_mode"],
                    trigger_reason=_normalize_text(
                        rollback_decision.get("decision"), default="unknown"
                    ),
                    source_execution_state_summary={
                        "commit_execution_status": _normalize_text(commit_execution.get("status"), default=""),
                        "push_execution_status": _normalize_text(push_execution.get("status"), default=""),
                        "pr_execution_status": _normalize_text(pr_execution.get("status"), default=""),
                        "merge_execution_status": _normalize_text(merge_execution.get("status"), default=""),
                    },
                    manual_intervention_required=True,
                    now=self.now,
                )
            else:
                rollback_execution = rollback_executor(
                    unit_id=_normalize_text(entry.get("pr_id"), default=""),
                    repo_path=execution_repo,
                    run_state_payload=run_state_payload,
                    rollback_decision_payload=rollback_decision,
                    commit_execution_payload=commit_execution,
                    push_execution_payload=push_execution,
                    pr_execution_payload=pr_execution,
                    merge_execution_payload=merge_execution,
                    dry_run=dry_run,
                    now=self.now,
                )
            for execution_name, execution_payload in (
                ("push", push_execution),
                ("pr", pr_execution),
                ("merge", merge_execution),
                ("rollback", rollback_execution),
            ):
                _write_json(
                    Path(
                        _normalize_text(
                            entry.get(f"{execution_name}_execution_path"), default=""
                        )
                    ),
                    execution_payload,
                )
                entry[f"{execution_name}_execution_summary"] = dict(execution_payload)
                decision_summary[f"{execution_name}_execution_status"] = _normalize_text(
                    execution_payload.get("status"), default="blocked"
                )
                decision_summary[
                    f"{execution_name}_execution_manual_intervention_required"
                ] = bool(execution_payload.get("manual_intervention_required", False))
            entry["decision_summary"] = decision_summary

            progression_path = Path(
                _normalize_text(entry.get("unit_progression_path"), default="")
            )
            progression = _read_json_object_if_exists(progression_path) or {}
            if bool(commit_execution.get("attempted", False)):
                _append_progression_checkpoint(
                    progression,
                    state="commit_execution_started",
                    now=self.now,
                    reason="bounded_commit_execution_attempted",
                )
                _append_progression_checkpoint(
                    progression,
                    state=(
                        "commit_executed"
                        if commit_execution.get("status") == "succeeded"
                        else "commit_execution_failed"
                    ),
                    now=self.now,
                    reason="bounded_commit_execution_completed",
                )
                _write_json(progression_path, progression)
            for execution_name, execution_payload, started_state, completed_state in (
                ("push", push_execution, "push_execution_started", "push_executed"),
                ("pr", pr_execution, "pr_creation_started", "pr_created"),
                ("merge", merge_execution, "merge_execution_started", "merge_executed"),
            ):
                if not bool(execution_payload.get("attempted", False)):
                    continue
                _append_progression_checkpoint(
                    progression,
                    state=started_state,
                    now=self.now,
                    reason=f"bounded_{execution_name}_execution_attempted",
                )
                _append_progression_checkpoint(
                    progression,
                    state=(
                        completed_state
                        if execution_payload.get("status") == "succeeded"
                        else f"{execution_name}_execution_failed"
                    ),
                    now=self.now,
                    reason=f"bounded_{execution_name}_execution_completed",
                )
                _write_json(progression_path, progression)
            if bool(rollback_execution.get("attempted", False)):
                _append_progression_checkpoint(
                    progression,
                    state="rollback_execution_started",
                    now=self.now,
                    reason="bounded_rollback_execution_attempted",
                )
                _append_progression_checkpoint(
                    progression,
                    state=(
                        "rollback_executed"
                        if rollback_execution.get("status") == "succeeded"
                        else "rollback_execution_failed"
                    ),
                    now=self.now,
                    reason="bounded_rollback_execution_completed",
                )
                _write_json(progression_path, progression)

        from automation.orchestration.planned_runner.state.run_state import (
            _augment_run_state_with_authority_validation,
            _augment_run_state_with_closed_loop,
            _augment_run_state_with_delivery_execution,
            _augment_run_state_with_remote_github,
            _augment_run_state_with_rollback_aftermath,
            _augment_run_state_with_rollback_execution,
        )

        run_state_payload = _augment_run_state_with_commit_execution(
            run_state_payload=run_state_payload,
            manifest_units=manifest_units,
        )
        run_state_payload = _augment_run_state_with_delivery_execution(
            run_state_payload=run_state_payload,
            manifest_units=manifest_units,
        )
        run_state_payload = _augment_run_state_with_rollback_execution(
            run_state_payload=run_state_payload,
            manifest_units=manifest_units,
        )
        run_state_payload = _augment_run_state_with_rollback_aftermath(
            run_state_payload=run_state_payload,
            manifest_units=manifest_units,
        )
        run_state_payload = _augment_run_state_with_authority_validation(
            run_state_payload=run_state_payload,
            manifest_units=manifest_units,
        )
        run_state_payload = _augment_run_state_with_closed_loop(
            run_state_payload=run_state_payload,
            manifest_units=manifest_units,
            run_status=run_status,
        )
        runtime_run_state_payload = {
            **run_state_payload,
            "github_read_evidence_present": isinstance(github_read_evidence, Mapping),
        }
        # Runtime wiring owns its detailed prompt surfaces and artifacts.  The
        # persisted run-state remains the orchestration contract, so do not
        # promote those implementation-detail fields into its public schema.
        _, manifest = reconnect_runtime_output_generation(
            run_root=run_root,
            run_state_payload=runtime_run_state_payload,
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
        run_state_payload = _augment_run_state_with_remote_github(
            run_state_payload=run_state_payload,
            manifest_units=manifest_units,
        )
        from automation.orchestration.planned_runner.state.lifecycle import (
            _augment_run_state_with_lifecycle_terminal_contract,
        )
        from automation.orchestration.planned_runner.state.operator_explainability import (
            _augment_run_state_with_operator_explainability,
        )
        from automation.orchestration.planned_runner.state.policy_overlay import (
            _augment_run_state_with_policy_overlay,
        )

        run_state_payload = _augment_run_state_with_policy_overlay(
            run_state_payload=run_state_payload
        )
        run_state_payload = _augment_run_state_with_lifecycle_terminal_contract(
            run_state_payload=run_state_payload
        )
        run_state_payload = _augment_run_state_with_operator_explainability(
            run_state_payload=run_state_payload
        )

        # The completion contract is a run-level artifact.  Keep its creation
        # here, after the runtime surfaces have been merged, so the persisted
        # contract and manifest summary describe the same run-state snapshot.
        from automation.orchestration.completion_contract import (
            build_completion_contract_surface,
            build_completion_run_state_summary_surface,
        )

        required_artifacts = _normalize_string_list(
            objective_contract_payload.get("required_artifacts"), sort_items=True
        )
        completion_contract_payload = build_completion_contract_surface(
            run_id=resolved_job_id,
            objective_contract_payload=objective_contract_payload,
            run_state_payload=run_state_payload,
            artifact_presence={
                artifact_name: (run_root / artifact_name).exists()
                for artifact_name in required_artifacts
            },
        )
        completion_contract_path = run_root / "completion_contract.json"
        _write_json(completion_contract_path, completion_contract_payload)
        completion_contract_summary = build_completion_run_state_summary_surface(
            completion_contract_payload
        )
        run_state_payload.update(completion_contract_summary)
        manifest["completion_contract_summary"] = completion_contract_summary
        manifest["completion_contract_path"] = str(completion_contract_path)

        # Approval artifacts are run-level contracts.  Persist their complete
        # payloads alongside their stable compact manifest summaries.
        from automation.orchestration.approval_transport import (
            build_approval_run_state_summary_surface,
            build_approval_transport_surface,
        )
        from automation.orchestration.approval_email_delivery import (
            build_approval_email_delivery_run_state_summary_surface,
            build_approval_email_delivery_summary_surface,
        )
        from automation.orchestration.approval_runtime_policy import (
            build_approval_runtime_rules_contract_surface,
            build_approval_runtime_rules_run_state_summary_surface,
            build_approval_runtime_rules_summary_surface,
        )
        from automation.orchestration.approval_delivery_adapter import (
            build_approval_delivery_handoff_contract_surface,
            build_approval_delivery_handoff_run_state_summary_surface,
            build_approval_delivery_handoff_summary_surface,
        )
        from automation.orchestration.approval_response_ingest import (
            build_approval_response_run_state_summary_surface,
            build_approval_response_summary_surface,
            build_approved_restart_run_state_summary_surface,
            build_approved_restart_summary_surface,
        )
        from automation.orchestration.approval_safety import (
            build_approval_safety_run_state_summary_surface,
            build_approval_safety_summary_surface,
        )
        from automation.orchestration.artifact_index import build_contract_artifact_index
        from automation.orchestration.reconcile_contract import (
            build_reconcile_contract_surface,
            build_reconcile_run_state_summary_surface,
        )
        from automation.orchestration.repair_suggestion_contract import (
            build_repair_suggestion_contract_surface,
            build_repair_suggestion_run_state_summary_surface,
        )
        from automation.orchestration.repair_plan_transport import (
            build_repair_plan_transport_run_state_summary_surface,
            build_repair_plan_transport_surface,
        )
        from automation.orchestration.repair_approval_binding import (
            build_repair_approval_binding_run_state_summary_surface,
            build_repair_approval_binding_surface,
        )
        from automation.orchestration.execution_authorization_gate import (
            build_execution_authorization_gate_run_state_summary_surface,
            build_execution_authorization_gate_surface,
        )
        from automation.orchestration.bounded_execution_bridge import (
            build_bounded_execution_bridge_run_state_summary_surface,
            build_bounded_execution_bridge_surface,
        )
        from automation.orchestration.execution_result_contract import (
            build_execution_result_contract_run_state_summary_surface,
            build_execution_result_contract_surface,
        )
        from automation.orchestration.verification_closure_contract import (
            build_verification_closure_contract_surface,
            build_verification_closure_run_state_summary_surface,
        )
        from automation.orchestration.retry_reentry_loop_contract import (
            build_retry_reentry_loop_contract_surface,
            build_retry_reentry_loop_run_state_summary_surface,
        )
        from automation.orchestration.endgame_closure_contract import (
            build_endgame_closure_contract_surface,
            build_endgame_closure_run_state_summary_surface,
        )
        from automation.orchestration.loop_hardening_contract import (
            build_loop_hardening_run_state_summary_surface,
        )
        from automation.orchestration.lane_stabilization_contract import (
            build_lane_stabilization_contract_surface,
            build_lane_stabilization_run_state_summary_surface,
        )
        from automation.orchestration.observability_rollup import (
            build_failure_bucket_rollup_summary_surface,
            build_failure_bucket_rollup_surface,
            build_fleet_run_rollup_summary_surface,
            build_fleet_run_rollup_surface,
            build_observability_rollup_contract_summary_surface,
            build_observability_rollup_contract_surface,
            build_observability_rollup_run_state_summary_surface,
        )
        from automation.orchestration.failure_bucketing_hardening import (
            build_failure_bucketing_hardening_run_state_summary_surface,
            build_failure_bucketing_hardening_summary_surface,
        )
        from automation.orchestration.artifact_retention import (
            build_artifact_retention_contract_surface,
            build_artifact_retention_run_state_summary_surface,
            build_artifact_retention_summary_surface,
            build_retention_manifest_summary_surface,
            build_retention_manifest_surface,
        )
        from automation.orchestration.fleet_safety_control import (
            build_fleet_safety_control_run_state_summary_surface,
            build_fleet_safety_control_summary_surface,
        )
        from automation.orchestration.planned_runner.summaries.artifact_payload import (
            _collect_execution_result_contract_records,
        )

        approval_transport_payload = build_approval_transport_surface(
            run_id=resolved_job_id,
            objective_contract_payload=objective_contract_payload,
            completion_contract_payload=completion_contract_payload,
            run_state_payload=run_state_payload,
            approval_input_payload=artifacts.get("approval_transport.json"),
            evaluated_at=_iso_now(self.now),
        )
        approval_transport_path = run_root / "approval_transport.json"
        _write_json(approval_transport_path, approval_transport_payload)
        approval_transport_summary = build_approval_run_state_summary_surface(
            approval_transport_payload
        )
        run_state_payload.update(approval_transport_summary)
        manifest["approval_transport_summary"] = approval_transport_summary
        manifest["approval_transport_path"] = str(approval_transport_path)

        reconcile_contract_payload = build_reconcile_contract_surface(
            run_id=resolved_job_id,
            objective_contract_payload=objective_contract_payload,
            completion_contract_payload=completion_contract_payload,
            approval_transport_payload=approval_transport_payload,
            run_state_payload=run_state_payload,
            artifact_presence={
                "objective_contract.json": objective_contract_path.exists(),
                "completion_contract.json": completion_contract_path.exists(),
                "approval_transport.json": approval_transport_path.exists(),
            },
        )
        reconcile_contract_path = run_root / "reconcile_contract.json"
        _write_json(reconcile_contract_path, reconcile_contract_payload)
        reconcile_contract_summary = build_reconcile_run_state_summary_surface(
            reconcile_contract_payload
        )
        run_state_payload.update(reconcile_contract_summary)
        manifest["reconcile_contract_summary"] = reconcile_contract_summary
        manifest["reconcile_contract_path"] = str(reconcile_contract_path)

        repair_suggestion_contract_payload = build_repair_suggestion_contract_surface(
            run_id=resolved_job_id,
            objective_contract_payload=objective_contract_payload,
            completion_contract_payload=completion_contract_payload,
            approval_transport_payload=approval_transport_payload,
            reconcile_contract_payload=reconcile_contract_payload,
            run_state_payload=run_state_payload,
            artifact_presence={
                "objective_contract.json": objective_contract_path.exists(),
                "completion_contract.json": completion_contract_path.exists(),
                "approval_transport.json": approval_transport_path.exists(),
                "reconcile_contract.json": reconcile_contract_path.exists(),
            },
        )
        repair_suggestion_contract_path = run_root / "repair_suggestion_contract.json"
        _write_json(repair_suggestion_contract_path, repair_suggestion_contract_payload)
        repair_suggestion_contract_summary = (
            build_repair_suggestion_run_state_summary_surface(
                repair_suggestion_contract_payload
            )
        )
        run_state_payload.update(repair_suggestion_contract_summary)
        manifest["repair_suggestion_contract_summary"] = repair_suggestion_contract_summary
        manifest["repair_suggestion_contract_path"] = str(repair_suggestion_contract_path)

        repair_plan_transport_payload = build_repair_plan_transport_surface(
            run_id=resolved_job_id,
            objective_contract_payload=objective_contract_payload,
            completion_contract_payload=completion_contract_payload,
            approval_transport_payload=approval_transport_payload,
            reconcile_contract_payload=reconcile_contract_payload,
            repair_suggestion_contract_payload=repair_suggestion_contract_payload,
            run_state_payload=run_state_payload,
            artifact_presence={
                "objective_contract.json": objective_contract_path.exists(),
                "completion_contract.json": completion_contract_path.exists(),
                "approval_transport.json": approval_transport_path.exists(),
                "reconcile_contract.json": reconcile_contract_path.exists(),
                "repair_suggestion_contract.json": repair_suggestion_contract_path.exists(),
            },
        )
        repair_plan_transport_path = run_root / "repair_plan_transport.json"
        _write_json(repair_plan_transport_path, repair_plan_transport_payload)
        repair_plan_transport_summary = (
            build_repair_plan_transport_run_state_summary_surface(
                repair_plan_transport_payload
            )
        )
        run_state_payload.update(repair_plan_transport_summary)
        manifest["repair_plan_transport_summary"] = repair_plan_transport_summary
        manifest["repair_plan_transport_path"] = str(repair_plan_transport_path)

        repair_approval_binding_payload = build_repair_approval_binding_surface(
            run_id=resolved_job_id,
            objective_contract_payload=objective_contract_payload,
            completion_contract_payload=completion_contract_payload,
            approval_transport_payload=approval_transport_payload,
            reconcile_contract_payload=reconcile_contract_payload,
            repair_suggestion_contract_payload=repair_suggestion_contract_payload,
            repair_plan_transport_payload=repair_plan_transport_payload,
            run_state_payload=run_state_payload,
            artifact_presence={
                name: (run_root / name).exists()
                for name in (
                    "objective_contract.json", "completion_contract.json",
                    "approval_transport.json", "reconcile_contract.json",
                    "repair_suggestion_contract.json", "repair_plan_transport.json",
                )
            },
        )
        repair_approval_binding_path = run_root / "repair_approval_binding.json"
        _write_json(repair_approval_binding_path, repair_approval_binding_payload)
        repair_approval_binding_summary = (
            build_repair_approval_binding_run_state_summary_surface(
                repair_approval_binding_payload
            )
        )
        run_state_payload.update(repair_approval_binding_summary)
        manifest["repair_approval_binding_summary"] = repair_approval_binding_summary
        manifest["repair_approval_binding_path"] = str(repair_approval_binding_path)

        execution_authorization_gate_payload = build_execution_authorization_gate_surface(
            run_id=resolved_job_id,
            objective_contract_payload=objective_contract_payload,
            completion_contract_payload=completion_contract_payload,
            approval_transport_payload=approval_transport_payload,
            reconcile_contract_payload=reconcile_contract_payload,
            repair_suggestion_contract_payload=repair_suggestion_contract_payload,
            repair_plan_transport_payload=repair_plan_transport_payload,
            repair_approval_binding_payload=repair_approval_binding_payload,
            run_state_payload=run_state_payload,
            artifact_presence={name: (run_root / name).exists() for name in manifest["artifact_ownership"].values()},
        )
        execution_authorization_gate_path = run_root / "execution_authorization_gate.json"
        _write_json(execution_authorization_gate_path, execution_authorization_gate_payload)
        execution_authorization_gate_summary = build_execution_authorization_gate_run_state_summary_surface(execution_authorization_gate_payload)
        run_state_payload.update(execution_authorization_gate_summary)
        manifest["execution_authorization_gate_summary"] = execution_authorization_gate_summary
        manifest["execution_authorization_gate_path"] = str(execution_authorization_gate_path)

        bounded_execution_bridge_payload = build_bounded_execution_bridge_surface(
            run_id=resolved_job_id,
            objective_contract_payload=objective_contract_payload,
            completion_contract_payload=completion_contract_payload,
            approval_transport_payload=approval_transport_payload,
            reconcile_contract_payload=reconcile_contract_payload,
            repair_suggestion_contract_payload=repair_suggestion_contract_payload,
            repair_plan_transport_payload=repair_plan_transport_payload,
            repair_approval_binding_payload=repair_approval_binding_payload,
            execution_authorization_gate_payload=execution_authorization_gate_payload,
            run_state_payload=run_state_payload,
            artifact_presence={name: (run_root / name).exists() for name in manifest["artifact_ownership"].values()},
        )
        bounded_execution_bridge_path = run_root / "bounded_execution_bridge.json"
        _write_json(bounded_execution_bridge_path, bounded_execution_bridge_payload)
        bounded_execution_bridge_summary = (
            build_bounded_execution_bridge_run_state_summary_surface(
                bounded_execution_bridge_payload
            )
        )
        run_state_payload.update(bounded_execution_bridge_summary)
        manifest["bounded_execution_bridge_summary"] = bounded_execution_bridge_summary
        manifest["bounded_execution_bridge_path"] = str(bounded_execution_bridge_path)

        execution_result_contract_payload = build_execution_result_contract_surface(
            run_id=resolved_job_id,
            objective_contract_payload=objective_contract_payload,
            completion_contract_payload=completion_contract_payload,
            approval_transport_payload=approval_transport_payload,
            reconcile_contract_payload=reconcile_contract_payload,
            repair_plan_transport_payload=repair_plan_transport_payload,
            repair_approval_binding_payload=repair_approval_binding_payload,
            execution_authorization_gate_payload=execution_authorization_gate_payload,
            bounded_execution_bridge_payload=bounded_execution_bridge_payload,
            run_state_payload=run_state_payload,
            execution_records=_collect_execution_result_contract_records(manifest_units),
            artifact_presence={name: (run_root / name).exists() for name in manifest["artifact_ownership"].values()},
        )
        execution_result_contract_path = run_root / "execution_result_contract.json"
        _write_json(execution_result_contract_path, execution_result_contract_payload)
        execution_result_contract_summary = (
            build_execution_result_contract_run_state_summary_surface(
                execution_result_contract_payload
            )
        )
        run_state_payload.update(execution_result_contract_summary)
        manifest["execution_result_contract_summary"] = execution_result_contract_summary
        manifest["execution_result_contract_path"] = str(execution_result_contract_path)

        verification_closure_contract_payload = build_verification_closure_contract_surface(
            run_id=resolved_job_id,
            objective_contract_payload=objective_contract_payload,
            completion_contract_payload=completion_contract_payload,
            approval_transport_payload=approval_transport_payload,
            reconcile_contract_payload=reconcile_contract_payload,
            execution_authorization_gate_payload=execution_authorization_gate_payload,
            bounded_execution_bridge_payload=bounded_execution_bridge_payload,
            execution_result_contract_payload=execution_result_contract_payload,
            run_state_payload=run_state_payload,
            artifact_presence={name: (run_root / name).exists() for name in manifest["artifact_ownership"].values()},
        )
        verification_closure_contract_path = run_root / "verification_closure_contract.json"
        _write_json(verification_closure_contract_path, verification_closure_contract_payload)
        verification_closure_contract_summary = (
            build_verification_closure_run_state_summary_surface(
                verification_closure_contract_payload
            )
        )
        run_state_payload.update(verification_closure_contract_summary)
        manifest["verification_closure_contract_summary"] = verification_closure_contract_summary
        manifest["verification_closure_contract_path"] = str(verification_closure_contract_path)

        retry_reentry_loop_contract_payload = build_retry_reentry_loop_contract_surface(
            run_id=resolved_job_id,
            completion_contract_payload=completion_contract_payload,
            approval_transport_payload=approval_transport_payload,
            reconcile_contract_payload=reconcile_contract_payload,
            repair_suggestion_contract_payload=repair_suggestion_contract_payload,
            repair_plan_transport_payload=repair_plan_transport_payload,
            repair_approval_binding_payload=repair_approval_binding_payload,
            execution_authorization_gate_payload=execution_authorization_gate_payload,
            bounded_execution_bridge_payload=bounded_execution_bridge_payload,
            execution_result_contract_payload=execution_result_contract_payload,
            verification_closure_contract_payload=verification_closure_contract_payload,
            run_state_payload=run_state_payload,
            artifact_presence={name: (run_root / name).exists() for name in manifest["artifact_ownership"].values()},
        )
        retry_reentry_loop_contract_path = run_root / "retry_reentry_loop_contract.json"
        _write_json(retry_reentry_loop_contract_path, retry_reentry_loop_contract_payload)
        retry_reentry_loop_contract_summary = (
            build_retry_reentry_loop_run_state_summary_surface(
                retry_reentry_loop_contract_payload
            )
        )
        run_state_payload.update(retry_reentry_loop_contract_summary)
        manifest["retry_reentry_loop_contract_summary"] = retry_reentry_loop_contract_summary
        manifest["retry_reentry_loop_contract_path"] = str(retry_reentry_loop_contract_path)

        endgame_closure_contract_payload = build_endgame_closure_contract_surface(
            run_id=resolved_job_id,
            completion_contract_payload=completion_contract_payload,
            approval_transport_payload=approval_transport_payload,
            reconcile_contract_payload=reconcile_contract_payload,
            execution_authorization_gate_payload=execution_authorization_gate_payload,
            bounded_execution_bridge_payload=bounded_execution_bridge_payload,
            execution_result_contract_payload=execution_result_contract_payload,
            verification_closure_contract_payload=verification_closure_contract_payload,
            retry_reentry_loop_contract_payload=retry_reentry_loop_contract_payload,
            run_state_payload=run_state_payload,
            artifact_presence={
                name: (run_root / name).exists()
                for name in manifest["artifact_ownership"].values()
            },
        )
        endgame_closure_contract_path = run_root / "endgame_closure_contract.json"
        _write_json(endgame_closure_contract_path, endgame_closure_contract_payload)
        endgame_closure_contract_summary = build_endgame_closure_run_state_summary_surface(
            endgame_closure_contract_payload
        )
        run_state_payload.update(endgame_closure_contract_summary)
        manifest["endgame_closure_contract_summary"] = endgame_closure_contract_summary
        manifest["endgame_closure_contract_path"] = str(endgame_closure_contract_path)

        facade = sys.modules["automation.orchestration.planned_execution_runner"]
        contract_context: dict[str, Any] = {
            "run_id": resolved_job_id,
            "objective_contract_payload": objective_contract_payload,
            "run_state_payload": run_state_payload,
            "manifest_units": manifest_units,
            "adapter": self.adapter,
            "dry_run": dry_run,
            "now": self.now,
            "execution_repo_path": execution_repo,
            "contract_artifact_index_payload": {},
            "lane_stabilization_contract_payload": {},
            "endgame_closure_contract_payload": endgame_closure_contract_payload,
            "retry_reentry_loop_contract_payload": {},
            "artifact_retention_contract_payload": {},
            "retention_manifest_payload": {},
            "observability_rollup_payload": {},
        }
        failure_bucketing_payload = _call_contract_builder(
            facade.build_failure_bucketing_hardening_contract_surface,
            **contract_context,
        )
        run_state_payload.update(
            build_failure_bucketing_hardening_run_state_summary_surface(
                failure_bucketing_payload
            )
        )
        loop_hardening_payload = _call_contract_builder(
            facade.build_loop_hardening_contract_surface,
            **contract_context,
        )
        fleet_safety_payload = _call_contract_builder(
            facade.build_fleet_safety_control_contract_surface,
            **contract_context,
            failure_bucketing_hardening_payload=failure_bucketing_payload,
            loop_hardening_contract_payload=loop_hardening_payload,
        )
        approval_email_payload = _call_contract_builder(
            facade.build_approval_email_delivery_contract_surface,
            **contract_context,
            fleet_safety_control_payload=fleet_safety_payload,
            failure_bucketing_hardening_payload=failure_bucketing_payload,
            loop_hardening_contract_payload=loop_hardening_payload,
        )
        approval_runtime_rules_payload = _call_contract_builder(
            build_approval_runtime_rules_contract_surface,
            **contract_context,
            approval_email_delivery_payload=approval_email_payload,
        )
        approval_delivery_handoff_payload = _call_contract_builder(
            build_approval_delivery_handoff_contract_surface,
            **contract_context,
            approval_email_delivery_payload=approval_email_payload,
            approval_runtime_rules_payload=approval_runtime_rules_payload,
            fleet_safety_control_payload=fleet_safety_payload,
            failure_bucketing_hardening_payload=failure_bucketing_payload,
        )
        approval_response_payload = _call_contract_builder(
            facade.build_approval_response_contract_surface,
            **contract_context,
            fleet_safety_control_payload=fleet_safety_payload,
            approval_email_delivery_payload=approval_email_payload,
            approval_runtime_rules_payload=approval_runtime_rules_payload,
            approval_delivery_handoff_payload=approval_delivery_handoff_payload,
        )
        approved_restart_payload = _call_contract_builder(
            facade.build_approved_restart_contract_surface,
            **contract_context,
            approval_response_payload=approval_response_payload,
            approval_email_delivery_payload=approval_email_payload,
            approval_delivery_handoff_payload=approval_delivery_handoff_payload,
            approval_runtime_rules_payload=approval_runtime_rules_payload,
            fleet_safety_control_payload=fleet_safety_payload,
            failure_bucketing_hardening_payload=failure_bucketing_payload,
        )
        approval_safety_payload = _call_contract_builder(
            facade.build_approval_safety_contract_surface,
            **contract_context,
            approval_email_delivery_payload=approval_email_payload,
            approval_response_payload=approval_response_payload,
            approved_restart_payload=approved_restart_payload,
            approval_delivery_handoff_payload=approval_delivery_handoff_payload,
            approval_runtime_rules_payload=approval_runtime_rules_payload,
            failure_bucketing_hardening_payload=failure_bucketing_payload,
        )
        run_state_payload.update(
            build_approval_email_delivery_run_state_summary_surface(approval_email_payload)
        )
        run_state_payload.update(
            build_approval_runtime_rules_run_state_summary_surface(
                approval_runtime_rules_payload
            )
        )
        run_state_payload.update(
            build_approval_delivery_handoff_run_state_summary_surface(
                approval_delivery_handoff_payload
            )
        )
        run_state_payload.update(
            build_approval_response_run_state_summary_surface(approval_response_payload)
        )
        run_state_payload.update(
            build_approved_restart_run_state_summary_surface(approved_restart_payload)
        )
        run_state_payload.update(
            build_approval_safety_run_state_summary_surface(approval_safety_payload)
        )

        approval_artifacts = (
            (
                "approval_email_delivery_contract",
                "approval_email_delivery_contract.json",
                approval_email_payload,
                build_approval_email_delivery_summary_surface,
            ),
            (
                "approval_runtime_rules_contract",
                "approval_runtime_rules_contract.json",
                approval_runtime_rules_payload,
                build_approval_runtime_rules_summary_surface,
            ),
            (
                "approval_delivery_handoff_contract",
                "approval_delivery_handoff_contract.json",
                approval_delivery_handoff_payload,
                build_approval_delivery_handoff_summary_surface,
            ),
            (
                "approval_response_contract",
                "approval_response_contract.json",
                approval_response_payload,
                build_approval_response_summary_surface,
            ),
            (
                "approved_restart_contract",
                "approved_restart_contract.json",
                approved_restart_payload,
                build_approved_restart_summary_surface,
            ),
            (
                "approval_safety_contract",
                "approval_safety_contract.json",
                approval_safety_payload,
                build_approval_safety_summary_surface,
            ),
        )
        approval_paths_by_role = {
            "objective_contract": str(objective_contract_path),
            "completion_contract": str(completion_contract_path),
            "approval_transport": str(approval_transport_path),
            "reconcile_contract": str(reconcile_contract_path),
            "repair_suggestion_contract": str(repair_suggestion_contract_path),
            "repair_plan_transport": str(repair_plan_transport_path),
            "repair_approval_binding": str(repair_approval_binding_path),
            "execution_authorization_gate": str(execution_authorization_gate_path),
            "bounded_execution_bridge": str(bounded_execution_bridge_path),
            "execution_result_contract": str(execution_result_contract_path),
            "verification_closure_contract": str(verification_closure_contract_path),
            "retry_reentry_loop_contract": str(retry_reentry_loop_contract_path),
            "endgame_closure_contract": str(endgame_closure_contract_path),
        }
        approval_summaries_by_role = {
            "objective_contract": manifest["objective_contract_summary"],
            "completion_contract": completion_contract_summary,
            "approval_transport": approval_transport_summary,
            "reconcile_contract": reconcile_contract_summary,
            "repair_suggestion_contract": repair_suggestion_contract_summary,
            "repair_plan_transport": repair_plan_transport_summary,
            "repair_approval_binding": repair_approval_binding_summary,
            "execution_authorization_gate": execution_authorization_gate_summary,
            "bounded_execution_bridge": bounded_execution_bridge_summary,
            "execution_result_contract": execution_result_contract_summary,
            "verification_closure_contract": verification_closure_contract_summary,
            "retry_reentry_loop_contract": retry_reentry_loop_contract_summary,
            "endgame_closure_contract": endgame_closure_contract_summary,
        }
        for role, artifact_name, payload, summary_builder in approval_artifacts:
            artifact_path = run_root / artifact_name
            _write_json(artifact_path, payload)
            summary = summary_builder(payload)
            manifest[f"{role}_summary"] = summary
            manifest[f"{role}_path"] = str(artifact_path)
            approval_paths_by_role[role] = str(artifact_path)
            approval_summaries_by_role[role] = summary
        manifest["contract_artifact_index"] = build_contract_artifact_index(
            paths_by_role=approval_paths_by_role,
            summaries_by_role=approval_summaries_by_role,
        )
        contract_context_with_index = {
            **contract_context,
            "contract_artifact_index_payload": manifest["contract_artifact_index"],
            "loop_hardening_contract_payload": loop_hardening_payload,
        }
        lane_stabilization_payload = _call_contract_builder(
            build_lane_stabilization_contract_surface,
            **contract_context_with_index,
        )
        observability_rollup_payload = _call_contract_builder(
            build_observability_rollup_contract_surface,
            **{
                **contract_context_with_index,
                "lane_stabilization_contract_payload": lane_stabilization_payload,
            },
        )
        failure_bucket_rollup_payload = _call_contract_builder(
            build_failure_bucket_rollup_surface,
            **{
                **contract_context_with_index,
                "observability_rollup_payload": observability_rollup_payload,
            },
        )
        fleet_run_rollup_payload = _call_contract_builder(
            build_fleet_run_rollup_surface,
            **{
                **contract_context_with_index,
                "observability_rollup_payload": observability_rollup_payload,
            },
        )
        contract_artifacts = (
            ("loop_hardening_contract", "loop_hardening_contract.json", loop_hardening_payload, build_loop_hardening_run_state_summary_surface),
            ("lane_stabilization_contract", "lane_stabilization_contract.json", lane_stabilization_payload, build_lane_stabilization_run_state_summary_surface),
            ("observability_rollup_contract", "observability_rollup_contract.json", observability_rollup_payload, build_observability_rollup_contract_summary_surface),
            ("failure_bucket_rollup", "failure_bucket_rollup.json", failure_bucket_rollup_payload, build_failure_bucket_rollup_summary_surface),
            ("fleet_run_rollup", "fleet_run_rollup.json", fleet_run_rollup_payload, build_fleet_run_rollup_summary_surface),
            ("failure_bucketing_hardening_contract", "failure_bucketing_hardening_contract.json", failure_bucketing_payload, build_failure_bucketing_hardening_summary_surface),
            ("fleet_safety_control_contract", "fleet_safety_control_contract.json", fleet_safety_payload, build_fleet_safety_control_summary_surface),
        )
        for role, artifact_name, payload, summary_builder in contract_artifacts:
            artifact_path = run_root / artifact_name
            _write_json(artifact_path, payload)
            summary = summary_builder(payload)
            manifest[f"{role}_summary"] = summary
            manifest[f"{role}_path"] = str(artifact_path)
            approval_paths_by_role[role] = str(artifact_path)
            approval_summaries_by_role[role] = summary
            if role in {
                "loop_hardening_contract",
                "lane_stabilization_contract",
            }:
                run_state_payload.update(summary)

        retention_manifest_payload = build_retention_manifest_surface(
            run_id=resolved_job_id,
            objective_contract_payload=objective_contract_payload,
            paths_by_role=approval_paths_by_role,
            summaries_by_role=approval_summaries_by_role,
            contract_artifact_index_payload=manifest["contract_artifact_index"],
            manifest_payload=manifest,
        )
        retention_manifest_path = run_root / "retention_manifest.json"
        _write_json(retention_manifest_path, retention_manifest_payload)
        retention_manifest_summary = build_retention_manifest_summary_surface(
            retention_manifest_payload
        )
        manifest["retention_manifest_summary"] = retention_manifest_summary
        manifest["retention_manifest_path"] = str(retention_manifest_path)
        artifact_retention_payload = build_artifact_retention_contract_surface(
            run_id=resolved_job_id,
            objective_contract_payload=objective_contract_payload,
            retention_manifest_payload=retention_manifest_payload,
            contract_artifact_index_payload=manifest["contract_artifact_index"],
            observability_rollup_payload=observability_rollup_payload,
            failure_bucketing_hardening_payload=failure_bucketing_payload,
            endgame_closure_contract_payload=endgame_closure_contract_payload,
        )
        artifact_retention_path = run_root / "artifact_retention_contract.json"
        _write_json(artifact_retention_path, artifact_retention_payload)
        artifact_retention_summary = build_artifact_retention_summary_surface(
            artifact_retention_payload
        )
        manifest["artifact_retention_contract_summary"] = artifact_retention_summary
        manifest["artifact_retention_contract_path"] = str(artifact_retention_path)
        run_state_payload.update(build_observability_rollup_run_state_summary_surface(observability_rollup_payload))
        run_state_payload.update(build_artifact_retention_run_state_summary_surface(artifact_retention_payload))
        run_state_payload.update(build_fleet_safety_control_run_state_summary_surface(fleet_safety_payload))
        manifest["contract_artifact_index"] = build_contract_artifact_index(
            paths_by_role={
                **approval_paths_by_role,
                "retention_manifest": str(retention_manifest_path),
                "artifact_retention_contract": str(artifact_retention_path),
            },
            summaries_by_role={
                **approval_summaries_by_role,
                "retention_manifest": retention_manifest_summary,
                "artifact_retention_contract": artifact_retention_summary,
            },
        )
        from automation.orchestration.planned_runner.summaries.approved_restart_payload import (
            _build_approved_restart_execution_contract_surface,
        )
        from automation.orchestration.planned_runner.summaries.browser_payload import (
            _build_approved_restart_execution_summary_surface,
        )

        approved_restart_execution_path = (
            run_root / "approved_restart_execution_contract.json"
        )
        prior_approved_restart_execution_payload = _read_json_object_if_exists(
            approved_restart_execution_path
        )
        try:
            approved_restart_execution_payload = (
                _build_approved_restart_execution_contract_surface(
                run_id=resolved_job_id,
                execution_repo_path=execution_repo,
                objective_contract_payload=objective_contract_payload,
                approval_email_delivery_payload=approval_email_payload,
                fleet_safety_control_payload=fleet_safety_payload,
                approval_runtime_rules_payload=approval_runtime_rules_payload,
                failure_bucketing_hardening_payload=failure_bucketing_payload,
                loop_hardening_contract_payload=loop_hardening_payload,
                approved_restart_payload=approved_restart_payload,
                approval_response_payload=approval_response_payload,
                approval_safety_payload=approval_safety_payload,
                prior_approved_restart_execution_payload=(
                    prior_approved_restart_execution_payload
                ),
                manifest_units=manifest_units,
                adapter=self.adapter,
                dry_run=dry_run,
                now=self.now,
                )
            )
        except (ImportError, AttributeError, NameError, TypeError, ValueError):
            approved_restart_execution_payload = {
                "schema_version": "v1",
                "run_id": resolved_job_id,
                "automatic_restart_execution_status": "not_executed",
                "automatic_restart_executed": False,
                "automatic_restart_attempted": False,
                "automatic_restart_count": 0,
                "automatic_restart_additional_execution_blocked": True,
                "automatic_restart_chained": False,
                "automatic_restart_result_status": "not_started",
                "automatic_restart_launch_pr_id": "",
                "automatic_restart_execution_reason": (
                    "restart_not_executed_split_helper_unavailable"
                ),
                "approval_skip_allowed": False,
                "approval_skip_applied": False,
                "approval_skip_gate_decision": "require_human_approval",
                "approval_skip_human_gate_preserved": True,
                "approval_skip_reason": "skip_invalid_or_insufficient_truth",
            }
        _write_json(
            approved_restart_execution_path,
            approved_restart_execution_payload,
        )
        manifest["approved_restart_execution_contract_path"] = str(
            approved_restart_execution_path
        )
        manifest["approved_restart_execution_contract_summary"] = (
            _build_approved_restart_execution_summary_surface(
                approved_restart_execution_payload
            )
        )
        _write_json(run_state_path, run_state_payload)

        from automation.orchestration.run_state_summary_contract import (
            build_manifest_run_state_summary_contract_surface,
            select_manifest_run_state_summary_compact,
        )

        run_state_summary_compact = select_manifest_run_state_summary_compact(
            run_state_payload
        )
        manifest["progression_summary"] = {
            "final_unit_state": review_terminal_state,
            "units_reviewed": len(manifest_units),
            "next_action": _normalize_text(decision_payload.get("next_action"), default=""),
            "progression_outcome": _normalize_text(
                decision_payload.get("progression_outcome"), default=""
            ),
            "result_acceptance": _normalize_text(
                decision_payload.get("result_acceptance"), default=""
            ),
            "progression_rule_id": _normalize_text(
                decision_payload.get("progression_rule_id"), default=""
            ),
        }
        manifest["run_state_summary_compact"] = run_state_summary_compact
        manifest["run_state_summary"] = dict(run_state_summary_compact)
        manifest["run_state_summary_contract"] = (
            build_manifest_run_state_summary_contract_surface()
        )

        manifest.update(
            {
                "decision_summary": decision_payload,
                "next_action_path": str(decision_path),
                "run_state_path": str(run_state_path),
                "manifest_path": str(manifest_path),
                "repository": _normalize_text(
                    policy_payload.get("repository"),
                    default=_normalize_text(
                        project_brief.get("target_repo"),
                        default=_normalize_text(repo_facts.get("repo"), default=""),
                    ),
                ),
            }
        )
        handoff_path = run_root / "action_handoff.json"
        handoff_payload = build_action_handoff_payload(
            job_id=resolved_job_id,
            decision_payload=decision_payload,
            now=self.now,
            external_evidence=github_read_evidence,
        )
        _write_json(handoff_path, handoff_payload)
        updated_retry_context = handoff_payload.get("updated_retry_context")
        if isinstance(updated_retry_context, Mapping):
            retry_context_store.set(
                job_id=resolved_job_id,
                retry_context=updated_retry_context,
                updated_at=_normalize_text(
                    handoff_payload.get("handoff_created_at"),
                    default=_iso_now(self.now),
                ),
            )
        manifest["action_handoff_path"] = str(handoff_path)
        manifest["retry_context_store_path"] = str(retry_context_store.path)
        manifest["handoff_summary"] = {
            "next_action": _normalize_text(handoff_payload.get("next_action"), default=""),
            "action_consumable": bool(handoff_payload.get("action_consumable", False)),
            "unsupported_reason": _normalize_text(
                handoff_payload.get("unsupported_reason"), default=""
            ),
        }
        _write_json(manifest_path, manifest)
        return manifest


__all__ = ["PlannedExecutionRunner", "DryRunCodexExecutionTransport"]
