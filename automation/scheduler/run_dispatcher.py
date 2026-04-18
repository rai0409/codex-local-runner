from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
import json
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Mapping

from automation.control.retry_decision import DECISION_ESCALATE_TO_HUMAN
from automation.control.retry_decision import DECISION_PAUSE_AND_WAIT
from automation.control.retry_decision import DECISION_RETRY_NOW
from automation.control.retry_decision import DECISION_TERMINAL_REFUSAL
from automation.control.retry_decision import evaluate_retry_decision
from automation.control.retry_context_store import FileRetryContextStore
from automation.control.execution_authority import normalize_requested_lane_input
from automation.control.execution_authority import resolve_action_routing
from automation.control.execution_authority import LANE_DETERMINISTIC_PYTHON
from automation.control.execution_authority import LANE_GITHUB_DETERMINISTIC
from automation.control.execution_authority import LANE_LLM_BACKED
from automation.control.execution_authority import ROUTING_CLASS_CONTROL
from automation.control.execution_authority import ROUTING_CLASS_EXECUTOR
from automation.control.execution_authority import ROUTING_CLASS_RETRY
from automation.observability.run_audit import RunAuditLogger
from automation.scheduler.pause_state import build_pause_payload
from automation.scheduler.pause_state import classify_pause_condition
from automation.scheduler.pause_state import is_pause_active
from automation.scheduler.pause_state import is_pause_resume_eligible
from automation.scheduler.pause_state import load_pause_payload
from automation.scheduler.pause_state import mark_pause_resumed
from automation.scheduler.pause_state import persist_pause_payload

def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


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


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return False


