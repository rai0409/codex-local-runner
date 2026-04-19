from __future__ import annotations

import json
import os
from typing import Any
from typing import Mapping
from typing import Protocol
from urllib import error as url_error
from urllib import parse
from urllib import request


GITHUB_API_BASE_URL_ENV_VAR = "CODEX_GITHUB_API_BASE_URL"
GITHUB_TOKEN_ENV_VAR = "CODEX_GITHUB_TOKEN"
FALLBACK_GITHUB_TOKEN_ENV_VAR = "GITHUB_TOKEN"

_DEFAULT_GITHUB_API_BASE_URL = "https://api.github.com"


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


class GitHubClientError(RuntimeError):
    def __init__(
        self,
        *,
        kind: str,
        message: str,
        status_code: int | None = None,
        response_body: str = "",
    ) -> None:
        super().__init__(message)
        self.kind = _normalize_text(kind, default="api_failure")
        self.status_code = status_code
        self.response_body = _normalize_text(response_body, default="")


class GitHubReadClient(Protocol):
    def get_repo(self, repo: str) -> Mapping[str, Any]:
        ...

    def get_branch(self, repo: str, branch: str) -> Mapping[str, Any]:
        ...

    def compare_refs(self, repo: str, base_ref: str, head_ref: str) -> Mapping[str, Any]:
        ...

    def list_open_pull_requests(
        self,
        repo: str,
        *,
        head_branch: str | None = None,
        base_branch: str | None = None,
    ) -> list[Mapping[str, Any]]:
        ...

    def get_pull_request(self, repo: str, pr_number: int) -> Mapping[str, Any]:
        ...

    def get_commit_status(self, repo: str, commit_sha: str) -> Mapping[str, Any]:
        ...

    def list_check_runs(self, repo: str, commit_sha: str) -> Mapping[str, Any]:
        ...


class GitHubWriteClient(Protocol):
    def create_pull_request(
        self,
        repo: str,
        *,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str,
        draft: bool,
    ) -> Mapping[str, Any]:
        ...

    def merge_pull_request(
        self,
        repo: str,
        *,
        pr_number: int,
        expected_head_sha: str | None = None,
        merge_method: str = "merge",
    ) -> Mapping[str, Any]:
        ...

    def update_pull_request(
        self,
        repo: str,
        *,
        pr_number: int,
        title: str | None = None,
        body: str | None = None,
        base_branch: str | None = None,
    ) -> Mapping[str, Any]:
        ...


