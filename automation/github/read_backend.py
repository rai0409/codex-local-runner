from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Mapping

from automation.github.github_client import GitHubClientError
from automation.github.github_client import GitHubReadClient
from automation.github.github_client import HttpGitHubReadClient

_ALLOWED_RESULT_STATUSES = {
    "success",
    "empty",
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


def _as_non_negative_int(value: Any, *, default: int = 0) -> int:
    maybe = _as_optional_int(value)
    if maybe is None:
        return default
    return max(0, maybe)


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


def _normalize_error_payload(
    *,
    kind: str,
    message: str,
    status_code: int | None = None,
) -> dict[str, Any]:
    return {
        "kind": _normalize_text(kind, default="api_failure"),
        "message": _normalize_text(message, default="unknown github read error"),
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
        "mode": "read_only",
        "write_actions_allowed": False,
        "status": normalized_status,
        "ok": normalized_status in {"success", "empty"},
        "data": dict(data or {}),
        "error": dict(error or {}),
    }


def _first_non_empty(*values: Any) -> str | None:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _normalize_pr_payload(pr: Mapping[str, Any]) -> dict[str, Any]:
    head = pr.get("head") if isinstance(pr.get("head"), Mapping) else {}
    base = pr.get("base") if isinstance(pr.get("base"), Mapping) else {}
    return {
        "number": _as_optional_int(pr.get("number")),
        "title": _normalize_text(pr.get("title"), default=""),
        "state": _normalize_text(pr.get("state"), default=""),
        "draft": bool(pr.get("draft", False)),
        "head_ref": _normalize_text(head.get("ref"), default=""),
        "head_sha": _normalize_text(head.get("sha"), default=""),
        "base_ref": _normalize_text(base.get("ref"), default=""),
        "html_url": _normalize_text(pr.get("html_url"), default=""),
    }


def _normalize_compare_status(value: Any) -> str:
    text = _normalize_text(value, default="unknown").lower()
    if text in {"identical", "ahead", "behind", "diverged"}:
        return text
    return "unknown"


@dataclass
class GitHubReadBackend:
    client: GitHubReadClient

    def get_default_branch(self, repo: str) -> dict[str, Any]:
        repo_name = _normalize_text(repo)
        if not repo_name:
            return _build_result(
                operation="get_default_branch",
                status="unsupported_query",
                error=_normalize_error_payload(
                    kind="unsupported_query",
                    message="repo is required",
                ),
            )
        try:
            payload = self.client.get_repo(repo_name)
        except GitHubClientError as exc:
            return _build_result(
                operation="get_default_branch",
                status=exc.kind,
                error=_normalize_error_payload(
                    kind=exc.kind,
                    message=str(exc),
                    status_code=exc.status_code,
                ),
                data={"repository": repo_name},
            )
        default_branch = _normalize_text(payload.get("default_branch"), default="")
        if not default_branch:
            return _build_result(
                operation="get_default_branch",
                status="empty",
                data={
                    "repository": repo_name,
                    "default_branch": None,
                },
            )
        return _build_result(
            operation="get_default_branch",
            status="success",
            data={
                "repository": repo_name,
                "default_branch": default_branch,
            },
        )

    def get_branch_head(self, repo: str, branch: str) -> dict[str, Any]:
        repo_name = _normalize_text(repo)
        branch_name = _normalize_text(branch)
        if not repo_name or not branch_name:
            return _build_result(
                operation="get_branch_head",
                status="unsupported_query",
                error=_normalize_error_payload(
                    kind="unsupported_query",
                    message="repo and branch are required",
                ),
            )
        try:
            payload = self.client.get_branch(repo_name, branch_name)
        except GitHubClientError as exc:
            data = {
                "repository": repo_name,
                "branch": branch_name,
                "exists": False if exc.kind == "not_found" else None,
                "head_sha": None,
            }
            return _build_result(
                operation="get_branch_head",
                status=exc.kind,
                error=_normalize_error_payload(
                    kind=exc.kind,
                    message=str(exc),
                    status_code=exc.status_code,
                ),
                data=data,
            )
        commit = payload.get("commit") if isinstance(payload.get("commit"), Mapping) else {}
        head_sha = _normalize_text(commit.get("sha"), default="")
        if not head_sha:
            return _build_result(
                operation="get_branch_head",
                status="empty",
                data={
                    "repository": repo_name,
                    "branch": branch_name,
                    "exists": True,
                    "head_sha": None,
                },
            )
        return _build_result(
            operation="get_branch_head",
            status="success",
            data={
                "repository": repo_name,
                "branch": branch_name,
                "exists": True,
                "head_sha": head_sha,
            },
        )

    def compare_refs(self, repo: str, base_ref: str, head_ref: str) -> dict[str, Any]:
        repo_name = _normalize_text(repo)
        base = _normalize_text(base_ref)
        head = _normalize_text(head_ref)
        if not repo_name or not base or not head:
            return _build_result(
                operation="compare_refs",
                status="unsupported_query",
                error=_normalize_error_payload(
                    kind="unsupported_query",
                    message="repo, base_ref, and head_ref are required",
                ),
            )
        try:
            payload = self.client.compare_refs(repo_name, base, head)
        except GitHubClientError as exc:
            return _build_result(
                operation="compare_refs",
                status=exc.kind,
                error=_normalize_error_payload(
                    kind=exc.kind,
                    message=str(exc),
                    status_code=exc.status_code,
                ),
                data={
                    "repository": repo_name,
                    "base_ref": base,
                    "head_ref": head,
                    "comparison_status": "unknown",
                    "changed_files": [],
                },
            )

        raw_files = payload.get("files")
        file_names: list[str] = []
        if isinstance(raw_files, list):
            file_names = _normalize_string_list(
                [item.get("filename") for item in raw_files if isinstance(item, Mapping)],
                sort_items=True,
            )

        data = {
            "repository": repo_name,
            "base_ref": base,
            "head_ref": head,
            "comparison_status": _normalize_compare_status(payload.get("status")),
            "ahead_by": _as_non_negative_int(payload.get("ahead_by"), default=0),
            "behind_by": _as_non_negative_int(payload.get("behind_by"), default=0),
            "total_commits": _as_non_negative_int(payload.get("total_commits"), default=0),
            "changed_files": file_names,
        }
        if (
            data["comparison_status"] == "unknown"
            and not file_names
            and data["total_commits"] == 0
            and data["ahead_by"] == 0
            and data["behind_by"] == 0
        ):
            return _build_result(operation="compare_refs", status="empty", data=data)
        return _build_result(operation="compare_refs", status="success", data=data)

    def find_open_pr(
        self,
        repo: str,
        *,
        head_branch: str | None = None,
        base_branch: str | None = None,
    ) -> dict[str, Any]:
        repo_name = _normalize_text(repo)
        head = _normalize_text(head_branch, default="")
        base = _normalize_text(base_branch, default="")
        if not repo_name:
            return _build_result(
                operation="find_open_pr",
                status="unsupported_query",
                error=_normalize_error_payload(
                    kind="unsupported_query",
                    message="repo is required",
                ),
            )
        if not head and not base:
            return _build_result(
                operation="find_open_pr",
                status="unsupported_query",
                error=_normalize_error_payload(
                    kind="unsupported_query",
                    message="head_branch or base_branch is required",
                ),
                data={
                    "repository": repo_name,
                    "query": {"head_branch": None, "base_branch": None},
                    "matched": False,
                    "match_count": 0,
                    "pr": None,
                },
            )
        try:
            pull_requests = self.client.list_open_pull_requests(
                repo_name,
                head_branch=head or None,
                base_branch=base or None,
            )
        except GitHubClientError as exc:
            return _build_result(
                operation="find_open_pr",
                status=exc.kind,
                error=_normalize_error_payload(
                    kind=exc.kind,
                    message=str(exc),
                    status_code=exc.status_code,
                ),
                data={
                    "repository": repo_name,
                    "query": {
                        "head_branch": head or None,
                        "base_branch": base or None,
                    },
                    "matched": False,
                    "match_count": 0,
                    "pr": None,
                },
            )

        normalized_prs = [
            _normalize_pr_payload(item)
            for item in pull_requests
            if isinstance(item, Mapping)
        ]
        normalized_prs = [
            item for item in normalized_prs if item.get("number") is not None
        ]
        normalized_prs = sorted(
            normalized_prs,
            key=lambda item: (int(item.get("number") or 0), _normalize_text(item.get("head_ref"))),
        )

        selected = normalized_prs[0] if normalized_prs else None
        data = {
            "repository": repo_name,
            "query": {
                "head_branch": head or None,
                "base_branch": base or None,
            },
            "matched": bool(selected),
            "match_count": len(normalized_prs),
            "pr": selected,
        }
        return _build_result(
            operation="find_open_pr",
            status="success" if selected else "empty",
            data=data,
        )

    def get_pr_status_summary(
        self,
        repo: str,
        *,
        pr_number: int | None = None,
        commit_sha: str | None = None,
    ) -> dict[str, Any]:
        repo_name = _normalize_text(repo)
        commit = _normalize_text(commit_sha, default="")
        normalized_pr_number = _as_optional_int(pr_number)
        if not repo_name:
            return _build_result(
                operation="get_pr_status_summary",
                status="unsupported_query",
                error=_normalize_error_payload(
                    kind="unsupported_query",
                    message="repo is required",
                ),
            )
        if normalized_pr_number is None and not commit:
            return _build_result(
                operation="get_pr_status_summary",
                status="unsupported_query",
                error=_normalize_error_payload(
                    kind="unsupported_query",
                    message="pr_number or commit_sha is required",
                ),
                data={
                    "repository": repo_name,
                    "pr_number": None,
                    "commit_sha": None,
                },
            )

        if normalized_pr_number is not None and not commit:
            try:
                pr_payload = self.client.get_pull_request(repo_name, normalized_pr_number)
            except GitHubClientError as exc:
                return _build_result(
                    operation="get_pr_status_summary",
                    status=exc.kind,
                    error=_normalize_error_payload(
                        kind=exc.kind,
                        message=str(exc),
                        status_code=exc.status_code,
                    ),
                    data={
                        "repository": repo_name,
                        "pr_number": normalized_pr_number,
                        "commit_sha": None,
                    },
                )
            head = pr_payload.get("head") if isinstance(pr_payload.get("head"), Mapping) else {}
            base = pr_payload.get("base") if isinstance(pr_payload.get("base"), Mapping) else {}
            commit = _normalize_text(head.get("sha"), default="")
            if not commit:
                return _build_result(
                    operation="get_pr_status_summary",
                    status="empty",
                    data={
                        "repository": repo_name,
                        "pr_number": normalized_pr_number,
                        "commit_sha": None,
                    },
                )
            pr_state = _normalize_text(pr_payload.get("state"), default="")
            pr_draft = bool(pr_payload.get("draft", False))
            pr_merged = bool(pr_payload.get("merged", False))
            mergeable_state = _normalize_text(pr_payload.get("mergeable_state"), default="")
            pr_head_ref = _normalize_text(head.get("ref"), default="")
            pr_base_ref = _normalize_text(base.get("ref"), default="")
        else:
            pr_state = ""
            pr_draft = False
            pr_merged = False
            mergeable_state = ""
            pr_head_ref = ""
            pr_base_ref = ""

        try:
            status_payload = self.client.get_commit_status(repo_name, commit)
            checks_payload = self.client.list_check_runs(repo_name, commit)
        except GitHubClientError as exc:
            return _build_result(
                operation="get_pr_status_summary",
                status=exc.kind,
                error=_normalize_error_payload(
                    kind=exc.kind,
                    message=str(exc),
                    status_code=exc.status_code,
                ),
                data={
                    "repository": repo_name,
                    "pr_number": normalized_pr_number,
                    "commit_sha": commit or None,
                },
            )

        status_state = _normalize_text(status_payload.get("state"), default="unknown").lower()
        if status_state not in {"success", "failure", "pending", "error"}:
            status_state = "unknown"

        status_contexts = status_payload.get("statuses")
        status_items = status_contexts if isinstance(status_contexts, list) else []
        status_counts = {
            "total": 0,
            "success": 0,
            "failure": 0,
            "pending": 0,
            "error": 0,
        }
        for item in status_items:
            if not isinstance(item, Mapping):
                continue
            state = _normalize_text(item.get("state"), default="").lower()
            if state not in {"success", "failure", "pending", "error"}:
                continue
            status_counts["total"] += 1
            status_counts[state] += 1

        check_runs = checks_payload.get("check_runs") if isinstance(checks_payload.get("check_runs"), list) else []
        check_counts = {
            "total": 0,
            "completed": 0,
            "success": 0,
            "failure": 0,
            "pending": 0,
        }
        for run in check_runs:
            if not isinstance(run, Mapping):
                continue
            check_counts["total"] += 1
            status = _normalize_text(run.get("status"), default="").lower()
            conclusion = _normalize_text(run.get("conclusion"), default="").lower()
            if status == "completed":
                check_counts["completed"] += 1
                if conclusion in {"success", "neutral", "skipped"}:
                    check_counts["success"] += 1
                else:
                    check_counts["failure"] += 1
            else:
                check_counts["pending"] += 1

        checks_state = "unknown"
        if status_state in {"failure", "error"}:
            checks_state = "failing"
        elif status_state == "pending":
            checks_state = "pending"
        elif check_counts["failure"] > 0:
            checks_state = "failing"
        elif check_counts["pending"] > 0:
            checks_state = "pending"
        elif status_state == "success" or check_counts["success"] > 0:
            checks_state = "passing"

        data = {
            "repository": repo_name,
            "pr_number": normalized_pr_number,
            "commit_sha": commit or None,
            "pr_state": pr_state or None,
            "pr_draft": pr_draft if normalized_pr_number is not None else None,
            "pr_merged": pr_merged if normalized_pr_number is not None else None,
            "mergeable_state": mergeable_state or None,
            "pr_head_ref": pr_head_ref or None,
            "pr_base_ref": pr_base_ref or None,
            "status_state": status_state,
            "status_contexts": status_counts,
            "check_runs": check_counts,
            "checks_state": checks_state,
        }
        if checks_state == "unknown" and status_counts["total"] == 0 and check_counts["total"] == 0:
            return _build_result(
                operation="get_pr_status_summary",
                status="empty",
                data=data,
            )
        return _build_result(
            operation="get_pr_status_summary",
            status="success",
            data=data,
        )


def build_github_read_backend(
    *,
    client: GitHubReadClient | None = None,
) -> GitHubReadBackend:
    resolved_client = client if client is not None else HttpGitHubReadClient()
    return GitHubReadBackend(client=resolved_client)
