from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from typing import Callable
from typing import Mapping

from automation.github.github_client import GitHubClientError
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
_WRITE_ACTION = "update_existing_pr"


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


def _requested_update(
    *,
    title: str | None,
    body: str | None,
    base_branch: str | None,
) -> tuple[dict[str, Any], bool]:
    payload: dict[str, Any] = {}
    if title is not None:
        payload["title"] = _normalize_text(title, default="")
    if body is not None:
        payload["body"] = _normalize_text(body, default="")
    if base_branch is not None:
        payload["base_branch"] = _normalize_text(base_branch, default="")
    has_explicit_update = bool(payload)
    return payload, has_explicit_update


def _pr_preview(current_pr: Mapping[str, Any]) -> dict[str, Any]:
    head = current_pr.get("head") if isinstance(current_pr.get("head"), Mapping) else {}
    base = current_pr.get("base") if isinstance(current_pr.get("base"), Mapping) else {}
    return {
        "number": _as_optional_int(current_pr.get("number")),
        "html_url": _normalize_text(current_pr.get("html_url"), default=""),
        "title": _normalize_text(current_pr.get("title"), default=""),
        "body": _normalize_text(current_pr.get("body"), default=""),
        "base_ref": _normalize_text(base.get("ref"), default=""),
        "head_ref": _normalize_text(head.get("ref"), default=""),
    }


