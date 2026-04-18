from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from automation.github.rollback_executor import BoundedRollbackExecutor
from automation.github.write_receipts import FileWriteReceiptStore
from orchestrator.rollback_executor import execute_constrained_rollback


class RollbackExecutorTests(unittest.TestCase):
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

    def _init_merged_repo(self, repo_dir: str) -> dict[str, str]:
        self._run_git(repo_dir, ["init"])
        self._run_git(repo_dir, ["checkout", "-b", "main"])

        (Path(repo_dir) / "README.md").write_text("base\n", encoding="utf-8")
        self._run_git(repo_dir, ["add", "README.md"])
        self._git_commit(repo_dir, "base")
        pre_merge_sha = self._run_git(repo_dir, ["rev-parse", "HEAD"])

        self._run_git(repo_dir, ["checkout", "-b", "feature"])
        (Path(repo_dir) / "feature.txt").write_text("feature\n", encoding="utf-8")
        self._run_git(repo_dir, ["add", "feature.txt"])
        self._git_commit(repo_dir, "feature")
        source_sha = self._run_git(repo_dir, ["rev-parse", "HEAD"])

        self._run_git(repo_dir, ["checkout", "main"])
        self._run_git(
            repo_dir,
            [
                "-c",
                "user.name=Test User",
                "-c",
                "user.email=test@example.com",
                "merge",
                "--no-ff",
                "--no-edit",
                source_sha,
            ],
        )
        post_merge_sha = self._run_git(repo_dir, ["rev-parse", "HEAD"])

        return {
            "target_ref": "refs/heads/main",
            "pre_merge_sha": pre_merge_sha,
            "post_merge_sha": post_merge_sha,
        }

    def test_constrained_rollback_succeeds_when_state_matches_trace(self) -> None:
        with tempfile.TemporaryDirectory() as repo_dir:
            trace = self._init_merged_repo(repo_dir)

            result = execute_constrained_rollback(
                repo_path=repo_dir,
                target_ref=trace["target_ref"],
                pre_merge_sha=trace["pre_merge_sha"],
                post_merge_sha=trace["post_merge_sha"],
            )

            head_after = self._run_git(repo_dir, ["rev-parse", "HEAD"])

        self.assertEqual(result["status"], "succeeded")
        self.assertTrue(result["attempted"])
        self.assertTrue(result["consistency_check_passed"])
        self.assertEqual(result["current_head_sha"], trace["post_merge_sha"])
        self.assertEqual(result["rollback_result_sha"], head_after)
        self.assertIsNone(result["error"])

    def test_constrained_rollback_skips_when_current_head_mismatches_trace(self) -> None:
        with tempfile.TemporaryDirectory() as repo_dir:
            trace = self._init_merged_repo(repo_dir)
            (Path(repo_dir) / "extra.txt").write_text("extra\n", encoding="utf-8")
            self._run_git(repo_dir, ["add", "extra.txt"])
            self._git_commit(repo_dir, "drift")

            result = execute_constrained_rollback(
                repo_path=repo_dir,
                target_ref=trace["target_ref"],
                pre_merge_sha=trace["pre_merge_sha"],
                post_merge_sha=trace["post_merge_sha"],
            )

        self.assertEqual(result["status"], "skipped")
        self.assertFalse(result["attempted"])
        self.assertFalse(result["consistency_check_passed"])
        self.assertEqual(result["error"], "current_head_mismatch_post_merge")

    def test_constrained_rollback_skips_when_target_ref_drifts(self) -> None:
        with tempfile.TemporaryDirectory() as repo_dir:
            trace = self._init_merged_repo(repo_dir)
            # Move away from target ref and ensure drift is detected safely as non-attempt.
            self._run_git(repo_dir, ["checkout", "-b", "other"])
            (Path(repo_dir) / "other.txt").write_text("other\n", encoding="utf-8")
            self._run_git(repo_dir, ["add", "other.txt"])
            self._git_commit(repo_dir, "other branch change")
            result = execute_constrained_rollback(
                repo_path=repo_dir,
                target_ref=trace["target_ref"],
                pre_merge_sha=trace["pre_merge_sha"],
                post_merge_sha=trace["post_merge_sha"],
            )

        self.assertEqual(result["status"], "skipped")
        self.assertFalse(result["attempted"])
        self.assertEqual(result["error"], "target_ref_drift_detected")


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


class _FakeRollbackReadBackend:
    def __init__(self, *, head_sha: str) -> None:
        self.branch_payload = _read_result(
            "get_branch_head",
            "success",
            {"exists": True, "head_sha": head_sha},
        )
        self.compare_payload = _read_result(
            "compare_refs",
            "success",
            {"comparison_status": "ahead"},
        )
        self.status_payload = _read_result(
            "get_pr_status_summary",
            "success",
            {"checks_state": "passing"},
        )

    def get_branch_head(self, repo: str, branch: str):
        return dict(self.branch_payload)

    def compare_refs(self, repo: str, base_ref: str, head_ref: str):
        return dict(self.compare_payload)

    def get_pr_status_summary(self, repo: str, *, pr_number: int | None = None, commit_sha: str | None = None):
        return dict(self.status_payload)


