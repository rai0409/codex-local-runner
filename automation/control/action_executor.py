from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Mapping

from automation.control.execution_authority import resolve_action_routing
from automation.control.execution_authority import LANE_GITHUB_DETERMINISTIC
from automation.control.execution_authority import ROUTING_CLASS_EXECUTOR
from automation.github.merge_executor import BoundedMergeExecutor
from automation.github.pr_creator import DraftPRCreator
from automation.github.pr_updater import BoundedPRUpdater
from automation.github.rollback_executor import BoundedRollbackExecutor
from automation.github.write_receipts import FileWriteReceiptStore

_PR_CREATION_RECEIPT_FILENAME = "pr_creation_receipt.json"
_PR_UPDATE_RECEIPT_FILENAME = "pr_update_receipt.json"
_MERGE_RECEIPT_FILENAME = "merge_receipt.json"
_ROLLBACK_RECEIPT_FILENAME = "rollback_receipt.json"

_SUPPORTED_ACTIONS = {
    "proceed_to_pr",
    "github.pr.update",
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
    items: list[str] = []
    seen: set[str] = set()
    for raw in value:
        text = str(raw).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        items.append(text)
    if sort_items:
        return sorted(items)
    return items


def _as_mapping(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


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


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return False


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _iso_now(now: Callable[[], datetime]) -> str:
    return now().isoformat(timespec="seconds")


def _receipt_filename_for_action(action: str) -> str:
    if action == "github.pr.update":
        return _PR_UPDATE_RECEIPT_FILENAME
    if action == "proceed_to_merge":
        return _MERGE_RECEIPT_FILENAME
    if action == "rollback_required":
        return _ROLLBACK_RECEIPT_FILENAME
    return _PR_CREATION_RECEIPT_FILENAME


def _default_receipt(
    *,
    job_id: str,
    requested_action: str | None,
    executed_at: str,
    whether_human_required: bool,
) -> dict[str, Any]:
    return {
        "job_id": job_id,
        "requested_action": requested_action,
        "attempted": False,
        "succeeded": False,
        "refusal_reason": None,
        "repository": None,
        "base_branch": None,
        "head_branch": None,
        "pr_number": None,
        "pr_url": None,
        "merge_commit_sha": None,
        "merged_state_summary": None,
        "checks_state_summary": None,
        "rollback_target": None,
        "rollback_scope_summary": None,
        "rollback_result_summary": None,
        "title_preview": None,
        "body_preview": None,
        "body_summary": None,
        "evidence_used_summary": {"read_operations": [], "constraints": []},
        "write_idempotency": None,
        "write_authority_state": None,
        "whether_human_required": whether_human_required,
        "executed_at": executed_at,
    }


def _normalize_write_authority(value: Mapping[str, Any] | None) -> dict[str, Any]:
    source = value if isinstance(value, Mapping) else {}
    state = _normalize_text(source.get("state"), default="").lower()
    if not state:
        enabled = _as_bool(source.get("enabled"))
        kill_switch = _as_bool(source.get("kill_switch"))
        dry_run = _as_bool(source.get("dry_run"))
        if not enabled:
            state = "disabled"
        elif kill_switch:
            state = "blocked"
        elif dry_run:
            state = "dry_run_only"
        else:
            state = "write_allowed"

    write_actions_allowed = _as_bool(source.get("write_actions_allowed"))
    if "write_actions_allowed" not in source:
        write_actions_allowed = state == "write_allowed"

    return {
        "state": state,
        "write_actions_allowed": write_actions_allowed,
        "allowed_categories": _normalize_string_list(source.get("allowed_categories"), sort_items=True),
        "allowed_actions": _normalize_string_list(source.get("allowed_actions"), sort_items=True),
    }


def _resolve_artifacts_from_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    artifact_input_dir = _normalize_text(manifest.get("artifact_input_dir"), default="")
    if not artifact_input_dir:
        return {"project_brief": {}, "repo_facts": {}, "pr_plan": {}}

    root = Path(artifact_input_dir)
    if not root.exists() or not root.is_dir():
        return {"project_brief": {}, "repo_facts": {}, "pr_plan": {}}

    result: dict[str, Any] = {"project_brief": {}, "repo_facts": {}, "pr_plan": {}}
    for name in ("project_brief", "repo_facts", "pr_plan"):
        path = root / f"{name}.json"
        if not path.exists():
            continue
        try:
            result[name] = _read_json_object(path)
        except Exception:
            result[name] = {}
    return result


def _derive_single_category(pr_plan: Mapping[str, Any]) -> str:
    prs = pr_plan.get("prs")
    if not isinstance(prs, list):
        return ""
    categories = sorted(
        {
            _normalize_text(item.get("tier_category"), default="")
            for item in prs
            if isinstance(item, Mapping) and _normalize_text(item.get("tier_category"), default="")
        }
    )
    if len(categories) == 1:
        return categories[0]
    return ""


def _build_title_and_body(
    *,
    job_id: str,
    requested_action: str,
    reason: str,
    pr_plan: Mapping[str, Any],
) -> tuple[str, str]:
    prs = pr_plan.get("prs")
    normalized_prs = [item for item in prs if isinstance(item, Mapping)] if isinstance(prs, list) else []
    if len(normalized_prs) == 1:
        title = _normalize_text(normalized_prs[0].get("title"), default="")
        if not title:
            title = f"[{job_id}] planned execution draft"
    else:
        title = f"[{job_id}] planned execution draft ({len(normalized_prs)} slices)"

    lines = [
        "Bounded draft PR created from persisted action handoff.",
        f"job_id: {job_id}",
        f"requested_action: {requested_action}",
        f"decision_reason: {_normalize_text(reason, default='(none)')}",
        f"plan_id: {_normalize_text(pr_plan.get('plan_id'), default='(unknown)')}",
    ]
    if normalized_prs:
        lines.append("planned_slices:")
        for item in normalized_prs:
            pr_id = _normalize_text(item.get("pr_id"), default="(unknown)")
            pr_title = _normalize_text(item.get("title"), default="(untitled)")
            lines.append(f"- {pr_id}: {pr_title}")
    return title, "\n".join(lines).strip()


def _policy_flag(policy_snapshot: Mapping[str, Any] | None, key: str) -> bool:
    if not isinstance(policy_snapshot, Mapping):
        return False
    pr_creation = policy_snapshot.get("pr_creation")
    if isinstance(pr_creation, Mapping) and key in pr_creation:
        return _as_bool(pr_creation.get(key))
    if key in policy_snapshot:
        return _as_bool(policy_snapshot.get(key))
    return False


@dataclass
class ActionExecutor:
    pr_creator: DraftPRCreator | None = None
    pr_updater: BoundedPRUpdater | None = None
    merge_executor: BoundedMergeExecutor | None = None
    rollback_executor: BoundedRollbackExecutor | None = None
    now: Callable[[], datetime] = datetime.now

    def execute_from_run_dir(
        self,
        run_dir: str | Path,
        *,
        repository: str | None = None,
        head_branch: str | None = None,
        base_branch: str | None = None,
        category: str | None = None,
        write_authority: Mapping[str, Any] | None = None,
        policy_snapshot: Mapping[str, Any] | None = None,
        pr_number: int | None = None,
        expected_head_sha: str | None = None,
        rollback_target: Mapping[str, Any] | None = None,
        pr_update: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        root = Path(run_dir)
        if not root.exists() or not root.is_dir():
            raise ValueError(f"run artifact directory does not exist: {root}")

        executed_at = _iso_now(self.now)
        default_job_id = _normalize_text(root.name, default="unknown_job")

        def _persist_receipt(payload: Mapping[str, Any], *, requested_action: str | None) -> dict[str, Any]:
            receipt_path = root / _receipt_filename_for_action(_normalize_text(requested_action, default=""))
            _write_json(receipt_path, payload)
            return dict(payload)

        handoff_path = root / "action_handoff.json"
        if not handoff_path.exists():
            receipt = _default_receipt(
                job_id=default_job_id,
                requested_action=None,
                executed_at=executed_at,
                whether_human_required=True,
            )
            receipt["refusal_reason"] = "action_handoff_missing"
            return _persist_receipt(receipt, requested_action=None)

        try:
            handoff = _read_json_object(handoff_path)
        except Exception as exc:
            receipt = _default_receipt(
                job_id=default_job_id,
                requested_action=None,
                executed_at=executed_at,
                whether_human_required=True,
            )
            receipt["refusal_reason"] = f"action_handoff_invalid:{_normalize_text(exc, default='invalid_json')}"
            return _persist_receipt(receipt, requested_action=None)

        manifest = {}
        manifest_path = root / "manifest.json"
        if manifest_path.exists():
            try:
                manifest = _read_json_object(manifest_path)
            except Exception:
                manifest = {}

        next_action_payload = {}
        next_action_path = root / "next_action.json"
        if next_action_path.exists():
            try:
                next_action_payload = _read_json_object(next_action_path)
            except Exception:
                next_action_payload = {}

        requested_action = _normalize_text(handoff.get("next_action"), default="")
        whether_human_required = bool(handoff.get("whether_human_required", False))
        resolved_job_id = _normalize_text(
            handoff.get("job_id"),
            default=_normalize_text(manifest.get("job_id"), default=default_job_id),
        )
        receipt = _default_receipt(
            job_id=resolved_job_id,
            requested_action=requested_action or None,
            executed_at=executed_at,
            whether_human_required=whether_human_required,
        )
        write_receipt_store = FileWriteReceiptStore(root / "write_receipts")

        def _refuse(reason: str) -> dict[str, Any]:
            receipt["refusal_reason"] = reason
            return _persist_receipt(receipt, requested_action=requested_action)

        next_action_token = _normalize_text(next_action_payload.get("next_action"), default="")
        if next_action_token and requested_action and next_action_token != requested_action:
            return _refuse("next_action_handoff_mismatch")

        if requested_action not in _SUPPORTED_ACTIONS:
            return _refuse(f"unsupported_action:{requested_action or 'missing'}")

        routing_selection = resolve_action_routing(
            requested_action,
            policy_snapshot=policy_snapshot,
            handoff_payload=handoff,
        )
        if not bool(routing_selection.get("known_action")):
            return _refuse("authority_action_unclassified")
        if not bool(routing_selection.get("allowed")):
            reason = _normalize_text(routing_selection.get("reason"), default="lane_not_allowed")
            return _refuse(f"authority_{reason}")
        if _normalize_text(routing_selection.get("routing_class"), default="") != ROUTING_CLASS_EXECUTOR:
            return _refuse("authority_routing_mismatch:executor_requires_executor_class")
        if _normalize_text(routing_selection.get("resolved_lane"), default="") != LANE_GITHUB_DETERMINISTIC:
            return _refuse("authority_routing_mismatch:executor_requires_github_deterministic")

        if not _as_bool(handoff.get("action_consumable")):
            unsupported_reason = _normalize_text(handoff.get("unsupported_reason"), default="handoff_not_consumable")
            return _refuse(f"handoff_action_not_consumable:{unsupported_reason}")

        authority = _normalize_write_authority(write_authority)
        receipt["write_authority_state"] = authority["state"] or None
        if not write_authority:
            return _refuse("write_authority_missing")
        if authority["state"] != "write_allowed" or not authority["write_actions_allowed"]:
            return _refuse(f"write_authority_blocked:{authority['state'] or 'unknown'}")

        allowed_actions = authority["allowed_actions"]
        if allowed_actions and requested_action not in set(allowed_actions):
            return _refuse("write_action_not_allowed")

        planning = _resolve_artifacts_from_manifest(manifest)
        project_brief = planning.get("project_brief") if isinstance(planning.get("project_brief"), Mapping) else {}
        repo_facts = planning.get("repo_facts") if isinstance(planning.get("repo_facts"), Mapping) else {}
        pr_plan = planning.get("pr_plan") if isinstance(planning.get("pr_plan"), Mapping) else {}
        resolved_category = _normalize_text(category, default=_derive_single_category(pr_plan))
        allowed_categories = authority["allowed_categories"]
        if allowed_categories:
            if not resolved_category:
                return _refuse("category_missing_for_authority_gate")
            if resolved_category not in set(allowed_categories):
                return _refuse("category_not_allowed_for_execution")

        resolved_repository = _normalize_text(
            repository,
            default=_normalize_text(
                repo_facts.get("repo"),
                default=_normalize_text(project_brief.get("target_repo"), default=""),
            ),
        )
        if not resolved_repository:
            return _refuse("repository_missing")
        receipt["repository"] = resolved_repository

        if requested_action == "proceed_to_pr":
            if self.pr_creator is None:
                return _refuse("pr_creation_executor_unavailable")

            resolved_head_branch = _normalize_text(
                head_branch,
                default=_normalize_text(
                    _as_mapping(policy_snapshot).get("head_branch") if _as_mapping(policy_snapshot) else "",
                    default="",
                ),
            )
            if not resolved_head_branch:
                return _refuse("head_branch_missing")

            resolved_base_branch = _normalize_text(
                base_branch,
                default=_normalize_text(
                    project_brief.get("target_branch"),
                    default=_normalize_text(repo_facts.get("default_branch"), default=""),
                ),
            )
            reason = _normalize_text(handoff.get("reason"), default="")
            title_preview, body_preview = _build_title_and_body(
                job_id=resolved_job_id,
                requested_action=requested_action,
                reason=reason,
                pr_plan=pr_plan,
            )
            if not title_preview:
                return _refuse("title_generation_failed")

            try:
                creation_result = self.pr_creator.create_draft_pr(
                    job_id=resolved_job_id,
                    repository=resolved_repository,
                    head_branch=resolved_head_branch,
                    base_branch=resolved_base_branch or None,
                    title=title_preview,
                    body=body_preview,
                    allow_missing_compare_evidence=_policy_flag(policy_snapshot, "allow_missing_compare_evidence"),
                    allow_missing_open_pr_evidence=_policy_flag(policy_snapshot, "allow_missing_open_pr_evidence"),
                    allow_missing_check_evidence=_policy_flag(policy_snapshot, "allow_missing_check_evidence"),
                    allow_not_found_as_absence=_policy_flag(policy_snapshot, "allow_not_found_as_absence"),
                    write_receipt_store=write_receipt_store,
                )
            except Exception:
                return _refuse("write_receipt_store_unavailable_or_corrupt")
            receipt["attempted"] = bool(creation_result.get("attempted", False))
            receipt["succeeded"] = bool(creation_result.get("succeeded", False))
            receipt["refusal_reason"] = _normalize_text(creation_result.get("refusal_reason"), default="") or None
            receipt["base_branch"] = _normalize_text(creation_result.get("base_branch"), default="") or (
                resolved_base_branch or None
            )
            receipt["head_branch"] = _normalize_text(creation_result.get("head_branch"), default="") or resolved_head_branch
            receipt["pr_number"] = creation_result.get("pr_number")
            receipt["pr_url"] = _normalize_text(creation_result.get("pr_url"), default="") or None
            receipt["title_preview"] = _normalize_text(creation_result.get("title_preview"), default="") or title_preview
            receipt["body_preview"] = _normalize_text(creation_result.get("body_preview"), default="") or body_preview
            receipt["body_summary"] = _normalize_text(creation_result.get("body_summary"), default="") or None
            evidence_used = creation_result.get("evidence_used_summary")
            receipt["evidence_used_summary"] = (
                dict(evidence_used)
                if isinstance(evidence_used, Mapping)
                else {"read_operations": [], "constraints": []}
            )
            idempotency = creation_result.get("idempotency")
            receipt["write_idempotency"] = dict(idempotency) if isinstance(idempotency, Mapping) else None
            return _persist_receipt(receipt, requested_action=requested_action)

        if requested_action == "github.pr.update":
            if self.pr_updater is None:
                return _refuse("pr_update_executor_unavailable")

            resolved_pr_number = _as_optional_int(
                pr_number
                if pr_number is not None
                else (_as_mapping(policy_snapshot).get("pr_number") if _as_mapping(policy_snapshot) else None)
            )
            if resolved_pr_number is None or resolved_pr_number <= 0:
                return _refuse("update_pr_number_missing_or_invalid")

            update_payload = pr_update if isinstance(pr_update, Mapping) else {}
            if not update_payload and isinstance(policy_snapshot, Mapping):
                maybe = policy_snapshot.get("pr_update")
                if isinstance(maybe, Mapping):
                    update_payload = maybe
            if not update_payload:
                maybe = handoff.get("pr_update")
                if isinstance(maybe, Mapping):
                    update_payload = maybe
            explicit_keys = {key for key in ("title", "body", "base_branch") if key in update_payload}
            if not explicit_keys:
                return _refuse("pr_update_missing_or_invalid")

            title = update_payload.get("title") if "title" in explicit_keys else None
            body = update_payload.get("body") if "body" in explicit_keys else None
            base = update_payload.get("base_branch") if "base_branch" in explicit_keys else None

            try:
                update_result = self.pr_updater.update_pr(
                    job_id=resolved_job_id,
                    repository=resolved_repository,
                    pr_number=resolved_pr_number,
                    title=str(title) if title is not None else None,
                    body=str(body) if body is not None else None,
                    base_branch=str(base) if base is not None else None,
                    write_receipt_store=write_receipt_store,
                )
            except Exception:
                return _refuse("write_receipt_store_unavailable_or_corrupt")

            receipt["attempted"] = bool(update_result.get("attempted", False))
            receipt["succeeded"] = bool(update_result.get("succeeded", False))
            receipt["refusal_reason"] = _normalize_text(update_result.get("refusal_reason"), default="") or None
            receipt["pr_number"] = _as_optional_int(update_result.get("pr_number"))
            receipt["pr_url"] = _normalize_text(update_result.get("pr_url"), default="") or None
            receipt["title_preview"] = _normalize_text(update_result.get("title_preview"), default="") or None
            receipt["body_preview"] = _normalize_text(update_result.get("body_preview"), default="") or None
            receipt["base_branch"] = _normalize_text(update_result.get("base_branch"), default="") or None
            evidence_used = update_result.get("evidence_used_summary")
            receipt["evidence_used_summary"] = (
                dict(evidence_used)
                if isinstance(evidence_used, Mapping)
                else {"read_operations": [], "constraints": []}
            )
            idempotency = update_result.get("idempotency")
            receipt["write_idempotency"] = dict(idempotency) if isinstance(idempotency, Mapping) else None
            return _persist_receipt(receipt, requested_action=requested_action)

        if requested_action == "proceed_to_merge":
            if self.merge_executor is None:
                return _refuse("merge_executor_unavailable")
            resolved_pr_number = _as_optional_int(
                pr_number
                if pr_number is not None
                else (_as_mapping(policy_snapshot).get("pr_number") if _as_mapping(policy_snapshot) else None)
            )
            if resolved_pr_number is None or resolved_pr_number <= 0:
                return _refuse("merge_pr_number_missing_or_invalid")

            try:
                merge_result = self.merge_executor.execute_merge(
                    job_id=resolved_job_id,
                    repository=resolved_repository,
                    pr_number=resolved_pr_number,
                    expected_head_sha=_normalize_text(expected_head_sha, default="") or None,
                    write_receipt_store=write_receipt_store,
                )
            except Exception:
                return _refuse("write_receipt_store_unavailable_or_corrupt")
            receipt["attempted"] = bool(merge_result.get("attempted", False))
            receipt["succeeded"] = bool(merge_result.get("succeeded", False))
            receipt["refusal_reason"] = _normalize_text(merge_result.get("refusal_reason"), default="") or None
            receipt["pr_number"] = _as_optional_int(merge_result.get("pr_number"))
            receipt["merge_commit_sha"] = _normalize_text(merge_result.get("merge_commit_sha"), default="") or None
            merged_summary = merge_result.get("merged_state_summary")
            checks_summary = merge_result.get("checks_state_summary")
            evidence_used = merge_result.get("evidence_used_summary")
            receipt["merged_state_summary"] = dict(merged_summary) if isinstance(merged_summary, Mapping) else None
            receipt["checks_state_summary"] = dict(checks_summary) if isinstance(checks_summary, Mapping) else None
            receipt["evidence_used_summary"] = (
                dict(evidence_used)
                if isinstance(evidence_used, Mapping)
                else {"read_operations": [], "constraints": []}
            )
            idempotency = merge_result.get("idempotency")
            receipt["write_idempotency"] = dict(idempotency) if isinstance(idempotency, Mapping) else None
            return _persist_receipt(receipt, requested_action=requested_action)

        if requested_action == "rollback_required":
            if self.rollback_executor is None:
                return _refuse("rollback_executor_unavailable")
            rollback_payload = rollback_target if isinstance(rollback_target, Mapping) else {}
            if not rollback_payload and isinstance(policy_snapshot, Mapping):
                maybe = policy_snapshot.get("rollback_target")
                if isinstance(maybe, Mapping):
                    rollback_payload = maybe
            repo_path = _normalize_text(rollback_payload.get("repo_path"), default="")
            target_ref = _normalize_text(rollback_payload.get("target_ref"), default="")
            pre_merge_sha = _normalize_text(rollback_payload.get("pre_merge_sha"), default="")
            post_merge_sha = _normalize_text(rollback_payload.get("post_merge_sha"), default="")
            if not repo_path or not target_ref or not pre_merge_sha or not post_merge_sha:
                return _refuse("rollback_target_missing_or_ambiguous")

            try:
                rollback_result = self.rollback_executor.execute_rollback(
                    job_id=resolved_job_id,
                    repository=resolved_repository,
                    repo_path=repo_path,
                    target_ref=target_ref,
                    pre_merge_sha=pre_merge_sha,
                    post_merge_sha=post_merge_sha,
                    write_receipt_store=write_receipt_store,
                )
            except Exception:
                return _refuse("write_receipt_store_unavailable_or_corrupt")
            receipt["attempted"] = bool(rollback_result.get("attempted", False))
            receipt["succeeded"] = bool(rollback_result.get("succeeded", False))
            receipt["refusal_reason"] = _normalize_text(rollback_result.get("refusal_reason"), default="") or None
            rollback_target_summary = rollback_result.get("rollback_target")
            rollback_scope_summary = rollback_result.get("rollback_scope_summary")
            rollback_result_summary = rollback_result.get("rollback_result_summary")
            evidence_used = rollback_result.get("evidence_used_summary")
            receipt["rollback_target"] = (
                dict(rollback_target_summary) if isinstance(rollback_target_summary, Mapping) else None
            )
            receipt["rollback_scope_summary"] = (
                dict(rollback_scope_summary) if isinstance(rollback_scope_summary, Mapping) else None
            )
            receipt["rollback_result_summary"] = (
                dict(rollback_result_summary) if isinstance(rollback_result_summary, Mapping) else None
            )
            receipt["evidence_used_summary"] = (
                dict(evidence_used)
                if isinstance(evidence_used, Mapping)
                else {"read_operations": [], "constraints": []}
            )
            idempotency = rollback_result.get("idempotency")
            receipt["write_idempotency"] = dict(idempotency) if isinstance(idempotency, Mapping) else None
            return _persist_receipt(receipt, requested_action=requested_action)

        return _refuse("unsupported_action_dispatch")


def execute_action_from_run_dir(
    run_dir: str | Path,
    *,
    executor: ActionExecutor,
    repository: str | None = None,
    head_branch: str | None = None,
    base_branch: str | None = None,
    category: str | None = None,
    write_authority: Mapping[str, Any] | None = None,
    policy_snapshot: Mapping[str, Any] | None = None,
    pr_number: int | None = None,
    expected_head_sha: str | None = None,
    rollback_target: Mapping[str, Any] | None = None,
    pr_update: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return executor.execute_from_run_dir(
        run_dir,
        repository=repository,
        head_branch=head_branch,
        base_branch=base_branch,
        category=category,
        write_authority=write_authority,
        policy_snapshot=policy_snapshot,
        pr_number=pr_number,
        expected_head_sha=expected_head_sha,
        rollback_target=rollback_target,
        pr_update=pr_update,
    )
