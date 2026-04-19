from __future__ import annotations

import unittest

from automation.github.github_client import GitHubClientError
from automation.github.write_backend import GitHubWriteBackend


class _FakeGitHubWriteClient:
    def __init__(self) -> None:
        self.payload: dict[str, object] = {
            "number": 42,
            "html_url": "https://example.test/pr/42",
            "state": "open",
            "draft": True,
            "title": "Draft PR",
            "head": {"ref": "feature/test"},
            "base": {"ref": "main"},
        }
        self.error: GitHubClientError | None = None
        self.merge_payload: dict[str, object] = {
            "sha": "c" * 40,
            "merged": True,
            "message": "Pull Request successfully merged",
        }
        self.merge_error: GitHubClientError | None = None
        self.update_payload: dict[str, object] = {
            "number": 42,
            "html_url": "https://example.test/pr/42",
            "state": "open",
            "draft": True,
            "title": "Updated title",
            "head": {"ref": "feature/test"},
            "base": {"ref": "main"},
        }
        self.update_error: GitHubClientError | None = None
        self.calls: list[dict[str, object]] = []
        self.merge_calls: list[dict[str, object]] = []
        self.update_calls: list[dict[str, object]] = []

    def create_pull_request(
        self,
        repo: str,
        *,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str,
        draft: bool,
    ):
        self.calls.append(
            {
                "repo": repo,
                "title": title,
                "body": body,
                "head_branch": head_branch,
                "base_branch": base_branch,
                "draft": draft,
            }
        )
        if self.error is not None:
            raise self.error
        return dict(self.payload)

    def merge_pull_request(
        self,
        repo: str,
        *,
        pr_number: int,
        expected_head_sha: str | None = None,
        merge_method: str = "merge",
    ):
        self.merge_calls.append(
            {
                "repo": repo,
                "pr_number": pr_number,
                "expected_head_sha": expected_head_sha,
                "merge_method": merge_method,
            }
        )
        if self.merge_error is not None:
            raise self.merge_error
        return dict(self.merge_payload)

    def update_pull_request(
        self,
        repo: str,
        *,
        pr_number: int,
        title: str | None = None,
        body: str | None = None,
        base_branch: str | None = None,
    ):
        self.update_calls.append(
            {
                "repo": repo,
                "pr_number": pr_number,
                "title": title,
                "body": body,
                "base_branch": base_branch,
            }
        )
        if self.update_error is not None:
            raise self.update_error
        return dict(self.update_payload)


