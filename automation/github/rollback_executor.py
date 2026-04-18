from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from typing import Callable
from typing import Mapping

from automation.github.read_backend import GitHubReadBackend
from automation.github.write_idempotency import DEDUPE_CONFLICTING_PRIOR_INTENT
from automation.github.write_idempotency import DEDUPE_PRECONDITION_CHANGED
from automation.github.write_idempotency import DEDUPE_REPLAY_SAME_INTENT
from automation.github.write_idempotency import DEDUPE_UNKNOWN_NEEDS_HUMAN
from automation.github.write_idempotency import evaluate_write_dedupe_status
from automation.github.write_receipts import FileWriteReceiptStore
from orchestrator.rollback_executor import execute_constrained_rollback

_BLOCKING_STATUSES = {"auth_failure", "api_failure", "unsupported_query"}
_MISSING_STATUSES = {"empty", "not_found"}
_WRITE_ACTION = "rollback_preparation_write_path"


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _result_status(payload: Mapping[str, Any]) -> str:
    return _normalize_text(payload.get("status"), default="api_failure")


def _result_data(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    data = payload.get("data")
    return data if isinstance(data, Mapping) else {}


def _record_evidence(
    *,
    target: list[dict[str, Any]],
    payload: Mapping[str, Any],
) -> None:
    target.append(
        {
            "operation": _normalize_text(payload.get("operation"), default="unknown_operation"),
            "status": _result_status(payload),
            "ok": bool(payload.get("ok", False)),
        }
    )


def _now_iso(now: Callable[[], datetime]) -> str:
    return now().isoformat(timespec="seconds")


@dataclass
class BoundedRollbackExecutor:
    read_backend: GitHubReadBackend
    now: Callable[[], datetime] = datetime.now

    def execute_rollback(
        self,
        *,
        job_id: str,
        repository: str,
        repo_path: str,
        target_ref: str,
        pre_merge_sha: str,
        post_merge_sha: str,
        write_receipt_store: FileWriteReceiptStore | None = None,
    ) -> dict[str, Any]:
        repo = _normalize_text(repository, default="")
        normalized_repo_path = _normalize_text(repo_path, default="")
        branch = _normalize_text(target_ref, default="")
        pre_sha = _normalize_text(pre_merge_sha, default="")
        post_sha = _normalize_text(post_merge_sha, default="")
        resolved_job_id = _normalize_text(job_id, default="")
        evidence_items: list[dict[str, Any]] = []
        dedupe_details: Mapping[str, Any] | None = None
        precondition_snapshot: dict[str, Any] = {}

        def _persist_write_receipt(
            *,
            final_classification: str,
            execution_status: str,
            response_summary: Mapping[str, Any] | None = None,
            observed_github_facts: Mapping[str, Any] | None = None,
        ) -> None:
            if write_receipt_store is None or not isinstance(dedupe_details, Mapping):
                return
            write_receipt_store.persist_record(
                write_action=_WRITE_ACTION,
                idempotency_key=_normalize_text(dedupe_details.get("idempotency_key"), default=""),
                updated_at=_now_iso(self.now),
                payload={
                    "idempotency_key": _normalize_text(dedupe_details.get("idempotency_key"), default=""),
                    "job_id": resolved_job_id,
                    "write_action": _WRITE_ACTION,
                    "target_identifiers": {
                        "repository": repo,
                        "target_ref": branch,
                        "pre_merge_sha": pre_sha,
                        "post_merge_sha": post_sha,
                    },
                    "intent_fingerprint": _normalize_text(dedupe_details.get("intent_fingerprint"), default=""),
                    "execution_status": _normalize_text(execution_status, default="not_attempted"),
                    "observed_github_facts": dict(observed_github_facts or {}),
                    "final_classification": final_classification,
                    "request_snapshot": {
                        "repository": repo,
                        "repo_path": normalized_repo_path,
                        "target_ref": branch,
                        "pre_merge_sha": pre_sha,
                        "post_merge_sha": post_sha,
                    },
                    "response_summary": dict(response_summary or {}),
                    "precondition_snapshot": dict(precondition_snapshot),
                },
            )

        def _with_idempotency(payload: Mapping[str, Any]) -> dict[str, Any]:
            out = dict(payload)
            if isinstance(dedupe_details, Mapping):
                out["idempotency"] = {
                    "write_action": _WRITE_ACTION,
                    "idempotency_key": _normalize_text(dedupe_details.get("idempotency_key"), default=""),
                    "intent_fingerprint": _normalize_text(dedupe_details.get("intent_fingerprint"), default=""),
                    "dedupe_status": _normalize_text(dedupe_details.get("dedupe_status"), default="first_attempt"),
                }
            return out

        def _refusal(reason: str, *, attempted: bool = False) -> dict[str, Any]:
            return _with_idempotency(
                {
                    "job_id": resolved_job_id,
                    "requested_action": "rollback_required",
                    "attempted": attempted,
                    "succeeded": False,
                    "refusal_reason": reason,
                    "repository": repo or None,
                    "rollback_target": {
                        "repo_path": normalized_repo_path or None,
                        "target_ref": branch or None,
                        "pre_merge_sha": pre_sha or None,
                        "post_merge_sha": post_sha or None,
                    },
                    "rollback_scope_summary": {
                        "mode": "constrained_single_merge_revert",
                        "bounded": True,
                    },
                    "rollback_result_summary": {
                        "status": "not_attempted" if not attempted else "failed",
                        "error": reason,
                    },
                    "evidence_used_summary": {"read_operations": evidence_items, "constraints": []},
                }
            )

        if not repo:
            return _refusal("repository_missing")
        if not normalized_repo_path:
            return _refusal("repo_path_missing")
        if not branch:
            return _refusal("target_ref_missing")
        if not pre_sha:
            return _refusal("pre_merge_sha_missing")
        if not post_sha:
            return _refusal("post_merge_sha_missing")

        prior_records = write_receipt_store.list_records(_WRITE_ACTION) if write_receipt_store is not None else []
        dedupe_details = evaluate_write_dedupe_status(
            job_id=resolved_job_id,
            write_action=_WRITE_ACTION,
            target_identifiers={
                "repository": repo,
                "target_ref": branch,
                "pre_merge_sha": pre_sha,
                "post_merge_sha": post_sha,
            },
            intent_payload={"mode": "constrained_single_merge_revert"},
            prior_records=prior_records,
        )
        dedupe_status = _normalize_text(dedupe_details.get("dedupe_status"), default="first_attempt")
        if dedupe_status == DEDUPE_CONFLICTING_PRIOR_INTENT:
            _persist_write_receipt(
                final_classification="conflict",
                execution_status="not_attempted",
                response_summary={"reason": "conflicting_prior_intent"},
            )
            return _refusal("idempotency_conflict:conflicting_prior_intent")
        if dedupe_status == DEDUPE_PRECONDITION_CHANGED:
            _persist_write_receipt(
                final_classification="precondition_changed",
                execution_status="not_attempted",
                response_summary={"reason": "prior_precondition_changed"},
            )
            return _refusal("idempotency_precondition_changed")
        if dedupe_status == DEDUPE_UNKNOWN_NEEDS_HUMAN:
            _persist_write_receipt(
                final_classification="needs_human",
                execution_status="not_attempted",
                response_summary={"reason": "prior_needs_human"},
            )
            return _refusal("idempotency_unknown_needs_human")

        branch_payload = self.read_backend.get_branch_head(repo, branch)
        _record_evidence(target=evidence_items, payload=branch_payload)
        branch_status = _result_status(branch_payload)
        if branch_status in _BLOCKING_STATUSES:
            return _refusal(f"branch_lookup_failed:{branch_status}")
        if branch_status in _MISSING_STATUSES:
            return _refusal(f"branch_lookup_missing:{branch_status}")
        branch_data = _result_data(branch_payload)
        remote_head_sha = _normalize_text(branch_data.get("head_sha"), default="")
        precondition_snapshot = {
            "expected_target_ref": branch,
            "expected_pre_merge_sha": pre_sha,
            "expected_post_merge_sha": post_sha,
            "observed_remote_head_sha": remote_head_sha or None,
        }

        if dedupe_status == DEDUPE_REPLAY_SAME_INTENT:
            if remote_head_sha == pre_sha:
                _persist_write_receipt(
                    final_classification="already_applied",
                    execution_status="not_attempted",
                    response_summary={"reason": "rollback_already_applied"},
                    observed_github_facts={"observed_remote_head_sha": remote_head_sha},
                )
                return _with_idempotency(
                    {
                        "job_id": resolved_job_id,
                        "requested_action": "rollback_required",
                        "attempted": False,
                        "succeeded": True,
                        "refusal_reason": None,
                        "repository": repo,
                        "rollback_target": {
                            "repo_path": normalized_repo_path,
                            "target_ref": branch,
                            "pre_merge_sha": pre_sha,
                            "post_merge_sha": post_sha,
                        },
                        "rollback_scope_summary": {
                            "mode": "constrained_single_merge_revert",
                            "bounded": True,
                        },
                        "rollback_result_summary": {
                            "status": "already_applied",
                            "error": None,
                            "consistency_check_passed": True,
                            "current_head_sha": remote_head_sha,
                            "rollback_result_sha": pre_sha,
                        },
                        "evidence_used_summary": {
                            "read_operations": evidence_items,
                            "constraints": ["rollback_already_applied_noop"],
                        },
                    }
                )
            if remote_head_sha and remote_head_sha != post_sha:
                _persist_write_receipt(
                    final_classification="precondition_changed",
                    execution_status="not_attempted",
                    response_summary={"reason": "rollback_head_changed_on_replay"},
                    observed_github_facts={"observed_remote_head_sha": remote_head_sha},
                )
                return _refusal("idempotency_precondition_changed:rollback_head_changed")

        if branch_data.get("exists") is False or not remote_head_sha:
            return _refusal("branch_head_missing")
        if remote_head_sha != post_sha:
            return _refusal("rollback_target_head_mismatch")

        compare_payload = self.read_backend.compare_refs(repo, pre_sha, post_sha)
        _record_evidence(target=evidence_items, payload=compare_payload)
        compare_status = _result_status(compare_payload)
        if compare_status in _BLOCKING_STATUSES:
            return _refusal(f"rollback_compare_failed:{compare_status}")
        if compare_status in _MISSING_STATUSES:
            return _refusal(f"rollback_compare_missing:{compare_status}")
        compare_state = _normalize_text(_result_data(compare_payload).get("comparison_status"), default="unknown")
        if compare_state not in {"ahead", "diverged"}:
            return _refusal(f"rollback_compare_not_actionable:{compare_state}")

        status_payload = self.read_backend.get_pr_status_summary(
            repo,
            commit_sha=post_sha,
        )
        _record_evidence(target=evidence_items, payload=status_payload)
        status = _result_status(status_payload)
        if status in _BLOCKING_STATUSES:
            return _refusal(f"rollback_commit_status_failed:{status}")
        if status in _MISSING_STATUSES:
            return _refusal(f"rollback_commit_status_missing:{status}")

        rollback_result = execute_constrained_rollback(
            repo_path=normalized_repo_path,
            target_ref=branch,
            pre_merge_sha=pre_sha,
            post_merge_sha=post_sha,
        )
        rollback_status = _normalize_text(rollback_result.get("status"), default="failed")
        attempted = bool(rollback_result.get("attempted", False))
        if rollback_status != "succeeded":
            _persist_write_receipt(
                final_classification="failed",
                execution_status="failed" if attempted else "not_attempted",
                response_summary={
                    "status": rollback_status,
                    "error": _normalize_text(rollback_result.get("error"), default="unknown"),
                },
                observed_github_facts={"observed_remote_head_sha": remote_head_sha},
            )
            return _with_idempotency(
                {
                    **_refusal(
                        f"rollback_execution_{rollback_status}:{_normalize_text(rollback_result.get('error'), default='unknown')}",
                        attempted=attempted,
                    ),
                    "rollback_result_summary": {
                        "status": rollback_status,
                        "error": _normalize_text(rollback_result.get("error"), default="unknown"),
                        "consistency_check_passed": bool(rollback_result.get("consistency_check_passed", False)),
                        "current_head_sha": _normalize_text(rollback_result.get("current_head_sha"), default="") or None,
                        "rollback_result_sha": _normalize_text(rollback_result.get("rollback_result_sha"), default="")
                        or None,
                    },
                }
            )

        _persist_write_receipt(
            final_classification="applied",
            execution_status="attempted",
            response_summary={
                "status": rollback_status,
                "rollback_result_sha": _normalize_text(rollback_result.get("rollback_result_sha"), default="") or None,
            },
            observed_github_facts={"observed_remote_head_sha": remote_head_sha, "compare_state": compare_state},
        )
        return _with_idempotency(
            {
                "job_id": resolved_job_id,
                "requested_action": "rollback_required",
                "attempted": attempted,
                "succeeded": True,
                "refusal_reason": None,
                "repository": repo,
                "rollback_target": {
                    "repo_path": normalized_repo_path,
                    "target_ref": branch,
                    "pre_merge_sha": pre_sha,
                    "post_merge_sha": post_sha,
                },
                "rollback_scope_summary": {
                    "mode": "constrained_single_merge_revert",
                    "bounded": True,
                },
                "rollback_result_summary": {
                    "status": rollback_status,
                    "error": None,
                    "consistency_check_passed": bool(rollback_result.get("consistency_check_passed", False)),
                    "current_head_sha": _normalize_text(rollback_result.get("current_head_sha"), default="") or None,
                    "rollback_result_sha": _normalize_text(rollback_result.get("rollback_result_sha"), default="")
                    or None,
                },
                "evidence_used_summary": {"read_operations": evidence_items, "constraints": []},
            }
        )
