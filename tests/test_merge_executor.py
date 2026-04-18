from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from automation.github.merge_executor import BoundedMergeExecutor
from automation.github.write_receipts import FileWriteReceiptStore
from orchestrator.merge_executor import execute_constrained_merge


class MergeExecutorTests(unittest.TestCase):
    def _run_git(self, repo_dir: str, args: list[str]) -> str:
        proc = subprocess.run(
            ["git", "-C", repo_dir, *args],
            check=True,
            text=True,
            capture_output=True,
        )
        return proc.stdout.strip()

    def _git_commit(self, repo_dir: str, message: str) -> None:
        self._run_git(
            repo_dir,
            [
                "-c",
                "user.name=Test User",
                "-c",
                "user.email=test@example.com",
                "commit",
                "-m",
                message,
            ],
        )

    def _init_mergeable_repo(self, repo_dir: str) -> dict[str, str]:
        self._run_git(repo_dir, ["init"])
        self._run_git(repo_dir, ["checkout", "-b", "main"])
        (Path(repo_dir) / "README.md").write_text("base\n", encoding="utf-8")
        self._run_git(repo_dir, ["add", "README.md"])
        self._git_commit(repo_dir, "base")
        base_sha = self._run_git(repo_dir, ["rev-parse", "HEAD"])

        self._run_git(repo_dir, ["checkout", "-b", "feature"])
        (Path(repo_dir) / "feature.txt").write_text("feature\n", encoding="utf-8")
        self._run_git(repo_dir, ["add", "feature.txt"])
        self._git_commit(repo_dir, "feature")
        source_sha = self._run_git(repo_dir, ["rev-parse", "HEAD"])

        self._run_git(repo_dir, ["checkout", "main"])
        return {
            "target_ref": "refs/heads/main",
            "base_sha": base_sha,
            "source_sha": source_sha,
        }

    def test_constrained_merge_succeeds_with_matching_invariants(self) -> None:
        with tempfile.TemporaryDirectory() as repo_dir:
            identity = self._init_mergeable_repo(repo_dir)

            result = execute_constrained_merge(
                repo_path=repo_dir,
                target_ref=identity["target_ref"],
                source_sha=identity["source_sha"],
                base_sha=identity["base_sha"],
            )

            head_after = self._run_git(repo_dir, ["rev-parse", "HEAD"])

        self.assertEqual(result["status"], "succeeded")
        self.assertTrue(result["attempted"])
        self.assertEqual(result["pre_merge_sha"], identity["base_sha"])
        self.assertEqual(result["post_merge_sha"], head_after)
        self.assertEqual(result["merge_result_sha"], head_after)
        self.assertIsNone(result["error"])

    def test_constrained_merge_is_skipped_on_base_sha_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as repo_dir:
            identity = self._init_mergeable_repo(repo_dir)

            result = execute_constrained_merge(
                repo_path=repo_dir,
                target_ref=identity["target_ref"],
                source_sha=identity["source_sha"],
                base_sha="0" * 40,
            )

        self.assertEqual(result["status"], "skipped")
        self.assertFalse(result["attempted"])
        self.assertEqual(result["error"], "base_sha_mismatch")

    def test_constrained_merge_is_skipped_when_source_already_merged(self) -> None:
        with tempfile.TemporaryDirectory() as repo_dir:
            identity = self._init_mergeable_repo(repo_dir)
            first = execute_constrained_merge(
                repo_path=repo_dir,
                target_ref=identity["target_ref"],
                source_sha=identity["source_sha"],
                base_sha=identity["base_sha"],
            )
            head_after_first = self._run_git(repo_dir, ["rev-parse", "HEAD"])

            second = execute_constrained_merge(
                repo_path=repo_dir,
                target_ref=identity["target_ref"],
                source_sha=identity["source_sha"],
                base_sha=head_after_first,
            )

        self.assertEqual(first["status"], "succeeded")
        self.assertEqual(second["status"], "skipped")
        self.assertFalse(second["attempted"])
        self.assertEqual(second["error"], "source_already_merged_into_target")

    def test_constrained_merge_fails_on_conflict_and_reports_failure(self) -> None:
        with tempfile.TemporaryDirectory() as repo_dir:
            self._run_git(repo_dir, ["init"])
            self._run_git(repo_dir, ["checkout", "-b", "main"])
            file_path = Path(repo_dir) / "conflict.txt"
            file_path.write_text("base\n", encoding="utf-8")
            self._run_git(repo_dir, ["add", "conflict.txt"])
            self._git_commit(repo_dir, "base")

            self._run_git(repo_dir, ["checkout", "-b", "feature"])
            file_path.write_text("feature\n", encoding="utf-8")
            self._run_git(repo_dir, ["add", "conflict.txt"])
            self._git_commit(repo_dir, "feature change")
            source_sha = self._run_git(repo_dir, ["rev-parse", "HEAD"])

            self._run_git(repo_dir, ["checkout", "main"])
            file_path.write_text("main\n", encoding="utf-8")
            self._run_git(repo_dir, ["add", "conflict.txt"])
            self._git_commit(repo_dir, "main change")
            base_sha = self._run_git(repo_dir, ["rev-parse", "HEAD"])

            result = execute_constrained_merge(
                repo_path=repo_dir,
                target_ref="refs/heads/main",
                source_sha=source_sha,
                base_sha=base_sha,
            )
            head_after = self._run_git(repo_dir, ["rev-parse", "HEAD"])

        self.assertEqual(result["status"], "failed")
        self.assertTrue(result["attempted"])
        self.assertEqual(result["pre_merge_sha"], base_sha)
        self.assertEqual(result["post_merge_sha"], head_after)
        self.assertIsNone(result["merge_result_sha"])
        self.assertTrue(bool(result["error"]))


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