class GitHubWriteBackendTests(unittest.TestCase):
    def test_create_draft_pr_success(self) -> None:
        client = _FakeGitHubWriteClient()
        backend = GitHubWriteBackend(client=client)

        payload = backend.create_draft_pr(
            repo="rai0409/codex-local-runner",
            title="Draft title",
            body="Draft body",
            head_branch="feature/test",
            base_branch="main",
        )

        self.assertEqual(payload["status"], "success")
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"]["pr"]["number"], 42)
        self.assertEqual(payload["data"]["pr"]["html_url"], "https://example.test/pr/42")
        self.assertEqual(client.calls[0]["draft"], True)

    def test_missing_fields_return_unsupported_query(self) -> None:
        backend = GitHubWriteBackend(client=_FakeGitHubWriteClient())
        payload = backend.create_draft_pr(
            repo="",
            title="",
            body="Draft body",
            head_branch="",
            base_branch="main",
        )
        self.assertEqual(payload["status"], "unsupported_query")
        self.assertFalse(payload["ok"])

    def test_auth_failure_and_api_failure_are_distinct(self) -> None:
        auth_client = _FakeGitHubWriteClient()
        auth_client.error = GitHubClientError(kind="auth_failure", message="missing token", status_code=401)
        auth_payload = GitHubWriteBackend(client=auth_client).create_draft_pr(
            repo="rai0409/codex-local-runner",
            title="Draft title",
            body="Draft body",
            head_branch="feature/test",
            base_branch="main",
        )

        api_client = _FakeGitHubWriteClient()
        api_client.error = GitHubClientError(kind="api_failure", message="upstream failure", status_code=500)
        api_payload = GitHubWriteBackend(client=api_client).create_draft_pr(
            repo="rai0409/codex-local-runner",
            title="Draft title",
            body="Draft body",
            head_branch="feature/test",
            base_branch="main",
        )

        self.assertEqual(auth_payload["status"], "auth_failure")
        self.assertEqual(api_payload["status"], "api_failure")

    def test_non_draft_response_is_refused_conservatively(self) -> None:
        client = _FakeGitHubWriteClient()
        client.payload["draft"] = False
        payload = GitHubWriteBackend(client=client).create_draft_pr(
            repo="rai0409/codex-local-runner",
            title="Draft title",
            body="Draft body",
            head_branch="feature/test",
            base_branch="main",
        )
        self.assertEqual(payload["status"], "api_failure")
        self.assertEqual(payload["error"]["kind"], "api_failure")

    def test_output_is_deterministic_for_same_response(self) -> None:
        backend = GitHubWriteBackend(client=_FakeGitHubWriteClient())
        kwargs = {
            "repo": "rai0409/codex-local-runner",
            "title": "Draft title",
            "body": "Draft body",
            "head_branch": "feature/test",
            "base_branch": "main",
        }
        first = backend.create_draft_pr(**kwargs)
        second = backend.create_draft_pr(**kwargs)
        self.assertEqual(first, second)

    def test_merge_pull_request_success(self) -> None:
        client = _FakeGitHubWriteClient()
        backend = GitHubWriteBackend(client=client)
        payload = backend.merge_pull_request(
            repo="rai0409/codex-local-runner",
            pr_number=17,
            expected_head_sha="a" * 40,
            merge_method="merge",
        )
        self.assertEqual(payload["operation"], "merge_pull_request")
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["data"]["merge_commit_sha"], "c" * 40)
        self.assertTrue(payload["data"]["merged"])
        self.assertEqual(client.merge_calls[0]["pr_number"], 17)

    def test_merge_pull_request_refuses_invalid_input(self) -> None:
        backend = GitHubWriteBackend(client=_FakeGitHubWriteClient())
        payload = backend.merge_pull_request(
            repo="",
            pr_number=0,
            expected_head_sha="",
            merge_method="merge",
        )
        self.assertEqual(payload["status"], "unsupported_query")
        self.assertFalse(payload["ok"])

    def test_merge_pull_request_handles_api_failure(self) -> None:
        client = _FakeGitHubWriteClient()
        client.merge_error = GitHubClientError(kind="api_failure", message="cannot merge", status_code=405)
        payload = GitHubWriteBackend(client=client).merge_pull_request(
            repo="rai0409/codex-local-runner",
            pr_number=23,
        )
        self.assertEqual(payload["status"], "api_failure")
        self.assertEqual(payload["error"]["status_code"], 405)

    def test_update_existing_pr_success(self) -> None:
        client = _FakeGitHubWriteClient()
        backend = GitHubWriteBackend(client=client)
        payload = backend.update_existing_pr(
            repo="rai0409/codex-local-runner",
            pr_number=42,
            title="Updated title",
            body="Updated body",
            base_branch="main",
        )
        self.assertEqual(payload["operation"], "update_existing_pr")
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["data"]["pr"]["number"], 42)
        self.assertTrue(payload["data"]["updated"])
        self.assertEqual(client.update_calls[0]["title"], "Updated title")

    def test_update_existing_pr_rejects_invalid_payload(self) -> None:
        backend = GitHubWriteBackend(client=_FakeGitHubWriteClient())
        payload = backend.update_existing_pr(
            repo="rai0409/codex-local-runner",
            pr_number=42,
            title=None,
            body=None,
            base_branch=None,
        )
        self.assertEqual(payload["status"], "unsupported_query")
        self.assertFalse(payload["ok"])

    def test_update_existing_pr_replay_when_state_already_matches_is_noop(self) -> None:
        client = _FakeGitHubWriteClient()
        backend = GitHubWriteBackend(client=client)
        payload = backend.update_existing_pr(
            repo="rai0409/codex-local-runner",
            pr_number=42,
            title="Updated title",
            body="Stable body",
            base_branch="main",
            current_pr={
                "number": 42,
                "html_url": "https://example.test/pr/42",
                "state": "open",
                "draft": True,
                "title": "Updated title",
                "body": "Stable body",
                "head": {"ref": "feature/test"},
                "base": {"ref": "main"},
            },
        )
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["data"]["classification"], "already_applied")
        self.assertFalse(payload["data"]["updated"])
        self.assertEqual(client.update_calls, [])

    def test_update_existing_pr_treats_explicit_empty_body_as_requested(self) -> None:
        client = _FakeGitHubWriteClient()
        backend = GitHubWriteBackend(client=client)
        payload = backend.update_existing_pr(
            repo="rai0409/codex-local-runner",
            pr_number=42,
            body="",
        )
        self.assertEqual(payload["status"], "success")
        self.assertEqual(client.update_calls[0]["body"], "")


if __name__ == "__main__":
    unittest.main()
