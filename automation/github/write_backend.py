from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Mapping

from automation.github.github_client import GitHubClientError
from automation.github.github_client import GitHubWriteClient
from automation.github.github_client import HttpGitHubWriteClient

_ALLOWED_RESULT_STATUSES = {
    "success",
    "not_found",
    "auth_failure",
    "api_failure",
    "unsupported_query",
}


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


def _normalize_error_payload(
    *,
    kind: str,
    message: str,
    status_code: int | None = None,
) -> dict[str, Any]:
    return {
        "kind": _normalize_text(kind, default="api_failure"),
        "message": _normalize_text(message, default="unknown github write error"),
        "status_code": status_code,
    }


def _build_result(
    *,
    operation: str,
    status: str,
    data: Mapping[str, Any] | None = None,
    error: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_status = _normalize_text(status, default="api_failure")
    if normalized_status not in _ALLOWED_RESULT_STATUSES:
        normalized_status = "api_failure"
    return {
        "operation": _normalize_text(operation, default="unknown_operation"),
        "mode": "write_limited",
        "write_actions_allowed": True,
        "status": normalized_status,
        "ok": normalized_status == "success",
        "data": dict(data or {}),
        "error": dict(error or {}),
    }


def _normalize_pull_request_payload(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    head = payload.get("head") if isinstance(payload.get("head"), Mapping) else {}
    base = payload.get("base") if isinstance(payload.get("base"), Mapping) else {}
    return {
        "number": _as_optional_int(payload.get("number")),
        "html_url": _normalize_text(payload.get("html_url"), default=""),
        "state": _normalize_text(payload.get("state"), default=""),
        "draft": bool(payload.get("draft", False)),
        "title": _normalize_text(payload.get("title"), default=""),
        "head_ref": _normalize_text(head.get("ref"), default=""),
        "base_ref": _normalize_text(base.get("ref"), default=""),
    }


@dataclass
class GitHubWriteBackend:
    client: GitHubWriteClient

    def create_draft_pr(
        self,
        *,
        repo: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str,
    ) -> dict[str, Any]:
        repository = _normalize_text(repo, default="")
        normalized_title = _normalize_text(title, default="")
        normalized_body = _normalize_text(body, default="")
        head = _normalize_text(head_branch, default="")
        base = _normalize_text(base_branch, default="")

        if not repository or not head or not base or not normalized_title:
            return _build_result(
                operation="create_draft_pr",
                status="unsupported_query",
                data={
                    "repository": repository or None,
                    "head_branch": head or None,
                    "base_branch": base or None,
                    "title_preview": normalized_title or None,
                },
                error=_normalize_error_payload(
                    kind="unsupported_query",
                    message="repo, title, head_branch, and base_branch are required",
                ),
            )

        try:
            created = self.client.create_pull_request(
                repository,
                title=normalized_title,
                body=normalized_body,
                head_branch=head,
                base_branch=base,
                draft=True,
            )
        except GitHubClientError as exc:
            return _build_result(
                operation="create_draft_pr",
                status=exc.kind,
                data={
                    "repository": repository,
                    "head_branch": head,
                    "base_branch": base,
                    "title_preview": normalized_title,
                },
                error=_normalize_error_payload(
                    kind=exc.kind,
                    message=str(exc),
                    status_code=exc.status_code,
                ),
            )

        normalized_pr = _normalize_pull_request_payload(created)
        if not normalized_pr["draft"]:
            return _build_result(
                operation="create_draft_pr",
                status="api_failure",
                data={
                    "repository": repository,
                    "head_branch": head,
                    "base_branch": base,
                    "pr": normalized_pr,
                },
                error=_normalize_error_payload(
                    kind="api_failure",
                    message="draft PR creation not confirmed by GitHub response",
                ),
            )

        if normalized_pr["number"] is None or not normalized_pr["html_url"]:
            return _build_result(
                operation="create_draft_pr",
                status="api_failure",
                data={
                    "repository": repository,
                    "head_branch": head,
                    "base_branch": base,
                    "pr": normalized_pr,
                },
                error=_normalize_error_payload(
                    kind="api_failure",
                    message="created PR response missing identity fields",
                ),
            )

        return _build_result(
            operation="create_draft_pr",
            status="success",
            data={
                "repository": repository,
                "head_branch": head,
                "base_branch": base,
                "pr": normalized_pr,
            },
        )

    def merge_pull_request(
        self,
        *,
        repo: str,
        pr_number: int,
        expected_head_sha: str | None = None,
        merge_method: str = "merge",
    ) -> dict[str, Any]:
        repository = _normalize_text(repo, default="")
        normalized_pr_number = _as_optional_int(pr_number)
        normalized_expected_sha = _normalize_text(expected_head_sha, default="")
        normalized_merge_method = _normalize_text(merge_method, default="merge")

        if not repository or normalized_pr_number is None or normalized_pr_number <= 0:
            return _build_result(
                operation="merge_pull_request",
                status="unsupported_query",
                data={
                    "repository": repository or None,
                    "pr_number": normalized_pr_number,
                    "expected_head_sha": normalized_expected_sha or None,
                    "merge_method": normalized_merge_method or None,
                },
                error=_normalize_error_payload(
                    kind="unsupported_query",
                    message="repo and positive pr_number are required",
                ),
            )

        try:
            merged_payload = self.client.merge_pull_request(
                repository,
                pr_number=normalized_pr_number,
                expected_head_sha=normalized_expected_sha or None,
                merge_method=normalized_merge_method,
            )
        except GitHubClientError as exc:
            return _build_result(
                operation="merge_pull_request",
                status=exc.kind,
                data={
                    "repository": repository,
                    "pr_number": normalized_pr_number,
                    "expected_head_sha": normalized_expected_sha or None,
                    "merge_method": normalized_merge_method,
                },
                error=_normalize_error_payload(
                    kind=exc.kind,
                    message=str(exc),
                    status_code=exc.status_code,
                ),
            )

        merged = bool(merged_payload.get("merged", False))
        merge_sha = _normalize_text(merged_payload.get("sha"), default="")
        merge_message = _normalize_text(merged_payload.get("message"), default="")
        if not merged or not merge_sha:
            return _build_result(
                operation="merge_pull_request",
                status="api_failure",
                data={
                    "repository": repository,
                    "pr_number": normalized_pr_number,
                    "merged": merged,
                    "merge_commit_sha": merge_sha or None,
                    "message": merge_message or None,
                },
                error=_normalize_error_payload(
                    kind="api_failure",
                    message=merge_message or "GitHub did not confirm successful merge",
                ),
            )

        return _build_result(
            operation="merge_pull_request",
            status="success",
            data={
                "repository": repository,
                "pr_number": normalized_pr_number,
                "merged": True,
                "merge_commit_sha": merge_sha,
                "message": merge_message or None,
            },
        )

    def update_existing_pr(
        self,
        *,
        repo: str,
        pr_number: int,
        title: str | None = None,
        body: str | None = None,
        base_branch: str | None = None,
        current_pr: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        repository = _normalize_text(repo, default="")
        normalized_pr_number = _as_optional_int(pr_number)
        title_requested = title is not None
        body_requested = body is not None
        base_requested = base_branch is not None
        normalized_title = _normalize_text(title, default="") if title_requested else ""
        normalized_body = _normalize_text(body, default="") if body_requested else ""
        normalized_base = _normalize_text(base_branch, default="") if base_requested else ""
        has_update = title_requested or body_requested or base_requested

        if not repository or normalized_pr_number is None or normalized_pr_number <= 0 or not has_update:
            return _build_result(
                operation="update_existing_pr",
                status="unsupported_query",
                data={
                    "repository": repository or None,
                    "pr_number": normalized_pr_number,
                    "title_preview": normalized_title or None,
                    "body_preview": normalized_body or None,
                    "base_branch": normalized_base or None,
                },
                error=_normalize_error_payload(
                    kind="unsupported_query",
                    message="repo, positive pr_number, and at least one update field are required",
                ),
            )

        if isinstance(current_pr, Mapping):
            normalized_current = _normalize_pull_request_payload(current_pr)
            same_title = (not title_requested) or normalized_current.get("title") == normalized_title
            same_base = (not base_requested) or normalized_current.get("base_ref") == normalized_base
            current_body = _normalize_text(current_pr.get("body"), default="")
            same_body = (not body_requested) or current_body == normalized_body
            if same_title and same_base and same_body:
                return _build_result(
                    operation="update_existing_pr",
                    status="success",
                    data={
                        "repository": repository,
                        "pr_number": normalized_pr_number,
                        "requested_update": {
                            "title": normalized_title if title_requested else None,
                            "body": normalized_body if body_requested else None,
                            "base_branch": normalized_base if base_requested else None,
                        },
                        "pr": normalized_current,
                        "updated": False,
                        "classification": "already_applied",
                    },
                )

        try:
            updated = self.client.update_pull_request(
                repository,
                pr_number=normalized_pr_number,
                title=normalized_title if title_requested else None,
                body=normalized_body if body_requested else None,
                base_branch=normalized_base if base_requested else None,
            )
        except GitHubClientError as exc:
            return _build_result(
                operation="update_existing_pr",
                status=exc.kind,
                data={
                    "repository": repository,
                    "pr_number": normalized_pr_number,
                    "title_preview": normalized_title or None,
                    "body_preview": normalized_body or None,
                    "base_branch": normalized_base or None,
                },
                error=_normalize_error_payload(
                    kind=exc.kind,
                    message=str(exc),
                    status_code=exc.status_code,
                ),
            )

        normalized_pr = _normalize_pull_request_payload(updated)
        if normalized_pr["number"] is None or not normalized_pr["html_url"]:
            return _build_result(
                operation="update_existing_pr",
                status="api_failure",
                data={
                    "repository": repository,
                    "pr_number": normalized_pr_number,
                    "pr": normalized_pr,
                },
                error=_normalize_error_payload(
                    kind="api_failure",
                    message="updated PR response missing identity fields",
                ),
            )

        return _build_result(
            operation="update_existing_pr",
            status="success",
            data={
                "repository": repository,
                "pr_number": normalized_pr_number,
                "requested_update": {
                    "title": normalized_title if title_requested else None,
                    "body": normalized_body if body_requested else None,
                    "base_branch": normalized_base if base_requested else None,
                },
                "pr": normalized_pr,
                "updated": True,
                "classification": "applied",
            },
        )


def build_github_write_backend(
    *,
    client: GitHubWriteClient | None = None,
) -> GitHubWriteBackend:
    resolved_client = client if client is not None else HttpGitHubWriteClient()
    return GitHubWriteBackend(client=resolved_client)