class HttpGitHubReadClient:
    def __init__(
        self,
        *,
        token: str | None = None,
        base_url: str | None = None,
    ) -> None:
        resolved_token = _normalize_text(
            token,
            default=_normalize_text(
                os.getenv(GITHUB_TOKEN_ENV_VAR),
                default=_normalize_text(os.getenv(FALLBACK_GITHUB_TOKEN_ENV_VAR)),
            ),
        )
        self._token = resolved_token
        self._base_url = _normalize_text(
            base_url,
            default=_normalize_text(
                os.getenv(GITHUB_API_BASE_URL_ENV_VAR),
                default=_DEFAULT_GITHUB_API_BASE_URL,
            ),
        ).rstrip("/")

    def _request_json(
        self,
        *,
        path: str,
        query: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any] | list[Any]:
        if not self._token:
            raise GitHubClientError(
                kind="auth_failure",
                message=(
                    f"missing GitHub token: set {GITHUB_TOKEN_ENV_VAR} "
                    f"or {FALLBACK_GITHUB_TOKEN_ENV_VAR}"
                ),
            )

        normalized_path = "/" + _normalize_text(path, default="").lstrip("/")
        url = f"{self._base_url}{normalized_path}"

        if isinstance(query, Mapping):
            filtered: dict[str, str] = {}
            for key, value in query.items():
                if value is None:
                    continue
                text = _normalize_text(value)
                if text:
                    filtered[str(key)] = text
            if filtered:
                url = f"{url}?{parse.urlencode(filtered)}"

        req = request.Request(
            url=url,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "codex-local-runner-read-only-client",
            },
            method="GET",
        )
        try:
            with request.urlopen(req) as response:
                body = response.read().decode("utf-8", errors="replace")
                payload = json.loads(body) if body else {}
                if isinstance(payload, (dict, list)):
                    return payload
                raise GitHubClientError(
                    kind="api_failure",
                    message="unexpected GitHub response shape",
                    status_code=int(getattr(response, "status", 0) or 0),
                    response_body=body,
                )
        except url_error.HTTPError as exc:
            status_code = int(getattr(exc, "code", 0) or 0)
            body = exc.read().decode("utf-8", errors="replace") if exc.fp is not None else ""
            if status_code in {401, 403}:
                kind = "auth_failure"
            elif status_code == 404:
                kind = "not_found"
            else:
                kind = "api_failure"
            raise GitHubClientError(
                kind=kind,
                message=f"github api request failed: status={status_code}",
                status_code=status_code,
                response_body=body,
            ) from exc
        except url_error.URLError as exc:
            raise GitHubClientError(
                kind="api_failure",
                message=f"github api request failed: {exc}",
            ) from exc
        except json.JSONDecodeError as exc:
            raise GitHubClientError(
                kind="api_failure",
                message=f"github api returned invalid json: {exc}",
            ) from exc

    def get_repo(self, repo: str) -> Mapping[str, Any]:
        payload = self._request_json(path=f"/repos/{repo}")
        return payload if isinstance(payload, Mapping) else {}

    def get_branch(self, repo: str, branch: str) -> Mapping[str, Any]:
        payload = self._request_json(path=f"/repos/{repo}/branches/{branch}")
        return payload if isinstance(payload, Mapping) else {}

    def compare_refs(self, repo: str, base_ref: str, head_ref: str) -> Mapping[str, Any]:
        payload = self._request_json(path=f"/repos/{repo}/compare/{base_ref}...{head_ref}")
        return payload if isinstance(payload, Mapping) else {}

    def list_open_pull_requests(
        self,
        repo: str,
        *,
        head_branch: str | None = None,
        base_branch: str | None = None,
    ) -> list[Mapping[str, Any]]:
        payload = self._request_json(
            path=f"/repos/{repo}/pulls",
            query={
                "state": "open",
                "head": head_branch,
                "base": base_branch,
            },
        )
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, Mapping)]
        return []

    def get_pull_request(self, repo: str, pr_number: int) -> Mapping[str, Any]:
        payload = self._request_json(path=f"/repos/{repo}/pulls/{pr_number}")
        return payload if isinstance(payload, Mapping) else {}

    def get_commit_status(self, repo: str, commit_sha: str) -> Mapping[str, Any]:
        payload = self._request_json(path=f"/repos/{repo}/commits/{commit_sha}/status")
        return payload if isinstance(payload, Mapping) else {}

    def list_check_runs(self, repo: str, commit_sha: str) -> Mapping[str, Any]:
        payload = self._request_json(path=f"/repos/{repo}/commits/{commit_sha}/check-runs")
        return payload if isinstance(payload, Mapping) else {}


