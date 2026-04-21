from __future__ import annotations

from typing import Any
from typing import Mapping

EXECUTION_RESULT_CONTRACT_SCHEMA_VERSION = "v1"

EXECUTION_RESULT_STATUSES = {
    "succeeded",
    "failed",
    "partial",
    "blocked",
    "not_executed",
    "unknown",
}

EXECUTION_RESULT_OUTCOMES = {
    "changes_applied",
    "no_changes",
    "patch_failed",
    "tests_failed",
    "command_failed",
    "blocked",
    "skipped",
    "unknown",
}

EXECUTION_RESULT_VALIDITIES = {
    "valid",
    "partial",
    "malformed",
    "missing",
    "unknown",
}

EXECUTION_RESULT_CONFIDENCE_LEVELS = {
    "high",
    "medium",
    "low",
}

EXECUTION_RESULT_SOURCE_POSTURES = {
    "ready",
    "deferred",
    "denied",
    "not_applicable",
    "insufficient_truth",
    "unknown",
}

EXECUTION_RESULT_REASON_CODES = {
    "bridge_blocked",
    "bridge_deferred",
    "bridge_not_applicable",
    "bridge_insufficient_truth",
    "authorization_denied",
    "not_attempted",
    "receipt_missing",
    "output_missing",
    "patch_failed",
    "tests_failed",
    "command_failed",
    "execution_failed",
    "execution_succeeded",
    "partial_evidence",
    "malformed_evidence",
    "conflicting_evidence",
    "unknown_evidence",
    "no_reason",
}

EXECUTION_RESULT_REASON_ORDER = (
    "authorization_denied",
    "bridge_blocked",
    "bridge_deferred",
    "bridge_not_applicable",
    "bridge_insufficient_truth",
    "not_attempted",
    "output_missing",
    "receipt_missing",
    "malformed_evidence",
    "conflicting_evidence",
    "patch_failed",
    "tests_failed",
    "command_failed",
    "execution_failed",
    "partial_evidence",
    "unknown_evidence",
    "execution_succeeded",
    "no_reason",
)

EXECUTION_RESULT_RUN_STATE_SUMMARY_SAFE_FIELDS = (
    "execution_result_contract_present",
    "execution_result_status",
    "execution_result_outcome",
    "execution_result_validity",
    "execution_result_confidence",
    "execution_result_primary_reason",
    "execution_result_attempted",
    "execution_result_receipt_present",
    "execution_result_output_present",
    "execution_result_manual_followup_required",
)

_ALLOWED_SUPPORTING_REFS = (
    "run_state.next_safe_action",
    "run_state.policy_primary_action",
    "run_state.policy_status",
    "run_state.commit_execution_executed",
    "run_state.push_execution_succeeded",
    "run_state.pr_execution_succeeded",
    "run_state.merge_execution_succeeded",
    "objective_contract.objective_status",
    "completion_contract.completion_status",
    "approval_transport.approval_status",
    "reconcile_contract.reconcile_status",
    "repair_plan_transport.repair_plan_status",
    "repair_approval_binding.repair_approval_binding_status",
    "execution_authorization_gate.execution_authorization_status",
    "bounded_execution_bridge.bounded_execution_status",
    "bounded_execution_bridge.bounded_execution_decision",
)


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes"}:
            return True
        if normalized in {"0", "false", "no"}:
            return False
    return False


def _normalize_enum(value: Any, *, allowed: set[str], default: str) -> str:
    text = _normalize_text(value, default="")
    if text in allowed:
        return text
    return default


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = _normalize_text(item, default="")
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def _normalize_reason_codes(values: list[str]) -> list[str]:
    seen: set[str] = set()
    filtered: list[str] = []
    for value in values:
        if value in EXECUTION_RESULT_REASON_CODES and value not in seen:
            seen.add(value)
            filtered.append(value)
    ordered: list[str] = []
    for reason in EXECUTION_RESULT_REASON_ORDER:
        if reason in filtered:
            ordered.append(reason)
    return ordered


