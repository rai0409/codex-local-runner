from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from automation.github.pr_updater import BoundedPRUpdater
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
        "operation": "update_existing_pr",
        "mode": "write_limited",
        "write_actions_allowed": True,
        "status": status,
        "ok": status == "success",
        "data": data or {},
        "error": {},
    }


class _FakeReadBackend:
    def __init__(self) -> None:
        self.status_payload = _read_result(
            "get_pr_status_summary",
            "success",
            {
                "commit_sha": "a" * 40,
                "pr_state": "open",
                "pr_merged": False,
                "checks_state": "passing",
            },
        )
        self.pull_request_payload = {
            "number": 42,
            "html_url": "https://example.test/pr/42",
            "state": "open",
            "draft": True,
            "title": "Current title",
            "body": "Current body",
            "head": {"ref": "feature/test"},
            "base": {"ref": "main"},
        }
        self.client = self

    def get_pr_status_summary(self, repo: str, *, pr_number: int | None = None, commit_sha: str | None = None):
        return dict(self.status_payload)

    def get_pull_request(self, repo: str, pr_number: int):
        return dict(self.pull_request_payload)


class _FakeWriteBackend:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.payload = _write_result(
            "success",
            {
                "classification": "applied",
                "updated": True,
                "pr": {
                    "number": 42,
                    "html_url": "https://example.test/pr/42",
                    "state": "open",
                    "draft": True,
                    "title": "Updated title",
                    "body": "Updated body",
                    "head": {"ref": "feature/test"},
                    "base": {"ref": "main"},
                },
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
        current_pr: dict[str, object] | None = None,
    ):
        self.calls.append(
            {
                "repo": repo,
                "pr_number": pr_number,
                "title": title,
                "body": body,
                "base_branch": base_branch,
            }
        )
        return dict(self.payload)


class BoundedPRUpdaterTests(unittest.TestCase):
    def test_noop_when_requested_fields_match(self) -> None:
        updater = BoundedPRUpdater(read_backend=_FakeReadBackend(), write_backend=_FakeWriteBackend())
        result = updater.update_pr(
            job_id="job-update-1",
            repository="rai0409/codex-local-runner",
            pr_number=42,
            title="Current title",
        )
        self.assertTrue(result["succeeded"])
        self.assertFalse(result["attempted"])

    def test_replay_same_intent_does_not_issue_second_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = FileWriteReceiptStore(Path(tmp_dir))
            read_backend = _FakeReadBackend()
            write_backend = _FakeWriteBackend()
            updater = BoundedPRUpdater(read_backend=read_backend, write_backend=write_backend)
            first = updater.update_pr(
                job_id="job-update-2",
                repository="rai0409/codex-local-runner",
                pr_number=42,
                title="Updated title",
                write_receipt_store=store,
            )
            read_backend.pull_request_payload["title"] = "Updated title"
            second = updater.update_pr(
                job_id="job-update-2",
                repository="rai0409/codex-local-runner",
                pr_number=42,
                title="Updated title",
                write_receipt_store=store,
            )
        self.assertTrue(first["succeeded"])
        self.assertTrue(second["succeeded"])
        self.assertFalse(second["attempted"])
        self.assertEqual(len(write_backend.calls), 1)

    def test_distinct_update_intents_are_not_collapsed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = FileWriteReceiptStore(Path(tmp_dir))
            read_backend = _FakeReadBackend()
            write_backend = _FakeWriteBackend()
            updater = BoundedPRUpdater(read_backend=read_backend, write_backend=write_backend)
            first = updater.update_pr(
                job_id="job-update-3",
                repository="rai0409/codex-local-runner",
                pr_number=42,
                title="Updated title",
                write_receipt_store=store,
            )
            second = updater.update_pr(
                job_id="job-update-3",
                repository="rai0409/codex-local-runner",
                pr_number=42,
                body="Updated body",
                write_receipt_store=store,
            )
        self.assertTrue(first["succeeded"])
        self.assertTrue(second["succeeded"])
        self.assertEqual(len(write_backend.calls), 2)


if __name__ == "__main__":
    unittest.main()
