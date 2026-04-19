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

_BLOCKING_EVIDENCE_STATUSES = {"auth_failure", "api_failure", "unsupported_query"}
_MISSING_EVIDENCE_STATUSES = {"empty", "not_found"}
_WRITE_ACTION = "create_draft_pr"


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


def _body_summary(body: str) -> str:
    first_line = _normalize_text(body.splitlines()[0] if body else "", default="")
    return first_line or "(empty)"


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
class DraftPRCreator:
    read_backend: GitHubReadBackend
    write_backend: GitHubWriteBackend
    now: Callable[[], datetime] = datetime.now

    def create_draft_pr(
        self,
        *,
        job_id: str,
        repository: str,
        head_branch: str,
        base_branch: str | None,
        title: str,
        body: str,
        allow_missing_compare_evidence: bool = False,
        allow_missing_open_pr_evidence: bool = False,
        allow_missing_check_evidence: bool = False,
        allow_not_found_as_absence: bool = False,
        write_receipt_store: FileWriteReceiptStore | None = None,
    ) -> dict[str, Any]:
        repo = _normalize_text(repository, default="")
        head = _normalize_text(head_branch, default="")
        base = _normalize_text(base_branch, default="")
        normalized_title = _normalize_text(title, default="")
        normalized_body = _normalize_text(body, default="")
        resolved_job_id = _normalize_text(job_id, default="")

        evidence_items: list[dict[str, Any]] = []
        evidence_constraints: list[str] = []
        dedupe_details: Mapping[str, Any] | None = None

        def _persist_write_receipt(
            *,
            final_classification: str,
            execution_status: str,
            response_summary: Mapping[str, Any] | None = None,
            observed_github_facts: Mapping[str, Any] | None = None,
            precondition_snapshot: Mapping[str, Any] | None = None,
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
                        "head_branch": head,
                        "base_branch": base,
                    },
                    "intent_fingerprint": _normalize_text(dedupe_details.get("intent_fingerprint"), default=""),
                    "execution_status": _normalize_text(execution_status, default="not_attempted"),
                    "observed_github_facts": dict(observed_github_facts or {}),
                    "final_classification": final_classification,
                    "request_snapshot": {
                        "repository": repo,
                        "head_branch": head,
                        "base_branch": base,
                        "title": normalized_title,
                        "body_summary": _body_summary(normalized_body),
                    },
                    "response_summary": dict(response_summary or {}),
                    "precondition_snapshot": dict(precondition_snapshot or {}),
                },
            )

        def _response_with_idempotency(payload: Mapping[str, Any]) -> dict[str, Any]:
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
            return _response_with_idempotency(
                {
                    "job_id": resolved_job_id,
                    "attempted": attempted,
                    "succeeded": False,
                    "refusal_reason": reason,
                    "repository": repo or None,
                    "base_branch": base or None,
                    "head_branch": head or None,
                    "pr_number": None,
                    "pr_url": None,
                    "title_preview": normalized_title or None,
                    "body_preview": normalized_body or None,
                    "body_summary": _body_summary(normalized_body),
                    "evidence_used_summary": {
                        "read_operations": evidence_items,
                        "constraints": sorted(set(evidence_constraints)),
                    },
                }
            )

        if not repo:
            return _refusal("repository_missing")
        if not head:
            return _refusal("head_branch_missing")
        if not normalized_title:
            return _refusal("pr_title_missing")

        if not base:
            default_branch_payload = self.read_backend.get_default_branch(repo)
            _record_evidence(target=evidence_items, payload=default_branch_payload)
            default_status = _result_status(default_branch_payload)
            if default_status in _BLOCKING_EVIDENCE_STATUSES:
                return _refusal(f"default_branch_lookup_failed:{default_status}")
            if default_status in _MISSING_EVIDENCE_STATUSES:
                return _refusal(f"default_branch_missing:{default_status}")
            base = _normalize_text(_result_data(default_branch_payload).get("default_branch"), default="")
            if not base:
                return _refusal("base_branch_unresolved")

        if head == base:
            return _refusal("head_and_base_branch_must_differ")

        prior_records = write_receipt_store.list_records(_WRITE_ACTION) if write_receipt_store is not None else []
        dedupe_details = evaluate_write_dedupe_status(
            job_id=resolved_job_id,
            write_action=_WRITE_ACTION,
            target_identifiers={
                "repository": repo,
                "head_branch": head,
                "base_branch": base,
            },
            intent_payload={
                "title": normalized_title,
                "body": normalized_body,
                "draft": True,
            },
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

        head_payload = self.read_backend.get_branch_head(repo, head)
        _record_evidence(target=evidence_items, payload=head_payload)
        head_status = _result_status(head_payload)
        if head_status in _BLOCKING_EVIDENCE_STATUSES:
            return _refusal(f"head_branch_lookup_failed:{head_status}")
        if head_status in _MISSING_EVIDENCE_STATUSES:
            return _refusal(f"head_branch_missing:{head_status}")
        head_data = _result_data(head_payload)
        head_exists = head_data.get("exists")
        head_sha = _normalize_text(head_data.get("head_sha"), default="")
        if head_exists is False or not head_sha:
            return _refusal("head_branch_missing_or_unresolved")

        base_payload = self.read_backend.get_branch_head(repo, base)
        _record_evidence(target=evidence_items, payload=base_payload)
        base_status = _result_status(base_payload)
        if base_status in _BLOCKING_EVIDENCE_STATUSES:
            return _refusal(f"base_branch_lookup_failed:{base_status}")
        if base_status in _MISSING_EVIDENCE_STATUSES:
            return _refusal(f"base_branch_missing:{base_status}")
        base_data = _result_data(base_payload)
        base_exists = base_data.get("exists")
        base_sha = _normalize_text(base_data.get("head_sha"), default="")
        if base_exists is False or not base_sha:
            return _refusal("base_branch_missing_or_unresolved")

        compare_payload = self.read_backend.compare_refs(repo, base, head)
        _record_evidence(target=evidence_items, payload=compare_payload)
        compare_status = _result_status(compare_payload)
        if compare_status in _BLOCKING_EVIDENCE_STATUSES:
            return _refusal(f"compare_refs_failed:{compare_status}")
        compare_data = _result_data(compare_payload)
        comparison_status = _normalize_text(compare_data.get("comparison_status"), default="unknown")
        if compare_status in _MISSING_EVIDENCE_STATUSES:
            if allow_missing_compare_evidence and compare_status == "empty":
                evidence_constraints.append(f"compare_refs_missing:{compare_status}")
            else:
                return _refusal(f"compare_refs_missing:{compare_status}")
        else:
            if comparison_status not in {"ahead", "diverged"}:
                return _refusal(f"compare_refs_not_creatable:{comparison_status}")

        open_pr_payload = self.read_backend.find_open_pr(
            repo,
            head_branch=head,
            base_branch=base,
        )
        _record_evidence(target=evidence_items, payload=open_pr_payload)
        open_pr_status = _result_status(open_pr_payload)
        if open_pr_status in _BLOCKING_EVIDENCE_STATUSES:
            return _refusal(f"open_pr_lookup_failed:{open_pr_status}")
        open_pr_data = _result_data(open_pr_payload)
        if open_pr_status == "success" and bool(open_pr_data.get("matched", False)):
            pr_data = open_pr_data.get("pr") if isinstance(open_pr_data.get("pr"), Mapping) else {}
            duplicate_number = _as_optional_int(pr_data.get("number"))
            duplicate_url = _normalize_text(pr_data.get("html_url"), default="")
            _persist_write_receipt(
                final_classification="already_applied",
                execution_status="not_attempted",
                response_summary={
                    "reason": "open_pr_already_exists",
                    "pr_number": duplicate_number,
                    "pr_url": duplicate_url or None,
                },
                observed_github_facts={
                    "open_pr_lookup_status": open_pr_status,
                    "open_pr_matched": True,
                },
                precondition_snapshot={
                    "head_sha": head_sha,
                    "base_sha": base_sha,
                    "comparison_status": comparison_status,
                },
            )
            return _response_with_idempotency(
                {
                    "job_id": resolved_job_id,
                    "attempted": False,
                    "succeeded": True,
                    "refusal_reason": None,
                    "repository": repo,
                    "base_branch": base,
                    "head_branch": head,
                    "pr_number": duplicate_number,
                    "pr_url": duplicate_url or None,
                    "title_preview": normalized_title,
                    "body_preview": normalized_body,
                    "body_summary": _body_summary(normalized_body),
                    "evidence_used_summary": {
                        "read_operations": evidence_items,
                        "constraints": sorted(set(evidence_constraints + ["open_pr_already_exists_noop"])),
                        "write_result": {"status": "already_applied"},
                    },
                }
            )
        if open_pr_status == "not_found":
            if allow_not_found_as_absence and allow_missing_open_pr_evidence:
                evidence_constraints.append("open_pr_lookup_not_found_treated_as_absence")
            else:
                return _refusal("open_pr_lookup_missing:not_found")
        if open_pr_status == "empty":
            evidence_constraints.append("open_pr_lookup_empty")

        checks_payload = self.read_backend.get_pr_status_summary(
            repo,
            commit_sha=head_sha,
        )
        _record_evidence(target=evidence_items, payload=checks_payload)
        checks_status = _result_status(checks_payload)
        if checks_status in _BLOCKING_EVIDENCE_STATUSES:
            return _refusal(f"checks_summary_failed:{checks_status}")
        if checks_status in _MISSING_EVIDENCE_STATUSES:
            if checks_status == "empty" and allow_missing_check_evidence:
                evidence_constraints.append("checks_summary_empty")
            elif checks_status == "not_found" and allow_missing_check_evidence and allow_not_found_as_absence:
                evidence_constraints.append("checks_summary_not_found_treated_as_absence")
            else:
                return _refusal(f"checks_summary_missing:{checks_status}")

        if dedupe_status == DEDUPE_REPLAY_SAME_INTENT:
            _persist_write_receipt(
                final_classification="precondition_changed",
                execution_status="not_attempted",
                response_summary={"reason": "replay_without_matching_open_pr"},
                observed_github_facts={
                    "open_pr_lookup_status": open_pr_status,
                    "open_pr_matched": bool(open_pr_data.get("matched", False)),
                },
                precondition_snapshot={
                    "head_sha": head_sha,
                    "base_sha": base_sha,
                    "comparison_status": comparison_status,
                },
            )
            return _refusal("idempotency_replay_precondition_changed")

        write_payload = self.write_backend.create_draft_pr(
            repo=repo,
            title=normalized_title,
            body=normalized_body,
            head_branch=head,
            base_branch=base,
        )
        write_status = _result_status(write_payload)
        write_data = _result_data(write_payload)
        pr_data = write_data.get("pr") if isinstance(write_data.get("pr"), Mapping) else {}
        pr_number = _as_optional_int(pr_data.get("number"))
        pr_url = _normalize_text(pr_data.get("html_url"), default="")

        if write_status != "success":
            write_error = write_payload.get("error") if isinstance(write_payload.get("error"), Mapping) else {}
            error_kind = _normalize_text(write_error.get("kind"), default=write_status)
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
                response_summary={"status": write_status, "error_kind": error_kind},
                observed_github_facts={"open_pr_lookup_status": open_pr_status},
                precondition_snapshot={
                    "head_sha": head_sha,
                    "base_sha": base_sha,
                    "comparison_status": comparison_status,
                },
            )
            return _response_with_idempotency(
                {
                    **_refusal(
                        f"draft_pr_creation_failed:{error_kind}",
                        attempted=True,
                    ),
                    "evidence_used_summary": {
                        "read_operations": evidence_items,
                        "constraints": sorted(set(evidence_constraints)),
                        "write_result": {
                            "status": write_status,
                            "error_kind": error_kind,
                        },
                    },
                }
            )

        _persist_write_receipt(
            final_classification="applied",
            execution_status="attempted",
            response_summary={
                "status": write_status,
                "pr_number": pr_number,
                "pr_url": pr_url or None,
            },
            observed_github_facts={"open_pr_lookup_status": open_pr_status},
            precondition_snapshot={
                "head_sha": head_sha,
                "base_sha": base_sha,
                "comparison_status": comparison_status,
            },
        )
        return _response_with_idempotency(
            {
                "job_id": resolved_job_id,
                "attempted": True,
                "succeeded": True,
                "refusal_reason": None,
                "repository": repo,
                "base_branch": base,
                "head_branch": head,
                "pr_number": pr_number,
                "pr_url": pr_url or None,
                "title_preview": normalized_title,
                "body_preview": normalized_body,
                "body_summary": _body_summary(normalized_body),
                "evidence_used_summary": {
                    "read_operations": evidence_items,
                    "constraints": sorted(set(evidence_constraints)),
                    "write_result": {
                        "status": write_status,
                    },
                },
            }
        )