class HttpGitHubWriteClient:
    def __init__(
        self,
        *,
        token: str | None = None,
        base_url: str | None = None,
    ) -> None:
        resolved_token = _normalize_text(
            token,
            default=_normalize_text(
                os.getenv(GITHUB_TOKEN_ENV_VAR),
                default=_normalize_text(os.getenv(FALLBACK_GITHUB_TOKEN_ENV_VAR)),
            ),
        )
        self._token = resolved_token
        self._base_url = _normalize_text(
            base_url,
            default=_normalize_text(
                os.getenv(GITHUB_API_BASE_URL_ENV_VAR),
                default=_DEFAULT_GITHUB_API_BASE_URL,
            ),
        ).rstrip("/")

    def _request_json(
        self,
        *,
        path: str,
        method: str,
        body: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any] | list[Any]:
        if not self._token:
            raise GitHubClientError(
                kind="auth_failure",
                message=(
                    f"missing GitHub token: set {GITHUB_TOKEN_ENV_VAR} "
                    f"or {FALLBACK_GITHUB_TOKEN_ENV_VAR}"
                ),
            )

        normalized_path = "/" + _normalize_text(path, default="").lstrip("/")
        url = f"{self._base_url}{normalized_path}"

        request_data: bytes | None = None
        if body is not None:
            request_data = json.dumps(dict(body), ensure_ascii=False).encode("utf-8")

        req = request.Request(
            url=url,
            data=request_data,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json; charset=utf-8",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "codex-local-runner-write-client",
            },
            method=method,
        )
        try:
            with request.urlopen(req) as response:
                body_text = response.read().decode("utf-8", errors="replace")
                payload = json.loads(body_text) if body_text else {}
                if isinstance(payload, (dict, list)):
                    return payload
                raise GitHubClientError(
                    kind="api_failure",
                    message="unexpected GitHub response shape",
                    status_code=int(getattr(response, "status", 0) or 0),
                    response_body=body_text,
                )
        except url_error.HTTPError as exc:
            status_code = int(getattr(exc, "code", 0) or 0)
            body_text = exc.read().decode("utf-8", errors="replace") if exc.fp is not None else ""
            if status_code in {401, 403}:
                kind = "auth_failure"
            elif status_code == 404:
                kind = "not_found"
            else:
                kind = "api_failure"
            raise GitHubClientError(
                kind=kind,
                message=f"github api request failed: status={status_code}",
                status_code=status_code,
                response_body=body_text,
            ) from exc
        except url_error.URLError as exc:
            raise GitHubClientError(
                kind="api_failure",
                message=f"github api request failed: {exc}",
            ) from exc
        except json.JSONDecodeError as exc:
            raise GitHubClientError(
                kind="api_failure",
                message=f"github api returned invalid json: {exc}",
            ) from exc

    def create_pull_request(
        self,
        repo: str,
        *,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str,
        draft: bool,
    ) -> Mapping[str, Any]:
        if not draft:
            raise GitHubClientError(
                kind="unsupported_query",
                message="write client only supports draft pull request creation",
            )

        payload = self._request_json(
            path=f"/repos/{repo}/pulls",
            method="POST",
            body={
                "title": title,
                "body": body,
                "head": head_branch,
                "base": base_branch,
                "draft": True,
            },
        )
        return payload if isinstance(payload, Mapping) else {}

    def merge_pull_request(
        self,
        repo: str,
        *,
        pr_number: int,
        expected_head_sha: str | None = None,
        merge_method: str = "merge",
    ) -> Mapping[str, Any]:
        normalized_method = _normalize_text(merge_method, default="merge")
        if normalized_method not in {"merge", "squash", "rebase"}:
            raise GitHubClientError(
                kind="unsupported_query",
                message=f"unsupported merge_method: {merge_method}",
            )
        payload_body: dict[str, Any] = {"merge_method": normalized_method}
        normalized_sha = _normalize_text(expected_head_sha, default="")
        if normalized_sha:
            payload_body["sha"] = normalized_sha

        payload = self._request_json(
            path=f"/repos/{repo}/pulls/{int(pr_number)}/merge",
            method="PUT",
            body=payload_body,
        )
        return payload if isinstance(payload, Mapping) else {}

    def update_pull_request(
        self,
        repo: str,
        *,
        pr_number: int,
        title: str | None = None,
        body: str | None = None,
        base_branch: str | None = None,
    ) -> Mapping[str, Any]:
        payload_body: dict[str, Any] = {}
        has_title = title is not None
        has_body = body is not None
        has_base = base_branch is not None
        normalized_title = _normalize_text(title, default="") if has_title else ""
        normalized_body = _normalize_text(body, default="") if has_body else ""
        normalized_base = _normalize_text(base_branch, default="") if has_base else ""
        if has_title:
            payload_body["title"] = normalized_title
        if has_body:
            payload_body["body"] = normalized_body
        if has_base:
            if not normalized_base:
                raise GitHubClientError(
                    kind="unsupported_query",
                    message="base_branch cannot be empty when explicitly provided",
                )
            payload_body["base"] = normalized_base
        if not payload_body:
            raise GitHubClientError(
                kind="unsupported_query",
                message="at least one of title, body, or base_branch is required",
            )

        payload = self._request_json(
            path=f"/repos/{repo}/pulls/{int(pr_number)}",
            method="PATCH",
            body=payload_body,
        )
        return payload if isinstance(payload, Mapping) else {}