class BoundedRollbackExecutorTests(unittest.TestCase):
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

    def _init_merged_repo(self, repo_dir: str) -> dict[str, str]:
        self._run_git(repo_dir, ["init"])
        self._run_git(repo_dir, ["checkout", "-b", "main"])
        (Path(repo_dir) / "README.md").write_text("base\n", encoding="utf-8")
        self._run_git(repo_dir, ["add", "README.md"])
        self._git_commit(repo_dir, "base")
        pre_merge_sha = self._run_git(repo_dir, ["rev-parse", "HEAD"])

        self._run_git(repo_dir, ["checkout", "-b", "feature"])
        (Path(repo_dir) / "feature.txt").write_text("feature\n", encoding="utf-8")
        self._run_git(repo_dir, ["add", "feature.txt"])
        self._git_commit(repo_dir, "feature")
        source_sha = self._run_git(repo_dir, ["rev-parse", "HEAD"])

        self._run_git(repo_dir, ["checkout", "main"])
        self._run_git(
            repo_dir,
            [
                "-c",
                "user.name=Test User",
                "-c",
                "user.email=test@example.com",
                "merge",
                "--no-ff",
                "--no-edit",
                source_sha,
            ],
        )
        post_merge_sha = self._run_git(repo_dir, ["rev-parse", "HEAD"])
        return {
            "target_ref": "main",
            "pre_merge_sha": pre_merge_sha,
            "post_merge_sha": post_merge_sha,
        }

    def test_rollback_success_under_narrow_explicit_valid_conditions(self) -> None:
        with tempfile.TemporaryDirectory() as repo_dir:
            trace = self._init_merged_repo(repo_dir)
            read_backend = _FakeRollbackReadBackend(head_sha=trace["post_merge_sha"])
            executor = BoundedRollbackExecutor(read_backend=read_backend)
            payload = executor.execute_rollback(
                job_id="job-rollback-1",
                repository="rai0409/codex-local-runner",
                repo_path=repo_dir,
                target_ref=trace["target_ref"],
                pre_merge_sha=trace["pre_merge_sha"],
                post_merge_sha=trace["post_merge_sha"],
            )

        self.assertTrue(payload["attempted"])
        self.assertTrue(payload["succeeded"])
        self.assertEqual(payload["rollback_result_summary"]["status"], "succeeded")

    def test_rollback_refuses_when_target_or_scope_is_ambiguous(self) -> None:
        with tempfile.TemporaryDirectory() as repo_dir:
            trace = self._init_merged_repo(repo_dir)
            read_backend = _FakeRollbackReadBackend(head_sha="f" * 40)
            payload = BoundedRollbackExecutor(read_backend=read_backend).execute_rollback(
                job_id="job-rollback-2",
                repository="rai0409/codex-local-runner",
                repo_path=repo_dir,
                target_ref=trace["target_ref"],
                pre_merge_sha=trace["pre_merge_sha"],
                post_merge_sha=trace["post_merge_sha"],
            )
        self.assertFalse(payload["succeeded"])
        self.assertEqual(payload["refusal_reason"], "rollback_target_head_mismatch")

    def test_rollback_refuses_on_blocking_backend_statuses(self) -> None:
        for status in ("auth_failure", "api_failure", "unsupported_query"):
            with self.subTest(status=status):
                with tempfile.TemporaryDirectory() as repo_dir:
                    trace = self._init_merged_repo(repo_dir)
                    read_backend = _FakeRollbackReadBackend(head_sha=trace["post_merge_sha"])
                    read_backend.compare_payload = _read_result("compare_refs", status, {})
                    payload = BoundedRollbackExecutor(read_backend=read_backend).execute_rollback(
                        job_id=f"job-rollback-{status}",
                        repository="rai0409/codex-local-runner",
                        repo_path=repo_dir,
                        target_ref=trace["target_ref"],
                        pre_merge_sha=trace["pre_merge_sha"],
                        post_merge_sha=trace["post_merge_sha"],
                    )
                self.assertFalse(payload["succeeded"])
                self.assertEqual(payload["refusal_reason"], f"rollback_compare_failed:{status}")

    def test_rollback_handles_empty_and_not_found_conservatively(self) -> None:
        with tempfile.TemporaryDirectory() as repo_dir:
            trace = self._init_merged_repo(repo_dir)
            read_empty = _FakeRollbackReadBackend(head_sha=trace["post_merge_sha"])
            read_empty.compare_payload = _read_result("compare_refs", "empty", {})
            empty_payload = BoundedRollbackExecutor(read_backend=read_empty).execute_rollback(
                job_id="job-rollback-empty",
                repository="rai0409/codex-local-runner",
                repo_path=repo_dir,
                target_ref=trace["target_ref"],
                pre_merge_sha=trace["pre_merge_sha"],
                post_merge_sha=trace["post_merge_sha"],
            )
            read_not_found = _FakeRollbackReadBackend(head_sha=trace["post_merge_sha"])
            read_not_found.compare_payload = _read_result("compare_refs", "not_found", {})
            not_found_payload = BoundedRollbackExecutor(read_backend=read_not_found).execute_rollback(
                job_id="job-rollback-not-found",
                repository="rai0409/codex-local-runner",
                repo_path=repo_dir,
                target_ref=trace["target_ref"],
                pre_merge_sha=trace["pre_merge_sha"],
                post_merge_sha=trace["post_merge_sha"],
            )
        self.assertEqual(empty_payload["refusal_reason"], "rollback_compare_missing:empty")
        self.assertEqual(not_found_payload["refusal_reason"], "rollback_compare_missing:not_found")

    def test_rollback_outputs_are_deterministic_for_same_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as repo_dir:
            trace = self._init_merged_repo(repo_dir)
            read_backend = _FakeRollbackReadBackend(head_sha=trace["post_merge_sha"])
            executor = BoundedRollbackExecutor(read_backend=read_backend)
            kwargs = {
                "job_id": "job-rollback-det",
                "repository": "rai0409/codex-local-runner",
                "repo_path": repo_dir,
                "target_ref": trace["target_ref"],
                "pre_merge_sha": trace["pre_merge_sha"],
                "post_merge_sha": trace["post_merge_sha"],
            }
            first = executor.execute_rollback(**kwargs)
            # second call should refuse because repo state changed by first rollback; use a fresh repo for deterministic comparison
        with tempfile.TemporaryDirectory() as repo_dir2:
            trace2 = self._init_merged_repo(repo_dir2)
            read_backend2 = _FakeRollbackReadBackend(head_sha=trace2["post_merge_sha"])
            executor2 = BoundedRollbackExecutor(read_backend=read_backend2)
            second = executor2.execute_rollback(
                job_id="job-rollback-det",
                repository="rai0409/codex-local-runner",
                repo_path=repo_dir2,
                target_ref=trace2["target_ref"],
                pre_merge_sha=trace2["pre_merge_sha"],
                post_merge_sha=trace2["post_merge_sha"],
            )
        first_cmp = dict(first)
        second_cmp = dict(second)
        first_cmp["rollback_target"] = {
            **(first_cmp.get("rollback_target") or {}),
            "repo_path": "<normalized>",
            "pre_merge_sha": "<normalized>",
            "post_merge_sha": "<normalized>",
        }
        second_cmp["rollback_target"] = {
            **(second_cmp.get("rollback_target") or {}),
            "repo_path": "<normalized>",
            "pre_merge_sha": "<normalized>",
            "post_merge_sha": "<normalized>",
        }
        first_cmp["rollback_result_summary"] = {
            **(first_cmp.get("rollback_result_summary") or {}),
            "current_head_sha": "<normalized>",
            "rollback_result_sha": "<normalized>",
        }
        second_cmp["rollback_result_summary"] = {
            **(second_cmp.get("rollback_result_summary") or {}),
            "current_head_sha": "<normalized>",
            "rollback_result_sha": "<normalized>",
        }
        first_idempotency = first_cmp.get("idempotency")
        second_idempotency = second_cmp.get("idempotency")
        if isinstance(first_idempotency, dict):
            first_idempotency["idempotency_key"] = "<normalized>"
            first_idempotency["intent_fingerprint"] = "<normalized>"
        if isinstance(second_idempotency, dict):
            second_idempotency["idempotency_key"] = "<normalized>"
            second_idempotency["intent_fingerprint"] = "<normalized>"
        self.assertEqual(first_cmp, second_cmp)

    def test_rollback_replay_already_applied_when_head_is_pre_merge_sha(self) -> None:
        with tempfile.TemporaryDirectory() as repo_dir:
            trace = self._init_merged_repo(repo_dir)
            with tempfile.TemporaryDirectory() as receipt_dir:
                store = FileWriteReceiptStore(Path(receipt_dir))
                first = BoundedRollbackExecutor(
                    read_backend=_FakeRollbackReadBackend(head_sha=trace["post_merge_sha"])
                ).execute_rollback(
                    job_id="job-rollback-replay",
                    repository="rai0409/codex-local-runner",
                    repo_path=repo_dir,
                    target_ref=trace["target_ref"],
                    pre_merge_sha=trace["pre_merge_sha"],
                    post_merge_sha=trace["post_merge_sha"],
                    write_receipt_store=store,
                )
                second = BoundedRollbackExecutor(
                    read_backend=_FakeRollbackReadBackend(head_sha=trace["pre_merge_sha"])
                ).execute_rollback(
                    job_id="job-rollback-replay",
                    repository="rai0409/codex-local-runner",
                    repo_path=repo_dir,
                    target_ref=trace["target_ref"],
                    pre_merge_sha=trace["pre_merge_sha"],
                    post_merge_sha=trace["post_merge_sha"],
                    write_receipt_store=store,
                )
        self.assertTrue(first["succeeded"])
        self.assertTrue(second["succeeded"])
        self.assertFalse(second["attempted"])
        self.assertEqual(second["rollback_result_summary"]["status"], "already_applied")


if __name__ == "__main__":
    unittest.main()
