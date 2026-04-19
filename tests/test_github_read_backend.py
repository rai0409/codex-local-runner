from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from automation.github.github_client import GitHubClientError
from automation.github.read_backend import GitHubReadBackend
from automation.github.read_backend import build_github_read_backend


class _FakeGitHubClient:
    def __init__(self) -> None:
        self.repo_payload: dict[str, object] = {"default_branch": "main"}
        self.branch_payload: dict[str, object] = {"commit": {"sha": "a" * 40}}
        self.compare_payload: dict[str, object] = {
            "status": "ahead",
            "ahead_by": 2,
            "behind_by": 0,
            "total_commits": 2,
            "files": [{"filename": "b.py"}, {"filename": "a.py"}],
        }
        self.pulls_payload: list[dict[str, object]] = []
        self.pull_payload: dict[str, object] = {
            "number": 10,
            "head": {"sha": "b" * 40},
        }
        self.commit_status_payload: dict[str, object] = {"state": "success", "statuses": []}
        self.check_runs_payload: dict[str, object] = {"check_runs": []}

        self.repo_error: GitHubClientError | None = None
        self.branch_error: GitHubClientError | None = None
        self.compare_error: GitHubClientError | None = None
        self.pulls_error: GitHubClientError | None = None
        self.pull_error: GitHubClientError | None = None
        self.commit_status_error: GitHubClientError | None = None
        self.check_runs_error: GitHubClientError | None = None

    def get_repo(self, repo: str):
        if self.repo_error is not None:
            raise self.repo_error
        return dict(self.repo_payload)

    def get_branch(self, repo: str, branch: str):
        if self.branch_error is not None:
            raise self.branch_error
        return dict(self.branch_payload)

    def compare_refs(self, repo: str, base_ref: str, head_ref: str):
        if self.compare_error is not None:
            raise self.compare_error
        return dict(self.compare_payload)

    def list_open_pull_requests(self, repo: str, *, head_branch: str | None = None, base_branch: str | None = None):
        if self.pulls_error is not None:
            raise self.pulls_error
        return [dict(item) for item in self.pulls_payload]

    def get_pull_request(self, repo: str, pr_number: int):
        if self.pull_error is not None:
            raise self.pull_error
        return dict(self.pull_payload)

    def get_commit_status(self, repo: str, commit_sha: str):
        if self.commit_status_error is not None:
            raise self.commit_status_error
        return dict(self.commit_status_payload)

    def list_check_runs(self, repo: str, commit_sha: str):
        if self.check_runs_error is not None:
            raise self.check_runs_error
        return dict(self.check_runs_payload)