def _write_result(operation: str, status: str, data: dict[str, object] | None = None) -> dict[str, object]:
    return {
        "operation": operation,
        "mode": "write_limited",
        "write_actions_allowed": True,
        "status": status,
        "ok": status == "success",
        "data": data or {},
        "error": {},
    }


class _FakeMergeReadBackend:
    def __init__(self) -> None:
        self.pr_status_payload = _read_result(
            "get_pr_status_summary",
            "success",
            {
                "commit_sha": "a" * 40,
                "pr_state": "open",
                "pr_draft": False,
                "pr_merged": False,
                "mergeable_state": "clean",
                "pr_head_ref": "feature/x",
                "pr_base_ref": "main",
                "checks_state": "passing",
            },
        )
        self.open_pr_payload = _read_result(
            "find_open_pr",
            "success",
            {
                "matched": True,
                "match_count": 1,
                "pr": {"number": 42},
            },
        )
        self.base_head_payload = _read_result(
            "get_branch_head",
            "success",
            {"exists": True, "head_sha": "b" * 40},
        )
        self.compare_payload = _read_result(
            "compare_refs",
            "success",
            {"comparison_status": "ahead"},
        )

    def get_pr_status_summary(self, repo: str, *, pr_number: int | None = None, commit_sha: str | None = None):
        return dict(self.pr_status_payload)

    def find_open_pr(self, repo: str, *, head_branch: str | None = None, base_branch: str | None = None):
        return dict(self.open_pr_payload)

    def get_branch_head(self, repo: str, branch: str):
        return dict(self.base_head_payload)

    def compare_refs(self, repo: str, base_ref: str, head_ref: str):
        return dict(self.compare_payload)


