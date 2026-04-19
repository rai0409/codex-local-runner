from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from typing import Mapping

from automation.control.review_progression import evaluate_review_progression_outcome
from automation.control.retry_context import normalize_retry_context
from automation.control.retry_context import update_retry_context
from automation.planning.planned_step_contract import BOUNDED_STATUS_BOUNDED

ALLOWED_NEXT_ACTIONS = {
    "same_prompt_retry",
    "repair_prompt_retry",
    "signal_recollect",
    "wait_for_checks",
    "prompt_recompile",
    "roadmap_replan",
    "escalate_to_human",
    "proceed_to_pr",
    "proceed_to_merge",
    "rollback_required",
}

_REFUSAL_OR_CONFLICT_FAILURE_TYPES = {
    "auth_failure",
    "permission_denied",
    "forbidden",
    "api_failure",
    "unsupported_query",
    "precondition_changed",
    "conflict",
    "needs_human",
    "terminal_refusal",
    "requested_lane_conflict",
    "routing_conflict",
    "routing_refused",
}

_REFUSAL_OR_CONFLICT_MESSAGE_TOKENS = (
    "requested_lane_conflict",
    "lane_not_allowed",
    "routing_conflict",
    "routing_refused",
    "precondition_changed",
    "needs_human",
    "terminal refusal",
    "terminal_refusal",
    "permission denied",
    "forbidden",
    "auth_failure",
)

_REFUSAL_OR_CONFLICT_REASON_FIELDS = (
    "refusal_reason",
    "routing_reason",
    "failure_reason",
)

_CHECKPOINT_CONSERVATIVE_DECISIONS = {
    "manual_review_required",
    "escalate",
    "global_stop_recommended",
}


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