class GitHubReadBackendTests(unittest.TestCase):
    def test_default_branch_retrieval(self) -> None:
        backend = GitHubReadBackend(client=_FakeGitHubClient())
        payload = backend.get_default_branch("rai0409/codex-local-runner")

        self.assertEqual(payload["status"], "success")
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"]["default_branch"], "main")
        self.assertEqual(payload["mode"], "read_only")
        self.assertFalse(payload["write_actions_allowed"])

    def test_branch_lookup_success_and_not_found(self) -> None:
        backend = GitHubReadBackend(client=_FakeGitHubClient())
        success_payload = backend.get_branch_head("rai0409/codex-local-runner", "main")
        self.assertEqual(success_payload["status"], "success")
        self.assertEqual(success_payload["data"]["exists"], True)
        self.assertEqual(success_payload["data"]["head_sha"], "a" * 40)

        client_not_found = _FakeGitHubClient()
        client_not_found.branch_error = GitHubClientError(
            kind="not_found",
            message="branch not found",
            status_code=404,
        )
        not_found_backend = GitHubReadBackend(client=client_not_found)
        not_found_payload = not_found_backend.get_branch_head("rai0409/codex-local-runner", "missing")
        self.assertEqual(not_found_payload["status"], "not_found")
        self.assertEqual(not_found_payload["data"]["exists"], False)

    def test_compare_result_normalization(self) -> None:
        backend = GitHubReadBackend(client=_FakeGitHubClient())
        payload = backend.compare_refs(
            "rai0409/codex-local-runner",
            "main",
            "feature/read-backend",
        )
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["data"]["comparison_status"], "ahead")
        self.assertEqual(payload["data"]["changed_files"], ["a.py", "b.py"])
        self.assertEqual(payload["data"]["ahead_by"], 2)
        self.assertEqual(payload["data"]["behind_by"], 0)

    def test_open_pr_lookup_normalization(self) -> None:
        client = _FakeGitHubClient()
        client.pulls_payload = [
            {
                "number": 22,
                "title": "Second",
                "state": "open",
                "draft": False,
                "head": {"ref": "feature/x", "sha": "b" * 40},
                "base": {"ref": "main"},
                "html_url": "https://example/pr/22",
            },
            {
                "number": 20,
                "title": "First",
                "state": "open",
                "draft": False,
                "head": {"ref": "feature/x", "sha": "a" * 40},
                "base": {"ref": "main"},
                "html_url": "https://example/pr/20",
            },
        ]
        backend = GitHubReadBackend(client=client)
        payload = backend.find_open_pr(
            "rai0409/codex-local-runner",
            head_branch="rai0409:feature/x",
            base_branch="main",
        )
        self.assertEqual(payload["status"], "success")
        self.assertTrue(payload["data"]["matched"])
        self.assertEqual(payload["data"]["match_count"], 2)
        self.assertEqual(payload["data"]["pr"]["number"], 20)

    def test_check_status_summary_normalization(self) -> None:
        client = _FakeGitHubClient()
        client.pull_payload = {
            "number": 30,
            "head": {"sha": "c" * 40},
        }
        client.commit_status_payload = {
            "state": "success",
            "statuses": [
                {"state": "success"},
                {"state": "success"},
            ],
        }
        client.check_runs_payload = {
            "check_runs": [
                {"status": "completed", "conclusion": "success"},
                {"status": "completed", "conclusion": "neutral"},
            ]
        }
        backend = GitHubReadBackend(client=client)
        payload = backend.get_pr_status_summary(
            "rai0409/codex-local-runner",
            pr_number=30,
        )
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["data"]["checks_state"], "passing")
        self.assertEqual(payload["data"]["status_contexts"]["total"], 2)
        self.assertEqual(payload["data"]["check_runs"]["success"], 2)

    def test_auth_config_missing_behavior(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            backend = build_github_read_backend()
            payload = backend.get_default_branch("rai0409/codex-local-runner")

        self.assertEqual(payload["status"], "auth_failure")
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["kind"], "auth_failure")

    def test_api_failure_behavior(self) -> None:
        client = _FakeGitHubClient()
        client.compare_error = GitHubClientError(
            kind="api_failure",
            message="upstream failed",
            status_code=500,
        )
        backend = GitHubReadBackend(client=client)
        payload = backend.compare_refs("rai0409/codex-local-runner", "main", "feature")
        self.assertEqual(payload["status"], "api_failure")
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["status_code"], 500)

    def test_abstraction_is_explicitly_read_only(self) -> None:
        backend = GitHubReadBackend(client=_FakeGitHubClient())
        self.assertFalse(hasattr(backend, "create_pull_request"))
        self.assertFalse(hasattr(backend, "merge_pull_request"))

        payload = backend.find_open_pr("rai0409/codex-local-runner", head_branch="rai0409:feature/x")
        self.assertEqual(payload["mode"], "read_only")
        self.assertFalse(payload["write_actions_allowed"])

    def test_deterministic_outputs_for_equivalent_responses(self) -> None:
        backend = GitHubReadBackend(client=_FakeGitHubClient())
        first = backend.compare_refs("rai0409/codex-local-runner", "main", "feature")
        second = backend.compare_refs("rai0409/codex-local-runner", "main", "feature")
        self.assertEqual(first, second)

    def test_ambiguous_partial_data_is_conservative(self) -> None:
        client = _FakeGitHubClient()
        client.branch_payload = {"name": "main"}
        backend = GitHubReadBackend(client=client)
        payload = backend.get_branch_head("rai0409/codex-local-runner", "main")
        self.assertEqual(payload["status"], "empty")
        self.assertTrue(payload["ok"])
        self.assertIsNone(payload["data"]["head_sha"])

    def test_success_empty_not_found_auth_and_unsupported_are_distinct(self) -> None:
        backend = GitHubReadBackend(client=_FakeGitHubClient())
        success = backend.get_default_branch("rai0409/codex-local-runner")
        empty = backend.find_open_pr("rai0409/codex-local-runner", head_branch="rai0409:none")

        not_found_client = _FakeGitHubClient()
        not_found_client.branch_error = GitHubClientError(kind="not_found", message="missing", status_code=404)
        not_found = GitHubReadBackend(client=not_found_client).get_branch_head(
            "rai0409/codex-local-runner",
            "missing",
        )

        with patch.dict(os.environ, {}, clear=True):
            auth_failure = build_github_read_backend().get_default_branch("rai0409/codex-local-runner")

        unsupported = backend.get_pr_status_summary("rai0409/codex-local-runner")

        self.assertEqual(success["status"], "success")
        self.assertEqual(empty["status"], "empty")
        self.assertEqual(not_found["status"], "not_found")
        self.assertEqual(auth_failure["status"], "auth_failure")
        self.assertEqual(unsupported["status"], "unsupported_query")


if __name__ == "__main__":
    unittest.main()