def _as_mapping(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


_EXECUTOR_RECEIPT_FILENAMES = (
    "pr_creation_receipt.json",
    "pr_update_receipt.json",
    "merge_receipt.json",
    "rollback_receipt.json",
)

_EXECUTOR_ACTION_TOKENS = {
    "proceed_to_pr",
    "github.pr.update",
    "proceed_to_merge",
    "rollback_required",
}

_DETERMINISTIC_WRITE_RESULT_STATUSES = {"already_applied", "no_op"}

_DETERMINISTIC_REFUSAL_PREFIXES = (
    "idempotency_",
    "write_authority_blocked",
    "write_action_not_allowed",
    "write_category_not_allowed",
    "merge_pr_number_missing_or_invalid",
    "update_pr_number_missing_or_invalid",
    "pr_update_missing_or_invalid",
    "rollback_target_missing_or_ambiguous",
    "unsupported_action",
)


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def _extract_run_id_from_manifest(manifest: Mapping[str, Any]) -> str | None:
    units = manifest.get("pr_units")
    if not isinstance(units, list):
        return None
    for unit in units:
        if not isinstance(unit, Mapping):
            continue
        receipt_path_text = _normalize_text(unit.get("receipt_path"), default="")
        if not receipt_path_text:
            continue
        receipt_path = Path(receipt_path_text)
        if not receipt_path.exists():
            continue
        try:
            receipt = _read_json_object(receipt_path)
        except Exception:
            continue
        run_id = _normalize_text(receipt.get("run_id"), default="")
        if run_id:
            return run_id
    return None


def _routing_cache_key(
    *,
    action: str,
    policy_snapshot: Mapping[str, Any] | None,
    handoff_payload: Mapping[str, Any] | None,
) -> tuple[str, str, str]:
    normalized = normalize_requested_lane_input(
        action,
        policy_snapshot=policy_snapshot,
        handoff_payload=handoff_payload,
    )
    fingerprint = _normalize_text(normalized.get("routing_input_fingerprint"), default="_") or "_"
    return (
        _normalize_text(action, default=""),
        fingerprint,
        "",
    )


def _load_terminal_executor_receipt_candidates(run_root: Path) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for filename in _EXECUTOR_RECEIPT_FILENAMES:
        path = run_root / filename
        if not path.exists():
            continue
        try:
            payload = _read_json_object(path)
        except Exception:
            continue
        requested_action = _normalize_text(payload.get("requested_action"), default="")
        if requested_action not in _EXECUTOR_ACTION_TOKENS:
            continue
        succeeded = _as_bool(payload.get("succeeded"))
        refusal_reason = _normalize_text(payload.get("refusal_reason"), default="")
        idempotency = payload.get("write_idempotency")
        idempotency_payload = idempotency if isinstance(idempotency, Mapping) else {}
        dedupe_status = _normalize_text(idempotency_payload.get("dedupe_status"), default="")
        evidence = payload.get("evidence_used_summary")
        evidence_payload = evidence if isinstance(evidence, Mapping) else {}
        write_result = evidence_payload.get("write_result")
        write_result_payload = write_result if isinstance(write_result, Mapping) else {}
        write_result_status = _normalize_text(write_result_payload.get("status"), default="")
        terminal_reason = ""
        dispatch_status = ""
        human_required = _as_bool(payload.get("whether_human_required"))
        if succeeded and (
            write_result_status in _DETERMINISTIC_WRITE_RESULT_STATUSES
            or dedupe_status == "already_applied"
        ):
            dispatch_status = "executed"
            terminal_reason = (
                f"short_circuit_existing_terminal_write_result:{requested_action}:{write_result_status or dedupe_status}"
            )
        elif not succeeded and refusal_reason and any(
            refusal_reason.startswith(prefix) for prefix in _DETERMINISTIC_REFUSAL_PREFIXES
        ):
            dispatch_status = "escalated"
            terminal_reason = f"short_circuit_existing_terminal_refusal:{requested_action}:{refusal_reason}"
            human_required = True

        if not dispatch_status or not terminal_reason:
            continue
        candidates.append(
            {
                "dispatch_status": dispatch_status,
                "routing_reason": terminal_reason,
                "whether_human_required": human_required,
                "executed_at": _normalize_text(payload.get("executed_at"), default=""),
                "receipt_path": str(path),
                "requested_action": requested_action,
            }
        )
    return candidates


def _select_retry_short_circuit_candidate(run_root: Path) -> dict[str, Any] | None:
    candidates = _load_terminal_executor_receipt_candidates(run_root)
    if not candidates:
        return None
    ordered = sorted(
        candidates,
        key=lambda item: (
            _normalize_text(item.get("executed_at"), default=""),
            _normalize_text(item.get("requested_action"), default=""),
            _normalize_text(item.get("receipt_path"), default=""),
        ),
    )
    return dict(ordered[-1])


def _resolve_retry_details(
    handoff_payload: Mapping[str, Any],
) -> tuple[str | None, int | None, int | None, int | None]:
    retry_ctx = handoff_payload.get("updated_retry_context")
    retry_context = retry_ctx if isinstance(retry_ctx, Mapping) else {}
    retry_class = _normalize_text(retry_context.get("prior_retry_class"), default="") or None
    retry_budget = _as_optional_int(
        handoff_payload.get("retry_budget_remaining")
        if handoff_payload.get("retry_budget_remaining") is not None
        else retry_context.get("retry_budget_remaining")
    )
    missing_signal_count = _as_optional_int(retry_context.get("missing_signal_count"))
    prior_attempt_count = _as_optional_int(retry_context.get("prior_attempt_count"))
    return retry_class, retry_budget, missing_signal_count, prior_attempt_count


def _merge_retry_signals(
    *,
    handoff_payload: Mapping[str, Any],
    persisted_retry_context: Mapping[str, Any] | None,
) -> tuple[str | None, int | None, int | None, int | None]:
    retry_class, retry_budget, missing_signal_count, prior_attempt_count = _resolve_retry_details(
        handoff_payload
    )
    persisted = persisted_retry_context if isinstance(persisted_retry_context, Mapping) else {}
    persisted_class = _normalize_text(persisted.get("prior_retry_class"), default="") or None
    persisted_budget = _as_optional_int(persisted.get("retry_budget_remaining"))
    persisted_missing_count = _as_optional_int(persisted.get("missing_signal_count"))
    persisted_attempt_count = _as_optional_int(persisted.get("prior_attempt_count"))
    resolved_class = retry_class or persisted_class
    if retry_budget is None:
        resolved_budget = persisted_budget
    elif persisted_budget is None:
        resolved_budget = retry_budget
    else:
        resolved_budget = min(retry_budget, persisted_budget)
    if missing_signal_count is None:
        resolved_missing = persisted_missing_count
    elif persisted_missing_count is None:
        resolved_missing = missing_signal_count
    else:
        resolved_missing = max(missing_signal_count, persisted_missing_count)
    if prior_attempt_count is None:
        resolved_attempt_count = persisted_attempt_count
    elif persisted_attempt_count is None:
        resolved_attempt_count = prior_attempt_count
    else:
        resolved_attempt_count = max(prior_attempt_count, persisted_attempt_count)
    return resolved_class, resolved_budget, resolved_missing, resolved_attempt_count


@dataclass
class DispatchRequest:
    artifacts_input_dir: str | Path
    output_dir: str | Path
    job_id: str | None = None
    dry_run: bool = True
    stop_on_failure: bool = True
    max_retry_dispatches: int = 1
    repository: str | None = None
    head_branch: str | None = None
    base_branch: str | None = None
    category: str | None = None
    write_authority: Mapping[str, Any] | None = None
    policy_snapshot: Mapping[str, Any] | None = None
    pr_number: int | None = None
    pr_update: Mapping[str, Any] | None = None
    expected_head_sha: str | None = None
    rollback_target: Mapping[str, Any] | None = None
    github_read_evidence: Mapping[str, Any] | None = None


@dataclass
class RunDispatcher:
    runner: Any
    action_executor: Any
    audit_logger: RunAuditLogger = field(default_factory=RunAuditLogger)
    now: Callable[[], datetime] = datetime.now

    def _record_audit(
        self,
        *,
        run_root: Path,
        job_id: str,
        scheduler_action_taken: str,
        execution_attempted: bool,
        retry_attempted: bool,
        routed_action: str | None,
        routing_reason: str,
        retry_class: str | None,
        retry_budget_remaining: int | None,
        whether_human_required: bool,
        outcome_status: str,
        run_id: str | None = None,
        pause_state: str | None = None,
        pause_reason: str | None = None,
        next_eligible_at: str | None = None,
    ) -> dict[str, Any]:
        return self.audit_logger.append(
            run_root,
            {
                "job_id": job_id,
                "run_id": run_id,
                "scheduler_action_taken": scheduler_action_taken,
                "execution_attempted": execution_attempted,
                "retry_attempted": retry_attempted,
                "routed_action": routed_action,
                "routing_reason": routing_reason,
                "retry_class": retry_class,
                "retry_budget_remaining": retry_budget_remaining,
                "whether_human_required": whether_human_required,
                "outcome_status": outcome_status,
                "pause_state": pause_state,
                "pause_reason": pause_reason,
                "next_eligible_at": next_eligible_at,
            },
        )

    def _load_run_decision_artifacts(self, run_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
        next_action_path = run_root / "next_action.json"
        handoff_path = run_root / "action_handoff.json"
        if not next_action_path.exists():
            raise ValueError(f"missing next_action.json: {next_action_path}")
        if not handoff_path.exists():
            raise ValueError(f"missing action_handoff.json: {handoff_path}")
        return _read_json_object(next_action_path), _read_json_object(handoff_path)

    def _retry_allowed(
        self,
        *,
        action: str,
        handoff_payload: Mapping[str, Any],
        retries_performed: int,
        max_retry_dispatches: int,
    ) -> tuple[bool, str]:
        _, retry_budget_remaining, missing_signal_count, _ = _resolve_retry_details(handoff_payload)
        if retries_performed >= max_retry_dispatches:
            return False, "dispatch_retry_cycle_exhausted"
        if action in {"same_prompt_retry", "repair_prompt_retry"} and retries_performed >= 1:
            return False, "retry_class_exhausted"
        if retry_budget_remaining is not None and retry_budget_remaining < 0:
            return False, "retry_budget_invalid"
        if action == "signal_recollect" and (missing_signal_count or 0) >= 2:
            return False, "missing_signal_repeated"
        return True, "retry_allowed"

    def _preserved_inputs_summary(self, request: DispatchRequest) -> dict[str, Any]:
        rollback_target = request.rollback_target if isinstance(request.rollback_target, Mapping) else {}
        pr_update = request.pr_update if isinstance(request.pr_update, Mapping) else {}
        return {
            "artifacts_input_dir": str(request.artifacts_input_dir),
            "output_dir": str(request.output_dir),
            "dry_run": bool(request.dry_run),
            "stop_on_failure": bool(request.stop_on_failure),
            "max_retry_dispatches": max(0, _as_non_negative_int(request.max_retry_dispatches, default=0)),
            "repository": _normalize_text(request.repository, default="") or None,
            "head_branch": _normalize_text(request.head_branch, default="") or None,
            "base_branch": _normalize_text(request.base_branch, default="") or None,
            "category": _normalize_text(request.category, default="") or None,
            "has_write_authority": isinstance(request.write_authority, Mapping),
            "has_policy_snapshot": isinstance(request.policy_snapshot, Mapping),
            "pr_number": _as_optional_int(request.pr_number),
            "pr_update_keys": sorted([key for key in ("title", "body", "base_branch") if key in pr_update]),
            "rollback_target_keys": sorted(
                [
                    key
                    for key in rollback_target.keys()
                    if _normalize_text(rollback_target.get(key), default="")
                ]
            ),
        }

    def _handle_existing_pause_if_any(
        self,
        *,
        run_root: Path,
        job_id: str,
    ) -> dict[str, Any] | None:
        existing_pause = load_pause_payload(run_root)
        if not is_pause_active(existing_pause):
            return None
        pause_payload = existing_pause if isinstance(existing_pause, Mapping) else {}
        pause_state = _normalize_text(pause_payload.get("pause_state"), default="paused_other_bounded")
        pause_reason = _normalize_text(pause_payload.get("pause_reason"), default="pause_active")
        next_eligible_at = _normalize_text(pause_payload.get("next_eligible_at"), default="") or None
        if not is_pause_resume_eligible(pause_payload, now=self.now):
            audit = self._record_audit(
                run_root=run_root,
                job_id=job_id,
                scheduler_action_taken="pause_skip",
                execution_attempted=False,
                retry_attempted=False,
                routed_action=None,
                routing_reason="paused_not_eligible",
                retry_class=None,
                retry_budget_remaining=None,
                whether_human_required=_as_bool(pause_payload.get("whether_human_required")),
                outcome_status="paused",
                run_id=_normalize_text(pause_payload.get("run_id"), default="") or None,
                pause_state=pause_state,
                pause_reason=pause_reason,
                next_eligible_at=next_eligible_at,
            )
            return {
                "job_id": job_id,
                "dispatch_status": "paused",
                "manifests": [],
                "audit": audit,
                "pause_state": dict(pause_payload),
            }

        resumed_payload = mark_pause_resumed(
            run_root,
            now=self.now,
            resume_reason="pause_eligible_for_resume",
        ) or dict(pause_payload)
        self._record_audit(
            run_root=run_root,
            job_id=job_id,
            scheduler_action_taken="resume",
            execution_attempted=False,
            retry_attempted=False,
            routed_action=None,
            routing_reason="pause_eligible_for_resume",
            retry_class=None,
            retry_budget_remaining=None,
            whether_human_required=_as_bool(resumed_payload.get("whether_human_required")),
            outcome_status="resumed",
            run_id=_normalize_text(resumed_payload.get("run_id"), default="") or None,
            pause_state=_normalize_text(resumed_payload.get("pause_state"), default="") or None,
            pause_reason=_normalize_text(resumed_payload.get("pause_reason"), default="") or None,
            next_eligible_at=_normalize_text(resumed_payload.get("next_eligible_at"), default="") or None,
        )
        return None

    def dispatch_once(self, request: DispatchRequest) -> dict[str, Any]:
        output_root = Path(request.output_dir)
        retries_performed = 0
        manifests: list[dict[str, Any]] = []
        last_audit: dict[str, Any] | None = None
        routing_cache: dict[tuple[str, str, str], dict[str, Any]] = {}

        retry_store = FileRetryContextStore(output_root / "retry_context_store.json")
        requested_job_id = _normalize_text(request.job_id, default="")
        if requested_job_id:
            pre_run_root = output_root / requested_job_id
            pause_gate_result = self._handle_existing_pause_if_any(
                run_root=pre_run_root,
                job_id=requested_job_id,
            )
            if pause_gate_result is not None:
                return pause_gate_result

        while True:
            manifest = self.runner.run(
                artifacts_input_dir=request.artifacts_input_dir,
                output_dir=request.output_dir,
                job_id=request.job_id,
                dry_run=request.dry_run,
                stop_on_failure=request.stop_on_failure,
                retry_context=None,
                policy_snapshot=request.policy_snapshot,
                github_read_evidence=request.github_read_evidence,
            )
            manifests.append(manifest)
            job_id = _normalize_text(manifest.get("job_id"), default="")
            run_root = output_root / job_id

            try:
                next_action_payload, handoff_payload = self._load_run_decision_artifacts(run_root)
            except Exception as exc:
                last_audit = self._record_audit(
                    run_root=run_root,
                    job_id=job_id,
                    scheduler_action_taken="escalate",
                    execution_attempted=False,
                    retry_attempted=False,
                    routed_action=None,
                    routing_reason=f"decision_artifacts_missing:{_normalize_text(exc, default='error')}",
                    retry_class=None,
                    retry_budget_remaining=None,
                    whether_human_required=True,
                    outcome_status="escalated",
                )
                return {
                    "job_id": job_id,
                    "dispatch_status": "escalated",
                    "manifests": manifests,
                    "audit": last_audit,
                }

            next_action = _normalize_text(next_action_payload.get("next_action"), default="")
            handoff_action = _normalize_text(handoff_payload.get("next_action"), default="")
            action_consumable = _as_bool(handoff_payload.get("action_consumable"))
            whether_human_required = _as_bool(handoff_payload.get("whether_human_required"))
            persisted_retry_record = retry_store.get_record(job_id)
            persisted_retry_context = (
                persisted_retry_record.get("retry_context")
                if isinstance(persisted_retry_record, Mapping)
                and isinstance(persisted_retry_record.get("retry_context"), Mapping)
                else None
            )
            retry_class, retry_budget_remaining, missing_signal_count, prior_attempt_count = _merge_retry_signals(
                handoff_payload=handoff_payload,
                persisted_retry_context=persisted_retry_context,
            )

            if next_action and handoff_action and next_action != handoff_action:
                last_audit = self._record_audit(
                    run_root=run_root,
                    job_id=job_id,
                    scheduler_action_taken="escalate",
                    execution_attempted=False,
                    retry_attempted=False,
                    routed_action=None,
                    routing_reason="next_action_handoff_mismatch",
                    retry_class=retry_class,
                    retry_budget_remaining=retry_budget_remaining,
                    whether_human_required=True,
                    outcome_status="escalated",
                )
                return {
                    "job_id": job_id,
                    "dispatch_status": "escalated",
                    "manifests": manifests,
                    "audit": last_audit,
                }

            action = handoff_action or next_action
            if not action:
                last_audit = self._record_audit(
                    run_root=run_root,
                    job_id=job_id,
                    scheduler_action_taken="escalate",
                    execution_attempted=False,
                    retry_attempted=False,
                    routed_action=None,
                    routing_reason="missing_next_action",
                    retry_class=retry_class,
                    retry_budget_remaining=retry_budget_remaining,
                    whether_human_required=True,
                    outcome_status="escalated",
                )
                return {
                    "job_id": job_id,
                    "dispatch_status": "escalated",
                    "manifests": manifests,
                    "audit": last_audit,
                }

            routing_key = _routing_cache_key(
                action=action,
                policy_snapshot=request.policy_snapshot if isinstance(request.policy_snapshot, Mapping) else None,
                handoff_payload=handoff_payload,
            )
            if routing_key in routing_cache:
                routing_selection = dict(routing_cache[routing_key])
            else:
                routing_selection = resolve_action_routing(
                    action,
                    policy_snapshot=request.policy_snapshot,
                    handoff_payload=handoff_payload,
                )
                routing_cache[routing_key] = dict(routing_selection)
            if not bool(routing_selection.get("known_action")):
                last_audit = self._record_audit(
                    run_root=run_root,
                    job_id=job_id,
                    scheduler_action_taken="escalate",
                    execution_attempted=False,
                    retry_attempted=False,
                    routed_action=action,
                    routing_reason="authority_action_unclassified",
                    retry_class=retry_class,
                    retry_budget_remaining=retry_budget_remaining,
                    whether_human_required=True,
                    outcome_status="escalated",
                )
                return {
                    "job_id": job_id,
                    "dispatch_status": "escalated",
                    "manifests": manifests,
                    "audit": last_audit,
                }
            if not bool(routing_selection.get("allowed")):
                reason = _normalize_text(routing_selection.get("reason"), default="lane_not_allowed")
                last_audit = self._record_audit(
                    run_root=run_root,
                    job_id=job_id,
                    scheduler_action_taken="escalate",
                    execution_attempted=False,
                    retry_attempted=False,
                    routed_action=action,
                    routing_reason=f"authority_{reason}",
                    retry_class=retry_class,
                    retry_budget_remaining=retry_budget_remaining,
                    whether_human_required=True,
                    outcome_status="escalated",
                )
                return {
                    "job_id": job_id,
                    "dispatch_status": "escalated",
                    "manifests": manifests,
                    "audit": last_audit,
                }
            resolved_lane = _normalize_text(routing_selection.get("resolved_lane"), default="")
            routing_class = _normalize_text(routing_selection.get("routing_class"), default="")
            if routing_class == ROUTING_CLASS_EXECUTOR and resolved_lane != LANE_GITHUB_DETERMINISTIC:
                last_audit = self._record_audit(
                    run_root=run_root,
                    job_id=job_id,
                    scheduler_action_taken="escalate",
                    execution_attempted=False,
                    retry_attempted=False,
                    routed_action=action,
                    routing_reason="authority_routing_mismatch:executor_requires_github_deterministic",
                    retry_class=retry_class,
                    retry_budget_remaining=retry_budget_remaining,
                    whether_human_required=True,
                    outcome_status="escalated",
                )
                return {
                    "job_id": job_id,
                    "dispatch_status": "escalated",
                    "manifests": manifests,
                    "audit": last_audit,
                }
            if routing_class == ROUTING_CLASS_RETRY and resolved_lane not in {
                LANE_LLM_BACKED,
                LANE_DETERMINISTIC_PYTHON,
            }:
                last_audit = self._record_audit(
                    run_root=run_root,
                    job_id=job_id,
                    scheduler_action_taken="escalate",
                    execution_attempted=False,
                    retry_attempted=False,
                    routed_action=action,
                    routing_reason="authority_routing_mismatch:retry_dispatch_disallows_github_lane",
                    retry_class=retry_class,
                    retry_budget_remaining=retry_budget_remaining,
                    whether_human_required=True,
                    outcome_status="escalated",
                )
                return {
                    "job_id": job_id,
                    "dispatch_status": "escalated",
                    "manifests": manifests,
                    "audit": last_audit,
                }
            if routing_class == ROUTING_CLASS_CONTROL and resolved_lane != LANE_DETERMINISTIC_PYTHON:
                last_audit = self._record_audit(
                    run_root=run_root,
                    job_id=job_id,
                    scheduler_action_taken="escalate",
                    execution_attempted=False,
                    retry_attempted=False,
                    routed_action=action,
                    routing_reason="authority_routing_mismatch:control_requires_deterministic_python",
                    retry_class=retry_class,
                    retry_budget_remaining=retry_budget_remaining,
                    whether_human_required=True,
                    outcome_status="escalated",
                )
                return {
                    "job_id": job_id,
                    "dispatch_status": "escalated",
                    "manifests": manifests,
                    "audit": last_audit,
                }
            if routing_class not in {ROUTING_CLASS_RETRY, ROUTING_CLASS_EXECUTOR, ROUTING_CLASS_CONTROL}:
                last_audit = self._record_audit(
                    run_root=run_root,
                    job_id=job_id,
                    scheduler_action_taken="escalate",
                    execution_attempted=False,
                    retry_attempted=False,
                    routed_action=action,
                    routing_reason="authority_routing_class_unresolved",
                    retry_class=retry_class,
                    retry_budget_remaining=retry_budget_remaining,
                    whether_human_required=True,
                    outcome_status="escalated",
                )
                return {
                    "job_id": job_id,
                    "dispatch_status": "escalated",
                    "manifests": manifests,
                    "audit": last_audit,
                }

            if routing_class == ROUTING_CLASS_RETRY:
                short_circuit = _select_retry_short_circuit_candidate(run_root)
                if isinstance(short_circuit, Mapping):
                    resolved_dispatch_status = _normalize_text(
                        short_circuit.get("dispatch_status"),
                        default="escalated",
                    )
                    if resolved_dispatch_status not in {"executed", "escalated"}:
                        resolved_dispatch_status = "escalated"
                    last_audit = self._record_audit(
                        run_root=run_root,
                        job_id=job_id,
                        scheduler_action_taken="short_circuit",
                        execution_attempted=False,
                        retry_attempted=False,
                        routed_action=action,
                        routing_reason=_normalize_text(
                            short_circuit.get("routing_reason"),
                            default="short_circuit_terminal_result",
                        ),
                        retry_class=retry_class,
                        retry_budget_remaining=retry_budget_remaining,
                        whether_human_required=_as_bool(short_circuit.get("whether_human_required")),
                        outcome_status=resolved_dispatch_status,
                    )
                    return {
                        "job_id": job_id,
                        "dispatch_status": resolved_dispatch_status,
                        "manifests": manifests,
                        "audit": last_audit,
                        "short_circuit": dict(short_circuit),
                    }

            pause_match = classify_pause_condition(
                next_action=action,
                reason=_normalize_text(
                    handoff_payload.get("reason"),
                    default=_normalize_text(next_action_payload.get("reason"), default=""),
                ),
                whether_human_required=whether_human_required,
                handoff_payload=handoff_payload,
                decision_payload=next_action_payload,
                now=self.now,
            )
            if isinstance(pause_match, Mapping):
                existing_pause = load_pause_payload(run_root)
                pause_payload = build_pause_payload(
                    job_id=job_id,
                    run_id=_extract_run_id_from_manifest(manifest),
                    pause_state=_normalize_text(pause_match.get("pause_state"), default="paused_other_bounded"),
                    pause_reason=_normalize_text(pause_match.get("pause_reason"), default="pause_condition_detected"),
                    provider_name=_normalize_text(pause_match.get("provider_name"), default="") or None,
                    retry_after_seconds=_as_optional_int(pause_match.get("retry_after_seconds")),
                    next_eligible_at=_normalize_text(pause_match.get("next_eligible_at"), default="") or None,
                    resume_from_stage="planned_execution_dispatch",
                    whether_human_required=_as_bool(pause_match.get("whether_human_required")),
                    preserved_inputs_summary=self._preserved_inputs_summary(request),
                    previous_pause_payload=existing_pause,
                    now=self.now,
                )
                persisted_pause = persist_pause_payload(run_root, pause_payload)
                last_audit = self._record_audit(
                    run_root=run_root,
                    job_id=job_id,
                    scheduler_action_taken="pause",
                    execution_attempted=False,
                    retry_attempted=False,
                    routed_action=action,
                    routing_reason=_normalize_text(
                        persisted_pause.get("pause_reason"),
                        default="pause_condition_detected",
                    ),
                    retry_class=retry_class,
                    retry_budget_remaining=retry_budget_remaining,
                    whether_human_required=_as_bool(persisted_pause.get("whether_human_required")),
                    outcome_status="paused",
                    run_id=_normalize_text(persisted_pause.get("run_id"), default="") or None,
                    pause_state=_normalize_text(persisted_pause.get("pause_state"), default="") or None,
                    pause_reason=_normalize_text(persisted_pause.get("pause_reason"), default="") or None,
                    next_eligible_at=_normalize_text(persisted_pause.get("next_eligible_at"), default="") or None,
                )
                return {
                    "job_id": job_id,
                    "dispatch_status": "paused",
                    "manifests": manifests,
                    "audit": last_audit,
                    "pause_state": persisted_pause,
                }

            if routing_class == ROUTING_CLASS_RETRY:
                retry_policy_override = None
                policy_snapshot = request.policy_snapshot if isinstance(request.policy_snapshot, Mapping) else {}
                if isinstance(policy_snapshot.get("retry_policy"), Mapping):
                    retry_policy_override = policy_snapshot.get("retry_policy")
                failure_type = _normalize_text(
                    handoff_payload.get("failure_type"),
                    default=_normalize_text(next_action_payload.get("failure_type"), default=""),
                )
                retry_after_seconds = _as_optional_int(
                    handoff_payload.get("retry_after_seconds")
                    if handoff_payload.get("retry_after_seconds") is not None
                    else next_action_payload.get("retry_after_seconds")
                )
                decision_context = {
                    "prior_attempt_count": _as_non_negative_int(prior_attempt_count, default=0),
                    "prior_retry_class": retry_class,
                    "missing_signal_count": _as_non_negative_int(missing_signal_count, default=0),
                    "retry_budget_remaining": _as_non_negative_int(retry_budget_remaining, default=0),
                }
                retry_decision = evaluate_retry_decision(
                    provider_name=_normalize_text(
                        handoff_payload.get("provider_name"),
                        default=_normalize_text(next_action_payload.get("provider_name"), default=""),
                    )
                    or None,
                    operation_class="read_check" if action == "wait_for_checks" else "execution",
                    failure_type=failure_type or None,
                    retry_class=action,
                    retry_context=decision_context,
                    pause_state_payload=load_pause_payload(run_root),
                    retry_after_seconds=retry_after_seconds,
                    whether_human_required=whether_human_required,
                    next_action=action,
                    reason=_normalize_text(
                        handoff_payload.get("reason"),
                        default=_normalize_text(next_action_payload.get("reason"), default=""),
                    ),
                    structured_result=None,
                    policy=retry_policy_override,
                    enforce_exhaustion_as_escalation=False,
                    now=self.now,
                )
                decision_kind = _normalize_text(retry_decision.get("decision_kind"), default="")
                if decision_kind == DECISION_PAUSE_AND_WAIT:
                    existing_pause = load_pause_payload(run_root)
                    pause_payload = build_pause_payload(
                        job_id=job_id,
                        run_id=_extract_run_id_from_manifest(manifest),
                        pause_state=_normalize_text(
                            retry_decision.get("pause_state"),
                            default="paused_other_bounded",
                        ),
                        pause_reason=_normalize_text(
                            retry_decision.get("reason"),
                            default="pause_and_wait policy decision",
                        ),
                        provider_name=_normalize_text(retry_decision.get("provider_class"), default="") or None,
                        retry_after_seconds=_as_optional_int(retry_decision.get("pause_retry_after_seconds")),
                        next_eligible_at=_normalize_text(retry_decision.get("next_eligible_at"), default="") or None,
                        resume_from_stage="planned_execution_dispatch",
                        whether_human_required=_as_bool(retry_decision.get("whether_human_required")),
                        preserved_inputs_summary=self._preserved_inputs_summary(request),
                        previous_pause_payload=existing_pause,
                        now=self.now,
                    )
                    persisted_pause = persist_pause_payload(run_root, pause_payload)
                    last_audit = self._record_audit(
                        run_root=run_root,
                        job_id=job_id,
                        scheduler_action_taken="pause",
                        execution_attempted=False,
                        retry_attempted=False,
                        routed_action=action,
                        routing_reason=_normalize_text(
                            persisted_pause.get("pause_reason"),
                            default="pause_and_wait policy decision",
                        ),
                        retry_class=retry_class,
                        retry_budget_remaining=retry_budget_remaining,
                        whether_human_required=_as_bool(persisted_pause.get("whether_human_required")),
                        outcome_status="paused",
                        run_id=_normalize_text(persisted_pause.get("run_id"), default="") or None,
                        pause_state=_normalize_text(persisted_pause.get("pause_state"), default="") or None,
                        pause_reason=_normalize_text(persisted_pause.get("pause_reason"), default="") or None,
                        next_eligible_at=_normalize_text(persisted_pause.get("next_eligible_at"), default="") or None,
                    )
                    return {
                        "job_id": job_id,
                        "dispatch_status": "paused",
                        "manifests": manifests,
                        "audit": last_audit,
                        "pause_state": persisted_pause,
                    }
                if decision_kind in {DECISION_TERMINAL_REFUSAL, DECISION_ESCALATE_TO_HUMAN}:
                    last_audit = self._record_audit(
                        run_root=run_root,
                        job_id=job_id,
                        scheduler_action_taken="escalate",
                        execution_attempted=False,
                        retry_attempted=False,
                        routed_action=action,
                        routing_reason=_normalize_text(
                            retry_decision.get("reason"),
                            default="retry policy refused retry progression",
                        ),
                        retry_class=retry_class,
                        retry_budget_remaining=retry_budget_remaining,
                        whether_human_required=True,
                        outcome_status="escalated",
                    )
                    return {
                        "job_id": job_id,
                        "dispatch_status": "escalated",
                        "manifests": manifests,
                        "audit": last_audit,
                    }
                if decision_kind != DECISION_RETRY_NOW:
                    last_audit = self._record_audit(
                        run_root=run_root,
                        job_id=job_id,
                        scheduler_action_taken="escalate",
                        execution_attempted=False,
                        retry_attempted=False,
                        routed_action=action,
                        routing_reason="retry_decision_kind_unrecognized",
                        retry_class=retry_class,
                        retry_budget_remaining=retry_budget_remaining,
                        whether_human_required=True,
                        outcome_status="escalated",
                    )
                    return {
                        "job_id": job_id,
                        "dispatch_status": "escalated",
                        "manifests": manifests,
                        "audit": last_audit,
                    }

                retry_allowed, reason = self._retry_allowed(
                    action=action,
                    handoff_payload=handoff_payload,
                    retries_performed=retries_performed,
                    max_retry_dispatches=max(0, int(request.max_retry_dispatches)),
                )
                if (
                    action in {"same_prompt_retry", "repair_prompt_retry"}
                    and retry_class == action
                    and (prior_attempt_count or 0) >= 1
                ):
                    retry_allowed = False
                    reason = "retry_class_exhausted"
                if reason == "retry_allowed":
                    if retry_budget_remaining is not None and retry_budget_remaining <= 0 and action in {
                        "same_prompt_retry",
                        "repair_prompt_retry",
                    }:
                        retry_allowed = False
                        reason = "retry_budget_exhausted"
                    if action == "signal_recollect" and (missing_signal_count or 0) >= 2:
                        retry_allowed = False
                        reason = "missing_signal_repeated"
                if (
                    reason == "retry_allowed"
                    and _as_non_negative_int(retry_decision.get("remaining_attempts"), default=0) <= 0
                ):
                    retry_allowed = False
                    reason = "retry_attempts_exhausted_by_policy"
                if retry_allowed:
                    retries_performed += 1
                    last_audit = self._record_audit(
                        run_root=run_root,
                        job_id=job_id,
                        scheduler_action_taken="retry_dispatch",
                        execution_attempted=False,
                        retry_attempted=True,
                        routed_action=action,
                        routing_reason=reason,
                        retry_class=retry_class,
                        retry_budget_remaining=retry_budget_remaining,
                        whether_human_required=whether_human_required,
                        outcome_status="retry_dispatched",
                    )
                    continue
                last_audit = self._record_audit(
                    run_root=run_root,
                    job_id=job_id,
                    scheduler_action_taken="escalate",
                    execution_attempted=False,
                    retry_attempted=False,
                    routed_action=action,
                    routing_reason=reason,
                    retry_class=retry_class,
                    retry_budget_remaining=retry_budget_remaining,
                    whether_human_required=True,
                    outcome_status="escalated",
                )
                return {
                    "job_id": job_id,
                    "dispatch_status": "escalated",
                    "manifests": manifests,
                    "audit": last_audit,
                }

            if routing_class == ROUTING_CLASS_CONTROL:
                last_audit = self._record_audit(
                    run_root=run_root,
                    job_id=job_id,
                    scheduler_action_taken="escalate",
                    execution_attempted=False,
                    retry_attempted=False,
                    routed_action=action,
                    routing_reason="authority_control_action_no_executor_route",
                    retry_class=retry_class,
                    retry_budget_remaining=retry_budget_remaining,
                    whether_human_required=True,
                    outcome_status="escalated",
                )
                return {
                    "job_id": job_id,
                    "dispatch_status": "escalated",
                    "manifests": manifests,
                    "audit": last_audit,
                }

            if routing_class != ROUTING_CLASS_EXECUTOR:
                last_audit = self._record_audit(
                    run_root=run_root,
                    job_id=job_id,
                    scheduler_action_taken="escalate",
                    execution_attempted=False,
                    retry_attempted=False,
                    routed_action=action,
                    routing_reason="unsupported_or_non_routable_action",
                    retry_class=retry_class,
                    retry_budget_remaining=retry_budget_remaining,
                    whether_human_required=True,
                    outcome_status="escalated",
                )
                return {
                    "job_id": job_id,
                    "dispatch_status": "escalated",
                    "manifests": manifests,
                    "audit": last_audit,
                }

            if not action_consumable:
                last_audit = self._record_audit(
                    run_root=run_root,
                    job_id=job_id,
                    scheduler_action_taken="escalate",
                    execution_attempted=False,
                    retry_attempted=False,
                    routed_action=action,
                    routing_reason="handoff_action_not_consumable",
                    retry_class=retry_class,
                    retry_budget_remaining=retry_budget_remaining,
                    whether_human_required=True,
                    outcome_status="escalated",
                )
                return {
                    "job_id": job_id,
                    "dispatch_status": "escalated",
                    "manifests": manifests,
                    "audit": last_audit,
                }

            if action == "proceed_to_merge" and request.pr_number is None:
                last_audit = self._record_audit(
                    run_root=run_root,
                    job_id=job_id,
                    scheduler_action_taken="escalate",
                    execution_attempted=False,
                    retry_attempted=False,
                    routed_action=action,
                    routing_reason="merge_pr_number_missing",
                    retry_class=retry_class,
                    retry_budget_remaining=retry_budget_remaining,
                    whether_human_required=True,
                    outcome_status="escalated",
                )
                return {
                    "job_id": job_id,
                    "dispatch_status": "escalated",
                    "manifests": manifests,
                    "audit": last_audit,
                }

            if action == "github.pr.update":
                pr_update = request.pr_update if isinstance(request.pr_update, Mapping) else {}
                explicit_update_keys = {key for key in ("title", "body", "base_branch") if key in pr_update}
                if request.pr_number is None:
                    last_audit = self._record_audit(
                        run_root=run_root,
                        job_id=job_id,
                        scheduler_action_taken="escalate",
                        execution_attempted=False,
                        retry_attempted=False,
                        routed_action=action,
                        routing_reason="update_pr_number_missing",
                        retry_class=retry_class,
                        retry_budget_remaining=retry_budget_remaining,
                        whether_human_required=True,
                        outcome_status="escalated",
                    )
                    return {
                        "job_id": job_id,
                        "dispatch_status": "escalated",
                        "manifests": manifests,
                        "audit": last_audit,
                    }
                if not explicit_update_keys:
                    last_audit = self._record_audit(
                        run_root=run_root,
                        job_id=job_id,
                        scheduler_action_taken="escalate",
                        execution_attempted=False,
                        retry_attempted=False,
                        routed_action=action,
                        routing_reason="pr_update_payload_missing_or_invalid",
                        retry_class=retry_class,
                        retry_budget_remaining=retry_budget_remaining,
                        whether_human_required=True,
                        outcome_status="escalated",
                    )
                    return {
                        "job_id": job_id,
                        "dispatch_status": "escalated",
                        "manifests": manifests,
                        "audit": last_audit,
                    }

            if action == "rollback_required":
                rollback_target = request.rollback_target if isinstance(request.rollback_target, Mapping) else {}
                required_keys = ("repo_path", "target_ref", "pre_merge_sha", "post_merge_sha")
                if not rollback_target or any(not _normalize_text(rollback_target.get(key), default="") for key in required_keys):
                    last_audit = self._record_audit(
                        run_root=run_root,
                        job_id=job_id,
                        scheduler_action_taken="escalate",
                        execution_attempted=False,
                        retry_attempted=False,
                        routed_action=action,
                        routing_reason="rollback_target_missing_or_ambiguous",
                        retry_class=retry_class,
                        retry_budget_remaining=retry_budget_remaining,
                        whether_human_required=True,
                        outcome_status="escalated",
                    )
                    return {
                        "job_id": job_id,
                        "dispatch_status": "escalated",
                        "manifests": manifests,
                        "audit": last_audit,
                    }

            receipt = self.action_executor.execute_from_run_dir(
                run_root,
                repository=request.repository,
                head_branch=request.head_branch,
                base_branch=request.base_branch,
                category=request.category,
                write_authority=request.write_authority,
                policy_snapshot=request.policy_snapshot,
                pr_number=request.pr_number,
                pr_update=request.pr_update,
                expected_head_sha=request.expected_head_sha,
                rollback_target=request.rollback_target,
            )
            succeeded = _as_bool(receipt.get("succeeded"))
            refusal_reason = _normalize_text(receipt.get("refusal_reason"), default="")
            last_audit = self._record_audit(
                run_root=run_root,
                job_id=job_id,
                scheduler_action_taken="route_to_executor",
                execution_attempted=True,
                retry_attempted=False,
                routed_action=action,
                routing_reason=refusal_reason or "executor_succeeded",
                retry_class=retry_class,
                retry_budget_remaining=retry_budget_remaining,
                whether_human_required=_as_bool(receipt.get("whether_human_required")),
                outcome_status="executed" if succeeded else "escalated",
            )
            return {
                "job_id": job_id,
                "dispatch_status": "executed" if succeeded else "escalated",
                "manifests": manifests,
                "audit": last_audit,
                "receipt": receipt,
            }