def _normalize_source_posture_from_bridge(
    *,
    bridge_status: str,
    bridge_denied: bool,
    authorization_status: str,
) -> str:
    if authorization_status == "denied" or bridge_denied:
        return "denied"
    if bridge_status == "ready":
        return "ready"
    if bridge_status == "deferred":
        return "deferred"
    if bridge_status == "not_applicable":
        return "not_applicable"
    if bridge_status == "insufficient_truth":
        return "insufficient_truth"
    if bridge_status == "blocked":
        return "deferred"
    return "unknown"


def _parse_command_success(command_results: list[Mapping[str, Any]], verify_status: str) -> tuple[bool, bool]:
    if command_results:
        statuses = [
            _normalize_text(item.get("status"), default="").lower()
            for item in command_results
            if isinstance(item, Mapping)
        ]
        if statuses:
            succeeded = all(status in {"passed", "success", "succeeded", "ok", "0"} for status in statuses)
            return True, succeeded
    if verify_status == "passed":
        return True, True
    if verify_status == "failed":
        return True, False
    return False, False


def _build_supporting_refs(
    *,
    next_safe_action: str,
    policy_primary_action: str,
    policy_status: str,
    commit_execution_executed: bool,
    push_execution_succeeded: bool,
    pr_execution_succeeded: bool,
    merge_execution_succeeded: bool,
    objective_status: str,
    completion_status: str,
    approval_status: str,
    reconcile_status: str,
    repair_plan_status: str,
    repair_approval_binding_status: str,
    execution_authorization_status: str,
    bounded_execution_status: str,
    bounded_execution_decision: str,
) -> list[str]:
    refs: list[str] = []
    if next_safe_action:
        refs.append("run_state.next_safe_action")
    if policy_primary_action:
        refs.append("run_state.policy_primary_action")
    if policy_status:
        refs.append("run_state.policy_status")
    if commit_execution_executed:
        refs.append("run_state.commit_execution_executed")
    if push_execution_succeeded:
        refs.append("run_state.push_execution_succeeded")
    if pr_execution_succeeded:
        refs.append("run_state.pr_execution_succeeded")
    if merge_execution_succeeded:
        refs.append("run_state.merge_execution_succeeded")
    if objective_status:
        refs.append("objective_contract.objective_status")
    if completion_status:
        refs.append("completion_contract.completion_status")
    if approval_status:
        refs.append("approval_transport.approval_status")
    if reconcile_status:
        refs.append("reconcile_contract.reconcile_status")
    if repair_plan_status:
        refs.append("repair_plan_transport.repair_plan_status")
    if repair_approval_binding_status:
        refs.append("repair_approval_binding.repair_approval_binding_status")
    if execution_authorization_status:
        refs.append("execution_authorization_gate.execution_authorization_status")
    if bounded_execution_status:
        refs.append("bounded_execution_bridge.bounded_execution_status")
    if bounded_execution_decision:
        refs.append("bounded_execution_bridge.bounded_execution_decision")

    ordered: list[str] = []
    for allowed in _ALLOWED_SUPPORTING_REFS:
        if allowed in refs and allowed not in ordered:
            ordered.append(allowed)
    return ordered


