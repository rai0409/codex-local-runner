from __future__ import annotations

from typing import Any
from typing import Mapping

LANE_STABILIZATION_CONTRACT_SCHEMA_VERSION = "v1"

LANE_STATUSES = {
    "lane_valid",
    "lane_transition_ready",
    "lane_transition_blocked",
    "lane_mismatch",
    "lane_stop_required",
    "not_applicable",
    "insufficient_truth",
}

LANE_DECISIONS = {
    "stay_in_lane",
    "transition_lane",
    "hold_current_lane",
    "escalate_manual",
    "stop_terminal",
    "not_applicable",
}

LANE_VALIDITIES = {
    "valid",
    "partial",
    "malformed",
    "insufficient_truth",
}

LANE_CONFIDENCE_LEVELS = {
    "high",
    "medium",
    "low",
}

LANE_VOCABULARY = {
    "truth_gathering",
    "manual_review_preparation",
    "replan_preparation",
    "closure_followup",
    "bounded_github_update",
    "bounded_local_patch",
    "unknown",
}

LANE_TRANSITION_STATUSES = {
    "not_required",
    "ready",
    "blocked",
    "invalid",
    "unknown",
}

LANE_TRANSITION_DECISIONS = {
    "transition",
    "hold",
    "block",
    "escalate_manual",
    "not_applicable",
}

LANE_PRECONDITIONS_STATUSES = {
    "satisfied",
    "not_satisfied",
    "unknown",
}

LANE_RETRY_POLICY_CLASSES = {
    "no_retry",
    "same_lane_bounded",
    "repair_bounded",
    "recollect_only",
    "replan_only",
    "manual_only",
    "unknown",
}

LANE_VERIFICATION_POLICY_CLASSES = {
    "truth_check",
    "execution_result_check",
    "closure_check",
    "manual_review_check",
    "unknown",
}

LANE_ESCALATION_POLICY_CLASSES = {
    "none",
    "manual_review",
    "manual_closure",
    "manual_replan",
    "unknown",
}

LANE_SOURCE_POSTURES = {
    "post_lane_stabilization",
    "insufficient_truth",
    "not_applicable",
}

LANE_REASON_CODES = {
    "malformed_lane_inputs",
    "insufficient_lane_truth",
    "not_applicable_terminal",
    "lane_mismatch_detected",
    "lane_transition_blocked",
    "lane_transition_ready",
    "lane_valid_stay",
    "lane_hold",
    "hardening_stop_required",
    "hardening_freeze_required",
    "transition_budget_exhausted",
    "manual_review_required",
    "replan_required",
    "truth_gathering_required",
    "closure_followup_required",
    "unknown",
    "no_reason",
}

LANE_REASON_ORDER = (
    "malformed_lane_inputs",
    "insufficient_lane_truth",
    "not_applicable_terminal",
    "lane_mismatch_detected",
    "lane_transition_blocked",
    "lane_transition_ready",
    "lane_valid_stay",
    "lane_hold",
    "hardening_stop_required",
    "hardening_freeze_required",
    "transition_budget_exhausted",
    "manual_review_required",
    "replan_required",
    "truth_gathering_required",
    "closure_followup_required",
    "unknown",
    "no_reason",
)

LANE_STABILIZATION_RUN_STATE_SUMMARY_SAFE_FIELDS = (
    "lane_stabilization_contract_present",
    "lane_status",
    "lane_decision",
    "lane_validity",
    "lane_confidence",
    "current_lane",
    "target_lane",
    "lane_transition_status",
    "lane_transition_decision",
    "lane_preconditions_status",
    "lane_retry_policy_class",
    "lane_verification_policy_class",
    "lane_escalation_policy_class",
    "lane_attempt_budget",
    "lane_reentry_budget",
    "lane_transition_count",
    "max_lane_transition_count",
    "lane_primary_reason",
    "lane_valid",
    "lane_mismatch_detected",
    "lane_transition_required",
    "lane_transition_allowed",
    "lane_transition_blocked",
    "lane_stop_required",
    "lane_manual_review_required",
    "lane_replan_required",
    "lane_truth_gathering_required",
    "lane_execution_allowed",
)

_DEFAULT_MAX_ATTEMPT_BUDGET = 2
_DEFAULT_MAX_REENTRY_BUDGET = 2
_DEFAULT_MAX_LANE_TRANSITION_COUNT = 2