class _FakeMergeWriteBackend:
    def __init__(self) -> None:
        self.payload = _write_result(
            "merge_pull_request",
            "success",
            {
                "merged": True,
                "merge_commit_sha": "c" * 40,
            },
        )
        self.calls: list[dict[str, object]] = []

    def merge_pull_request(
        self,
        *,
        repo: str,
        pr_number: int,
        expected_head_sha: str | None = None,
        merge_method: str = "merge",
    ):
        self.calls.append(
            {
                "repo": repo,
                "pr_number": pr_number,
                "expected_head_sha": expected_head_sha,
                "merge_method": merge_method,
            }
        )
        return dict(self.payload)


class BoundedMergeExecutorTests(unittest.TestCase):
    def test_merge_success_under_valid_gated_conditions(self) -> None:
        executor = BoundedMergeExecutor(
            read_backend=_FakeMergeReadBackend(),
            write_backend=_FakeMergeWriteBackend(),
        )
        payload = executor.execute_merge(
            job_id="job-merge-1",
            repository="rai0409/codex-local-runner",
            pr_number=42,
            expected_head_sha="a" * 40,
        )
        self.assertTrue(payload["attempted"])
        self.assertTrue(payload["succeeded"])
        self.assertEqual(payload["merge_commit_sha"], "c" * 40)

    def test_merge_refuses_when_target_pr_missing_or_ambiguous(self) -> None:
        read_backend = _FakeMergeReadBackend()
        read_backend.open_pr_payload = _read_result(
            "find_open_pr",
            "success",
            {"matched": True, "match_count": 2, "pr": {"number": 42}},
        )
        payload = BoundedMergeExecutor(
            read_backend=read_backend,
            write_backend=_FakeMergeWriteBackend(),
        ).execute_merge(
            job_id="job-merge-2",
            repository="rai0409/codex-local-runner",
            pr_number=42,
        )
        self.assertFalse(payload["succeeded"])
        self.assertEqual(payload["refusal_reason"], "open_pr_ambiguous")

    def test_merge_refuses_when_checks_missing_or_failing(self) -> None:
        read_backend = _FakeMergeReadBackend()
        read_backend.pr_status_payload = _read_result(
            "get_pr_status_summary",
            "success",
            {
                "commit_sha": "a" * 40,
                "pr_state": "open",
                "pr_draft": False,
                "pr_merged": False,
                "mergeable_state": "clean",
                "pr_head_ref": "feature/x",
                "pr_base_ref": "main",
                "checks_state": "pending",
            },
        )
        payload = BoundedMergeExecutor(
            read_backend=read_backend,
            write_backend=_FakeMergeWriteBackend(),
        ).execute_merge(
            job_id="job-merge-3",
            repository="rai0409/codex-local-runner",
            pr_number=42,
        )
        self.assertFalse(payload["succeeded"])
        self.assertEqual(payload["refusal_reason"], "checks_not_passing:pending")

    def test_merge_refuses_on_blocking_backend_statuses(self) -> None:
        for status in ("auth_failure", "api_failure", "unsupported_query"):
            with self.subTest(status=status):
                read_backend = _FakeMergeReadBackend()
                read_backend.pr_status_payload = _read_result("get_pr_status_summary", status, {})
                payload = BoundedMergeExecutor(
                    read_backend=read_backend,
                    write_backend=_FakeMergeWriteBackend(),
                ).execute_merge(
                    job_id=f"job-merge-{status}",
                    repository="rai0409/codex-local-runner",
                    pr_number=42,
                )
                self.assertFalse(payload["succeeded"])
                self.assertEqual(payload["refusal_reason"], f"pr_status_unavailable:{status}")

    def test_merge_handles_empty_and_not_found_conservatively(self) -> None:
        read_empty = _FakeMergeReadBackend()
        read_empty.pr_status_payload = _read_result("get_pr_status_summary", "empty", {})
        empty_payload = BoundedMergeExecutor(
            read_backend=read_empty,
            write_backend=_FakeMergeWriteBackend(),
        ).execute_merge(
            job_id="job-merge-empty",
            repository="rai0409/codex-local-runner",
            pr_number=42,
        )
        self.assertEqual(empty_payload["refusal_reason"], "pr_status_missing:empty")

        read_not_found = _FakeMergeReadBackend()
        read_not_found.pr_status_payload = _read_result("get_pr_status_summary", "not_found", {})
        not_found_payload = BoundedMergeExecutor(
            read_backend=read_not_found,
            write_backend=_FakeMergeWriteBackend(),
        ).execute_merge(
            job_id="job-merge-not-found",
            repository="rai0409/codex-local-runner",
            pr_number=42,
        )
        self.assertEqual(not_found_payload["refusal_reason"], "pr_status_missing:not_found")

    def test_merge_outputs_are_deterministic_for_same_inputs(self) -> None:
        executor = BoundedMergeExecutor(
            read_backend=_FakeMergeReadBackend(),
            write_backend=_FakeMergeWriteBackend(),
        )
        kwargs = {
            "job_id": "job-merge-det",
            "repository": "rai0409/codex-local-runner",
            "pr_number": 42,
            "expected_head_sha": "a" * 40,
        }
        first = executor.execute_merge(**kwargs)
        second = executor.execute_merge(**kwargs)
        self.assertEqual(first, second)

    def test_merge_replay_after_already_merged_is_already_applied(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = FileWriteReceiptStore(Path(tmp_dir))
            first = BoundedMergeExecutor(
                read_backend=_FakeMergeReadBackend(),
                write_backend=_FakeMergeWriteBackend(),
            ).execute_merge(
                job_id="job-merge-replay",
                repository="rai0409/codex-local-runner",
                pr_number=42,
                write_receipt_store=store,
            )
            replay_read = _FakeMergeReadBackend()
            replay_read.pr_status_payload = _read_result(
                "get_pr_status_summary",
                "success",
                {
                    "commit_sha": "a" * 40,
                    "pr_state": "open",
                    "pr_draft": False,
                    "pr_merged": True,
                    "mergeable_state": "clean",
                    "pr_head_ref": "feature/x",
                    "pr_base_ref": "main",
                    "checks_state": "passing",
                },
            )
            second = BoundedMergeExecutor(
                read_backend=replay_read,
                write_backend=_FakeMergeWriteBackend(),
            ).execute_merge(
                job_id="job-merge-replay",
                repository="rai0409/codex-local-runner",
                pr_number=42,
                write_receipt_store=store,
            )
        self.assertTrue(first["succeeded"])
        self.assertTrue(second["succeeded"])
        self.assertFalse(second["attempted"])
        self.assertTrue(second["merged_state_summary"]["merged"])

    def test_merge_replay_with_changed_head_sha_is_precondition_changed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = FileWriteReceiptStore(Path(tmp_dir))
            _ = BoundedMergeExecutor(
                read_backend=_FakeMergeReadBackend(),
                write_backend=_FakeMergeWriteBackend(),
            ).execute_merge(
                job_id="job-merge-sha",
                repository="rai0409/codex-local-runner",
                pr_number=42,
                write_receipt_store=store,
            )
            replay_read = _FakeMergeReadBackend()
            replay_read.pr_status_payload = _read_result(
                "get_pr_status_summary",
                "success",
                {
                    "commit_sha": "d" * 40,
                    "pr_state": "open",
                    "pr_draft": False,
                    "pr_merged": False,
                    "mergeable_state": "clean",
                    "pr_head_ref": "feature/x",
                    "pr_base_ref": "main",
                    "checks_state": "passing",
                },
            )
            replay = BoundedMergeExecutor(
                read_backend=replay_read,
                write_backend=_FakeMergeWriteBackend(),
            ).execute_merge(
                job_id="job-merge-sha",
                repository="rai0409/codex-local-runner",
                pr_number=42,
                write_receipt_store=store,
            )
        self.assertFalse(replay["succeeded"])
        self.assertEqual(replay["refusal_reason"], "idempotency_precondition_changed:head_sha_changed")


if __name__ == "__main__":
    unittest.main()
