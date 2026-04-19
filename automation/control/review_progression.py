from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Mapping

OUTCOME_REJECT_CURRENT_RESULT = "reject_current_result"
OUTCOME_RETRY_WITH_SAME_PROMPT = "retry_with_same_prompt"
OUTCOME_RETRY_WITH_REPAIR_PROMPT = "retry_with_repair_prompt"
OUTCOME_PROCEED_TO_NEXT_STEP = "proceed_to_next_step"
OUTCOME_CONSERVATIVE_ESCALATION = "conservative_escalation"

RESULT_ACCEPTED = "accept_current_result"
RESULT_REJECTED = "reject_current_result"


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _as_non_negative_int(value: Any, *, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return max(0, value)
    if isinstance(value, str):
        text = value.strip()
        if text and text.lstrip("-").isdigit():
            return max(0, int(text))
    return default


@dataclass(frozen=True)
class ProgressionInputs:
    category_mismatch: int
    scope_drift: int
    explicit_rollback: int
    refusal_or_conflict: int
    contradictory: int
    contract_missing: int
    contract_identity_conflict: int
    unbounded_contract: int
    missing_progression_metadata: int
    contract_gating_required: bool
    validation_failure: int
    execution_failure: int
    missing_artifacts: int
    missing_signals: int
    all_completed_and_passed: bool
    is_dry_run: bool
    run_status: str
    retry_budget_remaining: int
    prior_retry_class: str
    missing_signal_count: int


def _build_result(
    *,
    outcome: str,
    next_action: str,
    reason: str,
    rule_id: str,
    result_acceptance: str,
) -> dict[str, str]:
    return {
        "outcome": outcome,
        "next_action": next_action,
        "reason": reason,
        "rule_id": rule_id,
        "result_acceptance": result_acceptance,
    }


def normalize_progression_inputs(
    *,
    signals: Mapping[str, Any],
    retry_context: Mapping[str, Any],
) -> ProgressionInputs:
    return ProgressionInputs(
        category_mismatch=_as_non_negative_int(signals.get("category_mismatch"), default=0),
        scope_drift=_as_non_negative_int(signals.get("scope_drift"), default=0),
        explicit_rollback=_as_non_negative_int(signals.get("explicit_rollback"), default=0),
        refusal_or_conflict=_as_non_negative_int(signals.get("refusal_or_conflict"), default=0),
        contradictory=_as_non_negative_int(signals.get("contradictory"), default=0),
        contract_missing=_as_non_negative_int(signals.get("contract_missing"), default=0),
        contract_identity_conflict=_as_non_negative_int(signals.get("contract_identity_conflict"), default=0),
        unbounded_contract=_as_non_negative_int(signals.get("unbounded_contract"), default=0),
        missing_progression_metadata=_as_non_negative_int(signals.get("missing_progression_metadata"), default=0),
        contract_gating_required=bool(signals.get("contract_gating_required", False)),
        validation_failure=_as_non_negative_int(signals.get("validation_failure"), default=0),
        execution_failure=_as_non_negative_int(signals.get("execution_failure"), default=0),
        missing_artifacts=_as_non_negative_int(signals.get("missing_artifacts"), default=0),
        missing_signals=_as_non_negative_int(signals.get("missing_signals"), default=0),
        all_completed_and_passed=bool(signals.get("all_completed_and_passed", False)),
        is_dry_run=bool(signals.get("is_dry_run", False)),
        run_status=_normalize_text(signals.get("run_status"), default=""),
        retry_budget_remaining=_as_non_negative_int(retry_context.get("retry_budget_remaining"), default=0),
        prior_retry_class=_normalize_text(retry_context.get("prior_retry_class"), default=""),
        missing_signal_count=_as_non_negative_int(retry_context.get("missing_signal_count"), default=0),
    )


def evaluate_review_progression_outcome(
    *,
    signals: Mapping[str, Any],
    retry_context: Mapping[str, Any],
) -> dict[str, str]:
    inputs = normalize_progression_inputs(signals=signals, retry_context=retry_context)
    missing_total = inputs.missing_artifacts + inputs.missing_signals

    # Ordered, deterministic matrix; first match wins.
    if inputs.category_mismatch > 0:
        return _build_result(
            outcome=OUTCOME_REJECT_CURRENT_RESULT,
            next_action="roadmap_replan",
            reason="tier/category mismatch detected against pr_plan intent",
            rule_id="reject_category_mismatch",
            result_acceptance=RESULT_REJECTED,
        )
    if inputs.scope_drift > 0:
        return _build_result(
            outcome=OUTCOME_REJECT_CURRENT_RESULT,
            next_action="prompt_recompile",
            reason="scope drift detected against pr_plan touched_files",
            rule_id="reject_scope_drift",
            result_acceptance=RESULT_REJECTED,
        )
    if inputs.explicit_rollback > 0:
        return _build_result(
            outcome=OUTCOME_REJECT_CURRENT_RESULT,
            next_action="rollback_required",
            reason="explicit rollback requirement signaled by normalized result",
            rule_id="reject_explicit_rollback",
            result_acceptance=RESULT_REJECTED,
        )
    if inputs.refusal_or_conflict > 0:
        return _build_result(
            outcome=OUTCOME_CONSERVATIVE_ESCALATION,
            next_action="escalate_to_human",
            reason="explicit refusal/conflict signals require conservative escalation",
            rule_id="escalate_refusal_or_conflict",
            result_acceptance=RESULT_REJECTED,
        )
    if inputs.contradictory > 0:
        return _build_result(
            outcome=OUTCOME_CONSERVATIVE_ESCALATION,
            next_action="escalate_to_human",
            reason="contradictory artifact identities detected",
            rule_id="escalate_contradictory_artifacts",
            result_acceptance=RESULT_REJECTED,
        )
    if inputs.contract_identity_conflict > 0:
        return _build_result(
            outcome=OUTCOME_CONSERVATIVE_ESCALATION,
            next_action="escalate_to_human",
            reason="contract identity mismatch detected for bounded step or prompt contract",
            rule_id="escalate_contract_identity_conflict",
            result_acceptance=RESULT_REJECTED,
        )
    if inputs.contract_gating_required and inputs.contract_missing > 0:
        return _build_result(
            outcome=OUTCOME_REJECT_CURRENT_RESULT,
            next_action="signal_recollect",
            reason="contract sidecar artifacts are required but missing",
            rule_id="reject_missing_contract_artifacts",
            result_acceptance=RESULT_REJECTED,
        )
    if inputs.contract_gating_required and inputs.missing_progression_metadata > 0:
        return _build_result(
            outcome=OUTCOME_REJECT_CURRENT_RESULT,
            next_action="signal_recollect",
            reason="progression metadata missing from structured contracts",
            rule_id="reject_missing_progression_metadata",
            result_acceptance=RESULT_REJECTED,
        )
    if inputs.contract_gating_required and inputs.unbounded_contract > 0:
        return _build_result(
            outcome=OUTCOME_REJECT_CURRENT_RESULT,
            next_action="roadmap_replan",
            reason="bounded planned-step contract is not explicitly bounded",
            rule_id="reject_unbounded_step_contract",
            result_acceptance=RESULT_REJECTED,
        )
    if inputs.validation_failure > 0 and inputs.retry_budget_remaining <= 0:
        return _build_result(
            outcome=OUTCOME_CONSERVATIVE_ESCALATION,
            next_action="escalate_to_human",
            reason="validation failure with exhausted retry budget",
            rule_id="escalate_validation_retry_budget_exhausted",
            result_acceptance=RESULT_REJECTED,
        )
    if inputs.validation_failure > 0 and inputs.prior_retry_class == "repair_prompt_retry":
        return _build_result(
            outcome=OUTCOME_CONSERVATIVE_ESCALATION,
            next_action="escalate_to_human",
            reason="repair_prompt_retry already attempted and failed",
            rule_id="escalate_validation_retry_class_exhausted",
            result_acceptance=RESULT_REJECTED,
        )
    if inputs.validation_failure > 0:
        return _build_result(
            outcome=OUTCOME_RETRY_WITH_REPAIR_PROMPT,
            next_action="repair_prompt_retry",
            reason="validation/test failure after execution completion",
            rule_id="retry_validation_with_repair_prompt",
            result_acceptance=RESULT_REJECTED,
        )
    if inputs.execution_failure > 0 and inputs.retry_budget_remaining <= 0:
        return _build_result(
            outcome=OUTCOME_CONSERVATIVE_ESCALATION,
            next_action="escalate_to_human",
            reason="execution failure with exhausted retry budget",
            rule_id="escalate_execution_retry_budget_exhausted",
            result_acceptance=RESULT_REJECTED,
        )
    if inputs.execution_failure > 0 and inputs.prior_retry_class == "same_prompt_retry":
        return _build_result(
            outcome=OUTCOME_CONSERVATIVE_ESCALATION,
            next_action="escalate_to_human",
            reason="same_prompt_retry already attempted and failed",
            rule_id="escalate_execution_retry_class_exhausted",
            result_acceptance=RESULT_REJECTED,
        )
    if inputs.execution_failure > 0:
        return _build_result(
            outcome=OUTCOME_RETRY_WITH_SAME_PROMPT,
            next_action="same_prompt_retry",
            reason="explicit execution/tool failure with valid planned scope",
            rule_id="retry_execution_with_same_prompt",
            result_acceptance=RESULT_REJECTED,
        )
    if missing_total > 0 and inputs.missing_signal_count >= 2:
        return _build_result(
            outcome=OUTCOME_CONSERVATIVE_ESCALATION,
            next_action="escalate_to_human",
            reason="missing or incomplete execution signals observed repeatedly",
            rule_id="escalate_missing_signal_repeated",
            result_acceptance=RESULT_REJECTED,
        )
    if missing_total > 0:
        return _build_result(
            outcome=OUTCOME_REJECT_CURRENT_RESULT,
            next_action="signal_recollect",
            reason="missing or incomplete artifacts/signals require recollection",
            rule_id="reject_missing_signal_once",
            result_acceptance=RESULT_REJECTED,
        )
    if inputs.all_completed_and_passed and not inputs.is_dry_run:
        return _build_result(
            outcome=OUTCOME_PROCEED_TO_NEXT_STEP,
            next_action="proceed_to_pr",
            reason="all units completed with passing verification signals",
            rule_id="proceed_all_completed_and_verified",
            result_acceptance=RESULT_ACCEPTED,
        )
    if inputs.is_dry_run and inputs.run_status == "dry_run_completed":
        return _build_result(
            outcome=OUTCOME_REJECT_CURRENT_RESULT,
            next_action="signal_recollect",
            reason="dry_run_completed does not imply execution success",
            rule_id="reject_dry_run_completed_without_execution",
            result_acceptance=RESULT_REJECTED,
        )
    return _build_result(
        outcome=OUTCOME_CONSERVATIVE_ESCALATION,
        next_action="escalate_to_human",
        reason="unable to derive a safe deterministic automated next action",
        rule_id="escalate_unknown_or_ambiguous",
        result_acceptance=RESULT_REJECTED,
    )
