from __future__ import annotations

import unittest
from pathlib import Path
import tempfile

from automation.github.pr_creator import DraftPRCreator
from automation.github.write_receipts import FileWriteReceiptStore


def _read_result(operation: str, status: str, data: dict[str, object] | None = None) -> dict[str, object]:
    return {
        "operation": operation,
        "mode": "read_only",
        "write_actions_allowed": False,
        "status": status,
        "ok": status in {"success", "empty"},
        "data": data or {},
        "error": {},
    }


def _write_result(status: str, data: dict[str, object] | None = None) -> dict[str, object]:
    return {
        "operation": "create_draft_pr",
        "mode": "write_limited",
        "write_actions_allowed": True,
        "status": status,
        "ok": status == "success",
        "data": data or {},
        "error": {},
    }


class _FakeReadBackend:
    def __init__(self) -> None:
        self.default_branch_payload = _read_result(
            "get_default_branch",
            "success",
            {"default_branch": "main"},
        )
        self.head_payload = _read_result(
            "get_branch_head",
            "success",
            {"exists": True, "head_sha": "a" * 40},
        )
        self.base_payload = _read_result(
            "get_branch_head",
            "success",
            {"exists": True, "head_sha": "b" * 40},
        )
        self.compare_payload = _read_result(
            "compare_refs",
            "success",
            {"comparison_status": "ahead", "changed_files": ["a.py"]},
        )
        self.open_pr_payload = _read_result(
            "find_open_pr",
            "empty",
            {"matched": False, "match_count": 0, "pr": None},
        )
        self.checks_payload = _read_result(
            "get_pr_status_summary",
            "success",
            {"checks_state": "pending"},
        )

    def get_default_branch(self, repo: str):
        return dict(self.default_branch_payload)

    def get_branch_head(self, repo: str, branch: str):
        if branch == "feature/test":
            return dict(self.head_payload)
        return dict(self.base_payload)

    def compare_refs(self, repo: str, base_ref: str, head_ref: str):
        return dict(self.compare_payload)

    def find_open_pr(self, repo: str, *, head_branch: str | None = None, base_branch: str | None = None):
        return dict(self.open_pr_payload)

    def get_pr_status_summary(self, repo: str, *, pr_number: int | None = None, commit_sha: str | None = None):
        return dict(self.checks_payload)


class _FakeWriteBackend:
    def __init__(self) -> None:
        self.payload = _write_result(
            "success",
            {
                "pr": {
                    "number": 12,
                    "html_url": "https://example.test/pr/12",
                    "draft": True,
                }
            },
        )
        self.calls: list[dict[str, object]] = []

    def create_draft_pr(
        self,
        *,
        repo: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str,
    ):
        self.calls.append(
            {
                "repo": repo,
                "title": title,
                "body": body,
                "head_branch": head_branch,
                "base_branch": base_branch,
            }
        )
        return dict(self.payload)