def _as_mapping(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _as_non_negative_int(value: Any, *, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return max(0, value)
    if isinstance(value, str):
        text = value.strip()
        if text and text.isdigit():
            return int(text)
    return default


def _has_refusal_or_conflict_surface(
    *,
    result: Mapping[str, Any],
    execution: Mapping[str, Any],
    failure_type: str,
    failure_message: str,
) -> bool:
    if failure_type in _REFUSAL_OR_CONFLICT_FAILURE_TYPES:
        return True
    if any(token in failure_message for token in _REFUSAL_OR_CONFLICT_MESSAGE_TOKENS):
        return True
    for field in _REFUSAL_OR_CONFLICT_REASON_FIELDS:
        result_reason = _normalize_text(result.get(field), default="").lower()
        if result_reason and any(token in result_reason for token in _REFUSAL_OR_CONFLICT_MESSAGE_TOKENS):
            return True
        execution_reason = _normalize_text(execution.get(field), default="").lower()
        if execution_reason and any(token in execution_reason for token in _REFUSAL_OR_CONFLICT_MESSAGE_TOKENS):
            return True
    return False


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _read_json_object_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return _read_json_object(path)


def _load_manifest(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "manifest.json"
    if not path.exists():
        raise ValueError(f"missing manifest.json in run directory: {run_dir}")
    return _read_json_object(path)


def _load_pr_plan(pr_plan: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(pr_plan, Mapping):
        return {"prs": []}
    return dict(pr_plan)


def _build_pr_plan_index(pr_plan: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    raw_prs = pr_plan.get("prs")
    if not isinstance(raw_prs, list):
        return index
    for raw in raw_prs:
        if not isinstance(raw, Mapping):
            continue
        pr_id = _normalize_text(raw.get("pr_id"))
        if not pr_id:
            continue
        index[pr_id] = dict(raw)
    return index


def _get_contract_progression_metadata(contract: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(contract, Mapping):
        return {}
    return dict(contract.get("progression_metadata")) if isinstance(contract.get("progression_metadata"), Mapping) else {}


def _extract_expected_scope_files(
    *,
    unit: Mapping[str, Any],
    pr_plan_unit: Mapping[str, Any] | None,
) -> list[str]:
    bounded_contract = _as_mapping(unit.get("bounded_step_contract"))
    prompt_contract = _as_mapping(unit.get("pr_implementation_prompt_contract"))
    bounded_progression = _get_contract_progression_metadata(bounded_contract)
    prompt_progression = _get_contract_progression_metadata(prompt_contract)
    task_scope = (
        dict(prompt_contract.get("task_scope"))
        if isinstance(prompt_contract, Mapping) and isinstance(prompt_contract.get("task_scope"), Mapping)
        else {}
    )
    sources = (
        bounded_progression.get("strict_scope_files"),
        bounded_contract.get("scope_in") if isinstance(bounded_contract, Mapping) else None,
        prompt_progression.get("strict_scope_files"),
        task_scope.get("scope_in"),
        pr_plan_unit.get("touched_files") if isinstance(pr_plan_unit, Mapping) else None,
    )
    for source in sources:
        items = _normalize_string_list(source, sort_items=True)
        if items:
            return items
    return []


def _extract_expected_tier_category(
    *,
    unit: Mapping[str, Any],
    pr_plan_unit: Mapping[str, Any] | None,
) -> str:
    bounded_contract = _as_mapping(unit.get("bounded_step_contract"))
    prompt_contract = _as_mapping(unit.get("pr_implementation_prompt_contract"))
    bounded_progression = _get_contract_progression_metadata(bounded_contract)
    prompt_progression = _get_contract_progression_metadata(prompt_contract)
    task_scope = (
        dict(prompt_contract.get("task_scope"))
        if isinstance(prompt_contract, Mapping) and isinstance(prompt_contract.get("task_scope"), Mapping)
        else {}
    )
    candidates = (
        bounded_progression.get("tier_category"),
        bounded_contract.get("tier_category") if isinstance(bounded_contract, Mapping) else None,
        prompt_progression.get("tier_category"),
        task_scope.get("tier_category"),
        pr_plan_unit.get("tier_category") if isinstance(pr_plan_unit, Mapping) else None,
    )
    for item in candidates:
        text = _normalize_text(item, default="")
        if text:
            return text
    return ""


def _has_contract_identity_mismatch(unit: Mapping[str, Any]) -> bool:
    pr_id = _normalize_text(unit.get("pr_id"), default="")
    if not pr_id:
        return True

    bounded_contract = _as_mapping(unit.get("bounded_step_contract"))
    if isinstance(bounded_contract, Mapping):
        step_id = _normalize_text(bounded_contract.get("step_id"), default="")
        bounded_progression = _get_contract_progression_metadata(bounded_contract)
        progression_step_id = _normalize_text(bounded_progression.get("planned_step_id"), default="")
        if step_id and step_id != pr_id:
            return True
        if progression_step_id and progression_step_id != pr_id:
            return True

    prompt_contract = _as_mapping(unit.get("pr_implementation_prompt_contract"))
    if isinstance(prompt_contract, Mapping):
        source_step_id = _normalize_text(prompt_contract.get("source_step_id"), default="")
        prompt_progression = _get_contract_progression_metadata(prompt_contract)
        progression_step_id = _normalize_text(prompt_progression.get("planned_step_id"), default="")
        if source_step_id and source_step_id != pr_id:
            return True
        if progression_step_id and progression_step_id != pr_id:
            return True

    return False


def _has_contract_progression_metadata(unit: Mapping[str, Any]) -> bool:
    bounded_contract = _as_mapping(unit.get("bounded_step_contract"))
    prompt_contract = _as_mapping(unit.get("pr_implementation_prompt_contract"))
    bounded_progression = _get_contract_progression_metadata(bounded_contract)
    prompt_progression = _get_contract_progression_metadata(prompt_contract)
    return bool(bounded_progression) and bool(prompt_progression)


def _is_bounded_contract_ready(unit: Mapping[str, Any]) -> bool:
    bounded_contract = _as_mapping(unit.get("bounded_step_contract"))
    if not isinstance(bounded_contract, Mapping):
        return False
    boundedness = (
        dict(bounded_contract.get("boundedness"))
        if isinstance(bounded_contract.get("boundedness"), Mapping)
        else {}
    )
    status = _normalize_text(boundedness.get("status"), default="")
    return status == BOUNDED_STATUS_BOUNDED


def _uses_contract_sidecars(unit: Mapping[str, Any]) -> bool:
    bounded_path = _normalize_text(unit.get("bounded_step_contract_path"), default="")
    prompt_path = _normalize_text(unit.get("pr_implementation_prompt_contract_path"), default="")
    if bounded_path or prompt_path:
        return True
    return isinstance(unit.get("bounded_step_contract"), Mapping) or isinstance(
        unit.get("pr_implementation_prompt_contract"), Mapping
    )


def _resolve_checkpoint_decision_path(
    *,
    raw_unit: Mapping[str, Any],
    result_path: Path,
) -> Path | None:
    explicit_path = _normalize_text(raw_unit.get("checkpoint_decision_path"), default="")
    if explicit_path:
        return Path(explicit_path)
    inferred_path = result_path.parent / "checkpoint_decision.json"
    if inferred_path.exists():
        return inferred_path
    return None


def _checkpoint_requires_conservative_stop(unit: Mapping[str, Any]) -> bool:
    checkpoint = _as_mapping(unit.get("checkpoint_decision"))
    if not isinstance(checkpoint, Mapping):
        return False
    decision = _normalize_text(checkpoint.get("decision"), default="")
    if decision in _CHECKPOINT_CONSERVATIVE_DECISIONS:
        return True
    return bool(checkpoint.get("global_stop_recommended", False))


def _apply_run_state_guardrail(
    *,
    decision: Mapping[str, Any],
    run_state: Mapping[str, Any],
) -> dict[str, Any]:
    normalized = dict(decision)
    current_next_action = _normalize_text(normalized.get("next_action"), default="")
    execution_intent_action = current_next_action in {
        "proceed_to_commit",
        "proceed_to_pr",
        "proceed_to_merge",
        "proceed_to_rollback",
        "rollback_required",
    }
    next_run_action = _normalize_text(run_state.get("next_run_action"), default="")
    global_stop_recommended = bool(run_state.get("global_stop_recommended", False)) or bool(
        run_state.get("global_stop", False)
    )
    rollback_evaluation_pending = bool(run_state.get("rollback_evaluation_pending", False)) or (
        next_run_action == "evaluate_rollback"
    )
    loop_next_safe_action = _normalize_text(run_state.get("next_safe_action"), default="")
    loop_blocked_reason = _normalize_text(run_state.get("loop_blocked_reason"), default="")
    loop_terminal = bool(run_state.get("terminal", False))
    loop_manual_required = bool(run_state.get("loop_manual_intervention_required", False))
    loop_replan_required = bool(run_state.get("loop_replan_required", False))
    authority_validation_blocked = bool(run_state.get("authority_validation_blocked", False))
    execution_authority_blocked = bool(run_state.get("execution_authority_blocked", False))
    validation_blocked = bool(run_state.get("validation_blocked", False))
    authority_validation_blocked_reason = _normalize_text(
        run_state.get("authority_validation_blocked_reason"),
        default="",
    )
    remote_github_blocked = bool(run_state.get("remote_github_blocked", False))
    remote_github_manual_required = bool(run_state.get("remote_github_manual_required", False))
    remote_github_missing_or_ambiguous = bool(run_state.get("remote_github_missing_or_ambiguous", False))
    remote_github_blocked_reason = _normalize_text(
        run_state.get("remote_github_blocked_reason"),
        default="",
    )
    rollback_aftermath_blocked = bool(run_state.get("rollback_aftermath_blocked", False))
    rollback_aftermath_manual_required = bool(
        run_state.get("rollback_aftermath_manual_required", False)
    )
    rollback_aftermath_missing_or_ambiguous = bool(
        run_state.get("rollback_aftermath_missing_or_ambiguous", False)
    )
    rollback_validation_failed = bool(run_state.get("rollback_validation_failed", False))
    rollback_remote_followup_required = bool(
        run_state.get("rollback_remote_followup_required", False)
    )
    rollback_manual_followup_required = bool(
        run_state.get("rollback_manual_followup_required", False)
    )
    rollback_aftermath_blocked_reason = _normalize_text(
        run_state.get("rollback_aftermath_blocked_reason"),
        default="",
    )
    policy_status = _normalize_text(run_state.get("policy_status"), default="")
    policy_blocked = bool(run_state.get("policy_blocked", False))
    policy_manual_required = bool(run_state.get("policy_manual_required", False))
    policy_replan_required = bool(run_state.get("policy_replan_required", False))
    policy_resume_allowed = bool(run_state.get("policy_resume_allowed", False))
    policy_terminal = bool(run_state.get("policy_terminal", False))
    policy_blocked_reason = _normalize_text(run_state.get("policy_blocked_reason"), default="")
    policy_blocked_reasons = [
        _normalize_text(item, default="")
        for item in run_state.get("policy_blocked_reasons", [])
        if _normalize_text(item, default="")
    ] if isinstance(run_state.get("policy_blocked_reasons"), list) else []
    policy_disallowed_actions = {
        _normalize_text(item, default="")
        for item in run_state.get("policy_disallowed_actions", [])
        if _normalize_text(item, default="")
    } if isinstance(run_state.get("policy_disallowed_actions"), list) else set()
    policy_has_surface = any(
        key in run_state
        for key in (
            "policy_status",
            "policy_blocked",
            "policy_manual_required",
            "policy_replan_required",
            "policy_terminal",
        )
    )

    if (
        execution_intent_action
        and policy_has_surface
        and current_next_action not in {"escalate_to_human", "roadmap_replan", "rollback_required"}
    ):
        policy_reason = policy_blocked_reason or (policy_blocked_reasons[0] if policy_blocked_reasons else "")
        reason_tail = f" ({policy_reason})" if policy_reason else ""
        if policy_terminal:
            normalized["next_action"] = "escalate_to_human"
            normalized["reason"] = (
                "run_state_policy_guardrail: terminal policy state denies execution-intent continuation"
                f"{reason_tail}"
            )
            normalized["progression_outcome"] = "conservative_escalation"
            normalized["result_acceptance"] = "reject_current_result"
            normalized["progression_rule_id"] = "run_state_policy_guardrail_terminal"
        elif policy_replan_required:
            normalized["next_action"] = "roadmap_replan"
            normalized["reason"] = (
                "run_state_policy_guardrail: policy requires replanning before execution-intent continuation"
                f"{reason_tail}"
            )
            normalized["progression_outcome"] = "conservative_escalation"
            normalized["result_acceptance"] = "reject_current_result"
            normalized["progression_rule_id"] = "run_state_policy_guardrail_replan_required"
        elif policy_status == "manual_only" or policy_manual_required:
            normalized["next_action"] = "escalate_to_human"
            normalized["reason"] = (
                "run_state_policy_guardrail: policy classified state as manual-only for execution-intent actions"
                f"{reason_tail}"
            )
            normalized["progression_outcome"] = "conservative_escalation"
            normalized["result_acceptance"] = "reject_current_result"
            normalized["progression_rule_id"] = "run_state_policy_guardrail_manual_only"
        elif current_next_action in policy_disallowed_actions:
            normalized["next_action"] = "escalate_to_human"
            normalized["reason"] = (
                "run_state_policy_guardrail: policy disallowed current execution-intent action"
                f"{reason_tail}"
            )
            normalized["progression_outcome"] = "conservative_escalation"
            normalized["result_acceptance"] = "reject_current_result"
            normalized["progression_rule_id"] = "run_state_policy_guardrail_action_disallowed"
        elif policy_blocked:
            normalized["next_action"] = "escalate_to_human"
            normalized["reason"] = (
                "run_state_policy_guardrail: policy blocked execution-intent continuation"
                f"{reason_tail}"
            )
            normalized["progression_outcome"] = "conservative_escalation"
            normalized["result_acceptance"] = "reject_current_result"
            normalized["progression_rule_id"] = "run_state_policy_guardrail_blocked"
        elif policy_status == "resume_eligible" and not policy_resume_allowed:
            normalized["next_action"] = "escalate_to_human"
            normalized["reason"] = (
                "run_state_policy_guardrail: policy marked state non-resumable for execution-intent continuation"
                f"{reason_tail}"
            )
            normalized["progression_outcome"] = "conservative_escalation"
            normalized["result_acceptance"] = "reject_current_result"
            normalized["progression_rule_id"] = "run_state_policy_guardrail_resume_denied"
    elif global_stop_recommended and current_next_action not in {"escalate_to_human", "rollback_required"}:
        normalized["next_action"] = "escalate_to_human"
        normalized["reason"] = "run_state_guardrail: global stop recommended by orchestration state"
        normalized["progression_outcome"] = "conservative_escalation"
        normalized["result_acceptance"] = "reject_current_result"
        normalized["progression_rule_id"] = "run_state_guardrail_global_stop"
    elif rollback_evaluation_pending and current_next_action not in {"rollback_required", "escalate_to_human"}:
        normalized["next_action"] = "rollback_required"
        normalized["reason"] = "run_state_guardrail: rollback evaluation pending at run level"
        normalized["progression_outcome"] = "reject_current_result"
        normalized["result_acceptance"] = "reject_current_result"
        normalized["progression_rule_id"] = "run_state_guardrail_rollback_pending"
    elif loop_next_safe_action == "execute_rollback" and current_next_action not in {
        "rollback_required",
        "escalate_to_human",
    }:
        normalized["next_action"] = "rollback_required"
        normalized["reason"] = "run_state_guardrail: loop selected rollback as next safe action"
        normalized["progression_outcome"] = "reject_current_result"
        normalized["result_acceptance"] = "reject_current_result"
        normalized["progression_rule_id"] = "run_state_guardrail_loop_rollback"
    elif (
        execution_intent_action
        and (
            authority_validation_blocked
            or execution_authority_blocked
            or validation_blocked
        )
    ) and current_next_action not in {"escalate_to_human", "rollback_required"}:
        reason_tail = f" ({authority_validation_blocked_reason})" if authority_validation_blocked_reason else ""
        normalized["next_action"] = "escalate_to_human"
        normalized["reason"] = (
            "run_state_guardrail: execution authority/validation gate blocked automatic continuation"
            f"{reason_tail}"
        )
        normalized["progression_outcome"] = "conservative_escalation"
        normalized["result_acceptance"] = "reject_current_result"
        normalized["progression_rule_id"] = "run_state_guardrail_authority_validation_blocked"
    elif (
        execution_intent_action
        and (
            remote_github_blocked
            or remote_github_manual_required
            or remote_github_missing_or_ambiguous
        )
    ) and current_next_action not in {"escalate_to_human", "rollback_required"}:
        reason_tail = f" ({remote_github_blocked_reason})" if remote_github_blocked_reason else ""
        normalized["next_action"] = "escalate_to_human"
        normalized["reason"] = (
            "run_state_guardrail: remote/github delivery truth blocked automatic continuation"
            f"{reason_tail}"
        )
        normalized["progression_outcome"] = "conservative_escalation"
        normalized["result_acceptance"] = "reject_current_result"
        normalized["progression_rule_id"] = "run_state_guardrail_remote_github_blocked"
    elif (
        execution_intent_action
        and (
            rollback_aftermath_blocked
            or rollback_aftermath_manual_required
            or rollback_aftermath_missing_or_ambiguous
            or rollback_validation_failed
            or rollback_remote_followup_required
            or rollback_manual_followup_required
        )
    ) and current_next_action not in {"escalate_to_human", "rollback_required"}:
        reason_tail = f" ({rollback_aftermath_blocked_reason})" if rollback_aftermath_blocked_reason else ""
        normalized["next_action"] = "escalate_to_human"
        normalized["reason"] = (
            "run_state_guardrail: rollback aftermath truth is not safely closed for automatic continuation"
            f"{reason_tail}"
        )
        normalized["progression_outcome"] = "conservative_escalation"
        normalized["result_acceptance"] = "reject_current_result"
        normalized["progression_rule_id"] = "run_state_guardrail_rollback_aftermath_blocked"
    elif (
        execution_intent_action
        and (
            loop_next_safe_action
            in {
                "require_manual_intervention",
                "require_replanning",
                "stop_terminal_failure",
            }
            or loop_terminal
            or loop_manual_required
            or loop_replan_required
        )
    ) and current_next_action not in {"escalate_to_human", "rollback_required"}:
        reason_tail = f" ({loop_blocked_reason})" if loop_blocked_reason else ""
        normalized["next_action"] = "escalate_to_human"
        normalized["reason"] = (
            f"run_state_guardrail: loop state requires conservative operator gate via {loop_next_safe_action or 'pause'}"
            f"{reason_tail}"
        )
        normalized["progression_outcome"] = "conservative_escalation"
        normalized["result_acceptance"] = "reject_current_result"
        normalized["progression_rule_id"] = "run_state_guardrail_loop_manual_or_blocked"

    normalized["whether_human_required"] = _normalize_text(normalized.get("next_action"), default="") in {
        "escalate_to_human",
        "rollback_required",
    }
    return normalized


def _load_unit_payloads(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw_units = manifest.get("pr_units")
    if not isinstance(raw_units, list) or not raw_units:
        raise ValueError("manifest.pr_units must include at least one unit")

    units: list[dict[str, Any]] = []
    for raw in raw_units:
        if not isinstance(raw, Mapping):
            continue
        pr_id = _normalize_text(raw.get("pr_id"))
        if not pr_id:
            raise ValueError("manifest.pr_units[].pr_id is required")

        receipt_path = Path(_normalize_text(raw.get("receipt_path"), default=""))
        result_path = Path(_normalize_text(raw.get("result_path"), default=""))
        bounded_step_contract_path_text = _normalize_text(raw.get("bounded_step_contract_path"), default="")
        prompt_contract_path_text = _normalize_text(raw.get("pr_implementation_prompt_contract_path"), default="")
        bounded_step_contract_path = (
            Path(bounded_step_contract_path_text) if bounded_step_contract_path_text else None
        )
        prompt_contract_path = Path(prompt_contract_path_text) if prompt_contract_path_text else None
        checkpoint_decision_path = _resolve_checkpoint_decision_path(
            raw_unit=raw,
            result_path=result_path,
        )

        receipt = _read_json_object(receipt_path) if receipt_path.exists() else None
        result = _read_json_object(result_path) if result_path.exists() else None
        bounded_step_contract = (
            _read_json_object_if_exists(bounded_step_contract_path)
            if bounded_step_contract_path is not None
            else None
        )
        prompt_contract = (
            _read_json_object_if_exists(prompt_contract_path)
            if prompt_contract_path is not None
            else None
        )
        checkpoint_decision = (
            _read_json_object_if_exists(checkpoint_decision_path)
            if checkpoint_decision_path is not None
            else None
        )

        units.append(
            {
                "pr_id": pr_id,
                "manifest_status": _normalize_text(raw.get("status"), default=""),
                "compiled_prompt_path": _normalize_text(raw.get("compiled_prompt_path"), default=""),
                "receipt_path": str(receipt_path),
                "result_path": str(result_path),
                "bounded_step_contract_path": str(bounded_step_contract_path) if bounded_step_contract_path else "",
                "pr_implementation_prompt_contract_path": str(prompt_contract_path) if prompt_contract_path else "",
                "checkpoint_decision_path": str(checkpoint_decision_path) if checkpoint_decision_path else "",
                "receipt": receipt,
                "result": result,
                "bounded_step_contract": bounded_step_contract,
                "pr_implementation_prompt_contract": prompt_contract,
                "checkpoint_decision": checkpoint_decision,
            }
        )

    if not any(unit.get("receipt") is not None for unit in units):
        raise ValueError("at least one execution_receipt.json is required")

    return units


def _is_scope_drift(unit: Mapping[str, Any], pr_plan_unit: Mapping[str, Any] | None) -> bool:
    result = unit.get("result")
    if not isinstance(result, Mapping):
        return False

    changed_files = _normalize_string_list(result.get("changed_files"), sort_items=True)
    if not changed_files:
        return False

    planned_files = set(
        _extract_expected_scope_files(unit=unit, pr_plan_unit=pr_plan_unit)
    )
    if not planned_files:
        return False

    return any(path not in planned_files for path in changed_files)


def _is_category_mismatch(unit: Mapping[str, Any], pr_plan_unit: Mapping[str, Any] | None) -> bool:
    expected_tier = _extract_expected_tier_category(unit=unit, pr_plan_unit=pr_plan_unit)
    if not expected_tier:
        return False

    receipt = unit.get("receipt")
    if isinstance(receipt, Mapping):
        actual_receipt_tier = _normalize_text(receipt.get("tier_category"), default="")
        if actual_receipt_tier and actual_receipt_tier != expected_tier:
            return True

    result = unit.get("result")
    if isinstance(result, Mapping):
        actual_result_tier = _normalize_text(result.get("tier_category"), default="")
        if actual_result_tier and actual_result_tier != expected_tier:
            return True

        failure_type = _normalize_text(result.get("failure_type"), default="")
        failure_message = _normalize_text(result.get("failure_message"), default="").lower()
        if failure_type == "category_mismatch":
            return True
        if "category mismatch" in failure_message or "tier mismatch" in failure_message:
            return True

    return False


def _collect_run_signals(
    *,
    manifest: Mapping[str, Any],
    units: list[Mapping[str, Any]],
    pr_plan_index: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    missing_artifacts = 0
    contradictory = 0
    execution_failure = 0
    validation_failure = 0
    missing_signals = 0
    explicit_rollback = 0
    all_completed_and_passed = True
    observed_attempt_count = 0
    scope_drift = 0
    category_mismatch = 0
    refusal_or_conflict = 0
    contract_missing = 0
    contract_identity_conflict = 0
    unbounded_contract = 0
    missing_progression_metadata = 0
    contract_gating_required = any(_uses_contract_sidecars(unit) for unit in units)

    for unit in units:
        pr_id = _normalize_text(unit.get("pr_id"), default="")
        receipt = _as_mapping(unit.get("receipt"))
        result = _as_mapping(unit.get("result"))
        bounded_step_contract = _as_mapping(unit.get("bounded_step_contract"))
        prompt_contract = _as_mapping(unit.get("pr_implementation_prompt_contract"))

        if receipt is None:
            missing_artifacts += 1
        if result is None:
            missing_artifacts += 1
        if contract_gating_required and bounded_step_contract is None:
            contract_missing += 1
        if contract_gating_required and prompt_contract is None:
            contract_missing += 1

        if receipt is not None:
            receipt_pr = _normalize_text(receipt.get("pr_id"), default="")
            if receipt_pr and receipt_pr != pr_id:
                contradictory += 1

        if result is not None:
            result_pr = _normalize_text(result.get("pr_id"), default="")
            if result_pr and result_pr != pr_id:
                contradictory += 1

        if contract_gating_required and _has_contract_identity_mismatch(unit):
            contract_identity_conflict += 1
            all_completed_and_passed = False
        if contract_gating_required and not _has_contract_progression_metadata(unit):
            missing_progression_metadata += 1
            all_completed_and_passed = False
        if contract_gating_required and not _is_bounded_contract_ready(unit):
            unbounded_contract += 1
            all_completed_and_passed = False

        if _is_scope_drift(unit, pr_plan_index.get(pr_id)):
            scope_drift += 1
        if _is_category_mismatch(unit, pr_plan_index.get(pr_id)):
            category_mismatch += 1
        checkpoint_payload = _as_mapping(unit.get("checkpoint_decision"))
        checkpoint_decision = _normalize_text(
            checkpoint_payload.get("decision") if isinstance(checkpoint_payload, Mapping) else "",
            default="",
        )
        if checkpoint_decision == "rollback_evaluation_ready":
            explicit_rollback += 1
            all_completed_and_passed = False
        if _checkpoint_requires_conservative_stop(unit):
            refusal_or_conflict += 1
            all_completed_and_passed = False

        if result is None:
            all_completed_and_passed = False
            continue

        execution = _as_mapping(result.get("execution")) or {}
        execution_status = _normalize_text(execution.get("status"), default="")
        attempt_count = _as_non_negative_int(execution.get("attempt_count"), default=0)
        observed_attempt_count = max(observed_attempt_count, attempt_count)

        verify = _as_mapping(execution.get("verify")) or {}
        verify_status = _normalize_text(verify.get("status"), default="")

        failure_type = _normalize_text(result.get("failure_type"), default="")
        failure_message = _normalize_text(result.get("failure_message"), default="").lower()

        if failure_type == "rollback_required":
            explicit_rollback += 1

        if _has_refusal_or_conflict_surface(
            result=result,
            execution=execution,
            failure_type=failure_type,
            failure_message=failure_message,
        ):
            refusal_or_conflict += 1
            all_completed_and_passed = False

        if execution_status in {"failed", "timed_out"} or failure_type == "execution_failure":
            execution_failure += 1
            all_completed_and_passed = False
        elif execution_status in {"not_started", "running", ""}:
            missing_signals += 1
            all_completed_and_passed = False

        if verify_status == "failed" or failure_type == "evaluation_failure":
            validation_failure += 1
            all_completed_and_passed = False
        elif verify_status in {"not_run", ""}:
            missing_signals += 1
            all_completed_and_passed = False
        elif verify_status != "passed":
            all_completed_and_passed = False

    run_status = _normalize_text(manifest.get("run_status"), default="")
    is_dry_run = bool(manifest.get("dry_run", False)) or run_status.startswith("dry_run")

    return {
        "missing_artifacts": missing_artifacts,
        "contradictory": contradictory,
        "execution_failure": execution_failure,
        "validation_failure": validation_failure,
        "missing_signals": missing_signals,
        "explicit_rollback": explicit_rollback,
        "refusal_or_conflict": refusal_or_conflict,
        "all_completed_and_passed": all_completed_and_passed,
        "observed_attempt_count": observed_attempt_count,
        "scope_drift": scope_drift,
        "category_mismatch": category_mismatch,
        "contract_missing": contract_missing,
        "contract_identity_conflict": contract_identity_conflict,
        "unbounded_contract": unbounded_contract,
        "missing_progression_metadata": missing_progression_metadata,
        "contract_gating_required": contract_gating_required,
        "is_dry_run": is_dry_run,
        "run_status": run_status,
    }


def evaluate_next_action(
    *,
    manifest: Mapping[str, Any],
    units: list[Mapping[str, Any]],
    retry_context: Mapping[str, Any] | None = None,
    policy_snapshot: Mapping[str, Any] | None = None,
    pr_plan: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    pr_plan_payload = _load_pr_plan(pr_plan)
    pr_plan_index = _build_pr_plan_index(pr_plan_payload)

    retry_ctx = normalize_retry_context(retry_context, policy_snapshot=policy_snapshot)
    signals = _collect_run_signals(manifest=manifest, units=units, pr_plan_index=pr_plan_index)

    progression = evaluate_review_progression_outcome(
        signals=signals,
        retry_context=retry_ctx,
    )
    next_action = _normalize_text(progression.get("next_action"), default="")
    reason = _normalize_text(progression.get("reason"), default="")
    if next_action not in ALLOWED_NEXT_ACTIONS:
        raise ValueError(f"unsupported next_action computed: {next_action}")

    updated_retry_context = update_retry_context(
        current=retry_ctx,
        next_action=next_action,
        observed_attempt_count=_as_non_negative_int(signals.get("observed_attempt_count"), default=0),
    )

    whether_human_required = next_action in {
        "escalate_to_human",
        "rollback_required",
    }

    return {
        "next_action": next_action,
        "reason": reason,
        "progression_outcome": _normalize_text(progression.get("outcome"), default=""),
        "result_acceptance": _normalize_text(progression.get("result_acceptance"), default=""),
        "progression_rule_id": _normalize_text(progression.get("rule_id"), default=""),
        "retry_budget_remaining": _as_non_negative_int(
            updated_retry_context.get("retry_budget_remaining"),
            default=0,
        ),
        "whether_human_required": whether_human_required,
        "updated_retry_context": updated_retry_context,
    }


def evaluate_next_action_from_run_dir(
    run_dir: str | Path,
    *,
    retry_context: Mapping[str, Any] | None = None,
    policy_snapshot: Mapping[str, Any] | None = None,
    pr_plan: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(run_dir)
    if not root.exists() or not root.is_dir():
        raise ValueError(f"run artifact directory does not exist: {root}")

    manifest = _load_manifest(root)
    units = _load_unit_payloads(manifest)
    decision = evaluate_next_action(
        manifest=manifest,
        units=units,
        retry_context=retry_context,
        policy_snapshot=policy_snapshot,
        pr_plan=pr_plan,
    )
    run_state_payload = _read_json_object_if_exists(root / "run_state.json")
    if isinstance(run_state_payload, Mapping):
        return _apply_run_state_guardrail(decision=decision, run_state=run_state_payload)
    return decision


def load_json_file_if_present(path_value: str | None) -> dict[str, Any] | None:
    path_text = _normalize_text(path_value, default="")
    if not path_text:
        return None
    path = Path(path_text)
    if not path.exists():
        raise ValueError(f"input file does not exist: {path}")
    return _read_json_object(path)
