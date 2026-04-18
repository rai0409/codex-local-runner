from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from automation.control.action_executor import ActionExecutor
from automation.github.merge_executor import BoundedMergeExecutor
from automation.github.pr_creator import DraftPRCreator
from automation.github.pr_updater import BoundedPRUpdater
from automation.github.rollback_executor import BoundedRollbackExecutor


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
            {"comparison_status": "ahead", "changed_files": ["docs/readme.md"]},
        )
        self.open_pr_payload = _read_result(
            "find_open_pr",
            "success",
            {"matched": True, "match_count": 1, "pr": {"number": 42}},
        )
        self.status_payload = _read_result(
            "get_pr_status_summary",
            "success",
            {
                "commit_sha": "a" * 40,
                "pr_state": "open",
                "pr_draft": False,
                "pr_merged": False,
                "mergeable_state": "clean",
                "pr_head_ref": "feature/test",
                "pr_base_ref": "main",
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

    def get_default_branch(self, repo: str):
        return dict(self.default_branch_payload)

    def get_branch_head(self, repo: str, branch: str):
        if branch in {"feature/test", "main"}:
            if branch == "feature/test":
                return dict(self.head_payload)
            return dict(self.base_payload)
        return dict(self.base_payload)

    def compare_refs(self, repo: str, base_ref: str, head_ref: str):
        return dict(self.compare_payload)

    def find_open_pr(self, repo: str, *, head_branch: str | None = None, base_branch: str | None = None):
        return dict(self.open_pr_payload)

    def get_pr_status_summary(self, repo: str, *, pr_number: int | None = None, commit_sha: str | None = None):
        return dict(self.status_payload)

    def get_pull_request(self, repo: str, pr_number: int):
        return dict(self.pull_request_payload)


class _FakeWriteBackend:
    def __init__(self) -> None:
        self.pr_payload = _write_result(
            "create_draft_pr",
            "success",
            {
                "pr": {
                    "number": 99,
                    "html_url": "https://example.test/pr/99",
                    "draft": True,
                }
            },
        )
        self.merge_payload = _write_result(
            "merge_pull_request",
            "success",
            {
                "merged": True,
                "merge_commit_sha": "c" * 40,
            },
        )
        self.pr_calls: list[dict[str, object]] = []
        self.merge_calls: list[dict[str, object]] = []
        self.update_calls: list[dict[str, object]] = []
        self.branch_delete_called = False
        self.force_push_called = False
        self.update_payload = _write_result(
            "update_existing_pr",
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

    def create_draft_pr(
        self,
        *,
        repo: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str,
    ):
        self.pr_calls.append(
            {
                "repo": repo,
                "title": title,
                "body": body,
                "head_branch": head_branch,
                "base_branch": base_branch,
            }
        )
        return dict(self.pr_payload)

    def merge_pull_request(
        self,
        *,
        repo: str,
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
        return dict(self.merge_payload)

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
        self.update_calls.append(
            {
                "repo": repo,
                "pr_number": pr_number,
                "title": title,
                "body": body,
                "base_branch": base_branch,
                "has_current_pr": isinstance(current_pr, dict),
            }
        )
        return dict(self.update_payload)

    # Guardrails for this phase.
    def delete_branch(self, *args, **kwargs):  # pragma: no cover
        self.branch_delete_called = True
        raise AssertionError("delete_branch must not be called in this phase")

    def force_push(self, *args, **kwargs):  # pragma: no cover
        self.force_push_called = True
        raise AssertionError("force_push must not be called in this phase")


class ActionExecutorTests(unittest.TestCase):
    def _fixed_now(self) -> datetime:
        return datetime(2026, 4, 18, 13, 30, 0)

    def _write_json(self, path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

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

    def _write_run_artifacts(
        self,
        root: Path,
        *,
        handoff: dict[str, object],
        next_action: dict[str, object],
    ) -> Path:
        run_dir = root / "executions" / "job-1"
        planning_dir = root / "planning"
        planning_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(
            planning_dir / "project_brief.json",
            {
                "project_id": "job-1",
                "target_repo": "rai0409/codex-local-runner",
                "target_branch": "main",
            },
        )
        self._write_json(
            planning_dir / "repo_facts.json",
            {
                "repo": "rai0409/codex-local-runner",
                "default_branch": "main",
            },
        )
        self._write_json(
            planning_dir / "pr_plan.json",
            {
                "plan_id": "plan-1",
                "prs": [
                    {
                        "pr_id": "pr-01",
                        "title": "[docs] update docs",
                        "tier_category": "docs_only",
                    }
                ],
            },
        )
        self._write_json(
            run_dir / "manifest.json",
            {
                "job_id": "job-1",
                "artifact_input_dir": str(planning_dir),
                "pr_units": [],
            },
        )
        self._write_json(run_dir / "action_handoff.json", handoff)
        self._write_json(run_dir / "next_action.json", next_action)
        return run_dir

    def _build_executor(self, read_backend: _FakeReadBackend, write_backend: _FakeWriteBackend) -> ActionExecutor:
        return ActionExecutor(
            pr_creator=DraftPRCreator(read_backend=read_backend, write_backend=write_backend, now=self._fixed_now),
            pr_updater=BoundedPRUpdater(read_backend=read_backend, write_backend=write_backend, now=self._fixed_now),
            merge_executor=BoundedMergeExecutor(read_backend=read_backend, write_backend=write_backend, now=self._fixed_now),
            rollback_executor=BoundedRollbackExecutor(read_backend=read_backend, now=self._fixed_now),
            now=self._fixed_now,
        )

    def _write_authority_allowed(self) -> dict[str, object]:
        return {
            "state": "write_allowed",
            "write_actions_allowed": True,
            "allowed_categories": ["docs_only"],
            "allowed_actions": ["proceed_to_pr", "github.pr.update", "proceed_to_merge", "rollback_required"],
        }

    def test_proceed_to_pr_behavior_remains_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_dir = self._write_run_artifacts(
                Path(tmp_dir),
                handoff={
                    "job_id": "job-1",
                    "next_action": "proceed_to_pr",
                    "reason": "all units completed",
                    "action_consumable": True,
                    "whether_human_required": False,
                },
                next_action={"next_action": "proceed_to_pr"},
            )
            write_backend = _FakeWriteBackend()
            read_backend = _FakeReadBackend()
            read_backend.open_pr_payload = _read_result(
                "find_open_pr",
                "empty",
                {"matched": False, "match_count": 0, "pr": None},
            )
            receipt = self._build_executor(read_backend, write_backend).execute_from_run_dir(
                run_dir,
                head_branch="feature/test",
                write_authority=self._write_authority_allowed(),
            )
            persisted = json.loads((run_dir / "pr_creation_receipt.json").read_text(encoding="utf-8"))

        self.assertTrue(receipt["succeeded"])
        self.assertEqual(receipt["pr_number"], 99)
        self.assertEqual(receipt, persisted)
        self.assertEqual(len(write_backend.pr_calls), 1)
        self.assertEqual(len(write_backend.merge_calls), 0)

    def test_replayed_proceed_to_pr_uses_idempotent_receipt_and_avoids_duplicate_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_dir = self._write_run_artifacts(
                Path(tmp_dir),
                handoff={
                    "job_id": "job-1",
                    "next_action": "proceed_to_pr",
                    "reason": "all units completed",
                    "action_consumable": True,
                    "whether_human_required": False,
                },
                next_action={"next_action": "proceed_to_pr"},
            )
            write_backend = _FakeWriteBackend()
            read_backend = _FakeReadBackend()
            read_backend.open_pr_payload = _read_result(
                "find_open_pr",
                "empty",
                {"matched": False, "match_count": 0, "pr": None},
            )
            executor = self._build_executor(read_backend, write_backend)
            first = executor.execute_from_run_dir(
                run_dir,
                head_branch="feature/test",
                write_authority=self._write_authority_allowed(),
            )
            read_backend.open_pr_payload = _read_result(
                "find_open_pr",
                "success",
                {"matched": True, "match_count": 1, "pr": {"number": 99, "html_url": "https://example.test/pr/99"}},
            )
            second = executor.execute_from_run_dir(
                run_dir,
                head_branch="feature/test",
                write_authority=self._write_authority_allowed(),
            )

        self.assertTrue(first["succeeded"])
        self.assertTrue(second["succeeded"])
        self.assertFalse(second["attempted"])
        self.assertEqual(len(write_backend.pr_calls), 1)

    def test_refuses_when_explicit_lane_request_is_disallowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_dir = self._write_run_artifacts(
                Path(tmp_dir),
                handoff={
                    "job_id": "job-1",
                    "next_action": "proceed_to_pr",
                    "reason": "all units completed",
                    "action_consumable": True,
                    "whether_human_required": False,
                },
                next_action={"next_action": "proceed_to_pr"},
            )
            write_backend = _FakeWriteBackend()
            read_backend = _FakeReadBackend()
            receipt = self._build_executor(read_backend, write_backend).execute_from_run_dir(
                run_dir,
                head_branch="feature/test",
                write_authority=self._write_authority_allowed(),
                policy_snapshot={"requested_execution_lane": "llm_backed"},
            )

        self.assertFalse(receipt["succeeded"])
        self.assertEqual(receipt["refusal_reason"], "authority_requested_lane_not_allowed")
        self.assertEqual(len(write_backend.pr_calls), 0)

    def test_canonical_handoff_lane_intent_is_enforced_consistently(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_dir = self._write_run_artifacts(
                Path(tmp_dir),
                handoff={
                    "job_id": "job-1",
                    "next_action": "proceed_to_pr",
                    "reason": "all units completed",
                    "action_consumable": True,
                    "whether_human_required": False,
                    "requested_execution": {
                        "requested_lanes": {"proceed_to_pr": "github_deterministic"},
                    },
                },
                next_action={"next_action": "proceed_to_pr"},
            )
            write_backend = _FakeWriteBackend()
            read_backend = _FakeReadBackend()
            receipt = self._build_executor(read_backend, write_backend).execute_from_run_dir(
                run_dir,
                head_branch="feature/test",
                write_authority=self._write_authority_allowed(),
            )

        self.assertTrue(receipt["succeeded"])
        self.assertIsNone(receipt["refusal_reason"])

    def test_canonical_handoff_lane_disallowed_for_github_action_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_dir = self._write_run_artifacts(
                Path(tmp_dir),
                handoff={
                    "job_id": "job-1",
                    "next_action": "proceed_to_pr",
                    "reason": "all units completed",
                    "action_consumable": True,
                    "whether_human_required": False,
                    "requested_execution": {
                        "requested_lanes": {"proceed_to_pr": "llm_backed"},
                    },
                },
                next_action={"next_action": "proceed_to_pr"},
            )
            write_backend = _FakeWriteBackend()
            read_backend = _FakeReadBackend()
            receipt = self._build_executor(read_backend, write_backend).execute_from_run_dir(
                run_dir,
                head_branch="feature/test",
                write_authority=self._write_authority_allowed(),
            )

        self.assertFalse(receipt["succeeded"])
        self.assertEqual(receipt["refusal_reason"], "authority_requested_lane_not_allowed")
        self.assertEqual(len(write_backend.pr_calls), 0)

    def test_github_pr_update_routes_through_action_executor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_dir = self._write_run_artifacts(
                Path(tmp_dir),
                handoff={
                    "job_id": "job-1",
                    "next_action": "github.pr.update",
                    "reason": "bounded update",
                    "action_consumable": True,
                    "whether_human_required": False,
                    "pr_update": {"title": "Updated title"},
                },
                next_action={"next_action": "github.pr.update"},
            )
            write_backend = _FakeWriteBackend()
            read_backend = _FakeReadBackend()
            receipt = self._build_executor(read_backend, write_backend).execute_from_run_dir(
                run_dir,
                write_authority=self._write_authority_allowed(),
                pr_number=42,
                pr_update={"title": "Updated title"},
            )
            persisted = json.loads((run_dir / "pr_update_receipt.json").read_text(encoding="utf-8"))

        self.assertTrue(receipt["succeeded"])
        self.assertTrue(receipt["attempted"])
        self.assertEqual(receipt["pr_number"], 42)
        self.assertEqual(receipt, persisted)
        self.assertEqual(len(write_backend.update_calls), 1)

    def test_github_pr_update_noop_when_requested_state_already_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_dir = self._write_run_artifacts(
                Path(tmp_dir),
                handoff={
                    "job_id": "job-1",
                    "next_action": "github.pr.update",
                    "reason": "bounded update",
                    "action_consumable": True,
                    "whether_human_required": False,
                    "pr_update": {"title": "Current title"},
                },
                next_action={"next_action": "github.pr.update"},
            )
            write_backend = _FakeWriteBackend()
            read_backend = _FakeReadBackend()
            read_backend.pull_request_payload["title"] = "Current title"
            receipt = self._build_executor(read_backend, write_backend).execute_from_run_dir(
                run_dir,
                write_authority=self._write_authority_allowed(),
                pr_number=42,
                pr_update={"title": "Current title"},
            )

        self.assertTrue(receipt["succeeded"])
        self.assertFalse(receipt["attempted"])
        self.assertEqual(len(write_backend.update_calls), 0)

    def test_github_pr_update_replay_same_intent_does_not_duplicate_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_dir = self._write_run_artifacts(
                Path(tmp_dir),
                handoff={
                    "job_id": "job-1",
                    "next_action": "github.pr.update",
                    "reason": "bounded update",
                    "action_consumable": True,
                    "whether_human_required": False,
                    "pr_update": {"title": "Updated title"},
                },
                next_action={"next_action": "github.pr.update"},
            )
            write_backend = _FakeWriteBackend()
            read_backend = _FakeReadBackend()
            executor = self._build_executor(read_backend, write_backend)
            first = executor.execute_from_run_dir(
                run_dir,
                write_authority=self._write_authority_allowed(),
                pr_number=42,
                pr_update={"title": "Updated title"},
            )
            read_backend.pull_request_payload["title"] = "Updated title"
            second = executor.execute_from_run_dir(
                run_dir,
                write_authority=self._write_authority_allowed(),
                pr_number=42,
                pr_update={"title": "Updated title"},
            )

        self.assertTrue(first["succeeded"])
        self.assertTrue(second["succeeded"])
        self.assertFalse(second["attempted"])
        self.assertEqual(len(write_backend.update_calls), 1)

    def test_github_pr_update_omitted_vs_explicit_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_dir = self._write_run_artifacts(
                Path(tmp_dir),
                handoff={
                    "job_id": "job-1",
                    "next_action": "github.pr.update",
                    "reason": "bounded update",
                    "action_consumable": True,
                    "whether_human_required": False,
                    "pr_update": {"title": "Updated title"},
                },
                next_action={"next_action": "github.pr.update"},
            )
            write_backend = _FakeWriteBackend()
            read_backend = _FakeReadBackend()
            _ = self._build_executor(read_backend, write_backend).execute_from_run_dir(
                run_dir,
                write_authority=self._write_authority_allowed(),
                pr_number=42,
                pr_update={"title": "Updated title"},
            )

        self.assertEqual(len(write_backend.update_calls), 1)
        self.assertEqual(write_backend.update_calls[0]["title"], "Updated title")
        self.assertIsNone(write_backend.update_calls[0]["body"])
        self.assertIsNone(write_backend.update_calls[0]["base_branch"])

    def test_merge_success_under_fully_valid_conditions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_dir = self._write_run_artifacts(
                Path(tmp_dir),
                handoff={
                    "job_id": "job-1",
                    "next_action": "proceed_to_merge",
                    "reason": "all checks passing",
                    "action_consumable": True,
                    "whether_human_required": False,
                },
                next_action={"next_action": "proceed_to_merge"},
            )
            write_backend = _FakeWriteBackend()
            receipt = self._build_executor(_FakeReadBackend(), write_backend).execute_from_run_dir(
                run_dir,
                write_authority=self._write_authority_allowed(),
                pr_number=42,
                expected_head_sha="a" * 40,
            )

        self.assertTrue(receipt["attempted"])
        self.assertTrue(receipt["succeeded"])
        self.assertEqual(receipt["merge_commit_sha"], "c" * 40)
        self.assertEqual(len(write_backend.merge_calls), 1)
        self.assertFalse(write_backend.branch_delete_called)
        self.assertFalse(write_backend.force_push_called)

    def test_merge_refusal_paths_are_conservative(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            # Ambiguous PR lookup
            run_amb = self._write_run_artifacts(
                root / "amb",
                handoff={
                    "job_id": "job-1",
                    "next_action": "proceed_to_merge",
                    "reason": "all checks passing",
                    "action_consumable": True,
                    "whether_human_required": False,
                },
                next_action={"next_action": "proceed_to_merge"},
            )
            read_amb = _FakeReadBackend()
            read_amb.open_pr_payload = _read_result(
                "find_open_pr",
                "success",
                {"matched": True, "match_count": 2, "pr": {"number": 42}},
            )
            amb_receipt = self._build_executor(read_amb, _FakeWriteBackend()).execute_from_run_dir(
                run_amb,
                write_authority=self._write_authority_allowed(),
                pr_number=42,
            )

            # Checks failing
            run_checks = self._write_run_artifacts(
                root / "checks",
                handoff={
                    "job_id": "job-1",
                    "next_action": "proceed_to_merge",
                    "reason": "all checks passing",
                    "action_consumable": True,
                    "whether_human_required": False,
                },
                next_action={"next_action": "proceed_to_merge"},
            )
            read_checks = _FakeReadBackend()
            read_checks.status_payload = _read_result(
                "get_pr_status_summary",
                "success",
                {
                    "commit_sha": "a" * 40,
                    "pr_state": "open",
                    "pr_draft": False,
                    "pr_merged": False,
                    "mergeable_state": "clean",
                    "pr_head_ref": "feature/test",
                    "pr_base_ref": "main",
                    "checks_state": "pending",
                },
            )
            checks_receipt = self._build_executor(read_checks, _FakeWriteBackend()).execute_from_run_dir(
                run_checks,
                write_authority=self._write_authority_allowed(),
                pr_number=42,
            )

            # Blocking statuses + empty/not_found
            outcomes: list[dict[str, object]] = []
            for idx, status in enumerate(("auth_failure", "api_failure", "unsupported_query", "empty", "not_found"), start=1):
                run_dir = self._write_run_artifacts(
                    root / f"status-{idx}",
                    handoff={
                        "job_id": "job-1",
                        "next_action": "proceed_to_merge",
                        "reason": "all checks passing",
                        "action_consumable": True,
                        "whether_human_required": False,
                    },
                    next_action={"next_action": "proceed_to_merge"},
                )
                read_backend = _FakeReadBackend()
                read_backend.status_payload = _read_result("get_pr_status_summary", status, {})
                outcomes.append(
                    self._build_executor(read_backend, _FakeWriteBackend()).execute_from_run_dir(
                        run_dir,
                        write_authority=self._write_authority_allowed(),
                        pr_number=42,
                    )
                )

        self.assertEqual(amb_receipt["refusal_reason"], "open_pr_ambiguous")
        self.assertEqual(checks_receipt["refusal_reason"], "checks_not_passing:pending")
        self.assertEqual(outcomes[0]["refusal_reason"], "pr_status_unavailable:auth_failure")
        self.assertEqual(outcomes[1]["refusal_reason"], "pr_status_unavailable:api_failure")
        self.assertEqual(outcomes[2]["refusal_reason"], "pr_status_unavailable:unsupported_query")
        self.assertEqual(outcomes[3]["refusal_reason"], "pr_status_missing:empty")
        self.assertEqual(outcomes[4]["refusal_reason"], "pr_status_missing:not_found")

    def test_rollback_success_under_narrow_explicit_valid_conditions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_dir = Path(tmp_dir) / "repo"
            repo_dir.mkdir(parents=True, exist_ok=True)
            trace = self._init_merged_repo(str(repo_dir))
            run_dir = self._write_run_artifacts(
                Path(tmp_dir) / "run",
                handoff={
                    "job_id": "job-1",
                    "next_action": "rollback_required",
                    "reason": "explicit rollback required",
                    "action_consumable": True,
                    "whether_human_required": True,
                },
                next_action={"next_action": "rollback_required"},
            )
            read_backend = _FakeReadBackend()
            read_backend.base_payload = _read_result(
                "get_branch_head",
                "success",
                {"exists": True, "head_sha": trace["post_merge_sha"]},
            )
            write_backend = _FakeWriteBackend()
            executor = self._build_executor(read_backend, write_backend)
            receipt = executor.execute_from_run_dir(
                run_dir,
                write_authority=self._write_authority_allowed(),
                rollback_target={
                    "repo_path": str(repo_dir),
                    "target_ref": trace["target_ref"],
                    "pre_merge_sha": trace["pre_merge_sha"],
                    "post_merge_sha": trace["post_merge_sha"],
                },
            )
            persisted = json.loads((run_dir / "rollback_receipt.json").read_text(encoding="utf-8"))

        self.assertTrue(receipt["attempted"])
        self.assertTrue(receipt["succeeded"])
        self.assertEqual(receipt["rollback_result_summary"]["status"], "succeeded")
        self.assertEqual(receipt, persisted)

    def test_rollback_refusal_paths_are_conservative(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            repo_dir = root / "repo"
            repo_dir.mkdir(parents=True, exist_ok=True)
            trace = self._init_merged_repo(str(repo_dir))

            # Ambiguous target
            run_missing = self._write_run_artifacts(
                root / "missing",
                handoff={
                    "job_id": "job-1",
                    "next_action": "rollback_required",
                    "reason": "explicit rollback required",
                    "action_consumable": True,
                    "whether_human_required": True,
                },
                next_action={"next_action": "rollback_required"},
            )
            missing_receipt = self._build_executor(_FakeReadBackend(), _FakeWriteBackend()).execute_from_run_dir(
                run_missing,
                write_authority=self._write_authority_allowed(),
                rollback_target={},
            )

            # Blocking statuses + empty/not_found
            outcomes: list[dict[str, object]] = []
            statuses = ("auth_failure", "api_failure", "unsupported_query", "empty", "not_found")
            for idx, status in enumerate(statuses, start=1):
                run_dir = self._write_run_artifacts(
                    root / f"status-{idx}",
                    handoff={
                        "job_id": "job-1",
                        "next_action": "rollback_required",
                        "reason": "explicit rollback required",
                        "action_consumable": True,
                        "whether_human_required": True,
                    },
                    next_action={"next_action": "rollback_required"},
                )
                read_backend = _FakeReadBackend()
                read_backend.base_payload = _read_result(
                    "get_branch_head",
                    "success",
                    {"exists": True, "head_sha": trace["post_merge_sha"]},
                )
                read_backend.compare_payload = _read_result("compare_refs", status, {})
                outcomes.append(
                    self._build_executor(read_backend, _FakeWriteBackend()).execute_from_run_dir(
                        run_dir,
                        write_authority=self._write_authority_allowed(),
                        rollback_target={
                            "repo_path": str(repo_dir),
                            "target_ref": trace["target_ref"],
                            "pre_merge_sha": trace["pre_merge_sha"],
                            "post_merge_sha": trace["post_merge_sha"],
                        },
                    )
                )

        self.assertEqual(missing_receipt["refusal_reason"], "rollback_target_missing_or_ambiguous")
        self.assertEqual(outcomes[0]["refusal_reason"], "rollback_compare_failed:auth_failure")
        self.assertEqual(outcomes[1]["refusal_reason"], "rollback_compare_failed:api_failure")
        self.assertEqual(outcomes[2]["refusal_reason"], "rollback_compare_failed:unsupported_query")
        self.assertEqual(outcomes[3]["refusal_reason"], "rollback_compare_missing:empty")
        self.assertEqual(outcomes[4]["refusal_reason"], "rollback_compare_missing:not_found")

    def test_refusal_when_write_authority_blocks_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_dir = self._write_run_artifacts(
                Path(tmp_dir),
                handoff={
                    "job_id": "job-1",
                    "next_action": "proceed_to_merge",
                    "reason": "all checks passing",
                    "action_consumable": True,
                    "whether_human_required": False,
                },
                next_action={"next_action": "proceed_to_merge"},
            )
            receipt = self._build_executor(_FakeReadBackend(), _FakeWriteBackend()).execute_from_run_dir(
                run_dir,
                write_authority={
                    "state": "dry_run_only",
                    "write_actions_allowed": False,
                    "allowed_categories": ["docs_only"],
                    "allowed_actions": ["proceed_to_merge"],
                },
                pr_number=42,
            )
        self.assertFalse(receipt["attempted"])
        self.assertEqual(receipt["refusal_reason"], "write_authority_blocked:dry_run_only")

    def test_receipts_are_deterministic_for_equivalent_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            run_a = self._write_run_artifacts(
                root / "a",
                handoff={
                    "job_id": "job-1",
                    "next_action": "proceed_to_merge",
                    "reason": "all checks passing",
                    "action_consumable": True,
                    "whether_human_required": False,
                },
                next_action={"next_action": "proceed_to_merge"},
            )
            run_b = self._write_run_artifacts(
                root / "b",
                handoff={
                    "job_id": "job-1",
                    "next_action": "proceed_to_merge",
                    "reason": "all checks passing",
                    "action_consumable": True,
                    "whether_human_required": False,
                },
                next_action={"next_action": "proceed_to_merge"},
            )
            executor_a = self._build_executor(_FakeReadBackend(), _FakeWriteBackend())
            executor_b = self._build_executor(_FakeReadBackend(), _FakeWriteBackend())
            receipt_a = executor_a.execute_from_run_dir(
                run_a,
                write_authority=self._write_authority_allowed(),
                pr_number=42,
                expected_head_sha="a" * 40,
            )
            receipt_b = executor_b.execute_from_run_dir(
                run_b,
                write_authority=self._write_authority_allowed(),
                pr_number=42,
                expected_head_sha="a" * 40,
            )
        self.assertEqual(receipt_a, receipt_b)


if __name__ == "__main__":
    unittest.main()