class DraftPRCreatorTests(unittest.TestCase):
    def test_draft_pr_creation_success_with_valid_preconditions(self) -> None:
        creator = DraftPRCreator(read_backend=_FakeReadBackend(), write_backend=_FakeWriteBackend())
        result = creator.create_draft_pr(
            job_id="job-1",
            repository="rai0409/codex-local-runner",
            head_branch="feature/test",
            base_branch="main",
            title="Draft title",
            body="Draft body",
        )
        self.assertTrue(result["attempted"])
        self.assertTrue(result["succeeded"])
        self.assertIsNone(result["refusal_reason"])
        self.assertEqual(result["pr_number"], 12)

    def test_refusal_when_source_head_branch_missing(self) -> None:
        read_backend = _FakeReadBackend()
        read_backend.head_payload = _read_result(
            "get_branch_head",
            "not_found",
            {"exists": False, "head_sha": None},
        )
        creator = DraftPRCreator(read_backend=read_backend, write_backend=_FakeWriteBackend())
        result = creator.create_draft_pr(
            job_id="job-2",
            repository="rai0409/codex-local-runner",
            head_branch="feature/test",
            base_branch="main",
            title="Draft title",
            body="Draft body",
        )
        self.assertFalse(result["attempted"])
        self.assertFalse(result["succeeded"])
        self.assertIn("head_branch_missing", result["refusal_reason"])

    def test_refusal_when_base_branch_resolution_is_ambiguous(self) -> None:
        read_backend = _FakeReadBackend()
        read_backend.default_branch_payload = _read_result(
            "get_default_branch",
            "empty",
            {"default_branch": None},
        )
        creator = DraftPRCreator(read_backend=read_backend, write_backend=_FakeWriteBackend())
        result = creator.create_draft_pr(
            job_id="job-3",
            repository="rai0409/codex-local-runner",
            head_branch="feature/test",
            base_branch=None,
            title="Draft title",
            body="Draft body",
        )
        self.assertFalse(result["succeeded"])
        self.assertEqual(result["refusal_reason"], "default_branch_missing:empty")

    def test_refusal_when_open_pr_already_exists(self) -> None:
        read_backend = _FakeReadBackend()
        read_backend.open_pr_payload = _read_result(
            "find_open_pr",
            "success",
            {
                "matched": True,
                "match_count": 1,
                "pr": {"number": 77},
            },
        )
        creator = DraftPRCreator(read_backend=read_backend, write_backend=_FakeWriteBackend())
        result = creator.create_draft_pr(
            job_id="job-4",
            repository="rai0409/codex-local-runner",
            head_branch="feature/test",
            base_branch="main",
            title="Draft title",
            body="Draft body",
        )
        self.assertTrue(result["succeeded"])
        self.assertFalse(result["attempted"])
        self.assertEqual(result["pr_number"], 77)

    def test_idempotency_conflict_is_conservative(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = FileWriteReceiptStore(Path(tmp_dir))
            store.persist_record(
                write_action="create_draft_pr",
                idempotency_key="prior-key",
                updated_at="2026-04-18T14:00:00",
                payload={
                    "job_id": "job-7",
                    "write_action": "create_draft_pr",
                    "target_identifiers": {
                        "repository": "rai0409/codex-local-runner",
                        "head_branch": "feature/other",
                        "base_branch": "main",
                    },
                    "intent_fingerprint": "fingerprint",
                    "execution_status": "attempted",
                    "final_classification": "applied",
                },
            )
            creator = DraftPRCreator(read_backend=_FakeReadBackend(), write_backend=_FakeWriteBackend())
            result = creator.create_draft_pr(
                job_id="job-7",
                repository="rai0409/codex-local-runner",
                head_branch="feature/test",
                base_branch="main",
                title="Draft title",
                body="Draft body",
                write_receipt_store=store,
            )
        self.assertFalse(result["succeeded"])
        self.assertEqual(result["refusal_reason"], "idempotency_conflict:conflicting_prior_intent")

    def test_replay_same_intent_uses_already_applied_noop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = FileWriteReceiptStore(Path(tmp_dir))
            first_creator = DraftPRCreator(read_backend=_FakeReadBackend(), write_backend=_FakeWriteBackend())
            first = first_creator.create_draft_pr(
                job_id="job-8",
                repository="rai0409/codex-local-runner",
                head_branch="feature/test",
                base_branch="main",
                title="Draft title",
                body="Draft body",
                write_receipt_store=store,
            )
            replay_read = _FakeReadBackend()
            replay_read.open_pr_payload = _read_result(
                "find_open_pr",
                "success",
                {
                    "matched": True,
                    "match_count": 1,
                    "pr": {"number": 12, "html_url": "https://example.test/pr/12"},
                },
            )
            second = DraftPRCreator(read_backend=replay_read, write_backend=_FakeWriteBackend()).create_draft_pr(
                job_id="job-8",
                repository="rai0409/codex-local-runner",
                head_branch="feature/test",
                base_branch="main",
                title="Draft title",
                body="Draft body",
                write_receipt_store=store,
            )
        self.assertTrue(first["succeeded"])
        self.assertTrue(second["succeeded"])
        self.assertFalse(second["attempted"])
        self.assertEqual(second["pr_number"], 12)

    def test_refusal_on_auth_api_or_unsupported_query_statuses(self) -> None:
        for status in ("auth_failure", "api_failure", "unsupported_query"):
            with self.subTest(status=status):
                read_backend = _FakeReadBackend()
                read_backend.compare_payload = _read_result("compare_refs", status, {})
                creator = DraftPRCreator(read_backend=read_backend, write_backend=_FakeWriteBackend())
                result = creator.create_draft_pr(
                    job_id="job-5",
                    repository="rai0409/codex-local-runner",
                    head_branch="feature/test",
                    base_branch="main",
                    title="Draft title",
                    body="Draft body",
                )
                self.assertFalse(result["succeeded"])
                self.assertEqual(result["refusal_reason"], f"compare_refs_failed:{status}")

    def test_empty_or_not_found_are_conservative_without_policy_override(self) -> None:
        empty_backend = _FakeReadBackend()
        empty_backend.compare_payload = _read_result("compare_refs", "empty", {})
        empty_result = DraftPRCreator(read_backend=empty_backend, write_backend=_FakeWriteBackend()).create_draft_pr(
            job_id="job-empty",
            repository="rai0409/codex-local-runner",
            head_branch="feature/test",
            base_branch="main",
            title="Draft title",
            body="Draft body",
        )
        self.assertEqual(empty_result["refusal_reason"], "compare_refs_missing:empty")

        not_found_backend = _FakeReadBackend()
        not_found_backend.compare_payload = _read_result("compare_refs", "not_found", {})
        not_found_result = DraftPRCreator(
            read_backend=not_found_backend,
            write_backend=_FakeWriteBackend(),
        ).create_draft_pr(
            job_id="job-not-found",
            repository="rai0409/codex-local-runner",
            head_branch="feature/test",
            base_branch="main",
            title="Draft title",
            body="Draft body",
        )
        self.assertEqual(not_found_result["refusal_reason"], "compare_refs_missing:not_found")

    def test_equivalent_mocked_responses_remain_deterministic(self) -> None:
        creator = DraftPRCreator(read_backend=_FakeReadBackend(), write_backend=_FakeWriteBackend())
        kwargs = {
            "job_id": "job-det",
            "repository": "rai0409/codex-local-runner",
            "head_branch": "feature/test",
            "base_branch": "main",
            "title": "Draft title",
            "body": "Draft body",
        }
        first = creator.create_draft_pr(**kwargs)
        second = creator.create_draft_pr(**kwargs)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
