from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from typing import Callable
from typing import Mapping

from automation.github.read_backend import GitHubReadBackend
from automation.github.write_backend import GitHubWriteBackend
from automation.github.write_idempotency import DEDUPE_CONFLICTING_PRIOR_INTENT
from automation.github.write_idempotency import DEDUPE_PRECONDITION_CHANGED
from automation.github.write_idempotency import DEDUPE_REPLAY_SAME_INTENT
from automation.github.write_idempotency import DEDUPE_UNKNOWN_NEEDS_HUMAN
from automation.github.write_idempotency import evaluate_write_dedupe_status
from automation.github.write_receipts import FileWriteReceiptStore

_BLOCKING_STATUSES = {"auth_failure", "api_failure", "unsupported_query"}
_MISSING_STATUSES = {"empty", "not_found"}
_MERGEABLE_ALLOWED = {"clean"}
_WRITE_ACTION = "bounded_merge"


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


def _result_status(payload: Mapping[str, Any]) -> str:
    return _normalize_text(payload.get("status"), default="api_failure")


def _result_data(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    data = payload.get("data")
    return data if isinstance(data, Mapping) else {}


def _result_error(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    error = payload.get("error")
    return error if isinstance(error, Mapping) else {}


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
class BoundedMergeExecutor:
    read_backend: GitHubReadBackend
    write_backend: GitHubWriteBackend
    now: Callable[[], datetime] = datetime.now

    def execute_merge(
        self,
        *,
        job_id: str,
        repository: str,
        pr_number: int,
        expected_head_sha: str | None = None,
        write_receipt_store: FileWriteReceiptStore | None = None,
    ) -> dict[str, Any]:
        repo = _normalize_text(repository, default="")
        normalized_pr_number = _as_optional_int(pr_number)
        expected_sha = _normalize_text(expected_head_sha, default="")
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
                        "pr_number": normalized_pr_number,
                    },
                    "intent_fingerprint": _normalize_text(dedupe_details.get("intent_fingerprint"), default=""),
                    "execution_status": _normalize_text(execution_status, default="not_attempted"),
                    "observed_github_facts": dict(observed_github_facts or {}),
                    "final_classification": final_classification,
                    "request_snapshot": {
                        "repository": repo,
                        "pr_number": normalized_pr_number,
                        "expected_head_sha": expected_sha or None,
                        "merge_method": "merge",
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
                    "requested_action": "proceed_to_merge",
                    "attempted": attempted,
                    "succeeded": False,
                    "refusal_reason": reason,
                    "repository": repo or None,
                    "pr_number": normalized_pr_number,
                    "merge_commit_sha": None,
                    "merged_state_summary": {"merged": False},
                    "checks_state_summary": {"checks_state": "unknown"},
                    "evidence_used_summary": {"read_operations": evidence_items, "constraints": []},
                }
            )

        if not repo:
            return _refusal("repository_missing")
        if normalized_pr_number is None or normalized_pr_number <= 0:
            return _refusal("pr_number_missing_or_invalid")

        prior_records = write_receipt_store.list_records(_WRITE_ACTION) if write_receipt_store is not None else []
        dedupe_details = evaluate_write_dedupe_status(
            job_id=resolved_job_id,
            write_action=_WRITE_ACTION,
            target_identifiers={"repository": repo, "pr_number": normalized_pr_number},
            intent_payload={"merge_method": "merge", "expected_head_sha": expected_sha or None},
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

        status_payload = self.read_backend.get_pr_status_summary(
            repo,
            pr_number=normalized_pr_number,
        )
        _record_evidence(target=evidence_items, payload=status_payload)
        status = _result_status(status_payload)
        if status in _BLOCKING_STATUSES:
            return _refusal(f"pr_status_unavailable:{status}")
        if status in _MISSING_STATUSES:
            return _refusal(f"pr_status_missing:{status}")
        status_data = _result_data(status_payload)
        commit_sha = _normalize_text(status_data.get("commit_sha"), default="")
        pr_state = _normalize_text(status_data.get("pr_state"), default="")
        pr_draft = bool(status_data.get("pr_draft", False))
        pr_merged = bool(status_data.get("pr_merged", False))
        mergeable_state = _normalize_text(status_data.get("mergeable_state"), default="")
        checks_state = _normalize_text(status_data.get("checks_state"), default="unknown")
        pr_head_ref = _normalize_text(status_data.get("pr_head_ref"), default="")
        pr_base_ref = _normalize_text(status_data.get("pr_base_ref"), default="")

        precondition_snapshot = {
            "expected_pr_number": normalized_pr_number,
            "expected_head_sha": expected_sha or None,
            "observed_head_sha": commit_sha or None,
            "observed_pr_state": pr_state or None,
            "observed_pr_draft": pr_draft,
            "observed_pr_merged": pr_merged,
            "observed_mergeable_state": mergeable_state or None,
            "observed_checks_state": checks_state or None,
            "observed_head_ref": pr_head_ref or None,
            "observed_base_ref": pr_base_ref or None,
        }

        if dedupe_status == DEDUPE_REPLAY_SAME_INTENT:
            prior = dedupe_details.get("matched_record") if isinstance(dedupe_details.get("matched_record"), Mapping) else {}
            prior_preconditions = (
                prior.get("precondition_snapshot")
                if isinstance(prior.get("precondition_snapshot"), Mapping)
                else {}
            )
            prior_head_sha = _normalize_text(prior_preconditions.get("observed_head_sha"), default="")
            if pr_merged:
                _persist_write_receipt(
                    final_classification="already_applied",
                    execution_status="not_attempted",
                    response_summary={
                        "reason": "pr_already_merged_on_replay",
                        "observed_head_sha": commit_sha or None,
                    },
                    observed_github_facts={"pr_merged": True},
                )
                return _with_idempotency(
                    {
                        "job_id": resolved_job_id,
                        "requested_action": "proceed_to_merge",
                        "attempted": False,
                        "succeeded": True,
                        "refusal_reason": None,
                        "repository": repo,
                        "pr_number": normalized_pr_number,
                        "merge_commit_sha": None,
                        "merged_state_summary": {"merged": True, "mergeable_state": mergeable_state},
                        "checks_state_summary": {"checks_state": checks_state},
                        "evidence_used_summary": {
                            "read_operations": evidence_items,
                            "constraints": ["merge_already_applied_noop"],
                            "write_result": {"status": "already_applied"},
                        },
                    }
                )
            if prior_head_sha and commit_sha and prior_head_sha != commit_sha:
                _persist_write_receipt(
                    final_classification="precondition_changed",
                    execution_status="not_attempted",
                    response_summary={"reason": "merge_head_sha_changed_on_replay"},
                    observed_github_facts={"pr_merged": pr_merged, "observed_head_sha": commit_sha},
                )
                return _refusal("idempotency_precondition_changed:head_sha_changed")

        if not commit_sha:
            return _refusal("pr_head_commit_missing")
        if expected_sha and expected_sha != commit_sha:
            return _refusal("expected_head_sha_mismatch")
        if pr_state and pr_state != "open":
            return _refusal(f"pr_state_not_mergeable:{pr_state}")
        if pr_draft:
            return _refusal("pr_is_draft")
        if pr_merged:
            _persist_write_receipt(
                final_classification="already_applied",
                execution_status="not_attempted",
                response_summary={"reason": "pr_already_merged"},
                observed_github_facts={"pr_merged": True},
            )
            return _with_idempotency(
                {
                    "job_id": resolved_job_id,
                    "requested_action": "proceed_to_merge",
                    "attempted": False,
                    "succeeded": True,
                    "refusal_reason": None,
                    "repository": repo,
                    "pr_number": normalized_pr_number,
                    "merge_commit_sha": None,
                    "merged_state_summary": {"merged": True, "mergeable_state": mergeable_state},
                    "checks_state_summary": {"checks_state": checks_state},
                    "evidence_used_summary": {
                        "read_operations": evidence_items,
                        "constraints": ["merge_already_applied_noop"],
                        "write_result": {"status": "already_applied"},
                    },
                }
            )
        if checks_state != "passing":
            return _refusal(f"checks_not_passing:{checks_state or 'unknown'}")
        if not mergeable_state or mergeable_state not in _MERGEABLE_ALLOWED:
            return _refusal(f"mergeability_not_clean:{mergeable_state or 'unknown'}")
        if not pr_head_ref or not pr_base_ref:
            return _refusal("pr_branch_identity_missing")

        owner = repo.split("/", 1)[0] if "/" in repo else ""
        query_head = f"{owner}:{pr_head_ref}" if owner else pr_head_ref
        open_pr_payload = self.read_backend.find_open_pr(
            repo,
            head_branch=query_head,
            base_branch=pr_base_ref,
        )
        _record_evidence(target=evidence_items, payload=open_pr_payload)
        open_pr_status = _result_status(open_pr_payload)
        if open_pr_status in _BLOCKING_STATUSES:
            return _refusal(f"open_pr_lookup_failed:{open_pr_status}")
        if open_pr_status in _MISSING_STATUSES:
            return _refusal(f"open_pr_lookup_missing:{open_pr_status}")
        open_pr_data = _result_data(open_pr_payload)
        if not bool(open_pr_data.get("matched", False)):
            return _refusal("open_pr_not_matched")
        match_count = _as_optional_int(open_pr_data.get("match_count"))
        if match_count is None or match_count != 1:
            return _refusal("open_pr_ambiguous")
        matched_pr = open_pr_data.get("pr") if isinstance(open_pr_data.get("pr"), Mapping) else {}
        matched_pr_number = _as_optional_int(matched_pr.get("number"))
        if matched_pr_number != normalized_pr_number:
            return _refusal("open_pr_number_mismatch")

        base_head_payload = self.read_backend.get_branch_head(repo, pr_base_ref)
        _record_evidence(target=evidence_items, payload=base_head_payload)
        base_status = _result_status(base_head_payload)
        if base_status in _BLOCKING_STATUSES:
            return _refusal(f"base_branch_lookup_failed:{base_status}")
        if base_status in _MISSING_STATUSES:
            return _refusal(f"base_branch_lookup_missing:{base_status}")
        base_data = _result_data(base_head_payload)
        if base_data.get("exists") is False or not _normalize_text(base_data.get("head_sha"), default=""):
            return _refusal("base_branch_head_missing")

        compare_payload = self.read_backend.compare_refs(repo, pr_base_ref, commit_sha)
        _record_evidence(target=evidence_items, payload=compare_payload)
        compare_status = _result_status(compare_payload)
        if compare_status in _BLOCKING_STATUSES:
            return _refusal(f"compare_refs_failed:{compare_status}")
        if compare_status in _MISSING_STATUSES:
            return _refusal(f"compare_refs_missing:{compare_status}")
        compare_state = _normalize_text(_result_data(compare_payload).get("comparison_status"), default="unknown")
        if compare_state not in {"ahead", "diverged"}:
            return _refusal(f"compare_refs_not_mergeable:{compare_state}")

        merge_payload = self.write_backend.merge_pull_request(
            repo=repo,
            pr_number=normalized_pr_number,
            expected_head_sha=commit_sha,
            merge_method="merge",
        )
        merge_status = _result_status(merge_payload)
        merge_data = _result_data(merge_payload)
        merge_error = _result_error(merge_payload)
        merge_commit_sha = _normalize_text(merge_data.get("merge_commit_sha"), default="")
        merged = bool(merge_data.get("merged", False))
        if merge_status != "success" or not merged or not merge_commit_sha:
            error_kind = _normalize_text(merge_error.get("kind"), default=merge_status)
            failure_classification = (
                "auth_failure"
                if error_kind == "auth_failure"
                else "api_failure"
                if error_kind == "api_failure"
                else "unsupported"
                if error_kind == "unsupported_query"
                else "failed"
            )
            _persist_write_receipt(
                final_classification=failure_classification,
                execution_status="failed",
                response_summary={"status": merge_status, "error_kind": error_kind},
                observed_github_facts={"pr_merged": pr_merged, "open_pr_lookup_status": open_pr_status},
            )
            return _with_idempotency(
                {
                    **_refusal(f"merge_execution_failed:{error_kind}", attempted=True),
                    "evidence_used_summary": {
                        "read_operations": evidence_items,
                        "constraints": [],
                        "write_result": {
                            "status": merge_status,
                            "error_kind": error_kind,
                        },
                    },
                }
            )

        _persist_write_receipt(
            final_classification="applied",
            execution_status="attempted",
            response_summary={
                "status": merge_status,
                "merge_commit_sha": merge_commit_sha,
                "merged": merged,
            },
            observed_github_facts={"open_pr_lookup_status": open_pr_status, "compare_status": compare_state},
        )
        return _with_idempotency(
            {
                "job_id": resolved_job_id,
                "requested_action": "proceed_to_merge",
                "attempted": True,
                "succeeded": True,
                "refusal_reason": None,
                "repository": repo,
                "pr_number": normalized_pr_number,
                "merge_commit_sha": merge_commit_sha,
                "merged_state_summary": {"merged": True, "mergeable_state": mergeable_state},
                "checks_state_summary": {"checks_state": checks_state},
                "evidence_used_summary": {
                    "read_operations": evidence_items,
                    "constraints": [],
                    "write_result": {"status": merge_status},
                },
            }
        )