def build_execution_result_contract_surface(
    *,
    run_id: str,
    objective_contract_payload: Mapping[str, Any] | None,
    completion_contract_payload: Mapping[str, Any] | None,
    approval_transport_payload: Mapping[str, Any] | None,
    reconcile_contract_payload: Mapping[str, Any] | None,
    repair_plan_transport_payload: Mapping[str, Any] | None,
    repair_approval_binding_payload: Mapping[str, Any] | None,
    execution_authorization_gate_payload: Mapping[str, Any] | None,
    bounded_execution_bridge_payload: Mapping[str, Any] | None,
    run_state_payload: Mapping[str, Any] | None,
    execution_records: list[Mapping[str, Any]] | None = None,
    artifact_presence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    objective = dict(objective_contract_payload or {})
    completion = dict(completion_contract_payload or {})
    approval = dict(approval_transport_payload or {})
    reconcile = dict(reconcile_contract_payload or {})
    repair_plan = dict(repair_plan_transport_payload or {})
    repair_binding = dict(repair_approval_binding_payload or {})
    authorization = dict(execution_authorization_gate_payload or {})
    bounded = dict(bounded_execution_bridge_payload or {})
    run_state = dict(run_state_payload or {})
    artifacts = dict(artifact_presence or {})
    records = list(execution_records or [])

    objective_id = _normalize_text(
        objective.get("objective_id")
        or completion.get("objective_id")
        or approval.get("objective_id")
        or reconcile.get("objective_id")
        or repair_plan.get("objective_id")
        or repair_binding.get("objective_id")
        or authorization.get("objective_id")
        or bounded.get("objective_id")
        or run_state.get("objective_id"),
        default="",
    )
    objective_summary = _normalize_text(
        objective.get("objective_summary") or run_state.get("objective_summary"),
        default="",
    )
    requested_outcome = _normalize_text(
        objective.get("requested_outcome") or run_state.get("requested_outcome"),
        default="",
    )

    bridge_status = _normalize_text(
        bounded.get("bounded_execution_status") or run_state.get("bounded_execution_status"),
        default="",
    )
    bridge_decision = _normalize_text(
        bounded.get("bounded_execution_decision") or run_state.get("bounded_execution_decision"),
        default="",
    )
    bridge_denied = _normalize_bool(bounded.get("bounded_execution_denied"))
    bridge_manual_required = _normalize_bool(
        bounded.get("bounded_execution_manual_required")
        if "bounded_execution_manual_required" in bounded
        else run_state.get("bounded_execution_manual_required")
    )

    authorization_status = _normalize_text(
        authorization.get("execution_authorization_status")
        or run_state.get("execution_authorization_status"),
        default="",
    )

    source_posture = _normalize_enum(
        _normalize_source_posture_from_bridge(
            bridge_status=bridge_status,
            bridge_denied=bridge_denied,
            authorization_status=authorization_status,
        ),
        allowed=EXECUTION_RESULT_SOURCE_POSTURES,
        default="unknown",
    )

    record_count = len(records)
    output_present = False
    receipt_present = False
    attempted = False
    malformed = False
    output_malformed = False
    receipt_malformed = False

    patch_present = False
    patch_applied = False
    test_result_present = False
    test_passed = False
    command_result_present = False
    command_succeeded = False

    any_exec_completed = False
    any_exec_failed = False
    any_exec_running = False
    any_exec_not_started = False
    any_tests_failed = False
    any_patch_failed = False
    any_command_failed = False

    result_artifact_path = ""
    execution_receipt_path = ""

    verify_statuses: list[str] = []
    command_statuses: list[str] = []

    for record in records:
        result_path = _normalize_text(record.get("result_path"), default="")
        receipt_path = _normalize_text(record.get("receipt_path"), default="")
        result_exists = _normalize_bool(record.get("result_exists"))
        receipt_exists = _normalize_bool(record.get("receipt_exists"))
        result_payload = record.get("result_payload") if isinstance(record.get("result_payload"), Mapping) else None
        receipt_payload = record.get("receipt_payload") if isinstance(record.get("receipt_payload"), Mapping) else None
        record_output_malformed = _normalize_bool(record.get("result_malformed"))
        record_receipt_malformed = _normalize_bool(record.get("receipt_malformed"))

        if not result_artifact_path and result_path:
            result_artifact_path = result_path
        if not execution_receipt_path and receipt_path:
            execution_receipt_path = receipt_path

        output_present = output_present or result_exists or isinstance(result_payload, Mapping)
        receipt_present = receipt_present or receipt_exists or isinstance(receipt_payload, Mapping)
        output_malformed = output_malformed or record_output_malformed
        receipt_malformed = receipt_malformed or record_receipt_malformed
        # Artifact/receipt presence is conservative attempt evidence even when payload parsing fails.
        attempted = (
            attempted
            or result_exists
            or receipt_exists
            or record_output_malformed
            or record_receipt_malformed
        )

        if not isinstance(result_payload, Mapping):
            continue

        execution = result_payload.get("execution") if isinstance(result_payload.get("execution"), Mapping) else {}
        execution_status = _normalize_text(execution.get("status"), default="").lower()
        attempt_count = execution.get("attempt_count")
        attempt_count_int = int(attempt_count) if isinstance(attempt_count, int) and attempt_count >= 0 else 0

        verify = execution.get("verify") if isinstance(execution.get("verify"), Mapping) else {}
        verify_status = _normalize_text(verify.get("status"), default="").lower()
        verify_statuses.append(verify_status)

        raw_execution = result_payload.get("raw_execution") if isinstance(result_payload.get("raw_execution"), Mapping) else {}
        raw_result = raw_execution.get("result") if isinstance(raw_execution.get("result"), Mapping) else {}
        raw_verify = raw_result.get("verify") if isinstance(raw_result.get("verify"), Mapping) else {}
        command_results = raw_verify.get("command_results") if isinstance(raw_verify.get("command_results"), list) else []

        changed_files = _normalize_string_list(result_payload.get("changed_files"))
        additions = result_payload.get("additions") if isinstance(result_payload.get("additions"), int) else 0
        deletions = result_payload.get("deletions") if isinstance(result_payload.get("deletions"), int) else 0
        generated_patch_summary = _normalize_text(result_payload.get("generated_patch_summary"), default="")
        failure_type = _normalize_text(result_payload.get("failure_type"), default="").lower()

        record_attempted = (
            attempt_count_int > 0
            or execution_status in {"completed", "failed", "timed_out", "running"}
        )
        attempted = attempted or record_attempted

        if execution_status == "completed":
            any_exec_completed = True
        elif execution_status in {"failed", "timed_out"}:
            any_exec_failed = True
        elif execution_status == "running":
            any_exec_running = True
        elif execution_status in {"not_started", ""}:
            any_exec_not_started = True

        record_patch_present = bool(generated_patch_summary or changed_files or additions > 0 or deletions > 0)
        record_patch_applied = bool(changed_files or additions > 0 or deletions > 0)
        patch_present = patch_present or record_patch_present
        patch_applied = patch_applied or record_patch_applied

        if "patch" in failure_type and not record_patch_applied:
            any_patch_failed = True

        record_test_result_present = verify_status in {"passed", "failed", "not_run"}
        record_test_passed = verify_status == "passed"
        test_result_present = test_result_present or record_test_result_present
        test_passed = test_passed or record_test_passed
        if verify_status == "failed":
            any_tests_failed = True

        has_command_result, command_ok = _parse_command_success(
            [item for item in command_results if isinstance(item, Mapping)],
            verify_status,
        )
        command_result_present = command_result_present or has_command_result
        command_succeeded = command_succeeded or command_ok
        if has_command_result and not command_ok:
            any_command_failed = True
        if has_command_result:
            command_statuses.append("succeeded" if command_ok else "failed")

    malformed = output_malformed or receipt_malformed

    if not attempted and _normalize_bool(run_state.get("commit_execution_executed")):
        attempted = True
    if not attempted and _normalize_bool(run_state.get("rollback_execution_attempted")):
        attempted = True

    conflicting_evidence = bool(
        attempted
        and any_exec_not_started
        and (any_exec_completed or any_exec_failed or any_exec_running)
    )

    if attempted:
        if malformed:
            status = "unknown"
        elif conflicting_evidence:
            status = "unknown"
        elif any_exec_running:
            status = "partial"
        elif any_patch_failed or any_tests_failed or any_command_failed or any_exec_failed:
            status = "failed"
        elif any_exec_completed:
            if any(verify == "not_run" for verify in verify_statuses):
                status = "partial"
            else:
                status = "succeeded"
        else:
            status = "partial"
    else:
        if bridge_status == "blocked" or source_posture == "denied":
            status = "blocked"
        elif source_posture in {"deferred", "not_applicable"}:
            status = "not_executed"
        elif source_posture == "ready":
            status = "not_executed"
        elif source_posture == "insufficient_truth":
            status = "unknown"
        else:
            status = "unknown"

    status = _normalize_enum(status, allowed=EXECUTION_RESULT_STATUSES, default="unknown")

    if status == "succeeded":
        outcome = "changes_applied" if patch_applied else "no_changes"
    elif status == "failed":
        if any_patch_failed:
            outcome = "patch_failed"
        elif any_tests_failed:
            outcome = "tests_failed"
        else:
            outcome = "command_failed"
    elif status == "blocked":
        outcome = "blocked"
    elif status == "not_executed":
        outcome = "skipped"
    else:
        outcome = "unknown"

    outcome = _normalize_enum(outcome, allowed=EXECUTION_RESULT_OUTCOMES, default="unknown")

    if malformed:
        validity = "malformed"
    elif attempted and not output_present:
        validity = "missing"
    elif attempted and not receipt_present:
        validity = "partial"
    elif status in {"partial"}:
        validity = "partial"
    elif status == "unknown":
        validity = "unknown"
    elif status == "not_executed" and source_posture == "insufficient_truth":
        validity = "unknown"
    else:
        validity = "valid"

    validity = _normalize_enum(validity, allowed=EXECUTION_RESULT_VALIDITIES, default="unknown")

    reason_candidates: list[str] = []
    if status == "blocked":
        if source_posture == "denied" or authorization_status == "denied":
            reason_candidates.append("authorization_denied")
        else:
            reason_candidates.append("bridge_blocked")
    if status == "not_executed":
        if source_posture == "not_applicable":
            reason_candidates.append("bridge_not_applicable")
        elif source_posture == "deferred":
            reason_candidates.append("bridge_deferred")
        elif source_posture == "insufficient_truth":
            reason_candidates.append("bridge_insufficient_truth")
        reason_candidates.append("not_attempted")
    if malformed:
        reason_candidates.append("malformed_evidence")
    if conflicting_evidence:
        reason_candidates.append("conflicting_evidence")
    if attempted and not output_present:
        reason_candidates.append("output_missing")
    if attempted and not receipt_present:
        reason_candidates.append("receipt_missing")
    if any_patch_failed:
        reason_candidates.append("patch_failed")
    if any_tests_failed:
        reason_candidates.append("tests_failed")
    if any_command_failed:
        reason_candidates.append("command_failed")
    if any_exec_failed:
        reason_candidates.append("execution_failed")
    if status == "partial":
        reason_candidates.append("partial_evidence")
    if status == "unknown":
        reason_candidates.append("unknown_evidence")
    if status == "succeeded":
        reason_candidates.append("execution_succeeded")

    reason_codes = _normalize_reason_codes(reason_candidates)
    if not reason_codes:
        reason_codes = ["no_reason"]
    primary_reason = reason_codes[0]

    if validity == "valid" and status in {"succeeded", "failed"} and attempted and output_present and receipt_present:
        confidence = "high"
    elif validity in {"valid", "partial"} and status in {"partial", "blocked", "not_executed", "failed"}:
        confidence = "medium"
    else:
        confidence = "low"

    confidence = _normalize_enum(
        confidence,
        allowed=EXECUTION_RESULT_CONFIDENCE_LEVELS,
        default="low",
    )

    status_flags = {
        "execution_result_blocked": status == "blocked",
        "execution_result_not_executed": status == "not_executed",
        "execution_result_partial": status == "partial",
        "execution_result_failed": status == "failed",
        "execution_result_succeeded": status == "succeeded",
        "execution_result_unknown": status == "unknown",
    }

    if status == "not_executed":
        attempted = False
    if attempted and status == "not_executed":
        status = "unknown"
        status_flags = {
            "execution_result_blocked": False,
            "execution_result_not_executed": False,
            "execution_result_partial": False,
            "execution_result_failed": False,
            "execution_result_succeeded": False,
            "execution_result_unknown": True,
        }

    manual_followup_required = bool(
        status in {"failed", "partial", "unknown", "blocked"}
        or bridge_manual_required
        or _normalize_bool(run_state.get("manual_intervention_required"))
    )

    if any_patch_failed:
        patch_apply_result = "failed"
    elif patch_applied:
        patch_apply_result = "applied"
    elif patch_present:
        patch_apply_result = "unknown"
    else:
        patch_apply_result = "not_applicable"

    if any_tests_failed:
        test_summary = "failed"
    elif test_passed:
        test_summary = "passed"
    elif test_result_present:
        test_summary = "not_run"
    else:
        test_summary = "missing"

    if any_command_failed:
        command_summary = "failed"
    elif command_succeeded:
        command_summary = "succeeded"
    elif command_result_present:
        command_summary = "partial"
    else:
        command_summary = "missing"

    next_safe_hint = _normalize_text(run_state.get("next_safe_action"), default="")

    payload: dict[str, Any] = {
        "schema_version": EXECUTION_RESULT_CONTRACT_SCHEMA_VERSION,
        "run_id": _normalize_text(run_id, default=""),
        "objective_id": objective_id,
        "execution_result_status": status,
        "execution_result_outcome": outcome,
        "execution_result_validity": validity,
        "execution_result_confidence": confidence,
        "execution_result_primary_reason": primary_reason,
        "execution_result_reason_codes": reason_codes,
        "execution_result_attempted": bool(attempted),
        "execution_result_receipt_present": bool(receipt_present),
        "execution_result_output_present": bool(output_present),
        "execution_result_patch_present": bool(patch_present),
        "execution_result_patch_applied": bool(patch_applied),
        "execution_result_test_result_present": bool(test_result_present),
        "execution_result_test_passed": bool(test_passed),
        "execution_result_command_result_present": bool(command_result_present),
        "execution_result_command_succeeded": bool(command_succeeded),
        **status_flags,
        "execution_result_manual_followup_required": bool(manual_followup_required),
        "execution_result_source_posture": source_posture,
        "execution_result_bridge_status": bridge_status or "unknown",
        "execution_result_bridge_decision": bridge_decision or "unknown",
        "execution_result_authorization_status": authorization_status or "unknown",
        "supporting_compact_truth_refs": _build_supporting_refs(
            next_safe_action=next_safe_hint,
            policy_primary_action=_normalize_text(run_state.get("policy_primary_action"), default=""),
            policy_status=_normalize_text(run_state.get("policy_status"), default=""),
            commit_execution_executed=_normalize_bool(run_state.get("commit_execution_executed")),
            push_execution_succeeded=_normalize_bool(run_state.get("push_execution_succeeded")),
            pr_execution_succeeded=_normalize_bool(run_state.get("pr_execution_succeeded")),
            merge_execution_succeeded=_normalize_bool(run_state.get("merge_execution_succeeded")),
            objective_status=_normalize_text(objective.get("objective_status"), default=""),
            completion_status=_normalize_text(completion.get("completion_status"), default=""),
            approval_status=_normalize_text(approval.get("approval_status"), default=""),
            reconcile_status=_normalize_text(reconcile.get("reconcile_status"), default=""),
            repair_plan_status=_normalize_text(repair_plan.get("repair_plan_status"), default=""),
            repair_approval_binding_status=_normalize_text(
                repair_binding.get("repair_approval_binding_status"), default=""
            ),
            execution_authorization_status=authorization_status,
            bounded_execution_status=bridge_status,
            bounded_execution_decision=bridge_decision,
        ),
    }

    # Optional compact details.
    if result_artifact_path:
        payload["result_artifact_path"] = result_artifact_path
    if execution_receipt_path:
        payload["execution_receipt_path"] = execution_receipt_path
    payload["patch_apply_result"] = patch_apply_result
    payload["test_summary"] = test_summary
    payload["command_summary"] = command_summary
    if next_safe_hint:
        payload["next_safe_hint"] = next_safe_hint
    if objective_summary:
        payload["objective_summary"] = objective_summary
    if requested_outcome:
        payload["requested_outcome"] = requested_outcome
    completion_blocked_reason = _normalize_text(
        completion.get("completion_blocked_reason") or run_state.get("completion_blocked_reason"),
        default="",
    )
    if completion_blocked_reason:
        payload["completion_blocked_reason"] = completion_blocked_reason
    approval_blocked_reason = _normalize_text(
        approval.get("approval_blocked_reason") or run_state.get("approval_blocked_reason"),
        default="",
    )
    if approval_blocked_reason:
        payload["approval_blocked_reason"] = approval_blocked_reason
    reconcile_primary_mismatch = _normalize_text(
        reconcile.get("reconcile_primary_mismatch") or run_state.get("reconcile_primary_mismatch"),
        default="",
    )
    if reconcile_primary_mismatch:
        payload["reconcile_primary_mismatch"] = reconcile_primary_mismatch
    if _normalize_text(run_state.get("policy_primary_action"), default=""):
        payload["policy_primary_action"] = _normalize_text(
            run_state.get("policy_primary_action"), default=""
        )

    # Ensure boolean/status consistency invariants.
    payload["execution_result_succeeded"] = payload["execution_result_status"] == "succeeded"
    payload["execution_result_failed"] = payload["execution_result_status"] == "failed"
    payload["execution_result_partial"] = payload["execution_result_status"] == "partial"
    payload["execution_result_blocked"] = payload["execution_result_status"] == "blocked"
    payload["execution_result_not_executed"] = payload["execution_result_status"] == "not_executed"
    payload["execution_result_unknown"] = payload["execution_result_status"] == "unknown"

    if payload["execution_result_attempted"] and payload["execution_result_status"] == "not_executed":
        payload["execution_result_status"] = "unknown"
        payload["execution_result_outcome"] = "unknown"
        payload["execution_result_primary_reason"] = "conflicting_evidence"
        payload["execution_result_reason_codes"] = ["conflicting_evidence", "unknown_evidence"]
        payload["execution_result_succeeded"] = False
        payload["execution_result_failed"] = False
        payload["execution_result_partial"] = False
        payload["execution_result_blocked"] = False
        payload["execution_result_not_executed"] = False
        payload["execution_result_unknown"] = True

    return payload


def build_execution_result_contract_run_state_summary_surface(
    execution_result_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(execution_result_payload or {})

    status = _normalize_enum(
        payload.get("execution_result_status"),
        allowed=EXECUTION_RESULT_STATUSES,
        default="unknown",
    )
    outcome = _normalize_enum(
        payload.get("execution_result_outcome"),
        allowed=EXECUTION_RESULT_OUTCOMES,
        default="unknown",
    )
    validity = _normalize_enum(
        payload.get("execution_result_validity"),
        allowed=EXECUTION_RESULT_VALIDITIES,
        default="unknown",
    )
    confidence = _normalize_enum(
        payload.get("execution_result_confidence"),
        allowed=EXECUTION_RESULT_CONFIDENCE_LEVELS,
        default="low",
    )
    primary_reason = _normalize_text(payload.get("execution_result_primary_reason"), default="")
    if not primary_reason or primary_reason not in EXECUTION_RESULT_REASON_CODES:
        if status == "succeeded":
            primary_reason = "execution_succeeded"
        elif status == "failed":
            primary_reason = "execution_failed"
        elif status == "blocked":
            primary_reason = "bridge_blocked"
        elif status == "not_executed":
            primary_reason = "not_attempted"
        elif status == "partial":
            primary_reason = "partial_evidence"
        else:
            primary_reason = "unknown_evidence"

    present = bool(payload.get("execution_result_contract_present", False)) or bool(
        status or outcome or validity
    )

    return {
        "execution_result_contract_present": bool(present),
        "execution_result_status": status,
        "execution_result_outcome": outcome,
        "execution_result_validity": validity,
        "execution_result_confidence": confidence,
        "execution_result_primary_reason": primary_reason,
        "execution_result_attempted": _normalize_bool(payload.get("execution_result_attempted")),
        "execution_result_receipt_present": _normalize_bool(
            payload.get("execution_result_receipt_present")
        ),
        "execution_result_output_present": _normalize_bool(
            payload.get("execution_result_output_present")
        ),
        "execution_result_manual_followup_required": _normalize_bool(
            payload.get("execution_result_manual_followup_required")
        ),
    }
