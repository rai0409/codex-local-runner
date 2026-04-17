from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from typing import Mapping

from automation.control.retry_context import normalize_retry_context
from automation.control.retry_context import update_retry_context

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


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


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

        receipt = _read_json_object(receipt_path) if receipt_path.exists() else None
        result = _read_json_object(result_path) if result_path.exists() else None

        units.append(
            {
                "pr_id": pr_id,
                "manifest_status": _normalize_text(raw.get("status"), default=""),
                "compiled_prompt_path": _normalize_text(raw.get("compiled_prompt_path"), default=""),
                "receipt_path": str(receipt_path),
                "result_path": str(result_path),
                "receipt": receipt,
                "result": result,
            }
        )

    if not any(unit.get("receipt") is not None for unit in units):
        raise ValueError("at least one execution_receipt.json is required")

    return units


def _is_scope_drift(unit: Mapping[str, Any], pr_plan_unit: Mapping[str, Any] | None) -> bool:
    if not isinstance(pr_plan_unit, Mapping):
        return False
    result = unit.get("result")
    if not isinstance(result, Mapping):
        return False

    changed_files = _normalize_string_list(result.get("changed_files"), sort_items=True)
    if not changed_files:
        return False

    planned_files = set(_normalize_string_list(pr_plan_unit.get("touched_files"), sort_items=True))
    if not planned_files:
        return False

    return any(path not in planned_files for path in changed_files)


def _is_category_mismatch(unit: Mapping[str, Any], pr_plan_unit: Mapping[str, Any] | None) -> bool:
    if not isinstance(pr_plan_unit, Mapping):
        return False

    expected_tier = _normalize_text(pr_plan_unit.get("tier_category"), default="")
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

    for unit in units:
        pr_id = _normalize_text(unit.get("pr_id"), default="")
        receipt = _as_mapping(unit.get("receipt"))
        result = _as_mapping(unit.get("result"))

        if receipt is None:
            missing_artifacts += 1
        if result is None:
            missing_artifacts += 1

        if receipt is not None:
            receipt_pr = _normalize_text(receipt.get("pr_id"), default="")
            if receipt_pr and receipt_pr != pr_id:
                contradictory += 1

        if result is not None:
            result_pr = _normalize_text(result.get("pr_id"), default="")
            if result_pr and result_pr != pr_id:
                contradictory += 1

        if _is_scope_drift(unit, pr_plan_index.get(pr_id)):
            scope_drift += 1
        if _is_category_mismatch(unit, pr_plan_index.get(pr_id)):
            category_mismatch += 1

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

        if failure_type == "rollback_required":
            explicit_rollback += 1

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
        "all_completed_and_passed": all_completed_and_passed,
        "observed_attempt_count": observed_attempt_count,
        "scope_drift": scope_drift,
        "category_mismatch": category_mismatch,
        "is_dry_run": is_dry_run,
        "run_status": run_status,
    }


def _decide_action(signals: Mapping[str, Any], retry_ctx: Mapping[str, Any]) -> tuple[str, str]:
    budget = _as_non_negative_int(retry_ctx.get("retry_budget_remaining"), default=0)
    prior_retry_class = _normalize_text(retry_ctx.get("prior_retry_class"), default="")
    missing_signal_count = _as_non_negative_int(retry_ctx.get("missing_signal_count"), default=0)

    if _as_non_negative_int(signals.get("category_mismatch"), default=0) > 0:
        return "roadmap_replan", "tier/category mismatch detected against pr_plan intent"

    if _as_non_negative_int(signals.get("scope_drift"), default=0) > 0:
        return "prompt_recompile", "scope drift detected against pr_plan touched_files"

    if _as_non_negative_int(signals.get("explicit_rollback"), default=0) > 0:
        return "rollback_required", "explicit rollback requirement signaled by normalized result"

    if _as_non_negative_int(signals.get("contradictory"), default=0) > 0:
        return "escalate_to_human", "contradictory artifact identities detected"

    if _as_non_negative_int(signals.get("validation_failure"), default=0) > 0:
        if budget <= 0:
            return "escalate_to_human", "validation failure with exhausted retry budget"
        if prior_retry_class == "repair_prompt_retry":
            return "escalate_to_human", "repair_prompt_retry already attempted and failed"
        return "repair_prompt_retry", "validation/test failure after execution completion"

    if _as_non_negative_int(signals.get("execution_failure"), default=0) > 0:
        if budget <= 0:
            return "escalate_to_human", "execution failure with exhausted retry budget"
        if prior_retry_class == "same_prompt_retry":
            return "escalate_to_human", "same_prompt_retry already attempted and failed"
        return "same_prompt_retry", "explicit execution/tool failure with valid planned scope"

    missing_total = _as_non_negative_int(signals.get("missing_artifacts"), default=0) + _as_non_negative_int(
        signals.get("missing_signals"),
        default=0,
    )
    if missing_total > 0:
        if missing_signal_count >= 2:
            return "escalate_to_human", "missing or incomplete execution signals observed repeatedly"
        return "signal_recollect", "missing or incomplete artifacts/signals require recollection"

    if bool(signals.get("all_completed_and_passed", False)) and not bool(signals.get("is_dry_run", False)):
        return "proceed_to_pr", "all units completed with passing verification signals"

    if bool(signals.get("is_dry_run", False)) and _normalize_text(signals.get("run_status"), default="") == "dry_run_completed":
        return "signal_recollect", "dry_run_completed does not imply execution success"

    return "escalate_to_human", "unable to derive a safe deterministic automated next action"


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

    next_action, reason = _decide_action(signals, retry_ctx)
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
    return evaluate_next_action(
        manifest=manifest,
        units=units,
        retry_context=retry_context,
        policy_snapshot=policy_snapshot,
        pr_plan=pr_plan,
    )


def load_json_file_if_present(path_value: str | None) -> dict[str, Any] | None:
    path_text = _normalize_text(path_value, default="")
    if not path_text:
        return None
    path = Path(path_text)
    if not path.exists():
        raise ValueError(f"input file does not exist: {path}")
    return _read_json_object(path)