_ALLOWED_SUPPORTING_REFS = (
    "run_state.next_safe_action",
    "run_state.policy_primary_action",
    "run_state.policy_status",
    "completion_contract.completion_status",
    "completion_contract.completion_blocked_reason",
    "approval_transport.approval_status",
    "approval_transport.approval_blocked_reason",
    "reconcile_contract.reconcile_status",
    "reconcile_contract.reconcile_primary_mismatch",
    "retry_reentry_loop_contract.retry_loop_status",
    "retry_reentry_loop_contract.retry_loop_decision",
    "loop_hardening_contract.loop_hardening_status",
    "loop_hardening_contract.loop_hardening_decision",
    "endgame_closure_contract.final_closure_class",
    "endgame_closure_contract.closure_resolution_status",
    "verification_closure_contract.verification_outcome",
    "execution_result_contract.execution_result_status",
    "bounded_execution_bridge.bounded_execution_status",
    "execution_authorization_gate.execution_authorization_status",
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


def _normalize_non_negative_int(value: Any, *, default: int = 0) -> int:
    if isinstance(value, bool):
        return max(0, default)
    if isinstance(value, int):
        return max(0, value)
    if isinstance(value, str):
        text = value.strip()
        if text.isdigit():
            return int(text)
    return max(0, default)


def _normalize_positive_int(value: Any, *, default: int) -> int:
    candidate = _normalize_non_negative_int(value, default=default)
    return candidate if candidate > 0 else default


def _normalize_enum(value: Any, *, allowed: set[str], default: str) -> str:
    text = _normalize_text(value, default="")
    if text in allowed:
        return text
    return default


def _ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        text = _normalize_text(value, default="")
        if not text or text in seen:
            continue
        seen.add(text)
        ordered.append(text)
    return ordered


def _normalize_reason_codes(values: list[str]) -> list[str]:
    filtered = [value for value in _ordered_unique(values) if value in LANE_REASON_CODES]
    ordered: list[str] = []
    for reason in LANE_REASON_ORDER:
        if reason in filtered:
            ordered.append(reason)
    return ordered


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    if not text:
        return False
    lowered = text.lower()
    return any(needle in lowered for needle in needles)


def _infer_bounded_execution_lane(*, next_safe_hint: str, policy_primary_action: str) -> str:
    if _contains_any(next_safe_hint, ("pr", "merge", "push", "github")):
        return "bounded_github_update"
    if _contains_any(policy_primary_action, ("pr", "merge", "push", "github")):
        return "bounded_github_update"
    return "bounded_local_patch"


def _infer_target_lane(
    *,
    replan_required: bool,
    truth_gathering_required: bool,
    manual_required: bool,
    closure_followup_required: bool,
    authorization_status: str,
    bounded_execution_status: str,
    next_safe_hint: str,
    policy_primary_action: str,
) -> str:
    if replan_required:
        return "replan_preparation"
    if manual_required:
        return "manual_review_preparation"
    if closure_followup_required:
        return "closure_followup"
    if truth_gathering_required:
        return "truth_gathering"
    if authorization_status == "eligible" and bounded_execution_status == "ready":
        return _infer_bounded_execution_lane(
            next_safe_hint=next_safe_hint,
            policy_primary_action=policy_primary_action,
        )
    return "unknown"


def _infer_current_lane(
    *,
    explicit_current_lane: str,
    retry_loop_decision: str,
    final_closure_class: str,
    authorization_status: str,
    bounded_execution_status: str,
    next_safe_hint: str,
    policy_primary_action: str,
    fallback_target_lane: str,
) -> str:
    if explicit_current_lane in LANE_VOCABULARY:
        return explicit_current_lane

    if retry_loop_decision == "recollect":
        return "truth_gathering"
    if retry_loop_decision == "replan":
        return "replan_preparation"
    if retry_loop_decision == "escalate_manual":
        return "manual_review_preparation"

    if final_closure_class in {"completed_but_not_closed", "external_truth_pending"}:
        return "closure_followup"

    if authorization_status == "eligible" and bounded_execution_status == "ready":
        return _infer_bounded_execution_lane(
            next_safe_hint=next_safe_hint,
            policy_primary_action=policy_primary_action,
        )

    if fallback_target_lane in LANE_VOCABULARY and fallback_target_lane != "unknown":
        return fallback_target_lane
    return "unknown"


def _lane_policy_classes(
    *,
    lane: str,
    retry_loop_decision: str,
    manual_required: bool,
) -> tuple[str, str, str]:
    if lane == "truth_gathering":
        return (
            "recollect_only",
            "truth_check",
            "manual_review" if manual_required else "none",
        )
    if lane == "manual_review_preparation":
        return ("manual_only", "manual_review_check", "manual_review")
    if lane == "replan_preparation":
        return ("replan_only", "manual_review_check", "manual_replan")
    if lane == "closure_followup":
        return (
            "no_retry",
            "closure_check",
            "manual_closure" if manual_required else "none",
        )
    if lane in {"bounded_github_update", "bounded_local_patch"}:
        retry_class = "repair_bounded" if retry_loop_decision == "repair_retry" else "same_lane_bounded"
        return (retry_class, "execution_result_check", "manual_review" if manual_required else "none")
    return ("unknown", "unknown", "unknown")


def _lane_preconditions_status(
    *,
    lane: str,
    replan_required: bool,
    truth_gathering_required: bool,
    manual_required: bool,
    closure_followup_required: bool,
    authorization_status: str,
    bounded_execution_status: str,
    hardening_status: str,
    retry_loop_status: str,
) -> str:
    if lane == "truth_gathering":
        return "satisfied" if truth_gathering_required else "unknown"
    if lane == "manual_review_preparation":
        return "satisfied" if manual_required else "not_satisfied"
    if lane == "replan_preparation":
        return "satisfied" if replan_required else "not_satisfied"
    if lane == "closure_followup":
        return "satisfied" if closure_followup_required else "not_satisfied"
    if lane in {"bounded_github_update", "bounded_local_patch"}:
        execution_ready = (
            authorization_status == "eligible"
            and bounded_execution_status == "ready"
            and hardening_status not in {"freeze", "stop_required"}
            and retry_loop_status not in {"stop_required", "exhausted", "insufficient_truth"}
            and not replan_required
            and not truth_gathering_required
            and not manual_required
        )
        return "satisfied" if execution_ready else "not_satisfied"
    return "unknown"


def _build_supporting_refs(
    *,
    next_safe_hint: str,
    policy_primary_action: str,
    policy_status: str,
    completion_status: str,
    completion_blocked_reason: str,
    approval_status: str,
    approval_blocked_reason: str,
    reconcile_status: str,
    reconcile_primary_mismatch: str,
    retry_loop_status: str,
    retry_loop_decision: str,
    loop_hardening_status: str,
    loop_hardening_decision: str,
    final_closure_class: str,
    closure_resolution_status: str,
    verification_outcome: str,
    execution_result_status: str,
    bounded_execution_status: str,
    execution_authorization_status: str,
) -> list[str]:
    refs: list[str] = []
    if next_safe_hint:
        refs.append("run_state.next_safe_action")
    if policy_primary_action:
        refs.append("run_state.policy_primary_action")
    if policy_status:
        refs.append("run_state.policy_status")
    if completion_status:
        refs.append("completion_contract.completion_status")
    if completion_blocked_reason:
        refs.append("completion_contract.completion_blocked_reason")
    if approval_status:
        refs.append("approval_transport.approval_status")
    if approval_blocked_reason:
        refs.append("approval_transport.approval_blocked_reason")
    if reconcile_status:
        refs.append("reconcile_contract.reconcile_status")
    if reconcile_primary_mismatch:
        refs.append("reconcile_contract.reconcile_primary_mismatch")
    if retry_loop_status:
        refs.append("retry_reentry_loop_contract.retry_loop_status")
    if retry_loop_decision:
        refs.append("retry_reentry_loop_contract.retry_loop_decision")
    if loop_hardening_status:
        refs.append("loop_hardening_contract.loop_hardening_status")
    if loop_hardening_decision:
        refs.append("loop_hardening_contract.loop_hardening_decision")
    if final_closure_class:
        refs.append("endgame_closure_contract.final_closure_class")
    if closure_resolution_status:
        refs.append("endgame_closure_contract.closure_resolution_status")
    if verification_outcome:
        refs.append("verification_closure_contract.verification_outcome")
    if execution_result_status:
        refs.append("execution_result_contract.execution_result_status")
    if bounded_execution_status:
        refs.append("bounded_execution_bridge.bounded_execution_status")
    if execution_authorization_status:
        refs.append("execution_authorization_gate.execution_authorization_status")

    normalized = [ref for ref in _ordered_unique(refs) if ref in _ALLOWED_SUPPORTING_REFS]
    return normalized


def build_lane_stabilization_contract_surface(
    *,
    run_id: str,
    objective_contract_payload: Mapping[str, Any] | None,
    completion_contract_payload: Mapping[str, Any] | None,
    approval_transport_payload: Mapping[str, Any] | None,
    reconcile_contract_payload: Mapping[str, Any] | None,
    execution_authorization_gate_payload: Mapping[str, Any] | None,
    bounded_execution_bridge_payload: Mapping[str, Any] | None,
    execution_result_contract_payload: Mapping[str, Any] | None,
    verification_closure_contract_payload: Mapping[str, Any] | None,
    retry_reentry_loop_contract_payload: Mapping[str, Any] | None,
    endgame_closure_contract_payload: Mapping[str, Any] | None,
    loop_hardening_contract_payload: Mapping[str, Any] | None,
    run_state_payload: Mapping[str, Any] | None,
    artifact_presence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    objective = dict(objective_contract_payload or {})
    completion = dict(completion_contract_payload or {})
    approval = dict(approval_transport_payload or {})
    reconcile = dict(reconcile_contract_payload or {})
    execution_authorization = dict(execution_authorization_gate_payload or {})
    bounded_execution = dict(bounded_execution_bridge_payload or {})
    execution_result = dict(execution_result_contract_payload or {})
    verification = dict(verification_closure_contract_payload or {})
    retry_loop = dict(retry_reentry_loop_contract_payload or {})
    endgame = dict(endgame_closure_contract_payload or {})
    loop_hardening = dict(loop_hardening_contract_payload or {})
    run_state = dict(run_state_payload or {})
    artifacts = dict(artifact_presence or {})

    objective_id = _normalize_text(
        objective.get("objective_id")
        or completion.get("objective_id")
        or approval.get("objective_id")
        or reconcile.get("objective_id")
        or execution_authorization.get("objective_id")
        or bounded_execution.get("objective_id")
        or execution_result.get("objective_id")
        or verification.get("objective_id")
        or retry_loop.get("objective_id")
        or endgame.get("objective_id")
        or loop_hardening.get("objective_id")
        or run_state.get("objective_id"),
        default="",
    )

    retry_loop_status = _normalize_text(retry_loop.get("retry_loop_status"), default="")
    retry_loop_decision = _normalize_text(retry_loop.get("retry_loop_decision"), default="")
    verification_outcome = _normalize_text(verification.get("verification_outcome"), default="")
    final_closure_class = _normalize_text(endgame.get("final_closure_class"), default="")
    closure_resolution_status = _normalize_text(endgame.get("closure_resolution_status"), default="")
    execution_result_status = _normalize_text(execution_result.get("execution_result_status"), default="")
    execution_result_outcome = _normalize_text(execution_result.get("execution_result_outcome"), default="")
    bounded_execution_status = _normalize_text(bounded_execution.get("bounded_execution_status"), default="")
    execution_authorization_status = _normalize_text(
        execution_authorization.get("execution_authorization_status"),
        default="",
    )
    loop_hardening_status = _normalize_text(loop_hardening.get("loop_hardening_status"), default="")
    loop_hardening_decision = _normalize_text(loop_hardening.get("loop_hardening_decision"), default="")

    completion_status = _normalize_text(completion.get("completion_status"), default="")
    completion_blocked_reason = _normalize_text(
        completion.get("completion_blocked_reason")
        or completion.get("blocked_reason")
        or run_state.get("completion_blocked_reason"),
        default="",
    )
    approval_status = _normalize_text(approval.get("approval_status"), default="")
    approval_blocked_reason = _normalize_text(
        approval.get("approval_blocked_reason") or run_state.get("approval_blocked_reason"),
        default="",
    )
    reconcile_status = _normalize_text(reconcile.get("reconcile_status"), default="")
    reconcile_primary_mismatch = _normalize_text(
        reconcile.get("reconcile_primary_mismatch") or run_state.get("reconcile_primary_mismatch"),
        default="",
    )
    next_safe_hint = _normalize_text(run_state.get("next_safe_action"), default="")
    policy_primary_action = _normalize_text(run_state.get("policy_primary_action"), default="")
    policy_status = _normalize_text(run_state.get("policy_status"), default="")

    explicit_current_lane = _normalize_text(run_state.get("current_lane"), default="")
    explicit_current_lane = (
        explicit_current_lane if explicit_current_lane in LANE_VOCABULARY else ""
    )

    replan_required = any(
        (
            _normalize_bool(run_state.get("replan_required")),
            _normalize_bool(run_state.get("lane_replan_required")),
            _normalize_bool(retry_loop.get("replan_required")),
            retry_loop_decision == "replan",
        )
    )
    manual_required = any(
        (
            _normalize_bool(run_state.get("manual_escalation_required")),
            _normalize_bool(run_state.get("lane_manual_review_required")),
            _normalize_bool(retry_loop.get("manual_escalation_required")),
            _normalize_bool(loop_hardening.get("forced_manual_escalation_required")),
            _normalize_bool(verification.get("manual_closure_required")),
            _normalize_bool(endgame.get("manual_closure_only")),
            retry_loop_decision == "escalate_manual",
        )
    )
    truth_gathering_required = any(
        (
            _normalize_bool(run_state.get("recollect_required")),
            _normalize_bool(run_state.get("lane_truth_gathering_required")),
            _normalize_bool(run_state.get("repair_truth_gathering_required")),
            _normalize_bool(run_state.get("repair_plan_truth_gathering_required")),
            _normalize_bool(run_state.get("repair_approval_binding_truth_gathering_required")),
            _normalize_bool(run_state.get("execution_authorization_truth_gathering_required")),
            _normalize_bool(run_state.get("bounded_execution_truth_gathering_required")),
            retry_loop_decision == "recollect",
            retry_loop_status == "insufficient_truth",
            execution_authorization_status == "pending",
        )
    )
    closure_followup_required = any(
        (
            _normalize_bool(run_state.get("closure_followup_required")),
            verification_outcome in {"closure_followup", "external_truth_pending"},
            final_closure_class in {"completed_but_not_closed", "external_truth_pending"},
        )
    )

    inferred_target_lane = _infer_target_lane(
        replan_required=replan_required,
        truth_gathering_required=truth_gathering_required,
        manual_required=manual_required,
        closure_followup_required=closure_followup_required,
        authorization_status=execution_authorization_status,
        bounded_execution_status=bounded_execution_status,
        next_safe_hint=next_safe_hint,
        policy_primary_action=policy_primary_action,
    )

    current_lane = _infer_current_lane(
        explicit_current_lane=explicit_current_lane,
        retry_loop_decision=retry_loop_decision,
        final_closure_class=final_closure_class,
        authorization_status=execution_authorization_status,
        bounded_execution_status=bounded_execution_status,
        next_safe_hint=next_safe_hint,
        policy_primary_action=policy_primary_action,
        fallback_target_lane=inferred_target_lane,
    )

    target_lane = inferred_target_lane
    if target_lane == "unknown" and current_lane != "unknown":
        target_lane = current_lane

    lane_preconditions_status = _lane_preconditions_status(
        lane=target_lane,
        replan_required=replan_required,
        truth_gathering_required=truth_gathering_required,
        manual_required=manual_required,
        closure_followup_required=closure_followup_required,
        authorization_status=execution_authorization_status,
        bounded_execution_status=bounded_execution_status,
        hardening_status=loop_hardening_status,
        retry_loop_status=retry_loop_status,
    )

    lane_retry_policy_class, lane_verification_policy_class, lane_escalation_policy_class = _lane_policy_classes(
        lane=target_lane,
        retry_loop_decision=retry_loop_decision,
        manual_required=manual_required,
    )

    max_attempt_count = _normalize_positive_int(
        retry_loop.get("max_attempt_count") or run_state.get("max_attempt_count"),
        default=_DEFAULT_MAX_ATTEMPT_BUDGET,
    )
    max_reentry_count = _normalize_positive_int(
        retry_loop.get("max_reentry_count") or run_state.get("max_reentry_count"),
        default=_DEFAULT_MAX_REENTRY_BUDGET,
    )
    lane_transition_count = _normalize_non_negative_int(
        run_state.get("lane_transition_count")
        if run_state.get("lane_transition_count") is not None
        else retry_loop.get("reentry_count"),
        default=0,
    )
    max_lane_transition_count = _normalize_positive_int(
        run_state.get("max_lane_transition_count"),
        default=_DEFAULT_MAX_LANE_TRANSITION_COUNT,
    )

    if lane_retry_policy_class in {"same_lane_bounded", "repair_bounded"}:
        lane_attempt_budget = max_attempt_count
    else:
        lane_attempt_budget = 0

    if lane_retry_policy_class in {"recollect_only", "replan_only", "manual_only"}:
        lane_reentry_budget = max_reentry_count
    else:
        lane_reentry_budget = 0

    transition_budget_exhausted = lane_transition_count >= max_lane_transition_count

    lane_transition_required = (
        target_lane in LANE_VOCABULARY
        and target_lane != "unknown"
        and current_lane in LANE_VOCABULARY
        and current_lane != target_lane
    )

    bounded_lane = target_lane in {"bounded_github_update", "bounded_local_patch"}
    hardening_stop = loop_hardening_status == "stop_required" or _normalize_bool(
        loop_hardening.get("hardening_stop_required")
    )
    hardening_freeze = loop_hardening_status == "freeze" or _normalize_bool(
        loop_hardening.get("retry_freeze_required")
    )

    lane_mismatch_detected = False
    if explicit_current_lane and target_lane != "unknown" and explicit_current_lane != target_lane:
        lane_mismatch_detected = True
    if current_lane in {"bounded_github_update", "bounded_local_patch"} and (
        replan_required or truth_gathering_required or manual_required
    ):
        lane_mismatch_detected = True

    transition_preconditions_ok = lane_preconditions_status == "satisfied" and target_lane != "unknown"
    lane_transition_allowed = (
        lane_transition_required
        and not transition_budget_exhausted
        and not hardening_stop
        and transition_preconditions_ok
    )
    lane_transition_blocked = lane_transition_required and not lane_transition_allowed

    malformed_inputs = False
    required_surface_keys = (
        ("retry_reentry_loop_contract.json", retry_reentry_loop_contract_payload),
        ("loop_hardening_contract.json", loop_hardening_contract_payload),
        ("endgame_closure_contract.json", endgame_closure_contract_payload),
    )
    for key, surface in required_surface_keys:
        if _normalize_bool(artifacts.get(key)) and not isinstance(surface, Mapping):
            malformed_inputs = True
            break

    sparse_truth = not any(
        (
            retry_loop_status,
            retry_loop_decision,
            loop_hardening_status,
            loop_hardening_decision,
            final_closure_class,
            closure_resolution_status,
            verification_outcome,
            execution_result_status,
            execution_authorization_status,
            bounded_execution_status,
        )
    )

    not_applicable_terminal = any(
        (
            _normalize_bool(endgame.get("safely_closed")),
            final_closure_class == "safely_closed",
            _normalize_text(endgame.get("endgame_closure_status"), default="") == "safely_closed",
            retry_loop_status == "not_applicable",
        )
    )

    lane_status = "lane_valid"
    lane_decision = "stay_in_lane"
    lane_validity = "valid"
    lane_confidence = "medium"

    if malformed_inputs:
        lane_status = "insufficient_truth"
        lane_decision = "hold_current_lane"
        lane_validity = "malformed"
        lane_confidence = "low"
    elif sparse_truth:
        lane_status = "insufficient_truth"
        lane_decision = "hold_current_lane"
        lane_validity = "insufficient_truth"
        lane_confidence = "low"
    elif not_applicable_terminal:
        lane_status = "not_applicable"
        lane_decision = "not_applicable"
        lane_validity = "valid"
        lane_confidence = "high"
    elif lane_mismatch_detected:
        lane_status = "lane_mismatch"
        lane_decision = "transition_lane"
        lane_validity = "partial"
        lane_confidence = "medium"
    elif lane_transition_blocked:
        lane_status = "lane_transition_blocked"
        lane_decision = "transition_lane"
        lane_validity = "partial"
        lane_confidence = "low"
    elif lane_transition_allowed:
        lane_status = "lane_transition_ready"
        lane_decision = "transition_lane"
        lane_validity = "valid"
        lane_confidence = "medium"
    elif hardening_stop:
        lane_status = "lane_stop_required"
        lane_decision = "stop_terminal"
        lane_validity = "partial"
        lane_confidence = "low"
    elif lane_preconditions_status == "satisfied" and current_lane != "unknown":
        lane_status = "lane_valid"
        lane_decision = "stay_in_lane"
        lane_validity = "valid"
        lane_confidence = "high" if bounded_lane else "medium"
    else:
        lane_status = "lane_valid"
        lane_decision = "hold_current_lane"
        lane_validity = "partial"
        lane_confidence = "medium"

    # Boolean/status consistency hardening.
    if lane_status == "lane_mismatch":
        lane_mismatch_detected = True
        lane_transition_required = True
    if lane_status == "lane_transition_blocked":
        lane_transition_blocked = True
        lane_transition_required = True
    lane_stop_required = lane_status == "lane_stop_required"

    if lane_decision == "transition_lane":
        lane_transition_required = True
    if lane_transition_required and lane_decision not in {
        "transition_lane",
        "not_applicable",
        "hold_current_lane",
    }:
        lane_decision = "transition_lane"

    if lane_status == "not_applicable":
        lane_transition_required = False
        lane_transition_allowed = False
        lane_transition_blocked = False
        lane_mismatch_detected = False
        lane_stop_required = False
        lane_decision = "not_applicable"

    if lane_status == "lane_mismatch":
        lane_transition_blocked = False
        lane_stop_required = False
    if lane_status == "lane_transition_blocked":
        lane_mismatch_detected = False
        lane_stop_required = False
    if lane_status == "lane_stop_required":
        lane_mismatch_detected = False
        lane_transition_blocked = False

    lane_valid = lane_status == "lane_valid"

    lane_transition_status = "not_required"
    lane_transition_decision = "not_applicable"
    if lane_transition_required:
        if lane_status == "lane_transition_ready":
            lane_transition_status = "ready"
            lane_transition_decision = "transition"
        elif lane_status == "lane_transition_blocked":
            lane_transition_status = "blocked"
            lane_transition_decision = "block"
            if manual_required:
                lane_transition_decision = "escalate_manual"
        elif lane_status == "lane_mismatch":
            if target_lane == "unknown":
                lane_transition_status = "invalid"
                lane_transition_decision = "hold"
            elif lane_transition_allowed:
                lane_transition_status = "ready"
                lane_transition_decision = "transition"
            else:
                lane_transition_status = "blocked"
                lane_transition_decision = "block"
        else:
            lane_transition_status = "unknown"
            lane_transition_decision = "hold"

    lane_manual_review_required = manual_required or target_lane == "manual_review_preparation"
    lane_replan_required = replan_required or target_lane == "replan_preparation"
    lane_truth_gathering_required = (
        truth_gathering_required or target_lane == "truth_gathering"
    )

    lane_execution_allowed = (
        lane_preconditions_status == "satisfied"
        and lane_status == "lane_valid"
        and target_lane in {"bounded_github_update", "bounded_local_patch"}
        and execution_authorization_status == "eligible"
        and bounded_execution_status == "ready"
        and not lane_mismatch_detected
        and not lane_transition_required
        and not lane_transition_blocked
        and not lane_stop_required
        and not hardening_stop
        and not hardening_freeze
    )

    if lane_preconditions_status != "satisfied":
        lane_execution_allowed = False
    if lane_mismatch_detected:
        lane_execution_allowed = False

    if lane_decision == "escalate_manual":
        lane_manual_review_required = True
    if lane_decision == "stop_terminal":
        lane_stop_required = True
    if lane_decision == "transition_lane":
        lane_transition_required = True

    reason_lead = "lane_valid_stay"
    if lane_validity == "malformed":
        reason_lead = "malformed_lane_inputs"
    elif lane_validity == "insufficient_truth":
        reason_lead = "insufficient_lane_truth"
    elif lane_status == "not_applicable":
        reason_lead = "not_applicable_terminal"
    elif lane_status == "lane_mismatch":
        reason_lead = "lane_mismatch_detected"
    elif lane_status == "lane_transition_blocked":
        reason_lead = "lane_transition_blocked"
    elif lane_status == "lane_transition_ready":
        reason_lead = "lane_transition_ready"
    elif lane_status == "lane_stop_required":
        reason_lead = "hardening_stop_required"
    elif lane_decision == "hold_current_lane":
        reason_lead = "lane_hold"

    reason_candidates = [reason_lead]
    if hardening_stop:
        reason_candidates.append("hardening_stop_required")
    if hardening_freeze:
        reason_candidates.append("hardening_freeze_required")
    if transition_budget_exhausted:
        reason_candidates.append("transition_budget_exhausted")
    if lane_manual_review_required:
        reason_candidates.append("manual_review_required")
    if lane_replan_required:
        reason_candidates.append("replan_required")
    if lane_truth_gathering_required:
        reason_candidates.append("truth_gathering_required")
    if closure_followup_required:
        reason_candidates.append("closure_followup_required")
    if lane_status == "lane_valid" and lane_decision == "stay_in_lane":
        reason_candidates.append("lane_valid_stay")
    if lane_status == "lane_valid" and lane_decision == "hold_current_lane":
        reason_candidates.append("lane_hold")

    reason_codes = _normalize_reason_codes(reason_candidates)
    if not reason_codes:
        reason_codes = ["no_reason"]
    lane_primary_reason = reason_codes[0]

    lane_source_posture = "post_lane_stabilization"
    if lane_status == "insufficient_truth":
        lane_source_posture = "insufficient_truth"
    elif lane_status == "not_applicable":
        lane_source_posture = "not_applicable"

    if (
        _normalize_non_negative_int(run_state.get("lane_transition_count"), default=0)
        == _normalize_non_negative_int(run_state.get("lane_transition_count_compat"), default=0)
    ):
        # Alias-aware non-duplication: treat compact compatibility mirrors as one
        # source signal only.
        lane_transition_count = _normalize_non_negative_int(
            run_state.get("lane_transition_count"),
            default=lane_transition_count,
        )

    payload: dict[str, Any] = {
        "schema_version": LANE_STABILIZATION_CONTRACT_SCHEMA_VERSION,
        "run_id": _normalize_text(run_id, default=""),
        "objective_id": objective_id,
        "lane_status": _normalize_enum(
            lane_status,
            allowed=LANE_STATUSES,
            default="insufficient_truth",
        ),
        "lane_decision": _normalize_enum(
            lane_decision,
            allowed=LANE_DECISIONS,
            default="hold_current_lane",
        ),
        "lane_validity": _normalize_enum(
            lane_validity,
            allowed=LANE_VALIDITIES,
            default="insufficient_truth",
        ),
        "lane_confidence": _normalize_enum(
            lane_confidence,
            allowed=LANE_CONFIDENCE_LEVELS,
            default="low",
        ),
        "current_lane": _normalize_enum(
            current_lane,
            allowed=LANE_VOCABULARY,
            default="unknown",
        ),
        "target_lane": _normalize_enum(
            target_lane,
            allowed=LANE_VOCABULARY,
            default="unknown",
        ),
        "lane_transition_status": _normalize_enum(
            lane_transition_status,
            allowed=LANE_TRANSITION_STATUSES,
            default="unknown",
        ),
        "lane_transition_decision": _normalize_enum(
            lane_transition_decision,
            allowed=LANE_TRANSITION_DECISIONS,
            default="hold",
        ),
        "lane_preconditions_status": _normalize_enum(
            lane_preconditions_status,
            allowed=LANE_PRECONDITIONS_STATUSES,
            default="unknown",
        ),
        "lane_retry_policy_class": _normalize_enum(
            lane_retry_policy_class,
            allowed=LANE_RETRY_POLICY_CLASSES,
            default="unknown",
        ),
        "lane_verification_policy_class": _normalize_enum(
            lane_verification_policy_class,
            allowed=LANE_VERIFICATION_POLICY_CLASSES,
            default="unknown",
        ),
        "lane_escalation_policy_class": _normalize_enum(
            lane_escalation_policy_class,
            allowed=LANE_ESCALATION_POLICY_CLASSES,
            default="unknown",
        ),
        "lane_attempt_budget": lane_attempt_budget,
        "lane_reentry_budget": lane_reentry_budget,
        "lane_transition_count": lane_transition_count,
        "max_lane_transition_count": max_lane_transition_count,
        "lane_primary_reason": lane_primary_reason,
        "lane_reason_codes": reason_codes,
        "lane_valid": bool(lane_valid),
        "lane_mismatch_detected": bool(lane_mismatch_detected),
        "lane_transition_required": bool(lane_transition_required),
        "lane_transition_allowed": bool(lane_transition_allowed),
        "lane_transition_blocked": bool(lane_transition_blocked),
        "lane_stop_required": bool(lane_stop_required),
        "lane_manual_review_required": bool(lane_manual_review_required),
        "lane_replan_required": bool(lane_replan_required),
        "lane_truth_gathering_required": bool(lane_truth_gathering_required),
        "lane_execution_allowed": bool(lane_execution_allowed),
        "lane_source_posture": _normalize_enum(
            lane_source_posture,
            allowed=LANE_SOURCE_POSTURES,
            default="insufficient_truth",
        ),
        "retry_loop_status": retry_loop_status or "unknown",
        "retry_loop_decision": retry_loop_decision or "unknown",
        "loop_hardening_status": loop_hardening_status or "unknown",
        "loop_hardening_decision": loop_hardening_decision or "unknown",
        "final_closure_class": final_closure_class or "unknown",
        "closure_resolution_status": closure_resolution_status or "unknown",
        "verification_outcome": verification_outcome or "unknown",
        "execution_result_status": execution_result_status or "unknown",
        "bounded_execution_bridge_status": bounded_execution_status or "unknown",
        "execution_authorization_status": execution_authorization_status or "unknown",
        "supporting_compact_truth_refs": _build_supporting_refs(
            next_safe_hint=next_safe_hint,
            policy_primary_action=policy_primary_action,
            policy_status=policy_status,
            completion_status=completion_status,
            completion_blocked_reason=completion_blocked_reason,
            approval_status=approval_status,
            approval_blocked_reason=approval_blocked_reason,
            reconcile_status=reconcile_status,
            reconcile_primary_mismatch=reconcile_primary_mismatch,
            retry_loop_status=retry_loop_status,
            retry_loop_decision=retry_loop_decision,
            loop_hardening_status=loop_hardening_status,
            loop_hardening_decision=loop_hardening_decision,
            final_closure_class=final_closure_class,
            closure_resolution_status=closure_resolution_status,
            verification_outcome=verification_outcome,
            execution_result_status=execution_result_status,
            bounded_execution_status=bounded_execution_status,
            execution_authorization_status=execution_authorization_status,
        ),
    }

    if completion_blocked_reason:
        payload["completion_blocked_reason"] = completion_blocked_reason
    if approval_blocked_reason:
        payload["approval_blocked_reason"] = approval_blocked_reason
    if reconcile_primary_mismatch:
        payload["reconcile_primary_mismatch"] = reconcile_primary_mismatch
    if _normalize_text(retry_loop.get("retry_hint") or run_state.get("retry_hint"), default=""):
        payload["retry_hint"] = _normalize_text(
            retry_loop.get("retry_hint") or run_state.get("retry_hint"),
            default="",
        )
    if _normalize_text(retry_loop.get("reentry_hint") or run_state.get("reentry_hint"), default=""):
        payload["reentry_hint"] = _normalize_text(
            retry_loop.get("reentry_hint") or run_state.get("reentry_hint"),
            default="",
        )
    if _normalize_text(verification.get("closure_followup_hint") or run_state.get("closure_followup_hint"), default=""):
        payload["closure_followup_hint"] = _normalize_text(
            verification.get("closure_followup_hint") or run_state.get("closure_followup_hint"),
            default="",
        )
    if next_safe_hint:
        payload["next_safe_hint"] = next_safe_hint

    return payload


def build_lane_stabilization_run_state_summary_surface(
    lane_stabilization_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(lane_stabilization_payload or {})

    status = _normalize_enum(
        payload.get("lane_status"),
        allowed=LANE_STATUSES,
        default="insufficient_truth",
    )
    decision = _normalize_enum(
        payload.get("lane_decision"),
        allowed=LANE_DECISIONS,
        default="hold_current_lane",
    )
    validity = _normalize_enum(
        payload.get("lane_validity"),
        allowed=LANE_VALIDITIES,
        default="insufficient_truth",
    )
    confidence = _normalize_enum(
        payload.get("lane_confidence"),
        allowed=LANE_CONFIDENCE_LEVELS,
        default="low",
    )

    primary_reason = _normalize_text(payload.get("lane_primary_reason"), default="")
    if not primary_reason or primary_reason not in LANE_REASON_CODES:
        primary_reason = (
            "not_applicable_terminal"
            if status == "not_applicable"
            else "insufficient_lane_truth"
            if status == "insufficient_truth"
            else "lane_mismatch_detected"
            if status == "lane_mismatch"
            else "lane_transition_blocked"
            if status == "lane_transition_blocked"
            else "lane_transition_ready"
            if status == "lane_transition_ready"
            else "hardening_stop_required"
            if status == "lane_stop_required"
            else "lane_hold"
            if decision == "hold_current_lane"
            else "lane_valid_stay"
        )

    summary = {
        "lane_stabilization_contract_present": bool(payload.get("lane_stabilization_contract_present", False))
        or bool(status),
        "lane_status": status,
        "lane_decision": decision,
        "lane_validity": validity,
        "lane_confidence": confidence,
        "current_lane": _normalize_enum(
            payload.get("current_lane"),
            allowed=LANE_VOCABULARY,
            default="unknown",
        ),
        "target_lane": _normalize_enum(
            payload.get("target_lane"),
            allowed=LANE_VOCABULARY,
            default="unknown",
        ),
        "lane_transition_status": _normalize_enum(
            payload.get("lane_transition_status"),
            allowed=LANE_TRANSITION_STATUSES,
            default="unknown",
        ),
        "lane_transition_decision": _normalize_enum(
            payload.get("lane_transition_decision"),
            allowed=LANE_TRANSITION_DECISIONS,
            default="hold",
        ),
        "lane_preconditions_status": _normalize_enum(
            payload.get("lane_preconditions_status"),
            allowed=LANE_PRECONDITIONS_STATUSES,
            default="unknown",
        ),
        "lane_retry_policy_class": _normalize_enum(
            payload.get("lane_retry_policy_class"),
            allowed=LANE_RETRY_POLICY_CLASSES,
            default="unknown",
        ),
        "lane_verification_policy_class": _normalize_enum(
            payload.get("lane_verification_policy_class"),
            allowed=LANE_VERIFICATION_POLICY_CLASSES,
            default="unknown",
        ),
        "lane_escalation_policy_class": _normalize_enum(
            payload.get("lane_escalation_policy_class"),
            allowed=LANE_ESCALATION_POLICY_CLASSES,
            default="unknown",
        ),
        "lane_attempt_budget": _normalize_non_negative_int(payload.get("lane_attempt_budget"), default=0),
        "lane_reentry_budget": _normalize_non_negative_int(payload.get("lane_reentry_budget"), default=0),
        "lane_transition_count": _normalize_non_negative_int(payload.get("lane_transition_count"), default=0),
        "max_lane_transition_count": _normalize_positive_int(
            payload.get("max_lane_transition_count"),
            default=_DEFAULT_MAX_LANE_TRANSITION_COUNT,
        ),
        "lane_primary_reason": primary_reason,
        "lane_valid": _normalize_bool(payload.get("lane_valid")),
        "lane_mismatch_detected": _normalize_bool(payload.get("lane_mismatch_detected")),
        "lane_transition_required": _normalize_bool(payload.get("lane_transition_required")),
        "lane_transition_allowed": _normalize_bool(payload.get("lane_transition_allowed")),
        "lane_transition_blocked": _normalize_bool(payload.get("lane_transition_blocked")),
        "lane_stop_required": _normalize_bool(payload.get("lane_stop_required")),
        "lane_manual_review_required": _normalize_bool(payload.get("lane_manual_review_required")),
        "lane_replan_required": _normalize_bool(payload.get("lane_replan_required")),
        "lane_truth_gathering_required": _normalize_bool(payload.get("lane_truth_gathering_required")),
        "lane_execution_allowed": _normalize_bool(payload.get("lane_execution_allowed")),
    }

    if summary["lane_status"] == "lane_valid":
        summary["lane_valid"] = True
        summary["lane_mismatch_detected"] = False
        summary["lane_transition_blocked"] = False
        summary["lane_stop_required"] = False
    elif summary["lane_status"] == "lane_mismatch":
        summary["lane_valid"] = False
        summary["lane_mismatch_detected"] = True
        summary["lane_transition_required"] = True
        summary["lane_transition_blocked"] = False
        summary["lane_stop_required"] = False
    elif summary["lane_status"] == "lane_transition_blocked":
        summary["lane_valid"] = False
        summary["lane_mismatch_detected"] = False
        summary["lane_transition_required"] = True
        summary["lane_transition_blocked"] = True
        summary["lane_stop_required"] = False
    elif summary["lane_status"] == "lane_stop_required":
        summary["lane_valid"] = False
        summary["lane_mismatch_detected"] = False
        summary["lane_transition_blocked"] = False
        summary["lane_stop_required"] = True
    elif summary["lane_status"] == "not_applicable":
        summary["lane_valid"] = False
        summary["lane_mismatch_detected"] = False
        summary["lane_transition_required"] = False
        summary["lane_transition_allowed"] = False
        summary["lane_transition_blocked"] = False
        summary["lane_stop_required"] = False
        summary["lane_execution_allowed"] = False
        summary["lane_decision"] = "not_applicable"

    if summary["lane_decision"] == "transition_lane":
        summary["lane_transition_required"] = True
    if summary["lane_transition_required"] and summary["lane_decision"] not in {
        "transition_lane",
        "not_applicable",
    }:
        summary["lane_decision"] = "transition_lane"

    if summary["lane_transition_status"] == "ready":
        summary["lane_transition_required"] = True
        summary["lane_transition_allowed"] = True
    if summary["lane_transition_status"] == "blocked":
        summary["lane_transition_blocked"] = True
        summary["lane_transition_required"] = True

    if summary["lane_preconditions_status"] != "satisfied":
        summary["lane_execution_allowed"] = False
    if summary["lane_mismatch_detected"]:
        summary["lane_execution_allowed"] = False

    if summary["lane_status"] in {
        "lane_mismatch",
        "lane_transition_blocked",
        "lane_stop_required",
        "not_applicable",
        "insufficient_truth",
    }:
        summary["lane_execution_allowed"] = False

    return summary