@dataclass
class BoundedPRUpdater:
    read_backend: GitHubReadBackend
    write_backend: GitHubWriteBackend
    now: Callable[[], datetime] = datetime.now

    def update_pr(
        self,
        *,
        job_id: str,
        repository: str,
        pr_number: int,
        title: str | None = None,
        body: str | None = None,
        base_branch: str | None = None,
        write_receipt_store: FileWriteReceiptStore | None = None,
    ) -> dict[str, Any]:
        repo = _normalize_text(repository, default="")
        normalized_pr_number = _as_optional_int(pr_number)
        resolved_job_id = _normalize_text(job_id, default="")
        requested_update, has_explicit_update = _requested_update(
            title=title,
            body=body,
            base_branch=base_branch,
        )
        evidence_items: list[dict[str, Any]] = []
        evidence_constraints: list[str] = []
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
                        "requested_update": dict(requested_update),
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
                    "requested_action": "github.pr.update",
                    "attempted": attempted,
                    "succeeded": False,
                    "refusal_reason": reason,
                    "repository": repo or None,
                    "pr_number": normalized_pr_number,
                    "pr_url": None,
                    "title_preview": requested_update.get("title"),
                    "body_preview": requested_update.get("body"),
                    "base_branch": requested_update.get("base_branch"),
                    "evidence_used_summary": {"read_operations": evidence_items, "constraints": sorted(set(evidence_constraints))},
                }
            )

        if not repo:
            return _refusal("repository_missing")
        if normalized_pr_number is None or normalized_pr_number <= 0:
            return _refusal("pr_number_missing_or_invalid")
        if not has_explicit_update:
            return _refusal("pr_update_missing_or_invalid")
        if "base_branch" in requested_update and not _normalize_text(requested_update.get("base_branch"), default=""):
            return _refusal("base_branch_empty_when_explicitly_provided")

        if write_receipt_store is not None:
            try:
                prior_records = write_receipt_store.list_records(_WRITE_ACTION)
            except Exception:
                return _refusal("write_receipt_store_unavailable_or_corrupt")
        else:
            prior_records = []
        dedupe_details = evaluate_write_dedupe_status(
            job_id=resolved_job_id,
            write_action=_WRITE_ACTION,
            target_identifiers={"repository": repo, "pr_number": normalized_pr_number},
            intent_payload=requested_update,
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
        pr_state = _normalize_text(status_data.get("pr_state"), default="")
        pr_merged = bool(status_data.get("pr_merged", False))
        commit_sha = _normalize_text(status_data.get("commit_sha"), default="")
        if pr_merged:
            return _refusal("pr_already_merged")
        if pr_state and pr_state != "open":
            return _refusal(f"pr_state_not_updatable:{pr_state}")
        if not commit_sha:
            evidence_constraints.append("pr_head_commit_missing")

        try:
            current_pr_payload = self.read_backend.client.get_pull_request(repo, normalized_pr_number)
        except GitHubClientError as exc:
            error_kind = _normalize_text(exc.kind, default="api_failure")
            if error_kind in _BLOCKING_STATUSES:
                return _refusal(f"pr_lookup_failed:{error_kind}")
            if error_kind in _MISSING_STATUSES:
                return _refusal(f"pr_lookup_missing:{error_kind}")
            return _refusal(f"pr_lookup_failed:{error_kind}")

        current_preview = _pr_preview(current_pr_payload)
        precondition_snapshot = {
            "observed_pr_number": current_preview.get("number"),
            "observed_title": current_preview.get("title"),
            "observed_base_ref": current_preview.get("base_ref"),
            "observed_head_ref": current_preview.get("head_ref"),
            "observed_commit_sha": commit_sha or None,
            "requested_update": dict(requested_update),
        }

        matches_requested_state = True
        if "title" in requested_update and current_preview.get("title") != requested_update.get("title"):
            matches_requested_state = False
        if "body" in requested_update and current_preview.get("body") != requested_update.get("body"):
            matches_requested_state = False
        if "base_branch" in requested_update and current_preview.get("base_ref") != requested_update.get("base_branch"):
            matches_requested_state = False

        if matches_requested_state:
            _persist_write_receipt(
                final_classification="already_applied",
                execution_status="not_attempted",
                response_summary={"reason": "requested_update_already_applied"},
                observed_github_facts={"pr_state": pr_state or None, "pr_merged": pr_merged},
            )
            return _with_idempotency(
                {
                    "job_id": resolved_job_id,
                    "requested_action": "github.pr.update",
                    "attempted": False,
                    "succeeded": True,
                    "refusal_reason": None,
                    "repository": repo,
                    "pr_number": normalized_pr_number,
                    "pr_url": current_preview.get("html_url") or None,
                    "title_preview": current_preview.get("title") or None,
                    "body_preview": current_preview.get("body") or None,
                    "base_branch": current_preview.get("base_ref") or None,
                    "evidence_used_summary": {
                        "read_operations": evidence_items,
                        "constraints": sorted(set(evidence_constraints + ["update_already_applied_noop"])),
                        "write_result": {"status": "already_applied"},
                    },
                }
            )

        if dedupe_status == DEDUPE_REPLAY_SAME_INTENT:
            _persist_write_receipt(
                final_classification="precondition_changed",
                execution_status="not_attempted",
                response_summary={"reason": "update_replay_precondition_changed"},
                observed_github_facts={"pr_state": pr_state or None, "pr_merged": pr_merged},
            )
            return _refusal("idempotency_precondition_changed:update_replay")

        write_payload = self.write_backend.update_existing_pr(
            repo=repo,
            pr_number=normalized_pr_number,
            title=requested_update.get("title") if "title" in requested_update else None,
            body=requested_update.get("body") if "body" in requested_update else None,
            base_branch=requested_update.get("base_branch") if "base_branch" in requested_update else None,
            current_pr=current_pr_payload,
        )
        write_status = _result_status(write_payload)
        write_data = _result_data(write_payload)
        write_pr = write_data.get("pr") if isinstance(write_data.get("pr"), Mapping) else {}
        updated_preview = _pr_preview(write_pr)
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
                observed_github_facts={"pr_state": pr_state or None, "pr_merged": pr_merged},
            )
            return _refusal(f"pr_update_failed:{error_kind}", attempted=True)

        final_classification = _normalize_text(write_data.get("classification"), default="applied")
        if final_classification not in {"applied", "already_applied", "no_op"}:
            final_classification = "applied"
        _persist_write_receipt(
            final_classification=final_classification,
            execution_status="attempted" if final_classification == "applied" else "not_attempted",
            response_summary={
                "status": write_status,
                "classification": final_classification,
                "updated": bool(write_data.get("updated", True)),
            },
            observed_github_facts={"pr_state": pr_state or None, "pr_merged": pr_merged},
        )
        return _with_idempotency(
            {
                "job_id": resolved_job_id,
                "requested_action": "github.pr.update",
                "attempted": bool(write_data.get("updated", True)),
                "succeeded": True,
                "refusal_reason": None,
                "repository": repo,
                "pr_number": normalized_pr_number,
                "pr_url": updated_preview.get("html_url") or current_preview.get("html_url") or None,
                "title_preview": updated_preview.get("title") or current_preview.get("title") or None,
                "body_preview": updated_preview.get("body") or current_preview.get("body") or None,
                "base_branch": updated_preview.get("base_ref") or current_preview.get("base_ref") or None,
                "evidence_used_summary": {
                    "read_operations": evidence_items,
                    "constraints": sorted(set(evidence_constraints)),
                    "write_result": {
                        "status": write_status,
                        "classification": final_classification,
                        "updated": bool(write_data.get("updated", True)),
                    },
                },
            }
        )
